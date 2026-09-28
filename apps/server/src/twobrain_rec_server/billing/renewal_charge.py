"""Plan and execute the single saved-method renewal attempt.

The module deliberately keeps planning, provider mutation and outcome
reconciliation separate.  A renewal operation is persisted before the first
outbound request and is identified by a deterministic period key, so a
worker restart cannot create a second charge for the same paid interval.
"""

from __future__ import annotations

from collections.abc import Mapping
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
from twobrain_rec_server.billing.events import enqueue_billing_notification
from twobrain_rec_server.billing.notifications import BillingNotification
from twobrain_rec_server.billing.operations import (
    CHECKOUT_BLOCKING_STATES,
    BillingCheckoutDisabled,
    billing_checkout_allowed,
    require_billing_enabled,
)
from twobrain_rec_server.billing.payment_methods import (
    open_provider_reference,
    read_billing_encryption_key,
)
from twobrain_rec_server.billing.provider_events import validate_provider_identifier
from twobrain_rec_server.billing.purchases import (
    PurchaseError,
    base_price_is_accepted,
    compose_personal_catalog,
    reserve_acceptance_budget,
    settle_acceptance_budget,
    storage_price_is_accepted,
    storage_price_snapshot,
)
from twobrain_rec_server.billing.reconciliation import ProviderScope, validate_purchase_payment
from twobrain_rec_server.billing.storage import lock_storage_workspace
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
# Three attempts land 72, 48 and 24 hours before the paid-through boundary.
# The attempt interval equals the provider window, so the attempts never
# overlap: one declined card still leaves room for a real next attempt.
RENEWAL_ATTEMPT_COUNT = 3
RENEWAL_ATTEMPT_INTERVAL = timedelta(hours=24)
RENEWAL_ATTEMPTS = tuple(range(1, RENEWAL_ATTEMPT_COUNT + 1))
# The copy for a failed attempt states the moment access ends, in Moscow time.
MOSCOW_OFFSET = timedelta(hours=3)
# A missing provider id after a transport error is not safe to POST again:
# YooKassa may have accepted the first request. Only an untouched operation
# may enter the outbound mutation path; unknown is GET/list/manual recovery.
RENEWAL_CANDIDATE_STATES = frozenset({"scheduled"})
# Scheduled work remains pending only inside its dispatch window. At cutoff,
# expired unsent attempts are canceled before classifying the provider state.
# Sent or unknown payments still require authoritative reconciliation.
RENEWAL_PROVIDER_STATES = frozenset({"scheduled", "sent", "unknown", "processing"})


@dataclass(frozen=True, slots=True)
class RenewalChargeResult:
    operation_id: UUID
    status: str
    provider_id: str | None = None


def _utc(value: datetime) -> datetime:
    return value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)


def renewal_attempt_due_at(*, paid_through: datetime, attempt: int) -> datetime:
    """Return the moment one renewal attempt may start.

    Attempt ``1`` lands ``RENEWAL_REMINDER_HOURS`` before the paid-through
    boundary, every next attempt one interval later. Each window lasts 24 hours;
    missed windows are skipped and never produce a catch-up series of payments.
    """
    if attempt not in RENEWAL_ATTEMPTS:
        raise ValueError("renewal attempt number is invalid")
    first = _utc(paid_through) - timedelta(hours=RENEWAL_REMINDER_HOURS)
    return first + RENEWAL_ATTEMPT_INTERVAL * (attempt - 1)


def renewal_attempt_of(operation: BillingOperation) -> int:
    """Return the stored attempt number of one renewal operation.

    Operations planned before attempt scheduling existed carry no number. They
    were the only attempt of their period, so they stay final.
    """
    snapshot = operation.request_snapshot
    attempt = snapshot.get("renewal_attempt") if isinstance(snapshot, Mapping) else None
    if isinstance(attempt, int) and not isinstance(attempt, bool) and attempt in RENEWAL_ATTEMPTS:
        return attempt
    return RENEWAL_ATTEMPT_COUNT


def renewal_canceled_before_dispatch(operation) -> bool:
    return (
        operation.state == "canceled"
        and operation.provider_id is None
        and (operation.request_snapshot or {}).get("cancel_reason") in {
            "authority_cancelled", "acceptance_budget", "provider_unavailable"
        }
    )


def next_renewal_attempt(
    *,
    paid_through: datetime,
    now: datetime,
    resolved_attempts: set[int],
    unresolved: bool,
) -> datetime | None:
    """The same non-catch-up windows drive both the scheduler and user copy."""
    if unresolved:
        return None
    current = _utc(now)
    for attempt in RENEWAL_ATTEMPTS:
        due = renewal_attempt_due_at(paid_through=paid_through, attempt=attempt)
        if current >= due + RENEWAL_ATTEMPT_INTERVAL or attempt in resolved_attempts:
            continue
        return max(current, due)
    return None


def renewal_operation_key(
    *,
    workspace_id: UUID,
    paid_through: datetime,
    attempt: int = 1,
) -> str:
    """Return the idempotency key of one attempt of one paid period.

    The period reference is the same for every attempt, so re-planning one
    attempt reuses its operation.  The attempt suffix keeps the three attempts
    of one period apart, so each of them is a separate payment.
    """
    if attempt not in RENEWAL_ATTEMPTS:
        raise ValueError("renewal attempt number is invalid")
    period = _utc(paid_through).isoformat()
    stable_id = uuid5(NAMESPACE_URL, f"graf:renewal:{workspace_id}:{period}")
    return f"renewal:{stable_id}:a{attempt}"


def _moscow_label(value: datetime) -> str:
    return (_utc(value) + MOSCOW_OFFSET).strftime("%d.%m.%Y %H:%M")


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
        "purchase_purpose": "renewal",
        "cycle": subscription.cycle,
        "list_amount_minor": catalog.amount_minor,
        "payable_amount_minor": catalog.amount_minor,
        "currency": catalog.currency,
        "catalog_snapshot": catalog.as_dict(),
        "storage_capacity_bytes": catalog.storage_bytes,
        "selection_version": subscription.next_capacity_version or 0,
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
    provider_floor_minor: int = 100,
    allowed_workspace_ids: frozenset[UUID] | None = None,
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
    )
    if allowed_workspace_ids is not None:
        query = query.where(WorkspaceSubscription.workspace_id.in_(allowed_workspace_ids))
    planned: list[UUID] = []
    for subscription in await db.scalars(query):
        await lock_storage_workspace(db, subscription.workspace_id)
        await db.refresh(subscription, with_for_update=True)
        if (
            not subscription.recurring_allowed
            or not subscription.paid_through
            or subscription.paid_through <= current
        ):
            continue
        initial_checkout = await db.scalar(
            select(BillingOperation.id)
            .where(
                BillingOperation.workspace_id == subscription.workspace_id,
                BillingOperation.kind.in_(("initial_checkout", "storage_upgrade", "early_renewal")),
                BillingOperation.state.in_(CHECKOUT_BLOCKING_STATES),
            )
            .with_for_update()
            .limit(1)
        )
        if initial_checkout is not None:
            continue
        catalog = await _approved_catalog(db, cycle=subscription.cycle, now=current)
        base_catalog = catalog
        storage_price = None
        if catalog is not None:
            try:
                catalog, storage_price = await compose_personal_catalog(
                    db, base=catalog, subscription=subscription, now=current
                )
            except PurchaseError:
                subscription.renewal_resolution = "catalog_not_approved"
                continue
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
        if not base_price_is_accepted(subscription, base_catalog) or not storage_price_is_accepted(
            subscription, storage_price
        ):
            subscription.renewal_resolution = "price_changed"
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
        selected: tuple[int, str, datetime] | None = None
        # Attempts of one period are strictly sequential: the next key is
        # created only once the previous attempt is resolved at the provider,
        # so two attempts can never be in flight for the same paid period.
        for attempt in RENEWAL_ATTEMPTS:
            due_at = renewal_attempt_due_at(
                paid_through=subscription.paid_through,
                attempt=attempt,
            )
            if due_at > current:
                # This attempt is still ahead, and so is every later one.
                break
            key = renewal_operation_key(
                workspace_id=subscription.workspace_id,
                paid_through=subscription.paid_through,
                attempt=attempt,
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
            if (
                existing is not None
                and renewal_canceled_before_dispatch(existing)
                and existing.request_snapshot.get("cancel_reason") == "authority_cancelled"
            ):
                # A revoked, never-sent mandate did not use a bank attempt.
                # A fresh explicit mandate gets a distinct immutable operation.
                key = f"{key}:authority:{subscription.recurring_authority_version}"
                existing = await db.scalar(
                    select(BillingOperation)
                    .where(
                        BillingOperation.workspace_id == subscription.workspace_id,
                        BillingOperation.kind == "renewal",
                        BillingOperation.idempotency_key == key,
                    )
                    .with_for_update()
                )
            if (
                existing is not None
                and renewal_canceled_before_dispatch(existing)
                and existing.request_snapshot.get("cancel_reason") in {
                    "acceptance_budget", "provider_unavailable"
                }
            ):
                # Repeated local failures do not use a bank attempt. Find the
                # latest immutable successor under the workspace lock instead
                # of exhausting the single authority-version successor.
                root_key = renewal_operation_key(
                    workspace_id=subscription.workspace_id,
                    paid_through=subscription.paid_through,
                    attempt=attempt,
                )
                latest = await db.scalar(
                    select(BillingOperation)
                    .where(
                        BillingOperation.workspace_id == subscription.workspace_id,
                        BillingOperation.kind == "renewal",
                        BillingOperation.idempotency_key.startswith(root_key + ":"),
                    )
                    .order_by(BillingOperation.created_at.desc(), BillingOperation.id.desc())
                    .with_for_update()
                    .limit(1)
                )
                existing = latest or existing
                if (
                    renewal_canceled_before_dispatch(existing)
                    and current < due_at + RENEWAL_ATTEMPT_INTERVAL
                ):
                    key = f"{root_key}:retry:{existing.id}"
                    existing = None
            if current >= due_at + RENEWAL_ATTEMPT_INTERVAL:
                if (
                    existing is not None
                    and existing.state != "canceled"
                    and not (existing.state == "scheduled" and existing.provider_id is None)
                ):
                    break  # An older unknown payment still may succeed.
                continue  # No charge for a missed window.
            if existing is not None:
                if (
                    existing.provider_id is None
                    and existing.provider_key_expires_at is not None
                    and _utc(existing.provider_key_expires_at) > current
                    and existing.state in RENEWAL_CANDIDATE_STATES
                ):
                    # Still chargeable: charge this attempt before the next one.
                    planned.append(existing.id)
                    break
                if existing.state != "canceled" and not (
                    existing.state == "scheduled" and existing.provider_id is None
                ):
                    # The provider may still complete this attempt, so a new
                    # idempotency key must not open a second payment. Scope or
                    # reconciliation terminal states are also preserved as
                    # non-chargeable history for this paid period.
                    break
                # Resolved, or spent with an expired provider window: the next
                # attempt of the same period takes over.
                continue
            selected = (attempt, key, due_at)
            break
        if selected is None:
            continue
        attempt, key, due_at = selected
        operation_id = uuid5(NAMESPACE_URL, f"graf:renewal-operation:{key}")
        snapshot = _snapshot(subscription=subscription, catalog=catalog)
        snapshot["storage_price_snapshot"] = storage_price_snapshot(storage_price)
        snapshot["renewal_attempt"] = attempt
        method_label = getattr(default_method, "masked_label", None)
        if isinstance(method_label, str) and method_label:
            snapshot["payment_method_label"] = method_label
        operation = BillingOperation(
            id=operation_id,
            workspace_id=subscription.workspace_id,
            kind="renewal",
            idempotency_key=key,
            state="scheduled",
            # The attempt opens its own provider window when it is launched, so
            # an attempt planned inside the reminder window is chargeable right
            # away. Nothing reaches further than one window past the boundary.
            provider_key_expires_at=due_at + RENEWAL_ATTEMPT_INTERVAL,
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
                    {
                        "cycle": str(subscription.cycle),
                        "amount_minor": str(catalog.amount_minor),
                        "attempt": str(attempt),
                    }
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
    """Return scheduled operations whose own attempt moment has arrived."""
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
            due_at = renewal_attempt_due_at(
                paid_through=datetime.fromisoformat(paid_through_at),
                attempt=renewal_attempt_of(operation),
            )
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
    )
    projected = 0
    for candidate in await db.scalars(query):
        await lock_storage_workspace(db, candidate.workspace_id)
        subscription = await db.scalar(
            select(WorkspaceSubscription).where(
                WorkspaceSubscription.workspace_id == candidate.workspace_id,
            ).with_for_update().execution_options(populate_existing=True)
        )
        if (subscription is None or subscription.plan_code != "personal"
                or subscription.paid_through is None
                or _utc(subscription.paid_through) > current):
            continue
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
        expired_unsent = await db.scalars(
            select(BillingOperation).where(
                BillingOperation.workspace_id == subscription.workspace_id,
                BillingOperation.kind == "renewal",
                BillingOperation.state == "scheduled",
                BillingOperation.provider_id.is_(None),
                BillingOperation.provider_key_expires_at <= current,
            ).with_for_update()
        )
        for missed in expired_unsent:
            missed.state = "canceled"
            missed.request_snapshot = {**missed.request_snapshot, "cancel_reason": "window_missed"}
            missed_invoice = await db.scalar(select(BillingInvoice).where(
                BillingInvoice.operation_id == missed.id).with_for_update())
            if missed_invoice is not None:
                missed_invoice.status = "canceled"
            await settle_acceptance_budget(
                db, workspace_id=subscription.workspace_id,
                operation_id=missed.id, succeeded=False,
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


async def _enqueue_renewal_attempt_failure(
    db: AsyncSession,
    *,
    subscription: WorkspaceSubscription,
    invoice: BillingInvoice,
) -> None:
    """Tell the payer that one attempt failed and when access ends."""
    if subscription.billing_owner_id is None or subscription.paid_through is None:
        return
    await enqueue_billing_notification(
        db,
        workspace_id=subscription.workspace_id,
        recipient_id=subscription.billing_owner_id,
        event_id=f"renewal:{invoice.id}:attempt_failed",
        kind=BillingNotification.RENEWAL_ATTEMPT_FAILED,
        payload={
            "invoice": invoice.safe_number,
            "access_until": _moscow_label(subscription.paid_through),
            "action_path": "/billing/subscription",
        },
        marketing_allowed=False,
    )


async def record_renewal_decline(
    db: AsyncSession,
    *,
    subscription: WorkspaceSubscription | None,
    operation: BillingOperation,
    invoice: BillingInvoice,
    now: datetime,
    reason_code: str = "provider_declined",
) -> None:
    """Apply a confirmed decline to locked rows; the caller owns the transaction."""
    if (
        operation.kind != "renewal"
        or invoice.operation_id != operation.id
        or invoice.workspace_id != operation.workspace_id
        or (subscription is not None and subscription.workspace_id != operation.workspace_id)
    ):
        raise ValueError("renewal decline binding does not match")
    if (
        operation.state in {"canceled", "succeeded", "succeeded_refused"}
        or invoice.status == "succeeded"
    ):
        return
    await settle_acceptance_budget(
        db, workspace_id=operation.workspace_id, operation_id=operation.id, succeeded=False
    )
    operation.state = "canceled"
    invoice.status = "canceled"
    snapshot = operation.request_snapshot
    # A delayed observation may close old financial history, but must not
    # disable a new owner's card or announce the end of a newer paid period.
    if (
        subscription is None
        or subscription.paid_through is None
        or subscription.billing_owner_id is None
        or not isinstance(snapshot, Mapping)
        or snapshot.get("billing_actor_user_id") != str(subscription.billing_owner_id)
        or snapshot.get("paid_through_at") != _utc(subscription.paid_through).isoformat()
        or type(snapshot.get("recurring_authority_version")) is not int
        or snapshot["recurring_authority_version"] != subscription.recurring_authority_version
    ):
        return
    if renewal_attempt_of(operation) >= RENEWAL_ATTEMPT_COUNT:
        if subscription.recurring_allowed:
            subscription.recurring_allowed = False
            subscription.recurring_authority_version = (
                subscription.recurring_authority_version or 0
            ) + 1
        subscription.renewal_resolution = "canceled"
        if _utc(subscription.paid_through) <= _utc(now):
            _project_free(subscription)
    else:
        subscription.renewal_resolution = "attempt_failed"
    _record_charge_audit(
        db,
        subscription=subscription,
        operation=operation,
        outcome="canceled",
        reason_code=reason_code,
    )
    await _enqueue_renewal_attempt_failure(db, subscription=subscription, invoice=invoice)


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
    await lock_storage_workspace(db, workspace_id)
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
    dispatched = False

    async def refresh_after_dispatch():
        if not dispatched:
            return None
        await lock_storage_workspace(db, workspace_id)
        await db.refresh(subscription, with_for_update=True)
        await db.refresh(operation, with_for_update=True)
        await db.refresh(invoice, with_for_update=True)
        if (
            operation.state in {"succeeded", "succeeded_refused", "canceled", "reconciliation_gap"}
            or invoice.status == "succeeded"
        ):
            await db.commit()
            return RenewalChargeResult(operation_id, operation.state, operation.provider_id)
        return None

    async def cancel_before_dispatch(reason: str) -> RenewalChargeResult:
        operation.state = invoice.status = "canceled"
        operation.request_snapshot = {**operation.request_snapshot, "cancel_reason": reason}
        subscription.renewal_resolution = reason
        await settle_acceptance_budget(
            db, workspace_id=workspace_id, operation_id=operation.id, succeeded=False
        )
        _record_charge_audit(
            db, subscription=subscription, operation=operation,
            outcome="canceled", reason_code=reason,
        )
        await db.commit()
        return RenewalChargeResult(operation_id, "canceled")

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
        return await cancel_before_dispatch("schedule_changed")
    attempt = renewal_attempt_of(operation)
    due_at = (
        renewal_attempt_due_at(paid_through=subscription.paid_through, attempt=attempt)
        if subscription.paid_through is not None
        else None
    )
    if due_at is None or due_at > current:
        # Each attempt waits for its own moment inside the reminder window and
        # never starts earlier; an attempt planned late fires at once. A
        # renewal without a paid period cannot be charged at all.
        await db.rollback()
        return RenewalChargeResult(operation_id, "scheduled")
    if current >= due_at + RENEWAL_ATTEMPT_INTERVAL:
        return await cancel_before_dispatch("window_missed")
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
    if operation.state == "scheduled":
        current_base = await _approved_catalog(db, cycle=subscription.cycle, now=current)
        try:
            if current_base is None:
                raise PurchaseError("Цена недоступна")
            current_catalog, current_storage = await compose_personal_catalog(
                db, base=current_base, subscription=subscription, now=current
            )
            accepted = base_price_is_accepted(subscription, current_base)
            accepted = accepted and current_catalog.as_dict() == operation.request_snapshot.get(
                "catalog_snapshot"
            )
            accepted = accepted and storage_price_is_accepted(subscription, current_storage)
            accepted = accepted and storage_price_snapshot(
                current_storage
            ) == operation.request_snapshot.get("storage_price_snapshot")
        except PurchaseError:
            accepted = False
        if not accepted:
            return await cancel_before_dispatch("price_changed")
    try:
        require_billing_enabled(
            checkout_enabled=billing_checkout_allowed(settings, workspace_id),
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
        if method is None:
            await record_renewal_decline(
                db,
                subscription=subscription,
                operation=operation,
                invoice=invoice,
                now=current,
                reason_code="saved_method_missing",
            )
            await db.commit()
            return RenewalChargeResult(operation_id, operation.state)
        key = read_billing_encryption_key(settings.credential_encryption_key_file)
        if key is None or method.key_version != "billing-v1":
            raise ValueError("saved payment method is unavailable")
        provider_ref = open_provider_reference(
            method.encrypted_provider_ref,
            key,
        )
        if (
            invoice.amount_minor < max(100, settings.billing_provider_floor_minor)
            or invoice.currency != "RUB"
        ):
            raise ValueError("renewal invoice is invalid")
        provider_environment(settings.billing_yookassa_environment)
        try:
            await reserve_acceptance_budget(
                db,
                workspace_id=workspace_id,
                operation_id=operation.id,
                amount_minor=invoice.amount_minor,
                now=current,
            )
        except PurchaseError:
            return await cancel_before_dispatch("acceptance_budget")
        operation.request_snapshot = {
            **operation.request_snapshot,
            "purchase_schema": 2,
            "provider_environment": settings.billing_yookassa_environment,
            "provider_shop_id": settings.billing_yookassa_shop_id,
        }
        invoice.plan_snapshot = {
            **(invoice.plan_snapshot or {}),
            "purchase_schema": 2,
            "provider_environment": settings.billing_yookassa_environment,
            "provider_shop_id": settings.billing_yookassa_shop_id,
        }
        operation.state = "processing"
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
            await db.commit()  # Persist budget and send marker before the POST.
            dispatched = True
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
        await lock_storage_workspace(db, workspace_id)
        await db.refresh(subscription, with_for_update=True)
        await db.refresh(operation, with_for_update=True)
        await db.refresh(invoice, with_for_update=True)
        if (
            operation.state in {"succeeded", "succeeded_refused", "canceled", "reconciliation_gap"}
            or invoice.status == "succeeded"
        ):
            await db.commit()
            return RenewalChargeResult(operation_id, operation.state, operation.provider_id)
        provider_id = payment.get("id")
        if not isinstance(provider_id, str):
            raise YooKassaProviderError("provider payment reference is missing")
        provider_id = validate_provider_identifier(provider_id)
        operation.provider_id = provider_id
        if payment.get("status") == "canceled":
            try:
                validate_purchase_payment(
                    payment,
                    operation=operation,
                    invoice=invoice,
                    scope=ProviderScope(
                        environment=settings.billing_yookassa_environment,
                        shop_id=settings.billing_yookassa_shop_id,
                    ),
                )
            except ValueError as exc:
                raise YooKassaProviderError("provider payment binding is invalid") from exc
            await record_renewal_decline(
                db,
                subscription=subscription,
                operation=operation,
                invoice=invoice,
                now=current,
            )
            await db.commit()
            return RenewalChargeResult(operation_id, operation.state, provider_id)
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
    except BillingCheckoutDisabled:
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
        completed = await refresh_after_dispatch()
        if completed is not None:
            return completed
        if exc.status_code == 429:
            # The minute-based reconciler retries this operation with its
            # original key; the persisted key deadline still bounds retries.
            operation.state = "scheduled"
            invoice.status = "pending"
            subscription.renewal_resolution = "pending"
            _record_charge_audit(
                db,
                subscription=subscription,
                operation=operation,
                outcome="scheduled",
                reason_code="provider_rate_limited",
            )
            await db.commit()
            return RenewalChargeResult(operation_id, "scheduled")
        if exc.status_code is not None and 400 <= exc.status_code < 500:
            await record_renewal_decline(
                db,
                subscription=subscription,
                operation=operation,
                invoice=invoice,
                now=current,
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
    except (httpx.HTTPError, YooKassaConfigurationError, OSError):
        if not dispatched:
            return await cancel_before_dispatch("provider_unavailable")
        completed = await refresh_after_dispatch()
        if completed is not None:
            return completed
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
        completed = await refresh_after_dispatch()
        if completed is not None:
            return completed
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
