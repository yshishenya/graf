from __future__ import annotations

import asyncio
import os
import shutil
import subprocess
from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from uuid import UUID

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select

from tests.contract.test_ingest_openapi_contract import auth_headers
from tests.fixtures.processing import apply_job_worker_scope
from twobrain_rec_server.db.models import (
    PlaybackNormalizationAttempt,
    PlaybackNormalizationJob,
    TrackArtifact,
)
from twobrain_rec_server.normalization.media import (
    FORMAT_WHITELIST,
    build_full_decode_command,
    inspect_bmff,
    run_bounded_process,
)
from twobrain_rec_server.normalization.service import (
    FFmpegNormalizationPipeline,
    run_normalization_job,
)
from twobrain_rec_server.normalization.statuses import CANONICAL_PROFILE_VERSION

TEST_REC_DIRECTORY_ENV = "GRAF_TEST_REC_DIR"
WORKING_COPY_DURATION_SECONDS = 4


@dataclass(frozen=True, slots=True)
class AuthorizedSources:
    microphone: Path
    system: Path
    playback: Path


@dataclass(frozen=True, slots=True)
class PreparedSources:
    microphone: bytes
    system: bytes
    canonical_m4a: bytes
    non_faststart_m4a: bytes


@dataclass(frozen=True, slots=True)
class ScenarioResult:
    alias: str
    derivation_kind: str
    output_byte_length: int
    output_duration_seconds: int
    attempt_count: int


def _digest_file(path: Path) -> str:
    digest = sha256()
    with path.open("rb") as source:
        while chunk := source.read(4 * 1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _authorized_sources(root: Path) -> AuthorizedSources:
    media_files = [path for path in root.rglob("*") if path.is_file()]
    wav_files = sorted(
        (path for path in media_files if path.suffix.casefold() == ".wav"),
        key=lambda path: (path.stat().st_size, str(path)),
        reverse=True,
    )
    m4a_files = sorted(
        (path for path in media_files if path.suffix.casefold() == ".m4a"),
        key=lambda path: (path.stat().st_size, str(path)),
        reverse=True,
    )
    assert len(wav_files) >= 2, "authorized input must contain two WAV sources"
    assert m4a_files, "authorized input must contain an M4A candidate"
    return AuthorizedSources(
        microphone=wav_files[0],
        system=wav_files[1],
        playback=m4a_files[0],
    )


def _copy_authorized_sources(
    sources: AuthorizedSources,
    destination: Path,
) -> tuple[AuthorizedSources, dict[str, str]]:
    destination.mkdir(mode=0o700, parents=True)
    selected = {
        "microphone": sources.microphone,
        "system": sources.system,
        "playback": sources.playback,
    }
    before = {alias: _digest_file(path) for alias, path in selected.items()}
    copied = AuthorizedSources(
        microphone=destination / "source-a.wav",
        system=destination / "source-b.wav",
        playback=destination / "source-c.m4a",
    )
    for alias, target in {
        "microphone": copied.microphone,
        "system": copied.system,
        "playback": copied.playback,
    }.items():
        shutil.copyfile(selected[alias], target)
        assert _digest_file(target) == before[alias]
    return copied, before


def _run_setup_ffmpeg(arguments: list[str]) -> None:
    completed = subprocess.run(
        arguments,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.PIPE,
        timeout=120,
        check=False,
    )
    assert completed.returncode == 0, (
        "working-copy media setup failed "
        f"with {len(completed.stderr)} bytes of redacted diagnostics"
    )


def _ffmpeg_input_arguments(ffmpeg: str, source: Path) -> list[str]:
    return [
        ffmpeg,
        "-hide_banner",
        "-loglevel",
        "error",
        "-nostdin",
        "-xerror",
        "-y",
        "-protocol_whitelist",
        "file",
        "-format_whitelist",
        FORMAT_WHITELIST,
        "-probesize",
        "16777216",
        "-analyzeduration",
        "30000000",
        "-i",
        str(source),
    ]


def _extract_wav_working_copy(ffmpeg: str, source: Path, output: Path) -> None:
    _run_setup_ffmpeg(
        [
            *_ffmpeg_input_arguments(ffmpeg, source),
            "-map",
            "0:a:0",
            "-t",
            str(WORKING_COPY_DURATION_SECONDS),
            "-vn",
            "-sn",
            "-dn",
            "-map_metadata",
            "-1",
            "-map_chapters",
            "-1",
            "-ac",
            "1",
            "-ar",
            "16000",
            "-c:a",
            "pcm_s16le",
            "-f",
            "wav",
            str(output),
        ]
    )


def _extract_m4a_working_copy(ffmpeg: str, source: Path, output: Path) -> None:
    _run_setup_ffmpeg(
        [
            *_ffmpeg_input_arguments(ffmpeg, source),
            "-map",
            "0:a:0",
            "-t",
            str(WORKING_COPY_DURATION_SECONDS),
            "-vn",
            "-sn",
            "-dn",
            "-map_metadata",
            "-1",
            "-map_chapters",
            "-1",
            "-c:a",
            "copy",
            "-fflags",
            "+bitexact",
            "-disposition:a:0",
            "default",
            "-f",
            "ipod",
            str(output),
        ]
    )


def _make_non_faststart_copy(ffmpeg: str, source: Path, output: Path) -> None:
    _run_setup_ffmpeg(
        [
            *_ffmpeg_input_arguments(ffmpeg, source),
            "-map",
            "0:a:0",
            "-vn",
            "-sn",
            "-dn",
            "-map_metadata",
            "-1",
            "-map_chapters",
            "-1",
            "-c:a",
            "copy",
            "-fflags",
            "+bitexact",
            "-disposition:a:0",
            "default",
            "-f",
            "ipod",
            str(output),
        ]
    )


def _prepare_scenario_sources(
    *,
    copied: AuthorizedSources,
    work_directory: Path,
    pipeline: FFmpegNormalizationPipeline,
    ffmpeg: str,
) -> PreparedSources:
    microphone = work_directory / "scenario-microphone.wav"
    system = work_directory / "scenario-system.wav"
    extracted_m4a = work_directory / "scenario-source.m4a"
    canonical_m4a = work_directory / "scenario-canonical.m4a"
    non_faststart_m4a = work_directory / "scenario-non-faststart.m4a"
    _extract_wav_working_copy(ffmpeg, copied.microphone, microphone)
    _extract_wav_working_copy(ffmpeg, copied.system, system)
    _extract_m4a_working_copy(ffmpeg, copied.playback, extracted_m4a)
    normalized = asyncio.run(pipeline.derive_single_source(extracted_m4a, canonical_m4a))
    assert normalized.full_decode_passed is True
    assert normalized.output_sample_rate_hz == 48_000
    assert normalized.output_channel_count == 1
    assert inspect_bmff(canonical_m4a).moov_before_mdat is True
    _make_non_faststart_copy(ffmpeg, canonical_m4a, non_faststart_m4a)
    assert inspect_bmff(non_faststart_m4a).moov_before_mdat is False
    return PreparedSources(
        microphone=microphone.read_bytes(),
        system=system.read_bytes(),
        canonical_m4a=canonical_m4a.read_bytes(),
        non_faststart_m4a=non_faststart_m4a.read_bytes(),
    )


def _descriptor(role: str, data: bytes) -> dict[str, object]:
    is_playback = role == "playback"
    return {
        "track_role": role,
        "codec": "m4a-aac-lc" if is_playback else "pcm_s16le",
        "sample_rate_hz": 48_000 if is_playback else 16_000,
        "channel_count": 1,
        "duration_seconds": WORKING_COPY_DURATION_SECONDS,
        "byte_length": len(data),
        "sha256": sha256(data).hexdigest(),
    }


def _accept_first_party(
    client: TestClient,
    *,
    alias: str,
    sources: PreparedSources,
    candidate: bytes | None,
) -> UUID:
    meeting_response = client.post(
        "/api/v1/meetings",
        headers=auth_headers(),
        json={
            "local_recording_id": f"test-rec-{alias}",
            "duration_seconds": WORKING_COPY_DURATION_SECONDS,
        },
    )
    assert meeting_response.status_code == 200
    meeting = meeting_response.json()
    payloads = {
        "manifest": b'{"schema":"test-rec-working-copy"}',
        "microphone": sources.microphone,
        "system": sources.system,
    }
    if candidate is not None:
        payloads["playback"] = candidate
    session_response = client.post(
        f"/api/v1/meetings/{meeting['meeting_id']}/upload-sessions",
        headers=auth_headers(),
        json={
            "expected_tracks": list(payloads),
            "expected_track_sizes": {role: len(data) for role, data in payloads.items()},
        },
    )
    assert session_response.status_code == 200
    session = session_response.json()
    descriptors = []
    for role, data in payloads.items():
        digest = sha256(data).hexdigest()
        upload = client.put(
            f"/api/v1/upload-sessions/{session['session_id']}/tracks/{role}/parts/0",
            headers=auth_headers()
            | {"X-Byte-Offset": "0", "X-Content-SHA256": digest},
            content=data,
        )
        assert upload.status_code == 200
        descriptors.append(_descriptor(role, data))
    finalize = client.post(
        f"/api/v1/upload-sessions/{session['session_id']}/finalize",
        headers=auth_headers(),
        json={
            "manifest_sha256": sha256(payloads["manifest"]).hexdigest(),
            "tracks": descriptors,
        },
    )
    assert finalize.status_code == 200
    return UUID(str(meeting["meeting_id"]))


def _accept_manual(
    client: TestClient,
    *,
    alias: str,
    body: bytes,
    filename: str,
    content_type: str,
) -> UUID:
    response = client.post(
        "/api/v1/media-uploads",
        headers=auth_headers(),
        data={
            "title": f"Test-rec {alias}",
            "duration_seconds": str(WORKING_COPY_DURATION_SECONDS),
            "local_recording_id": f"test-rec-{alias}",
        },
        files={"file": (filename, body, content_type)},
    )
    assert response.status_code == 202
    return UUID(response.json()["meeting"]["meeting_id"])


async def _execute_job(
    client: TestClient,
    *,
    meeting_id: UUID,
    work_directory: Path,
    pipeline: FFmpegNormalizationPipeline,
) -> tuple[str, TrackArtifact, int, list[TrackArtifact]]:
    async with client.app_state["sessionmaker"]() as db:
        job = await db.scalar(
            select(PlaybackNormalizationJob).where(
                PlaybackNormalizationJob.meeting_id == meeting_id
            )
        )
        assert job is not None
        assert job.state == "queued"
        await apply_job_worker_scope(db, job)
        execution = await run_normalization_job(
            db=db,
            storage=client.app_state["storage"],
            job_id=job.id,
            work_directory=work_directory,
            pipeline=pipeline,
        )
    async with client.app_state["sessionmaker"]() as db:
        refreshed = await db.get(PlaybackNormalizationJob, job.id)
        artifacts = list(
            await db.scalars(
                select(TrackArtifact).where(TrackArtifact.meeting_id == meeting_id)
            )
        )
        attempts = list(
            await db.scalars(
                select(PlaybackNormalizationAttempt).where(
                    PlaybackNormalizationAttempt.job_id == job.id
                )
            )
        )
        assert refreshed is not None
        assert refreshed.state == "ready"
        assert refreshed.canonical_track_artifact_id == execution.canonical_track_artifact_id
        canonical = next(
            artifact
            for artifact in artifacts
            if artifact.id == execution.canonical_track_artifact_id
        )
        assert canonical.status == "stored"
        assert canonical.normalization_profile_version == CANONICAL_PROFILE_VERSION
        assert canonical.validated_at is not None
        assert canonical.sample_rate_hz == 48_000
        assert canonical.channel_count == 1
        assert len(attempts) == 1
        assert attempts[0].state == "published"
        assert attempts[0].full_decode_passed is True
        return execution.derivation_kind, canonical, len(attempts), artifacts


def _full_decode(ffmpeg: str, canonical_path: Path) -> None:
    result = asyncio.run(
        run_bounded_process(
            build_full_decode_command(ffmpeg, canonical_path, stream_index=0),
            timeout_seconds=30,
            stdout_limit_bytes=0,
            stderr_limit_bytes=1024 * 1024,
            allowed_executables=(ffmpeg,),
            cwd=canonical_path.parent,
        )
    )
    assert result.return_code == 0


def _run_scenario(
    client: TestClient,
    *,
    alias: str,
    meeting_id: UUID,
    expected_derivation: str,
    work_directory: Path,
    pipeline: FFmpegNormalizationPipeline,
    ffmpeg: str,
) -> tuple[ScenarioResult, list[TrackArtifact]]:
    derivation, canonical, attempt_count, artifacts = asyncio.run(
        _execute_job(
            client,
            meeting_id=meeting_id,
            work_directory=work_directory,
            pipeline=pipeline,
        )
    )
    assert derivation == expected_derivation
    canonical_body = client.app_state["storage"].objects[canonical.storage_object_key]
    assert len(canonical_body) == canonical.byte_length
    canonical_path = work_directory.parent / f"{alias}-canonical.m4a"
    canonical_path.write_bytes(canonical_body)
    _full_decode(ffmpeg, canonical_path)
    assert inspect_bmff(canonical_path).moov_before_mdat is True
    range_response = client.get(
        f"/api/v1/cabinet/meetings/{meeting_id}/playback",
        headers={**auth_headers(), "Range": "bytes=0-1023"},
    )
    assert range_response.status_code == 206
    assert range_response.headers["accept-ranges"] == "bytes"
    assert range_response.content == canonical_body[: len(range_response.content)]
    canonical_path.unlink()
    assert list(work_directory.iterdir()) == []
    return (
        ScenarioResult(
            alias=alias,
            derivation_kind=derivation,
            output_byte_length=canonical.byte_length,
            output_duration_seconds=canonical.duration_seconds,
            attempt_count=attempt_count,
        ),
        artifacts,
    )


def test_authorized_test_rec_converts_automatically_and_leaves_no_residue(
    client: TestClient,
    tmp_path: Path,
) -> None:
    configured_root = os.environ.get(TEST_REC_DIRECTORY_ENV)
    if configured_root is None:
        pytest.skip(f"set {TEST_REC_DIRECTORY_ENV} for authorized local evidence")
    source_root = Path(configured_root).resolve()
    assert source_root.is_dir(), "authorized input directory is unavailable"
    ffmpeg = shutil.which("ffmpeg")
    ffprobe = shutil.which("ffprobe")
    if ffmpeg is None or ffprobe is None:
        pytest.skip("FFmpeg capability is validated in the media runtime container")

    original_sources = _authorized_sources(source_root)
    working_root = tmp_path / "feature-099-test-rec"
    source_copy_root = working_root / "original-copies"
    job_work_root = working_root / "job-work"
    job_work_root.mkdir(mode=0o700, parents=True)
    copied_sources, original_digests = _copy_authorized_sources(
        original_sources,
        source_copy_root,
    )
    pipeline = FFmpegNormalizationPipeline(
        ffmpeg_path=ffmpeg,
        ffprobe_path=ffprobe,
        probe_timeout_seconds=30,
        process_timeout_seconds=120,
    )

    try:
        prepared = _prepare_scenario_sources(
            copied=copied_sources,
            work_directory=working_root,
            pipeline=pipeline,
            ffmpeg=ffmpeg,
        )
        scenarios: list[ScenarioResult] = []

        candidate_id = _accept_first_party(
            client,
            alias="candidate-copy",
            sources=prepared,
            candidate=prepared.canonical_m4a,
        )
        result, candidate_artifacts = _run_scenario(
            client,
            alias="candidate-copy",
            meeting_id=candidate_id,
            expected_derivation="uploaded_candidate",
            work_directory=job_work_root,
            pipeline=pipeline,
            ffmpeg=ffmpeg,
        )
        scenarios.append(result)
        assert any(
            artifact.track_role == "playback" and artifact.status == "superseded"
            for artifact in candidate_artifacts
        )

        remux_id = _accept_first_party(
            client,
            alias="candidate-remux",
            sources=prepared,
            candidate=prepared.non_faststart_m4a,
        )
        result, _ = _run_scenario(
            client,
            alias="candidate-remux",
            meeting_id=remux_id,
            expected_derivation="lossless_faststart_remux",
            work_directory=job_work_root,
            pipeline=pipeline,
            ffmpeg=ffmpeg,
        )
        scenarios.append(result)

        fallback_id = _accept_first_party(
            client,
            alias="dual-source-fallback",
            sources=prepared,
            candidate=None,
        )
        result, _ = _run_scenario(
            client,
            alias="dual-source-fallback",
            meeting_id=fallback_id,
            expected_derivation="dual_source_mix_transcode",
            work_directory=job_work_root,
            pipeline=pipeline,
            ffmpeg=ffmpeg,
        )
        scenarios.append(result)

        manual_m4a_id = _accept_manual(
            client,
            alias="manual-m4a",
            body=prepared.canonical_m4a,
            filename="manual-source.m4a",
            content_type="audio/mp4",
        )
        result, manual_m4a_artifacts = _run_scenario(
            client,
            alias="manual-m4a",
            meeting_id=manual_m4a_id,
            expected_derivation="source_byte_copy",
            work_directory=job_work_root,
            pipeline=pipeline,
            ffmpeg=ffmpeg,
        )
        scenarios.append(result)
        assert any(
            artifact.track_role == "media" and artifact.status == "stored"
            for artifact in manual_m4a_artifacts
        )

        manual_wav_id = _accept_manual(
            client,
            alias="manual-wav",
            body=prepared.microphone,
            filename="manual-source.wav",
            content_type="audio/wav",
        )
        result, manual_wav_artifacts = _run_scenario(
            client,
            alias="manual-wav",
            meeting_id=manual_wav_id,
            expected_derivation="single_source_transcode",
            work_directory=job_work_root,
            pipeline=pipeline,
            ffmpeg=ffmpeg,
        )
        scenarios.append(result)
        assert any(
            artifact.track_role == "media" and artifact.status == "stored"
            for artifact in manual_wav_artifacts
        )

        assert [scenario.alias for scenario in scenarios] == [
            "candidate-copy",
            "candidate-remux",
            "dual-source-fallback",
            "manual-m4a",
            "manual-wav",
        ]
        assert all(scenario.output_byte_length > 0 for scenario in scenarios)
        assert all(scenario.output_duration_seconds > 0 for scenario in scenarios)
        assert all(scenario.attempt_count == 1 for scenario in scenarios)
    finally:
        for object_key in tuple(client.app_state["storage"].objects):
            client.app_state["storage"].delete_object(object_key)
        shutil.rmtree(working_root, ignore_errors=True)

    assert client.app_state["storage"].objects == {}
    assert not working_root.exists()
    assert _digest_file(original_sources.microphone) == original_digests["microphone"]
    assert _digest_file(original_sources.system) == original_digests["system"]
    assert _digest_file(original_sources.playback) == original_digests["playback"]
