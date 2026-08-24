from __future__ import annotations

import re
from collections.abc import Mapping
from datetime import datetime
from uuid import UUID

from twobrain_rec_server.domain.speaker_turns import SPEAKER_REASON_CODES
from twobrain_rec_server.observability.redaction import redact_mapping

ALLOWED_AUDIT_KEYS = {
    "attempt_count",
    "accepted_turn_count",
    "alignment_version",
    "attribution_result_state",
    "blocked_count",
    "dependency",
    "diagnostic_class",
    "defect_origin",
    "diarization_segment_count",
    "duration_seconds",
    "duplicate_text_count",
    "error_code",
    "error_origin",
    "event",
    "external_job_id_present",
    "failure_reason",
    "failure_source",
    "meeting_id",
    "mediascribe_job_id",
    "poll_attempt",
    "provider_build_version",
    "provider_job_id",
    "provider_model_version",
    "provider_result_version",
    "prompt_config_hash",
    "prompt_hash",
    "prompt_name",
    "prompt_source",
    "prompt_version",
    "reason_code",
    "reason_codes",
    "result_version",
    "schema_version",
    "reused_count",
    "raw_turn_count",
    "segment_count",
    "source_result_hash",
    "started_count",
    "state",
    "status",
    "summary_status",
    "text_conservation_status",
    "transcript_status",
    "transcript_reason",
    "unknown_tiny_count",
    "multi_label_conflict_count",
    "workflow_id",
    "workflow_run_id",
    "workspace_id",
}

ALLOWED_AUDIT_EVENT_TYPES = frozenset(
    {
        "summary_template_created",
        "summary_template_updated",
        "summary_template_archived",
        "summary_template_deleted",
        "summary_generation_requested",
        "summary_generation_started",
        "summary_generation_retried",
        "summary_generation_failed",
        "summary_generation_accepted",
        "summary_generation_rejected",
        "summary_generation_cancelled",
        "prompt_optimization_queued",
        "prompt_optimization_resumed",
        "prompt_optimization_candidate",
        "prompt_optimization_rejected",
        "prompt_optimization_promoted",
        "prompt_optimization_rolled_back",
        "share_granted",
        "share_updated",
        "share_revoked",
        "share_link_rotated",
        "share_link_expired",
        "share_link_revoked",
        "share_invitation_requested",
        "share_invitation_sent",
        "share_invitation_accepted",
        "share_invitation_failed",
        "share_invitation_revoked",
    }
)

SAFE_TRANSCRIPT_METADATA_VALUES = {
    "transcript_status": {"available", "unavailable"},
    "transcript_reason": {"no_recognizable_speech", None},
}
SAFE_ATTRIBUTION_VALUE_RE = re.compile(r"^[A-Za-z0-9_.:+-]{1,160}$")
URI_VALUE_RE = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*://")
LOCAL_PATH_VALUE_RE = re.compile(r"^(?:/|~(?:/|$)|[A-Za-z]:[/\\])")
SAFE_ATTRIBUTION_STRING_KEYS = {
    "alignment_version",
    "attribution_result_state",
    "defect_origin",
    "provider_build_version",
    "provider_job_id",
    "provider_model_version",
    "provider_result_version",
    "source_result_hash",
    "text_conservation_status",
}

DENIED_ACCESS_AUDIT_KEYS = {
    "request_class",
    "feature_area",
    "reason_category",
    "validation_outcome",
}

PROCESSING_ANALYTICS_EVENTS = frozenset(
    {
        "processing_attempt_started",
        "processing_first_usable_transcript",
        "processing_retry_scheduled",
        "processing_retry_completed",
        "processing_reconciliation_completed",
        "processing_manual_check_requested",
        "processing_manual_check_completed",
        "processing_terminal_outcome",
        "processing_support_handoff",
        "processing_surface_parity_observed",
    }
)
PROCESSING_ANALYTICS_SURFACES = frozenset(
    {"server", "web_list", "web_detail", "embedded_desktop_detail", "contract_test"}
)
PROCESSING_ANALYTICS_DIMENSION_KEYS = frozenset(
    {
        "attempt_kind", "media_size_bucket", "track_mode", "latency_bucket",
        "summary_state_at_ready", "playback_state_at_ready", "retry_reason",
        "schedule_source", "delay_bucket", "retry_count_bucket", "retry_outcome",
        "same_key_reused", "new_attempt_created", "reconciliation_outcome",
        "request_result", "same_job_check", "claim_result", "check_outcome",
        "timer_superseded", "terminal_category", "next_action", "artifact_preserved",
        "handoff_reason", "handoff_state", "fixture_class", "parity_result",
        "projection_contract_version", "mismatch_reason",
    }
)
_ANALYTICS_REQUIRED_DIMENSIONS = {
    "processing_attempt_started": {"attempt_kind", "media_size_bucket", "track_mode"},
    "processing_first_usable_transcript": {
        "latency_bucket", "attempt_kind", "media_size_bucket", "track_mode",
        "summary_state_at_ready", "playback_state_at_ready",
    },
    "processing_retry_scheduled": {"retry_reason", "schedule_source", "delay_bucket", "retry_count_bucket"},
    "processing_retry_completed": {
        "retry_outcome", "attempt_kind", "latency_bucket", "same_key_reused", "new_attempt_created",
    },
    "processing_reconciliation_completed": {"reconciliation_outcome", "attempt_kind", "latency_bucket"},
    "processing_manual_check_requested": {"request_result", "same_job_check"},
    "processing_manual_check_completed": {"claim_result", "check_outcome", "latency_bucket", "timer_superseded"},
    "processing_terminal_outcome": {"terminal_category", "next_action", "artifact_preserved"},
    "processing_support_handoff": {"handoff_reason", "handoff_state", "artifact_preserved"},
    "processing_surface_parity_observed": {
        "fixture_class", "parity_result", "projection_contract_version",
    },
}
_ANALYTICS_ENUMS = {
    "attempt_kind": {"initial", "automatic_retry", "manual_check", "same_key_reconciliation", "worker_resume"},
    "media_size_bucket": {"under_10mb", "10mb_100mb", "100mb_1gb", "over_1gb", "unknown"},
    "track_mode": {"single", "dual", "unknown"},
    "latency_bucket": {"under_30s", "30s_2m", "2m_5m", "5m_15m", "15m_30m", "30m_2h", "over_2h", "unknown"},
    "summary_state_at_ready": {"not_requested", "queued", "running", "available", "failed", "unavailable", "unknown"},
    "playback_state_at_ready": {"not_requested", "queued", "running", "available", "failed", "unavailable", "unknown"},
    "retry_reason": {"result_not_ready", "temporary_unavailable", "transport", "bounded_fallback", "deadline_window", "unknown"},
    "schedule_source": {"external_hint", "server_fallback", "manual_override", "unknown"},
    "delay_bucket": {"under_30s", "30s_2m", "2m_15m", "15m_1h", "over_1h", "unknown"},
    "retry_count_bucket": {"first", "second", "third_plus", "unknown"},
    "retry_outcome": {"first_usable_transcript", "artifact_progress", "still_retryable", "terminal", "support_handoff", "unknown"},
    "reconciliation_outcome": {"same_key_job_confirmed", "same_key_conflict_blocked", "no_safe_linkage", "support_handoff"},
    "request_result": {"accepted", "already_in_flight", "stale_schedule", "duplicate_suppressed", "not_safe"},
    "claim_result": {"claimed_once", "already_in_flight", "stale_noop", "duplicate_suppressed"},
    "check_outcome": {"first_usable_transcript", "artifact_progress", "still_retryable", "terminal", "support_handoff", "unknown"},
    "terminal_category": {"invalid_input", "unsupported_media", "processing_failure", "deadline_exhausted", "configuration", "deletion_closed", "unknown"},
    "next_action": {"new_attempt", "contact_support", "operator_action", "none"},
    "handoff_reason": {"terminal_processing", "unknown_outcome", "deletion_pending", "configuration", "no_safe_retry"},
    "handoff_state": {"offered", "accepted", "submitted", "unavailable"},
    "fixture_class": {"transcript_pending_diarization", "transcript_ready_summary_running", "retryable_waiting", "manual_in_flight", "terminal_support", "deletion_pending"},
    "parity_result": {"match", "mismatch"},
}
_ANALYTICS_BOOLEAN_DIMENSIONS = {"same_key_reused", "new_attempt_created", "same_job_check", "timer_superseded", "artifact_preserved"}


def validate_processing_aggregate_event(
    *,
    event_name: str,
    window: str,
    window_started_at: str,
    window_ended_at: str,
    surface: str,
    count: int,
    dimensions: Mapping[str, object],
) -> dict[str, object]:
    """Validate the strict, metadata-only Feature 195 rollup envelope."""

    if event_name not in PROCESSING_ANALYTICS_EVENTS:
        raise ValueError("unknown_processing_analytics_event")
    if window not in {"hour", "day"} or surface not in PROCESSING_ANALYTICS_SURFACES:
        raise ValueError("invalid_processing_analytics_window_or_surface")
    if count < 1:
        raise ValueError("processing_analytics_count_must_be_positive")
    try:
        started = datetime.fromisoformat(window_started_at.replace("Z", "+00:00"))
        ended = datetime.fromisoformat(window_ended_at.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("invalid_processing_analytics_timestamp") from exc
    if started.tzinfo is None or ended.tzinfo is None or ended < started:
        raise ValueError("invalid_processing_analytics_window")
    required = _ANALYTICS_REQUIRED_DIMENSIONS[event_name]
    if not required.issubset(dimensions) or set(dimensions) - PROCESSING_ANALYTICS_DIMENSION_KEYS:
        raise ValueError("invalid_processing_analytics_dimensions")
    for key, value in dimensions.items():
        if key in _ANALYTICS_BOOLEAN_DIMENSIONS:
            if not isinstance(value, bool):
                raise ValueError("invalid_processing_analytics_boolean")
        elif key == "projection_contract_version":
            if value not in {"processing-status-v1"}:
                raise ValueError("invalid_processing_analytics_contract_version")
        elif key in _ANALYTICS_ENUMS and value not in _ANALYTICS_ENUMS[key]:
            raise ValueError("invalid_processing_analytics_dimension_value")
    if dimensions.get("parity_result") == "mismatch" and "mismatch_reason" not in dimensions:
        raise ValueError("processing_analytics_mismatch_reason_required")
    return {
        "schema_version": 1,
        "event_name": event_name,
        "window": window,
        "window_started_at": window_started_at,
        "window_ended_at": window_ended_at,
        "surface": surface,
        "count": count,
        "dimensions": dict(dimensions),
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
    for key in SAFE_ATTRIBUTION_STRING_KEYS:
        value = sanitized.get(key)
        if (
            isinstance(value, str)
            and SAFE_ATTRIBUTION_VALUE_RE.fullmatch(value)
            and URI_VALUE_RE.match(value) is None
            and LOCAL_PATH_VALUE_RE.match(value) is None
        ):
            redacted[key] = value
        elif key in sanitized:
            redacted[key] = "[REDACTED]"
    reason_codes = sanitized.get("reason_codes")
    if (
        isinstance(reason_codes, (list, tuple))
        and all(isinstance(code, str) and code in SPEAKER_REASON_CODES for code in reason_codes)
    ):
        redacted["reason_codes"] = list(reason_codes)
    else:
        redacted.pop("reason_codes", None)
    return redacted


def safe_denied_access_metadata(**values: object) -> dict[str, object]:
    return redact_mapping(
        {key: value for key, value in values.items() if key in DENIED_ACCESS_AUDIT_KEYS}
    )
