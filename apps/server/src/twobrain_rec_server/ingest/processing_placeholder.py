from dataclasses import dataclass
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from twobrain_rec_server.db.models import ProcessingPlaceholder
from twobrain_rec_server.domain.statuses import MeetingStatus, ProcessingStatus
from twobrain_rec_server.ingest import store as store_module


@dataclass(frozen=True, slots=True)
class ProcessingPlaceholderView:
    meeting_id: UUID
    workspace_id: UUID
    processing_status: ProcessingStatus
    meeting_status: MeetingStatus
    workflow_id: None = None
    mediascribe_job_id: None = None


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
    placeholder = await db.scalar(select(ProcessingPlaceholder).where(ProcessingPlaceholder.meeting_id == meeting_id))
    if placeholder is None:
        return get_processing_placeholder(meeting_id)
    return ProcessingPlaceholderView(
        meeting_id=placeholder.meeting_id,
        workspace_id=placeholder.workspace_id,
        processing_status=ProcessingStatus(placeholder.status),
        meeting_status=MeetingStatus(placeholder.meeting_status),
    )
