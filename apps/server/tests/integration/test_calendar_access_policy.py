import asyncio
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy import select

from tests.contract.test_ingest_openapi_contract import auth_headers
from tests.fakes.auth_contexts import USER_ID, WORKSPACE_ID
from tests.fixtures.calendar import calendar_event_fixture
from twobrain_rec_server.auth.context import TenantScope
from twobrain_rec_server.cabinet.queries import get_cabinet_meeting_review
from twobrain_rec_server.calendar.normalize import normalize_calendar_event
from twobrain_rec_server.calendar.sync import upsert_event_snapshot
from twobrain_rec_server.db.models import CalendarSource, ExternalCalendar


def test_authorized_cabinet_review_includes_safe_calendar_roster_context(client) -> None:
    meeting = client.post(
        "/api/v1/meetings",
        headers=auth_headers(),
        json={"local_recording_id": "calendar-roster-review", "duration_seconds": 900},
    )
    meeting_id = meeting.json()["meeting_id"]
    event_id = _seed_calendar_event_with_roster(client)
    linked = client.put(
        f"/api/v1/meetings/{meeting_id}/calendar-context",
        headers=auth_headers(),
        json={"event_id": event_id, "context_reason": "manual_selection"},
    )

    review = _load_review(client, UUID(meeting_id))
    roster = review.calendar_roster

    assert linked.status_code == 200
    assert roster.available is True
    assert roster.participant_count == 2
    assert roster.participants[0].participant_kind == "organizer"
    assert roster.participants[0].email_present is True
    assert "organizer@example.test" not in review.model_dump_json()
    assert "attendee@example.test" not in review.model_dump_json()


def test_denied_cabinet_viewer_cannot_read_calendar_roster_context(client) -> None:
    meeting = client.post(
        "/api/v1/meetings",
        headers=auth_headers(),
        json={"local_recording_id": "calendar-roster-denied", "duration_seconds": 900},
    )
    meeting_id = meeting.json()["meeting_id"]
    event_id = _seed_calendar_event_with_roster(client)
    linked = client.put(
        f"/api/v1/meetings/{meeting_id}/calendar-context",
        headers=auth_headers(),
        json={"event_id": event_id, "context_reason": "manual_selection"},
    )

    denied_review = _load_review(client, UUID(meeting_id), viewer_user_id=uuid4())

    assert linked.status_code == 200
    assert denied_review is None


def _seed_calendar_event_with_roster(client) -> str:
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


def _load_review(client, meeting_id: UUID, viewer_user_id=USER_ID):
    sessionmaker = client.app_state["sessionmaker"]

    async def load():
        async with sessionmaker() as session:
            return await get_cabinet_meeting_review(
                session,
                workspace_id=WORKSPACE_ID,
                meeting_id=meeting_id,
                viewer_user_id=viewer_user_id,
            )

    return asyncio.run(load())


def _tenant_scope():
    from tests.fakes.auth_contexts import DEVICE_ID, ORG_ID

    return TenantScope(organization_id=ORG_ID, workspace_id=WORKSPACE_ID, user_id=USER_ID, device_id=DEVICE_ID)
