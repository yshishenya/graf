from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from email.utils import formataddr
from html import escape
from typing import Any

import httpx

from twobrain_rec_server.config import Settings


class EmailLoginDeliveryError(RuntimeError):
    def __init__(
        self,
        reason_code: str,
        *,
        retryable: bool = True,
        status_code: int | None = None,
        outcome_unknown: bool = False,
    ) -> None:
        super().__init__(reason_code)
        self.reason_code = reason_code
        self.retryable = retryable
        self.status_code = status_code
        self.outcome_unknown = outcome_unknown


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

    async def send_workspace_invitation_review_notice(self, *, recipient_email: str) -> None:
        payload = {
            "to": [recipient_email],
            "from": formataddr((self.from_name, self.from_address)),
            "subject": "Приглашение в команду GRAF",
            "plain_body": _plain_workspace_invitation_review_body(),
            "html_body": _html_workspace_invitation_review_body(),
            "tag": "workspace-invitation-review",
            "headers": {"X-2brain-Email-Purpose": "workspace-invitation-review"},
        }
        await self._post_message(payload)

    async def send_meeting_invitation(
        self,
        *,
        recipient_email: str,
        acceptance_url: str,
        delivery_key: str,
        content_scope: str = "summary_only",
        inviter_name: str | None = None,
        meeting_title: str | None = None,
        occurred_at: datetime | None = None,
        duration_seconds: int | None = None,
        expires_at: datetime | None = None,
    ) -> None:
        safe_url = escape(acceptance_url, quote=True)
        plain_body, html_body = _meeting_invitation_bodies(
            acceptance_url=acceptance_url,
            safe_url=safe_url,
            content_scope=content_scope,
            inviter_name=inviter_name,
            meeting_title=meeting_title,
            occurred_at=occurred_at,
            duration_seconds=duration_seconds,
            expires_at=expires_at,
        )
        payload = {
            "to": [recipient_email],
            "from": formataddr((self.from_name, self.from_address)),
            "subject": (
                "Вам открыли запись встречи в GRAF"
                if content_scope == "full_meeting"
                else "Вам открыли итоги встречи в GRAF"
            ),
            "plain_body": plain_body,
            "html_body": html_body,
            "tag": "meeting-share-invitation",
            "headers": {
                "X-2brain-Email-Purpose": "meeting-share-invitation",
                "X-2brain-Delivery-Key": delivery_key,
            },
        }
        await self._post_message(payload)

    async def send_account_created_email(
        self,
        *,
        recipient_email: str,
        meeting_title: str | None,
        content_scope: str = "summary_only",
        graf_url: str,
        settings_url: str,
        delivery_key: str,
    ) -> None:
        plain_body, html_body = _account_created_email_bodies(
            recipient_email=recipient_email,
            meeting_title=meeting_title,
            content_scope=content_scope,
            graf_url=graf_url,
            settings_url=settings_url,
        )
        payload = {
            "to": [recipient_email],
            "from": formataddr((self.from_name, self.from_address)),
            "subject": "Ваш аккаунт GRAF создан",
            "plain_body": plain_body,
            "html_body": html_body,
            "tag": "account-created",
            "headers": {
                "X-2brain-Email-Purpose": "account-created",
                "X-2brain-Delivery-Key": delivery_key,
            },
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
            raise EmailLoginDeliveryError(
                "postal_timeout", retryable=False, outcome_unknown=True
            ) from exc
        except httpx.RequestError as exc:
            raise EmailLoginDeliveryError(
                "postal_request_failed", retryable=False, outcome_unknown=True
            ) from exc
        if response.status_code >= 500:
            raise EmailLoginDeliveryError(
                "postal_http_error",
                retryable=False,
                outcome_unknown=True,
                status_code=response.status_code,
            )
        if response.status_code >= 400:
            raise EmailLoginDeliveryError("postal_http_error", retryable=True, status_code=response.status_code)
        try:
            data = response.json()
        except ValueError as exc:
            raise EmailLoginDeliveryError(
                "postal_malformed_response", retryable=False, outcome_unknown=True
            ) from exc
        if not isinstance(data, dict) or data.get("status") != "success":
            raise EmailLoginDeliveryError("postal_delivery_rejected", retryable=True)


def _meeting_invitation_bodies(
    *,
    acceptance_url: str,
    safe_url: str,
    content_scope: str = "summary_only",
    inviter_name: str | None,
    meeting_title: str | None,
    occurred_at: datetime | None,
    duration_seconds: int | None,
    expires_at: datetime | None,
) -> tuple[str, str]:
    inviter = _safe_email_label(inviter_name, fallback="Пользователь GRAF")
    title = _safe_email_label(meeting_title, fallback="Встреча")
    safe_title = escape(title)
    safe_inviter = escape(inviter)
    recording_access = content_scope == "full_meeting"
    access_label = "запись встречи" if recording_access else "итоги встречи"
    access_details = (
        "Вам доступны расшифровка, саммари, прослушивание и скачивание аудио."
        if recording_access
        else "Доступ ограничен итогами этой встречи."
    )
    details: list[str] = [f"Встреча: {title}"]
    html_details: list[str] = [f"<strong>{safe_title}</strong>"]
    if occurred_at is not None:
        date_label = _meeting_invitation_datetime(occurred_at)
        details.append(f"Дата: {date_label}")
        html_details.append(f"<span>Дата: {escape(date_label)}</span>")
    if duration_seconds is not None:
        duration_label = _meeting_invitation_duration(duration_seconds)
        details.append(f"Продолжительность: {duration_label}")
        html_details.append(f"<span>Продолжительность: {escape(duration_label)}</span>")
    if expires_at is not None:
        expiry_label = _meeting_invitation_datetime(expires_at)
        details.append(f"Приглашение действует до: {expiry_label}")
        html_details.append(f"<span>Ссылка действует до: {escape(expiry_label)}</span>")
    plain = (
        f"{inviter} открыл(а) вам {access_label} в GRAF.\n\n"
        + "\n".join(details)
        + "\n\nОткройте одноразовую ссылку, чтобы войти или создать аккаунт GRAF.\n"
        + f"{acceptance_url}\n\n"
        + access_details
        + " Рабочая область не меняется."
    )
    html = (
        '<div style="font-family:-apple-system,BlinkMacSystemFont,\'Segoe UI\',Arial,sans-serif;'
        'max-width:560px;color:#373941;line-height:1.5">'
        f"<p><strong>{safe_inviter}</strong> открыл(а) вам {escape(access_label)} в GRAF.</p>"
        '<div style="border:1px solid #dfe1e7;border-radius:12px;padding:18px 20px;">'
        + "<br>".join(html_details)
        + "</div>"
        '<p style="margin:24px 0"><a href="'
        + safe_url
        + '" style="display:inline-block;background:#7657f5;color:#fff;border-radius:10px;'
        'padding:12px 20px;text-decoration:none;font-weight:700">Открыть GRAF</a></p>'
        "<p style=\"color:#646a78;font-size:14px\">Одноразовая ссылка ведёт на вход или регистрацию GRAF."
        f" {escape(access_details)} Рабочая область не меняется.</p>"
        "</div>"
    )
    return plain, html


def _safe_email_label(value: str | None, *, fallback: str) -> str:
    label = " ".join((value or fallback).split())[:160]
    return fallback if "@" in label else label or fallback


def _meeting_invitation_datetime(value: datetime) -> str:
    aware = value.replace(tzinfo=UTC) if value.tzinfo is None else value.astimezone(UTC)
    return aware.strftime("%d.%m.%Y, %H:%M UTC")


def _meeting_invitation_duration(seconds: int) -> str:
    minutes = max(0, int(seconds)) // 60
    if minutes < 60:
        return f"{minutes} мин"
    hours, remainder = divmod(minutes, 60)
    return f"{hours} ч {remainder} мин" if remainder else f"{hours} ч"


def _mask_email_address(address: str) -> str:
    local, _, domain = address.strip().lower().partition("@")
    if not local or not domain:
        return "ваш адрес"
    masked_local = f"{local[0]}***" if len(local) > 1 else "*"
    return f"{masked_local}@{domain}"


def _account_created_email_bodies(
    *,
    recipient_email: str,
    meeting_title: str | None,
    content_scope: str = "summary_only",
    graf_url: str,
    settings_url: str,
) -> tuple[str, str]:
    title = _safe_email_label(meeting_title, fallback="Встреча")
    masked_email = _mask_email_address(recipient_email)
    safe_title = escape(title)
    safe_email = escape(masked_email)
    access_label = "записи" if content_scope == "full_meeting" else "итогам"
    safe_access_label = escape(access_label)
    safe_graf_url = escape(graf_url, quote=True)
    safe_settings_url = escape(settings_url, quote=True)
    plain = (
        f"Вам открыли доступ к {access_label} встречи «{title}». GRAF создал личный аккаунт для этого доступа.\n\n"
        f"GRAF автоматически создал бесплатный аккаунт на адрес {masked_email}.\n\n"
        "Пароль создавать не нужно. Для входа используется одноразовая ссылка из письма-приглашения.\n\n"
        "Открыть GRAF:\n"
        f"{graf_url}\n\n"
        "Открыть настройки аккаунта:\n"
        f"{settings_url}\n\n"
        "Если вы не ожидали этого письма, вы можете отозвать доступ к встрече "
        "или обратиться в поддержку."
    )
    html = (
        '<div style="font-family:-apple-system,BlinkMacSystemFont,\'Segoe UI\',Arial,sans-serif;'
        'max-width:560px;color:#373941;line-height:1.5">'
        '<div style="color:#111820;font-size:28px;line-height:1;font-weight:850;'
        'letter-spacing:-1px;margin:0 0 28px">GRAF</div>'
        f"<p>Вам открыли доступ к {safe_access_label} встречи <strong>«{safe_title}»</strong>. "
        "GRAF создал личный аккаунт для этого доступа.</p>"
        f"<p>GRAF автоматически создал бесплатный аккаунт на адрес <strong>{safe_email}</strong>.</p>"
        '<div style="border:1px solid #dfe1e7;border-radius:12px;padding:16px 18px;'
        'background:#f7f7f8;margin:24px 0">'
        "<strong>Пароль создавать не нужно.</strong><br>"
        "Для входа используется одноразовая ссылка из письма-приглашения."
        "</div>"
        f'<p style="margin:24px 0 12px"><a href="{safe_graf_url}" style="display:inline-block;'
        'background:#7657f5;color:#fff;border-radius:10px;padding:12px 20px;'
        'text-decoration:none;font-weight:700">Открыть GRAF</a></p>'
        f'<p style="margin:0 0 28px"><a href="{safe_settings_url}" style="color:#7657f5;'
        'font-weight:700">Открыть настройки аккаунта</a></p>'
        '<p style="color:#646a78;font-size:14px">Если вы не ожидали этого письма, вы можете '
        "отозвать доступ к встрече или обратиться в поддержку.</p>"
        "</div>"
    )
    return plain, html


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


async def send_workspace_invitation_review_notice(
    *,
    settings: Settings,
    recipient_email: str,
) -> None:
    if not settings.email_login_delivery_enabled:
        raise EmailLoginDeliveryError("postal_delivery_disabled", retryable=False)
    client = PostalEmailLoginClient.from_settings(settings)
    await client.send_workspace_invitation_review_notice(recipient_email=recipient_email)


async def send_meeting_invitation(
    *,
    settings: Settings,
    recipient_email: str,
    acceptance_url: str,
    delivery_key: str,
    content_scope: str = "summary_only",
    inviter_name: str | None = None,
    meeting_title: str | None = None,
    occurred_at: datetime | None = None,
    duration_seconds: int | None = None,
    expires_at: datetime | None = None,
) -> None:
    if not settings.email_login_delivery_enabled:
        raise EmailLoginDeliveryError("postal_delivery_disabled", retryable=False)
    client = PostalEmailLoginClient.from_settings(settings)
    await client.send_meeting_invitation(
        recipient_email=recipient_email,
        acceptance_url=acceptance_url,
        delivery_key=delivery_key,
        content_scope=content_scope,
        inviter_name=inviter_name,
        meeting_title=meeting_title,
        occurred_at=occurred_at,
        duration_seconds=duration_seconds,
        expires_at=expires_at,
    )


async def send_account_created_email(
    *,
    settings: Settings,
    recipient_email: str,
    meeting_title: str | None,
    content_scope: str = "summary_only",
    graf_url: str,
    settings_url: str,
    delivery_key: str,
) -> None:
    if not settings.email_login_delivery_enabled:
        raise EmailLoginDeliveryError("postal_delivery_disabled", retryable=False)
    client = PostalEmailLoginClient.from_settings(settings)
    await client.send_account_created_email(
        recipient_email=recipient_email,
        meeting_title=meeting_title,
        content_scope=content_scope,
        graf_url=graf_url,
        settings_url=settings_url,
        delivery_key=delivery_key,
    )


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
                    <div style="display:inline-block;color:#111820;font-size:24px;line-height:1;font-weight:850;letter-spacing:0;">GRAF</div>
                    <div style="width:42px;height:4px;border-radius:999px;background:#8b5cf6;margin:10px auto 0;"></div>
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
                    <div style="font-weight:700;color:#555862;">GRAF</div>
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


def _plain_workspace_invitation_review_body() -> str:
    return (
        "У вас есть приглашение в команду GRAF.\n\n"
        "Войдите в GRAF под этой почтой и самостоятельно решите, принимать ли приглашение. "
        "Без вашего подтверждения доступ к команде не будет создан."
    )


def _html_workspace_invitation_review_body() -> str:
    return """
    <!doctype html>
    <html lang="ru">
      <body>
        <h1>У вас есть приглашение в команду GRAF</h1>
        <p>Войдите в GRAF под этой почтой и самостоятельно решите, принимать ли приглашение.</p>
        <p>Без вашего подтверждения доступ к команде не будет создан.</p>
      </body>
    </html>
    """
