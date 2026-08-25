from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from twobrain_rec_server.api.schemas import ProcessingArtifactProjection, ProcessingStatusResponse
from twobrain_rec_server.domain.statuses import (
    ProcessingAvailabilityStatus,
    ProcessingResultStatus,
    ProcessingStatus,
)
from twobrain_rec_server.processing import store
from twobrain_rec_server.processing.results import result_lineage_is_current


async def get_content_safe_processing_status(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    meeting_id: UUID,
) -> ProcessingStatusResponse | None:
    meeting = await store.load_meeting_for_workspace(db, workspace_id=workspace_id, meeting_id=meeting_id)
    if meeting is None:
        return None
    media_revision = await store.latest_media_revision_for_meeting(db, workspace_id=workspace_id, meeting_id=meeting_id)
    media_revision_id = media_revision.id if media_revision is not None else None
    workflow = await store.get_processing_workflow(
        db,
        workspace_id=workspace_id,
        meeting_id=meeting_id,
        media_revision_id=media_revision_id,
    )
    job = await store.get_mediascribe_job(
        db,
        workspace_id=workspace_id,
        meeting_id=meeting_id,
        media_revision_id=media_revision_id,
        processing_workflow_id=workflow.id if workflow is not None else None,
    )
    result = await store.latest_processing_result(
        db,
        workspace_id=workspace_id,
        meeting_id=meeting_id,
        media_revision_id=media_revision_id,
    )
    try:
        state = ProcessingStatus(workflow.status) if workflow is not None else ProcessingStatus(meeting.processing_status)
    except ValueError:
        state = ProcessingStatus.BLOCKED
    same_result_lineage = result_lineage_is_current(
        result,
        media_revision_id=media_revision_id,
    )
    safe_result = result if same_result_lineage else None
    result_terminal_no_speech = bool(
        safe_result is not None
        and safe_result.status == ProcessingResultStatus.IMPORTED.value
        and safe_result.failure_reason == "no_recognizable_speech"
    )
    if result_terminal_no_speech:
        state = ProcessingStatus.FAILED_TERMINAL
    transcript_available = (
        same_result_lineage
        and result.transcript_status == ProcessingAvailabilityStatus.AVAILABLE.value
        and result.segment_count > 0
        and result.diarization_status == ProcessingAvailabilityStatus.AVAILABLE.value
        and result.diarization_segment_count > 0
    )
    diarization_available = (
        same_result_lineage
        and result.diarization_status == ProcessingAvailabilityStatus.AVAILABLE.value
        and result.diarization_segment_count > 0
    )
    updated_at = None
    if workflow is not None:
        updated_at = workflow.updated_at
    elif result is not None:
        updated_at = result.updated_at
    retry_class = workflow.retry_class if workflow is not None and workflow.retry_class in {
        "retryable", "unknown_outcome", "terminal", "none"
    } else (
        "retryable" if state in {ProcessingStatus.FAILED_RETRYABLE, ProcessingStatus.WAITING_RETRY} else
        "unknown_outcome" if state == ProcessingStatus.BLOCKED_UNKNOWN else
        "terminal" if state == ProcessingStatus.FAILED_TERMINAL else "none"
    )
    if result_terminal_no_speech:
        retry_class = "terminal"
    next_attempt_source = workflow.next_attempt_source if workflow is not None and workflow.next_attempt_source in {
        "provider_retry_after", "provider_next_retry_at", "server_fallback", "manual_override"
    } else None
    attempt_in_flight = state in {
        ProcessingStatus.STARTING,
        ProcessingStatus.WORKFLOW_STARTED,
        ProcessingStatus.SUBMITTING,
        ProcessingStatus.SUBMITTED,
        ProcessingStatus.POLLING,
        ProcessingStatus.IMPORTING,
    }
    if workflow is not None and workflow.manual_claimed_at is not None:
        attempt_in_flight = attempt_in_flight or workflow.manual_claimed_by == "user"
    manual_action = "none"
    has_external_job_id = bool(
        job is not None
        and isinstance(job.external_job_id, str)
        and bool(job.external_job_id.strip())
    )
    has_idempotency_key = bool(
        job is not None
        and isinstance(job.idempotency_key, str)
        and bool(job.idempotency_key.strip())
    )
    job_status = getattr(job.status, "value", job.status) if job is not None else None
    same_job_recovery_safe = bool(
        has_external_job_id
        or (
            has_idempotency_key
            and job_status
            not in {"failed", "deleting", "blocked"}
        )
    )
    if (
        state == ProcessingStatus.BLOCKED_UNKNOWN
        and has_idempotency_key
    ) or (
        state in {ProcessingStatus.WAITING_RETRY, ProcessingStatus.FAILED_RETRYABLE}
        and same_job_recovery_safe
    ):
        manual_action = "check_now"
    elif state == ProcessingStatus.FAILED_TERMINAL:
        manual_action = "new_attempt"
    elif state in {ProcessingStatus.BLOCKED, ProcessingStatus.FAILED_RETRYABLE}:
        manual_action = "contact_support"
    summary_state = store.summary_status_from_result(safe_result).value
    return ProcessingStatusResponse(
        meeting_id=meeting.id,
        media_revision_id=media_revision_id,
        workspace_id=meeting.workspace_id,
        state=state,
        reason_code=(
            workflow.last_reason_code
            if workflow is not None and workflow.last_reason_code
            else safe_result.failure_reason
            if safe_result is not None
            else None
        ),
        workflow_id=workflow.workflow_id if workflow is not None else None,
        attempt_ordinal=int(workflow.attempt_ordinal or 1) if workflow is not None else 1,
        mediascribe_job_id_present=bool(job is not None and job.external_job_id),
        content_available=transcript_available,
        transcript_available=transcript_available,
        diarization_available=diarization_available,
        summary_status=summary_state,
        retry_class=retry_class,
        next_attempt_at=workflow.next_attempt_at if workflow is not None else None,
        next_attempt_source=next_attempt_source,
        schedule_generation=int(workflow.schedule_generation or 0) if workflow is not None else 0,
        server_time=datetime.now(UTC),
        manual_action=manual_action,
        attempt_in_flight=attempt_in_flight,
        artifacts={
            "transcript": ProcessingArtifactProjection(
                state="available" if transcript_available else "processing" if safe_result is None else safe_result.transcript_status,
                visible=transcript_available,
            ),
            "diarization": ProcessingArtifactProjection(
                state="available" if diarization_available else "processing" if safe_result is None else safe_result.diarization_status,
                visible=diarization_available,
            ),
            "summary": ProcessingArtifactProjection(state=summary_state, visible=summary_state == "available"),
        },
        updated_at=updated_at,
        archive_audio=workflow.archive_audio if workflow is not None else True,
        transient_state=workflow.transient_state if workflow is not None else "not_applicable",
        transient_purge_due_at=workflow.transient_purge_due_at if workflow is not None else None,
    )
