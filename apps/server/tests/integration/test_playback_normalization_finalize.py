from __future__ import annotations

import asyncio
from hashlib import sha256
from pathlib import Path
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from tests.contract.test_ingest_openapi_contract import auth_headers
from tests.fakes.auth_contexts import DEVICE_ID, ORG_ID, USER_ID, WORKSPACE_ID
from tests.fixtures.artifacts import track_descriptor
from tests.fixtures.processing import (
    apply_job_worker_scope,
    create_finalized_mixed_recording,
    deterministic_canonical_wav_bytes,
)
from tests.integration.test_playback_normalization_media_matrix import _pipeline, _run_ffmpeg
from twobrain_rec_server.auth.context import TenantScope
from twobrain_rec_server.db.models import (
    MediaRevision,
    PlaybackNormalizationJob,
    TrackArtifact,
)
from twobrain_rec_server.db.tenant_context import apply_tenant_scope
from twobrain_rec_server.normalization.service import (
    NormalizationExecutionFailure,
    run_normalization_job,
    upsert_playback_normalization_job,
)
from twobrain_rec_server.normalization.statuses import CANONICAL_PROFILE_VERSION


class NeverCalledNormalizationPipeline:
    async def derive_candidate(self, _source_path: Path, _output_path: Path):
        raise AssertionError("source custody must fail before conversion")

    async def derive_dual_source(
        self,
        _microphone_path: Path,
        _system_path: Path,
        _output_path: Path,
    ):
        raise AssertionError("source custody must fail before conversion")

    async def derive_single_source(self, _source_path: Path, _output_path: Path):
        raise AssertionError("source custody must fail before conversion")


def _generate_canonical_playback_candidate(path: Path) -> None:
    """Generate an ephemeral canonical review M4A; no audio fixture is stored."""

    _run_ffmpeg(
        [
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=440:duration=1",
            "-map",
            "0:a:0",
            "-vn",
            "-sn",
            "-dn",
            "-map_metadata",
            "-1",
            "-map_chapters",
            "-1",
            "-ar",
            "48000",
            "-ac",
            "1",
            "-c:a",
            "aac",
            "-profile:a",
            "aac_low",
            "-b:a",
            "64k",
            "-fflags",
            "+bitexact",
            "-flags:a",
            "+bitexact",
            "-movflags",
            "+faststart",
            "-f",
            "ipod",
            str(path),
        ]
    )


def _accept_first_party_recording(
    client: TestClient,
    *,
    local_recording_id: str,
    include_playback: bool,
) -> tuple[dict[str, object], dict[str, object]]:
    meeting = client.post(
        "/api/v1/meetings",
        headers=auth_headers(),
        json={"local_recording_id": local_recording_id, "duration_seconds": 60},
    ).json()
    payloads = {
        "manifest": b'{"schema":"test"}',
        "microphone": b"microphone-source",
        "system": b"system-source",
    }
    if include_playback:
        payloads["playback"] = b"untrusted-playback-candidate"
    expected_tracks = list(payloads)
    session_response = client.post(
        f"/api/v1/meetings/{meeting['meeting_id']}/upload-sessions",
        headers=auth_headers(),
        json={
            "expected_tracks": expected_tracks,
            "expected_track_sizes": {role: len(data) for role, data in payloads.items()},
        },
    )
    assert session_response.status_code == 200
    session = session_response.json()

    tracks: list[dict[str, object]] = []
    for role, data in payloads.items():
        digest = sha256(data).hexdigest()
        response = client.put(
            f"/api/v1/upload-sessions/{session['session_id']}/tracks/{role}/parts/0",
            headers=auth_headers()
            | {"X-Byte-Offset": "0", "X-Content-SHA256": digest},
            content=data,
        )
        assert response.status_code == 200
        tracks.append(
            track_descriptor(role, len(data))
            | {
                "byte_length": len(data),
                "sha256": digest,
                "codec": "m4a-aac-lc" if role == "playback" else "pcm_s16le",
            }
        )

    response = client.post(
        f"/api/v1/upload-sessions/{session['session_id']}/finalize",
        headers=auth_headers(),
        json={"manifest_sha256": sha256(payloads["manifest"]).hexdigest(), "tracks": tracks},
    )
    return meeting, response.json() | {"status_code": response.status_code}


def test_finalize_persists_optional_playback_as_hidden_candidate_and_queues_validation(
    client: TestClient,
) -> None:
    meeting, result = _accept_first_party_recording(
        client,
        local_recording_id="normalization-candidate-finalize",
        include_playback=True,
    )

    assert result["status_code"] == 200

    async def load_truth():
        async with client.app_state["sessionmaker"]() as db:
            revision = await db.get(MediaRevision, UUID(str(meeting["media_revision"]["media_revision_id"])))
            artifacts = (
                await db.scalars(
                    select(TrackArtifact).where(
                        TrackArtifact.meeting_id == UUID(str(meeting["meeting_id"]))
                    )
                )
            ).all()
            job = await db.scalar(
                select(PlaybackNormalizationJob).where(
                    PlaybackNormalizationJob.media_revision_id == revision.id,
                    PlaybackNormalizationJob.profile_version == CANONICAL_PROFILE_VERSION,
                )
            )
            return revision, artifacts, job

    revision, artifacts, job = asyncio.run(load_truth())
    playback = next(artifact for artifact in artifacts if artifact.track_role == "playback")
    assert playback.status == "candidate"
    assert playback.validated_at is None
    assert playback.normalization_profile_version is None
    assert playback.sha256 == sha256(b"untrusted-playback-candidate").hexdigest()
    assert "playback" not in revision.track_sha256_by_role
    assert job is not None
    assert job.state == "queued"
    assert job.trigger_kind == "finalize"
    assert job.priority_class == "new_ingest"
    assert job.planned_action == "validate_candidate"
    assert job.workflow_id == f"playback-normalization/{revision.id}/v1"


def test_finalize_without_candidate_queues_authoritative_source_normalization(
    client: TestClient,
) -> None:
    meeting, result = _accept_first_party_recording(
        client,
        local_recording_id="normalization-source-finalize",
        include_playback=False,
    )

    assert result["status_code"] == 200

    async def load_job() -> PlaybackNormalizationJob | None:
        async with client.app_state["sessionmaker"]() as db:
            return await db.scalar(
                select(PlaybackNormalizationJob).where(
                    PlaybackNormalizationJob.meeting_id == UUID(str(meeting["meeting_id"]))
                )
            )

    job = asyncio.run(load_job())
    assert job is not None
    assert job.planned_action == "normalize_source"


def test_v5_canonical_review_candidate_is_reused_without_touching_asr_wav(
    client: TestClient,
    tmp_path: Path,
) -> None:
    review_candidate = tmp_path / "review-candidate.m4a"
    _generate_canonical_playback_candidate(review_candidate)
    finalized = create_finalized_mixed_recording(
        client,
        "normalization-v5-candidate-reuse",
        media_bytes=deterministic_canonical_wav_bytes(frame_count=16_000),
        playback_bytes=review_candidate.read_bytes(),
    )
    meeting_id = UUID(str(finalized["meeting"]["meeting_id"]))
    expected_media_digest = next(
        track["sha256"] for track in finalized["tracks"] if track["track_role"] == "media"
    )

    async def execute():
        async with client.app_state["sessionmaker"]() as db:
            job = await db.scalar(
                select(PlaybackNormalizationJob).where(
                    PlaybackNormalizationJob.meeting_id == meeting_id
                )
            )
            assert job is not None
            await apply_job_worker_scope(db, job)
            result = await run_normalization_job(
                db=db,
                storage=client.app_state["storage"],
                job_id=job.id,
                work_directory=tmp_path,
                pipeline=_pipeline(),
            )
            refreshed_job = await db.get(PlaybackNormalizationJob, job.id)
            artifacts = list(
                await db.scalars(
                    select(TrackArtifact).where(TrackArtifact.meeting_id == meeting_id)
                )
            )
            canonical = await db.get(TrackArtifact, result.canonical_track_artifact_id)
            return result, refreshed_job, artifacts, canonical

    result, job, artifacts, canonical = asyncio.run(execute())

    assert result.reused is False
    assert result.derivation_kind == "uploaded_candidate"
    assert job is not None and job.state == "ready"
    assert canonical is not None
    assert canonical.status == "stored"
    assert canonical.derivation_kind == "uploaded_candidate"
    assert canonical.source_fingerprint_sha256 == job.source_fingerprint_sha256
    assert next(artifact for artifact in artifacts if artifact.track_role == "media").sha256 == expected_media_digest
    assert {artifact.track_role for artifact in artifacts}.isdisjoint({"microphone", "system"})


def test_v5_invalid_review_candidate_falls_back_to_authoritative_wav(
    client: TestClient,
    tmp_path: Path,
) -> None:
    finalized = create_finalized_mixed_recording(
        client,
        "normalization-v5-candidate-fallback",
        media_bytes=deterministic_canonical_wav_bytes(frame_count=16_000),
    )
    meeting_id = UUID(str(finalized["meeting"]["meeting_id"]))
    expected_media_digest = next(
        track["sha256"] for track in finalized["tracks"] if track["track_role"] == "media"
    )

    async def execute():
        async with client.app_state["sessionmaker"]() as db:
            job = await db.scalar(
                select(PlaybackNormalizationJob).where(
                    PlaybackNormalizationJob.meeting_id == meeting_id
                )
            )
            assert job is not None
            await apply_job_worker_scope(db, job)
            result = await run_normalization_job(
                db=db,
                storage=client.app_state["storage"],
                job_id=job.id,
                work_directory=tmp_path,
                pipeline=_pipeline(),
            )
            refreshed_job = await db.get(PlaybackNormalizationJob, job.id)
            artifacts = list(
                await db.scalars(
                    select(TrackArtifact).where(TrackArtifact.meeting_id == meeting_id)
                )
            )
            canonical = await db.get(TrackArtifact, result.canonical_track_artifact_id)
            return result, refreshed_job, artifacts, canonical

    result, job, artifacts, canonical = asyncio.run(execute())

    assert result.reused is False
    assert result.derivation_kind == "single_source_transcode"
    assert job is not None and job.state == "ready"
    assert canonical is not None
    assert canonical.status == "stored"
    assert canonical.derivation_kind == "single_source_transcode"
    assert canonical.source_fingerprint_sha256 == job.source_fingerprint_sha256
    assert next(artifact for artifact in artifacts if artifact.track_role == "media").sha256 == expected_media_digest
    assert {artifact.track_role for artifact in artifacts}.isdisjoint({"microphone", "system"})


def test_candidate_digest_does_not_change_authoritative_source_fingerprint() -> None:
    from twobrain_rec_server.ingest.media_revisions import source_fingerprint_sha256

    revision_id = UUID("11111111-1111-4111-8111-111111111111")
    common = {
        "manifest": "a" * 64,
        "microphone": "b" * 64,
        "system": "c" * 64,
    }

    without_candidate = source_fingerprint_sha256(
        media_revision_id=revision_id,
        source_kind="initial_recording",
        manifest_sha256="a" * 64,
        track_sha256_by_role=common,
        duration_seconds=60,
    )
    with_candidate = source_fingerprint_sha256(
        media_revision_id=revision_id,
        source_kind="initial_recording",
        manifest_sha256="a" * 64,
        track_sha256_by_role=common | {"playback": "d" * 64},
        duration_seconds=60,
    )

    assert with_candidate == without_candidate


def test_unfinalized_and_unmanaged_sources_cannot_create_normalization_jobs(
    client: TestClient,
) -> None:
    meeting = client.post(
        "/api/v1/meetings",
        headers=auth_headers(),
        json={"local_recording_id": "normalization-unfinalized", "duration_seconds": 60},
    ).json()
    meeting_id = UUID(str(meeting["meeting_id"]))
    revision_id = UUID(str(meeting["media_revision"]["media_revision_id"]))
    session = client.post(
        f"/api/v1/meetings/{meeting_id}/upload-sessions",
        headers=auth_headers(),
        json={"expected_tracks": ["manifest", "microphone", "system"]},
    ).json()
    raw_part = b"raw-in-flight-microphone"
    response = client.put(
        f"/api/v1/upload-sessions/{session['session_id']}/tracks/microphone/parts/0",
        headers=auth_headers()
        | {
            "X-Byte-Offset": "0",
            "X-Content-SHA256": sha256(raw_part).hexdigest(),
        },
        content=raw_part,
    )
    assert response.status_code == 200

    async def assert_no_job() -> None:
        async with client.app_state["sessionmaker"]() as db:
            revision = await db.get(MediaRevision, revision_id)
            jobs = list(
                await db.scalars(
                    select(PlaybackNormalizationJob).where(
                        PlaybackNormalizationJob.meeting_id == meeting_id
                    )
                )
            )
            assert revision is not None
            assert revision.status == "pending_upload"
            assert jobs == []
            await apply_tenant_scope(
                db,
                TenantScope(
                    organization_id=ORG_ID,
                    workspace_id=WORKSPACE_ID,
                    user_id=USER_ID,
                    device_id=DEVICE_ID,
                ),
            )
            with pytest.raises(ValueError, match="accepted media revision"):
                await upsert_playback_normalization_job(
                    db,
                    workspace_id=revision.workspace_id,
                    meeting_id=meeting_id,
                    media_revision_id=revision_id,
                )
            with pytest.raises(ValueError, match="accepted media revision"):
                await upsert_playback_normalization_job(
                    db,
                    workspace_id=revision.workspace_id,
                    meeting_id=meeting_id,
                    media_revision_id=UUID("99999999-9999-4999-8999-999999999999"),
                )

    asyncio.run(assert_no_job())


def test_authoritative_source_digest_mismatch_stops_before_conversion(
    client: TestClient,
    tmp_path: Path,
) -> None:
    meeting, result = _accept_first_party_recording(
        client,
        local_recording_id="normalization-source-mismatch",
        include_playback=False,
    )
    assert result["status_code"] == 200
    meeting_id = UUID(str(meeting["meeting_id"]))
    source_keys = set(client.app_state["storage"].objects)

    async def execute_mismatch():
        async with client.app_state["sessionmaker"]() as db:
            job = await db.scalar(
                select(PlaybackNormalizationJob).where(
                    PlaybackNormalizationJob.meeting_id == meeting_id
                )
            )
            microphone = await db.scalar(
                select(TrackArtifact).where(
                    TrackArtifact.meeting_id == meeting_id,
                    TrackArtifact.track_role == "microphone",
                )
            )
            assert job is not None and microphone is not None
            microphone.sha256 = "f" * 64
            await db.commit()
            await apply_job_worker_scope(db, job)
            with pytest.raises(NormalizationExecutionFailure) as caught:
                await run_normalization_job(
                    db=db,
                    storage=client.app_state["storage"],
                    job_id=job.id,
                    work_directory=tmp_path,
                    pipeline=NeverCalledNormalizationPipeline(),
                )
            refreshed = await db.get(PlaybackNormalizationJob, job.id)
            canonical = list(
                await db.scalars(
                    select(TrackArtifact).where(
                        TrackArtifact.meeting_id == meeting_id,
                        TrackArtifact.track_role == "playback",
                        TrackArtifact.status == "stored",
                    )
                )
            )
            return caught.value, refreshed, canonical

    failure, job, canonical = asyncio.run(execute_mismatch())
    assert failure.reason_code.value == "source_mismatch"
    assert failure.should_retry is False
    assert job.state == "terminal"
    assert job.reason_code == "source_mismatch"
    assert canonical == []
    assert set(client.app_state["storage"].objects) == source_keys
