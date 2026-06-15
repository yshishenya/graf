from __future__ import annotations

from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from twobrain_rec_server.api.schemas import ProcessingStatusResponse
from twobrain_rec_server.domain.statuses import ProcessingAvailabilityStatus, ProcessingStatus
from twobrain_rec_server.processing import store


async def get_content_safe_processing_status(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    meeting_id: UUID,
) -> ProcessingStatusResponse | None:
    meeting = await store.load_meeting_for_workspace(db, workspace_id=workspace_id, meeting_id=meeting_id)
    if meeting is None:
        return None
    workflow = await store.get_processing_workflow(db, workspace_id=workspace_id, meeting_id=meeting_id)
    job = await store.get_mediascribe_job(db, workspace_id=workspace_id, meeting_id=meeting_id)
    result = await store.latest_processing_result(db, workspace_id=workspace_id, meeting_id=meeting_id)
    state = ProcessingStatus(workflow.status) if workflow is not None else ProcessingStatus(meeting.processing_status)
    transcript_available = (
        result is not None and result.transcript_status == ProcessingAvailabilityStatus.AVAILABLE.value
    )
    diarization_available = (
        result is not None and result.diarization_status == ProcessingAvailabilityStatus.AVAILABLE.value
    )
    updated_at = None
    if workflow is not None:
        updated_at = workflow.updated_at
    elif result is not None:
        updated_at = result.updated_at
    return ProcessingStatusResponse(
        meeting_id=meeting.id,
        workspace_id=meeting.workspace_id,
        state=state,
        reason_code=workflow.last_reason_code if workflow is not None else None,
        workflow_id=workflow.workflow_id if workflow is not None else None,
        mediascribe_job_id_present=bool(job is not None and job.external_job_id),
        content_available=transcript_available or diarization_available,
        transcript_available=transcript_available,
        diarization_available=diarization_available,
        summary_status=store.summary_status_from_result(result).value,
        updated_at=updated_at,
    )
