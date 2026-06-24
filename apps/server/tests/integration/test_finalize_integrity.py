from hashlib import sha256
from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy import select

from tests.contract.test_ingest_openapi_contract import auth_headers
from tests.fixtures.artifacts import deterministic_wav_bytes, track_descriptor
from twobrain_rec_server.db.models import IngestAuditEvent, Meeting, UploadSession


def _create_session_with_parts(
    client: TestClient,
    expected_track_sizes: dict[str, int] | None = None,
    meeting_id: str | None = None,
    sizes: tuple[int, int, int] = (8, 9, 10),
) -> tuple[str, list[dict[str, object]]]:
    if meeting_id is None:
        meeting = client.post(
            "/api/v1/meetings",
            headers=auth_headers(),
            json={"local_recording_id": "finalize-integrity", "duration_seconds": 60},
        ).json()
        meeting_id = meeting["meeting_id"]
    session = client.post(
        f"/api/v1/meetings/{meeting_id}/upload-sessions",
        headers=auth_headers(),
        json={
            "expected_track_sizes": expected_track_sizes
            or {"manifest": sizes[0], "microphone": sizes[1], "system": sizes[2]}
        },
    ).json()

    tracks = []
    for size, role in zip(sizes, ["manifest", "microphone", "system"], strict=True):
        data = deterministic_wav_bytes(size)
        digest = sha256(data).hexdigest()
        response = client.put(
            f"/api/v1/upload-sessions/{session['session_id']}/tracks/{role}/parts/0",
            headers=auth_headers() | {"X-Byte-Offset": "0", "X-Content-SHA256": digest},
            content=data,
        )
        assert response.status_code == 200
        tracks.append(track_descriptor(role, size) | {"sha256": digest, "byte_length": size})
    return session["session_id"], tracks


def _finalize(client: TestClient, session_id: str, tracks: list[dict[str, object]], manifest_sha256: str):
    return client.post(
        f"/api/v1/upload-sessions/{session_id}/finalize",
        headers=auth_headers(),
        json={"manifest_sha256": manifest_sha256, "tracks": tracks},
    )


def test_finalize_rejects_mismatched_manifest_sha(client: TestClient) -> None:
    session_id, tracks = _create_session_with_parts(client)

    response = _finalize(client, session_id, tracks, sha256(b"wrong-manifest").hexdigest())

    assert response.status_code == 400
    assert response.json()["code"] == "manifest_checksum_mismatch"


def test_finalize_validation_failure_persists_degraded_state_and_audit(client: TestClient) -> None:
    session_id, tracks = _create_session_with_parts(client)

    response = _finalize(client, session_id, tracks, sha256(b"wrong-manifest").hexdigest())

    assert response.status_code == 400

    async def persisted_state():
        async with client.app_state["sessionmaker"]() as db:
            session = await db.get(UploadSession, UUID(session_id))
            meeting = await db.get(Meeting, session.meeting_id)
            audit = await db.scalar(
                select(IngestAuditEvent)
                .where(
                    IngestAuditEvent.upload_session_id == session.id,
                    IngestAuditEvent.event_type == "finalize_degraded",
                )
                .order_by(IngestAuditEvent.created_at.desc())
            )
            return meeting, session, audit

    import asyncio

    meeting, session, audit = asyncio.run(persisted_state())
    assert meeting.status == "degraded"
    assert session.status == "degraded"
    assert audit is not None
    assert audit.meeting_id == meeting.id
    assert audit.workspace_id == meeting.workspace_id
    assert audit.actor_user_id is not None
    assert audit.device_id is not None
    assert audit.metadata_json == {
        "reason_code": "manifest_checksum_mismatch",
        "reason": "Manifest checksum mismatch",
    }


def test_finalize_rejects_mismatched_track_sha(client: TestClient) -> None:
    session_id, tracks = _create_session_with_parts(client)
    tracks[1] = tracks[1] | {"sha256": sha256(b"wrong-microphone").hexdigest()}

    response = _finalize(client, session_id, tracks, str(tracks[0]["sha256"]))

    assert response.status_code == 400
    assert response.json()["code"] == "track_checksum_mismatch"


def test_finalize_rejects_mismatched_track_byte_length(client: TestClient) -> None:
    session_id, tracks = _create_session_with_parts(client, {"manifest": 8, "microphone": 9, "system": 11})
    tracks[2] = tracks[2] | {"byte_length": 11}

    response = _finalize(client, session_id, tracks, str(tracks[0]["sha256"]))

    assert response.status_code == 400
    assert response.json()["code"] == "track_length_mismatch"


def test_finalize_rejects_role_object_mapping_mismatch(client: TestClient) -> None:
    session_id, tracks = _create_session_with_parts(client)
    microphone = next(track for track in tracks if track["track_role"] == "microphone")
    system = next(track for track in tracks if track["track_role"] == "system")
    tracks = [
        track
        if track["track_role"] == "manifest"
        else track | {"sha256": system["sha256"]}
        if track["track_role"] == "microphone"
        else track | {"sha256": microphone["sha256"]}
        for track in tracks
    ]

    response = _finalize(client, session_id, tracks, str(tracks[0]["sha256"]))

    assert response.status_code == 400
    assert response.json()["code"] == "track_checksum_mismatch"


def test_finalize_rejects_expected_track_size_mismatch(client: TestClient) -> None:
    session_id, tracks = _create_session_with_parts(client, {"manifest": 8, "microphone": 99, "system": 10})

    response = _finalize(client, session_id, tracks, str(tracks[0]["sha256"]))

    assert response.status_code == 409
    assert response.json()["code"] == "expected_track_size_mismatch"


def test_finalize_rejects_immutable_media_revision_fingerprint_change(client: TestClient) -> None:
    meeting = client.post(
        "/api/v1/meetings",
        headers=auth_headers(),
        json={"local_recording_id": "finalize-fingerprint-conflict", "duration_seconds": 60},
    ).json()
    first_session_id, first_tracks = _create_session_with_parts(client, meeting_id=meeting["meeting_id"])
    first_finalize = _finalize(client, first_session_id, first_tracks, str(first_tracks[0]["sha256"]))
    assert first_finalize.status_code == 200

    second_session_id, second_tracks = _create_session_with_parts(
        client,
        meeting_id=meeting["meeting_id"],
        sizes=(8, 11, 12),
    )
    response = _finalize(client, second_session_id, second_tracks, str(second_tracks[0]["sha256"]))

    assert response.status_code == 409
    assert response.json()["code"] == "media_revision_fingerprint_conflict"
