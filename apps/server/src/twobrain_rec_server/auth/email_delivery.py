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
    from_name: str = "GRAF"
    host_header: str | None = None
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
            from_name=settings.email_login_from_name.strip() or "GRAF",
            host_header=settings.postal_host_header.strip() if settings.postal_host_header else None,
            timeout_seconds=settings.postal_request_timeout_seconds,
        )

    async def send_login_code(self, *, recipient_email: str, code: str, ttl_seconds: int) -> None:
        ttl_minutes = max(1, ttl_seconds // 60)
        payload = {
            "to": [recipient_email],
            "from": formataddr((self.from_name, self.from_address)),
            "subject": "Код входа в GRAF",
            "plain_body": _plain_login_code_body(code=code, ttl_minutes=ttl_minutes),
            "html_body": _html_login_code_body(code=code, ttl_minutes=ttl_minutes),
            "tag": "email-login-code",
            "headers": {"X-2brain-Email-Purpose": "browser-login"},
        }
        await self._post_message(payload)

    async def _post_message(self, payload: dict[str, Any]) -> None:
        timeout = httpx.Timeout(self.timeout_seconds)
        headers = {"X-Server-API-Key": self.api_key, "Content-Type": "application/json"}
        if self.host_header:
            headers["Host"] = self.host_header
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
        "Подтвердите вход в GRAF\n\n"
        "Ваш код подтверждения:\n\n"
        f"{code}\n\n"
        f"Код действует {ttl_minutes} минут. "
        "Если вы не запрашивали вход или регистрацию, просто игнорируйте это письмо."
    )


def _html_login_code_body(*, code: str, ttl_minutes: int) -> str:
    escaped_code = escape(code)
    return f"""
    <!doctype html>
    <html lang="ru">
      <body style="margin:0;background:#f7f7f8;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Arial,sans-serif;color:#373941;">
        <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="background:#f7f7f8;padding:44px 16px;">
          <tr>
            <td align="center">
              <table role="presentation" width="100%" cellspacing="0" cellpadding="0" style="max-width:560px;background:#ffffff;border-radius:0;padding:0;">
                <tr>
                  <td align="center" style="padding:36px 36px 16px;">
                    <div style="min-width:74px;height:34px;border-radius:8px;background:#111820;color:#ffffff;display:inline-block;line-height:34px;font-weight:800;font-size:18px;letter-spacing:1px;">GRAF</div>
                  </td>
                </tr>
                <tr>
                  <td align="center" style="padding:0 36px;">
                    <h1 style="margin:0 0 22px;font-size:28px;line-height:1.2;font-weight:760;color:#42434a;">Подтвердите вход</h1>
                    <p style="margin:0 0 18px;font-size:16px;line-height:1.5;color:#555862;">Ваш код подтверждения:</p>
                    <div style="background:#f0f0f2;border-radius:4px;padding:18px 24px;margin:0 auto 24px;max-width:360px;font-size:28px;line-height:1;font-weight:780;letter-spacing:3px;color:#3a3c43;">{escaped_code}</div>
                    <p style="margin:0 0 18px;font-size:16px;line-height:1.5;color:#555862;">Код действует {ttl_minutes} минут. Не пересылайте это письмо: оно открывает доступ к вашему кабинету GRAF.</p>
                    <p style="margin:0 0 28px;font-size:15px;line-height:1.5;color:#555862;">Если вы не запрашивали вход или регистрацию, просто проигнорируйте это письмо.</p>
                  </td>
                </tr>
                <tr>
                  <td align="center" style="border-top:1px solid #e5e5e7;padding:18px 36px 34px;color:#777b84;font-size:12px;line-height:1.5;">
                    <div>Made by GRAF</div>
                    <div>Самостоятельный кабинет записи и расшифровки встреч</div>
                  </td>
                </tr>
              </table>
            </td>
          </tr>
        </table>
      </body>
    </html>
    """
