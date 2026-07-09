from __future__ import annotations

from collections.abc import Mapping
from uuid import UUID

from twobrain_rec_server.observability.redaction import redact_mapping

ALLOWED_AUDIT_KEYS = {
    "attempt_count",
    "blocked_count",
    "dependency",
    "diagnostic_class",
    "diarization_segment_count",
    "duration_seconds",
    "error_code",
    "error_origin",
    "event",
    "external_job_id_present",
    "failure_reason",
    "failure_source",
    "meeting_id",
    "mediascribe_job_id",
    "poll_attempt",
    "reason_code",
    "result_version",
    "reused_count",
    "segment_count",
    "started_count",
    "state",
    "status",
    "summary_status",
    "transcript_status",
    "transcript_reason",
    "workflow_id",
    "workspace_id",
}

SAFE_TRANSCRIPT_METADATA_VALUES = {
    "transcript_status": {"available", "unavailable"},
    "transcript_reason": {"no_recognizable_speech", None},
}

DENIED_ACCESS_AUDIT_KEYS = {
    "request_class",
    "feature_area",
    "reason_category",
    "validation_outcome",
}


def safe_audit_metadata(values: Mapping[str, object]) -> dict[str, object]:
    """Return metadata allowed for logs/audit without content-bearing fields."""
    sanitized: dict[str, object] = {}
    for key, value in values.items():
        if key not in ALLOWED_AUDIT_KEYS:
            continue
        if isinstance(value, UUID):
            sanitized[key] = str(value)
        else:
            sanitized[key] = value
    redacted = redact_mapping(sanitized)
    for key, allowed_values in SAFE_TRANSCRIPT_METADATA_VALUES.items():
        if key in sanitized and sanitized[key] in allowed_values:
            redacted[key] = sanitized[key]
    return redacted


def safe_denied_access_metadata(**values: object) -> dict[str, object]:
    return redact_mapping(
        {
            key: value
            for key, value in values.items()
            if key in DENIED_ACCESS_AUDIT_KEYS
        }
    )
