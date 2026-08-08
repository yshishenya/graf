from hashlib import sha256

from fastapi.testclient import TestClient
from sqlalchemy.ext.asyncio import AsyncSession

from tests.contract.test_ingest_openapi_contract import auth_headers
from tests.fixtures.artifacts import deterministic_wav_bytes, track_descriptor
from twobrain_rec_server.auth.context import TenantScope
from twobrain_rec_server.db.models import PlaybackNormalizationJob
from twobrain_rec_server.db.tenant_context import apply_tenant_scope


async def apply_job_worker_scope(db: AsyncSession, job: PlaybackNormalizationJob) -> None:
    """Apply the exact production worker authority before a direct job execution."""

    await apply_tenant_scope(
        db,
        TenantScope(
            organization_id=job.organization_id,
            workspace_id=job.workspace_id,
            user_id=job.requested_by_user_id,
            device_id=job.source_device_id,
        ),
        context_kind="worker",
    )


def enable_processing_autostart(client: TestClient, temporal_client: object | None = None) -> object | None:
    client.app.state.settings.processing_enabled = True
    if temporal_client is not None:
        client.app.state.temporal_client = temporal_client
    return temporal_client


def mixed_recording_v5_contract_fixture() -> dict[str, object]:
    """Metadata-only v5 package shape for contract tests.

    This intentionally carries no audio bytes, transcript text, local paths or
    provider credentials. Tests which need payload bytes build them locally from
    the existing deterministic helper instead.
    """

    return {
        "schema_version": "local-recording-manifest.v5",
        "media_scribe_source_mode": "single_wav_v1",
        "source_kind": "initial_mixed_recording",
        "expected_tracks": ["manifest", "media", "playback"],
        "descriptors": {
            "media": {
                "track_role": "media",
                "codec": "wav-pcm-s16le",
                "sample_rate_hz": 16_000,
                "channel_count": 1,
            },
            "playback": {
                "track_role": "playback",
                "codec": "m4a-aac-lc",
                "sample_rate_hz": 48_000,
                "channel_count": 1,
            },
        },
    }


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


def create_finalized_mixed_recording(
    client: TestClient,
    local_recording_id: str = "processing-ready-v5",
    *,
    media_bytes: bytes | None = None,
    playback_bytes: bytes | None = None,
) -> dict[str, object]:
    """Create an accepted metadata-only v5 package for processing tests.

    The generated WAV contains only zero PCM frames; it is an ephemeral test
    signal and never a checked-in audio fixture. Playback is a review-only
    candidate: it is never an ASR input and tests may replace its bytes to
    exercise the playback-normalization boundary.
    """

    meeting_response = client.post(
        "/api/v1/meetings",
        headers=auth_headers(),
        json={
            "local_recording_id": local_recording_id,
            "duration_seconds": 1,
            "source_kind": "initial_mixed_recording",
            "media_scribe_source_mode": "single_wav_v1",
        },
    )
    assert meeting_response.status_code == 200
    meeting = meeting_response.json()
    session_response = client.post(
        f"/api/v1/meetings/{meeting['meeting_id']}/upload-sessions",
        headers=auth_headers(),
        json={"expected_tracks": ["manifest", "media", "playback"]},
    )
    assert session_response.status_code == 200
    session = session_response.json()

    artifacts = {
        "manifest": b"{}",
        "media": media_bytes if media_bytes is not None else deterministic_canonical_wav_bytes(),
        "playback": playback_bytes
        if playback_bytes is not None
        else b"synthetic-playback-metadata-only",
    }
    descriptors = {
        "manifest": ("json", 1, 1),
        "media": ("wav-pcm-s16le", 16_000, 1),
        "playback": ("m4a-aac-lc", 48_000, 1),
    }
    tracks: list[dict[str, object]] = []
    for role in ["manifest", "media", "playback"]:
        data = artifacts[role]
        digest = sha256(data).hexdigest()
        upload = client.put(
            f"/api/v1/upload-sessions/{session['session_id']}/tracks/{role}/parts/0",
            headers=auth_headers() | {"X-Byte-Offset": "0", "X-Content-SHA256": digest},
            content=data,
        )
        assert upload.status_code == 200
        codec, sample_rate_hz, channel_count = descriptors[role]
        tracks.append(
            {
                "track_role": role,
                "codec": codec,
                "sample_rate_hz": sample_rate_hz,
                "channel_count": channel_count,
                "duration_seconds": 1,
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
    finalized = finalize.json()
    return {"finalize": finalized, "meeting": finalized["meeting"], "session": session, "tracks": tracks}


def deterministic_canonical_wav_bytes(frame_count: int = 160) -> bytes:
    """Return a small valid PCM s16le mono/16 kHz WAV without speech data."""

    payload = b"\x00\x00" * frame_count
    fmt_chunk = (
        (1).to_bytes(2, "little")
        + (1).to_bytes(2, "little")
        + (16_000).to_bytes(4, "little")
        + (32_000).to_bytes(4, "little")
        + (2).to_bytes(2, "little")
        + (16).to_bytes(2, "little")
    )
    return (
        b"RIFF"
        + (36 + len(payload)).to_bytes(4, "little")
        + b"WAVEfmt "
        + len(fmt_chunk).to_bytes(4, "little")
        + fmt_chunk
        + b"data"
        + len(payload).to_bytes(4, "little")
        + payload
    )
