from datetime import UTC, datetime, timedelta
from hashlib import sha256
from uuid import UUID

import twobrain_rec_server.ingest.store as store_module
from sqlalchemy import select
from twobrain_rec_server.db.models import Meeting, UploadSession
from twobrain_rec_server.ingest.store import InMemoryIngestStore

from tests.contract.test_ingest_openapi_contract import auth_headers
from tests.fixtures.artifacts import deterministic_wav_bytes, track_descriptor


def _create_meeting(client, local_recording_id: str = "lifecycle") -> dict:
    response = client.post(
        "/api/v1/meetings",
        headers=auth_headers(),
        json={"local_recording_id": local_recording_id, "duration_seconds": 60},
    )
    assert response.status_code == 200
    return response.json()


def _create_upload_session(client, meeting_id: str, expected_track_sizes: dict[str, int] | None = None) -> dict:
    response = client.post(
        f"/api/v1/meetings/{meeting_id}/upload-sessions",
        headers=auth_headers(),
        json={"expected_track_sizes": expected_track_sizes or {"manifest": 8, "microphone": 9, "system": 10}},
    )
    assert response.status_code == 200
    return response.json()


def _upload_tracks(client, session_id: str) -> list[dict[str, object]]:
    tracks = []
    for size, role in [(8, "manifest"), (9, "microphone"), (10, "system")]:
        data = deterministic_wav_bytes(size)
        digest = sha256(data).hexdigest()
        response = client.put(
            f"/api/v1/upload-sessions/{session_id}/tracks/{role}/parts/0",
            headers=auth_headers() | {"X-Byte-Offset": "0", "X-Content-SHA256": digest},
            content=data,
        )
        assert response.status_code == 200
        tracks.append(track_descriptor(role, size) | {"sha256": digest, "byte_length": size})
    return tracks


def _finalize(client, session_id: str, tracks: list[dict[str, object]]):
    return client.post(
        f"/api/v1/upload-sessions/{session_id}/finalize",
        headers=auth_headers(),
        json={"manifest_sha256": tracks[0]["sha256"], "tracks": tracks},
    )


def test_one_active_upload_session_per_meeting(client) -> None:
    meeting = _create_meeting(client, "lifecycle-one-active")
    first = _create_upload_session(client, meeting["meeting_id"])

    second = client.post(
        f"/api/v1/meetings/{meeting['meeting_id']}/upload-sessions",
        headers=auth_headers(),
        json={"expected_track_sizes": {"manifest": 8, "microphone": 9, "system": 10}},
    )

    assert first["status"] == "pending"
    assert second.status_code == 409
    assert second.json()["code"] == "active_upload_session_exists"


def test_create_upload_session_reloads_persisted_meeting_after_store_reset(client) -> None:
    meeting = _create_meeting(client, "lifecycle-cold-meeting")
    store_module.store = InMemoryIngestStore()

    session = _create_upload_session(client, meeting["meeting_id"])

    assert session["meeting_id"] == meeting["meeting_id"]


def test_create_upload_session_persists_meeting_uploading_status(client) -> None:
    meeting = _create_meeting(client, "lifecycle-meeting-status")

    _create_upload_session(client, meeting["meeting_id"])

    async def persisted_status() -> str | None:
        async with client.app_state["sessionmaker"]() as db:
            return await db.scalar(select(Meeting.status).where(Meeting.id == UUID(meeting["meeting_id"])))

    import asyncio

    assert asyncio.run(persisted_status()) == "uploading"


def test_conflicting_meeting_create_is_rejected(client) -> None:
    first = client.post(
        "/api/v1/meetings",
        headers=auth_headers(),
        json={"local_recording_id": "lifecycle-meeting-conflict", "duration_seconds": 60, "title": "Original"},
    )
    assert first.status_code == 200

    replay = client.post(
        "/api/v1/meetings",
        headers=auth_headers(),
        json={"local_recording_id": "lifecycle-meeting-conflict", "duration_seconds": 60, "title": "Original"},
    )
    conflict = client.post(
        "/api/v1/meetings",
        headers=auth_headers(),
        json={"local_recording_id": "lifecycle-meeting-conflict", "duration_seconds": 61, "title": "Changed"},
    )

    assert replay.status_code == 200
    assert replay.json()["meeting_id"] == first.json()["meeting_id"]
    assert conflict.status_code == 409
    assert conflict.json()["code"] == "idempotency_conflict"


def test_upload_session_idempotency_key_replays_matching_request(client) -> None:
    meeting = _create_meeting(client, "lifecycle-session-idempotency")
    headers = auth_headers() | {"Idempotency-Key": "session-create-001"}
    first = client.post(
        f"/api/v1/meetings/{meeting['meeting_id']}/upload-sessions",
        headers=headers,
        json={"expected_track_sizes": {"system": 4}},
    )
    replay = client.post(
        f"/api/v1/meetings/{meeting['meeting_id']}/upload-sessions",
        headers=headers,
        json={"expected_track_sizes": {"system": 4}},
    )

    assert first.status_code == 200
    assert replay.status_code == 200
    assert replay.json()["session_id"] == first.json()["session_id"]


def test_upload_session_idempotency_key_conflict_is_rejected(client) -> None:
    meeting = _create_meeting(client, "lifecycle-session-idempotency-conflict")
    headers = auth_headers() | {"Idempotency-Key": "session-create-002"}
    first = client.post(
        f"/api/v1/meetings/{meeting['meeting_id']}/upload-sessions",
        headers=headers,
        json={"expected_track_sizes": {"system": 4}},
    )
    conflict = client.post(
        f"/api/v1/meetings/{meeting['meeting_id']}/upload-sessions",
        headers=headers,
        json={"expected_track_sizes": {"system": 5}},
    )

    assert first.status_code == 200
    assert conflict.status_code == 409
    assert conflict.json()["code"] == "idempotency_conflict"


def test_expired_session_rejects_upload_finalize_and_abort(client) -> None:
    meeting = _create_meeting(client, "lifecycle-expired")
    session = _create_upload_session(client, meeting["meeting_id"])

    async def expire_session() -> None:
        async with client.app_state["sessionmaker"]() as db:
            model = await db.get(UploadSession, UUID(session["session_id"]))
            assert model is not None
            model.expires_at = datetime.now(UTC) - timedelta(seconds=1)
            await db.commit()

    import asyncio

    asyncio.run(expire_session())
    store_module.store = InMemoryIngestStore()

    data = deterministic_wav_bytes(4)
    digest = sha256(data).hexdigest()
    upload = client.put(
        f"/api/v1/upload-sessions/{session['session_id']}/tracks/system/parts/0",
        headers=auth_headers() | {"X-Byte-Offset": "0", "X-Content-SHA256": digest},
        content=data,
    )
    finalize = client.post(
        f"/api/v1/upload-sessions/{session['session_id']}/finalize",
        headers=auth_headers(),
        json={
            "manifest_sha256": "a" * 64,
            "tracks": [
                track_descriptor("manifest", 8) | {"sha256": "a" * 64},
                track_descriptor("microphone", 9),
                track_descriptor("system", 10),
            ],
        },
    )
    abort = client.post(
        f"/api/v1/upload-sessions/{session['session_id']}/abort",
        headers=auth_headers(),
        json={"reason": "too late"},
    )

    assert upload.status_code == 409
    assert upload.json()["code"] == "session_expired"
    assert finalize.status_code == 409
    assert finalize.json()["code"] == "session_expired"
    assert abort.status_code == 409
    assert abort.json()["code"] == "session_expired"


def test_terminal_sessions_reject_additional_mutations_and_persist_finalized_at(client) -> None:
    meeting = _create_meeting(client, "lifecycle-terminal")
    session = _create_upload_session(client, meeting["meeting_id"])
    tracks = _upload_tracks(client, session["session_id"])

    finalized = _finalize(client, session["session_id"], tracks)
    assert finalized.status_code == 200

    data = deterministic_wav_bytes(4)
    digest = sha256(data).hexdigest()
    upload = client.put(
        f"/api/v1/upload-sessions/{session['session_id']}/tracks/system/parts/1",
        headers=auth_headers() | {"X-Byte-Offset": "10", "X-Content-SHA256": digest},
        content=data,
    )
    abort = client.post(
        f"/api/v1/upload-sessions/{session['session_id']}/abort",
        headers=auth_headers(),
        json={"reason": "late abort"},
    )
    replay_finalize = _finalize(client, session["session_id"], tracks)

    async def finalized_at():
        async with client.app_state["sessionmaker"]() as db:
            return await db.scalar(select(UploadSession.finalized_at).where(UploadSession.id == UUID(session["session_id"])))

    import asyncio

    assert upload.status_code == 409
    assert upload.json()["code"] == "session_terminal"
    assert abort.status_code == 409
    assert abort.json()["code"] == "session_terminal"
    assert replay_finalize.status_code == 409
    assert replay_finalize.json()["code"] == "session_terminal"
    assert asyncio.run(finalized_at()) is not None
