import asyncio
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select

from tests.contract.test_ingest_openapi_contract import auth_headers
from tests.fakes.auth_contexts import DEVICE_ID, USER_ID, WORKSPACE_ID
from tests.fixtures.calendar import calendar_event_fixture
from twobrain_rec_server.auth.context import TenantScope
from twobrain_rec_server.calendar.audit import calendar_context_activity_projections
from twobrain_rec_server.calendar.normalize import normalize_calendar_event
from twobrain_rec_server.calendar.sync import upsert_event_snapshot
from twobrain_rec_server.db.models import (
    CalendarSource,
    ExternalCalendar,
    RecordingCalendarContextLink,
    RecordingCalendarMatchAttempt,
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


def test_098_meeting_deletion_purges_or_scrubs_calendar_context_snapshot(client) -> None:
    # FR-019/FR-041, SC-014: deletion owns the synthetic meeting snapshot lifecycle.
    meeting = client.post(
        "/api/v1/meetings",
        headers=auth_headers(),
        json={"local_recording_id": "calendar-context-scrub-098", "duration_seconds": 900},
    )
    meeting_id = UUID(meeting.json()["meeting_id"])
    event_id = _seed_calendar_event(client)
    linked = client.put(
        f"/api/v1/meetings/{meeting_id}/calendar-context",
        headers=auth_headers(),
        json={"event_id": event_id, "context_reason": "manual_selection"},
    )
    before = _calendar_context_row(client, meeting_id)

    deletion = client.post(
        f"/api/v1/cabinet/meetings/{meeting_id}/deletion-requests",
        headers=auth_headers(),
        json={"confirmation_boundary": BOUNDED_DELETE_COPY},
    )
    after = _calendar_context_row(client, meeting_id)

    assert linked.status_code == 200
    assert before is not None
    assert before.matched_title == "Synthetic Planning Sync"
    assert before.matched_roster_count == 2
    assert deletion.status_code == 202
    assert (
        "calendar_context_deletion_accounted",
        "meeting_deleted",
    ) in _calendar_activity(client, meeting_id)
    if after is not None:
        assert after.context_state == "deleted"
        assert after.calendar_event_snapshot_id is None
        assert after.candidate_event_ids_json == []
        assert after.matched_event_starts_at is None
        assert after.matched_event_ends_at is None
        assert after.matched_title is None
        assert after.matched_title_state == "unavailable"
        assert after.matched_roster_json == []
        assert after.matched_roster_state == "not_available"
        assert after.matched_roster_count == 0
        assert after.recurring_series_key_sha256 is None
        assert after.source_version_fingerprint_sha256 is None


def test_098_meeting_deletion_purges_or_scrubs_consumed_match_attempt(client) -> None:
    # FR-041/FR-052: consumed synthetic match evidence cannot outlive meeting deletion unsanitized.
    local_recording_id = "calendar-attempt-scrub-098"
    meeting = client.post(
        "/api/v1/meetings",
        headers=auth_headers(),
        json={"local_recording_id": local_recording_id, "duration_seconds": 900},
    )
    meeting_id = UUID(meeting.json()["meeting_id"])
    event_id = UUID(_seed_calendar_event(client))
    linked = client.put(
        f"/api/v1/meetings/{meeting_id}/calendar-context",
        headers=auth_headers(),
        json={"event_id": str(event_id), "context_reason": "manual_selection"},
    )
    attempt_id = _attach_consumed_attempt(
        client,
        meeting_id=meeting_id,
        local_recording_id=local_recording_id,
        event_id=event_id,
    )

    deletion = client.post(
        f"/api/v1/cabinet/meetings/{meeting_id}/deletion-requests",
        headers=auth_headers(),
        json={"confirmation_boundary": BOUNDED_DELETE_COPY},
    )
    attempt = _calendar_attempt_row(client, attempt_id)

    assert linked.status_code == 200
    assert deletion.status_code == 202
    if attempt is not None:
        assert attempt.selected_event_snapshot_id is None
        assert attempt.candidate_event_ids_json == []
        assert attempt.candidate_count == 0
        assert attempt.matched_event_snapshot_id is None
        assert attempt.matched_event_starts_at is None
        assert attempt.matched_event_ends_at is None
        assert attempt.matched_title is None
        assert attempt.matched_title_state == "unavailable"
        assert attempt.matched_roster_json == []
        assert attempt.matched_roster_state == "not_available"
        assert attempt.matched_roster_count == 0
        assert attempt.recurring_series_key_sha256 is None
        assert attempt.source_version_fingerprint_sha256 is None


def _seed_calendar_event(client) -> str:
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

    async def seed() -> str:
        async with sessionmaker() as session:
            source = await session.get(CalendarSource, source_id)
            calendar = await session.scalar(
                select(ExternalCalendar).where(ExternalCalendar.calendar_source_id == source.id)
            )
            starts_at = datetime.now(UTC) + timedelta(minutes=5)
            snapshot = await upsert_event_snapshot(
                session,
                tenant_scope=client.app_state.get("tenant_scope") or _tenant_scope(),
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


def _calendar_link_state(client, meeting_id: UUID) -> tuple[str, bool]:
    sessionmaker = client.app_state["sessionmaker"]

    async def read() -> tuple[str, bool]:
        async with sessionmaker() as session:
            link = await session.scalar(
                select(RecordingCalendarContextLink).where(
                    RecordingCalendarContextLink.meeting_id == meeting_id
                )
            )
            return link.manual_override_state, link.unlinked_at is not None

    return asyncio.run(read())


def _calendar_context_row(client, meeting_id: UUID) -> RecordingCalendarContextLink | None:
    sessionmaker = client.app_state["sessionmaker"]

    async def read() -> RecordingCalendarContextLink | None:
        async with sessionmaker() as session:
            return await session.scalar(
                select(RecordingCalendarContextLink).where(
                    RecordingCalendarContextLink.meeting_id == meeting_id
                )
            )

    return asyncio.run(read())


def _calendar_activity(client, meeting_id: UUID) -> list[tuple[str, str]]:
    sessionmaker = client.app_state["sessionmaker"]

    async def read() -> list[tuple[str, str]]:
        async with sessionmaker() as session:
            projections = await calendar_context_activity_projections(
                session,
                workspace_id=WORKSPACE_ID,
                meeting_id=meeting_id,
            )
            return [(projection.event_type, projection.reason) for projection in projections]

    return asyncio.run(read())


def _attach_consumed_attempt(
    client,
    *,
    meeting_id: UUID,
    local_recording_id: str,
    event_id: UUID,
) -> UUID:
    sessionmaker = client.app_state["sessionmaker"]

    async def seed() -> UUID:
        async with sessionmaker() as session:
            now = datetime.now(UTC).replace(microsecond=0)
            attempt = RecordingCalendarMatchAttempt(
                workspace_id=WORKSPACE_ID,
                owner_user_id=USER_ID,
                device_id=DEVICE_ID,
                local_recording_id=local_recording_id,
                idempotency_key_sha256="a" * 64,
                request_fingerprint_sha256="b" * 64,
                recording_started_at=now,
                decision_intent="user_selected",
                selected_event_snapshot_id=event_id,
                attempt_state="matched_user",
                safe_reason_code="user_selected",
                context_confidence="selected",
                candidate_event_ids_json=[str(event_id)],
                candidate_count=1,
                matched_event_snapshot_id=event_id,
                matched_event_starts_at=now,
                matched_event_ends_at=now + timedelta(minutes=30),
                matched_title="Synthetic Planning Sync",
                matched_title_state="available",
                matched_roster_json=[
                    {
                        "participant_kind": "organizer",
                        "response_status": "organizer",
                        "display_name": "Synthetic Owner",
                        "email_present": True,
                        "workspace_relation": "owner",
                        "recipient_candidate_class": "organizer",
                    }
                ],
                matched_roster_state="available",
                matched_roster_count=1,
                recurring_series_key_sha256="c" * 64,
                source_version_fingerprint_sha256="d" * 64,
                freshness_class="current",
                matcher_version="calendar_auto_match_v1",
                evaluated_at=now,
                expires_at=now + timedelta(hours=24),
                consumed_by_meeting_id=meeting_id,
                consumed_at=now,
            )
            session.add(attempt)
            await session.flush()
            context = await session.scalar(
                select(RecordingCalendarContextLink).where(
                    RecordingCalendarContextLink.meeting_id == meeting_id
                )
            )
            assert context is not None
            context.match_attempt_id = attempt.id
            await session.commit()
            return attempt.id

    return asyncio.run(seed())


def _calendar_attempt_row(client, attempt_id: UUID) -> RecordingCalendarMatchAttempt | None:
    sessionmaker = client.app_state["sessionmaker"]

    async def read() -> RecordingCalendarMatchAttempt | None:
        async with sessionmaker() as session:
            return await session.get(RecordingCalendarMatchAttempt, attempt_id)

    return asyncio.run(read())


def _tenant_scope():
    from tests.fakes.auth_contexts import ORG_ID

    return TenantScope(
        organization_id=ORG_ID, workspace_id=WORKSPACE_ID, user_id=USER_ID, device_id=DEVICE_ID
    )
