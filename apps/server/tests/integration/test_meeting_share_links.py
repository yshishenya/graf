import asyncio
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import func, select

from tests.contract.test_ingest_openapi_contract import auth_headers
from tests.fakes.auth_contexts import DEVICE_ID, ORG_ID, USER_ID, WORKSPACE_ID
from tests.fixtures.cabinet import seed_cabinet_meetings
from tests.fixtures.cabinet_access import (
    SHARED_USER_ID,
    add_workspace_user,
    audit_events,
    auth_headers_for,
)
from tests.fixtures.calendar import attendee_heavy_event_fixture, calendar_event_fixture
from twobrain_rec_server.auth.context import TenantScope
from twobrain_rec_server.calendar.normalize import normalize_calendar_event
from twobrain_rec_server.calendar.sync import upsert_event_snapshot
from twobrain_rec_server.db.models import (
    CalendarSource,
    ExportPackage,
    ExternalCalendar,
    MeetingEgressAuditEvent,
    MeetingShareGrant,
)


def test_login_required_share_link_resolves_for_grantee_and_can_be_revoked(client) -> None:
    seeds = seed_cabinet_meetings(client)
    add_workspace_user(client)

    share = client.post(
        f"/api/v1/cabinet/meetings/{seeds.ready_id}/shares",
        headers=auth_headers(),
        json={"grantee_user_id": str(SHARED_USER_ID)},
    )
    assert share.status_code == 201
    payload = share.json()
    token_url = payload["share_url"]

    resolved = client.get(
        f"/api/v1{token_url}",
        headers=auth_headers_for(),
        follow_redirects=False,
    )
    assert resolved.status_code == 302
    assert resolved.headers["location"] == f"/meetings/{seeds.ready_id}"

    grant_id = payload["grant"]["grant_id"]
    revoked = client.delete(
        f"/api/v1/cabinet/meetings/{seeds.ready_id}/shares/{grant_id}",
        headers=auth_headers(),
    )
    blocked = client.get(
        f"/api/v1{token_url}",
        headers=auth_headers_for(),
        follow_redirects=False,
    )

    assert revoked.status_code == 204
    assert blocked.status_code == 404
    event_dump = [event.event_type for event in audit_events(client, seeds.ready_id)]
    assert event_dump == ["share_granted", "share_link_opened", "share_revoked"]
    for event in audit_events(client, seeds.ready_id):
        assert "token" not in event.metadata_json
        assert "share_token_hash" not in event.metadata_json


def test_calendar_attendees_do_not_create_meeting_share_grants(client) -> None:
    meeting = client.post(
        "/api/v1/meetings",
        headers=auth_headers(),
        json={"local_recording_id": "calendar-no-share", "duration_seconds": 900},
    )
    meeting_id = meeting.json()["meeting_id"]
    event_id = _seed_calendar_event_with_external_attendee(client)

    linked = client.put(
        f"/api/v1/meetings/{meeting_id}/calendar-context",
        headers=auth_headers(),
        json={"event_id": event_id, "context_reason": "manual_selection"},
    )
    grant_count = _share_grant_count(client, UUID(meeting_id))

    assert linked.status_code == 200
    assert grant_count == 0


def test_us6_roster_heavy_match_has_zero_share_or_delivery_side_effects(client) -> None:
    # FR-021/SC-008: recipient-candidate metadata remains inert after a real match.
    meeting = client.post(
        "/api/v1/meetings",
        headers=auth_headers(),
        json={
            "local_recording_id": "calendar-roster-heavy-no-delivery-098",
            "duration_seconds": 900,
        },
    )
    assert meeting.status_code == 200
    meeting_id = UUID(meeting.json()["meeting_id"])
    event_id = _seed_calendar_event_with_external_attendee(client, attendee_count=25)
    before = _meeting_side_effect_counts(client, meeting_id)

    linked = client.put(
        f"/api/v1/meetings/{meeting_id}/calendar-context",
        headers=auth_headers(),
        json={"event_id": event_id, "context_reason": "manual_selection"},
    )
    review = client.get(
        f"/api/v1/cabinet/meetings/{meeting_id}",
        headers=auth_headers(),
    )
    after = _meeting_side_effect_counts(client, meeting_id)

    assert linked.status_code == 200
    assert review.status_code == 200
    roster = linked.json()["roster"]
    assert roster["participant_count"] == 25
    assert len(roster["participants"]) == 25
    forbidden_action_fields = {
        "access_grant_id",
        "delivery_state",
        "message_recipient",
        "recipient_email",
        "report_recipient",
        "send",
        "share_grant_id",
        "summary_recipient",
    }
    for participant in roster["participants"]:
        assert forbidden_action_fields.isdisjoint(participant)
        assert participant["email_present"] is True
        assert participant["recipient_candidate_class"] == "external"
    assert review.json()["share"]["active_grants"] == []
    assert (
        after
        == before
        == {
            "egress_events": 0,
            "export_packages": 0,
            "share_grants": 0,
        }
    )
    serialized = linked.text + review.text
    assert "guest@external.test" not in serialized
    for index in range(1, 25):
        assert f"attendee-{index}@example.test" not in serialized


def _seed_calendar_event_with_external_attendee(
    client,
    *,
    attendee_count: int = 1,
) -> str:
    source_response = client.post(
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
    source_id = UUID(source_response.json()["source"]["source_id"])
    sessionmaker = client.app_state["sessionmaker"]
    participants = attendee_heavy_event_fixture(count=attendee_count)["participants"]
    participants[0] = {
        **participants[0],
        "email": "guest@external.test",
        "email_hash": "sha256:synthetic-external-guest",
        "display_name": "External Guest",
        "workspace_relation": "external",
        "recipient_candidate_class": "external",
    }

    async def seed() -> str:
        async with sessionmaker() as session:
            source = await session.get(CalendarSource, source_id)
            calendar = await session.scalar(
                select(ExternalCalendar).where(ExternalCalendar.calendar_source_id == source.id)
            )
            starts_at = datetime.now(UTC) + timedelta(minutes=5)
            snapshot = await upsert_event_snapshot(
                session,
                TenantScope(
                    organization_id=ORG_ID,
                    workspace_id=WORKSPACE_ID,
                    user_id=USER_ID,
                    device_id=DEVICE_ID,
                ),
                source,
                calendar,
                normalize_calendar_event(
                    calendar_event_fixture(
                        "caldav_yandex",
                        starts_at=starts_at,
                        ends_at=starts_at + timedelta(hours=1),
                        participants=participants,
                    )
                ),
            )
            await session.commit()
            return str(snapshot.id)

    return asyncio.run(seed())


def _share_grant_count(client, meeting_id: UUID) -> int:
    sessionmaker = client.app_state["sessionmaker"]

    async def count() -> int:
        async with sessionmaker() as session:
            return await session.scalar(
                select(func.count())
                .select_from(MeetingShareGrant)
                .where(MeetingShareGrant.meeting_id == meeting_id)
            )

    return int(asyncio.run(count()))


def _meeting_side_effect_counts(client, meeting_id: UUID) -> dict[str, int]:
    async def count() -> dict[str, int]:
        async with client.app_state["sessionmaker"]() as session:
            counts: dict[str, int] = {}
            for key, model in (
                ("egress_events", MeetingEgressAuditEvent),
                ("export_packages", ExportPackage),
                ("share_grants", MeetingShareGrant),
            ):
                counts[key] = int(
                    await session.scalar(
                        select(func.count())
                        .select_from(model)
                        .where(model.meeting_id == meeting_id)
                    )
                    or 0
                )
            return counts

    return asyncio.run(count())
