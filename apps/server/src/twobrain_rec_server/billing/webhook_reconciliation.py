"""Durable provider reconciliation for accepted YooKassa webhook signals."""

from __future__ import annotations

from typing import TYPE_CHECKING

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from twobrain_rec_server.billing.entitlements import (
    grant_confirmed_payment,
    grant_confirmed_renewal,
)
from twobrain_rec_server.billing.events import enqueue_billing_notification
from twobrain_rec_server.billing.notifications import BillingNotification
from twobrain_rec_server.billing.payment_methods import (
    extract_saved_bank_card,
    read_billing_encryption_key,
)
from twobrain_rec_server.billing.promotions import release_payment_promo
from twobrain_rec_server.billing.provider_events import (
    ProviderEventError,
)
from twobrain_rec_server.billing.reconciliation import (
    ProviderObservationError,
    ProviderScope,
    extract_payment_observation,
    extract_receipt_observation,
    extract_refund_observation,
    record_observed_receipt,
    record_observed_refund,
    saved_bank_card_confirmed,
)
from twobrain_rec_server.billing.yookassa import (
    YooKassaClient,
    YooKassaConfigurationError,
    YooKassaProviderError,
)
from twobrain_rec_server.db.models import (
    BillingInvoice,
    BillingOperation,
    BillingWebhookEvent,
    WorkspaceMembership,
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
) -> dict[str, int]:
    """Poll persisted initial payments when the webhook was lost.

    This is observation-only and requires a provider id already persisted by
    the hosted checkout path; a POST timeout before that id remains a manual
    reconciliation gap until the provider can be searched by metadata.
    """
    if not settings.billing_checkout_enabled:
        return {"processed": 0, "succeeded": 0, "canceled": 0, "pending": 0, "failed": 0}
    filters = [
        BillingOperation.kind == "initial_checkout",
        BillingOperation.provider_id.is_not(None),
        BillingOperation.state.in_(("provider_pending", "unknown")),
    ]
    if operation_id is not None:
        filters.append(BillingOperation.id == operation_id)
    operations = tuple(
        await db.scalars(
            select(BillingOperation)
            .where(*filters)
            .order_by(BillingOperation.updated_at, BillingOperation.id)
            .limit(max(1, min(limit, 500)))
            .with_for_update()
        )
    )
    counters = {"processed": 0, "succeeded": 0, "canceled": 0, "pending": 0, "failed": 0}
    try:
        async with YooKassaClient(settings) as provider:
            environment = "test" if "test" in str(settings.billing_yookassa_base_url).lower() else "production"
            scope = ProviderScope(environment=environment, shop_id=settings.billing_yookassa_shop_id)
            for operation in operations:
                counters["processed"] += 1
                try:
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
                            payment_method_key=read_billing_encryption_key(settings.credential_encryption_key_file),
                            receipt_registration=observation.receipt_registration,
                        )
                        if grant_result in {"granted", "duplicate"}:
                            counters["succeeded"] += 1
                        else:
                            counters["failed"] += 1
                    elif observation.status == "canceled":
                        await release_payment_promo(
                            db,
                            workspace_id=operation.workspace_id,
                            provider_payment_id=observation.provider_payment_id,
                            now=observation.provider_created_at,
                        )
                        operation.state = "canceled"
                        invoice = await db.scalar(
                            select(BillingInvoice).where(BillingInvoice.operation_id == operation.id).with_for_update()
                        )
                        if invoice is not None:
                            invoice.status = "canceled"
                        counters["canceled"] += 1
                    else:
                        counters["pending"] += 1
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
        counters["failed"] += len(operations)
    return counters


async def reconcile_pending_webhook_events(
    db: AsyncSession,
    settings: Settings,
    *,
    limit: int = 100,
) -> dict[str, int]:
    """Read provider truth outside the webhook request and commit per event."""

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
                        if result in {"granted", "duplicate", "refused", "observed", "inserted", "receipt_observed"}
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


async def _reconcile_event(
    db: AsyncSession,
    settings: Settings,
    provider: YooKassaClient,
    event: BillingWebhookEvent,
) -> str:
    environment = "test" if "test" in str(settings.billing_yookassa_base_url).lower() else "production"
    scope = ProviderScope(environment=environment, shop_id=settings.billing_yookassa_shop_id)
    if event.event_type.startswith("payment."):
        payload = await provider.get_payment(event.object_id)
        observation = extract_payment_observation(payload, scope=scope)
        if observation.status == "succeeded":
            operation = await db.scalar(
                select(BillingOperation)
                .where(
                    BillingOperation.workspace_id == event.workspace_id,
                    BillingOperation.provider_id == observation.provider_payment_id,
                )
                .with_for_update()
            )
            if operation is not None and operation.kind == "renewal":
                result = await grant_confirmed_renewal(
                    db,
                    workspace_id=event.workspace_id,
                    provider_payment_id=observation.provider_payment_id,
                    amount_minor=observation.amount_minor,
                    currency=observation.currency,
                    grant_starts_at=observation.provider_created_at,
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
                payment_method_key=read_billing_encryption_key(settings.credential_encryption_key_file),
                receipt_registration=observation.receipt_registration,
            )
        if observation.status == "canceled":
            await release_payment_promo(
                db,
                workspace_id=event.workspace_id,
                provider_payment_id=observation.provider_payment_id,
                now=observation.provider_created_at,
            )
        return "observed"
    if event.event_type == "refund.succeeded":
        candidate = await _find_refund(provider, event.object_id)
        if candidate is None:
            raise ProviderObservationError("provider refund was not found in GET/list backstop")
        observation = extract_refund_observation(candidate, scope=scope)
        return await record_observed_refund(db, workspace_id=event.workspace_id, observation=observation)
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
            raise ProviderObservationError("provider receipt observation conflicts with stored truth")
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
