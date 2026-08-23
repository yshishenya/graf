from __future__ import annotations

from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from twobrain_rec_server.calendar.matching import scrub_match_attempt_snapshot
from twobrain_rec_server.db.models import (
    CalendarAuditEvent,
    CalendarCredentialEnvelope,
    CalendarEventSnapshot,
    CalendarParticipant,
    CalendarReminderState,
    CalendarSource,
    ConferenceLinkCandidate,
    ExternalCalendar,
    Meeting,
    RecordingCalendarContextLink,
    RecordingCalendarMatchAttempt,
)


def disconnect_result(source_id: UUID) -> dict[str, object]:
    return {
        "source_id": str(source_id),
        "connection_state": "disconnected",
        "credentials_purged": True,
        "unmatched_future_cache_purged": True,
        # Retained for API compatibility. Disconnect is deliberately local to
        # GRAF and never calls a provider-side revoke endpoint.
        "external_revoke": "not_applicable",
        "matched_context_retention": "meeting_retention_policy",
    }


async def disconnect_source(
    db: AsyncSession,
    source: CalendarSource,
) -> dict[str, object]:
    now = datetime.now(UTC)
    source.connection_state = "disconnected"
    source.credential_state = "purged"
    source.sync_state = "failed_closed"
    source.selected_calendar_count = 0
    source.disconnected_at = now
    envelopes = await db.scalars(
        select(CalendarCredentialEnvelope).where(
            CalendarCredentialEnvelope.calendar_source_id == source.id
        )
    )
    for envelope in envelopes:
        envelope.revoked_at = envelope.revoked_at or now
        envelope.purged_at = envelope.purged_at or now
        # Keep only a tombstone row for audit/retention checks.  A purged
        # envelope must never remain decryptable by a later runtime worker.
        envelope.sealed_payload = b""
        envelope.secret_kind = "purged"
    calendars = await db.scalars(
        select(ExternalCalendar).where(ExternalCalendar.calendar_source_id == source.id)
    )
    for calendar in calendars:
        calendar.selected = False
        calendar.visibility = "disconnected"

    source_event_ids = set(
        await db.scalars(
            select(CalendarEventSnapshot.id).where(
                CalendarEventSnapshot.workspace_id == source.workspace_id,
                CalendarEventSnapshot.calendar_source_id == source.id,
            )
        )
    )
    await purge_expired_unconsumed_match_attempts(
        db,
        workspace_id=source.workspace_id,
        expired_at=now,
    )
    # ponytail: keep the disconnect path workspace-bounded until observed latency or
    # row volume justifies indexed source-reference columns on attempts and contexts.
    attempts = (
        await db.scalars(
            select(RecordingCalendarMatchAttempt).where(
                RecordingCalendarMatchAttempt.workspace_id == source.workspace_id,
            )
        )
    ).all()
    for attempt in attempts:
        if not _attempt_references_events(attempt, source_event_ids):
            continue
        if attempt.consumed_by_meeting_id is None:
            await db.delete(attempt)
        else:
            scrub_match_attempt_snapshot(attempt)

    context_rows = (
        await db.scalars(
            select(RecordingCalendarContextLink).where(
                RecordingCalendarContextLink.workspace_id == source.workspace_id,
            )
        )
    ).all()
    source_event_id_text = {str(event_id) for event_id in source_event_ids}
    for context in context_rows:
        if context.calendar_event_snapshot_id in source_event_ids:
            context.calendar_event_snapshot_id = None
        original_candidates = [str(value) for value in context.candidate_event_ids_json or []]
        remaining_candidates = [
            value for value in original_candidates if value not in source_event_id_text
        ]
        if remaining_candidates == original_candidates:
            continue
        context.candidate_event_ids_json = remaining_candidates
        context.candidate_count = len(remaining_candidates)
        if context.context_state == "ambiguous" and not remaining_candidates:
            context.context_state = "calendar_unavailable"
            context.context_confidence = "none"
            context.context_reasons_json = ["calendar_unavailable"]
            context.safe_reason_code = "calendar_unavailable"
            context.decision_source = "system_skip"
            context.evaluated_at = now

    # Apply FK detaches and attempt purges before deleting provider snapshots.
    await db.flush()
    purge_snapshots = await db.scalars(
        select(CalendarEventSnapshot).where(
            CalendarEventSnapshot.calendar_source_id == source.id,
            CalendarEventSnapshot.starts_at >= now,
        )
    )
    for snapshot in purge_snapshots:
        await db.execute(
            update(CalendarAuditEvent)
            .where(CalendarAuditEvent.calendar_event_snapshot_id == snapshot.id)
            .values(calendar_event_snapshot_id=None)
        )
        await db.execute(
            delete(CalendarParticipant).where(
                CalendarParticipant.calendar_event_snapshot_id == snapshot.id
            )
        )
        await db.execute(
            delete(ConferenceLinkCandidate).where(
                ConferenceLinkCandidate.calendar_event_snapshot_id == snapshot.id
            )
        )
        await db.execute(
            delete(CalendarReminderState).where(
                CalendarReminderState.calendar_event_snapshot_id == snapshot.id
            )
        )
        await db.delete(snapshot)
    return disconnect_result(source.id)


async def purge_expired_unconsumed_match_attempts(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    expired_at: datetime | None = None,
) -> int:
    """Purge bounded pre-meeting attempts once their exact TTL has elapsed."""

    cutoff = expired_at or datetime.now(UTC)
    result = await db.execute(
        delete(RecordingCalendarMatchAttempt)
        .where(
            RecordingCalendarMatchAttempt.workspace_id == workspace_id,
            RecordingCalendarMatchAttempt.consumed_by_meeting_id.is_(None),
            RecordingCalendarMatchAttempt.consumed_at.is_(None),
            RecordingCalendarMatchAttempt.expires_at <= cutoff,
        )
        .execution_options(synchronize_session=False)
    )
    return int(result.rowcount or 0)


async def account_meeting_calendar_context_deletion(
    db: AsyncSession,
    *,
    meeting: Meeting,
    actor_user_id: UUID | None,
    device_id: UUID | None,
    accounted_at: datetime | None = None,
) -> int:
    now = accounted_at or datetime.now(UTC)
    if meeting.title_source == "calendar":
        meeting.title = None
        meeting.title_source = "generic"
        meeting.title_updated_at = now
    links = (
        await db.scalars(
            select(RecordingCalendarContextLink).where(
                RecordingCalendarContextLink.workspace_id == meeting.workspace_id,
                RecordingCalendarContextLink.meeting_id == meeting.id,
            )
        )
    ).all()
    for link in links:
        link.calendar_event_snapshot_id = None
        link.match_attempt_id = None
        link.context_state = "deleted"
        link.context_confidence = "none"
        link.context_reasons_json = ["meeting_deleted"]
        link.title_source = meeting.title_source
        link.roster_source = "none"
        link.unlinked_at = now
        link.manual_override_state = "meeting_deletion_requested"
        link.safe_reason_code = "meeting_deleted"
        link.decision_source = "system_skip"
        link.evaluated_at = now
        link.candidate_event_ids_json = []
        link.candidate_count = 0
        link.matched_event_starts_at = None
        link.matched_event_ends_at = None
        link.matched_title = None
        link.matched_title_state = "unavailable"
        link.matched_roster_json = []
        link.matched_roster_state = "not_available"
        link.matched_roster_count = 0
        link.recurring_series_key_sha256 = None
        link.source_version_fingerprint_sha256 = None

    attempt_ids = list(
        await db.scalars(
            select(RecordingCalendarMatchAttempt.id).where(
                RecordingCalendarMatchAttempt.workspace_id == meeting.workspace_id,
                RecordingCalendarMatchAttempt.consumed_by_meeting_id == meeting.id,
            )
        )
    )
    await db.flush()
    if attempt_ids:
        await db.execute(
            delete(RecordingCalendarMatchAttempt)
            .where(RecordingCalendarMatchAttempt.id.in_(attempt_ids))
            .execution_options(synchronize_session=False)
        )

    artifact_count = len(links) + len(attempt_ids)
    if artifact_count:
        db.add(
            CalendarAuditEvent(
                workspace_id=meeting.workspace_id,
                meeting_id=meeting.id,
                actor_user_id=actor_user_id,
                device_id=device_id,
                event_type="calendar_context_deletion_accounted",
                outcome="completed",
                safe_reason_code="meeting_deleted",
                metadata_json={
                    "context_link_count": len(links),
                    "match_attempt_count": len(attempt_ids),
                },
                created_at=now,
            )
        )
    return artifact_count


def _attempt_references_events(
    attempt: RecordingCalendarMatchAttempt,
    event_ids: set[UUID],
) -> bool:
    if attempt.selected_event_snapshot_id in event_ids:
        return True
    if attempt.matched_event_snapshot_id in event_ids:
        return True
    event_id_text = {str(event_id) for event_id in event_ids}
    return any(str(value) in event_id_text for value in attempt.candidate_event_ids_json or [])
