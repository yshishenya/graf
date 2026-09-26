"""One-shot, restart-safe billing maintenance projection.

The scheduler owns cadence; this function owns only bounded, idempotent DB
maintenance. It never creates a payment, changes provider authority, or sends
customer content.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from twobrain_rec_server.billing.catalog import ADDON_CAPACITY_BYTES, PERSONAL_STORAGE_BYTES
from twobrain_rec_server.billing.operations import (
    CHECKOUT_BLOCKING_STATES,
    INITIAL_CHECKOUT_OBSERVATION_EXPIRED,
)
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
# The provider idempotence key lives for 24 hours from creation. A row that
# somehow never stored one is given the same window before it counts as
# abandoned, so no blocking state can outlive every recovery route.
MISSING_PROVIDER_KEY_GRACE = timedelta(hours=24)


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

    # Bound every initial checkout once its provider-key window is over. The
    # two branches intentionally have different meanings:
    #
    # * without provider_id there is no confirmation URL and no safe provider
    #   GET target, so the local operation/invoice become canceled;
    # * with provider_id the provider payment is known, so only the local
    #   blocking state expires. The row remains observable by GET/webhook and a
    #   late success can still grant the original invoice exactly once.
    #
    # Every writer sets the key, but a row without one would otherwise be
    # blocking and unreachable by every pass at the same time. Such a row is
    # treated as expired once the same window has elapsed since creation.
    initial_expiry_states = CHECKOUT_BLOCKING_STATES | {"provider_key_expired"}
    abandoned_query = (
        select(BillingOperation)
        .where(
            BillingOperation.kind == "initial_checkout",
            BillingOperation.state.in_(initial_expiry_states),
            or_(
                BillingOperation.provider_key_expires_at <= current,
                and_(
                    BillingOperation.provider_key_expires_at.is_(None),
                    BillingOperation.created_at <= current - MISSING_PROVIDER_KEY_GRACE,
                ),
            ),
        )
        .order_by(BillingOperation.updated_at, BillingOperation.id)
        .limit(MAINTENANCE_BATCH_LIMIT)
        .with_for_update()
    )
    if workspace_id is not None:
        abandoned_query = abandoned_query.where(
            BillingOperation.workspace_id == workspace_id
        )
    abandoned = await db.scalars(abandoned_query)
    abandoned_operations = 0
    expired_provider_observations = 0
    for operation in abandoned:
        operation.updated_at = current
        invoice = await db.scalar(
            select(BillingInvoice)
            .where(BillingInvoice.operation_id == operation.id)
            .with_for_update()
        )
        if getattr(operation, "provider_id", None) is None:
            operation.state = "canceled"
            if invoice is not None and invoice.status != "succeeded":
                invoice.status = "canceled"
            audit_action = "billing.abandoned_operation_canceled"
            outcome = "canceled"
            reason_code = "provider_key_expired_without_payment"
            state = "canceled"
            abandoned_operations += 1
        else:
            # Expiring the local blocking projection is not a provider verdict.
            # Keep the provider id, invoice and webhook/GET reconciliation path.
            operation.state = INITIAL_CHECKOUT_OBSERVATION_EXPIRED
            if invoice is not None and invoice.status == "pending":
                invoice.status = "unknown"
            audit_action = "billing.provider_observation_expired"
            outcome = "expired"
            reason_code = "provider_observation_window_elapsed"
            state = INITIAL_CHECKOUT_OBSERVATION_EXPIRED
            expired_provider_observations += 1
        db.add(
            BillingAuditEvent(
                workspace_id=operation.workspace_id,
                action=audit_action,
                target_kind="billing_operation",
                target_ref=None,
                outcome=outcome,
                reason_code=reason_code,
                metadata_json={"operation_kind": operation.kind, "state": state},
            )
        )
    if abandoned_operations or expired_provider_observations:
        await db.flush()

    # A browser timeout must not leave an operation in a mutable state forever.
    # Marking it unknown is a local classification only; provider GET/list
    # reconciliation remains the authority and can resolve a late success.
    # An operation without a provider payment id is excluded: it still has a
    # reachable payment to continue, and the abandoned pass above owns its exit.
    stuck_cutoff = current - STUCK_OPERATION_MAX_AGE
    stuck_query = (
        select(BillingOperation)
        .where(
            BillingOperation.state.in_(("scheduled", "provider_pending")),
            # Renewal operations have a 72-hour planning window and their
            # own exact-cutoff state machine. Generic 30-minute stale
            # classification would make them ineligible for the charge.
            BillingOperation.kind != "renewal",
            BillingOperation.provider_id.is_not(None),
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
        "abandoned_operations": abandoned_operations,
        "expired_provider_observations": expired_provider_observations,
        "storage_projections_checked": storage_projections_checked,
        "storage_addons_checked": storage_addons_checked,
        "pending_notifications": pending_notifications,
        **addon_counters,
    }
