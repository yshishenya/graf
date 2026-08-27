import asyncio
from datetime import timedelta
from pathlib import Path
from types import SimpleNamespace
from uuid import UUID

import pytest

from twobrain_rec_server.config import Settings
from twobrain_rec_server.normalization import worker as worker_module
from twobrain_rec_server.normalization.worker import (
    _wake_processing_after_normalization,
    cleanup_startup_work_directory,
    normalization_activity_lease_duration,
    packaged_schema_head,
    require_schema_head,
    require_storage_ready,
    run_normalization_reconciliation_loop,
    run_playback_normalization_activity,
    validate_media_tools,
    validate_startup_work_directory,
)
from twobrain_rec_server.normalization.worker_readiness import (
    clear_worker_readiness_marker,
    publish_worker_readiness_marker,
    require_worker_readiness_marker,
)


def test_worker_main_sets_private_file_umask(monkeypatch) -> None:
    seen_umasks: list[int] = []

    def run_and_close(coroutine) -> None:
        coroutine.close()

    monkeypatch.setattr(worker_module.os, "umask", seen_umasks.append)
    monkeypatch.setattr(worker_module.asyncio, "run", run_and_close)

    worker_module.main()

    assert seen_umasks == [0o077]


def test_activity_lease_outlives_one_missed_heartbeat_until_reconciliation() -> None:
    settings = Settings(playback_normalization_enabled=True)

    assert settings.playback_normalization_heartbeat_seconds == 30
    assert settings.playback_normalization_reconcile_interval_seconds == 60
    assert normalization_activity_lease_duration(settings) == timedelta(seconds=90)


@pytest.mark.anyio
async def test_normalization_activity_reuses_worker_dependencies(monkeypatch, tmp_path) -> None:
    workspace_id = UUID("11111111-1111-4111-8111-111111111111")
    meeting_id = UUID("22222222-2222-4222-8222-222222222222")
    revision_id = UUID("33333333-3333-4333-8333-333333333333")
    job_id = UUID("44444444-4444-4444-8444-444444444444")
    settings = Settings(
        playback_normalization_enabled=True,
        playback_normalization_work_directory=tmp_path,
    )
    storage = object()
    job = SimpleNamespace(
        id=job_id,
        meeting_id=meeting_id,
        media_revision_id=revision_id,
        profile_version="profile-v1",
        validation_version="validation-v1",
        state="queued",
        lease_expires_at=None,
    )

    class Db:
        async def scalar(self, _statement):
            return job

    class Session:
        async def __aenter__(self):
            return Db()

        async def __aexit__(self, *_args) -> None:
            return None

    async def apply_scope(*_args, **_kwargs) -> None:
        return None

    async def run_job(**kwargs):
        assert kwargs["storage"] is storage
        return SimpleNamespace(
            job_id=job_id,
            canonical_track_artifact_id=UUID("55555555-5555-4555-8555-555555555555"),
            reused=False,
        )

    def must_not_create(*_args, **_kwargs):
        raise AssertionError("worker activity created an owned dependency")

    monkeypatch.setattr(worker_module, "apply_tenant_scope", apply_scope)
    monkeypatch.setattr(worker_module, "run_normalization_job", run_job)
    monkeypatch.setattr(worker_module, "create_engine", must_not_create)
    monkeypatch.setattr(worker_module, "get_storage", must_not_create)
    monkeypatch.setattr(
        "temporalio.activity.info",
        lambda: SimpleNamespace(workflow_run_id="run", activity_id="activity", attempt=1),
    )
    monkeypatch.setattr("temporalio.activity.heartbeat", lambda *_args, **_kwargs: None)

    result = await run_playback_normalization_activity(
        {
            "organization_id": "66666666-6666-4666-8666-666666666666",
            "workspace_id": str(workspace_id),
            "user_id": "77777777-7777-4777-8777-777777777777",
            "device_id": "88888888-8888-4888-8888-888888888888",
            "job_id": str(job_id),
            "meeting_id": str(meeting_id),
            "media_revision_id": str(revision_id),
            "profile_version": "profile-v1",
            "validation_version": "validation-v1",
        },
        settings=settings,
        sessionmaker=Session,
        storage=storage,
    )

    assert result == {
        "job_id": str(job_id),
        "canonical_track_artifact_id": "55555555-5555-4555-8555-555555555555",
        "state": "ready",
        "reused": "false",
    }


@pytest.mark.anyio
async def test_normalization_wake_uses_persisted_active_processing_workflow(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[object, object]] = []

    class Handle:
        async def signal(self, signal) -> None:
            calls.append(("signal", signal))

    class TemporalClient:
        def get_workflow_handle(self, workflow_id: str) -> Handle:
            calls.append(("workflow_id", workflow_id))
            return Handle()

    media_revision_id = UUID("22222222-2222-4222-8222-222222222222")
    workspace_id = UUID("44444444-4444-4444-8444-444444444444")
    meeting_id = UUID("55555555-5555-4555-8555-555555555555")
    persisted_workflow_id = f"processing/{media_revision_id}/2"

    async def active_workflow(_db, **kwargs):
        assert kwargs == {
            "workspace_id": workspace_id,
            "meeting_id": meeting_id,
            "media_revision_id": media_revision_id,
            "active_only": True,
        }
        return SimpleNamespace(workflow_id=persisted_workflow_id)

    monkeypatch.setattr(worker_module, "get_processing_workflow", active_workflow)

    await _wake_processing_after_normalization(
        db=object(),
        temporal_client=TemporalClient(),
        workspace_id=workspace_id,
        meeting_id=meeting_id,
        media_revision_id=media_revision_id,
    )
    assert calls[0] == ("workflow_id", persisted_workflow_id)
    assert calls[1][0] == "signal"


def test_startup_cleanup_removes_only_owned_normalization_work_directories(
    tmp_path: Path,
) -> None:
    job_id = UUID("11111111-1111-4111-8111-111111111111")
    owned_directory = tmp_path / f"{job_id}-orphan"
    owned_directory.mkdir()
    (owned_directory / "output.m4a").write_bytes(b"synthetic")
    unrelated_directory = tmp_path / "operator-evidence"
    unrelated_directory.mkdir()
    (unrelated_directory / "keep.txt").write_text("keep", encoding="utf-8")

    removed = cleanup_startup_work_directory(tmp_path)

    assert removed == 1
    assert not owned_directory.exists()
    assert unrelated_directory.is_dir()


def test_worker_readiness_marker_is_private_exact_and_cleared(tmp_path: Path) -> None:
    publish_worker_readiness_marker(tmp_path)
    require_worker_readiness_marker(tmp_path)

    marker = tmp_path / ".worker-readiness-v1"
    assert marker.stat().st_mode & 0o777 == 0o600
    marker.chmod(0o644)
    with pytest.raises(RuntimeError, match="marker is invalid"):
        require_worker_readiness_marker(tmp_path)

    clear_worker_readiness_marker(tmp_path)
    assert not marker.exists()


def test_startup_work_directory_requires_private_owned_non_symlink_with_capacity(
    tmp_path: Path,
    monkeypatch,
) -> None:
    work = tmp_path / "work"
    work.mkdir(mode=0o700)
    work.chmod(0o700)
    monkeypatch.setattr(
        worker_module.shutil,
        "disk_usage",
        lambda _path: SimpleNamespace(free=10_000),
    )

    assert validate_startup_work_directory(work, minimum_free_bytes=10_000) == work

    work.chmod(0o755)
    with pytest.raises(RuntimeError, match="mode must be 0700"):
        validate_startup_work_directory(work, minimum_free_bytes=1)
    work.chmod(0o700)

    with pytest.raises(RuntimeError, match="insufficient free space"):
        validate_startup_work_directory(work, minimum_free_bytes=10_001)

    symlink = tmp_path / "work-link"
    symlink.symlink_to(work, target_is_directory=True)
    with pytest.raises(RuntimeError, match="must not be a symlink"):
        validate_startup_work_directory(symlink, minimum_free_bytes=1)


def test_worker_startup_requires_executable_media_tools(tmp_path: Path) -> None:
    ffmpeg = tmp_path / "ffmpeg"
    ffprobe = tmp_path / "ffprobe"
    ffmpeg.write_text("#!/bin/sh\n", encoding="utf-8")
    ffprobe.write_text("#!/bin/sh\n", encoding="utf-8")

    with pytest.raises(RuntimeError, match="FFmpeg executable is unavailable"):
        validate_media_tools(ffmpeg_path=ffmpeg, ffprobe_path=ffprobe)

    ffmpeg.chmod(0o700)
    ffprobe.chmod(0o700)
    validate_media_tools(ffmpeg_path=ffmpeg, ffprobe_path=ffprobe)


@pytest.mark.anyio
async def test_storage_startup_gate_requires_explicit_ready_result() -> None:
    class ReadyStorage:
        async def is_ready_async(self) -> bool:
            return True

    class BlockedStorage:
        def is_ready(self) -> bool:
            return False

    await require_storage_ready(ReadyStorage())
    with pytest.raises(RuntimeError, match="storage is unavailable"):
        await require_storage_ready(BlockedStorage())
    with pytest.raises(RuntimeError, match="readiness is unavailable"):
        await require_storage_ready(object())


@pytest.mark.anyio
async def test_schema_startup_gate_requires_exact_migration_head() -> None:
    class Connection:
        def __init__(self, version: str) -> None:
            self.version = version

        async def scalar(self, _statement) -> str:
            return self.version

    class ConnectionContext:
        def __init__(self, version: str) -> None:
            self.connection = Connection(version)

        async def __aenter__(self):
            return self.connection

        async def __aexit__(self, *_args) -> None:
            return None

    class Engine:
        def __init__(self, version: str) -> None:
            self.version = version

        def connect(self) -> ConnectionContext:
            return ConnectionContext(self.version)

    await require_schema_head(Engine(packaged_schema_head()))
    with pytest.raises(RuntimeError, match="schema head is unavailable"):
        await require_schema_head(Engine("0037_auth_rate_limit_buckets"))
    with pytest.raises(RuntimeError, match="schema head is unavailable"):
        await require_schema_head(Engine("0034_share_grant_token_replay"))
    with pytest.raises(RuntimeError, match="schema head is unavailable"):
        await require_schema_head(Engine("0021_media_revision_upload_contract"))


def test_worker_schema_head_is_derived_from_packaged_migrations() -> None:
    assert packaged_schema_head() == "0083_processing_recovery"


@pytest.mark.anyio
async def test_initial_reconciliation_failure_disposes_engine_and_storage(
    tmp_path: Path,
    monkeypatch,
) -> None:
    class FakeEngine:
        disposed = False

        async def dispose(self) -> None:
            self.disposed = True

    class FakeStorage:
        closed = False

        def close(self) -> None:
            self.closed = True

    class FakeWorker:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args) -> None:
            return None

    engine = FakeEngine()
    storage = FakeStorage()
    settings = Settings(
        playback_normalization_enabled=True,
        playback_normalization_work_directory=tmp_path,
    )

    async def no_op_async(*_args, **_kwargs) -> None:
        return None

    async def connect_temporal(_settings, *, identity=None):
        assert identity is not None
        return object()

    async def fail_reconciliation(**_kwargs) -> None:
        raise RuntimeError("initial reconciliation failed")

    monkeypatch.setattr(worker_module, "get_settings", lambda: settings)
    monkeypatch.setattr(worker_module, "configure_logging", lambda _settings: None)
    monkeypatch.setattr(
        worker_module, "validate_startup_work_directory", lambda *_args, **_kwargs: tmp_path
    )
    monkeypatch.setattr(worker_module, "validate_media_tools", lambda **_kwargs: None)
    monkeypatch.setattr(worker_module, "cleanup_startup_work_directory", lambda _path: 0)
    monkeypatch.setattr(worker_module, "get_storage", lambda _settings: storage)
    monkeypatch.setattr(worker_module, "create_engine", lambda _settings: engine)
    monkeypatch.setattr(worker_module, "create_sessionmaker", lambda _engine: object())
    monkeypatch.setattr(worker_module, "require_storage_ready", no_op_async)
    monkeypatch.setattr(worker_module, "require_schema_head", no_op_async)
    monkeypatch.setattr(worker_module, "connect_temporal_client", connect_temporal)
    monkeypatch.setattr(
        worker_module,
        "create_normalization_temporal_workers",
        lambda **_kwargs: (FakeWorker(), FakeWorker()),
    )
    monkeypatch.setattr(worker_module, "reconcile_normalization_jobs", fail_reconciliation)

    with pytest.raises(RuntimeError, match="initial reconciliation failed"):
        await worker_module.run_worker()

    assert engine.disposed is True
    assert storage.closed is True


@pytest.mark.anyio
async def test_reconciliation_failure_logs_only_safe_error_type(monkeypatch) -> None:
    logged: list[tuple[str, dict[str, str]]] = []

    async def fail_reconciliation(**_kwargs) -> None:
        raise RuntimeError("private/path/meeting-review.m4a")

    async def stop_after_one_cycle(_seconds: int) -> None:
        raise asyncio.CancelledError

    def capture_warning(message: str, *, extra: dict[str, str]) -> None:
        logged.append((message, extra))

    monkeypatch.setattr(worker_module, "reconcile_normalization_jobs", fail_reconciliation)
    monkeypatch.setattr(worker_module.asyncio, "sleep", stop_after_one_cycle)
    monkeypatch.setattr(worker_module.LOGGER, "warning", capture_warning)

    with pytest.raises(asyncio.CancelledError):
        await run_normalization_reconciliation_loop(
            sessionmaker=object(),
            settings=Settings(playback_normalization_enabled=True),
            storage=object(),
            temporal_client=object(),
        )

    assert logged == [
        (
            "playback_normalization.reconciliation_failed",
            {"error_type": "RuntimeError"},
        )
    ]
    assert "meeting-review" not in repr(logged)
