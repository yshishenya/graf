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
