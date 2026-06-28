import asyncio
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select

from tests.contract.test_ingest_openapi_contract import auth_headers
from tests.fakes.auth_contexts import DEVICE_ID, ORG_ID, USER_ID, WORKSPACE_ID
from tests.fixtures.calendar import calendar_event_fixture
from twobrain_rec_server.auth.context import TenantScope
from twobrain_rec_server.calendar.normalize import normalize_calendar_event
from twobrain_rec_server.calendar.sync import upsert_event_snapshot
from twobrain_rec_server.db.models import (
    CalendarCredentialEnvelope,
    CalendarEventSnapshot,
    CalendarSource,
    ExternalCalendar,
)


def test_disconnect_purges_credentials_and_unmatched_future_cache(client) -> None:
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
    _seed_future_event(client, source_id)

    disconnected = client.post(f"/api/v1/calendar/sources/{source_id}/disconnect", headers=auth_headers())
    state = _disconnect_state(client, source_id)

    assert disconnected.status_code == 200
    assert disconnected.json()["credentials_purged"] is True
    assert disconnected.json()["unmatched_future_cache_purged"] is True
    assert state["source"].connection_state == "disconnected"
    assert state["source"].credential_state == "purged"
    assert state["credential"].purged_at is not None
    assert state["future_event_count"] == 0


def _seed_future_event(client, source_id: UUID) -> None:
    sessionmaker = client.app_state["sessionmaker"]

    async def seed() -> None:
        async with sessionmaker() as session:
            source = await session.get(CalendarSource, source_id)
            calendar = await session.scalar(select(ExternalCalendar).where(ExternalCalendar.calendar_source_id == source.id))
            starts_at = datetime.now(UTC) + timedelta(minutes=10)
            await upsert_event_snapshot(
                session,
                TenantScope(organization_id=ORG_ID, workspace_id=WORKSPACE_ID, user_id=USER_ID, device_id=DEVICE_ID),
                source,
                calendar,
                normalize_calendar_event(
                    calendar_event_fixture(
                        "caldav_yandex",
                        starts_at=starts_at,
                        ends_at=starts_at + timedelta(hours=1),
                    )
                ),
            )
            await session.commit()

    asyncio.run(seed())


def _disconnect_state(client, source_id: UUID) -> dict[str, object]:
    sessionmaker = client.app_state["sessionmaker"]

    async def load() -> dict[str, object]:
        async with sessionmaker() as session:
            source = await session.get(CalendarSource, source_id)
            credential = await session.scalar(
                select(CalendarCredentialEnvelope).where(CalendarCredentialEnvelope.calendar_source_id == source_id)
            )
            future_events = await session.scalars(
                select(CalendarEventSnapshot).where(CalendarEventSnapshot.calendar_source_id == source_id)
            )
            return {
                "source": source,
                "credential": credential,
                "future_event_count": len(list(future_events)),
            }

    return asyncio.run(load())
