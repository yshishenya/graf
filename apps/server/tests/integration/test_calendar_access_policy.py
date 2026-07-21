import asyncio
from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

from sqlalchemy import delete, func, select

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
from tests.fixtures.calendar import attendee_heavy_event_fixture, calendar_event_fixture
from twobrain_rec_server.auth.context import TenantScope
from twobrain_rec_server.cabinet.queries import get_cabinet_meeting_review
from twobrain_rec_server.calendar.normalize import normalize_calendar_event
from twobrain_rec_server.calendar.sync import upsert_event_snapshot
from twobrain_rec_server.db.models import (
    CalendarParticipant,
    CalendarSource,
    ExternalCalendar,
    Meeting,
    MeetingShareGrant,
    RecordingCalendarContextLink,
    WorkspaceMembership,
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
    _mark_context_as_legacy_link(client, UUID(meeting_id))

    review = _load_review(client, UUID(meeting_id))
    roster = review.calendar_roster

    assert linked.status_code == 200
    assert roster.available is True
    assert roster.participant_count == 2
    assert roster.participants[0].participant_kind == "organizer"
    assert roster.participants[0].email_present is True
    assert "organizer@example.test" not in review.model_dump_json()
    assert "attendee@example.test" not in review.model_dump_json()


def test_098_auto_context_uses_immutable_roster_and_renders_web_embedded_parity(client) -> None:
    # FR-016/FR-020/FR-033/FR-048: provider rows may change after match without UI drift.
    meeting = client.post(
        "/api/v1/meetings",
        headers=auth_headers(),
        json={"local_recording_id": "calendar-immutable-roster-098", "duration_seconds": 900},
    )
    meeting_id = UUID(meeting.json()["meeting_id"])
    event_id = UUID(_seed_calendar_event_with_roster(client))
    linked = client.put(
        f"/api/v1/meetings/{meeting_id}/calendar-context",
        headers=auth_headers(),
        json={"event_id": str(event_id), "context_reason": "manual_selection"},
    )
    assert linked.status_code == 200
    _replace_context_with_immutable_auto_snapshot(client, meeting_id, event_id)

    review = _load_review(client, meeting_id)
    serialized = review.model_dump_json()

    assert review.calendar_context.state == "matched_auto"
    assert review.calendar_context.label == "Подобрано автоматически"
    assert review.meeting.calendar_context.state == review.calendar_context.state
    assert review.meeting.calendar_context.label == "Из календаря"
    assert review.calendar_context_detail.matched_title == "Synthetic Planning Sync"
    assert review.calendar_context_detail.matched_event_starts_at == datetime(
        2026, 7, 13, 9, 0, tzinfo=UTC
    )
    assert review.calendar_roster is not None
    assert review.calendar_roster.available is True
    assert review.calendar_roster.participant_count == 1
    assert review.calendar_roster.participants[0].display_name == "Synthetic Immutable Owner"
    assert review.access.state == "owner"
    assert review.access.can_view is True
    assert "mutable-provider@example.test" not in serialized
    assert "immutable-owner@example.test" not in serialized

    pages = {
        "web-list": client.get("/meetings", headers=auth_headers()),
        "embedded-list": client.get("/desktop/meetings", headers=auth_headers()),
        "web-detail": client.get(f"/meetings/{meeting_id}", headers=auth_headers()),
        "embedded-detail": client.get(f"/desktop/meetings/{meeting_id}", headers=auth_headers()),
    }
    for surface, response in pages.items():
        assert response.status_code == 200, surface
        if surface.endswith("list"):
            assert response.text.count("Из календаря") == 0, surface
            assert "Подобрано автоматически" not in response.text
        else:
            assert response.text.count("Подобрано автоматически") == 1, surface
            assert response.text.count("Synthetic Planning Sync") >= 1, surface
            assert "09:00–10:00" in response.text
        assert "mutable-provider@example.test" not in response.text
        assert "immutable-owner@example.test" not in response.text


def test_098_private_and_no_context_rows_never_project_stale_title_or_roster(client) -> None:
    # FR-009/FR-033/FR-037: protected states remain generic on every read surface.
    meetings: dict[str, UUID] = {}
    for state in ("skipped_private", "no_context"):
        response = client.post(
            "/api/v1/meetings",
            headers=auth_headers(),
            json={
                "local_recording_id": f"calendar-protected-{state}-098",
                "duration_seconds": 120,
            },
        )
        assert response.status_code == 200
        meetings[state] = UUID(response.json()["meeting_id"])
    _seed_protected_context_rows(client, meetings)

    for state, meeting_id in meetings.items():
        review = _load_review(client, meeting_id)
        serialized = review.model_dump_json()

        assert review.calendar_context is not None
        assert review.calendar_context.state == state
        assert review.calendar_roster is None
        assert "Synthetic Hidden Calendar Title" not in serialized
        assert "Synthetic Hidden Participant" not in serialized
        assert "hidden-participant@example.test" not in serialized

        for path in (f"/meetings/{meeting_id}", f"/desktop/meetings/{meeting_id}"):
            response = client.get(path, headers=auth_headers())
            assert response.status_code == 200
            assert "Synthetic Hidden Calendar Title" not in response.text
            assert "Synthetic Hidden Participant" not in response.text
            assert "hidden-participant@example.test" not in response.text


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
    member_headers = admin_auth_headers_for(
        user_id=DEFAULT_MEMBER_USER_ID, device_id=DEFAULT_MEMBER_DEVICE_ID
    )
    event_id = _seed_calendar_event_with_roster(
        client,
        headers=member_headers,
        tenant_scope=_tenant_scope(
            user_id=DEFAULT_MEMBER_USER_ID, device_id=DEFAULT_MEMBER_DEVICE_ID
        ),
    )
    initial_count = _active_calendar_context_count(client, UUID(meeting_id))

    linked = client.put(
        f"/api/v1/meetings/{meeting_id}/calendar-context",
        headers=member_headers,
        json={"event_id": event_id, "context_reason": "manual_selection"},
    )

    assert linked.status_code == 404
    assert linked.json()["code"] == "meeting_not_found"
    assert _active_calendar_context_count(client, UUID(meeting_id)) == initial_count


def test_member_cannot_link_another_users_calendar_event_to_own_meeting(client) -> None:
    _seed_default_workspace_roles(client)
    member_headers = admin_auth_headers_for(
        user_id=DEFAULT_MEMBER_USER_ID, device_id=DEFAULT_MEMBER_DEVICE_ID
    )
    meeting = client.post(
        "/api/v1/meetings",
        headers=member_headers,
        json={"local_recording_id": "calendar-link-foreign-event", "duration_seconds": 900},
    )
    meeting_id = meeting.json()["meeting_id"]
    owner_event_id = _seed_calendar_event_with_roster(client)
    initial_count = _active_calendar_context_count(client, UUID(meeting_id))

    linked = client.put(
        f"/api/v1/meetings/{meeting_id}/calendar-context",
        headers=member_headers,
        json={"event_id": owner_event_id, "context_reason": "manual_selection"},
    )

    assert linked.status_code == 404
    assert linked.json()["code"] == "calendar_event_not_found"
    assert _active_calendar_context_count(client, UUID(meeting_id)) == initial_count


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
    member_headers = admin_auth_headers_for(
        user_id=DEFAULT_MEMBER_USER_ID, device_id=DEFAULT_MEMBER_DEVICE_ID
    )

    unlinked = client.delete(
        f"/api/v1/meetings/{meeting_id}/calendar-context", headers=member_headers
    )

    assert linked.status_code == 200
    assert unlinked.status_code == 404
    assert unlinked.json()["code"] == "meeting_not_found"
    assert _active_calendar_context_count(client, UUID(meeting_id)) == 1


def test_us3_authorized_non_owner_get_is_safe_and_mutations_remain_owner_only(client) -> None:
    # FR-004/FR-020/FR-033/FR-037/FR-038/FR-039, SC-005/SC-011: read != mutate.
    _seed_default_workspace_roles(client)
    meeting = client.post(
        "/api/v1/meetings",
        headers=auth_headers(),
        json={
            "local_recording_id": "calendar-team-context-policy-098",
            "duration_seconds": 900,
            "started_at": datetime.now(UTC).isoformat(),
        },
    )
    assert meeting.status_code == 200
    meeting_id = UUID(meeting.json()["meeting_id"])
    event_id = _seed_calendar_event_with_roster(client)
    selected = client.put(
        f"/api/v1/meetings/{meeting_id}/calendar-context",
        headers=auth_headers(),
        json={"event_id": event_id, "context_reason": "ambiguity_resolution"},
    )
    assert selected.status_code == 200
    _set_team_visibility(client, meeting_id)
    member_headers = admin_auth_headers_for(
        user_id=DEFAULT_MEMBER_USER_ID,
        device_id=DEFAULT_MEMBER_DEVICE_ID,
    )
    path = f"/api/v1/meetings/{meeting_id}/calendar-context"

    read = client.get(path, headers=member_headers)
    correction = client.put(
        path,
        headers=member_headers,
        json={"event_id": event_id, "context_reason": "correction"},
    )
    cleared = client.delete(path, headers=member_headers)

    assert read.status_code == 200
    body = read.json()
    assert body["context_state"] == "matched_user"
    assert body["reason_code"] is None
    assert body["candidates"] == []
    assert body["can_change"] is False
    assert body["can_clear"] is False
    assert "owner@example.test" not in read.text
    assert "attendee@example.test" not in read.text
    for response in (correction, cleared):
        assert response.status_code == 404
        assert response.json()["code"] == "meeting_not_found"

    context = _calendar_context_row(client, meeting_id)
    assert context.context_state == "matched_user"
    assert str(context.calendar_event_snapshot_id) == event_id


def test_us5_authorized_non_owner_gets_safe_recurring_predecessor_pointer(client) -> None:
    # FR-024/FR-025, SC-009: current and predecessor access are evaluated separately.
    _seed_default_workspace_roles(client)
    predecessor_id, current_id, predecessor_started_at = _seed_recurring_access_pair(
        client,
        suffix="authorized",
        predecessor_visibility="team",
    )
    member_headers = admin_auth_headers_for(
        user_id=DEFAULT_MEMBER_USER_ID,
        device_id=DEFAULT_MEMBER_DEVICE_ID,
    )

    assert _load_review(client, current_id, viewer_user_id=DEFAULT_MEMBER_USER_ID) is not None
    assert _load_review(client, predecessor_id, viewer_user_id=DEFAULT_MEMBER_USER_ID) is not None

    response = client.get(
        f"/api/v1/meetings/{current_id}/calendar-context",
        headers=member_headers,
    )

    assert response.status_code == 200
    previous = response.json()["previous_recurring_meeting"]
    assert previous is not None
    assert previous["meeting_id"] == str(predecessor_id)
    assert previous["safe_title"] == "Synthetic Authorized Recurring Predecessor"
    assert datetime.fromisoformat(previous["started_at"]) == predecessor_started_at
    assert previous["readiness_state"] in {
        "notes_ready",
        "transcript_ready",
        "processing",
        "unavailable",
    }


def test_us5_inaccessible_recurring_predecessor_has_no_placeholder_or_existence_leak(
    client,
) -> None:
    # FR-025/FR-026, SC-009: access to the current occurrence never implies prior access.
    _seed_default_workspace_roles(client)
    predecessor_id, current_id, _ = _seed_recurring_access_pair(
        client,
        suffix="inaccessible",
        predecessor_visibility="owner_only",
    )
    member_headers = admin_auth_headers_for(
        user_id=DEFAULT_MEMBER_USER_ID,
        device_id=DEFAULT_MEMBER_DEVICE_ID,
    )

    assert _load_review(client, current_id, viewer_user_id=DEFAULT_MEMBER_USER_ID) is not None
    assert _load_review(client, predecessor_id, viewer_user_id=DEFAULT_MEMBER_USER_ID) is None

    response = client.get(
        f"/api/v1/meetings/{current_id}/calendar-context",
        headers=member_headers,
    )

    assert response.status_code == 200
    assert response.json()["previous_recurring_meeting"] is None
    assert str(predecessor_id) not in response.text
    assert "Synthetic Inaccessible Recurring Predecessor" not in response.text


def test_us6_roster_heavy_match_does_not_grant_attendee_access(client) -> None:
    # FR-021/SC-008: roster metadata cannot mutate membership, visibility or grants.
    _seed_default_workspace_roles(client)
    membership_count_before = _workspace_membership_count(client)
    meeting = client.post(
        "/api/v1/meetings",
        headers=auth_headers(),
        json={
            "local_recording_id": "calendar-roster-heavy-no-access-098",
            "duration_seconds": 900,
        },
    )
    assert meeting.status_code == 200
    meeting_id = UUID(meeting.json()["meeting_id"])
    participants = attendee_heavy_event_fixture(count=25)["participants"]
    participants[0] = {
        **participants[0],
        "email": "workspace-member@example.test",
        "email_hash": "sha256:synthetic-workspace-member",
        "display_name": "Synthetic Workspace Member",
        "workspace_relation": "internal",
        "recipient_candidate_class": "internal_attendee",
    }
    event_id = _seed_calendar_event_with_roster(client, participants=participants)

    linked = client.put(
        f"/api/v1/meetings/{meeting_id}/calendar-context",
        headers=auth_headers(),
        json={"event_id": event_id, "context_reason": "manual_selection"},
    )
    member_headers = admin_auth_headers_for(
        user_id=DEFAULT_MEMBER_USER_ID,
        device_id=DEFAULT_MEMBER_DEVICE_ID,
    )
    denied = client.get(
        f"/api/v1/meetings/{meeting_id}/calendar-context",
        headers=member_headers,
    )
    owner_review = _load_review(client, meeting_id)
    visibility, share_grant_count = _meeting_access_truth(client, meeting_id)

    assert linked.status_code == 200
    assert linked.json()["roster"]["participant_count"] == 25
    assert owner_review is not None
    assert owner_review.calendar_roster is not None
    assert owner_review.calendar_roster.participant_count == 25
    assert denied.status_code == 404
    assert denied.json()["code"] == "meeting_not_found"
    assert "Synthetic Workspace Member" not in denied.text
    assert "workspace-member@example.test" not in denied.text
    assert _load_review(client, meeting_id, viewer_user_id=DEFAULT_MEMBER_USER_ID) is None
    assert visibility == "owner_only"
    assert share_grant_count == 0
    assert _workspace_membership_count(client) == membership_count_before
    serialized = linked.text + owner_review.model_dump_json()
    for index in range(25):
        assert f"attendee-{index}@example.test" not in serialized
    assert "workspace-member@example.test" not in serialized


def _seed_calendar_event_with_roster(
    client,
    *,
    headers: dict[str, str] | None = None,
    tenant_scope: TenantScope | None = None,
    participants: list[dict[str, object]] | None = None,
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
            calendar = await session.scalar(
                select(ExternalCalendar).where(ExternalCalendar.calendar_source_id == source.id)
            )
            starts_at = datetime.now(UTC) + timedelta(minutes=5)
            event_payload = calendar_event_fixture(
                "caldav_yandex",
                starts_at=starts_at,
                ends_at=starts_at + timedelta(hours=1),
            )
            if participants is not None:
                event_payload["participants"] = participants
            snapshot = await upsert_event_snapshot(
                session,
                tenant_scope=tenant_scope
                or client.app_state.get("tenant_scope")
                or _tenant_scope(),
                source=source,
                calendar=calendar,
                event=normalize_calendar_event(event_payload),
            )
            await session.commit()
            return str(snapshot.id)

    return asyncio.run(seed())


def _mark_context_as_legacy_link(client, meeting_id: UUID) -> None:
    async def update() -> None:
        async with client.app_state["sessionmaker"]() as session:
            link = await session.scalar(
                select(RecordingCalendarContextLink).where(
                    RecordingCalendarContextLink.workspace_id == WORKSPACE_ID,
                    RecordingCalendarContextLink.meeting_id == meeting_id,
                )
            )
            assert link is not None
            link.context_state = "legacy_linked"
            link.decision_source = "legacy"
            link.matched_roster_json = []
            link.matched_roster_state = "not_available"
            link.matched_roster_count = 0
            await session.commit()

    asyncio.run(update())


def _replace_context_with_immutable_auto_snapshot(
    client,
    meeting_id: UUID,
    event_id: UUID,
) -> None:
    async def update() -> None:
        async with client.app_state["sessionmaker"]() as session:
            link = await session.scalar(
                select(RecordingCalendarContextLink).where(
                    RecordingCalendarContextLink.workspace_id == WORKSPACE_ID,
                    RecordingCalendarContextLink.meeting_id == meeting_id,
                )
            )
            assert link is not None
            link.context_state = "matched_auto"
            link.context_confidence = "high"
            link.safe_reason_code = "single_fresh_candidate"
            link.decision_source = "automatic"
            link.matcher_version = "calendar_auto_match_v1"
            link.matched_event_starts_at = datetime(2026, 7, 13, 9, 0, tzinfo=UTC)
            link.matched_event_ends_at = datetime(2026, 7, 13, 10, 0, tzinfo=UTC)
            link.matched_title = "Synthetic Planning Sync"
            link.matched_title_state = "available"
            link.matched_roster_json = [
                {
                    "participant_kind": "organizer",
                    "response_status": "organizer",
                    "display_name": "Synthetic Immutable Owner",
                    "email": "immutable-owner@example.test",
                    "email_present": True,
                    "workspace_relation": "owner",
                    "recipient_candidate_class": "organizer",
                }
            ]
            link.matched_roster_state = "available"
            link.matched_roster_count = 1
            link.title_source = "calendar"
            link.roster_source = "calendar"
            await session.execute(
                delete(CalendarParticipant).where(
                    CalendarParticipant.calendar_event_snapshot_id == event_id
                )
            )
            session.add(
                CalendarParticipant(
                    calendar_event_snapshot_id=event_id,
                    workspace_id=WORKSPACE_ID,
                    participant_kind="required_attendee",
                    response_status="accepted",
                    email="mutable-provider@example.test",
                    email_hash="sha256:mutable-provider",
                    display_name="Synthetic Mutable Provider Participant",
                    workspace_relation="external",
                    recipient_candidate_class="external_attendee",
                )
            )
            await session.commit()

    asyncio.run(update())


def _seed_protected_context_rows(client, meetings: dict[str, UUID]) -> None:
    async def seed() -> None:
        async with client.app_state["sessionmaker"]() as session:
            for state, meeting_id in meetings.items():
                link = await session.scalar(
                    select(RecordingCalendarContextLink).where(
                        RecordingCalendarContextLink.workspace_id == WORKSPACE_ID,
                        RecordingCalendarContextLink.meeting_id == meeting_id,
                    )
                )
                assert link is not None
                link.calendar_event_snapshot_id = None
                link.context_state = state
                link.context_confidence = "none"
                link.context_reasons_json = []
                link.title_source = "generic"
                link.roster_source = "none"
                link.manual_override_state = "none"
                link.safe_reason_code = (
                    "private_free_busy_skipped"
                    if state == "skipped_private"
                    else "no_matching_event"
                )
                link.decision_source = "automatic"
                link.matcher_version = "calendar_auto_match_v1"
                link.evaluated_at = datetime.now(UTC)
                link.candidate_event_ids_json = []
                link.candidate_count = 0
                link.matched_title = "Synthetic Hidden Calendar Title"
                link.matched_title_state = "available"
                link.matched_roster_json = [
                    {
                        "participant_kind": "required_attendee",
                        "response_status": "accepted",
                        "display_name": "Synthetic Hidden Participant",
                        "email": "hidden-participant@example.test",
                    }
                ]
                link.matched_roster_state = "available"
                link.matched_roster_count = 1
            await session.commit()

    asyncio.run(seed())


def _set_team_visibility(client, meeting_id: UUID) -> None:
    async def update() -> None:
        async with client.app_state["sessionmaker"]() as session:
            meeting = await session.get(Meeting, meeting_id)
            assert meeting is not None
            meeting.visibility = "team"
            await session.commit()

    asyncio.run(update())


def _calendar_context_row(client, meeting_id: UUID) -> RecordingCalendarContextLink:
    async def load() -> RecordingCalendarContextLink:
        async with client.app_state["sessionmaker"]() as session:
            context = await session.scalar(
                select(RecordingCalendarContextLink).where(
                    RecordingCalendarContextLink.workspace_id == WORKSPACE_ID,
                    RecordingCalendarContextLink.meeting_id == meeting_id,
                )
            )
            assert context is not None
            return context

    return asyncio.run(load())


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


def _workspace_membership_count(client) -> int:
    async def count() -> int:
        async with client.app_state["sessionmaker"]() as session:
            return int(
                await session.scalar(
                    select(func.count())
                    .select_from(WorkspaceMembership)
                    .where(WorkspaceMembership.workspace_id == WORKSPACE_ID)
                )
                or 0
            )

    return asyncio.run(count())


def _meeting_access_truth(client, meeting_id: UUID) -> tuple[str, int]:
    async def load() -> tuple[str, int]:
        async with client.app_state["sessionmaker"]() as session:
            meeting = await session.get(Meeting, meeting_id)
            assert meeting is not None
            grant_count = int(
                await session.scalar(
                    select(func.count())
                    .select_from(MeetingShareGrant)
                    .where(MeetingShareGrant.meeting_id == meeting_id)
                )
                or 0
            )
            return meeting.visibility, grant_count

    return asyncio.run(load())


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
    return TenantScope(
        organization_id=ORG_ID, workspace_id=WORKSPACE_ID, user_id=user_id, device_id=device_id
    )


def _seed_recurring_access_pair(
    client,
    *,
    suffix: str,
    predecessor_visibility: str,
) -> tuple[UUID, UUID, datetime]:
    current_started_at = datetime(2026, 7, 20, 12, 0, tzinfo=UTC)
    predecessor_started_at = current_started_at - timedelta(days=1)
    series_key = "5" * 64
    predecessor = client.post(
        "/api/v1/meetings",
        headers=auth_headers(),
        json={
            "local_recording_id": f"recurring-access-predecessor-{suffix}-098",
            "duration_seconds": 1800,
            "title": f"Synthetic {suffix.title()} Recurring Predecessor",
            "title_source": "app_context",
            "started_at": predecessor_started_at.isoformat(),
            "ended_at": (predecessor_started_at + timedelta(minutes=30)).isoformat(),
        },
    )
    current = client.post(
        "/api/v1/meetings",
        headers=auth_headers(),
        json={
            "local_recording_id": f"recurring-access-current-{suffix}-098",
            "duration_seconds": 1800,
            "title": f"Synthetic {suffix.title()} Current Occurrence",
            "title_source": "app_context",
            "started_at": current_started_at.isoformat(),
            "ended_at": (current_started_at + timedelta(minutes=30)).isoformat(),
        },
    )
    assert predecessor.status_code == 200
    assert current.status_code == 200
    predecessor_id = UUID(predecessor.json()["meeting_id"])
    current_id = UUID(current.json()["meeting_id"])

    async def seed_context() -> None:
        async with client.app_state["sessionmaker"]() as session:
            rows = (
                (
                    predecessor_id,
                    predecessor_started_at,
                    f"Synthetic {suffix.title()} Recurring Predecessor",
                    predecessor_visibility,
                ),
                (
                    current_id,
                    current_started_at,
                    f"Synthetic {suffix.title()} Current Occurrence",
                    "team",
                ),
            )
            for meeting_id, started_at, title, visibility in rows:
                meeting = await session.get(Meeting, meeting_id)
                context = await session.scalar(
                    select(RecordingCalendarContextLink).where(
                        RecordingCalendarContextLink.workspace_id == WORKSPACE_ID,
                        RecordingCalendarContextLink.meeting_id == meeting_id,
                    )
                )
                assert meeting is not None
                assert context is not None
                meeting.title = title
                meeting.title_source = "calendar"
                meeting.title_updated_at = started_at
                meeting.started_at = started_at
                meeting.ended_at = started_at + timedelta(minutes=30)
                meeting.visibility = visibility
                context.calendar_event_snapshot_id = None
                context.context_state = "matched_auto"
                context.context_confidence = "high"
                context.context_reasons_json = ["synthetic_recurring_match"]
                context.title_source = "calendar"
                context.roster_source = "none"
                context.manual_override_state = "none"
                context.safe_reason_code = "single_fresh_candidate"
                context.decision_source = "automatic"
                context.matcher_version = "calendar_auto_match_v1"
                context.evaluated_at = started_at
                context.candidate_event_ids_json = []
                context.candidate_count = 0
                context.matched_event_starts_at = started_at
                context.matched_event_ends_at = started_at + timedelta(minutes=30)
                context.matched_title = title
                context.matched_title_state = "available"
                context.matched_roster_json = []
                context.matched_roster_state = "not_available"
                context.matched_roster_count = 0
                context.recurring_series_key_sha256 = series_key
                context.source_version_fingerprint_sha256 = "f" * 64
                context.linked_at = started_at
                context.unlinked_at = None
            await session.commit()

    asyncio.run(seed_context())
    return predecessor_id, current_id, predecessor_started_at
