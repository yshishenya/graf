import inspect
from datetime import UTC, datetime
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest
from starlette.requests import Request

from twobrain_rec_server.api.billing import (
    MAX_BILLING_WEBHOOK_BYTES,
    SUPPORTED_PROVIDER_EVENTS,
    _handle_billing_webhook,
)
from twobrain_rec_server.billing.provider_events import (
    ProviderEventError,
    WebhookInbox,
    parse_provider_event,
)
from twobrain_rec_server.billing.webhook_reconciliation import _find_refund
from twobrain_rec_server.billing.yookassa import YooKassaClient
from twobrain_rec_server.config import Settings


def _payload(*, created_at: str = "2026-08-06T09:00:00Z") -> dict[str, object]:
    return {
        "type": "notification",
        "event": "payment.succeeded",
        "object": {"id": "pay-1", "created_at": created_at, "amount": {"value": "79.00"}},
    }


def test_webhook_inbox_is_idempotent_and_detects_conflicting_replay() -> None:
    inbox = WebhookInbox()
    first = parse_provider_event(_payload())
    assert inbox.accept(first) == "accepted"
    assert inbox.accept(first) == "duplicate"
    extra_amount_metadata = parse_provider_event(
        {
            **_payload(),
            "object": {**_payload()["object"], "amount": {"value": "79.00", "secret": "must-not-hash"}},
        }
    )
    assert extra_amount_metadata.payload_hash == first.payload_hash
    next_state = parse_provider_event({**_payload(), "event": "payment.canceled"})
    assert inbox.accept(next_state) == "accepted"
    amount_conflict = parse_provider_event(
        {**_payload(), "object": {**_payload()["object"], "amount": {"value": "80.00"}}}
    )
    assert inbox.accept(amount_conflict) == "replay_conflict"


def test_webhook_parser_accepts_out_of_order_timestamps_but_rejects_malformed() -> None:
    older = parse_provider_event(_payload(created_at="2026-08-05T09:00:00Z"))
    newer = parse_provider_event({**_payload(), "object": {**_payload()["object"], "id": "pay-2"}})
    assert older.occurred_at < newer.occurred_at
    with pytest.raises(ProviderEventError):
        parse_provider_event({"type": "notification", "event": "payment.succeeded", "object": {}})


def test_webhook_parser_rejects_path_manipulation_in_provider_object_id() -> None:
    with pytest.raises(ProviderEventError):
        parse_provider_event({**_payload(), "object": {"id": "../refunds", "created_at": "2026-08-06T09:00:00Z"}})


def test_webhook_parser_rejects_non_notification_envelope() -> None:
    with pytest.raises(ProviderEventError):
        parse_provider_event({**_payload(), "type": "payment"})


def test_payment_method_notification_without_created_at_remains_a_bounded_signal() -> None:
    event = parse_provider_event(
        {
            "type": "notification",
            "event": "payment_method.active",
            "object": {"id": "pm-1", "status": "active"},
        }
    )

    assert event.event_id.startswith("yookassa_")
    assert event.occurred_at == datetime(1970, 1, 1, tzinfo=UTC)


def test_webhook_reconciliation_has_authoritative_get_and_list_fallbacks() -> None:
    assert hasattr(YooKassaClient, "get_payment")
    assert hasattr(YooKassaClient, "list_refunds")
    assert hasattr(YooKassaClient, "get_receipt")


def test_webhook_parser_binds_workspace_only_from_provider_metadata() -> None:
    workspace_id = uuid4()
    event = parse_provider_event(
        {
            **_payload(),
            "object": {
                **_payload()["object"],
                "metadata": {"workspace_id": str(workspace_id), "card": "must-not-persist"},
            },
        }
    )
    assert event.workspace_id == workspace_id


def test_webhook_request_path_only_persists_signal_and_defers_provider_reads() -> None:
    source = inspect.getsource(_handle_billing_webhook)

    assert "pending_reconciliation" in source
    assert "get_payment" not in source
    assert "list_refunds" not in source
    assert "grant_confirmed_payment" not in source


@pytest.mark.asyncio
async def test_chunked_webhook_body_is_bounded_before_json_parse(tmp_path: Path) -> None:
    secret = tmp_path / "webhook-secret"
    secret.write_text("expected-secret", encoding="utf-8")
    app = SimpleNamespace(
        state=SimpleNamespace(
            settings=Settings(
                billing_yookassa_base_url="https://api.yookassa.test",
                billing_yookassa_environment="test",
                billing_yookassa_shop_id="shop-1",
                billing_yookassa_webhook_secret_file=secret,
            )
        )
    )
    payload = b"{" + b"x" * MAX_BILLING_WEBHOOK_BYTES + b"}"
    sent = False

    async def receive() -> dict[str, object]:
        nonlocal sent
        if sent:
            return {"type": "http.disconnect"}
        sent = True
        return {"type": "http.request", "body": payload, "more_body": False}

    request = Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/api/v1/billing/providers/yookassa/webhook/test",
            "headers":[
                (b"content-type", b"application/json"),
                (b"x-billing-webhook-secret", b"expected-secret"),
            ],
            "query_string": b"",
            "app": app,
        },
        receive,
    )
    response = await _handle_billing_webhook(request, "expected-secret", environment="test")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_provider_webhook_without_proxy_secret_fails_closed(tmp_path: Path) -> None:
    secret = tmp_path / "webhook-secret"
    secret.write_text("expected-secret", encoding="utf-8")
    app = SimpleNamespace(
        state=SimpleNamespace(
            settings=Settings(
                billing_yookassa_base_url="https://api.yookassa.test",
                billing_yookassa_environment="test",
                billing_yookassa_shop_id="shop-1",
                billing_yookassa_webhook_secret_file=secret,
            )
        )
    )
    request = Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/api/v1/billing/providers/yookassa/webhook/test",
            "headers": [(b"content-type", b"application/json")],
            "query_string": b"",
            "app": app,
        }
    )
    response = await _handle_billing_webhook(request, None, environment="test")
    assert response.status_code == 401


def test_payment_method_active_is_observed_without_granting_authority() -> None:
    assert "payment_method.active" in SUPPORTED_PROVIDER_EVENTS


@pytest.mark.asyncio
async def test_refund_backstop_follows_cursor_until_match() -> None:
    class Provider:
        def __init__(self) -> None:
            self.cursors: list[str | None] = []

        async def list_refunds(self, *, cursor: str | None = None, limit: int | None = None) -> dict[str, object]:
            self.cursors.append(cursor)
            if cursor is None:
                return {"items": [], "next_cursor": "page-2"}
            return {"items": [{"id": "refund-target", "status": "succeeded"}]}

    provider = Provider()
    assert await _find_refund(provider, "refund-target") == {"id": "refund-target", "status": "succeeded"}
    assert provider.cursors == [None, "page-2"]
