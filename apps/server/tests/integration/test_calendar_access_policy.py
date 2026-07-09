import asyncio
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy import func, select

from tests.contract.test_ingest_openapi_contract import auth_headers
from tests.fakes.auth_contexts import DEVICE_ID, ORG_ID, USER_ID, WORKSPACE_ID
from tests.fixtures.admin import (
    DEFAULT_MEMBER_DEVICE_ID,
    DEFAULT_MEMBER_USER_ID,
    seed_default_workspace_admin_roles,
)
from tests.fixtures.admin import (
    auth_headers_for as admin_auth_headers_for,
)
from tests.fixtures.calendar import calendar_event_fixture
from twobrain_rec_server.auth.context import TenantScope
from twobrain_rec_server.cabinet.queries import get_cabinet_meeting_review
from twobrain_rec_server.calendar.normalize import normalize_calendar_event
from twobrain_rec_server.calendar.sync import upsert_event_snapshot
from twobrain_rec_server.db.models import (
    CalendarSource,
    ExternalCalendar,
    RecordingCalendarContextLink,
)


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


def test_member_cannot_link_calendar_context_to_another_users_meeting(client) -> None:
    _seed_default_workspace_roles(client)
    meeting = client.post(
        "/api/v1/meetings",
        headers=auth_headers(),
        json={"local_recording_id": "calendar-link-foreign-meeting", "duration_seconds": 900},
    )
    meeting_id = meeting.json()["meeting_id"]
    member_headers = admin_auth_headers_for(user_id=DEFAULT_MEMBER_USER_ID, device_id=DEFAULT_MEMBER_DEVICE_ID)
    event_id = _seed_calendar_event_with_roster(
        client,
        headers=member_headers,
        tenant_scope=_tenant_scope(user_id=DEFAULT_MEMBER_USER_ID, device_id=DEFAULT_MEMBER_DEVICE_ID),
    )

    linked = client.put(
        f"/api/v1/meetings/{meeting_id}/calendar-context",
        headers=member_headers,
        json={"event_id": event_id, "context_reason": "manual_selection"},
    )

    assert linked.status_code == 404
    assert linked.json()["code"] == "meeting_not_found"
    assert _active_calendar_context_count(client, UUID(meeting_id)) == 0


def test_member_cannot_link_another_users_calendar_event_to_own_meeting(client) -> None:
    _seed_default_workspace_roles(client)
    member_headers = admin_auth_headers_for(user_id=DEFAULT_MEMBER_USER_ID, device_id=DEFAULT_MEMBER_DEVICE_ID)
    meeting = client.post(
        "/api/v1/meetings",
        headers=member_headers,
        json={"local_recording_id": "calendar-link-foreign-event", "duration_seconds": 900},
    )
    meeting_id = meeting.json()["meeting_id"]
    owner_event_id = _seed_calendar_event_with_roster(client)

    linked = client.put(
        f"/api/v1/meetings/{meeting_id}/calendar-context",
        headers=member_headers,
        json={"event_id": owner_event_id, "context_reason": "manual_selection"},
    )

    assert linked.status_code == 404
    assert linked.json()["code"] == "calendar_event_not_found"
    assert _active_calendar_context_count(client, UUID(meeting_id)) == 0


def test_member_cannot_unlink_calendar_context_from_another_users_meeting(client) -> None:
    _seed_default_workspace_roles(client)
    meeting = client.post(
        "/api/v1/meetings",
        headers=auth_headers(),
        json={"local_recording_id": "calendar-unlink-foreign-meeting", "duration_seconds": 900},
    )
    meeting_id = meeting.json()["meeting_id"]
    event_id = _seed_calendar_event_with_roster(client)
    linked = client.put(
        f"/api/v1/meetings/{meeting_id}/calendar-context",
        headers=auth_headers(),
        json={"event_id": event_id, "context_reason": "manual_selection"},
    )
    member_headers = admin_auth_headers_for(user_id=DEFAULT_MEMBER_USER_ID, device_id=DEFAULT_MEMBER_DEVICE_ID)

    unlinked = client.delete(f"/api/v1/meetings/{meeting_id}/calendar-context", headers=member_headers)

    assert linked.status_code == 200
    assert unlinked.status_code == 404
    assert unlinked.json()["code"] == "meeting_not_found"
    assert _active_calendar_context_count(client, UUID(meeting_id)) == 1


def _seed_calendar_event_with_roster(
    client,
    *,
    headers: dict[str, str] | None = None,
    tenant_scope: TenantScope | None = None,
) -> str:
    headers = headers or auth_headers()
    created = client.post(
        "/api/v1/calendar/sources",
        headers=headers,
        json={
            "provider_family": "caldav_yandex",
            "auth_mode": "app_password",
            "username": "owner@example.test",
            "credential_input": "synthetic-secret",
            "selected_provider_calendar_ids": ["primary"],
        },
    )
    assert created.status_code == 201
    source_id = UUID(created.json()["source"]["source_id"])
    sessionmaker = client.app_state["sessionmaker"]

    async def seed() -> str:
        async with sessionmaker() as session:
            source = await session.get(CalendarSource, source_id)
            calendar = await session.scalar(select(ExternalCalendar).where(ExternalCalendar.calendar_source_id == source.id))
            starts_at = datetime.now(UTC) + timedelta(minutes=5)
            snapshot = await upsert_event_snapshot(
                session,
                tenant_scope=tenant_scope or client.app_state.get("tenant_scope") or _tenant_scope(),
                source=source,
                calendar=calendar,
                event=normalize_calendar_event(
                    calendar_event_fixture(
                        "caldav_yandex",
                        starts_at=starts_at,
                        ends_at=starts_at + timedelta(hours=1),
                    )
                ),
            )
            await session.commit()
            return str(snapshot.id)

    return asyncio.run(seed())


def _seed_default_workspace_roles(client) -> None:
    async def seed() -> None:
        async with client.app_state["sessionmaker"]() as session:
            await seed_default_workspace_admin_roles(session)

    asyncio.run(seed())


def _active_calendar_context_count(client, meeting_id: UUID) -> int:
    async def count() -> int:
        async with client.app_state["sessionmaker"]() as session:
            return await session.scalar(
                select(func.count())
                .select_from(RecordingCalendarContextLink)
                .where(
                    RecordingCalendarContextLink.meeting_id == meeting_id,
                    RecordingCalendarContextLink.unlinked_at.is_(None),
                )
            )

    return int(asyncio.run(count()) or 0)


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


def _tenant_scope(user_id: UUID = USER_ID, device_id: UUID = DEVICE_ID):
    return TenantScope(organization_id=ORG_ID, workspace_id=WORKSPACE_ID, user_id=user_id, device_id=device_id)
