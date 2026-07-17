from datetime import UTC, datetime
from hashlib import sha256
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from tests.contract.test_ingest_openapi_contract import auth_headers
from tests.fakes.auth_contexts import DEVICE_ID, ORG_ID, USER_ID, WORKSPACE_ID
from tests.fixtures.artifacts import deterministic_wav_bytes, track_descriptor
from twobrain_rec_server.db.models import (
    Meeting,
    RegisteredDevice,
    UserIdentity,
    WorkspaceMembership,
)
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
        tracks.append(
            track_descriptor(role, len(data)) | {"sha256": digest, "byte_length": len(data)}
        )

    finalize = client.post(
        f"/api/v1/upload-sessions/{session_id}/finalize",
        headers=auth_headers(),
        json={"manifest_sha256": tracks[0]["sha256"], "tracks": tracks},
    )
    assert finalize.status_code == 200
    assert finalize.json()["meeting"]["status"] == "ingested_pending_processing"


def test_v5_mixed_recording_accepts_exact_single_wav_and_playback_package(client: TestClient) -> None:
    meeting_response = client.post(
        "/api/v1/meetings",
        headers=auth_headers(),
        json={
            "local_recording_id": "meeting-v5-mixed",
            "duration_seconds": 60,
            "source_kind": "initial_mixed_recording",
            "media_scribe_source_mode": "single_wav_v1",
        },
    )
    assert meeting_response.status_code == 200
    meeting = meeting_response.json()
    assert meeting["media_revision"]["source_kind"] == "initial_mixed_recording"

    session_response = client.post(
        f"/api/v1/meetings/{meeting['meeting_id']}/upload-sessions",
        headers=auth_headers(),
        json={"expected_tracks": ["manifest", "media", "playback"]},
    )
    assert session_response.status_code == 200
    session_id = session_response.json()["session_id"]

    tracks = []
    descriptor_values = {
        "manifest": ("json", 1, 1),
        "media": ("wav-pcm-s16le", 16_000, 1),
        "playback": ("m4a-aac-lc", 48_000, 1),
    }
    for index, role in enumerate(["manifest", "media", "playback"]):
        data = deterministic_wav_bytes(256 + index)
        digest = sha256(data).hexdigest()
        upload = client.put(
            f"/api/v1/upload-sessions/{session_id}/tracks/{role}/parts/0",
            headers=auth_headers() | {"X-Byte-Offset": "0", "X-Content-SHA256": digest},
            content=data,
        )
        assert upload.status_code == 200
        codec, sample_rate_hz, channel_count = descriptor_values[role]
        tracks.append(
            {
                "track_role": role,
                "codec": codec,
                "sample_rate_hz": sample_rate_hz,
                "channel_count": channel_count,
                "duration_seconds": 1 if role == "manifest" else 60,
                "byte_length": len(data),
                "sha256": digest,
            }
        )

    finalize = client.post(
        f"/api/v1/upload-sessions/{session_id}/finalize",
        headers=auth_headers(),
        json={"manifest_sha256": tracks[0]["sha256"], "tracks": tracks},
    )
    assert finalize.status_code == 200
    assert finalize.json()["meeting"]["status"] == "ingested_pending_processing"


def test_v5_mixed_recording_rejects_legacy_upload_roles(client: TestClient) -> None:
    meeting_response = client.post(
        "/api/v1/meetings",
        headers=auth_headers(),
        json={
            "local_recording_id": "meeting-v5-reject-legacy-roles",
            "duration_seconds": 60,
            "source_kind": "initial_mixed_recording",
            "media_scribe_source_mode": "single_wav_v1",
        },
    )
    assert meeting_response.status_code == 200

    session_response = client.post(
        f"/api/v1/meetings/{meeting_response.json()['meeting_id']}/upload-sessions",
        headers=auth_headers(),
        json={"expected_tracks": ["manifest", "microphone", "system"]},
    )

    assert session_response.status_code == 400
    assert session_response.json()["code"] == "invalid_expected_track_roles"


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
            return (
                model.title,
                model.started_at,
                model.ended_at,
                model.recording_display_timezone_offset_minutes,
            )

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


@pytest.mark.parametrize(
    ("title", "requested_source", "expected_source"),
    [
        ("Synthetic User Title", "user_confirmed", "user_confirmed"),
        ("Synthetic App Title", "app_context", "app_context"),
        ("Synthetic Generic Title", "generic", "generic"),
        ("Synthetic Unknown Title", "unknown", "legacy_unknown"),
        ("Synthetic Missing Source Title", None, "legacy_unknown"),
        (None, "user_confirmed", "generic"),
    ],
)
def test_us4_create_meeting_persists_normalized_title_provenance(
    client: TestClient,
    title: str | None,
    requested_source: str | None,
    expected_source: str,
) -> None:
    # FR-017/FR-018/FR-035: ingest persists provenance needed for title precedence.
    payload: dict[str, object] = {
        "local_recording_id": f"title-provenance-{expected_source}-{uuid4()}",
        "duration_seconds": 600,
    }
    if title is not None:
        payload["title"] = title
    if requested_source is not None:
        payload["title_source"] = requested_source

    response = client.post("/api/v1/meetings", headers=auth_headers(), json=payload)

    assert response.status_code == 200
    assert response.json()["title"] == title
    assert response.json()["title_source"] == expected_source
    meeting_id = UUID(response.json()["meeting_id"])

    async def load_title_truth() -> tuple[str | None, str]:
        async with client.app_state["sessionmaker"]() as db:
            meeting = await db.get(Meeting, meeting_id)
            assert meeting is not None
            return meeting.title, meeting.title_source

    assert client.portal.call(load_title_truth) == (title, expected_source)


def test_us4_create_retry_rejects_title_provenance_drift(client: TestClient) -> None:
    # FR-027/FR-035: identical text with changed provenance is not an idempotent retry.
    payload = {
        "local_recording_id": "title-provenance-retry-098",
        "duration_seconds": 600,
        "title": "Synthetic Stable Recording Title",
        "title_source": "app_context",
    }
    created = client.post("/api/v1/meetings", headers=auth_headers(), json=payload)
    exact_retry = client.post("/api/v1/meetings", headers=auth_headers(), json=payload)
    drifted = client.post(
        "/api/v1/meetings",
        headers=auth_headers(),
        json=payload | {"title_source": "user_confirmed"},
    )

    assert created.status_code == 200
    assert exact_retry.status_code == 200
    assert exact_retry.json()["meeting_id"] == created.json()["meeting_id"]
    assert drifted.status_code == 409
    assert drifted.json()["code"] == "idempotency_conflict"

    async def load_source() -> str:
        async with client.app_state["sessionmaker"]() as db:
            meeting = await db.get(Meeting, UUID(created.json()["meeting_id"]))
            assert meeting is not None
            return meeting.title_source

    assert client.portal.call(load_source) == "app_context"


def test_create_meeting_local_recording_id_is_scoped_to_current_user(client: TestClient) -> None:
    local_id = "user-scoped-local-recording-id"
    first = client.post(
        "/api/v1/meetings",
        headers=auth_headers(),
        json={"local_recording_id": local_id, "duration_seconds": 60, "title": "Owner recording"},
    )
    assert first.status_code == 200

    other_user_id = UUID("30000000-0000-0000-0000-000000000088")
    other_device_id = UUID("40000000-0000-0000-0000-000000000087")

    async def seed_other_user() -> None:
        async with client.app_state["sessionmaker"]() as db:
            db.add_all(
                [
                    UserIdentity(
                        id=other_user_id,
                        organization_id=ORG_ID,
                        external_subject=str(other_user_id),
                    ),
                    WorkspaceMembership(
                        workspace_id=WORKSPACE_ID,
                        user_id=other_user_id,
                        role="member",
                        status="active",
                    ),
                    RegisteredDevice(
                        id=other_device_id,
                        workspace_id=WORKSPACE_ID,
                        user_id=other_user_id,
                        device_public_id="other-user-local-recording-id",
                        status="active",
                    ),
                ]
            )
            await db.commit()

    client.portal.call(seed_other_user)
    other_headers = auth_headers() | {
        "X-User-Id": str(other_user_id),
        "X-Device-Id": str(other_device_id),
    }

    second = client.post(
        "/api/v1/meetings",
        headers=other_headers,
        json={"local_recording_id": local_id, "duration_seconds": 120, "title": "Other recording"},
    )

    assert second.status_code == 200
    assert second.json()["meeting_id"] != first.json()["meeting_id"]
    assert second.json()["title"] == "Other recording"


def test_create_meeting_unsafe_legacy_title_retry_returns_existing_meeting(
    client: TestClient,
) -> None:
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
                    title="meet.example.test/abc-defg-hij",
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
            "title": "meet.example.test/abc-defg-hij",
            "started_at": "2026-06-26T21:30:00Z",
            "duration_seconds": 60,
        },
    )

    assert response.status_code == 200
    assert response.json()["meeting_id"] == str(meeting_id)
