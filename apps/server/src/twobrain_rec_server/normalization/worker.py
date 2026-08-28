from __future__ import annotations

import asyncio
import logging
import os
import re
import shutil
import stat
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from pathlib import Path
from uuid import UUID

from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import select, text

from twobrain_rec_server.auth.context import TenantScope
from twobrain_rec_server.config import Settings, get_settings
from twobrain_rec_server.db.models import PlaybackNormalizationJob
from twobrain_rec_server.db.session import create_engine, create_sessionmaker
from twobrain_rec_server.db.tenant_context import apply_tenant_scope
from twobrain_rec_server.normalization.pickup import reconcile_normalization_jobs
from twobrain_rec_server.normalization.service import (
    FFmpegNormalizationPipeline,
    NormalizationExecutionDeferred,
    NormalizationExecutionFailure,
    activate_due_normalization_retry,
    recover_expired_normalization_job,
    run_normalization_job,
)
from twobrain_rec_server.normalization.statuses import JobState
from twobrain_rec_server.normalization.worker_readiness import (
    PlaybackNormalizationReadinessWorkflow,
    clear_worker_readiness_marker,
    playback_normalization_readiness_task_queue,
    playback_normalization_worker_identity,
    publish_worker_readiness_marker,
    run_playback_normalization_readiness_activity,
)
from twobrain_rec_server.observability.logging import configure_logging
from twobrain_rec_server.processing.store import get_processing_workflow
from twobrain_rec_server.storage.minio_client import get_storage
from twobrain_rec_server.workflows.playback_normalization_workflow import (
    PlaybackNormalizationWorkflow,
)
from twobrain_rec_server.workflows.processing_workflow import MediaScribeProcessingWorkflow
from twobrain_rec_server.workflows.temporal_client import (
    connect_temporal_client,
)

WORK_DIRECTORY_NAME = re.compile(
    r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}-[A-Za-z0-9_-]+$"
)
LOGGER = logging.getLogger("twobrain_rec.normalization.worker")


def validate_startup_work_directory(
    work_directory: str | Path,
    *,
    minimum_free_bytes: int,
) -> Path:
    root = Path(work_directory)
    if root.is_symlink():
        raise RuntimeError("playback normalization work directory must not be a symlink")
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    metadata = root.lstat()
    if not stat.S_ISDIR(metadata.st_mode):
        raise RuntimeError("playback normalization work path is not a directory")
    if stat.S_IMODE(metadata.st_mode) != 0o700:
        raise RuntimeError("playback normalization work directory mode must be 0700")
    if metadata.st_uid != os.geteuid():
        raise RuntimeError("playback normalization work directory owner is invalid")
    if minimum_free_bytes <= 0:
        raise ValueError("minimum_free_bytes must be positive")
    if shutil.disk_usage(root).free < minimum_free_bytes:
        raise RuntimeError("playback normalization work directory has insufficient free space")
    return root


def validate_media_tools(*, ffmpeg_path: str | Path, ffprobe_path: str | Path) -> None:
    for tool_name, tool_path in (("FFmpeg", ffmpeg_path), ("FFprobe", ffprobe_path)):
        path = Path(tool_path)
        if not path.is_file() or not os.access(path, os.X_OK):
            raise RuntimeError(f"playback normalization {tool_name} executable is unavailable")


async def require_storage_ready(storage: object) -> None:
    is_ready_async = getattr(storage, "is_ready_async", None)
    if is_ready_async is not None:
        ready = bool(await is_ready_async())
    else:
        is_ready = getattr(storage, "is_ready", None)
        if is_ready is None:
            raise RuntimeError("playback normalization storage readiness is unavailable")
        ready = bool(await asyncio.to_thread(is_ready))
    if not ready:
        raise RuntimeError("playback normalization storage is unavailable")


def packaged_schema_head(alembic_ini_path: str | Path | None = None) -> str:
    candidates = (
        (Path(alembic_ini_path),)
        if alembic_ini_path is not None
        else (Path("/app/alembic.ini"), Path(__file__).resolve().parents[3] / "alembic.ini")
    )
    config_path = next((candidate for candidate in candidates if candidate.is_file()), None)
    if config_path is None:
        raise RuntimeError("packaged Alembic configuration is unavailable")
    config = Config(str(config_path))
    script_location = config.get_main_option("script_location")
    if not script_location:
        raise RuntimeError("packaged Alembic script location is unavailable")
    script_path = Path(script_location)
    if not script_path.is_absolute():
        script_path = config_path.parent / script_path
    config.set_main_option("script_location", str(script_path.resolve()))
    heads = ScriptDirectory.from_config(config).get_heads()
    if len(heads) != 1:
        raise RuntimeError("packaged Alembic migrations must have exactly one head")
    return heads[0]


async def require_schema_head(engine: object) -> None:
    expected_head = packaged_schema_head()
    async with engine.connect() as connection:
        version = await connection.scalar(text("select version_num from alembic_version"))
    if version != expected_head:
        raise RuntimeError("playback normalization schema head is unavailable")


def cleanup_startup_work_directory(work_directory: str | Path) -> int:
    root = Path(work_directory)
    root.mkdir(mode=0o700, parents=True, exist_ok=True)
    removed = 0
    for child in root.iterdir():
        if not WORK_DIRECTORY_NAME.fullmatch(child.name):
            continue
        if child.is_symlink() or child.is_file():
            child.unlink(missing_ok=True)
        elif child.is_dir():
            shutil.rmtree(child)
        else:
            continue
        removed += 1
    return removed


def _required_uuid(payload: dict[str, str], field_name: str) -> UUID:
    raw_value = payload.get(field_name)
    if not raw_value:
        raise ValueError(f"missing playback normalization field: {field_name}")
    try:
        return UUID(raw_value)
    except ValueError as exc:
        raise ValueError(f"invalid playback normalization field: {field_name}") from exc


def tenant_scope_from_normalization_payload(payload: dict[str, str]) -> TenantScope:
    auth_session_id = payload.get("auth_session_id")
    return TenantScope(
        organization_id=_required_uuid(payload, "organization_id"),
        workspace_id=_required_uuid(payload, "workspace_id"),
        user_id=_required_uuid(payload, "user_id"),
        device_id=_required_uuid(payload, "device_id"),
        auth_session_id=UUID(auth_session_id) if auth_session_id else None,
    )


def normalization_activity_lease_duration(settings: Settings) -> timedelta:
    heartbeat_seconds = int(settings.playback_normalization_heartbeat_seconds)
    reconcile_seconds = int(settings.playback_normalization_reconcile_interval_seconds)
    return timedelta(seconds=max(heartbeat_seconds * 3, heartbeat_seconds + reconcile_seconds))


async def renew_normalization_activity_lease(
    *,
    sessionmaker,
    tenant_scope: TenantScope,
    job_id: UUID,
    lease_owner_sha256: str,
    lease_duration: timedelta,
    now: datetime | None = None,
) -> bool:
    async with sessionmaker() as db:
        await apply_tenant_scope(db, tenant_scope, context_kind="worker")
        job = await db.scalar(
            select(PlaybackNormalizationJob)
            .where(
                PlaybackNormalizationJob.id == job_id,
                PlaybackNormalizationJob.workspace_id == tenant_scope.workspace_id,
            )
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        if (
            job is None
            or job.state
            not in {
                JobState.RUNNING.value,
                JobState.PUBLISHING.value,
            }
            or job.lease_owner_sha256 != lease_owner_sha256
        ):
            return False
        current_time = now or datetime.now(UTC)
        job.last_heartbeat_at = current_time
        job.lease_expires_at = current_time + lease_duration
        await db.commit()
        return True


async def _normalization_activity_heartbeat_loop(
    *,
    sessionmaker,
    tenant_scope: TenantScope,
    job_id: UUID,
    lease_owner_sha256: str,
    settings: Settings,
    heartbeat,
) -> None:
    interval = int(settings.playback_normalization_heartbeat_seconds)
    lease_duration = normalization_activity_lease_duration(settings)
    while True:
        await asyncio.sleep(interval)
        if not await renew_normalization_activity_lease(
            sessionmaker=sessionmaker,
            tenant_scope=tenant_scope,
            job_id=job_id,
            lease_owner_sha256=lease_owner_sha256,
            lease_duration=lease_duration,
        ):
            return
        heartbeat({"state": "normalizing", "job_id": str(job_id)})


async def _wake_processing_after_normalization(
    *,
    db,
    temporal_client: object | None,
    workspace_id: UUID,
    meeting_id: UUID,
    media_revision_id: UUID,
) -> None:
    if temporal_client is None:
        return
    try:
        workflow = await get_processing_workflow(
            db,
            workspace_id=workspace_id,
            meeting_id=meeting_id,
            media_revision_id=media_revision_id,
            active_only=True,
        )
        if workflow is None:
            return
        handle = temporal_client.get_workflow_handle(workflow.workflow_id)
        await handle.signal(MediaScribeProcessingWorkflow.request_manual_check)
    except Exception as exc:
        # The processing workflow may not exist yet or Temporal may be briefly
        # unavailable. Its bounded fallback timer remains authoritative.
        LOGGER.info(
            "playback_normalization.processing_wake_deferred",
            extra={"error_type": type(exc).__name__},
        )
        return


async def run_playback_normalization_activity(
    payload: dict[str, str],
    *,
    settings: Settings | None = None,
    sessionmaker=None,
    storage: object | None = None,
    temporal_client: object | None = None,
) -> dict[str, str]:
    from temporalio import activity
    from temporalio.exceptions import ApplicationError

    tenant_scope = tenant_scope_from_normalization_payload(payload)
    job_id = _required_uuid(payload, "job_id")
    meeting_id = _required_uuid(payload, "meeting_id")
    media_revision_id = _required_uuid(payload, "media_revision_id")
    profile_version = payload.get("profile_version")
    validation_version = payload.get("validation_version")
    activity_info = activity.info()
    lease_owner = (
        f"{activity_info.workflow_run_id}:{activity_info.activity_id}:{activity_info.attempt}"
    )
    lease_owner_sha256 = sha256(lease_owner.encode("utf-8")).hexdigest()
    activity.heartbeat({"state": "starting", "job_id": str(job_id)})

    settings = settings or get_settings()
    if not settings.playback_normalization_enabled:
        raise RuntimeError("playback normalization capability is disabled")
    owned_engine = None
    if sessionmaker is None:
        owned_engine = create_engine(settings)
        sessionmaker = create_sessionmaker(owned_engine)
    if storage is None:
        storage = get_storage(settings)
    try:
        async with sessionmaker() as db:
            await apply_tenant_scope(db, tenant_scope, context_kind="worker")
            job = await db.scalar(
                select(PlaybackNormalizationJob).where(
                    PlaybackNormalizationJob.id == job_id,
                    PlaybackNormalizationJob.workspace_id == tenant_scope.workspace_id,
                )
            )
            if (
                job is None
                or job.meeting_id != meeting_id
                or job.media_revision_id != media_revision_id
                or job.profile_version != profile_version
                or job.validation_version != validation_version
            ):
                raise ValueError("playback normalization job identity mismatch")
            if (
                job.state in {JobState.RUNNING.value, JobState.PUBLISHING.value}
                and job.lease_expires_at is not None
                and (
                    job.lease_expires_at
                    if job.lease_expires_at.tzinfo is not None
                    else job.lease_expires_at.replace(tzinfo=UTC)
                )
                <= datetime.now(UTC)
            ):
                recovery = await recover_expired_normalization_job(
                    db,
                    storage=storage,
                    job_id=job.id,
                )
                if recovery is not None and recovery.next_attempt_at is not None:
                    await activate_due_normalization_retry(
                        db,
                        job_id=job.id,
                        now=datetime.now(UTC),
                        recover_worker_interruption=True,
                    )
            activity.heartbeat({"state": "normalizing", "job_id": str(job_id)})
            heartbeat_task = asyncio.create_task(
                _normalization_activity_heartbeat_loop(
                    sessionmaker=sessionmaker,
                    tenant_scope=tenant_scope,
                    job_id=job.id,
                    lease_owner_sha256=lease_owner_sha256,
                    settings=settings,
                    heartbeat=activity.heartbeat,
                )
            )
            try:
                # The service fences ownership before and after object upload.
                # Let an in-flight transfer reach that post-upload fence: task
                # cancellation can otherwise leave a completed MinIO PUT without
                # durable cleanup evidence.
                result = await run_normalization_job(
                    db=db,
                    storage=storage,
                    job_id=job.id,
                    work_directory=settings.playback_normalization_work_directory,
                    pipeline=FFmpegNormalizationPipeline.from_settings(settings),
                    lease_duration=normalization_activity_lease_duration(settings),
                    lease_owner=lease_owner,
                    work_budget_bytes=settings.playback_normalization_work_budget_bytes,
                    output_max_bytes=settings.playback_normalization_output_max_bytes,
                    work_reserve_bytes=settings.playback_normalization_work_reserve_bytes,
                )
            except NormalizationExecutionDeferred:
                raise ApplicationError(
                    "playback normalization job is already owned",
                    type="PlaybackNormalizationDeferred",
                    non_retryable=True,
                ) from None
            except NormalizationExecutionFailure as exc:
                if not exc.should_retry:
                    await _wake_processing_after_normalization(
                        db=db,
                        temporal_client=temporal_client,
                        workspace_id=tenant_scope.workspace_id,
                        meeting_id=meeting_id,
                        media_revision_id=media_revision_id,
                    )
                raise ApplicationError(
                    exc.reason_code.value,
                    type="PlaybackNormalizationFailure",
                    non_retryable=not exc.should_retry,
                ) from None
            finally:
                heartbeat_task.cancel()
                await asyncio.gather(heartbeat_task, return_exceptions=True)
            await _wake_processing_after_normalization(
                db=db,
                temporal_client=temporal_client,
                workspace_id=tenant_scope.workspace_id,
                meeting_id=meeting_id,
                media_revision_id=media_revision_id,
            )
            activity.heartbeat({"state": "published", "job_id": str(job_id)})
            return {
                "job_id": str(result.job_id),
                "canonical_track_artifact_id": str(result.canonical_track_artifact_id),
                "state": "ready",
                "reused": "true" if result.reused else "false",
            }
    finally:
        if owned_engine is not None:
            await owned_engine.dispose()


async def run_normalization_reconciliation_loop(
    *,
    sessionmaker,
    settings,
    storage: object,
    temporal_client: object,
) -> None:
    while True:
        try:
            await reconcile_normalization_jobs(
                sessionmaker=sessionmaker,
                settings=settings,
                storage=storage,
                temporal_client=temporal_client,
            )
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            LOGGER.warning(
                "playback_normalization.reconciliation_failed",
                extra={"error_type": type(exc).__name__},
            )
        await asyncio.sleep(int(settings.playback_normalization_reconcile_interval_seconds))


def create_normalization_temporal_workers(
    *,
    client: object,
    settings: Settings,
    worker_identity: str,
    normalization_activity: object,
    readiness_activity: object,
) -> tuple[object, object]:
    from temporalio.worker import Worker

    normalization_worker = Worker(
        client,
        task_queue=settings.playback_normalization_task_queue,
        workflows=[PlaybackNormalizationWorkflow],
        activities=[normalization_activity],
        max_concurrent_activities=settings.playback_normalization_worker_concurrency,
        identity=worker_identity,
    )
    readiness_worker = Worker(
        client,
        task_queue=playback_normalization_readiness_task_queue(
            settings.playback_normalization_task_queue
        ),
        workflows=[PlaybackNormalizationReadinessWorkflow],
        activities=[readiness_activity],
        max_concurrent_activities=1,
        identity=worker_identity,
    )
    return normalization_worker, readiness_worker


async def run_worker() -> None:
    from temporalio import activity

    settings = get_settings()
    configure_logging(settings)
    if not settings.playback_normalization_enabled:
        raise RuntimeError("playback normalization worker requires enabled capability")
    validate_startup_work_directory(
        settings.playback_normalization_work_directory,
        minimum_free_bytes=settings.playback_normalization_work_budget_bytes,
    )
    validate_media_tools(
        ffmpeg_path=settings.playback_normalization_ffmpeg_path,
        ffprobe_path=settings.playback_normalization_ffprobe_path,
    )
    clear_worker_readiness_marker(settings.playback_normalization_work_directory)
    cleanup_startup_work_directory(settings.playback_normalization_work_directory)
    storage = get_storage(settings)
    engine = None
    try:
        engine = create_engine(settings)
        await require_storage_ready(storage)
        await require_schema_head(engine)
        worker_identity = playback_normalization_worker_identity()
        client = await connect_temporal_client(settings, identity=worker_identity)
        sessionmaker = create_sessionmaker(engine)

        async def normalization_activity_impl(payload: dict[str, str]) -> dict[str, str]:
            return await run_playback_normalization_activity(
                payload,
                settings=settings,
                sessionmaker=sessionmaker,
                storage=storage,
                temporal_client=client,
            )

        normalization_activity = activity.defn(name="run_playback_normalization_activity")(
            normalization_activity_impl
        )
        readiness_activity = activity.defn(name="playback_normalization_worker_readiness_activity")(
            run_playback_normalization_readiness_activity
        )
        normalization_worker, readiness_worker = create_normalization_temporal_workers(
            client=client,
            settings=settings,
            worker_identity=worker_identity,
            normalization_activity=normalization_activity,
            readiness_activity=readiness_activity,
        )
        async with normalization_worker, readiness_worker:
            await reconcile_normalization_jobs(
                sessionmaker=sessionmaker,
                settings=settings,
                storage=storage,
                temporal_client=client,
                recover_worker_interrupted=True,
            )
            publish_worker_readiness_marker(settings.playback_normalization_work_directory)
            await run_normalization_reconciliation_loop(
                sessionmaker=sessionmaker,
                settings=settings,
                storage=storage,
                temporal_client=client,
            )
    finally:
        clear_worker_readiness_marker(settings.playback_normalization_work_directory)
        close_storage = getattr(storage, "close", None)
        if close_storage is not None:
            close_storage()
        if engine is not None:
            await engine.dispose()


def main() -> None:
    os.umask(0o077)
    asyncio.run(run_worker())


if __name__ == "__main__":
    main()
