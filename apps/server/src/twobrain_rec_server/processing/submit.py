from __future__ import annotations

import shutil
import tempfile
from dataclasses import dataclass
from pathlib import Path

from anyio import to_thread
from sqlalchemy.ext.asyncio import AsyncSession

from twobrain_rec_server.config import Settings
from twobrain_rec_server.db.models import MediaScribeJob, ProcessingWorkflow
from twobrain_rec_server.domain.statuses import MediaScribeJobStatus, ProcessingStatus
from twobrain_rec_server.mediascribe.client import MediaScribeClientError
from twobrain_rec_server.mediascribe.import_results import (
    MediaScribeResultValidationError,
    normalize_result,
    result_digest,
)
from twobrain_rec_server.outcomes.service import ensure_outcomes_for_processing_result
from twobrain_rec_server.processing import store
from twobrain_rec_server.processing.reasons import (
    BLOCKED_AUDIO_TOO_LARGE,
    BLOCKED_MISSING_ARTIFACTS,
    MEDIASCRIBE_MALFORMED_RESPONSE,
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

    mic, incoming = await store.load_track_pair(
        db,
        workspace_id=workflow.workspace_id,
        meeting_id=workflow.meeting_id,
        media_revision_id=workflow.media_revision_id,
    )
    if mic is None or incoming is None:
        await store.set_workflow_status(
            db,
            workflow,
            ProcessingStatus.BLOCKED,
            reason_code=BLOCKED_MISSING_ARTIFACTS,
            terminal=True,
        )
        raise RuntimeError(BLOCKED_MISSING_ARTIFACTS)

    audio_bytes = mic.byte_length + incoming.byte_length
    if audio_bytes > settings.processing_max_submit_audio_bytes:
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
        mic_artifact=mic,
        incoming_artifact=incoming,
    )
    await store.set_workflow_status(db, workflow, ProcessingStatus.SUBMITTING)
    try:
        with tempfile.TemporaryDirectory(prefix="twobrain-rec-mediascribe-") as temp_dir:
            _ensure_temp_capacity(Path(temp_dir), audio_bytes)
            mic_path = Path(temp_dir) / "microphone.wav"
            incoming_path = Path(temp_dir) / "incoming.wav"
            await _stage_artifact(storage, mic.storage_object_key, mic_path, expected_bytes=mic.byte_length)
            await _stage_artifact(storage, incoming.storage_object_key, incoming_path, expected_bytes=incoming.byte_length)
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


async def _stage_artifact(storage: object, object_key: str, target_path: Path, *, expected_bytes: int) -> None:
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

    await store.update_mediascribe_job_status(db, job=job, status=poll.status, reason_code=poll.reason_code)
    if poll.status != MediaScribeJobStatus.READY:
        if poll.status == MediaScribeJobStatus.FAILED:
            await store.set_workflow_status(db, workflow, ProcessingStatus.FAILED_TERMINAL, reason_code=poll.reason_code, terminal=True)
            return ImportProcessingResult(imported=False, status=ProcessingStatus.FAILED_TERMINAL)
        return ImportProcessingResult(imported=False, status=ProcessingStatus.POLLING)

    await store.set_workflow_status(db, workflow, ProcessingStatus.IMPORTING)
    try:
        result = normalize_result(await mediascribe_client.fetch_result(job.external_job_id))
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
    await store.set_workflow_status(db, workflow, ProcessingStatus.PROCESSED, terminal=True)
    await store.record_processing_audit_event(
        db,
        workspace_id=workflow.workspace_id,
        meeting_id=workflow.meeting_id,
        processing_workflow_id=workflow.id,
        mediascribe_job_id=job.id,
        event_type="result_imported",
        metadata={
            "segment_count": len(result.transcript),
            "diarization_segment_count": len(result.diarization),
            "summary_status": result.summary_status.value,
        },
    )
    return ImportProcessingResult(imported=True, status=ProcessingStatus.PROCESSED)
