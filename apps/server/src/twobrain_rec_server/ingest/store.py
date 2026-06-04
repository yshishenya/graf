from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from twobrain_rec_server.config import Settings
from twobrain_rec_server.domain.statuses import (
    MeetingStatus,
    ProcessingStatus,
    TrackRole,
    UploadSessionStatus,
    UploadStrategy,
)


@dataclass(slots=True)
class MeetingRecord:
    id: UUID
    workspace_id: UUID
    organization_id: UUID
    created_by_user_id: UUID
    device_id: UUID
    local_recording_id: str
    duration_seconds: int
    title: str | None
    status: MeetingStatus = MeetingStatus.DRAFT
    processing_status: ProcessingStatus = ProcessingStatus.NOT_SUBMITTED
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


@dataclass(slots=True)
class UploadPartRecord:
    track_role: TrackRole
    part_number: int
    byte_offset: int
    byte_length: int
    sha256: str
    object_key: str
    data: bytes


@dataclass(slots=True)
class UploadSessionRecord:
    id: UUID
    meeting_id: UUID
    workspace_id: UUID
    organization_id: UUID
    device_id: UUID
    created_by_user_id: UUID
    status: UploadSessionStatus
    expires_at: datetime
    upload_strategy: UploadStrategy = UploadStrategy.SERVER_MEDIATED
    processing_status: ProcessingStatus = ProcessingStatus.NOT_SUBMITTED
    parts: dict[tuple[TrackRole, int], UploadPartRecord] = field(default_factory=dict)


@dataclass(slots=True)
class AuditEvent:
    event_type: str
    workspace_id: UUID
    meeting_id: UUID | None
    upload_session_id: UUID | None
    metadata: dict[str, object]
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))


class InMemoryIngestStore:
    def __init__(self) -> None:
        self.meetings: dict[UUID, MeetingRecord] = {}
        self.meetings_by_local_id: dict[tuple[UUID, str], UUID] = {}
        self.sessions: dict[UUID, UploadSessionRecord] = {}
        self.audit_events: list[AuditEvent] = []

    def create_or_get_meeting(
        self,
        *,
        settings: Settings,
        organization_id: UUID,
        workspace_id: UUID,
        user_id: UUID,
        device_id: UUID,
        local_recording_id: str,
        duration_seconds: int,
        title: str | None,
    ) -> MeetingRecord:
        key = (workspace_id, local_recording_id)
        if key in self.meetings_by_local_id:
            return self.meetings[self.meetings_by_local_id[key]]
        if duration_seconds > settings.max_recording_duration_seconds:
            raise ValueError("recording_duration_exceeded")
        meeting = MeetingRecord(
            id=uuid4(),
            workspace_id=workspace_id,
            organization_id=organization_id,
            created_by_user_id=user_id,
            device_id=device_id,
            local_recording_id=local_recording_id,
            duration_seconds=duration_seconds,
            title=title,
        )
        self.meetings[meeting.id] = meeting
        self.meetings_by_local_id[key] = meeting.id
        return meeting

    def create_upload_session(
        self,
        *,
        settings: Settings,
        meeting: MeetingRecord,
    ) -> UploadSessionRecord:
        session = UploadSessionRecord(
            id=uuid4(),
            meeting_id=meeting.id,
            workspace_id=meeting.workspace_id,
            organization_id=meeting.organization_id,
            device_id=meeting.device_id,
            created_by_user_id=meeting.created_by_user_id,
            status=UploadSessionStatus.PENDING,
            expires_at=datetime.now(UTC) + timedelta(seconds=settings.upload_session_ttl_seconds),
        )
        meeting.status = MeetingStatus.UPLOADING
        self.sessions[session.id] = session
        return session


store = InMemoryIngestStore()
