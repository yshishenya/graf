from __future__ import annotations

from dataclasses import dataclass

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
from twobrain_rec_server.processing import store
from twobrain_rec_server.processing.reasons import (
    BLOCKED_MISSING_ARTIFACTS,
    MEDIASCRIBE_MALFORMED_RESPONSE,
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
    )
    if existing_job is not None and existing_job.external_job_id:
        return SubmitProcessingResult(job=existing_job, submitted=False)

    mic, incoming = await store.load_track_pair(
        db,
        workspace_id=workflow.workspace_id,
        meeting_id=workflow.meeting_id,
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

    job = await store.upsert_mediascribe_job(
        db,
        workflow=workflow,
        mic_artifact=mic,
        incoming_artifact=incoming,
    )
    await store.set_workflow_status(db, workflow, ProcessingStatus.SUBMITTING)
    get_bytes_async = getattr(storage, "get_bytes_async", None)
    if get_bytes_async is not None:
        mic_bytes = await get_bytes_async(mic.storage_object_key)
        incoming_bytes = await get_bytes_async(incoming.storage_object_key)
    else:
        mic_bytes = storage.get_bytes(mic.storage_object_key)
        incoming_bytes = storage.get_bytes(incoming.storage_object_key)
    try:
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
    await store.persist_processing_result(
        db,
        job=job,
        result=result,
        source_result_hash=result_digest(result),
    )
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
