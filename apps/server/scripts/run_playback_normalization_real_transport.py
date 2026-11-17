#!/usr/bin/env python3
"""Explicit, isolated supervisor for the F099 real-transport acceptance.

This file is intentionally standard-library only.  It composes the environment,
proves the admitted local dependencies, hands PostgreSQL resource ownership to
the existing test runner, enforces the process deadline and performs verified
cleanup after the child exits.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import signal
import stat
import subprocess
import sys
import tempfile
import threading
import time
from contextlib import suppress
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, NoReturn

POSTGRES_IMAGE = "postgres:17-alpine"
MINIO_IMAGE = "minio/minio:RELEASE.2025-05-24T17-08-30Z"
DEFAULT_TEMPORAL_CLI = Path("/opt/homebrew/bin/temporal")
TEMPORAL_CLI_SHA256 = "268711d469c0b8a981251d49c4f2150c7ae41665018800749b95ca44aa83593a"
TEMPORAL_VERSION_MARKERS = ("1.8.2", "Server 1.31.2")
WHOLE_RUN_SECONDS = 600
RESOURCE_OPERATION_SECONDS = 30
TERM_GRACE_SECONDS = 5
KILL_GRACE_SECONDS = 5
MINIMUM_FREE_BYTES = 7 * 1024 * 1024 * 1024
RESOURCE_LABEL = "pro.2brain.graf.f099.run"
CONTEXT_SCHEMA_VERSION = 1
ACCEPTANCE_PATH = "acceptance/playback_normalization_real_transport.py"
SERVER_RELATIVE_PATH = Path("apps/server")
TEST_RUNNER = "scripts/run_local_postgres_tests.sh"


def _fail(message: str) -> NoReturn:
    print(f"f099_real_transport: {message}", file=sys.stderr)
    raise SystemExit(2)


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        while chunk := source.read(1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def _utc_now() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat()


def _atomic_write_json(path: Path, payload: dict[str, Any], *, mode: int = 0o600) -> None:
    temporary = path.with_name(f"{path.name}.tmp.{os.getpid()}")
    descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, mode)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as output:
            json.dump(payload, output, ensure_ascii=True, sort_keys=True, separators=(",", ":"))
            output.write("\n")
        os.replace(temporary, path)
    finally:
        temporary.unlink(missing_ok=True)


def _read_json(path: Path) -> dict[str, Any]:
    metadata = path.lstat()
    if not stat.S_ISREG(metadata.st_mode) or stat.S_ISLNK(metadata.st_mode):
        _fail(f"expected a regular non-symlink file at {path.name}")
    if metadata.st_uid != os.geteuid():
        _fail(f"unexpected owner for {path.name}")
    if metadata.st_size > 65536:
        _fail(f"unexpected size for {path.name}")
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, json.JSONDecodeError):
        _fail(f"invalid JSON in {path.name}")
    if not isinstance(document, dict):
        _fail(f"invalid document shape in {path.name}")
    return document


def _private_directory(path: Path) -> Path:
    path.mkdir(mode=0o700, parents=True, exist_ok=True)
    metadata = path.lstat()
    if not stat.S_ISDIR(metadata.st_mode) or stat.S_ISLNK(metadata.st_mode):
        _fail(f"expected a real directory at {path}")
    if metadata.st_mode & 0o077:
        _fail(f"directory mode must be 0700 at {path}")
    if metadata.st_uid != os.geteuid():
        _fail(f"unexpected directory owner at {path}")
    return path


def _require_no_dotenv(repo_root: Path) -> None:
    for candidate in (repo_root / ".env", repo_root / SERVER_RELATIVE_PATH / ".env"):
        if os.path.lexists(candidate):
            _fail(f"refusing to run while {candidate.relative_to(repo_root)} exists")


def _resolve_docker_host() -> str:
    configured = os.environ.get("GRAF_F099_DOCKER_HOST") or os.environ.get("DOCKER_HOST")
    if not configured:
        _fail("set GRAF_F099_DOCKER_HOST to the verified local Docker unix socket")
    if not configured.startswith("unix://"):
        _fail("Docker must be addressed through a local unix socket")
    socket_path = Path(configured.removeprefix("unix://"))
    if not socket_path.is_absolute():
        _fail("Docker socket path must be absolute")
    try:
        metadata = socket_path.lstat()
    except OSError:
        _fail("Docker socket is unavailable")
    if not stat.S_ISSOCK(metadata.st_mode):
        _fail("Docker socket is not a unix socket")
    return configured


def _docker_environment(docker_host: str, docker_config: Path) -> dict[str, str]:
    return {
        "DOCKER_HOST": docker_host,
        "DOCKER_CONFIG": str(docker_config),
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
    }


def _run(
    arguments: list[str],
    *,
    environment: dict[str, str],
    timeout: int = RESOURCE_OPERATION_SECONDS,
    check: bool = True,
) -> subprocess.CompletedProcess[str]:
    try:
        completed = subprocess.run(
            arguments,
            stdin=subprocess.DEVNULL,
            capture_output=True,
            text=True,
            timeout=timeout,
            check=False,
            env=environment,
        )
    except subprocess.TimeoutExpired:
        _fail(f"command timed out: {arguments[0]}")
    if check and completed.returncode != 0:
        _fail(f"command failed: {arguments[0]}")
    return completed


def _image_id(docker: list[str], reference: str, environment: dict[str, str]) -> str:
    completed = _run(
        [*docker, "image", "inspect", "--format", "{{.Id}}", reference],
        environment=environment,
    )
    image_id = completed.stdout.strip()
    if not image_id.startswith("sha256:") or len(image_id) != 71:
        _fail(f"admitted image ID is invalid for {reference.split(':')[0]}")
    return image_id


def _container_identity(
    docker: list[str],
    reference: str,
    environment: dict[str, str],
) -> str | None:
    completed = _run(
        [
            *docker,
            "inspect",
            "--format",
            '{{.Id}}|{{.Name}}|{{index .Config.Labels "'
            + RESOURCE_LABEL
            + '"}}|{{.Image}}',
            reference,
        ],
        environment=environment,
        check=False,
    )
    if completed.returncode != 0:
        return None
    identity = completed.stdout.strip()
    return identity or None


def _exact_container_ids(
    docker: list[str],
    name: str,
    environment: dict[str, str],
) -> list[str]:
    completed = _run(
        [*docker, "ps", "-aq", "--no-trunc", "--filter", f"name=^/{name}$"],
        environment=environment,
    )
    return [line.strip() for line in completed.stdout.splitlines() if line.strip()]


def _remove_verified_container(
    docker: list[str],
    *,
    name: str,
    run_token: str,
    image_id: str,
    candidate_id: str | None,
    environment: dict[str, str],
) -> tuple[bool, str]:
    identity = None
    if candidate_id:
        identity = _container_identity(docker, candidate_id, environment)
    if identity is None:
        try:
            candidates = _exact_container_ids(docker, name, environment)
        except (subprocess.TimeoutExpired, OSError):
            return False, "lookup_failed"
        if not candidates:
            return True, "confirmed_absent"
        if len(candidates) != 1:
            return False, "ambiguous_lookup"
        candidate_id = candidates[0]
        identity = _container_identity(docker, candidate_id, environment)
    if identity is None:
        return False, "identity_unreadable"
    parts = identity.split("|")
    if len(parts) != 4:
        return False, "identity_malformed"
    actual_id, actual_name, actual_token, actual_image = parts
    if (
        actual_name != f"/{name}"
        or actual_token != run_token
        or actual_image != image_id
    ):
        return False, "foreign_or_mismatched_container"
    try:
        completed = _run(
            [*docker, "rm", "--force", "--volumes", actual_id],
            environment=environment,
            check=False,
        )
    except (subprocess.TimeoutExpired, OSError):
        return False, "remove_failed"
    if completed.returncode != 0:
        return False, "remove_failed"
    if _container_identity(docker, actual_id, environment) is not None:
        return False, "still_present_after_remove"
    try:
        remaining = _exact_container_ids(docker, name, environment)
    except (subprocess.TimeoutExpired, OSError):
        return False, "absence_lookup_failed"
    if remaining:
        return False, "name_still_present"
    return True, "removed"


def _terminate_process_group(process: subprocess.Popen[bytes]) -> None:
    if process.poll() is not None:
        return
    try:
        os.killpg(process.pid, signal.SIGTERM)
    except ProcessLookupError:
        return
    with suppress(subprocess.TimeoutExpired):
        process.wait(timeout=TERM_GRACE_SECONDS)
        return
    try:
        os.killpg(process.pid, signal.SIGKILL)
    except ProcessLookupError:
        return
    with suppress(subprocess.TimeoutExpired):
        process.wait(timeout=KILL_GRACE_SECONDS)


def _clean_environment(
    *,
    run_directory: Path,
    docker_host: str,
    docker_config: Path,
    server_root: Path,
    postgres_resource_dir: Path,
    acceptance_context: Path,
) -> dict[str, str]:
    temporary = _private_directory(run_directory / "tmp")
    environment = {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "HOME": os.environ["HOME"],
        "TMPDIR": str(temporary),
        "LANG": os.environ.get("LANG", "C.UTF-8"),
        "LC_ALL": os.environ.get("LC_ALL", os.environ.get("LANG", "C.UTF-8")),
        "DOCKER_HOST": docker_host,
        "DOCKER_CONFIG": str(docker_config),
        "UV_NO_ENV_FILE": "1",
        "UV_NO_CONFIG": "1",
        "UV_OFFLINE": "1",
        "UV_FROZEN": "1",
        "UV_PROJECT_ENVIRONMENT": str(server_root / ".venv"),
        "GRAF_TEST_POSTGRES_RESOURCE_DIR": str(postgres_resource_dir),
        "GRAF_F099_ACCEPTANCE_CONTEXT": str(acceptance_context),
        "GRAF_TEST_WORKERS": "1",
        "PYTHONHASHSEED": "0",
    }
    return environment


def _verify_frozen_dependencies(
    server_root: Path,
    environment: dict[str, str],
) -> None:
    python = server_root / ".venv" / "bin" / "python"
    if not python.is_file():
        _fail("apps/server/.venv is missing; prepare frozen dependencies explicitly")
    completed = subprocess.run(
        [
            str(python),
            "-c",
            "import pytest, temporalio, minio, gepa, asyncpg",
        ],
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
        env=environment,
    )
    if completed.returncode != 0:
        _fail("frozen test dependencies are incomplete; prepare them explicitly first")
    uv = shutil.which("uv")
    if uv is None:
        _fail("uv is required to run the existing PostgreSQL test runner")
    completed = subprocess.run(
        [
            uv,
            "run",
            "--no-sync",
            "--frozen",
            "--extra",
            "dev",
            "--extra",
            "evaluation",
            "python",
            "-c",
            "import pytest, temporalio, minio, gepa",
        ],
        cwd=server_root,
        stdin=subprocess.DEVNULL,
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
        env=environment,
    )
    if completed.returncode != 0:
        _fail("uv cannot run the frozen dependency set without installing packages")


def _verify_temporal(path: Path, environment: dict[str, str]) -> str:
    if not path.is_absolute() or not path.is_file() or not os.access(path, os.X_OK):
        _fail("temporal CLI must be an absolute executable path")
    digest = _sha256_file(path)
    if digest != TEMPORAL_CLI_SHA256:
        _fail("temporal CLI checksum does not match the admitted local binary")
    completed = _run([str(path), "--version"], environment=environment, timeout=30)
    if not all(marker in completed.stdout for marker in TEMPORAL_VERSION_MARKERS):
        _fail("temporal CLI version does not match the admitted local versions")
    return digest


def _verify_media_tool(configured: str | None, name: str, environment: dict[str, str]) -> tuple[Path, str, str]:
    candidate = configured or shutil.which(name)
    if not candidate:
        _fail(f"{name} is required")
    path = Path(candidate)
    if not path.is_absolute() or not path.is_file() or not os.access(path, os.X_OK):
        _fail(f"{name} must be an absolute executable path")
    completed = _run([str(path), "-version"], environment=environment, timeout=30)
    first_line = completed.stdout.splitlines()[0] if completed.stdout else ""
    if name not in first_line:
        _fail(f"{name} did not report a usable version")
    return path, _sha256_file(path), first_line


def _parse_arguments(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run the isolated F099 T014 real-transport acceptance.",
    )
    parser.add_argument(
        "--prepare-only",
        action="store_true",
        help="validate dependencies and write the run context without starting the child",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    arguments = _parse_arguments(sys.argv[1:] if argv is None else argv)
    repo_root = Path(__file__).resolve().parents[3]
    server_root = repo_root / SERVER_RELATIVE_PATH
    _require_no_dotenv(repo_root)

    docker_host = _resolve_docker_host()
    run_directory = Path(tempfile.mkdtemp(prefix="graf-f099-real-transport-"))
    os.chmod(run_directory, 0o700)
    docker_config = _private_directory(run_directory / "docker-config")
    docker_environment = _docker_environment(docker_host, docker_config)
    docker = [shutil.which("docker") or "/usr/bin/docker"]
    if not Path(docker[0]).is_file():
        _fail("docker CLI is unavailable")

    free_bytes = shutil.disk_usage(run_directory).free
    if free_bytes < MINIMUM_FREE_BYTES:
        _fail("insufficient free space for the acceptance work budget")

    _run([*docker, "info"], environment=docker_environment)
    postgres_image_id = _image_id(docker, POSTGRES_IMAGE, docker_environment)
    minio_image_id = _image_id(docker, MINIO_IMAGE, docker_environment)

    temporal_cli = Path(os.environ.get("GRAF_F099_TEMPORAL_CLI", DEFAULT_TEMPORAL_CLI))
    if str(temporal_cli) == str(DEFAULT_TEMPORAL_CLI) and not temporal_cli.exists():
        temporal_cli = Path(shutil.which("temporal") or DEFAULT_TEMPORAL_CLI)
    temporal_sha256 = _verify_temporal(temporal_cli, docker_environment)

    ffmpeg_path, ffmpeg_sha256, ffmpeg_version = _verify_media_tool(
        os.environ.get("GRAF_F099_FFMPEG"), "ffmpeg", docker_environment
    )
    ffprobe_path, ffprobe_sha256, ffprobe_version = _verify_media_tool(
        os.environ.get("GRAF_F099_FFPROBE"), "ffprobe", docker_environment
    )

    run_token = os.urandom(16).hex()
    postgres_resource_dir = _private_directory(run_directory / "postgres")
    work_directory = _private_directory(run_directory / "work")
    postgres_container = f"graf-postgres-test-f099-{run_token}"
    minio_container = f"graf-minio-test-f099-{run_token}"
    postgres_manifest = {
        "schema_version": CONTEXT_SCHEMA_VERSION,
        "run_token": run_token,
        "container_name": postgres_container,
        "image_id": postgres_image_id,
    }
    _atomic_write_json(
        postgres_resource_dir / "postgres-resource.json", postgres_manifest
    )
    postgres_receipt = run_directory / "postgres-resource-cleanup.json"
    _atomic_write_json(
        postgres_receipt,
        {
            **postgres_manifest,
            "state": "cleanup_required",
            "created_at": _utc_now(),
        },
    )
    acceptance_context = run_directory / "acceptance-context.json"
    result_file = work_directory / "acceptance-result.json"
    minio_resource = work_directory / "minio-resource.json"
    context = {
        "schema_version": CONTEXT_SCHEMA_VERSION,
        "run_token": run_token,
        "docker_host": docker_host,
        "postgres_image_id": postgres_image_id,
        "minio_image": MINIO_IMAGE,
        "minio_image_id": minio_image_id,
        "minio_container_name": minio_container,
        "temporal_cli_path": str(temporal_cli),
        "temporal_cli_sha256": temporal_sha256,
        "ffmpeg_path": str(ffmpeg_path),
        "ffmpeg_sha256": ffmpeg_sha256,
        "ffmpeg_version": ffmpeg_version,
        "ffprobe_path": str(ffprobe_path),
        "ffprobe_sha256": ffprobe_sha256,
        "ffprobe_version": ffprobe_version,
        "work_directory": str(work_directory),
        "result_file": str(result_file),
        "minio_resource_file": str(minio_resource),
        "whole_run_seconds": WHOLE_RUN_SECONDS,
    }
    _atomic_write_json(acceptance_context, context)

    environment = _clean_environment(
        run_directory=run_directory,
        docker_host=docker_host,
        docker_config=docker_config,
        server_root=server_root,
        postgres_resource_dir=postgres_resource_dir,
        acceptance_context=acceptance_context,
    )
    _verify_frozen_dependencies(server_root, environment)

    safe_receipt: dict[str, Any] = {
        "schema_version": CONTEXT_SCHEMA_VERSION,
        "run_token": run_token,
        "status": "not_started",
        "docker_host_kind": "unix_socket",
        "postgres_image_id": postgres_image_id,
        "minio_image_id": minio_image_id,
        "temporal_cli_sha256": temporal_sha256,
        "ffmpeg_sha256": ffmpeg_sha256,
        "ffprobe_sha256": ffprobe_sha256,
        "free_bytes_at_start": free_bytes,
        "started_at": _utc_now(),
    }
    supervisor_receipt = run_directory / "supervisor-result.json"

    if arguments.prepare_only:
        safe_receipt.update(status="prepared", finished_at=_utc_now())
        _atomic_write_json(supervisor_receipt, safe_receipt)
        print(json.dumps(safe_receipt, ensure_ascii=True, sort_keys=True))
        return 0

    child_environment = dict(environment)
    command = [
        "bash",
        str(server_root / TEST_RUNNER),
        "--focused",
        "-q",
        "-n",
        "0",
        ACCEPTANCE_PATH,
    ]
    process = subprocess.Popen(
        command,
        cwd=server_root,
        env=child_environment,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        start_new_session=True,
    )
    bootstrap_timed_out = False
    stop_monitor = threading.Event()

    def monitor_bootstrap() -> None:
        nonlocal bootstrap_timed_out
        state_file = postgres_resource_dir / "postgres-state.json"
        while not stop_monitor.wait(0.5):
            try:
                state = json.loads(state_file.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue
            if state.get("phase") != "starting":
                continue
            started_at = state.get("monotonic_ms")
            if not isinstance(started_at, int):
                continue
            if time.monotonic() * 1000 - started_at <= 60_000:
                continue
            bootstrap_timed_out = True
            try:
                os.killpg(process.pid, signal.SIGTERM)
            except ProcessLookupError:
                return
            time.sleep(TERM_GRACE_SECONDS)
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                return
            return

    monitor = threading.Thread(target=monitor_bootstrap, daemon=True)
    monitor.start()
    timed_out = False
    try:
        output, _ = process.communicate(timeout=WHOLE_RUN_SECONDS)
    except subprocess.TimeoutExpired:
        timed_out = True
        _terminate_process_group(process)
        output, _ = process.communicate()
    finally:
        stop_monitor.set()
        monitor.join(timeout=1)
    if output:
        sys.stdout.write(output.decode("utf-8", "replace"))
        sys.stdout.flush()

    postgres_cleanup: tuple[bool, str]
    postgres_state: dict[str, Any] = {}
    state_path = postgres_resource_dir / "postgres-state.json"
    if state_path.exists():
        try:
            postgres_state = _read_json(state_path)
        except SystemExit:
            postgres_state = {}
    candidate_id = postgres_state.get("container_id") if isinstance(postgres_state.get("container_id"), str) else None
    cid_path = postgres_resource_dir / "postgres.cid"
    if candidate_id is None and cid_path.is_file() and not cid_path.is_symlink():
        cid_text = cid_path.read_text(encoding="utf-8", errors="ignore").strip()
        if cid_text and "\n" not in cid_text:
            candidate_id = cid_text
    postgres_cleanup = _remove_verified_container(
        docker,
        name=postgres_container,
        run_token=run_token,
        image_id=postgres_image_id,
        candidate_id=candidate_id,
        environment=docker_environment,
    )

    minio_cleanup: tuple[bool, str] = (True, "not_started")
    if minio_resource.exists():
        try:
            minio_state = _read_json(minio_resource)
        except SystemExit:
            minio_state = {}
        minio_candidate = minio_state.get("container_id")
        minio_cleanup = _remove_verified_container(
            docker,
            name=minio_container,
            run_token=run_token,
            image_id=minio_image_id,
            candidate_id=minio_candidate if isinstance(minio_candidate, str) else None,
            environment=docker_environment,
        )

    acceptance_status = "missing"
    acceptance_summary: dict[str, Any] = {}
    if result_file.exists():
        try:
            acceptance_summary = _read_json(result_file)
        except SystemExit:
            acceptance_summary = {}
        acceptance_status = str(acceptance_summary.get("status", "invalid"))

    cleanup_clean = postgres_cleanup[0] and minio_cleanup[0]
    _atomic_write_json(
        postgres_receipt,
        {
            **postgres_manifest,
            "state": "clean" if postgres_cleanup[0] else "cleanup_required",
            "result": postgres_cleanup[1],
            "updated_at": _utc_now(),
        },
    )
    safe_receipt.update(
        {
            "status": "pass"
            if process.returncode == 0
            and not timed_out
            and acceptance_status == "pass"
            and cleanup_clean
            else "fail",
            "child_exit_code": process.returncode,
            "timed_out": timed_out or bootstrap_timed_out,
            "bootstrap_timed_out": bootstrap_timed_out,
            "acceptance_status": acceptance_status,
            "postgres_cleanup": postgres_cleanup[1],
            "minio_cleanup": minio_cleanup[1],
            "scenario_count": len(acceptance_summary.get("scenarios", []))
            if isinstance(acceptance_summary.get("scenarios"), list)
            else 0,
            "finished_at": _utc_now(),
        }
    )
    _atomic_write_json(supervisor_receipt, safe_receipt)
    shutil.rmtree(work_directory, ignore_errors=True)
    print(json.dumps(safe_receipt, ensure_ascii=True, sort_keys=True))
    if safe_receipt["status"] != "pass":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
