from __future__ import annotations

import asyncio
from hashlib import sha256
from uuid import UUID

from fastapi.testclient import TestClient
from sqlalchemy import func, select

from tests.contract.test_ingest_openapi_contract import auth_headers
from tests.fixtures.artifacts import deterministic_wav_bytes
from tests.fixtures.processing import mixed_recording_v5_contract_fixture
from tests.fixtures.recording_sync import revision_aware_recording_fixture
from twobrain_rec_server.db.models import MediaRevision, UploadSession


def test_v5_revision_persists_only_canonical_media_identity(client: TestClient) -> None:
    fixture = mixed_recording_v5_contract_fixture()
    meeting_response = client.post(
        "/api/v1/meetings",
        headers=auth_headers(),
        json={
            "local_recording_id": "identity-v5-mixed-001",
            "local_media_revision_id": "identity-v5-mixed-001--initial",
            "duration_seconds": 60,
            "source_kind": fixture["source_kind"],
            "media_scribe_source_mode": fixture["media_scribe_source_mode"],
        },
    )
    assert meeting_response.status_code == 200
    meeting = meeting_response.json()
    session_response = client.post(
        f"/api/v1/meetings/{meeting['meeting_id']}/upload-sessions",
        headers=auth_headers() | {"Idempotency-Key": "identity-v5-mixed-session"},
        json={"expected_tracks": fixture["expected_tracks"]},
    )
    assert session_response.status_code == 200
    session = session_response.json()

    descriptor_values = {
        "manifest": ("json", 1, 1),
        "media": ("wav-pcm-s16le", 16_000, 1),
        "playback": ("m4a-aac-lc", 48_000, 1),
    }
    tracks: list[dict[str, object]] = []
    for index, role in enumerate(fixture["expected_tracks"]):
        assert isinstance(role, str)
        data = deterministic_wav_bytes(256 + index)
        digest = sha256(data).hexdigest()
        upload = client.put(
            f"/api/v1/upload-sessions/{session['session_id']}/tracks/{role}/parts/0",
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
        f"/api/v1/upload-sessions/{session['session_id']}/finalize",
        headers=auth_headers(),
        json={"manifest_sha256": tracks[0]["sha256"], "tracks": tracks},
    )
    assert finalize.status_code == 200

    async def load_revision() -> MediaRevision:
        async with client.app_state["sessionmaker"]() as db:
            revision = await db.scalar(
                select(MediaRevision).where(
                    MediaRevision.local_media_revision_id == "identity-v5-mixed-001--initial"
                )
            )
            assert revision is not None
            return revision

    revision = asyncio.run(load_revision())
    assert revision.source_kind == "initial_mixed_recording"
    assert revision.immutable is True
    assert revision.track_sha256_by_role == {
        "manifest": tracks[0]["sha256"],
        "media": tracks[1]["sha256"],
    }
    assert "playback" not in revision.track_sha256_by_role


def test_meeting_create_reuses_one_initial_media_revision(client: TestClient) -> None:
    fixture = revision_aware_recording_fixture("identity-revision-001")
    payload = {
        "local_recording_id": fixture.local_recording_id,
        "local_media_revision_id": fixture.local_media_revision_id,
        "title": "Synthetic identity fixture",
        "duration_seconds": 60,
    }

    first = client.post("/api/v1/meetings", headers=auth_headers(), json=payload)
    second = client.post("/api/v1/meetings", headers=auth_headers(), json=payload)
    conflict = client.post(
        "/api/v1/meetings",
        headers=auth_headers(),
        json=payload | {"local_media_revision_id": "identity-revision-001--edited"},
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["meeting_id"] == second.json()["meeting_id"]
    assert first.json()["media_revision"]["media_revision_id"] == second.json()["media_revision"]["media_revision_id"]
    assert first.json()["local_media_revision_id"] == fixture.local_media_revision_id
    assert conflict.status_code == 409
    assert conflict.json()["code"] == "media_revision_conflict"

    async def count_revisions() -> int:
        async with client.app_state["sessionmaker"]() as db:
            return await db.scalar(
                select(func.count(MediaRevision.id)).where(
                    MediaRevision.local_media_revision_id == fixture.local_media_revision_id
                )
            )

    assert asyncio.run(count_revisions()) == 1


def test_upload_session_reuses_revision_identity_with_idempotency(client: TestClient) -> None:
    fixture = revision_aware_recording_fixture("identity-session-001")
    meeting_response = client.post(
        "/api/v1/meetings",
        headers=auth_headers(),
        json={
            "local_recording_id": fixture.local_recording_id,
            "local_media_revision_id": fixture.local_media_revision_id,
            "duration_seconds": 60,
        },
    )
    assert meeting_response.status_code == 200
    meeting = meeting_response.json()
    headers = auth_headers() | {"Idempotency-Key": "session-identity-key"}

    first = client.post(
        f"/api/v1/meetings/{meeting['meeting_id']}/upload-sessions",
        headers=headers,
        json={"expected_tracks": ["manifest", "microphone", "system"]},
    )
    second = client.post(
        f"/api/v1/meetings/{meeting['meeting_id']}/upload-sessions",
        headers=headers,
        json={"expected_tracks": ["manifest", "microphone", "system"]},
    )

    assert first.status_code == 200
    assert second.status_code == 200
    assert first.json()["session_id"] == second.json()["session_id"]
    assert first.json()["media_revision_id"] == meeting["media_revision"]["media_revision_id"]

    async def count_sessions() -> int:
        async with client.app_state["sessionmaker"]() as db:
            return await db.scalar(
                select(func.count(UploadSession.id)).where(
                    UploadSession.media_revision_id == UUID(meeting["media_revision"]["media_revision_id"])
                )
            )

    assert asyncio.run(count_sessions()) == 1


def test_finalize_persists_accepted_media_revision_fingerprint(client: TestClient) -> None:
    fixture = revision_aware_recording_fixture("identity-finalize-001")
    meeting_response = client.post(
        "/api/v1/meetings",
        headers=auth_headers(),
        json={
            "local_recording_id": fixture.local_recording_id,
            "local_media_revision_id": fixture.local_media_revision_id,
            "duration_seconds": 60,
        },
    )
    meeting = meeting_response.json()
    session_response = client.post(
        f"/api/v1/meetings/{meeting['meeting_id']}/upload-sessions",
        headers=auth_headers() | {"Idempotency-Key": "session-finalize-key"},
        json={"expected_tracks": ["manifest", "microphone", "system"]},
    )
    session = session_response.json()
    for track in fixture.expected_tracks:
        role = str(track["track_role"])
        data = deterministic_wav_bytes(int(track["byte_length"]))
        part_response = client.put(
            f"/api/v1/upload-sessions/{session['session_id']}/tracks/{role}/parts/0",
            headers=auth_headers() | {"X-Byte-Offset": "0", "X-Content-SHA256": str(track["sha256"])},
            content=data,
        )
        assert part_response.status_code == 200

    finalize_response = client.post(
        f"/api/v1/upload-sessions/{session['session_id']}/finalize",
        headers=auth_headers(),
        json={"manifest_sha256": fixture.manifest_sha256, "tracks": fixture.expected_tracks},
    )

    assert finalize_response.status_code == 200

    async def load_revision() -> MediaRevision:
        async with client.app_state["sessionmaker"]() as db:
            revision = await db.scalar(
                select(MediaRevision).where(MediaRevision.local_media_revision_id == fixture.local_media_revision_id)
            )
            assert revision is not None
            return revision

    revision = asyncio.run(load_revision())
    assert revision.status == "accepted"
    assert revision.immutable is True
    assert revision.accepted_at is not None
    assert revision.manifest_sha256 == fixture.manifest_sha256
    assert revision.track_sha256_by_role == fixture.track_sha256_by_role
