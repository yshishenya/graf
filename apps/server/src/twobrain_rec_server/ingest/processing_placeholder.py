from dataclasses import dataclass
from uuid import UUID

from twobrain_rec_server.domain.statuses import ProcessingStatus
from twobrain_rec_server.ingest.store import store


@dataclass(frozen=True, slots=True)
class ProcessingPlaceholderView:
    meeting_id: UUID
    workspace_id: UUID
    processing_status: ProcessingStatus
    workflow_id: None = None
    mediascribe_job_id: None = None


def get_processing_placeholder(meeting_id: UUID) -> ProcessingPlaceholderView | None:
    meeting = store.meetings.get(meeting_id)
    if meeting is None:
        return None
    return ProcessingPlaceholderView(
        meeting_id=meeting.id,
        workspace_id=meeting.workspace_id,
        processing_status=meeting.processing_status,
    )
