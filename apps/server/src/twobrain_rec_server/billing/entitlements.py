from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from twobrain_rec_server.billing.catalog import (
    FREE_PROCESSING_SECONDS,
    PlanCode,
    storage_capacity_bytes,
)
from twobrain_rec_server.db.models import (
    BillingAuditEvent,
    BillingInvoice,
    BillingOperation,
    WorkspaceMembership,
    WorkspaceSubscription,
)


@dataclass(frozen=True, slots=True)
class EntitlementSnapshot:
    plan_code: PlanCode
    processing_unlimited: bool
    storage_capacity_bytes: int


def effective_plan_code(
    *,
    plan_code: PlanCode,
    state: str,
    now: datetime,
    paid_through: datetime | None,
    trial_ends_at: datetime | None,
) -> PlanCode:
    """Apply the authoritative cutoff before projecting paid capabilities."""
    current = now.astimezone(UTC)
    if plan_code == "trial":
        return "trial" if trial_ends_at is not None and trial_ends_at.astimezone(UTC) > current else "free"
    if plan_code == "personal":
        return "personal" if paid_through is not None and paid_through.astimezone(UTC) > current else "free"
    return "free" if state not in {"free", "trial", "personal"} else plan_code


def entitlement_for_plan(
    *,
    plan_code: PlanCode,
    storage_addon_bytes: int | None = None,
) -> EntitlementSnapshot:
    return EntitlementSnapshot(
        plan_code=plan_code,
        processing_unlimited=plan_code in {"trial", "personal"},
        storage_capacity_bytes=storage_capacity_bytes(plan_code, storage_addon_bytes),
    )


def processing_admission(
    *,
    entitlement: EntitlementSnapshot,
    committed_free_seconds: int,
    accepted_seconds: int,
    save_audio: bool,
) -> tuple[bool, str]:
    """Return a stable reason code; archive choice never blocks paid processing."""
    if accepted_seconds <= 0:
        raise ValueError("accepted seconds must be positive")
    if entitlement.processing_unlimited:
        return True, "paid_unlimited"
    if committed_free_seconds + accepted_seconds > FREE_PROCESSING_SECONDS:
        return (False, "free_processing_exhausted")
    if not save_audio:
        return True, "free_without_audio_archive"
    return True, "free_with_audio_archive"


def _add_paid_interval(moment: datetime, cycle: str) -> datetime:
    if cycle == "month":
        year = moment.year + (moment.month == 12)
        month = 1 if moment.month == 12 else moment.month + 1
        return moment.replace(year=year, month=month, day=min(moment.day, calendar.monthrange(year, month)[1]))
    if cycle == "year":
        return moment.replace(year=moment.year + 1)
    raise ValueError("paid cycle is invalid")


async def grant_confirmed_payment(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    provider_payment_id: str,
    amount_minor: int,
    currency: str,
    paid_at: datetime,
) -> str:
    """Grant one immutable invoice only after provider GET confirms its amount."""
    operation = await db.scalar(
        select(BillingOperation)
        .where(BillingOperation.workspace_id == workspace_id, BillingOperation.provider_id == provider_payment_id)
        .with_for_update()
    )
    if operation is None:
        return "unmatched"
    invoice = await db.scalar(
        select(BillingInvoice).where(BillingInvoice.operation_id == operation.id).with_for_update()
    )
    if invoice is None or invoice.amount_minor != amount_minor or invoice.currency != currency:
        operation.state = "reconciliation_gap"
        return "amount_mismatch"
    if invoice.status == "succeeded":
        return "duplicate"
    snapshot = operation.request_snapshot
    plan_code = snapshot.get("plan_code")
    cycle = snapshot.get("cycle")
    if plan_code != "personal" or cycle not in {"month", "year"}:
        operation.state = "reconciliation_gap"
        return "snapshot_invalid"
    owner = await db.scalar(
        select(WorkspaceMembership).where(
            WorkspaceMembership.workspace_id == workspace_id,
            WorkspaceMembership.role == "owner",
            WorkspaceMembership.status == "active",
        ).order_by(WorkspaceMembership.created_at)
    )
    if owner is None:
        operation.state = "reconciliation_gap"
        return "owner_missing"
    paid_at = paid_at.astimezone(UTC)
    paid_through = _add_paid_interval(paid_at, cycle)
    subscription = await db.scalar(
        select(WorkspaceSubscription).where(WorkspaceSubscription.workspace_id == workspace_id).with_for_update()
    )
    if subscription is None:
        subscription = WorkspaceSubscription(workspace_id=workspace_id)
        db.add(subscription)
    subscription.billing_owner_id = owner.user_id
    subscription.state = "personal"
    subscription.plan_code = "personal"
    subscription.cycle = cycle
    subscription.capacity_bytes = storage_capacity_bytes("personal")
    subscription.paid_through = paid_through
    subscription.billing_anchor = paid_at
    subscription.recurring_allowed = bool(snapshot.get("recurring_consent"))
    subscription.recurring_authority_version += 1
    subscription.application_version += 1
    invoice.status = "succeeded"
    operation.state = "succeeded"
    db.add(
        BillingAuditEvent(
            workspace_id=workspace_id,
            actor_user_id=owner.user_id,
            action="entitlement.grant_confirmed_payment",
            target_kind="billing_invoice",
            target_ref=invoice.safe_number,
            outcome="success",
            reason_code="provider_get_confirmed",
            metadata_json={"amount_minor": str(amount_minor), "currency": currency},
        )
    )
    await db.flush()
    return "granted"
