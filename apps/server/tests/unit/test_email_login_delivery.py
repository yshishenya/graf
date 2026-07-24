from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from email.utils import formataddr

import httpx
import pytest

from twobrain_rec_server.auth.email_delivery import (
    EmailLoginDeliveryError,
    PostalEmailLoginClient,
    send_account_created_email,
    send_email_login_code,
    send_meeting_invitation,
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
    assert payload["from"] == formataddr(("GRAF", "no-reply@rec.2brain.pro"))
    assert payload["subject"] == "Код входа в GRAF"
    assert payload["tag"] == "email-login-code"
    assert "123456" in payload["plain_body"]
    assert "Подтвердите вход в GRAF" in payload["plain_body"]
    assert "Подтвердите вход" in payload["html_body"]
    assert "кабинету GRAF" in payload["html_body"]
    assert "letter-spacing:0" in payload["html_body"]
    assert "background:#111820" not in payload["html_body"]
    assert "Made by GRAF" not in payload["html_body"]
    assert ">2</div>" not in payload["html_body"]
    assert "background:#f0f0f2" in payload["html_body"]


@pytest.mark.anyio
async def test_postal_invitation_resend_is_generic_and_requires_explicit_acceptance() -> None:
    seen: dict[str, object] = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        seen["payload"] = json.loads(request.content)
        return httpx.Response(200, json={"status": "success"})

    client = PostalEmailLoginClient(
        api_url="http://postal-web:5000",
        api_key="postal-test-key",
        from_address="no-reply@rec.2brain.pro",
        transport=httpx.MockTransport(handler),
    )

    await client.send_workspace_invitation_review_notice(recipient_email="owner@example.test")

    payload = seen["payload"]
    assert isinstance(payload, dict)
    assert payload["tag"] == "workspace-invitation-review"
    assert payload["to"] == ["owner@example.test"]
    assert "самостоятельно решите" in payload["plain_body"]
    assert "Без вашего подтверждения" in payload["html_body"]
    assert "workspace_id" not in payload["plain_body"]


@pytest.mark.anyio
async def test_postal_meeting_invitation_contains_safe_metadata_and_signup_cta() -> None:
    seen: dict[str, object] = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        seen["payload"] = json.loads(request.content)
        return httpx.Response(200, json={"status": "success"})

    client = PostalEmailLoginClient(
        api_url="http://postal-web:5000",
        api_key="postal-test-key",
        from_address="no-reply@rec.2brain.pro",
        transport=httpx.MockTransport(handler),
    )
    await client.send_meeting_invitation(
        recipient_email="recipient@example.test",
        acceptance_url="https://graf.example.test/share-invitations/synthetic-token",
        delivery_key="synthetic-delivery-key",
        inviter_name="Алексей Петров",
        meeting_title="Планирование релиза",
        occurred_at=datetime(2026, 7, 23, 10, 0, tzinfo=UTC),
        duration_seconds=3_600,
        expires_at=datetime.now(UTC) + timedelta(days=7),
    )

    payload = seen["payload"]
    assert isinstance(payload, dict)
    assert "Планирование релиза" in payload["plain_body"]
    assert "Алексей Петров" in payload["plain_body"]
    assert "1 ч" in payload["plain_body"]
    assert "создать аккаунт GRAF" in payload["plain_body"]
    assert "транскрип" not in payload["plain_body"].lower()
    assert "audio" not in payload["html_body"].lower()
    assert "recipient@example.test" not in payload["plain_body"]
    assert payload["tag"] == "meeting-share-invitation"


@pytest.mark.anyio
async def test_postal_account_created_email_uses_magic_link_copy_and_masked_address() -> None:
    seen: dict[str, object] = {}

    async def handler(request: httpx.Request) -> httpx.Response:
        seen["payload"] = json.loads(request.content)
        return httpx.Response(200, json={"status": "success"})

    client = PostalEmailLoginClient(
        api_url="http://postal-web:5000",
        api_key="postal-test-key",
        from_address="no-reply@graf.example.test",
        transport=httpx.MockTransport(handler),
    )
    await client.send_account_created_email(
        recipient_email="recipient@example.test",
        meeting_title="Планирование релиза",
        graf_url="https://graf.example.test/meetings",
        settings_url="https://graf.example.test/settings",
        delivery_key="account-created:synthetic-invitation",
    )

    payload = seen["payload"]
    assert isinstance(payload, dict)
    assert payload["subject"] == "Ваш аккаунт GRAF создан"
    assert payload["tag"] == "account-created"
    assert payload["headers"]["X-2brain-Email-Purpose"] == "account-created"
    assert payload["headers"]["X-2brain-Delivery-Key"] == "account-created:synthetic-invitation"
    assert "Планирование релиза" in payload["plain_body"]
    assert "r***@example.test" in payload["plain_body"]
    assert "recipient@example.test" not in payload["plain_body"]
    assert "одноразовая ссылка из письма-приглашения" in payload["plain_body"]
    assert "https://graf.example.test/meetings" in payload["plain_body"]
    assert "https://graf.example.test/settings" in payload["plain_body"]


@pytest.mark.anyio
async def test_send_account_created_email_fails_closed_when_delivery_disabled() -> None:
    with pytest.raises(EmailLoginDeliveryError, match="postal_delivery_disabled"):
        await send_account_created_email(
            settings=Settings(),
            recipient_email="recipient@example.test",
            meeting_title="Встреча",
            graf_url="https://graf.example.test/meetings",
            settings_url="https://graf.example.test/settings",
            delivery_key="synthetic-delivery-key",
        )


@pytest.mark.anyio
async def test_postal_timeout_is_first_class_outcome_unknown() -> None:
    async def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.ReadTimeout("timeout", request=request)

    client = PostalEmailLoginClient(
        api_url="http://postal-web:5000",
        api_key="postal-test-key",
        from_address="no-reply@rec.2brain.pro",
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(EmailLoginDeliveryError) as error:
        await client.send_meeting_invitation(
            recipient_email="recipient@example.test",
            acceptance_url="https://graf.example.test/share-invitations/synthetic-token",
            delivery_key="synthetic-delivery-key",
        )
    assert error.value.reason_code == "postal_timeout"
    assert error.value.outcome_unknown is True
    assert error.value.retryable is False


@pytest.mark.anyio
async def test_postal_malformed_response_is_first_class_outcome_unknown() -> None:
    async def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="not-json")

    client = PostalEmailLoginClient(
        api_url="http://postal-web:5000",
        api_key="postal-test-key",
        from_address="no-reply@rec.2brain.pro",
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(EmailLoginDeliveryError) as error:
        await client.send_meeting_invitation(
            recipient_email="recipient@example.test",
            acceptance_url="https://graf.example.test/share-invitations/synthetic-token",
            delivery_key="synthetic-delivery-key",
        )
    assert error.value.reason_code == "postal_malformed_response"
    assert error.value.outcome_unknown is True
    assert error.value.retryable is False


@pytest.mark.anyio
async def test_postal_5xx_is_first_class_outcome_unknown() -> None:
    async def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, json={"status": "error"})

    client = PostalEmailLoginClient(
        api_url="http://postal-web:5000",
        api_key="postal-test-key",
        from_address="no-reply@rec.2brain.pro",
        transport=httpx.MockTransport(handler),
    )

    with pytest.raises(EmailLoginDeliveryError) as error:
        await client.send_meeting_invitation(
            recipient_email="recipient@example.test",
            acceptance_url="https://graf.example.test/share-invitations/synthetic-token",
            delivery_key="synthetic-delivery-key",
        )
    assert error.value.reason_code == "postal_http_error"
    assert error.value.outcome_unknown is True
    assert error.value.retryable is False


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


@pytest.mark.anyio
async def test_send_meeting_invitation_fails_closed_when_delivery_disabled() -> None:
    with pytest.raises(EmailLoginDeliveryError, match="postal_delivery_disabled"):
        await send_meeting_invitation(
            settings=Settings(),
            recipient_email="recipient@example.test",
            acceptance_url="https://graf.example.test/meetings/synthetic-meeting",
            delivery_key="synthetic-delivery-key",
        )
