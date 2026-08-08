import asyncio
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select

from tests.contract.test_ingest_openapi_contract import auth_headers
from tests.fakes.auth_contexts import DEVICE_ID, ORG_ID, USER_ID, WORKSPACE_ID
from tests.fixtures.calendar import calendar_event_fixture
from twobrain_rec_server.auth.context import TenantScope
from twobrain_rec_server.calendar.lifecycle import purge_expired_unconsumed_match_attempts
from twobrain_rec_server.calendar.normalize import normalize_calendar_event
from twobrain_rec_server.calendar.sync import upsert_event_snapshot
from twobrain_rec_server.db.models import (
    CalendarCredentialEnvelope,
    CalendarEventSnapshot,
    CalendarSource,
    ExternalCalendar,
    RecordingCalendarContextLink,
    RecordingCalendarMatchAttempt,
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

    disconnected = client.post(
        f"/api/v1/calendar/sources/{source_id}/disconnect", headers=auth_headers()
    )
    state = _disconnect_state(client, source_id)

    assert disconnected.status_code == 200
    assert disconnected.json()["credentials_purged"] is True
    assert disconnected.json()["unmatched_future_cache_purged"] is True
    assert state["source"].connection_state == "disconnected"
    assert state["source"].credential_state == "purged"
    assert state["credential"].purged_at is not None
    assert state["future_event_count"] == 0


def test_098_disconnect_purges_unconsumed_attempt_with_unresolved_candidates(client) -> None:
    # FR-041/FR-052: unresolved synthetic candidate references purge with their source.
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
    event_id = _seed_future_event(client, source_id)
    attempt_id = _seed_unconsumed_attempt(client, event_id=event_id)
    meeting = client.post(
        "/api/v1/meetings",
        headers=auth_headers(),
        json={
            "local_recording_id": "calendar-disconnect-unresolved-context-098",
            "duration_seconds": 900,
        },
    )
    meeting_id = UUID(meeting.json()["meeting_id"])
    _seed_unresolved_context(client, meeting_id=meeting_id, event_id=event_id)

    disconnected = client.post(
        f"/api/v1/calendar/sources/{source_id}/disconnect",
        headers=auth_headers(),
    )
    state = _disconnect_match_state(
        client,
        event_id=event_id,
        attempt_id=attempt_id,
        meeting_id=meeting_id,
    )

    assert disconnected.status_code == 200
    assert state["event"] is None
    assert state["attempt"] is None
    assert state["context"].context_state == "calendar_unavailable"
    assert state["context"].candidate_event_ids_json == []
    assert state["context"].candidate_count == 0


def test_098_disconnect_purges_expired_unconsumed_attempt_at_ttl_boundary(client) -> None:
    # FR-052: an unconsumed attempt is purgeable at, not after, its exact expiry.
    exact_expiry = datetime.now(UTC).replace(microsecond=0) + timedelta(minutes=1)
    attempt_id = _seed_unconsumed_attempt(
        client,
        event_id=None,
        expires_at=exact_expiry,
    )

    purged = _purge_expired_attempts(client, expired_at=exact_expiry)

    assert purged == 1
    assert _match_attempt(client, attempt_id) is None


def test_098_disconnect_detaches_provider_cache_but_retains_safe_matched_context(client) -> None:
    # FR-016/FR-019/FR-041: only the synthetic meeting-owned safe snapshot survives disconnect.
    meeting = client.post(
        "/api/v1/meetings",
        headers=auth_headers(),
        json={"local_recording_id": "calendar-disconnect-retained-098", "duration_seconds": 900},
    )
    meeting_id = UUID(meeting.json()["meeting_id"])
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
    event_id = _seed_future_event(client, source_id)
    linked = client.put(
        f"/api/v1/meetings/{meeting_id}/calendar-context",
        headers=auth_headers(),
        json={"event_id": str(event_id), "context_reason": "manual_selection"},
    )

    disconnected = client.post(
        f"/api/v1/calendar/sources/{source_id}/disconnect",
        headers=auth_headers(),
    )
    state = _disconnect_matched_context_state(
        client,
        meeting_id=meeting_id,
        event_id=event_id,
    )

    assert linked.status_code == 200
    assert disconnected.status_code == 200
    assert disconnected.json()["matched_context_retention"] == "meeting_retention_policy"
    assert state["event"] is None
    context = state["context"]
    assert context is not None
    assert context.context_state == "matched_user"
    assert context.calendar_event_snapshot_id is None
    assert context.matched_title == "Synthetic Planning Sync"
    assert context.matched_roster_state == "available"
    assert context.matched_roster_count == 2
    assert context.candidate_event_ids_json == []


def _seed_future_event(client, source_id: UUID) -> UUID:
    sessionmaker = client.app_state["sessionmaker"]

    async def seed() -> UUID:
        async with sessionmaker() as session:
            source = await session.get(CalendarSource, source_id)
            calendar = await session.scalar(
                select(ExternalCalendar).where(ExternalCalendar.calendar_source_id == source.id)
            )
            starts_at = datetime.now(UTC) + timedelta(minutes=10)
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
                        description=None,
                        description_state="unavailable",
                        location=None,
                        attachments_metadata=[],
                        provider_extras={"raw_payload_retained": False},
                    )
                ),
            )
            await session.commit()
            return snapshot.id

    return asyncio.run(seed())


def _seed_unconsumed_attempt(
    client,
    *,
    event_id: UUID | None,
    expires_at: datetime | None = None,
) -> UUID:
    sessionmaker = client.app_state["sessionmaker"]

    async def seed() -> UUID:
        async with sessionmaker() as session:
            now = datetime.now(UTC).replace(microsecond=0)
            attempt = RecordingCalendarMatchAttempt(
                workspace_id=WORKSPACE_ID,
                owner_user_id=USER_ID,
                device_id=DEVICE_ID,
                local_recording_id="calendar-disconnect-attempt-098",
                idempotency_key_sha256="e" * 64,
                request_fingerprint_sha256="f" * 64,
                recording_started_at=now,
                decision_intent="automatic",
                attempt_state="ambiguous",
                safe_reason_code="multiple_time_candidates",
                context_confidence="ambiguous",
                candidate_event_ids_json=[str(event_id)] if event_id is not None else [],
                candidate_count=1 if event_id is not None else 0,
                matched_title_state="unavailable",
                matched_roster_json=[],
                matched_roster_state="not_available",
                matched_roster_count=0,
                freshness_class="current",
                matcher_version="calendar_auto_match_v1",
                evaluated_at=now,
                expires_at=expires_at or now + timedelta(hours=24),
            )
            session.add(attempt)
            await session.commit()
            return attempt.id

    return asyncio.run(seed())


def _match_attempt(client, attempt_id: UUID) -> RecordingCalendarMatchAttempt | None:
    sessionmaker = client.app_state["sessionmaker"]

    async def load() -> RecordingCalendarMatchAttempt | None:
        async with sessionmaker() as session:
            return await session.get(RecordingCalendarMatchAttempt, attempt_id)

    return asyncio.run(load())


def _purge_expired_attempts(client, *, expired_at: datetime) -> int:
    sessionmaker = client.app_state["sessionmaker"]

    async def purge() -> int:
        async with sessionmaker() as session:
            count = await purge_expired_unconsumed_match_attempts(
                session,
                workspace_id=WORKSPACE_ID,
                expired_at=expired_at,
            )
            await session.commit()
            return count

    return asyncio.run(purge())


def _disconnect_match_state(
    client,
    *,
    event_id: UUID,
    attempt_id: UUID,
    meeting_id: UUID,
) -> dict[str, object]:
    sessionmaker = client.app_state["sessionmaker"]

    async def load() -> dict[str, object]:
        async with sessionmaker() as session:
            return {
                "event": await session.get(CalendarEventSnapshot, event_id),
                "attempt": await session.get(RecordingCalendarMatchAttempt, attempt_id),
                "context": await session.scalar(
                    select(RecordingCalendarContextLink).where(
                        RecordingCalendarContextLink.meeting_id == meeting_id
                    )
                ),
            }

    return asyncio.run(load())


def _seed_unresolved_context(
    client,
    *,
    meeting_id: UUID,
    event_id: UUID,
) -> None:
    sessionmaker = client.app_state["sessionmaker"]

    async def seed() -> None:
        async with sessionmaker() as session:
            context = await session.scalar(
                select(RecordingCalendarContextLink).where(
                    RecordingCalendarContextLink.meeting_id == meeting_id
                )
            )
            assert context is not None
            context.context_state = "ambiguous"
            context.context_confidence = "ambiguous"
            context.context_reasons_json = ["multiple_time_candidates"]
            context.safe_reason_code = "multiple_time_candidates"
            context.decision_source = "automatic"
            context.candidate_event_ids_json = [str(event_id)]
            context.candidate_count = 1
            await session.commit()

    asyncio.run(seed())


def _disconnect_matched_context_state(
    client,
    *,
    meeting_id: UUID,
    event_id: UUID,
) -> dict[str, object]:
    sessionmaker = client.app_state["sessionmaker"]

    async def load() -> dict[str, object]:
        async with sessionmaker() as session:
            return {
                "event": await session.get(CalendarEventSnapshot, event_id),
                "context": await session.scalar(
                    select(RecordingCalendarContextLink).where(
                        RecordingCalendarContextLink.meeting_id == meeting_id
                    )
                ),
            }

    return asyncio.run(load())


def _disconnect_state(client, source_id: UUID) -> dict[str, object]:
    sessionmaker = client.app_state["sessionmaker"]

    async def load() -> dict[str, object]:
        async with sessionmaker() as session:
            source = await session.get(CalendarSource, source_id)
            credential = await session.scalar(
                select(CalendarCredentialEnvelope).where(
                    CalendarCredentialEnvelope.calendar_source_id == source_id
                )
            )
            future_events = await session.scalars(
                select(CalendarEventSnapshot).where(
                    CalendarEventSnapshot.calendar_source_id == source_id
                )
            )
            return {
                "source": source,
                "credential": credential,
                "future_event_count": len(list(future_events)),
            }

    return asyncio.run(load())
