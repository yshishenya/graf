import asyncio
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select

from tests.contract.test_ingest_openapi_contract import auth_headers
from tests.fixtures.calendar import calendar_event_fixture
from twobrain_rec_server.auth.context import TenantScope
from twobrain_rec_server.calendar.normalize import normalize_calendar_event
from twobrain_rec_server.calendar.sync import upsert_event_snapshot
from twobrain_rec_server.db.models import (
    CalendarSource,
    ExternalCalendar,
    RecordingCalendarContextLink,
)
from twobrain_rec_server.deletion.report import BOUNDED_DELETE_COPY


def test_meeting_deletion_accounts_for_active_calendar_context_link(client) -> None:
    meeting = client.post(
        "/api/v1/meetings",
        headers=auth_headers(),
        json={"local_recording_id": "calendar-context-delete", "duration_seconds": 900},
    )
    meeting_id = meeting.json()["meeting_id"]
    event_id = _seed_calendar_event(client)
    linked = client.put(
        f"/api/v1/meetings/{meeting_id}/calendar-context",
        headers=auth_headers(),
        json={"event_id": event_id, "context_reason": "manual_selection"},
    )
    deletion = client.post(
        f"/api/v1/cabinet/meetings/{meeting_id}/deletion-requests",
        headers=auth_headers(),
        json={"confirmation_boundary": BOUNDED_DELETE_COPY},
    )
    link_state = _calendar_link_state(client, UUID(meeting_id))

    assert linked.status_code == 200
    assert deletion.status_code == 202
    assert link_state == ("meeting_deletion_requested", True)


def _seed_calendar_event(client) -> str:
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

    async def seed() -> str:
        async with sessionmaker() as session:
            source = await session.get(CalendarSource, source_id)
            calendar = await session.scalar(select(ExternalCalendar).where(ExternalCalendar.calendar_source_id == source.id))
            starts_at = datetime.now(UTC) + timedelta(minutes=5)
            snapshot = await upsert_event_snapshot(
                session,
                tenant_scope=client.app_state.get("tenant_scope") or _tenant_scope(),
                source=source,
                calendar=calendar,
                event=normalize_calendar_event(
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


def _calendar_link_state(client, meeting_id: UUID) -> tuple[str, bool]:
    sessionmaker = client.app_state["sessionmaker"]

    async def read() -> tuple[str, bool]:
        async with sessionmaker() as session:
            link = await session.scalar(
                select(RecordingCalendarContextLink).where(RecordingCalendarContextLink.meeting_id == meeting_id)
            )
            return link.manual_override_state, link.unlinked_at is not None

    return asyncio.run(read())


def _tenant_scope():
    from tests.fakes.auth_contexts import DEVICE_ID, ORG_ID, USER_ID, WORKSPACE_ID

    return TenantScope(organization_id=ORG_ID, workspace_id=WORKSPACE_ID, user_id=USER_ID, device_id=DEVICE_ID)
