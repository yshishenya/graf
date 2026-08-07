import inspect
from pathlib import Path
from types import SimpleNamespace
from uuid import uuid4

import pytest
from starlette.requests import Request

from twobrain_rec_server.api.billing import SUPPORTED_PROVIDER_EVENTS, _handle_billing_webhook
from twobrain_rec_server.billing.provider_events import (
    ProviderEventError,
    WebhookInbox,
    parse_provider_event,
)
from twobrain_rec_server.billing.yookassa import YooKassaClient
from twobrain_rec_server.config import Settings


def _payload(event_id: str, *, created_at: str = "2026-08-06T09:00:00Z") -> dict[str, object]:
    return {
        "id": event_id,
        "event": "payment.succeeded",
        "object": {"id": "pay-1", "created_at": created_at, "amount": {"value": "79.00"}},
    }


def test_webhook_inbox_is_idempotent_and_detects_conflicting_replay() -> None:
    inbox = WebhookInbox()
    first = parse_provider_event(_payload("evt-1"))
    assert inbox.accept(first) == "accepted"
    assert inbox.accept(first) == "duplicate"
    extra_amount_metadata = parse_provider_event(
        {
            **_payload("evt-1"),
            "object": {**_payload("evt-1")["object"], "amount": {"value": "79.00", "secret": "must-not-hash"}},
        }
    )
    assert extra_amount_metadata.payload_hash == first.payload_hash
    conflict = parse_provider_event({**_payload("evt-1"), "event": "payment.canceled"})
    assert inbox.accept(conflict) == "replay_conflict"
    amount_conflict = parse_provider_event(
        {**_payload("evt-1"), "object": {**_payload("evt-1")["object"], "amount": {"value": "80.00"}}}
    )
    assert inbox.accept(amount_conflict) == "replay_conflict"


def test_webhook_parser_accepts_out_of_order_timestamps_but_rejects_malformed() -> None:
    older = parse_provider_event(_payload("evt-old", created_at="2026-08-05T09:00:00Z"))
    newer = parse_provider_event(_payload("evt-new"))
    assert older.occurred_at < newer.occurred_at
    with pytest.raises(ProviderEventError):
        parse_provider_event({"id": "evt-bad", "event": "payment.succeeded", "object": {}})


def test_webhook_reconciliation_has_authoritative_get_and_list_fallbacks() -> None:
    assert hasattr(YooKassaClient, "get_payment")
    assert hasattr(YooKassaClient, "list_refunds")
    assert hasattr(YooKassaClient, "get_receipt")


def test_webhook_parser_binds_workspace_only_from_provider_metadata() -> None:
    workspace_id = uuid4()
    event = parse_provider_event(
        {
            **_payload("evt-workspace"),
            "object": {
                **_payload("evt-workspace")["object"],
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
async def test_provider_webhook_without_proxy_secret_fails_closed(tmp_path: Path) -> None:
    secret = tmp_path / "webhook-secret"
    secret.write_text("expected-secret", encoding="utf-8")
    app = SimpleNamespace(
        state=SimpleNamespace(
            settings=Settings(
                billing_yookassa_base_url="https://api.yookassa.test",
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
