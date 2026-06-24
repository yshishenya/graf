from hashlib import sha256

from fastapi.testclient import TestClient

from tests.contract.test_ingest_openapi_contract import auth_headers
from tests.fixtures.artifacts import deterministic_wav_bytes, track_descriptor


def enable_processing_autostart(client: TestClient, temporal_client: object | None = None) -> object | None:
    client.app.state.settings.processing_enabled = True
    if temporal_client is not None:
        client.app.state.temporal_client = temporal_client
    return temporal_client


def create_finalized_meeting(
    client: TestClient,
    local_recording_id: str = "processing-ready",
    *,
    duration_seconds: int = 60,
) -> dict[str, object]:
    meeting_response = client.post(
        "/api/v1/meetings",
        headers=auth_headers(),
        json={"local_recording_id": local_recording_id, "duration_seconds": duration_seconds},
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
    tracks: list[dict[str, object]] = []
    for role, size in [("manifest", 8), ("microphone", 16), ("system", 24)]:
        data = deterministic_wav_bytes(size)
        digest = sha256(data).hexdigest()
        response = client.put(
            f"/api/v1/upload-sessions/{session['session_id']}/tracks/{role}/parts/0",
            headers=auth_headers() | {"X-Byte-Offset": "0", "X-Content-SHA256": digest},
            content=data,
        )
        assert response.status_code == 200
        tracks.append(track_descriptor(role, size) | {"sha256": digest, "byte_length": size})
    finalize = client.post(
        f"/api/v1/upload-sessions/{session['session_id']}/finalize",
        headers=auth_headers(),
        json={"manifest_sha256": tracks[0]["sha256"], "tracks": tracks},
    )
    assert finalize.status_code == 200
    finalized = finalize.json()
    return {"finalize": finalized, "meeting": finalized["meeting"], "session": session, "tracks": tracks}
