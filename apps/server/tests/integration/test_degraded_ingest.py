from hashlib import sha256

from tests.contract.test_ingest_openapi_contract import auth_headers
from tests.fixtures.artifacts import deterministic_wav_bytes, track_descriptor
from tests.fixtures.cabinet import seed_cabinet_meetings


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


def test_desktop_sync_exposes_review_ready_state_for_processed_upload(client) -> None:
    seeds = seed_cabinet_meetings(client)

    response = client.get(
        "/api/v1/desktop/recordings/cabinet-ready/sync-state",
        headers=auth_headers(),
        params={"local_media_revision_id": "cabinet-ready--initial"},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["meeting"]["meeting_id"] == str(seeds.ready_id)
    assert payload["review"]["available"] is True
    assert payload["review"]["status"] == "ready"
    assert payload["review"]["media_revision_id"] == payload["media_revision"]["media_revision_id"]
    assert payload["review"]["transcript_available"] is True
    assert payload["review"]["diarization_available"] is True
    assert payload["review"]["desktop_url"] == f"/desktop/meetings/{seeds.ready_id}"
