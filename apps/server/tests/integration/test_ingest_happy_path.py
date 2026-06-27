from datetime import UTC, datetime
from hashlib import sha256
from uuid import UUID, uuid4

from fastapi.testclient import TestClient
from sqlalchemy import select

from tests.contract.test_ingest_openapi_contract import auth_headers
from tests.fakes.auth_contexts import DEVICE_ID, USER_ID, WORKSPACE_ID
from tests.fixtures.artifacts import deterministic_wav_bytes, track_descriptor
from twobrain_rec_server.db.models import Meeting
from twobrain_rec_server.domain.statuses import MeetingStatus, ProcessingStatus


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
            "recording_display_timezone_offset_minutes": 180,
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
            return model.title, model.started_at, model.ended_at, model.recording_display_timezone_offset_minutes

    title, started_at, ended_at, offset_minutes = client.portal.call(persisted_metadata)
    assert title == "Zoom - 2026-06-26 11:30"
    assert started_at is not None
    assert ended_at is not None
    assert offset_minutes == 180
    assert started_at.isoformat().startswith("2026-06-26T11:30:00")
    assert ended_at.isoformat().startswith("2026-06-26T12:15:00")


def test_create_meeting_duplicate_rejects_mutated_recording_metadata(client: TestClient) -> None:
    payload = {
        "local_recording_id": "meeting-metadata-idempotency-059",
        "title": "Zoom - 2026-06-26 11:30",
        "started_at": "2026-06-26T11:30:00Z",
        "ended_at": "2026-06-26T12:15:00Z",
        "recording_display_timezone_offset_minutes": 180,
        "duration_seconds": 2700,
    }
    response = client.post("/api/v1/meetings", headers=auth_headers(), json=payload)
    assert response.status_code == 200

    exact_retry = client.post("/api/v1/meetings", headers=auth_headers(), json=payload)
    assert exact_retry.status_code == 200
    assert exact_retry.json()["meeting_id"] == response.json()["meeting_id"]

    for mutation in [
        {"started_at": "2026-06-26T11:31:00Z"},
        {"ended_at": "2026-06-26T12:16:00Z"},
        {"recording_display_timezone_offset_minutes": 120},
    ]:
        conflict = client.post("/api/v1/meetings", headers=auth_headers(), json=payload | mutation)
        assert conflict.status_code == 409
        assert conflict.json()["code"] == "idempotency_conflict"


def test_create_meeting_unsafe_legacy_title_retry_returns_existing_meeting(client: TestClient) -> None:
    meeting_id = uuid4()

    async def seed_legacy_meeting() -> None:
        async with client.app_state["sessionmaker"]() as db:
            db.add(
                Meeting(
                    id=meeting_id,
                    workspace_id=WORKSPACE_ID,
                    created_by_user_id=USER_ID,
                    device_id=DEVICE_ID,
                    local_recording_id="legacy-unsafe-title-retry",
                    title="meet.google.com/abc-defg-hij",
                    started_at=datetime(2026, 6, 26, 21, 30, tzinfo=UTC),
                    duration_seconds=60,
                    status=MeetingStatus.DRAFT.value,
                    processing_status=ProcessingStatus.NOT_SUBMITTED.value,
                )
            )
            await db.commit()

    client.portal.call(seed_legacy_meeting)

    response = client.post(
        "/api/v1/meetings",
        headers=auth_headers(),
        json={
            "local_recording_id": "legacy-unsafe-title-retry",
            "title": "meet.google.com/abc-defg-hij",
            "started_at": "2026-06-26T21:30:00Z",
            "duration_seconds": 60,
        },
    )

    assert response.status_code == 200
    assert response.json()["meeting_id"] == str(meeting_id)
