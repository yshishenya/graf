"""Durable provider reconciliation for accepted YooKassa webhook signals."""

from __future__ import annotations

from contextlib import AsyncExitStack
from datetime import UTC, datetime
from hashlib import sha256
from typing import TYPE_CHECKING
from uuid import UUID

import httpx
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from twobrain_rec_server.billing.entitlements import (
    grant_confirmed_payment,
    grant_confirmed_renewal,
)
from twobrain_rec_server.billing.events import enqueue_billing_notification
from twobrain_rec_server.billing.notifications import BillingNotification
from twobrain_rec_server.billing.operations import INITIAL_CHECKOUT_OBSERVATION_EXPIRED
from twobrain_rec_server.billing.payment_methods import (
    extract_payment_method_label,
    extract_saved_bank_card,
    read_billing_encryption_key,
)
from twobrain_rec_server.billing.promotions import release_payment_promo
from twobrain_rec_server.billing.provider_events import ProviderEventError
from twobrain_rec_server.billing.reconciliation import (
    PaymentObservation,
    ProviderObservationError,
    ProviderScope,
    extract_payment_observation,
    extract_receipt_observation,
    extract_refund_observation,
    record_observed_receipt,
    record_observed_refund,
    saved_bank_card_confirmed,
    validate_renewal_payment,
)
from twobrain_rec_server.billing.renewal_charge import record_renewal_decline
from twobrain_rec_server.billing.storage import lock_storage_workspace
from twobrain_rec_server.billing.yookassa import (
    YooKassaClient,
    YooKassaConfigurationError,
    YooKassaProviderError,
    provider_environment,
)
from twobrain_rec_server.db.models import (
    BillingInvoice,
    BillingOperation,
    BillingWebhookEvent,
    Workspace,
    WorkspaceMembership,
    WorkspaceSubscription,
)

if TYPE_CHECKING:
    from twobrain_rec_server.config import Settings


RECONCILABLE_WEBHOOK_STATES = frozenset(("accepted", "pending_reconciliation"))
MAX_REFUND_LIST_PAGES = 20


async def reconcile_pending_initial_checkout_operations(
    db: AsyncSession,
    settings: Settings,
    *,
    limit: int = 100,
    operation_id: object | None = None,
    defer_referral_reward: bool = False,
    commit_each_operation: bool = False,
) -> dict[str, int]:
    """Poll persisted initial payments when the webhook was lost.

    This is observation-only and requires a provider id already persisted by
    the hosted checkout path; a POST timeout before that id remains a manual
    reconciliation gap until the provider can be searched by metadata. The
    maintenance worker enables ``commit_each_operation`` so one provider
    observation cannot retain locks for the rest of the batch.
    """
    if not (settings.billing_provider_observation_enabled or settings.billing_checkout_enabled):
        return {"processed": 0, "succeeded": 0, "canceled": 0, "pending": 0, "failed": 0}
    observation_states = ("provider_pending", "unknown")
    # The worker's unscoped pass is bounded to the live observation window. A
    # terminal observation-expired row may be queried only by an explicit user
    # refresh or webhook-linked operation id; otherwise the worker would poll
    # the same provider forever after the deadline.
    if operation_id is not None:
        observation_states = (*observation_states, INITIAL_CHECKOUT_OBSERVATION_EXPIRED)
    filters = [
        BillingOperation.kind == "initial_checkout",
        BillingOperation.provider_id.is_not(None),
        BillingOperation.state.in_(observation_states),
    ]
    if operation_id is not None:
        filters.append(BillingOperation.id == operation_id)
    operations = tuple(
        await db.scalars(
            select(BillingOperation)
            .where(*filters)
            .order_by(BillingOperation.updated_at, BillingOperation.id)
            .limit(max(1, min(limit, 500)))
        )
    )
    counters = {"processed": 0, "succeeded": 0, "canceled": 0, "pending": 0, "failed": 0}
    valid_operations: list[BillingOperation] = []

    async def reconcile_operation(operation: BillingOperation, provider: YooKassaClient, scope: ProviderScope) -> str:
        payload = await provider.get_payment(operation.provider_id or "")
        observation = extract_payment_observation(payload, scope=scope)
        if observation.status == "succeeded":
            grant_result = await grant_confirmed_payment(
                db,
                workspace_id=operation.workspace_id,
                provider_payment_id=observation.provider_payment_id,
                amount_minor=observation.amount_minor,
                currency=observation.currency,
                paid_at=observation.provider_created_at,
                recurring_method_confirmed=saved_bank_card_confirmed(payload),
                saved_payment_method=extract_saved_bank_card(payload),
                payment_method_label=extract_payment_method_label(payload),
                payment_method_key=read_billing_encryption_key(
                    settings.credential_encryption_key_file
                ),
                receipt_registration=observation.receipt_registration,
                defer_referral_reward=defer_referral_reward,
            )
            if grant_result in {"granted", "duplicate"}:
                if defer_referral_reward:
                    await _enqueue_deferred_referral_reconciliation(
                        db,
                        operation=operation,
                        observation=observation,
                    )
                return "succeeded"
            return "failed"
        if observation.status == "canceled":
            await release_payment_promo(
                db,
                workspace_id=operation.workspace_id,
                provider_payment_id=observation.provider_payment_id,
                now=observation.provider_created_at,
            )
            operation.state = "canceled"
            invoice = await db.scalar(
                select(BillingInvoice)
                .where(BillingInvoice.operation_id == operation.id)
                .with_for_update()
            )
            if invoice is not None:
                invoice.status = "canceled"
            return "canceled"
        return "pending"

    provider: YooKassaClient | None = None
    scope: ProviderScope | None = None
    try:
        async with AsyncExitStack() as provider_stack:
            for candidate in operations:
                counters["processed"] += 1
                # Webhooks lock the workspace before the operation. Keep this scan
                # unlocked and acquire the operation row only after the same advisory
                # lock to preserve one lock order for both paths.
                await lock_storage_workspace(db, candidate.workspace_id)
                operation = await db.scalar(
                    select(BillingOperation)
                    .where(
                        BillingOperation.id == candidate.id,
                        BillingOperation.workspace_id == candidate.workspace_id,
                        BillingOperation.kind == "initial_checkout",
                        BillingOperation.provider_id.is_not(None),
                        BillingOperation.state.in_(observation_states),
                    )
                    .with_for_update()
                )
                if operation is None:
                    if commit_each_operation:
                        await db.commit()
                    continue
                workspace = await db.scalar(
                    select(Workspace)
                    .join(
                        WorkspaceMembership,
                        (WorkspaceMembership.workspace_id == Workspace.id)
                        & (WorkspaceMembership.user_id == Workspace.owner_user_id),
                    )
                    .where(
                        Workspace.id == operation.workspace_id,
                        Workspace.kind == "personal",
                        WorkspaceMembership.role == "owner",
                        WorkspaceMembership.status == "active",
                    )
                    .with_for_update()
                )
                if workspace is not None:
                    if provider is None:
                        environment = provider_environment(settings.billing_yookassa_environment)
                        scope = ProviderScope(
                            environment=environment, shop_id=settings.billing_yookassa_shop_id
                        )
                        provider = await provider_stack.enter_async_context(
                            YooKassaClient(settings)
                        )
                    if commit_each_operation:
                        try:
                            assert provider is not None and scope is not None
                            outcome = await reconcile_operation(operation, provider, scope)
                            counters[outcome] += 1
                        except (
                            ProviderEventError,
                            ProviderObservationError,
                            YooKassaConfigurationError,
                            YooKassaProviderError,
                            ValueError,
                            httpx.HTTPError,
                        ):
                            await db.rollback()
                            counters["failed"] += 1
                        else:
                            await db.commit()
                    else:
                        valid_operations.append(operation)
                    continue
                operation.state = "manual_resolution"
                invoice = await db.scalar(
                    select(BillingInvoice)
                    .where(BillingInvoice.operation_id == operation.id)
                    .with_for_update()
                )
                if invoice is not None:
                    invoice.status = "manual_resolution"
                counters["failed"] += 1
                if commit_each_operation:
                    await db.commit()
            if not valid_operations:
                return counters
            assert provider is not None and scope is not None
            for operation in valid_operations:
                try:
                    counters[await reconcile_operation(operation, provider, scope)] += 1
                except (
                    ProviderEventError,
                    ProviderObservationError,
                    YooKassaConfigurationError,
                    YooKassaProviderError,
                    ValueError,
                    httpx.HTTPError,
                ):
                    counters["failed"] += 1
    except (YooKassaConfigurationError, ValueError):
        if commit_each_operation:
            await db.rollback()
        counters["failed"] += len(valid_operations) or 1
    return counters


async def _enqueue_deferred_referral_reconciliation(
    db: AsyncSession,
    *,
    operation: BillingOperation,
    observation: object,
) -> None:
    """Persist a maintenance-owned retry for cross-workspace referral credit.

    Browser status refresh runs in the payer workspace context. The entitlement
    grant is safe there, but the inviter's ledger is intentionally writable only
    by maintenance. A deterministic inbox row keeps that reward eventual and
    idempotent without widening request RLS.
    """
    provider_payment_id = str(getattr(observation, "provider_payment_id", ""))
    occurred_at = getattr(observation, "provider_created_at", None)
    if not provider_payment_id or occurred_at is None:
        return
    provider_event_id = f"status_refresh_{sha256(provider_payment_id.encode()).hexdigest()}"
    payload_hash = sha256(
        f"payment.succeeded:{provider_payment_id}:{occurred_at.isoformat()}".encode()
    ).hexdigest()
    existing = await db.scalar(
        select(BillingWebhookEvent).where(
            BillingWebhookEvent.workspace_id == operation.workspace_id,
            BillingWebhookEvent.provider_event_id == provider_event_id,
        )
    )
    if existing is not None:
        return
    try:
        async with db.begin_nested():
            db.add(
                BillingWebhookEvent(
                    workspace_id=operation.workspace_id,
                    provider_event_id=provider_event_id,
                    event_type="payment.succeeded",
                    object_id=provider_payment_id,
                    occurred_at=occurred_at,
                    payload_hash=payload_hash,
                    state="pending_reconciliation",
                    metadata_json={"source": "status_refresh", "referral_reward_deferred": True},
                )
            )
            await db.flush()
    except IntegrityError:
        # Another serialized status refresh already enqueued this deterministic
        # event; the confirmed entitlement remains committed.
        return


async def reconcile_pending_webhook_events(
    db: AsyncSession,
    settings: Settings,
    *,
    limit: int = 100,
) -> dict[str, int]:
    """Read provider truth outside the webhook request and commit per event."""

    if not (settings.billing_provider_observation_enabled or settings.billing_checkout_enabled):
        return {"processed": 0, "reconciled": 0, "pending": 0, "failed": 0}

    ids = tuple(
        await db.scalars(
            select(BillingWebhookEvent.id)
            .where(BillingWebhookEvent.state.in_(RECONCILABLE_WEBHOOK_STATES))
            .order_by(BillingWebhookEvent.received_at, BillingWebhookEvent.id)
            .limit(max(1, min(limit, 500)))
        )
    )
    counters = {"processed": 0, "reconciled": 0, "pending": 0, "failed": 0}
    try:
        async with YooKassaClient(settings) as provider:
            for event_id in ids:
                event = await db.scalar(
                    select(BillingWebhookEvent)
                    .where(BillingWebhookEvent.id == event_id)
                    .with_for_update()
                )
                if event is None or event.state not in RECONCILABLE_WEBHOOK_STATES:
                    continue
                counters["processed"] += 1
                try:
                    result = await _reconcile_event(db, settings, provider, event)
                    event.state = (
                        "reconciled"
                        if result
                        in {
                            "granted",
                            "duplicate",
                            "refused",
                            "observed",
                            "inserted",
                            "receipt_observed",
                        }
                        else "reconciliation_gap"
                    )
                    event.metadata_json = {
                        **(event.metadata_json or {}),
                        "reconciliation": result,
                    }
                    await db.commit()
                    counters["reconciled"] += 1
                except (
                    ProviderEventError,
                    ProviderObservationError,
                    YooKassaConfigurationError,
                    YooKassaProviderError,
                    ValueError,
                    httpx.HTTPError,
                ):
                    await db.rollback()
                    counters["pending"] += 1
    except (YooKassaConfigurationError, ValueError):
        counters["failed"] += len(ids)
    return counters


async def _locked_operation(
    db: AsyncSession,
    *,
    workspace_id: UUID,
    observation: PaymentObservation,
) -> BillingOperation | None:
    """Return the operation a provider-confirmed payment belongs to.

    Matching is normally by provider id. When the create-payment response never
    reached us, provider_id was never stored, so the payment looks unmatched and
    both access and cleanup stall. The provider echoes our operation id in the
    payment metadata, so binding it here is what turns a lost response into a
    granted entitlement instead of a permanently stuck operation.
    """
    operation = await db.scalar(
        select(BillingOperation)
        .where(
            BillingOperation.workspace_id == workspace_id,
            BillingOperation.provider_id == observation.provider_payment_id,
        )
        .with_for_update()
    )
    if operation is not None or observation.operation_id is None:
        return operation
    candidate = await db.scalar(
        select(BillingOperation)
        .where(
            BillingOperation.id == observation.operation_id,
            BillingOperation.workspace_id == workspace_id,
            BillingOperation.provider_id.is_(None),
        )
        .with_for_update()
    )
    if candidate is None:
        return None
    candidate.provider_id = observation.provider_payment_id
    await db.flush()
    return candidate


async def _reconcile_event(
    db: AsyncSession,
    settings: Settings,
    provider: YooKassaClient,
    event: BillingWebhookEvent,
) -> str:
    workspace = await db.get(Workspace, event.workspace_id)
    owner = None
    if (
        workspace is not None
        and workspace.kind == "personal"
        and workspace.owner_user_id is not None
    ):
        owner = await db.scalar(
            select(WorkspaceMembership).where(
                WorkspaceMembership.workspace_id == event.workspace_id,
                WorkspaceMembership.user_id == workspace.owner_user_id,
                WorkspaceMembership.role == "owner",
                WorkspaceMembership.status == "active",
            )
        )
    if owner is None:
        return "workspace_scope_invalid"
    environment = provider_environment(settings.billing_yookassa_environment)
    scope = ProviderScope(environment=environment, shop_id=settings.billing_yookassa_shop_id)
    if event.event_type.startswith("payment."):
        payload = await provider.get_payment(event.object_id)
        observation = extract_payment_observation(payload, scope=scope)
        if observation.status in {"succeeded", "canceled"}:
            # Same prefix as entitlement projection and renewal observation:
            # never acquire an operation before its workspace/subscription.
            await lock_storage_workspace(db, event.workspace_id)
            await db.scalar(
                select(Workspace).where(Workspace.id == event.workspace_id).with_for_update()
            )
            subscription = await db.scalar(
                select(WorkspaceSubscription)
                .where(WorkspaceSubscription.workspace_id == event.workspace_id)
                .with_for_update()
            )
        if observation.status == "succeeded":
            operation = await _locked_operation(
                db,
                workspace_id=event.workspace_id,
                observation=observation,
            )
            if operation is not None and operation.kind == "renewal":
                result = await grant_confirmed_renewal(
                    db,
                    workspace_id=event.workspace_id,
                    provider_payment_id=observation.provider_payment_id,
                    amount_minor=observation.amount_minor,
                    currency=observation.currency,
                    grant_starts_at=(
                        datetime.now(UTC)
                        if operation.state == "provider_key_expired"
                        else observation.provider_created_at
                    ),
                )
                if result not in {"granted", "duplicate", "refused"}:
                    raise ProviderObservationError("renewal entitlement projection failed")
                return result
            return await grant_confirmed_payment(
                db,
                workspace_id=event.workspace_id,
                provider_payment_id=observation.provider_payment_id,
                amount_minor=observation.amount_minor,
                currency=observation.currency,
                paid_at=observation.provider_created_at,
                recurring_method_confirmed=saved_bank_card_confirmed(payload),
                saved_payment_method=extract_saved_bank_card(payload),
                payment_method_label=extract_payment_method_label(payload),
                payment_method_key=read_billing_encryption_key(
                    settings.credential_encryption_key_file
                ),
                receipt_registration=observation.receipt_registration,
            )
        if observation.status == "canceled":
            operation = await _locked_operation(
                db,
                workspace_id=event.workspace_id,
                observation=observation,
            )
            if operation is not None and operation.kind == "renewal":
                invoice = await db.scalar(
                    select(BillingInvoice).where(
                        BillingInvoice.operation_id == operation.id,
                        BillingInvoice.workspace_id == event.workspace_id,
                    ).with_for_update()
                )
                if invoice is None or subscription is None:
                    raise ProviderObservationError("renewal decline projection is missing")
                if subscription.billing_owner_id != workspace.owner_user_id:
                    raise ProviderObservationError("renewal owner does not match")
                validate_renewal_payment(payload, operation=operation, invoice=invoice)
                await record_renewal_decline(
                    db, subscription=subscription, operation=operation, invoice=invoice,
                    now=datetime.now(UTC),
                )
                return "observed"
            await release_payment_promo(
                db,
                workspace_id=event.workspace_id,
                provider_payment_id=observation.provider_payment_id,
                now=observation.provider_created_at,
            )
            if operation is not None and operation.kind == "initial_checkout":
                operation.state = "canceled"
                invoice = await db.scalar(
                    select(BillingInvoice)
                    .where(BillingInvoice.operation_id == operation.id)
                    .with_for_update()
                )
                if invoice is not None:
                    invoice.status = "canceled"
        return "observed"
    if event.event_type == "refund.succeeded":
        candidate = await _find_refund(provider, event.object_id)
        if candidate is None:
            raise ProviderObservationError("provider refund was not found in GET/list backstop")
        observation = extract_refund_observation(candidate, scope=scope)
        return await record_observed_refund(
            db, workspace_id=event.workspace_id, observation=observation
        )
    if event.event_type == "payment_method.active":
        # The payment.succeeded authoritative GET remains the only path that
        # grants recurring authority. This provider signal is retained as a
        # safe observation until a verified zero-amount binding flow is enabled.
        return "observed"
    if event.event_type.startswith("receipt."):
        payload = await provider.get_receipt(event.object_id)
        observation = extract_receipt_observation(payload, scope=scope)
        result = await record_observed_receipt(
            db,
            workspace_id=event.workspace_id,
            observation=observation,
            source="webhook",
            observed_at=event.received_at,
        )
        if result == "unmatched":
            raise ProviderObservationError("provider receipt parent was not found")
        if result == "conflict":
            raise ProviderObservationError(
                "provider receipt observation conflicts with stored truth"
            )
        if observation.parent_kind == "payment" and result in {"inserted", "updated"}:
            operation = await db.scalar(
                select(BillingOperation).where(
                    BillingOperation.workspace_id == event.workspace_id,
                    BillingOperation.provider_id == observation.provider_parent_id,
                )
            )
            invoice = None
            if operation is not None:
                invoice = await db.scalar(
                    select(BillingInvoice).where(
                        BillingInvoice.workspace_id == event.workspace_id,
                        BillingInvoice.operation_id == operation.id,
                    )
                )
            if invoice is not None and observation.status == "succeeded":
                owner = await db.scalar(
                    select(WorkspaceMembership)
                    .where(
                        WorkspaceMembership.workspace_id == event.workspace_id,
                        WorkspaceMembership.role == "owner",
                        WorkspaceMembership.status == "active",
                    )
                    .order_by(WorkspaceMembership.user_id)
                )
                if owner is not None:
                    await enqueue_billing_notification(
                        db,
                        workspace_id=event.workspace_id,
                        recipient_id=owner.user_id,
                        event_id=f"receipt:{invoice.id}:available",
                        kind=BillingNotification.RECEIPT_AVAILABLE,
                        payload={
                            "invoice": invoice.safe_number,
                            "action_path": f"/billing/invoices/{invoice.safe_number}",
                        },
                        marketing_allowed=False,
                    )
        return "receipt_observed"
    raise ProviderEventError("unsupported provider event")


async def _find_refund(provider: YooKassaClient, refund_id: str) -> dict[str, object] | None:
    """Search a bounded number of provider pages without retaining raw payloads."""
    cursor: str | None = None
    seen_cursors: set[str] = set()
    for _ in range(MAX_REFUND_LIST_PAGES):
        payload = await provider.list_refunds(cursor=cursor, limit=100)
        items = payload.get("items", [])
        if not isinstance(items, list):
            raise ProviderObservationError("provider refund list is invalid")
        for item in items:
            if isinstance(item, dict) and item.get("id") == refund_id:
                return item
        next_cursor = payload.get("next_cursor")
        if next_cursor is None:
            return None
        if not isinstance(next_cursor, str) or not next_cursor or next_cursor in seen_cursors:
            raise ProviderObservationError("provider refund cursor is invalid")
        seen_cursors.add(next_cursor)
        cursor = next_cursor
    raise ProviderObservationError("provider refund pagination exceeded safety bound")
