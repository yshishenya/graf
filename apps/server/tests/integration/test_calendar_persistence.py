import asyncio
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID

import pytest
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from tests.contract.test_ingest_openapi_contract import auth_headers
from tests.fixtures.calendar import calendar_event_fixture
from twobrain_rec_server.calendar.credentials import unseal_credential
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
    CalendarSettingsPreference,
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
RESOLVE_PATH = "/api/v1/desktop/recordings/{local_recording_id}/calendar-context/resolve"


async def _selected_calendar(
    session: AsyncSession, source_id: UUID
) -> ExternalCalendar:
    calendar = await session.scalar(
        select(ExternalCalendar)
        .where(
            ExternalCalendar.calendar_source_id == source_id,
            ExternalCalendar.selected.is_(True),
        )
        .order_by(ExternalCalendar.provider_calendar_id)
    )
    assert calendar is not None
    return calendar


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
            "username": "owner@example.test",
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
    assert fetched.json()["source"]["sync_state"] == "queued"
    assert fetched.json()["source"]["sync_horizon_end"] is not None


def test_calendar_source_manual_url_api_seals_url_username_and_secret(client) -> None:
    created = client.post(
        "/api/v1/calendar/sources",
        headers=auth_headers(),
        json={
            "provider_family": "custom_caldav",
            "auth_mode": "manual_url",
            "display_label": "Manual CalDAV",
            "caldav_url": "https://calendar.example.test/dav/user/",
            "username": "owner@example.test",
            "credential_input": "synthetic-secret",
        },
    )

    assert created.status_code == 201
    assert "synthetic-secret" not in created.text
    assert "calendar.example.test" not in created.text

    source_id = UUID(created.json()["source"]["source_id"])
    sessionmaker = client.app_state["sessionmaker"]

    async def load_secret() -> dict[str, str]:
        async with sessionmaker() as session:
            envelope = await session.scalar(
                select(CalendarCredentialEnvelope).where(
                    CalendarCredentialEnvelope.calendar_source_id == source_id
                )
            )
            return json.loads(
                unseal_credential(
                    envelope.sealed_payload,
                    client.app.state.credential_encryption_key,
                )
            )

    sealed_payload = asyncio.run(load_secret())

    assert sealed_payload == {
        "caldav_url": "https://calendar.example.test/dav/user/",
        "username": "owner@example.test",
        "credential_input": "synthetic-secret",
    }


def test_calendar_source_manual_url_api_rejects_unsafe_url_without_echoing_secret(client) -> None:
    response = client.post(
        "/api/v1/calendar/sources",
        headers=auth_headers(),
        json={
            "provider_family": "custom_caldav",
            "auth_mode": "manual_url",
            "caldav_url": "file:///tmp/calendar.ics",
            "credential_input": "synthetic-secret",
        },
    )

    assert response.status_code == 400
    assert response.json()["code"] == "invalid_calendar_connection_fields"
    assert "synthetic-secret" not in response.text


def test_calendar_event_snapshot_upsert_and_upcoming_response(client) -> None:
    created = client.post(
        "/api/v1/calendar/sources",
        headers=auth_headers(),
        json={
            "provider_family": "caldav_yandex",
            "auth_mode": "app_password",
            "username": "owner@example.test",
            "credential_input": "synthetic-secret",
            "selected_provider_calendar_ids": ["primary"],
        },
    )
    source_id = created.json()["source"]["source_id"]
    sessionmaker = client.app_state["sessionmaker"]

    async def seed_event() -> None:
        async with sessionmaker() as session:
            source = await session.get(CalendarSource, UUID(source_id))
            external_calendar = await _selected_calendar(session, source.id)
            await upsert_event_snapshot(
                session,
                tenant_scope=client.app_state.get("tenant_scope") or _tenant_scope(),
                source=source,
                calendar=external_calendar,
                event=normalize_calendar_event(calendar_event_fixture("caldav_yandex")),
            )
            starts_at = datetime.now(UTC) + timedelta(minutes=5)
            await upsert_event_snapshot(
                session,
                tenant_scope=client.app_state.get("tenant_scope") or _tenant_scope(),
                source=source,
                calendar=external_calendar,
                event=normalize_calendar_event(
                    calendar_event_fixture(
                        "caldav_yandex",
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
    assert body["events"][0]["provider_family"] == "caldav_yandex"
    assert body["events"][0]["title"] == "Synthetic Planning Sync"
    assert body["events"][0]["meeting_link_present"] is True
    assert body["events"][0]["attendee_count"] == 2
    assert body["events"][0]["roster_state"] == "available"
    assert body["events"][0]["recipient_candidate_count"] == 2
    assert "organizer@example.test" not in upcoming.text
    assert "attendee@example.test" not in upcoming.text

    desktop = client.get(
        "/api/v1/desktop/calendar/upcoming?before_minutes=15&after_minutes=60",
        headers=auth_headers(),
    )

    assert desktop.status_code == 200
    assert desktop.json()["events"][0]["join_prompt_due_at"] is not None
    assert desktop.json()["events"][0]["record_prompt_due_at"] is not None
    assert desktop.json()["events"][0]["join_prompt_state"] == "not_due"
    assert desktop.json()["events"][0]["record_prompt_state"] == "not_due"


def test_calendar_upcoming_ignores_selected_unavailable_calendar(client) -> None:
    created = client.post(
        "/api/v1/calendar/sources",
        headers=auth_headers(),
        json={
            "provider_family": "caldav_yandex",
            "auth_mode": "app_password",
            "username": "owner@example.test",
            "credential_input": "synthetic-secret",
            "selected_provider_calendar_ids": ["primary"],
        },
    )
    source_id = UUID(created.json()["source"]["source_id"])
    sessionmaker = client.app_state["sessionmaker"]
    now = datetime.now(UTC)

    async def seed_unavailable_event() -> None:
        async with sessionmaker() as session:
            source = await session.get(CalendarSource, source_id)
            external_calendar = await _selected_calendar(session, source.id)
            external_calendar.visibility = "unavailable"
            session.add(
                CalendarEventSnapshot(
                    workspace_id=source.workspace_id,
                    calendar_source_id=source.id,
                    external_calendar_id=external_calendar.id,
                    provider_event_id="selected-but-unavailable",
                    starts_at=now + timedelta(minutes=10),
                    ends_at=now + timedelta(minutes=40),
                    title="Unavailable selected meeting",
                    privacy_class="public",
                    source_status="confirmed",
                    conference_summary_json={"meeting_link_present": True},
                    attachments_metadata_json=[],
                    provider_extras_json={},
                    safe_to_show_in_list=True,
                    safe_to_use_as_title=True,
                    sensitivity_reasons_json=[],
                )
            )
            await session.commit()

    import asyncio

    asyncio.run(seed_unavailable_event())

    upcoming = client.get(
        "/api/v1/calendar/events/upcoming?limit=10",
        headers=auth_headers(),
    )

    assert upcoming.status_code == 200
    assert upcoming.json()["events"] == []
    assert "Unavailable selected meeting" not in upcoming.text


def test_desktop_calendar_upcoming_respects_selection_and_prompt_preferences(client) -> None:
    created = client.post(
        "/api/v1/calendar/sources",
        headers=auth_headers(),
        json={
            "provider_family": "caldav_yandex",
            "auth_mode": "app_password",
            "username": "owner@example.test",
            "credential_input": "synthetic-secret",
            "selected_provider_calendar_ids": ["selected"],
        },
    )
    source_id = UUID(created.json()["source"]["source_id"])
    sessionmaker = client.app_state["sessionmaker"]
    now = datetime.now(UTC)

    async def seed_events_and_preferences() -> None:
        async with sessionmaker() as session:
            source = await session.get(CalendarSource, source_id)
            selected_calendar = await session.scalar(
                select(ExternalCalendar).where(
                    ExternalCalendar.calendar_source_id == source.id,
                    ExternalCalendar.provider_calendar_id == "selected",
                )
            )
            unselected_calendar = ExternalCalendar(
                workspace_id=source.workspace_id,
                calendar_source_id=source.id,
                provider_calendar_id="unselected",
                display_label="Unselected calendar",
                visibility="available",
            )
            session.add(unselected_calendar)
            await session.flush()
            for calendar, event_id, title, privacy_class in (
                (selected_calendar, "selected-event", "Selected meeting", "public"),
                (unselected_calendar, "unselected-event", "Unselected meeting", "public"),
                (selected_calendar, "private-event", None, "free_busy_only"),
            ):
                private_overrides = (
                    {"participants": [], "conference_links": []}
                    if privacy_class == "free_busy_only"
                    else {}
                )
                await upsert_event_snapshot(
                    session,
                    tenant_scope=client.app_state.get("tenant_scope") or _tenant_scope(),
                    source=source,
                    calendar=calendar,
                    event=normalize_calendar_event(
                        calendar_event_fixture(
                            "caldav_yandex",
                            provider_event_id=event_id,
                            ical_uid=f"{event_id}@example.test",
                            starts_at=now + timedelta(minutes=5),
                            ends_at=now + timedelta(minutes=45),
                            title=title,
                            title_state="free_busy_only"
                            if privacy_class == "free_busy_only"
                            else "available",
                            privacy_class=privacy_class,
                            **private_overrides,
                        )
                    ),
                )
            session.add(
                CalendarSettingsPreference(
                    workspace_id=source.workspace_id,
                    owner_user_id=source.owner_user_id,
                    join_prompt_enabled=False,
                    record_prompt_enabled=False,
                )
            )
            await session.commit()

    import asyncio

    asyncio.run(seed_events_and_preferences())

    desktop = client.get(
        "/api/v1/desktop/calendar/upcoming?before_minutes=15&after_minutes=60",
        headers=auth_headers(),
    )

    assert desktop.status_code == 200
    body = desktop.json()
    assert [event["title"] for event in body["events"]] == ["Selected meeting"]
    assert body["events"][0]["join_prompt_state"] == "not_available"
    assert body["events"][0]["record_prompt_state"] == "not_available"
    assert "Unselected meeting" not in desktop.text
    assert "private-event" not in desktop.text


def test_desktop_calendar_upcoming_includes_events_overlapping_lookup_window(client) -> None:
    created = client.post(
        "/api/v1/calendar/sources",
        headers=auth_headers(),
        json={
            "provider_family": "caldav_yandex",
            "auth_mode": "app_password",
            "username": "owner@example.test",
            "credential_input": "synthetic-secret",
            "selected_provider_calendar_ids": ["primary"],
        },
    )
    source_id = UUID(created.json()["source"]["source_id"])
    sessionmaker = client.app_state["sessionmaker"]
    now = datetime.now(UTC)

    async def seed_events() -> None:
        async with sessionmaker() as session:
            source = await session.get(CalendarSource, source_id)
            calendar = await session.scalar(
                select(ExternalCalendar).where(
                    ExternalCalendar.calendar_source_id == source.id,
                    ExternalCalendar.selected.is_(True),
                )
            )
            for event_id, starts_at, ends_at in (
                ("already-running", now - timedelta(minutes=45), now + timedelta(minutes=15)),
                ("new-overlap", now - timedelta(minutes=5), now + timedelta(minutes=30)),
            ):
                session.add(
                    CalendarEventSnapshot(
                        workspace_id=source.workspace_id,
                        calendar_source_id=source.id,
                        external_calendar_id=calendar.id,
                        provider_event_id=event_id,
                        starts_at=starts_at,
                        ends_at=ends_at,
                        title=event_id,
                        privacy_class="public",
                        source_status="confirmed",
                        conference_summary_json={"meeting_link_present": True},
                        attachments_metadata_json=[],
                        provider_extras_json={},
                        safe_to_show_in_list=True,
                        safe_to_use_as_title=True,
                        sensitivity_reasons_json=[],
                    )
                )
            await session.commit()

    asyncio.run(seed_events())

    desktop = client.get(
        "/api/v1/desktop/calendar/upcoming?before_minutes=15&after_minutes=60",
        headers=auth_headers(),
    )

    assert desktop.status_code == 200
    assert {event["title"] for event in desktop.json()["events"]} == {
        "already-running",
        "new-overlap",
    }


def test_calendar_upcoming_applies_default_preferences_before_limit(client) -> None:
    created = client.post(
        "/api/v1/calendar/sources",
        headers=auth_headers(),
        json={
            "provider_family": "caldav_yandex",
            "auth_mode": "app_password",
            "username": "owner@example.test",
            "credential_input": "synthetic-secret",
            "selected_provider_calendar_ids": ["primary"],
        },
    )
    source_id = UUID(created.json()["source"]["source_id"])
    sessionmaker = client.app_state["sessionmaker"]
    now = datetime.now(UTC)

    async def seed_events() -> None:
        async with sessionmaker() as session:
            source = await session.get(CalendarSource, source_id)
            calendar = await session.scalar(
                select(ExternalCalendar).where(
                    ExternalCalendar.calendar_source_id == source.id,
                    ExternalCalendar.selected.is_(True),
                )
            )
            noisy_events = [
                CalendarEventSnapshot(
                    workspace_id=source.workspace_id,
                    calendar_source_id=source.id,
                    external_calendar_id=calendar.id,
                    provider_event_id=f"all-day-noise-{index}",
                    starts_at=now + timedelta(minutes=index + 1),
                    ends_at=now + timedelta(minutes=index + 61),
                    title=f"All-day noise {index}",
                    all_day=True,
                    privacy_class="public",
                    source_status="confirmed",
                    conference_summary_json={"meeting_link_present": True},
                    attachments_metadata_json=[],
                    provider_extras_json={"provider_family": "caldav_yandex"},
                    safe_to_show_in_list=True,
                    safe_to_use_as_title=True,
                    sensitivity_reasons_json=[],
                )
                for index in range(51)
            ]
            valid_event = CalendarEventSnapshot(
                workspace_id=source.workspace_id,
                calendar_source_id=source.id,
                external_calendar_id=calendar.id,
                provider_event_id="valid-meeting-after-noise",
                starts_at=now + timedelta(hours=2),
                ends_at=now + timedelta(hours=3),
                title="Valid meeting after noise",
                privacy_class="public",
                source_status="confirmed",
                conference_summary_json={
                    "meeting_link_present": False,
                    "participant_count": 2,
                },
                attachments_metadata_json=[],
                provider_extras_json={
                    "provider_family": "caldav_yandex",
                    "participant_count": 2,
                },
                safe_to_show_in_list=True,
                safe_to_use_as_title=True,
                sensitivity_reasons_json=[],
            )
            session.add_all([*noisy_events, valid_event])
            await session.commit()

    import asyncio

    asyncio.run(seed_events())

    upcoming = client.get(
        "/api/v1/calendar/events/upcoming",
        headers=auth_headers(),
        params={
            "from": now.isoformat().replace("+00:00", "Z"),
            "to": (now + timedelta(hours=4)).isoformat().replace("+00:00", "Z"),
            "limit": "1",
        },
    )

    assert upcoming.status_code == 200
    body = upcoming.json()
    assert body["events"][0]["title"] == "Valid meeting after noise"
    assert body["events"][0]["meeting_link_present"] is False
    assert body["events"][0]["attendee_count"] == 2
    assert "All-day noise" not in upcoming.text


def test_calendar_event_snapshot_persists_context_fields_and_recurrence_instances(client) -> None:
    created = client.post(
        "/api/v1/calendar/sources",
        headers=auth_headers(),
        json={
            "provider_family": "caldav_yandex",
            "auth_mode": "app_password",
            "username": "owner@example.test",
            "credential_input": "synthetic-secret",
            "selected_provider_calendar_ids": ["primary"],
        },
    )
    source_id = UUID(created.json()["source"]["source_id"])
    sessionmaker = client.app_state["sessionmaker"]

    async def seed_events() -> tuple[str | None, str | None, int, list[datetime]]:
        async with sessionmaker() as session:
            source = await session.get(CalendarSource, source_id)
            calendar = await _selected_calendar(session, source.id)
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


def test_calendar_context_link_rejects_unselected_calendar_event(client) -> None:
    meeting = client.post(
        "/api/v1/meetings",
        headers=auth_headers(),
        json={
            "local_recording_id": "calendar-unselected-link",
            "duration_seconds": 900,
            "started_at": "2026-07-01T09:00:00Z",
        },
    )
    created = client.post(
        "/api/v1/calendar/sources",
        headers=auth_headers(),
        json={
            "provider_family": "caldav_yandex",
            "auth_mode": "app_password",
            "username": "owner@example.test",
            "credential_input": "synthetic-secret",
            "selected_provider_calendar_ids": ["primary"],
        },
    )
    source_id = UUID(created.json()["source"]["source_id"])
    sessionmaker = client.app_state["sessionmaker"]

    async def seed_unselected_event() -> str:
        async with sessionmaker() as session:
            source = await session.get(CalendarSource, source_id)
            unselected_calendar = ExternalCalendar(
                workspace_id=source.workspace_id,
                calendar_source_id=source.id,
                provider_calendar_id="not-selected",
                display_label="Not selected",
                visibility="available",
                selected=False,
            )
            session.add(unselected_calendar)
            await session.flush()
            event = CalendarEventSnapshot(
                workspace_id=source.workspace_id,
                calendar_source_id=source.id,
                external_calendar_id=unselected_calendar.id,
                provider_event_id="not-selected-event",
                starts_at=datetime(2026, 7, 1, 9, 0, tzinfo=UTC),
                ends_at=datetime(2026, 7, 1, 10, 0, tzinfo=UTC),
                title="Should not link",
                privacy_class="public",
                source_status="confirmed",
                conference_summary_json={"meeting_link_present": True},
                attachments_metadata_json=[],
                provider_extras_json={},
                safe_to_show_in_list=True,
                safe_to_use_as_title=True,
                sensitivity_reasons_json=[],
            )
            session.add(event)
            await session.commit()
            return str(event.id)

    event_id = asyncio.run(seed_unselected_event())
    linked = client.put(
        f"/api/v1/meetings/{meeting.json()['meeting_id']}/calendar-context",
        headers=auth_headers(),
        json={"event_id": event_id, "context_reason": "manual_selection"},
    )

    assert linked.status_code == 404
    assert linked.json()["code"] == "calendar_event_not_found"
    assert _meeting_title(client, UUID(meeting.json()["meeting_id"])) is None


def test_calendar_sync_result_updates_token_and_marks_missing_future_events_deleted(client) -> None:
    created = client.post(
        "/api/v1/calendar/sources",
        headers=auth_headers(),
        json={
            "provider_family": "caldav_yandex",
            "auth_mode": "app_password",
            "username": "owner@example.test",
            "credential_input": "synthetic-secret",
            "selected_provider_calendar_ids": ["primary"],
        },
    )
    source_id = UUID(created.json()["source"]["source_id"])
    sessionmaker = client.app_state["sessionmaker"]

    async def sync_twice() -> tuple[str, datetime | None, str | None]:
        async with sessionmaker() as session:
            source = await session.get(CalendarSource, source_id)
            calendar = await _selected_calendar(session, source.id)
            tenant_scope = client.app_state.get("tenant_scope") or _tenant_scope()
            first = normalize_calendar_event(
                calendar_event_fixture(
                    "caldav_yandex",
                    provider_event_id="kept-event",
                    ical_uid="kept-event@example.test",
                    starts_at=datetime(2026, 7, 2, 9, 0, tzinfo=UTC),
                )
            )
            stale = normalize_calendar_event(
                calendar_event_fixture(
                    "caldav_yandex",
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
                    "caldav_yandex",
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
                select(CalendarEventSnapshot).where(
                    CalendarEventSnapshot.provider_event_id == "missing-event"
                )
            )
            kept = await session.scalar(
                select(CalendarEventSnapshot).where(
                    CalendarEventSnapshot.provider_event_id == "kept-event"
                )
            )
            await session.commit()
            return kept.source_version, missing.source_deleted_at, calendar.sync_token

    import asyncio

    kept_version, missing_deleted_at, sync_token = asyncio.run(sync_twice())

    assert kept_version == "etag-2"
    assert missing_deleted_at.replace(tzinfo=UTC) == datetime(2026, 7, 1, 8, 5, tzinfo=UTC)
    assert sync_token == "token-2"


@pytest.mark.parametrize(
    "provider_mutation",
    ["rename", "move", "delete", "cancel", "roster_sync"],
)
def test_matched_auto_calendar_context_stays_stable_after_provider_mutation(
    client,
    provider_mutation: str,
) -> None:
    """FR-016/FR-019, SC-006: provider sync cannot rewrite auto-match history."""

    seeded = _seed_stable_matched_calendar_context(client, provider_mutation)
    before = _stable_calendar_context_state(client, seeded["meeting_id"])

    provider_state = _mutate_matched_provider_event(
        client,
        source_id=seeded["source_id"],
        event_id=seeded["event_id"],
        provider_mutation=provider_mutation,
    )

    after = _stable_calendar_context_state(client, seeded["meeting_id"])

    assert after["meeting_title"] == "Synthetic Stable Planning"
    assert after["meeting_title_source"] == "calendar"
    assert after["context_snapshot"] == before["context_snapshot"]
    assert after["review_projection"] == before["review_projection"]
    assert after["review_projection"]["context_state"] == "matched_auto"
    assert after["review_projection"]["event_id"] == str(seeded["event_id"])
    assert sorted(after["review_projection"]["roster_names"]) == [
        "Synthetic Stable Owner",
        "Synthetic Stable Reviewer",
    ]
    assert "Synthetic Mutable Provider" not in after["review_text"]
    assert "mutable-provider@example.test" not in after["review_text"]
    assert "stable-owner@example.test" not in after["review_text"]
    assert "stable-reviewer@example.test" not in after["review_text"]
    if provider_mutation == "rename":
        assert provider_state["title"] == "Synthetic Mutable Provider Rename"
    elif provider_mutation == "move":
        provider_starts_at = provider_state["starts_at"]
        matched_starts_at = before["context_snapshot"]["starts_at"]
        assert isinstance(provider_starts_at, datetime)
        assert isinstance(matched_starts_at, datetime)
        assert provider_starts_at.replace(tzinfo=UTC) == matched_starts_at.replace(
            tzinfo=UTC
        ) + timedelta(days=2)
    elif provider_mutation == "delete":
        assert provider_state["source_deleted_at"] is not None
    elif provider_mutation == "cancel":
        assert provider_state["source_status"] == "cancelled"
    else:
        assert provider_state["participant_names"] == ["Synthetic Mutable Provider Participant"]


def test_calendar_title_fallback_preserves_manual_title_and_names_untitled_recording(
    client,
) -> None:
    manual = client.post(
        "/api/v1/meetings",
        headers=auth_headers(),
        json={
            "local_recording_id": "calendar-manual-title",
            "duration_seconds": 900,
            "started_at": "2026-07-01T11:15:00Z",
            "title": "Manual title",
        },
    )
    untitled = client.post(
        "/api/v1/meetings",
        headers=auth_headers(),
        json={
            "local_recording_id": "calendar-title-fallback",
            "duration_seconds": 900,
            "started_at": "2026-07-01T12:15:00Z",
        },
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

    assert manual_link.status_code == 200, manual_link.json()
    assert fallback_link.status_code == 200, fallback_link.json()
    assert manual_link.json()["title_source"] == "legacy_unknown"
    assert fallback_link.json()["title_source"] == "calendar"
    assert _meeting_title(client, UUID(manual.json()["meeting_id"])) == "Manual title"
    assert _meeting_title(client, UUID(untitled.json()["meeting_id"])) == "Synthetic Planning Sync"


def _seed_stable_matched_calendar_context(client, suffix: str) -> dict[str, UUID]:
    recording_started_at = datetime.now(UTC).replace(microsecond=0)
    local_recording_id = f"calendar-stable-history-{suffix}"
    created = client.post(
        "/api/v1/calendar/sources",
        headers=auth_headers(),
        json={
            "provider_family": "caldav_yandex",
            "auth_mode": "app_password",
            "username": "stable-owner@example.test",
            "credential_input": "synthetic-stable-secret",
            "selected_provider_calendar_ids": ["primary"],
        },
    )
    assert created.status_code == 201
    source_id = UUID(created.json()["source"]["source_id"])
    sessionmaker = client.app_state["sessionmaker"]

    async def seed_event() -> UUID:
        async with sessionmaker() as session:
            source = await session.get(CalendarSource, source_id)
            source.sync_state = "synced"
            source.last_successful_sync_at = recording_started_at - timedelta(minutes=1)
            source.last_sync_finished_at = source.last_successful_sync_at
            source.sync_horizon_start = recording_started_at - timedelta(days=1)
            source.sync_horizon_end = recording_started_at + timedelta(days=365)
            calendar = await _selected_calendar(session, source.id)
            event = normalize_calendar_event(
                calendar_event_fixture(
                    "caldav_yandex",
                    provider_event_id=f"stable-history-{suffix}",
                    ical_uid=f"stable-history-{suffix}@example.test",
                    recurring_series_id=f"stable-series-{suffix}",
                    source_version="stable-etag-1",
                    starts_at=recording_started_at - timedelta(minutes=5),
                    ends_at=recording_started_at + timedelta(minutes=55),
                    title="Synthetic Stable Planning",
                    participants=[
                        {
                            "participant_kind": "organizer",
                            "response_status": "organizer",
                            "email": "stable-owner@example.test",
                            "email_hash": "sha256:stable-owner",
                            "display_name": "Synthetic Stable Owner",
                            "workspace_relation": "owner",
                            "recipient_candidate_class": "organizer",
                        },
                        {
                            "participant_kind": "required_attendee",
                            "response_status": "accepted",
                            "email": "stable-reviewer@example.test",
                            "email_hash": "sha256:stable-reviewer",
                            "display_name": "Synthetic Stable Reviewer",
                            "workspace_relation": "external",
                            "recipient_candidate_class": "external_attendee",
                        },
                    ],
                )
            )
            snapshot = await upsert_event_snapshot(
                session,
                tenant_scope=client.app_state.get("tenant_scope") or _tenant_scope(),
                source=source,
                calendar=calendar,
                event=event,
            )
            await session.commit()
            return snapshot.id

    event_id = asyncio.run(seed_event())
    resolved = client.post(
        RESOLVE_PATH.format(local_recording_id=local_recording_id),
        headers=auth_headers() | {"Idempotency-Key": f"stable-history-{suffix}-resolve-098"},
        json={
            "recording_started_at": recording_started_at.isoformat(),
            "decision_intent": "automatic",
            "contract_version": "calendar_auto_context_v1",
        },
    )
    assert resolved.status_code == 200
    assert resolved.json()["context_state"] == "matched_auto"
    assert resolved.json()["candidate_count"] == 1
    meeting = client.post(
        "/api/v1/meetings",
        headers=auth_headers(),
        json={
            "local_recording_id": local_recording_id,
            "duration_seconds": 1800,
            "started_at": recording_started_at.isoformat(),
            "ended_at": (recording_started_at + timedelta(minutes=30)).isoformat(),
            "recording_display_timezone_offset_minutes": 180,
            "title": "Synthetic App Context",
            "title_source": "app_context",
            "calendar_match_attempt_id": resolved.json()["attempt_id"],
        },
    )
    assert meeting.status_code == 200
    assert meeting.json()["calendar_context"]["state"] == "matched_auto"
    meeting_id = UUID(meeting.json()["meeting_id"])
    return {"meeting_id": meeting_id, "source_id": source_id, "event_id": event_id}


def _mutate_matched_provider_event(
    client,
    *,
    source_id: UUID,
    event_id: UUID,
    provider_mutation: str,
) -> dict[str, object]:
    sessionmaker = client.app_state["sessionmaker"]

    async def mutate() -> dict[str, object]:
        async with sessionmaker() as session:
            source = await session.get(CalendarSource, source_id)
            existing = await session.get(CalendarEventSnapshot, event_id)
            assert existing is not None
            calendar = await session.get(ExternalCalendar, existing.external_calendar_id)
            assert calendar is not None
            starts_at = existing.starts_at
            ends_at = existing.ends_at
            events = []
            if provider_mutation != "delete":
                events = [
                    normalize_calendar_event(
                        calendar_event_fixture(
                            "caldav_yandex",
                            provider_event_id=existing.provider_event_id,
                            ical_uid=existing.ical_uid,
                            recurring_series_id=existing.recurring_series_id,
                            source_version="mutable-etag-2",
                            source_status=(
                                "cancelled" if provider_mutation == "cancel" else "confirmed"
                            ),
                            starts_at=(
                                starts_at + timedelta(days=2)
                                if provider_mutation == "move"
                                else starts_at
                            ),
                            ends_at=(
                                ends_at + timedelta(days=2)
                                if provider_mutation == "move"
                                else ends_at
                            ),
                            title=(
                                "Synthetic Mutable Provider Rename"
                                if provider_mutation == "rename"
                                else "Synthetic Stable Planning"
                            ),
                            participants=(
                                [
                                    {
                                        "participant_kind": "optional_attendee",
                                        "response_status": "declined",
                                        "email": "mutable-provider@example.test",
                                        "email_hash": "sha256:mutable-provider",
                                        "display_name": "Synthetic Mutable Provider Participant",
                                        "workspace_relation": "external",
                                        "recipient_candidate_class": "external_attendee",
                                    }
                                ]
                                if provider_mutation == "roster_sync"
                                else calendar_event_fixture("caldav_yandex")["participants"]
                            ),
                        )
                    )
                ]
            await apply_calendar_sync_result(
                session,
                tenant_scope=client.app_state.get("tenant_scope") or _tenant_scope(),
                source=source,
                calendar=calendar,
                events=events,
                sync_token=f"stable-history-{provider_mutation}",
                synced_at=starts_at - timedelta(hours=1),
            )
            await session.commit()
            updated = await session.get(CalendarEventSnapshot, event_id)
            participant_names = list(
                await session.scalars(
                    select(CalendarParticipant.display_name)
                    .where(CalendarParticipant.calendar_event_snapshot_id == event_id)
                    .order_by(CalendarParticipant.display_name)
                )
            )
            return {
                "title": updated.title,
                "starts_at": updated.starts_at,
                "source_status": updated.source_status,
                "source_deleted_at": updated.source_deleted_at,
                "participant_names": participant_names,
            }

    return asyncio.run(mutate())


def _stable_calendar_context_state(client, meeting_id: UUID) -> dict[str, object]:
    sessionmaker = client.app_state["sessionmaker"]

    async def read_state() -> tuple[str | None, str, dict[str, object]]:
        async with sessionmaker() as session:
            meeting = await session.get(Meeting, meeting_id)
            link = await session.scalar(
                select(RecordingCalendarContextLink).where(
                    RecordingCalendarContextLink.meeting_id == meeting_id
                )
            )
            snapshot = {
                "event_id": str(link.calendar_event_snapshot_id),
                "starts_at": link.matched_event_starts_at,
                "ends_at": link.matched_event_ends_at,
                "title": link.matched_title,
                "title_state": link.matched_title_state,
                "roster": link.matched_roster_json,
                "roster_state": link.matched_roster_state,
                "roster_count": link.matched_roster_count,
                "series_fingerprint": link.recurring_series_key_sha256,
                "source_version_fingerprint": link.source_version_fingerprint_sha256,
            }
            return meeting.title, meeting.title_source, snapshot

    meeting_title, meeting_title_source, context_snapshot = asyncio.run(read_state())
    assert context_snapshot["series_fingerprint"] is not None
    assert context_snapshot["source_version_fingerprint"] is not None
    review = client.get(
        f"/api/v1/cabinet/meetings/{meeting_id}",
        headers=auth_headers(),
    )
    assert review.status_code == 200
    body = review.json()
    detail = body["calendar_context_detail"]
    roster = body["calendar_roster"]
    projection = {
        "meeting_title": body["meeting"]["title"],
        "summary_state": body["calendar_context"]["state"],
        "context_state": detail["context_state"],
        "event_id": detail["event_id"],
        "title_source": detail["title_source"],
        "detail_roster": detail["roster"],
        "roster_state": roster["roster_state"],
        "roster_count": roster["participant_count"],
        "roster_names": [participant["display_name"] for participant in roster["participants"]],
    }
    return {
        "meeting_title": meeting_title,
        "meeting_title_source": meeting_title_source,
        "context_snapshot": context_snapshot,
        "review_projection": projection,
        "review_text": review.text,
    }


def _seed_calendar_event_at(client, *, starts_at: datetime, ends_at: datetime) -> str:
    created = client.post(
        "/api/v1/calendar/sources",
        headers=auth_headers(),
        json={
            "provider_family": "caldav_yandex",
            "auth_mode": "app_password",
            "username": "owner@example.test",
            "credential_input": "synthetic-secret",
            "selected_provider_calendar_ids": ["primary"],
        },
    )
    source_id = UUID(created.json()["source"]["source_id"])
    sessionmaker = client.app_state["sessionmaker"]

    async def seed_event() -> str:
        async with sessionmaker() as session:
            source = await session.get(CalendarSource, source_id)
            external_calendar = await _selected_calendar(session, source.id)
            snapshot = await upsert_event_snapshot(
                session,
                tenant_scope=client.app_state.get("tenant_scope") or _tenant_scope(),
                source=source,
                calendar=external_calendar,
                event=normalize_calendar_event(
                    calendar_event_fixture(
                        "caldav_yandex",
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

    return TenantScope(
        organization_id=ORG_ID, workspace_id=WORKSPACE_ID, user_id=USER_ID, device_id=DEVICE_ID
    )
