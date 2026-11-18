"""Real automatic server acceptance for F099 T014.

This module lives outside ``testpaths`` and outside the ``test_*.py`` pattern.
It is collected only through the explicit supervisor
``scripts/run_playback_normalization_real_transport.py``.

The standard-library guard below runs before any application import.  It
requires the supervisor context and a private manifest, so an accidental
selection cannot start MinIO, Temporal, PostgreSQL or migrations.
"""

# The standard-library guard must run before every application import.
# ruff: noqa: E402

from __future__ import annotations

import json
import os
import stat
from pathlib import Path

CONTEXT_ENV = "GRAF_F099_ACCEPTANCE_CONTEXT"
CONTEXT_KEYS = {
    "schema_version",
    "run_token",
    "docker_host",
    "postgres_image_id",
    "minio_image",
    "minio_image_id",
    "minio_container_name",
    "temporal_cli_path",
    "temporal_cli_sha256",
    "ffmpeg_path",
    "ffmpeg_sha256",
    "ffmpeg_version",
    "ffprobe_path",
    "ffprobe_sha256",
    "ffprobe_version",
    "work_directory",
    "result_file",
    "minio_resource_file",
    "whole_run_seconds",
}
RESOURCE_LABEL = "pro.2brain.graf.f099.run"


def _load_launch_context() -> dict[str, object]:
    raw_path = os.environ.get(CONTEXT_ENV)
    if not raw_path:
        raise RuntimeError(
            "real transport acceptance requires the explicit F099 supervisor context; "
            "run apps/server/scripts/run_playback_normalization_real_transport.py"
        )
    path = Path(raw_path)
    if not path.is_absolute():
        raise RuntimeError("acceptance context path must be absolute")
    metadata = path.lstat()
    if not stat.S_ISREG(metadata.st_mode) or stat.S_ISLNK(metadata.st_mode):
        raise RuntimeError("acceptance context must be a regular non-symlink file")
    if metadata.st_mode & 0o177:
        raise RuntimeError("acceptance context mode must be 0600")
    if metadata.st_uid != os.geteuid():
        raise RuntimeError("acceptance context owner is invalid")
    if metadata.st_size > 65536:
        raise RuntimeError("acceptance context is too large")
    document = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(document, dict) or set(document) != CONTEXT_KEYS:
        raise RuntimeError("acceptance context has an unexpected shape")
    if type(document["schema_version"]) is not int or document["schema_version"] != 1:
        raise RuntimeError("acceptance context schema_version must be 1")
    token = document["run_token"]
    if (
        not isinstance(token, str)
        or len(token) != 32
        or any(character not in "0123456789abcdef" for character in token)
    ):
        raise RuntimeError("acceptance context run_token is invalid")
    work_directory = Path(str(document["work_directory"]))
    if not work_directory.is_absolute() or work_directory.is_symlink():
        raise RuntimeError("acceptance work directory is invalid")
    work_metadata = work_directory.stat()
    if work_metadata.st_mode & 0o077 or work_metadata.st_uid != os.geteuid():
        raise RuntimeError("acceptance work directory must be private and owned")
    return document


LAUNCH = _load_launch_context()

import asyncio  # noqa: E402
import hashlib  # noqa: E402
import shutil  # noqa: E402
import socket  # noqa: E402
import subprocess  # noqa: E402
import tempfile  # noqa: E402
import time  # noqa: E402
import uuid  # noqa: E402
from contextlib import suppress  # noqa: E402
from typing import Any  # noqa: E402

import httpx  # noqa: E402
from sqlalchemy import func, select, text  # noqa: E402
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine  # noqa: E402
from sqlalchemy.pool import NullPool  # noqa: E402
from temporalio import activity  # noqa: E402
from temporalio.client import WorkflowExecutionStatus  # noqa: E402
from temporalio.testing import WorkflowEnvironment  # noqa: E402

pytest_plugins = ("tests.conftest",)

from tests.fakes.auth_contexts import (
    AUTH_BOOTSTRAP_WORKSPACE_ID,
    DEVICE_ID,
    ORG_ID,
    USER_ID,
    WORKSPACE_ID,
)  # noqa: E402
from twobrain_rec_server.auth.context import TenantScope  # noqa: E402
from twobrain_rec_server.config import Settings  # noqa: E402
from twobrain_rec_server.db.models import (  # noqa: E402
    Meeting,
    PlaybackNormalizationAttempt,
    PlaybackNormalizationJob,
    TrackArtifact,
)
from twobrain_rec_server.db.tenant_context import apply_tenant_scope  # noqa: E402
from twobrain_rec_server.main import create_app  # noqa: E402
from twobrain_rec_server.normalization.media import (  # noqa: E402
    build_full_decode_command,
    build_probe_command,
    inspect_bmff,
    parse_probe_output,
    validate_canonical_profile,
)
from twobrain_rec_server.normalization.worker import (  # noqa: E402
    create_normalization_temporal_workers,
    run_playback_normalization_activity,
)
from twobrain_rec_server.normalization.worker_readiness import (  # noqa: E402
    run_playback_normalization_readiness_activity,
)
from twobrain_rec_server.workflows.temporal_client import (
    playback_normalization_workflow_id,  # noqa: E402
)

SCENARIO_SECONDS = 120
DOWNLOAD_SECONDS = 60
RESOURCE_SECONDS = 60
TEARDOWN_SECONDS = 30
PROFILE_VERSION = "review_m4a_aac_lc_48k_mono_64k_v1"
def _auth_headers() -> dict[str, str]:
    return {
        "X-Organization-Id": str(ORG_ID),
        "X-Workspace-Id": str(WORKSPACE_ID),
        "X-User-Id": str(USER_ID),
        "X-Device-Id": str(DEVICE_ID),
    }


SCOPE = TenantScope(
    organization_id=ORG_ID,
    workspace_id=WORKSPACE_ID,
    user_id=USER_ID,
    device_id=DEVICE_ID,
)


def _private_json(path: Path, payload: dict[str, Any]) -> None:
    temporary = path.with_name(f"{path.name}.tmp.{os.getpid()}")
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as output:
            json.dump(payload, output, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
            output.write("\n")
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while chunk := source.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _docker_command() -> list[str]:
    docker = shutil.which("docker")
    if not docker:
        raise RuntimeError("docker CLI is unavailable")
    return [docker]


def _docker(arguments: list[str], *, timeout: int = RESOURCE_SECONDS) -> subprocess.CompletedProcess[str]:
    completed = subprocess.run(
        [*_docker_command(), *arguments],
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=timeout,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError(f"docker command failed: {arguments[0]}")
    return completed


def _container_identity(name: str) -> tuple[str, str, str, str] | None:
    completed = subprocess.run(
        [
            *_docker_command(),
            "inspect",
            "--format",
            '{{.Id}}|{{.Name}}|{{index .Config.Labels "' + RESOURCE_LABEL + '"}}|{{.Image}}',
            name,
        ],
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=RESOURCE_SECONDS,
        check=False,
    )
    if completed.returncode != 0:
        return None
    parts = completed.stdout.strip().split("|")
    return tuple(parts) if len(parts) == 4 else None


def _exact_container_ids(name: str) -> list[str]:
    completed = _docker(["ps", "-aq", "--no-trunc", "--filter", f"name=^/{name}$"])
    return [line.strip() for line in completed.stdout.splitlines() if line.strip()]


def _remove_verified_container(
    *, name: str, token: str, image_id: str, candidate_id: str | None
) -> str:
    identity = _container_identity(candidate_id) if candidate_id else None
    if identity is None:
        candidates = _exact_container_ids(name)
        if not candidates:
            return "confirmed_absent"
        if len(candidates) != 1:
            return "ambiguous_lookup"
        candidate_id = candidates[0]
        identity = _container_identity(candidate_id)
    if identity is None:
        return "identity_unreadable"
    actual_id, actual_name, actual_token, actual_image = identity
    if actual_name != f"/{name}" or actual_token != token or actual_image != image_id:
        return "foreign_or_mismatched_container"
    completed = subprocess.run(
        [*_docker_command(), "rm", "--force", "--volumes", actual_id],
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=TEARDOWN_SECONDS,
        check=False,
    )
    if completed.returncode != 0:
        return "remove_failed"
    if _container_identity(actual_id) is not None:
        return "still_present_after_remove"
    if _exact_container_ids(name):
        return "name_still_present"
    return "removed"


def _free_port() -> int:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.bind(("127.0.0.1", 0))
        return int(listener.getsockname()[1])


def _wait_for_http(url: str, *, deadline: float) -> None:
    import urllib.error
    import urllib.request

    while time.monotonic() < deadline:
        try:
            with urllib.request.urlopen(url, timeout=2) as response:
                if response.status == 200:
                    return
        except (urllib.error.URLError, TimeoutError, ConnectionError):
            pass
        time.sleep(0.25)
    raise RuntimeError("MinIO readiness deadline exceeded")


def _start_minio() -> dict[str, str]:
    token = str(LAUNCH["run_token"])
    name = str(LAUNCH["minio_container_name"])
    image_id = str(LAUNCH["minio_image_id"])
    image_reference = str(LAUNCH["minio_image"])
    local_image = _docker(["image", "inspect", "--format", "{{.Id}}", image_reference]).stdout.strip()
    if local_image != image_id:
        raise RuntimeError("MinIO image ID does not match the admitted local image")
    if _exact_container_ids(name):
        raise RuntimeError("MinIO container name is already in use")
    resource_file = Path(str(LAUNCH["minio_resource_file"]))
    _private_json(
        resource_file,
        {
            "schema_version": 1,
            "run_token": token,
            "container_name": name,
            "image_id": image_id,
            "state": "cleanup_required",
        },
    )
    access_key = "graf" + token[:12]
    secret_key = token * 2
    bucket = "graf-f099-" + token[:16]
    completed = subprocess.run(
        [
            *_docker_command(),
            "run",
            "--detach",
            "--rm",
            "--pull=never",
            "--name",
            name,
            "--label",
            f"{RESOURCE_LABEL}={token}",
            "--env",
            f"MINIO_ROOT_USER={access_key}",
            "--env",
            f"MINIO_ROOT_PASSWORD={secret_key}",
            "--publish",
            "127.0.0.1::9000",
            "--memory",
            "512m",
            "--cpus",
            "1",
            image_id,
            "server",
            "/data",
        ],
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=RESOURCE_SECONDS,
        check=False,
    )
    if completed.returncode != 0:
        raise RuntimeError("MinIO container did not start")
    identity = _container_identity(name)
    if identity is None:
        raise RuntimeError("MinIO container identity is unavailable")
    actual_id, actual_name, actual_token, actual_image = identity
    if actual_name != f"/{name}" or actual_token != token or actual_image != image_id:
        raise RuntimeError("MinIO container identity does not match the admitted resource")
    _private_json(
        resource_file,
        {
            "schema_version": 1,
            "run_token": token,
            "container_name": name,
            "image_id": image_id,
            "container_id": actual_id,
            "state": "running",
        },
    )
    port_line = _docker(["port", actual_id, "9000/tcp"]).stdout.strip().splitlines()
    if len(port_line) != 1 or ":" not in port_line[0]:
        raise RuntimeError("MinIO did not expose exactly one loopback port")
    port = int(port_line[0].rsplit(":", 1)[1])
    _wait_for_http(
        f"http://127.0.0.1:{port}/minio/health/ready",
        deadline=time.monotonic() + RESOURCE_SECONDS,
    )
    return {
        "endpoint": f"127.0.0.1:{port}",
        "access_key": access_key,
        "secret_key": secret_key,
        "bucket": bucket,
        "container_id": actual_id,
    }


def _stop_minio(container_id: str) -> str:
    token = str(LAUNCH["run_token"])
    name = str(LAUNCH["minio_container_name"])
    image_id = str(LAUNCH["minio_image_id"])
    result = _remove_verified_container(
        name=name, token=token, image_id=image_id, candidate_id=container_id
    )
    resource_file = Path(str(LAUNCH["minio_resource_file"]))
    with suppress(OSError):
        _private_json(
            resource_file,
            {
                "schema_version": 1,
                "run_token": token,
                "container_name": name,
                "image_id": image_id,
                "state": "clean" if result in {"removed", "confirmed_absent"} else "cleanup_required",
                "result": result,
            },
        )
    return result


def _create_wav(path: Path, ffmpeg: str) -> None:
    completed = subprocess.run(
        [
            ffmpeg,
            "-hide_banner",
            "-loglevel",
            "error",
            "-nostdin",
            "-y",
            "-f",
            "lavfi",
            "-i",
            "sine=frequency=440:duration=1",
            "-ar",
            "16000",
            "-ac",
            "1",
            "-c:a",
            "pcm_s16le",
            str(path),
        ],
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=DOWNLOAD_SECONDS,
        check=False,
    )
    if completed.returncode != 0 or not path.is_file():
        raise RuntimeError("synthetic WAV generation failed")


async def _assert_media_role(media_sessionmaker: Any) -> dict[str, str]:
    async with media_sessionmaker() as session:
        identity = (
            await session.execute(
                text(
                    "select current_user, session_user, "
                    "(select rolsuper from pg_roles where rolname = current_user), "
                    "(select rolbypassrls from pg_roles where rolname = current_user), "
                    "(select rolcanlogin from pg_roles where rolname = current_user)"
                )
            )
        ).one()
        row_security = (await session.execute(text("show row_security"))).scalar_one()
    current_user, session_user, is_super, bypass_rls, can_login = identity
    if current_user != "twobrain_rec_media" or session_user != "twobrain_rec_media":
        raise RuntimeError("media role is not the active session role")
    if is_super or bypass_rls or not can_login:
        raise RuntimeError("media role has unsafe attributes")
    if str(row_security).lower() != "on":
        raise RuntimeError("media role must run with row_security=on")

    return {
        "current_user": "twobrain_rec_media",
        "row_security": "on",
    }


async def _assert_media_tenant_visibility(
    media_sessionmaker: Any, meeting_id: uuid.UUID
) -> dict[str, str]:
    async with media_sessionmaker() as session:
        await apply_tenant_scope(session, SCOPE, context_kind="worker")
        visible = await session.scalar(
            select(func.count())
            .select_from(Meeting)
            .where(Meeting.id == meeting_id, Meeting.workspace_id == WORKSPACE_ID)
        )
    if visible != 1:
        raise RuntimeError("media role cannot see its own tenant meeting")
    async with media_sessionmaker() as session:
        foreign = TenantScope(
            organization_id=ORG_ID,
            workspace_id=uuid.UUID(int=0xDEAD),
            user_id=USER_ID,
            device_id=DEVICE_ID,
        )
        await apply_tenant_scope(session, foreign, context_kind="worker")
        leaked = await session.scalar(select(func.count()).select_from(Meeting))
    if leaked:
        raise RuntimeError("media role leaked another tenant")
    return {"own_tenant_rows": "1", "foreign_tenant_rows": "0"}


async def _wait_job(
    app: Any,
    media_revision_id: uuid.UUID,
    *,
    deadline: float,
) -> PlaybackNormalizationJob:
    while time.monotonic() < deadline:
        async with app.state.db_sessionmaker() as session:
            await apply_tenant_scope(session, SCOPE, context_kind="worker")
            job = await session.scalar(
                select(PlaybackNormalizationJob).where(
                    PlaybackNormalizationJob.workspace_id == WORKSPACE_ID,
                    PlaybackNormalizationJob.media_revision_id == media_revision_id,
                )
            )
        if job is not None and job.state in {"ready", "terminal", "cancelled"}:
            return job
        await asyncio.sleep(0.5)
    raise RuntimeError("normalization job deadline exceeded")


async def _upload(
    client: httpx.AsyncClient,
    *,
    filename: str,
    payload: bytes,
    content_type: str,
    local_recording_id: str,
) -> dict[str, Any]:
    response = await client.post(
        "/api/v1/media-uploads",
        headers=_auth_headers(),
        data={
            "duration_seconds": "1",
            "local_recording_id": local_recording_id,
            "archive_audio": "true",
            "title": "F099 synthetic acceptance",
        },
        files={"file": (filename, payload, content_type)},
    )
    if response.status_code != 202:
        raise RuntimeError(
            f"media upload was not accepted: HTTP {response.status_code} {response.text[:300]}"
        )
    return response.json()


async def _prove_canonical(
    *,
    storage: Any,
    artifact: TrackArtifact,
    ffmpeg: str,
    ffprobe: str,
    work_directory: Path,
) -> dict[str, Any]:
    download_directory = Path(tempfile.mkdtemp(prefix="canonical-", dir=work_directory))
    try:
        destination = download_directory / "canonical.m4a"
        await storage.download_verified_to_path_async(
            artifact.storage_object_key,
            destination,
            expected_length=artifact.byte_length,
            expected_sha256=artifact.sha256,
            max_bytes=artifact.byte_length,
        )
        digest = _sha256_file(destination)
        if digest != artifact.sha256 or destination.stat().st_size != artifact.byte_length:
            raise RuntimeError("downloaded canonical does not match its stored metadata")
        bmff_layout = inspect_bmff(destination)
        probe = subprocess.run(
            build_probe_command(ffprobe, destination),
            stdin=subprocess.DEVNULL,
            capture_output=True,
            timeout=DOWNLOAD_SECONDS,
            check=False,
        )
        if probe.returncode != 0:
            raise RuntimeError("ffprobe rejected the downloaded canonical")
        facts = parse_probe_output(probe.stdout)
        decode = subprocess.run(
            build_full_decode_command(ffmpeg, destination, stream_index=0),
            stdin=subprocess.DEVNULL,
            capture_output=True,
            timeout=DOWNLOAD_SECONDS,
            check=False,
        )
        if decode.returncode != 0:
            raise RuntimeError("full decode rejected the downloaded canonical")
        validate_canonical_profile(
            facts,
            bmff_layout=bmff_layout,
            byte_length=artifact.byte_length,
            full_decode_passed=True,
        )
        return {
            "byte_length": artifact.byte_length,
            "sha256": digest,
            "duration_seconds": str(facts.duration_seconds),
            "moov_before_mdat": bmff_layout.moov_before_mdat,
            "fragmented": bmff_layout.fragmented,
            "full_decode": "pass",
        }
    finally:
        shutil.rmtree(download_directory, ignore_errors=True)


async def _prove_source_preserved(
    *,
    storage: Any,
    artifact: TrackArtifact,
    expected_bytes: bytes,
    work_directory: Path,
) -> dict[str, Any]:
    download_directory = Path(tempfile.mkdtemp(prefix="source-", dir=work_directory))
    try:
        destination = download_directory / "source.bin"
        await storage.download_verified_to_path_async(
            artifact.storage_object_key,
            destination,
            expected_length=len(expected_bytes),
            expected_sha256=_sha256_bytes(expected_bytes),
            max_bytes=len(expected_bytes),
        )
        if destination.read_bytes() != expected_bytes:
            raise RuntimeError("accepted source bytes changed")
        return {"byte_length": len(expected_bytes), "sha256": _sha256_bytes(expected_bytes)}
    finally:
        shutil.rmtree(download_directory, ignore_errors=True)


def _enable_download_observation(storage: Any) -> list[dict[str, Any]]:
    observed: list[dict[str, Any]] = []
    original_async = storage.download_verified_to_path_async
    original_sync = storage.download_verified_to_path

    async def wrapped_async(object_key: str, destination_path: Any, **kwargs: Any) -> int:
        observed.append(
            {
                "expected_length": kwargs.get("expected_length"),
                "expected_sha256": kwargs.get("expected_sha256"),
            }
        )
        return await original_async(object_key, destination_path, **kwargs)

    def wrapped_sync(object_key: str, destination_path: Any, **kwargs: Any) -> int:
        observed.append(
            {
                "expected_length": kwargs.get("expected_length"),
                "expected_sha256": kwargs.get("expected_sha256"),
            }
        )
        return original_sync(object_key, destination_path, **kwargs)

    storage.download_verified_to_path_async = wrapped_async
    storage.download_verified_to_path = wrapped_sync
    return observed


async def _range_check(
    client: httpx.AsyncClient,
    *,
    meeting_id: uuid.UUID,
    canonical_path: Path,
) -> dict[str, Any]:
    canonical = canonical_path.read_bytes()
    end = min(99, len(canonical) - 1)
    response = await client.get(
        f"/api/v1/cabinet/meetings/{meeting_id}/playback",
        headers={**_auth_headers(), "Range": f"bytes=0-{end}"},
    )
    if response.status_code != 206:
        raise RuntimeError(f"authorized Range returned HTTP {response.status_code}")
    expected_range = f"bytes 0-{end}/{len(canonical)}"
    if response.headers.get("Content-Range") != expected_range:
        raise RuntimeError("authorized Range returned an unexpected Content-Range")
    if response.content != canonical[: end + 1]:
        raise RuntimeError("authorized Range returned unexpected bytes")
    return {"status": 206, "content_range": expected_range}


async def _prepare_success_upload(
    *, client: httpx.AsyncClient, wav_bytes: bytes
) -> dict[str, Any]:
    return await _upload(
        client,
        filename="synthetic.wav",
        payload=wav_bytes,
        content_type="audio/wav",
        local_recording_id=f"f099-success-{uuid.uuid4().hex}",
    )


async def _observe_success_barrier(
    *,
    app: Any,
    media_sessionmaker: Any,
    payload: dict[str, Any],
) -> tuple[uuid.UUID, uuid.UUID, dict[str, str]]:
    meeting_id = uuid.UUID(payload["meeting"]["meeting_id"])
    revision_id = uuid.UUID(payload["upload_session"]["media_revision_id"])
    async with app.state.db_sessionmaker() as session:
        await apply_tenant_scope(session, SCOPE, context_kind="worker")
        jobs = list(
            (
                await session.execute(
                    select(PlaybackNormalizationJob).where(
                        PlaybackNormalizationJob.workspace_id == WORKSPACE_ID,
                        PlaybackNormalizationJob.media_revision_id == revision_id,
                    )
                )
            ).scalars()
        )
        canonical_count = await session.scalar(
            select(func.count())
            .select_from(TrackArtifact)
            .where(
                TrackArtifact.workspace_id == WORKSPACE_ID,
                TrackArtifact.media_revision_id == revision_id,
                TrackArtifact.track_role == "playback",
                TrackArtifact.status == "stored",
            )
        )
    if len(jobs) != 1:
        raise RuntimeError("accepted success source did not create exactly one durable job")
    if canonical_count:
        raise RuntimeError("canonical playback was exposed before worker processing")
    visibility = await _assert_media_tenant_visibility(media_sessionmaker, meeting_id)
    return meeting_id, revision_id, visibility


async def _run_success_scenario(
    *,
    client: httpx.AsyncClient,
    app: Any,
    storage: Any,
    observed_downloads: list[dict[str, Any]],
    ffmpeg: str,
    ffprobe: str,
    work_directory: Path,
    wav_bytes: bytes,
    meeting_id: uuid.UUID,
    revision_id: uuid.UUID,
) -> dict[str, Any]:
    started = time.monotonic()
    job = await _wait_job(app, revision_id, deadline=started + SCENARIO_SECONDS)
    if job.state != "ready" or job.canonical_track_artifact_id is None:
        raise RuntimeError(f"success source reached {job.state}/{job.reason_code}")

    async with app.state.db_sessionmaker() as session:
        await apply_tenant_scope(session, SCOPE, context_kind="worker")
        canonical = await session.get(TrackArtifact, job.canonical_track_artifact_id)
        attempts = list(
            (
                await session.execute(
                    select(PlaybackNormalizationAttempt).where(
                        PlaybackNormalizationAttempt.job_id == job.id
                    )
                )
            ).scalars()
        )
        source = await session.scalar(
            select(TrackArtifact).where(
                TrackArtifact.workspace_id == WORKSPACE_ID,
                TrackArtifact.media_revision_id == revision_id,
                TrackArtifact.track_role == "media",
                TrackArtifact.status == "stored",
            )
        )
    if canonical is None or canonical.track_role != "playback" or canonical.status != "stored":
        raise RuntimeError("canonical playback metadata is missing")
    if canonical.normalization_profile_version != PROFILE_VERSION or canonical.validated_at is None:
        raise RuntimeError("canonical playback was not validated")
    if canonical.media_revision_id != revision_id or canonical.meeting_id != meeting_id:
        raise RuntimeError("canonical playback lineage is incorrect")
    async with app.state.db_sessionmaker() as session:
        await apply_tenant_scope(session, SCOPE, context_kind="worker")
        validated_count = await session.scalar(
            select(func.count())
            .select_from(TrackArtifact)
            .where(
                TrackArtifact.workspace_id == WORKSPACE_ID,
                TrackArtifact.media_revision_id == revision_id,
                TrackArtifact.track_role == "playback",
                TrackArtifact.status == "stored",
                TrackArtifact.normalization_profile_version == PROFILE_VERSION,
                TrackArtifact.validated_at.is_not(None),
            )
        )
    if validated_count != 1:
        raise RuntimeError("success source did not produce exactly one validated playback")
    if len(attempts) != 1:
        raise RuntimeError("success source did not converge to exactly one attempt")
    published = [attempt for attempt in attempts if attempt.state == "published"]
    if len(published) != 1 or published[0].published_track_artifact_id != canonical.id:
        raise RuntimeError("canonical playback does not have exactly one published attempt")
    if not published[0].full_decode_passed or not published[0].moov_before_mdat:
        raise RuntimeError("published attempt did not pass decode/profile requirements")
    if source is None:
        raise RuntimeError("accepted source artifact is missing")
    if source.byte_length != len(wav_bytes) or source.sha256 != _sha256_bytes(wav_bytes):
        raise RuntimeError("accepted source metadata changed")
    if not any(item.get("expected_sha256") == source.sha256 for item in observed_downloads):
        raise RuntimeError("source was not downloaded through the verified-download helper")

    handle = app.state.temporal_client.get_workflow_handle(
        playback_normalization_workflow_id(revision_id)
    )
    while time.monotonic() < started + SCENARIO_SECONDS:
        description = await handle.describe()
        if description.status == WorkflowExecutionStatus.COMPLETED:
            break
        await asyncio.sleep(0.25)
    else:
        raise RuntimeError("normalization workflow did not complete")

    canonical_facts = await _prove_canonical(
        storage=storage,
        artifact=canonical,
        ffmpeg=ffmpeg,
        ffprobe=ffprobe,
        work_directory=work_directory,
    )
    source_facts = await _prove_source_preserved(
        storage=storage,
        artifact=source,
        expected_bytes=wav_bytes,
        work_directory=work_directory,
    )
    return {
        "name": "A-success-wav",
        "status": "pass",
        "job_state": job.state,
        "attempts": len(attempts),
        "published_attempts": len(published),
        "canonical": canonical_facts,
        "source": source_facts,
        "elapsed_seconds": round(time.monotonic() - started, 2),
        "_canonical_artifact_id": str(canonical.id),
        "_meeting_id": str(meeting_id),
    }


async def _run_corrupt_scenario(
    *,
    client: httpx.AsyncClient,
    app: Any,
    storage: Any,
    corrupt_bytes: bytes,
    work_directory: Path,
) -> dict[str, Any]:
    started = time.monotonic()
    payload = await _upload(
        client,
        filename="invalid.wav",
        payload=corrupt_bytes,
        content_type="audio/wav",
        local_recording_id=f"f099-corrupt-{uuid.uuid4().hex}",
    )
    revision_id = uuid.UUID(payload["upload_session"]["media_revision_id"])
    job = await _wait_job(app, revision_id, deadline=started + SCENARIO_SECONDS)
    async with app.state.db_sessionmaker() as session:
        await apply_tenant_scope(session, SCOPE, context_kind="worker")
        canonical_count = await session.scalar(
            select(func.count())
            .select_from(TrackArtifact)
            .where(
                TrackArtifact.workspace_id == WORKSPACE_ID,
                TrackArtifact.media_revision_id == revision_id,
                TrackArtifact.track_role == "playback",
            )
        )
        attempts = list(
            (
                await session.execute(
                    select(PlaybackNormalizationAttempt).where(
                        PlaybackNormalizationAttempt.job_id == job.id
                    )
                )
            ).scalars()
        )
        source = await session.scalar(
            select(TrackArtifact).where(
                TrackArtifact.workspace_id == WORKSPACE_ID,
                TrackArtifact.media_revision_id == revision_id,
                TrackArtifact.track_role == "media",
                TrackArtifact.status == "stored",
            )
        )
    if job.state != "terminal" or job.reason_code != "corrupt_source":
        raise RuntimeError(f"corrupt source reached {job.state}/{job.reason_code}")
    if job.next_attempt_at is not None:
        raise RuntimeError("corrupt source kept an automatic retry")
    if job.canonical_track_artifact_id is not None or canonical_count:
        raise RuntimeError("corrupt source exposed a canonical playback artifact")
    if any(attempt.state in {"uploaded", "published"} for attempt in attempts):
        raise RuntimeError("corrupt source published a normalization attempt")
    if source is None or source.byte_length != len(corrupt_bytes):
        raise RuntimeError("accepted corrupt source was not preserved")
    if source.sha256 != _sha256_bytes(corrupt_bytes):
        raise RuntimeError("accepted corrupt source digest changed")
    source_facts = await _prove_source_preserved(
        storage=storage,
        artifact=source,
        expected_bytes=corrupt_bytes,
        work_directory=work_directory,
    )
    for attempt in attempts:
        if await storage.object_exists_async(attempt.storage_object_key):
            raise RuntimeError("corrupt source left an unowned attempt object")
    return {
        "name": "A-corrupt-source",
        "status": "pass",
        "job_state": job.state,
        "reason_code": job.reason_code,
        "next_attempt_at": None,
        "canonical_artifacts": 0,
        "published_attempts": len([a for a in attempts if a.state == "published"]),
        "source": source_facts,
        "elapsed_seconds": round(time.monotonic() - started, 2),
    }


async def _run_acceptance(
    *,
    postgres_database_url: str,
    media_database_url: str,
) -> dict[str, Any]:
    work_directory = Path(str(LAUNCH["work_directory"]))
    result_file = Path(str(LAUNCH["result_file"]))
    token = str(LAUNCH["run_token"])
    ffmpeg = str(LAUNCH["ffmpeg_path"])
    ffprobe = str(LAUNCH["ffprobe_path"])
    minio = _start_minio()
    result: dict[str, Any] = {
        "schema_version": 1,
        "status": "fail",
        "run_token": token,
        "scenarios": [],
        "checks": {},
        "cleanup": {},
    }
    media_engine = None
    completed = False
    try:
        media_engine = create_async_engine(media_database_url, poolclass=NullPool)
        media_sessionmaker = async_sessionmaker(media_engine, expire_on_commit=False)
        result["checks"]["media_role"] = await _assert_media_role(media_sessionmaker)

        temporal_port = _free_port()
        async with await WorkflowEnvironment.start_local(
            dev_server_existing_path=str(LAUNCH["temporal_cli_path"]),
            ip="127.0.0.1",
            port=temporal_port,
            ui=False,
            dev_server_database_filename=None,
        ) as environment:
            normalization_work_directory = work_directory / "normalization"
            normalization_work_directory.mkdir(mode=0o700)
            settings = Settings(
                _env_file=None,
                env="development",
                database_url=postgres_database_url,
                minio_endpoint=minio["endpoint"],
                minio_access_key=minio["access_key"],
                minio_secret_key=minio["secret_key"],
                minio_bucket=minio["bucket"],
                minio_secure=False,
                temporal_address=f"127.0.0.1:{temporal_port}",
                temporal_namespace="default",
                playback_normalization_enabled=True,
                playback_normalization_automatic_dispatch_enabled=True,
                playback_normalization_task_queue=f"graf-f099-{token}",
                playback_normalization_work_directory=normalization_work_directory,
                playback_normalization_ffmpeg_path=Path(ffmpeg),
                playback_normalization_ffprobe_path=Path(ffprobe),
                processing_enabled=False,
                web_login_workspace_id=AUTH_BOOTSTRAP_WORKSPACE_ID,
            )
            app = create_app(settings)
            app.state.temporal_client = environment.client
            storage = app.state.storage
            await storage.ensure_bucket_async()
            observed_downloads = _enable_download_observation(storage)

            async def normalization(payload: dict[str, str]) -> dict[str, str]:
                return await run_playback_normalization_activity(
                    payload,
                    settings=settings,
                    sessionmaker=media_sessionmaker,
                    storage=storage,
                    temporal_client=environment.client,
                )

            normalization_activity = activity.defn(
                name="run_playback_normalization_activity"
            )(normalization)
            readiness_activity = activity.defn(
                name="playback_normalization_worker_readiness_activity"
            )(run_playback_normalization_readiness_activity)
            normalization_worker, readiness_worker = create_normalization_temporal_workers(
                client=environment.client,
                settings=settings,
                worker_identity=f"f099-real-{token}",
                normalization_activity=normalization_activity,
                readiness_activity=readiness_activity,
            )

            async with app.router.lifespan_context(app), httpx.AsyncClient(
                transport=httpx.ASGITransport(app=app),
                base_url="http://f099-acceptance.invalid",
                timeout=60,
            ) as client:
                wav_path = work_directory / "synthetic-source.wav"
                _create_wav(wav_path, ffmpeg)
                wav_bytes = wav_path.read_bytes()
                result["checks"]["synthetic_source_sha256"] = _sha256_bytes(wav_bytes)
                success_payload = await _prepare_success_upload(
                    client=client, wav_bytes=wav_bytes
                )
                success_meeting_id, success_revision_id, visibility = (
                    await _observe_success_barrier(
                        app=app,
                        media_sessionmaker=media_sessionmaker,
                        payload=success_payload,
                    )
                )
                result["checks"]["media_visibility"] = visibility
                async with normalization_worker, readiness_worker:
                    success = await _run_success_scenario(
                        client=client,
                        app=app,
                        storage=storage,
                        observed_downloads=observed_downloads,
                        ffmpeg=ffmpeg,
                        ffprobe=ffprobe,
                        work_directory=work_directory,
                        wav_bytes=wav_bytes,
                        meeting_id=success_meeting_id,
                        revision_id=success_revision_id,
                    )
                    canonical_artifact_id = success.pop("_canonical_artifact_id")
                    canonical_temporary = work_directory / "canonical-range.m4a"
                    async with app.state.db_sessionmaker() as session:
                        await apply_tenant_scope(session, SCOPE, context_kind="worker")
                        canonical = await session.get(
                            TrackArtifact, uuid.UUID(canonical_artifact_id)
                        )
                    if canonical is None:
                        raise RuntimeError("canonical artifact disappeared")
                    await storage.download_verified_to_path_async(
                        canonical.storage_object_key,
                        canonical_temporary,
                        expected_length=canonical.byte_length,
                        expected_sha256=canonical.sha256,
                        max_bytes=canonical.byte_length,
                    )
                    try:
                        success["range"] = await _range_check(
                            client,
                            meeting_id=success_meeting_id,
                            canonical_path=canonical_temporary,
                        )
                    finally:
                        canonical_temporary.unlink(missing_ok=True)
                    result["scenarios"].append(success)
                    result["scenarios"].append(
                        await _run_corrupt_scenario(
                            client=client,
                            app=app,
                            storage=storage,
                            corrupt_bytes=b"\x00",
                            work_directory=work_directory,
                        )
                    )
                    if list(normalization_work_directory.iterdir()):
                        raise RuntimeError("normalization work directory is not clean")
                    completed = True
    except Exception as error:
        result["failure_type"] = type(error).__name__
        result["failure_message"] = str(error)[:300]
        raise
    finally:
        try:
            result["cleanup"]["minio"] = _stop_minio(minio["container_id"])
        except Exception as error:  # noqa: BLE001 - cleanup failure is a FAIL receipt
            result["cleanup"]["minio"] = f"cleanup_error_{type(error).__name__}"
        if media_engine is not None:
            await media_engine.dispose()
        minio_clean = result["cleanup"].get("minio") in {"removed", "confirmed_absent"}
        if completed and minio_clean:
            result["status"] = "pass"
        _private_json(result_file, result)


def test_real_transport_acceptance(
    postgres_seeded_database_url: str,
    postgres_media_database_url: str,
) -> None:
    asyncio.run(
        _run_acceptance(
            postgres_database_url=postgres_seeded_database_url,
            media_database_url=postgres_media_database_url,
        )
    )
