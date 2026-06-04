from uuid import UUID

from tests.contract.test_ingest_openapi_contract import auth_headers


OTHER_WORKSPACE = UUID("20000000-0000-0000-0000-000000000099")


def test_cross_workspace_upload_session_read_is_denied_without_existence_leak(client) -> None:
    meeting = client.post(
        "/api/v1/meetings",
        headers=auth_headers(),
        json={"local_recording_id": "tenant-denial", "duration_seconds": 60},
    ).json()
    session = client.post(
        f"/api/v1/meetings/{meeting['meeting_id']}/upload-sessions",
        headers=auth_headers(),
        json={},
    ).json()
    wrong_headers = auth_headers() | {"X-Workspace-Id": str(OTHER_WORKSPACE)}
    response = client.get(f"/api/v1/upload-sessions/{session['session_id']}", headers=wrong_headers)
    assert response.status_code in {403, 404}
    assert "object_key" not in response.text
