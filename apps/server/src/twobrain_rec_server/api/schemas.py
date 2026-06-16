from datetime import datetime
from typing import Annotated, Literal
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


MeetingReviewStatus = Literal[
    "local_only",
    "uploading",
    "submitted",
    "processing",
    "ready",
    "partial",
    "blocked",
    "failed",
    "unavailable",
    "deleted_future",
]
MeetingSource = Literal["desktop_recording", "manual_upload", "unknown"]
PrimaryAction = Literal["open", "wait", "retry_future", "open_status", "unavailable"]
SourceRoleView = Literal["local_microphone", "incoming_system", "unknown"]
GovernanceState = Literal["available", "disabled", "planned", "policy_blocked", "browser_handoff", "out_of_scope"]
SlotStateValue = Literal["available", "disabled", "planned", "policy_blocked", "out_of_scope"]
NextAction = Literal["wait", "retry_future", "contact_operator", "open_desktop_queue", "none"]
AccessState = Literal["owner", "team", "shared", "denied", "unavailable", "deleted"]
ArtifactClass = Literal["audio", "transcript", "summary", "package"]
ArtifactEgressStateValue = Literal[
    "available",
    "policy_blocked",
    "missing",
    "processing",
    "failed",
    "deleted",
    "owner_only",
    "audit_unavailable",
]
ArtifactAction = Literal["download", "export", "disabled"]
TeamVisibilityState = Literal["enabled", "disabled", "policy_blocked"]
CopyLinkState = Literal["available", "auth_required", "disabled"]
PublicLinkState = Literal["disabled_by_default", "policy_blocked"]
ShareGrantStatus = Literal["active", "revoked"]
ActivityOutcome = Literal["allowed", "denied", "completed", "failed"]
ExportPackageStatus = Literal["requested", "ready", "failed", "expired"]


class MeetingAccessState(BaseModel):
    state: AccessState
    label: str
    reason: str | None = None
    can_view: bool
    can_share: bool
    can_manage_team_visibility: bool
    can_download: bool
    can_export: bool


class ArtifactEgressState(BaseModel):
    artifact_class: ArtifactClass
    state: ArtifactEgressStateValue
    label: str
    reason: str | None = None
    action: ArtifactAction


class ShareGrantView(BaseModel):
    grant_id: UUID
    display_name: str
    role_label: Literal["Owner", "Team", "Can view"]
    status: ShareGrantStatus
    created_at: datetime


class SharePanelState(BaseModel):
    team_visibility: TeamVisibilityState
    active_grants: list[ShareGrantView] = Field(default_factory=list)
    copy_link_state: CopyLinkState
    public_link_state: PublicLinkState


class MeetingActivityItem(BaseModel):
    event_id: UUID
    event_type: str
    actor_label: str
    artifact_class: ArtifactClass | None = None
    outcome: ActivityOutcome
    reason: str | None = None
    created_at: datetime


class MeetingActivityResponse(BaseModel):
    meeting_id: UUID
    redaction_state: Literal["metadata_only", "limited_by_policy"] = "metadata_only"
    items: list[MeetingActivityItem] = Field(default_factory=list)


class MeetingAccessResponse(BaseModel):
    meeting_id: UUID
    access: MeetingAccessState
    share: SharePanelState
    artifacts: list[ArtifactEgressState] = Field(default_factory=list)
    deletion_truth_copy: str


class CreateShareGrantRequest(BaseModel):
    grantee_user_id: UUID


class ShareGrantResponse(BaseModel):
    grant: ShareGrantView
    share_url: str


class CreateExportPackageRequest(BaseModel):
    artifact_classes: list[ArtifactClass] = Field(min_length=1)


class ExportPackageExclusion(BaseModel):
    artifact_class: ArtifactClass
    policy_reason: str


class ExportPackageResponse(BaseModel):
    export_id: UUID
    status: ExportPackageStatus
    included_artifacts: list[ArtifactClass] = Field(default_factory=list)
    excluded_artifacts: list[ExportPackageExclusion] = Field(default_factory=list)


class GovernanceActionState(BaseModel):
    state: GovernanceState
    label: str
    reason: str | None = None
    destructive: bool = False


class GovernanceActionSummary(BaseModel):
    share: GovernanceActionState
    export: GovernanceActionState
    download: GovernanceActionState
    retention: GovernanceActionState
    delete: GovernanceActionState


class SlotState(BaseModel):
    state: SlotStateValue
    label: str
    reason: str | None = None


class MeetingFilterState(BaseModel):
    q: str | None = None
    status: MeetingReviewStatus | None = None
    access: AccessState | None = None
    sort: str = "updated_desc"


class MeetingListItem(BaseModel):
    meeting_id: UUID
    title: str
    started_at: datetime | None = None
    ended_at: datetime | None = None
    duration_seconds: int = Field(ge=0)
    source: MeetingSource = "desktop_recording"
    status: MeetingReviewStatus
    status_label: str
    status_reason: str | None = None
    primary_action: PrimaryAction
    transcript_available: bool = False
    diarization_available: bool = False
    notes_available: bool = False
    updated_at: datetime | None = None
    access: MeetingAccessState | None = None
    artifacts: list[ArtifactEgressState] = Field(default_factory=list)
    governance: GovernanceActionSummary
    future_slots: list[SlotState] = Field(default_factory=list)


class MeetingListResponse(BaseModel):
    items: list[MeetingListItem]
    filters: MeetingFilterState
    generated_at: datetime


class MeetingProvenance(BaseModel):
    source_roles: list[SourceRoleView] = Field(default_factory=list)
    processing_dependency: str | None = None
    content_policy: str = "authorized_detail_only"


class ProcessingReviewState(BaseModel):
    state: MeetingReviewStatus
    stage: str | None = None
    reason_code: str | None = None
    reason_label: str | None = None
    content_available: bool = False
    transcript_available: bool = False
    diarization_available: bool = False
    summary_available: bool = False
    updated_at: datetime | None = None
    next_action: NextAction = "none"


class TranscriptSegmentView(BaseModel):
    segment_id: str
    sequence: int
    start_seconds: float
    end_seconds: float
    timestamp_label: str
    speaker_label: str
    source_role: SourceRoleView
    text: str
    confidence_label: str | None = None


class TranscriptReviewState(BaseModel):
    available: bool
    language: str | None = None
    degraded_reason: str | None = None
    search_enabled: bool = False
    segments: list[TranscriptSegmentView] = Field(default_factory=list)


class SpeakerLaneSegment(BaseModel):
    start_seconds: float
    end_seconds: float


class SpeakerLane(BaseModel):
    speaker_key: str
    label: str
    talk_time_percent: int = Field(ge=0, le=100)
    source_roles: list[SourceRoleView] = Field(default_factory=list)
    segments: list[SpeakerLaneSegment] = Field(default_factory=list)
    confidence_label: str | None = None


class SpeakerReviewState(BaseModel):
    available: bool
    assignment_state: Literal["available", "reserved", "disabled", "conflict_future", "unavailable"]
    degraded_reason: str | None = None
    speakers: list[SpeakerLane] = Field(default_factory=list)


class NotesReviewState(BaseModel):
    available: bool
    sections: list[dict] = Field(default_factory=list)
    unavailable_reason: Literal[
        "none",
        "not_requested",
        "processing",
        "generation_future",
        "partial_transcript",
        "policy_blocked",
    ]


class PlaybackReviewState(BaseModel):
    available: bool = False
    duration_seconds: int = Field(default=0, ge=0)
    speed_options: list[float] = Field(default_factory=lambda: [0.75, 1.0, 1.25, 1.5, 2.0])


class MeetingReviewResponse(BaseModel):
    meeting: MeetingListItem
    provenance: MeetingProvenance
    processing: ProcessingReviewState
    transcript: TranscriptReviewState
    speakers: SpeakerReviewState
    notes: NotesReviewState
    playback: PlaybackReviewState
    governance: GovernanceActionSummary
    access: MeetingAccessState | None = None
    share: SharePanelState | None = None
    artifacts: list[ArtifactEgressState] = Field(default_factory=list)
    activity: MeetingActivityResponse | None = None
    deletion_truth_copy: str | None = None
    assistant: SlotState
    template: SlotState
