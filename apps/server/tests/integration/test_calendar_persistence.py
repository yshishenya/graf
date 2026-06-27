from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID

from sqlalchemy import select

from tests.contract.test_ingest_openapi_contract import auth_headers
from tests.fixtures.calendar import calendar_event_fixture
from twobrain_rec_server.calendar.normalize import (
    normalize_calendar_event,
    normalize_icalendar_event,
)
from twobrain_rec_server.calendar.sync import apply_calendar_sync_result, upsert_event_snapshot
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
)

REPO_ROOT = Path(__file__).resolve().parents[4]
MIGRATION_PATH = (
    REPO_ROOT
    / "apps/server/src/twobrain_rec_server/db/migrations/versions/0010_calendar_context_ingestion.py"
)
CALENDAR_TABLES = {
    "calendar_sources",
    "calendar_credential_envelopes",
    "external_calendars",
    "calendar_event_snapshots",
    "calendar_participants",
    "conference_link_candidates",
    "recording_calendar_context_links",
    "calendar_reminder_states",
    "calendar_audit_events",
}


def test_calendar_models_define_required_tables() -> None:
    assert CalendarSource.__tablename__ == "calendar_sources"
    assert CalendarCredentialEnvelope.__tablename__ == "calendar_credential_envelopes"
    assert ExternalCalendar.__tablename__ == "external_calendars"
    assert CalendarEventSnapshot.__tablename__ == "calendar_event_snapshots"
    assert CalendarParticipant.__tablename__ == "calendar_participants"
    assert ConferenceLinkCandidate.__tablename__ == "conference_link_candidates"
    assert RecordingCalendarContextLink.__tablename__ == "recording_calendar_context_links"
    assert CalendarReminderState.__tablename__ == "calendar_reminder_states"
    assert CalendarAuditEvent.__tablename__ == "calendar_audit_events"


def test_calendar_models_keep_workspace_scope_and_sensitive_fields() -> None:
    assert "workspace_id" in CalendarSource.__table__.columns
    assert "sealed_payload" in CalendarCredentialEnvelope.__table__.columns
    assert "provider_extras_json" in CalendarEventSnapshot.__table__.columns
    assert "email_hash" in CalendarParticipant.__table__.columns
    assert "url_hash" in ConferenceLinkCandidate.__table__.columns
    assert "open_meeting_url" not in CalendarReminderState.__table__.columns


def test_calendar_migration_declares_all_calendar_tables_and_rls() -> None:
    migration = MIGRATION_PATH.read_text()

    for table_name in CALENDAR_TABLES:
        assert table_name in migration
    assert "enable row level security" in migration
    assert "force row level security" in migration


def test_calendar_source_selected_calendars_and_sync_persist(client) -> None:
    created = client.post(
        "/api/v1/calendar/sources",
        headers=auth_headers(),
        json={
            "provider_family": "caldav_yandex",
            "auth_mode": "app_password",
            "credential_input": "synthetic-secret",
            "selected_provider_calendar_ids": ["primary"],
        },
    )
    source_id = created.json()["source"]["source_id"]

    selected = client.patch(
        f"/api/v1/calendar/sources/{source_id}/selected-calendars",
        headers=auth_headers(),
        json={"selected_provider_calendar_ids": ["primary", "team", "team"]},
    )
    synced = client.post(f"/api/v1/calendar/sources/{source_id}/sync", headers=auth_headers())
    fetched = client.get(f"/api/v1/calendar/sources/{source_id}", headers=auth_headers())

    assert created.status_code == 201
    assert selected.status_code == 200
    assert synced.status_code == 202
    assert fetched.status_code == 200
    assert fetched.json()["source"]["selected_calendar_count"] == 2
    assert fetched.json()["source"]["sync_state"] == "synced"
    assert fetched.json()["source"]["sync_horizon_end"] is not None


def test_calendar_event_snapshot_upsert_and_upcoming_response(client) -> None:
    created = client.post(
        "/api/v1/calendar/sources",
        headers=auth_headers(),
        json={
            "provider_family": "google_calendar",
            "auth_mode": "oauth",
            "selected_provider_calendar_ids": ["primary"],
        },
    )
    source_id = created.json()["source"]["source_id"]
    sessionmaker = client.app_state["sessionmaker"]

    async def seed_event() -> None:
        async with sessionmaker() as session:
            source = await session.get(CalendarSource, UUID(source_id))
            external_calendar = await session.scalar(
                select(ExternalCalendar).where(ExternalCalendar.calendar_source_id == source.id)
            )
            await upsert_event_snapshot(
                session,
                tenant_scope=client.app_state.get("tenant_scope") or _tenant_scope(),
                source=source,
                calendar=external_calendar,
                event=normalize_calendar_event(calendar_event_fixture("google_calendar")),
            )
            starts_at = datetime.now(UTC) + timedelta(minutes=5)
            await upsert_event_snapshot(
                session,
                tenant_scope=client.app_state.get("tenant_scope") or _tenant_scope(),
                source=source,
                calendar=external_calendar,
                event=normalize_calendar_event(
                    calendar_event_fixture(
                        "google_calendar",
                        provider_event_id="desktop-event",
                        ical_uid="desktop-event@example.test",
                        starts_at=starts_at,
                        ends_at=starts_at + timedelta(hours=1),
                    )
                ),
            )
            await session.commit()

    import asyncio

    asyncio.run(seed_event())

    upcoming = client.get(
        "/api/v1/calendar/events/upcoming?from=2026-06-01T00:00:00Z&to=2026-08-01T00:00:00Z&limit=10",
        headers=auth_headers(),
    )

    assert upcoming.status_code == 200
    body = upcoming.json()
    assert body["truncated"] is False
    assert body["events"][0]["provider_family"] == "google_calendar"
    assert body["events"][0]["title"] == "Synthetic Planning Sync"
    assert body["events"][0]["meeting_link_present"] is True
    assert body["events"][0]["attendee_count"] == 2
    assert body["events"][0]["roster_state"] == "available"
    assert body["events"][0]["recipient_candidate_count"] == 2
    assert "organizer@example.test" not in upcoming.text
    assert "attendee@example.test" not in upcoming.text

    desktop = client.get("/api/v1/desktop/calendar/upcoming?before_minutes=15&after_minutes=60", headers=auth_headers())

    assert desktop.status_code == 200
    assert desktop.json()["events"][0]["join_prompt_due_at"] is not None
    assert desktop.json()["events"][0]["record_prompt_due_at"] is not None


def test_calendar_event_snapshot_persists_context_fields_and_recurrence_instances(client) -> None:
    created = client.post(
        "/api/v1/calendar/sources",
        headers=auth_headers(),
        json={
            "provider_family": "caldav_yandex",
            "auth_mode": "app_password",
            "selected_provider_calendar_ids": ["primary"],
        },
    )
    source_id = UUID(created.json()["source"]["source_id"])
    sessionmaker = client.app_state["sessionmaker"]

    async def seed_events() -> tuple[str | None, str | None, int, list[datetime]]:
        async with sessionmaker() as session:
            source = await session.get(CalendarSource, source_id)
            calendar = await session.scalar(
                select(ExternalCalendar).where(ExternalCalendar.calendar_source_id == source.id)
            )
            tenant_scope = client.app_state.get("tenant_scope") or _tenant_scope()
            first = await upsert_event_snapshot(
                session,
                tenant_scope=tenant_scope,
                source=source,
                calendar=calendar,
                event=normalize_icalendar_event(
                    """
BEGIN:VCALENDAR
BEGIN:VEVENT
UID:series@example.test
RECURRENCE-ID:20260708T090000Z
DTSTART:20260708T100000Z
DTEND:20260708T110000Z
SUMMARY:Moved occurrence
DESCRIPTION:Agenda one
LOCATION:Room one
TRANSP:OPAQUE
ATTACH:https://files.example.test/private.pdf
END:VEVENT
END:VCALENDAR
""",
                    provider_family="caldav_yandex",
                    provider_calendar_id="primary",
                ),
            )
            await upsert_event_snapshot(
                session,
                tenant_scope=tenant_scope,
                source=source,
                calendar=calendar,
                event=normalize_icalendar_event(
                    """
BEGIN:VCALENDAR
BEGIN:VEVENT
UID:series@example.test
RECURRENCE-ID:20260715T090000Z
DTSTART:20260715T090000Z
DTEND:20260715T100000Z
SUMMARY:Second occurrence
END:VEVENT
END:VCALENDAR
""",
                    provider_family="caldav_yandex",
                    provider_calendar_id="primary",
                ),
            )
            snapshots = list(
                await session.scalars(
                    select(CalendarEventSnapshot)
                    .where(CalendarEventSnapshot.ical_uid == "series@example.test")
                    .order_by(CalendarEventSnapshot.starts_at)
                )
            )
            await session.commit()
            return (
                first.description,
                first.location,
                len(snapshots),
                [snapshot.original_start for snapshot in snapshots],
            )

    import asyncio

    description, location, count, original_starts = asyncio.run(seed_events())

    assert description == "Agenda one"
    assert location == "Room one"
    assert count == 2
    assert [original_start.replace(tzinfo=UTC) for original_start in original_starts] == [
        datetime(2026, 7, 8, 9, 0, tzinfo=UTC),
        datetime(2026, 7, 15, 9, 0, tzinfo=UTC),
    ]


def test_calendar_context_link_does_not_match_past_event_to_later_recording(client) -> None:
    meeting = client.post(
        "/api/v1/meetings",
        headers=auth_headers(),
        json={
            "local_recording_id": "calendar-no-retro-match",
            "duration_seconds": 900,
            "started_at": "2026-07-01T10:00:00Z",
        },
    )
    event_id = _seed_calendar_event_at(
        client,
        starts_at=datetime(2026, 7, 1, 8, 0, tzinfo=UTC),
        ends_at=datetime(2026, 7, 1, 9, 0, tzinfo=UTC),
    )

    linked = client.put(
        f"/api/v1/meetings/{meeting.json()['meeting_id']}/calendar-context",
        headers=auth_headers(),
        json={"event_id": event_id, "context_reason": "manual_selection"},
    )

    assert linked.status_code == 409
    assert linked.json()["code"] == "calendar_event_not_linkable"


def test_calendar_sync_result_updates_token_and_marks_missing_future_events_deleted(client) -> None:
    created = client.post(
        "/api/v1/calendar/sources",
        headers=auth_headers(),
        json={
            "provider_family": "google_calendar",
            "auth_mode": "oauth",
            "selected_provider_calendar_ids": ["primary"],
        },
    )
    source_id = UUID(created.json()["source"]["source_id"])
    sessionmaker = client.app_state["sessionmaker"]

    async def sync_twice() -> tuple[str, datetime | None, str | None]:
        async with sessionmaker() as session:
            source = await session.get(CalendarSource, source_id)
            calendar = await session.scalar(select(ExternalCalendar).where(ExternalCalendar.calendar_source_id == source.id))
            tenant_scope = client.app_state.get("tenant_scope") or _tenant_scope()
            first = normalize_calendar_event(
                calendar_event_fixture(
                    "google_calendar",
                    provider_event_id="kept-event",
                    ical_uid="kept-event@example.test",
                    starts_at=datetime(2026, 7, 2, 9, 0, tzinfo=UTC),
                )
            )
            stale = normalize_calendar_event(
                calendar_event_fixture(
                    "google_calendar",
                    provider_event_id="missing-event",
                    ical_uid="missing-event@example.test",
                    starts_at=datetime(2026, 7, 3, 9, 0, tzinfo=UTC),
                )
            )
            await apply_calendar_sync_result(
                session,
                tenant_scope=tenant_scope,
                source=source,
                calendar=calendar,
                events=[first, stale],
                sync_token="token-1",
                synced_at=datetime(2026, 7, 1, 8, 0, tzinfo=UTC),
            )
            updated = normalize_calendar_event(
                calendar_event_fixture(
                    "google_calendar",
                    provider_event_id="kept-event",
                    ical_uid="kept-event@example.test",
                    source_version="etag-2",
                    starts_at=datetime(2026, 7, 2, 9, 30, tzinfo=UTC),
                )
            )
            await apply_calendar_sync_result(
                session,
                tenant_scope=tenant_scope,
                source=source,
                calendar=calendar,
                events=[updated],
                sync_token="token-2",
                synced_at=datetime(2026, 7, 1, 8, 5, tzinfo=UTC),
            )
            missing = await session.scalar(
                select(CalendarEventSnapshot).where(CalendarEventSnapshot.provider_event_id == "missing-event")
            )
            kept = await session.scalar(select(CalendarEventSnapshot).where(CalendarEventSnapshot.provider_event_id == "kept-event"))
            await session.commit()
            return kept.source_version, missing.source_deleted_at, calendar.sync_token

    import asyncio

    kept_version, missing_deleted_at, sync_token = asyncio.run(sync_twice())

    assert kept_version == "etag-2"
    assert missing_deleted_at.replace(tzinfo=UTC) == datetime(2026, 7, 1, 8, 5, tzinfo=UTC)
    assert sync_token == "token-2"


def test_calendar_title_fallback_preserves_manual_title_and_names_untitled_recording(client) -> None:
    manual = client.post(
        "/api/v1/meetings",
        headers=auth_headers(),
        json={"local_recording_id": "calendar-manual-title", "duration_seconds": 900, "title": "Manual title"},
    )
    untitled = client.post(
        "/api/v1/meetings",
        headers=auth_headers(),
        json={"local_recording_id": "calendar-title-fallback", "duration_seconds": 900},
    )
    manual_event = _seed_calendar_event_at(
        client,
        starts_at=datetime(2026, 7, 1, 11, 0, tzinfo=UTC),
        ends_at=datetime(2026, 7, 1, 12, 0, tzinfo=UTC),
    )
    fallback_event = _seed_calendar_event_at(
        client,
        starts_at=datetime(2026, 7, 1, 12, 0, tzinfo=UTC),
        ends_at=datetime(2026, 7, 1, 13, 0, tzinfo=UTC),
    )

    manual_link = client.put(
        f"/api/v1/meetings/{manual.json()['meeting_id']}/calendar-context",
        headers=auth_headers(),
        json={"event_id": manual_event, "context_reason": "manual_selection"},
    )
    fallback_link = client.put(
        f"/api/v1/meetings/{untitled.json()['meeting_id']}/calendar-context",
        headers=auth_headers(),
        json={"event_id": fallback_event, "context_reason": "manual_selection"},
    )

    assert manual_link.json()["title_source"] == "user_or_generic"
    assert fallback_link.json()["title_source"] == "calendar"
    assert _meeting_title(client, UUID(manual.json()["meeting_id"])) == "Manual title"
    assert _meeting_title(client, UUID(untitled.json()["meeting_id"])) == "Synthetic Planning Sync"


def _seed_calendar_event_at(client, *, starts_at: datetime, ends_at: datetime) -> str:
    created = client.post(
        "/api/v1/calendar/sources",
        headers=auth_headers(),
        json={
            "provider_family": "google_calendar",
            "auth_mode": "oauth",
            "selected_provider_calendar_ids": ["primary"],
        },
    )
    source_id = UUID(created.json()["source"]["source_id"])
    sessionmaker = client.app_state["sessionmaker"]

    async def seed_event() -> str:
        async with sessionmaker() as session:
            source = await session.get(CalendarSource, source_id)
            external_calendar = await session.scalar(
                select(ExternalCalendar).where(ExternalCalendar.calendar_source_id == source.id)
            )
            snapshot = await upsert_event_snapshot(
                session,
                tenant_scope=client.app_state.get("tenant_scope") or _tenant_scope(),
                source=source,
                calendar=external_calendar,
                event=normalize_calendar_event(
                    calendar_event_fixture(
                        "google_calendar",
                        provider_event_id="past-event",
                        ical_uid="past-event@example.test",
                        starts_at=starts_at,
                        ends_at=ends_at,
                    )
                ),
            )
            await session.commit()
            return str(snapshot.id)

    import asyncio

    return asyncio.run(seed_event())


def _meeting_title(client, meeting_id: UUID) -> str | None:
    sessionmaker = client.app_state["sessionmaker"]

    async def read_title() -> str | None:
        async with sessionmaker() as session:
            meeting = await session.get(Meeting, meeting_id)
            return meeting.title

    import asyncio

    return asyncio.run(read_title())


def _tenant_scope():
    from tests.fakes.auth_contexts import DEVICE_ID, ORG_ID, USER_ID, WORKSPACE_ID
    from twobrain_rec_server.auth.context import TenantScope

    return TenantScope(organization_id=ORG_ID, workspace_id=WORKSPACE_ID, user_id=USER_ID, device_id=DEVICE_ID)
