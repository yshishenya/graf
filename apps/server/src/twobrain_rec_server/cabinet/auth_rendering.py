from __future__ import annotations

from urllib.parse import urlencode
from uuid import UUID

from twobrain_rec_server.auth.redirects import safe_first_party_path
from twobrain_rec_server.cabinet.templates import render_template, trusted_component_html
from twobrain_rec_server.cabinet.view_models import PROVIDER_LINK_LABELS

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
        label = PROVIDER_LINK_LABELS.get(
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
    invitation_flow: bool = False,
    recovery_mode: bool = False,
    product_analytics_provider: dict[str, object] | None = None,
) -> str:
    safe_next = _safe_browser_next_path(next_path)
    embedded = safe_next.startswith("/desktop/")
    provider_actions = _login_provider_actions(providers, next_path=safe_next)
    if recovery_mode:
        provider_actions = [action for action in provider_actions if action["active"]]
    success_result = error in {
        "email_connected_relogin_required",
        "yandex_connected_relogin_required",
        "vk_connected_relogin_required",
        "sign_in_method_connected_relogin_required",
    }
    message_heading = "Подключение завершено" if success_result else "Не удалось продолжить"
    content = render_template(
        "cabinet/auth/login.html",
        workspace_configured=workspace_id is not None,
        providers=provider_actions,
        next_path=safe_next,
        signup_href=f"/sign-up?{urlencode({'next': safe_next})}",
        invitation_flow=invitation_flow,
        recovery_mode=recovery_mode,
        embedded=embedded,
        error_message=_login_error_message(error),
        message_kind="success" if success_result else "error",
        message_heading=message_heading,
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
    return _standalone_page(
        "Регистрация", content, product_analytics_provider=product_analytics_provider
    )


def render_email_code_page(
    *,
    email: str,
    state_nonce: str,
    next_path: str,
    dev_code: str | None = None,
    error: str | None = None,
    flow: str = "login",
    csrf_token: str | None = None,
    product_analytics_provider: dict[str, object] | None = None,
) -> str:
    safe_next = _safe_browser_next_path(next_path)
    link_flow = flow in {"link", "desktop_link"}
    link_base_path = "/desktop/settings/account" if flow == "desktop_link" else "/settings/account"
    verify_path = (
        f"{link_base_path}/email-link/verify"
        if link_flow
        else ("/sign-up/email/verify" if flow == "signup" else "/login/email/verify")
    )
    resend_path = (
        f"{link_base_path}/email-link/start"
        if link_flow
        else ("/sign-up/email/start" if flow == "signup" else "/login/email/start")
    )
    back_path = link_base_path if link_flow else ("/sign-up" if flow == "signup" else "/login")
    invitation_flow = flow == "share_invitation"
    can_verify = bool(state_nonce) and error not in {
        "auth_rate_limited",
        "email_code_invalid",
        "email_code_expired",
    }
    message_heading = {
        "auth_rate_limited": "Слишком много попыток",
        "email_delivery_unavailable": "Почта временно недоступна",
        "email_invalid": "Проверьте email",
        "email_code_wrong": "Код введён неверно",
        "email_code_expired": "Код истёк",
    }.get(error, "Код не принят")
    page_title = (
        "Запросите новый код"
        if not can_verify
        else (
            "Откройте итоги встречи"
            if invitation_flow
            else (
                "Подтвердите email для подключения"
                if link_flow
                else ("Подтвердите почту" if flow == "signup" else "Подтвердите вход")
            )
        )
    )
    subtitle = (
        "Исправьте email и запросите новый код."
        if error == "email_invalid"
        else "Запросите новый одноразовый код, чтобы продолжить."
        if not can_verify
        else (
            f"Проверьте {email}: мы отправили 6-значный код. Если аккаунта GRAF ещё нет, "
            "он создастся автоматически."
            if invitation_flow
            else (
                f"Проверьте {email}: мы отправили 6-значный код для создания аккаунта."
                if flow == "signup"
                else (
                    f"Проверьте {email}: мы отправили 6-значный код для подключения к текущему профилю."
                    if link_flow
                    else f"Проверьте {email}: мы отправили 6-значный код для входа."
                )
            )
        )
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
        csrf_token=csrf_token,
        dev_code=dev_code,
        error_message=_login_error_message(error, link_flow=link_flow),
        message_heading=message_heading,
        embedded_code_panel=flow == "desktop_link",
        can_verify=can_verify,
        retry_requires_email=not bool(email),
    )
    return _standalone_page(
        "Код входа", content, product_analytics_provider=product_analytics_provider
    )


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
    return safe_first_party_path(value) or "/meetings"


def _login_error_message(error: str | None, *, link_flow: bool = False) -> str | None:
    if not error:
        return None
    if error == "ambiguous_email_recovery_required" and link_flow:
        return (
            "Этот email связан с несколькими профилями. Вернитесь в настройки и "
            "подтвердите другой уже подключённый способ входа — например, Яндекс ID или VK."
        )
    messages = {
        "missing_auth_context": "Нужен вход, чтобы открыть кабинет встреч.",
        "auth_handoff_invalid": "Не удалось безопасно открыть тарифы. Войдите ещё раз.",
        "auth_handoff_session_invalid": "Сессия приложения истекла. Войдите снова.",
        "auth_handoff_expired": "Ссылка из приложения истекла. Войдите снова.",
        "account_linking_other_profile_required": "Войдите способом второго профиля, чтобы устранить причину. После этого вернитесь в основной профиль и повторите подключение способа входа.",
        "email_connected_relogin_required": "Email подключён к текущему профилю. Войдите снова любым сохранённым способом.",
        "yandex_connected_relogin_required": "Яндекс ID подключён к текущему профилю. Войдите снова любым сохранённым способом.",
        "vk_connected_relogin_required": "VK ID подключён к текущему профилю. Войдите снова любым сохранённым способом.",
        "sign_in_method_connected_relogin_required": "Способ входа подключён к текущему профилю. Войдите снова любым сохранённым способом.",
        "auth_session_invalid": "Сессия не найдена. Войдите снова.",
        "auth_session_expired": "Сессия истекла. Войдите снова.",
        "device_revoked": "Доступ этого устройства отозван. Войдите с доверенного браузера.",
        "workspace_required": "Вход пока не настроен на сервере. Обратитесь к администратору GRAF.",
        "provider_missing": "Этот способ входа не настроен.",
        "provider_disabled": "Этот способ входа выключен политикой кабинета.",
        "callback_denied": "Провайдер не подтвердил вход. Начните вход заново или выберите другой способ.",
        "callback_state_invalid": "Ссылка входа недействительна. Начните вход заново.",
        "callback_state_expired": "Ссылка входа истекла. Начните вход заново.",
        "callback_state_reused": "Эта ссылка входа уже использована. Начните вход заново.",
        "provider_unavailable": "Провайдер временно недоступен. Попробуйте снова или выберите другой способ входа.",
        "provider_future": "Этот способ входа появится позже. Сейчас используйте вход по email.",
        "auth_dependency_unavailable": "Сервис входа временно недоступен.",
        "email_invalid": "Введите корректный email.",
        "ambiguous_email_recovery_required": "Этот email связан с несколькими профилями. Вход по коду заблокирован, чтобы не открыть чужие встречи. Войдите ниже через уже подключённый Яндекс ID или VK: GRAF откроет настройки, где можно безопасно подключить email.",
        "ambiguous_email_recovery_unavailable": "Этот email связан с несколькими профилями, поэтому вход по коду заблокирован. Яндекс ID и VK сейчас недоступны — обратитесь к администратору GRAF, чтобы безопасно восстановить доступ.",
        "email_start_unavailable": "Не удалось отправить код. Проверьте email и попробуйте снова.",
        "email_delivery_unavailable": "Почтовая доставка временно недоступна. Попробуйте запросить код еще раз.",
        "auth_rate_limited": "Слишком много попыток. Попробуйте снова через несколько минут.",
        "email_code_wrong": "Проверьте цифры и попробуйте ещё раз. После трёх неверных попыток код блокируется.",
        "workspace_enrollment_required": "Регистрация в этом кабинете закрыта. Попросите администратора выслать приглашение.",
        "email_code_invalid": "Код не подошёл и больше не действует. Запросите новый код.",
        "email_code_expired": "Код истек. Запросите новый код.",
        "share_invitation_email_required": "Введите email, на который пришло приглашение.",
        "share_invitation_unavailable": "Приглашение больше недоступно. Запросите новое.",
        "share_recipient_mismatch": "Этот аккаунт не совпадает с приглашённым адресом. Войдите с другим аккаунтом.",
    }
    return messages.get(error, "Не удалось открыть сессию кабинета. Попробуйте войти снова.")
