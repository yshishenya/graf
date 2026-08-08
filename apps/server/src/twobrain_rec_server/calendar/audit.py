from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from twobrain_rec_server.db.models import CalendarAuditEvent
from twobrain_rec_server.observability.redaction import redact_mapping

CALENDAR_MATCH_AUDIT_OUTCOMES = frozenset(
    {
        "matched_auto",
        "matched_user",
        "provisional_prestart",
        "no_context",
        "ambiguous",
        "skipped_private",
        "skipped_all_day",
        "skipped_manual_upload",
        "skipped_offline_or_unknown",
        "skipped_stale_calendar",
        "calendar_unavailable",
        "declined_by_user",
        "cleared_by_user",
    }
)

CALENDAR_MATCH_AUDIT_REASONS = frozenset(
    {
        "single_fresh_candidate",
        "multiple_time_candidates",
        "back_to_back_boundary",
        "no_matching_event",
        "weak_event_signal",
        "private_free_busy_skipped",
        "all_day_skipped",
        "selected_source_stale",
        "latest_sync_failed",
        "calendar_not_connected",
        "calendar_not_selected",
        "calendar_unavailable",
        "manual_upload_skipped",
        "offline_or_unknown_skipped",
        "prestart_not_reached",
        "user_selected",
        "user_declined",
        "user_cleared",
        "meeting_deleted",
    }
)

_CALENDAR_MATCH_FRESHNESS_CLASSES = frozenset(
    {"current", "stale", "latest_sync_failed", "never_synced", "unavailable"}
)
_CALENDAR_MATCH_DECISION_SOURCES = frozenset({"automatic", "user", "system_skip", "legacy"})
_CALENDAR_MATCH_OUTCOME_KEYS = frozenset({"context_state", "outcome"})
_CALENDAR_MATCH_REASON_KEYS = frozenset({"safe_reason_code", "reason_code"})
_CALENDAR_MATCH_COUNT_LIMITS = {
    "candidate_count": 50,
    "roster_count": 2_147_483_647,
}
_CALENDAR_MATCH_BOOLEAN_KEYS = frozenset({"title_applied", "user_override_preserved"})
_CALENDAR_MATCH_VERSIONS = frozenset({"calendar_auto_match_v1"})
_CALENDAR_CONTEXT_ACTIVITY_OUTCOMES = {
    "calendar_context_owner_mutation": frozenset({"matched_user", "cleared_by_user"}),
    "calendar_context_deletion_accounted": frozenset({"completed"}),
}


@dataclass(frozen=True, slots=True)
class CalendarContextActivityProjection:
    event_id: UUID
    event_type: str
    actor_user_id: UUID | None
    reason: str
    created_at: datetime


def metadata_only_calendar_audit(metadata: Mapping[str, Any]) -> dict[str, Any]:
    return redact_mapping(metadata)


def safe_calendar_match_audit_outcome(value: str) -> str:
    if value not in CALENDAR_MATCH_AUDIT_OUTCOMES:
        raise ValueError("calendar match audit outcome rejected")
    return value


def safe_calendar_match_audit_reason(value: str | None) -> str | None:
    if value is not None and value not in CALENDAR_MATCH_AUDIT_REASONS:
        raise ValueError("calendar match audit reason rejected")
    return value


def calendar_match_audit_metadata(metadata: Mapping[str, Any]) -> dict[str, str | int | bool]:
    """Return a bounded metadata-only calendar-match audit payload."""

    safe: dict[str, str | int | bool] = {}
    for key, value in metadata.items():
        if value is None:
            continue
        if key in _CALENDAR_MATCH_OUTCOME_KEYS:
            safe[key] = safe_calendar_match_audit_outcome(_require_string(value))
        elif key in _CALENDAR_MATCH_REASON_KEYS:
            reason = safe_calendar_match_audit_reason(_require_string(value))
            if reason is not None:
                safe[key] = reason
        elif key == "matcher_version":
            version = _require_string(value)
            if version not in _CALENDAR_MATCH_VERSIONS:
                _reject_calendar_match_metadata()
            safe[key] = version
        elif key in _CALENDAR_MATCH_COUNT_LIMITS:
            if isinstance(value, bool) or not isinstance(value, int):
                _reject_calendar_match_metadata()
            if value < 0 or value > _CALENDAR_MATCH_COUNT_LIMITS[key]:
                _reject_calendar_match_metadata()
            safe[key] = value
        elif key == "freshness_class":
            freshness = _require_string(value)
            if freshness not in _CALENDAR_MATCH_FRESHNESS_CLASSES:
                _reject_calendar_match_metadata()
            safe[key] = freshness
        elif key == "decision_source":
            decision_source = _require_string(value)
            if decision_source not in _CALENDAR_MATCH_DECISION_SOURCES:
                _reject_calendar_match_metadata()
            safe[key] = decision_source
        elif key in _CALENDAR_MATCH_BOOLEAN_KEYS:
            if not isinstance(value, bool):
                _reject_calendar_match_metadata()
            safe[key] = value
    return safe


def _require_string(value: Any) -> str:
    if not isinstance(value, str):
        _reject_calendar_match_metadata()
    return value


def _reject_calendar_match_metadata() -> None:
    raise ValueError("calendar match audit metadata-only payload rejected")


async def write_calendar_audit_event(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    event_type: str,
    outcome: str,
    actor_user_id: UUID | None = None,
    device_id: UUID | None = None,
    calendar_source_id: UUID | None = None,
    calendar_event_snapshot_id: UUID | None = None,
    meeting_id: UUID | None = None,
    safe_reason_code: str | None = None,
    metadata: Mapping[str, Any] | None = None,
) -> CalendarAuditEvent:
    event = CalendarAuditEvent(
        workspace_id=workspace_id,
        calendar_source_id=calendar_source_id,
        calendar_event_snapshot_id=calendar_event_snapshot_id,
        meeting_id=meeting_id,
        actor_user_id=actor_user_id,
        device_id=device_id,
        event_type=event_type,
        outcome=outcome,
        safe_reason_code=safe_reason_code,
        metadata_json=metadata_only_calendar_audit(metadata or {}),
    )
    db.add(event)
    await db.flush()
    return event


async def calendar_context_activity_projections(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    meeting_id: UUID,
    limit: int = 50,
) -> list[CalendarContextActivityProjection]:
    """Load the bounded owner-action/lifecycle subset for meeting activity."""

    bounded_limit = max(0, min(limit, 50))
    if bounded_limit == 0:
        return []
    events = (
        await db.scalars(
            select(CalendarAuditEvent)
            .where(
                CalendarAuditEvent.workspace_id == workspace_id,
                CalendarAuditEvent.meeting_id == meeting_id,
                CalendarAuditEvent.event_type.in_(tuple(_CALENDAR_CONTEXT_ACTIVITY_OUTCOMES)),
            )
            .order_by(CalendarAuditEvent.created_at.desc(), CalendarAuditEvent.id.desc())
            .limit(bounded_limit)
        )
    ).all()
    projections: list[CalendarContextActivityProjection] = []
    for event in events:
        allowed_outcomes = _CALENDAR_CONTEXT_ACTIVITY_OUTCOMES.get(event.event_type)
        if allowed_outcomes is None or event.outcome not in allowed_outcomes:
            continue
        if event.safe_reason_code not in CALENDAR_MATCH_AUDIT_REASONS:
            continue
        projections.append(
            CalendarContextActivityProjection(
                event_id=event.id,
                event_type=event.event_type,
                actor_user_id=event.actor_user_id,
                reason=event.safe_reason_code,
                created_at=event.created_at,
            )
        )
    return projections
