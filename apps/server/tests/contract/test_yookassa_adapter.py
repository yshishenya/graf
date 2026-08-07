import json
from pathlib import Path

import httpx
import pytest

from twobrain_rec_server.billing.yookassa import YooKassaClient, YooKassaConfigurationError
from twobrain_rec_server.config import Settings


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
