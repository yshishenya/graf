from __future__ import annotations

import socket
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import UTC, datetime, timedelta
from importlib import import_module
from math import ceil
from time import perf_counter_ns
from urllib.parse import urlparse
from uuid import UUID, uuid4

import pytest
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from tests.contract.test_ingest_openapi_contract import auth_headers
from tests.fakes.auth_contexts import DEVICE_ID, ORG_ID, USER_ID, WORKSPACE_ID
from twobrain_rec_server.auth.context import TenantScope
from twobrain_rec_server.db.models import (
    CalendarAuditEvent,
    CalendarEventSnapshot,
    CalendarParticipant,
    CalendarSource,
    ConferenceLinkCandidate,
    ExternalCalendar,
    Meeting,
    Organization,
    RecordingCalendarContextLink,
    RecordingCalendarMatchAttempt,
    RegisteredDevice,
    UserIdentity,
    Workspace,
    WorkspaceMembership,
)

RESOLVE_PATH = "/api/v1/desktop/recordings/{local_recording_id}/calendar-context/resolve"
MATCHER_VERSION = "calendar_auto_match_v1"
SAFE_TITLE = "Synthetic Clear Planning"
FOREIGN_ORG_ID = UUID("10000000-0000-0000-0000-000000000098")
FOREIGN_WORKSPACE_ID = UUID("20000000-0000-0000-0000-000000000098")
FOREIGN_USER_ID = UUID("30000000-0000-0000-0000-000000000098")
FOREIGN_DEVICE_ID = UUID("40000000-0000-0000-0000-000000000098")


def _tenant_scope() -> TenantScope:
    return TenantScope(
        organization_id=ORG_ID,
        workspace_id=WORKSPACE_ID,
        user_id=USER_ID,
        device_id=DEVICE_ID,
    )


def _matching_api():
    module = import_module("twobrain_rec_server.calendar.matching")
    return (
        module.resolve_recording_calendar_context,
        module.consume_recording_calendar_match_attempt,
    )


def _resolve(
    client,
    *,
    local_recording_id: str,
    recording_started_at: datetime,
    idempotency_key: str,
):
    return client.post(
        RESOLVE_PATH.format(local_recording_id=local_recording_id),
        headers=auth_headers() | {"Idempotency-Key": idempotency_key},
        json={
            "recording_started_at": recording_started_at.isoformat(),
            "decision_intent": "automatic",
            "contract_version": "calendar_auto_context_v1",
        },
    )


def _create_meeting_for_attempt(
    client,
    *,
    local_recording_id: str,
    title: str,
    attempt_id: UUID,
    started_at: datetime,
    ended_at: datetime,
):
    return client.post(
        "/api/v1/meetings",
        headers=auth_headers(),
        json={
            "local_recording_id": local_recording_id,
            "duration_seconds": int((ended_at - started_at).total_seconds()),
            "title": title,
            "title_source": "app_context",
            "calendar_match_attempt_id": str(attempt_id),
            "started_at": started_at.isoformat(),
            "ended_at": ended_at.isoformat(),
        },
    )


def _load_attempt_context_truth(
    client,
    *,
    attempt_id: UUID,
    meeting_id: UUID,
) -> tuple[str, str | None, UUID | None, str, str | None, UUID | None, int]:
    async def load() -> tuple[str, str | None, UUID | None, str, str | None, UUID | None, int]:
        async with client.app_state["sessionmaker"]() as db:
            attempt = await db.get(RecordingCalendarMatchAttempt, attempt_id)
            context = await db.scalar(
                select(RecordingCalendarContextLink).where(
                    RecordingCalendarContextLink.workspace_id == WORKSPACE_ID,
                    RecordingCalendarContextLink.meeting_id == meeting_id,
                )
            )
            assert attempt is not None
            assert context is not None
            return (
                attempt.attempt_state,
                attempt.safe_reason_code,
                attempt.consumed_by_meeting_id,
                context.context_state,
                context.safe_reason_code,
                context.calendar_event_snapshot_id,
                context.matched_roster_count,
            )

    return client.portal.call(load)


def _p95_ms(samples_ns: list[int]) -> float:
    ordered = sorted(samples_ns)
    return ordered[ceil(len(ordered) * 0.95) - 1] / 1_000_000


def _seed_clear_calendar(
    client,
    *,
    recording_started_at: datetime,
    event_starts_at: datetime | None = None,
    event_ends_at: datetime | None = None,
    calendar_selected: bool = True,
    source_fresh: bool = True,
) -> UUID:
    async def seed() -> UUID:
        async with client.app_state["sessionmaker"]() as db:
            starts_at = event_starts_at or recording_started_at - timedelta(minutes=5)
            ends_at = event_ends_at or recording_started_at + timedelta(minutes=55)
            source = CalendarSource(
                workspace_id=WORKSPACE_ID,
                owner_user_id=USER_ID,
                provider_family="caldav_yandex",
                provider_label="Synthetic Calendar",
                auth_mode="app_password",
                credential_state="sealed",
                connection_state="active",
                sync_state="synced",
                sync_horizon_start=recording_started_at - timedelta(hours=1),
                sync_horizon_end=recording_started_at + timedelta(days=1),
                last_sync_finished_at=recording_started_at
                - (timedelta(minutes=1) if source_fresh else timedelta(days=2)),
                last_successful_sync_at=recording_started_at
                - (timedelta(minutes=1) if source_fresh else timedelta(days=2)),
                capabilities_json={},
                selected_calendar_count=1,
            )
            db.add(source)
            await db.flush()
            calendar = ExternalCalendar(
                workspace_id=WORKSPACE_ID,
                calendar_source_id=source.id,
                provider_calendar_id="synthetic-primary",
                display_label="Synthetic Work Calendar",
                visibility="available",
                selected=calendar_selected,
            )
            db.add(calendar)
            await db.flush()
            event = CalendarEventSnapshot(
                workspace_id=WORKSPACE_ID,
                calendar_source_id=source.id,
                external_calendar_id=calendar.id,
                provider_event_id="synthetic-clear-event",
                ical_uid="synthetic-clear-event@example.test",
                source_version="synthetic-v1",
                source_status="confirmed",
                starts_at=starts_at,
                ends_at=ends_at,
                duration_seconds=int((ends_at - starts_at).total_seconds()),
                all_day=False,
                title=SAFE_TITLE,
                description=None,
                location=None,
                privacy_class="public",
                conference_summary_json={"meeting_link_present": True},
                attachments_metadata_json=[],
                provider_extras_json={
                    "participant_count": 2,
                    "provider_family": "caldav_yandex",
                    "roster_state": "available",
                    "title_state": "available",
                },
                safe_to_show_in_list=True,
                safe_to_use_as_title=True,
                sensitivity_reasons_json=[],
                source_updated_at=recording_started_at - timedelta(minutes=1),
            )
            db.add(event)
            await db.flush()
            db.add_all(
                [
                    CalendarParticipant(
                        calendar_event_snapshot_id=event.id,
                        workspace_id=WORKSPACE_ID,
                        participant_kind="organizer",
                        response_status="organizer",
                        email="owner@example.test",
                        email_hash="sha256:synthetic-owner",
                        display_name="Synthetic Owner",
                        workspace_relation="owner",
                        recipient_candidate_class="organizer",
                    ),
                    CalendarParticipant(
                        calendar_event_snapshot_id=event.id,
                        workspace_id=WORKSPACE_ID,
                        participant_kind="required_attendee",
                        response_status="accepted",
                        email="attendee@example.test",
                        email_hash="sha256:synthetic-attendee",
                        display_name="Synthetic Attendee",
                        workspace_relation="external",
                        recipient_candidate_class="external_attendee",
                    ),
                    ConferenceLinkCandidate(
                        calendar_event_snapshot_id=event.id,
                        workspace_id=WORKSPACE_ID,
                        source_field="location",
                        provider_family="generic",
                        url_hash="sha256:synthetic-clear-link",
                        redacted_url_preview="meet.example.test/...",
                        contains_passcode=False,
                        sensitivity_class="meeting_link",
                    ),
                ]
            )
            await db.commit()
            return event.id

    return client.portal.call(seed)


def _seed_ambiguous_calendar(
    client,
    *,
    recording_started_at: datetime,
    scenario: str = "overlap",
) -> tuple[UUID, UUID]:
    async def seed() -> tuple[UUID, UUID]:
        async with client.app_state["sessionmaker"]() as db:
            source = CalendarSource(
                workspace_id=WORKSPACE_ID,
                owner_user_id=USER_ID,
                provider_family="caldav_yandex",
                provider_label="Synthetic Choice Calendar",
                auth_mode="app_password",
                credential_state="sealed",
                connection_state="active",
                sync_state="synced",
                sync_horizon_start=recording_started_at - timedelta(hours=1),
                sync_horizon_end=recording_started_at + timedelta(days=1),
                last_sync_finished_at=recording_started_at - timedelta(minutes=1),
                last_successful_sync_at=recording_started_at - timedelta(minutes=1),
                capabilities_json={},
                selected_calendar_count=1,
            )
            db.add(source)
            await db.flush()
            calendar = ExternalCalendar(
                workspace_id=WORKSPACE_ID,
                calendar_source_id=source.id,
                provider_calendar_id=f"synthetic-choice-{scenario}",
                display_label="Synthetic Choice Calendar",
                visibility="available",
                selected=True,
            )
            db.add(calendar)
            await db.flush()
            if scenario == "overlap":
                intervals = (
                    (
                        recording_started_at - timedelta(minutes=10),
                        recording_started_at + timedelta(minutes=20),
                    ),
                    (
                        recording_started_at - timedelta(minutes=5),
                        recording_started_at + timedelta(minutes=30),
                    ),
                )
            else:
                assert scenario == "back_to_back"
                intervals = (
                    (
                        recording_started_at - timedelta(minutes=30),
                        recording_started_at,
                    ),
                    (
                        recording_started_at,
                        recording_started_at + timedelta(minutes=30),
                    ),
                )
            events: list[CalendarEventSnapshot] = []
            for index, (starts_at, ends_at) in enumerate(intervals, start=1):
                event = CalendarEventSnapshot(
                    workspace_id=WORKSPACE_ID,
                    calendar_source_id=source.id,
                    external_calendar_id=calendar.id,
                    provider_event_id=f"synthetic-{scenario}-{index}-098",
                    ical_uid=f"synthetic-{scenario}-{index}-098@example.test",
                    source_version=f"synthetic-{scenario}-v{index}",
                    source_status="confirmed",
                    starts_at=starts_at,
                    ends_at=ends_at,
                    duration_seconds=int((ends_at - starts_at).total_seconds()),
                    all_day=False,
                    title=f"Synthetic Choice Event {index}",
                    description=None,
                    location=None,
                    privacy_class="public",
                    conference_summary_json={
                        "meeting_link_present": True,
                        "url_hash": f"sha256:synthetic-{scenario}-{index}",
                    },
                    attachments_metadata_json=[],
                    provider_extras_json={
                        "participant_count": 0,
                        "title_state": "available",
                    },
                    safe_to_show_in_list=True,
                    safe_to_use_as_title=True,
                    sensitivity_reasons_json=[],
                    source_updated_at=recording_started_at - timedelta(minutes=1),
                )
                db.add(event)
                events.append(event)
            await db.commit()
            return events[0].id, events[1].id

    return client.portal.call(seed)


def _meeting_model(*, local_recording_id: str, started_at: datetime) -> Meeting:
    return Meeting(
        workspace_id=WORKSPACE_ID,
        created_by_user_id=USER_ID,
        device_id=DEVICE_ID,
        local_recording_id=local_recording_id,
        title="Synthetic Local Recording",
        title_source="app_context",
        title_updated_at=started_at,
        started_at=started_at,
        ended_at=started_at + timedelta(minutes=30),
        duration_seconds=1800,
        status="draft",
        processing_status="not_submitted",
    )


def _matched_attempt(
    *,
    local_recording_id: str,
    event_id: UUID,
    recording_started_at: datetime,
    sequence: int,
) -> RecordingCalendarMatchAttempt:
    evaluated_at = recording_started_at + timedelta(seconds=2)
    return RecordingCalendarMatchAttempt(
        workspace_id=WORKSPACE_ID,
        owner_user_id=USER_ID,
        device_id=DEVICE_ID,
        local_recording_id=local_recording_id,
        idempotency_key_sha256=f"{sequence + 1:064x}",
        request_fingerprint_sha256=f"{sequence + 10_001:064x}",
        recording_started_at=recording_started_at,
        decision_intent="automatic",
        selected_event_snapshot_id=None,
        attempt_state="matched_auto",
        safe_reason_code="single_fresh_candidate",
        context_confidence="high",
        candidate_event_ids_json=[],
        candidate_count=1,
        matched_event_snapshot_id=event_id,
        matched_event_starts_at=recording_started_at - timedelta(minutes=5),
        matched_event_ends_at=recording_started_at + timedelta(minutes=55),
        matched_title=SAFE_TITLE,
        matched_title_state="available",
        matched_roster_json=[
            {
                "participant_kind": "organizer",
                "response_status": "organizer",
                "display_name": "Synthetic Owner",
                "email_present": True,
                "workspace_relation": "owner",
                "recipient_candidate_class": "organizer",
            },
            {
                "participant_kind": "required_attendee",
                "response_status": "accepted",
                "display_name": "Synthetic Attendee",
                "email_present": True,
                "workspace_relation": "external",
                "recipient_candidate_class": "external_attendee",
            },
        ],
        matched_roster_state="available",
        matched_roster_count=2,
        source_version_fingerprint_sha256="f" * 64,
        freshness_class="current",
        matcher_version=MATCHER_VERSION,
        evaluated_at=evaluated_at,
        expires_at=evaluated_at + timedelta(hours=24),
    )


def _seed_foreign_workspace_attempt(
    client,
    *,
    local_recording_id: str,
    event_id: UUID,
    recording_started_at: datetime,
) -> UUID:
    async def seed() -> UUID:
        async with client.app_state["sessionmaker"]() as db:
            db.add_all(
                [
                    Organization(
                        id=FOREIGN_ORG_ID,
                        slug="synthetic-foreign-org-098",
                        name="Synthetic Foreign Org",
                    ),
                    Workspace(
                        id=FOREIGN_WORKSPACE_ID,
                        organization_id=FOREIGN_ORG_ID,
                        slug="synthetic-foreign-workspace-098",
                        name="Synthetic Foreign Workspace",
                    ),
                    UserIdentity(
                        id=FOREIGN_USER_ID,
                        organization_id=FOREIGN_ORG_ID,
                        external_subject=str(FOREIGN_USER_ID),
                        display_name="Synthetic Foreign Owner",
                    ),
                ]
            )
            await db.flush()
            db.add_all(
                [
                    WorkspaceMembership(
                        workspace_id=FOREIGN_WORKSPACE_ID,
                        user_id=FOREIGN_USER_ID,
                        role="owner",
                        status="active",
                    ),
                    RegisteredDevice(
                        id=FOREIGN_DEVICE_ID,
                        workspace_id=FOREIGN_WORKSPACE_ID,
                        user_id=FOREIGN_USER_ID,
                        device_public_id="synthetic-foreign-device-098",
                        status="active",
                    ),
                ]
            )
            await db.flush()
            attempt = _matched_attempt(
                local_recording_id=local_recording_id,
                event_id=event_id,
                recording_started_at=recording_started_at,
                sequence=98,
            )
            attempt.workspace_id = FOREIGN_WORKSPACE_ID
            attempt.owner_user_id = FOREIGN_USER_ID
            attempt.device_id = FOREIGN_DEVICE_ID
            attempt.matched_title = "Synthetic Foreign Workspace Title"
            attempt.matched_roster_json = [
                {
                    "participant_kind": "organizer",
                    "response_status": "organizer",
                    "display_name": "Synthetic Foreign Participant",
                    "email_present": True,
                    "workspace_relation": "owner",
                    "recipient_candidate_class": "organizer",
                }
            ]
            attempt.matched_roster_count = 1
            db.add(attempt)
            await db.commit()
            return attempt.id

    return client.portal.call(seed)


async def _add_recurring_occurrence(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    owner_user_id: UUID,
    device_id: UUID,
    local_recording_id: str,
    title: str,
    started_at: datetime,
    series_key: str,
    context_state: str = "matched_auto",
    visibility: str = "owner_only",
    deletion_state: str = "none",
) -> UUID:
    meeting = Meeting(
        workspace_id=workspace_id,
        created_by_user_id=owner_user_id,
        device_id=device_id,
        local_recording_id=local_recording_id,
        title=title,
        title_source="calendar",
        title_updated_at=started_at,
        started_at=started_at,
        ended_at=started_at + timedelta(minutes=30),
        duration_seconds=1800,
        status="draft",
        processing_status="not_submitted",
        visibility=visibility,
        deletion_state=deletion_state,
    )
    db.add(meeting)
    await db.flush()
    db.add(
        RecordingCalendarContextLink(
            workspace_id=workspace_id,
            meeting_id=meeting.id,
            context_state=context_state,
            context_confidence="high",
            context_reasons_json=["synthetic_recurring_match"],
            title_source="calendar",
            roster_source="none",
            manual_override_state="none",
            safe_reason_code="single_fresh_candidate",
            decision_source=("user" if context_state == "matched_user" else "automatic"),
            matcher_version=MATCHER_VERSION,
            evaluated_at=started_at,
            candidate_event_ids_json=[],
            candidate_count=0,
            matched_event_starts_at=started_at,
            matched_event_ends_at=started_at + timedelta(minutes=30),
            matched_title=title,
            matched_title_state="available",
            matched_roster_json=[],
            matched_roster_state="not_available",
            matched_roster_count=0,
            recurring_series_key_sha256=series_key,
            source_version_fingerprint_sha256="e" * 64,
            linked_at=started_at,
        )
    )
    await db.flush()
    return meeting.id


def test_us1_clear_match_consumes_atomically_and_preserves_safe_title_roster_idempotency(
    client,
) -> None:
    # FR-001/FR-016/FR-017/FR-020/FR-027/FR-030, SC-011: consume retains only context truth.
    recording_started_at = datetime.now(UTC).replace(microsecond=0)
    event_id = _seed_clear_calendar(client, recording_started_at=recording_started_at)
    local_recording_id = "integration-clear-match-098"
    resolved = _resolve(
        client,
        local_recording_id=local_recording_id,
        recording_started_at=recording_started_at,
        idempotency_key="integration-clear-key-098",
    )
    assert resolved.status_code == 200
    assert resolved.json()["context_state"] == "matched_auto"
    payload = {
        "local_recording_id": local_recording_id,
        "duration_seconds": 1800,
        "title": "Synthetic Local Recording",
        "title_source": "app_context",
        "calendar_match_attempt_id": resolved.json()["attempt_id"],
        "started_at": recording_started_at.isoformat(),
        "ended_at": (recording_started_at + timedelta(minutes=30)).isoformat(),
    }

    created = client.post("/api/v1/meetings", headers=auth_headers(), json=payload)

    assert created.status_code == 200
    assert created.json()["title"] == SAFE_TITLE
    assert created.json()["title_source"] == "calendar"
    assert created.json()["calendar_context"] == {
        "state": "matched_auto",
        "label": "Из календаря",
        "title_source": "calendar",
        "needs_owner_action": False,
    }

    async def load_truth() -> tuple[
        Meeting, RecordingCalendarMatchAttempt, RecordingCalendarContextLink, tuple[int, int, int]
    ]:
        async with client.app_state["sessionmaker"]() as db:
            meeting = await db.get(Meeting, UUID(created.json()["meeting_id"]))
            attempt = await db.get(
                RecordingCalendarMatchAttempt,
                UUID(resolved.json()["attempt_id"]),
            )
            context = await db.scalar(
                select(RecordingCalendarContextLink).where(
                    RecordingCalendarContextLink.meeting_id == meeting.id
                )
            )
            counts = (
                int(await db.scalar(select(func.count()).select_from(Meeting)) or 0),
                int(
                    await db.scalar(select(func.count()).select_from(RecordingCalendarMatchAttempt))
                    or 0
                ),
                int(
                    await db.scalar(select(func.count()).select_from(RecordingCalendarContextLink))
                    or 0
                ),
            )
            assert meeting is not None
            assert attempt is not None
            assert context is not None
            return meeting, attempt, context, counts

    meeting, attempt, context, counts = client.portal.call(load_truth)
    assert counts == (1, 1, 1)
    assert meeting.title == SAFE_TITLE
    assert meeting.title_source == "calendar"
    assert attempt.attempt_state == "matched_auto"
    assert attempt.safe_reason_code == "single_fresh_candidate"
    assert attempt.consumed_by_meeting_id == meeting.id
    assert attempt.evaluated_at is not None
    assert attempt.expires_at is not None
    assert attempt.consumed_at is not None
    assert attempt.created_at is not None
    assert attempt.updated_at is not None
    assert attempt.selected_event_snapshot_id is None
    assert attempt.matched_event_snapshot_id is None
    assert attempt.candidate_event_ids_json == []
    assert attempt.candidate_count == 0
    assert attempt.matched_event_starts_at is None
    assert attempt.matched_event_ends_at is None
    assert attempt.matched_title is None
    assert attempt.matched_title_state == "unavailable"
    assert attempt.matched_roster_json == []
    assert attempt.matched_roster_state == "not_available"
    assert attempt.matched_roster_count == 0
    assert attempt.recurring_series_key_sha256 is None
    assert attempt.source_version_fingerprint_sha256 is None
    assert context.match_attempt_id == attempt.id
    assert context.calendar_event_snapshot_id == event_id
    assert context.context_state == "matched_auto"
    assert context.matched_event_starts_at is not None
    assert context.matched_event_ends_at is not None
    assert context.matched_title == SAFE_TITLE
    assert context.matched_roster_state == "available"
    assert context.matched_roster_count == 2
    assert context.source_version_fingerprint_sha256 is not None
    assert len(context.matched_roster_json) == 2
    assert all("email" not in item for item in context.matched_roster_json)
    assert "owner@example.test" not in created.text
    assert "attendee@example.test" not in created.text

    repeated = client.post("/api/v1/meetings", headers=auth_headers(), json=payload)
    assert repeated.status_code == 200
    assert repeated.json()["meeting_id"] == created.json()["meeting_id"]
    assert client.portal.call(load_truth)[3] == counts


@pytest.mark.parametrize(
    (
        "case_id",
        "meeting_minutes",
        "expected_state",
        "expected_reason",
        "expected_title",
        "expected_title_source",
        "expected_roster_count",
    ),
    [
        (
            "reaches-event-start",
            20,
            "matched_auto",
            "single_fresh_candidate",
            SAFE_TITLE,
            "calendar",
            2,
        ),
        (
            "stops-before-event-start",
            3,
            "no_context",
            "prestart_not_reached",
            "Synthetic Provisional Recording",
            "app_context",
            0,
        ),
    ],
    ids=("reaches-event-start", "stops-before-event-start"),
)
def test_us1_us2_persisted_provisional_prestart_is_finalized_when_consumed(
    client,
    case_id: str,
    meeting_minutes: int,
    expected_state: str,
    expected_reason: str,
    expected_title: str,
    expected_title_source: str,
    expected_roster_count: int,
) -> None:
    # FR-002/FR-005/FR-013/FR-016/FR-017/FR-032, SC-001/SC-010: finalize on consume.
    recording_started_at = datetime.now(UTC).replace(microsecond=0)
    event_id = _seed_clear_calendar(
        client,
        recording_started_at=recording_started_at,
        event_starts_at=recording_started_at + timedelta(minutes=4),
        event_ends_at=recording_started_at + timedelta(minutes=60),
    )
    local_recording_id = f"integration-prestart-{case_id}-098"
    resolved = _resolve(
        client,
        local_recording_id=local_recording_id,
        recording_started_at=recording_started_at,
        idempotency_key=f"integration-prestart-{case_id}-key-098",
    )

    assert resolved.status_code == 200
    assert resolved.json()["context_state"] == "provisional_prestart"
    assert resolved.json()["reason_code"] == "single_fresh_candidate"
    attempt_id = UUID(resolved.json()["attempt_id"])
    created = _create_meeting_for_attempt(
        client,
        local_recording_id=local_recording_id,
        title="Synthetic Provisional Recording",
        attempt_id=attempt_id,
        started_at=recording_started_at,
        ended_at=recording_started_at + timedelta(minutes=meeting_minutes),
    )

    assert created.status_code == 200
    assert created.json()["title"] == expected_title
    assert created.json()["title_source"] == expected_title_source
    meeting_id = UUID(created.json()["meeting_id"])
    expected_event_id = event_id if expected_state == "matched_auto" else None
    assert _load_attempt_context_truth(
        client,
        attempt_id=attempt_id,
        meeting_id=meeting_id,
    ) == (
        expected_state,
        expected_reason,
        meeting_id,
        expected_state,
        expected_reason,
        expected_event_id,
        expected_roster_count,
    )


@pytest.mark.parametrize(
    ("calendar_state", "expected_reason"),
    [
        ("not_connected", "calendar_not_connected"),
        ("not_selected", "calendar_not_selected"),
    ],
)
def test_us2_no_connected_or_selected_calendar_resolve_then_create_is_non_blocking(
    client,
    calendar_state: str,
    expected_reason: str,
) -> None:
    # FR-013/FR-032/FR-049, SC-010/SC-015: calendar absence adds no blocking step.
    recording_started_at = datetime.now(UTC).replace(microsecond=0)
    if calendar_state == "not_selected":
        _seed_clear_calendar(
            client,
            recording_started_at=recording_started_at,
            calendar_selected=False,
        )
    local_recording_id = f"integration-calendar-{calendar_state}-098"
    local_title = "Synthetic Ordinary Recording"
    resolved = _resolve(
        client,
        local_recording_id=local_recording_id,
        recording_started_at=recording_started_at,
        idempotency_key=f"integration-calendar-{calendar_state}-key-098",
    )

    assert resolved.status_code == 200
    assert resolved.json()["context_state"] == "calendar_unavailable"
    assert resolved.json()["reason_code"] == expected_reason
    assert resolved.json()["candidate_count"] == 0
    attempt_id = UUID(resolved.json()["attempt_id"])

    created = _create_meeting_for_attempt(
        client,
        local_recording_id=local_recording_id,
        title=local_title,
        attempt_id=attempt_id,
        started_at=recording_started_at,
        ended_at=recording_started_at + timedelta(minutes=15),
    )

    assert created.status_code == 200
    assert created.json()["title"] == local_title
    assert created.json()["title_source"] == "app_context"
    assert created.json()["calendar_context"] == {
        "state": "calendar_unavailable",
        "label": "Без контекста календаря",
        "title_source": "app_context",
        "needs_owner_action": False,
    }
    meeting_id = UUID(created.json()["meeting_id"])

    assert _load_attempt_context_truth(
        client,
        attempt_id=attempt_id,
        meeting_id=meeting_id,
    ) == (
        "calendar_unavailable",
        expected_reason,
        meeting_id,
        "calendar_unavailable",
        expected_reason,
        None,
        0,
    )


def test_us1_resolve_reads_snapshots_without_provider_network_io(
    client,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    # FR-003/FR-031: live resolve is bounded local DB work only.
    recording_started_at = datetime.now(UTC).replace(microsecond=0)
    _seed_clear_calendar(client, recording_started_at=recording_started_at)

    original_create_connection = socket.create_connection
    original_connect = socket.socket.connect
    postgres_port = urlparse(client.app.state.settings.database_url).port
    assert postgres_port is not None

    def is_local_postgres(address: object) -> bool:
        return (
            isinstance(address, tuple)
            and len(address) >= 2
            and address[0] in {"127.0.0.1", "::1", "localhost"}
            and address[1] == postgres_port
        )

    def reject_create_connection(address, *args, **kwargs):
        if is_local_postgres(address):
            return original_create_connection(address, *args, **kwargs)
        raise AssertionError("calendar resolve attempted provider/network I/O")

    def reject_connect(sock, address):
        if is_local_postgres(address):
            return original_connect(sock, address)
        raise AssertionError("calendar resolve attempted provider/network I/O")

    monkeypatch.setattr(socket, "create_connection", reject_create_connection)
    monkeypatch.setattr(socket.socket, "connect", reject_connect)

    resolved = _resolve(
        client,
        local_recording_id="integration-no-provider-io-098",
        recording_started_at=recording_started_at,
        idempotency_key="integration-no-provider-key-098",
    )

    assert resolved.status_code == 200
    assert resolved.json()["context_state"] == "matched_auto"


def test_us2_recovered_meeting_without_live_attempt_skips_calendar_and_keeps_title(
    client,
) -> None:
    # FR-002/FR-012/FR-032, SC-004/SC-010: recovery cannot rematch from upload time.
    recording_started_at = datetime.now(UTC).replace(microsecond=0)
    _seed_clear_calendar(client, recording_started_at=recording_started_at)
    local_recording_id = "integration-recovered-without-attempt-098"
    recovery_title = "Synthetic Recovered Queue Title"

    created = client.post(
        "/api/v1/meetings",
        headers=auth_headers(),
        json={
            "local_recording_id": local_recording_id,
            "duration_seconds": 1200,
            "title": recovery_title,
            "title_source": "app_context",
            "started_at": recording_started_at.isoformat(),
            "ended_at": (recording_started_at + timedelta(minutes=20)).isoformat(),
        },
    )

    assert created.status_code == 200
    assert created.json()["title"] == recovery_title
    assert created.json()["title_source"] == "app_context"
    assert created.json()["calendar_context"] == {
        "state": "skipped_offline_or_unknown",
        "label": "Без контекста календаря",
        "title_source": "app_context",
        "needs_owner_action": False,
    }

    async def load_context() -> tuple[RecordingCalendarContextLink | None, int]:
        async with client.app_state["sessionmaker"]() as db:
            meeting_id = UUID(created.json()["meeting_id"])
            context = await db.scalar(
                select(RecordingCalendarContextLink).where(
                    RecordingCalendarContextLink.meeting_id == meeting_id
                )
            )
            attempt_count = int(
                await db.scalar(select(func.count()).select_from(RecordingCalendarMatchAttempt))
                or 0
            )
            return context, attempt_count

    context, attempt_count = client.portal.call(load_context)
    assert context is not None
    assert context.context_state == "skipped_offline_or_unknown"
    assert context.safe_reason_code == "offline_or_unknown_skipped"
    assert context.calendar_event_snapshot_id is None
    assert context.match_attempt_id is None
    assert context.candidate_count == 0
    assert context.matched_title is None
    assert context.matched_roster_json == []
    assert attempt_count == 0


def test_us2_foreign_workspace_attempt_is_indistinguishable_from_unknown_attempt(
    client,
) -> None:
    # FR-004/FR-012/FR-030, SC-005/SC-011: an opaque cross-space ID leaks no truth.
    recording_started_at = datetime.now(UTC).replace(microsecond=0)
    event_id = _seed_clear_calendar(client, recording_started_at=recording_started_at)
    foreign_local_id = "integration-foreign-attempt-098"
    unknown_local_id = "integration-unknown-attempt-098"
    foreign_attempt_id = _seed_foreign_workspace_attempt(
        client,
        local_recording_id=foreign_local_id,
        event_id=event_id,
        recording_started_at=recording_started_at,
    )
    unknown_attempt_id = uuid4()

    def create(local_recording_id: str, attempt_id: UUID):
        return client.post(
            "/api/v1/meetings",
            headers=auth_headers(),
            json={
                "local_recording_id": local_recording_id,
                "duration_seconds": 900,
                "title": "Synthetic Recovery Title",
                "title_source": "app_context",
                "calendar_match_attempt_id": str(attempt_id),
                "started_at": recording_started_at.isoformat(),
                "ended_at": (recording_started_at + timedelta(minutes=15)).isoformat(),
            },
        )

    foreign = create(foreign_local_id, foreign_attempt_id)
    unknown = create(unknown_local_id, unknown_attempt_id)

    assert foreign.status_code == unknown.status_code == 200
    expected_context = {
        "state": "skipped_offline_or_unknown",
        "label": "Без контекста календаря",
        "title_source": "app_context",
        "needs_owner_action": False,
    }
    assert foreign.json()["calendar_context"] == expected_context
    assert unknown.json()["calendar_context"] == expected_context
    assert foreign.json()["title"] == unknown.json()["title"] == "Synthetic Recovery Title"
    serialized = foreign.text + unknown.text
    assert str(foreign_attempt_id) not in serialized
    assert "Synthetic Foreign Workspace Title" not in serialized
    assert "Synthetic Foreign Participant" not in serialized

    async def load_truth() -> tuple[
        RecordingCalendarMatchAttempt | None, list[RecordingCalendarContextLink]
    ]:
        async with client.app_state["sessionmaker"]() as db:
            attempt = await db.get(RecordingCalendarMatchAttempt, foreign_attempt_id)
            meeting_ids = [
                UUID(foreign.json()["meeting_id"]),
                UUID(unknown.json()["meeting_id"]),
            ]
            contexts = list(
                await db.scalars(
                    select(RecordingCalendarContextLink)
                    .where(RecordingCalendarContextLink.meeting_id.in_(meeting_ids))
                    .order_by(RecordingCalendarContextLink.meeting_id)
                )
            )
            return attempt, contexts

    foreign_attempt, contexts = client.portal.call(load_truth)
    assert foreign_attempt is not None
    assert foreign_attempt.consumed_by_meeting_id is None
    assert foreign_attempt.consumed_at is None
    assert len(contexts) == 2
    assert all(context.workspace_id == WORKSPACE_ID for context in contexts)
    assert all(context.context_state == "skipped_offline_or_unknown" for context in contexts)
    assert all(context.match_attempt_id is None for context in contexts)


@pytest.mark.parametrize(
    ("scenario", "expected_reason"),
    [
        ("overlap", "multiple_time_candidates"),
        ("back_to_back", "back_to_back_boundary"),
    ],
)
def test_us3_ambiguous_boundaries_never_attach_an_arbitrary_event(
    client,
    scenario: str,
    expected_reason: str,
) -> None:
    # FR-014/FR-027/FR-037, SC-003/SC-013: overlap/boundary remains unlinked.
    recording_started_at = datetime.now(UTC).replace(microsecond=0)
    event_ids = _seed_ambiguous_calendar(
        client,
        recording_started_at=recording_started_at,
        scenario=scenario,
    )
    local_recording_id = f"integration-{scenario}-choice-098"
    resolved = _resolve(
        client,
        local_recording_id=local_recording_id,
        recording_started_at=recording_started_at,
        idempotency_key=f"integration-{scenario}-choice-key-098",
    )

    assert resolved.status_code == 200
    assert resolved.json()["context_state"] == "ambiguous"
    assert resolved.json()["reason_code"] == expected_reason
    assert resolved.json()["candidate_count"] == 2
    created = client.post(
        "/api/v1/meetings",
        headers=auth_headers(),
        json={
            "local_recording_id": local_recording_id,
            "duration_seconds": 900,
            "title": "Synthetic Ambiguous Recording",
            "title_source": "app_context",
            "calendar_match_attempt_id": resolved.json()["attempt_id"],
            "started_at": recording_started_at.isoformat(),
            "ended_at": (recording_started_at + timedelta(minutes=15)).isoformat(),
        },
    )

    assert created.status_code == 200
    assert created.json()["title"] == "Synthetic Ambiguous Recording"
    assert created.json()["title_source"] == "app_context"
    assert created.json()["calendar_context"]["state"] == "ambiguous"

    async def load_context() -> RecordingCalendarContextLink | None:
        async with client.app_state["sessionmaker"]() as db:
            return await db.scalar(
                select(RecordingCalendarContextLink).where(
                    RecordingCalendarContextLink.meeting_id == UUID(created.json()["meeting_id"])
                )
            )

    context = client.portal.call(load_context)
    assert context is not None
    assert context.calendar_event_snapshot_id is None
    assert context.context_state == "ambiguous"
    assert context.safe_reason_code == expected_reason
    assert set(context.candidate_event_ids_json) == {str(value) for value in event_ids}
    assert context.candidate_count == 2
    assert context.matched_title is None
    assert context.matched_roster_json == []


def test_us3_back_to_back_owner_can_select_the_recently_ended_candidate(client) -> None:
    # FR-014/FR-015/FR-038: every safe boundary candidate shown to the owner is actionable.
    recording_started_at = datetime.now(UTC).replace(microsecond=0)
    event_ids = _seed_ambiguous_calendar(
        client,
        recording_started_at=recording_started_at,
        scenario="back_to_back",
    )
    local_recording_id = "integration-back-to-back-ended-choice-098"
    resolved = _resolve(
        client,
        local_recording_id=local_recording_id,
        recording_started_at=recording_started_at,
        idempotency_key="integration-back-to-back-ended-choice-key-098",
    )
    created = client.post(
        "/api/v1/meetings",
        headers=auth_headers(),
        json={
            "local_recording_id": local_recording_id,
            "duration_seconds": 900,
            "title": "Synthetic Boundary Recording",
            "title_source": "app_context",
            "calendar_match_attempt_id": resolved.json()["attempt_id"],
            "started_at": recording_started_at.isoformat(),
            "ended_at": (recording_started_at + timedelta(minutes=15)).isoformat(),
        },
    )

    selected = client.put(
        f"/api/v1/meetings/{created.json()['meeting_id']}/calendar-context",
        headers=auth_headers(),
        json={
            "event_id": str(event_ids[0]),
            "context_reason": "ambiguity_resolution",
        },
    )

    assert resolved.status_code == 200
    assert resolved.json()["reason_code"] == "back_to_back_boundary"
    assert created.status_code == 200
    assert selected.status_code == 200
    assert selected.json()["event_id"] == str(event_ids[0])
    assert selected.json()["context_state"] == "matched_user"


def test_us3_explicit_selection_and_retry_replace_ambiguity_once(client) -> None:
    # FR-015/FR-027/FR-038, SC-013/SC-014: retry preserves one user-selected row.
    recording_started_at = datetime.now(UTC).replace(microsecond=0)
    event_ids = _seed_ambiguous_calendar(
        client,
        recording_started_at=recording_started_at,
    )
    local_recording_id = "integration-ambiguity-selection-retry-098"
    resolved = _resolve(
        client,
        local_recording_id=local_recording_id,
        recording_started_at=recording_started_at,
        idempotency_key="integration-ambiguity-selection-retry-key-098",
    )
    created = client.post(
        "/api/v1/meetings",
        headers=auth_headers(),
        json={
            "local_recording_id": local_recording_id,
            "duration_seconds": 1200,
            "title": "Synthetic Choice Recording",
            "title_source": "app_context",
            "calendar_match_attempt_id": resolved.json()["attempt_id"],
            "started_at": recording_started_at.isoformat(),
            "ended_at": (recording_started_at + timedelta(minutes=20)).isoformat(),
        },
    )
    meeting_id = UUID(created.json()["meeting_id"])
    path = f"/api/v1/meetings/{meeting_id}/calendar-context"
    payload = {
        "event_id": str(event_ids[1]),
        "context_reason": "ambiguity_resolution",
    }

    selected = client.put(path, headers=auth_headers(), json=payload)
    retried = client.put(path, headers=auth_headers(), json=payload)

    assert selected.status_code == retried.status_code == 200
    assert retried.json() == selected.json()

    async def load_truth() -> tuple[list[RecordingCalendarContextLink], list[CalendarAuditEvent]]:
        async with client.app_state["sessionmaker"]() as db:
            contexts = list(
                await db.scalars(
                    select(RecordingCalendarContextLink).where(
                        RecordingCalendarContextLink.workspace_id == WORKSPACE_ID,
                        RecordingCalendarContextLink.meeting_id == meeting_id,
                    )
                )
            )
            audits = list(
                await db.scalars(
                    select(CalendarAuditEvent).where(
                        CalendarAuditEvent.workspace_id == WORKSPACE_ID,
                        CalendarAuditEvent.meeting_id == meeting_id,
                        CalendarAuditEvent.outcome == "matched_user",
                    )
                )
            )
            return contexts, audits

    contexts, audits = client.portal.call(load_truth)
    assert len(contexts) == 1
    context = contexts[0]
    assert context.calendar_event_snapshot_id == event_ids[1]
    assert context.context_state == "matched_user"
    assert context.safe_reason_code == "user_selected"
    assert context.decision_source == "user"
    assert context.candidate_event_ids_json == []
    assert selected.json()["context_state"] == "matched_user"
    assert len(audits) == 2
    assert all(audit.safe_reason_code == "user_selected" for audit in audits)


def test_us3_recording_start_explicit_choice_can_resolve_stale_safe_snapshot(client) -> None:
    # FR-028: stale data blocks automatic choice but may require and accept owner selection.
    recording_started_at = datetime.now(UTC).replace(microsecond=0)
    event_id = _seed_clear_calendar(
        client,
        recording_started_at=recording_started_at,
        source_fresh=False,
    )

    response = client.post(
        RESOLVE_PATH.format(local_recording_id="explicit-stale-choice-098"),
        headers=auth_headers() | {"Idempotency-Key": "explicit-stale-choice-key-098"},
        json={
            "recording_started_at": recording_started_at.isoformat(),
            "decision_intent": "user_selected",
            "event_id": str(event_id),
            "contract_version": "calendar_auto_context_v1",
        },
    )

    assert response.status_code == 200
    assert response.json()["context_state"] == "matched_user"
    assert response.json()["reason_code"] == "user_selected"
    assert response.json()["context_confidence"] == "selected"


@pytest.mark.parametrize(
    "unsafe_case",
    ["private", "all_day", "cancelled", "deleted", "zero_duration", "weak_signal"],
)
def test_us3_explicit_selection_rejects_every_unsafe_candidate_class(
    client,
    unsafe_case: str,
) -> None:
    # FR-009/FR-014/FR-037/FR-038: an owner-supplied ID never bypasses eligibility.
    recording_started_at = datetime.now(UTC).replace(microsecond=0)
    event_id = _seed_clear_calendar(client, recording_started_at=recording_started_at)

    async def make_event_unsafe() -> None:
        async with client.app_state["sessionmaker"]() as db:
            event = await db.get(CalendarEventSnapshot, event_id)
            assert event is not None
            if unsafe_case == "private":
                event.privacy_class = "private"
            elif unsafe_case == "all_day":
                event.all_day = True
            elif unsafe_case == "cancelled":
                event.source_status = "cancelled"
            elif unsafe_case == "deleted":
                event.source_deleted_at = recording_started_at
            elif unsafe_case == "zero_duration":
                event.ends_at = event.starts_at
                event.duration_seconds = 0
            else:
                assert unsafe_case == "weak_signal"
                event.location = None
                event.conference_summary_json = {}
                event.provider_extras_json = {"title_state": "available"}
                await db.execute(
                    delete(CalendarParticipant).where(
                        CalendarParticipant.calendar_event_snapshot_id == event_id
                    )
                )
                await db.execute(
                    delete(ConferenceLinkCandidate).where(
                        ConferenceLinkCandidate.calendar_event_snapshot_id == event_id
                    )
                )
            await db.commit()

    client.portal.call(make_event_unsafe)
    meeting = client.post(
        "/api/v1/meetings",
        headers=auth_headers(),
        json={
            "local_recording_id": f"integration-unsafe-owner-choice-{unsafe_case}-098",
            "duration_seconds": 900,
            "title": "Synthetic Protected Owner Title",
            "title_source": "user_confirmed",
            "started_at": recording_started_at.isoformat(),
        },
    )
    assert meeting.status_code == 200

    selected = client.put(
        f"/api/v1/meetings/{meeting.json()['meeting_id']}/calendar-context",
        headers=auth_headers(),
        json={"event_id": str(event_id), "context_reason": "correction"},
    )

    assert selected.status_code == 409
    assert selected.json()["code"] == "calendar_event_not_linkable"

    async def load_truth() -> tuple[str, UUID | None, str | None]:
        async with client.app_state["sessionmaker"]() as db:
            meeting_row = await db.get(Meeting, UUID(meeting.json()["meeting_id"]))
            context = await db.scalar(
                select(RecordingCalendarContextLink).where(
                    RecordingCalendarContextLink.meeting_id == meeting_row.id
                )
            )
            assert context is not None
            return context.context_state, context.calendar_event_snapshot_id, meeting_row.title

    context_state, linked_event_id, title = client.portal.call(load_truth)
    assert context_state != "matched_user"
    assert linked_event_id is None
    assert title == "Synthetic Protected Owner Title"


def test_us3_start_decline_and_later_clear_remain_distinct_terminal_states(client) -> None:
    # FR-029/FR-038/FR-039/FR-051, SC-014: decline-at-start is never a later clear.
    recording_started_at = datetime.now(UTC).replace(microsecond=0)
    declined_local_id = "integration-start-declined-098"
    declined = client.post(
        RESOLVE_PATH.format(local_recording_id=declined_local_id),
        headers=auth_headers() | {"Idempotency-Key": "integration-start-declined-key-098"},
        json={
            "recording_started_at": recording_started_at.isoformat(),
            "decision_intent": "user_declined",
            "contract_version": "calendar_auto_context_v1",
        },
    )
    assert declined.status_code == 200
    assert declined.json()["context_state"] == "declined_by_user"
    declined_meeting = client.post(
        "/api/v1/meetings",
        headers=auth_headers(),
        json={
            "local_recording_id": declined_local_id,
            "duration_seconds": 900,
            "calendar_match_attempt_id": declined.json()["attempt_id"],
            "started_at": recording_started_at.isoformat(),
            "ended_at": (recording_started_at + timedelta(minutes=15)).isoformat(),
        },
    )
    assert declined_meeting.status_code == 200
    assert declined_meeting.json()["calendar_context"]["state"] == "declined_by_user"

    event_ids = _seed_ambiguous_calendar(
        client,
        recording_started_at=recording_started_at,
    )
    clear_meeting = client.post(
        "/api/v1/meetings",
        headers=auth_headers(),
        json={
            "local_recording_id": "integration-later-cleared-098",
            "duration_seconds": 900,
            "started_at": recording_started_at.isoformat(),
            "ended_at": (recording_started_at + timedelta(minutes=15)).isoformat(),
        },
    )
    clear_meeting_id = UUID(clear_meeting.json()["meeting_id"])
    path = f"/api/v1/meetings/{clear_meeting_id}/calendar-context"
    selected = client.put(
        path,
        headers=auth_headers(),
        json={
            "event_id": str(event_ids[0]),
            "context_reason": "ambiguity_resolution",
        },
    )
    cleared = client.delete(path, headers=auth_headers())
    automatic_retry = _resolve(
        client,
        local_recording_id=declined_local_id,
        recording_started_at=recording_started_at,
        idempotency_key="integration-auto-after-decline-key-098",
    )

    assert selected.status_code == 200
    assert cleared.status_code == 200
    assert automatic_retry.status_code == 409

    async def load_states() -> tuple[RecordingCalendarContextLink, RecordingCalendarContextLink]:
        async with client.app_state["sessionmaker"]() as db:
            declined_context = await db.scalar(
                select(RecordingCalendarContextLink).where(
                    RecordingCalendarContextLink.meeting_id
                    == UUID(declined_meeting.json()["meeting_id"])
                )
            )
            cleared_context = await db.scalar(
                select(RecordingCalendarContextLink).where(
                    RecordingCalendarContextLink.meeting_id == clear_meeting_id
                )
            )
            assert declined_context is not None
            assert cleared_context is not None
            return declined_context, cleared_context

    declined_context, cleared_context = client.portal.call(load_states)
    assert declined_context.context_state == "declined_by_user"
    assert declined_context.manual_override_state == "declined_by_user"
    assert cleared_context.context_state == "cleared_by_user"
    assert cleared_context.manual_override_state != "declined_by_user"
    assert declined_context.calendar_event_snapshot_id is None
    assert cleared_context.calendar_event_snapshot_id is None
    assert cleared.json()["context_state"] == "cleared_by_user"
    assert cleared.json()["reason_code"] == "user_cleared"

    declined_detail = client.get(
        f"/api/v1/cabinet/meetings/{declined_meeting.json()['meeting_id']}",
        headers=auth_headers(),
    )
    cleared_detail = client.get(
        f"/api/v1/cabinet/meetings/{clear_meeting_id}",
        headers=auth_headers(),
    )
    assert declined_detail.status_code == cleared_detail.status_code == 200
    assert declined_detail.json()["calendar_context"]["state"] == "declined_by_user"
    assert declined_detail.json()["calendar_context"]["label"] == (
        "Вы начали запись без календарного контекста"
    )
    assert cleared_detail.json()["calendar_context"]["state"] == "cleared_by_user"
    assert cleared_detail.json()["calendar_context"]["label"] == "Контекст убран вами"


def test_us3_concurrent_owner_selections_keep_one_authoritative_row_and_two_audits(
    client,
) -> None:
    # FR-027/FR-029/FR-038, SC-014: racing owner choices serialize into one row.
    recording_started_at = datetime.now(UTC).replace(microsecond=0)
    event_ids = _seed_ambiguous_calendar(
        client,
        recording_started_at=recording_started_at,
    )
    meeting = client.post(
        "/api/v1/meetings",
        headers=auth_headers(),
        json={
            "local_recording_id": "integration-concurrent-owner-choice-098",
            "duration_seconds": 1200,
            "started_at": recording_started_at.isoformat(),
            "ended_at": (recording_started_at + timedelta(minutes=20)).isoformat(),
        },
    )
    meeting_id = UUID(meeting.json()["meeting_id"])
    path = f"/api/v1/meetings/{meeting_id}/calendar-context"

    def select_event(event_id: UUID):
        return client.put(
            path,
            headers=auth_headers(),
            json={
                "event_id": str(event_id),
                "context_reason": "ambiguity_resolution",
            },
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(select_event, event_id) for event_id in event_ids]
        responses = [future.result() for future in as_completed(futures)]

    assert len(responses) == 2
    assert all(response.status_code == 200 for response in responses)

    async def load_truth() -> tuple[list[RecordingCalendarContextLink], list[CalendarAuditEvent]]:
        async with client.app_state["sessionmaker"]() as db:
            contexts = list(
                await db.scalars(
                    select(RecordingCalendarContextLink).where(
                        RecordingCalendarContextLink.workspace_id == WORKSPACE_ID,
                        RecordingCalendarContextLink.meeting_id == meeting_id,
                    )
                )
            )
            audits = list(
                await db.scalars(
                    select(CalendarAuditEvent).where(
                        CalendarAuditEvent.workspace_id == WORKSPACE_ID,
                        CalendarAuditEvent.meeting_id == meeting_id,
                        CalendarAuditEvent.outcome == "matched_user",
                    )
                )
            )
            return contexts, audits

    contexts, audits = client.portal.call(load_truth)
    assert len(contexts) == 1
    assert contexts[0].context_state == "matched_user"
    assert contexts[0].calendar_event_snapshot_id in set(event_ids)
    assert len(audits) == 2


@pytest.mark.parametrize(
    ("requested_source", "expected_title", "expected_source"),
    [
        ("app_context", SAFE_TITLE, "calendar"),
        ("generic", SAFE_TITLE, "calendar"),
        ("user_confirmed", "Synthetic User Recording Title", "user_confirmed"),
        ("unknown", "Synthetic User Recording Title", "legacy_unknown"),
    ],
)
def test_us4_automatic_match_obeys_desktop_title_precedence(
    client,
    requested_source: str,
    expected_title: str,
    expected_source: str,
) -> None:
    # FR-017/FR-018/FR-035, SC-001/SC-007: provenance decides title replacement.
    recording_started_at = datetime.now(UTC).replace(microsecond=0)
    event_id = _seed_clear_calendar(client, recording_started_at=recording_started_at)
    local_recording_id = f"integration-auto-title-precedence-{requested_source}-098"
    resolved = _resolve(
        client,
        local_recording_id=local_recording_id,
        recording_started_at=recording_started_at,
        idempotency_key=f"integration-auto-title-precedence-{requested_source}-key-098",
    )
    created = client.post(
        "/api/v1/meetings",
        headers=auth_headers(),
        json={
            "local_recording_id": local_recording_id,
            "duration_seconds": 1200,
            "title": "Synthetic User Recording Title",
            "title_source": requested_source,
            "calendar_match_attempt_id": resolved.json()["attempt_id"],
            "started_at": recording_started_at.isoformat(),
            "ended_at": (recording_started_at + timedelta(minutes=20)).isoformat(),
        },
    )

    assert created.status_code == 200
    assert created.json()["title"] == expected_title
    assert created.json()["title_source"] == expected_source
    assert created.json()["calendar_context"]["state"] == "matched_auto"

    async def load_truth() -> tuple[Meeting, RecordingCalendarContextLink]:
        async with client.app_state["sessionmaker"]() as db:
            meeting = await db.get(Meeting, UUID(created.json()["meeting_id"]))
            assert meeting is not None
            context = await db.scalar(
                select(RecordingCalendarContextLink).where(
                    RecordingCalendarContextLink.meeting_id == meeting.id
                )
            )
            assert context is not None
            return meeting, context

    meeting, context = client.portal.call(load_truth)
    assert meeting.title == expected_title
    assert meeting.title_source == expected_source
    assert context.calendar_event_snapshot_id == event_id
    assert context.title_source == expected_source


@pytest.mark.parametrize(
    "authoritative_source",
    ["user_confirmed", "upload_provided", "file_name_derived", "legacy_unknown"],
)
def test_us4_authoritative_titles_survive_calendar_correction_and_clear(
    client,
    authoritative_source: str,
) -> None:
    # FR-017/FR-018/FR-035/FR-038/FR-039, SC-007: provenance outranks correction.
    recording_started_at = datetime.now(UTC).replace(microsecond=0)
    event_id = _seed_clear_calendar(client, recording_started_at=recording_started_at)
    local_recording_id = f"integration-title-precedence-{authoritative_source}-098"
    resolved = _resolve(
        client,
        local_recording_id=local_recording_id,
        recording_started_at=recording_started_at,
        idempotency_key=f"integration-title-precedence-{authoritative_source}-key-098",
    )
    created = client.post(
        "/api/v1/meetings",
        headers=auth_headers(),
        json={
            "local_recording_id": local_recording_id,
            "duration_seconds": 1200,
            "title": "Synthetic Replaceable App Title",
            "title_source": "app_context",
            "calendar_match_attempt_id": resolved.json()["attempt_id"],
            "started_at": recording_started_at.isoformat(),
            "ended_at": (recording_started_at + timedelta(minutes=20)).isoformat(),
        },
    )
    assert created.status_code == 200
    assert created.json()["title_source"] == "calendar"
    meeting_id = UUID(created.json()["meeting_id"])
    authoritative_title = f"Synthetic Authoritative {authoritative_source} Title"

    async def set_authoritative_title() -> None:
        async with client.app_state["sessionmaker"]() as db:
            meeting = await db.get(Meeting, meeting_id)
            assert meeting is not None
            meeting.title = authoritative_title
            meeting.title_source = authoritative_source
            meeting.title_updated_at = datetime.now(UTC)
            await db.commit()

    client.portal.call(set_authoritative_title)
    path = f"/api/v1/meetings/{meeting_id}/calendar-context"
    corrected = client.put(
        path,
        headers=auth_headers(),
        json={"event_id": str(event_id), "context_reason": "correction"},
    )

    async def load_title() -> tuple[str | None, str]:
        async with client.app_state["sessionmaker"]() as db:
            meeting = await db.get(Meeting, meeting_id)
            assert meeting is not None
            return meeting.title, meeting.title_source

    assert corrected.status_code == 200
    assert corrected.json()["context_state"] == "matched_user"
    assert corrected.json()["title_source"] == authoritative_source
    assert client.portal.call(load_title) == (authoritative_title, authoritative_source)

    cleared = client.delete(path, headers=auth_headers())

    assert cleared.status_code == 200
    assert cleared.json()["context_state"] == "cleared_by_user"
    assert cleared.json()["title_source"] == authoritative_source
    assert client.portal.call(load_title) == (authoritative_title, authoritative_source)

    async def load_context() -> RecordingCalendarContextLink | None:
        async with client.app_state["sessionmaker"]() as db:
            return await db.scalar(
                select(RecordingCalendarContextLink).where(
                    RecordingCalendarContextLink.workspace_id == WORKSPACE_ID,
                    RecordingCalendarContextLink.meeting_id == meeting_id,
                )
            )

    context = client.portal.call(load_context)
    assert context is not None
    assert context.context_state == "cleared_by_user"
    assert context.title_source == authoritative_source
    assert context.calendar_event_snapshot_id is None
    assert context.matched_title is None
    assert context.matched_roster_json == []


def test_us4_calendar_correction_then_clear_keeps_latest_visible_title_on_retry(
    client,
) -> None:
    # FR-018/FR-019/FR-027/FR-038/FR-039, SC-006/SC-014: clear is not a rename.
    recording_started_at = datetime.now(UTC).replace(microsecond=0)
    _seed_clear_calendar(client, recording_started_at=recording_started_at)
    local_recording_id = "integration-calendar-correction-clear-title-098"
    resolved = _resolve(
        client,
        local_recording_id=local_recording_id,
        recording_started_at=recording_started_at,
        idempotency_key="integration-calendar-correction-clear-title-key-098",
    )
    create_payload = {
        "local_recording_id": local_recording_id,
        "duration_seconds": 1200,
        "title": "Synthetic Replaceable Before Correction",
        "title_source": "app_context",
        "calendar_match_attempt_id": resolved.json()["attempt_id"],
        "started_at": recording_started_at.isoformat(),
        "ended_at": (recording_started_at + timedelta(minutes=20)).isoformat(),
    }
    created = client.post("/api/v1/meetings", headers=auth_headers(), json=create_payload)
    assert created.status_code == 200
    assert created.json()["title"] == SAFE_TITLE
    assert created.json()["title_source"] == "calendar"
    meeting_id = UUID(created.json()["meeting_id"])
    correction_events = _seed_ambiguous_calendar(
        client,
        recording_started_at=recording_started_at,
    )
    path = f"/api/v1/meetings/{meeting_id}/calendar-context"

    corrected = client.put(
        path,
        headers=auth_headers(),
        json={
            "event_id": str(correction_events[1]),
            "context_reason": "correction",
        },
    )
    assert corrected.status_code == 200
    assert corrected.json()["context_state"] == "matched_user"
    assert corrected.json()["title_source"] == "calendar"

    async def load_truth() -> tuple[Meeting, RecordingCalendarContextLink]:
        async with client.app_state["sessionmaker"]() as db:
            meeting = await db.get(Meeting, meeting_id)
            context = await db.scalar(
                select(RecordingCalendarContextLink).where(
                    RecordingCalendarContextLink.workspace_id == WORKSPACE_ID,
                    RecordingCalendarContextLink.meeting_id == meeting_id,
                )
            )
            assert meeting is not None
            assert context is not None
            return meeting, context

    corrected_meeting, corrected_context = client.portal.call(load_truth)
    assert corrected_meeting.title == "Synthetic Choice Event 2"
    assert corrected_meeting.title_source == "calendar"
    assert corrected_context.calendar_event_snapshot_id == correction_events[1]

    cleared = client.delete(path, headers=auth_headers())
    retried = client.post("/api/v1/meetings", headers=auth_headers(), json=create_payload)

    assert cleared.status_code == 200
    assert cleared.json()["context_state"] == "cleared_by_user"
    assert cleared.json()["title_source"] == "calendar"
    assert retried.status_code == 200
    assert retried.json()["meeting_id"] == str(meeting_id)
    assert retried.json()["title"] == "Synthetic Choice Event 2"
    assert retried.json()["title_source"] == "calendar"
    assert retried.json()["calendar_context"]["state"] == "cleared_by_user"

    final_meeting, final_context = client.portal.call(load_truth)
    assert final_meeting.title == "Synthetic Choice Event 2"
    assert final_meeting.title_source == "calendar"
    assert final_context.context_state == "cleared_by_user"
    assert final_context.calendar_event_snapshot_id is None
    assert final_context.matched_title is None
    assert final_context.matched_roster_json == []

    review = client.get(
        f"/api/v1/cabinet/meetings/{meeting_id}",
        headers=auth_headers(),
    )
    assert review.status_code == 200
    calendar_activity = [
        item
        for item in review.json()["activity"]["items"]
        if item["event_type"] == "calendar_context_owner_mutation"
    ]
    assert {item["reason"] for item in calendar_activity} == {
        "user_selected",
        "user_cleared",
    }
    assert {item["outcome"] for item in calendar_activity} == {"completed"}
    assert {item["artifact_class"] for item in calendar_activity} == {None}


def test_us5_authorized_recurring_pointer_uses_latest_earlier_same_series_only(
    client,
) -> None:
    # FR-024/FR-025/FR-045, SC-009: ordering is by the immutable occurrence time.
    current_started_at = datetime(2026, 7, 20, 12, 0, tzinfo=UTC)
    series_key = "1" * 64

    async def seed() -> tuple[UUID, UUID, UUID, UUID, UUID]:
        async with client.app_state["sessionmaker"]() as db:
            older_id = await _add_recurring_occurrence(
                db,
                workspace_id=WORKSPACE_ID,
                owner_user_id=USER_ID,
                device_id=DEVICE_ID,
                local_recording_id="recurring-older-authorized-098",
                title="Synthetic Older Series Occurrence",
                started_at=current_started_at - timedelta(days=14),
                series_key=series_key,
            )
            latest_id = await _add_recurring_occurrence(
                db,
                workspace_id=WORKSPACE_ID,
                owner_user_id=USER_ID,
                device_id=DEVICE_ID,
                local_recording_id="recurring-latest-authorized-098",
                title="Synthetic Latest Series Occurrence",
                started_at=current_started_at - timedelta(days=1),
                series_key=series_key,
                context_state="matched_user",
            )
            different_series_id = await _add_recurring_occurrence(
                db,
                workspace_id=WORKSPACE_ID,
                owner_user_id=USER_ID,
                device_id=DEVICE_ID,
                local_recording_id="recurring-different-series-098",
                title="Synthetic Different Series Occurrence",
                started_at=current_started_at - timedelta(minutes=1),
                series_key="2" * 64,
            )
            future_id = await _add_recurring_occurrence(
                db,
                workspace_id=WORKSPACE_ID,
                owner_user_id=USER_ID,
                device_id=DEVICE_ID,
                local_recording_id="recurring-future-occurrence-098",
                title="Synthetic Future Series Occurrence",
                started_at=current_started_at + timedelta(days=1),
                series_key=series_key,
            )
            current_id = await _add_recurring_occurrence(
                db,
                workspace_id=WORKSPACE_ID,
                owner_user_id=USER_ID,
                device_id=DEVICE_ID,
                local_recording_id="recurring-current-occurrence-098",
                title="Synthetic Current Series Occurrence",
                started_at=current_started_at,
                series_key=series_key,
            )
            await db.commit()
            return older_id, latest_id, different_series_id, future_id, current_id

    older_id, latest_id, different_series_id, future_id, current_id = client.portal.call(seed)
    response = client.get(
        f"/api/v1/meetings/{current_id}/calendar-context",
        headers=auth_headers(),
    )

    assert response.status_code == 200
    previous = response.json()["previous_recurring_meeting"]
    assert previous is not None
    assert previous["meeting_id"] == str(latest_id)
    assert previous["safe_title"] == "Synthetic Latest Series Occurrence"
    assert datetime.fromisoformat(previous["started_at"]) == current_started_at - timedelta(days=1)
    assert previous["readiness_state"] in {
        "notes_ready",
        "transcript_ready",
        "processing",
        "unavailable",
    }
    for unrelated_id in (older_id, different_series_id, future_id):
        assert str(unrelated_id) not in response.text
    for unrelated_title in (
        "Synthetic Older Series Occurrence",
        "Synthetic Different Series Occurrence",
        "Synthetic Future Series Occurrence",
    ):
        assert unrelated_title not in response.text


def test_us5_deleted_latest_recurring_predecessor_does_not_fall_back_or_leak(
    client,
) -> None:
    # FR-024–FR-026, SC-009: choose the latest earlier occurrence, then authorize it.
    current_started_at = datetime(2026, 7, 20, 12, 0, tzinfo=UTC)
    series_key = "3" * 64

    async def seed() -> tuple[UUID, UUID, UUID]:
        async with client.app_state["sessionmaker"]() as db:
            older_id = await _add_recurring_occurrence(
                db,
                workspace_id=WORKSPACE_ID,
                owner_user_id=USER_ID,
                device_id=DEVICE_ID,
                local_recording_id="recurring-older-before-deleted-098",
                title="Synthetic Older Visible Recurring Meeting",
                started_at=current_started_at - timedelta(days=14),
                series_key=series_key,
            )
            deleted_id = await _add_recurring_occurrence(
                db,
                workspace_id=WORKSPACE_ID,
                owner_user_id=USER_ID,
                device_id=DEVICE_ID,
                local_recording_id="recurring-deleted-latest-098",
                title="Synthetic Deleted Latest Recurring Meeting",
                started_at=current_started_at - timedelta(days=1),
                series_key=series_key,
                deletion_state="complete",
            )
            current_id = await _add_recurring_occurrence(
                db,
                workspace_id=WORKSPACE_ID,
                owner_user_id=USER_ID,
                device_id=DEVICE_ID,
                local_recording_id="recurring-current-after-deleted-098",
                title="Synthetic Current After Deleted",
                started_at=current_started_at,
                series_key=series_key,
            )
            await db.commit()
            return older_id, deleted_id, current_id

    older_id, deleted_id, current_id = client.portal.call(seed)
    response = client.get(
        f"/api/v1/meetings/{current_id}/calendar-context",
        headers=auth_headers(),
    )

    assert response.status_code == 200
    assert response.json()["previous_recurring_meeting"] is None
    for forbidden_value in (
        str(older_id),
        str(deleted_id),
        "Synthetic Older Visible Recurring Meeting",
        "Synthetic Deleted Latest Recurring Meeting",
    ):
        assert forbidden_value not in response.text


def test_us5_cross_workspace_and_other_active_space_predecessors_never_project(
    client,
) -> None:
    # FR-004/FR-024–FR-026, SC-005/SC-009: a hash collision cannot cross tenant space.
    current_started_at = datetime(2026, 7, 20, 12, 0, tzinfo=UTC)
    series_key = "4" * 64

    async def seed() -> tuple[UUID, UUID, UUID]:
        async with client.app_state["sessionmaker"]() as db:
            other_space_id = uuid4()
            other_space_device_id = uuid4()
            db.add(
                Organization(
                    id=FOREIGN_ORG_ID,
                    slug="synthetic-recurring-foreign-org-098",
                    name="Synthetic Recurring Foreign Org",
                )
            )
            await db.flush()
            db.add_all(
                [
                    Workspace(
                        id=other_space_id,
                        organization_id=ORG_ID,
                        slug="synthetic-recurring-other-space-098",
                        name="Synthetic Recurring Other Space",
                    ),
                    Workspace(
                        id=FOREIGN_WORKSPACE_ID,
                        organization_id=FOREIGN_ORG_ID,
                        slug="synthetic-recurring-foreign-workspace-098",
                        name="Synthetic Recurring Foreign Workspace",
                    ),
                    UserIdentity(
                        id=FOREIGN_USER_ID,
                        organization_id=FOREIGN_ORG_ID,
                        external_subject="synthetic-recurring-foreign-owner-098",
                        display_name="Synthetic Recurring Foreign Owner",
                    ),
                ]
            )
            await db.flush()
            db.add_all(
                [
                    WorkspaceMembership(
                        workspace_id=other_space_id,
                        user_id=USER_ID,
                        role="owner",
                        status="active",
                    ),
                    WorkspaceMembership(
                        workspace_id=FOREIGN_WORKSPACE_ID,
                        user_id=FOREIGN_USER_ID,
                        role="owner",
                        status="active",
                    ),
                    RegisteredDevice(
                        id=other_space_device_id,
                        workspace_id=other_space_id,
                        user_id=USER_ID,
                        device_public_id="synthetic-recurring-other-space-device-098",
                        status="active",
                    ),
                    RegisteredDevice(
                        id=FOREIGN_DEVICE_ID,
                        workspace_id=FOREIGN_WORKSPACE_ID,
                        user_id=FOREIGN_USER_ID,
                        device_public_id="synthetic-recurring-foreign-device-098",
                        status="active",
                    ),
                ]
            )
            await db.flush()
            other_space_meeting_id = await _add_recurring_occurrence(
                db,
                workspace_id=other_space_id,
                owner_user_id=USER_ID,
                device_id=other_space_device_id,
                local_recording_id="recurring-other-active-space-098",
                title="Synthetic Other Active Space Predecessor",
                started_at=current_started_at - timedelta(days=1),
                series_key=series_key,
            )
            foreign_workspace_meeting_id = await _add_recurring_occurrence(
                db,
                workspace_id=FOREIGN_WORKSPACE_ID,
                owner_user_id=FOREIGN_USER_ID,
                device_id=FOREIGN_DEVICE_ID,
                local_recording_id="recurring-foreign-workspace-098",
                title="Synthetic Foreign Workspace Predecessor",
                started_at=current_started_at - timedelta(days=2),
                series_key=series_key,
            )
            current_id = await _add_recurring_occurrence(
                db,
                workspace_id=WORKSPACE_ID,
                owner_user_id=USER_ID,
                device_id=DEVICE_ID,
                local_recording_id="recurring-current-space-boundary-098",
                title="Synthetic Current Space Boundary",
                started_at=current_started_at,
                series_key=series_key,
            )
            await db.commit()
            return other_space_meeting_id, foreign_workspace_meeting_id, current_id

    other_space_meeting_id, foreign_workspace_meeting_id, current_id = client.portal.call(seed)
    response = client.get(
        f"/api/v1/meetings/{current_id}/calendar-context",
        headers=auth_headers(),
    )

    assert response.status_code == 200
    assert response.json()["previous_recurring_meeting"] is None
    for forbidden_value in (
        str(other_space_meeting_id),
        str(foreign_workspace_meeting_id),
        "Synthetic Other Active Space Predecessor",
        "Synthetic Foreign Workspace Predecessor",
    ):
        assert forbidden_value not in response.text


def test_us1_consumption_accepts_before_expiry_and_rejects_exact_boundary(client) -> None:
    # FR-052: `consumed_at < expires_at`; equality is already expired.
    _, consume_recording_calendar_match_attempt = _matching_api()
    recording_started_at = datetime.now(UTC).replace(microsecond=0)
    event_id = _seed_clear_calendar(client, recording_started_at=recording_started_at)

    async def exercise_boundary() -> tuple[str, str, bool, bool]:
        async with client.app_state["sessionmaker"]() as db:
            before_meeting = _meeting_model(
                local_recording_id="expiry-before-098",
                started_at=recording_started_at,
            )
            boundary_meeting = _meeting_model(
                local_recording_id="expiry-boundary-098",
                started_at=recording_started_at,
            )
            before_attempt = _matched_attempt(
                local_recording_id=before_meeting.local_recording_id,
                event_id=event_id,
                recording_started_at=recording_started_at,
                sequence=1,
            )
            boundary_attempt = _matched_attempt(
                local_recording_id=boundary_meeting.local_recording_id,
                event_id=event_id,
                recording_started_at=recording_started_at,
                sequence=2,
            )
            db.add_all([before_meeting, boundary_meeting, before_attempt, boundary_attempt])
            await db.flush()

            before_context = await consume_recording_calendar_match_attempt(
                db,
                _tenant_scope(),
                meeting=before_meeting,
                attempt_id=before_attempt.id,
                consumed_at=before_attempt.expires_at - timedelta(microseconds=1),
            )
            boundary_context = await consume_recording_calendar_match_attempt(
                db,
                _tenant_scope(),
                meeting=boundary_meeting,
                attempt_id=boundary_attempt.id,
                consumed_at=boundary_attempt.expires_at,
            )
            await db.flush()
            return (
                before_context.context_state,
                boundary_context.context_state,
                before_attempt.consumed_by_meeting_id == before_meeting.id,
                boundary_attempt.consumed_by_meeting_id is None,
            )

    before_state, boundary_state, before_consumed, boundary_unconsumed = client.portal.call(
        exercise_boundary
    )

    assert before_state == "matched_auto"
    assert boundary_state == "skipped_offline_or_unknown"
    assert before_consumed is True
    assert boundary_unconsumed is True


@pytest.mark.serial_performance
def test_sc017_one_hundred_warmed_atomic_consumptions_are_within_50ms_p95(client) -> None:
    # SC-017: 100 measured same-transaction attempt consumptions after one warm-up.
    _, consume_recording_calendar_match_attempt = _matching_api()
    recording_started_at = datetime.now(UTC).replace(microsecond=0)
    event_id = _seed_clear_calendar(client, recording_started_at=recording_started_at)

    async def measure() -> list[int]:
        async with client.app_state["sessionmaker"]() as db:
            pairs: list[tuple[Meeting, RecordingCalendarMatchAttempt]] = []
            for index in range(101):
                local_recording_id = f"consumption-performance-{index:03d}-098"
                meeting = _meeting_model(
                    local_recording_id=local_recording_id,
                    started_at=recording_started_at,
                )
                attempt = _matched_attempt(
                    local_recording_id=local_recording_id,
                    event_id=event_id,
                    recording_started_at=recording_started_at,
                    sequence=10_000 + index,
                )
                pairs.append((meeting, attempt))
                db.add_all([meeting, attempt])
            await db.flush()

            warm_meeting, warm_attempt = pairs[0]
            warm_context = await consume_recording_calendar_match_attempt(
                db,
                _tenant_scope(),
                meeting=warm_meeting,
                attempt_id=warm_attempt.id,
                consumed_at=recording_started_at + timedelta(minutes=1),
            )
            await db.flush()
            assert warm_context.context_state == "matched_auto"

            samples_ns: list[int] = []
            for meeting, attempt in pairs[1:]:
                started = perf_counter_ns()
                context = await consume_recording_calendar_match_attempt(
                    db,
                    _tenant_scope(),
                    meeting=meeting,
                    attempt_id=attempt.id,
                    consumed_at=recording_started_at + timedelta(minutes=1),
                )
                await db.flush()
                samples_ns.append(perf_counter_ns() - started)
                assert context.context_state == "matched_auto"
            await db.rollback()
            return samples_ns

    samples_ns = client.portal.call(measure)

    p95_ms = _p95_ms(samples_ns)
    assert len(samples_ns) == 100
    assert p95_ms <= 50
