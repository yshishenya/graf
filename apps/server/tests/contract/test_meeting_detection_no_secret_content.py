from __future__ import annotations

from copy import deepcopy

from fastapi.testclient import TestClient

from tests.contract.test_ingest_openapi_contract import auth_headers
from tests.contract.test_meeting_detection_api_contract import meeting_detection_payload


def test_telemetry_rejects_allowed_field_with_private_url(client: TestClient) -> None:
    payload = meeting_detection_payload()
    unsafe = deepcopy(payload)
    unsafe["unknownNativeAppRollups"][0]["displayName"] = "https://private.example/join"

    response = client.post(
        "/api/v1/desktop/meeting-detection/telemetry",
        headers=auth_headers() | {"Idempotency-Key": "meeting-detection:unsafe-url"},
        json=unsafe,
    )

    assert response.status_code == 400
    body = response.json()
    assert body["code"] == "meeting_detection_telemetry_unsafe_payload"
    assert "private.example" not in str(body)


def test_telemetry_rejects_email_without_echoing_secret(client: TestClient) -> None:
    payload = meeting_detection_payload()
    unsafe = deepcopy(payload)
    unsafe["unknownNativeAppRollups"][0]["displayName"] = "alice@example.com"

    response = client.post(
        "/api/v1/desktop/meeting-detection/telemetry",
        headers=auth_headers() | {"Idempotency-Key": "meeting-detection:unsafe-email"},
        json=unsafe,
    )

    assert response.status_code == 400
    body = response.json()
    assert body["code"] == "meeting_detection_telemetry_unsafe_payload"
    assert "alice@example.com" not in str(body)


def test_telemetry_response_does_not_echo_candidate_identity(client: TestClient) -> None:
    response = client.post(
        "/api/v1/desktop/meeting-detection/telemetry",
        headers=auth_headers() | {"Idempotency-Key": "meeting-detection:no-echo"},
        json=meeting_detection_payload(),
    )

    assert response.status_code == 201
    body_dump = str(response.json())
    assert "Example VKS" not in body_dump
    assert "ru.example.vks" not in body_dump
