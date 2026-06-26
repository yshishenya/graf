from tests.contract.test_ingest_openapi_contract import auth_headers


def test_rejects_oversized_and_control_character_meeting_fields(client) -> None:
    oversized = client.post(
        "/api/v1/meetings",
        headers=auth_headers(),
        json={"local_recording_id": "x" * 241, "title": "ok", "duration_seconds": 60},
    )
    control = client.post(
        "/api/v1/meetings",
        headers=auth_headers(),
        json={"local_recording_id": "bad\nid", "title": "ok", "duration_seconds": 60},
    )

    assert oversized.status_code == 422
    assert control.status_code == 422
    assert oversized.json()["code"] == "request_validation_error"
    assert control.json()["code"] == "request_validation_error"
    assert "bad\\nid" not in control.text


def test_request_id_is_bounded_and_sanitized(client) -> None:
    response = client.get(
        "/api/v1/health/live",
        headers={"X-Request-Id": "request\n" + ("x" * 300)},
    )

    assert response.status_code == 200
    assert "\n" not in response.headers["x-request-id"]
    assert len(response.headers["x-request-id"]) <= 120
