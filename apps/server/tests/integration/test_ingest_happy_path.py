from hashlib import sha256

from fastapi.testclient import TestClient

from tests.contract.test_ingest_openapi_contract import auth_headers
from tests.fixtures.artifacts import deterministic_wav_bytes, track_descriptor


def test_30_minute_dual_track_happy_path(client: TestClient) -> None:
    meeting_response = client.post(
        "/api/v1/meetings",
        headers=auth_headers(),
        json={"local_recording_id": "meeting-30m", "duration_seconds": 1800},
    )
    assert meeting_response.status_code == 200
    meeting_id = meeting_response.json()["meeting_id"]

    session_response = client.post(
        f"/api/v1/meetings/{meeting_id}/upload-sessions",
        headers=auth_headers(),
        json={"expected_tracks": ["manifest", "microphone", "system"]},
    )
    assert session_response.status_code == 200
    session_id = session_response.json()["session_id"]

    tracks = []
    for role in ["manifest", "microphone", "system"]:
        data = deterministic_wav_bytes(512)
        digest = sha256(data).hexdigest()
        response = client.put(
            f"/api/v1/upload-sessions/{session_id}/tracks/{role}/parts/0",
            headers=auth_headers() | {"X-Byte-Offset": "0", "X-Content-SHA256": digest},
            content=data,
        )
        assert response.status_code == 200
        tracks.append(track_descriptor(role, len(data)) | {"sha256": digest, "byte_length": len(data)})

    finalize = client.post(
        f"/api/v1/upload-sessions/{session_id}/finalize",
        headers=auth_headers(),
        json={"manifest_sha256": tracks[0]["sha256"], "tracks": tracks},
    )
    assert finalize.status_code == 200
    assert finalize.json()["meeting"]["status"] == "ingested_pending_processing"
