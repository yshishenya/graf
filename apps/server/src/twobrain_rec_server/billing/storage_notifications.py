"""Finite storage observations; snapshot, generation and outbox commit together."""
from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import func, select, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.exc import DBAPIError, SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession

from twobrain_rec_server.billing.catalog import FREE_STORAGE_BYTES
from twobrain_rec_server.billing.database import require_billing_maintenance_database
from twobrain_rec_server.billing.events import BillingEvent, enqueue_billing_event
from twobrain_rec_server.billing.purchases import effective_paid_storage
from twobrain_rec_server.billing.storage import (
    lock_storage_workspace,
    project_active_playback_storage,
)
from twobrain_rec_server.db.models import (
    BillingNotificationPreference,
    ExternalIdentity,
    StorageNotificationScan,
    StorageNotificationState,
    UserIdentity,
    Workspace,
    WorkspaceMembership,
    WorkspaceSubscription,
)
from twobrain_rec_server.db.tenant_context import apply_tenant_context

STORAGE_SCAN_LIMIT = 100
STORAGE_SCAN_TIMEOUT = 60
_BANDS = {"normal": "normal", "80%": "80", "95%": "95", "full": "100"}
_RANK = {"normal": 0, "80": 1, "95": 2, "100": 3}


async def storage_notice_owner(
    db: AsyncSession, *, workspace_id: UUID, expected_recipient: UUID | None = None,
) -> tuple[UUID, str | None] | None:
    """None excludes closed/merged owners; missing permission/email still advances band."""
    workspace = await db.scalar(select(Workspace).where(Workspace.id == workspace_id))
    if workspace is None or workspace.kind != "personal" or workspace.owner_user_id is None:
        return None
    owner_id = workspace.owner_user_id
    if expected_recipient is not None and owner_id != expected_recipient:
        return None
    # Preferences writers lock identity even before the first preference row;
    # unlink locks the chosen external identity. NOWAIT avoids inversion with
    # account merge's identity-first locks; a conflict is a durable retry.
    owner = await db.scalar(select(UserIdentity).where(UserIdentity.id == owner_id).with_for_update(read=True, nowait=True))
    if owner is None or owner.status != "active" or owner.merged_into_user_id is not None:
        return None
    membership = await db.scalar(select(WorkspaceMembership).where(
        WorkspaceMembership.workspace_id == workspace_id, WorkspaceMembership.user_id == owner_id,
    ).with_for_update(read=True, nowait=True))
    subscription = await db.scalar(select(WorkspaceSubscription).where(
        WorkspaceSubscription.workspace_id == workspace_id,
    ).with_for_update(read=True, nowait=True))
    preference = await db.get(BillingNotificationPreference, owner_id)
    allowed = (membership is not None and membership.role == "owner" and membership.status == "active"
               and (subscription is None or subscription.billing_owner_id in {None, owner_id})
               and (preference is None or preference.optional_email_enabled is not False))
    if not allowed:
        return owner_id, None
    identity = await db.scalar(select(ExternalIdentity).where(
        ExternalIdentity.user_id == owner_id, ExternalIdentity.is_active.is_(True),
        ExternalIdentity.is_verified.is_(True), ExternalIdentity.email.is_not(None), ExternalIdentity.email != "",
    ).order_by(ExternalIdentity.email, ExternalIdentity.id).limit(1).with_for_update(read=True, nowait=True))
    return owner_id, identity.email if identity is not None else None



async def observe_storage_workspace(db: AsyncSession, *, workspace_id: UUID) -> str:
    """Caller holds the cursor before its savepoint; never commit here."""
    await lock_storage_workspace(db, workspace_id)
    workspace = await db.scalar(select(Workspace).where(Workspace.id == workspace_id).with_for_update())
    if workspace is None or workspace.kind != "personal":
        return "skipped"
    subscription = await db.scalar(select(WorkspaceSubscription).where(
        WorkspaceSubscription.workspace_id == workspace_id,
    ).with_for_update())
    state = await db.scalar(select(StorageNotificationState).where(
        StorageNotificationState.workspace_id == workspace_id,
    ).with_for_update())
    owner = await storage_notice_owner(db, workspace_id=workspace_id)
    if owner is None:
        return "skipped"
    if subscription is not None and subscription.plan_code not in {"free", "trial", "personal"}:
        raise ValueError("storage capacity unavailable")
    if subscription is not None and subscription.plan_code in {"trial", "personal"}:
        cutoff = (WorkspaceSubscription.trial_ends_at if subscription.plan_code == "trial"
                  else WorkspaceSubscription.paid_through)
        if await db.scalar(select(cutoff.is_not(None) & func.isfinite(cutoff)).where(
            WorkspaceSubscription.workspace_id == workspace_id,
        )) is not True:
            raise ValueError("storage capacity unavailable")
    now = datetime.now(UTC)
    capacity = await effective_paid_storage(db, subscription=subscription, now=now) if subscription else FREE_STORAGE_BYTES
    projection = await project_active_playback_storage(db, workspace_id=workspace_id, capacity_bytes=capacity)
    band = _BANDS[projection.threshold]
    previous = state.band if state is not None and state.owner_user_id == owner[0] else "normal"
    rise = _RANK[band] > _RANK[previous]
    if state is None:
        state = StorageNotificationState(workspace_id=workspace_id, generation=0)
        db.add(state)
    state.owner_user_id, state.band, state.observed_at = owner[0], band, now
    if rise:
        state.generation += 1
        if owner[1] is not None:
            await enqueue_billing_event(
                db, workspace_id=workspace_id, recipient_id=owner[0], event_type=BillingEvent.STORAGE_THRESHOLD,
                subject_ref=f"{workspace_id.hex}:{state.generation}:{band}",
                payload={"storage_level": band, "storage_used_bytes": str(projection.used_bytes),
                         "storage_capacity_bytes": str(capacity),
                         "storage_observed_at": now.astimezone(ZoneInfo("Europe/Moscow")).strftime("%d.%m.%Y %H:%M"),
                         "action_path": "/billing/usage"},
            )
    await db.flush()
    return "observed"


def _finish_scan(scan: StorageNotificationScan) -> None:
    scan.last_finished_summary = {
        "started_at": scan.cycle_started_at.isoformat(), "finished_at": datetime.now(UTC).isoformat(),
        **{k: getattr(scan, k) for k in ("attempted", "observed", "skipped", "failed")},
        "incomplete": scan.failed > 0,
    }
    scan.cycle_started_at = scan.upper_workspace_id = scan.after_workspace_id = None


async def reconcile_storage_notifications(sessionmaker, context) -> dict[str, int]:
    """At most 100 committed candidates, with one durable finite cursor, in 60s."""
    counters = {"storage_attempted": 0, "storage_observed": 0, "storage_skipped": 0,
                "storage_failed": 0, "storage_finished": 0, "storage_incomplete": 0}
    try:
        async with asyncio.timeout(STORAGE_SCAN_TIMEOUT):
            for _ in range(STORAGE_SCAN_LIMIT):
                async with sessionmaker() as db:
                    async with db.begin():
                        await apply_tenant_context(db, context)
                        await db.execute(text("SET LOCAL statement_timeout = '2s'"))
                        await db.execute(text("SET LOCAL lock_timeout = '1s'"))
                        await require_billing_maintenance_database(db)
                        await db.execute(insert(StorageNotificationScan).values(id=1).on_conflict_do_nothing())
                        scan = await db.scalar(select(StorageNotificationScan).where(StorageNotificationScan.id == 1).with_for_update())
                        if scan.cycle_started_at is None:
                            started = datetime.now(UTC)
                            upper = await db.scalar(select(Workspace.id).where(
                                Workspace.kind == "personal", Workspace.created_at <= started,
                            ).order_by(Workspace.id.desc()).limit(1))
                            scan.cycle_started_at, scan.upper_workspace_id = started, upper
                            for key in ("attempted", "observed", "skipped", "failed"):
                                setattr(scan, key, 0)
                            scan.last_error_code = None
                        candidate = None
                        if scan.upper_workspace_id is not None:
                            query = select(Workspace.id).where(
                                Workspace.kind == "personal", Workspace.created_at <= scan.cycle_started_at,
                                Workspace.id <= scan.upper_workspace_id,
                            ).order_by(Workspace.id).limit(1)
                            if scan.after_workspace_id is not None:
                                query = query.where(Workspace.id > scan.after_workspace_id)
                            candidate = await db.scalar(query)
                        if candidate is None:
                            _finish_scan(scan)
                            finished_incomplete = scan.failed > 0
                        else:
                            error = None
                            try:
                                async with db.begin_nested():
                                    result = await observe_storage_workspace(db, workspace_id=candidate)
                            except (SQLAlchemyError, ValueError) as exc:
                                if isinstance(exc, DBAPIError) and exc.connection_invalidated:
                                    raise
                                code = getattr(getattr(exc, "orig", None), "sqlstate", None)
                                error = {"55P03": "lock_timeout", "57014": "query_timeout"}.get(
                                    code, "database_error" if isinstance(exc, SQLAlchemyError) else "snapshot_unavailable",
                                )
                                result = "failed"
                            # A rolled-back savepoint released Workspace locks. Write ONLY cursor metadata here.
                            scan.attempted += 1
                            setattr(scan, result, getattr(scan, result) + 1)
                            scan.after_workspace_id = candidate
                            if error is not None:
                                scan.last_error_code = error
                    # Count only after the commit has returned successfully.
                    if candidate is None:
                        counters["storage_finished"] = 1
                        counters["storage_incomplete"] = int(finished_incomplete)
                        break
                    counters["storage_attempted"] += 1
                    counters[f"storage_{result}"] += 1
                    if result == "failed":
                        counters["storage_incomplete"] = 1
    except TimeoutError:
        counters["storage_incomplete"] = 1
    return counters
