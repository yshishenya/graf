from __future__ import annotations

from dataclasses import dataclass
from email.utils import formataddr
from html import escape
from typing import Any

import httpx

from twobrain_rec_server.config import Settings


class EmailLoginDeliveryError(RuntimeError):
    def __init__(self, reason_code: str, *, retryable: bool = True, status_code: int | None = None) -> None:
        super().__init__(reason_code)
        self.reason_code = reason_code
        self.retryable = retryable
        self.status_code = status_code


@dataclass(frozen=True, slots=True)
class PostalEmailLoginClient:
    api_url: str
    api_key: str
    from_address: str
    from_name: str = "2brain Rec"
    timeout_seconds: int = 10
    transport: httpx.AsyncBaseTransport | None = None

    @classmethod
    def from_settings(cls, settings: Settings) -> PostalEmailLoginClient:
        if settings.postal_api_url is None:
            raise EmailLoginDeliveryError("postal_config_missing", retryable=False)
        if settings.postal_api_key_file is None:
            raise EmailLoginDeliveryError("postal_config_missing", retryable=False)
        if settings.email_login_from_address is None:
            raise EmailLoginDeliveryError("postal_config_missing", retryable=False)
        try:
            api_key = settings.postal_api_key_file.read_text(encoding="utf-8").strip()
        except OSError as exc:
            raise EmailLoginDeliveryError("postal_config_missing", retryable=False) from exc
        if not api_key:
            raise EmailLoginDeliveryError("postal_config_missing", retryable=False)
        return cls(
            api_url=str(settings.postal_api_url).rstrip("/"),
            api_key=api_key,
            from_address=settings.email_login_from_address.strip(),
            from_name=settings.email_login_from_name.strip() or "2brain Rec",
            timeout_seconds=settings.postal_request_timeout_seconds,
        )

    async def send_login_code(self, *, recipient_email: str, code: str, ttl_seconds: int) -> None:
        ttl_minutes = max(1, ttl_seconds // 60)
        payload = {
            "to": [recipient_email],
            "from": formataddr((self.from_name, self.from_address)),
            "subject": "Код входа в 2brain Rec",
            "plain_body": _plain_login_code_body(code=code, ttl_minutes=ttl_minutes),
            "html_body": _html_login_code_body(code=code, ttl_minutes=ttl_minutes),
            "tag": "email-login-code",
            "headers": {"X-2brain-Email-Purpose": "browser-login"},
        }
        await self._post_message(payload)

    async def _post_message(self, payload: dict[str, Any]) -> None:
        timeout = httpx.Timeout(self.timeout_seconds)
        headers = {"X-Server-API-Key": self.api_key, "Content-Type": "application/json"}
        try:
            async with httpx.AsyncClient(
                base_url=self.api_url,
                timeout=timeout,
                headers=headers,
                transport=self.transport,
            ) as client:
                response = await client.post("/api/v1/send/message", json=payload)
        except httpx.TimeoutException as exc:
            raise EmailLoginDeliveryError("postal_timeout", retryable=True) from exc
        except httpx.RequestError as exc:
            raise EmailLoginDeliveryError("postal_request_failed", retryable=True) from exc
        if response.status_code >= 400:
            raise EmailLoginDeliveryError("postal_http_error", retryable=True, status_code=response.status_code)
        try:
            data = response.json()
        except ValueError as exc:
            raise EmailLoginDeliveryError("postal_malformed_response", retryable=True) from exc
        if not isinstance(data, dict) or data.get("status") != "success":
            raise EmailLoginDeliveryError("postal_delivery_rejected", retryable=True)


async def send_email_login_code(
    *,
    settings: Settings,
    recipient_email: str,
    code: str,
    ttl_seconds: int,
) -> None:
    if not settings.email_login_delivery_enabled:
        raise EmailLoginDeliveryError("postal_delivery_disabled", retryable=False)
    client = PostalEmailLoginClient.from_settings(settings)
    await client.send_login_code(recipient_email=recipient_email, code=code, ttl_seconds=ttl_seconds)


def _plain_login_code_body(*, code: str, ttl_minutes: int) -> str:
    return (
        "Код входа в 2brain Rec:\n\n"
        f"{code}\n\n"
        f"Код действует {ttl_minutes} минут. Если вы не запрашивали вход, просто игнорируйте это письмо."
    )


def _html_login_code_body(*, code: str, ttl_minutes: int) -> str:
    escaped_code = escape(code)
    return (
        "<p>Код входа в 2brain Rec:</p>"
        f"<p style=\"font-size:24px;font-weight:700;letter-spacing:4px\">{escaped_code}</p>"
        f"<p>Код действует {ttl_minutes} минут. "
        "Если вы не запрашивали вход, просто игнорируйте это письмо.</p>"
    )
