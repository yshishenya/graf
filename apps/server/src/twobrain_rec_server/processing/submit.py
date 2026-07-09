from __future__ import annotations

from dataclasses import dataclass

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
    BLOCKED_MISSING_ARTIFACTS,
    DIAGNOSTIC_INPUT_AUDIO_PROBLEM,
    DIAGNOSTIC_MEDIASCRIBE_SERVICE_PROBLEM,
    DIAGNOSTIC_PROCESSED_NO_TRANSCRIPT,
    FAILURE_SOURCE_INPUT_AUDIO,
    FAILURE_SOURCE_MEDIASCRIBE,
    INVALID_AUDIO_PAYLOAD,
    MEDIASCRIBE_MALFORMED_RESPONSE,
    NO_RECOGNIZABLE_SPEECH,
)


@dataclass(frozen=True, slots=True)
class SubmitProcessingResult:
    job: MediaScribeJob
    submitted: bool


@dataclass(frozen=True, slots=True)
class ImportProcessingResult:
    imported: bool
    status: ProcessingStatus


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

    if source.byte_length > settings.processing_max_in_memory_audio_bytes:
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
    get_bytes_async = getattr(storage, "get_bytes_async", None)
    try:
        if source.request_mode == "single_track":
            media_artifact = source.source_artifact
            if media_artifact is None:
                raise RuntimeError(BLOCKED_MISSING_ARTIFACTS)
            if get_bytes_async is not None:
                media_bytes = await get_bytes_async(media_artifact.storage_object_key)
            else:
                media_bytes = storage.get_bytes(media_artifact.storage_object_key)
            response = await mediascribe_client.submit_single_track(
                media_bytes=media_bytes,
                media_content_type=media_artifact.codec,
                diarize=settings.mediascribe_diarize,
                summarize=settings.mediascribe_summarize,
            )
        else:
            mic = source.mic_artifact
            incoming = source.incoming_artifact
            if mic is None or incoming is None:
                raise RuntimeError(BLOCKED_MISSING_ARTIFACTS)
            if get_bytes_async is not None:
                mic_bytes = await get_bytes_async(mic.storage_object_key)
                incoming_bytes = await get_bytes_async(incoming.storage_object_key)
            else:
                mic_bytes = storage.get_bytes(mic.storage_object_key)
                incoming_bytes = storage.get_bytes(incoming.storage_object_key)
            response = await mediascribe_client.submit_dual_track(
                mic_bytes=mic_bytes,
                incoming_bytes=incoming_bytes,
                diarize=settings.mediascribe_diarize,
                summarize=settings.mediascribe_summarize,
            )
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
