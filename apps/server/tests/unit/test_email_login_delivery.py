from __future__ import annotations

import json

import httpx
import pytest

from twobrain_rec_server.auth.email_delivery import (
    EmailLoginDeliveryError,
    PostalEmailLoginClient,
    send_email_login_code,
)
from twobrain_rec_server.config import Settings


@pytest.mark.anyio
async def test_postal_email_login_client_sends_code_with_server_api_key() -> None:
    seen: dict[str, object] = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        seen["path"] = request.url.path
        seen["api_key"] = request.headers.get("x-server-api-key")
        seen["host"] = request.headers.get("host")
        seen["payload"] = json.loads(request.content)
        return httpx.Response(200, json={"status": "success", "data": {"message_id": "msg_1"}})

    client = PostalEmailLoginClient(
        api_url="http://postal-web:5000",
        api_key="postal-test-key",
        from_address="no-reply@rec.2brain.pro",
        host_header="postal.2brain.pro",
        transport=httpx.MockTransport(handler),
    )

    await client.send_login_code(recipient_email="owner@example.test", code="123456", ttl_seconds=900)

    assert seen["path"] == "/api/v1/send/message"
    assert seen["api_key"] == "postal-test-key"
    assert seen["host"] == "postal.2brain.pro"
    payload = seen["payload"]
    assert isinstance(payload, dict)
    assert payload["to"] == ["owner@example.test"]
    assert payload["from"] == "2brain Rec <no-reply@rec.2brain.pro>"
    assert payload["tag"] == "email-login-code"
    assert "123456" in payload["plain_body"]
    assert "Подтвердите вход" in payload["plain_body"]
    assert "Подтвердите вход" in payload["html_body"]
    assert "background:#f0f0f2" in payload["html_body"]


@pytest.mark.anyio
async def test_postal_email_login_client_rejects_postal_error_response() -> None:
    async def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json={"status": "error", "data": {"code": "UnauthenticatedFromAddress"}})

    client = PostalEmailLoginClient(
        api_url="http://postal-web:5000",
        api_key="postal-test-key",
        from_address="no-reply@rec.2brain.pro",
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(EmailLoginDeliveryError, match="postal_delivery_rejected"):
        await client.send_login_code(recipient_email="owner@example.test", code="123456", ttl_seconds=900)


@pytest.mark.anyio
async def test_send_email_login_code_fails_closed_when_delivery_disabled() -> None:
    settings = Settings()

    with pytest.raises(EmailLoginDeliveryError, match="postal_delivery_disabled"):
        await send_email_login_code(
            settings=settings,
            recipient_email="owner@example.test",
            code="123456",
            ttl_seconds=900,
        )
