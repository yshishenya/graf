"""One-shot, restart-safe billing maintenance projection.

The scheduler owns cadence; this function owns only bounded, idempotent DB
maintenance. It never creates a payment, changes provider authority, or sends
customer content.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from twobrain_rec_server.billing.catalog import ADDON_CAPACITY_BYTES, PERSONAL_STORAGE_BYTES
from twobrain_rec_server.billing.promotions import expire_promo_reservations
from twobrain_rec_server.billing.referral_rewards import mature_pending_credits
from twobrain_rec_server.billing.storage import (
    project_active_playback_storage,
    release_expired_storage_reservations,
)
from twobrain_rec_server.db.models import (
    BillingAuditEvent,
    BillingInvoice,
    BillingNotificationDelivery,
    BillingOperation,
    StorageReservation,
    WorkspaceSubscription,
)

STUCK_OPERATION_MAX_AGE = timedelta(minutes=30)
MAINTENANCE_BATCH_LIMIT = 100


def _snapshot_datetime(value: object) -> datetime | None:
    if not isinstance(value, str):
        return None
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        return None
    return parsed.astimezone(UTC)


async def _reconcile_storage_addon_operations(
    db: AsyncSession,
    *,
    current: datetime,
    workspace_id: UUID | None,
) -> dict[str, int]:
    """Project authoritative succeeded add-on operations into one capacity field.

    The current schema has no separate add-on row yet; the immutable operation
    snapshot is therefore the durable source and `WorkspaceSubscription` is
    the single serialized projection. Invalid or incomplete snapshots fail
    closed into an audit gap rather than silently changing quota.
    """
    query = (
        select(BillingOperation)
        .join(
            BillingInvoice,
            (BillingInvoice.operation_id == BillingOperation.id)
            & (BillingInvoice.workspace_id == BillingOperation.workspace_id),
        )
        .where(
            BillingOperation.kind == "storage_upgrade",
            BillingOperation.state == "succeeded",
        )
        .order_by(BillingOperation.updated_at, BillingOperation.id)
        .limit(MAINTENANCE_BATCH_LIMIT)
        .with_for_update()
    )
    if workspace_id is not None:
        query = query.where(BillingOperation.workspace_id == workspace_id)
    projected = scheduled = gaps = 0
    for operation in await db.scalars(query):
        snapshot = operation.request_snapshot or {}
        target = snapshot.get("addon_capacity_bytes", snapshot.get("capacity_bytes"))
        effective_at = _snapshot_datetime(snapshot.get("effective_at"))
        ends_at = _snapshot_datetime(snapshot.get("ends_at"))
        snapshot_cycle = snapshot.get("cycle")
        if (
            isinstance(target, bool)
            or not isinstance(target, int)
            or target not in ADDON_CAPACITY_BYTES
            or effective_at is None
            or ends_at is None
            or snapshot_cycle not in {"month", "year"}
        ):
            operation.state = "reconciliation_gap"
            db.add(
                BillingAuditEvent(
                    workspace_id=operation.workspace_id,
                    action="billing.maintenance_addon_projection",
                    target_kind="billing_operation",
                    target_ref=None,
                    outcome="gap",
                    reason_code="addon_snapshot_invalid",
                    metadata_json={"operation_kind": "storage_upgrade"},
                )
            )
            gaps += 1
            continue
        subscription = await db.scalar(
            select(WorkspaceSubscription)
            .where(WorkspaceSubscription.workspace_id == operation.workspace_id)
            .with_for_update()
        )
        if subscription is None or subscription.plan_code != "personal":
            operation.state = "reconciliation_gap"
            db.add(
                BillingAuditEvent(
                    workspace_id=operation.workspace_id,
                    action="billing.maintenance_addon_projection",
                    target_kind="billing_operation",
                    target_ref=None,
                    outcome="gap",
                    reason_code="addon_requires_personal_subscription",
                    metadata_json={"operation_kind": "storage_upgrade"},
                )
            )
            gaps += 1
            continue
        if (
            subscription.cycle != snapshot_cycle
            or subscription.paid_through is None
            or subscription.paid_through.astimezone(UTC) != ends_at
            or effective_at >= ends_at
        ):
            operation.state = "reconciliation_gap"
            db.add(
                BillingAuditEvent(
                    workspace_id=operation.workspace_id,
                    action="billing.maintenance_addon_projection",
                    target_kind="billing_operation",
                    target_ref=None,
                    outcome="gap",
                    reason_code="addon_coterm_mismatch",
                    metadata_json={"operation_kind": "storage_upgrade"},
                )
            )
            gaps += 1
            continue
        if effective_at > current:
            scheduled += 1
            continue
        if subscription.capacity_bytes != target:
            subscription.capacity_bytes = target
            subscription.application_version = (subscription.application_version or 0) + 1
        operation.state = "succeeded_projected"
        db.add(
            BillingAuditEvent(
                workspace_id=operation.workspace_id,
                action="billing.maintenance_addon_projection",
                target_kind="workspace_subscription",
                target_ref=None,
                outcome="projected",
                reason_code="provider_confirmed_operation",
                metadata_json={"capacity_class": "approved_addon"},
            )
        )
        projected += 1
    return {
        "storage_addon_operations_projected": projected,
        "storage_addon_operations_scheduled": scheduled,
        "storage_addon_gaps": gaps,
    }


async def reconcile_billing_maintenance(
    db: AsyncSession,
    *,
    now: datetime | None = None,
    workspace_id: UUID | None = None,
) -> dict[str, int]:
    """Run one bounded maintenance pass and return counters only."""
    current = (now or datetime.now(UTC)).astimezone(UTC)
    expired_promos = await expire_promo_reservations(db, now=current)
    matured_credits = await mature_pending_credits(db, now=current)
    addon_counters = await _reconcile_storage_addon_operations(
        db,
        current=current,
        workspace_id=workspace_id,
    )

    # A browser timeout must not leave an operation in a mutable state forever.
    # Marking it unknown is a local classification only; provider GET/list
    # reconciliation remains the authority and can resolve a late success.
    stuck_cutoff = current - STUCK_OPERATION_MAX_AGE
    stuck_query = (
        select(BillingOperation)
        .where(
            BillingOperation.state.in_(("scheduled", "provider_pending")),
            BillingOperation.updated_at <= stuck_cutoff,
        )
        .order_by(BillingOperation.updated_at, BillingOperation.id)
        .limit(MAINTENANCE_BATCH_LIMIT)
        .with_for_update()
    )
    if workspace_id is not None:
        stuck_query = stuck_query.where(BillingOperation.workspace_id == workspace_id)
    stuck_operations = 0
    for operation in await db.scalars(stuck_query):
        operation.state = "unknown"
        operation.updated_at = current
        db.add(
            BillingAuditEvent(
                workspace_id=operation.workspace_id,
                action="billing.maintenance_stuck_operation",
                target_kind="billing_operation",
                target_ref=None,
                outcome="classified",
                reason_code="provider_truth_required",
                metadata_json={"operation_kind": operation.kind, "state": "unknown"},
            )
        )
        stuck_operations += 1

    query = select(WorkspaceSubscription.workspace_id)
    if workspace_id is not None:
        query = query.where(WorkspaceSubscription.workspace_id == workspace_id)
    subscription_workspace_ids = set(await db.scalars(query))
    reservation_query = select(StorageReservation.workspace_id).where(StorageReservation.state == "active").distinct()
    if workspace_id is not None:
        reservation_query = reservation_query.where(StorageReservation.workspace_id == workspace_id)
    subscription_workspace_ids.update(await db.scalars(reservation_query))
    released_reservations = 0
    storage_projections_checked = 0
    storage_addons_checked = 0
    for current_workspace_id in sorted(subscription_workspace_ids, key=str)[:MAINTENANCE_BATCH_LIMIT]:
        released_reservations += await release_expired_storage_reservations(
            db,
            workspace_id=current_workspace_id,
            now=current,
        )
        subscription = await db.scalar(
            select(WorkspaceSubscription).where(WorkspaceSubscription.workspace_id == current_workspace_id)
        )
        if subscription is not None:
            await project_active_playback_storage(
                db,
                workspace_id=current_workspace_id,
                capacity_bytes=subscription.capacity_bytes,
            )
            storage_projections_checked += 1
            # Add-ons are total-capacity selections projected on the
            # workspace subscription until their dedicated invoice slice is
            # persisted. Count them for bounded maintenance evidence; do not
            # mutate capacity or create a provider operation here.
            if subscription.capacity_bytes > PERSONAL_STORAGE_BYTES:
                storage_addons_checked += 1

    pending_notifications_query = select(func.count(BillingNotificationDelivery.id)).where(
        BillingNotificationDelivery.state.in_(("pending", "retry"))
    )
    if workspace_id is not None:
        pending_notifications_query = pending_notifications_query.where(
            BillingNotificationDelivery.workspace_id == workspace_id
        )
    pending_notifications = int(await db.scalar(pending_notifications_query) or 0)
    await db.flush()
    return {
        "expired_promos": expired_promos,
        "matured_credits": matured_credits,
        "released_storage_reservations": released_reservations,
        "stuck_operations": stuck_operations,
        "storage_projections_checked": storage_projections_checked,
        "storage_addons_checked": storage_addons_checked,
        "pending_notifications": pending_notifications,
        **addon_counters,
    }
