from tests.contract.test_ingest_openapi_contract import auth_headers


def test_over_limit_duration_does_not_create_successful_meeting(client) -> None:
    response = client.post(
        "/api/v1/meetings",
        headers=auth_headers(),
        json={"local_recording_id": "too-long", "duration_seconds": 99_999},
    )
    assert response.status_code == 400
    assert response.json()["code"] == "recording_duration_exceeded"
