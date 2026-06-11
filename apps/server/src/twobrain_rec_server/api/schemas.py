from datetime import datetime
from typing import Annotated
from uuid import UUID

from pydantic import BaseModel, Field, StringConstraints

from twobrain_rec_server.domain.statuses import (
    MeetingStatus,
    ProcessingStatus,
    TrackRole,
    UploadSessionStatus,
    UploadStrategy,
)


class HealthResponse(BaseModel):
    status: str = "ok"


class ReadyResponse(BaseModel):
    status: str


class ReadyDetailResponse(BaseModel):
    status: str
    checks: dict[str, str]


class Problem(BaseModel):
    type: str = "about:blank"
    title: str
    status: int
    code: str
    detail: str | None = None
    request_id: str | None = None


class TrackDescriptor(BaseModel):
    track_role: TrackRole
    codec: str
    sample_rate_hz: int = Field(gt=0)
    channel_count: int = Field(gt=0)
    duration_seconds: int = Field(gt=0)
    byte_length: int = Field(ge=0)
    sha256: str = Field(pattern=r"^[a-f0-9]{64}$")


SafeClientText = Annotated[str, StringConstraints(strip_whitespace=True, pattern=r"^[^\x00-\x1f\x7f]+$")]


class CreateMeetingRequest(BaseModel):
    local_recording_id: Annotated[SafeClientText, Field(min_length=1, max_length=240)]
    title: Annotated[SafeClientText, Field(max_length=500)] | None = None
    started_at: datetime | None = None
    ended_at: datetime | None = None
    duration_seconds: int = Field(gt=0)


class MeetingResponse(BaseModel):
    meeting_id: UUID
    workspace_id: UUID
    local_recording_id: str
    status: MeetingStatus
    processing_status: ProcessingStatus
    started_at: datetime | None = None
    ended_at: datetime | None = None
    created_at: datetime | None = None


class CreateUploadSessionRequest(BaseModel):
    expected_tracks: list[TrackRole] = Field(default_factory=lambda: [TrackRole.MANIFEST, TrackRole.MICROPHONE, TrackRole.SYSTEM])
    expected_track_sizes: dict[TrackRole, int] = Field(default_factory=dict)
    manifest_sha256: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")


class UploadSessionResponse(BaseModel):
    session_id: UUID
    meeting_id: UUID
    status: UploadSessionStatus
    upload_strategy: UploadStrategy = UploadStrategy.SERVER_MEDIATED
    expires_at: datetime
    accepted_bytes_by_track: dict[str, int] = Field(default_factory=dict)
    processing_status: ProcessingStatus = ProcessingStatus.NOT_SUBMITTED
    workflow_id: None = None
    mediascribe_job_id: None = None
    desktop_label: str | None = None
    desktop_truth_rule: str | None = None


class UploadPartResponse(BaseModel):
    session_id: UUID
    track_role: TrackRole
    part_number: int = Field(ge=0)
    byte_offset: int = Field(ge=0)
    byte_length: int = Field(ge=0)
    sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    status: str = "accepted"


class MissingRange(BaseModel):
    start: int = Field(ge=0)
    end: int = Field(ge=0)


class MissingRangesResponse(BaseModel):
    session_id: UUID
    missing_ranges_by_track: dict[TrackRole, list[MissingRange]]


class FinalizeUploadRequest(BaseModel):
    manifest_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    tracks: list[TrackDescriptor] = Field(min_length=3)


class FinalizeUploadResponse(BaseModel):
    meeting: MeetingResponse
    upload_session: UploadSessionResponse
    object_count: int = Field(ge=0)
    workflow_started: bool = False
    mediascribe_job_created: bool = False


class AbortUploadRequest(BaseModel):
    reason: Annotated[SafeClientText, Field(max_length=240)] | None = None


class ProcessingPickupRequest(BaseModel):
    meeting_id: UUID | None = None
    limit: int = Field(default=25, ge=1, le=100)


class ProcessingPickupResponse(BaseModel):
    accepted: bool
    started_count: int = Field(ge=0)
    reused_count: int = Field(ge=0)
    blocked_count: int = Field(ge=0)
    meeting_ids: list[UUID] = Field(default_factory=list)


class ProcessingStatusResponse(BaseModel):
    meeting_id: UUID
    workspace_id: UUID
    state: ProcessingStatus
    reason_code: str | None = None
    workflow_id: str | None = None
    mediascribe_job_id_present: bool = False
    content_available: bool = False
    transcript_available: bool = False
    diarization_available: bool = False
    summary_status: str = "not_requested"
    updated_at: datetime | None = None
