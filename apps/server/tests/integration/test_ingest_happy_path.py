from hashlib import sha256
from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy import select

from tests.contract.test_ingest_openapi_contract import auth_headers
from tests.fixtures.artifacts import deterministic_wav_bytes, track_descriptor
from twobrain_rec_server.db.models import Meeting


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


def test_create_meeting_persists_recording_title_and_instants(client: TestClient) -> None:
    response = client.post(
        "/api/v1/meetings",
        headers=auth_headers(),
        json={
            "local_recording_id": "meeting-metadata-059",
            "local_media_revision_id": "meeting-metadata-059--initial",
            "title": "Zoom - 2026-06-26 11:30",
            "started_at": "2026-06-26T11:30:00Z",
            "ended_at": "2026-06-26T12:15:00Z",
            "duration_seconds": 2700,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["started_at"].startswith("2026-06-26T11:30:00")
    assert payload["ended_at"].startswith("2026-06-26T12:15:00")
    meeting_id = UUID(payload["meeting_id"])

    async def persisted_metadata():
        async with client.app_state["sessionmaker"]() as db:
            model = await db.scalar(select(Meeting).where(Meeting.id == meeting_id))
            assert model is not None
            return model.title, model.started_at, model.ended_at

    title, started_at, ended_at = client.portal.call(persisted_metadata)
    assert title == "Zoom - 2026-06-26 11:30"
    assert started_at is not None
    assert ended_at is not None
    assert started_at.isoformat().startswith("2026-06-26T11:30:00")
    assert ended_at.isoformat().startswith("2026-06-26T12:15:00")
