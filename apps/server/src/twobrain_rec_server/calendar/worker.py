"""Maintenance reconciler for queued calendar syncs."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from twobrain_rec_server.auth.context import TenantScope
from twobrain_rec_server.calendar.caldav import CalDAVAdapter
from twobrain_rec_server.calendar.capabilities import provider_adapter_family
from twobrain_rec_server.calendar.google import (
    GoogleCalendarAdapter,
    GoogleCalendarRuntime,
    google_oauth_config_from_settings,
)
from twobrain_rec_server.calendar.owner_content import owner_content_key_from_settings
from twobrain_rec_server.calendar.providers import CalendarProvider
from twobrain_rec_server.calendar.sync import future_sync_horizon, run_calendar_provider_sync
from twobrain_rec_server.config import Settings
from twobrain_rec_server.db.models import CalendarSource, Workspace
from twobrain_rec_server.db.session import create_engine, create_sessionmaker
from twobrain_rec_server.db.tenant_context import (
    MaintenanceTenantContext,
    apply_tenant_context,
    apply_tenant_scope,
)

logger = logging.getLogger(__name__)

CALENDAR_SYNC_OPERATION = "calendar_sync_reconciliation"
CALENDAR_SYNC_POLL_SECONDS = 15
CALENDAR_SYNC_INTERVAL_SECONDS = 60
CALENDAR_SYNC_LEASE_SECONDS = 5 * 60
WORKER_DEVICE_ID = UUID(int=0)


def _google_provider(settings: Settings) -> CalendarProvider | None:
    config = google_oauth_config_from_settings(settings)
    if config is None:
        return None
    return GoogleCalendarRuntime(GoogleCalendarAdapter(config))


def provider_for_source(
    source: CalendarSource,
    settings: Settings,
    *,
    provider_factory: Callable[[str], CalendarProvider | None] | None = None,
) -> CalendarProvider | None:
    if provider_factory is not None:
        provider = provider_factory(source.provider_family)
        if provider is not None:
            return provider
    if source.provider_family == "google_calendar":
        return _google_provider(settings)
    if provider_adapter_family(source.provider_family) == "caldav":
        return CalDAVAdapter(source.provider_family)
    return None


async def run_one_calendar_sync(
    sessionmaker: async_sessionmaker[AsyncSession],
    settings: Settings,
    context: MaintenanceTenantContext,
    *,
    source_id: UUID | None = None,
    provider_factory: Callable[[str], CalendarProvider | None] | None = None,
    credential_encryption_key: bytes | None = None,
) -> bool:
    async with sessionmaker() as db:
        await apply_tenant_context(db, context)
        query = (
            select(CalendarSource, Workspace.organization_id)
            .join(Workspace, Workspace.id == CalendarSource.workspace_id)
            .where(CalendarSource.sync_state == "queued")
        )
        if source_id is not None:
            query = query.where(CalendarSource.id == source_id)
        row = (
            await db.execute(
                query.order_by(CalendarSource.last_sync_started_at, CalendarSource.id)
                .with_for_update(skip_locked=True)
                .limit(1)
            )
        ).first()
        if row is None:
            return False
        source, organization_id = row
        source.sync_state = "syncing"
        source.last_sync_started_at = datetime.now(UTC)
        source.last_safe_error_code = None
        claim = source.last_sync_started_at
        await db.commit()

    scope = TenantScope(
        organization_id=organization_id,
        workspace_id=source.workspace_id,
        user_id=source.owner_user_id,
        device_id=WORKER_DEVICE_ID,
    )
    provider = (
        provider_for_source(source, settings)
        if provider_factory is None
        else provider_for_source(source, settings, provider_factory=provider_factory)
    )
    key = credential_encryption_key or owner_content_key_from_settings(settings)
    async with sessionmaker() as db:
        await apply_tenant_scope(db, scope, context_kind="worker")
        if provider is None or key is None:
            current = await db.scalar(
                select(CalendarSource)
                .where(
                    CalendarSource.id == source.id,
                    CalendarSource.workspace_id == scope.workspace_id,
                    CalendarSource.owner_user_id == scope.user_id,
                )
                .with_for_update()
            )
            if (
                current is not None
                and current.last_sync_started_at == claim
                and current.connection_state == "active"
            ):
                current.sync_state = "stale" if current.last_successful_sync_at else "failed"
                current.last_safe_error_code = (
                    "provider_unavailable"
                    if provider is None
                    else "credential_encryption_unavailable"
                )
                current.last_sync_finished_at = datetime.now(UTC)
            await db.commit()
            return True
        try:
            await asyncio.wait_for(
                run_calendar_provider_sync(
                    db,
                    tenant_scope=scope,
                    source_id=source.id,
                    provider=provider,
                    credential_encryption_key=key,
                    expected_claim=claim,
                ),
                timeout=CALENDAR_SYNC_LEASE_SECONDS - 30,
            )
            await db.commit()
        except Exception:
            await db.rollback()
            await apply_tenant_scope(db, scope, context_kind="worker")
            current = await db.scalar(
                select(CalendarSource)
                .where(
                    CalendarSource.id == source.id,
                    CalendarSource.workspace_id == scope.workspace_id,
                    CalendarSource.owner_user_id == scope.user_id,
                )
                .with_for_update()
            )
            if (
                current is not None
                and current.sync_state == "syncing"
                and current.last_sync_started_at == claim
                and current.connection_state == "active"
            ):
                current.sync_state = "stale" if current.last_successful_sync_at else "failed"
                current.last_safe_error_code = "provider_unavailable"
                current.last_sync_finished_at = datetime.now(UTC)
            await db.commit()
            raise
    return True


def calendar_maintenance_context() -> MaintenanceTenantContext:
    return MaintenanceTenantContext(
        operation_name=CALENDAR_SYNC_OPERATION,
        actor_id="graf-maintenance",
        reason_category="calendar_provider_sync",
        feature_area="calendar",
    )


async def enqueue_due_calendar_syncs(
    sessionmaker: async_sessionmaker[AsyncSession],
    context: MaintenanceTenantContext,
    *,
    now: datetime | None = None,
) -> int:
    """Queue enabled sources and reclaim expired workers without reviving credentials."""

    current_time = now or datetime.now(UTC)
    horizon_start, horizon_end = future_sync_horizon(current_time)
    queued_count = 0
    async with sessionmaker() as db:
        await apply_tenant_context(db, context)
        sources = list(
            await db.scalars(
                select(CalendarSource)
                .where(
                    CalendarSource.provider_family.in_({"caldav_yandex", "google_calendar"}),
                    CalendarSource.connection_state == "active",
                    CalendarSource.disconnected_at.is_(None),
                    CalendarSource.credential_state == "sealed",
                    CalendarSource.sync_state.in_(
                        {
                            "syncing",
                            "never_synced",
                            "synced",
                            "stale",
                            "failed",
                            "failed_closed",
                            "provider_unavailable",
                            "rate_limited",
                        }
                    ),
                )
                .with_for_update(skip_locked=True)
            )
        )
        for source in sources:
            if source.sync_state == "failed_closed" and source.last_safe_error_code not in {
                "provider_unavailable",
                "credential_encryption_unavailable",
            }:
                continue
            if source.last_safe_error_code in {"invalid_credentials", "revoked_access"}:
                continue
            if source.sync_state == "syncing":
                started = source.last_sync_started_at
                if started is not None and current_time - started < timedelta(
                    seconds=CALENDAR_SYNC_LEASE_SECONDS
                ):
                    continue
                last_run = None
            else:
                last_run = source.last_sync_finished_at or source.last_sync_started_at
            if last_run is not None:
                if last_run.tzinfo is None:
                    last_run = last_run.replace(tzinfo=UTC)
                if current_time - last_run < timedelta(seconds=CALENDAR_SYNC_INTERVAL_SECONDS):
                    continue
            source.sync_horizon_start = horizon_start
            source.sync_horizon_end = horizon_end
            source.last_sync_started_at = current_time
            source.sync_state = "queued"
            source.last_safe_error_code = None
            queued_count += 1
        await db.commit()
    return queued_count


async def run_calendar_sync_reconciler(settings: Settings) -> None:
    """Continuously consume queued syncs with tenant-scoped worker sessions."""

    engine = create_engine(settings)
    sessionmaker = create_sessionmaker(engine)
    context = calendar_maintenance_context()
    try:
        while True:
            try:
                await enqueue_due_calendar_syncs(sessionmaker, context)
                processed = await run_one_calendar_sync(sessionmaker, settings, context)
            except asyncio.CancelledError:
                raise
            except Exception as error:
                logger.error(
                    "calendar sync reconciliation cycle failed; error_type=%s",
                    type(error).__name__,
                )
                processed = False
            if not processed:
                await asyncio.sleep(CALENDAR_SYNC_POLL_SECONDS)
    finally:
        await engine.dispose()
