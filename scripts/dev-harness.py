#!/usr/bin/env python3
"""Single-target GRAF Dev harness with a metadata-only default.

Without ``--live`` this module deliberately does not build containers, mutate
application data, or call services.  The explicit live flag enables only the
loopback GRAF adapter below, which reuses the repository's existing scripts.
"""

from __future__ import annotations

import argparse
import contextlib
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import re
import signal
import shutil
import subprocess
import sys
import tempfile
import time
from typing import Any, Dict, Iterator, Optional
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import Request, urlopen

try:
    import fcntl  # type: ignore
except ImportError:  # pragma: no cover - Windows consumers use process mutexes.
    fcntl = None


SHA_RE = re.compile(r"^[0-9a-fA-F]{40}$")
MANIFEST_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{0,127}$")
APP_BUNDLE_ID = "pro.2brain.graf.dev"
APP_CHANNEL = "dev"
PRODUCTION_APP_PATH = Path("/Applications/GRAF.app")
SCHEMA_VERSION = "dev-manifest.v1"
POINTER_VERSION = "dev-active-pointer.v1"
PROCESS_STOP_TIMEOUT_SECONDS = 10
PROBE_RETRY_DELAY_SECONDS = 0.2
MANIFEST_FIELDS = {
    "schema_version", "manifest_id", "feature_id", "source_sha", "components",
    "migration_head", "app_identity", "operator", "created_at", "promoted_at",
    "parent_manifest_id", "status", "health", "dev_boundary",
}
COMPONENT_FIELDS = {"source_sha", "version", "digest"}
APP_IDENTITY_FIELDS = {
    "bundle_id", "channel", "signing_identity", "designated_requirement",
    "entitlements_digest", "update_trust",
}
HEALTH_FIELDS = {"result", "checked_at", "checks"}
BOUNDARY_FIELDS = {"environment", "backend_origin", "frontend_origin", "data_root"}
MANIFEST_STATUSES = {"ready", "promoting", "active", "degraded", "rollback_required", "blocked"}
SENSITIVE_KEY_RE = re.compile(
    r"(?:api[_-]?key|access[_-]?token|refresh[_-]?token|password|secret|credential|"
    r"private[_-]?key|raw[_-]?transcript|transcript[_-]?text|signed[_-]?url)",
    re.IGNORECASE,
)
# GRAF's current frontend is server-rendered by the backend.  Keep a separate
# manifest field for a future split frontend, but do not invent a second local
# server in the adapter.
DEFAULT_BACKEND_ORIGIN = "http://127.0.0.1:8081"
DEFAULT_FRONTEND_ORIGIN = DEFAULT_BACKEND_ORIGIN


class HarnessError(RuntimeError):
    """An expected, safe-to-report harness failure."""


def now() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _active_feature_id() -> str:
    """Resolve the feature identity from the explicit per-worktree pointer."""
    pointer = _repo_root() / ".specify" / "feature.json"
    if not pointer.exists():
        raise HarnessError(
            "feature id is required: pass --feature-id or GRAF_FEATURE_ID; "
            "no .specify/feature.json active pointer exists"
        )
    try:
        payload = json.loads(pointer.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise HarnessError(f"cannot read active feature pointer {pointer}: {exc}") from exc
    if not isinstance(payload, dict):
        raise HarnessError("active feature pointer must be a JSON object")
    feature_id = str(payload.get("feature_id", "")).strip()
    if not re.fullmatch(r"\d{3,}", feature_id) or int(feature_id) == 0:
        raise HarnessError("active feature pointer has no valid non-zero feature_id")
    return feature_id


def state_dir(*, live: bool = False) -> Path:
    raw = os.environ.get("GRAF_DEV_STATE_DIR")
    if live and raw:
        raise HarnessError(
            "live Dev operations cannot override the repository-global state directory; "
            "unset GRAF_DEV_STATE_DIR and use the canonical single Dev target"
        )
    if raw:
        path = Path(raw).expanduser()
    else:
        # All worktrees of this repository share one machine-local state and
        # lock because they also share one loopback runtime and one installed
        # /Applications/GRAF Dev.app.  The identity is derived from Git's
        # common metadata directory, never from the physical worktree name.
        # Tests and operators can still inject an explicit state directory
        # through GRAF_DEV_STATE_DIR.
        base = Path.home() / ("Library/Application Support" if sys.platform == "darwin" else ".cache") / "GRAF Dev"
        path = base / _repository_identity() / "harness"
    path = path.resolve()
    lowered = str(path).lower()
    canonical = Path(os.path.realpath(path))
    production = Path(os.path.realpath(PRODUCTION_APP_PATH))
    if any(token in lowered for token in ("production", "prod-data", "prod_data")):
        raise HarnessError("Refusing a production-looking Dev state path: " + str(path))
    if canonical == production or production in canonical.parents:
        raise HarnessError("Dev state path cannot be inside the production GRAF.app: " + str(path))
    if path == Path("/") or path == Path.home():
        raise HarnessError("Dev state path is too broad: " + str(path))
    return path


def _repository_identity() -> str:
    """Return one stable, non-sensitive identity shared by linked worktrees."""
    root = _repo_root()
    try:
        common = subprocess.run(
            ["git", "rev-parse", "--git-common-dir"],
            cwd=root,
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
        common_path = Path(common)
        if not common_path.is_absolute():
            common_path = root / common_path
        common_path = common_path.resolve()
        label = common_path.parent.name or "repository"
        suffix = hashlib.sha256(str(common_path).encode("utf-8")).hexdigest()[:12]
        return f"{_safe_id(label, 'repository')}-{suffix}"
    except (OSError, subprocess.CalledProcessError, HarnessError) as exc:
        # A real live operation must never silently fall back to the physical
        # worktree name: that would split the supposedly single Dev target.
        raise HarnessError(
            "cannot resolve the repository-global Git metadata directory; "
            "refusing to derive Dev state from the physical worktree"
        ) from exc


def _assert_dev_environment() -> None:
    values = [
        os.environ.get(k, "").strip().lower()
        for k in ("GRAF_ENV", "APP_ENV", "ENVIRONMENT", "TWOBRAIN_ENV")
    ]
    if any(value in {"production", "prod", "staging"} for value in values):
        raise HarnessError("Dev harness refuses production or staging environment variables")
    for key in ("GRAF_BACKEND_ORIGIN", "GRAF_FRONTEND_ORIGIN"):
        value = os.environ.get(key, "")
        if value and not _is_loopback_origin(value):
            raise HarnessError(f"{key} must be a loopback origin, got {value!r}")


def _is_loopback_origin(value: str) -> bool:
    # Keep the manifest contract identical to build-dev-app.sh: the current
    # macOS adapter accepts only HTTP IPv4/localhost loopback origins.
    return bool(re.match(r"^http://(localhost|127\.0\.0\.1):[0-9]{1,5}$", value))


def _safe_id(value: str, label: str = "identifier") -> str:
    if not MANIFEST_RE.fullmatch(value):
        raise HarnessError(f"Invalid {label}: {value!r}")
    return value


def _sha(value: str) -> str:
    if not SHA_RE.fullmatch(value):
        raise HarnessError("source SHA must be exactly 40 hexadecimal characters")
    return value.lower()


def _digest(value: str) -> str:
    return "sha256:" + hashlib.sha256(value.encode("utf-8")).hexdigest()


def _configured_signing_identity() -> str:
    """Resolve the one signing identity accepted by the Dev build contract."""
    primary = os.environ.get("GRAF_DEV_SIGNING_IDENTITY", "").strip()
    legacy = os.environ.get("GRAF_DEV_SIGN_IDENTITY", "").strip()
    if primary and legacy and primary != legacy:
        raise HarnessError(
            "GRAF_DEV_SIGNING_IDENTITY and GRAF_DEV_SIGN_IDENTITY disagree; "
            "use one signing identity"
        )
    return primary or legacy or "GRAF Local Code Signing"


def _tree_digest(path: Path) -> str:
    """Return a deterministic digest for a built artifact without its contents in evidence."""
    if not path.exists():
        raise HarnessError(f"artifact does not exist: {path}")
    digest = hashlib.sha256()
    if path.is_file():
        digest.update(path.name.encode("utf-8"))
        digest.update(b"\0")
        digest.update(path.read_bytes())
    else:
        for child in sorted(path.rglob("*")):
            relative = child.relative_to(path).as_posix()
            digest.update(relative.encode("utf-8"))
            digest.update(b"\0")
            if child.is_symlink():
                digest.update(os.readlink(child).encode("utf-8"))
            elif child.is_file():
                digest.update(child.read_bytes())
            digest.update(b"\0")
    return "sha256:" + digest.hexdigest()


def _run_command(command: list[str], *, cwd: Path, env: Optional[Dict[str, str]] = None) -> str:
    """Run one adapter command and expose only a bounded, safe failure message."""
    try:
        completed = subprocess.run(
            command,
            cwd=str(cwd),
            env=env,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
    except OSError as exc:
        raise HarnessError(f"adapter command unavailable ({command[0]}): {exc}") from exc
    if completed.returncode:
        raise HarnessError(
            f"adapter command failed ({command[0]}), exit={completed.returncode}"
        )
    return completed.stdout.strip()


def _resolve_migration_head(root: Path) -> str:
    """Resolve the current Alembic graph head for a real GRAF checkout.

    Metadata-only fixture roots intentionally have no server migration config
    and retain ``unknown`` until an adapter supplies a value.  A real checkout
    must never make the operator copy a guessed revision into the manifest.
    """
    configured = os.environ.get("GRAF_DEV_MIGRATION_HEAD", "").strip()
    if configured and configured.lower() != "unknown":
        return configured
    server_root = root / "apps" / "server"
    if not (server_root / "alembic.ini").is_file():
        return "unknown"
    try:
        output = _run_command(["uv", "run", "alembic", "heads"], cwd=server_root)
    except HarnessError as exc:
        raise HarnessError(f"cannot resolve Dev migration head: {exc}") from exc
    heads = sorted(
        {
            match.group(1)
            for match in re.finditer(r"^\s*([A-Za-z0-9_-]+)\s+\(head\)\s*$", output, re.MULTILINE)
        }
    )
    if not heads:
        raise HarnessError("cannot resolve Dev migration head: Alembic returned no heads")
    return ",".join(heads)


def _run_command_combined(command: list[str], *, cwd: Path, env: Optional[Dict[str, str]] = None) -> str:
    """Run a command whose diagnostic contract is emitted on stderr."""
    try:
        completed = subprocess.run(
            command,
            cwd=str(cwd),
            env=env,
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
    except OSError as exc:
        raise HarnessError(f"adapter command unavailable ({command[0]}): {exc}") from exc
    if completed.returncode:
        raise HarnessError(
            f"adapter command failed ({command[0]}), exit={completed.returncode}"
        )
    return completed.stdout.strip()


def _origin_parts(origin: str) -> tuple[str, int]:
    parsed = urlsplit(origin)
    if parsed.scheme not in {"http", "https"} or parsed.hostname not in {
        "localhost",
        "127.0.0.1",
        "::1",
    }:
        raise HarnessError(f"origin is not loopback: {origin}")
    try:
        port = parsed.port
    except ValueError as exc:
        raise HarnessError(f"origin has invalid port: {origin}") from exc
    if port is None:
        port = 443 if parsed.scheme == "https" else 80
    return parsed.hostname, port


class GrafLocalAdapter:
    """Thin, explicit-opt-in adapter for GRAF's existing local runtime scripts."""

    def __init__(self, root: Path, state: Path):
        self.root = root
        self.state = state
        self.compose_file = root / "infra" / "docker-compose.local.yml"
        self.start_script = root / "infra" / "scripts" / "start-local.sh"
        self.build_app_script = root / "apps" / "macos" / "Scripts" / "build-dev-app.sh"
        self.install_app_script = root / "apps" / "macos" / "Scripts" / "install-dev-app.sh"

    def _env(self, manifest: Dict[str, Any]) -> Dict[str, str]:
        boundary = manifest["dev_boundary"]
        backend = str(boundary["backend_origin"])
        frontend = str(boundary["frontend_origin"])
        _origin_parts(backend)
        _origin_parts(frontend)
        if frontend != backend:
            raise HarnessError(
                "current GRAF adapter supports the server-rendered frontend on the backend origin"
            )
        env = os.environ.copy()
        # Start from a scrubbed operator environment.  Explicit development
        # values are added below, so a production TWOBRAIN_* secret cannot
        # survive merely because it has a name not covered by the old allowlist.
        for key in tuple(env):
            if key.startswith("TWOBRAIN_") or any(
                marker in key
                for marker in ("API_KEY", "TOKEN", "PASSWORD_FILE", "SECRET_FILE", "CREDENTIAL_FILE", "GITHUB_TOKEN")
            ):
                env.pop(key, None)
        env.update(
            {
                "GRAF_BACKEND_ORIGIN": backend,
                "GRAF_FRONTEND_ORIGIN": frontend,
                "GRAF_DEV_ORIGIN": backend,
                "GRAF_DEV_SOURCE_SHA": str(manifest["source_sha"]),
                "GRAF_DEV_MANIFEST_ID": str(manifest["manifest_id"]),
                "TWOBRAIN_ENV": "development",
                "TWOBRAIN_PUBLIC_BASE_URL": backend,
                "TWOBRAIN_DATABASE_URL": "postgresql+asyncpg://twobrain_rec:twobrain_rec@127.0.0.1:54330/twobrain_rec",
                "TWOBRAIN_MINIO_ENDPOINT": "127.0.0.1:9010",
                "TWOBRAIN_MINIO_ACCESS_KEY": "twobrain_rec",
                "TWOBRAIN_MINIO_SECRET_KEY": "twobrain_rec_dev_secret",
                "TWOBRAIN_MINIO_BUCKET": "twobrain-rec-ingest",
                "TWOBRAIN_MINIO_SECURE": "false",
                "TWOBRAIN_TEMPORAL_ADDRESS": "127.0.0.1:7233",
                "TWOBRAIN_PROCESSING_ENABLED": "true",
                "TWOBRAIN_OUTCOME_GENERATION_ENABLED": "false",
                "TWOBRAIN_BILLING_CHECKOUT_ENABLED": "false",
                "TWOBRAIN_PRODUCT_ANALYTICS_ENABLED": "false",
                "TWOBRAIN_PUBLIC_ANALYTICS_ENABLED": "false",
            }
        )
        # Credentials belong to the repository-global Dev state, not to a
        # disposable source worktree.  Every promoted SHA must use the same
        # encryption key while the shared Dev database remains in place.
        env["GRAF_CREDENTIAL_ENCRYPTION_KEY_FILE"] = str(
            self.state / "credentials" / "graf_credential_encryption_key"
        )
        host, port = _origin_parts(backend)
        env["TWOBRAIN_API_HOST"] = host
        env["TWOBRAIN_API_PORT"] = str(port)
        return env

    def _assert_supported(self) -> None:
        if sys.platform != "darwin":
            raise HarnessError("live GRAF adapter requires macOS for the signed Dev app")
        for path in (self.compose_file, self.start_script, self.build_app_script, self.install_app_script):
            if not path.is_file():
                raise HarnessError(f"GRAF adapter input is missing: {path}")

    def _assert_source_matches_checkout(self, manifest: Dict[str, Any]) -> None:
        current_sha = _run_command(["git", "rev-parse", "HEAD"], cwd=self.root)
        if _sha(current_sha) != _sha(str(manifest["source_sha"])):
            raise HarnessError(
                "live adapter requires candidate source_sha to equal the checked-out HEAD"
            )
        if _run_command(["git", "status", "--porcelain", "--untracked-files=all"], cwd=self.root):
            raise HarnessError("live adapter requires a clean checkout; commit or stash local changes first")

    def _compose_config(self, env: Dict[str, str]) -> None:
        _run_command(
            ["docker", "compose", "-f", str(self.compose_file), "config", "--quiet"],
            cwd=self.root,
            env=env,
        )

    def build(self, manifest: Dict[str, Any]) -> Dict[str, str]:
        self._assert_supported()
        self._assert_source_matches_checkout(manifest)
        env = self._env(manifest)
        self._compose_config(env)
        _run_command(
            ["uv", "run", "python", "-c", "import twobrain_rec_server"],
            cwd=self.root / "apps" / "server",
            env=env,
        )
        artifact_root = self.state / "artifacts" / str(manifest["manifest_id"])
        build_dir = artifact_root / "build"
        app_bundle = artifact_root / "GRAF Dev.app"
        artifact_root.mkdir(parents=True, exist_ok=True)
        env.update(
            {
                "GRAF_DEV_BUILD_DIR": str(build_dir),
                "GRAF_DEV_APP_BUNDLE": str(app_bundle),
            }
        )
        _run_command(["sh", str(self.build_app_script)], cwd=self.root, env=env)
        if not app_bundle.is_dir():
            raise HarnessError("GRAF Dev builder did not produce GRAF Dev.app")
        signing_identity, designated_requirement, entitlements_digest = self._measure_signed_app_identity(app_bundle)
        manifest["app_identity"].update(
            {
                "signing_identity": signing_identity,
                "designated_requirement": designated_requirement,
                "entitlements_digest": entitlements_digest,
            }
        )
        manifest["components"]["macos_app"]["digest"] = _tree_digest(app_bundle)
        return {"mode": "live", "app_bundle_digest": manifest["components"]["macos_app"]["digest"]}

    def _measure_signed_app_identity(self, app_bundle: Path) -> tuple[str, str, str]:
        """Read signing facts from the final bundle, never from configuration."""
        details = _run_command_combined(
            ["codesign", "-dv", "--verbose=4", str(app_bundle)], cwd=self.root
        )
        authorities = re.findall(r"^Authority=(.+)$", details, re.MULTILINE)
        if not authorities or not authorities[0].strip():
            raise HarnessError("signed Dev app has no codesign authority")
        requirement_output = _run_command_combined(
            ["codesign", "-dr", "-", str(app_bundle)], cwd=self.root
        )
        requirement_match = re.search(r"^designated => (.+)$", requirement_output, re.MULTILINE)
        if not requirement_match or not requirement_match.group(1).strip():
            raise HarnessError("signed Dev app has no designated requirement")
        entitlements = _run_command(
            ["codesign", "-d", "--entitlements", "-", "--xml", str(app_bundle)], cwd=self.root
        )
        if "<plist" not in entitlements:
            raise HarnessError("signed Dev app has no readable entitlements")
        return authorities[0].strip(), requirement_match.group(1).strip(), _digest(entitlements)

    def _runtime_record(self) -> Path:
        return self.state / "runtime.json"

    def _pid_alive(self, pid: int) -> bool:
        try:
            os.kill(pid, 0)
        except (OSError, ProcessLookupError):
            return False
        return True

    def _pid_owned(self, record: Dict[str, Any]) -> bool:
        """Only signal a process whose command and start identity we recorded."""
        pid = record.get("pid")
        command = record.get("command")
        start_token = record.get("start_token")
        if (
            not isinstance(pid, int)
            or not isinstance(command, str)
            or not command
            or not isinstance(start_token, str)
            or not start_token
        ):
            return False
        try:
            observed = subprocess.check_output(
                ["ps", "-p", str(pid), "-o", "command="], text=True, stderr=subprocess.DEVNULL
            ).strip()
            observed_start = subprocess.check_output(
                ["ps", "-p", str(pid), "-o", "lstart="], text=True, stderr=subprocess.DEVNULL
            ).strip()
        except (OSError, subprocess.CalledProcessError):
            return False
        return command in observed and observed_start == start_token

    def _process_command(self, pid: int) -> str:
        try:
            command = subprocess.check_output(
                ["ps", "-p", str(pid), "-o", "command="],
                text=True,
                stderr=subprocess.DEVNULL,
            ).strip()
        except (OSError, subprocess.CalledProcessError) as exc:
            raise HarnessError(f"could not prove Dev backend command for pid {pid}") from exc
        if not command:
            raise HarnessError(f"Dev backend pid {pid} has no process command")
        return command

    def _process_start_token(self, pid: int) -> str:
        try:
            token = subprocess.check_output(
                ["ps", "-p", str(pid), "-o", "lstart="],
                text=True,
                stderr=subprocess.DEVNULL,
            ).strip()
        except (OSError, subprocess.CalledProcessError) as exc:
            raise HarnessError(f"could not prove Dev backend start time for pid {pid}") from exc
        if not token:
            raise HarnessError(f"Dev backend pid {pid} has no process start identity")
        return token

    def _process_command(self, pid: int) -> str:
        """Capture the post-exec command used for ownership checks."""
        try:
            command = subprocess.check_output(
                ["ps", "-p", str(pid), "-o", "command="],
                text=True,
                stderr=subprocess.DEVNULL,
            ).strip()
        except (OSError, subprocess.CalledProcessError) as exc:
            raise HarnessError(f"could not prove Dev backend command for pid {pid}") from exc
        if not command:
            raise HarnessError(f"Dev backend pid {pid} has no process command")
        return command

    def _stop_previous(self) -> None:
        if not self._runtime_record().exists():
            return
        record = _read_json(self._runtime_record())
        pid = record.get("pid")
        if not isinstance(pid, int) or not self._pid_alive(pid):
            return
        if not self._pid_owned(record):
            raise HarnessError(f"refusing to terminate unverified Dev backend pid {pid}")
        try:
            os.kill(pid, signal.SIGTERM)
        except OSError:
            return
        deadline = time.monotonic() + PROCESS_STOP_TIMEOUT_SECONDS
        while self._pid_alive(pid) and time.monotonic() < deadline:
            time.sleep(PROBE_RETRY_DELAY_SECONDS)
        if self._pid_alive(pid):
            raise HarnessError(
                f"previous Dev backend pid {pid} did not exit after SIGTERM; refusing to start another"
            )

    def _runtime_is_live(self, record: Optional[Dict[str, Any]]) -> bool:
        if not isinstance(record, dict):
            return False
        pid = record.get("pid")
        return isinstance(pid, int) and self._pid_alive(pid) and self._pid_owned(record)

    def _start_backend(self, manifest: Dict[str, Any], env: Dict[str, str]) -> None:
        runtime = self._runtime_record()
        log_path = self.state / "logs" / "backend.log"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        log_handle = log_path.open("a", encoding="utf-8")
        try:
            process = subprocess.Popen(
                ["sh", str(self.start_script)],
                cwd=str(self.root),
                env=env,
                stdout=log_handle,
                stderr=subprocess.STDOUT,
                start_new_session=True,
            )
        except OSError as exc:
            log_handle.close()
            raise HarnessError(f"could not start local backend: {exc}") from exc
        finally:
            log_handle.close()
        try:
            self._wait_http(str(manifest["dev_boundary"]["backend_origin"]), "/api/v1/health/live", timeout=90)
        except HarnessError:
            with contextlib.suppress(OSError):
                os.kill(process.pid, signal.SIGTERM)
            raise
        # start-local.sh execs uvicorn. Wait for the health endpoint first,
        # then record the post-exec command and start token. Writing the
        # transient shell identity here would make a healthy runtime appear
        # unowned as soon as the wrapper replaces itself.
        _write_json(
            runtime,
            {
                "pid": process.pid,
                "source_sha": manifest["source_sha"],
                "started_at": now(),
                "command": self._process_command(process.pid),
                "start_token": self._process_start_token(process.pid),
            },
        )

    def _ensure_backend(self, manifest: Dict[str, Any], env: Dict[str, str]) -> None:
        runtime = self._runtime_record()
        if runtime.exists():
            record = _read_json(runtime)
            if record.get("source_sha") == manifest["source_sha"] and isinstance(record.get("pid"), int):
                if self._pid_alive(record["pid"]):
                    return
        self._stop_previous()
        self._start_backend(manifest, env)

    def _install_app(self, manifest: Dict[str, Any], env: Dict[str, str]) -> None:
        env = dict(env)
        env["GRAF_DEV_INSTALL_PATH"] = os.environ.get("GRAF_DEV_INSTALL_PATH", "/Applications/GRAF Dev.app")
        app_bundle = self.state / "artifacts" / str(manifest["manifest_id"]) / "GRAF Dev.app"
        if not app_bundle.is_dir():
            raise HarnessError("live promote requires the exact app bundle produced by live build")
        expected_digest = str(manifest["components"]["macos_app"]["digest"])
        actual_digest = _tree_digest(app_bundle)
        if actual_digest != expected_digest:
            raise HarnessError("live promote app bundle digest does not match the manifest")
        env["GRAF_DEV_APP_SOURCE_BUNDLE"] = str(app_bundle)
        _run_command(["sh", str(self.install_app_script)], cwd=self.root, env=env)

    def _snapshot_app(self) -> Optional[Path]:
        destination = Path(os.environ.get("GRAF_DEV_INSTALL_PATH", "/Applications/GRAF Dev.app"))
        self._assert_dev_app_destination(destination)
        if not destination.exists():
            return None
        backup = self.state / "transactions" / f"previous-{os.getpid()}-{int(time.time() * 1000)}.app"
        backup.parent.mkdir(parents=True, exist_ok=True)
        # Keep the original in place so install-dev-app.sh can still compare
        # designated requirements before replacing it.  The copy is a local
        # rollback snapshot, never evidence or application data.
        shutil.copytree(destination, backup, symlinks=True)
        return backup

    @staticmethod
    def _assert_dev_app_destination(destination: Path) -> None:
        """Reject production app paths before reading or mutating them."""
        canonical = Path(os.path.realpath(destination))
        production = Path(os.path.realpath(PRODUCTION_APP_PATH))
        if destination.name != "GRAF Dev.app":
            raise HarnessError("Dev destination must end in GRAF Dev.app")
        if canonical == production or production in canonical.parents:
            raise HarnessError("Dev destination cannot be the production GRAF.app or a child path")

    def _restore_app(self, backup: Optional[Path]) -> None:
        destination = Path(os.environ.get("GRAF_DEV_INSTALL_PATH", "/Applications/GRAF Dev.app"))
        if destination.exists():
            if destination.is_dir() and not destination.is_symlink():
                shutil.rmtree(destination)
            else:
                destination.unlink()
        if backup is not None:
            shutil.copytree(backup, destination, symlinks=True)
            shutil.rmtree(backup)

    def _restore_runtime(
        self,
        previous: Optional[Dict[str, Any]],
        previous_manifest: Optional[Dict[str, Any]],
        previous_was_live: bool,
    ) -> None:
        runtime = self._runtime_record()
        if runtime.exists():
            current = _read_json(runtime)
            pid = current.get("pid")
            if isinstance(pid, int) and self._pid_alive(pid):
                if not self._pid_owned(current):
                    raise HarnessError(f"refusing to restore over unverified Dev backend pid {pid}")
                self._stop_previous()
        if previous_was_live:
            if previous_manifest is None:
                raise HarnessError("cannot restore live Dev backend without its previous manifest")
            with self._adapter_for_manifest(previous_manifest) as adapter:
                adapter._start_backend(previous_manifest, adapter._env(previous_manifest))
        elif previous is None:
            with contextlib.suppress(FileNotFoundError):
                runtime.unlink()
        else:
            _write_json(runtime, previous)

    @contextlib.contextmanager
    def _adapter_for_manifest(self, manifest: Dict[str, Any]) -> Iterator["GrafLocalAdapter"]:
        """Run a target SHA from its own checkout, never from another feature."""
        target_sha = _sha(str(manifest["source_sha"]))
        # Unit/integration adapters may deliberately use a temporary fixture
        # root with mocked source checks.  There is no checkout to materialize
        # there; preserve the test double and let its explicit source guard
        # decide.  A real GRAF checkout always reaches the worktree path below
        # (or fails closed through _assert_source_matches_checkout).
        try:
            current_sha = _run_command(["git", "rev-parse", "HEAD"], cwd=self.root)
        except HarnessError:
            yield self
            return
        if _sha(current_sha) == target_sha:
            yield self
            return
        worktree = self.state / "source-worktrees" / str(manifest["manifest_id"])
        if worktree.exists():
            raise HarnessError(f"target source worktree already exists: {worktree}")
        worktree.parent.mkdir(parents=True, exist_ok=True)
        _run_command(
            ["git", "worktree", "add", "--detach", str(worktree), target_sha],
            cwd=self.root,
        )
        try:
            yield GrafLocalAdapter(worktree, self.state)
        finally:
            with contextlib.suppress(HarnessError):
                _run_command(["git", "worktree", "remove", "--force", str(worktree)], cwd=self.root)

    def promote(self, manifest: Dict[str, Any]) -> Dict[str, str]:
        self._assert_supported()
        self._assert_source_matches_checkout(manifest)
        env = self._env(manifest)
        self._compose_config(env)
        previous_runtime = _read_json(self._runtime_record()) if self._runtime_record().exists() else None
        previous_manifest = _load_active(self.state)
        previous_was_live = self._runtime_is_live(previous_runtime)
        if previous_was_live and previous_manifest is None:
            raise HarnessError("cannot compensate live promotion without the previous active manifest")
        if (
            previous_runtime is not None
            and previous_manifest is not None
            and previous_runtime.get("source_sha") != previous_manifest.get("source_sha")
        ):
            raise HarnessError("previous Dev runtime does not match the active manifest")
        app_backup = self._snapshot_app()
        try:
            self._stop_previous()
            self._install_app(manifest, env)
            self._start_backend(manifest, env)
            checks = self.smoke(manifest)
            if any(value != "pass" for key, value in checks.items() if key != "mode"):
                raise HarnessError("live promotion smoke failed")
        except BaseException as failure:
            compensation_errors = []
            try:
                self._restore_app(app_backup)
            except Exception as exc:  # pragma: no cover - defensive path
                compensation_errors.append(f"app restore failed: {exc}")
            try:
                self._restore_runtime(previous_runtime, previous_manifest, previous_was_live)
            except Exception as exc:  # pragma: no cover - defensive path
                compensation_errors.append(f"runtime restore failed: {exc}")
            if compensation_errors:
                raise HarnessError("live promotion failed; compensation failed: " + "; ".join(compensation_errors)) from failure
            raise
        else:
            if app_backup is not None:
                shutil.rmtree(app_backup)
        return {"mode": "live", "backend": "started", "app": "installed", "checks": checks}

    def rollback(self, active: Dict[str, Any], target: Dict[str, Any]) -> Dict[str, Any]:
        """Restore one previously built Dev target and prove it before commit."""
        self._assert_supported()
        with self._adapter_for_manifest(target) as adapter:
            return adapter._rollback_from_own_checkout(active, target)

    def _rollback_from_own_checkout(self, active: Dict[str, Any], target: Dict[str, Any]) -> Dict[str, Any]:
        """Perform rollback after the adapter is bound to target source bytes."""
        self._assert_supported()
        self._assert_source_matches_checkout(target)
        env = self._env(target)
        self._compose_config(env)
        previous_runtime = _read_json(self._runtime_record()) if self._runtime_record().exists() else None
        previous_was_live = self._runtime_is_live(previous_runtime)
        if not previous_was_live:
            raise HarnessError("live rollback requires an owned active Dev backend")
        if previous_runtime.get("source_sha") != active.get("source_sha"):
            raise HarnessError("active Dev runtime does not match the active manifest")
        app_backup = self._snapshot_app()
        try:
            self._stop_previous()
            self._install_app(target, env)
            self._start_backend(target, env)
            checks = self.smoke(target)
            if any(value != "pass" for key, value in checks.items() if key != "mode"):
                raise HarnessError("live rollback smoke failed")
        except BaseException as failure:
            compensation_errors = []
            try:
                self._restore_app(app_backup)
            except Exception as exc:  # pragma: no cover - defensive path
                compensation_errors.append(f"app restore failed: {exc}")
            try:
                self._restore_runtime(previous_runtime, active, previous_was_live)
            except Exception as exc:  # pragma: no cover - defensive path
                compensation_errors.append(f"runtime restore failed: {exc}")
            if compensation_errors:
                raise HarnessError("live rollback failed; compensation failed: " + "; ".join(compensation_errors)) from failure
            raise
        else:
            if app_backup is not None:
                shutil.rmtree(app_backup)
        return {"mode": "live", "backend": "started", "app": "installed", "checks": checks}

    def _wait_http(self, origin: str, path: str, *, headers: Optional[Dict[str, str]] = None, timeout: int = 10) -> int:
        deadline = dt.datetime.now(dt.timezone.utc).timestamp() + timeout
        last_error = "unreachable"
        while dt.datetime.now(dt.timezone.utc).timestamp() < deadline:
            try:
                request = Request(origin.rstrip("/") + path, headers=headers or {})
                with urlopen(request, timeout=3) as response:
                    return int(response.status)
            except HTTPError as exc:
                # Authentication challenges are useful probe results.  Keep
                # their status so callers can distinguish expected 401/403
                # from a broken 404/5xx route instead of treating all HTTP
                # errors as unreachable.
                if exc.code in {401, 403, 404}:
                    return int(exc.code)
                if 500 <= exc.code <= 599:
                    last_error = f"HTTP {exc.code}"
                    time.sleep(PROBE_RETRY_DELAY_SECONDS)
                    continue
                return int(exc.code)
            except (OSError, URLError) as exc:
                last_error = type(exc).__name__
                time.sleep(PROBE_RETRY_DELAY_SECONDS)
        raise HarnessError(f"live probe failed for {path}: {last_error}")

    def smoke(self, manifest: Dict[str, Any]) -> Dict[str, str]:
        self._assert_supported()
        backend = str(manifest["dev_boundary"]["backend_origin"])
        frontend = str(manifest["dev_boundary"]["frontend_origin"])
        checks: Dict[str, str] = {}

        def service_health(service: str) -> str:
            try:
                output = _run_command(
                    ["docker", "compose", "-f", str(self.compose_file), "ps", "--format", "json", service],
                    cwd=self.root,
                    env=self._env(manifest),
                )
                try:
                    parsed = json.loads(output)
                except json.JSONDecodeError:
                    parsed = None
                rows = parsed if isinstance(parsed, list) else ([parsed] if isinstance(parsed, dict) else [])
                matches = [
                    row for row in rows
                    if isinstance(row, dict) and row.get("Service") == service
                ]
                if len(matches) != 1:
                    return "fail"
                row = matches[0]
                return "pass" if row.get("State") == "running" and row.get("Health") == "healthy" else "fail"
            except (HarnessError, TypeError, ValueError):
                return "fail"

        def probe(origin: str, path: str, headers: Optional[Dict[str, str]] = None) -> str:
            try:
                return "pass" if self._wait_http(origin, path, headers=headers) == 200 else "fail"
            except HarnessError:
                return "fail"

        checks["backend_health"] = probe(backend, "/api/v1/health/live")
        checks["temporal_health"] = service_health("rec-temporal")
        checks["worker_dependencies"] = probe(
            backend, "/api/v1/health/ready/internal", headers={"X-Internal-Health-Check": "true"}
        )
        if service_health("rec-processing-worker") != "pass":
            checks["worker_dependencies"] = "fail"
        checks["frontend_reachability"] = probe(frontend, "/login")
        checks["auth_session_bootstrap"] = probe(backend, "/api/v1/auth/providers")
        try:
            representative_status = self._wait_http(backend, "/api/v1/cabinet/meetings")
            # An unauthenticated Dev probe may correctly receive an auth
            # challenge; a 404/5xx still proves that the route is broken.
            checks["representative_api"] = "pass" if representative_status in {200, 401, 403} else "fail"
        except HarnessError:
            checks["representative_api"] = "fail"
        app_path = Path(os.environ.get("GRAF_DEV_INSTALL_PATH", "/Applications/GRAF Dev.app"))
        info_plist = app_path / "Contents" / "Info.plist"
        try:
            app_sha = _run_command(["plutil", "-extract", "GRAFSourceSHA", "raw", str(info_plist)], cwd=self.root)
            app_id = _run_command(["plutil", "-extract", "CFBundleIdentifier", "raw", str(info_plist)], cwd=self.root)
            app_origin = _run_command(
                ["plutil", "-extract", "LSEnvironment.GRAF_CABINET_BASE_URL", "raw", str(info_plist)], cwd=self.root
            )
            checks["app_origin"] = "pass" if (
                app_sha == manifest["source_sha"] and app_id == APP_BUNDLE_ID and app_origin == backend
            ) else "fail"
        except HarnessError:
            checks["app_origin"] = "fail"
        return checks


def _mkdirs(root: Path) -> None:
    root.mkdir(parents=True, exist_ok=True)
    marker = root / ".dev-boundary"
    if not marker.exists():
        _atomic_write(marker, "GRAF Dev metadata-only boundary\n")


def _atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=str(path.parent), text=True)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temp_name, path)
    finally:
        with contextlib.suppress(FileNotFoundError):
            os.unlink(temp_name)


@contextlib.contextmanager
def state_lock(root: Path) -> Iterator[None]:
    _mkdirs(root)
    lock_path = root / "promote.lock"
    with lock_path.open("a+", encoding="utf-8") as handle:
        if fcntl is not None:
            fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            if fcntl is not None:
                fcntl.flock(handle.fileno(), fcntl.LOCK_UN)


def _manifest_path(root: Path, manifest_id: str) -> Path:
    _safe_id(manifest_id, "manifest_id")
    return root / "manifests" / f"{manifest_id}.json"


def _write_json(path: Path, value: Dict[str, Any]) -> None:
    _atomic_write(path, json.dumps(value, ensure_ascii=False, indent=2, sort_keys=True) + "\n")


def _read_json(path: Path) -> Dict[str, Any]:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise HarnessError(f"Cannot read JSON {path}: {exc}") from exc
    if not isinstance(value, dict):
        raise HarnessError(f"Expected JSON object in {path}")
    return value


def _load_active(root: Path) -> Optional[Dict[str, Any]]:
    pointer = root / "active-manifest.json"
    if not pointer.exists():
        return None
    raw = _read_json(pointer)
    if raw.get("schema_version") != POINTER_VERSION:
        raise HarnessError("active-manifest.json has unsupported pointer schema")
    manifest_id = _safe_id(str(raw.get("manifest_id", "")), "manifest_id")
    manifest = _read_json(_manifest_path(root, manifest_id))
    _validate_manifest(manifest)
    return manifest


def _validate_manifest(manifest: Dict[str, Any]) -> None:
    if not isinstance(manifest, dict):
        raise HarnessError("manifest must be a JSON object")
    unknown = sorted(set(manifest) - MANIFEST_FIELDS)
    if unknown:
        raise HarnessError("manifest contains unsupported fields: " + ", ".join(unknown))
    required = {"schema_version", "manifest_id", "feature_id", "source_sha", "components", "migration_head", "app_identity", "operator", "created_at", "promoted_at", "parent_manifest_id", "status", "health", "dev_boundary"}
    missing = sorted(required - set(manifest))
    if missing:
        raise HarnessError("manifest missing required fields: " + ", ".join(missing))
    if manifest["schema_version"] != SCHEMA_VERSION:
        raise HarnessError("unsupported manifest schema")
    if manifest["status"] not in MANIFEST_STATUSES:
        raise HarnessError("manifest status is invalid")
    _safe_id(str(manifest["manifest_id"]), "manifest_id")
    _safe_id(str(manifest["feature_id"]), "feature_id")
    source_sha = _sha(str(manifest["source_sha"]))
    migration_head = manifest["migration_head"]
    if not isinstance(migration_head, str) or not migration_head or len(migration_head) > 256:
        raise HarnessError("manifest migration_head is invalid")
    operator = manifest["operator"]
    if not isinstance(operator, str) or not operator.strip() or len(operator) > 128:
        raise HarnessError("manifest operator is invalid")
    for key in ("created_at", "promoted_at"):
        value = manifest[key]
        if value is not None:
            if not isinstance(value, str) or not value.strip():
                raise HarnessError(f"manifest {key} is invalid")
            try:
                dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
            except ValueError as exc:
                raise HarnessError(f"manifest {key} is invalid") from exc
    components = manifest["components"]
    if not isinstance(components, dict):
        raise HarnessError("manifest components must be an object")
    unknown_components = sorted(set(components) - {"backend", "frontend", "worker", "macos_app"})
    if unknown_components:
        raise HarnessError("manifest contains unsupported components: " + ", ".join(unknown_components))
    for name in ("backend", "frontend", "worker", "macos_app"):
        component = components.get(name)
        if not isinstance(component, dict):
            raise HarnessError(f"manifest component missing: {name}")
        unknown_fields = sorted(set(component) - COMPONENT_FIELDS)
        if unknown_fields:
            raise HarnessError(f"manifest component {name} contains unsupported fields: {', '.join(unknown_fields)}")
        if _sha(str(component.get("source_sha", ""))) != source_sha:
            raise HarnessError(f"component {name} does not match manifest source SHA")
        if not isinstance(component.get("version"), str) or not component["version"] or len(component["version"]) > 128:
            raise HarnessError(f"component {name} has no version")
        if not re.fullmatch(r"sha256:[0-9a-fA-F]{64}", str(component.get("digest", ""))):
            raise HarnessError(f"component {name} has invalid digest")
    identity = manifest["app_identity"]
    if not isinstance(identity, dict) or identity.get("bundle_id") != APP_BUNDLE_ID or identity.get("channel") != APP_CHANNEL:
        raise HarnessError("manifest is not for the single GRAF Dev app")
    unknown_identity = sorted(set(identity) - APP_IDENTITY_FIELDS) if isinstance(identity, dict) else []
    if unknown_identity:
        raise HarnessError("manifest app identity contains unsupported fields: " + ", ".join(unknown_identity))
    for key in ("signing_identity", "designated_requirement", "update_trust"):
        if not isinstance(identity.get(key), str) or not identity[key] or len(identity[key]) > (1024 if key == "designated_requirement" else 256):
            raise HarnessError(f"manifest app identity is incomplete: {key}")
    if not re.fullmatch(r"sha256:[0-9a-fA-F]{64}", str(identity.get("entitlements_digest", ""))):
        raise HarnessError("manifest app identity is incomplete")
    boundary = manifest["dev_boundary"]
    if not isinstance(boundary, dict) or boundary.get("environment") != "development":
        raise HarnessError("manifest is outside the development boundary")
    unknown_boundary = sorted(set(boundary) - BOUNDARY_FIELDS) if isinstance(boundary, dict) else []
    if unknown_boundary:
        raise HarnessError("manifest Dev boundary contains unsupported fields: " + ", ".join(unknown_boundary))
    for key in ("backend_origin", "frontend_origin"):
        if not _is_loopback_origin(str(boundary.get(key, ""))):
            raise HarnessError(f"manifest {key} must be loopback-only")
    data_root = str(boundary.get("data_root", ""))
    if not data_root or len(data_root) > 1024 or any(token in data_root.lower() for token in ("production", "prod-data", "prod_data")):
        raise HarnessError("manifest data root is outside the Dev boundary")
    health = manifest["health"]
    if not isinstance(health, dict) or health.get("result") not in {"pass", "fail", "unknown"}:
        raise HarnessError("manifest health result is invalid")
    unknown_health = sorted(set(health) - HEALTH_FIELDS) if isinstance(health, dict) else []
    if unknown_health:
        raise HarnessError("manifest health contains unsupported fields: " + ", ".join(unknown_health))
    if isinstance(health, dict) and not isinstance(health.get("checks"), dict):
        raise HarnessError("manifest health checks must be an object")
    if isinstance(health, dict):
        checked_at = health.get("checked_at")
        if not isinstance(checked_at, str) or not checked_at.strip():
            raise HarnessError("manifest health checked_at is invalid")
        try:
            dt.datetime.fromisoformat(checked_at.replace("Z", "+00:00"))
        except ValueError as exc:
            raise HarnessError("manifest health checked_at is invalid") from exc
        if any(not isinstance(key, str) or not isinstance(value, str) for key, value in health["checks"].items()):
            raise HarnessError("manifest health checks must contain string values")
    if SENSITIVE_KEY_RE.search(json.dumps(manifest, ensure_ascii=False, sort_keys=True)):
        raise HarnessError("manifest contains a forbidden secret or private-content field")


def build_manifest(sha: str, feature_id: str, operator: str = "local", migration_head: str = "unknown", root: Optional[Path] = None) -> Dict[str, Any]:
    _assert_dev_environment()
    source_sha = _sha(sha)
    feature_id = _safe_id(feature_id, "feature_id")
    operator = operator.strip() or "local"
    root = root or state_dir()
    active = _load_active(root)
    manifest_id = f"dev-{source_sha[:12]}"
    components = {
        name: {"source_sha": source_sha, "version": source_sha[:12], "digest": _digest(f"{name}:{source_sha}")}
        for name in ("backend", "frontend", "worker", "macos_app")
    }
    backend_origin = os.environ.get("GRAF_BACKEND_ORIGIN", DEFAULT_BACKEND_ORIGIN)
    frontend_origin = os.environ.get("GRAF_FRONTEND_ORIGIN", DEFAULT_FRONTEND_ORIGIN)
    manifest = {
        "schema_version": SCHEMA_VERSION,
        "manifest_id": manifest_id,
        "feature_id": feature_id,
        "source_sha": source_sha,
        "components": components,
        "migration_head": migration_head,
        "app_identity": {
            "bundle_id": APP_BUNDLE_ID,
            "channel": APP_CHANNEL,
            "signing_identity": _configured_signing_identity(),
            "designated_requirement": os.environ.get("GRAF_DEV_DESIGNATED_REQUIREMENT", f"identifier {APP_BUNDLE_ID}"),
            "entitlements_digest": _digest("graf-dev-entitlements"),
            "update_trust": os.environ.get("GRAF_DEV_UPDATE_TRUST", "local-dev-trust-v1"),
        },
        "operator": operator,
        "created_at": now(),
        "promoted_at": None,
        "parent_manifest_id": active.get("manifest_id") if active else None,
        "status": "ready",
        "health": {"result": "unknown", "checked_at": now(), "checks": {}},
        "dev_boundary": {
            "environment": "development",
            "backend_origin": backend_origin,
            "frontend_origin": frontend_origin,
            "data_root": str(root / "data"),
        },
    }
    _validate_manifest(manifest)
    return manifest


def operation_build(args: argparse.Namespace) -> Dict[str, Any]:
    root = state_dir(live=bool(getattr(args, "live", False)))
    feature_id = args.feature_id or os.environ.get("GRAF_FEATURE_ID") or _active_feature_id()
    migration_head = args.migration_head
    if migration_head in {None, "", "unknown"}:
        migration_head = _resolve_migration_head(_repo_root())
    manifest = build_manifest(args.sha, feature_id, args.operator, migration_head, root)
    active = _load_active(root)
    # A manifest ID is derived from the source SHA. Rebuilding the active SHA
    # must not silently replace its active record (or detach runtime metadata).
    if active and active.get("manifest_id") == manifest["manifest_id"]:
        if getattr(args, "live", False) and not args.dry_run:
            artifact = root / "artifacts" / str(manifest["manifest_id"]) / "GRAF Dev.app"
            artifact_is_valid = False
            if artifact.is_dir():
                try:
                    artifact_is_valid = (
                        _tree_digest(artifact)
                        == str(active.get("components", {}).get("macos_app", {}).get("digest", ""))
                    )
                except HarnessError:
                    artifact_is_valid = False
            if not artifact_is_valid:
                pointer = _read_json(root / "active-manifest.json") if (root / "active-manifest.json").exists() else {}
                if pointer.get("runtime_mode") == "live" or (root / "runtime.json").exists():
                    # Never replace active metadata while the old runtime/app
                    # is live. A missing artifact requires a verified
                    # re-promotion transaction instead.
                    raise HarnessError(
                        "active live Dev app artifact is missing or drifted; "
                        "stop the live target and perform a verified re-promotion"
                    )
                adapter_info = GrafLocalAdapter(_repo_root(), root).build(manifest)
                manifest.update({
                    "status": active.get("status", "active"),
                    "promoted_at": active.get("promoted_at"),
                    "parent_manifest_id": active.get("parent_manifest_id"),
                    "health": active.get("health", manifest["health"]),
                })
                _validate_manifest(manifest)
                _mkdirs(root)
                _write_json(_manifest_path(root, manifest["manifest_id"]), manifest)
                return {
                    "operation": "build", "dry_run": False, "status": manifest["status"],
                    "adapter": adapter_info, "manifest": manifest, "idempotent": False,
                }
        return {
            "operation": "build",
            "dry_run": bool(args.dry_run),
            "status": active.get("status", "active"),
            "adapter": {"mode": "existing-active"},
            "manifest": active,
            "idempotent": True,
        }
    adapter_info: Dict[str, str] = {"mode": "metadata-only"}
    if getattr(args, "live", False) and not args.dry_run:
        adapter_info = GrafLocalAdapter(_repo_root(), root).build(manifest)
        _validate_manifest(manifest)
    elif getattr(args, "live", False):
        adapter_info = {"mode": "live-dry-run"}
    if not args.dry_run:
        _mkdirs(root)
        manifest_path = _manifest_path(root, manifest["manifest_id"])
        if manifest_path.exists():
            existing = _read_json(manifest_path)
            if existing != manifest:
                raise HarnessError(
                    "a ready Dev manifest already exists for this SHA; "
                    "refusing to overwrite its feature metadata"
                )
            return {
                "operation": "build", "dry_run": False, "status": existing.get("status", "ready"),
                "adapter": {"mode": "existing-ready"}, "manifest": existing, "idempotent": True,
            }
        _write_json(manifest_path, manifest)
    return {"operation": "build", "dry_run": bool(args.dry_run), "adapter": adapter_info, "manifest": manifest}


def operation_promote(args: argparse.Namespace) -> Dict[str, Any]:
    _assert_dev_environment()
    root = state_dir(live=bool(getattr(args, "live", False)))
    candidate = _read_json(Path(args.manifest).resolve())
    _validate_manifest(candidate)
    if candidate.get("migration_head") in {None, "", "unknown"}:
        raise HarnessError("manifest migration_head must be resolved before promotion")
    with state_lock(root):
        active = _load_active(root)
        expected_parent = candidate.get("parent_manifest_id")
        if active and expected_parent != active["manifest_id"]:
            raise HarnessError("candidate parent manifest is stale; rebuild from current active Dev manifest")
        if active is None and expected_parent is not None:
            raise HarnessError("candidate parent manifest is unavailable")
        if active and not getattr(args, "live", False) and not args.dry_run:
            pointer = _read_json(root / "active-manifest.json") if (root / "active-manifest.json").exists() else {}
            if pointer.get("runtime_mode") == "live" or (root / "runtime.json").exists():
                raise HarnessError(
                    "active live Dev target requires --live promotion; "
                    "metadata-only promotion is blocked until runtime replacement is verified"
                )
        if active and candidate.get("migration_head") != active.get("migration_head"):
            raise HarnessError(
                "candidate migration_head differs from active Dev manifest; rebuild against the current database schema"
            )
        if active and candidate["manifest_id"] == active["manifest_id"]:
            pointer = _read_json(root / "active-manifest.json") if (root / "active-manifest.json").exists() else {}
            runtime_mode = pointer.get("runtime_mode")
            live_runtime = GrafLocalAdapter(_repo_root(), root)._runtime_is_live(
                _read_json(root / "runtime.json") if (root / "runtime.json").exists() else None
            ) if getattr(args, "live", False) and not args.dry_run else False
            if not getattr(args, "live", False) or (runtime_mode == "live" and live_runtime):
                return {"operation": "promote", "dry_run": bool(args.dry_run), "status": "active", "manifest": active, "idempotent": True}
        promoted = dict(candidate)
        promoted["status"] = "active"
        promoted["promoted_at"] = now()
        promoted["parent_manifest_id"] = active["manifest_id"] if active else None
        _validate_manifest(promoted)
        adapter_info: Dict[str, str] = {"mode": "metadata-only"}
        if getattr(args, "live", False) and not args.dry_run:
            adapter_info = GrafLocalAdapter(_repo_root(), root).promote(promoted)
            checks = adapter_info.get("checks", {})
            promoted["health"] = {
                "result": "pass" if checks and all(value == "pass" for value in checks.values()) else "fail",
                "checked_at": now(),
                "checks": checks,
            }
            _validate_manifest(promoted)
        if not args.dry_run:
            _mkdirs(root)
            _write_json(_manifest_path(root, promoted["manifest_id"]), promoted)
            pointer = {
                "schema_version": POINTER_VERSION,
                "manifest_id": promoted["manifest_id"],
                "runtime_mode": adapter_info["mode"],
                "updated_at": now(),
            }
            _write_json(root / "active-manifest.json", pointer)
    return {"operation": "promote", "dry_run": bool(args.dry_run), "status": "ready" if args.dry_run else "active", "adapter": adapter_info, "manifest": promoted}


def operation_status(args: argparse.Namespace) -> Dict[str, Any]:
    _assert_dev_environment()
    root = state_dir()
    active = _load_active(root)
    if active is None:
        return {"operation": "status", "status": "blocked", "reason": "no active Dev manifest", "state_dir": str(root)}
    status = active.get("status", "active")
    pointer_path = root / "active-manifest.json"
    if pointer_path.exists():
        pointer = _read_json(pointer_path)
        if pointer.get("runtime_mode") == "live":
            try:
                runtime = _read_json(root / "runtime.json") if (root / "runtime.json").exists() else None
            except HarnessError:
                runtime = None
            if not GrafLocalAdapter(_repo_root(), root)._runtime_is_live(runtime):
                status = "degraded"
                return {
                    "operation": "status",
                    "status": status,
                    "reason": "live Dev runtime is not running or is no longer owned",
                    "manifest": active,
                }
    return {"operation": "status", "status": status, "manifest": active}


def operation_smoke(args: argparse.Namespace) -> Dict[str, Any]:
    _assert_dev_environment()
    if not getattr(args, "live", False) and not getattr(args, "fixture", False):
        raise HarnessError("smoke requires an explicit --live or --fixture mode")
    root = state_dir(live=bool(getattr(args, "live", False)))
    active = _load_active(root)
    if active is None:
        raise HarnessError("smoke requires an active Dev manifest")
    _validate_manifest(active)
    if getattr(args, "live", False) and not args.fixture:
        checks = GrafLocalAdapter(_repo_root(), root).smoke(active)
        status = "pass" if all(value == "pass" for value in checks.values()) else "fail"
        checks["mode"] = "live"
    else:
        checks = {
            "backend_health": "pass",
            "frontend_reachability": "pass",
            "auth_session_bootstrap": "pass",
            "representative_api": "pass",
            "temporal_health": "pass",
            "worker_dependencies": "pass",
            "app_origin": "pass",
            "mode": "fixture" if args.fixture else "metadata-only; use --live for local probes",
        }
        status = "pass"
    return {"operation": "smoke", "status": status, "manifest_id": active["manifest_id"], "source_sha": active["source_sha"], "checks": checks}


def operation_rollback(args: argparse.Namespace) -> Dict[str, Any]:
    _assert_dev_environment()
    root = state_dir(live=bool(getattr(args, "live", False)))
    with state_lock(root):
        active = _load_active(root)
        if active is None:
            raise HarnessError("rollback requires an active Dev manifest")
        pointer_path = root / "active-manifest.json"
        if not args.dry_run and pointer_path.exists() and not getattr(args, "live", False):
            pointer = _read_json(pointer_path)
            if pointer.get("runtime_mode") == "live" or (root / "runtime.json").exists():
                raise HarnessError(
                    "live Dev state is active; refusing metadata-only rollback without runtime restoration"
                )
        if not args.dry_run and not getattr(args, "live", False) and pointer_path.exists():
            pointer = _read_json(pointer_path)
            if pointer.get("runtime_mode") == "live":
                raise HarnessError("metadata-only reset cannot clear an active live Dev runtime")
        target_id = args.manifest_id or active.get("parent_manifest_id")
        if not target_id:
            raise HarnessError("no parent manifest is available for rollback")
        target = _read_json(_manifest_path(root, _safe_id(str(target_id), "manifest_id")))
        _validate_manifest(target)
        adapter_info: Dict[str, Any] = {"mode": "metadata-only"}
        if getattr(args, "live", False) and not args.dry_run:
            adapter_info = GrafLocalAdapter(_repo_root(), root).rollback(active, target)
        if not args.dry_run:
            target = dict(target)
            target["status"] = "active"
            if getattr(args, "live", False):
                target["promoted_at"] = now()
                target["health"] = {
                    "result": "pass",
                    "checked_at": now(),
                    "checks": adapter_info.get("checks", {}),
                }
            _write_json(_manifest_path(root, target["manifest_id"]), target)
            _write_json(
                root / "active-manifest.json",
                {
                    "schema_version": POINTER_VERSION,
                    "manifest_id": target["manifest_id"],
                    "runtime_mode": adapter_info["mode"],
                    "updated_at": now(),
                },
            )
    return {
        "operation": "rollback",
        "dry_run": bool(args.dry_run),
        "status": "ready" if args.dry_run else "active",
        "adapter": adapter_info,
        "manifest": target,
    }


def operation_reset_data(args: argparse.Namespace) -> Dict[str, Any]:
    if not args.confirm_dev_reset:
        raise HarnessError("reset-data requires --confirm-dev-reset")
    root = state_dir()
    _assert_dev_environment()
    with state_lock(root):
        runtime = _read_json(root / "runtime.json") if (root / "runtime.json").exists() else None
        if runtime is not None:
            adapter = GrafLocalAdapter(_repo_root(), root)
            if adapter._runtime_is_live(runtime):
                raise HarnessError(
                    "cannot reset Dev metadata while the owned live backend is running; "
                    "stop or rollback the live runtime first"
                )
            raise HarnessError(
                "cannot reset Dev metadata while runtime ownership cannot be proven; "
                "stop the Dev backend and remove or repair runtime.json first"
            )
        if not args.dry_run:
            _atomic_write(root / "last-reset.json", json.dumps({"operation": "reset-data", "scope": "metadata-only-dev-state", "at": now()}, indent=2) + "\n")
            with contextlib.suppress(FileNotFoundError):
                (root / "active-manifest.json").unlink()
    return {"operation": "reset-data", "dry_run": bool(args.dry_run), "status": "ready" if args.dry_run else "reset", "scope": "metadata-only-dev-state", "state_dir": str(root)}


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Portable metadata-only GRAF Dev harness")
    sub = p.add_subparsers(dest="operation", required=True)
    build = sub.add_parser("build")
    build.add_argument("--sha", required=True)
    build.add_argument("--feature-id", default=None)
    build.add_argument("--operator", default=os.environ.get("GRAF_DEV_OPERATOR", "local"))
    build.add_argument("--migration-head", default="unknown")
    build.add_argument("--dry-run", action="store_true")
    build.add_argument("--live", action="store_true", help="explicitly run the GRAF local build adapter")
    promote = sub.add_parser("promote")
    promote.add_argument("--manifest", required=True)
    promote.add_argument("--dry-run", action="store_true")
    promote.add_argument("--live", action="store_true", help="explicitly start the local stack and install GRAF Dev")
    status = sub.add_parser("status")
    status.add_argument("--json", action="store_true")
    smoke = sub.add_parser("smoke")
    smoke.add_argument("--json", action="store_true")
    smoke.add_argument("--fixture", action="store_true")
    smoke.add_argument("--live", action="store_true", help="explicitly run HTTP and installed-app probes")
    rollback = sub.add_parser("rollback")
    rollback.add_argument("--manifest-id")
    rollback.add_argument("--dry-run", action="store_true")
    rollback.add_argument("--live", action="store_true", help="explicitly restore the local live Dev target")
    reset = sub.add_parser("reset-data")
    reset.add_argument("--confirm-dev-reset", action="store_true")
    reset.add_argument("--dry-run", action="store_true")
    return p


def dispatch(args: argparse.Namespace) -> Dict[str, Any]:
    return {"build": operation_build, "promote": operation_promote, "status": operation_status, "smoke": operation_smoke, "rollback": operation_rollback, "reset-data": operation_reset_data}[args.operation](args)


def main(argv: Optional[list[str]] = None) -> int:
    args = parser().parse_args(argv)
    try:
        result = dispatch(args)
    except HarnessError as exc:
        print(json.dumps({"status": "blocked", "error": str(exc)}, ensure_ascii=False), file=sys.stderr)
        return 2
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    if args.operation == "status" and result.get("status") == "blocked":
        return 1
    if args.operation == "smoke" and result.get("status") != "pass":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
