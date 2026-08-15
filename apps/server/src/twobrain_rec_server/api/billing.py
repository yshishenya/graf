from __future__ import annotations

import json

from fastapi import APIRouter, Header, Request
from fastapi.responses import JSONResponse
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from twobrain_rec_server.billing.launch_gates import provider_environment
from twobrain_rec_server.billing.provider_events import (
    ProviderEventError,
    WebhookInbox,
    parse_provider_event,
    redacted_event_metadata,
    validate_webhook_secret,
)
from twobrain_rec_server.billing.yookassa import YooKassaConfigurationError, read_webhook_secret
from twobrain_rec_server.db.models import BillingWebhookEvent, Workspace
from twobrain_rec_server.db.tenant_context import WorkspaceAuthContext, apply_tenant_context

router = APIRouter(prefix="/api/v1/billing", tags=["billing"])

SUPPORTED_PROVIDER_EVENTS = frozenset(
    {
        "payment.succeeded",
        "payment.canceled",
        "payment.waiting_for_capture",
        "payment.pending",
        "refund.succeeded",
        "payment_method.active",
        "receipt.succeeded",
        "receipt.waiting_for_cancellation",
    }
)
MAX_BILLING_WEBHOOK_BYTES = 256 * 1024


def _is_json_content_type(value: object) -> bool:
    if not isinstance(value, str):
        return False
    media_type = value.split(";", 1)[0].strip().lower()
    return media_type == "application/json"


def _inbox(request: Request) -> WebhookInbox:
    inbox = getattr(request.app.state, "billing_webhook_inbox", None)
    if inbox is None:
        inbox = WebhookInbox()
        request.app.state.billing_webhook_inbox = inbox
    return inbox


async def _read_bounded_webhook_body(request: Request) -> bytes:
    """Read chunked requests without buffering an attacker-controlled body."""
    chunks: list[bytes] = []
    size = 0
    async for chunk in request.stream():
        size += len(chunk)
        if size > MAX_BILLING_WEBHOOK_BYTES:
            raise ProviderEventError("provider event is too large")
        chunks.append(chunk)
    return b"".join(chunks)


@router.post("/webhook", status_code=200, include_in_schema=False)
async def billing_webhook(
    request: Request,
    x_billing_webhook_secret: str | None = Header(default=None, alias="X-Billing-Webhook-Secret"),
) -> JSONResponse:
    """Backward-compatible webhook path; new provider config uses explicit environment."""
    return await _handle_billing_webhook(request, x_billing_webhook_secret, environment=None)


@router.post("/providers/yookassa/webhook/{environment}", status_code=200, include_in_schema=False)
async def billing_provider_webhook(
    environment: str,
    request: Request,
    x_billing_webhook_secret: str | None = Header(default=None, alias="X-Billing-Webhook-Secret"),
) -> JSONResponse:
    return await _handle_billing_webhook(request, x_billing_webhook_secret, environment=environment)


async def _handle_billing_webhook(
    request: Request,
    x_billing_webhook_secret: str | None,
    *,
    environment: str | None,
) -> JSONResponse:
    settings = request.app.state.settings
    try:
        configured_environment = provider_environment(settings.billing_yookassa_environment)
        if environment is not None and environment not in {"test", "production"}:
            raise ProviderEventError("provider environment is invalid")
        if environment is not None and environment != configured_environment:
            raise ProviderEventError("provider environment does not match configured shop")
        # The reverse proxy must inject this secret only after validating the
        # YooKassa source network and TLS. The app itself stays fail-closed;
        # reconciliation GETs are an additional authenticity check, not an
        # authorization boundary.
        secret = read_webhook_secret(settings.billing_yookassa_webhook_secret_file)
        validate_webhook_secret(supplied=x_billing_webhook_secret, expected=secret)
        if not _is_json_content_type(request.headers.get("content-type")):
            raise ProviderEventError("provider event content type is invalid")
        content_length = request.headers.get("content-length")
        if content_length is not None:
            try:
                if int(content_length) < 0 or int(content_length) > MAX_BILLING_WEBHOOK_BYTES:
                    raise ProviderEventError("provider event is too large")
            except ValueError as exc:
                raise ProviderEventError("provider content length is invalid") from exc
        body = await _read_bounded_webhook_body(request)
        payload = json.loads(body)
        if not isinstance(payload, dict):
            raise ProviderEventError("provider event must be an object")
        event = parse_provider_event(payload)
        if event.event_type not in SUPPORTED_PROVIDER_EVENTS:
            raise ProviderEventError("unsupported provider event")
    except (ProviderEventError, YooKassaConfigurationError, ValueError):
        return JSONResponse(status_code=401, content={"status": "rejected"})

    if event.workspace_id is None:
        # A provider event without our immutable workspace metadata cannot be
        # safely attached to a tenant. Return a retryable response rather than
        # acknowledging an event that would otherwise be lost.
        return JSONResponse(status_code=503, content={"status": "deferred_without_workspace"})
    if event.workspace_id == settings.web_login_workspace_id:
        return JSONResponse(status_code=200, content={"status": "ignored_workspace_scope"})

    sessionmaker = getattr(request.app.state, "db_sessionmaker", None)
    if sessionmaker is None:
        return JSONResponse(status_code=503, content={"status": "deferred_store_unavailable"})
    try:
        async with sessionmaker() as db:
            await apply_tenant_context(db, WorkspaceAuthContext(workspace_id=event.workspace_id))
            workspace = await db.get(Workspace, event.workspace_id)
            if workspace is None:
                return JSONResponse(
                    status_code=200,
                    content={"status": "ignored_workspace_scope"},
                )
            if workspace.kind != "personal" or workspace.owner_user_id is None:
                return JSONResponse(
                    status_code=200,
                    content={"status": "ignored_workspace_scope"},
                )
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
            if stored is not None and result in {"accepted", "duplicate"}:
                if stored.state not in {"reconciled", "reconciliation_gap"}:
                    stored.state = "pending_reconciliation"
                await db.commit()
            if result == "replay_conflict":
                return JSONResponse(status_code=409, content={"status": result})
    except (ValueError, IntegrityError):
        return JSONResponse(status_code=503, content={"status": "deferred_store_error"})
    request.app.state.billing_last_webhook_metadata = redacted_event_metadata(event)
    return JSONResponse(status_code=200, content={"status": result})
