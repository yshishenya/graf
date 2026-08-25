import json
from hashlib import sha256
from pathlib import Path

import httpx
import pytest

from twobrain_rec_server.billing.yookassa import (
    YooKassaClient,
    YooKassaConfigurationError,
    YooKassaProviderError,
    build_receipt_payload,
)
from twobrain_rec_server.config import Settings


def test_receipt_payload_uses_exact_minor_unit_amount_and_fails_closed() -> None:
    receipt = build_receipt_payload(
        receipt_contact="billing@example.test",
        amount_minor=10001,
        currency="RUB",
        description="Личный",
        tax_system_code=2,
        vat_code=1,
        payment_subject="service",
        payment_mode="full_payment",
    )
    assert receipt["items"][0]["amount"] == {"value": "100.01", "currency": "RUB"}
    with pytest.raises(YooKassaConfigurationError, match="receipt contact"):
        build_receipt_payload(
            receipt_contact=None,
            amount_minor=10001,
            currency="RUB",
            description="Личный",
            tax_system_code=2,
            vat_code=1,
            payment_subject="service",
            payment_mode="full_payment",
        )


@pytest.mark.asyncio
async def test_yookassa_adapter_allows_payment_and_read_only_refund_observation(tmp_path: Path) -> None:
    secret = tmp_path / "secret"
    secret.write_text("test-secret", encoding="utf-8")
    requests: list[httpx.Request] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.url.path == "/v3/payments":
            return httpx.Response(200, json={"id": "pay-1", "status": "pending"})
        return httpx.Response(200, json={"items": []})

    settings = Settings(
        billing_yookassa_base_url="https://api.yookassa.test",
        billing_yookassa_shop_id="shop-1",
        billing_yookassa_secret_file=secret,
        billing_provider_floor_minor=100,
    )
    async with YooKassaClient(settings, transport=httpx.MockTransport(handler)) as client:
        payment = await client.create_payment(
            amount_minor=79_000,
            currency="RUB",
            description="Личный",
            idempotence_key="op-1",
            metadata={"return_url": "https://rec.2brain.pro/account/billing"},
        )
        refunds = await client.list_refunds(payment_id="pay-1")
    assert payment["id"] == "pay-1"
    assert refunds == {"items": []}
    assert requests[0].headers["Idempotence-Key"] == "op-1"
    assert all(request.url.path != "/v3/refunds" or request.method == "GET" for request in requests)


@pytest.mark.asyncio
async def test_yookassa_adapter_does_not_allow_zero_payment(tmp_path: Path) -> None:
    secret = tmp_path / "secret"
    secret.write_text("test-secret", encoding="utf-8")
    settings = Settings(
        billing_yookassa_base_url="https://api.yookassa.test",
        billing_yookassa_shop_id="shop-1",
        billing_yookassa_secret_file=secret,
        billing_provider_floor_minor=100,
    )
    async with YooKassaClient(
        settings, transport=httpx.MockTransport(lambda _: httpx.Response(200))
    ) as client:
        with pytest.raises(ValueError):
            await client.create_payment(
                amount_minor=0,
                currency="RUB",
                description="Личный",
                idempotence_key="op-1",
                metadata={},
            )
        assert client.supports_zero_amount_binding is False
        with pytest.raises(ValueError, match="provider floor"):
            await client.create_payment(
                amount_minor=1,
                currency="RUB",
                description="Личный",
                idempotence_key="op-floor",
                metadata={},
            )


@pytest.mark.asyncio
async def test_yookassa_refund_listing_forwards_bounded_cursor_and_limit(tmp_path: Path) -> None:
    secret = tmp_path / "secret"
    secret.write_text("test-secret", encoding="utf-8")
    requests: list[httpx.Request] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        return httpx.Response(200, json={"items": [], "next_cursor": "next"})

    settings = Settings(
        billing_yookassa_base_url="https://api.yookassa.test",
        billing_yookassa_shop_id="shop-1",
        billing_yookassa_secret_file=secret,
    )
    async with YooKassaClient(settings, transport=httpx.MockTransport(handler)) as client:
        await client.list_refunds(cursor="previous", limit=100)
        with pytest.raises(ValueError, match="between 1 and 100"):
            await client.list_refunds(limit=101)
    assert requests[0].url.params["cursor"] == "previous"
    assert requests[0].url.params["limit"] == "100"


def test_yookassa_client_rejects_unallowlisted_api_host(tmp_path: Path) -> None:
    secret = tmp_path / "test-secret"
    secret.write_text("test-secret", encoding="utf-8")
    settings = Settings(
        billing_yookassa_base_url="https://evil.example.test",
        billing_yookassa_shop_id="shop-1",
        billing_yookassa_secret_file=secret,
    )

    with pytest.raises(YooKassaConfigurationError, match="allowlisted"):
        YooKassaClient(settings)


def test_yookassa_client_rejects_versioned_base_path(tmp_path: Path) -> None:
    secret = tmp_path / "secret"
    secret.write_text("synthetic", encoding="utf-8")
    settings = Settings(
        billing_yookassa_base_url="https://api.yookassa.test/v3",
        billing_yookassa_shop_id="shop-test",
        billing_yookassa_secret_file=secret,
    )

    with pytest.raises(YooKassaConfigurationError, match="allowlisted"):
        YooKassaClient(settings)


@pytest.mark.asyncio
async def test_yookassa_adapter_uses_hosted_redirect_and_saved_method_consent(tmp_path: Path) -> None:
    secret = tmp_path / "secret"
    secret.write_text("test-secret", encoding="utf-8")
    captured: list[httpx.Request] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(200, json={"id": "pay-2"})

    settings = Settings(
        billing_yookassa_base_url="https://api.yookassa.test",
        billing_yookassa_shop_id="shop-1",
        billing_yookassa_secret_file=secret,
    )
    async with YooKassaClient(settings, transport=httpx.MockTransport(handler)) as client:
        await client.create_payment(
            amount_minor=7_900,
            currency="RUB",
            description="Личный",
            idempotence_key="op-2",
            metadata={"return_url": "https://rec.2brain.pro/account/billing"},
            save_payment_method=True,
        )
    assert len(captured) == 1
    payload = json.loads(captured[0].content)
    assert payload["save_payment_method"] is True
    assert payload["confirmation"]["type"] == "redirect"
    assert captured[0].headers["Idempotence-Key"] == "op-2"


@pytest.mark.asyncio
async def test_yookassa_adapter_hashes_overlong_idempotence_key(tmp_path: Path) -> None:
    secret = tmp_path / "secret"
    secret.write_text("test-secret", encoding="utf-8")
    captured: list[httpx.Request] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(200, json={"id": "pay-long-key"})

    settings = Settings(
        billing_yookassa_base_url="https://api.yookassa.test",
        billing_yookassa_shop_id="shop-1",
        billing_yookassa_secret_file=secret,
    )
    key = "checkout:" + "x" * 100
    async with YooKassaClient(settings, transport=httpx.MockTransport(handler)) as client:
        await client.create_payment(
            amount_minor=7_900,
            currency="RUB",
            description="Личный",
            idempotence_key=key,
            metadata={"return_url": "https://rec.2brain.pro/billing"},
        )

    assert captured[0].headers["Idempotence-Key"] == sha256(key.encode()).hexdigest()


@pytest.mark.asyncio
async def test_yookassa_adapter_recurring_payment_uses_saved_method_without_confirmation(tmp_path: Path) -> None:
    secret = tmp_path / "secret"
    secret.write_text("test-secret", encoding="utf-8")
    captured: list[httpx.Request] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        captured.append(request)
        return httpx.Response(200, json={"id": "pay-renewal-1", "status": "pending"})

    settings = Settings(
        billing_yookassa_base_url="https://api.yookassa.test",
        billing_yookassa_shop_id="shop-1",
        billing_yookassa_secret_file=secret,
    )
    async with YooKassaClient(settings, transport=httpx.MockTransport(handler)) as client:
        await client.create_payment(
            amount_minor=79_000,
            currency="RUB",
            description="Личный, месяц",
            idempotence_key="renewal-op-1",
            metadata={"workspace_id": "workspace-1", "operation_id": "operation-1"},
            payment_method_id="pm-card-1",
        )
    payload = json.loads(captured[0].content)
    assert payload["payment_method_id"] == "pm-card-1"
    assert "confirmation" not in payload
    assert "save_payment_method" not in payload
    assert captured[0].headers["Idempotence-Key"] == "renewal-op-1"


@pytest.mark.asyncio
async def test_yookassa_adapter_exposes_provider_status_code(tmp_path: Path) -> None:
    secret = tmp_path / "secret"
    secret.write_text("test-secret", encoding="utf-8")
    settings = Settings(
        billing_yookassa_base_url="https://api.yookassa.test",
        billing_yookassa_shop_id="shop-1",
        billing_yookassa_secret_file=secret,
    )
    async with YooKassaClient(
        settings,
        transport=httpx.MockTransport(lambda _: httpx.Response(402, json={"type": "error"})),
    ) as client:
        with pytest.raises(YooKassaProviderError) as exc_info:
            await client.create_payment(
                amount_minor=79_000,
                currency="RUB",
                description="Личный",
                idempotence_key="renewal-4xx",
                metadata={},
                payment_method_id="pm-card-1",
            )
    assert exc_info.value.status_code == 402
