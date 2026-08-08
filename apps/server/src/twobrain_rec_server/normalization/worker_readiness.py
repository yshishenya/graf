from __future__ import annotations

import re
from datetime import timedelta
from uuid import UUID

WORKER_READINESS_SCHEMA_VERSION = "playback_normalization_worker_readiness_v1"
WORKER_READINESS_ACTIVITY_NAME = "playback_normalization_worker_readiness_activity"
WORKER_IDENTITY_PREFIX = "graf-playback-normalization:"
WORKER_READINESS_TASK_QUEUE_SUFFIX = "-readiness"
WORKER_READINESS_MARKER_NAME = ".worker-readiness-v1"
WORKER_READINESS_MARKER_CONTENT = f"{WORKER_READINESS_SCHEMA_VERSION}\n"
SAFE_HOSTNAME = re.compile(r"[^A-Za-z0-9._-]+")


def playback_normalization_worker_identity(hostname: str | None = None) -> str:
    if hostname is None:
        import socket

        hostname = socket.gethostname()
    normalized = SAFE_HOSTNAME.sub("-", hostname.strip()).strip("-.")[:120]
    if not normalized:
        raise RuntimeError("playback normalization worker hostname is unavailable")
    return f"{WORKER_IDENTITY_PREFIX}{normalized}"


def playback_normalization_readiness_task_queue(task_queue: str) -> str:
    normalized = task_queue.strip()
    if not normalized or len(normalized) + len(WORKER_READINESS_TASK_QUEUE_SUFFIX) > 255:
        raise ValueError("playback normalization readiness task queue is invalid")
    return f"{normalized}{WORKER_READINESS_TASK_QUEUE_SUFFIX}"


def _readiness_marker_path(work_directory: str | object):
    from pathlib import Path

    return Path(work_directory) / WORKER_READINESS_MARKER_NAME


def clear_worker_readiness_marker(work_directory: str | object) -> None:
    marker = _readiness_marker_path(work_directory)
    if marker.is_symlink():
        marker.unlink(missing_ok=True)
        return
    if marker.exists() and not marker.is_file():
        raise RuntimeError("playback normalization readiness marker path is unsafe")
    marker.unlink(missing_ok=True)


def publish_worker_readiness_marker(work_directory: str | object) -> None:
    import os

    marker = _readiness_marker_path(work_directory)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(marker, flags, 0o600)
    try:
        os.write(descriptor, WORKER_READINESS_MARKER_CONTENT.encode("ascii"))
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def require_worker_readiness_marker(work_directory: str | object) -> None:
    import os
    import stat

    marker = _readiness_marker_path(work_directory)
    metadata = marker.lstat()
    if (
        not stat.S_ISREG(metadata.st_mode)
        or stat.S_IMODE(metadata.st_mode) != 0o600
        or metadata.st_uid != os.geteuid()
        or marker.read_text(encoding="ascii") != WORKER_READINESS_MARKER_CONTENT
    ):
        raise RuntimeError("playback normalization readiness marker is invalid")


def build_worker_readiness_receipt(
    payload: dict[str, str],
    *,
    hostname: str | None = None,
) -> dict[str, str]:
    if set(payload) != {"probe_id"}:
        raise ValueError("worker readiness payload is invalid")
    probe_id = str(UUID(payload["probe_id"]))
    from twobrain_rec_server.normalization.statuses import (
        CANONICAL_PROFILE_VERSION,
        VALIDATION_VERSION,
    )

    return {
        "schema_version": WORKER_READINESS_SCHEMA_VERSION,
        "probe_id": probe_id,
        "worker_identity": playback_normalization_worker_identity(hostname),
        "profile_version": CANONICAL_PROFILE_VERSION,
        "validation_version": VALIDATION_VERSION,
    }


async def run_playback_normalization_readiness_activity(
    payload: dict[str, str],
) -> dict[str, str]:
    return build_worker_readiness_receipt(payload)


try:
    from temporalio import workflow
except Exception:  # pragma: no cover - import fallback for docs and narrow unit tests
    workflow = None


if workflow is not None:

    @workflow.defn
    class PlaybackNormalizationReadinessWorkflow:
        @workflow.run
        async def run(self, payload: dict[str, str]) -> dict[str, str]:
            from temporalio.common import RetryPolicy

            return await workflow.execute_activity(
                WORKER_READINESS_ACTIVITY_NAME,
                payload,
                start_to_close_timeout=timedelta(seconds=10),
                retry_policy=RetryPolicy(maximum_attempts=1),
            )

else:

    class PlaybackNormalizationReadinessWorkflow:
        async def run(self, payload: dict[str, str]) -> dict[str, str]:
            return payload
