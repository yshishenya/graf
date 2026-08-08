import asyncio
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select

from tests.contract.test_ingest_openapi_contract import auth_headers
from twobrain_rec_server.calendar.sync import record_source_sync_failure
from twobrain_rec_server.db.models import (
    CalendarAuditEvent,
    CalendarSource,
    RecordingCalendarContextLink,
)

RESOLVE_PATH = "/api/v1/desktop/recordings/{local_recording_id}/calendar-context/resolve"


def test_provider_timeout_marks_calendar_stale_without_blocking_meeting_creation(client) -> None:
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
    _mark_failure(client, source_id, "provider_timeout")

    listed = client.get("/api/v1/calendar/sources", headers=auth_headers())
    meeting = client.post(
        "/api/v1/meetings",
        headers=auth_headers(),
        json={"local_recording_id": "calendar-provider-down", "duration_seconds": 600},
    )

    source = listed.json()["sources"][0]
    assert source["sync_state"] == "stale"
    assert source["safe_error_code"] == "provider_timeout"
    assert meeting.status_code == 200


def test_us2_latest_provider_failure_resolves_and_consumes_fail_soft(client) -> None:
    # FR-028/FR-030/FR-032, SC-010/SC-011: provider failure is safe state, not ingest failure.
    created_source = client.post(
        "/api/v1/calendar/sources",
        headers=auth_headers(),
        json={
            "provider_family": "caldav_yandex",
            "auth_mode": "app_password",
            "username": "synthetic-owner@example.test",
            "credential_input": "synthetic-provider-secret",
            "selected_provider_calendar_ids": ["synthetic-primary"],
        },
    )
    assert created_source.status_code == 201
    source_id = UUID(created_source.json()["source"]["source_id"])
    _mark_failure(client, source_id, "provider_timeout")
    recording_started_at = datetime.now(UTC).replace(microsecond=0)
    local_recording_id = "calendar-provider-fail-soft-098"

    resolved = client.post(
        RESOLVE_PATH.format(local_recording_id=local_recording_id),
        headers=auth_headers() | {"Idempotency-Key": "provider-fail-soft-key-098"},
        json={
            "recording_started_at": recording_started_at.isoformat(),
            "decision_intent": "automatic",
            "contract_version": "calendar_auto_context_v1",
        },
    )

    assert resolved.status_code == 200
    assert resolved.json()["context_state"] == "skipped_stale_calendar"
    assert resolved.json()["reason_code"] == "latest_sync_failed"
    assert resolved.json()["candidate_count"] == 0
    assert "provider_timeout" not in resolved.text
    assert "synthetic-provider-secret" not in resolved.text

    meeting = client.post(
        "/api/v1/meetings",
        headers=auth_headers(),
        json={
            "local_recording_id": local_recording_id,
            "duration_seconds": 600,
            "title": "Synthetic Provider Failure Recording",
            "title_source": "app_context",
            "calendar_match_attempt_id": resolved.json()["attempt_id"],
            "started_at": recording_started_at.isoformat(),
            "ended_at": (recording_started_at + timedelta(minutes=10)).isoformat(),
        },
    )

    assert meeting.status_code == 200
    assert meeting.json()["title"] == "Synthetic Provider Failure Recording"
    assert meeting.json()["processing_status"] == "not_submitted"
    assert meeting.json()["calendar_context"] == {
        "state": "skipped_stale_calendar",
        "label": "Без контекста календаря",
        "title_source": "app_context",
        "needs_owner_action": False,
    }
    upload_session = client.post(
        f"/api/v1/meetings/{meeting.json()['meeting_id']}/upload-sessions",
        headers=auth_headers(),
        json={"expected_tracks": ["manifest", "microphone", "system"]},
    )
    assert upload_session.status_code == 200
    assert upload_session.json()["status"] == "pending"
    assert upload_session.json()["expected_tracks"] == ["manifest", "microphone", "system"]

    async def load_truth() -> tuple[
        RecordingCalendarContextLink | None,
        list[CalendarAuditEvent],
    ]:
        async with client.app_state["sessionmaker"]() as db:
            context = await db.scalar(
                select(RecordingCalendarContextLink).where(
                    RecordingCalendarContextLink.meeting_id == UUID(meeting.json()["meeting_id"])
                )
            )
            audit_events = list(
                await db.scalars(
                    select(CalendarAuditEvent)
                    .where(
                        CalendarAuditEvent.workspace_id == context.workspace_id,
                        CalendarAuditEvent.outcome == "skipped_stale_calendar",
                    )
                    .order_by(CalendarAuditEvent.created_at)
                )
            )
            return context, audit_events

    context, audit_events = client.portal.call(load_truth)
    assert context is not None
    assert context.context_state == "skipped_stale_calendar"
    assert context.safe_reason_code == "latest_sync_failed"
    assert context.calendar_event_snapshot_id is None
    assert context.candidate_count == 0
    assert [event.event_type for event in audit_events] == [
        "calendar_match_resolved",
        "calendar_match_consumed",
    ]
    assert [event.metadata_json["freshness_class"] for event in audit_events] == [
        "latest_sync_failed",
        "latest_sync_failed",
    ]
    assert all("user_override_preserved" not in event.metadata_json for event in audit_events)


def _mark_failure(client, source_id: UUID, reason: str) -> None:
    sessionmaker = client.app_state["sessionmaker"]

    async def mark() -> None:
        async with sessionmaker() as session:
            source = await session.get(CalendarSource, source_id)
            source.last_successful_sync_at = datetime.now(UTC) - timedelta(minutes=30)
            record_source_sync_failure(source, reason=reason, now=datetime.now(UTC))
            await session.commit()

    asyncio.run(mark())
