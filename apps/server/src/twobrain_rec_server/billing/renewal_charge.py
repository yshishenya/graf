"""Plan and execute the single saved-method renewal attempt.

The module deliberately keeps planning, provider mutation and outcome
reconciliation separate.  A renewal operation is persisted before the first
outbound request and is identified by a deterministic period key, so a
worker restart cannot create a second charge for the same paid interval.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from uuid import NAMESPACE_URL, UUID, uuid5

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from twobrain_rec_server.billing.audit import metadata_only
from twobrain_rec_server.billing.authority import (
    BillingAuthorizationError,
    require_authority_version,
)
from twobrain_rec_server.billing.catalog import (
    FREE_STORAGE_BYTES,
    CatalogNotApproved,
    PlanCatalogSnapshot,
    validate_plan_version,
)
from twobrain_rec_server.billing.operations import (
    CHECKOUT_BLOCKING_STATES,
    BillingEmergencyStop,
    require_billing_enabled,
)
from twobrain_rec_server.billing.payment_methods import (
    open_provider_reference,
    read_billing_encryption_key,
)
from twobrain_rec_server.billing.provider_events import validate_provider_identifier
from twobrain_rec_server.billing.yookassa import (
    YooKassaClient,
    YooKassaConfigurationError,
    YooKassaProviderError,
    build_receipt_payload,
    provider_environment,
)
from twobrain_rec_server.config import Settings
from twobrain_rec_server.db.models import (
    BillingAuditEvent,
    BillingInvoice,
    BillingOperation,
    BillingPaymentMethod,
    BillingPlanVersion,
    Workspace,
    WorkspaceMembership,
    WorkspaceSubscription,
)

RENEWAL_REMINDER_HOURS = 72
RENEWAL_PROVIDER_WINDOW = timedelta(hours=24)
# A missing provider id after a transport error is not safe to POST again:
# YooKassa may have accepted the first request. Only an untouched operation
# may enter the outbound mutation path; unknown is GET/list/manual recovery.
RENEWAL_CANDIDATE_STATES = frozenset({"scheduled"})
# `scheduled` is an in-flight reservation during the reminder window.  At the
# exact cutoff it must remain chargeable; provider-key expiry is final and
# revokes recurring authority instead of keeping the card armed.
RENEWAL_PROVIDER_STATES = frozenset({"scheduled", "sent", "unknown", "processing"})


@dataclass(frozen=True, slots=True)
class RenewalChargeResult:
    operation_id: UUID
    status: str
    provider_id: str | None = None


def _utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def renewal_operation_key(*, workspace_id: UUID, paid_through: datetime) -> str:
    period = _utc(paid_through).isoformat()
    stable_id = uuid5(NAMESPACE_URL, f"graf:renewal:{workspace_id}:{period}")
    return f"renewal:{stable_id}"


def renewal_invoice_number(operation_id: UUID) -> str:
    return f"INV-RNW-{operation_id.hex[:20].upper()}"


async def _approved_catalog(
    db: AsyncSession,
    *,
    cycle: object,
    now: datetime,
) -> PlanCatalogSnapshot | None:
    if cycle not in {"month", "year"}:
        return None
    rows = await db.scalars(
        select(BillingPlanVersion)
        .where(
            BillingPlanVersion.plan_code == "personal",
            BillingPlanVersion.cycle == cycle,
        )
        .order_by(BillingPlanVersion.version.desc())
    )
    for row in rows:
        try:
            return validate_plan_version(row, now=now)
        except (CatalogNotApproved, ValueError):
            continue
    return None


def _snapshot(
    *, subscription: WorkspaceSubscription, catalog: PlanCatalogSnapshot
) -> dict[str, object]:
    paid_through = (
        _utc(subscription.paid_through) if subscription.paid_through is not None else None
    )
    return {
        "plan_code": "personal",
        "cycle": subscription.cycle,
        "list_amount_minor": catalog.amount_minor,
        "payable_amount_minor": catalog.amount_minor,
        "currency": catalog.currency,
        "catalog_snapshot": catalog.as_dict(),
        "storage_capacity_bytes": subscription.capacity_bytes,
        "billing_actor_user_id": str(subscription.billing_owner_id)
        if subscription.billing_owner_id
        else None,
        "recurring_authority_version": subscription.recurring_authority_version,
        "paid_through_at": paid_through.isoformat() if paid_through is not None else None,
        "purchased_duration": subscription.cycle,
    }


async def plan_due_renewals(
    db: AsyncSession,
    *,
    now: datetime | None = None,
    limit: int = 100,
    provider_floor_minor: int = 1,
) -> tuple[UUID, ...]:
    """Persist one renewal operation/invoice for each due subscription.

    The subscription row is locked while checking the deterministic period key.
    A missing saved method is a durable ``method_required`` state, not a
    provider mutation.  The caller owns the commit so the operation is durable
    before :func:`charge_renewal_operation` can call YooKassa.
    """
    current = _utc(now or datetime.now(UTC))
    if limit < 1 or limit > 500:
        raise ValueError("renewal planning limit must be between 1 and 500")
    if provider_floor_minor <= 0:
        raise ValueError("renewal provider floor must be positive")
    query = (
        select(WorkspaceSubscription)
        .join(Workspace, Workspace.id == WorkspaceSubscription.workspace_id)
        .join(
            WorkspaceMembership,
            WorkspaceMembership.workspace_id == WorkspaceSubscription.workspace_id,
        )
        .where(
            Workspace.kind == "personal",
            Workspace.owner_user_id == WorkspaceSubscription.billing_owner_id,
            WorkspaceMembership.user_id == WorkspaceSubscription.billing_owner_id,
            WorkspaceMembership.role == "owner",
            WorkspaceMembership.status == "active",
            WorkspaceSubscription.state == "personal",
            WorkspaceSubscription.plan_code == "personal",
            WorkspaceSubscription.recurring_allowed.is_(True),
            WorkspaceSubscription.paid_through.is_not(None),
            WorkspaceSubscription.paid_through > current,
            WorkspaceSubscription.paid_through <= current + timedelta(hours=RENEWAL_REMINDER_HOURS),
        )
        .order_by(WorkspaceSubscription.paid_through, WorkspaceSubscription.workspace_id)
        .limit(limit)
        .with_for_update(skip_locked=True)
    )
    planned: list[UUID] = []
    for subscription in await db.scalars(query):
        initial_checkout = await db.scalar(
            select(BillingOperation.id)
            .where(
                BillingOperation.workspace_id == subscription.workspace_id,
                BillingOperation.kind == "initial_checkout",
                BillingOperation.state.in_(CHECKOUT_BLOCKING_STATES),
            )
            .limit(1)
        )
        if initial_checkout is not None:
            continue
        catalog = await _approved_catalog(db, cycle=subscription.cycle, now=current)
        if (
            catalog is None
            or catalog.amount_minor is None
            or catalog.amount_minor < provider_floor_minor
            or subscription.billing_owner_id is None
            or subscription.paid_through is None
        ):
            subscription.renewal_resolution = (
                "provider_floor"
                if catalog is not None
                and catalog.amount_minor is not None
                and catalog.amount_minor < provider_floor_minor
                else "catalog_not_approved"
            )
            continue
        default_method = await db.scalar(
            select(BillingPaymentMethod)
            .where(
                BillingPaymentMethod.workspace_id == subscription.workspace_id,
                BillingPaymentMethod.owner_user_id == subscription.billing_owner_id,
                BillingPaymentMethod.state == "active",
                BillingPaymentMethod.is_default.is_(True),
                BillingPaymentMethod.verified_at.is_not(None),
            )
            .limit(1)
        )
        if default_method is None:
            subscription.renewal_resolution = "method_required"
            continue
        receipt_contact = await db.scalar(
            select(BillingInvoice.receipt_contact_snapshot)
            .where(
                BillingInvoice.workspace_id == subscription.workspace_id,
                BillingInvoice.status == "succeeded",
                BillingInvoice.receipt_contact_snapshot.is_not(None),
            )
            .order_by(BillingInvoice.created_at.desc())
            .limit(1)
        )
        if not isinstance(receipt_contact, str) or not receipt_contact.strip():
            subscription.renewal_resolution = "receipt_contact_required"
            continue
        key = renewal_operation_key(
            workspace_id=subscription.workspace_id,
            paid_through=subscription.paid_through,
        )
        existing = await db.scalar(
            select(BillingOperation)
            .where(
                BillingOperation.workspace_id == subscription.workspace_id,
                BillingOperation.kind == "renewal",
                BillingOperation.idempotency_key == key,
            )
            .with_for_update()
        )
        if existing is not None:
            if existing.state in RENEWAL_CANDIDATE_STATES and existing.provider_id is None:
                planned.append(existing.id)
            continue
        operation_id = uuid5(NAMESPACE_URL, f"graf:renewal-operation:{key}")
        snapshot = _snapshot(subscription=subscription, catalog=catalog)
        method_label = getattr(default_method, "masked_label", None)
        if isinstance(method_label, str) and method_label:
            snapshot["payment_method_label"] = method_label
        operation = BillingOperation(
            id=operation_id,
            workspace_id=subscription.workspace_id,
            kind="renewal",
            idempotency_key=key,
            state="scheduled",
            # Reserve during the reminder window, but do not mutate the
            # provider before the paid-through boundary.
            provider_key_expires_at=_utc(subscription.paid_through) + RENEWAL_PROVIDER_WINDOW,
            request_snapshot=snapshot,
        )
        db.add(operation)
        db.add(
            BillingInvoice(
                workspace_id=subscription.workspace_id,
                operation_id=operation_id,
                safe_number=renewal_invoice_number(operation_id),
                amount_minor=catalog.amount_minor,
                currency=catalog.currency,
                status="pending",
                plan_snapshot=snapshot,
                receipt_contact_snapshot=receipt_contact.strip(),
            )
        )
        db.add(
            BillingAuditEvent(
                workspace_id=subscription.workspace_id,
                actor_user_id=subscription.billing_owner_id,
                action="renewal.operation_scheduled",
                target_kind="billing_operation",
                target_ref=renewal_invoice_number(operation_id),
                outcome="scheduled",
                reason_code="one_operation_per_period",
                metadata_json=metadata_only(
                    {"cycle": str(subscription.cycle), "amount_minor": str(catalog.amount_minor)}
                ),
            )
        )
        planned.append(operation_id)
    await db.flush()
    return tuple(planned)


async def pending_renewal_charge_candidates(
    db: AsyncSession,
    *,
    now: datetime | None = None,
    limit: int = 100,
) -> tuple[tuple[UUID, UUID], ...]:
    """Return scheduled operations whose paid-through boundary has arrived."""
    current = _utc(now or datetime.now(UTC))
    rows = await db.execute(
        select(BillingOperation.id, BillingOperation.workspace_id)
        .join(Workspace, Workspace.id == BillingOperation.workspace_id)
        .join(
            WorkspaceSubscription,
            WorkspaceSubscription.workspace_id == BillingOperation.workspace_id,
        )
        .join(
            WorkspaceMembership,
            WorkspaceMembership.workspace_id == BillingOperation.workspace_id,
        )
        .where(
            Workspace.kind == "personal",
            Workspace.owner_user_id == WorkspaceSubscription.billing_owner_id,
            WorkspaceMembership.user_id == WorkspaceSubscription.billing_owner_id,
            WorkspaceMembership.role == "owner",
            WorkspaceMembership.status == "active",
            BillingOperation.kind == "renewal",
            BillingOperation.provider_id.is_(None),
            BillingOperation.state.in_(RENEWAL_CANDIDATE_STATES),
            BillingOperation.provider_key_expires_at.is_not(None),
            BillingOperation.provider_key_expires_at > current,
        )
        .order_by(BillingOperation.updated_at, BillingOperation.id)
        .limit(limit)
    )
    candidates: list[tuple[UUID, UUID]] = []
    for operation_id, workspace_id in rows.all():
        operation = await db.get(BillingOperation, operation_id)
        if operation is None:
            continue
        paid_through_at = operation.request_snapshot.get("paid_through_at")
        if not isinstance(paid_through_at, str):
            continue
        try:
            due_at = _utc(datetime.fromisoformat(paid_through_at))
        except ValueError:
            continue
        if due_at <= current:
            candidates.append((operation_id, workspace_id))
    return tuple(candidates)


def _project_free(subscription: WorkspaceSubscription) -> None:
    subscription.state = "free"
    subscription.plan_code = "free"
    subscription.cycle = "none"
    subscription.capacity_bytes = FREE_STORAGE_BYTES
    subscription.application_version = (subscription.application_version or 0) + 1


def _record_charge_audit(
    db: AsyncSession,
    *,
    subscription: WorkspaceSubscription,
    operation: BillingOperation,
    outcome: str,
    reason_code: str,
) -> None:
    db.add(
        BillingAuditEvent(
            workspace_id=subscription.workspace_id,
            actor_user_id=subscription.billing_owner_id,
            action="renewal.provider_charge",
            target_kind="billing_operation",
            target_ref=None,
            outcome=outcome,
            reason_code=reason_code,
            metadata_json={"state": operation.state},
        )
    )


async def project_renewal_cutoffs(
    db: AsyncSession,
    *,
    now: datetime | None = None,
    limit: int = 100,
) -> int:
    """Project missed/final renewal outcomes to Free exactly at paid cutoff."""
    current = _utc(now or datetime.now(UTC))
    query = (
        select(WorkspaceSubscription)
        .where(
            WorkspaceSubscription.plan_code == "personal",
            WorkspaceSubscription.paid_through.is_not(None),
            WorkspaceSubscription.paid_through <= current,
        )
        .order_by(WorkspaceSubscription.paid_through, WorkspaceSubscription.workspace_id)
        .limit(limit)
        .with_for_update(skip_locked=True)
    )
    projected = 0
    for subscription in await db.scalars(query):
        workspace = await db.get(Workspace, subscription.workspace_id)
        owner = await db.scalar(
            select(WorkspaceMembership).where(
                WorkspaceMembership.workspace_id == subscription.workspace_id,
                WorkspaceMembership.user_id == subscription.billing_owner_id,
                WorkspaceMembership.role == "owner",
                WorkspaceMembership.status == "active",
            )
        )
        scope_valid = (
            workspace is not None
            and workspace.kind == "personal"
            and workspace.owner_user_id == subscription.billing_owner_id
            and owner is not None
        )
        operation = await db.scalar(
            select(BillingOperation)
            .where(
                BillingOperation.workspace_id == subscription.workspace_id,
                BillingOperation.kind == "renewal",
            )
            .order_by(BillingOperation.created_at.desc(), BillingOperation.id.desc())
            .limit(1)
        )
        state = operation.state if operation is not None else None
        pending = state in RENEWAL_PROVIDER_STATES
        if not scope_valid:
            _project_free(subscription)
            if subscription.recurring_allowed:
                subscription.recurring_allowed = False
                subscription.recurring_authority_version = (
                    subscription.recurring_authority_version or 0
                ) + 1
            subscription.renewal_resolution = "workspace_scope_invalid"
            db.add(
                BillingAuditEvent(
                    workspace_id=subscription.workspace_id,
                    actor_user_id=subscription.billing_owner_id,
                    action="renewal.cutoff_projected_free",
                    target_kind="workspace_subscription",
                    target_ref=None,
                    outcome="blocked",
                    reason_code="workspace_scope_invalid",
                    metadata_json={"no_grace": "true"},
                )
            )
            projected += 1
            continue
        if subscription.state == "free" and subscription.plan_code == "free":
            if state == "provider_key_expired" and subscription.recurring_allowed:
                subscription.recurring_allowed = False
                subscription.recurring_authority_version = (
                    subscription.recurring_authority_version or 0
                ) + 1
                subscription.renewal_resolution = "manual_resume_required"
            continue
        _project_free(subscription)
        if pending:
            subscription.renewal_resolution = (
                "provider_key_expired" if state == "provider_key_expired" else "unknown_pending"
            )
        else:
            subscription.recurring_allowed = False
            subscription.recurring_authority_version = (
                subscription.recurring_authority_version or 0
            ) + 1
            subscription.renewal_resolution = "manual_resume_required"
        db.add(
            BillingAuditEvent(
                workspace_id=subscription.workspace_id,
                actor_user_id=subscription.billing_owner_id,
                action="renewal.cutoff_projected_free",
                target_kind="workspace_subscription",
                target_ref=None,
                outcome="projected",
                reason_code="unknown_pending" if pending else "renewal_not_confirmed",
                metadata_json={"no_grace": "true"},
            )
        )
        projected += 1
    await db.flush()
    return projected


async def charge_renewal_operation(
    db: AsyncSession,
    settings: Settings,
    *,
    operation_id: UUID,
    workspace_id: UUID,
    now: datetime | None = None,
) -> RenewalChargeResult:
    """Send one saved-method payment while holding the subscription authority lock."""
    current = _utc(now or datetime.now(UTC))
    await db.rollback()
    subscription = await db.scalar(
        select(WorkspaceSubscription)
        .where(WorkspaceSubscription.workspace_id == workspace_id)
        .with_for_update()
    )
    operation = await db.scalar(
        select(BillingOperation)
        .where(
            BillingOperation.id == operation_id,
            BillingOperation.workspace_id == workspace_id,
            BillingOperation.kind == "renewal",
        )
        .with_for_update()
    )
    if operation is None:
        await db.rollback()
        return RenewalChargeResult(operation_id, "missing")
    if operation.provider_id is not None or operation.state not in RENEWAL_CANDIDATE_STATES:
        await db.rollback()
        return RenewalChargeResult(operation_id, operation.state, operation.provider_id)
    invoice = await db.scalar(
        select(BillingInvoice)
        .where(
            BillingInvoice.operation_id == operation.id,
            BillingInvoice.workspace_id == workspace_id,
        )
        .with_for_update()
    )
    if subscription is None or invoice is None:
        operation.state = "manual_resolution"
        await db.commit()
        return RenewalChargeResult(operation_id, "manual_resolution")
    workspace = await db.get(Workspace, workspace_id)
    owner = await db.scalar(
        select(WorkspaceMembership)
        .where(
            WorkspaceMembership.workspace_id == workspace_id,
            WorkspaceMembership.user_id == subscription.billing_owner_id,
            WorkspaceMembership.role == "owner",
            WorkspaceMembership.status == "active",
        )
        .with_for_update()
    )
    try:
        billing_actor_id = UUID(str(operation.request_snapshot.get("billing_actor_user_id")))
    except (TypeError, ValueError):
        billing_actor_id = None
    if (
        workspace is None
        or workspace.kind != "personal"
        or workspace.owner_user_id != subscription.billing_owner_id
        or owner is None
        or billing_actor_id != subscription.billing_owner_id
    ):
        operation.state = "manual_resolution"
        invoice.status = "manual_resolution"
        if subscription.recurring_allowed:
            subscription.recurring_allowed = False
            subscription.recurring_authority_version = (
                subscription.recurring_authority_version or 0
            ) + 1
        subscription.renewal_resolution = "workspace_scope_invalid"
        await db.commit()
        return RenewalChargeResult(operation_id, "manual_resolution")
    expected_paid_through = operation.request_snapshot.get("paid_through_at")
    current_paid_through = (
        _utc(subscription.paid_through).isoformat()
        if subscription.paid_through is not None
        else None
    )
    if expected_paid_through != current_paid_through:
        operation.state = "canceled"
        invoice.status = "canceled"
        subscription.renewal_resolution = "schedule_changed"
        _record_charge_audit(
            db,
            subscription=subscription,
            operation=operation,
            outcome="canceled",
            reason_code="renewal_schedule_changed",
        )
        await db.commit()
        return RenewalChargeResult(operation_id, "canceled")
    if subscription.paid_through is not None and _utc(subscription.paid_through) > current:
        # The reminder window reserves the operation; the provider mutation
        # starts at the exact paid-through boundary, never earlier.
        await db.rollback()
        return RenewalChargeResult(operation_id, "scheduled")
    if (
        operation.provider_key_expires_at is None
        or _utc(operation.provider_key_expires_at) <= current
    ):
        operation.state = "manual_resolution"
        invoice.status = "manual_resolution"
        subscription.recurring_allowed = False
        subscription.recurring_authority_version = (
            subscription.recurring_authority_version or 0
        ) + 1
        subscription.renewal_resolution = "provider_key_expired"
        _record_charge_audit(
            db,
            subscription=subscription,
            operation=operation,
            outcome="manual_resolution",
            reason_code="provider_key_expired",
        )
        await db.commit()
        return RenewalChargeResult(operation_id, "manual_resolution")
    try:
        require_billing_enabled(
            checkout_enabled=bool(settings.billing_checkout_enabled),
            emergency_stop=bool(settings.billing_emergency_stop),
        )
        expected_version = operation.request_snapshot.get("recurring_authority_version")
        if (
            subscription.billing_owner_id is None
            or not subscription.recurring_allowed
            or not isinstance(expected_version, int)
            or isinstance(expected_version, bool)
        ):
            raise ValueError("recurring authority is unavailable")
        require_authority_version(
            expected=expected_version,
            actual=subscription.recurring_authority_version,
        )
        method = await db.scalar(
            select(BillingPaymentMethod)
            .where(
                BillingPaymentMethod.workspace_id == workspace_id,
                BillingPaymentMethod.owner_user_id == subscription.billing_owner_id,
                BillingPaymentMethod.state == "active",
                BillingPaymentMethod.is_default.is_(True),
                BillingPaymentMethod.verified_at.is_not(None),
            )
            .with_for_update()
        )
        key = read_billing_encryption_key(settings.credential_encryption_key_file)
        if method is None or key is None or method.key_version != "billing-v1":
            raise ValueError("saved payment method is unavailable")
        provider_ref = open_provider_reference(
            method.encrypted_provider_ref,
            key,
        )
        if invoice.amount_minor <= 0 or invoice.currency != "RUB":
            raise ValueError("renewal invoice is invalid")
        provider_environment(settings.billing_yookassa_environment)
        operation.state = "processing"
        await db.flush()
        async with YooKassaClient(settings) as provider:
            receipt = build_receipt_payload(
                receipt_contact=invoice.receipt_contact_snapshot,
                amount_minor=invoice.amount_minor,
                currency=invoice.currency,
                description=f"GRAF Личный, {operation.request_snapshot.get('cycle', 'month')}",
                tax_system_code=settings.billing_receipt_tax_system_code,
                vat_code=settings.billing_receipt_vat_code,
                payment_subject=settings.billing_receipt_payment_subject,
                payment_mode=settings.billing_receipt_payment_mode,
            )
            payment = await provider.create_payment(
                amount_minor=invoice.amount_minor,
                currency=invoice.currency,
                description=f"GRAF Личный, {operation.request_snapshot.get('cycle', 'month')}",
                idempotence_key=operation.idempotency_key,
                metadata={
                    "workspace_id": str(workspace_id),
                    "operation_id": str(operation.id),
                    "invoice_number": invoice.safe_number,
                },
                payment_method_id=provider_ref,
                receipt=receipt,
            )
        provider_id = payment.get("id")
        if not isinstance(provider_id, str):
            raise YooKassaProviderError("provider payment reference is missing")
        provider_id = validate_provider_identifier(provider_id)
        operation.provider_id = provider_id
        operation.state = "sent"
        invoice.status = "pending"
        _record_charge_audit(
            db,
            subscription=subscription,
            operation=operation,
            outcome="sent",
            reason_code="saved_method_charge_sent",
        )
        await db.commit()
        return RenewalChargeResult(operation_id, "sent", provider_id)
    except BillingEmergencyStop:
        await db.rollback()
        return RenewalChargeResult(operation_id, "blocked")
    except BillingAuthorizationError:
        operation.state = "canceled"
        invoice.status = "canceled"
        subscription.renewal_resolution = "authority_refused"
        _record_charge_audit(
            db,
            subscription=subscription,
            operation=operation,
            outcome="canceled",
            reason_code="recurring_authority_changed",
        )
        await db.commit()
        return RenewalChargeResult(operation_id, "canceled")
    except YooKassaProviderError as exc:
        if exc.status_code is not None and 400 <= exc.status_code < 500:
            operation.state = "canceled"
            invoice.status = "canceled"
            subscription.recurring_allowed = False
            subscription.recurring_authority_version = (
                subscription.recurring_authority_version or 0
            ) + 1
            subscription.renewal_resolution = "canceled"
            if subscription.paid_through is not None and _utc(subscription.paid_through) <= current:
                _project_free(subscription)
            _record_charge_audit(
                db,
                subscription=subscription,
                operation=operation,
                outcome="canceled",
                reason_code="provider_declined",
            )
            await db.commit()
            return RenewalChargeResult(operation_id, "canceled")
        operation.state = "unknown"
        invoice.status = "unknown"
        subscription.renewal_resolution = "pending"
        _record_charge_audit(
            db,
            subscription=subscription,
            operation=operation,
            outcome="unknown",
            reason_code="provider_observation_unknown",
        )
        await db.commit()
        return RenewalChargeResult(operation_id, "unknown")
    except (httpx.HTTPError, YooKassaConfigurationError):
        operation.state = "unknown"
        invoice.status = "unknown"
        subscription.renewal_resolution = "pending"
        _record_charge_audit(
            db,
            subscription=subscription,
            operation=operation,
            outcome="unknown",
            reason_code="provider_transport_unknown",
        )
        await db.commit()
        return RenewalChargeResult(operation_id, "unknown")
    except (ValueError, TypeError):
        operation.state = "manual_resolution"
        invoice.status = "manual_resolution"
        subscription.renewal_resolution = "method_required"
        _record_charge_audit(
            db,
            subscription=subscription,
            operation=operation,
            outcome="manual_resolution",
            reason_code="renewal_precondition_failed",
        )
        await db.commit()
        return RenewalChargeResult(operation_id, "manual_resolution")
