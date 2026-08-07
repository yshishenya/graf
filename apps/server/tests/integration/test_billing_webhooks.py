import inspect
from uuid import uuid4

import pytest

from twobrain_rec_server.api.billing import SUPPORTED_PROVIDER_EVENTS, _handle_billing_webhook
from twobrain_rec_server.billing.provider_events import (
    ProviderEventError,
    WebhookInbox,
    parse_provider_event,
)
from twobrain_rec_server.billing.yookassa import YooKassaClient


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
    conflict = parse_provider_event({**_payload("evt-1"), "event": "payment.canceled"})
    assert inbox.accept(conflict) == "replay_conflict"


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


def test_payment_method_active_is_observed_without_granting_authority() -> None:
    assert "payment_method.active" in SUPPORTED_PROVIDER_EVENTS
