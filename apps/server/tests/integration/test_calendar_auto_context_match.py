from __future__ import annotations

import asyncio
import json
import os
import socket
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import replace
from datetime import UTC, datetime, timedelta
from functools import partial
from hashlib import sha256
from importlib import import_module
from math import ceil
from time import perf_counter_ns
from urllib.parse import urlparse
from uuid import UUID, uuid4

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from sqlalchemy import delete, func, select
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from tests.contract.test_ingest_openapi_contract import auth_headers
from tests.fakes.auth_contexts import DEVICE_ID, ORG_ID, REVOKED_DEVICE_ID, USER_ID, WORKSPACE_ID
from tests.fixtures.artifacts import track_descriptor
from twobrain_rec_server.auth.context import TenantScope
from twobrain_rec_server.auth.sessions import issue_auth_session
from twobrain_rec_server.db.models import (
    AuthSessionDeviceBinding,
    CalendarAuditEvent,
    CalendarEventSnapshot,
    CalendarParticipant,
    CalendarSource,
    ConferenceLinkCandidate,
    ExternalCalendar,
    IngestAuditEvent,
    MediaRevision,
    Meeting,
    Organization,
    ProcessingPlaceholder,
    PurgeJournal,
    RecordingCalendarContextLink,
    RecordingCalendarMatchAttempt,
    RegisteredDevice,
    TemporaryUploadObject,
    TrackArtifact,
    UploadPart,
    UploadSession,
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
    if p95_ms > 50 and os.environ.get("GRAF_PERFORMANCE_GATE", "required") == "report":
        pytest.xfail(f"shared-host timing report: p95={p95_ms:.2f}ms exceeds 50ms")
    assert p95_ms <= 50


@pytest.mark.parametrize(
    ("intent", "state"),
    [("user_selected", "matched_user"), ("user_declined", "declined_by_user")],
)
def test_desktop_sync_calendar_match_receipt_after_lost_create_response(
    client, monkeypatch, intent: str, state: str,
) -> None:
    started = datetime.now(UTC).replace(microsecond=0)
    recording_id = str(uuid4())
    other_device = uuid4()
    headers = auth_headers()
    body = {
        "recording_started_at": started.isoformat(),
        "decision_intent": intent,
        "contract_version": "calendar_auto_context_v1",
    }
    if intent == "user_selected":
        body["event_id"] = str(_seed_clear_calendar(client, recording_started_at=started))
    resolved = client.post(
        RESOLVE_PATH.format(local_recording_id=recording_id),
        headers=headers | {"Idempotency-Key": f"calendar-receipt-{recording_id}"},
        json=body,
    )
    assert resolved.status_code == 200
    attempt_id = resolved.json()["attempt_id"]
    # Deliberately ignore the successful create body; recovery uses only sync-state.
    assert _create_meeting_for_attempt(
        client,
        local_recording_id=recording_id,
        title="Synthetic recording",
        attempt_id=UUID(attempt_id),
        started_at=started,
        ended_at=started + timedelta(seconds=60),
    ).status_code == 200

    path = f"/api/v1/desktop/recordings/{recording_id}/sync-state"
    legacy = client.get(path, headers=headers)
    assert legacy.status_code == 200
    assert "calendar_match_receipt" not in legacy.json()
    # Server-copy proof is fresh for every sync response, including legacy callers.
    assert legacy.headers.get("Cache-Control") == "no-store"
    meeting_id = UUID(legacy.json()["meeting"]["meeting_id"])

    async def age_receipt_and_seed_device() -> str:
        async with client.app_state["sessionmaker"]() as db:
            attempt = await db.get(RecordingCalendarMatchAttempt, UUID(attempt_id))
            assert attempt is not None and attempt.consumed_at is not None
            assert attempt.matched_event_snapshot_id is None
            attempt.consumed_at = started - timedelta(days=2)
            attempt.expires_at = started - timedelta(days=1)
            db.add(RegisteredDevice(
                id=other_device,
                workspace_id=WORKSPACE_ID,
                user_id=USER_ID,
                device_public_id="calendar-receipt-other-device",
                status="active",
            ))
            issued = await issue_auth_session(
                db, workspace_id=WORKSPACE_ID, user_id=USER_ID, provider="receipt-test",
                device_id=DEVICE_ID, now=started,
            )
            db.add(AuthSessionDeviceBinding(
                auth_session_id=issued.id, registered_device_id=DEVICE_ID, device_state="trusted",
            ))
            await db.commit()
            return issued.token

    token = client.portal.call(age_receipt_and_seed_device)
    session_headers = {"Authorization": f"Bearer {token}"}
    params = {"include_calendar_match_receipt": "true"}
    recovery = client.get(path, headers=session_headers, params=params)
    assert recovery.status_code == 200
    assert recovery.headers["Cache-Control"] == "no-store"
    recovered = recovery.json()
    receipt = {"attempt_id": attempt_id, "state": state}
    assert recovered.pop("calendar_match_receipt") == receipt
    assert recovered == legacy.json()

    if intent == "user_selected":
        cleared = client.delete(f"/api/v1/meetings/{meeting_id}/calendar-context", headers=headers)
        assert cleared.status_code == 200
        assert cleared.json()["context_state"] == "cleared_by_user"
        historical = client.get(path, headers=headers, params=params)
        assert historical.status_code == 200
        assert historical.json()["calendar_match_receipt"] == receipt

    wrong_device = client.get(path, headers=headers | {"X-Device-Id": str(other_device)}, params=params)
    assert wrong_device.status_code == 200
    assert "calendar_match_receipt" not in wrong_device.json()
    revoked = client.get(path, headers=headers | {"X-Device-Id": str(REVOKED_DEVICE_ID)}, params=params)
    assert revoked.status_code == 403
    assert revoked.headers["Cache-Control"] == "no-store"
    wrong_revision = client.get(
        path, headers=headers, params=params | {"local_media_revision_id": "different-revision"},
    )
    assert wrong_revision.status_code == 200
    assert "calendar_match_receipt" not in wrong_revision.json()
    wrong_recording = client.get(
        f"/api/v1/desktop/recordings/{uuid4()}/sync-state", headers=headers, params=params,
    )
    assert wrong_recording.status_code == 404
    assert wrong_recording.headers["Cache-Control"] == "no-store"
    assert "calendar_match_receipt" not in wrong_recording.json()

    upload = client.post(
        f"/api/v1/meetings/{meeting_id}/upload-sessions",
        headers=headers,
        json={"expected_track_sizes": {"manifest": 8, "media": 9, "playback": 10}},
    )
    assert upload.status_code == 200

    async def expire_upload_session() -> None:
        async with client.app_state["sessionmaker"]() as db:
            session = await db.get(UploadSession, UUID(upload.json()["session_id"]))
            assert session is not None
            session.expires_at = started - timedelta(seconds=1)
            await db.commit()

    client.portal.call(expire_upload_session)
    expired_upload = client.get(path, headers=session_headers, params=params)
    assert expired_upload.status_code == 200
    assert expired_upload.json()["conflict"]["state"] == "upload_session_expired"
    assert expired_upload.json()["calendar_match_receipt"] == receipt

    async def fence_meeting() -> None:
        async with client.app_state["sessionmaker"]() as db:
            meeting = await db.get(Meeting, meeting_id)
            assert meeting is not None
            meeting.deleted_at = started
            await db.commit()

    client.portal.call(fence_meeting)
    deleting = client.get(path, headers=headers, params=params)
    assert deleting.status_code == 200
    assert "calendar_match_receipt" not in deleting.json()

    # Restore this synthetic tombstone, then mutate after the sync projection
    # but before the receipt SELECT. The original response still names the
    # old revision; the receipt must independently decline to confirm it.
    async def restore_meeting() -> None:
        async with client.app_state["sessionmaker"]() as db:
            meeting = await db.get(Meeting, meeting_id)
            assert meeting is not None
            meeting.deleted_at = None
            await db.commit()

    client.portal.call(restore_meeting)
    module = import_module("twobrain_rec_server.ingest.desktop_sync")
    read_receipt = module.calendar_match_receipt

    async def mutate_before_receipt(db, **kwargs):
        async with client.app_state["sessionmaker"]() as writer:
            if intent == "user_selected":
                writer.add(MediaRevision(
                    workspace_id=WORKSPACE_ID, meeting_id=meeting_id,
                    local_media_revision_id=f"{recording_id}--replacement",
                    revision_number=2, status="accepted",
                ))
            else:
                device = await writer.get(RegisteredDevice, DEVICE_ID)
                assert device is not None
                device.status = "revoked"
            await writer.commit()
        return await read_receipt(db, **kwargs)

    monkeypatch.setattr(module, "calendar_match_receipt", mutate_before_receipt)
    raced = client.get(path, headers=session_headers, params=params)
    assert raced.status_code == 200
    assert raced.json()["local_media_revision_id"] == f"{recording_id}--initial"
    assert "calendar_match_receipt" not in raced.json()


def test_desktop_sync_calendar_match_receipt_omits_unconsumed_expired_attempt(client) -> None:
    started = datetime.now(UTC).replace(microsecond=0)
    recording_id = str(uuid4())
    resolved = client.post(
        RESOLVE_PATH.format(local_recording_id=recording_id),
        headers=auth_headers() | {"Idempotency-Key": f"calendar-receipt-{recording_id}"},
        json={
            "recording_started_at": started.isoformat(),
            "decision_intent": "user_declined",
            "contract_version": "calendar_auto_context_v1",
        },
    )
    assert resolved.status_code == 200
    attempt_id = UUID(resolved.json()["attempt_id"])

    async def expire() -> None:
        async with client.app_state["sessionmaker"]() as db:
            attempt = await db.get(RecordingCalendarMatchAttempt, attempt_id)
            assert attempt is not None
            attempt.expires_at = started - timedelta(seconds=1)
            await db.commit()

    client.portal.call(expire)
    # Existing clients still get their historical fallback; it never proves a decline.
    created = _create_meeting_for_attempt(
        client,
        local_recording_id=recording_id,
        title="Synthetic recording",
        attempt_id=attempt_id,
        started_at=started,
        ended_at=started + timedelta(seconds=60),
    )
    assert created.status_code == 200
    assert created.json()["calendar_context"]["state"] != "declined_by_user"
    recovery = client.get(
        f"/api/v1/desktop/recordings/{recording_id}/sync-state",
        headers=auth_headers(),
        params={"include_calendar_match_receipt": "true"},
    )
    assert recovery.status_code == 200
    assert "calendar_match_receipt" not in recovery.json()


STRICT_CREATE_PATH = "/api/v1/desktop/meetings/with-calendar-context"


def _strict_calendar_create_body(client, *, intent: str):
    started = datetime.now(UTC).replace(microsecond=0)
    recording_id = str(uuid4())
    resolve_body = {
        "recording_started_at": started.isoformat(),
        "decision_intent": intent,
        "contract_version": "calendar_auto_context_v1",
    }
    if intent == "user_selected":
        resolve_body["event_id"] = str(_seed_clear_calendar(client, recording_started_at=started))
    resolved = client.post(
        RESOLVE_PATH.format(local_recording_id=recording_id),
        headers=auth_headers() | {"Idempotency-Key": f"strict-create-{recording_id}"},
        json=resolve_body,
    )
    assert resolved.status_code == 200
    return {
        "local_recording_id": recording_id,
        "local_media_revision_id": f"{recording_id}:v1",
        "calendar_match_attempt_id": resolved.json()["attempt_id"],
        "started_at": started.isoformat(),
        "ended_at": (started + timedelta(seconds=60)).isoformat(),
        "duration_seconds": 60,
    }


@pytest.mark.parametrize(
    ("intent", "state"),
    [("user_selected", "matched_user"), ("user_declined", "declined_by_user")],
)
def test_strict_calendar_create_replays_only_the_original_accepted_decision(client, intent, state):
    body = _strict_calendar_create_body(client, intent=intent)
    headers = auth_headers()
    created = client.post(STRICT_CREATE_PATH, headers=headers, json=body)
    assert created.status_code == 200
    meeting_id = UUID(created.json()["meeting_id"])
    attempt_id = UUID(body["calendar_match_attempt_id"])

    async def age_and_remove_card_context():
        async with client.app_state["sessionmaker"]() as db:
            attempt = await db.get(RecordingCalendarMatchAttempt, attempt_id)
            assert attempt is not None
            assert attempt.consumed_by_meeting_id == meeting_id
            assert attempt.attempt_state == state
            assert attempt.consumed_at is not None
            attempt.consumed_at = datetime.now(UTC) - timedelta(days=2)
            attempt.expires_at = datetime.now(UTC) - timedelta(days=1)
            await db.execute(delete(RecordingCalendarContextLink).where(
                RecordingCalendarContextLink.meeting_id == meeting_id,
            ))
            await db.commit()

    client.portal.call(age_and_remove_card_context)
    replayed = client.post(STRICT_CREATE_PATH, headers=headers, json=body)
    assert replayed.status_code == 200
    assert UUID(replayed.json()["meeting_id"]) == meeting_id
    for changed in (
        {"duration_seconds": 61},
        {"calendar_match_attempt_id": str(uuid4())},
        {"local_media_revision_id": f"{body['local_recording_id']}:v2"},
    ):
        assert client.post(STRICT_CREATE_PATH, headers=headers, json=body | changed).status_code == 409

    recovered = client.get(
        f"/api/v1/desktop/recordings/{body['local_recording_id']}/sync-state",
        headers=headers,
        params={
            "include_calendar_match_receipt": "true",
            "local_media_revision_id": body["local_media_revision_id"],
        },
    )
    assert recovered.status_code == 200
    assert recovered.json()["calendar_match_receipt"] == {"attempt_id": str(attempt_id), "state": state}

    async def replace_revision():
        async with client.app_state["sessionmaker"]() as db:
            db.add(MediaRevision(
                workspace_id=WORKSPACE_ID, meeting_id=meeting_id,
                local_media_revision_id=f"{body['local_recording_id']}:v2",
                revision_number=2, status="accepted",
            ))
            await db.commit()

    client.portal.call(replace_revision)
    assert client.post(STRICT_CREATE_PATH, headers=headers, json=body).status_code == 409


@pytest.mark.parametrize("revision_case", ["current", "replacement", "alias"])
def test_calendar_upload_session_is_pinned_after_receipt(client, monkeypatch, revision_case):
    body = _strict_calendar_create_body(client, intent="user_declined")
    if revision_case != "alias":
        body["local_media_revision_id"] = f"{body['local_recording_id']}--initial"
    headers = auth_headers()
    assert client.post(STRICT_CREATE_PATH, headers=headers, json=body).status_code == 200
    state = client.get(
        f"/api/v1/desktop/recordings/{body['local_recording_id']}/sync-state",
        headers=headers,
        params={"local_media_revision_id": body["local_media_revision_id"], "include_calendar_match_receipt": "true"},
    ).json()
    assert state["calendar_match_receipt"] == {
        "attempt_id": body["calendar_match_attempt_id"], "state": "declined_by_user",
    }
    meeting_id = state["meeting"]["meeting_id"]
    pinned_revision = state["media_revision"]["media_revision_id"]
    pinned_path = f"/api/v1/desktop/meetings/{meeting_id}/upload-sessions"
    key = {"Idempotency-Key": f"pinned-{meeting_id}"}

    async def issue_device_token(foreign=False):
        async with client.app_state["sessionmaker"]() as db:
            device_id = uuid4() if foreign else DEVICE_ID
            if foreign:
                db.add(RegisteredDevice(
                    id=device_id, workspace_id=WORKSPACE_ID, user_id=USER_ID,
                    device_public_id="pinned-other-device", status="active",
                ))
                await db.flush()
            issued = await issue_auth_session(
                db, workspace_id=WORKSPACE_ID, user_id=USER_ID, provider="pinned-test", device_id=device_id,
            )
            db.add(AuthSessionDeviceBinding(
                auth_session_id=issued.id, registered_device_id=device_id, device_state="trusted",
            ))
            await db.commit()
            return issued.token, issued.id

    token, auth_id = client.portal.call(issue_device_token)
    key_headers = {"Authorization": f"Bearer {token}"} | key
    sizes = {"manifest": 100, "media": 200, "playback": 300}
    tracks = {"expected_track_sizes": sizes}

    async def upload_truth():
        async with client.app_state["sessionmaker"]() as db:
            uid = UUID(meeting_id)
            meeting = await db.get(Meeting, uid)
            return (
                meeting.status,
                await db.scalar(select(func.count()).where(UploadSession.meeting_id == uid)),
                await db.scalar(select(func.count()).where(IngestAuditEvent.meeting_id == uid)),
            )

    before = client.portal.call(upload_truth)
    assert client.post(pinned_path, headers=key_headers, json=tracks).status_code == 422
    scoped = tracks | {"calendar_match_attempt_id": body["calendar_match_attempt_id"]}
    wrong = client.post(pinned_path, headers=key_headers, json=scoped | {"expected_media_revision_id": str(uuid4())})
    assert wrong.status_code == 409
    assert wrong.json()["code"] == "media_revision_conflict"
    assert client.portal.call(upload_truth) == before

    async def replace_preferred_revision():
        async with client.app_state["sessionmaker"]() as db:
            second = MediaRevision(
                workspace_id=WORKSPACE_ID, meeting_id=UUID(meeting_id),
                local_media_revision_id=(
                    f"{body['local_recording_id']}--initial" if revision_case == "alias"
                    else f"{body['local_recording_id']}--replacement"
                ),
                revision_number=2, status="pending_upload",
            )
            db.add(second)
            await db.commit()
            return str(second.id)

    exact = scoped | {"expected_media_revision_id": pinned_revision}
    if revision_case != "current":
        replacement = client.portal.call(replace_preferred_revision)
        stale = client.post(pinned_path, headers=key_headers, json=exact)
        assert stale.status_code == 409
        assert stale.json()["code"] == "media_revision_conflict"
        assert client.portal.call(upload_truth) == before

        if revision_case == "alias":
            alias = client.post(pinned_path, headers=key_headers, json=scoped | {"expected_media_revision_id": replacement})
            assert alias.status_code == 409
            assert alias.json()["code"] == "media_revision_conflict"
            assert client.portal.call(upload_truth) == before

        # Existing clients keep selecting the preferred revision.
        old = client.post(f"/api/v1/meetings/{meeting_id}/upload-sessions", headers=headers | key, json=tracks)
        assert old.status_code == 200
        assert old.json()["media_revision_id"] == replacement
        return

    wrong_attempt = client.post(pinned_path, headers=key_headers, json=exact | {"calendar_match_attempt_id": str(uuid4())})
    assert wrong_attempt.status_code == 409
    assert client.portal.call(upload_truth) == before

    assert client.post(pinned_path, headers=headers | key, json=exact).status_code == 403
    foreign_token, _ = client.portal.call(issue_device_token, True)
    foreign_headers = {
        "Authorization": f"Bearer {foreign_token}",
        "X-Workspace-Id": str(WORKSPACE_ID),
        "X-Device-Id": str(DEVICE_ID),
    } | key
    forged = client.post(pinned_path, headers=foreign_headers, json=exact)
    assert forged.status_code == 401
    assert forged.json()["code"] == "auth_session_mismatched"
    for override in (
        {"expected_track_sizes": {}},
        {"expected_track_sizes": sizes | {"manifest": 0}},
        {"expected_tracks": ["manifest", "media", "playback", "manifest"]},
    ):
        malformed = client.post(pinned_path, headers=key_headers, json=exact | override)
        assert malformed.status_code == 400
        assert malformed.json()["code"] == "invalid_expected_track_size"
    assert client.portal.call(upload_truth) == before

    sessions = import_module("twobrain_rec_server.ingest.sessions")
    store = import_module("twobrain_rec_server.ingest.store").store
    problem = import_module("twobrain_rec_server.api.problems").ProblemDetail
    persist = sessions.persist_audit_event

    async def fail_after_flush(*args, **kwargs):
        await persist(*args, **kwargs)
        raise problem(status=503, code="test_late_rollback", title="Test late rollback")

    before_cache = set(store.sessions), len(store.audit_events)
    with monkeypatch.context() as patch:
        patch.setattr(sessions, "persist_audit_event", fail_after_flush)
        rolled_back = client.post(pinned_path, headers=key_headers, json=exact)
    assert rolled_back.status_code == 503
    assert rolled_back.json()["code"] == "test_late_rollback"
    assert client.portal.call(upload_truth) == before
    assert (set(store.sessions), len(store.audit_events)) == before_cache

    # Ignore the first successful response; retry uses the same key and exact revision.
    assert client.post(pinned_path, headers=key_headers, json=exact).status_code == 200
    replay = client.post(pinned_path, headers=key_headers, json=exact)
    assert replay.status_code == 200
    session_id = replay.json()["session_id"]
    checked = client.get(f"/api/v1/upload-sessions/{session_id}", headers=headers)
    assert checked.status_code == 200
    assert checked.json() == replay.json()
    assert checked.json()["meeting_id"] == meeting_id
    assert checked.json()["media_revision_id"] == pinned_revision
    assert checked.json()["expected_track_sizes"] == sizes
    assert client.portal.call(upload_truth)[1] == 1
    assert client.post(pinned_path, headers=foreign_headers, json=exact).status_code == 401

    proof_path = f"{pinned_path}/{session_id}"
    proof_query = {"expected_media_revision_id": pinned_revision}
    scoped_headers = {"Authorization": f"Bearer {token}"}
    payload = b"calendar-part-test"
    part_headers = scoped_headers | {"X-Byte-Offset": "0", "X-Content-SHA256": sha256(payload).hexdigest()}

    def proof_get(path=proof_path, params=proof_query, actor=scoped_headers):
        return client.get(path, headers=actor, params=params)

    def refused_part(path):
        response = client.put(path, headers=part_headers, content=payload)
        assert response.status_code == 404
        assert response.json()["code"] == "upload_session_not_found"

    status_module = import_module("twobrain_rec_server.ingest.status")
    with pytest.raises(problem) as unavailable:
        client.portal.call(
            status_module.get_calendar_upload_session_proof,
            UUID(meeting_id), UUID(session_id), UUID(pinned_revision), _tenant_scope(), None,
        )
    assert unavailable.value.status == 503

    proof = proof_get()
    assert proof.status_code == 200
    assert proof.headers["Cache-Control"] == "no-store"
    assert proof.json() == {field: checked.json()[field] for field in (
        "session_id", "meeting_id", "media_revision_id", "status", "expires_at",
        "expected_tracks", "expected_track_sizes",
    )}
    for response, expected_status in (
        (proof_get(actor={}), 401),
        (proof_get(actor=headers), 403),
        (proof_get(actor={"Authorization": f"Bearer {foreign_token}"}), 404),
        (proof_get(params={}), 422),
    ):
        assert response.status_code == expected_status
        assert response.headers["Cache-Control"] == "no-store"
    wrong_revision = proof_get(params={"expected_media_revision_id": str(uuid4())})
    assert wrong_revision.status_code == 404
    assert wrong_revision.headers["Cache-Control"] == "no-store"
    assert proof_get(path=proof_path.replace(meeting_id, str(uuid4()))).status_code == 404

    # The legacy loader put a copy in memory. A matching but nonexistent DB session still has no proof.
    cached_only = uuid4()
    original = store.sessions[UUID(session_id)]
    store.sessions[cached_only] = replace(original, id=cached_only, calendar_match_attempt_id=None)
    try:
        assert proof_get(path=f"{pinned_path}/{cached_only}").status_code == 404
        storage = client.app_state["storage"]
        before_objects = dict(storage.objects)
        refused_part(f"/api/v1/upload-sessions/{cached_only}/tracks/media/parts/0")
        assert storage.objects == before_objects
    finally:
        store.sessions.pop(cached_only)

    accepted_attempt = UUID(body["calendar_match_attempt_id"])

    async def set_session_scope(device, revision, attempt_id=accepted_attempt):
        async with client.app_state["sessionmaker"]() as db:
            session = await db.get(UploadSession, UUID(session_id))
            assert session is not None
            session.device_id = device
            session.media_revision_id = revision
            session.calendar_match_attempt_id = attempt_id
            await db.commit()

    after = client.portal.call(upload_truth)
    for device, revision, attempt_id in (
        (REVOKED_DEVICE_ID, UUID(pinned_revision), accepted_attempt),
        (DEVICE_ID, None, accepted_attempt),
        (DEVICE_ID, UUID(pinned_revision), None),
    ):
        client.portal.call(set_session_scope, device, revision, attempt_id)
        assert proof_get().status_code == 404
        refused = client.post(pinned_path, headers=key_headers, json=exact)
        assert refused.status_code == 409
        assert refused.json()["code"] == "idempotency_conflict"
        assert client.portal.call(upload_truth) == after
    client.portal.call(set_session_scope, DEVICE_ID, UUID(pinned_revision), uuid4())
    assert proof_get().status_code == 404
    refused = client.post(pinned_path, headers=key_headers, json=exact)
    assert refused.status_code == 409
    assert refused.json()["code"] == "idempotency_conflict"
    client.portal.call(set_session_scope, DEVICE_ID, UUID(pinned_revision))

    async def set_writability(*, status="pending", deletion_state="none", expected_sizes=sizes):
        async with client.app_state["sessionmaker"]() as db:
            session = await db.get(UploadSession, UUID(session_id))
            meeting = await db.get(Meeting, UUID(meeting_id))
            session.status = status
            session.expected_track_sizes = expected_sizes
            meeting.deletion_state = deletion_state
            await db.commit()

    for kwargs in (
        {"status": "finalized"},
        {"deletion_state": "requested"},
        {"expected_sizes": sizes | {"media": True}},
    ):
        client.portal.call(partial(set_writability, **kwargs))
        assert proof_get().status_code == 404
    client.portal.call(set_writability)
    assert proof_get().status_code == 200

    async def expire_auth_before_statement():
        from twobrain_rec_server.db.models import AuthSession

        async with client.app_state["sessionmaker"]() as db:
            auth = await db.get(AuthSession, auth_id)
            auth.expires_at = datetime.now(UTC) + timedelta(seconds=1)
            await db.commit()
            scalar = db.scalar

            async def after_expiry(*args, **kwargs):
                await asyncio.sleep(1.1)
                return await scalar(*args, **kwargs)

            with monkeypatch.context() as patch:
                patch.setattr(db, "scalar", after_expiry)
                with pytest.raises(problem) as expired:
                    await status_module.get_calendar_upload_session_proof(
                        UUID(meeting_id), UUID(session_id), UUID(pinned_revision),
                        replace(_tenant_scope(), auth_session_id=auth_id), db,
                    )
                assert expired.value.status == 404
            auth.expires_at = datetime.now(UTC) + timedelta(minutes=5)
            await db.commit()

    client.portal.call(expire_auth_before_statement)
    assert proof_get().status_code == 200

    async def expire_session(terminal):
        async with client.app_state["sessionmaker"]() as db:
            session = await db.get(UploadSession, UUID(session_id))
            assert session is not None
            session.expires_at = datetime.now(UTC) - timedelta(seconds=1)
            if terminal:
                session.status = "expired"
            await db.commit()

    for terminal in (False, True):
        client.portal.call(expire_session, terminal)
        assert proof_get().status_code == 404
        expired = client.post(pinned_path, headers=key_headers, json=exact)
        assert expired.status_code == 409
        assert expired.json()["code"] == "session_terminal"
        assert client.portal.call(upload_truth) == after


    async def restore_session():
        async with client.app_state["sessionmaker"]() as db:
            original = await db.get(UploadSession, UUID(session_id))
            original.status = "pending"
            original.expires_at = datetime.now(UTC) + timedelta(minutes=5)
            await db.commit()

    async def make_replacement_authoritative():
        async with client.app_state["sessionmaker"]() as db:
            original = await db.get(UploadSession, UUID(session_id))
            newer = MediaRevision(
                workspace_id=WORKSPACE_ID, meeting_id=UUID(meeting_id),
                local_media_revision_id=f"{body['local_recording_id']}--replacement",
                revision_number=2, status="pending_upload",
            )
            db.add(newer)
            await db.flush()
            db.add(UploadSession(
                meeting_id=original.meeting_id, media_revision_id=newer.id,
                workspace_id=original.workspace_id, device_id=original.device_id,
                created_by_user_id=original.created_by_user_id, status="pending",
                expected_track_roles=original.expected_track_roles,
                expected_track_sizes=original.expected_track_sizes,
                max_package_bytes_snapshot=original.max_package_bytes_snapshot,
                max_track_bytes_snapshot=original.max_track_bytes_snapshot,
                expires_at=original.expires_at, created_at=original.created_at + timedelta(seconds=1),
            ))
            await db.commit()

    client.portal.call(restore_session)
    assert proof_get().status_code == 200
    part_prefix = f"/api/v1/upload-sessions/{session_id}/tracks"
    first_part = f"{part_prefix}/manifest/parts/0"
    for stage in ("first", "replay"):
        accepted = client.put(first_part, headers=part_headers, content=payload)
        assert accepted.status_code == 200, (stage, accepted.json().get("code"))

    storage = client.app_state["storage"]
    before_objects = dict(storage.objects)
    writes = []

    async def set_binding(state):
        async with client.app_state["sessionmaker"]() as db:
            binding = await db.scalar(select(AuthSessionDeviceBinding).where(
                AuthSessionDeviceBinding.auth_session_id == auth_id,
            ))
            binding.device_state = state
            await db.commit()

    parts_module = import_module("twobrain_rec_server.ingest.parts")
    lock_meeting = parts_module.lock_meeting_fence

    async def revoke_before_lock(*args, **kwargs):
        await set_binding("revoked")
        return await lock_meeting(*args, **kwargs)

    with monkeypatch.context() as patch:
        patch.setattr(parts_module, "lock_meeting_fence", revoke_before_lock)
        refused_part(first_part)
    client.portal.call(set_binding, "trusted")
    assert storage.objects == before_objects

    def put_then_change(change):
        async def put(key, stream, length):
            writes.append(key)
            storage.put_stream(key, stream, length)
            await change()
        return put

    second_part = f"{part_prefix}/media/parts/0"
    with monkeypatch.context() as patch:
        patch.setattr(storage, "put_stream_async", put_then_change(partial(expire_session, False)), raising=False)
        refused_part(second_part)
    assert len(writes) == 1 and storage.objects == before_objects
    client.portal.call(restore_session)

    with monkeypatch.context() as patch:
        patch.setattr(storage, "put_stream_async", put_then_change(make_replacement_authoritative), raising=False)
        refused_part(second_part)
        assert len(writes) == 2
        refused_part(first_part)
        refused_part(second_part)
        assert len(writes) == 2
    assert storage.objects == before_objects
    state = client.get(f"/api/v1/upload-sessions/{session_id}", headers=headers)
    assert state.json()["accepted_bytes_by_track"] == {"manifest": len(payload)}
    assert proof_get().status_code == 404

    async def verify_calendar_cleanup_keeps_pin():
        from twobrain_rec_server.calendar.lifecycle import account_meeting_calendar_context_deletion

        async with client.app_state["sessionmaker"]() as db:
            meeting = await db.get(Meeting, UUID(meeting_id))
            assert await account_meeting_calendar_context_deletion(
                db, meeting=meeting, actor_user_id=USER_ID, device_id=DEVICE_ID,
            )
            await db.commit()
        async with client.app_state["sessionmaker"]() as db:
            assert await db.get(RecordingCalendarMatchAttempt, accepted_attempt) is None
            session = await db.get(UploadSession, UUID(session_id))
            assert session.calendar_match_attempt_id == accepted_attempt

    client.portal.call(verify_calendar_cleanup_keeps_pin)


@pytest.mark.parametrize("rejection", ["automatic", "expired", "unknown", "different_start", "foreign_device", "late_failure"])
def test_strict_calendar_create_rejection_has_no_ingest_side_effects(client, monkeypatch, rejection):
    body = _strict_calendar_create_body(
        client, intent="automatic" if rejection == "automatic" else "user_declined",
    )
    attempt_id = UUID(body["calendar_match_attempt_id"])
    recording_id = body["local_recording_id"]
    store = import_module("twobrain_rec_server.ingest.store").store
    counts_before = len(store.meetings), len(store.audit_events)

    async def expire():
        async with client.app_state["sessionmaker"]() as db:
            attempt = await db.get(RecordingCalendarMatchAttempt, attempt_id)
            assert attempt is not None
            attempt.expires_at = datetime.now(UTC) - timedelta(seconds=1)
            await db.commit()

    async def other_device_headers():
        async with client.app_state["sessionmaker"]() as db:
            device = RegisteredDevice(
                id=uuid4(), workspace_id=WORKSPACE_ID, user_id=USER_ID,
                device_public_id="strict-other-device", status="active",
            )
            db.add(device)
            await db.flush()
            issued = await issue_auth_session(
                db, workspace_id=WORKSPACE_ID, user_id=USER_ID, provider="strict-test",
                device_id=device.id,
            )
            db.add(AuthSessionDeviceBinding(
                auth_session_id=issued.id, registered_device_id=device.id, device_state="trusted",
            ))
            await db.commit()
            return {"Authorization": f"Bearer {issued.token}"}

    headers = auth_headers()
    if rejection == "expired":
        client.portal.call(expire)
    elif rejection == "foreign_device":
        headers = client.portal.call(other_device_headers)
    elif rejection == "unknown":
        body["calendar_match_attempt_id"] = str(uuid4())
    elif rejection == "different_start":
        body["started_at"] = (datetime.fromisoformat(body["started_at"]) + timedelta(seconds=1)).isoformat()

    async def truth():
        async with client.app_state["sessionmaker"]() as db:
            attempt = await db.get(RecordingCalendarMatchAttempt, attempt_id)
            assert attempt is not None and attempt.consumed_at is None
            return tuple([
                await db.scalar(select(func.count()).select_from(model))
                for model in (
                    Meeting, MediaRevision, ProcessingPlaceholder, RecordingCalendarContextLink,
                    IngestAuditEvent, CalendarAuditEvent,
                )
            ])

    db_before = client.portal.call(truth)
    if rejection == "late_failure":
        api = import_module("twobrain_rec_server.api.ingest")
        problems = import_module("twobrain_rec_server.api.problems")

        async def fail_before_commit(db, meeting, context):
            assert context is not None and context.context_state == "declined_by_user"
            assert await db.get(MediaRevision, meeting.media_revision_id) is not None
            attempt = await db.get(RecordingCalendarMatchAttempt, attempt_id)
            assert attempt is not None and attempt.consumed_by_meeting_id == meeting.id
            raise problems.ProblemDetail(status=503, code="synthetic_late_failure", title="Test fault")

        with monkeypatch.context() as patch:
            patch.setattr(api, "content_safe_meeting_response", fail_before_commit)
            response = client.post(STRICT_CREATE_PATH, headers=headers, json=body)
        assert response.status_code == 503
        assert response.json()["code"] == "synthetic_late_failure"
    else:
        response = client.post(STRICT_CREATE_PATH, headers=headers, json=body)
        assert response.status_code == 409
        assert response.json()["code"] == "calendar_match_not_accepted"
    assert client.portal.call(truth) == db_before
    assert (len(store.meetings), len(store.audit_events)) == counts_before
    assert (WORKSPACE_ID, USER_ID, recording_id) not in store.meetings_by_local_id
    if rejection == "late_failure":
        sync_path = f"/api/v1/desktop/recordings/{recording_id}/sync-state"
        recovery = client.get(sync_path, headers=headers, params={"include_calendar_match_receipt": "true"})
        assert recovery.status_code == 404
        assert "calendar_match_receipt" not in recovery.json()
        assert client.post(STRICT_CREATE_PATH, headers=headers, json=body).status_code == 200


def test_strict_calendar_create_cannot_attach_to_legacy_meeting_without_proof(client):
    body = _strict_calendar_create_body(client, intent="user_declined")
    attempt_id = UUID(body["calendar_match_attempt_id"])

    async def expire_then_return_deadline():
        async with client.app_state["sessionmaker"]() as db:
            attempt = await db.get(RecordingCalendarMatchAttempt, attempt_id)
            deadline = attempt.expires_at
            attempt.expires_at = datetime.now(UTC) - timedelta(seconds=1)
            await db.commit()
            return deadline

    deadline = client.portal.call(expire_then_return_deadline)
    api = import_module("twobrain_rec_server.api.ingest")

    async def send_to_legacy_router():
        legacy = FastAPI()
        legacy.state = client.app.state
        legacy.router.routes.extend(
            route for route in api.router.routes if getattr(route, "path", None) == "/api/v1/meetings"
        )
        async with AsyncClient(transport=ASGITransport(app=legacy), base_url="http://testserver") as old:
            headers = auth_headers()
            absent = await old.post(STRICT_CREATE_PATH, headers=headers, json=body)
            assert absent.status_code == 404
            async with client.app_state["sessionmaker"]() as db:
                assert await db.scalar(select(Meeting.id).where(
                    Meeting.local_recording_id == body["local_recording_id"],
                )) is None
            return await old.post("/api/v1/meetings", headers=headers, json=body)

    legacy = client.portal.call(send_to_legacy_router)
    assert legacy.status_code == 200
    meeting_id = UUID(legacy.json()["meeting_id"])

    async def restore_deadline():
        async with client.app_state["sessionmaker"]() as db:
            attempt = await db.get(RecordingCalendarMatchAttempt, attempt_id)
            attempt.expires_at = deadline
            await db.commit()

    client.portal.call(restore_deadline)
    refused = client.post(STRICT_CREATE_PATH, headers=auth_headers(), json=body)
    assert refused.status_code == 409
    assert refused.json()["code"] == "calendar_match_not_accepted"
    _, _, consumed_by, context, *_ = _load_attempt_context_truth(
        client, attempt_id=attempt_id, meeting_id=meeting_id,
    )
    assert consumed_by is None and context == "skipped_offline_or_unknown"


@pytest.mark.parametrize("create_first", [False, True])
def test_strict_calendar_create_and_replay_respect_origin_deletion(client, create_first):
    body = _strict_calendar_create_body(client, intent="user_declined")
    headers = auth_headers()
    if create_first:
        assert client.post(STRICT_CREATE_PATH, headers=headers, json=body).status_code == 200

    copy = import_module("twobrain_rec_server.deletion.report").BOUNDED_DELETE_COPY
    deletion = client.post(
        f"/api/v1/desktop/recordings/{body['local_recording_id']}/deletion-requests",
        headers=headers,
        json={"operation_id": str(uuid4()), "confirmation_boundary": copy},
    )
    assert deletion.status_code == 202
    refused = client.post(STRICT_CREATE_PATH, headers=headers, json=body)
    assert refused.status_code == 409
    assert refused.json()["code"] == (
        "meeting_deletion_active" if create_first else "recording_deletion_active"
    )


@pytest.mark.parametrize("replay", [False, True])
def test_strict_calendar_create_rejects_revocation_while_waiting_for_origin(client, monkeypatch, replay):
    body = _strict_calendar_create_body(client, intent="user_declined")
    recording_id = body["local_recording_id"]
    attempt_id = UUID(body["calendar_match_attempt_id"])
    meetings = import_module("twobrain_rec_server.ingest.meetings")
    lock_origin = meetings.lock_recording_origin

    async def run_race():
        async with client.app_state["sessionmaker"]() as writer:
            issued = await issue_auth_session(
                writer, workspace_id=WORKSPACE_ID, user_id=USER_ID,
                provider="strict-race", device_id=DEVICE_ID,
            )
            writer.add(AuthSessionDeviceBinding(
                auth_session_id=issued.id, registered_device_id=DEVICE_ID, device_state="trusted",
            ))
            await writer.commit()
            headers = {"Authorization": f"Bearer {issued.token}"}
            async with AsyncClient(transport=ASGITransport(app=client.app), base_url="http://testserver") as http:
                if replay:
                    assert (await http.post(STRICT_CREATE_PATH, headers=headers, json=body)).status_code == 200
                await lock_origin(writer, _tenant_scope(), recording_id)
                waiting = asyncio.Event()

                async def observe_lock(db, scope, origin):
                    waiting.set()
                    await lock_origin(db, scope, origin)

                with monkeypatch.context() as patch:
                    patch.setattr(meetings, "lock_recording_origin", observe_lock)
                    async with asyncio.timeout(5), asyncio.TaskGroup() as tasks:
                        response = tasks.create_task(http.post(STRICT_CREATE_PATH, headers=headers, json=body))
                        await waiting.wait()
                        device = await writer.get(RegisteredDevice, DEVICE_ID)
                        assert device is not None
                        device.status = "revoked"
                        await writer.commit()
                assert response.result().status_code == 409
            attempt = await writer.get(RecordingCalendarMatchAttempt, attempt_id)
            assert attempt is not None
            assert (attempt.consumed_at is not None) == replay
            meeting_count = await writer.scalar(select(func.count()).select_from(Meeting).where(
                Meeting.local_recording_id == recording_id,
            ))
            assert meeting_count == int(replay)

    client.portal.call(run_race)

@pytest.mark.parametrize("replay", [False, True])
def test_calendar_upload_session_rechecks_revoked_binding_after_meeting_lock(client, monkeypatch, replay):
    body = _strict_calendar_create_body(client, intent="user_declined")
    recording = body["local_recording_id"]
    body["local_media_revision_id"] = f"{recording}--initial"
    assert client.post(STRICT_CREATE_PATH, headers=auth_headers(), json=body).status_code == 200
    state = client.get(
        f"/api/v1/desktop/recordings/{recording}/sync-state",
        headers=auth_headers(), params={"local_media_revision_id": body["local_media_revision_id"]},
    ).json()
    meeting_id = UUID(state["meeting"]["meeting_id"])
    path = f"/api/v1/desktop/meetings/{meeting_id}/upload-sessions"
    payload = {
        "expected_media_revision_id": state["media_revision"]["media_revision_id"],
        "calendar_match_attempt_id": body["calendar_match_attempt_id"],
        "expected_track_sizes": {"manifest": 100, "media": 200, "playback": 300},
    }
    sessions = import_module("twobrain_rec_server.ingest.sessions")
    lock_meeting = sessions.lock_meeting_fence

    async def run_race():
        async with client.app_state["sessionmaker"]() as writer:
            issued = await issue_auth_session(
                writer, workspace_id=WORKSPACE_ID, user_id=USER_ID,
                provider="pinned-race", device_id=DEVICE_ID,
            )
            binding = AuthSessionDeviceBinding(
                auth_session_id=issued.id, registered_device_id=DEVICE_ID, device_state="trusted",
            )
            writer.add(binding)
            await writer.commit()
            headers = {"Authorization": f"Bearer {issued.token}", "Idempotency-Key": f"pinned-race-{meeting_id}"}

            async def truth():
                meeting = await writer.get(Meeting, meeting_id, populate_existing=True)
                return (
                    meeting.status,
                    await writer.scalar(select(func.count()).where(UploadSession.meeting_id == meeting_id)),
                    await writer.scalar(select(func.count()).where(IngestAuditEvent.meeting_id == meeting_id)),
                )

            async with AsyncClient(transport=ASGITransport(app=client.app), base_url="http://testserver") as http:
                if replay:
                    assert (await http.post(path, headers=headers, json=payload)).status_code == 200
                before = await truth()
                await lock_meeting(writer, workspace_id=WORKSPACE_ID, meeting_id=meeting_id)
                waiting = asyncio.Event()

                async def observe_lock(db, **kwargs):
                    waiting.set()
                    return await lock_meeting(db, **kwargs)

                with monkeypatch.context() as patch:
                    patch.setattr(sessions, "lock_meeting_fence", observe_lock)
                    async with asyncio.timeout(5), asyncio.TaskGroup() as tasks:
                        response = tasks.create_task(http.post(path, headers=headers, json=payload))
                        await waiting.wait()
                        binding.device_state = "revoked"
                        await writer.commit()
                assert response.result().status_code == 409
                assert response.result().json()["code"] == "calendar_match_not_accepted"
                assert await truth() == before

    client.portal.call(run_race)


@pytest.mark.parametrize("case", [
    "revoke_before_publish", "revoke_before_degraded", "single_part", "multipart",
    "cache_only", "expires_after_admission", "part_arrives_before_degraded",
    "protected_part", "protected_missing", "protected_cleaner_claimed", "protected_recovery_changed",
    "protected_no_archive", "protected_commit_lost_accepted", "protected_commit_lost_rolled_back",
])
def test_calendar_finalize_rechecks_admission(client, monkeypatch, tmp_path, case):
    body = _strict_calendar_create_body(client, intent="user_declined")
    recording = body["local_recording_id"]
    body["local_media_revision_id"] = f"{recording}--initial"
    assert client.post(STRICT_CREATE_PATH, headers=auth_headers(), json=body).status_code == 200
    state = client.get(
        f"/api/v1/desktop/recordings/{recording}/sync-state", headers=auth_headers(),
        params={"local_media_revision_id": body["local_media_revision_id"]},
    ).json()
    meeting_id = UUID(state["meeting"]["meeting_id"])
    revision_id = UUID(state["media_revision"]["media_revision_id"])
    sessionmaker = client.app_state["sessionmaker"]
    tracks = {"manifest": b"manifest", "media": b"two media parts", "playback": b"playback"}

    async def issue_token():
        async with sessionmaker() as db:
            issued = await issue_auth_session(
                db, workspace_id=WORKSPACE_ID, user_id=USER_ID, provider="calendar-finalize-test", device_id=DEVICE_ID,
            )
            binding = AuthSessionDeviceBinding(
                auth_session_id=issued.id, registered_device_id=DEVICE_ID, device_state="trusted",
            )
            db.add(binding)
            await db.commit()
            return issued.token, binding.id

    token, binding_id = client.portal.call(issue_token)
    headers = {"Authorization": f"Bearer {token}"}
    opened = client.post(
        f"/api/v1/desktop/meetings/{meeting_id}/upload-sessions",
        headers=headers | {"Idempotency-Key": f"finalize-pin-{meeting_id}"},
        json={
            "expected_media_revision_id": str(revision_id),
            "calendar_match_attempt_id": body["calendar_match_attempt_id"],
            "expected_track_sizes": {role: len(data) for role, data in tracks.items()},
        },
    )
    assert opened.status_code == 200
    session_id = UUID(opened.json()["session_id"])
    path = f"/api/v1/upload-sessions/{session_id}"
    for role, data in tracks.items():
        chunks = (data,)
        if role == "media":
            if case == "multipart":
                chunks = (data[:4], data[4:])
            elif case == "part_arrives_before_degraded":
                chunks = (data[:4],)
        offset = 0
        for number, chunk in enumerate(chunks):
            reply = client.put(
                f"{path}/tracks/{role}/parts/{number}", content=chunk,
                headers=headers | {"X-Byte-Offset": str(offset), "X-Content-SHA256": sha256(chunk).hexdigest()},
            )
            assert reply.status_code == 200
            offset += len(chunk)

    storage = client.app_state["storage"]
    parts_before = dict(storage.objects)
    protected = case.startswith("protected_")
    expected_keys = set(parts_before)
    journal_id = uuid4()
    recovery_file = tmp_path / "recovery"
    if protected:
        recovery_id = uuid4()
        settings = client.app.state.settings
        settings.strict_storage_scope = "test-scope"
        settings.strict_storage_recovery_file = recovery_file
        settings.strict_storage_recovery_id = recovery_id
        recovery_file.with_suffix(".lock").touch()
        recovery_file.write_text(json.dumps({
            "schema": 1, "scope": "test-scope", "state": "reconciled", "recovery_id": str(recovery_id),
        }))

        async def seed_protected_part():
            async with sessionmaker.begin() as db:
                part = await db.scalar(select(UploadPart).where(
                    UploadPart.upload_session_id == session_id, UploadPart.track_role == "media",
                ))
                old_key = part.storage_object_key
                protected_key = f"{old_key.rsplit('/', 1)[0]}/calendar-attempts/1/7"
                part.storage_object_key = protected_key
                custody = await db.scalar(select(TemporaryUploadObject).where(
                    TemporaryUploadObject.upload_session_id == session_id,
                    TemporaryUploadObject.storage_object_key == old_key,
                ))
                custody.storage_object_key = protected_key
                if case != "protected_missing":
                    db.add(PurgeJournal(
                        id=journal_id, workspace_id=WORKSPACE_ID, meeting_id=meeting_id,
                        media_revision_id=revision_id, deletion_epoch=0,
                        artifact_class="strict_upload_attempt", object_key=protected_key,
                        state="retained", write_state="accepted", multipart_upload_id="synthetic-upload-id",
                        storage_scope="test-scope", storage_epoch=1,
                    ))
                return old_key, protected_key

        old_key, protected_key = client.portal.call(seed_protected_part)
        expected_keys.remove(old_key)
        expected_keys.add(protected_key)
    finalize_body = {
        "manifest_sha256": sha256(tracks["manifest"]).hexdigest(),
        "tracks": [track_descriptor(role, data=data) for role, data in tracks.items()],
        "archive_audio": case != "protected_no_archive",
    }
    finalize_path = f"{path}/finalize"

    async def truth():
        async with sessionmaker() as db:
            meeting = await db.get(Meeting, meeting_id)
            session = await db.get(UploadSession, session_id)
            revision = await db.get(MediaRevision, revision_id)
            events = await db.scalars(select(IngestAuditEvent.event_type).where(
                IngestAuditEvent.upload_session_id == session_id,
                IngestAuditEvent.event_type.in_(["finalized", "finalize_degraded"]),
            ))
            keys = await db.scalars(select(TrackArtifact.storage_object_key).where(
                TrackArtifact.media_revision_id == revision_id,
            ))
            return meeting.status, session.status, revision.status, list(events), set(keys)

    async def revoke():
        async with sessionmaker() as db:
            binding = await db.get(AuthSessionDeviceBinding, binding_id)
            binding.device_state = "revoked"
            await db.commit()

    before = client.portal.call(truth)
    finalize_module = import_module("twobrain_rec_server.ingest.finalize")
    persist_degraded = finalize_module._persist_degraded_finalize_failure
    lock_meeting = finalize_module._lock_finalize_lifecycle_fence
    require_access = finalize_module.require_calendar_upload_access

    async def claim_before_publish(*args, **kwargs):
        async with sessionmaker.begin() as db:
            journal = await db.get(PurgeJournal, journal_id)
            journal.state = "deleting"
        return await lock_meeting(*args, **kwargs)

    persist_audit = finalize_module.persist_audit_event
    commit = AsyncSession.commit

    async def mark_finalize_commit(db, *args, **kwargs):
        await persist_audit(db, *args, **kwargs)
        db.info["simulate_lost_finalize_commit"] = True

    async def lose_finalize_commit(db):
        if not db.info.pop("simulate_lost_finalize_commit", False):
            return await commit(db)
        if case == "protected_commit_lost_accepted":
            await commit(db)
        else:
            await db.rollback()
        raise SQLAlchemyError("synthetic commit response lost")

    async def change_recovery_before_commit(*args, **kwargs):
        await persist_audit(*args, **kwargs)
        recovery_file.unlink()

    async def revoke_then_degrade(**kwargs):
        await revoke()
        return await persist_degraded(**kwargs)

    async def revoke_then_lock(*args, **kwargs):
        await revoke()
        return await lock_meeting(*args, **kwargs)

    async def expire_after_admission(db, session, tenant_scope):
        await require_access(db, session, tenant_scope)
        session.expires_at = datetime.now(UTC) - timedelta(seconds=1)
        async with sessionmaker() as writer:
            saved = await writer.get(UploadSession, session_id)
            saved.expires_at = session.expires_at
            await writer.commit()

    async def accept_second_part_then_degrade(**kwargs):
        chunk = tracks["media"][4:]
        async with AsyncClient(transport=ASGITransport(app=client.app), base_url="http://testserver") as http:
            part = await http.put(
                f"{path}/tracks/media/parts/1", content=chunk,
                headers=headers | {"X-Byte-Offset": "4", "X-Content-SHA256": sha256(chunk).hexdigest()},
            )
            assert part.status_code == 200
        return await persist_degraded(**kwargs)

    materialized = []
    materialize = finalize_module._materialize_track_object

    async def count_materialization(**kwargs):
        materialized.append(kwargs["role"])
        return await materialize(**kwargs)

    if case == "cache_only":
        store = import_module("twobrain_rec_server.ingest.store").store
        missing_id = uuid4()
        store.sessions[missing_id] = replace(store.sessions[session_id], id=missing_id, calendar_match_attempt_id=None)
        finalize_path = f"/api/v1/upload-sessions/{missing_id}/finalize"

    with monkeypatch.context() as patch:
        patch.setattr(finalize_module, "_materialize_track_object", count_materialization)
        if protected:
            def forbidden_storage(*args, **kwargs):
                pytest.fail("Single-part protected finalization must not access storage")
            for method in ("iter_object", "get_bytes", "get_bytes_async", "put_stream", "delete_object"):
                patch.setattr(storage, method, forbidden_storage)
        if case == "protected_cleaner_claimed":
            patch.setattr(finalize_module, "_lock_finalize_lifecycle_fence", claim_before_publish)
        if case == "protected_recovery_changed":
            patch.setattr(finalize_module, "persist_audit_event", change_recovery_before_commit)
        if case.startswith("protected_commit_lost_"):
            patch.setattr(finalize_module, "persist_audit_event", mark_finalize_commit)
            patch.setattr(AsyncSession, "commit", lose_finalize_commit)
        if case == "revoke_before_degraded":
            patch.setattr(finalize_module, "_persist_degraded_finalize_failure", revoke_then_degrade)
            finalize_body = finalize_body | {"manifest_sha256": sha256(b"wrong").hexdigest()}
        if case == "revoke_before_publish":
            patch.setattr(finalize_module, "_lock_finalize_lifecycle_fence", revoke_then_lock)
        if case == "expires_after_admission":
            patch.setattr(finalize_module, "require_calendar_upload_access", expire_after_admission)
        if case == "part_arrives_before_degraded":
            patch.setattr(finalize_module, "_persist_degraded_finalize_failure", accept_second_part_then_degrade)
            finalize_body = finalize_body | {"manifest_sha256": sha256(b"wrong").hexdigest()}
        result = client.post(finalize_path, headers=headers, json=finalize_body)
    after = client.portal.call(truth)
    if case in ("single_part", "protected_part", "protected_no_archive", "protected_commit_lost_accepted"):
        if case == "protected_commit_lost_accepted":
            assert result.status_code == 503 and result.json()["code"] == "persistence_unavailable"
        else:
            assert result.status_code == 200, result.json()
        assert after[1:4] == ("finalized", "accepted", ["finalized"])
        assert after[4] == expected_keys
        assert len(materialized) == 3
        if protected:
            async def retained_journal():
                async with sessionmaker() as db:
                    row = await db.get(PurgeJournal, journal_id)
                    custody = await db.scalar(select(TemporaryUploadObject).where(
                        TemporaryUploadObject.upload_session_id == session_id,
                        TemporaryUploadObject.storage_object_key == protected_key,
                    ))
                    return row.state, row.write_state, row.object_key, custody.object_role
            expected_role = "transient_source" if case == "protected_no_archive" else "accepted_part"
            assert client.portal.call(retained_journal) == ("retained", "accepted", protected_key, expected_role)
    else:
        expected_status, expected_code = {
            "multipart": (503, "calendar_finalize_multipart_unavailable"),
            "part_arrives_before_degraded": (503, "calendar_finalize_multipart_unavailable"),
            "expires_after_admission": (409, "session_expired"),
        }.get(case, (404, "upload_session_not_found"))
        if protected:
            expected_status, expected_code = 503, "strict_upload_part_unavailable"
        if case == "protected_commit_lost_rolled_back":
            expected_code = "persistence_unavailable"
        assert result.status_code == expected_status, result.json()
        assert result.json()["code"] == expected_code
        assert after == before
        assert len(materialized) == (3 if case in ("revoke_before_publish", "expires_after_admission") or protected else 0)
    if case == "part_arrives_before_degraded":
        assert parts_before.items() <= storage.objects.items()
        assert [data for key, data in storage.objects.items() if key not in parts_before] == [tracks["media"][4:]]
    else:
        assert storage.objects == parts_before


@pytest.mark.parametrize("tamper", [False, True], ids=["valid", "missing-attempt-metadata"])
def test_strict_track_assembly_real_minio_and_calendar_owner(client, tmp_path, tamper):
    """Opt-in proof with the pinned, disposable loopback MinIO."""
    from contextlib import contextmanager
    from io import BytesIO
    from time import monotonic

    from minio import Minio

    from twobrain_rec_server.api.schemas import TrackDescriptor
    from twobrain_rec_server.db.tenant_context import apply_tenant_scope
    from twobrain_rec_server.domain.statuses import TrackRole, UploadSessionStatus
    from twobrain_rec_server.ingest import store, strict_upload
    from twobrain_rec_server.ingest.media_revisions import mark_media_revision_accepted
    from twobrain_rec_server.ingest.status import require_calendar_upload_access
    from twobrain_rec_server.storage.minio_client import MinioStorage, StorageTransferError
    from twobrain_rec_server.storage.strict_upload_writer import StrictUploadWriteTarget

    endpoint = os.environ.get("GRAF_TEST_STRICT_MINIO_ENDPOINT")
    if not endpoint:
        pytest.skip("requires a dedicated disposable MinIO")
    host, port = endpoint.split(":")
    assert host == "127.0.0.1" and port.isdecimal()
    access = os.environ["GRAF_TEST_STRICT_MINIO_ACCESS"]
    secret = os.environ["GRAF_TEST_STRICT_MINIO_SECRET"]
    bucket = f"graf-test-{uuid4().hex}"
    recovery = uuid4()
    path = tmp_path / "recovery"
    path.with_suffix(".lock").touch()
    path.write_text(json.dumps({
        "schema": 1, "scope": "test-scope", "state": "reconciled", "recovery_id": str(recovery),
    }))
    settings = client.app.state.settings.model_copy(update={
        "minio_endpoint": endpoint, "minio_access_key": access, "minio_secret_key": secret,
        "minio_secure": False, "minio_bucket": bucket, "strict_storage_scope": "test-scope",
        "strict_storage_recovery_file": path, "strict_storage_recovery_id": recovery,
        "strict_storage_read_fence_directory": tmp_path,
    })
    storage = MinioStorage(settings)
    storage.client.make_bucket(bucket)
    target = StrictUploadWriteTarget(
        f"http://{endpoint}", socket.getaddrinfo(host, port, type=socket.SOCK_STREAM), bucket,
        lambda pool: Minio(
            endpoint, access_key=access, secret_key=secret, secure=False, http_client=pool, region="us-east-1",
        ),
    )

    @contextmanager
    def admit_generation(scope, current, epoch):
        assert (scope, current, epoch) == ("test-scope", str(recovery), 1)
        yield target

    create = _strict_calendar_create_body(client, intent="user_declined")
    recording = create["local_recording_id"]
    create["local_media_revision_id"] = f"{recording}--initial"
    assert client.post(STRICT_CREATE_PATH, headers=auth_headers(), json=create).status_code == 200
    state = client.get(
        f"/api/v1/desktop/recordings/{recording}/sync-state", headers=auth_headers(),
        params={"local_media_revision_id": create["local_media_revision_id"]},
    ).json()
    meeting_id = UUID(state["meeting"]["meeting_id"])
    revision_id = UUID(state["media_revision"]["media_revision_id"])
    sessions = client.app_state["sessionmaker"]
    payloads = {TrackRole.MANIFEST: (b"manifest",), TrackRole.MEDIA: (b"first-", b"second"), TrackRole.PLAYBACK: (b"preview",)}

    async def issue():
        async with sessions.begin() as db:
            issued = await issue_auth_session(
                db, workspace_id=WORKSPACE_ID, user_id=USER_ID, provider="calendar-finalize-test", device_id=DEVICE_ID,
            )
            db.add(AuthSessionDeviceBinding(
                auth_session_id=issued.id, registered_device_id=DEVICE_ID, device_state="trusted",
            ))
            return issued.id, issued.token

    auth_id, token = client.portal.call(issue)
    opened = client.post(
        f"/api/v1/desktop/meetings/{meeting_id}/upload-sessions",
        headers={"Authorization": f"Bearer {token}", "Idempotency-Key": f"strict-minio-{meeting_id}"},
        json={
            "expected_media_revision_id": str(revision_id),
            "calendar_match_attempt_id": create["calendar_match_attempt_id"],
            "expected_track_sizes": {role.value: sum(map(len, chunks)) for role, chunks in payloads.items()},
        },
    )
    assert opened.status_code == 200
    session_id = UUID(opened.json()["session_id"])
    scope = replace(_tenant_scope(), auth_session_id=auth_id)

    async def run():
        deadline = monotonic() + 30
        descriptors = [
            TrackDescriptor(
                track_role=role, codec="wav", sample_rate_hz=48_000, channel_count=1, duration_seconds=1,
                byte_length=sum(map(len, chunks)), sha256=sha256(b"".join(chunks)).hexdigest(),
            )
            for role, chunks in payloads.items()
        ]
        manifest, media, _playback = descriptors
        keys = {}
        async with sessions() as db:
            await apply_tenant_scope(db, scope)
            await db.commit()
            async with db.begin():
                session = await store.load_upload_session_record(db, session_id)
            assert session is not None

            async def product_access(_meeting):
                await require_calendar_upload_access(db, session, scope)

            for role, chunks in payloads.items():
                offset = 0
                for number, chunk in enumerate(chunks):
                    obj = strict_upload.StrictUploadObject(WORKSPACE_ID, meeting_id, revision_id, session_id, role, number)
                    digest = sha256(chunk).hexdigest()
                    staged = await strict_upload.stage_strict_upload(
                        db, settings=settings, object=obj, epoch=1, admission=admit_generation,
                        admit_product=product_access, source=BytesIO(chunk),
                        byte_length=len(chunk), expected_sha256=digest, deadline=deadline,
                    )
                    part = store.UploadPartRecord(role, number, offset, len(chunk), digest, staged.key, b"")
                    async with strict_upload.accept_strict_uploads(
                        db, settings=settings, staged=(staged,), tenant_scope=scope,
                        admission=admit_generation, deadline=deadline,
                    ):
                        session.status = UploadSessionStatus.UPLOADING
                        await store.persist_upload_session(db, session, commit=False)
                        await store.persist_temporary_upload_object(db, session, part, commit=False)
                        await store.persist_upload_part(db, session, part, commit=False)
                    offset += len(chunk)
                    keys[role] = staged.key

            async with db.begin():
                session = await store.load_upload_session_record(db, session_id)
                meeting = await store.load_meeting_record(db, meeting_id=meeting_id, retain_in_memory=False)
            assert session is not None and meeting is not None
            reused = {keys[TrackRole.MANIFEST], keys[TrackRole.PLAYBACK]}
            if tamper:
                # An operator replacing an object can preserve its bytes but
                # cannot manufacture ownership just by matching the checksum.
                second = payloads[TrackRole.MEDIA][1]
                await asyncio.to_thread(
                    storage.client.put_object, bucket, keys[TrackRole.MEDIA], BytesIO(second), len(second),
                )
                with pytest.raises(StorageTransferError, match="source_mismatch"):
                    async with strict_upload.assemble_strict_track(
                        db, settings=settings, tenant_scope=scope, session=session, track=media, storage=storage,
                        recovery=str(recovery), deletion_epoch=0, deadline=deadline,
                    ):
                        pytest.fail("track containing an unowned object reached the writer")
                async with sessions() as observer:
                    upload = await observer.get(UploadSession, session_id)
                    assert upload.status == UploadSessionStatus.UPLOADING.value
                    assert await observer.scalar(select(func.count()).select_from(TrackArtifact).where(
                        TrackArtifact.media_revision_id == revision_id,
                    )) == 0
                    assert await observer.scalar(select(func.count()).select_from(PurgeJournal).where(
                        PurgeJournal.meeting_id == meeting_id, PurgeJournal.state == "retained",
                        PurgeJournal.write_state == "accepted",
                    )) == 4
                return {}
            async with strict_upload.assemble_strict_track(
                db, settings=settings, tenant_scope=scope, session=session, track=media, storage=storage,
                recovery=str(recovery), deletion_epoch=0, deadline=deadline,
            ) as stream:
                combined = await strict_upload.stage_strict_upload(
                    db, settings=settings, object=strict_upload.StrictUploadObject(
                        WORKSPACE_ID, meeting_id, revision_id, session_id, TrackRole.MEDIA,
                    ), epoch=1, admission=admit_generation, admit_product=product_access,
                    source=stream, byte_length=media.byte_length, expected_sha256=media.sha256, deadline=deadline,
                )
            keys[TrackRole.MEDIA] = combined.key
            async with strict_upload.accept_strict_uploads(
                db, settings=settings, staged=(combined,), tenant_scope=scope,
                admission=admit_generation, deadline=deadline,
            ):
                await mark_media_revision_accepted(
                    db, media_revision_id=revision_id, manifest_sha256=manifest.sha256, tracks=descriptors, commit=False,
                )
                session.status = UploadSessionStatus.FINALIZED
                session.finalized_at = datetime.now(UTC)
                await store.persist_upload_session(db, session, commit=False)
                await store.persist_finalized_tracks(
                    db, meeting, session, descriptors, manifest.sha256, keys, reused_strict_keys=reused, commit=False,
                )
        async with sessions() as observer:
            row = await observer.get(PurgeJournal, combined.id)
            assert (row.state, row.write_state) == ("retained", "accepted")
            assert set(await observer.scalars(select(TrackArtifact.storage_object_key).where(
                TrackArtifact.media_revision_id == revision_id,
            ))) == set(keys.values())
        return keys

    keys = client.portal.call(run)
    if tamper:
        assert len(list(storage.client.list_objects(bucket, recursive=True))) == 4
    for role, key in keys.items():
        response = storage.client.get_object(bucket, key)
        try:
            assert response.read() == b"".join(payloads[role])
        finally:
            response.close()
            response.release_conn()
