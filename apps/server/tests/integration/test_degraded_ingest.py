from hashlib import sha256

from tests.contract.test_ingest_openapi_contract import auth_headers
from tests.fixtures.artifacts import deterministic_wav_bytes, track_descriptor


def test_finalize_without_required_tracks_returns_truthful_failure(client) -> None:
    meeting = client.post(
        "/api/v1/meetings",
        headers=auth_headers(),
        json={"local_recording_id": "missing-track", "duration_seconds": 60},
    ).json()
    session = client.post(
        f"/api/v1/meetings/{meeting['meeting_id']}/upload-sessions",
        headers=auth_headers(),
        json={},
    ).json()
    data = deterministic_wav_bytes(64)
    digest = sha256(data).hexdigest()
    client.put(
        f"/api/v1/upload-sessions/{session['session_id']}/tracks/microphone/parts/0",
        headers=auth_headers() | {"X-Byte-Offset": "0", "X-Content-SHA256": digest},
        content=data,
    )
    response = client.post(
        f"/api/v1/upload-sessions/{session['session_id']}/finalize",
        headers=auth_headers(),
        json={"manifest_sha256": "a" * 64, "tracks": [track_descriptor("microphone", 64)]},
    )
    assert response.status_code == 422
    assert response.json()["detail"][0]["type"] == "too_short"
