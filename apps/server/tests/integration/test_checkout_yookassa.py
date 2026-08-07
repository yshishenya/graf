from pathlib import Path

import httpx
import pytest

from twobrain_rec_server.billing.provider_events import (
    ProviderEventError,
    WebhookInbox,
    parse_provider_event,
)
from twobrain_rec_server.billing.yookassa import YooKassaClient, YooKassaProviderError
from twobrain_rec_server.config import Settings


@pytest.mark.asyncio
async def test_hosted_success_decline_timeout_and_duplicate_key_are_observable(tmp_path: Path) -> None:
    secret = tmp_path / "secret"
    secret.write_text("test-secret", encoding="utf-8")
    requests: list[httpx.Request] = []

    async def handler(request: httpx.Request) -> httpx.Response:
        requests.append(request)
        if request.headers["Idempotence-Key"] == "decline":
            return httpx.Response(402, json={"status": "canceled"})
        if request.headers["Idempotence-Key"] == "timeout":
            raise httpx.ReadTimeout("synthetic timeout")
        return httpx.Response(200, json={"id": "pay-1", "status": "pending"})

    settings = Settings(
        billing_yookassa_base_url="https://api.yookassa.test",
        billing_yookassa_shop_id="shop-1",
        billing_yookassa_secret_file=secret,
        billing_provider_floor_minor=100,
    )
    async with YooKassaClient(settings, transport=httpx.MockTransport(handler)) as client:
        first = await client.create_payment(
            amount_minor=79_000,
            currency="RUB",
            description="Личный",
            idempotence_key="same-key",
            metadata={},
        )
        second = await client.create_payment(
            amount_minor=79_000,
            currency="RUB",
            description="Личный",
            idempotence_key="same-key",
            metadata={},
        )
        assert first["id"] == second["id"]
        with pytest.raises(YooKassaProviderError):
            await client.create_payment(
                amount_minor=79_000,
                currency="RUB",
                description="Личный",
                idempotence_key="decline",
                metadata={},
            )
        with pytest.raises(httpx.ReadTimeout):
            await client.create_payment(
                amount_minor=79_000,
                currency="RUB",
                description="Личный",
                idempotence_key="timeout",
                metadata={},
            )
    assert [request.headers["Idempotence-Key"] for request in requests[:2]] == ["same-key", "same-key"]


def test_webhook_duplicate_and_malformed_events_fail_closed() -> None:
    payload = {
        "id": "event-1",
        "event": "payment.succeeded",
        "object": {
            "id": "payment-1",
            "created_at": "2026-08-07T12:00:00Z",
            "metadata": {"workspace_id": "22222222-2222-4222-8222-222222222222"},
        },
    }
    event = parse_provider_event(payload)
    inbox = WebhookInbox()
    assert inbox.accept(event) == "accepted"
    assert inbox.accept(event) == "duplicate"
    conflict = parse_provider_event({**payload, "event": "payment.canceled"})
    assert inbox.accept(conflict) == "replay_conflict"
    with pytest.raises(ProviderEventError):
        parse_provider_event({"id": "event-2", "event": "payment.succeeded", "object": {}})
