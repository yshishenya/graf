"""Full owner-content roundtrip, plaintext protection and owner/lifecycle gates."""

import asyncio
import json
from datetime import UTC, datetime, timedelta

from sqlalchemy import inspect, select

from tests.contract.test_ingest_openapi_contract import auth_headers
from tests.fixtures.admin import DEFAULT_MEMBER_USER_ID, seed_default_workspace_admin_roles
from tests.fixtures.calendar import calendar_event_fixture
from tests.integration.test_calendar_provider_runtime import _create_selected_source, _tenant_scope
from twobrain_rec_server.calendar.normalize import normalize_calendar_event
from twobrain_rec_server.calendar.owner_content import attach_owner_content, owner_event_content
from twobrain_rec_server.calendar.sync import upsert_event_snapshot
from twobrain_rec_server.db.models import (
    CalendarEventSnapshot,
    CalendarParticipant,
    CalendarSource,
    ExternalCalendar,
)


def test_private_owner_content_roundtrips_without_plaintext_url_and_read_flush(client):
    source_id = _create_selected_source(client)
    title = "Личная встреча owner@example.test " + "Я" * 700
    description = "Повестка " * 900 + "https://example.test/join?pwd=synthetic-code"
    location = "Код доступа: synthetic-pin"
    participant_name = "Участник owner@example.test " + "Ю" * 400
    attachments = [
        {"title": "Материал", "fileUrl": "https://example.test/file?token=synthetic-token"}
    ]
    event = normalize_calendar_event(
        calendar_event_fixture(
            starts_at=datetime.now(UTC) + timedelta(minutes=3),
            provider_calendar_id="primary",
            title=title,
            description=description,
            location=location,
            privacy_class="private",
            attachments_metadata=attachments,
            participants=[
                {
                    "participant_kind": "organizer",
                    "response_status": "accepted",
                    "email": "owner@example.test",
                    "display_name": participant_name,
                }
            ],
        )
    )

    async def persist_and_read():
        async with client.app_state["sessionmaker"]() as session:
            source = await session.get(CalendarSource, source_id)
            calendar = await session.scalar(
                select(ExternalCalendar).where(
                    ExternalCalendar.calendar_source_id == source_id,
                    ExternalCalendar.selected.is_(True),
                )
            )
            snapshot = await upsert_event_snapshot(
                session,
                tenant_scope=_tenant_scope(),
                source=source,
                calendar=calendar,
                event=event,
                credential_encryption_key=client.app.state.credential_encryption_key,
            )
            await session.commit()
            event_id = snapshot.id
        async with client.app_state["sessionmaker"]() as session:
            snapshot = await session.get(CalendarEventSnapshot, event_id)
            assert snapshot.title == title
            assert snapshot.description is None
            assert snapshot.location is None
            mapped = {
                column.key: getattr(snapshot, column.key)
                for column in inspect(snapshot).mapper.columns
            }
            plain = json.dumps(mapped, default=str)
            for secret in ("synthetic-code", "synthetic-pin", "synthetic-token"):
                assert secret not in plain
            attach_owner_content([snapshot], client.app.state.credential_encryption_key)
            content = owner_event_content(snapshot)
            assert content["description"] == description
            assert content["location"] == location
            assert content["attachments"] == attachments
            assert content["participants"][0]["display_name"] == participant_name
            participant = await session.scalar(
                select(CalendarParticipant).where(
                    CalendarParticipant.calendar_event_snapshot_id == event_id
                )
            )
            assert participant.display_name == participant_name
            assert snapshot not in session.dirty
            await session.commit()
        return event_id

    event_id = asyncio.run(persist_and_read())
    response = client.get("/api/v1/calendar/events/upcoming", headers=auth_headers())
    assert response.status_code == 200
    owner_row = next(row for row in response.json()["events"] if row["event_id"] == str(event_id))
    assert owner_row["title"] == title
    assert owner_row["title_state"] == "available"
    assert owner_row["description"] == description
    assert owner_row["location"] == location
    assert owner_row["participants"][0]["display_name"] == participant_name
    assert owner_row["attachments"] == attachments
    desktop = client.get("/api/v1/desktop/calendar/upcoming", headers=auth_headers())
    assert (
        next(row for row in desktop.json()["events"] if row["event_id"] == str(event_id))["title"]
        == title
    )

    # A selected calendar owned by another user in the SAME workspace is excluded.
    async def change_owner():
        async with client.app_state["sessionmaker"]() as session:
            await seed_default_workspace_admin_roles(session)
            source = await session.get(CalendarSource, source_id)
            source.owner_user_id = DEFAULT_MEMBER_USER_ID
            await session.commit()

    asyncio.run(change_owner())
    excluded = client.get("/api/v1/calendar/events/upcoming", headers=auth_headers())
    assert str(event_id) not in excluded.text
    assert description not in excluded.text
    assert (
        client.get(
            f"/api/v1/calendar/events/{event_id}/open",
            headers=auth_headers(),
            follow_redirects=False,
        ).status_code
        == 404
    )


def test_deselected_and_disconnected_calendar_never_returns_owner_envelope(client):
    source_id = _create_selected_source(client)
    event = normalize_calendar_event(
        calendar_event_fixture(
            starts_at=datetime.now(UTC) + timedelta(minutes=3), provider_calendar_id="primary"
        )
    )

    async def seed():
        async with client.app_state["sessionmaker"]() as session:
            source = await session.get(CalendarSource, source_id)
            calendar = await session.scalar(
                select(ExternalCalendar).where(
                    ExternalCalendar.calendar_source_id == source_id,
                    ExternalCalendar.selected.is_(True),
                )
            )
            row = await upsert_event_snapshot(
                session,
                tenant_scope=_tenant_scope(),
                source=source,
                calendar=calendar,
                event=event,
                credential_encryption_key=client.app.state.credential_encryption_key,
            )
            await session.commit()
            return row.id

    event_id = asyncio.run(seed())
    for selected in ([], ["primary"]):
        assert (
            client.patch(
                f"/api/v1/calendar/sources/{source_id}/selected-calendars",
                headers=auth_headers(),
                json={"selected_provider_calendar_ids": selected},
            ).status_code
            == 200
        )
        response = client.get("/api/v1/calendar/events/upcoming", headers=auth_headers())
        assert (str(event_id) in response.text) is bool(selected)
    assert (
        client.post(
            f"/api/v1/calendar/sources/{source_id}/disconnect", headers=auth_headers()
        ).status_code
        == 200
    )
    assert (
        str(event_id)
        not in client.get("/api/v1/calendar/events/upcoming", headers=auth_headers()).text
    )
