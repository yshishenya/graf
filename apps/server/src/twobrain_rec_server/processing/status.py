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
    )
    result = await store.latest_processing_result(
        db,
        workspace_id=workspace_id,
        meeting_id=meeting_id,
        media_revision_id=media_revision_id,
    )
    state = ProcessingStatus(workflow.status) if workflow is not None else ProcessingStatus(meeting.processing_status)
    transcript_available = (
        result is not None
        and result.transcript_status == ProcessingAvailabilityStatus.AVAILABLE.value
        and result.segment_count > 0
    )
    diarization_available = (
        result is not None
        and result.diarization_status == ProcessingAvailabilityStatus.AVAILABLE.value
        and result.diarization_segment_count > 0
    )
    updated_at = None
    if workflow is not None:
        updated_at = workflow.updated_at
    elif result is not None:
        updated_at = result.updated_at
    return ProcessingStatusResponse(
        meeting_id=meeting.id,
        media_revision_id=result.media_revision_id
        if result is not None and result.media_revision_id is not None
        else job.media_revision_id
        if job is not None and job.media_revision_id is not None
        else workflow.media_revision_id
        if workflow is not None and workflow.media_revision_id is not None
        else media_revision_id,
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
        archive_audio=workflow.archive_audio if workflow is not None else True,
        transient_state=workflow.transient_state if workflow is not None else "not_applicable",
        transient_purge_due_at=workflow.transient_purge_due_at if workflow is not None else None,
    )
