import json
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID

import pytest
import yaml
from pydantic import ValidationError

from twobrain_rec_server.api.schemas import (
    CalendarContextCandidateView,
    CalendarMatchDecisionIntent,
    CalendarRosterSnapshotItem,
    CreateMeetingRequest,
    MeetingCalendarContextSummary,
    ResolveRecordingCalendarContextRequest,
    ResolveRecordingCalendarContextResponse,
)

CONTRACT_PATH = (
    Path(__file__).parents[4] / "specs/012-server-ingest-foundation/contracts/openapi.yaml"
)


def test_runtime_openapi_matches_committed_contract(client) -> None:
    runtime = client.get("/openapi.json").json()
    committed = yaml.safe_load(CONTRACT_PATH.read_text(encoding="utf-8"))

    assert runtime == committed


def test_problem_schema_uses_request_id_not_trace_id(client) -> None:
    schema = client.get("/openapi.json").json()
    problem = schema["components"]["schemas"]["Problem"]["properties"]

    assert "request_id" in problem
    assert "trace_id" not in problem


def test_readiness_contract_has_public_503_and_internal_detail(client) -> None:
    schema = client.get("/openapi.json").json()

    public_ready = schema["paths"]["/api/v1/health/ready"]["get"]["responses"]
    internal_ready = schema["paths"]["/api/v1/health/ready/internal"]["get"]["responses"]
    assert "200" in public_ready
    assert "503" in public_ready
    assert "checks" not in schema["components"]["schemas"]["ReadyResponse"]["properties"]
    assert "checks" in schema["components"]["schemas"]["ReadyDetailResponse"]["properties"]
    assert "200" in internal_ready
    assert "503" in internal_ready


def test_validation_error_schema_matches_current_toolchain(client) -> None:
    schema = client.get("/openapi.json").json()
    validation_error = schema["components"]["schemas"]["ValidationError"]["properties"]

    required = {"loc", "msg", "type"}
    assert required.issubset(validation_error)


def test_cabinet_csrf_guard_does_not_change_public_openapi_contract(client) -> None:
    schema = client.get("/openapi.json").json()
    operation = schema["paths"]["/api/v1/cabinet/meetings/{meeting_id}/deletion-requests"]["post"]

    assert operation["operationId"] == "createMeetingDeletionRequest"
    assert "CreateDeletionRequest" in json.dumps(operation, sort_keys=True)
    assert "X-CSRF-Token" not in json.dumps(operation, sort_keys=True)


def test_meeting_detection_telemetry_openapi_contract_is_registered(client) -> None:
    schema = client.get("/openapi.json").json()
    operation = schema["paths"]["/api/v1/desktop/meeting-detection/telemetry"]["post"]

    assert operation["operationId"] == "createMeetingDetectionTelemetry"
    assert "MeetingDetectionTelemetryRequest" in json.dumps(operation, sort_keys=True)
    assert "MeetingDetectionTelemetryResponse" in json.dumps(operation, sort_keys=True)


def test_meeting_detection_registry_openapi_contract_is_registered(client) -> None:
    schema = client.get("/openapi.json").json()
    operation = schema["paths"]["/api/v1/desktop/meeting-detection/target-registry"]["get"]

    assert operation["operationId"] == "getMeetingDetectionTargetRegistry"
    assert "MeetingDetectionRegistryResponse" in json.dumps(operation, sort_keys=True)
    assert "If-None-Match" in json.dumps(operation, sort_keys=True)
    assert "X-GRAF-Meeting-Detection-Signals" not in json.dumps(operation, sort_keys=True)


def test_calendar_auto_context_create_and_context_schemas_are_registered(client) -> None:
    schema = client.get("/openapi.json").json()
    components = schema["components"]["schemas"]

    create_fields = components["CreateMeetingRequest"]["properties"]
    assert {"title_source", "calendar_match_attempt_id"} <= create_fields.keys()

    context_fields = components["MeetingCalendarContextResponse"]["properties"]
    assert {
        "context_state",
        "context_confidence",
        "reason_code",
        "decision_source",
        "matched_title",
        "matched_event_starts_at",
        "matched_event_ends_at",
        "candidate_count",
        "candidates",
        "roster",
        "previous_recurring_meeting",
        "can_change",
        "can_clear",
    } <= context_fields.keys()
    context_dump = json.dumps(
        {
            name: components[name]
            for name in (
                "CalendarContextCandidateView",
                "CalendarContextRosterView",
                "CalendarRosterSnapshotItem",
                "PreviousRecurringMeetingView",
            )
        },
        sort_keys=True,
    )
    for forbidden_field in ("description", "email", "meeting_url", "passcode", "provider_payload"):
        assert f'"{forbidden_field}"' not in context_dump


def test_calendar_auto_context_resolve_models_have_owned_schema_until_route_registration() -> None:
    # T024 registers the resolve route. Until then these direct assertions keep
    # its request/response contract owned without weakening exact runtime drift.
    request_schema = ResolveRecordingCalendarContextRequest.model_json_schema()
    response_schema = ResolveRecordingCalendarContextResponse.model_json_schema()
    summary_schema = MeetingCalendarContextSummary.model_json_schema()

    assert request_schema["additionalProperties"] is False
    assert response_schema["additionalProperties"] is False
    assert summary_schema["additionalProperties"] is False
    assert {
        "recording_started_at",
        "decision_intent",
        "event_id",
        "contract_version",
    } <= request_schema["properties"].keys()
    assert {
        "attempt_id",
        "context_state",
        "reason_code",
        "context_confidence",
        "candidate_count",
        "matcher_version",
        "expires_at",
    } <= response_schema["properties"].keys()

    recording_started_at = datetime(2026, 7, 13, 9, tzinfo=UTC)
    automatic = ResolveRecordingCalendarContextRequest(
        recording_started_at=recording_started_at,
        decision_intent=CalendarMatchDecisionIntent.AUTOMATIC,
        contract_version="calendar_auto_context_v1",
    )
    assert automatic.event_id is None

    with pytest.raises(ValidationError):
        ResolveRecordingCalendarContextRequest(
            recording_started_at=recording_started_at,
            decision_intent=CalendarMatchDecisionIntent.USER_SELECTED,
            contract_version="calendar_auto_context_v1",
        )
    with pytest.raises(ValidationError):
        ResolveRecordingCalendarContextRequest(
            recording_started_at=recording_started_at,
            decision_intent=CalendarMatchDecisionIntent.AUTOMATIC,
            event_id=UUID("00000000-0000-0000-0000-000000000098"),
            contract_version="calendar_auto_context_v1",
        )

    legacy_create = CreateMeetingRequest(local_recording_id="legacy-client", duration_seconds=1)
    assert legacy_create.title_source is None
    assert legacy_create.calendar_match_attempt_id is None

    candidate_fields = {
        "event_id": UUID("00000000-0000-0000-0000-000000000011"),
        "safe_title": "Planning",
        "starts_at": recording_started_at,
        "ends_at": datetime(2026, 7, 13, 10, tzinfo=UTC),
        "safe_source_label": "Work calendar",
    }
    with pytest.raises(ValidationError):
        CalendarContextCandidateView(**candidate_fields, description="forbidden")
    with pytest.raises(ValidationError):
        CalendarRosterSnapshotItem(
            participant_kind="person",
            response_status="accepted",
            email="forbidden",
        )
