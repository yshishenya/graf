from __future__ import annotations

from fastapi import APIRouter, Header, Request
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from twobrain_rec_server.billing.provider_events import (
    ProviderEventError,
    WebhookInbox,
    parse_provider_event,
    redacted_event_metadata,
    validate_webhook_secret,
)
from twobrain_rec_server.billing.yookassa import YooKassaConfigurationError, read_webhook_secret
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
    try:
        async with sessionmaker() as db:
            await apply_tenant_context(db, WorkspaceAuthContext(workspace_id=event.workspace_id))
            existing = await db.scalar(
                select(BillingWebhookEvent).where(
                    BillingWebhookEvent.workspace_id == event.workspace_id,
                    BillingWebhookEvent.provider_event_id == event.event_id,
                )
            )
            if existing is not None:
                result = "duplicate" if existing.payload_hash == event.payload_hash else "replay_conflict"
            else:
                db.add(
                    BillingWebhookEvent(
                        workspace_id=event.workspace_id,
                        provider_event_id=event.event_id,
                        event_type=event.event_type,
                        object_id=event.object_id,
                        occurred_at=event.occurred_at,
                        payload_hash=event.payload_hash,
                        metadata_json=redacted_event_metadata(event),
                    )
                )
                try:
                    await db.commit()
                    result = "accepted"
                except IntegrityError:
                    await db.rollback()
                    result = "duplicate"
    except (ValueError, IntegrityError):
        return JSONResponse(status_code=503, content={"status": "deferred_store_error"})
    request.app.state.billing_last_webhook_metadata = redacted_event_metadata(event)
    return JSONResponse(status_code=202, content={"status": result})
