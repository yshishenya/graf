from datetime import datetime
from enum import StrEnum
from typing import Annotated, Any, Literal, Self
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    PrivateAttr,
    StringConstraints,
    field_validator,
    model_validator,
)

from twobrain_rec_server.api.problems import ProblemDetail
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


SafeClientText = Annotated[
    str, StringConstraints(strip_whitespace=True, pattern=r"^[^\x00-\x1f\x7f]+$")
]


class MeetingTitleSource(StrEnum):
    USER_CONFIRMED = "user_confirmed"
    CALENDAR = "calendar"
    APP_CONTEXT = "app_context"
    GENERIC = "generic"
    UPLOAD_PROVIDED = "upload_provided"
    FILE_NAME_DERIVED = "file_name_derived"
    LEGACY_UNKNOWN = "legacy_unknown"


class DesktopMeetingTitleSource(StrEnum):
    USER_CONFIRMED = "user_confirmed"
    APP_CONTEXT = "app_context"
    GENERIC = "generic"
    UNKNOWN = "unknown"


LegacyMeetingTitleSource = Literal["user", "user_or_generic", "unknown"]


class CalendarMatchDecisionIntent(StrEnum):
    AUTOMATIC = "automatic"
    USER_SELECTED = "user_selected"
    USER_DECLINED = "user_declined"


class CalendarMatchAttemptState(StrEnum):
    MATCHED_AUTO = "matched_auto"
    MATCHED_USER = "matched_user"
    PROVISIONAL_PRESTART = "provisional_prestart"
    AMBIGUOUS = "ambiguous"
    NO_CONTEXT = "no_context"
    SKIPPED_PRIVATE = "skipped_private"
    SKIPPED_ALL_DAY = "skipped_all_day"
    SKIPPED_STALE_CALENDAR = "skipped_stale_calendar"
    CALENDAR_UNAVAILABLE = "calendar_unavailable"
    DECLINED_BY_USER = "declined_by_user"


class CalendarContextState(StrEnum):
    MATCHED_AUTO = "matched_auto"
    MATCHED_USER = "matched_user"
    AMBIGUOUS = "ambiguous"
    NO_CONTEXT = "no_context"
    SKIPPED_PRIVATE = "skipped_private"
    SKIPPED_ALL_DAY = "skipped_all_day"
    SKIPPED_STALE_CALENDAR = "skipped_stale_calendar"
    CALENDAR_UNAVAILABLE = "calendar_unavailable"
    SKIPPED_OFFLINE_OR_UNKNOWN = "skipped_offline_or_unknown"
    SKIPPED_MANUAL_UPLOAD = "skipped_manual_upload"
    DECLINED_BY_USER = "declined_by_user"
    CLEARED_BY_USER = "cleared_by_user"
    DELETED = "deleted"
    LEGACY_LINKED = "legacy_linked"


class CalendarContextConfidence(StrEnum):
    HIGH = "high"
    SELECTED = "selected"
    AMBIGUOUS = "ambiguous"
    NONE = "none"


class CalendarContextDecisionSource(StrEnum):
    AUTOMATIC = "automatic"
    USER = "user"
    SYSTEM_SKIP = "system_skip"
    LEGACY = "legacy"


class CalendarContextReasonCode(StrEnum):
    SINGLE_FRESH_CANDIDATE = "single_fresh_candidate"
    MULTIPLE_TIME_CANDIDATES = "multiple_time_candidates"
    BACK_TO_BACK_BOUNDARY = "back_to_back_boundary"
    NO_MATCHING_EVENT = "no_matching_event"
    WEAK_EVENT_SIGNAL = "weak_event_signal"
    PRIVATE_FREE_BUSY_SKIPPED = "private_free_busy_skipped"
    ALL_DAY_SKIPPED = "all_day_skipped"
    SELECTED_SOURCE_STALE = "selected_source_stale"
    LATEST_SYNC_FAILED = "latest_sync_failed"
    CALENDAR_NOT_CONNECTED = "calendar_not_connected"
    CALENDAR_NOT_SELECTED = "calendar_not_selected"
    CALENDAR_UNAVAILABLE = "calendar_unavailable"
    MANUAL_UPLOAD_SKIPPED = "manual_upload_skipped"
    OFFLINE_OR_UNKNOWN_SKIPPED = "offline_or_unknown_skipped"
    PRESTART_NOT_REACHED = "prestart_not_reached"
    USER_SELECTED = "user_selected"
    USER_DECLINED = "user_declined"
    USER_CLEARED = "user_cleared"
    MEETING_DELETED = "meeting_deleted"


class CalendarContextTitleState(StrEnum):
    AVAILABLE = "available"
    POLICY_HIDDEN = "policy_hidden"
    UNAVAILABLE = "unavailable"


class CalendarContextRosterState(StrEnum):
    AVAILABLE = "available"
    NOT_AVAILABLE = "not_available"
    HIDDEN = "hidden"


class PreviousRecurringMeetingReadiness(StrEnum):
    NOTES_READY = "notes_ready"
    TRANSCRIPT_READY = "transcript_ready"
    PROCESSING = "processing"
    UNAVAILABLE = "unavailable"


class SupportIncidentReportRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    schema_version: str
    redaction_state: Literal["metadata_only"]
    range_mismatch_metadata: dict[str, Any] = Field(default_factory=dict)
    local_file_completeness_profile: dict[str, Any] = Field(default_factory=dict)
    local_purge_tasks: list[Any] = Field(default_factory=list)


class SupportIncidentResponse(BaseModel):
    incident_id: Annotated[str, Field(pattern=r"^CUST-[A-Z0-9-]{1,27}$")]
    incident_status: Literal["synced", "pending_sync"]
    github_issue_number: int | None = Field(default=None, gt=0)
    github_issue_url: str | None = None
    dedupe_status: Literal["created", "updated"]
    affected_count: int = Field(ge=1)
    copy_fallback_available: bool = True
    user_message: str


class CalendarProviderPreset(BaseModel):
    provider_family: str
    label: str
    adapter_family: Literal["caldav", "rich_api", "ews", "google_api"]
    supported: bool
    runtime_available: bool = False
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
    external_revoke: Literal[
        "confirmed", "not_supported", "pending", "failed", "not_applicable"
    ] = "not_supported"
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
    show_upcoming_time: bool = True
    show_upcoming_title: bool = True


class DesktopCalendarPromptEvent(CalendarEventSummary):
    join_prompt_due_at: datetime | None = None
    record_prompt_due_at: datetime | None = None
    join_prompt_state: str
    record_prompt_state: str
    open_meeting_url: str | None = None


class DesktopCalendarPromptResponse(BaseModel):
    show_upcoming_time: bool = True
    show_upcoming_title: bool = True
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
    host_category: Literal["first_party", "enterprise_domain", "unknown"] = Field(
        alias="hostCategory"
    )
    pattern_class: Literal["meeting_room", "join_intent", "landing", "settings", "unsupported"] = (
        Field(
            alias="patternClass",
        )
    )


class MeetingTargetRegistryTarget(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    id: Annotated[
        SafeClientText, Field(min_length=3, max_length=80, pattern=r"^[a-z0-9][a-z0-9_-]{2,80}$")
    ]
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
    native_bundle_ids: list[
        Annotated[str, Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_.-]{1,200}$")]
    ] = Field(
        default_factory=list,
        alias="nativeBundleIds",
    )
    windows_process_names: list[
        Annotated[str, Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_.\- ]{1,200}$")]
    ] = Field(
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


class AssistedAutoStartPolicy(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    scope: Literal["workspace", "all_workspaces"] = "workspace"
    policy_ref: str = Field(alias="policyRef", pattern=r"^sha256:[0-9a-f]{64}$")
    acknowledgement_subject_ref: str = Field(
        alias="acknowledgementSubjectRef",
        pattern=r"^sha256:[0-9a-f]{64}$",
    )
    device_ref: str = Field(alias="deviceRef", pattern=r"^sha256:[0-9a-f]{64}$")
    policy_version: str = Field(
        alias="policyVersion",
        min_length=1,
        max_length=64,
        pattern=r"^[A-Za-z0-9._-]+$",
    )
    acknowledgement_version: str = Field(
        alias="acknowledgementVersion",
        min_length=1,
        max_length=64,
        pattern=r"^[A-Za-z0-9._-]+$",
    )
    enabled: Literal[True]
    issued_at: datetime = Field(alias="issuedAt")
    expires_at: datetime = Field(alias="expiresAt")
    notice_mode: Literal["internal_no_participant_notice"] = Field(alias="noticeMode")


class MeetingTargetRegistryDocument(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    schema_version: Literal[1] = Field(alias="schemaVersion")
    registry_version: Annotated[
        str, Field(alias="registryVersion", pattern=r"^[0-9]{4}\.[0-9]{2}\.[0-9]{2}\.[0-9]+$")
    ]
    generated_at: datetime = Field(alias="generatedAt")
    expires_at: datetime | None = Field(default=None, alias="expiresAt")
    targets: list[MeetingTargetRegistryTarget] = Field(min_length=1)
    non_target_rules: list[MeetingTargetNonTargetRule] = Field(
        default_factory=list,
        alias="nonTargetRules",
    )
    assisted_auto_start_policy: AssistedAutoStartPolicy | None = Field(
        default=None,
        alias="assistedAutoStartPolicy",
        exclude_if=lambda value: value is None,
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
    signal_families: list[MeetingDetectionSignalFamily] = Field(
        default_factory=list, alias="signalFamilies"
    )
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
    candidate_reasons: list[MeetingDetectionCandidateReason] = Field(
        alias="candidateReasons", min_length=1
    )
    stable_observation_count: int = Field(alias="stableObservationCount", ge=0)
    duration_buckets: MeetingDetectionDurationBuckets = Field(alias="durationBuckets")
    manual_record_nearby_count: int = Field(alias="manualRecordNearbyCount", ge=0)
    suppression_reasons: list[MeetingDetectionCandidateSuppression] = Field(
        default_factory=list,
        alias="suppressionReasons",
    )
    bundle_id: str | None = Field(
        default=None, alias="bundleId", pattern=r"^[A-Za-z0-9][A-Za-z0-9_.-]{1,200}$"
    )
    display_name: SafeClientText | None = Field(
        default=None, alias="displayName", min_length=1, max_length=80
    )
    signing_team_id: str | None = Field(
        default=None, alias="signingTeamId", pattern=r"^[A-Za-z0-9]{5,20}$"
    )
    version: Annotated[SafeClientText, Field(max_length=80)] | None = None
    calendar_or_join_hint_count: int = Field(default=0, alias="calendarOrJoinHintCount", ge=0)
    non_target_suppression_count: int = Field(default=0, alias="nonTargetSuppressionCount", ge=0)


class MeetingDetectionResourceRollup(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    cpu_p95_percent_bucket: Literal[
        "not_measured", "under_1", "from_1_to_2", "from_2_to_5", "over_5"
    ] = Field(
        default="not_measured",
        alias="cpuP95PercentBucket",
    )
    memory_overhead_bucket_mb: Literal[
        "not_measured", "under_10", "from_10_to_30", "from_30_to_60", "over_60"
    ] = Field(
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
    client_version: Annotated[
        SafeClientText, Field(alias="clientVersion", min_length=1, max_length=80)
    ]
    platform: Literal["macos", "windows"]
    os_version_major: Annotated[
        SafeClientText, Field(alias="osVersionMajor", min_length=1, max_length=40)
    ]
    registry_version: Annotated[
        SafeClientText, Field(alias="registryVersion", min_length=1, max_length=80)
    ]
    candidate_filter_version: Annotated[
        SafeClientText, Field(alias="candidateFilterVersion", min_length=1, max_length=80)
    ]
    created_at: datetime = Field(alias="createdAt")
    rollup_window: MeetingDetectionRollupWindow = Field(alias="rollupWindow")
    policy: MeetingDetectionPolicySummary
    target_rollups: list[MeetingDetectionTargetRollup] = Field(
        default_factory=list, alias="targetRollups", max_length=200
    )
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


class ResolveRecordingCalendarContextRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    recording_started_at: datetime
    decision_intent: CalendarMatchDecisionIntent
    event_id: UUID | None = None
    contract_version: Literal["calendar_auto_context_v1"]

    @field_validator("recording_started_at")
    @classmethod
    def require_timezone_aware_start(cls, value: datetime) -> datetime:
        if value.utcoffset() is None:
            raise ValueError("recording_started_at must include a timezone")
        return value

    @model_validator(mode="after")
    def validate_event_selection(self) -> "ResolveRecordingCalendarContextRequest":
        if self.decision_intent is CalendarMatchDecisionIntent.USER_SELECTED:
            if self.event_id is None:
                raise ValueError("event_id is required for user_selected intent")
        elif self.event_id is not None:
            raise ValueError("event_id is allowed only for user_selected intent")
        return self


class ResolveRecordingCalendarContextResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    attempt_id: UUID
    context_state: CalendarMatchAttemptState
    reason_code: CalendarContextReasonCode
    context_confidence: CalendarContextConfidence
    candidate_count: int = Field(ge=0)
    matcher_version: Annotated[SafeClientText, Field(min_length=1, max_length=80)]
    expires_at: datetime


class CalendarContextCandidateView(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_id: UUID
    safe_title: Annotated[SafeClientText, Field(max_length=500)] | None = None
    starts_at: datetime
    ends_at: datetime
    safe_source_label: Annotated[SafeClientText, Field(min_length=1, max_length=160)]
    roster_state: CalendarContextRosterState = CalendarContextRosterState.NOT_AVAILABLE
    participant_count: int = Field(default=0, ge=0)

    @model_validator(mode="after")
    def validate_event_interval(self) -> "CalendarContextCandidateView":
        if self.ends_at <= self.starts_at:
            raise ValueError("ends_at must be later than starts_at")
        return self


class CalendarRosterSnapshotItem(BaseModel):
    model_config = ConfigDict(extra="forbid")

    participant_kind: Annotated[SafeClientText, Field(min_length=1, max_length=80)]
    response_status: Annotated[SafeClientText, Field(min_length=1, max_length=80)]
    display_name: Annotated[SafeClientText, Field(max_length=240)] | None = None
    email_present: bool = False
    workspace_relation: Annotated[SafeClientText, Field(min_length=1, max_length=80)] = "unknown"
    recipient_candidate_class: Annotated[SafeClientText, Field(min_length=1, max_length=80)] = (
        "unknown"
    )


class CalendarContextRosterView(BaseModel):
    model_config = ConfigDict(extra="forbid")

    roster_state: CalendarContextRosterState = CalendarContextRosterState.NOT_AVAILABLE
    participant_count: int = Field(default=0, ge=0)
    participants: list[CalendarRosterSnapshotItem] = Field(default_factory=list, max_length=100)


class PreviousRecurringMeetingView(BaseModel):
    model_config = ConfigDict(extra="forbid")

    meeting_id: UUID
    safe_title: Annotated[SafeClientText, Field(max_length=500)] | None = None
    started_at: datetime
    readiness_state: PreviousRecurringMeetingReadiness


class MeetingCalendarContextSummary(BaseModel):
    model_config = ConfigDict(extra="forbid")

    state: CalendarContextState
    label: Annotated[SafeClientText, Field(min_length=1, max_length=160)]
    reason_label: Annotated[
        SafeClientText | None,
        Field(
            default=None,
            min_length=1,
            max_length=240,
            exclude_if=lambda value: value is None,
        ),
    ]
    title_source: MeetingTitleSource | None = None
    needs_owner_action: bool = False


class PutMeetingCalendarContextRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_id: UUID
    context_reason: Literal[
        "manual_selection",
        "ambiguity_resolution",
        "correction",
        "current_event_prompt",
        "event_start_prompt",
    ]


class MeetingCalendarContextResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    meeting_id: UUID
    event_id: UUID | None = None
    context_state: CalendarContextState
    context_confidence: CalendarContextConfidence | None = None
    reason_code: CalendarContextReasonCode | None = None
    decision_source: CalendarContextDecisionSource | None = None
    title_source: MeetingTitleSource | LegacyMeetingTitleSource | None = None
    matched_title: Annotated[SafeClientText, Field(max_length=500)] | None = None
    matched_event_starts_at: datetime | None = None
    matched_event_ends_at: datetime | None = None
    candidate_count: int = Field(default=0, ge=0)
    candidates: list[CalendarContextCandidateView] = Field(default_factory=list, max_length=10)
    roster: CalendarContextRosterView | None = None
    previous_recurring_meeting: PreviousRecurringMeetingView | None = None
    can_change: bool = False
    can_clear: bool = False


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
    model_config = ConfigDict(extra="forbid")

    local_recording_id: Annotated[SafeClientText, Field(min_length=1, max_length=240)]
    local_media_revision_id: (
        Annotated[SafeClientText, Field(min_length=1, max_length=300)] | None
    ) = None
    source_kind: MediaRevisionSourceKind = MediaRevisionSourceKind.INITIAL_RECORDING
    media_scribe_source_mode: Literal["dual", "single_wav_v1"] = "dual"
    title: Annotated[SafeClientText, Field(max_length=500)] | None = None
    title_source: DesktopMeetingTitleSource | None = None
    calendar_match_attempt_id: UUID | None = None
    started_at: datetime | None = None
    ended_at: datetime | None = None
    recording_display_timezone_offset_minutes: int | None = Field(
        default=None, ge=-14 * 60, le=14 * 60
    )
    duration_seconds: int = Field(gt=0)


class MeetingResponse(BaseModel):
    meeting_id: UUID
    workspace_id: UUID
    local_recording_id: str
    local_media_revision_id: str | None = None
    title: str | None = None
    title_source: MeetingTitleSource | LegacyMeetingTitleSource = MeetingTitleSource.GENERIC
    media_revision: MediaRevisionSummary | None = None
    status: MeetingStatus
    processing_status: ProcessingStatus
    started_at: datetime | None = None
    ended_at: datetime | None = None
    recording_display_timezone_offset_minutes: int | None = None
    calendar_context: MeetingCalendarContextSummary | None = None
    created_at: datetime | None = None


class CreateUploadSessionRequest(BaseModel):
    expected_tracks: list[TrackRole] = Field(
        default_factory=lambda: [TrackRole.MANIFEST, TrackRole.MICROPHONE, TrackRole.SYSTEM]
    )
    expected_track_sizes: dict[TrackRole, int] = Field(default_factory=dict)
    manifest_sha256: str | None = Field(default=None, pattern=r"^[a-f0-9]{64}$")


class CreateMediaRevisionUploadSessionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    local_media_revision_id: Annotated[SafeClientText, Field(min_length=1, max_length=300)]
    source_kind: MediaRevisionSourceKind = MediaRevisionSourceKind.REPROCESS
    duration_seconds: int = Field(gt=0)
    expected_tracks: list[TrackRole] = Field(default_factory=list)
    expected_track_sizes: dict[TrackRole, int] = Field(default_factory=dict)


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
    archive_audio: bool = True
    workflow_id: None = None
    mediascribe_job_id: None = None
    desktop_label: str | None = None
    desktop_truth_rule: str | None = None


class MediaRevisionUploadSessionResponse(BaseModel):
    """Durable reprocess upload handle pinned to one immutable revision."""

    media_revision: MediaRevisionSummary
    upload_session: UploadSessionResponse


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
    archive_audio: bool = True


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
    archive_audio: bool | None = None


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
    archive_audio: bool = True
    transient_state: str = "not_applicable"
    transient_purge_due_at: datetime | None = None
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


LifecycleActivityOutcome = Literal[
    "accepted", "denied", "completed", "failed", "skipped", "blocked"
]


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
    dry_run: bool = True


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
SourceRoleView = Literal[
    "local_microphone",
    "incoming_system",
    "uploaded_media",
    "canonical_mixed",
    "unknown",
]
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
PlaybackSourceMode = Literal["none", "stored_review_m4a"]
PlaybackPreparationStateValue = Literal[
    "preparing",
    "available",
    "unavailable",
    "deleting",
    "deleted",
]
PlaybackPreparationReasonCode = Literal[
    "normalization_queued",
    "normalization_running",
    "normalization_publishing",
    "normalization_retry_wait",
    "reconciliation_pending",
    "canonical_artifact_missing",
    "canonical_ready",
    "access_denied",
    "empty_source",
    "no_audio",
    "ambiguous_audio_tracks",
    "unsupported_media",
    "encrypted_media",
    "corrupt_source",
    "limit_exceeded",
    "source_missing",
    "source_mismatch",
    "meeting_deleting",
    "meeting_deleted",
    "audio_purged",
]
GovernanceState = Literal[
    "available", "disabled", "planned", "policy_blocked", "browser_handoff", "out_of_scope"
]
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
ContentExportScope = Literal["transcript", "summary", "combined"]
ContentExportFormat = Literal["txt", "md", "csv", "xlsx", "json", "srt", "vtt"]
CONTENT_EXPORT_FORMATS_BY_SCOPE: dict[ContentExportScope, tuple[ContentExportFormat, ...]] = {
    "transcript": ("txt", "md", "csv", "xlsx", "json", "srt", "vtt"),
    "summary": ("txt", "md", "xlsx", "json"),
    "combined": ("txt", "md", "xlsx", "json"),
}
CONTENT_EXPORT_FORMATS = frozenset(
    format_name for formats in CONTENT_EXPORT_FORMATS_BY_SCOPE.values() for format_name in formats
)
ContentExportReadinessState = Literal[
    "available",
    "processing",
    "partial",
    "missing",
    "denied",
    "deletion_in_progress",
    "failed",
    "audit_unavailable",
]
TeamVisibilityState = Literal["enabled", "disabled", "policy_blocked"]
CopyLinkState = Literal["available", "auth_required", "disabled"]
PublicLinkState = Literal["disabled_by_default", "policy_blocked"]
ShareGrantStatus = Literal["active", "revoked"]
ActivityOutcome = Literal["allowed", "denied", "completed", "failed", "prepared"]
ExportPackageStatus = Literal["requested", "ready", "failed", "expired"]
SummaryTemplateKind = Literal["builtin", "personal"]
SummaryTemplateStatus = Literal["active", "archived", "deleted"]
SummaryDetailLevel = Literal["brief", "standard", "detailed"]
SummaryOutputLanguage = Literal["ru", "en"]
SummarySection = Literal[
    "summary",
    "key_points",
    "decisions",
    "action_items",
    "followups",
    "risks",
    "questions",
    "evidence",
]
SummaryCandidateState = Literal[
    "queued",
    "generating",
    "blocked_dependency",
    "candidate",
    "accepted",
    "rejected",
    "failed",
    "cancelled",
]
SummaryCandidateProjectionState = Literal[
    "generating",
    "ready",
    "accepted",
    "closed",
    "failed",
    "blocked",
    "stale",
    "expired",
]
SummaryCandidateReasonCode = Literal[
    "generating",
    "dismissed",
    "cancelled",
    "result_invalid",
    "transcript_unavailable",
    "source_unavailable",
    "source_changed",
    "template_unavailable",
    "revision_changed",
    "prompt_invalid",
    "provider_outcome_unknown",
    "content_unavailable",
    "input_too_large",
    "generation_in_progress",
    "meeting_deleting",
    "meeting_deleted",
    "temporary_unavailable",
    "prompt_unavailable",
    "provider_unavailable",
    "generation_failed",
]
SummaryCandidateNextAction = Literal[
    "wait",
    "review",
    "new_candidate",
    "refresh",
    "choose_format",
    "refresh_status",
    "open_meeting",
    "open_meetings",
    "retry",
]
ShareAudienceType = Literal["user", "workspace", "team", "link"]
ShareContentScope = Literal["summary_only", "full_meeting"]
ShareCapabilityState = Literal["available", "policy_blocked", "auth_required"]
ShareRecipientSource = Literal["workspace", "calendar", "workspace_calendar"]
ShareRecipientType = Literal["workspace_member"]
ShareRecipientFreshness = Literal["current", "stale", "unknown"]
ExternalInvitationState = Literal["available", "disabled"]
ShareInvitationStatus = Literal[
    "pending",
    "sending",
    "sent",
    "accepted",
    "expired",
    "revoked",
    "failed",
    "outcome_unknown",
    "deleted",
]


class CreateSummaryTemplateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    name: SafeClientText = Field(min_length=1, max_length=80)
    purpose: SafeClientText = Field(min_length=1, max_length=240)
    sections: list[SummarySection] = Field(min_length=1, max_length=8)
    output_language: SummaryOutputLanguage
    detail_level: SummaryDetailLevel

    @field_validator("name")
    @classmethod
    def normalize_name(cls, value: str) -> str:
        return " ".join(value.split())

    @field_validator("sections")
    @classmethod
    def require_unique_sections(cls, value: list[SummarySection]) -> list[SummarySection]:
        if len(value) != len(set(value)):
            raise ValueError("summary sections must be unique")
        return value


class UpdateSummaryTemplateRequest(CreateSummaryTemplateRequest):
    expected_version: int = Field(ge=1)


class SummaryTemplateView(BaseModel):
    template_id: UUID | None = None
    template_key: str
    kind: SummaryTemplateKind
    name: str
    purpose: str
    sections: list[SummarySection]
    output_language: SummaryOutputLanguage
    detail_level: SummaryDetailLevel
    version: int = Field(ge=1)
    status: SummaryTemplateStatus
    can_edit: bool = False
    can_duplicate: bool = True


class SummaryTemplateListResponse(BaseModel):
    default_template_key: str
    can_manage_default: bool = False
    recommended: list[SummaryTemplateView] = Field(default_factory=list, max_length=4)
    personal: list[SummaryTemplateView] = Field(default_factory=list, max_length=100)


class UpdateDefaultSummaryTemplateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    template_key: str = Field(min_length=1, max_length=120)
    template_id: UUID | None = None
    template_version: int = Field(ge=1)


class CreateSummaryCandidateRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    template_key: str = Field(min_length=1, max_length=120)
    template_id: UUID | None = None
    template_version: int = Field(ge=1)
    expected_current_outcome_set_id: UUID | None = None
    request_intent: Annotated[SafeClientText, Field(max_length=64)] = "manual_format"
    request_intent_id: UUID | None = None

    @field_validator("request_intent")
    @classmethod
    def validate_request_intent(cls, value: str) -> str:
        if value not in {"manual_format", "manual_refresh"}:
            raise ValueError("unsupported summary request intent")
        return value

    @model_validator(mode="after")
    def require_refresh_intent_id(self) -> Self:
        if self.request_intent == "manual_refresh" and self.request_intent_id is None:
            raise ValueError("manual refresh requires request_intent_id")
        if self.request_intent == "manual_format" and self.request_intent_id is not None:
            raise ValueError("manual format must not include request_intent_id")
        return self


class SummaryCandidateProvenance(BaseModel):
    source_result_id: UUID | None = None
    media_revision_id: UUID | None = None
    source_revision_label: Annotated[SafeClientText, Field(max_length=160)] | None = None
    template_id: UUID | None = None
    source_result_hash: Annotated[SafeClientText, Field(max_length=128)] | None = None
    template_key: Annotated[SafeClientText, Field(max_length=120)] | None = None
    template_version: int | None = Field(default=None, ge=1)
    generator_version: Annotated[SafeClientText, Field(max_length=120)] | None = None


class SummaryCandidatePreviewItem(BaseModel):
    category: SummarySection
    sequence: int = Field(default=0, ge=0)
    text: str = ""
    owner_text: str = ""
    due_date_text: str = ""
    truth_label: str = ""
    source_refs: list["OutcomeSourceReferenceView"] = Field(default_factory=list, max_length=8)


class SummaryCandidateResponse(BaseModel):
    candidate_id: UUID
    state: SummaryCandidateProjectionState
    current_outcome_set_id: UUID | None = None
    poll_url: str
    outcome_set_id: UUID | None = None
    template_key: str | None = None
    template_name: str | None = None
    template_id: UUID | None = None
    template_version: int | None = None
    reason_code: SummaryCandidateReasonCode | None = None
    retryable: bool = False
    next_action: SummaryCandidateNextAction | None = None
    format_name: Annotated[SafeClientText, Field(max_length=120)] | None = None
    expires_at: datetime | None = None
    provenance: SummaryCandidateProvenance | None = None


class SummaryCandidateListResponse(BaseModel):
    candidates: list[SummaryCandidateResponse] = Field(default_factory=list, max_length=8)


class CreateScopedShareGrantRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    audience_type: ShareAudienceType = "user"
    audience_id: UUID | None = None
    content_scope: ShareContentScope = "summary_only"
    can_download: bool = False
    can_export: bool = False
    expires_at: datetime | None = None

    @model_validator(mode="after")
    def require_matching_audience_identity(self) -> Self:
        if self.audience_type == "link" and self.audience_id is not None:
            raise ValueError("link audience must not include audience_id")
        if self.audience_type != "link" and self.audience_id is None:
            raise ValueError("non-link audience requires audience_id")
        return self


class CreateMeetingShareInvitationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    address: str = Field(min_length=3, max_length=320)
    content_scope: ShareContentScope = "summary_only"
    can_download: bool = False
    can_export: bool = False

    @field_validator("address")
    @classmethod
    def validate_delivery_address(cls, value: str) -> str:
        normalized = value.strip().lower()
        local, separator, domain = normalized.rpartition("@")
        if not separator or not local or "." not in domain or domain.startswith("."):
            raise ValueError("invalid delivery address")
        return normalized

    @model_validator(mode="after")
    def require_complete_external_scope(self) -> Self:
        if self.content_scope == "summary_only" and (self.can_download or self.can_export):
            raise ValueError("summary invitations cannot include recording artifacts")
        if self.content_scope == "full_meeting" and (not self.can_download or not self.can_export):
            raise ValueError("recording invitations require download and export access")
        return self


class MeetingShareInvitationResponse(BaseModel):
    invitation_id: UUID
    status: ShareInvitationStatus
    expires_at: datetime


class ShareRecipientView(BaseModel):
    user_id: UUID
    display_label: str
    source: ShareRecipientSource = "workspace"
    recipient_type: ShareRecipientType = "workspace_member"
    freshness: ShareRecipientFreshness = "current"


class ShareRecipientListResponse(BaseModel):
    items: list[ShareRecipientView] = Field(default_factory=list, max_length=20)


class PublicShareSummaryResponse(BaseModel):
    meeting_label: str
    occurred_at: datetime
    duration_seconds: int = Field(ge=0)
    summary_sections: list[dict[str, object]] = Field(default_factory=list, max_length=100)


class MeetingAccessState(BaseModel):
    state: AccessState
    label: str
    reason: str | None = None
    can_view: bool
    can_share: bool
    can_manage_team_visibility: bool
    can_download: bool
    can_export: bool
    content_scope: ShareContentScope = "full_meeting"
    can_view_full_meeting: bool = True


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
    audience_type: ShareAudienceType = "user"
    content_scope: ShareContentScope = "summary_only"
    expires_at: datetime | None = None


class ShareInvitationView(BaseModel):
    invitation_id: UUID
    status: ShareInvitationStatus
    created_at: datetime
    expires_at: datetime
    content_scope: ShareContentScope = "summary_only"
    display_label: str = "Приглашение"


class SharePanelState(BaseModel):
    team_visibility: TeamVisibilityState
    active_grants: list[ShareGrantView] = Field(default_factory=list)
    active_invitations: list[ShareInvitationView] = Field(default_factory=list)
    copy_link_state: CopyLinkState
    public_link_state: PublicLinkState
    capability_state: ShareCapabilityState = "available"
    capability_reason: str | None = None
    external_invitation_state: ExternalInvitationState = "disabled"
    recipient_sources: list[Literal["workspace", "calendar"]] = Field(
        default_factory=lambda: ["workspace"]
    )


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
    model_config = ConfigDict(extra="forbid")

    grantee_user_id: UUID | None = None
    audience_type: ShareAudienceType = "user"
    audience_id: UUID | None = None
    content_scope: ShareContentScope = "summary_only"
    can_download: bool = False
    can_export: bool = False
    expires_at: datetime | None = None

    @model_validator(mode="after")
    def normalize_legacy_recipient(self) -> Self:
        if self.grantee_user_id is not None:
            if self.audience_id is not None and self.audience_id != self.grantee_user_id:
                raise ValueError("recipient identifiers must match")
            self.audience_id = self.grantee_user_id
        if self.audience_type == "link" and self.audience_id is not None:
            raise ValueError("link audience must not include audience_id")
        if self.audience_type != "link" and self.audience_id is None:
            raise ValueError("non-link audience requires audience_id")
        return self


class ShareGrantResponse(BaseModel):
    grant: ShareGrantView
    share_url: str
    notification_status: Literal[
        "sent", "not_available", "failed", "outcome_unknown", "not_attempted"
    ] = "not_attempted"


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


class ContentExportSelectionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    content_scope: ContentExportScope
    format: ContentExportFormat
    processing_result_id: UUID
    outcome_set_id: UUID | None = None
    include_speaker_labels: bool = True
    include_timestamps: bool = True
    include_evidence: bool = True

    @model_validator(mode="before")
    @classmethod
    def reject_unknown_export_format(cls, value: Any) -> Any:
        if isinstance(value, dict):
            format_name = value.get("format")
            if format_name not in CONTENT_EXPORT_FORMATS:
                raise ProblemDetail(
                    status=422,
                    code="unsupported_export_format",
                    title="Unsupported export format",
                )
        return value

    @model_validator(mode="after")
    def validate_scope_format_compatibility(self) -> Self:
        if self.format not in CONTENT_EXPORT_FORMATS_BY_SCOPE[self.content_scope]:
            raise ProblemDetail(
                status=422,
                code="unsupported_export_combination",
                title="Unsupported export combination",
            )
        summary_requested = self.content_scope in {"summary", "combined"}
        if summary_requested != (self.outcome_set_id is not None):
            raise ProblemDetail(
                status=422,
                code="invalid_export_selection",
                title="Invalid export selection",
            )
        return self


class ContentExportReadiness(BaseModel):
    state: ContentExportReadinessState
    reason: str | None = None


class ContentExportDefaults(BaseModel):
    include_speaker_labels: bool = True
    include_timestamps: bool = True
    include_evidence: bool = True


class ContentExportCapabilityResponse(BaseModel):
    processing_result_id: UUID | None = None
    outcome_set_id: UUID | None = None
    transcript: ContentExportReadiness
    summary: ContentExportReadiness
    combined: ContentExportReadiness
    formats: dict[ContentExportScope, list[ContentExportFormat]]
    defaults: ContentExportDefaults = Field(default_factory=ContentExportDefaults)
    language: str | None = None
    duration_seconds: int


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
    # Template identity is part of the server-authoritative summary format
    # state.  The key alone is not enough for personal template revisions.
    template_id: UUID | None = None
    version: int | None = Field(default=None, ge=1)
    template_version: int | None = Field(default=None, ge=1)


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
    seekable: bool = False


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


class PlaybackPreparationState(BaseModel):
    state: PlaybackPreparationStateValue = "unavailable"
    reason_code: PlaybackPreparationReasonCode = "no_audio"
    label: str = "Аудио недоступно"
    automatic_recovery: bool = False
    can_play: bool = False
    action: Literal["disabled"] = "disabled"


class MeetingListItem(BaseModel):
    meeting_id: UUID
    title: str
    started_at: datetime | None = None
    uploaded_at: datetime | None = None
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
    calendar_context: MeetingCalendarContextSummary | None = None
    previous_recurring_meeting: PreviousRecurringMeetingView | None = None
    playback: PlaybackPreparationState = Field(default_factory=PlaybackPreparationState)
    future_slots: list[SlotState] = Field(default_factory=list)
    _presentation_meeting_status: str | None = PrivateAttr(default=None)


class MeetingListResponse(BaseModel):
    items: list[MeetingListItem]
    filters: MeetingFilterState
    generated_at: datetime
    _has_more: bool = PrivateAttr(default=False)


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
    speaker_key: str = ""
    attribution_state: Literal["confirmed", "unconfirmed", "unknown", "mixed", "uncertain"] = (
        "unknown"
    )
    result_state: Literal["accepted", "degraded_provider_result"] = "accepted"
    provider_speaker_key: str | None = None
    processing_result_id: UUID | None = None
    source_role_original: str | None = Field(default=None, exclude=True)
    confidence_label: str | None = None
    seekable: bool = False
    seek_seconds: float | None = None


class TranscriptSpeakerTurnView(BaseModel):
    turn_id: str
    sequence: int
    start_seconds: float
    end_seconds: float
    timestamp_label: str
    speaker_label: str
    source_role: SourceRoleView
    text: str
    speaker_key: str = ""
    attribution_state: Literal["confirmed", "unconfirmed", "unknown", "mixed", "uncertain"] = (
        "unknown"
    )
    result_state: Literal["accepted", "degraded_provider_result"] = "accepted"
    provider_speaker_key: str | None = None
    processing_result_id: UUID | None = None
    source_segment_ids: list[str] = Field(default_factory=list)
    overlap: bool = False
    confidence_label: str | None = None
    seekable: bool = False
    seek_seconds: float | None = None


class TranscriptReviewState(BaseModel):
    available: bool
    language: str | None = None
    degraded_reason: str | None = None
    search_enabled: bool = False
    segments: list[TranscriptSegmentView] = Field(default_factory=list)
    speaker_turns: list[TranscriptSpeakerTurnView] = Field(default_factory=list)
    result_state: Literal["accepted", "degraded_provider_result"] = "accepted"


class SpeakerLaneSegment(BaseModel):
    start_seconds: float
    end_seconds: float


class SpeakerLane(BaseModel):
    speaker_key: str
    label: str
    display_name: str | None = None
    talk_time_percent: int = Field(ge=0, le=100)
    source_roles: list[SourceRoleView] = Field(default_factory=list)
    segments: list[SpeakerLaneSegment] = Field(default_factory=list)
    confidence_label: str | None = None
    provider_speaker_key: str | None = None
    confirmed: bool = True
    can_rename: bool = True


class SpeakerReviewState(BaseModel):
    available: bool
    assignment_state: Literal["available", "reserved", "disabled", "conflict_future", "unavailable"]
    degraded_reason: str | None = None
    turns: list[TranscriptSpeakerTurnView] = Field(default_factory=list)
    speakers: list[SpeakerLane] = Field(default_factory=list)
    can_rename: bool = False
    result_state: Literal["accepted", "degraded_provider_result"] = "accepted"
    talk_time_label: str = "Доля распознанной речи"


class CalendarRosterParticipantView(CalendarRosterSnapshotItem):
    pass


class CalendarRosterReviewState(BaseModel):
    model_config = ConfigDict(extra="forbid")

    available: bool = False
    roster_state: CalendarContextRosterState = CalendarContextRosterState.NOT_AVAILABLE
    participant_count: int = Field(default=0, ge=0)
    source: Literal["calendar", "none"] = "none"
    participants: list[CalendarRosterParticipantView] = Field(default_factory=list, max_length=100)


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


class PlaybackReviewState(PlaybackPreparationState):
    available: bool = False
    duration_seconds: int = Field(default=0, ge=0)
    speed_options: list[float] = Field(default_factory=lambda: [0.75, 1.0, 1.25, 1.5, 2.0])
    unavailable_reason: PlaybackUnavailableReason = "none"
    playback_path: str | None = None
    policy_label: str = "Аудио недоступно"
    source_mode: PlaybackSourceMode = "none"
    included_sources: list[SourceRoleView] = Field(default_factory=list)

    @model_validator(mode="after")
    def align_legacy_playback_fields(self) -> Self:
        # Older internal callers construct the review model with `available`.
        # Keep that compatibility while the durable API truth is `can_play`.
        if self.available and not self.can_play:
            self.can_play = True
            self.state = "available"
            self.reason_code = "canonical_ready"
        elif self.can_play and not self.available:
            self.available = True
        if self.policy_label != "Аудио недоступно" and self.label == "Аудио недоступно":
            self.label = self.policy_label
        return self


class MeetingReviewResponse(BaseModel):
    meeting: MeetingListItem
    calendar_context: MeetingCalendarContextSummary | None = None
    calendar_context_detail: MeetingCalendarContextResponse | None = None
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
    content_exports: ContentExportCapabilityResponse | None = None
    activity: MeetingActivityResponse | None = None
    deletion_truth_copy: str | None = None
    assistant: SlotState
    template: SlotState
