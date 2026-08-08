"""Credential-free YooKassa test-shop matrix.

This is a provider-boundary harness, not a public-shop smoke test. It proves
the request contract and observation paths locally; real test-shop evidence
still requires merchant credentials and a controlled canary.
"""

import json
from pathlib import Path

import httpx
import pytest

from twobrain_rec_server.billing.reconciliation import (
    ObservationRecords,
    ProviderScope,
    extract_payment_observation,
    extract_receipt_observation,
)
from twobrain_rec_server.billing.yookassa import YooKassaClient, YooKassaProviderError
from twobrain_rec_server.config import Settings


class MockShopHarness:
    def __init__(self) -> None:
        self.requests: list[httpx.Request] = []
        self.payments: dict[str, dict] = {}
        self.post_status: int = 200
        self.timeout_keys: set[str] = set()
        self.refunds: list[dict] = []
        self.receipts: dict[str, dict] = {}

    async def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append(request)
        if request.method == "POST" and request.url.path == "/v3/payments":
            key = request.headers.get("Idempotence-Key", "")
            if key in self.timeout_keys:
                raise httpx.ReadTimeout("synthetic test-shop timeout", request=request)
            if self.post_status >= 400:
                return httpx.Response(self.post_status, json={"status": "canceled"})
            payload = json.loads(request.content)
            payment = self.payments.setdefault(
                key,
                {
                    "id": f"pay-{len(self.payments) + 1}",
                    "status": "pending",
                    "amount": payload["amount"],
                    "created_at": "2026-08-07T12:00:00Z",
                    "metadata": payload["metadata"],
                    "payment_method": {"type": "bank_card", "saved": payload["save_payment_method"]},
                },
            )
            return httpx.Response(
                200,
                json={
                    "id": payment["id"],
                    "status": payment["status"],
                    "confirmation": {"confirmation_url": "https://api.yookassa.test/checkout/1"},
                },
            )
        if request.method == "GET" and request.url.path.startswith("/v3/payments/"):
            payment_id = request.url.path.rsplit("/", 1)[-1]
            payment = next((item for item in self.payments.values() if item["id"] == payment_id), None)
            return httpx.Response(200, json=payment or {"id": payment_id, "status": "canceled"})
        if request.method == "GET" and request.url.path == "/v3/refunds":
            return httpx.Response(200, json={"items": self.refunds})
        if request.method == "GET" and request.url.path.startswith("/v3/receipts/"):
            receipt_id = request.url.path.rsplit("/", 1)[-1]
            return httpx.Response(200, json=self.receipts.get(receipt_id, {"id": receipt_id, "status": "canceled"}))
        if request.method == "POST" and request.url.path == "/v3/refunds":
            raise AssertionError("product must never call YooKassa refund mutation")
        return httpx.Response(404, json={"error": "not found"})


def _settings(secret: Path) -> Settings:
    return Settings(
        billing_yookassa_base_url="https://api.yookassa.test",
        billing_yookassa_shop_id="shop-test",
        billing_yookassa_secret_file=secret,
        billing_provider_floor_minor=100,
    )


@pytest.mark.asyncio
async def test_test_shop_initial_and_saved_payment_contract(tmp_path: Path) -> None:
    secret = tmp_path / "secret"
    secret.write_text("synthetic-only", encoding="utf-8")
    harness = MockShopHarness()
    async with YooKassaClient(_settings(secret), transport=httpx.MockTransport(harness)) as client:
        result = await client.create_payment(
            amount_minor=79_000,
            currency="RUB",
            description="GRAF Личный",
            idempotence_key="initial-1",
            metadata={"return_url": "https://rec.example/billing"},
            save_payment_method=True,
        )
    assert result["id"] == "pay-1"
    payload = json.loads(harness.requests[0].content)
    assert payload["save_payment_method"] is True
    assert harness.requests[0].headers["Idempotence-Key"] == "initial-1"


@pytest.mark.asyncio
async def test_test_shop_decline_timeout_late_success_and_no_duplicate_key(tmp_path: Path) -> None:
    secret = tmp_path / "secret"
    secret.write_text("synthetic-only", encoding="utf-8")
    harness = MockShopHarness()
    harness.post_status = 402
    async with YooKassaClient(_settings(secret), transport=httpx.MockTransport(harness)) as client:
        with pytest.raises(YooKassaProviderError):
            await client.create_payment(
                amount_minor=79_000,
                currency="RUB",
                description="GRAF Личный",
                idempotence_key="decline-1",
                metadata={},
            )

    harness.post_status = 200
    harness.timeout_keys.add("timeout-1")
    async with YooKassaClient(_settings(secret), transport=httpx.MockTransport(harness)) as client:
        with pytest.raises(httpx.ReadTimeout):
            await client.create_payment(
                amount_minor=79_000,
                currency="RUB",
                description="GRAF Личный",
                idempotence_key="timeout-1",
                metadata={},
            )
        # A later provider GET is the only success authority after timeout.
        harness.timeout_keys.clear()
        payment = await client.create_payment(
            amount_minor=79_000,
            currency="RUB",
            description="GRAF Личный",
            idempotence_key="timeout-1",
            metadata={},
        )
        harness.payments["timeout-1"]["status"] = "succeeded"
        observed = await client.get_payment(payment["id"])
    assert observed["status"] == "succeeded"
    scope = ProviderScope(environment="test", shop_id="shop-test")
    records = ObservationRecords()
    pending = extract_payment_observation(harness.payments["timeout-1"], scope=scope)
    pending = pending.__class__(
        scope=pending.scope,
        provider_payment_id=pending.provider_payment_id,
        amount_minor=pending.amount_minor,
        currency=pending.currency,
        status="pending",
        provider_created_at=pending.provider_created_at,
    )
    succeeded = extract_payment_observation(harness.payments["timeout-1"], scope=scope)
    assert records.record(pending, source="poll", observed_at=pending.provider_created_at) == "inserted"
    assert records.record(succeeded, source="poll", observed_at=succeeded.provider_created_at) == "updated"


@pytest.mark.asyncio
async def test_test_shop_floor_zero_binding_receipt_and_refund_observation_are_read_only(tmp_path: Path) -> None:
    secret = tmp_path / "secret"
    secret.write_text("synthetic-only", encoding="utf-8")
    harness = MockShopHarness()
    harness.refunds = [
        {
            "id": "refund-1",
            "payment_id": "pay-1",
            "status": "succeeded",
            "amount": {"value": "1.00", "currency": "RUB"},
            "created_at": "2026-08-07T12:01:00Z",
        }
    ]
    harness.receipts["receipt-1"] = {
        "id": "receipt-1",
        "type": "payment",
        "payment_id": "pay-1",
        "status": "succeeded",
        "registered_at": "2026-08-07T12:01:01Z",
    }
    async with YooKassaClient(_settings(secret), transport=httpx.MockTransport(harness)) as client:
        assert client.supports_zero_amount_binding is False
        with pytest.raises(ValueError, match="floor"):
            await client.create_payment(
                amount_minor=1,
                currency="RUB",
                description="floor",
                idempotence_key="floor-1",
                metadata={},
            )
        refunds = await client.list_refunds(payment_id="pay-1")
        receipt = await client.get_receipt("receipt-1")
    assert refunds["items"][0]["id"] == "refund-1"
    assert extract_receipt_observation(receipt, scope=ProviderScope(environment="test", shop_id="shop-test")).provider_parent_id == "pay-1"
    assert all(not (request.method == "POST" and request.url.path == "/v3/refunds") for request in harness.requests)
