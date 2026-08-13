from __future__ import annotations

import calendar
from dataclasses import dataclass
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from twobrain_rec_server.billing.audit import metadata_only
from twobrain_rec_server.billing.catalog import (
    FREE_PROCESSING_SECONDS,
    PlanCode,
    storage_capacity_bytes,
)
from twobrain_rec_server.billing.events import enqueue_billing_notification
from twobrain_rec_server.billing.notifications import BillingNotification
from twobrain_rec_server.billing.payment_methods import (
    SavedPaymentMethod,
    seal_provider_reference,
    validate_payment_method_key_version,
)
from twobrain_rec_server.billing.promotions import redeem_invoice_promo
from twobrain_rec_server.billing.receipts import ReceiptRegistration, merge_receipt_registration
from twobrain_rec_server.billing.referral_rewards import create_pending_credit
from twobrain_rec_server.billing.storage import lock_storage_workspace
from twobrain_rec_server.db.models import (
    BillingAuditEvent,
    BillingEntitlementGrant,
    BillingInvoice,
    BillingOperation,
    BillingPaymentMethod,
    Workspace,
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
        year = moment.year + 1
        return moment.replace(year=year, day=min(moment.day, calendar.monthrange(year, moment.month)[1]))
    raise ValueError("paid cycle is invalid")


def recurring_actor_matches_current_owner(*, snapshot_actor: object, current_owner_id: UUID) -> bool:
    try:
        return UUID(str(snapshot_actor)) == current_owner_id
    except (TypeError, ValueError):
        return False


def _snapshot_storage_capacity(snapshot: object, *, fallback: int) -> int:
    if isinstance(snapshot, dict):
        value = snapshot.get("storage_capacity_bytes")
        if isinstance(value, int) and not isinstance(value, bool) and value > 0:
            return value
        catalog = snapshot.get("catalog_snapshot")
        value = catalog.get("storage_bytes") if isinstance(catalog, dict) else None
        if isinstance(value, int) and not isinstance(value, bool) and value > 0:
            return value
    return fallback


async def grant_confirmed_payment(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    provider_payment_id: str,
    amount_minor: int,
    currency: str,
    paid_at: datetime,
    recurring_method_confirmed: bool = False,
    saved_payment_method: SavedPaymentMethod | None = None,
    payment_method_key: bytes | None = None,
    payment_method_key_version: str = "billing-v1",
    payment_method_label: str | None = None,
    receipt_registration: ReceiptRegistration | None = None,
    defer_referral_reward: bool = False,
) -> str:
    """Grant one immutable invoice only after provider GET confirms its amount."""
    await lock_storage_workspace(db, workspace_id)
    operation = await db.scalar(
        select(BillingOperation)
        .where(BillingOperation.workspace_id == workspace_id, BillingOperation.provider_id == provider_payment_id)
        .with_for_update()
    )
    if operation is None:
        return "unmatched"
    if operation.kind != "initial_checkout":
        operation.state = "reconciliation_gap"
        return "operation_kind_mismatch"
    invoice = await db.scalar(
        select(BillingInvoice).where(BillingInvoice.operation_id == operation.id).with_for_update()
    )
    if invoice is None or invoice.amount_minor != amount_minor or invoice.currency != currency:
        operation.state = "reconciliation_gap"
        return "amount_mismatch"
    if operation.state == "succeeded_refused":
        return "refused"
    existing_grant = await db.scalar(
        select(BillingEntitlementGrant)
        .where(BillingEntitlementGrant.workspace_id == workspace_id, BillingEntitlementGrant.invoice_id == invoice.id)
        .with_for_update()
    )
    if existing_grant is not None:
        if not defer_referral_reward:
            snapshot = operation.request_snapshot
            cycle = snapshot.get("cycle") if isinstance(snapshot, dict) else None
            try:
                payer_user_id = UUID(str(snapshot["billing_actor_user_id"])) if isinstance(snapshot, dict) else None
            except (KeyError, TypeError, ValueError):
                payer_user_id = None
            if payer_user_id is not None and cycle in {"month", "year"}:
                await create_pending_credit(
                    db,
                    workspace_id=workspace_id,
                    invitee_user_id=payer_user_id,
                    provider_payment_id=provider_payment_id,
                    paid_at=existing_grant.starts_at,
                    cycle=cycle,
                )
        return "duplicate"
    receipt_became_available = False
    if receipt_registration is not None:
        try:
            updated_snapshot, receipt_became_available = merge_receipt_registration(
                invoice.plan_snapshot,
                status=receipt_registration,
            )
        except ValueError:
            operation.state = "reconciliation_gap"
            return "receipt_mismatch"
        invoice.plan_snapshot = updated_snapshot
    snapshot = operation.request_snapshot
    plan_code = snapshot.get("plan_code")
    cycle = snapshot.get("cycle")
    if plan_code != "personal" or cycle not in {"month", "year"}:
        operation.state = "reconciliation_gap"
        return "snapshot_invalid"
    try:
        payer_user_id = UUID(str(snapshot["billing_actor_user_id"]))
    except (KeyError, TypeError, ValueError):
        operation.state = "reconciliation_gap"
        return "snapshot_invalid"
    workspace = await db.scalar(
        select(Workspace).where(Workspace.id == workspace_id).with_for_update()
    )
    owner = await db.scalar(
        select(WorkspaceMembership).where(
            WorkspaceMembership.workspace_id == workspace_id,
            WorkspaceMembership.user_id == (workspace.owner_user_id if workspace is not None else None),
            WorkspaceMembership.role == "owner",
            WorkspaceMembership.status == "active",
        )
    )
    if workspace is None or workspace.kind != "personal" or owner is None:
        operation.state = "reconciliation_gap"
        return "owner_missing"
    recurring_actor_matches = recurring_actor_matches_current_owner(
        snapshot_actor=snapshot.get("billing_actor_user_id"),
        current_owner_id=owner.user_id,
    )
    paid_at = paid_at.astimezone(UTC)
    paid_through = _add_paid_interval(paid_at, cycle)
    db.add(
        BillingEntitlementGrant(
            workspace_id=workspace_id,
            invoice_id=invoice.id,
            provider_payment_id=provider_payment_id,
            plan_code=plan_code,
            cycle=cycle,
            starts_at=paid_at,
            ends_at=paid_through,
            amount_minor=amount_minor,
            currency=currency,
        )
    )
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
    subscription.capacity_bytes = _snapshot_storage_capacity(
        snapshot,
        fallback=storage_capacity_bytes("personal"),
    )
    subscription.paid_through = paid_through
    subscription.billing_anchor = paid_at
    if saved_payment_method is not None and payment_method_key is not None and recurring_actor_matches:
        methods = await db.scalars(
            select(BillingPaymentMethod)
            .where(
                BillingPaymentMethod.workspace_id == workspace_id,
                BillingPaymentMethod.is_default.is_(True),
            )
            .with_for_update()
        )
        for method in methods:
            method.is_default = False
            method.state = "replaced"
        db.add(
            BillingPaymentMethod(
                workspace_id=workspace_id,
                owner_user_id=owner.user_id,
                encrypted_provider_ref=seal_provider_reference(saved_payment_method.provider_ref, payment_method_key),
                key_version=validate_payment_method_key_version(payment_method_key_version),
                kind=saved_payment_method.kind,
                masked_label=saved_payment_method.masked_label,
                state="active",
                is_default=True,
                verified_at=paid_at,
            )
        )
    subscription.recurring_allowed = (
        bool(snapshot.get("recurring_consent"))
        and recurring_actor_matches
        and recurring_method_confirmed
        and saved_payment_method is not None
        and payment_method_key is not None
    )
    subscription.recurring_authority_version = (subscription.recurring_authority_version or 0) + 1
    subscription.application_version = (subscription.application_version or 0) + 1
    invoice.status = "succeeded"
    if payment_method_label and "payment_method_label" not in invoice.plan_snapshot:
        invoice.plan_snapshot = {**invoice.plan_snapshot, "payment_method_label": payment_method_label}
    operation.state = "succeeded"
    await redeem_invoice_promo(db, invoice_id=invoice.id, now=paid_at)
    if not defer_referral_reward:
        await create_pending_credit(
            db,
            workspace_id=workspace_id,
            invitee_user_id=payer_user_id,
            provider_payment_id=provider_payment_id,
            paid_at=paid_at,
            cycle=cycle,
        )
    db.add(
        BillingAuditEvent(
            workspace_id=workspace_id,
            actor_user_id=owner.user_id,
            action="entitlement.grant_confirmed_payment",
            target_kind="billing_invoice",
            target_ref=invoice.safe_number,
            outcome="success",
            reason_code=(
                "provider_get_confirmed"
                if recurring_actor_matches
                else "provider_get_confirmed_recurring_suppressed"
            ),
            metadata_json=metadata_only(
                {
                    "currency": currency,
                    "recurring_authority": "current_owner" if recurring_actor_matches else "owner_changed",
                }
            ),
        )
    )
    await enqueue_billing_notification(
        db,
        workspace_id=workspace_id,
        recipient_id=owner.user_id,
        event_id=f"payment:{invoice.id}:succeeded",
        kind=BillingNotification.PAYMENT_SUCCEEDED,
        payload={"invoice": invoice.safe_number, "action_path": "/billing"},
        marketing_allowed=False,
    )
    if receipt_became_available:
        await enqueue_billing_notification(
            db,
            workspace_id=workspace_id,
            recipient_id=owner.user_id,
            event_id=f"receipt:{invoice.id}:available",
            kind=BillingNotification.RECEIPT_AVAILABLE,
            payload={"invoice": invoice.safe_number, "action_path": f"/billing/invoices/{invoice.safe_number}"},
            marketing_allowed=False,
        )
    await db.flush()
    return "granted"


async def grant_confirmed_renewal(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    provider_payment_id: str,
    amount_minor: int,
    currency: str,
    grant_starts_at: datetime,
) -> str:
    """Project one GET-confirmed renewal into the append-only entitlement ledger."""
    await lock_storage_workspace(db, workspace_id)
    operation = await db.scalar(
        select(BillingOperation)
        .where(
            BillingOperation.workspace_id == workspace_id,
            BillingOperation.provider_id == provider_payment_id,
            BillingOperation.kind == "renewal",
        )
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
    if operation.state == "succeeded_refused":
        return "duplicate"
    if operation.state in {"manual_resolution", "reconciliation_gap"}:
        return "reconciliation_blocked"
    existing = await db.scalar(
        select(BillingEntitlementGrant)
        .where(
            BillingEntitlementGrant.workspace_id == workspace_id,
            BillingEntitlementGrant.invoice_id == invoice.id,
        )
        .with_for_update()
    )
    if existing is not None:
        return "duplicate"
    snapshot = operation.request_snapshot
    cycle = snapshot.get("cycle")
    if snapshot.get("plan_code") != "personal" or cycle not in {"month", "year"}:
        operation.state = "reconciliation_gap"
        return "snapshot_invalid"
    subscription = await db.scalar(
        select(WorkspaceSubscription).where(WorkspaceSubscription.workspace_id == workspace_id).with_for_update()
    )
    if subscription is None:
        operation.state = "reconciliation_gap"
        return "subscription_missing"
    expected_authority = snapshot.get("recurring_authority_version")
    authority_matches = (
        subscription.recurring_allowed
        and isinstance(expected_authority, int)
        and not isinstance(expected_authority, bool)
        and expected_authority == subscription.recurring_authority_version
    )
    if not authority_matches:
        operation.state = "succeeded_refused"
        invoice.status = "succeeded"
        subscription.renewal_resolution = "late_success_refused"
        db.add(
            BillingAuditEvent(
                workspace_id=workspace_id,
                actor_user_id=subscription.billing_owner_id,
                action="renewal_success_refused",
                target_kind="billing_operation",
                target_ref=invoice.safe_number,
                outcome="blocked",
                reason_code="recurring_authority_changed",
                metadata_json={},
            )
        )
        if subscription.billing_owner_id is not None:
            await enqueue_billing_notification(
                db,
                workspace_id=workspace_id,
                recipient_id=subscription.billing_owner_id,
                event_id=f"renewal:{invoice.id}:late_success_refused",
                kind=BillingNotification.RENEWAL_LATE_SUCCESS_REFUSED,
                payload={"invoice": invoice.safe_number, "action_path": "/billing/history"},
                marketing_allowed=False,
            )
        await db.flush()
        return "refused"
    starts_at = grant_starts_at.astimezone(UTC)
    ends_at = _add_paid_interval(starts_at, cycle)
    db.add(
        BillingEntitlementGrant(
            workspace_id=workspace_id,
            invoice_id=invoice.id,
            provider_payment_id=provider_payment_id,
            plan_code="personal",
            cycle=cycle,
            starts_at=starts_at,
            ends_at=ends_at,
            amount_minor=amount_minor,
            currency=currency,
            source="renewal_provider_confirmed",
        )
    )
    subscription.state = "personal"
    subscription.plan_code = "personal"
    subscription.cycle = cycle
    subscription.paid_through = ends_at
    subscription.capacity_bytes = _snapshot_storage_capacity(
        snapshot,
        fallback=subscription.capacity_bytes or storage_capacity_bytes("personal"),
    )
    subscription.renewal_resolution = "succeeded"
    subscription.application_version = (subscription.application_version or 0) + 1
    invoice.status = "succeeded"
    operation.state = "succeeded"
    db.add(
        BillingAuditEvent(
            workspace_id=workspace_id,
            actor_user_id=subscription.billing_owner_id,
            action="entitlement.grant_confirmed_renewal",
            target_kind="billing_invoice",
            target_ref=invoice.safe_number,
            outcome="success",
            reason_code="provider_get_confirmed",
            metadata_json=metadata_only({"amount_minor": str(amount_minor), "currency": currency}),
        )
    )
    await db.flush()
    return "granted"
