from __future__ import annotations

from datetime import UTC, datetime, timedelta

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from twobrain_rec_server.auth.context import TenantScope
from twobrain_rec_server.calendar.credentials import safe_credential_failure
from twobrain_rec_server.calendar.normalize import NormalizedCalendarEvent
from twobrain_rec_server.db.models import (
    CalendarEventSnapshot,
    CalendarParticipant,
    CalendarSource,
    ConferenceLinkCandidate,
    ExternalCalendar,
)


def future_sync_horizon(now: datetime | None = None) -> tuple[datetime, datetime]:
    start = now or datetime.now(UTC)
    return start, start + timedelta(days=365)


def record_source_sync_failure(source: CalendarSource, *, reason: str, now: datetime | None = None) -> dict[str, str]:
    failure = safe_credential_failure(reason)
    finished_at = now or datetime.now(UTC)
    source.last_sync_finished_at = finished_at
    source.last_safe_error_code = failure["safe_error_code"]
    source.sync_state = "stale" if source.last_successful_sync_at else "failed"
    if failure["credential_state"] != "sealed":
        source.credential_state = failure["credential_state"]
    return failure


async def upsert_event_snapshot(
    db: AsyncSession,
    tenant_scope: TenantScope,
    source: CalendarSource,
    calendar: ExternalCalendar,
    event: NormalizedCalendarEvent,
) -> CalendarEventSnapshot:
    existing = await db.scalar(
        select(CalendarEventSnapshot).where(
            CalendarEventSnapshot.workspace_id == tenant_scope.workspace_id,
            CalendarEventSnapshot.calendar_source_id == source.id,
            CalendarEventSnapshot.external_calendar_id == calendar.id,
            CalendarEventSnapshot.provider_event_id == event.provider_event_id,
            CalendarEventSnapshot.ical_uid == event.ical_uid,
        )
    )
    snapshot = existing or CalendarEventSnapshot(
        workspace_id=tenant_scope.workspace_id,
        calendar_source_id=source.id,
        external_calendar_id=calendar.id,
    )
    if existing is None:
        db.add(snapshot)

    snapshot.provider_event_id = event.provider_event_id
    snapshot.ical_uid = event.ical_uid
    snapshot.recurring_series_id = event.recurring_series_id
    snapshot.recurrence_instance_id = event.recurrence_instance_id
    snapshot.original_start = event.original_start
    snapshot.source_version = event.source_version
    snapshot.source_status = event.source_status
    snapshot.starts_at = event.starts_at
    snapshot.ends_at = event.ends_at
    snapshot.duration_seconds = event.duration_seconds
    snapshot.timezone = event.timezone
    snapshot.all_day = event.all_day
    snapshot.floating_time = event.floating_time
    snapshot.recurrence_rule_json = event.recurrence_rule
    snapshot.recurrence_exceptions_json = event.recurrence_exceptions
    snapshot.title = event.title
    snapshot.privacy_class = event.privacy_class
    snapshot.conference_summary_json = {
        "meeting_link_present": event.meeting_link_present,
        "provider_families": sorted({link.get("provider_family", "generic") for link in event.conference_links}),
    }
    snapshot.provider_extras_json = event.provider_extras | {
        "recipient_candidate_count": sum(1 for participant in event.participants if participant.get("recipient_candidate_class") not in {"resource", "room", "group", "unavailable"}),
        "roster_state": "available" if event.participants else "not_available",
        "participant_count": event.participant_count,
        "provider_family": event.provider_family,
        "title_state": event.title_state,
    }
    snapshot.safe_to_show_in_list = event.title_state == "available"
    snapshot.safe_to_use_as_title = event.title_state == "available"
    snapshot.sensitivity_reasons_json = [
        field for field, state in event.limitation_states.items() if state in {"private_redacted", "free_busy_only"}
    ]
    await db.flush()

    await db.execute(delete(CalendarParticipant).where(CalendarParticipant.calendar_event_snapshot_id == snapshot.id))
    await db.execute(delete(ConferenceLinkCandidate).where(ConferenceLinkCandidate.calendar_event_snapshot_id == snapshot.id))
    for participant in event.participants:
        db.add(
            CalendarParticipant(
                calendar_event_snapshot_id=snapshot.id,
                workspace_id=tenant_scope.workspace_id,
                participant_kind=participant["participant_kind"],
                response_status=participant["response_status"],
                email=participant.get("email"),
                email_hash=participant.get("email_hash"),
                display_name=participant.get("display_name"),
                workspace_relation=participant.get("workspace_relation", "unknown"),
                recipient_candidate_class=participant.get("recipient_candidate_class", "unknown"),
            )
        )
    for link in event.conference_links:
        db.add(
            ConferenceLinkCandidate(
                calendar_event_snapshot_id=snapshot.id,
                workspace_id=tenant_scope.workspace_id,
                source_field=link.get("source_field", "unknown"),
                provider_family=link.get("provider_family", "generic"),
                url_hash=link["url_hash"],
                redacted_url_preview=link.get("redacted_url_preview"),
                contains_passcode=bool(link.get("contains_passcode", False)),
                sensitivity_class=link.get("sensitivity_class", "meeting_link"),
            )
        )
    return snapshot


async def apply_calendar_sync_result(
    db: AsyncSession,
    *,
    tenant_scope: TenantScope,
    source: CalendarSource,
    calendar: ExternalCalendar,
    events: list[NormalizedCalendarEvent],
    sync_token: str | None,
    synced_at: datetime | None = None,
) -> list[CalendarEventSnapshot]:
    finished_at = synced_at or datetime.now(UTC)
    synced_snapshots: list[CalendarEventSnapshot] = []
    for event in events:
        snapshot = await upsert_event_snapshot(db, tenant_scope, source, calendar, event)
        snapshot.source_deleted_at = None
        synced_snapshots.append(snapshot)

    calendar.sync_token = sync_token
    calendar.last_seen_at = finished_at
    source.last_sync_finished_at = finished_at
    source.last_successful_sync_at = finished_at
    source.sync_state = "synced"
    source.last_safe_error_code = None

    seen_ids = [snapshot.id for snapshot in synced_snapshots]
    stale_conditions = [
        CalendarEventSnapshot.workspace_id == tenant_scope.workspace_id,
        CalendarEventSnapshot.calendar_source_id == source.id,
        CalendarEventSnapshot.external_calendar_id == calendar.id,
        CalendarEventSnapshot.starts_at >= (source.sync_horizon_start or finished_at),
        CalendarEventSnapshot.source_deleted_at.is_(None),
    ]
    if seen_ids:
        stale_conditions.append(CalendarEventSnapshot.id.not_in(seen_ids))
    await db.execute(update(CalendarEventSnapshot).where(*stale_conditions).values(source_deleted_at=finished_at))
    return synced_snapshots
