from __future__ import annotations

import httpx
from fastapi import APIRouter, Header, Request
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from twobrain_rec_server.billing.entitlements import grant_confirmed_payment
from twobrain_rec_server.billing.provider_events import (
    ProviderEventError,
    WebhookInbox,
    parse_provider_event,
    redacted_event_metadata,
    validate_webhook_secret,
)
from twobrain_rec_server.billing.reconciliation import (
    ProviderObservationError,
    ProviderScope,
    extract_payment_observation,
    extract_refund_observation,
    record_observed_refund,
    saved_bank_card_confirmed,
)
from twobrain_rec_server.billing.yookassa import (
    YooKassaClient,
    YooKassaConfigurationError,
    YooKassaProviderError,
    read_webhook_secret,
)
from twobrain_rec_server.db.models import BillingWebhookEvent
from twobrain_rec_server.db.tenant_context import WorkspaceAuthContext, apply_tenant_context

router = APIRouter(prefix="/api/v1/billing", tags=["billing"])

SUPPORTED_PROVIDER_EVENTS = frozenset(
    {
        "payment.succeeded",
        "payment.canceled",
        "payment.waiting_for_capture",
        "payment.pending",
        "refund.succeeded",
        "receipt.succeeded",
        "receipt.waiting_for_cancellation",
    }
)


def _inbox(request: Request) -> WebhookInbox:
    inbox = getattr(request.app.state, "billing_webhook_inbox", None)
    if inbox is None:
        inbox = WebhookInbox()
        request.app.state.billing_webhook_inbox = inbox
    return inbox


@router.post("/webhook", status_code=202, include_in_schema=False)
async def billing_webhook(
    request: Request,
    x_billing_webhook_secret: str | None = Header(default=None, alias="X-Billing-Webhook-Secret"),
) -> JSONResponse:
    settings = request.app.state.settings
    try:
        secret = read_webhook_secret(settings.billing_yookassa_webhook_secret_file)
        validate_webhook_secret(supplied=x_billing_webhook_secret, expected=secret)
        payload = await request.json()
        if not isinstance(payload, dict):
            raise ProviderEventError("provider event must be an object")
        event = parse_provider_event(payload)
        if event.event_type not in SUPPORTED_PROVIDER_EVENTS:
            raise ProviderEventError("unsupported provider event")
    except (ProviderEventError, YooKassaConfigurationError, ValueError):
        return JSONResponse(status_code=401, content={"status": "rejected"})

    if event.workspace_id is None:
        # A provider event without our immutable workspace metadata cannot be
        # safely attached to a tenant. Keep the response retryable and do not
        # create an unauditable cross-workspace record.
        return JSONResponse(status_code=202, content={"status": "deferred_without_workspace"})

    sessionmaker = getattr(request.app.state, "db_sessionmaker", None)
    if sessionmaker is None:
        return JSONResponse(status_code=503, content={"status": "deferred_store_unavailable"})
    reconcile_status: str | None = None
    try:
        async with sessionmaker() as db:
            await apply_tenant_context(db, WorkspaceAuthContext(workspace_id=event.workspace_id))
            existing = await db.scalar(
                select(BillingWebhookEvent).where(
                    BillingWebhookEvent.workspace_id == event.workspace_id,
                    BillingWebhookEvent.provider_event_id == event.event_id,
                )
            )
            stored = existing
            if existing is not None:
                result = "duplicate" if existing.payload_hash == event.payload_hash else "replay_conflict"
            else:
                stored = BillingWebhookEvent(
                    workspace_id=event.workspace_id,
                    provider_event_id=event.event_id,
                    event_type=event.event_type,
                    object_id=event.object_id,
                    occurred_at=event.occurred_at,
                    payload_hash=event.payload_hash,
                    metadata_json=redacted_event_metadata(event),
                )
                db.add(stored)
                try:
                    await db.commit()
                    result = "accepted"
                except IntegrityError:
                    await db.rollback()
                    stored = None
                    result = "duplicate"
            if stored is not None and result in {"accepted", "duplicate"} and event.event_type.startswith("payment."):
                stored.state = "pending_reconciliation"
                try:
                    async with YooKassaClient(settings) as provider:
                        provider_payload = await provider.get_payment(event.object_id)
                    scope = ProviderScope(
                        environment="test" if "test" in str(settings.billing_yookassa_base_url).lower() else "production",
                        shop_id=settings.billing_yookassa_shop_id,
                    )
                    observation = extract_payment_observation(provider_payload, scope=scope)
                    if observation.status == "succeeded":
                        reconcile_status = await grant_confirmed_payment(
                            db,
                            workspace_id=event.workspace_id,
                            provider_payment_id=observation.provider_payment_id,
                            amount_minor=observation.amount_minor,
                            currency=observation.currency,
                            paid_at=observation.provider_created_at,
                            recurring_method_confirmed=saved_bank_card_confirmed(provider_payload),
                        )
                    else:
                        reconcile_status = "observed"
                    stored.state = "reconciled" if reconcile_status in {"granted", "duplicate", "observed"} else "reconciliation_gap"
                    await db.commit()
                except (ProviderObservationError, YooKassaConfigurationError, YooKassaProviderError, ValueError, httpx.HTTPError):
                    await db.rollback()
                    reconcile_status = "pending_reconciliation"
            elif stored is not None and result in {"accepted", "duplicate"} and event.event_type == "refund.succeeded":
                stored.state = "pending_reconciliation"
                try:
                    async with YooKassaClient(settings) as provider:
                        refund_payload = await provider.list_refunds()
                    items = refund_payload.get("items", [])
                    if not isinstance(items, list):
                        items = []
                    candidate = next(
                        (item for item in items if isinstance(item, dict) and item.get("id") == event.object_id),
                        None,
                    )
                    if candidate is None:
                        raise ProviderObservationError("provider refund was not found in GET/list backstop")
                    scope = ProviderScope(
                        environment="test" if "test" in str(settings.billing_yookassa_base_url).lower() else "production",
                        shop_id=settings.billing_yookassa_shop_id,
                    )
                    observation = extract_refund_observation(candidate, scope=scope)
                    reconcile_status = await record_observed_refund(
                        db, workspace_id=event.workspace_id, observation=observation
                    )
                    stored.state = "reconciled" if reconcile_status in {"inserted", "duplicate"} else "reconciliation_gap"
                    await db.commit()
                except (ProviderObservationError, YooKassaConfigurationError, YooKassaProviderError, ValueError, httpx.HTTPError):
                    await db.rollback()
                    reconcile_status = "pending_reconciliation"
    except (ValueError, IntegrityError):
        return JSONResponse(status_code=503, content={"status": "deferred_store_error"})
    request.app.state.billing_last_webhook_metadata = redacted_event_metadata(event)
    return JSONResponse(status_code=202, content={"status": reconcile_status or result})
