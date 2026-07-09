from __future__ import annotations

from urllib.parse import urlencode
from uuid import UUID

from twobrain_rec_server.cabinet.templates import render_template, trusted_component_html

_PLANNED_LOGIN_PROVIDER_ACTIONS: tuple[dict[str, str | bool], ...] = (
    {"provider": "tbank", "label": "T-Банк ID", "mark": "T", "active": False},
    {"provider": "sber", "label": "Sber ID", "mark": "S", "active": False},
    {"provider": "gosuslugi", "label": "Госуслуги", "mark": "Г", "active": False},
    {"provider": "alfa", "label": "Alfa ID", "mark": "A", "active": False},
)


def _login_provider_actions(providers: list, *, next_path: str) -> list[dict[str, str | bool]]:
    active_actions: dict[str, dict[str, str | bool]] = {}
    safe_next = _safe_browser_next_path(next_path)
    for provider in providers:
        provider_id = str(getattr(provider, "provider", "") or "").strip()
        if not provider_id or not bool(getattr(provider, "enabled", True)):
            continue
        if provider_id == "telegram":
            continue
        label = _login_provider_label(
            provider_id, str(getattr(provider, "label", "") or provider_id)
        )
        mark = _login_provider_mark(provider_id, label)
        active = provider_id in {"yandex", "vk"}
        if not active:
            continue
        action: dict[str, str | bool] = {
            "provider": provider_id,
            "label": label,
            "mark": mark,
            "active": active,
            "href": f"/login/{provider_id}/start?{urlencode({'next': safe_next})}",
        }
        active_actions[provider_id] = action

    actions = [
        active_actions[provider_id]
        for provider_id in ("yandex", "vk")
        if provider_id in active_actions
    ]
    actions.extend(dict(action) for action in _PLANNED_LOGIN_PROVIDER_ACTIONS[:2])
    if "vk" in active_actions:
        actions.extend(
            [
                {
                    "provider": "mail_ru",
                    "label": "Mail.ru",
                    "mark": "@",
                    "active": True,
                    "href": f"/login/vk/start?{urlencode({'next': safe_next, 'auth_provider': 'mail_ru'})}",
                },
                {
                    "provider": "ok_ru",
                    "label": "Одноклассники",
                    "mark": "OK",
                    "active": True,
                    "href": f"/login/vk/start?{urlencode({'next': safe_next, 'auth_provider': 'ok_ru'})}",
                },
            ]
        )
    actions.extend(dict(action) for action in _PLANNED_LOGIN_PROVIDER_ACTIONS[2:])
    return actions


def _login_provider_label(provider_id: str, fallback: str) -> str:
    labels = {
        "yandex": "Яндекс ID",
        "vk": "VK ID",
    }
    return labels.get(provider_id, fallback)


def _login_provider_mark(provider_id: str, label: str) -> str:
    marks = {
        "yandex": "Я",
        "vk": "VK",
    }
    return marks.get(provider_id, label[:2].upper())


def render_login_page(
    *,
    workspace_id: UUID | None,
    providers: list,
    next_path: str = "/meetings",
    error: str | None = None,
    product_analytics_provider: dict[str, object] | None = None,
) -> str:
    safe_next = _safe_browser_next_path(next_path)
    content = render_template(
        "cabinet/auth/login.html",
        workspace_configured=workspace_id is not None,
        providers=_login_provider_actions(providers, next_path=safe_next),
        next_path=safe_next,
        signup_href=f"/sign-up?{urlencode({'next': safe_next})}",
        error_message=_login_error_message(error),
    )
    return _standalone_page("Вход", content, product_analytics_provider=product_analytics_provider)


def render_signup_page(
    *,
    workspace_id: UUID | None,
    providers: list,
    next_path: str = "/meetings",
    error: str | None = None,
    mode: str | None = None,
    product_analytics_provider: dict[str, object] | None = None,
) -> str:
    safe_next = _safe_browser_next_path(next_path)
    email_mode = str(mode or "").lower() == "email"
    content = render_template(
        "cabinet/auth/signup.html",
        workspace_configured=workspace_id is not None,
        providers=_login_provider_actions(providers, next_path=safe_next),
        next_path=safe_next,
        email_mode=email_mode,
        error_message=_login_error_message(error),
        login_href=f"/login?{urlencode({'next': safe_next})}",
        signup_href=f"/sign-up?{urlencode({'next': safe_next})}",
        signup_email_href=f"/sign-up?{urlencode({'next': safe_next, 'mode': 'email'})}",
    )
    return _standalone_page("Регистрация", content, product_analytics_provider=product_analytics_provider)


def render_email_code_page(
    *,
    email: str,
    state_nonce: str,
    next_path: str,
    dev_code: str | None = None,
    error: str | None = None,
    flow: str = "login",
    product_analytics_provider: dict[str, object] | None = None,
) -> str:
    safe_next = _safe_browser_next_path(next_path)
    verify_path = "/sign-up/email/verify" if flow == "signup" else "/login/email/verify"
    resend_path = "/sign-up/email/start" if flow == "signup" else "/login/email/start"
    back_path = "/sign-up" if flow == "signup" else "/login"
    page_title = "Подтвердите почту" if flow == "signup" else "Подтвердите вход"
    subtitle = (
        f"Проверьте {email}: мы отправили 6-значный код для создания аккаунта."
        if flow == "signup"
        else f"Проверьте {email}: мы отправили 6-значный код для входа."
    )
    content = render_template(
        "cabinet/auth/email_code.html",
        page_title=page_title,
        subtitle=subtitle,
        verify_path=verify_path,
        resend_path=resend_path,
        back_href=f"{back_path}?{urlencode({'next': safe_next})}",
        email=email,
        state_nonce=state_nonce,
        next_path=safe_next,
        dev_code=dev_code,
        error_message=_login_error_message(error),
    )
    return _standalone_page("Код входа", content, product_analytics_provider=product_analytics_provider)


def _standalone_page(
    title: str,
    content: str,
    *,
    csrf_token: str | None = None,
    product_analytics_provider: dict[str, object] | None = None,
) -> str:
    return render_template(
        "cabinet/base.html",
        title=title,
        surface_mode="auth",
        csrf_token=csrf_token,
        product_analytics_provider=product_analytics_provider,
        content=trusted_component_html(content, source="auth.shell"),
    )


def _safe_browser_next_path(value: str | None) -> str:
    if value is None:
        return "/meetings"
    stripped = value.strip()
    if not stripped or not stripped.startswith("/") or stripped.startswith("//"):
        return "/meetings"
    if any(char in stripped for char in "\r\n"):
        return "/meetings"
    return stripped


def _login_error_message(error: str | None) -> str | None:
    if not error:
        return None
    messages = {
        "missing_auth_context": "Нужен вход, чтобы открыть кабинет встреч.",
        "auth_session_invalid": "Сессия не найдена. Войдите снова.",
        "auth_session_expired": "Сессия истекла. Войдите снова.",
        "device_revoked": "Доступ этого устройства отозван. Войдите с доверенного браузера.",
        "workspace_required": "Нужен workspace id для входа в self-hosted кабинет.",
        "provider_missing": "Этот способ входа не настроен.",
        "provider_disabled": "Этот способ входа выключен политикой кабинета.",
        "provider_future": "Этот способ входа появится позже. Сейчас используйте вход по email.",
        "auth_dependency_unavailable": "Сервис входа временно недоступен.",
        "email_invalid": "Введите корректный email.",
        "email_start_unavailable": "Не удалось отправить код для этого кабинета. Проверьте workspace id и email.",
        "email_delivery_unavailable": "Почтовая доставка временно недоступна. Попробуйте запросить код еще раз.",
        "email_code_invalid": "Код не подошел. Проверьте письмо и попробуйте еще раз.",
        "email_code_expired": "Код истек. Запросите новый код.",
    }
    return messages.get(error, "Не удалось открыть сессию кабинета. Попробуйте войти снова.")
