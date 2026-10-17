from copy import deepcopy
from pathlib import Path
from uuid import uuid4

import httpx
import pytest

from twobrain_rec_server.billing import provider_scope
from twobrain_rec_server.billing.provider_events import parse_provider_event
from twobrain_rec_server.billing.provider_scope import resolve_child_scope
from twobrain_rec_server.billing.yookassa import YooKassaClient, YooKassaProviderError
from twobrain_rec_server.config import Settings


@pytest.fixture
def scope_case(tmp_path: Path, monkeypatch):
    secret = tmp_path / "synthetic-secret"
    secret.write_text("synthetic-secret")
    settings = Settings(
        billing_yookassa_base_url="https://api.yookassa.test",
        billing_yookassa_shop_id="shop-1",
        billing_yookassa_environment="test",
        billing_yookassa_secret_file=secret,
    )
    payment = {
        "id": "payment-1",
        "test": True,
        "paid": True,
        "status": "succeeded",
        "recipient": {"account_id": "shop-1"},
        "amount": {"value": "10.00", "currency": "RUB"},
        "created_at": "2026-10-17T07:46:30Z",
        "metadata": {"workspace_id": str(uuid4()), "operation_id": str(uuid4())},
    }
    refund = {
        "id": "refund-1",
        "payment_id": "payment-1",
        "status": "succeeded",
        "amount": {"value": "1.00", "currency": "RUB"},
        "created_at": "2026-10-17T07:46:30Z",
    }
    receipt = {
        "id": "receipt-1",
        "type": "refund",
        "refund_id": "refund-1",
        "payment_id": "payment-1",
        "status": "succeeded",
    }
    state = {"payment": payment, "refund": refund, "receipt": receipt, "calls": [], "status": 200}

    async def handle(request):
        import asyncio

        state["calls"].append((request.method, request.url.path))
        assert request.method == "GET"
        if state.get("delay"):
            await asyncio.sleep(state["delay"])
        if state.get("timeout"):
            raise httpx.ReadTimeout("synthetic timeout", request=request)
        kind = request.url.path.split("/")[-2][:-1]
        return httpx.Response(state["status"], json=deepcopy(state[kind]))

    original = YooKassaClient.__init__
    monkeypatch.setattr(
        YooKassaClient,
        "__init__",
        lambda self, settings: original(self, settings, transport=httpx.MockTransport(handle)),
    )
    return settings, state


def signal(kind, obj):
    return parse_provider_event(
        {"type": "notification", "event": f"{kind}.succeeded", "object": obj}
    )


@pytest.mark.asyncio
@pytest.mark.parametrize("kind", ["refund", "payment_receipt", "refund_receipt"])
async def test_child_scope_uses_exact_bounded_parent_chain_and_original_identity(scope_case, kind):
    settings, state = scope_case
    if kind == "payment_receipt":
        state["receipt"] = {
            "id": "receipt-1",
            "type": "payment",
            "payment_id": "payment-1",
            "status": "succeeded",
        }
    source = deepcopy(state["refund" if kind == "refund" else "receipt"])
    event = signal("refund" if kind == "refund" else "receipt", source)
    resolved, payment, scope = await resolve_child_scope(event, source, settings)
    assert resolved.workspace_id is not None
    assert str(resolved.workspace_id) == state["payment"]["metadata"]["workspace_id"]
    assert str(resolved.operation_id) == state["payment"]["metadata"]["operation_id"]
    assert (resolved.event_id, resolved.payload_hash, resolved.occurred_at, resolved.object_id) == (
        event.event_id,
        event.payload_hash,
        event.occurred_at,
        event.object_id,
    )
    expected = [] if kind == "refund" else [("GET", "/v3/receipts/receipt-1")]
    if kind != "payment_receipt":
        expected += [("GET", "/v3/refunds/refund-1")]
    assert state["calls"] == expected + [("GET", "/v3/payments/payment-1")]
    assert payment == state["payment"] and scope.shop_id == "shop-1"


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "fault",
    [
        "refund_id",
        "payment_id",
        "receipt_id",
        "receipt_parent",
        "receipt_payment_conflict",
        "shop",
        "missing_shop",
        "test",
        "missing_test",
        "string_test",
        "workspace_uuid",
        "operation_uuid",
        "child_workspace",
        "currency",
        "excess_amount",
        "incoming_parent",
        "operation_hint",
    ],
)
async def test_scope_rejects_conflicting_identity_without_mutation(scope_case, fault):
    settings, state = scope_case
    source = deepcopy(state["receipt"])
    if fault == "refund_id":
        state["refund"]["id"] = "other-refund"
    elif fault == "payment_id":
        state["payment"]["id"] = "other-payment"
    elif fault == "receipt_id":
        state["receipt"]["id"] = "other-receipt"
    elif fault == "receipt_parent":
        state["receipt"]["refund_id"] = "other-refund"
    elif fault == "receipt_payment_conflict":
        state["receipt"]["payment_id"] = "different-payment"
    elif fault == "shop":
        state["payment"]["recipient"]["account_id"] = "other-shop"
    elif fault == "missing_shop":
        state["payment"].pop("recipient")
    elif fault == "test":
        state["payment"]["test"] = False
    elif fault == "missing_test":
        state["payment"].pop("test")
    elif fault == "string_test":
        state["payment"]["test"] = "true"
    elif fault == "workspace_uuid":
        state["payment"]["metadata"]["workspace_id"] = "invalid"
    elif fault == "operation_uuid":
        state["payment"]["metadata"]["operation_id"] = "invalid"
    elif fault == "child_workspace":
        state["refund"]["metadata"] = {"workspace_id": str(uuid4())}
    elif fault == "currency":
        state["refund"]["amount"]["currency"] = "USD"
    elif fault == "excess_amount":
        state["refund"]["amount"]["value"] = "11.00"
    elif fault == "incoming_parent":
        source["refund_id"] = "foreign-refund"
    elif fault == "operation_hint":
        source["metadata"] = {"operation_id": str(uuid4())}
    event = signal("receipt", source)
    expected = (
        provider_scope.ProviderScopeUnavailable
        if fault
        in {"missing_shop", "missing_test", "string_test", "workspace_uuid", "operation_uuid"}
        else ValueError
    )
    with pytest.raises(expected):
        await resolve_child_scope(event, source, settings)
    assert len(state["calls"]) <= 3
    assert all(method == "GET" for method, _ in state["calls"])


@pytest.mark.asyncio
@pytest.mark.parametrize("status", [401, 403, 404, 429, 500, 503])
async def test_scope_upstream_failure_never_retries_or_lists(scope_case, status):
    settings, state = scope_case
    state["status"] = status
    with pytest.raises(YooKassaProviderError):
        await resolve_child_scope(signal("refund", state["refund"]), state["refund"], settings)
    assert state["calls"] == [("GET", "/v3/refunds/refund-1")]


@pytest.mark.asyncio
async def test_scope_has_one_deadline_for_whole_chain(scope_case, monkeypatch):
    settings, state = scope_case
    assert provider_scope.SCOPE_RESOLUTION_TIMEOUT_SECONDS == 8
    # Each individual request fits; the cumulative chain must still time out.
    monkeypatch.setattr(provider_scope, "SCOPE_RESOLUTION_TIMEOUT_SECONDS", 0.05)
    state["delay"] = 0.03
    with pytest.raises(TimeoutError):
        await resolve_child_scope(signal("receipt", state["receipt"]), state["receipt"], settings)
    assert state["calls"] == [("GET", "/v3/receipts/receipt-1"), ("GET", "/v3/refunds/refund-1")]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "fault", ["refund_pending", "receipt_pending", "missing_metadata", "missing_operation"]
)
async def test_scope_incomplete_binding_remains_retryable(scope_case, fault):
    settings, state = scope_case
    if fault == "refund_pending":
        state["refund"]["status"] = "pending"
    elif fault == "receipt_pending":
        state["receipt"]["status"] = "pending"
    elif fault == "missing_metadata":
        state["payment"].pop("metadata")
    else:
        state["payment"]["metadata"].pop("operation_id")
    with pytest.raises(provider_scope.ProviderScopeUnavailable):
        await resolve_child_scope(signal("receipt", state["receipt"]), state["receipt"], settings)


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "kind,field",
    [
        ("receipt", "type"),
        ("receipt", "status"),
        ("payment", "status"),
        ("payment", "created_at"),
        ("payment", "amount"),
    ],
)
async def test_malformed_authoritative_shape_is_retryable(scope_case, kind, field):
    settings, state = scope_case
    source = deepcopy(state["receipt"])
    state[kind][field] = []
    with pytest.raises(provider_scope.ProviderScopeUnavailable):
        await resolve_child_scope(signal("receipt", source), source, settings)


@pytest.mark.asyncio
@pytest.mark.parametrize("shop_id", ["", " shop-1 ", "x" * 161])
async def test_missing_shop_configuration_is_retryable_without_get(scope_case, shop_id):
    settings, state = scope_case
    settings.billing_yookassa_shop_id = shop_id
    with pytest.raises(provider_scope.YooKassaConfigurationError):
        await resolve_child_scope(signal("refund", state["refund"]), state["refund"], settings)
    assert state["calls"] == []


@pytest.mark.parametrize(
    "error",
    [PermissionError("private-path"), UnicodeDecodeError("utf8", b"\xff", 0, 1, "private-path")],
)
def test_provider_secret_read_failure_is_sanitized(tmp_path, monkeypatch, error):
    from twobrain_rec_server.billing.yookassa import YooKassaConfigurationError, _read_secret

    secret = tmp_path / "secret"
    secret.write_text("synthetic")

    def unreadable(*args, **kwargs):
        raise error

    monkeypatch.setattr(Path, "read_text", unreadable)
    with pytest.raises(YooKassaConfigurationError, match="^YooKassa secret is unavailable$"):
        _read_secret(secret)


@pytest.mark.asyncio
async def test_payment_receipt_cannot_claim_refund_parent(scope_case):
    settings, state = scope_case
    state["receipt"]["type"] = "payment"
    with pytest.raises(ValueError):
        await resolve_child_scope(signal("receipt", state["receipt"]), state["receipt"], settings)
    assert state["calls"] == [("GET", "/v3/receipts/receipt-1")]


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "field,value", [("payment_id", []), ("refund_id", ""), ("status", []), ("type", [])]
)
async def test_malformed_callback_is_rejected_before_any_get(scope_case, field, value):
    settings, state = scope_case
    source = deepcopy(state["receipt"])
    source[field] = value
    with pytest.raises(ValueError):
        await resolve_child_scope(signal("receipt", source), source, settings)
    assert state["calls"] == []


@pytest.mark.asyncio
async def test_authoritative_child_operation_hint_cannot_conflict(scope_case):
    settings, state = scope_case
    state["refund"]["metadata"] = {"operation_id": str(uuid4())}
    with pytest.raises(ValueError):
        await resolve_child_scope(signal("receipt", state["receipt"]), state["receipt"], settings)


@pytest.mark.parametrize("status", [[], {}, 123, True])
def test_shared_provider_status_extractors_normalize_malformed_types(status):
    from twobrain_rec_server.billing.reconciliation import (
        ProviderObservationError,
        _payment_status,
        _receipt_registration,
    )

    for extractor in (_payment_status, _receipt_registration):
        with pytest.raises(ProviderObservationError):
            extractor(status)
