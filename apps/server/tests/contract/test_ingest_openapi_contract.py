from hashlib import sha256

from fastapi.testclient import TestClient

from tests.fakes.auth_contexts import DEVICE_ID, ORG_ID, USER_ID, WORKSPACE_ID
from tests.fixtures.artifacts import deterministic_wav_bytes, track_descriptor


def auth_headers() -> dict[str, str]:
    return {
        "X-Organization-Id": str(ORG_ID),
        "X-Workspace-Id": str(WORKSPACE_ID),
        "X-User-Id": str(USER_ID),
        "X-Device-Id": str(DEVICE_ID),
    }


def test_happy_path_contract_exposes_server_mediated_ingest(client: TestClient) -> None:
    meeting_response = client.post(
        "/api/v1/meetings",
        headers=auth_headers(),
        json={
            "local_recording_id": "local-001",
            "title": "Contract test",
            "duration_seconds": 1800,
        },
    )
    assert meeting_response.status_code == 200
    meeting = meeting_response.json()

    session_response = client.post(
        f"/api/v1/meetings/{meeting['meeting_id']}/upload-sessions",
        headers=auth_headers(),
        json={"expected_tracks": ["manifest", "microphone", "system"]},
    )
    assert session_response.status_code == 200
    session = session_response.json()
    assert session["upload_strategy"] == "server_mediated"

    uploaded_tracks = []
    for index, role in enumerate(["manifest", "microphone", "system"]):
        data = deterministic_wav_bytes(128 + index)
        digest = sha256(data).hexdigest()
        part_response = client.put(
            f"/api/v1/upload-sessions/{session['session_id']}/tracks/{role}/parts/0",
            headers=auth_headers() | {"X-Byte-Offset": "0", "X-Content-SHA256": digest},
            content=data,
        )
        assert part_response.status_code == 200
        uploaded_tracks.append(track_descriptor(role, len(data)) | {"sha256": digest, "byte_length": len(data)})

    finalize_response = client.post(
        f"/api/v1/upload-sessions/{session['session_id']}/finalize",
        headers=auth_headers(),
        json={"manifest_sha256": uploaded_tracks[0]["sha256"], "tracks": uploaded_tracks},
    )
    assert finalize_response.status_code == 200
    finalized = finalize_response.json()
    assert finalized["meeting"]["status"] == "ingested_pending_processing"
    assert finalized["workflow_started"] is False
    assert finalized["mediascribe_job_created"] is False
    assert finalized["upload_session"]["workflow_id"] is None
    assert finalized["upload_session"]["mediascribe_job_id"] is None
