from enum import StrEnum


class MeetingStatus(StrEnum):
    DRAFT = "draft"
    UPLOADING = "uploading"
    INGESTED_PENDING_PROCESSING = "ingested_pending_processing"
    DEGRADED = "degraded"
    FAILED = "failed"
    ABORTED = "aborted"
    EXPIRED = "expired"


class UploadSessionStatus(StrEnum):
    PENDING = "pending"
    UPLOADING = "uploading"
    RETRYING = "retrying"
    FINALIZING = "finalizing"
    FINALIZED = "finalized"
    DEGRADED = "degraded"
    FAILED = "failed"
    ABORTED = "aborted"
    EXPIRED = "expired"


class MediaRevisionStatus(StrEnum):
    PENDING_UPLOAD = "pending_upload"
    UPLOADING = "uploading"
    ACCEPTED = "accepted"
    BLOCKED = "blocked"
    SUPERSEDED = "superseded"
    DELETED = "deleted"


class MediaRevisionSourceKind(StrEnum):
    INITIAL_RECORDING = "initial_recording"
    MANUAL_UPLOAD = "manual_upload"
    LOCAL_TRIM = "local_trim"
    VIDEO_CAPTURE = "video_capture"
    REPLACE = "replace"
    RESTORE = "restore"
    REPROCESS = "reprocess"


class SyncConflictState(StrEnum):
    NONE = "none"
    LOCAL_FILES_MISSING = "local_files_missing"
    LOCAL_CHECKSUM_CHANGED = "local_checksum_changed"
    QUEUE_DOCUMENT_MALFORMED = "queue_document_malformed"
    QUEUE_SCHEMA_MIGRATION_BLOCKED = "queue_schema_migration_blocked"
    SERVER_MEETING_DELETED = "server_meeting_deleted"
    ACCESS_REVOKED = "access_revoked"
    AUTH_REQUIRED = "auth_required"
    STALE_DEVICE_IDENTITY = "stale_device_identity"
    SERVER_EXPECTED_METADATA_MISMATCH = "server_expected_metadata_mismatch"
    SERVER_RANGES_INCONSISTENT = "server_ranges_inconsistent"
    UPLOAD_SESSION_EXPIRED = "upload_session_expired"
    PROCESSING_FAILED = "processing_failed"
    PROCESSING_BLOCKED = "processing_blocked"
    RETENTION_EXPIRED = "retention_expired"
    DEPENDENCY_UNAVAILABLE = "dependency_unavailable"


class CustodyState(StrEnum):
    SERVER_REGISTERED = "server_registered"
    UPLOAD_SESSION_CREATED = "upload_session_created"
    PARTIAL_UPLOADED = "partial_uploaded"
    FINALIZED = "finalized"
    PROCESSING = "processing"
    DELIVERED = "delivered"
    RETAINED_AWAITING_CONDITION = "retained_awaiting_condition"
    CANNOT_SEND = "cannot_send"
    TERMINAL_UNDELIVERED = "terminal_undelivered"


class CustodyUploadState(StrEnum):
    NOT_STARTED = "not_started"
    SESSION_CREATED = "session_created"
    PARTIAL_UPLOADED = "partial_uploaded"
    FINALIZED = "finalized"
    BLOCKED = "blocked"
    TERMINAL = "terminal"


class CustodyProcessingState(StrEnum):
    NOT_SUBMITTED = "not_submitted"
    PENDING_PROCESSING = "pending_processing"
    PROCESSING = "processing"
    PROCESSED = "processed"
    BLOCKED = "blocked"
    FAILED_RETRYABLE = "failed_retryable"
    FAILED_TERMINAL = "failed_terminal"
    CANCELED = "canceled"


class CustodyOwner(StrEnum):
    PRODUCT_AUTOMATIC = "product_automatic"
    MEETING_OWNER = "meeting_owner"
    WORKSPACE_ADMIN = "workspace_admin"
    SUPPORT = "support"
    POLICY_LIFECYCLE = "policy_lifecycle"


class CustodyRetryClass(StrEnum):
    AUTOMATIC = "automatic"
    PAUSED_UNTIL_USER_ACTION = "paused_until_user_action"
    PAUSED_UNTIL_ADMIN_ACTION = "paused_until_admin_action"
    NOT_RETRYABLE = "not_retryable"
    TERMINAL = "terminal"


class CustodyNormalUserAction(StrEnum):
    NONE = "none"
    SIGN_IN = "sign_in"
    CHOOSE_WORKSPACE = "choose_workspace"
    GRANT_PERMISSION = "grant_permission"
    OPEN_REVIEW = "open_review"
    OPEN_DIAGNOSTICS = "open_diagnostics"
    COPY_SAFE_REPORT = "copy_safe_report"
    DELETE_LOCAL_COPY = "delete_local_copy"


class CustodyMetadataSafety(StrEnum):
    METADATA_ONLY = "metadata_only"


class ProcessingStatus(StrEnum):
    NOT_SUBMITTED = "not_submitted"
    PENDING_PROCESSING = "pending_processing"
    STARTING = "starting"
    WORKFLOW_STARTED = "workflow_started"
    SUBMITTING = "submitting"
    SUBMITTED = "submitted"
    POLLING = "polling"
    IMPORTING = "importing"
    PROCESSED = "processed"
    BLOCKED = "blocked"
    FAILED_RETRYABLE = "failed_retryable"
    FAILED_TERMINAL = "failed_terminal"
    CANCELED = "canceled"


class MediaScribeJobStatus(StrEnum):
    NOT_SUBMITTED = "not_submitted"
    SUBMITTED = "submitted"
    UPLOADED = "uploaded"
    TRANSCRIBING = "transcribing"
    DIARIZING = "diarizing"
    SUMMARIZING = "summarizing"
    READY = "ready"
    FAILED = "failed"
    BLOCKED = "blocked"


class ProcessingResultStatus(StrEnum):
    IMPORTING = "importing"
    IMPORTED = "imported"
    PARTIAL = "partial"
    FAILED = "failed"


class ProcessingAvailabilityStatus(StrEnum):
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    FAILED = "failed"


class SummaryStatus(StrEnum):
    NOT_REQUESTED = "not_requested"
    AVAILABLE = "available"
    UNAVAILABLE = "unavailable"
    FAILED = "failed"


class OutcomeCategory(StrEnum):
    SUMMARY = "summary"
    KEY_POINTS = "key_points"
    DECISIONS = "decisions"
    ACTION_ITEMS = "action_items"
    FOLLOWUPS = "followups"
    RISKS = "risks"
    QUESTIONS = "questions"
    EVIDENCE = "evidence"


class OutcomeCategoryState(StrEnum):
    AVAILABLE = "available"
    NOT_FOUND = "not_found"
    NOT_INFERABLE = "not_inferable"
    PROCESSING = "processing"
    BLOCKED = "blocked"
    UNSAFE = "unsafe"
    UNAVAILABLE = "unavailable"


class OutcomeSetStatus(StrEnum):
    QUEUED = "queued"
    GENERATING = "generating"
    AVAILABLE = "available"
    PARTIAL = "partial"
    BLOCKED = "blocked"
    FAILED = "failed"
    UNSAFE = "unsafe"


class OutcomeSourceKind(StrEnum):
    STORED_OUTPUT = "stored_output"
    EXTRACTIVE_GENERATOR = "extractive_generator"
    MEDIASCRIBE_SUMMARY = "mediascribe_summary"
    PROVIDER_OUTPUT = "provider_output"
    NOT_INFERABLE = "not_inferable"
    BLOCKED = "blocked"


class OutcomeGeneratorKind(StrEnum):
    DETERMINISTIC_EXTRACTIVE = "deterministic_extractive"
    MEDIASCRIBE_SUMMARY = "mediascribe_summary"
    LLM_PROVIDER = "llm_provider"
    MANUAL_FIXTURE = "manual_fixture"


class OutcomeTruthLabel(StrEnum):
    SUPPORTED = "supported"
    NOT_FOUND = "not_found"
    NOT_INFERABLE = "not_inferable"
    UNSAFE = "unsafe"
    BLOCKED = "blocked"


class OutcomeLifecycleState(StrEnum):
    ACTIVE = "active"
    DELETING = "deleting"
    DELETED = "deleted"
    RETENTION_EXPIRED = "retention_expired"
    BLOCKED = "blocked"


class OutcomeGenerationAttemptStatus(StrEnum):
    QUEUED = "queued"
    GENERATING = "generating"
    STORED = "stored"
    PARTIAL = "partial"
    BLOCKED = "blocked"
    FAILED_RETRYABLE = "failed_retryable"
    FAILED_TERMINAL = "failed_terminal"
    UNSAFE = "unsafe"


class ProcessingDependencyName(StrEnum):
    TEMPORAL = "temporal"
    MEDIASCRIBE = "mediascribe"
    POSTGRES = "postgres"
    MINIO = "minio"
    LANGFUSE = "langfuse"


class ProcessingDependencyStateValue(StrEnum):
    NOT_CONTACTED = "not_contacted"
    SUBMITTED = "submitted"
    STORED = "stored"
    IMPORTED = "imported"
    FAILED = "failed"
    BLOCKED = "blocked"
    DELETION_PENDING_FUTURE = "deletion_pending_future"
    DELETE_NOT_SUPPORTED_UNKNOWN = "delete_not_supported_unknown"
    DELETED_FUTURE = "deleted_future"


class DeletionState(StrEnum):
    NONE = "none"
    REQUESTED = "requested"
    DELETING = "deleting"
    ACTIVE_PURGE_COMPLETE = "active_purge_complete"
    PENDING_BACKUP_EXPIRY = "pending_backup_expiry"
    COMPLETE = "complete"
    RETRYABLE_FAILED = "retryable_failed"
    TERMINAL_FAILED = "terminal_failed"
    POLICY_BLOCKED = "policy_blocked"
    POST_EGRESS_LIMIT = "post_egress_limit"
    LOCAL_PURGE_UNVERIFIED = "local_purge_unverified"


class RetentionPolicyState(StrEnum):
    NOT_CONFIGURED = "not_configured"
    ACTIVE = "active"
    UNSAFE = "unsafe"
    BLOCKED = "blocked"
    EXPIRED = "expired"


class RetentionPolicySource(StrEnum):
    DEPLOYMENT_DEFAULT = "deployment_default"
    WORKSPACE_DEFAULT = "workspace_default"
    TEST_FIXTURE = "test_fixture"


class DeletionRequestSource(StrEnum):
    OWNER = "owner"
    ADMIN = "admin"
    RETENTION_JOB = "retention_job"


class DeletionReasonCode(StrEnum):
    USER_REQUEST = "user_request"
    RETENTION_EXPIRED = "retention_expired"
    POLICY_BLOCKED = "policy_blocked"
    RETRY = "retry"


class DeletionArtifactClass(StrEnum):
    MEETING_ROW = "meeting_row"
    CALENDAR_CONTEXT = "calendar_context"
    MEDIA_REVISION = "media_revision"
    AUDIO_OBJECT = "audio_object"
    PLAYBACK_CANDIDATE = "playback_candidate"
    PLAYBACK_CANONICAL = "playback_canonical"
    NORMALIZATION_ATTEMPT_TEMP = "normalization_attempt_temp"
    NORMALIZATION_JOB = "normalization_job"
    NORMALIZATION_BACKFILL = "normalization_backfill"
    TRANSCRIPT = "transcript"
    DIARIZATION = "diarization"
    NOTES_SUMMARY = "notes_summary"
    EXPORT_PACKAGE = "export_package"
    SHARE_GRANT = "share_grant"
    UPLOAD_TEMP = "upload_temp"
    PROCESSING_WORKFLOW = "processing_workflow"
    MEDIASCRIBE = "mediascribe"
    LANGFUSE = "langfuse"
    DIAGNOSTICS = "diagnostics"
    BACKUP = "backup"
    LOCAL_DESKTOP_BUFFER = "local_desktop_buffer"
    POST_EGRESS_COPY = "post_egress_copy"
    SEARCH_INDEX = "search_index"


class DeletionControlScope(StrEnum):
    CONTROLLED = "controlled"
    EXTERNAL = "external"
    LOCAL_DEVICE = "local_device"
    BACKUP = "backup"
    POST_EGRESS = "post_egress"
    NOT_APPLICABLE = "not_applicable"


class DeletionArtifactState(StrEnum):
    NOT_STARTED = "not_started"
    PURGE_REQUESTED = "purge_requested"
    PURGED = "purged"
    METADATA_RETAINED = "metadata_retained"
    PENDING_EXPIRY = "pending_expiry"
    DELETE_REQUESTED = "delete_requested"
    DELETE_CONFIRMED = "delete_confirmed"
    DELETE_NOT_SUPPORTED = "delete_not_supported"
    UNKNOWN = "unknown"
    NOT_APPLICABLE = "not_applicable"
    RETRYABLE_FAILED = "retryable_failed"
    TERMINAL_FAILED = "terminal_failed"
    LOCAL_PENDING = "local_pending"
    LOCAL_ACKNOWLEDGED = "local_acknowledged"
    LOCAL_UNREACHABLE = "local_unreachable"
    LOCAL_EXPIRY_RELIED_UPON = "local_expiry_relied_upon"
    OUTSIDE_2BRAIN_CONTROL = "outside_2brain_control"


class LocalPurgeTaskType(StrEnum):
    PURGE_LOCAL_BUFFERS = "purge_local_buffers"
    PURGE_LOCAL_EXPORTS = "purge_local_exports"
    CONFIRM_LOCAL_EXPIRY = "confirm_local_expiry"


class LocalPurgeTaskState(StrEnum):
    PENDING = "pending"
    CLAIMED = "claimed"
    ACKNOWLEDGED = "acknowledged"
    FAILED = "failed"
    UNREACHABLE = "unreachable"
    EXPIRED = "expired"
    LOCAL_EXPIRY_RELIED_UPON = "local_expiry_relied_upon"


class LifecycleAuditOutcome(StrEnum):
    ACCEPTED = "accepted"
    DENIED = "denied"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"
    BLOCKED = "blocked"


class UploadStrategy(StrEnum):
    SERVER_MEDIATED = "server_mediated"


class TrackRole(StrEnum):
    MICROPHONE = "microphone"
    SYSTEM = "system"
    MEDIA = "media"
    MANIFEST = "manifest"
    PLAYBACK = "playback"


class DeviceStatus(StrEnum):
    ACTIVE = "active"
    REVOKED = "revoked"


class UserStatus(StrEnum):
    ACTIVE = "active"
    DISABLED = "disabled"


class CalendarCredentialState(StrEnum):
    PENDING = "pending"
    SEALED = "sealed"
    EXPIRED = "expired"
    REVOKED = "revoked"
    PURGED = "purged"
    INVALID = "invalid"


class CalendarConnectionState(StrEnum):
    ACTIVE = "active"
    DEGRADED = "degraded"
    NEEDS_REAUTH = "needs_reauth"
    DISABLED_BY_POLICY = "disabled_by_policy"
    DISCONNECTING = "disconnecting"
    DISCONNECTED = "disconnected"


class CalendarSyncState(StrEnum):
    NEVER_SYNCED = "never_synced"
    SYNCING = "syncing"
    SYNCED = "synced"
    PARTIAL = "partial"
    RATE_LIMITED = "rate_limited"
    PROVIDER_UNAVAILABLE = "provider_unavailable"
    FAILED_CLOSED = "failed_closed"


class CalendarLimitationState(StrEnum):
    SUPPORTED = "supported"
    UNSUPPORTED = "unsupported"
    NOT_RETURNED = "not_returned"
    PRIVATE_REDACTED = "private_redacted"
    FREE_BUSY_ONLY = "free_busy_only"
    ADMIN_POLICY_DEPENDENT = "admin_policy_dependent"
    UNKNOWN = "unknown"
