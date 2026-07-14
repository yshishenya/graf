from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy import select

from tests.contract.test_calendar_context_contract import _seed_calendar_event
from tests.contract.test_ingest_openapi_contract import auth_headers
from tests.fakes.auth_contexts import USER_ID, WORKSPACE_ID
from twobrain_rec_server.db.models import (
    CalendarAuditEvent,
    CalendarEventSnapshot,
    CalendarParticipant,
    CalendarSource,
    ConferenceLinkCandidate,
    ExternalCalendar,
    Meeting,
    RecordingCalendarContextLink,
    RecordingCalendarMatchAttempt,
)

RESOLVE_PATH = "/api/v1/desktop/recordings/{local_recording_id}/calendar-context/resolve"
RECORDING_STARTED_AT = datetime(2026, 7, 13, 9, 0, tzinfo=UTC)


def _resolve_payload(*, started_at: datetime = RECORDING_STARTED_AT) -> dict[str, str]:
    return {
        "recording_started_at": started_at.isoformat(),
        "decision_intent": "automatic",
        "contract_version": "calendar_auto_context_v1",
    }


def _resolve_headers(key: str) -> dict[str, str]:
    return auth_headers() | {"Idempotency-Key": key}


def _aware_utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def _seed_private_calendar(client: TestClient, *, recording_started_at: datetime) -> None:
    async def seed() -> None:
        async with client.app_state["sessionmaker"]() as db:
            source = CalendarSource(
                workspace_id=WORKSPACE_ID,
                owner_user_id=USER_ID,
                provider_family="caldav_yandex",
                provider_label="Synthetic Private Calendar",
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
                provider_calendar_id="synthetic-private-primary",
                display_label="Synthetic Private Calendar",
                visibility="available",
                selected=True,
            )
            db.add(calendar)
            await db.flush()
            event = CalendarEventSnapshot(
                workspace_id=WORKSPACE_ID,
                calendar_source_id=source.id,
                external_calendar_id=calendar.id,
                provider_event_id="synthetic-private-event-098",
                ical_uid="synthetic-private-event-098@example.test",
                source_version="synthetic-private-v1",
                source_status="confirmed",
                starts_at=recording_started_at - timedelta(minutes=5),
                ends_at=recording_started_at + timedelta(minutes=55),
                duration_seconds=3600,
                all_day=False,
                title="Synthetic Restricted Planning Title",
                description="Synthetic Restricted Agenda Text",
                location="Synthetic Restricted Location",
                privacy_class="private",
                conference_summary_json={"meeting_link_present": True},
                attachments_metadata_json=[],
                provider_extras_json={
                    "participant_count": 1,
                    "provider_family": "caldav_yandex",
                    "roster_state": "private_redacted",
                    "title_state": "private_redacted",
                },
                safe_to_show_in_list=False,
                safe_to_use_as_title=False,
                sensitivity_reasons_json=["private_redacted"],
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
                        email="synthetic-private-person@example.test",
                        email_hash="sha256:synthetic-private-person",
                        display_name="Synthetic Restricted Person",
                        workspace_relation="owner",
                        recipient_candidate_class="organizer",
                    ),
                    ConferenceLinkCandidate(
                        calendar_event_snapshot_id=event.id,
                        workspace_id=WORKSPACE_ID,
                        source_field="location",
                        provider_family="generic",
                        url_hash="sha256:synthetic-private-link",
                        redacted_url_preview="private.example.test/...",
                        contains_passcode=True,
                        sensitivity_class="meeting_link",
                    ),
                ]
            )
            await db.commit()

    client.portal.call(seed)


def test_us1_resolve_and_create_openapi_contract_is_registered(client: TestClient) -> None:
    # FR-032/FR-048: one owned server contract serves desktop and cabinet truth.
    schema = client.app.openapi()
    operation = schema["paths"][RESOLVE_PATH]["post"]

    assert operation["operationId"] == "resolveRecordingCalendarContext"
    parameters = {
        (parameter["in"], parameter["name"]): parameter for parameter in operation["parameters"]
    }
    assert parameters[("path", "local_recording_id")]["required"] is True
    assert parameters[("path", "local_recording_id")]["schema"]["maxLength"] == 240
    assert parameters[("header", "Idempotency-Key")]["required"] is True
    operation_dump = json.dumps(operation, sort_keys=True)
    assert "ResolveRecordingCalendarContextRequest" in operation_dump
    assert "ResolveRecordingCalendarContextResponse" in operation_dump

    create_operation = schema["paths"]["/api/v1/meetings"]["post"]
    create_dump = json.dumps(create_operation, sort_keys=True)
    assert "CreateMeetingRequest" in create_dump
    assert "MeetingResponse" in create_dump
    create_fields = schema["components"]["schemas"]["CreateMeetingRequest"]["properties"]
    response_fields = schema["components"]["schemas"]["MeetingResponse"]["properties"]
    assert {"title_source", "calendar_match_attempt_id"} <= create_fields.keys()
    assert "calendar_context" in response_fields
    assert "MeetingCalendarContextSummary" in json.dumps(response_fields["calendar_context"])


def test_us1_resolve_rejects_local_recording_id_larger_than_storage_contract(
    client: TestClient,
) -> None:
    # FR-027/FR-032: path validation fails before a database-sized attempt write.
    response = client.post(
        RESOLVE_PATH.format(local_recording_id="r" * 241),
        headers=_resolve_headers("contract-overlong-local-recording-id-key-098"),
        json=_resolve_payload(),
    )

    assert response.status_code == 422
    assert response.json()["code"] == "request_validation_error"


def test_us1_resolve_expiry_is_exactly_evaluated_at_plus_24_hours(
    client: TestClient,
) -> None:
    # FR-052: response and durable attempt share the exact, non-rounded TTL boundary.
    local_recording_id = "contract-expiry-098"
    response = client.post(
        RESOLVE_PATH.format(local_recording_id=local_recording_id),
        headers=_resolve_headers("contract-expiry-key-098"),
        json=_resolve_payload(),
    )

    assert response.status_code == 200
    body = response.json()
    assert {
        "attempt_id",
        "context_state",
        "reason_code",
        "context_confidence",
        "candidate_count",
        "matcher_version",
        "expires_at",
    } == body.keys()

    async def load_attempt() -> RecordingCalendarMatchAttempt | None:
        async with client.app_state["sessionmaker"]() as db:
            return await db.scalar(
                select(RecordingCalendarMatchAttempt).where(
                    RecordingCalendarMatchAttempt.local_recording_id == local_recording_id
                )
            )

    attempt = client.portal.call(load_attempt)
    assert attempt is not None
    assert _aware_utc(attempt.expires_at) - _aware_utc(attempt.evaluated_at) == timedelta(hours=24)
    assert datetime.fromisoformat(body["expires_at"]).astimezone(UTC) == _aware_utc(
        attempt.expires_at
    )


def test_us1_resolve_is_idempotent_and_rejects_same_key_with_changed_input(
    client: TestClient,
) -> None:
    # FR-027: retries return one opaque attempt; key reuse with different input is explicit.
    path = RESOLVE_PATH.format(local_recording_id="contract-idempotency-098")
    headers = _resolve_headers("contract-idempotency-key-098")
    payload = _resolve_payload()

    first = client.post(path, headers=headers, json=payload)
    repeated = client.post(path, headers=headers, json=payload)
    changed = client.post(
        path,
        headers=headers,
        json=_resolve_payload(started_at=RECORDING_STARTED_AT + timedelta(seconds=1)),
    )

    assert first.status_code == 200
    assert repeated.status_code == 200
    assert repeated.json() == first.json()
    assert changed.status_code == 409
    assert changed.json()["code"] == "calendar_match_idempotency_conflict"


def test_us1_resolve_requires_idempotency_key(client: TestClient) -> None:
    response = client.post(
        RESOLVE_PATH.format(local_recording_id="contract-missing-key-098"),
        headers=auth_headers(),
        json=_resolve_payload(),
    )

    assert response.status_code == 422


def test_us2_private_resolve_hides_count_details_and_records_metadata_only_audit(
    client: TestClient,
) -> None:
    # FR-010/FR-029/FR-030/FR-033, SC-004/SC-011: hidden events have zero detail signal.
    recording_started_at = datetime.now(UTC).replace(microsecond=0)
    _seed_private_calendar(client, recording_started_at=recording_started_at)
    local_recording_id = "contract-private-no-detail-098"

    response = client.post(
        RESOLVE_PATH.format(local_recording_id=local_recording_id),
        headers=_resolve_headers("contract-private-no-detail-key-098"),
        json=_resolve_payload(started_at=recording_started_at),
    )

    assert response.status_code == 200
    body = response.json()
    assert body == {
        "attempt_id": body["attempt_id"],
        "context_state": "skipped_private",
        "reason_code": "private_free_busy_skipped",
        "context_confidence": "none",
        "candidate_count": 0,
        "matcher_version": "calendar_auto_match_v1",
        "expires_at": body["expires_at"],
    }
    forbidden_markers = (
        "synthetic-private-event-098",
        "Synthetic Restricted Planning Title",
        "Synthetic Restricted Agenda Text",
        "Synthetic Restricted Location",
        "synthetic-private-person@example.test",
        "Synthetic Restricted Person",
        "private.example.test",
        "synthetic-private-link",
    )
    assert all(marker not in response.text for marker in forbidden_markers)

    async def load_truth() -> tuple[
        RecordingCalendarMatchAttempt | None,
        list[CalendarAuditEvent],
    ]:
        async with client.app_state["sessionmaker"]() as db:
            attempt = await db.get(
                RecordingCalendarMatchAttempt,
                UUID(body["attempt_id"]),
            )
            audit_events = list(
                await db.scalars(
                    select(CalendarAuditEvent).where(
                        CalendarAuditEvent.workspace_id == WORKSPACE_ID,
                        CalendarAuditEvent.outcome == "skipped_private",
                    )
                )
            )
            return attempt, audit_events

    attempt, audit_events = client.portal.call(load_truth)
    assert attempt is not None
    assert attempt.candidate_count == 0
    assert attempt.candidate_event_ids_json == []
    assert attempt.matched_event_snapshot_id is None
    assert attempt.matched_title is None
    assert attempt.matched_roster_json == []
    assert len(audit_events) == 1
    audit = audit_events[0]
    assert audit.safe_reason_code == "private_free_busy_skipped"
    assert audit.metadata_json["candidate_count"] == 0
    assert "user_override_preserved" not in audit.metadata_json
    assert set(audit.metadata_json) <= {
        "context_state",
        "outcome",
        "safe_reason_code",
        "reason_code",
        "matcher_version",
        "candidate_count",
        "roster_count",
        "freshness_class",
        "decision_source",
        "title_applied",
        "user_override_preserved",
    }
    serialized_audit = repr(audit.metadata_json)
    assert all(marker not in serialized_audit for marker in forbidden_markers)


def test_us3_meeting_calendar_context_crud_openapi_contract_is_registered(
    client: TestClient,
) -> None:
    # FR-014/FR-015/FR-033/FR-038/FR-039: one safe projection backs owner CRUD.
    schema = client.app.openapi()
    path = schema["paths"]["/api/v1/meetings/{meeting_id}/calendar-context"]

    assert set(path) >= {"get", "put", "delete"}
    for method in ("get", "put", "delete"):
        response_dump = json.dumps(path[method]["responses"]["200"], sort_keys=True)
        assert "MeetingCalendarContextResponse" in response_dump
    assert "PutMeetingCalendarContextRequest" in json.dumps(
        path["put"]["requestBody"], sort_keys=True
    )

    fields = schema["components"]["schemas"]["MeetingCalendarContextResponse"]["properties"]
    assert {
        "meeting_id",
        "event_id",
        "context_state",
        "context_confidence",
        "reason_code",
        "decision_source",
        "title_source",
        "matched_title",
        "matched_event_starts_at",
        "matched_event_ends_at",
        "candidate_count",
        "candidates",
        "roster",
        "previous_recurring_meeting",
        "can_change",
        "can_clear",
    } <= fields.keys()


def test_us3_owner_get_select_retry_and_clear_use_one_authoritative_projection(
    client: TestClient,
) -> None:
    # FR-014/FR-015/FR-027/FR-038/FR-039/FR-051, SC-013/SC-014: owner intent is durable.
    meeting = client.post(
        "/api/v1/meetings",
        headers=auth_headers(),
        json={
            "local_recording_id": "contract-owner-context-crud-098",
            "duration_seconds": 1200,
            "started_at": "2026-07-01T09:00:00Z",
            "title": "Synthetic Owner Recording",
            "title_source": "app_context",
        },
    )
    assert meeting.status_code == 200
    meeting_id = meeting.json()["meeting_id"]
    event_id = _seed_calendar_event(client)
    path = f"/api/v1/meetings/{meeting_id}/calendar-context"
    selection = {"event_id": event_id, "context_reason": "ambiguity_resolution"}

    selected = client.put(path, headers=auth_headers(), json=selection)
    read = client.get(path, headers=auth_headers())
    retried = client.put(path, headers=auth_headers(), json=selection)
    cleared = client.delete(path, headers=auth_headers())
    clear_retried = client.delete(path, headers=auth_headers())

    assert selected.status_code == 200
    assert read.status_code == 200
    assert retried.status_code == 200
    selected_body = selected.json()
    assert selected_body["context_state"] == "matched_user"
    assert selected_body["reason_code"] == "user_selected"
    assert selected_body["decision_source"] == "user"
    assert selected_body["event_id"] == event_id
    assert selected_body["candidate_count"] == 0
    assert selected_body["candidates"] == []
    assert selected_body["can_change"] is True
    assert selected_body["can_clear"] is True
    assert read.json() == selected_body
    assert retried.json() == selected_body

    for response in (cleared, clear_retried):
        assert response.status_code == 200
        body = response.json()
        assert body["context_state"] == "cleared_by_user"
        assert body["reason_code"] == "user_cleared"
        assert body["decision_source"] == "user"
        assert body["event_id"] is None
        assert body["candidate_count"] == 0
        assert body["candidates"] == []
        assert body["roster"] is None
        assert body["can_change"] is True
        assert body["can_clear"] is False


def test_us5_previous_recurring_meeting_openapi_projection_is_metadata_bounded(
    client: TestClient,
) -> None:
    # FR-024/FR-025/FR-026: the pointer has no transcript, summary, roster, or access payload.
    schemas = client.app.openapi()["components"]["schemas"]
    projection = schemas["PreviousRecurringMeetingView"]

    assert projection["additionalProperties"] is False
    assert set(projection["properties"]) == {
        "meeting_id",
        "safe_title",
        "started_at",
        "readiness_state",
    }
    assert set(projection["required"]) == {
        "meeting_id",
        "started_at",
        "readiness_state",
    }
    assert schemas["PreviousRecurringMeetingReadiness"]["enum"] == [
        "notes_ready",
        "transcript_ready",
        "processing",
        "unavailable",
    ]


def test_us5_authorized_previous_recurring_projection_matches_context_and_review_api(
    client: TestClient,
) -> None:
    # FR-024/FR-025/FR-045: one bounded pointer is reused without replacing current truth.
    previous_id, current_id = _create_recurring_pointer_fixture(
        client,
        local_recording_prefix="t077-authorized-pointer",
    )

    context_response = client.get(
        f"/api/v1/meetings/{current_id}/calendar-context",
        headers=auth_headers(),
    )
    review_response = client.get(
        f"/api/v1/cabinet/meetings/{current_id}",
        headers=auth_headers(),
    )

    assert context_response.status_code == 200
    assert review_response.status_code == 200
    expected_pointer = {
        "meeting_id": str(previous_id),
        "safe_title": "Synthetic Previous Planning",
        "started_at": "2026-07-06T09:00:00Z",
        "readiness_state": "processing",
    }
    assert context_response.json()["previous_recurring_meeting"] == expected_pointer
    review = review_response.json()
    assert review["calendar_context_detail"]["previous_recurring_meeting"] == expected_pointer
    assert review["meeting"]["title"] == "Synthetic Current Planning"
    assert review["calendar_roster"]["participants"][0]["display_name"] == (
        "Synthetic Current Invitee"
    )
    for forbidden in (
        "SYNTHETIC_PREVIOUS_DESCRIPTION_DO_NOT_RENDER",
        "Synthetic Previous Invitee",
        "synthetic-previous-transcript-do-not-render",
    ):
        assert forbidden not in context_response.text
        assert forbidden not in review_response.text


def test_us5_deleted_previous_recurring_projection_is_null_without_existence_leak(
    client: TestClient,
) -> None:
    # FR-025/FR-026: an independently denied predecessor is indistinguishable from absence.
    previous_id, current_id = _create_recurring_pointer_fixture(
        client,
        local_recording_prefix="t077-deleted-pointer",
        previous_deleted=True,
    )

    context_response = client.get(
        f"/api/v1/meetings/{current_id}/calendar-context",
        headers=auth_headers(),
    )
    review_response = client.get(
        f"/api/v1/cabinet/meetings/{current_id}",
        headers=auth_headers(),
    )

    assert context_response.status_code == 200
    assert review_response.status_code == 200
    assert context_response.json()["previous_recurring_meeting"] is None
    assert review_response.json()["calendar_context_detail"]["previous_recurring_meeting"] is None
    for forbidden in (
        str(previous_id),
        "Synthetic Previous Planning",
        "Synthetic Previous Invitee",
        "SYNTHETIC_PREVIOUS_DESCRIPTION_DO_NOT_RENDER",
    ):
        assert forbidden not in context_response.text
        assert forbidden not in review_response.text


def _create_recurring_pointer_fixture(
    client: TestClient,
    *,
    local_recording_prefix: str,
    previous_deleted: bool = False,
) -> tuple[UUID, UUID]:
    starts = (
        datetime(2026, 7, 6, 9, 0, tzinfo=UTC),
        datetime(2026, 7, 13, 9, 0, tzinfo=UTC),
    )
    titles = ("Synthetic Previous Planning", "Synthetic Current Planning")
    meeting_ids: list[UUID] = []
    for sequence, (title, started_at) in enumerate(zip(titles, starts, strict=True), start=1):
        response = client.post(
            "/api/v1/meetings",
            headers=auth_headers(),
            json={
                "local_recording_id": f"{local_recording_prefix}-{sequence}",
                "title": title,
                "title_source": "app_context",
                "started_at": started_at.isoformat(),
                "ended_at": (started_at + timedelta(minutes=30)).isoformat(),
                "recording_display_timezone_offset_minutes": 180,
                "duration_seconds": 1800,
            },
        )
        assert response.status_code == 200
        meeting_ids.append(UUID(response.json()["meeting_id"]))

    previous_id, current_id = meeting_ids

    async def seed() -> None:
        async with client.app_state["sessionmaker"]() as db:
            source = CalendarSource(
                workspace_id=WORKSPACE_ID,
                owner_user_id=USER_ID,
                provider_family="caldav_yandex",
                provider_label="Synthetic Recurring Calendar",
                auth_mode="app_password",
                credential_state="sealed",
                connection_state="active",
                sync_state="synced",
                sync_horizon_start=starts[0] - timedelta(days=1),
                sync_horizon_end=starts[1] + timedelta(days=1),
                last_sync_finished_at=starts[1] - timedelta(minutes=5),
                last_successful_sync_at=starts[1] - timedelta(minutes=5),
                capabilities_json={},
                selected_calendar_count=1,
            )
            db.add(source)
            await db.flush()
            calendar = ExternalCalendar(
                workspace_id=WORKSPACE_ID,
                calendar_source_id=source.id,
                provider_calendar_id=f"{local_recording_prefix}-calendar",
                display_label="Synthetic Recurring Calendar",
                visibility="available",
                selected=True,
            )
            db.add(calendar)
            await db.flush()

            events: list[CalendarEventSnapshot] = []
            for sequence, (title, started_at) in enumerate(
                zip(titles, starts, strict=True), start=1
            ):
                event = CalendarEventSnapshot(
                    workspace_id=WORKSPACE_ID,
                    calendar_source_id=source.id,
                    external_calendar_id=calendar.id,
                    provider_event_id=f"{local_recording_prefix}-event-{sequence}",
                    ical_uid=f"{local_recording_prefix}@example.test",
                    recurring_series_id=f"{local_recording_prefix}-series",
                    recurrence_instance_id=started_at.isoformat(),
                    source_version=f"synthetic-v{sequence}",
                    source_status="confirmed",
                    starts_at=started_at,
                    ends_at=started_at + timedelta(hours=1),
                    duration_seconds=3600,
                    timezone="Europe/Moscow",
                    all_day=False,
                    title=title,
                    description=(
                        "SYNTHETIC_PREVIOUS_DESCRIPTION_DO_NOT_RENDER"
                        if sequence == 1
                        else "Synthetic current agenda"
                    ),
                    privacy_class="public",
                    conference_summary_json={},
                    attachments_metadata_json=[],
                    provider_extras_json={"roster_state": "available"},
                    safe_to_show_in_list=True,
                    safe_to_use_as_title=True,
                    sensitivity_reasons_json=[],
                    source_updated_at=starts[1] - timedelta(minutes=5),
                )
                db.add(event)
                await db.flush()
                events.append(event)

            previous_meeting = await db.get(Meeting, previous_id)
            assert previous_meeting is not None
            previous_meeting.status = "ingested_pending_processing"
            previous_meeting.processing_status = "polling"
            if previous_deleted:
                previous_meeting.deletion_state = "complete"

            links = list(
                await db.scalars(
                    select(RecordingCalendarContextLink)
                    .where(
                        RecordingCalendarContextLink.workspace_id == WORKSPACE_ID,
                        RecordingCalendarContextLink.meeting_id.in_(meeting_ids),
                    )
                    .order_by(RecordingCalendarContextLink.meeting_id)
                )
            )
            links_by_meeting = {link.meeting_id: link for link in links}
            for sequence, (meeting_id, event, title, started_at) in enumerate(
                zip(meeting_ids, events, titles, starts, strict=True), start=1
            ):
                link = links_by_meeting[meeting_id]
                invitee = (
                    "Synthetic Previous Invitee" if sequence == 1 else "Synthetic Current Invitee"
                )
                link.calendar_event_snapshot_id = event.id
                link.context_state = "matched_auto"
                link.context_confidence = "high"
                link.context_reasons_json = ["single_fresh_candidate"]
                link.title_source = "calendar"
                link.roster_source = "calendar"
                link.manual_override_state = "none"
                link.safe_reason_code = "single_fresh_candidate"
                link.decision_source = "automatic"
                link.matcher_version = "calendar_auto_match_v1"
                link.evaluated_at = started_at
                link.candidate_event_ids_json = []
                link.candidate_count = 0
                link.matched_event_starts_at = started_at
                link.matched_event_ends_at = started_at + timedelta(hours=1)
                link.matched_title = title
                link.matched_title_state = "available"
                link.matched_roster_json = [
                    {
                        "participant_kind": "required_attendee",
                        "response_status": "accepted",
                        "display_name": invitee,
                        "email_present": False,
                        "workspace_relation": "external",
                        "recipient_candidate_class": "external_attendee",
                    }
                ]
                link.matched_roster_state = "available"
                link.matched_roster_count = 1
                link.recurring_series_key_sha256 = "a" * 64
                link.linked_at = started_at
            await db.commit()

    client.portal.call(seed)
    return previous_id, current_id
