from __future__ import annotations

from collections.abc import Mapping
from uuid import UUID

from twobrain_rec_server.observability.redaction import redact_mapping
from twobrain_rec_server.processing import reasons

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

SAFE_AUDIT_METADATA_VALUES = {
    "error_code": {
        reasons.INVALID_AUDIO_PAYLOAD,
        reasons.MEDIASCRIBE_AUTH_FAILED,
        reasons.MEDIASCRIBE_JOB_FAILED,
        reasons.MEDIASCRIBE_MALFORMED_RESPONSE,
        reasons.MEDIASCRIBE_PAYLOAD_TOO_LARGE,
        reasons.MEDIASCRIBE_RATE_LIMITED,
        reasons.MEDIASCRIBE_SERVER_ERROR,
        reasons.MEDIASCRIBE_TIMEOUT,
        reasons.MEDIASCRIBE_VALIDATION_FAILED,
        None,
    },
    "error_origin": {reasons.FAILURE_SOURCE_INPUT_AUDIO, reasons.FAILURE_SOURCE_MEDIASCRIBE, None},
    "failure_reason": {
        reasons.INVALID_AUDIO_PAYLOAD,
        reasons.MEDIASCRIBE_AUTH_FAILED,
        reasons.MEDIASCRIBE_JOB_FAILED,
        reasons.MEDIASCRIBE_MALFORMED_RESPONSE,
        reasons.MEDIASCRIBE_PAYLOAD_TOO_LARGE,
        reasons.MEDIASCRIBE_RATE_LIMITED,
        reasons.MEDIASCRIBE_SERVER_ERROR,
        reasons.MEDIASCRIBE_TIMEOUT,
        reasons.MEDIASCRIBE_VALIDATION_FAILED,
        reasons.NO_RECOGNIZABLE_SPEECH,
        None,
    },
    "failure_source": {reasons.FAILURE_SOURCE_INPUT_AUDIO, reasons.FAILURE_SOURCE_MEDIASCRIBE, None},
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
    for key, allowed_values in SAFE_AUDIT_METADATA_VALUES.items():
        if key not in sanitized:
            continue
        if sanitized[key] in allowed_values:
            redacted[key] = sanitized[key]
        else:
            redacted[key] = "[REDACTED]"
    return redacted


def safe_denied_access_metadata(**values: object) -> dict[str, object]:
    return redact_mapping(
        {
            key: value
            for key, value in values.items()
            if key in DENIED_ACCESS_AUDIT_KEYS
        }
    )
