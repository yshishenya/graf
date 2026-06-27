import asyncio
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import UUID

import yaml
from fastapi.routing import APIRoute
from sqlalchemy import select

from tests.contract.test_ingest_openapi_contract import auth_headers
from tests.fakes.auth_contexts import DEVICE_ID, ORG_ID, USER_ID, WORKSPACE_ID
from tests.fixtures.calendar import calendar_event_fixture
from twobrain_rec_server.auth.context import TenantScope
from twobrain_rec_server.calendar.normalize import normalize_calendar_event
from twobrain_rec_server.calendar.sync import upsert_event_snapshot
from twobrain_rec_server.config import Settings
from twobrain_rec_server.db.models import CalendarSource, ExternalCalendar
from twobrain_rec_server.main import create_app

REPO_ROOT = Path(__file__).resolve().parents[4]
CONTRACT_PATH = REPO_ROOT / "specs/060-calendar-context-ingestion/contracts/calendar-context.openapi.yaml"


def test_calendar_openapi_contract_paths_are_registered() -> None:
    app = create_app(Settings())
    route_paths = {route.path for route in app.routes if isinstance(route, APIRoute)}
    contract = yaml.safe_load(CONTRACT_PATH.read_text())

    assert set(contract["paths"]) <= route_paths


def test_calendar_openapi_contract_does_not_return_write_only_credentials() -> None:
    schema = yaml.safe_load(CONTRACT_PATH.read_text())

    assert "credential_input" in schema["components"]["schemas"]["ConnectCalendarSourceRequest"]["properties"]
    assert "credential_input" not in str(schema["components"]["schemas"]["CalendarSourceResponse"])


def test_calendar_provider_endpoint_lists_supported_presets(client) -> None:
    response = client.get("/api/v1/calendar/providers", headers=auth_headers())

    assert response.status_code == 200
    families = {provider["provider_family"] for provider in response.json()["providers"]}
    assert {
        "caldav_yandex",
        "caldav_mail_ru",
        "google_calendar",
        "microsoft_graph",
        "exchange_ews",
        "bitrix24",
        "custom_caldav_vk_workspace",
        "caldav_mailion_myoffice",
        "caldav_r7_office",
        "caldav_communigate_pro",
        "caldav_rupost",
        "caldav_nextcloud_sogo",
        "custom_caldav",
    } <= families


def test_calendar_source_lifecycle_contract_never_returns_credentials(client) -> None:
    created = client.post(
        "/api/v1/calendar/sources",
        headers=auth_headers(),
        json={
            "provider_family": "caldav_yandex",
            "auth_mode": "app_password",
            "display_label": "Synthetic calendar",
            "credential_input": "synthetic-secret",
            "selected_provider_calendar_ids": ["primary"],
        },
    )

    assert created.status_code == 201
    body = created.json()
    source_id = body["source"]["source_id"]
    assert body["source"]["credential_state"] == "sealed"
    assert "synthetic-secret" not in str(body)
    assert body["calendars"][0]["selected"] is True

    listed = client.get("/api/v1/calendar/sources", headers=auth_headers())
    assert listed.status_code == 200
    assert listed.json()["sources"][0]["source_id"] == source_id

    selected = client.patch(
        f"/api/v1/calendar/sources/{source_id}/selected-calendars",
        headers=auth_headers(),
        json={"selected_provider_calendar_ids": ["primary", "team"]},
    )
    assert selected.status_code == 200
    assert {calendar["calendar_id"] for calendar in selected.json()["calendars"]} == {"primary", "team"}

    sync = client.post(f"/api/v1/calendar/sources/{source_id}/sync", headers=auth_headers())
    assert sync.status_code == 202
    assert sync.json()["sync_state"] == "synced"

    disconnected = client.post(f"/api/v1/calendar/sources/{source_id}/disconnect", headers=auth_headers())
    assert disconnected.status_code == 200
    assert disconnected.json()["connection_state"] == "disconnected"


def test_calendar_source_contract_rejects_unsupported_provider_without_echoing_secret(client) -> None:
    response = client.post(
        "/api/v1/calendar/sources",
        headers=auth_headers(),
        json={
            "provider_family": "unknown_provider",
            "auth_mode": "app_password",
            "credential_input": "synthetic-secret",
        },
    )

    assert response.status_code == 400
    assert response.json()["code"] == "unsupported_calendar_provider"
    assert "synthetic-secret" not in response.text


def test_calendar_source_contract_returns_404_for_missing_source(client) -> None:
    response = client.get(
        "/api/v1/calendar/sources/00000000-0000-0000-0000-000000000060",
        headers=auth_headers(),
    )

    assert response.status_code == 404
    assert response.json()["code"] == "calendar_source_not_found"


def test_meeting_calendar_context_link_and_unlink_contract(client) -> None:
    meeting = client.post(
        "/api/v1/meetings",
        headers=auth_headers(),
        json={
            "local_recording_id": "calendar-context-recording",
            "duration_seconds": 1200,
            "started_at": "2026-07-01T09:00:00Z",
        },
    )
    assert meeting.status_code == 200
    meeting_id = meeting.json()["meeting_id"]
    event_id = _seed_calendar_event(client)

    linked = client.put(
        f"/api/v1/meetings/{meeting_id}/calendar-context",
        headers=auth_headers(),
        json={"event_id": event_id, "context_reason": "manual_selection"},
    )
    unlinked = client.delete(f"/api/v1/meetings/{meeting_id}/calendar-context", headers=auth_headers())

    assert linked.status_code == 200
    assert linked.json()["context_state"] == "linked"
    assert linked.json()["event_id"] == event_id
    assert linked.json()["context_confidence"] == "high"
    assert unlinked.status_code == 200
    assert unlinked.json()["context_state"] == "unlinked"


def test_upcoming_calendar_contract_returns_safe_roster_counts_without_attendee_dump(client) -> None:
    _seed_calendar_event(client)

    upcoming = client.get(
        "/api/v1/calendar/events/upcoming?from=2026-07-01T00:00:00Z&to=2026-07-02T00:00:00Z",
        headers=auth_headers(),
    )

    assert upcoming.status_code == 200
    event = upcoming.json()["events"][0]
    assert event["attendee_count"] == 2
    assert event["roster_state"] == "available"
    assert event["recipient_candidate_count"] == 2
    assert "organizer@example.test" not in upcoming.text
    assert "attendee@example.test" not in upcoming.text


def _seed_calendar_event(client) -> str:
    source_response = client.post(
        "/api/v1/calendar/sources",
        headers=auth_headers(),
        json={
            "provider_family": "google_calendar",
            "auth_mode": "oauth",
            "selected_provider_calendar_ids": ["primary"],
        },
    )
    source_id = UUID(source_response.json()["source"]["source_id"])
    sessionmaker = client.app_state["sessionmaker"]

    async def seed() -> str:
        async with sessionmaker() as session:
            source = await session.get(CalendarSource, source_id)
            calendar = await session.scalar(select(ExternalCalendar).where(ExternalCalendar.calendar_source_id == source.id))
            starts_at = datetime(2026, 7, 1, 9, 0, tzinfo=UTC) + timedelta(minutes=5)
            snapshot = await upsert_event_snapshot(
                session,
                TenantScope(organization_id=ORG_ID, workspace_id=WORKSPACE_ID, user_id=USER_ID, device_id=DEVICE_ID),
                source,
                calendar,
                normalize_calendar_event(
                    calendar_event_fixture(
                        "google_calendar",
                        starts_at=starts_at,
                        ends_at=starts_at + timedelta(hours=1),
                    )
                ),
            )
            await session.commit()
            return str(snapshot.id)

    return asyncio.run(seed())
