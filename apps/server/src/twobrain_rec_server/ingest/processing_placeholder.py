from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from twobrain_rec_server.db.models import (
    MediaScribeJob,
    Meeting,
    ProcessingPlaceholder,
    ProcessingWorkflow,
)
from twobrain_rec_server.domain.statuses import MeetingStatus, ProcessingStatus
from twobrain_rec_server.ingest import store as store_module


@dataclass(frozen=True, slots=True)
class ProcessingPlaceholderView:
    meeting_id: UUID
    workspace_id: UUID
    processing_status: ProcessingStatus
    meeting_status: MeetingStatus
    workflow_id: str | None = None
    mediascribe_job_id: str | None = None


def get_processing_placeholder(meeting_id: UUID) -> ProcessingPlaceholderView | None:
    meeting = store_module.store.meetings.get(meeting_id)
    if meeting is None:
        return None
    return ProcessingPlaceholderView(
        meeting_id=meeting.id,
        workspace_id=meeting.workspace_id,
        processing_status=meeting.processing_status,
        meeting_status=meeting.status,
    )


async def load_processing_placeholder(
    db: AsyncSession | None,
    meeting_id: UUID,
) -> ProcessingPlaceholderView | None:
    if db is None:
        return get_processing_placeholder(meeting_id)
    workflow = await db.scalar(select(ProcessingWorkflow).where(ProcessingWorkflow.meeting_id == meeting_id))
    if workflow is not None:
        job = await db.scalar(select(MediaScribeJob).where(MediaScribeJob.meeting_id == meeting_id))
        meeting = await db.get(Meeting, meeting_id)
        return ProcessingPlaceholderView(
            meeting_id=workflow.meeting_id,
            workspace_id=workflow.workspace_id,
            processing_status=ProcessingStatus(workflow.status),
            meeting_status=MeetingStatus(meeting.status) if meeting is not None else MeetingStatus.INGESTED_PENDING_PROCESSING,
            workflow_id=workflow.workflow_id,
            mediascribe_job_id=job.external_job_id if job is not None else None,
        )
    placeholder = await db.scalar(select(ProcessingPlaceholder).where(ProcessingPlaceholder.meeting_id == meeting_id))
    if placeholder is None:
        return get_processing_placeholder(meeting_id)
    return ProcessingPlaceholderView(
        meeting_id=placeholder.meeting_id,
        workspace_id=placeholder.workspace_id,
        processing_status=ProcessingStatus(placeholder.status),
        meeting_status=MeetingStatus(placeholder.meeting_status),
    )
