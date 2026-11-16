from __future__ import annotations

import asyncio
import json
import shutil
from hashlib import sha256
from pathlib import Path
from uuid import UUID, uuid4

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from tests.contract.test_ingest_openapi_contract import auth_headers
from tests.fakes.fake_temporal import FakeTemporalClient
from tests.fixtures.artifacts import deterministic_wav_bytes
from tests.fixtures.playback_normalization import synthetic_pcm_wav_bytes
from tests.fixtures.processing import apply_job_worker_scope, deterministic_canonical_wav_bytes
from tests.integration.test_playback_normalization_finalize import (
    _accept_first_party_recording,
)
from twobrain_rec_server.db.models import (
    Meeting,
    PlaybackNormalizationAttempt,
    PlaybackNormalizationJob,
    PurgeJournal,
    RecordingCalendarContextLink,
    TrackArtifact,
)
from twobrain_rec_server.normalization.service import (
    CandidateRejected,
    FFmpegNormalizationPipeline,
    NormalizationExecutionDeferred,
    NormalizationExecutionFailure,
    NormalizedOutput,
    run_normalization_job,
)
from twobrain_rec_server.storage.recovery import read_with_storage_fence
from twobrain_rec_server.storage.strict_upload_keys import STRICT_UPLOAD_ATTEMPT


class FakeNormalizationPipeline:
    def __init__(self, candidate_mode: str) -> None:
        self.candidate_mode = candidate_mode
        self.calls: list[str] = []

    async def derive_candidate(self, source_path: Path, output_path: Path) -> NormalizedOutput:
        self.calls.append("candidate")
        assert source_path.read_bytes() == b"untrusted-playback-candidate"
        if self.candidate_mode == "invalid":
            raise CandidateRejected()
        body = (
            b"canonical-candidate-copy"
            if self.candidate_mode == "copy"
            else b"canonical-candidate-remux"
        )
        output_path.write_bytes(body)
        return _normalized_output(
            body,
            derivation_kind=(
                "uploaded_candidate"
                if self.candidate_mode == "copy"
                else "lossless_faststart_remux"
            ),
            source_count=1,
        )

    async def derive_single_source(
        self,
        source_path: Path,
        output_path: Path,
        *,
        tolerant_first: bool = False,
        expected_duration_seconds: int | None = None,
    ) -> NormalizedOutput:
        self.calls.append("single_source")
        assert source_path.read_bytes() == deterministic_canonical_wav_bytes()
        body = b"canonical-single-source-transcode"
        output_path.write_bytes(body)
        return _normalized_output(
            body,
            derivation_kind="single_source_transcode",
            source_count=1,
        )


class FakeManualNormalizationPipeline:
    def __init__(self) -> None:
        self.source_body: bytes | None = None

    async def derive_single_source(
        self,
        source_path: Path,
        output_path: Path,
        *,
        tolerant_first: bool = False,
        expected_duration_seconds: int | None = None,
    ) -> NormalizedOutput:
        assert tolerant_first is True
        assert expected_duration_seconds is not None
        self.source_body = source_path.read_bytes()
        body = b"canonical-manual-source"
        output_path.write_bytes(body)
        return _normalized_output(
            body,
            derivation_kind="single_source_transcode",
            source_count=1,
        )


def _normalized_output(
    body: bytes,
    *,
    derivation_kind: str,
    source_count: int,
    selected_stream_index: int | None = 0,
) -> NormalizedOutput:
    return NormalizedOutput(
        derivation_kind=derivation_kind,
        selected_stream_index=selected_stream_index,
        source_stream_count=source_count,
        source_audio_stream_count=source_count,
        source_duration_ms=60_000,
        output_duration_ms=60_000,
        output_byte_length=len(body),
        output_sha256=sha256(body).hexdigest(),
        output_audio_bit_rate=64_000,
        output_sample_rate_hz=48_000,
        output_channel_count=1,
        moov_before_mdat=True,
        fragmented=False,
        full_decode_passed=True,
    )


@pytest.mark.parametrize("scenario", ["accepted", "lease_replaced", "missing_journal"])
def test_normalization_checks_every_protected_input_with_media_role(
    client: TestClient, tmp_path: Path, monkeypatch: pytest.MonkeyPatch, scenario: str,
) -> None:
    meeting, result = _accept_first_party_recording(
        client, local_recording_id=f"protected-normalization-{scenario}", include_playback=True,
    )
    assert result["status_code"] == 200
    meeting_id = UUID(str(meeting["meeting_id"]))
    pipeline = FakeNormalizationPipeline("invalid")
    settings = client.app.state.settings
    recovery_id = uuid4()
    recovery_file = tmp_path / "recovery"
    recovery_file.with_suffix(".lock").touch()
    recovery_file.write_text(json.dumps({
        "schema": 1, "scope": "test-scope", "state": "reconciled", "recovery_id": str(recovery_id),
    }))
    settings.strict_storage_scope = "test-scope"
    settings.strict_storage_recovery_file = recovery_file
    settings.strict_storage_recovery_id = recovery_id
    settings.strict_storage_read_fence_directory = tmp_path
    storage = client.app_state["storage"]
    sessions = client.app_state["sessionmaker"]
    actual_reads: list[str] = []
    inputs = {}

    async def exercise():
        async with sessions.begin() as owner:
            job = await owner.scalar(select(PlaybackNormalizationJob).where(
                PlaybackNormalizationJob.meeting_id == meeting_id,
            ))
            assert job is not None
            current = await owner.get(Meeting, meeting_id)
            for source in await owner.scalars(select(TrackArtifact).where(
                TrackArtifact.meeting_id == meeting_id,
            )):
                role = source.track_role
                prefix = (
                    f"organizations/{job.organization_id}/workspaces/{job.workspace_id}/"
                    f"meetings/{meeting_id}/"
                )
                suffix = (
                    f"sessions/{uuid4()}/tracks/media/parts/00000001/calendar-attempts/1/2"
                    if role == "media"
                    else f"artifacts/media-revisions/{job.media_revision_id}/attempts/1/3/tracks/{role}"
                )
                key, journal_id = prefix + suffix, uuid4()
                inputs[key] = (journal_id, role, storage.objects[source.storage_object_key])
                source.storage_object_key = key
                if scenario == "missing_journal" and role == "media":
                    continue
                owner.add(PurgeJournal(
                    id=journal_id, workspace_id=job.workspace_id, meeting_id=meeting_id,
                    media_revision_id=job.media_revision_id, object_key=key,
                    artifact_class=STRICT_UPLOAD_ATTEMPT, state="retained", write_state="accepted",
                    storage_scope="test-scope", storage_epoch=1, deletion_epoch=current.deletion_epoch,
                ))

        async def ordinary_download(*args, **kwargs):
            pytest.fail("Protected input used the ordinary storage path")

        async def protected_download(key, destination, **request):
            journal_id, role, body = inputs[key]
            assert request["attempt_id"] == journal_id
            assert request["epoch"] == 1
            assert request["expected_sha256"] == sha256(body).hexdigest()
            assert request["expected_length"] == len(body)
            if role == "media" and scenario == "lease_replaced":
                async with sessions.begin() as other:
                    current_job = await other.get(PlaybackNormalizationJob, job.id)
                    current_job.lease_owner_sha256 = sha256(b"replacement").hexdigest()

            def read(_cancelled):
                actual_reads.append(role)
                return destination.write_bytes(body)

            return await read_with_storage_fence(
                request["fence_path"], admit=request["admit"], read=read,
            )

        monkeypatch.setattr(storage, "download_to_path_async", ordinary_download)
        monkeypatch.setattr(storage, "download_strict_source_to_path_async", protected_download, raising=False)
        async with client.app_state["media_sessionmaker"]() as db:
            db.info["runtime_settings"] = settings
            await apply_job_worker_scope(db, job)
            execution = run_normalization_job(
                db=db, storage=storage, job_id=job.id, work_directory=tmp_path, pipeline=pipeline,
            )
            if scenario == "accepted":
                assert (await execution).derivation_kind == "single_source_transcode"
                assert actual_reads == ["playback", "media"]
                assert pipeline.calls == ["candidate", "single_source"]
                return
            if scenario == "lease_replaced":
                with pytest.raises(NormalizationExecutionDeferred):
                    await execution
                assert not db.in_transaction()
            else:
                with pytest.raises(NormalizationExecutionFailure, match="source_missing"):
                    await execution
            assert actual_reads == ["playback"]
            assert pipeline.calls == ["candidate"]
        async with sessions() as check:
            persisted = await check.get(PlaybackNormalizationJob, job.id)
            assert persisted.canonical_track_artifact_id is None

    asyncio.run(exercise())


@pytest.mark.parametrize(
    ("candidate_mode", "expected_calls", "expected_derivation"),
    [
        ("copy", ["candidate"], "uploaded_candidate"),
        ("remux", ["candidate"], "lossless_faststart_remux"),
        ("invalid", ["candidate", "single_source"], "single_source_transcode"),
    ],
)
def test_first_party_workflow_uses_candidate_then_deterministic_source_fallback(
    client: TestClient,
    tmp_path: Path,
    candidate_mode: str,
    expected_calls: list[str],
    expected_derivation: str,
) -> None:
    meeting, result = _accept_first_party_recording(
        client,
        local_recording_id=f"normalization-workflow-{candidate_mode}",
        include_playback=True,
    )
    assert result["status_code"] == 200
    pipeline = FakeNormalizationPipeline(candidate_mode)

    async def execute_and_load():
        async with client.app_state["sessionmaker"]() as db:
            job = await db.scalar(
                select(PlaybackNormalizationJob).where(
                    PlaybackNormalizationJob.meeting_id == UUID(str(meeting["meeting_id"]))
                )
            )
            assert job is not None
            await apply_job_worker_scope(db, job)
            execution = await run_normalization_job(
                db=db,
                storage=client.app_state["storage"],
                job_id=job.id,
                work_directory=tmp_path,
                pipeline=pipeline,
            )
        async with client.app_state["sessionmaker"]() as db:
            refreshed_job = await db.get(PlaybackNormalizationJob, job.id)
            artifacts = (
                await db.scalars(
                    select(TrackArtifact).where(
                        TrackArtifact.meeting_id == UUID(str(meeting["meeting_id"])),
                        TrackArtifact.track_role == "playback",
                    )
                )
            ).all()
            attempt = await db.scalar(
                select(PlaybackNormalizationAttempt).where(
                    PlaybackNormalizationAttempt.job_id == job.id
                )
            )
            return execution, refreshed_job, artifacts, attempt

    execution, job, artifacts, attempt = asyncio.run(execute_and_load())
    assert pipeline.calls == expected_calls
    assert execution.reused is False
    assert execution.derivation_kind == expected_derivation
    assert job.state == "ready"
    assert job.canonical_track_artifact_id is not None
    canonical = next(
        artifact for artifact in artifacts if artifact.id == job.canonical_track_artifact_id
    )
    assert canonical.status == "stored"
    assert canonical.normalization_profile_version is not None
    assert canonical.validated_at is not None
    assert canonical.derivation_kind == expected_derivation
    assert (
        next(artifact for artifact in artifacts if artifact.id != canonical.id).status
        == "superseded"
    )
    assert attempt.state == "published"
    assert attempt.published_track_artifact_id == canonical.id


def test_ready_job_is_reused_without_running_media_again(
    client: TestClient, tmp_path: Path
) -> None:
    meeting, result = _accept_first_party_recording(
        client,
        local_recording_id="normalization-ready-reuse",
        include_playback=True,
    )
    assert result["status_code"] == 200
    first_pipeline = FakeNormalizationPipeline("copy")
    second_pipeline = FakeNormalizationPipeline("invalid")

    async def execute_twice():
        async with client.app_state["sessionmaker"]() as db:
            job = await db.scalar(
                select(PlaybackNormalizationJob).where(
                    PlaybackNormalizationJob.meeting_id == UUID(str(meeting["meeting_id"]))
                )
            )
            assert job is not None
            await apply_job_worker_scope(db, job)
            first = await run_normalization_job(
                db=db,
                storage=client.app_state["storage"],
                job_id=job.id,
                work_directory=tmp_path,
                pipeline=first_pipeline,
            )
            second = await run_normalization_job(
                db=db,
                storage=client.app_state["storage"],
                job_id=job.id,
                work_directory=tmp_path,
                pipeline=second_pipeline,
            )
            attempt_count = len(
                (
                    await db.scalars(
                        select(PlaybackNormalizationAttempt).where(
                            PlaybackNormalizationAttempt.job_id == job.id
                        )
                    )
                ).all()
            )
            return first, second, attempt_count

    first, second, attempt_count = asyncio.run(execute_twice())
    assert first.reused is False
    assert second.reused is True
    assert second.canonical_track_artifact_id == first.canonical_track_artifact_id
    assert first_pipeline.calls == ["candidate"]
    assert second_pipeline.calls == []
    assert attempt_count == 1


def test_manual_media_job_uses_the_accepted_media_artifact_and_publishes_canonical(
    client: TestClient,
    tmp_path: Path,
) -> None:
    client.app.state.settings.playback_normalization_enabled = True
    client.app.state.temporal_client = FakeTemporalClient()
    source_body = deterministic_wav_bytes(256)
    response = client.post(
        "/api/v1/media-uploads",
        headers=auth_headers(),
        data={
            "title": "Stable manual title",
            "duration_seconds": "60",
            "local_recording_id": "manual-normalization-worker-source",
        },
        files={"file": ("manual.wav", source_body, "audio/wav")},
    )
    assert response.status_code == 202
    meeting_id = UUID(response.json()["meeting"]["meeting_id"])
    pipeline = FakeManualNormalizationPipeline()
    work_directory = tmp_path / "normalization-work"

    async def execute_and_load():
        async with client.app_state["sessionmaker"]() as db:
            job = await db.scalar(
                select(PlaybackNormalizationJob).where(
                    PlaybackNormalizationJob.meeting_id == meeting_id
                )
            )
            assert job is not None
            await apply_job_worker_scope(db, job)
            execution = await run_normalization_job(
                db=db,
                storage=client.app_state["storage"],
                job_id=job.id,
                work_directory=work_directory,
                pipeline=pipeline,
            )
        async with client.app_state["sessionmaker"]() as db:
            artifacts = list(
                await db.scalars(
                    select(TrackArtifact).where(TrackArtifact.meeting_id == meeting_id)
                )
            )
            refreshed_job = await db.get(PlaybackNormalizationJob, job.id)
            stored_meeting = await db.get(Meeting, meeting_id)
            calendar_context = await db.scalar(
                select(RecordingCalendarContextLink).where(
                    RecordingCalendarContextLink.meeting_id == meeting_id
                )
            )
            return execution, refreshed_job, artifacts, stored_meeting, calendar_context

    execution, job, artifacts, stored_meeting, calendar_context = asyncio.run(execute_and_load())
    assert pipeline.source_body == source_body
    assert execution.derivation_kind == "single_source_transcode"
    assert job.state == "ready"
    assert job.canonical_track_artifact_id == execution.canonical_track_artifact_id
    source = next(artifact for artifact in artifacts if artifact.track_role == "media")
    canonical = next(
        artifact for artifact in artifacts if artifact.id == execution.canonical_track_artifact_id
    )
    assert source.status == "stored"
    assert canonical.track_role == "playback"
    assert canonical.status == "stored"
    assert canonical.validated_at is not None
    assert stored_meeting.title == "Stable manual title"
    assert stored_meeting.title_source == "upload_provided"
    assert calendar_context.context_state == "skipped_manual_upload"
    assert calendar_context.calendar_event_snapshot_id is None
    assert list(work_directory.iterdir()) == []


def test_real_ffmpeg_pipeline_builds_historical_dual_source_playback(tmp_path: Path) -> None:
    # Retained pre-v5 audio remains playable; no transcription submission occurs.
    ffmpeg = shutil.which("ffmpeg")
    ffprobe = shutil.which("ffprobe")
    if ffmpeg is None or ffprobe is None:
        pytest.fail("FFmpeg and ffprobe are required for this media test; install ffmpeg and ensure both tools are on PATH", pytrace=False)
    microphone_path = tmp_path / "microphone.wav"
    system_path = tmp_path / "system.wav"
    output_path = tmp_path / "meeting-review.m4a"
    microphone_path.write_bytes(synthetic_pcm_wav_bytes(duration_milliseconds=200))
    system_path.write_bytes(synthetic_pcm_wav_bytes(duration_milliseconds=250))
    pipeline = FFmpegNormalizationPipeline(
        ffmpeg_path=ffmpeg,
        ffprobe_path=ffprobe,
        probe_timeout_seconds=15,
        process_timeout_seconds=30,
    )

    output = asyncio.run(pipeline.derive_dual_source(microphone_path, system_path, output_path))

    assert output.derivation_kind == "dual_source_mix_transcode"
    assert output.output_sample_rate_hz == 48_000
    assert output.output_channel_count == 1
    assert output.moov_before_mdat is True
    assert output.fragmented is False
    assert output.full_decode_passed is True
    assert output.output_byte_length == output_path.stat().st_size
