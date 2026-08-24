from __future__ import annotations

from datetime import UTC, date, datetime

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from twobrain_rec_server.admin.queries import AdminWorkspaceContext
from twobrain_rec_server.db.models import (
    AdminAuditEvent,
    BillingNotificationDelivery,
    BillingOperation,
    MediaScribeJob,
    Meeting,
    ObservedProviderRefund,
    PlaybackBackfillRun,
    PlaybackNormalizationAttempt,
    PlaybackNormalizationJob,
    ProcessingWorkflow,
    PurgeJournal,
    StorageReservation,
    WorkspaceMembership,
    WorkspaceUsageDaily,
)
from twobrain_rec_server.normalization.statuses import (
    AttemptState,
    JobState,
    NormalizationReason,
)

METRIC_FAMILIES = ("adoption", "usage", "funnel", "reliability", "governance")


def metric_families() -> list[str]:
    return list(METRIC_FAMILIES)


async def get_admin_metrics(
    db: AsyncSession,
    *,
    context: AdminWorkspaceContext,
    family: str | None = None,
    date_from: date | None = None,
    date_to: date | None = None,
) -> dict[str, object]:
    active_users = int(
        await db.scalar(
            select(func.count())
            .select_from(WorkspaceMembership)
            .where(
                WorkspaceMembership.workspace_id == context.workspace_id,
                WorkspaceMembership.status == "active",
            )
        )
        or 0
    )
    usage_stmt = select(WorkspaceUsageDaily).where(
        WorkspaceUsageDaily.workspace_id == context.workspace_id
    )
    if date_from is not None:
        usage_stmt = usage_stmt.where(WorkspaceUsageDaily.usage_date >= date_from)
    if date_to is not None:
        usage_stmt = usage_stmt.where(WorkspaceUsageDaily.usage_date <= date_to)
    usage_rows = (await db.execute(usage_stmt)).scalars().all()
    recording_minutes = sum(row.recording_minutes for row in usage_rows)
    usage_window = _usage_date_window(usage_rows, date_from=date_from, date_to=date_to)
    usage_freshness = _usage_freshness(usage_rows)
    meetings_total = int(
        await db.scalar(
            select(func.count())
            .select_from(Meeting)
            .where(Meeting.workspace_id == context.workspace_id)
        )
        or 0
    )
    problem_meetings = int(
        await db.scalar(
            select(func.count())
            .select_from(Meeting)
            .where(
                Meeting.workspace_id == context.workspace_id,
                Meeting.processing_status.in_(("failed_terminal", "blocked")),
            )
        )
        or 0
    )
    audit_events = int(
        await db.scalar(
            select(func.count())
            .select_from(AdminAuditEvent)
            .where(AdminAuditEvent.workspace_id == context.workspace_id)
        )
        or 0
    )
    playback_normalization = await _playback_normalization_metrics(
        db,
        workspace_id=context.workspace_id,
    )
    processing_recovery = await _processing_recovery_metrics(
        db,
        workspace_id=context.workspace_id,
    )
    billing = await _billing_metrics(db, workspace_id=context.workspace_id)
    cards = [
        _card(
            "active_users",
            "adoption",
            "Активные пользователи",
            "Активные memberships",
            "workspace members",
            "identity",
            active_users,
            "/admin/users",
            date_window=usage_window,
        ),
        _card(
            "recording_minutes",
            "usage",
            "Минуты записи",
            "Сумма source-backed usage rollups",
            "workspace usage days",
            "usage_rollup",
            recording_minutes,
            "/admin/balance",
            date_window=usage_window,
            freshness=usage_freshness,
        ),
        _card(
            "server_known_meetings",
            "funnel",
            "Серверные встречи",
            "Встречи, принятые сервером",
            "meetings",
            "meeting_store",
            meetings_total,
            "/admin/files",
            date_window=usage_window,
        ),
        _card(
            "problem_meetings",
            "reliability",
            "Проблемные встречи",
            "Встречи с terminal/blocked processing",
            "meetings",
            "meeting_store",
            problem_meetings,
            "/admin/files",
            date_window=usage_window,
        ),
        _card(
            "playback_normalization_backlog",
            "reliability",
            "Очередь подготовки аудио",
            "Автоматическая очередь записей, которым ещё нужен готовый звук",
            "playback normalization jobs",
            "normalization_store",
            int(playback_normalization["backlog_total"]),
            "/admin/metrics?family=reliability",
            date_window=usage_window,
        ),
        _card(
            "processing_retryable_backlog",
            "reliability",
            "Ожидающие восстановления",
            "Retryable/unknown processing states with durable recovery data",
            "processing workflows",
            "processing_recovery",
            processing_recovery["retryable_backlog"],
            "/admin/metrics?family=reliability",
            date_window=usage_window,
        ),
        _card(
            "admin_audit_events",
            "governance",
            "События аудита",
            "Metadata-only admin audit events",
            "admin audit events",
            "audit_journal",
            audit_events,
            "/admin/audit",
            date_window=usage_window,
        ),
        _card(
            "billing_unknown_operations",
            "reliability",
            "Неизвестные платежные исходы",
            "Операции, ожидающие подтверждения YooKassa",
            "billing operations",
            "billing_reconciliation",
            billing["unknown_operations"],
            "/admin/metrics?family=reliability",
            date_window=usage_window,
        ),
        _card(
            "billing_notification_failures",
            "reliability",
            "Ошибки уведомлений",
            "Transactional delivery в retry/failed",
            "billing notification deliveries",
            "billing_notifications",
            billing["notification_failures"],
            "/admin/metrics?family=reliability",
            date_window=usage_window,
        ),
        _card(
            "billing_storage_reserved_bytes",
            "usage",
            "Зарезервированное хранилище",
            "Зарезервированные байты playback-архива",
            "storage reservations",
            "billing_storage",
            billing["storage_reserved_bytes"],
            "/admin/balance",
            date_window=usage_window,
        ),
        _card(
            "billing_observed_refunds",
            "governance",
            "Наблюдаемые возвраты",
            "Только provider-confirmed reconciliation, без refund mutation",
            "observed provider refunds",
            "billing_reconciliation",
            billing["observed_refunds"],
            "/admin/metrics?family=governance",
            date_window=usage_window,
        ),
    ]
    if family:
        cards = [card for card in cards if card["family"] == family]
    return {
        "metrics": cards,
        "playback_normalization": playback_normalization,
        "processing_recovery": processing_recovery,
        "billing": billing,
    }


async def _processing_recovery_metrics(
    db: AsyncSession,
    *,
    workspace_id,
) -> dict[str, object]:
    """Expose bounded operator signals, never provider payloads or identifiers."""

    workflow_states = {
        str(state): int(count)
        for state, count in (
            await db.execute(
                select(ProcessingWorkflow.status, func.count())
                .where(ProcessingWorkflow.workspace_id == workspace_id)
                .group_by(ProcessingWorkflow.status)
            )
        ).all()
    }
    retryable_states = ("waiting_retry", "failed_retryable", "blocked_unknown")
    retryable_backlog = sum(workflow_states.get(state, 0) for state in retryable_states)
    stale_due = int(
        await db.scalar(
            select(func.count())
            .select_from(ProcessingWorkflow)
            .where(
                ProcessingWorkflow.workspace_id == workspace_id,
                ProcessingWorkflow.status == "waiting_retry",
                ProcessingWorkflow.next_attempt_at.is_not(None),
                ProcessingWorkflow.next_attempt_at < datetime.now(UTC),
            )
        )
        or 0
    )
    duplicate_job_rows = int(
        await db.scalar(
            select(func.count())
            .select_from(
                select(MediaScribeJob.external_job_id)
                .where(
                    MediaScribeJob.workspace_id == workspace_id,
                    MediaScribeJob.external_job_id.is_not(None),
                )
                .group_by(MediaScribeJob.external_job_id)
                .having(func.count() > 1)
                .subquery()
            )
        )
        or 0
    )
    queue_states = {
        str(state): int(count)
        for state, count in (
            await db.execute(
                select(MediaScribeJob.provider_queue_state, func.count())
                .where(
                    MediaScribeJob.workspace_id == workspace_id,
                    MediaScribeJob.provider_queue_state.is_not(None),
                )
                .group_by(MediaScribeJob.provider_queue_state)
            )
        ).all()
    }
    return {
        "workflow_states": workflow_states,
        "retryable_backlog": retryable_backlog,
        "stale_due": stale_due,
        "duplicate_job_groups": duplicate_job_rows,
        "queue_state_buckets": queue_states,
        "fairness_bucket": "workspace_scoped",
    }


async def _billing_metrics(db: AsyncSession, *, workspace_id) -> dict[str, int]:
    operation_state_rows = (
        await db.execute(
            select(BillingOperation.state, func.count())
            .where(BillingOperation.workspace_id == workspace_id)
            .group_by(BillingOperation.state)
        )
    ).all()
    operation_states = {str(state): int(count) for state, count in operation_state_rows}
    notification_failures = int(
        await db.scalar(
            select(func.count())
            .select_from(BillingNotificationDelivery)
            .where(
                BillingNotificationDelivery.workspace_id == workspace_id,
                BillingNotificationDelivery.state.in_(("retry", "failed")),
            )
        )
        or 0
    )
    reserved_bytes = int(
        await db.scalar(
            select(func.coalesce(func.sum(StorageReservation.declared_bytes - StorageReservation.committed_bytes), 0))
            .where(
                StorageReservation.workspace_id == workspace_id,
                StorageReservation.state == "active",
            )
        )
        or 0
    )
    observed_refunds = int(
        await db.scalar(
            select(func.count())
            .select_from(ObservedProviderRefund)
            .where(ObservedProviderRefund.workspace_id == workspace_id)
        )
        or 0
    )
    return {
        "unknown_operations": operation_states.get("unknown", 0)
        + operation_states.get("provider_key_expired", 0),
        "notification_failures": notification_failures,
        "storage_reserved_bytes": max(0, reserved_bytes),
        "observed_refunds": observed_refunds,
    }


async def _playback_normalization_metrics(
    db: AsyncSession,
    *,
    workspace_id,
) -> dict[str, object]:
    run_states = {
        str(state): int(count)
        for state, count in (
            await db.execute(
                select(PlaybackBackfillRun.state, func.count())
                .where(PlaybackBackfillRun.workspace_id == workspace_id)
                .group_by(PlaybackBackfillRun.state)
                .order_by(PlaybackBackfillRun.state)
            )
        ).all()
    }
    job_states = {
        str(state): int(count)
        for state, count in (
            await db.execute(
                select(PlaybackNormalizationJob.state, func.count())
                .where(PlaybackNormalizationJob.workspace_id == workspace_id)
                .group_by(PlaybackNormalizationJob.state)
                .order_by(PlaybackNormalizationJob.state)
            )
        ).all()
    }
    allowed_reasons = {reason.value for reason in NormalizationReason}
    reason_counts = {
        str(reason): int(count)
        for reason, count in (
            await db.execute(
                select(PlaybackNormalizationJob.reason_code, func.count())
                .where(
                    PlaybackNormalizationJob.workspace_id == workspace_id,
                    PlaybackNormalizationJob.reason_code.is_not(None),
                )
                .group_by(PlaybackNormalizationJob.reason_code)
                .order_by(PlaybackNormalizationJob.reason_code)
            )
        ).all()
        if str(reason) in allowed_reasons
    }
    backlog_states = (
        JobState.QUEUED.value,
        JobState.RUNNING.value,
        JobState.PUBLISHING.value,
        JobState.RETRY_WAIT.value,
    )
    backlog_total = sum(job_states.get(state, 0) for state in backlog_states)
    oldest_created_at = await db.scalar(
        select(func.min(PlaybackNormalizationJob.created_at)).where(
            PlaybackNormalizationJob.workspace_id == workspace_id,
            PlaybackNormalizationJob.state.in_(backlog_states),
        )
    )
    oldest_age_seconds = 0
    if oldest_created_at is not None:
        if oldest_created_at.tzinfo is None:
            oldest_created_at = oldest_created_at.replace(tzinfo=UTC)
        oldest_age_seconds = max(
            0,
            int((datetime.now(UTC) - oldest_created_at).total_seconds()),
        )
    retry_cycle_buckets = {"0": 0, "1": 0, "2": 0, "3_plus": 0}
    for retry_cycle_count, count in (
        await db.execute(
            select(PlaybackNormalizationJob.retry_cycle_count, func.count())
            .where(PlaybackNormalizationJob.workspace_id == workspace_id)
            .group_by(PlaybackNormalizationJob.retry_cycle_count)
        )
    ).all():
        bucket = str(retry_cycle_count) if retry_cycle_count < 3 else "3_plus"
        retry_cycle_buckets[bucket] = retry_cycle_buckets.get(bucket, 0) + int(count)
    cleanup_pending_count = int(
        await db.scalar(
            select(func.count())
            .select_from(PlaybackNormalizationAttempt)
            .where(
                PlaybackNormalizationAttempt.workspace_id == workspace_id,
                PlaybackNormalizationAttempt.state == AttemptState.CLEANUP_PENDING.value,
            )
        )
        or 0
    )
    purge_journal_terminal_unknown_count = int(
        await db.scalar(
            select(func.count())
            .select_from(PurgeJournal)
            .where(
                PurgeJournal.workspace_id == workspace_id,
                PurgeJournal.state == "terminal_unknown",
            )
        )
        or 0
    )
    purge_journal_terminal_unknown_orphan_count = int(
        await db.scalar(
            select(func.count())
            .select_from(PurgeJournal)
            .where(
                PurgeJournal.workspace_id == workspace_id,
                PurgeJournal.state == "terminal_unknown",
                PurgeJournal.deletion_request_id.is_(None),
            )
        )
        or 0
    )
    last_safe_heartbeat_at = await db.scalar(
        select(func.max(PlaybackNormalizationJob.last_heartbeat_at)).where(
            PlaybackNormalizationJob.workspace_id == workspace_id
        )
    )
    if last_safe_heartbeat_at is not None and last_safe_heartbeat_at.tzinfo is None:
        last_safe_heartbeat_at = last_safe_heartbeat_at.replace(tzinfo=UTC)
    backfill_row = (
        await db.execute(
            select(
                func.coalesce(func.sum(PlaybackBackfillRun.evaluated_count), 0),
                func.coalesce(func.sum(PlaybackBackfillRun.preserve_valid_count), 0),
                func.coalesce(func.sum(PlaybackBackfillRun.validate_candidate_count), 0),
                func.coalesce(func.sum(PlaybackBackfillRun.normalize_source_count), 0),
                func.coalesce(func.sum(PlaybackBackfillRun.unavailable_source_count), 0),
                func.coalesce(func.sum(PlaybackBackfillRun.ready_count), 0),
                func.coalesce(func.sum(PlaybackBackfillRun.terminal_count), 0),
                func.coalesce(func.sum(PlaybackBackfillRun.cancelled_count), 0),
            ).where(PlaybackBackfillRun.workspace_id == workspace_id)
        )
    ).one()
    backfill_progress = {
        key: int(value)
        for key, value in zip(
            (
                "evaluated",
                "preserve_valid",
                "validate_candidate",
                "normalize_source",
                "unavailable_source",
                "ready",
                "terminal",
                "cancelled",
            ),
            backfill_row,
            strict=True,
        )
    }
    return {
        "run_states": run_states,
        "job_states": job_states,
        "reason_counts": reason_counts,
        "backlog_total": backlog_total,
        "oldest_backlog_age_seconds": oldest_age_seconds,
        "retry_cycle_buckets": retry_cycle_buckets,
        "cleanup_pending_count": cleanup_pending_count,
        "purge_journal_terminal_unknown_count": purge_journal_terminal_unknown_count,
        "purge_journal_terminal_unknown_orphan_count": purge_journal_terminal_unknown_orphan_count,
        "last_safe_heartbeat_at": (
            last_safe_heartbeat_at.isoformat() if last_safe_heartbeat_at is not None else None
        ),
        "backfill_progress": backfill_progress,
    }


def _card(
    metric_id: str,
    family: str,
    label: str,
    definition: str,
    denominator: str,
    source_category: str,
    value: int,
    drill_down_path: str,
    date_window: dict[str, str | None],
    freshness: str = "source_backed",
) -> dict[str, object]:
    return {
        "metric_id": metric_id,
        "family": family,
        "label": label,
        "definition": definition,
        "denominator": denominator,
        "source_category": source_category,
        "date_window": date_window,
        "freshness": freshness,
        "value": value,
        "drill_down_path": drill_down_path,
    }


def _usage_date_window(
    rows: list[WorkspaceUsageDaily],
    *,
    date_from: date | None,
    date_to: date | None,
) -> dict[str, str | None]:
    row_dates = sorted(row.usage_date for row in rows)
    return {
        "from": (date_from or (row_dates[0] if row_dates else None)).isoformat()
        if (date_from or row_dates)
        else None,
        "to": (date_to or (row_dates[-1] if row_dates else None)).isoformat()
        if (date_to or row_dates)
        else None,
    }


def _usage_freshness(rows: list[WorkspaceUsageDaily]) -> str:
    if not rows:
        return "unavailable"
    if all(row.freshness_state == "fresh" for row in rows):
        return "fresh"
    return "incomplete"
