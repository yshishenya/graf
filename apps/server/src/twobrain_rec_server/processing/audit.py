from __future__ import annotations

from collections.abc import Mapping
from uuid import UUID

from twobrain_rec_server.observability.redaction import redact_mapping

ALLOWED_AUDIT_KEYS = {
    "attempt_count",
    "blocked_count",
    "dependency",
    "diarization_segment_count",
    "duration_seconds",
    "event",
    "external_job_id_present",
    "meeting_id",
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
    "workflow_id",
    "workspace_id",
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
    return redact_mapping(sanitized)


def safe_denied_access_metadata(**values: object) -> dict[str, object]:
    return redact_mapping(
        {
            key: value
            for key, value in values.items()
            if key in DENIED_ACCESS_AUDIT_KEYS
        }
    )
