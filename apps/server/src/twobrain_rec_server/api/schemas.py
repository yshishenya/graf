from datetime import datetime
from typing import Annotated, Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, StringConstraints

from twobrain_rec_server.domain.statuses import (
    CustodyMetadataSafety,
    CustodyNormalUserAction,
    CustodyOwner,
    CustodyProcessingState,
    CustodyRetryClass,
    CustodyState,
    CustodyUploadState,
    DeletionArtifactState,
    DeletionControlScope,
    DeletionReasonCode,
    DeletionState,
    LocalPurgeTaskState,
    LocalPurgeTaskType,
    MediaRevisionSourceKind,
    MediaRevisionStatus,
    MeetingStatus,
    ProcessingStatus,
    SyncConflictState,
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


class ProblemCustodyExtension(BaseModel):
    owner: CustodyOwner
    retry_class: CustodyRetryClass
    normal_user_action: CustodyNormalUserAction
    metadata_safety: CustodyMetadataSafety = CustodyMetadataSafety.METADATA_ONLY


class Problem(BaseModel):
    type: str = "about:blank"
    title: str
    status: int
    code: str
    detail: str | None = None
    request_id: str | None = None
    custody_owner: CustodyOwner | None = None
    retry_class: CustodyRetryClass | None = None
    normal_user_action: CustodyNormalUserAction | None = None
    metadata_safety: CustodyMetadataSafety | None = None
    custody: ProblemCustodyExtension | None = None


SafeClientText = Annotated[str, StringConstraints(strip_whitespace=True, pattern=r"^[^\x00-\x1f\x7f]+$")]


class SupportIncidentReportRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    schema_version: str
    redaction_state: Literal["metadata_only"]
    range_mismatch_metadata: dict[str, Any] = Field(default_factory=dict)
    local_file_completeness_profile: dict[str, Any] = Field(default_factory=dict)
    local_purge_tasks: list[Any] = Field(default_factory=list)


class SupportIncidentResponse(BaseModel):
    incident_id: Annotated[str, Field(pattern=r"^CUST-[1-9][0-9]*$")]
    incident_status: Literal["created", "updated"]
    github_issue_number: int = Field(gt=0)
    github_issue_url: str
    dedupe_status: Literal["created", "updated"]
    affected_count: int = Field(ge=1)
    copy_fallback_available: bool = True
    user_message: str


class CalendarProviderPreset(BaseModel):
    provider_family: str
    label: str
    adapter_family: Literal["caldav", "rich_api", "ews"]
    supported: bool
    capability_state: dict[str, str] = Field(default_factory=dict)


class CalendarProviderListResponse(BaseModel):
    providers: list[CalendarProviderPreset] = Field(default_factory=list)


class ConnectCalendarSourceRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    provider_family: str
    auth_mode: Literal["app_password", "manual_url"]
    display_label: str | None = Field(default=None, max_length=160)
    caldav_url: str | None = Field(default=None, max_length=1000)
    username: str | None = Field(default=None, max_length=240)
    credential_input: str | None = None
    selected_provider_calendar_ids: list[str] = Field(default_factory=list)


class SelectCalendarsRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    selected_provider_calendar_ids: list[str] = Field(default_factory=list)


class CalendarSourceSummary(BaseModel):
    source_id: UUID | None = None
    provider_family: str | None = None
    provider_label: str | None = None
    connection_state: str | None = None
    credential_state: str | None = None
    sync_state: str | None = None
    selected_calendar_count: int = 0
    sync_horizon_end: datetime | None = None
    last_successful_sync_at: datetime | None = None
    safe_error_code: str | None = None


class ExternalCalendarSummary(BaseModel):
    calendar_id: str
    display_label: str
    selected: bool
    color: str | None = None
    visibility: str = "available"


class CalendarSourceListResponse(BaseModel):
    sources: list[CalendarSourceSummary] = Field(default_factory=list)


class CalendarSourceResponse(BaseModel):
    source: CalendarSourceSummary
    calendars: list[ExternalCalendarSummary] = Field(default_factory=list)


class CalendarSyncResponse(BaseModel):
    source_id: UUID
    sync_state: str
    accepted: bool
    event_count: int = 0
    safe_error_code: str | None = None


class CalendarDisconnectResponse(BaseModel):
    source_id: UUID
    connection_state: Literal["disconnected"]
    credentials_purged: bool
    unmatched_future_cache_purged: bool
    matched_context_retention: Literal["meeting_retention_policy"] = "meeting_retention_policy"


class CalendarEventSummary(BaseModel):
    event_id: UUID
    provider_family: str
    starts_at: datetime
    ends_at: datetime
    title: str | None = None
    title_state: Literal["available", "private_redacted", "free_busy_only", "policy_hidden"]
    meeting_link_present: bool = False
    attendee_count: int = 0
    roster_state: str = "not_available"
    recipient_candidate_count: int = 0
    privacy_class: str = "unknown"


class UpcomingCalendarEventsResponse(BaseModel):
    events: list[CalendarEventSummary] = Field(default_factory=list)
    truncated: bool = False


class DesktopCalendarPromptEvent(CalendarEventSummary):
    join_prompt_due_at: datetime | None = None
    record_prompt_due_at: datetime | None = None
    join_prompt_state: str
    record_prompt_state: str
    open_meeting_url: str | None = None


class DesktopCalendarPromptResponse(BaseModel):
    events: list[DesktopCalendarPromptEvent] = Field(default_factory=list)


MeetingDetectionMode = Literal["detect_only", "detect_and_ask"]
MeetingDetectionUploadMode = Literal[
    "local_only",
    "manual_export",
    "workspace_opt_in",
    "dogfood_opt_in",
    "automatic_candidate_upload",
]
MeetingDetectionSupportMode = Literal[
    "prompt_enabled",
    "diagnostic_only",
    "blocked_missing_bundle",
    "manual_or_browser_only",
    "disabled",
]
MeetingDetectionTargetFamily = Literal[
    "native_app",
    "browser_meeting",
    "provider",
    "manual_only",
    "unknown",
]
MeetingDetectionSignalFamily = Literal[
    "macos_audio_hal_assertion",
    "browser_metadata",
    "calendar_overlap",
    "join_intent",
    "system_audio_activity",
    "manual_record_nearby",
    "adapter_health",
]
MeetingDetectionCandidateReason = Literal[
    "stable_mic_duration",
    "repeated_observation",
    "manual_record_nearby",
    "calendar_or_join_hint",
    "vks_name_token",
    "known_vks_vendor",
    "known_registry_neighbor",
    "long_duration_bucket",
]
MeetingDetectionCandidateSuppression = Literal[
    "low_score",
    "short_duration",
    "browser_bundle",
    "audio_utility",
    "system_service",
    "media_player",
    "audio_editor",
    "game",
    "screen_recorder",
    "known_non_target",
    "workspace_upload_disabled",
]


class MeetingTargetBrowserServicePattern(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    service_family: Annotated[SafeClientText, Field(alias="serviceFamily", max_length=80)]
    host_category: Literal["first_party", "enterprise_domain", "unknown"] = Field(alias="hostCategory")
    pattern_class: Literal["meeting_room", "join_intent", "landing", "settings", "unsupported"] = Field(
        alias="patternClass",
    )


class MeetingTargetRegistryTarget(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    id: Annotated[SafeClientText, Field(min_length=3, max_length=80, pattern=r"^[a-z0-9][a-z0-9_-]{2,80}$")]
    display_name: Annotated[SafeClientText, Field(alias="displayName", min_length=1, max_length=80)]
    market: Literal["global", "russia", "enterprise", "unknown"]
    platform: Literal["macos", "windows", "browser", "cross_platform"]
    target_family: Literal["native_app", "browser_meeting", "provider", "manual_only"] = Field(
        alias="targetFamily",
    )
    mode: MeetingDetectionSupportMode
    evidence: Literal[
        "runtime_verified",
        "runtime_start_verified",
        "package_verified",
        "installed_verified",
        "confirmed",
        "seed",
        "verify_required",
        "future_windows",
    ]
    required_signals: list[
        Literal[
            "macos_audio_hal_assertion",
            "browser_metadata",
            "calendar_or_join_intent",
            "windows_future_adapter",
        ]
    ] = Field(alias="requiredSignals", min_length=1)
    native_bundle_ids: list[Annotated[str, Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_.-]{1,200}$")]] = Field(
        default_factory=list,
        alias="nativeBundleIds",
    )
    windows_process_names: list[Annotated[str, Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_.\- ]{1,200}$")]] = Field(
        default_factory=list,
        alias="windowsProcessNames",
    )
    browser_service_patterns: list[MeetingTargetBrowserServicePattern] = Field(
        default_factory=list,
        alias="browserServicePatterns",
    )
    comments: Annotated[SafeClientText, Field(max_length=500)] | None = None


class MeetingTargetNonTargetRule(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    platform: Literal["macos", "windows", "browser"]
    rule_kind: Literal[
        "bundle_id",
        "bundle_prefix",
        "display_name_token",
        "category",
        "windows_process_name",
        "browser_service_family",
    ] = Field(alias="ruleKind")
    rule_value: Annotated[SafeClientText, Field(alias="ruleValue", min_length=2, max_length=240)]
    reason_code: Annotated[SafeClientText, Field(alias="reasonCode", min_length=2, max_length=120)]


class MeetingTargetRegistryDocument(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    schema_version: Literal[1] = Field(alias="schemaVersion")
    registry_version: Annotated[str, Field(alias="registryVersion", pattern=r"^[0-9]{4}\.[0-9]{2}\.[0-9]{2}\.[0-9]+$")]
    generated_at: datetime = Field(alias="generatedAt")
    expires_at: datetime | None = Field(default=None, alias="expiresAt")
    targets: list[MeetingTargetRegistryTarget] = Field(min_length=1)
    non_target_rules: list[MeetingTargetNonTargetRule] = Field(
        default_factory=list,
        alias="nonTargetRules",
    )


class MeetingDetectionRegistryResponse(MeetingTargetRegistryDocument):
    etag: Annotated[SafeClientText, Field(max_length=160)] | None = None


class MeetingDetectionRollupWindow(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    bucket: Literal["hour", "day"]
    started_at: datetime = Field(alias="startedAt")
    ended_at: datetime = Field(alias="endedAt")


class MeetingDetectionPolicySummary(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    detection_mode: MeetingDetectionMode = Field(alias="detectionMode")
    upload_mode: MeetingDetectionUploadMode = Field(alias="uploadMode")
    unknown_identity_upload_allowed: bool = Field(alias="unknownIdentityUploadAllowed")


class MeetingDetectionDurationBuckets(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    under_5s: int = Field(default=0, alias="under5s", ge=0)
    from_5s_to_30s: int = Field(default=0, alias="from5sTo30s", ge=0)
    from_30s_to_5m: int = Field(default=0, alias="from30sTo5m", ge=0)
    over_5m: int = Field(default=0, alias="over5m", ge=0)


class MeetingDetectionOutcomes(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    observed: int = Field(default=0, ge=0)
    prompt_eligible: int = Field(default=0, alias="promptEligible", ge=0)
    blocked: int = Field(default=0, ge=0)
    prompted: int = Field(default=0, ge=0)
    skipped: int = Field(default=0, ge=0)
    suppressed: int = Field(default=0, ge=0)
    recorded: int = Field(default=0, ge=0)
    ended: int = Field(default=0, ge=0)
    missed_manual_start_nearby: int = Field(default=0, alias="missedManualStartNearby", ge=0)
    health_degraded: int = Field(default=0, alias="healthDegraded", ge=0)


class MeetingDetectionTargetRollup(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    target_id: Annotated[SafeClientText, Field(alias="targetId", min_length=3, max_length=80)]
    target_family: MeetingDetectionTargetFamily = Field(alias="targetFamily")
    support_mode: MeetingDetectionSupportMode = Field(alias="supportMode")
    signal_families: list[MeetingDetectionSignalFamily] = Field(default_factory=list, alias="signalFamilies")
    outcomes: MeetingDetectionOutcomes = Field(default_factory=MeetingDetectionOutcomes)
    duration_buckets: MeetingDetectionDurationBuckets = Field(
        default_factory=MeetingDetectionDurationBuckets,
        alias="durationBuckets",
    )
    reason_codes: list[Annotated[SafeClientText, Field(max_length=80)]] = Field(
        default_factory=list,
        alias="reasonCodes",
    )


class MeetingDetectionUnknownNativeAppRollup(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    identity_mode: Literal["redacted", "raw_candidate_allowed"] = Field(alias="identityMode")
    upload_eligibility: Literal[
        "local_only_low_score",
        "local_only_non_target",
        "server_candidate_upload",
    ] = Field(alias="uploadEligibility")
    candidate_score: int = Field(alias="candidateScore", ge=0, le=20)
    candidate_reasons: list[MeetingDetectionCandidateReason] = Field(alias="candidateReasons", min_length=1)
    stable_observation_count: int = Field(alias="stableObservationCount", ge=0)
    duration_buckets: MeetingDetectionDurationBuckets = Field(alias="durationBuckets")
    manual_record_nearby_count: int = Field(alias="manualRecordNearbyCount", ge=0)
    suppression_reasons: list[MeetingDetectionCandidateSuppression] = Field(
        default_factory=list,
        alias="suppressionReasons",
    )
    bundle_id: str | None = Field(default=None, alias="bundleId", pattern=r"^[A-Za-z0-9][A-Za-z0-9_.-]{1,200}$")
    display_name: SafeClientText | None = Field(default=None, alias="displayName", min_length=1, max_length=80)
    signing_team_id: str | None = Field(default=None, alias="signingTeamId", pattern=r"^[A-Za-z0-9]{5,20}$")
    version: Annotated[SafeClientText, Field(max_length=80)] | None = None
    calendar_or_join_hint_count: int = Field(default=0, alias="calendarOrJoinHintCount", ge=0)
    non_target_suppression_count: int = Field(default=0, alias="nonTargetSuppressionCount", ge=0)


class MeetingDetectionResourceRollup(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    cpu_p95_percent_bucket: Literal["not_measured", "under_1", "from_1_to_2", "from_2_to_5", "over_5"] = Field(
        default="not_measured",
        alias="cpuP95PercentBucket",
    )
    memory_overhead_bucket_mb: Literal["not_measured", "under_10", "from_10_to_30", "from_30_to_60", "over_60"] = Field(
        default="not_measured",
        alias="memoryOverheadBucketMb",
    )
    parser_restart_count: int = Field(alias="parserRestartCount", ge=0)
    dropped_event_count: int = Field(alias="droppedEventCount", ge=0)
    disk_bytes_written: int = Field(alias="diskBytesWritten", ge=0)
    upload_attempt_count: int = Field(alias="uploadAttemptCount", ge=0)


class MeetingDetectionTelemetryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    schema_version: Literal[1] = Field(alias="schemaVersion")
    client_version: Annotated[SafeClientText, Field(alias="clientVersion", min_length=1, max_length=80)]
    platform: Literal["macos", "windows"]
    os_version_major: Annotated[SafeClientText, Field(alias="osVersionMajor", min_length=1, max_length=40)]
    registry_version: Annotated[SafeClientText, Field(alias="registryVersion", min_length=1, max_length=80)]
    candidate_filter_version: Annotated[SafeClientText, Field(alias="candidateFilterVersion", min_length=1, max_length=80)]
    created_at: datetime = Field(alias="createdAt")
    rollup_window: MeetingDetectionRollupWindow = Field(alias="rollupWindow")
    policy: MeetingDetectionPolicySummary
    target_rollups: list[MeetingDetectionTargetRollup] = Field(default_factory=list, alias="targetRollups", max_length=200)
    unknown_native_app_rollups: list[MeetingDetectionUnknownNativeAppRollup] = Field(
        default_factory=list,
        alias="unknownNativeAppRollups",
        max_length=100,
    )
    resource_rollup: MeetingDetectionResourceRollup = Field(alias="resourceRollup")


class MeetingDetectionTelemetryResponse(BaseModel):
    batch_id: UUID
    dedupe_status: Literal["created", "duplicate"]
    accepted_target_rollup_count: int = Field(ge=0)
    accepted_candidate_count: int = Field(ge=0)
    suppressed_candidate_count: int = Field(ge=0)
    registry_version: SafeClientText
    next_upload_after: datetime


class PutMeetingCalendarContextRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_id: UUID
    context_reason: Literal["manual_selection", "current_event_prompt", "event_start_prompt"]


class MeetingCalendarContextResponse(BaseModel):
    meeting_id: UUID
    event_id: UUID | None = None
    context_state: Literal["linked", "unlinked", "no_context"]
    context_confidence: str | None = None
    title_source: str | None = None


class TrackDescriptor(BaseModel):
    track_role: TrackRole
    codec: str
    sample_rate_hz: int = Field(gt=0)
    channel_count: int = Field(gt=0)
    duration_seconds: int = Field(gt=0)
    byte_length: int = Field(ge=0)
    sha256: str = Field(pattern=r"^[a-f0-9]{64}$")


class MediaRevisionSummary(BaseModel):
    media_revision_id: UUID | None = None
    local_media_revision_id: str | None = None
    revision_number: int = 1
    source_kind: MediaRevisionSourceKind = MediaRevisionSourceKind.INITIAL_RECORDING
    status: MediaRevisionStatus = MediaRevisionStatus.PENDING_UPLOAD
    manifest_sha256: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")
    track_sha256_by_role: dict[str, str] = Field(default_factory=dict)


class CreateMeetingRequest(BaseModel):
    local_recording_id: Annotated[SafeClientText, Field(min_length=1, max_length=240)]
    local_media_revision_id: Annotated[SafeClientText, Field(min_length=1, max_length=300)] | None = None
    title: Annotated[SafeClientText, Field(max_length=500)] | None = None
    started_at: datetime | None = None
    ended_at: datetime | None = None
    recording_display_timezone_offset_minutes: int | None = Field(default=None, ge=-14 * 60, le=14 * 60)
    duration_seconds: int = Field(gt=0)


class MeetingResponse(BaseModel):
    meeting_id: UUID
    workspace_id: UUID
    local_recording_id: str
    local_media_revision_id: str | None = None
    title: str | None = None
    title_source: str = "generic"
    media_revision: MediaRevisionSummary | None = None
    status: MeetingStatus
    processing_status: ProcessingStatus
    started_at: datetime | None = None
    ended_at: datetime | None = None
    recording_display_timezone_offset_minutes: int | None = None
    created_at: datetime | None = None


class CreateUploadSessionRequest(BaseModel):
    expected_tracks: list[TrackRole] = Field(default_factory=lambda: [TrackRole.MANIFEST, TrackRole.MICROPHONE, TrackRole.SYSTEM])
    expected_track_sizes: dict[TrackRole, int] = Field(default_factory=dict)
    manifest_sha256: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")


class UploadSessionResponse(BaseModel):
    session_id: UUID
    meeting_id: UUID
    media_revision_id: UUID | None = None
    status: UploadSessionStatus
    upload_strategy: UploadStrategy = UploadStrategy.SERVER_MEDIATED
    expires_at: datetime
    expected_tracks: list[TrackRole] = Field(default_factory=list)
    expected_track_sizes: dict[TrackRole, int] = Field(default_factory=dict)
    accepted_bytes_by_track: dict[str, int] = Field(default_factory=dict)
    processing_status: ProcessingStatus = ProcessingStatus.NOT_SUBMITTED
    workflow_id: None = None
    mediascribe_job_id: None = None
    desktop_label: str | None = None
    desktop_truth_rule: str | None = None


class DesktopSyncMeetingState(BaseModel):
    meeting_id: UUID
    status: MeetingStatus
    processing_status: ProcessingStatus
    deletion_state: DeletionState = DeletionState.NONE
    access_state: str = "owner"


class MissingRange(BaseModel):
    start: int = Field(ge=0)
    end: int = Field(ge=0)


class DesktopSyncUploadSessionState(BaseModel):
    session_id: UUID | None = None
    status: UploadSessionStatus | None = None
    expected_tracks: list[TrackRole] = Field(default_factory=list)
    accepted_bytes_by_track: dict[str, int] = Field(default_factory=dict)
    missing_ranges_by_track: dict[str, list[MissingRange]] = Field(default_factory=dict)
    desktop_truth_rule: str = "server_ranges_authoritative"


class DesktopSyncProcessingState(BaseModel):
    status: ProcessingStatus = ProcessingStatus.NOT_SUBMITTED
    workflow_id: str | None = None
    reason_code: str | None = None


class DesktopSyncReviewState(BaseModel):
    available: bool = False
    status: str = "unavailable"
    media_revision_id: UUID | None = None
    transcript_available: bool = False
    diarization_available: bool = False
    content_available: bool = False
    web_url: str | None = None
    desktop_url: str | None = None


class DesktopSyncConflict(BaseModel):
    state: SyncConflictState = SyncConflictState.NONE
    reason: str | None = None
    next_action: str = "continue_upload"


class CustodyIncidentReadModel(BaseModel):
    safe_recording_identity: Annotated[SafeClientText, Field(max_length=180)]
    reason_category: Annotated[SafeClientText, Field(max_length=120)]
    problem_code: Annotated[SafeClientText, Field(max_length=120)]
    owner: CustodyOwner
    retry_class: CustodyRetryClass
    normal_user_action: CustodyNormalUserAction
    created_at: datetime | None = None
    updated_at: datetime | None = None
    lifecycle_state: CustodyState
    retention_deadline: datetime | None = None
    server_identity_present: bool
    metadata_safety: CustodyMetadataSafety = CustodyMetadataSafety.METADATA_ONLY


class CustodyReadModel(BaseModel):
    state: CustodyState
    upload_state: CustodyUploadState
    processing_state: CustodyProcessingState
    owner: CustodyOwner
    retry_class: CustodyRetryClass
    normal_user_action: CustodyNormalUserAction
    display_priority: int = Field(ge=0)
    review_available: bool = False
    review_desktop_url: str | None = None
    safe_incident_available: bool = False
    incident: CustodyIncidentReadModel | None = None
    retention_deadline: datetime | None = None
    copy_key: Annotated[str, Field(pattern=r"^custody\.[a-z0-9_]+$")]
    metadata_safety: CustodyMetadataSafety = CustodyMetadataSafety.METADATA_ONLY


class DesktopRecordingSyncStateResponse(BaseModel):
    local_recording_id: str
    local_media_revision_id: str
    meeting: DesktopSyncMeetingState
    media_revision: MediaRevisionSummary
    upload_session: DesktopSyncUploadSessionState
    processing: DesktopSyncProcessingState
    review: DesktopSyncReviewState
    conflict: DesktopSyncConflict = Field(default_factory=DesktopSyncConflict)
    custody: CustodyReadModel | None = None


class UploadPartResponse(BaseModel):
    session_id: UUID
    track_role: TrackRole
    part_number: int = Field(ge=0)
    byte_offset: int = Field(ge=0)
    byte_length: int = Field(ge=0)
    sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    status: str = "accepted"


class MissingRangesResponse(BaseModel):
    session_id: UUID
    missing_ranges_by_track: dict[TrackRole, list[MissingRange]]


class FinalizeUploadRequest(BaseModel):
    manifest_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    tracks: list[TrackDescriptor] = Field(min_length=2)


class FinalizeUploadResponse(BaseModel):
    meeting: MeetingResponse
    upload_session: UploadSessionResponse
    object_count: int = Field(ge=0)
    workflow_started: bool = False
    mediascribe_job_created: bool = False


class ManualMediaUploadResponse(FinalizeUploadResponse):
    request_mode: Literal["single_track"] = "single_track"


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
    media_revision_id: UUID | None = None
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


class CreateDeletionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    confirmation_boundary: Literal["Delete this meeting everywhere GRAF controls."]
    reason_code: DeletionReasonCode = DeletionReasonCode.USER_REQUEST


class DeletionLifecycleState(BaseModel):
    state: DeletionState
    label: str
    reason: str | None = None
    can_retry: bool
    can_view_report: bool


class ArtifactDeletionState(BaseModel):
    artifact_class: str
    control_scope: DeletionControlScope
    state: DeletionArtifactState
    label: str
    safe_reason: str | None = None
    completed_at: datetime | None = None


class LocalPurgeTask(BaseModel):
    task_id: UUID
    meeting_id: UUID
    task_type: LocalPurgeTaskType
    state: LocalPurgeTaskState
    safe_reason: str | None = None
    expires_at: datetime
    ack_url: str | None = None


class LocalPurgeTaskList(BaseModel):
    tasks: list[LocalPurgeTask] = Field(default_factory=list)


class LocalPurgeAckRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    state: Literal[
        LocalPurgeTaskState.ACKNOWLEDGED,
        LocalPurgeTaskState.FAILED,
        LocalPurgeTaskState.LOCAL_EXPIRY_RELIED_UPON,
    ]
    reason_code: Annotated[SafeClientText, Field(max_length=120)] | None = None
    client_version: Annotated[SafeClientText, Field(max_length=80)] | None = None
    completed_at: datetime | None = None


LifecycleActivityOutcome = Literal["accepted", "denied", "completed", "failed", "skipped", "blocked"]


class LifecycleActivityItem(BaseModel):
    event_id: UUID
    event_type: Annotated[SafeClientText, Field(max_length=120)]
    actor_label: Annotated[SafeClientText, Field(max_length=80)]
    outcome: LifecycleActivityOutcome
    safe_reason: Annotated[SafeClientText, Field(max_length=240)] | None = None
    created_at: datetime


class DeletionVerificationReport(BaseModel):
    meeting_id: UUID
    request_id: UUID
    overall_state: DeletionState
    bounded_copy: str
    artifact_states: list[ArtifactDeletionState] = Field(default_factory=list)
    backup: ArtifactDeletionState
    local_purge: list[LocalPurgeTask] = Field(default_factory=list)
    dependencies: list[ArtifactDeletionState] = Field(default_factory=list)
    post_egress_limits: list[ArtifactDeletionState] = Field(default_factory=list)
    activity: list[LifecycleActivityItem] = Field(default_factory=list)
    generated_at: datetime | None = None


class DeletionRequestResponse(BaseModel):
    request_id: UUID
    meeting_id: UUID
    lifecycle: DeletionLifecycleState
    report_url: str


class RetentionRunRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    limit: int = Field(default=100, ge=1, le=500)
    dry_run: bool = False


class RetentionRunResponse(BaseModel):
    evaluated: int = Field(ge=0)
    created_requests: int = Field(ge=0)
    skipped: int = Field(ge=0)
    blocked: int = Field(ge=0)
    policy_snapshot_id: UUID | None = None


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
MeetingSource = Literal["desktop_recording", "video_recording", "manual_upload", "unknown"]
PrimaryAction = Literal["open", "wait", "retry_future", "open_status", "unavailable"]
SourceRoleView = Literal["local_microphone", "incoming_system", "unknown"]
PlaybackUnavailableReason = Literal[
    "none",
    "no_audio",
    "policy_disabled",
    "access_denied",
    "processing",
    "failed",
    "deleted",
    "deleting",
    "audio_purged",
    "transcript_only",
    "review_audio_unavailable",
    "storage_unavailable",
]
PlaybackSourceMode = Literal["none", "combined_review_stream", "single_retained_track", "stored_review_m4a"]
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


NotesActionAvailabilityState = Literal[
    "available",
    "not_found",
    "not_inferable",
    "processing",
    "blocked",
    "unavailable",
    "deferred",
    "unsafe",
]
NotesActionSourceBasis = Literal[
    "stored_output",
    "processing_status",
    "transcript_only",
    "policy_deferral",
    "not_supported",
    "blocked",
]
NotesActionReadinessImpact = Literal["closes_gap", "keeps_gap_open", "non_blocking"]
OutcomeTruthLabel = Literal["supported", "not_found", "not_inferable", "unsafe", "blocked"]
OutcomeEvidenceKind = Literal["segment", "timestamp", "category_state", "source_hint"]


class OutcomeSourceReferenceView(BaseModel):
    transcript_segment_id: UUID | None = None
    sequence: int | None = None
    start_seconds: float | None = Field(default=None, ge=0)
    end_seconds: float | None = Field(default=None, ge=0)
    speaker_label: str | None = None
    source_role: str | None = None
    evidence_kind: OutcomeEvidenceKind


class OutcomeItemView(BaseModel):
    category: str
    sequence: int = Field(ge=0)
    text: str | None = None
    owner_text: str | None = None
    due_date_text: str | None = None
    truth_label: OutcomeTruthLabel
    source_refs: list[OutcomeSourceReferenceView] = Field(default_factory=list)


class OutcomeProvenanceView(BaseModel):
    generator_kind: str
    generator_version: str
    generated_at: datetime | None = None
    latency_ms: int | None = Field(default=None, ge=0)


def _default_deferred_notes_category() -> "NotesActionCategoryState":
    return NotesActionCategoryState(
        state="deferred",
        label="Outcomes deferred",
        reason="Generated meeting outcomes are deferred until stored output is available.",
        readiness_impact="keeps_gap_open",
        copy_key="notes.outcomes.deferred",
    )


class NotesActionCategoryState(BaseModel):
    state: NotesActionAvailabilityState
    label: str
    reason: str
    readiness_impact: NotesActionReadinessImpact
    copy_key: str
    items: list[OutcomeItemView] = Field(default_factory=list)


class NotesActionTruthState(BaseModel):
    summary: NotesActionCategoryState
    key_points: NotesActionCategoryState = Field(default_factory=_default_deferred_notes_category)
    decisions: NotesActionCategoryState
    action_items: NotesActionCategoryState
    followups: NotesActionCategoryState
    risks: NotesActionCategoryState = Field(default_factory=_default_deferred_notes_category)
    questions: NotesActionCategoryState = Field(default_factory=_default_deferred_notes_category)
    evidence: NotesActionCategoryState = Field(default_factory=_default_deferred_notes_category)
    source_basis: NotesActionSourceBasis
    provenance: OutcomeProvenanceView | None = None


def default_notes_action_truth() -> NotesActionTruthState:
    category = _default_deferred_notes_category()
    return NotesActionTruthState(
        summary=category,
        key_points=category,
        decisions=category,
        action_items=category,
        followups=category,
        risks=category,
        questions=category,
        evidence=category,
        source_basis="policy_deferral",
    )


class MeetingUploadProgressState(BaseModel):
    status: str
    label: str
    uploaded_bytes: int = Field(ge=0)
    total_bytes: int = Field(ge=0)
    progress_percent: int | None = Field(default=None, ge=0, le=100)
    is_active: bool = False


class MeetingListItem(BaseModel):
    meeting_id: UUID
    title: str
    started_at: datetime | None = None
    ended_at: datetime | None = None
    recording_display_timezone_offset_minutes: int | None = None
    duration_seconds: int = Field(ge=0)
    source: MeetingSource = "desktop_recording"
    status: MeetingReviewStatus
    status_label: str
    status_reason: str | None = None
    primary_action: PrimaryAction
    transcript_available: bool = False
    diarization_available: bool = False
    notes_available: bool = False
    notes_action_truth: NotesActionTruthState = Field(default_factory=default_notes_action_truth)
    updated_at: datetime | None = None
    access: MeetingAccessState | None = None
    artifacts: list[ArtifactEgressState] = Field(default_factory=list)
    governance: GovernanceActionSummary
    custody: CustodyReadModel | None = None
    upload: MeetingUploadProgressState | None = None
    future_slots: list[SlotState] = Field(default_factory=list)


class MeetingListResponse(BaseModel):
    items: list[MeetingListItem]
    filters: MeetingFilterState
    generated_at: datetime


class MeetingProvenance(BaseModel):
    media_revision_id: UUID | None = None
    local_media_revision_id: str | None = None
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
    seekable: bool = False
    seek_seconds: float | None = None


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


class CalendarRosterParticipantView(BaseModel):
    participant_kind: str
    response_status: str
    display_name: str | None = None
    email_present: bool = False
    workspace_relation: str = "unknown"
    recipient_candidate_class: str = "unknown"


class CalendarRosterReviewState(BaseModel):
    available: bool = False
    roster_state: str = "not_available"
    participant_count: int = 0
    source: Literal["calendar", "none"] = "none"
    participants: list[CalendarRosterParticipantView] = Field(default_factory=list)


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
    unavailable_reason: PlaybackUnavailableReason = "none"
    playback_path: str | None = None
    policy_label: str = "Аудио недоступно"
    source_mode: PlaybackSourceMode = "none"
    included_sources: list[SourceRoleView] = Field(default_factory=list)


class MeetingReviewResponse(BaseModel):
    meeting: MeetingListItem
    provenance: MeetingProvenance
    processing: ProcessingReviewState
    transcript: TranscriptReviewState
    speakers: SpeakerReviewState
    calendar_roster: CalendarRosterReviewState | None = None
    notes: NotesReviewState
    notes_action_truth: NotesActionTruthState = Field(default_factory=default_notes_action_truth)
    playback: PlaybackReviewState
    governance: GovernanceActionSummary
    access: MeetingAccessState | None = None
    share: SharePanelState | None = None
    artifacts: list[ArtifactEgressState] = Field(default_factory=list)
    activity: MeetingActivityResponse | None = None
    deletion_truth_copy: str | None = None
    assistant: SlotState
    template: SlotState
