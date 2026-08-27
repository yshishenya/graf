from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from hashlib import sha256
from uuid import UUID

from anyio import to_thread
from sqlalchemy import and_, case, exists, or_, select, text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from twobrain_rec_server.auth.context import TenantScope
from twobrain_rec_server.config import Settings
from twobrain_rec_server.db.models import (
    Meeting,
    PlaybackBackfillRun,
    PlaybackNormalizationAttempt,
    PlaybackNormalizationJob,
    TrackArtifact,
    Workspace,
)
from twobrain_rec_server.db.tenant_context import (
    MaintenanceTenantContext,
    apply_tenant_context,
    apply_tenant_scope,
    require_database_context,
)
from twobrain_rec_server.normalization.service import (
    activate_due_normalization_retry,
    cleanup_normalization_attempt,
    cleanup_unpublished_normalization_attempts,
    inventory_playback_backfill_page,
    mark_playback_backfill_blocked,
    recover_expired_normalization_job,
    recover_missing_ready_normalization_job,
)
from twobrain_rec_server.normalization.statuses import (
    BackfillState,
    JobState,
    NormalizationReason,
    TriggerKind,
)
from twobrain_rec_server.processing.fences import meeting_is_deleted_or_deleting
from twobrain_rec_server.workflows.temporal_client import (
    cancel_workflow_best_effort,
    connect_temporal_client,
    playback_normalization_workflow_id,
    start_playback_normalization_workflow,
)


@dataclass(frozen=True, slots=True)
class NormalizationDispatchResult:
    attempted: bool = False
    started: bool = False
    reused: bool = False


@dataclass(frozen=True, slots=True)
class NormalizationLeaseResult:
    claimed: bool
    reused: bool
    owner_sha256: str | None = None


@dataclass(frozen=True, slots=True)
class NormalizationPickupCandidate:
    job_id: UUID
    tenant_scope: TenantScope
    state: str


@dataclass(frozen=True, slots=True)
class NormalizationCleanupCandidate:
    attempt_id: UUID
    job_id: UUID
    tenant_scope: TenantScope
    state: str


@dataclass(frozen=True, slots=True)
class BackfillWorkspaceCandidate:
    tenant_scope: TenantScope


@dataclass(frozen=True, slots=True)
class NormalizationReconcileResult:
    workspaces_enumerated: int = 0
    inventory_evaluated: int = 0
    inventory_completed: int = 0
    inventory_blocked: int = 0
    enumerated: int = 0
    dispatched: int = 0
    reused: int = 0
    recovered: int = 0
    cleaned: int = 0
    ready_verified: int = 0


def _aware_utc(value: datetime) -> datetime:
    return value if value.tzinfo is not None else value.replace(tzinfo=UTC)


def _dispatch_lease_duration(settings: Settings) -> timedelta:
    return timedelta(
        seconds=max(120, int(settings.playback_normalization_reconcile_interval_seconds) * 3)
    )


async def claim_due_normalization_job(
    *,
    db: AsyncSession,
    job_id: UUID,
    lease_owner: str,
    lease_duration: timedelta,
    now: datetime | None = None,
) -> NormalizationLeaseResult:
    require_database_context(
        db,
        allowed_context_kinds=frozenset({"request", "worker"}),
    )
    current_time = now or datetime.now(UTC)
    if current_time.tzinfo is None or current_time.utcoffset() is None:
        raise ValueError("now must be timezone-aware")
    if not lease_owner.strip() or lease_duration <= timedelta(0):
        raise ValueError("lease owner and duration must be explicit")
    owner_sha256 = sha256(lease_owner.encode("utf-8")).hexdigest()
    job = await db.scalar(
        select(PlaybackNormalizationJob)
        .where(PlaybackNormalizationJob.id == job_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if job is None:
        return NormalizationLeaseResult(claimed=False, reused=False)
    if job.state == JobState.READY.value:
        return NormalizationLeaseResult(claimed=False, reused=True)
    if job.state != JobState.QUEUED.value:
        return NormalizationLeaseResult(claimed=False, reused=False)
    if job.trigger_kind == TriggerKind.LEGACY_BACKFILL.value:
        run = (
            await db.get(PlaybackBackfillRun, job.backfill_run_id)
            if job.backfill_run_id is not None
            else None
        )
        if (
            run is None
            or run.inventory_completed_at is None
            or run.state
            not in {
                BackfillState.INVENTORY_COMPLETE.value,
                BackfillState.DISPATCHING.value,
                BackfillState.COMPLETE.value,
            }
        ):
            return NormalizationLeaseResult(claimed=False, reused=False)
    if job.next_attempt_at is not None and _aware_utc(job.next_attempt_at) > current_time:
        return NormalizationLeaseResult(claimed=False, reused=False)
    if job.lease_expires_at is not None and _aware_utc(job.lease_expires_at) > current_time:
        return NormalizationLeaseResult(claimed=False, reused=True)
    job.lease_owner_sha256 = owner_sha256
    job.lease_expires_at = current_time + lease_duration
    job.last_heartbeat_at = current_time
    await db.commit()
    return NormalizationLeaseResult(
        claimed=True,
        reused=False,
        owner_sha256=owner_sha256,
    )


async def _release_dispatch_lease(
    db: AsyncSession,
    *,
    job_id: UUID,
    owner_sha256: str | None,
) -> None:
    await db.rollback()
    job = await db.scalar(
        select(PlaybackNormalizationJob)
        .where(PlaybackNormalizationJob.id == job_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if job is None or (owner_sha256 is not None and job.lease_owner_sha256 != owner_sha256):
        return
    job.lease_owner_sha256 = None
    job.lease_expires_at = None
    await db.commit()


async def dispatch_normalization_after_accepted_commit(
    *,
    db: AsyncSession | None,
    settings: Settings,
    tenant_scope: TenantScope,
    media_revision_id: UUID | None,
    temporal_client: object | None = None,
    lease_owner: str = "accepted-source-post-commit",
    now: datetime | None = None,
) -> NormalizationDispatchResult:
    if (
        db is None
        or media_revision_id is None
        or not settings.playback_normalization_enabled
        or not settings.playback_normalization_automatic_dispatch_enabled
    ):
        return NormalizationDispatchResult()
    require_database_context(
        db,
        allowed_context_kinds=frozenset({"request", "worker"}),
        workspace_id=tenant_scope.workspace_id,
    )
    current_time = now or datetime.now(UTC)
    job = await db.scalar(
        select(PlaybackNormalizationJob).where(
            PlaybackNormalizationJob.workspace_id == tenant_scope.workspace_id,
            PlaybackNormalizationJob.media_revision_id == media_revision_id,
        )
    )
    if job is None:
        return NormalizationDispatchResult(attempted=True)
    if job.state == JobState.RETRY_WAIT.value:
        await activate_due_normalization_retry(db, job_id=job.id, now=current_time)
    lease = await claim_due_normalization_job(
        db=db,
        job_id=job.id,
        lease_owner=lease_owner,
        lease_duration=_dispatch_lease_duration(settings),
        now=current_time,
    )
    if not lease.claimed:
        return NormalizationDispatchResult(attempted=True, reused=lease.reused)
    started = None
    deterministic_workflow_id = playback_normalization_workflow_id(media_revision_id)
    try:
        job = await db.get(PlaybackNormalizationJob, job.id)
        if job is None:
            return NormalizationDispatchResult(attempted=True)
        if temporal_client is None:
            if not settings.temporal_address:
                await _release_dispatch_lease(
                    db,
                    job_id=job.id,
                    owner_sha256=lease.owner_sha256,
                )
                return NormalizationDispatchResult(attempted=True)
            temporal_client = await connect_temporal_client(settings)
        started = await start_playback_normalization_workflow(
            temporal_client=temporal_client,
            settings=settings,
            job_id=job.id,
            meeting_id=job.meeting_id,
            media_revision_id=job.media_revision_id,
            tenant_scope=tenant_scope,
            profile_version=job.profile_version,
            validation_version=job.validation_version,
        )
        job_id = job.id
        meeting_id = job.meeting_id
        await db.rollback()
        meeting = await db.scalar(
            select(Meeting)
            .where(
                Meeting.workspace_id == tenant_scope.workspace_id,
                Meeting.id == meeting_id,
            )
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        job = await db.scalar(
            select(PlaybackNormalizationJob)
            .where(PlaybackNormalizationJob.id == job_id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
        handoff_valid = (
            meeting is not None
            and not meeting_is_deleted_or_deleting(meeting)
            and job is not None
            and job.state in {
                JobState.QUEUED.value,
                JobState.RUNNING.value,
                JobState.PUBLISHING.value,
                JobState.READY.value,
            }
            and (
                job.state != JobState.QUEUED.value
                or (
                    job.lease_owner_sha256 == lease.owner_sha256
                    and job.lease_expires_at is not None
                    and _aware_utc(job.lease_expires_at) > current_time
                )
            )
        )
        meeting_invalid = meeting is None or meeting_is_deleted_or_deleting(meeting)
        job_invalid = job is None or job.state not in {
            JobState.QUEUED.value,
            JobState.RUNNING.value,
            JobState.PUBLISHING.value,
            JobState.READY.value,
        }
        if not handoff_valid:
            await db.rollback()
            cancel_reused = meeting_invalid or job_invalid
            if not started.reused or cancel_reused:
                await cancel_workflow_best_effort(temporal_client, started.workflow_id)
            return NormalizationDispatchResult(attempted=True)
        if started.run_id is not None:
            job.workflow_run_id = started.run_id
        await db.commit()
        return NormalizationDispatchResult(
            attempted=True,
            started=not started.reused,
            reused=started.reused,
        )
    except Exception:
        if temporal_client is not None:
            await cancel_workflow_best_effort(
                temporal_client,
                started.workflow_id if started is not None else deterministic_workflow_id,
            )
        await _release_dispatch_lease(
            db,
            job_id=job.id,
            owner_sha256=lease.owner_sha256,
        )
        return NormalizationDispatchResult(attempted=True)


async def enumerate_normalization_pickup_candidates(
    db: AsyncSession,
    *,
    now: datetime,
    batch_size: int,
    recover_worker_interrupted: bool = False,
) -> list[NormalizationPickupCandidate]:
    require_database_context(
        db,
        allowed_context_kinds=frozenset({"maintenance"}),
        maintenance_operation="playback_normalization_dispatch",
    )
    if not 1 <= batch_size <= 25:
        raise ValueError("batch_size must be between 1 and 25")
    lease_available = or_(
        PlaybackNormalizationJob.lease_expires_at.is_(None),
        PlaybackNormalizationJob.lease_expires_at <= now,
    )
    queued_due = and_(
        PlaybackNormalizationJob.state == JobState.QUEUED.value,
        or_(
            PlaybackNormalizationJob.next_attempt_at.is_(None),
            PlaybackNormalizationJob.next_attempt_at <= now,
        ),
        lease_available,
    )
    expired_running = and_(
        PlaybackNormalizationJob.state.in_([JobState.RUNNING.value, JobState.PUBLISHING.value]),
        PlaybackNormalizationJob.lease_expires_at.is_not(None),
        PlaybackNormalizationJob.lease_expires_at <= now,
    )
    due_retry = and_(
        PlaybackNormalizationJob.state == JobState.RETRY_WAIT.value,
        PlaybackNormalizationJob.next_attempt_at.is_not(None),
        PlaybackNormalizationJob.next_attempt_at <= now,
    )
    worker_interrupted_retry = and_(
        PlaybackNormalizationJob.state == JobState.RETRY_WAIT.value,
        PlaybackNormalizationJob.reason_code == NormalizationReason.WORKER_INTERRUPTED.value,
        PlaybackNormalizationJob.next_attempt_at.is_not(None),
        PlaybackNormalizationJob.next_attempt_at > now,
    )
    backfill_dispatchable = or_(
        PlaybackNormalizationJob.trigger_kind != TriggerKind.LEGACY_BACKFILL.value,
        exists().where(
            PlaybackBackfillRun.id == PlaybackNormalizationJob.backfill_run_id,
            PlaybackBackfillRun.inventory_completed_at.is_not(None),
            PlaybackBackfillRun.state.in_(
                (
                    BackfillState.INVENTORY_COMPLETE.value,
                    BackfillState.DISPATCHING.value,
                    BackfillState.COMPLETE.value,
                )
            ),
        ),
    )
    rows = (
        await db.execute(
            select(
                PlaybackNormalizationJob.id,
                PlaybackNormalizationJob.state,
                PlaybackNormalizationJob.priority_class,
                PlaybackNormalizationJob.next_attempt_at,
                PlaybackNormalizationJob.organization_id,
                PlaybackNormalizationJob.requested_by_user_id,
                PlaybackNormalizationJob.source_device_id,
                PlaybackNormalizationJob.workspace_id,
            )
            .where(
                backfill_dispatchable,
                or_(
                    queued_due,
                    expired_running,
                    due_retry,
                    worker_interrupted_retry if recover_worker_interrupted else False,
                ),
            )
            .order_by(
                case(
                    (PlaybackNormalizationJob.priority_class == "new_ingest", 0),
                    (PlaybackNormalizationJob.priority_class == "due_retry", 1),
                    else_=2,
                ),
                PlaybackNormalizationJob.next_attempt_at,
                PlaybackNormalizationJob.last_heartbeat_at,
                PlaybackNormalizationJob.created_at,
                PlaybackNormalizationJob.id,
            )
            .limit(batch_size)
        )
    ).all()
    return [
        NormalizationPickupCandidate(
            job_id=row.id,
            state=row.state,
            tenant_scope=TenantScope(
                organization_id=row.organization_id,
                workspace_id=row.workspace_id,
                user_id=row.requested_by_user_id,
                device_id=row.source_device_id,
            ),
        )
        for row in rows
    ]


async def enumerate_ready_normalization_candidates(
    db: AsyncSession,
    *,
    batch_size: int,
) -> list[NormalizationPickupCandidate]:
    require_database_context(
        db,
        allowed_context_kinds=frozenset({"maintenance"}),
        maintenance_operation="playback_normalization_dispatch",
    )
    if not 1 <= batch_size <= 25:
        raise ValueError("batch_size must be between 1 and 25")
    rows = (
        await db.execute(
            select(
                PlaybackNormalizationJob.id,
                PlaybackNormalizationJob.state,
                PlaybackNormalizationJob.organization_id,
                PlaybackNormalizationJob.requested_by_user_id,
                PlaybackNormalizationJob.source_device_id,
                PlaybackNormalizationJob.workspace_id,
            )
            .where(PlaybackNormalizationJob.state == JobState.READY.value)
            .order_by(
                PlaybackNormalizationJob.last_heartbeat_at.asc().nulls_first(),
                PlaybackNormalizationJob.ready_at,
                PlaybackNormalizationJob.created_at,
                PlaybackNormalizationJob.id,
            )
            .limit(batch_size)
        )
    ).all()
    return [
        NormalizationPickupCandidate(
            job_id=row.id,
            state=row.state,
            tenant_scope=TenantScope(
                organization_id=row.organization_id,
                workspace_id=row.workspace_id,
                user_id=row.requested_by_user_id,
                device_id=row.source_device_id,
            ),
        )
        for row in rows
    ]


async def enumerate_normalization_cleanup_candidates(
    db: AsyncSession,
    *,
    batch_size: int,
) -> list[NormalizationCleanupCandidate]:
    require_database_context(
        db,
        allowed_context_kinds=frozenset({"maintenance"}),
        maintenance_operation="playback_normalization_dispatch",
    )
    if not 1 <= batch_size <= 25:
        raise ValueError("batch_size must be between 1 and 25")
    if db.get_bind().dialect.name == "postgresql":
        rows = (
            await db.execute(
                text(
                    """
                    select attempt_id, job_id, organization_id, workspace_id,
                           user_id, device_id, attempt_state
                    from rec_playback_normalization_cleanup_page(:page_size)
                    """
                ),
                {"page_size": batch_size},
            )
        ).all()
    else:
        rows = (
            await db.execute(
                select(
                    PlaybackNormalizationAttempt.id.label("attempt_id"),
                    PlaybackNormalizationJob.id.label("job_id"),
                    PlaybackNormalizationJob.organization_id,
                    PlaybackNormalizationJob.workspace_id,
                    PlaybackNormalizationJob.requested_by_user_id.label("user_id"),
                    PlaybackNormalizationJob.source_device_id.label("device_id"),
                    PlaybackNormalizationAttempt.state.label("attempt_state"),
                )
                .join(
                    PlaybackNormalizationJob,
                    PlaybackNormalizationJob.id == PlaybackNormalizationAttempt.job_id,
                )
                .where(
                    PlaybackNormalizationAttempt.state.in_(
                        (
                            "local_preparing",
                            "uploaded",
                            "cleanup_pending",
                            "purged",
                        )
                    ),
                    or_(
                        PlaybackNormalizationAttempt.state != "purged",
                        PlaybackNormalizationAttempt.cleaned_at.is_(None),
                    ),
                    or_(
                        PlaybackNormalizationJob.state.not_in(
                            (JobState.RUNNING.value, JobState.PUBLISHING.value)
                        ),
                        PlaybackNormalizationJob.lease_expires_at.is_(None),
                        PlaybackNormalizationJob.lease_expires_at <= datetime.now(UTC),
                    ),
                )
                .order_by(
                    PlaybackNormalizationAttempt.updated_at.asc().nulls_first(),
                    PlaybackNormalizationAttempt.id,
                )
                .limit(batch_size)
            )
        ).all()
    return [
        NormalizationCleanupCandidate(
            attempt_id=_as_uuid(row.attempt_id),
            job_id=_as_uuid(row.job_id),
            state=row.attempt_state,
            tenant_scope=TenantScope(
                organization_id=_as_uuid(row.organization_id),
                workspace_id=_as_uuid(row.workspace_id),
                user_id=_as_uuid(row.user_id),
                device_id=_as_uuid(row.device_id),
            ),
        )
        for row in rows
    ]


def _as_uuid(value: object) -> UUID:
    return value if isinstance(value, UUID) else UUID(str(value))


async def enumerate_backfill_workspace_candidates(
    db: AsyncSession,
    *,
    after_workspace_id: UUID | None,
    page_size: int,
) -> list[BackfillWorkspaceCandidate]:
    """Return only safe scope IDs for one globally bounded workspace page."""

    require_database_context(
        db,
        allowed_context_kinds=frozenset({"maintenance"}),
        maintenance_operation="playback_normalization_inventory",
    )

    if not 1 <= page_size <= 50:
        raise ValueError("page_size must be between 1 and 50")
    if db.get_bind().dialect.name == "postgresql":
        rows = (
            await db.execute(
                text(
                    """
                    select organization_id, workspace_id, user_id, device_id
                    from rec_playback_normalization_workspace_page(
                        :after_workspace_id,
                        :page_size
                    )
                    """
                ),
                {
                    "after_workspace_id": after_workspace_id,
                    "page_size": page_size,
                },
            )
        ).all()
    else:
        seed_meeting_id = (
            select(Meeting.id)
            .where(Meeting.workspace_id == Workspace.id)
            .order_by(Meeting.created_at, Meeting.id)
            .limit(1)
            .correlate(Workspace)
            .scalar_subquery()
        )
        statement = (
            select(
                Workspace.organization_id,
                Workspace.id.label("workspace_id"),
                Meeting.created_by_user_id.label("user_id"),
                Meeting.device_id,
            )
            .join(Meeting, Meeting.id == seed_meeting_id)
            .order_by(Workspace.id)
            .limit(page_size)
        )
        if after_workspace_id is not None:
            statement = statement.where(Workspace.id > after_workspace_id)
        rows = (await db.execute(statement)).all()
    return [
        BackfillWorkspaceCandidate(
            tenant_scope=TenantScope(
                organization_id=_as_uuid(row.organization_id),
                workspace_id=_as_uuid(row.workspace_id),
                user_id=_as_uuid(row.user_id),
                device_id=_as_uuid(row.device_id),
            )
        )
        for row in rows
    ]


async def _inventory_legacy_workspaces(
    *,
    sessionmaker: async_sessionmaker[AsyncSession],
    settings: Settings,
    now: datetime,
    actor_id: str,
) -> tuple[int, int, int, int]:
    workspaces_enumerated = inventory_evaluated = inventory_completed = 0
    inventory_blocked = 0
    cursor: UUID | None = None
    workspace_page_size = int(settings.playback_normalization_workspace_page_size)
    while True:
        async with sessionmaker() as maintenance_db:
            await apply_tenant_context(
                maintenance_db,
                MaintenanceTenantContext(
                    operation_name="playback_normalization_inventory",
                    actor_id=actor_id,
                    reason_category="automatic_backfill",
                    feature_area="playback_normalization",
                ),
            )
            workspace_page = await enumerate_backfill_workspace_candidates(
                maintenance_db,
                after_workspace_id=cursor,
                page_size=workspace_page_size,
            )
        for candidate in workspace_page:
            workspaces_enumerated += 1
            try:
                async with sessionmaker() as db:
                    await apply_tenant_scope(db, candidate.tenant_scope, context_kind="worker")
                    result = await inventory_playback_backfill_page(
                        db,
                        workspace_id=candidate.tenant_scope.workspace_id,
                        page_size=int(settings.playback_normalization_inventory_page_size),
                        now=now,
                    )
                inventory_evaluated += result.evaluated
                inventory_completed += int(result.inventory_completed)
            except Exception:
                inventory_blocked += 1
                try:
                    async with sessionmaker() as db:
                        await apply_tenant_scope(
                            db,
                            candidate.tenant_scope,
                            context_kind="worker",
                        )
                        await mark_playback_backfill_blocked(
                            db,
                            workspace_id=candidate.tenant_scope.workspace_id,
                            now=now,
                        )
                except Exception:
                    pass
        if len(workspace_page) < workspace_page_size:
            break
        cursor = workspace_page[-1].tenant_scope.workspace_id
    return (
        workspaces_enumerated,
        inventory_evaluated,
        inventory_completed,
        inventory_blocked,
    )


async def _storage_object_exists(storage: object, object_key: str) -> bool:
    exists_async = getattr(storage, "object_exists_async", None)
    if exists_async is not None:
        return bool(await exists_async(object_key))
    exists = getattr(storage, "object_exists", None)
    if exists is None:
        raise RuntimeError("storage_unavailable")
    return bool(await to_thread.run_sync(lambda: exists(object_key)))


async def _verify_ready_job(
    db: AsyncSession,
    *,
    storage: object,
    job: PlaybackNormalizationJob,
    now: datetime,
) -> bool:
    require_database_context(db, allowed_context_kinds=frozenset({"worker"}))
    snapshot = await db.scalar(
        select(PlaybackNormalizationJob)
        .where(PlaybackNormalizationJob.id == job.id)
        .execution_options(populate_existing=True)
    )
    if snapshot is None or snapshot.state != JobState.READY.value:
        return False
    canonical = None
    if snapshot.canonical_track_artifact_id is not None:
        canonical = await db.scalar(
            select(TrackArtifact)
            .where(
                TrackArtifact.workspace_id == snapshot.workspace_id,
                TrackArtifact.meeting_id == snapshot.meeting_id,
                TrackArtifact.id == snapshot.canonical_track_artifact_id,
            )
            .execution_options(populate_existing=True)
        )
    present = canonical is not None and await _storage_object_exists(
        storage, canonical.storage_object_key
    )
    if not present:
        snapshot_id = snapshot.id
        await db.rollback()
        await recover_missing_ready_normalization_job(db, job_id=snapshot_id, now=now)
        return False

    # Storage I/O happens without database locks. Recheck the lifecycle fence
    # before touching the ready row so deletion cannot be followed by a stale
    # heartbeat write or a ready-state resurrection.
    await db.rollback()
    meeting = await db.scalar(
        select(Meeting)
        .where(
            Meeting.workspace_id == snapshot.workspace_id,
            Meeting.id == snapshot.meeting_id,
        )
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if meeting is None or meeting_is_deleted_or_deleting(meeting):
        await db.rollback()
        return False
    current = await db.scalar(
        select(PlaybackNormalizationJob)
        .where(
            PlaybackNormalizationJob.workspace_id == snapshot.workspace_id,
            PlaybackNormalizationJob.id == snapshot.id,
        )
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if (
        current is None
        or current.state != JobState.READY.value
        or current.canonical_track_artifact_id != snapshot.canonical_track_artifact_id
    ):
        await db.rollback()
        return False
    current.last_heartbeat_at = now
    await db.commit()
    return True


async def reconcile_normalization_jobs(
    *,
    sessionmaker: async_sessionmaker[AsyncSession],
    settings: Settings,
    storage: object,
    temporal_client: object | None = None,
    now: datetime | None = None,
    actor_id: str = "rec-media-worker",
    recover_worker_interrupted: bool = False,
) -> NormalizationReconcileResult:
    if not (
        settings.playback_normalization_enabled
        and settings.playback_normalization_automatic_dispatch_enabled
    ):
        return NormalizationReconcileResult()
    current_time = now or datetime.now(UTC)
    batch_size = int(settings.playback_normalization_dispatch_batch_size)
    async with sessionmaker() as maintenance_db:
        await apply_tenant_context(
            maintenance_db,
            MaintenanceTenantContext(
                operation_name="playback_normalization_dispatch",
                actor_id=actor_id,
                reason_category="automatic_recovery",
                feature_area="playback_normalization",
            ),
        )
        ready_candidates = await enumerate_ready_normalization_candidates(
            maintenance_db,
            batch_size=batch_size,
        )
    async with sessionmaker() as maintenance_db:
        await apply_tenant_context(
            maintenance_db,
            MaintenanceTenantContext(
                operation_name="playback_normalization_dispatch",
                actor_id=actor_id,
                reason_category="automatic_recovery",
                feature_area="playback_normalization",
            ),
        )
        cleanup_candidates = await enumerate_normalization_cleanup_candidates(
            maintenance_db,
            batch_size=batch_size,
        )
    dispatched = reused = recovered = cleaned = ready_verified = 0
    for candidate in ready_candidates:
        async with sessionmaker() as db:
            await apply_tenant_scope(db, candidate.tenant_scope, context_kind="worker")
            job = await db.get(PlaybackNormalizationJob, candidate.job_id)
            if job is None or job.state != JobState.READY.value:
                continue
            try:
                if await _verify_ready_job(
                    db,
                    storage=storage,
                    job=job,
                    now=current_time,
                ):
                    ready_verified += 1
                else:
                    recovered += 1
            except Exception:
                continue

    for candidate in cleanup_candidates:
        async with sessionmaker() as db:
            await apply_tenant_scope(db, candidate.tenant_scope, context_kind="worker")
            cleaned += int(
                await cleanup_normalization_attempt(
                    db,
                    storage=storage,
                    attempt_id=candidate.attempt_id,
                    cleanup_reason="automatic_recovery",
                    now=current_time,
                )
            )

    async with sessionmaker() as maintenance_db:
        await apply_tenant_context(
            maintenance_db,
            MaintenanceTenantContext(
                operation_name="playback_normalization_dispatch",
                actor_id=actor_id,
                reason_category="automatic_recovery",
                feature_area="playback_normalization",
            ),
        )
        candidates = await enumerate_normalization_pickup_candidates(
            maintenance_db,
            now=current_time,
            batch_size=batch_size,
            recover_worker_interrupted=recover_worker_interrupted,
        )

    for candidate in candidates:
        async with sessionmaker() as db:
            await apply_tenant_scope(db, candidate.tenant_scope, context_kind="worker")
            job = await db.get(PlaybackNormalizationJob, candidate.job_id)
            if job is None:
                continue
            if job.state in {JobState.RUNNING.value, JobState.PUBLISHING.value}:
                recovery = await recover_expired_normalization_job(
                    db,
                    storage=storage,
                    job_id=job.id,
                    now=current_time,
                )
                if recovery is not None:
                    recovered += 1
                continue
            cleaned += await cleanup_unpublished_normalization_attempts(
                db,
                storage=storage,
                job_id=job.id,
            )
            if job.state == JobState.RETRY_WAIT.value:
                is_worker_restart_recovery = (
                    recover_worker_interrupted
                    and job.reason_code == NormalizationReason.WORKER_INTERRUPTED.value
                )
                if job.next_attempt_at is None or (
                    _aware_utc(job.next_attempt_at) > current_time
                    and not is_worker_restart_recovery
                ):
                    continue
                await activate_due_normalization_retry(
                    db,
                    job_id=job.id,
                    now=current_time,
                    recover_worker_interruption=is_worker_restart_recovery,
                )
            result = await dispatch_normalization_after_accepted_commit(
                db=db,
                settings=settings,
                tenant_scope=candidate.tenant_scope,
                media_revision_id=job.media_revision_id,
                temporal_client=temporal_client,
                lease_owner=f"{actor_id}:{job.id}",
                now=current_time,
            )
            if result.started:
                dispatched += 1
            if result.reused:
                reused += 1
    (
        workspaces_enumerated,
        inventory_evaluated,
        inventory_completed,
        inventory_blocked,
    ) = await _inventory_legacy_workspaces(
        sessionmaker=sessionmaker,
        settings=settings,
        now=current_time,
        actor_id=actor_id,
    )
    return NormalizationReconcileResult(
        workspaces_enumerated=workspaces_enumerated,
        inventory_evaluated=inventory_evaluated,
        inventory_completed=inventory_completed,
        inventory_blocked=inventory_blocked,
        enumerated=len(candidates),
        dispatched=dispatched,
        reused=reused,
        recovered=recovered,
        cleaned=cleaned,
        ready_verified=ready_verified,
    )
