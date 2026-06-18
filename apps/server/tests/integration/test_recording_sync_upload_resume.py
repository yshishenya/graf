from __future__ import annotations

import asyncio
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from uuid import UUID

import twobrain_rec_server.ingest.store as store_module
from tests.contract.test_ingest_openapi_contract import auth_headers
from tests.fixtures.artifacts import deterministic_wav_bytes
from twobrain_rec_server.db.models import UploadSession
from twobrain_rec_server.ingest.store import InMemoryIngestStore


def _create_meeting(client, local_recording_id: str) -> dict:
    response = client.post(
        "/api/v1/meetings",
        headers=auth_headers(),
        json={
            "local_recording_id": local_recording_id,
            "local_media_revision_id": f"{local_recording_id}--initial",
            "duration_seconds": 60,
        },
    )
    assert response.status_code == 200
    return response.json()


def _create_upload_session(client, meeting_id: str, *, idempotency_key: str = "resume-session") -> dict:
    response = client.post(
        f"/api/v1/meetings/{meeting_id}/upload-sessions",
        headers=auth_headers() | {"Idempotency-Key": idempotency_key},
        json={
            "expected_tracks": ["manifest", "microphone", "system"],
            "expected_track_sizes": {"manifest": 32, "microphone": 128, "system": 96},
        },
    )
    assert response.status_code == 200
    return response.json()


def _put_part(client, session_id: str, role: str, offset: int, data: bytes, part_number: int = 0):
    return client.put(
        f"/api/v1/upload-sessions/{session_id}/tracks/{role}/parts/{part_number}",
        headers=auth_headers() | {
            "X-Byte-Offset": str(offset),
            "X-Content-SHA256": sha256(data).hexdigest(),
        },
        content=data,
    )


def test_sync_state_returns_server_authoritative_resume_ranges(client) -> None:
    local_id = "resume-ranges-001"
    meeting = _create_meeting(client, local_id)
    session = _create_upload_session(client, meeting["meeting_id"])
    accepted = deterministic_wav_bytes(64)

    first = _put_part(client, session["session_id"], "microphone", 0, accepted)
    replay = _put_part(client, session["session_id"], "microphone", 0, accepted)
    sync_state = client.get(
        f"/api/v1/desktop/recordings/{local_id}/sync-state",
        headers=auth_headers(),
        params={"local_media_revision_id": f"{local_id}--initial"},
    )

    assert first.status_code == 200
    assert replay.status_code == 200
    assert sync_state.status_code == 200
    body = sync_state.json()
    assert body["meeting"]["meeting_id"] == meeting["meeting_id"]
    assert body["media_revision"]["media_revision_id"] == meeting["media_revision"]["media_revision_id"]
    assert body["upload_session"]["session_id"] == session["session_id"]
    assert body["upload_session"]["accepted_bytes_by_track"] == {"microphone": 64}
    assert body["upload_session"]["missing_ranges_by_track"]["microphone"] == [{"start": 64, "end": 128}]
    assert body["upload_session"]["missing_ranges_by_track"]["system"] == [{"start": 0, "end": 96}]
    assert body["conflict"]["state"] == "none"


def test_sync_state_expires_old_session_and_allows_same_revision_retry(client) -> None:
    local_id = "resume-expired-001"
    meeting = _create_meeting(client, local_id)
    session = _create_upload_session(client, meeting["meeting_id"], idempotency_key="resume-expired-original")

    async def expire_session() -> None:
        async with client.app_state["sessionmaker"]() as db:
            model = await db.get(UploadSession, UUID(session["session_id"]))
            assert model is not None
            model.expires_at = datetime.now(UTC) - timedelta(seconds=5)
            await db.commit()

    asyncio.run(expire_session())
    store_module.store = InMemoryIngestStore()

    expired_state = client.get(
        f"/api/v1/desktop/recordings/{local_id}/sync-state",
        headers=auth_headers(),
        params={"local_media_revision_id": f"{local_id}--initial"},
    )
    retry_session = _create_upload_session(
        client,
        meeting["meeting_id"],
        idempotency_key="resume-expired-retry",
    )

    assert expired_state.status_code == 200
    assert expired_state.json()["upload_session"]["status"] == "expired"
    assert expired_state.json()["conflict"]["state"] == "upload_session_expired"
    assert expired_state.json()["conflict"]["next_action"] == "create_upload_session"
    assert retry_session["session_id"] != session["session_id"]
    assert retry_session["media_revision_id"] == meeting["media_revision"]["media_revision_id"]
    assert retry_session["meeting_id"] == meeting["meeting_id"]
