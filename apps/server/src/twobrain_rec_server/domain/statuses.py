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
