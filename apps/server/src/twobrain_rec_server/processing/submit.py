from __future__ import annotations

import shutil
import tempfile
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path

from anyio import to_thread
from sqlalchemy.ext.asyncio import AsyncSession

from twobrain_rec_server.config import Settings
from twobrain_rec_server.db.models import MediaScribeJob, ProcessingWorkflow
from twobrain_rec_server.domain.statuses import (
    MediaScribeJobStatus,
    ProcessingAvailabilityStatus,
    ProcessingStatus,
)
from twobrain_rec_server.mediascribe.client import MediaScribeClientError
from twobrain_rec_server.mediascribe.import_results import (
    MediaScribeResultValidationError,
    normalize_result,
    result_digest,
)
from twobrain_rec_server.mediascribe.schemas import MediaScribePollResponse, MediaScribeResult
from twobrain_rec_server.outcomes.service import ensure_outcomes_for_processing_result
from twobrain_rec_server.processing import store
from twobrain_rec_server.processing.reasons import (
    BLOCKED_AUDIO_TOO_LARGE,
    BLOCKED_MEDIASCRIBE_SUBMISSION_OUTCOME_UNKNOWN,
    BLOCKED_MISSING_ARTIFACTS,
    DIAGNOSTIC_INPUT_AUDIO_PROBLEM,
    DIAGNOSTIC_MEDIASCRIBE_SERVICE_PROBLEM,
    DIAGNOSTIC_PROCESSED_NO_TRANSCRIPT,
    FAILURE_SOURCE_INPUT_AUDIO,
    FAILURE_SOURCE_MEDIASCRIBE,
    INVALID_AUDIO_PAYLOAD,
    MEDIASCRIBE_MALFORMED_RESPONSE,
    NO_RECOGNIZABLE_SPEECH,
    PROCESSING_TEMP_STORAGE_UNAVAILABLE,
)

DOWNLOAD_CHUNK_BYTES = 4 * 1024 * 1024


@dataclass(frozen=True, slots=True)
class SubmitProcessingResult:
    job: MediaScribeJob
    submitted: bool


@dataclass(frozen=True, slots=True)
class ImportProcessingResult:
    imported: bool
    status: ProcessingStatus


class ArtifactStagingError(RuntimeError):
    pass


class TempStorageUnavailableError(RuntimeError):
    pass


async def submit_to_mediascribe(
    *,
    db: AsyncSession,
    settings: Settings,
    storage: object,
    mediascribe_client: object,
    workflow: ProcessingWorkflow,
) -> SubmitProcessingResult:
    existing_job = await store.get_mediascribe_job(
        db,
        workspace_id=workflow.workspace_id,
        meeting_id=workflow.meeting_id,
        media_revision_id=workflow.media_revision_id,
    )
    if existing_job is not None and existing_job.external_job_id:
        return SubmitProcessingResult(job=existing_job, submitted=False)
    if (
        existing_job is not None
        and existing_job.status == MediaScribeJobStatus.BLOCKED.value
        and existing_job.last_error_code == BLOCKED_MEDIASCRIBE_SUBMISSION_OUTCOME_UNKNOWN
    ):
        await store.set_workflow_status(
            db,
            workflow,
            ProcessingStatus.BLOCKED,
            reason_code=BLOCKED_MEDIASCRIBE_SUBMISSION_OUTCOME_UNKNOWN,
            terminal=True,
        )
        raise MediaScribeClientError(
            BLOCKED_MEDIASCRIBE_SUBMISSION_OUTCOME_UNKNOWN,
            retryable=False,
        )

    source = await store.load_processing_source(
        db,
        workspace_id=workflow.workspace_id,
        meeting_id=workflow.meeting_id,
        media_revision_id=workflow.media_revision_id,
    )
    if source is None:
        await store.set_workflow_status(
            db,
            workflow,
            ProcessingStatus.BLOCKED,
            reason_code=BLOCKED_MISSING_ARTIFACTS,
            terminal=True,
        )
        raise RuntimeError(BLOCKED_MISSING_ARTIFACTS)

    if source.byte_length > settings.processing_max_submit_audio_bytes:
        await store.set_workflow_status(
            db,
            workflow,
            ProcessingStatus.BLOCKED,
            reason_code=BLOCKED_AUDIO_TOO_LARGE,
            terminal=True,
        )
        raise RuntimeError(BLOCKED_AUDIO_TOO_LARGE)

    job = await store.upsert_mediascribe_job(
        db,
        workflow=workflow,
        mic_artifact=source.mic_artifact,
        incoming_artifact=source.incoming_artifact,
        source_artifact=source.source_artifact,
        request_mode=source.request_mode,
    )
    await store.set_workflow_status(db, workflow, ProcessingStatus.SUBMITTING)
    try:
        with tempfile.TemporaryDirectory(prefix="twobrain-rec-mediascribe-") as temp_dir:
            temp_path = Path(temp_dir)
            _ensure_temp_capacity(temp_path, source.byte_length)
            if source.request_mode == "single_track":
                media_artifact = source.source_artifact
                if media_artifact is None:
                    raise ArtifactStagingError("source_artifact_missing")
                media_path = temp_path / (
                    "meeting-transcription.wav" if source.is_v5_mixed_recording else "source-media.bin"
                )
                await _stage_artifact(
                    storage,
                    media_artifact.storage_object_key,
                    media_path,
                    expected_bytes=media_artifact.byte_length,
                    expected_sha256=media_artifact.sha256,
                )
                if source.is_v5_mixed_recording:
                    _verify_v5_canonical_wav(media_path)
                with media_path.open("rb") as media_file:
                    response = await mediascribe_client.submit_single_track(
                        media_file=media_file,
                        media_content_type="audio/wav" if source.is_v5_mixed_recording else media_artifact.codec,
                        media_filename="meeting-transcription.wav" if source.is_v5_mixed_recording else None,
                        diarize=settings.mediascribe_diarize,
                        summarize=settings.mediascribe_summarize,
                    )
            else:
                mic = source.mic_artifact
                incoming = source.incoming_artifact
                if mic is None or incoming is None:
                    raise ArtifactStagingError("track_artifact_missing")
                mic_path = temp_path / "microphone.wav"
                incoming_path = temp_path / "incoming.wav"
                await _stage_artifact(
                    storage,
                    mic.storage_object_key,
                    mic_path,
                    expected_bytes=mic.byte_length,
                    expected_sha256=mic.sha256,
                )
                await _stage_artifact(
                    storage,
                    incoming.storage_object_key,
                    incoming_path,
                    expected_bytes=incoming.byte_length,
                    expected_sha256=incoming.sha256,
                )
                with mic_path.open("rb") as mic_file, incoming_path.open("rb") as incoming_file:
                    response = await mediascribe_client.submit_dual_track(
                        mic_file=mic_file,
                        incoming_file=incoming_file,
                        diarize=settings.mediascribe_diarize,
                        summarize=settings.mediascribe_summarize,
                    )
    except ArtifactStagingError as exc:
        await store.set_workflow_status(
            db,
            workflow,
            ProcessingStatus.BLOCKED,
            reason_code=BLOCKED_MISSING_ARTIFACTS,
            terminal=True,
        )
        raise RuntimeError(BLOCKED_MISSING_ARTIFACTS) from exc
    except TempStorageUnavailableError as exc:
        await store.set_workflow_status(
            db,
            workflow,
            ProcessingStatus.FAILED_RETRYABLE,
            reason_code=PROCESSING_TEMP_STORAGE_UNAVAILABLE,
        )
        raise RuntimeError(PROCESSING_TEMP_STORAGE_UNAVAILABLE) from exc
    except OSError as exc:
        await store.set_workflow_status(
            db,
            workflow,
            ProcessingStatus.FAILED_RETRYABLE,
            reason_code=PROCESSING_TEMP_STORAGE_UNAVAILABLE,
        )
        raise RuntimeError(PROCESSING_TEMP_STORAGE_UNAVAILABLE) from exc
    except MediaScribeClientError as exc:
        if source.is_v5_mixed_recording and exc.retryable:
            await store.update_mediascribe_job_status(
                db,
                job=job,
                status=MediaScribeJobStatus.BLOCKED,
                reason_code=BLOCKED_MEDIASCRIBE_SUBMISSION_OUTCOME_UNKNOWN,
                error_message=BLOCKED_MEDIASCRIBE_SUBMISSION_OUTCOME_UNKNOWN,
            )
            await store.set_workflow_status(
                db,
                workflow,
                ProcessingStatus.BLOCKED,
                reason_code=BLOCKED_MEDIASCRIBE_SUBMISSION_OUTCOME_UNKNOWN,
                terminal=True,
            )
            raise MediaScribeClientError(
                BLOCKED_MEDIASCRIBE_SUBMISSION_OUTCOME_UNKNOWN,
                retryable=False,
            ) from exc
        status = ProcessingStatus.FAILED_RETRYABLE if exc.retryable else ProcessingStatus.FAILED_TERMINAL
        await store.update_mediascribe_job_status(
            db,
            job=job,
            status=MediaScribeJobStatus.FAILED,
            reason_code=exc.reason_code,
            error_message=exc.reason_code,
        )
        await store.set_workflow_status(db, workflow, status, reason_code=exc.reason_code, terminal=not exc.retryable)
        raise

    await store.persist_mediascribe_submission(
        db,
        job=job,
        external_job_id=response.external_job_id,
        status=response.status,
    )
    await store.set_workflow_status(db, workflow, ProcessingStatus.SUBMITTED)
    return SubmitProcessingResult(job=job, submitted=True)


def _ensure_temp_capacity(temp_dir: Path, expected_bytes: int) -> None:
    try:
        free_bytes = shutil.disk_usage(temp_dir).free
    except OSError as exc:
        raise TempStorageUnavailableError(PROCESSING_TEMP_STORAGE_UNAVAILABLE) from exc
    if free_bytes < expected_bytes:
        raise TempStorageUnavailableError(PROCESSING_TEMP_STORAGE_UNAVAILABLE)


async def _stage_artifact(
    storage: object,
    object_key: str,
    target_path: Path,
    *,
    expected_bytes: int,
    expected_sha256: str,
) -> None:
    download_to_path_async = getattr(storage, "download_to_path_async", None)
    download_to_path = getattr(storage, "download_to_path", None)
    try:
        if download_to_path_async is not None:
            downloaded = await download_to_path_async(object_key, target_path, chunk_size=DOWNLOAD_CHUNK_BYTES)
        elif download_to_path is not None:
            downloaded = await to_thread.run_sync(
                lambda: download_to_path(object_key, target_path, chunk_size=DOWNLOAD_CHUNK_BYTES)
            )
        else:
            raise ArtifactStagingError("storage_streaming_unavailable")
    except KeyError as exc:
        raise ArtifactStagingError("storage_object_missing") from exc
    except OSError as exc:
        raise TempStorageUnavailableError(PROCESSING_TEMP_STORAGE_UNAVAILABLE) from exc
    try:
        actual_bytes = target_path.stat().st_size
    except OSError as exc:
        raise ArtifactStagingError("storage_object_not_staged") from exc
    if downloaded != expected_bytes or actual_bytes != expected_bytes:
        raise ArtifactStagingError("storage_object_size_mismatch")
    try:
        actual_sha256 = await to_thread.run_sync(_sha256_file, target_path)
    except OSError as exc:
        raise ArtifactStagingError("storage_object_not_staged") from exc
    if actual_sha256 != expected_sha256:
        raise ArtifactStagingError("storage_object_digest_mismatch")


def _sha256_file(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as stream:
        while chunk := stream.read(DOWNLOAD_CHUNK_BYTES):
            digest.update(chunk)
    return digest.hexdigest()


def _verify_v5_canonical_wav(path: Path) -> None:
    """Verify the exact v5 PCM WAV boundary before any provider request.

    Descriptor validation at ingest is necessary but insufficient: this parses
    the staged bytes so a mislabeled object can never be sent as canonical
    audio. The parser is bounded to the RIFF headers and never loads audio into
    memory.
    """

    try:
        file_size = path.stat().st_size
        with path.open("rb") as stream:
            header = stream.read(12)
            if len(header) != 12 or header[:4] != b"RIFF" or header[8:12] != b"WAVE":
                raise ArtifactStagingError("invalid_v5_wav_header")
            riff_size = int.from_bytes(header[4:8], "little")
            if riff_size + 8 != file_size:
                raise ArtifactStagingError("invalid_v5_wav_size")
            fmt: bytes | None = None
            data_size: int | None = None
            while stream.tell() + 8 <= file_size:
                chunk_header = stream.read(8)
                chunk_id = chunk_header[:4]
                chunk_size = int.from_bytes(chunk_header[4:], "little")
                if chunk_size > file_size - stream.tell():
                    raise ArtifactStagingError("invalid_v5_wav_chunk")
                if chunk_id == b"fmt ":
                    fmt = stream.read(chunk_size)
                elif chunk_id == b"data":
                    data_size = chunk_size
                    stream.seek(chunk_size, 1)
                else:
                    stream.seek(chunk_size, 1)
                if chunk_size % 2:
                    if stream.tell() >= file_size:
                        raise ArtifactStagingError("invalid_v5_wav_padding")
                    stream.seek(1, 1)
    except OSError as exc:
        raise ArtifactStagingError("invalid_v5_wav") from exc

    if fmt is None or len(fmt) < 16 or data_size is None or data_size <= 0:
        raise ArtifactStagingError("invalid_v5_wav_format")
    audio_format = int.from_bytes(fmt[0:2], "little")
    channel_count = int.from_bytes(fmt[2:4], "little")
    sample_rate = int.from_bytes(fmt[4:8], "little")
    block_align = int.from_bytes(fmt[12:14], "little")
    bits_per_sample = int.from_bytes(fmt[14:16], "little")
    if (
        audio_format != 1
        or channel_count != 1
        or sample_rate != 16_000
        or block_align != 2
        or bits_per_sample != 16
        or data_size % block_align != 0
    ):
        raise ArtifactStagingError("invalid_v5_wav_format")


async def poll_and_import_mediascribe_result(
    *,
    db: AsyncSession,
    workflow: ProcessingWorkflow,
    job: MediaScribeJob,
    mediascribe_client: object,
) -> ImportProcessingResult:
    if job.external_job_id is None:
        await store.set_workflow_status(db, workflow, ProcessingStatus.FAILED_TERMINAL, reason_code="missing_external_job_id", terminal=True)
        return ImportProcessingResult(imported=False, status=ProcessingStatus.FAILED_TERMINAL)
    await store.set_workflow_status(db, workflow, ProcessingStatus.POLLING)
    try:
        poll = await mediascribe_client.poll_job(job.external_job_id)
    except MediaScribeClientError as exc:
        status = ProcessingStatus.FAILED_RETRYABLE if exc.retryable else ProcessingStatus.FAILED_TERMINAL
        await store.update_mediascribe_job_status(
            db,
            job=job,
            status=MediaScribeJobStatus.FAILED,
            reason_code=exc.reason_code,
            error_message=exc.reason_code,
        )
        await store.set_workflow_status(db, workflow, status, reason_code=exc.reason_code, terminal=not exc.retryable)
        return ImportProcessingResult(imported=False, status=status)

    if poll.status != MediaScribeJobStatus.READY:
        if poll.status == MediaScribeJobStatus.FAILED:
            await store.update_mediascribe_job_status(
                db,
                job=job,
                status=poll.status,
                reason_code=poll.reason_code,
                error_message=poll.error_origin,
            )
            if _is_input_audio_failure(poll):
                return await _persist_input_audio_failure_result(db=db, workflow=workflow, job=job, poll=poll)
            await store.set_workflow_status(
                db,
                workflow,
                ProcessingStatus.FAILED_TERMINAL,
                reason_code=poll.reason_code,
                terminal=True,
            )
            await _record_processing_diagnostic(
                db,
                workflow=workflow,
                job=job,
                event_type=DIAGNOSTIC_MEDIASCRIBE_SERVICE_PROBLEM,
                diagnostic_class=DIAGNOSTIC_MEDIASCRIBE_SERVICE_PROBLEM,
                error_code=poll.error_code or poll.reason_code,
                error_origin=poll.error_origin,
                failure_reason=poll.reason_code,
                failure_source=FAILURE_SOURCE_MEDIASCRIBE,
            )
            return ImportProcessingResult(imported=False, status=ProcessingStatus.FAILED_TERMINAL)
        await store.update_mediascribe_job_status(db, job=job, status=poll.status, reason_code=poll.reason_code)
        return ImportProcessingResult(imported=False, status=ProcessingStatus.POLLING)

    await store.update_mediascribe_job_status(db, job=job, status=poll.status, reason_code=poll.reason_code)
    await store.set_workflow_status(db, workflow, ProcessingStatus.IMPORTING)
    try:
        result = _classify_ready_result(normalize_result(await mediascribe_client.fetch_result(job.external_job_id)))
    except MediaScribeClientError as exc:
        status = ProcessingStatus.FAILED_RETRYABLE if exc.retryable else ProcessingStatus.FAILED_TERMINAL
        await store.update_mediascribe_job_status(
            db,
            job=job,
            status=MediaScribeJobStatus.FAILED,
            reason_code=exc.reason_code,
            error_message=exc.reason_code,
        )
        await store.set_workflow_status(db, workflow, status, reason_code=exc.reason_code, terminal=not exc.retryable)
        return ImportProcessingResult(imported=False, status=status)
    except MediaScribeResultValidationError:
        await store.update_mediascribe_job_status(
            db,
            job=job,
            status=MediaScribeJobStatus.FAILED,
            reason_code=MEDIASCRIBE_MALFORMED_RESPONSE,
            error_message=MEDIASCRIBE_MALFORMED_RESPONSE,
        )
        await store.set_workflow_status(
            db,
            workflow,
            ProcessingStatus.FAILED_RETRYABLE,
            reason_code=MEDIASCRIBE_MALFORMED_RESPONSE,
        )
        return ImportProcessingResult(imported=False, status=ProcessingStatus.FAILED_RETRYABLE)
    result_row = await store.persist_processing_result(
        db,
        job=job,
        result=result,
        source_result_hash=result_digest(result),
    )
    await ensure_outcomes_for_processing_result(db, result=result_row)
    await store.set_workflow_status(db, workflow, ProcessingStatus.PROCESSED, reason_code=result.failure_reason, terminal=True)
    await _record_import_diagnostic(db, workflow=workflow, job=job, result=result)
    return ImportProcessingResult(imported=True, status=ProcessingStatus.PROCESSED)


def _is_input_audio_failure(poll: MediaScribePollResponse) -> bool:
    return poll.error_code == INVALID_AUDIO_PAYLOAD and poll.error_origin == FAILURE_SOURCE_INPUT_AUDIO


def _classify_ready_result(result: MediaScribeResult) -> MediaScribeResult:
    if (
        result.transcript_status == ProcessingAvailabilityStatus.UNAVAILABLE
        and result.transcript_reason == NO_RECOGNIZABLE_SPEECH
    ):
        return result.model_copy(
            update={
                "failure_reason": NO_RECOGNIZABLE_SPEECH,
                "failure_source": FAILURE_SOURCE_INPUT_AUDIO,
            }
        )
    return result


async def _persist_input_audio_failure_result(
    *,
    db: AsyncSession,
    workflow: ProcessingWorkflow,
    job: MediaScribeJob,
    poll: MediaScribePollResponse,
) -> ImportProcessingResult:
    result = MediaScribeResult(
        external_job_id=job.external_job_id or poll.external_job_id,
        transcript_status=ProcessingAvailabilityStatus.UNAVAILABLE,
        failure_reason=poll.error_code or poll.reason_code or INVALID_AUDIO_PAYLOAD,
        failure_source=FAILURE_SOURCE_INPUT_AUDIO,
    )
    result_row = await store.persist_processing_result(
        db,
        job=job,
        result=result,
        source_result_hash=result_digest(result),
    )
    await ensure_outcomes_for_processing_result(db, result=result_row)
    await store.set_workflow_status(
        db,
        workflow,
        ProcessingStatus.PROCESSED,
        reason_code=result.failure_reason,
        terminal=True,
    )
    await _record_processing_diagnostic(
        db,
        workflow=workflow,
        job=job,
        event_type=DIAGNOSTIC_INPUT_AUDIO_PROBLEM,
        diagnostic_class=DIAGNOSTIC_INPUT_AUDIO_PROBLEM,
        error_code=poll.error_code or poll.reason_code,
        error_origin=poll.error_origin,
        failure_reason=result.failure_reason,
        failure_source=FAILURE_SOURCE_INPUT_AUDIO,
        transcript_status=ProcessingAvailabilityStatus.UNAVAILABLE.value,
    )
    return ImportProcessingResult(imported=True, status=ProcessingStatus.PROCESSED)


async def _record_import_diagnostic(
    db: AsyncSession,
    *,
    workflow: ProcessingWorkflow,
    job: MediaScribeJob,
    result: MediaScribeResult,
) -> None:
    if result.failure_source == FAILURE_SOURCE_INPUT_AUDIO and result.transcript_status == ProcessingAvailabilityStatus.UNAVAILABLE:
        await _record_processing_diagnostic(
            db,
            workflow=workflow,
            job=job,
            event_type=DIAGNOSTIC_PROCESSED_NO_TRANSCRIPT,
            diagnostic_class=DIAGNOSTIC_PROCESSED_NO_TRANSCRIPT,
            transcript_status=result.transcript_status.value,
            transcript_reason=result.transcript_reason,
            failure_reason=result.failure_reason,
            failure_source=result.failure_source,
            segment_count=len(result.transcript),
        )
        return
    await store.record_processing_audit_event(
        db,
        workspace_id=workflow.workspace_id,
        meeting_id=workflow.meeting_id,
        processing_workflow_id=workflow.id,
        mediascribe_job_id=job.id,
        event_type="result_imported",
        metadata={
            "mediascribe_job_id": job.id,
            "segment_count": len(result.transcript),
            "diarization_segment_count": len(result.diarization),
            "summary_status": result.summary_status.value,
            "transcript_status": result.transcript_status.value,
            "transcript_reason": result.transcript_reason,
        },
    )


async def _record_processing_diagnostic(
    db: AsyncSession,
    *,
    workflow: ProcessingWorkflow,
    job: MediaScribeJob,
    event_type: str,
    diagnostic_class: str,
    transcript_status: str | None = None,
    transcript_reason: str | None = None,
    error_code: str | None = None,
    error_origin: str | None = None,
    failure_reason: str | None = None,
    failure_source: str | None = None,
    segment_count: int | None = None,
) -> None:
    metadata = {
        "mediascribe_job_id": job.id,
        "transcript_status": transcript_status,
        "transcript_reason": transcript_reason,
        "error_code": error_code,
        "error_origin": error_origin,
        "failure_reason": failure_reason,
        "failure_source": failure_source,
        "diagnostic_class": diagnostic_class,
    }
    if segment_count is not None:
        metadata["segment_count"] = segment_count
    await store.record_processing_audit_event(
        db,
        workspace_id=workflow.workspace_id,
        meeting_id=workflow.meeting_id,
        processing_workflow_id=workflow.id,
        mediascribe_job_id=job.id,
        event_type=event_type,
        metadata={key: value for key, value in metadata.items() if value is not None},
    )
