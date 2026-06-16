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
    AUDIO_OBJECT = "audio_object"
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
    MANIFEST = "manifest"


class DeviceStatus(StrEnum):
    ACTIVE = "active"
    REVOKED = "revoked"


class UserStatus(StrEnum):
    ACTIVE = "active"
    DISABLED = "disabled"
