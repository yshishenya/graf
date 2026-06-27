from enum import StrEnum


class IngestFailureReason(StrEnum):
    MISSING_REQUIRED_TRACK = "missing_required_track"
    MANIFEST_VALIDATION_FAILED = "manifest_validation_failed"
    CHECKSUM_MISMATCH = "checksum_mismatch"
    CHECKSUM_CONFLICT = "checksum_conflict"
    STORAGE_UNAVAILABLE = "storage_unavailable"
    PARTIAL_OBJECT_WRITE = "partial_object_write"
    RECORDING_DURATION_EXCEEDED = "recording_duration_exceeded"
    TRACK_BYTES_EXCEEDED = "track_bytes_exceeded"
    PACKAGE_BYTES_EXCEEDED = "package_bytes_exceeded"
    SESSION_EXPIRED = "session_expired"
    USER_ABORTED = "user_aborted"


class CalendarSafeReason(StrEnum):
    INVALID_CREDENTIALS = "invalid_credentials"
    PROVIDER_TIMEOUT = "provider_timeout"
    RATE_LIMITED = "rate_limited"
    TENANT_POLICY_DENIED = "tenant_policy_denied"
    PROVIDER_UNAVAILABLE = "provider_unavailable"
    MALFORMED_PROVIDER_PAYLOAD = "malformed_provider_payload"
    CALENDAR_CONTEXT_UNAVAILABLE = "calendar_context_unavailable"
    PRIVATE_EVENT_REDACTED = "private_event_redacted"
