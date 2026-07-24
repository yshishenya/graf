from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from types import MappingProxyType
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from twobrain_rec_server.db.models.ingest import IngestAuditEvent
from twobrain_rec_server.normalization.statuses import (
    CANONICAL_PROFILE_VERSION,
    VALIDATION_VERSION,
    BackfillState,
    JobState,
    NormalizationReason,
    PlannedAction,
    TriggerKind,
)

NORMALIZATION_AUDIT_EVENT_TYPES = frozenset(
    {
        "playback_normalization_requested",
        "playback_normalization_started",
        "playback_normalization_retried",
        "playback_normalization_retry_cycle_exhausted",
        "playback_normalization_incident_recorded",
        "playback_normalization_legacy_source_unavailable",
        "playback_normalization_publishing",
        "playback_normalization_completed",
        "playback_normalization_skipped",
        "playback_normalization_backfilled",
        "playback_normalization_duplicate_reused",
        "playback_normalization_failed",
        "playback_normalization_cancelled",
        "playback_normalization_temp_cleaned",
        "playback_backfill_inventory_planned",
        "playback_backfill_inventory_completed",
        "playback_backfill_completed",
    }
)

COUNTER_KEYS = frozenset(
    {
        "attempt_count",
        "retry_cycle_count",
        "cooldown_cycle",
        "stream_count",
        "audio_stream_count",
        "evaluated_count",
        "preserve_valid_count",
        "validate_candidate_count",
        "normalize_source_count",
        "unavailable_source_count",
        "ready_count",
        "terminal_count",
        "cancelled_count",
    }
)
TIMESTAMP_KEYS = frozenset(
    {
        "inventory_started_at",
        "inventory_completed_at",
        "completed_at",
    }
)
ALLOWED_METADATA_KEYS = frozenset(
    {
        "profile_version",
        "validation_version",
        "state",
        "reason_code",
        "trigger_kind",
        "planned_action",
        "duration_bucket",
        "byte_bucket",
        "full_decode_passed",
        "moov_before_mdat",
        "cleanup_result",
    }
    | COUNTER_KEYS
    | TIMESTAMP_KEYS
)

DURATION_BUCKETS = frozenset({"under_5m", "under_30m", "under_2h", "under_4h"})
BYTE_BUCKETS = frozenset(
    {"under_16mib", "under_128mib", "under_1gib", "under_2_5gib", "under_5gib"}
)
CLEANUP_RESULTS = frozenset(
    {
        "not_required",
        "deleted",
        "already_missing",
        "already_missing_pending_recheck",
        "deferred_retry",
    }
)
STATE_VALUES = frozenset(state.value for state in JobState) | frozenset(
    state.value for state in BackfillState
)

UNSAFE_TEXT_RE = re.compile(
    r"(?:^|\s)(?:/|~[/\\])|"
    r"(?:https?|s3|minio)://|"
    r"(?:bearer|token|password|credential|secret|stderr|stdout)\b|"
    r"\.(?:m4a|mp4|mov|wav|mp3|flac|ogg|opus|webm|mkv)(?:$|\s)",
    re.IGNORECASE,
)


class NormalizationAuditError(ValueError):
    """Normalization metadata was rejected without echoing private input."""


@dataclass(frozen=True, slots=True)
class NormalizationAuditReceipt:
    event_type: str
    metadata_json: Mapping[str, str | int | bool]


def _reject() -> None:
    raise NormalizationAuditError("Normalization audit metadata rejected")


def _safe_timestamp(value: object) -> str:
    if isinstance(value, datetime):
        parsed = value
    elif isinstance(value, str) and not UNSAFE_TEXT_RE.search(value):
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            _reject()
    else:
        _reject()
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        _reject()
    return parsed.isoformat()


def _safe_value(key: str, value: object) -> str | int | bool:
    if isinstance(value, dict | list | tuple | set) or value is None:
        _reject()
    if key in COUNTER_KEYS:
        if isinstance(value, bool) or not isinstance(value, int) or value < 0:
            _reject()
        return value
    if key in TIMESTAMP_KEYS:
        return _safe_timestamp(value)
    if key in {"full_decode_passed", "moov_before_mdat"}:
        if not isinstance(value, bool):
            _reject()
        return value
    if not isinstance(value, str) or UNSAFE_TEXT_RE.search(value):
        _reject()

    allowed_values: dict[str, frozenset[str]] = {
        "profile_version": frozenset({CANONICAL_PROFILE_VERSION}),
        "validation_version": frozenset({VALIDATION_VERSION}),
        "state": STATE_VALUES,
        "reason_code": frozenset(reason.value for reason in NormalizationReason),
        "trigger_kind": frozenset(kind.value for kind in TriggerKind),
        "planned_action": frozenset(action.value for action in PlannedAction),
        "duration_bucket": DURATION_BUCKETS,
        "byte_bucket": BYTE_BUCKETS,
        "cleanup_result": CLEANUP_RESULTS,
    }
    if value not in allowed_values[key]:
        _reject()
    return value


def _validate_event_requirements(event_type: str, metadata: Mapping[str, object]) -> None:
    required: dict[str, frozenset[str]] = {
        "playback_normalization_completed": frozenset(
            {
                "profile_version",
                "state",
                "attempt_count",
                "full_decode_passed",
                "moov_before_mdat",
            }
        ),
        "playback_normalization_failed": frozenset({"reason_code"}),
        "playback_normalization_cancelled": frozenset({"reason_code"}),
        "playback_normalization_temp_cleaned": frozenset({"cleanup_result"}),
        "playback_normalization_incident_recorded": frozenset(
            {"reason_code", "cooldown_cycle"}
        ),
        "playback_normalization_legacy_source_unavailable": frozenset(
            {"reason_code", "trigger_kind", "planned_action"}
        ),
    }
    if not required.get(event_type, frozenset()) <= set(metadata):
        _reject()
    if event_type == "playback_normalization_completed" and metadata.get("state") != "ready":
        _reject()


def build_audit_receipt(
    event_type: str,
    metadata: Mapping[str, object],
) -> NormalizationAuditReceipt:
    if event_type not in NORMALIZATION_AUDIT_EVENT_TYPES:
        _reject()
    if not isinstance(metadata, Mapping) or not set(metadata) <= ALLOWED_METADATA_KEYS:
        _reject()
    safe_metadata = {key: _safe_value(key, value) for key, value in metadata.items()}
    _validate_event_requirements(event_type, safe_metadata)
    return NormalizationAuditReceipt(
        event_type=event_type,
        metadata_json=MappingProxyType(safe_metadata),
    )


def add_normalization_audit_event(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    event_type: str,
    metadata: Mapping[str, object],
    created_at: datetime,
    meeting_id: UUID | None = None,
    media_revision_id: UUID | None = None,
    actor_user_id: UUID | None = None,
    device_id: UUID | None = None,
) -> None:
    """Add one validated metadata-only event to the caller's transaction."""

    receipt = build_audit_receipt(event_type, metadata)
    db.add(
        IngestAuditEvent(
            workspace_id=workspace_id,
            meeting_id=meeting_id,
            media_revision_id=media_revision_id,
            actor_user_id=actor_user_id,
            device_id=device_id,
            event_type=receipt.event_type,
            metadata_json=dict(receipt.metadata_json),
            created_at=created_at,
        )
    )
