from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from twobrain_rec_server.db.models import (
    CalendarAuditEvent,
    CalendarCredentialEnvelope,
    CalendarEventSnapshot,
    CalendarParticipant,
    CalendarSource,
    ConferenceLinkCandidate,
    ExternalCalendar,
    Meeting,
    RecordingCalendarContextLink,
)


def disconnect_result(source_id: UUID) -> dict[str, object]:
    return {
        "source_id": str(source_id),
        "connection_state": "disconnected",
        "credentials_purged": True,
        "unmatched_future_cache_purged": True,
        "matched_context_retention": "meeting_retention_policy",
    }


async def disconnect_source(db: AsyncSession, source: CalendarSource) -> dict[str, object]:
    now = datetime.now(UTC)
    source.connection_state = "disconnected"
    source.credential_state = "purged"
    source.sync_state = "failed_closed"
    source.selected_calendar_count = 0
    source.disconnected_at = now
    envelopes = await db.scalars(
        select(CalendarCredentialEnvelope).where(CalendarCredentialEnvelope.calendar_source_id == source.id)
    )
    for envelope in envelopes:
        envelope.revoked_at = envelope.revoked_at or now
        envelope.purged_at = envelope.purged_at or now
    calendars = await db.scalars(select(ExternalCalendar).where(ExternalCalendar.calendar_source_id == source.id))
    for calendar in calendars:
        calendar.selected = False
        calendar.visibility = "disconnected"
    linked_event_ids = select(RecordingCalendarContextLink.calendar_event_snapshot_id).where(
        RecordingCalendarContextLink.workspace_id == source.workspace_id,
        RecordingCalendarContextLink.unlinked_at.is_(None),
    )
    purge_snapshots = await db.scalars(
        select(CalendarEventSnapshot).where(
            CalendarEventSnapshot.calendar_source_id == source.id,
            CalendarEventSnapshot.starts_at >= now,
            CalendarEventSnapshot.id.not_in(linked_event_ids),
        )
    )
    for snapshot in purge_snapshots:
        await db.execute(delete(CalendarParticipant).where(CalendarParticipant.calendar_event_snapshot_id == snapshot.id))
        await db.execute(delete(ConferenceLinkCandidate).where(ConferenceLinkCandidate.calendar_event_snapshot_id == snapshot.id))
        await db.delete(snapshot)
    return disconnect_result(source.id)


async def account_meeting_calendar_context_deletion(
    db: AsyncSession,
    *,
    meeting: Meeting,
    actor_user_id: UUID | None,
    device_id: UUID | None,
    accounted_at: datetime | None = None,
) -> int:
    now = accounted_at or datetime.now(UTC)
    links = (
        await db.scalars(
            select(RecordingCalendarContextLink).where(
                RecordingCalendarContextLink.workspace_id == meeting.workspace_id,
                RecordingCalendarContextLink.meeting_id == meeting.id,
                RecordingCalendarContextLink.unlinked_at.is_(None),
            )
        )
    ).all()
    for link in links:
        link.unlinked_at = now
        link.manual_override_state = "meeting_deletion_requested"
    if links:
        db.add(
            CalendarAuditEvent(
                workspace_id=meeting.workspace_id,
                meeting_id=meeting.id,
                actor_user_id=actor_user_id,
                device_id=device_id,
                event_type="calendar_context_deletion_accounted",
                outcome="completed",
                safe_reason_code="meeting_deletion_requested",
                metadata_json={"context_link_count": len(links)},
                created_at=now,
            )
        )
    return len(links)
