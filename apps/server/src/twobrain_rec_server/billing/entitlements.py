from __future__ import annotations

import calendar
import json
from dataclasses import dataclass, replace
from datetime import UTC, datetime
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from twobrain_rec_server.billing.admin_grants import AccessResolution, resolve_adjustments
from twobrain_rec_server.billing.audit import metadata_only
from twobrain_rec_server.billing.catalog import (
    CAPABILITY_BOOLEANS,
    EXPORT_FORMATS,
    FREE_PROCESSING_SECONDS,
    CatalogNotApproved,
    PlanCode,
    storage_capacity_bytes,
    validate_capabilities,
)
from twobrain_rec_server.billing.catalog_migration import exact_snapshot_version
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
    BillingPlan,
    BillingPlanPrice,
    BillingPlanVersion,
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
        return (
            "trial"
            if trial_ends_at is not None and trial_ends_at.astimezone(UTC) > current
            else "free"
        )
    if plan_code not in {"free", "trial"}:
        return (
            plan_code
            if paid_through is not None and paid_through.astimezone(UTC) > current
            else "free"
        )
    return "free" if state not in {"free", "trial", "personal"} else plan_code


def legacy_capabilities(plan_code: str, *, capacity_bytes: int | None = None) -> dict[str, object]:
    """Exact pre-catalog product defaults; never invent capabilities for a new code."""
    if plan_code not in {"free", "trial", "personal"}:
        raise CatalogNotApproved("subscription requires a pinned capability version")
    return validate_capabilities({
        **dict.fromkeys(CAPABILITY_BOOLEANS, True),
        "processing_unlimited": plan_code in {"trial", "personal"},
        "storage_bytes": capacity_bytes if capacity_bytes is not None else storage_capacity_bytes(plan_code),
        "processing_seconds": FREE_PROCESSING_SECONDS,
        "processing_window": "calendar_month_moscow",
        "export_formats": sorted(EXPORT_FORMATS),
    })


async def resolve_entitlements(
    db: AsyncSession, *, workspace_id: UUID, subject_user_id: UUID | None,
    now: datetime, hard_denies: frozenset[str] = frozenset(),
) -> AccessResolution:
    """Resolve exact paid terms and non-monetary sources without modifying billing."""
    if now.tzinfo is None or now.utcoffset() is None:
        raise ValueError("entitlement time must be timezone-aware")
    subscription = await db.get(WorkspaceSubscription, workspace_id, populate_existing=True)
    code = effective_plan_code(
        plan_code=subscription.plan_code if subscription else "free",
        state=subscription.state if subscription else "free", now=now,
        paid_through=subscription.paid_through if subscription else None,
        trial_ends_at=subscription.trial_ends_at if subscription else None,
    )
    version = None
    access_until = None
    if code == "free":
        plan = await db.scalar(select(BillingPlan).where(BillingPlan.code == "free"))
        if plan is not None and plan.current_version_id is not None:
            version = await db.get(BillingPlanVersion, plan.current_version_id)
    elif subscription is not None:
        access_until = subscription.trial_ends_at if code == "trial" else subscription.paid_through
        if subscription.pinned_plan_version_id is not None:
            version = await db.get(BillingPlanVersion, subscription.pinned_plan_version_id)
            if version is None or version.plan_code != code:
                raise CatalogNotApproved("subscription capability pin is inconsistent")
    if version is not None and version.status not in (None, "legacy"):
        if version.status not in {"published", "retired"} or version.capability_schema_version != 1:
            raise CatalogNotApproved("subscription capability version is unavailable")
        capabilities = validate_capabilities(version.capabilities)
        if subscription and code != "free":
            capabilities["storage_bytes"] = max(capabilities["storage_bytes"], subscription.capacity_bytes or 0)
    else:
        capabilities = legacy_capabilities(
            code, capacity_bytes=subscription.capacity_bytes if subscription and code != "free" else None,
        )
    access = await resolve_adjustments(
        db, workspace_id=workspace_id, subject_user_id=subject_user_id,
        base_capabilities=capabilities, now=now, hard_denies=hard_denies,
    )
    if access.plan_version_id is not None:
        gift = await db.get(BillingPlanVersion, access.plan_version_id)
        code = gift.plan_code
    return replace(
        access, plan_code=code,
        base_source="gift" if access.plan_version_id else ("paid" if code not in {"free", "trial"} else code),
        base_plan_version_id=version.id if version is not None else None,
        access_until=access.plan_ends_at or access_until,
    )


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
        return moment.replace(
            year=year, month=month, day=min(moment.day, calendar.monthrange(year, month)[1])
        )
    if cycle == "year":
        year = moment.year + 1
        return moment.replace(
            year=year, day=min(moment.day, calendar.monthrange(year, moment.month)[1])
        )
    raise ValueError("paid cycle is invalid")


def recurring_actor_matches_current_owner(
    *, snapshot_actor: object, current_owner_id: UUID
) -> bool:
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


async def _confirmed_catalog(
    db: AsyncSession, snapshot: object, invoice: BillingInvoice,
) -> tuple[BillingPlanVersion, BillingPlanPrice] | None:
    """Keep legacy invoices payable; managed offers require both exact financial snapshots."""
    if (
        not isinstance(snapshot, dict) or not isinstance(snapshot.get("plan_code"), str)
        or not isinstance(snapshot.get("cycle"), str) or snapshot["cycle"] not in {"month", "year"}
    ):
        raise CatalogNotApproved("invalid paid snapshot")
    sources = (snapshot, invoice.plan_snapshot)
    managed = any(
        isinstance(source, dict) and isinstance(source.get("catalog_snapshot"), dict)
        and {"plan_version_id", "price_id", "capability_schema_version", "capabilities"}.intersection(source["catalog_snapshot"])
        for source in sources
    )
    if not managed and snapshot.get("plan_code") == "personal":
        return None
    resolved = await exact_snapshot_version(db, invoice.plan_snapshot, lock=False)
    if resolved is None or resolved[1] is None or resolved[0].status == "legacy":
        raise CatalogNotApproved("paid catalog is not pinned")
    version, price = resolved
    fields = (
        "plan_code", "cycle", "catalog_snapshot", "list_amount_minor", "payable_amount_minor",
        "billing_actor_user_id", "currency", "storage_capacity_bytes", "recurring_consent",
        "offer_consent", "recurring_authority_version",
    )
    if json.dumps({key:snapshot.get(key) for key in fields}, sort_keys=True, allow_nan=False) != json.dumps(
        {key:invoice.plan_snapshot.get(key) for key in fields}, sort_keys=True, allow_nan=False,
    ):
        raise CatalogNotApproved("financial snapshots differ")
    if (
        version.plan_code in {"free", "trial"}
        or type(snapshot.get("payable_amount_minor")) is not int
        or snapshot["payable_amount_minor"] != invoice.amount_minor
        or not 0 < invoice.amount_minor <= price.amount_minor
        or invoice.currency != price.currency
    ):
        raise CatalogNotApproved("paid amount differs from offer")
    return version, price


def _pin_confirmed_terms(
    subscription: WorkspaceSubscription,
    catalog: tuple[BillingPlanVersion, BillingPlanPrice] | None,
) -> None:
    # A fresh legacy payment must not retain a previous managed offer's capabilities.
    subscription.pinned_plan_version_id = catalog[0].id if catalog else None
    subscription.pinned_price_id = catalog[1].id if catalog else None
    subscription.pin_state = "pinned" if catalog else "pending"
    subscription.pin_checked_application_version = subscription.application_version if catalog else None
    subscription.next_charge_at = subscription.paid_through
    subscription.schedule_version = (subscription.schedule_version or 0) + 1


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
        .where(
            BillingOperation.workspace_id == workspace_id,
            BillingOperation.provider_id == provider_payment_id,
        )
        .with_for_update()
    )
    if operation is None:
        return "unmatched"
    if operation.kind != "initial_checkout":
        operation.state = "reconciliation_gap"
        return "operation_kind_mismatch"
    invoice = await db.scalar(
        select(BillingInvoice).where(
            BillingInvoice.operation_id == operation.id, BillingInvoice.workspace_id == workspace_id,
        ).with_for_update()
    )
    if invoice is None or invoice.amount_minor != amount_minor or invoice.currency != currency:
        operation.state = "reconciliation_gap"
        return "amount_mismatch"
    if operation.state == "succeeded_refused":
        return "refused"
    existing_grant = await db.scalar(
        select(BillingEntitlementGrant)
        .where(
            BillingEntitlementGrant.workspace_id == workspace_id,
            BillingEntitlementGrant.invoice_id == invoice.id,
        )
        .with_for_update()
    )
    receipt_became_available = False
    if receipt_registration is not None:
        try:
            updated_snapshot, receipt_became_available = merge_receipt_registration(
                invoice.plan_snapshot,
                status=receipt_registration,
            )
        except ValueError:
            if existing_grant is None:
                operation.state = "reconciliation_gap"
                return "receipt_mismatch"
        else:
            invoice.plan_snapshot = updated_snapshot
    if existing_grant is not None:
        snapshot = operation.request_snapshot
        cycle = snapshot.get("cycle") if isinstance(snapshot, dict) else None
        try:
            payer_user_id = (
                UUID(str(snapshot["billing_actor_user_id"])) if isinstance(snapshot, dict) else None
            )
        except (KeyError, TypeError, ValueError):
            payer_user_id = None
        if payer_user_id is not None:
            if not defer_referral_reward and cycle in {"month", "year"}:
                await create_pending_credit(
                    db,
                    workspace_id=workspace_id,
                    invitee_user_id=payer_user_id,
                    provider_payment_id=provider_payment_id,
                    paid_at=existing_grant.starts_at,
                    cycle=cycle,
                )
            if receipt_became_available:
                await enqueue_billing_notification(
                    db,
                    workspace_id=workspace_id,
                    recipient_id=payer_user_id,
                    event_id=f"receipt:{invoice.id}:available",
                    kind=BillingNotification.RECEIPT_AVAILABLE,
                    payload={
                        "invoice": invoice.safe_number,
                        "action_path": f"/billing/invoices/{invoice.safe_number}",
                    },
                    marketing_allowed=False,
                )
        return "duplicate"
    snapshot = operation.request_snapshot
    try:
        catalog = await _confirmed_catalog(db, snapshot, invoice)
    except (CatalogNotApproved, ValueError):
        operation.state = "reconciliation_gap"
        return "snapshot_invalid"
    plan_code = snapshot["plan_code"]
    cycle = snapshot["cycle"]
    try:
        payer_user_id = UUID(str(snapshot["billing_actor_user_id"]))
    except (KeyError, TypeError, ValueError):
        operation.state = "reconciliation_gap"
        return "snapshot_invalid"
    workspace = await db.scalar(
        select(Workspace).where(Workspace.id == workspace_id).with_for_update()
    )
    owner = await db.scalar(
        select(WorkspaceMembership)
        .where(
            WorkspaceMembership.workspace_id == workspace_id,
            WorkspaceMembership.user_id
            == (workspace.owner_user_id if workspace is not None else None),
            WorkspaceMembership.role == "owner",
            WorkspaceMembership.status == "active",
        )
        .with_for_update()
    )
    if workspace is None or workspace.kind != "personal" or owner is None:
        operation.state = "reconciliation_gap"
        return "owner_missing"
    recurring_actor_matches = recurring_actor_matches_current_owner(
        snapshot_actor=snapshot.get("billing_actor_user_id"),
        current_owner_id=owner.user_id,
    )
    paid_at = paid_at.astimezone(UTC)
    timezone = "Europe/Moscow" if catalog else "UTC"
    paid_through = _add_paid_interval(paid_at.astimezone(ZoneInfo(timezone)), cycle).astimezone(UTC)
    db.add(
        BillingEntitlementGrant(
            workspace_id=workspace_id,
            invoice_id=invoice.id,
            provider_payment_id=provider_payment_id,
            plan_code=plan_code,
            plan_version_id=catalog[0].id if catalog else None,
            cycle=cycle,
            starts_at=paid_at,
            ends_at=paid_through,
            amount_minor=amount_minor,
            currency=currency,
        )
    )
    subscription = await db.scalar(
        select(WorkspaceSubscription)
        .where(WorkspaceSubscription.workspace_id == workspace_id)
        .with_for_update()
    )
    if subscription is None:
        subscription = WorkspaceSubscription(workspace_id=workspace_id)
        db.add(subscription)
    subscription.billing_owner_id = owner.user_id
    subscription.state = "personal"
    subscription.plan_code = plan_code
    subscription.cycle = cycle
    subscription.capacity_bytes = _snapshot_storage_capacity(
        snapshot,
        fallback=catalog[0].storage_bytes if catalog else storage_capacity_bytes("personal"),
    )
    subscription.paid_through = paid_through
    subscription.billing_anchor = paid_at
    subscription.timezone = timezone
    subscription.application_version = (subscription.application_version or 0) + 1
    _pin_confirmed_terms(subscription, catalog)
    if (
        saved_payment_method is not None
        and payment_method_key is not None
        and recurring_actor_matches
    ):
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
                encrypted_provider_ref=seal_provider_reference(
                    saved_payment_method.provider_ref, payment_method_key
                ),
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
    invoice.status = "succeeded"
    if payment_method_label and "payment_method_label" not in invoice.plan_snapshot:
        invoice.plan_snapshot = {
            **invoice.plan_snapshot,
            "payment_method_label": payment_method_label,
        }
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
                    "recurring_authority": "current_owner"
                    if recurring_actor_matches
                    else "owner_changed",
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
            payload={
                "invoice": invoice.safe_number,
                "action_path": f"/billing/invoices/{invoice.safe_number}",
            },
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
    # Keep the row-lock order identical to manual checkout: workspace,
    # subscription, then operation. This prevents renewal confirmation from
    # deadlocking with a checkout that already owns the subscription row.
    workspace = await db.scalar(
        select(Workspace).where(Workspace.id == workspace_id).with_for_update()
    )
    subscription = await db.scalar(
        select(WorkspaceSubscription)
        .where(WorkspaceSubscription.workspace_id == workspace_id)
        .with_for_update()
    )
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
        select(BillingInvoice).where(
            BillingInvoice.operation_id == operation.id, BillingInvoice.workspace_id == workspace_id,
        ).with_for_update()
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
    try:
        catalog = await _confirmed_catalog(db, snapshot, invoice)
    except (CatalogNotApproved, ValueError):
        operation.state = "reconciliation_gap"
        return "snapshot_invalid"
    plan_code = snapshot["plan_code"]
    cycle = snapshot["cycle"]
    if subscription is None:
        operation.state = "reconciliation_gap"
        return "subscription_missing"
    if catalog is not None and (
        invoice.amount_minor != catalog[1].amount_minor
        or subscription.pinned_plan_version_id != catalog[0].id
        or subscription.pinned_price_id != catalog[1].id
        or snapshot.get("pinned_plan_version_id") != str(catalog[0].id)
        or snapshot.get("pinned_price_id") != str(catalog[1].id)
        or type(snapshot.get("schedule_version")) is not int
        or snapshot["schedule_version"] != subscription.schedule_version
    ):
        operation.state = "reconciliation_gap"
        return "schedule_mismatch"
    owner = await db.scalar(
        select(WorkspaceMembership)
        .where(
            WorkspaceMembership.workspace_id == workspace_id,
            WorkspaceMembership.user_id
            == (workspace.owner_user_id if workspace is not None else None),
            WorkspaceMembership.role == "owner",
            WorkspaceMembership.status == "active",
        )
        .with_for_update()
    )
    if (
        workspace is None
        or workspace.kind != "personal"
        or owner is None
        or subscription.billing_owner_id != owner.user_id
    ):
        operation.state = "succeeded_refused"
        invoice.status = "succeeded"
        if subscription.recurring_allowed:
            subscription.recurring_allowed = False
            subscription.recurring_authority_version = (
                subscription.recurring_authority_version or 0
            ) + 1
        subscription.renewal_resolution = "workspace_scope_invalid"
        db.add(
            BillingAuditEvent(
                workspace_id=workspace_id,
                actor_user_id=subscription.billing_owner_id,
                action="renewal_success_refused",
                target_kind="billing_operation",
                target_ref=invoice.safe_number,
                outcome="blocked",
                reason_code="workspace_scope_invalid",
                metadata_json={},
            )
        )
        await db.flush()
        return "refused"
    expected_authority = snapshot.get("recurring_authority_version")
    authority_matches = (
        subscription.recurring_allowed
        and recurring_actor_matches_current_owner(
            snapshot_actor=snapshot.get("billing_actor_user_id"),
            current_owner_id=owner.user_id,
        )
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
    timezone = ZoneInfo(subscription.timezone or "UTC") if catalog else UTC
    ends_at = _add_paid_interval(starts_at.astimezone(timezone), cycle).astimezone(UTC)
    db.add(
        BillingEntitlementGrant(
            workspace_id=workspace_id,
            invoice_id=invoice.id,
            provider_payment_id=provider_payment_id,
            plan_code=plan_code,
            plan_version_id=catalog[0].id if catalog else None,
            cycle=cycle,
            starts_at=starts_at,
            ends_at=ends_at,
            amount_minor=amount_minor,
            currency=currency,
            source="renewal_provider_confirmed",
        )
    )
    subscription.state = "personal"
    subscription.plan_code = plan_code
    subscription.cycle = cycle
    subscription.paid_through = ends_at
    subscription.capacity_bytes = _snapshot_storage_capacity(
        snapshot,
        fallback=subscription.capacity_bytes or (catalog[0].storage_bytes if catalog else storage_capacity_bytes("personal")),
    )
    subscription.renewal_resolution = "succeeded"
    subscription.application_version = (subscription.application_version or 0) + 1
    _pin_confirmed_terms(subscription, catalog)
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
