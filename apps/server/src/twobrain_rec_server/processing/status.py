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
from twobrain_rec_server.processing.reasons import (
    BLOCKED_CONFIG,
    BLOCKED_FREE_PROCESSING_EXHAUSTED,
    BLOCKED_UNAUTHORIZED,
    FAILURE_SOURCE_INPUT_AUDIO,
    INVALID_AUDIO_PAYLOAD,
    MEDIASCRIBE_AUTH_FAILED,
    NO_RECOGNIZABLE_SPEECH,
)
from twobrain_rec_server.processing.results import result_is_complete, result_lineage_is_current


async def get_content_safe_processing_status(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    meeting_id: UUID,
) -> ProcessingStatusResponse | None:
    server_time = datetime.now(UTC)
    meeting = await store.load_meeting_for_workspace(
        db, workspace_id=workspace_id, meeting_id=meeting_id
    )
    if meeting is None:
        return None
    media_revision = await store.latest_media_revision_for_meeting(
        db, workspace_id=workspace_id, meeting_id=meeting_id
    )
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
        state = (
            ProcessingStatus(workflow.status)
            if workflow is not None
            else ProcessingStatus(meeting.processing_status)
        )
    except ValueError:
        state = ProcessingStatus.BLOCKED
    same_result_lineage = result_lineage_is_current(
        result,
        media_revision_id=media_revision_id,
    )
    safe_result = (
        result
        if same_result_lineage
        and workflow is not None
        and result.processing_workflow_id == workflow.id
        else None
    )
    preparation = await store.load_manual_upload_preparation(
        db,
        workspace_id=workspace_id,
        meeting_id=meeting_id,
        media_revision_id=media_revision_id,
        revision=media_revision,
    )
    result_terminal_input = bool(
        safe_result is not None
        and safe_result.status == ProcessingResultStatus.IMPORTED.value
        and (
            safe_result.failure_reason == NO_RECOGNIZABLE_SPEECH
            or (
                safe_result.failure_reason == INVALID_AUDIO_PAYLOAD
                and safe_result.failure_source == FAILURE_SOURCE_INPUT_AUDIO
            )
        )
        and workflow is not None
        and safe_result.processing_workflow_id == workflow.id
    )
    result_requires_new_upload = bool(
        result_terminal_input
        and safe_result is not None
        and safe_result.failure_reason == INVALID_AUDIO_PAYLOAD
        and safe_result.failure_source == FAILURE_SOURCE_INPUT_AUDIO
    )
    current_workflow_imported_result = bool(
        safe_result is not None
        and safe_result.status == ProcessingResultStatus.IMPORTED.value
        and workflow is not None
        and safe_result.processing_workflow_id == workflow.id
        and not result_terminal_input
    )
    current_workflow_complete_result = bool(
        current_workflow_imported_result and result_is_complete(safe_result)
    )
    current_workflow_incomplete_result = bool(
        current_workflow_imported_result and not current_workflow_complete_result
    )
    if current_workflow_complete_result:
        # Result persistence deliberately precedes the final workflow status.
        # A crash in that narrow window must not hide an imported result behind
        # a stale importing/canceled projection.
        state = ProcessingStatus.PROCESSED
        preparation = None
    elif current_workflow_incomplete_result and state in {
        ProcessingStatus.PROCESSED,
        ProcessingStatus.BLOCKED,
        ProcessingStatus.FAILED_TERMINAL,
        ProcessingStatus.CANCELED,
    }:
        # Provider-ready data without the requested diarization is a final,
        # unusable transcript milestone. Keep stored artifacts hidden and give
        # the user a real recovery path instead of polling a closed workflow.
        state = ProcessingStatus.FAILED_TERMINAL
        preparation = None
    elif state == ProcessingStatus.PROCESSED and not result_terminal_input:
        # Audio cleanup after a successful no-archive run must not replace the
        # durable processing result with the normalization job's cancelled state.
        preparation = None
    if result_terminal_input or preparation is not None and preparation.state == "terminal":
        state = ProcessingStatus.FAILED_TERMINAL
    elif preparation is not None and preparation.state == "cancelled":
        state = ProcessingStatus.CANCELED
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
    reason_code = (
        safe_result.failure_reason
        if current_workflow_imported_result and safe_result is not None
        else preparation.reason_code
        if preparation is not None and preparation.state != "ready"
        else workflow.last_reason_code
        if workflow is not None and workflow.last_reason_code
        else safe_result.failure_reason
        if safe_result is not None
        else None
    )
    if result_terminal_input or (
        preparation is not None and preparation.state in {"terminal", "cancelled"}
    ):
        retry_class = "terminal"
    elif preparation is not None and preparation.state == "pending":
        retry_class = (
            "retryable" if preparation.reason_code == "normalization_retry_wait" else "none"
        )
    elif state == ProcessingStatus.PROCESSED:
        # A processed workflow may retain a historical retry class. It is no
        # longer recoverable work once the current lifecycle is complete.
        retry_class = "none"
    elif state == ProcessingStatus.FAILED_TERMINAL or (
        state == ProcessingStatus.BLOCKED and reason_code == BLOCKED_FREE_PROCESSING_EXHAUSTED
    ):
        retry_class = "terminal"
    else:
        retry_class = (
            workflow.retry_class
            if workflow is not None
            and workflow.retry_class in {"retryable", "unknown_outcome", "terminal", "none"}
            else (
                "retryable"
                if state in {ProcessingStatus.FAILED_RETRYABLE, ProcessingStatus.WAITING_RETRY}
                else "unknown_outcome"
                if state == ProcessingStatus.BLOCKED_UNKNOWN
                else "terminal"
                if state == ProcessingStatus.FAILED_TERMINAL
                else "none"
            )
        )
    next_attempt_source = (
        workflow.next_attempt_source
        if workflow is not None
        and workflow.next_attempt_source
        in {"provider_retry_after", "provider_next_retry_at", "server_fallback", "manual_override"}
        else None
    )
    attempt_in_flight = state in {
        ProcessingStatus.STARTING,
        ProcessingStatus.WORKFLOW_STARTED,
        ProcessingStatus.SUBMITTING,
        ProcessingStatus.SUBMITTED,
        ProcessingStatus.POLLING,
        ProcessingStatus.IMPORTING,
    }
    if preparation is not None and preparation.state == "pending":
        attempt_in_flight = preparation.reason_code != "normalization_retry_wait"
    manual_claim_expired = False
    if workflow is not None and workflow.manual_claimed_at is not None:
        claimed_at = workflow.manual_claimed_at
        if claimed_at.tzinfo is None:
            claimed_at = claimed_at.replace(tzinfo=UTC)
        manual_claim_expired = (
            workflow.manual_claimed_by == "user"
            and server_time - claimed_at >= store.PROCESSING_MANUAL_CHECK_CLAIM_LEASE
        )
        if manual_claim_expired and workflow.last_reason_code == "manual_processing_check":
            attempt_in_flight = False
        elif workflow.manual_claimed_by == "user":
            attempt_in_flight = True
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
        or (has_idempotency_key and job_status not in {"failed", "deleting", "blocked"})
    )
    if (
        result_requires_new_upload
        or (preparation is not None and preparation.state in {"terminal", "cancelled"})
        or (state == ProcessingStatus.CANCELED and reason_code == "audio_purged")
    ):
        manual_action = "upload_another"
    elif preparation is not None and preparation.reason_code == "normalization_retry_wait":
        manual_action = "retry_preparation"
    elif (
        (manual_claim_expired and same_job_recovery_safe)
        or (state == ProcessingStatus.BLOCKED_UNKNOWN and has_idempotency_key)
        or (
            state in {ProcessingStatus.WAITING_RETRY, ProcessingStatus.FAILED_RETRYABLE}
            and same_job_recovery_safe
        )
    ):
        manual_action = "check_now"
    elif (
        state in {ProcessingStatus.BLOCKED, ProcessingStatus.FAILED_TERMINAL}
        and reason_code == BLOCKED_FREE_PROCESSING_EXHAUSTED
    ):
        manual_action = "new_attempt"
    elif state == ProcessingStatus.FAILED_TERMINAL and reason_code in {
        BLOCKED_CONFIG,
        BLOCKED_UNAUTHORIZED,
        MEDIASCRIBE_AUTH_FAILED,
    }:
        manual_action = "contact_support"
    elif state == ProcessingStatus.FAILED_TERMINAL:
        manual_action = "new_attempt"
    elif state in {ProcessingStatus.BLOCKED, ProcessingStatus.FAILED_RETRYABLE}:
        manual_action = "contact_support"
    summary_state = store.summary_status_from_result(safe_result).value
    terminal_without_usable_transcript = (
        state
        in {
            ProcessingStatus.BLOCKED,
            ProcessingStatus.FAILED_TERMINAL,
            ProcessingStatus.CANCELED,
        }
        and not transcript_available
    )
    transcript_artifact_state = (
        "unavailable"
        if terminal_without_usable_transcript
        else "available"
        if transcript_available
        else "processing"
        if safe_result is None
        else safe_result.transcript_status
    )
    diarization_artifact_state = (
        "unavailable"
        if terminal_without_usable_transcript
        else "available"
        if diarization_available
        else "processing"
        if safe_result is None
        else safe_result.diarization_status
    )
    return ProcessingStatusResponse(
        meeting_id=meeting.id,
        media_revision_id=media_revision_id,
        workspace_id=meeting.workspace_id,
        state=state,
        reason_code=reason_code,
        workflow_id=workflow.workflow_id if workflow is not None else None,
        attempt_ordinal=int(workflow.attempt_ordinal or 1) if workflow is not None else 1,
        mediascribe_job_id_present=bool(job is not None and job.external_job_id),
        content_available=transcript_available,
        transcript_available=transcript_available,
        diarization_available=diarization_available,
        summary_status=summary_state,
        retry_class=retry_class,
        next_attempt_at=(
            preparation.next_attempt_at
            if preparation is not None and preparation.state == "pending"
            else workflow.next_attempt_at
            if workflow is not None
            else None
        ),
        next_attempt_source=(
            "server_fallback"
            if preparation is not None
            and preparation.state == "pending"
            and preparation.next_attempt_at is not None
            else next_attempt_source
        ),
        schedule_generation=int(workflow.schedule_generation or 0) if workflow is not None else 0,
        server_time=server_time,
        manual_action=manual_action,
        attempt_in_flight=attempt_in_flight,
        artifacts={
            "transcript": ProcessingArtifactProjection(
                state=transcript_artifact_state,
                visible=transcript_available,
            ),
            "diarization": ProcessingArtifactProjection(
                state=diarization_artifact_state,
                visible=diarization_available,
            ),
            "summary": ProcessingArtifactProjection(
                state=summary_state, visible=summary_state == "available"
            ),
        },
        updated_at=updated_at,
        archive_audio=workflow.archive_audio if workflow is not None else True,
        transient_state=workflow.transient_state if workflow is not None else "not_applicable",
        transient_purge_due_at=workflow.transient_purge_due_at if workflow is not None else None,
    )
