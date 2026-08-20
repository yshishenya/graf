from __future__ import annotations

import inspect
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import UUID, uuid4

import pytest
from fastapi.responses import RedirectResponse
from fastapi.routing import APIRoute

from twobrain_rec_server.api.problems import ProblemDetail
from twobrain_rec_server.auth.account_closure import AccountCloseView
from twobrain_rec_server.auth.account_merge import MergeEntityCounts, build_merge_preview
from twobrain_rec_server.auth.context import AuthenticatedPrincipal, TenantScope
from twobrain_rec_server.auth.workspace_onboarding import WorkspaceAccessView
from twobrain_rec_server.cabinet.auth_rendering import (
    render_email_code_page,
    render_login_page,
    render_signup_page,
)
from twobrain_rec_server.cabinet.rendering import render_account_merge_page, render_settings_page
from twobrain_rec_server.cabinet.view_models import (
    AccountProfileView,
    AccountProviderView,
    AccountSettingsSurface,
)
from twobrain_rec_server.cabinet.web_routes import account_merge as account_merge_routes
from twobrain_rec_server.cabinet.web_routes import settings as settings_routes
from twobrain_rec_server.cabinet.web_routes.account_merge import router as account_merge_router
from twobrain_rec_server.cabinet.web_routes.auth import router as auth_router
from twobrain_rec_server.cabinet.web_routes.referrals import router as referrals_router
from twobrain_rec_server.cabinet.web_routes.settings import router
from twobrain_rec_server.cabinet.web_routes.spaces import router as spaces_router


def test_feature_159_login_copy_is_truthful_without_removing_explicit_signup_routes() -> None:
    login = render_login_page(workspace_id=UUID(int=1), providers=[])
    signup = render_signup_page(workspace_id=UUID(int=1), providers=[], mode="email")
    routes = {route.path for route in auth_router.routes if isinstance(route, APIRoute)}

    assert "Обычный вход не создаёт аккаунт автоматически." in login
    assert "Зарегистрироваться" not in login
    assert 'action="/sign-up/email/start"' in signup
    assert "/sign-up" in routes
    assert "/sign-up/email/start" in routes
    assert "/sign-up/email/verify" in routes


def test_account_close_routes_have_browser_and_desktop_variants_with_csrf_dependency() -> None:
    routes = {
        (route.path, tuple(route.methods or ()))
        for route in router.routes
        if isinstance(route, APIRoute)
    }
    assert ("/settings/account/close", ("POST",)) in routes
    assert ("/desktop/settings/account/close", ("POST",)) in routes
    assert ("/settings/account/close/cancel", ("POST",)) in routes
    assert ("/desktop/settings/account/close/cancel", ("POST",)) in routes


def test_account_security_has_bulk_session_and_device_controls_with_browser_variants() -> None:
    routes = {
        (route.path, tuple(route.methods or ()))
        for route in router.routes
        if isinstance(route, APIRoute)
    }
    assert {
        ("/settings/account/sessions/revoke-others", ("POST",)),
        ("/desktop/settings/account/sessions/revoke-others", ("POST",)),
        ("/settings/account/devices/revoke-others", ("POST",)),
        ("/desktop/settings/account/devices/revoke-others", ("POST",)),
    } <= routes


def test_account_link_and_merge_mutations_have_browser_desktop_parity_and_csrf() -> None:
    routes = {
        route.path: route
        for route in (*router.routes, *account_merge_router.routes)
        if isinstance(route, APIRoute)
    }
    expected = {
        "/settings/account/email-link/start",
        "/desktop/settings/account/email-link/start",
        "/settings/account/email-link/verify",
        "/desktop/settings/account/email-link/verify",
        "/settings/account/merge/{intent_id}/confirm",
        "/desktop/settings/account/merge/{intent_id}/confirm",
        "/settings/account/merge/{intent_id}/cancel",
        "/desktop/settings/account/merge/{intent_id}/cancel",
    }
    assert expected <= routes.keys()
    for path in expected:
        dependencies = {
            getattr(dependency.call, "__name__", "")
            for dependency in routes[path].dependant.dependencies
            if dependency.call is not None
        }
        assert "require_web_csrf" in dependencies


def test_account_merge_preview_routes_keep_browser_desktop_parity() -> None:
    routes = {
        route.path: route for route in account_merge_router.routes if isinstance(route, APIRoute)
    }
    assert {
        "/settings/account/merge/{intent_id}",
        "/desktop/settings/account/merge/{intent_id}",
    } <= routes.keys()


@pytest.mark.asyncio
async def test_account_merge_intent_lookup_rejects_missing_session_before_query() -> None:
    class QueryMustNotRun:
        async def scalar(self, _statement):
            raise AssertionError("sessionless intent lookup reached the database")

    principal = AuthenticatedPrincipal(
        user_id=UUID(int=2),
        organization_id=UUID(int=3),
        workspace_ids=frozenset({UUID(int=4)}),
        subject="sessionless",
    )
    tenant_scope = TenantScope(
        organization_id=principal.organization_id,
        workspace_id=UUID(int=4),
        user_id=principal.user_id,
        device_id=UUID(int=5),
    )

    with pytest.raises(ProblemDetail) as error:
        await account_merge_routes._owned_intent(
            QueryMustNotRun(),
            intent_id=UUID(int=1),
            principal=principal,
            tenant_scope=tenant_scope,
        )

    assert error.value.status == 404
    assert error.value.code == "merge_intent_not_found"


def test_account_merge_forms_keep_browser_and_desktop_return_routes() -> None:
    preview = build_merge_preview(
        survivor_user_id=UUID("00000000-0000-0000-0000-000000000002"),
        source_user_id=UUID("00000000-0000-0000-0000-000000000003"),
    )
    intent_id = UUID("00000000-0000-0000-0000-000000000001")

    browser = render_account_merge_page(preview, intent_id=intent_id, csrf_token="safe-csrf")
    desktop = render_account_merge_page(
        preview, intent_id=intent_id, embedded=True, csrf_token="safe-csrf"
    )

    assert f'action="/settings/account/merge/{intent_id}/confirm"' in browser
    assert f'action="/settings/account/merge/{intent_id}/cancel"' in browser
    assert f'action="/desktop/settings/account/merge/{intent_id}/confirm"' in desktop
    assert f'action="/desktop/settings/account/merge/{intent_id}/cancel"' in desktop


def test_desktop_email_link_code_page_keeps_verify_resend_and_back_on_desktop_routes() -> None:
    page = render_email_code_page(
        email="user@example.test",
        state_nonce="synthetic-state",
        next_path="/desktop/settings/account",
        flow="desktop_link",
        csrf_token="synthetic-csrf",
    )

    assert 'action="/desktop/settings/account/email-link/verify"' in page
    assert 'action="/desktop/settings/account/email-link/start"' in page
    assert 'href="/desktop/settings/account?next=%2Fdesktop%2Fsettings%2Faccount"' in page
    assert 'action="/settings/account/email-link/' not in page
    assert "data-embedded-code-panel" in page
    assert "data-embedded-code-panel" not in render_email_code_page(
        email="user@example.test",
        state_nonce="synthetic-state",
        next_path="/settings/account",
        flow="link",
        csrf_token="synthetic-csrf",
    )


@pytest.mark.parametrize("flow", ["link", "desktop_link"])
def test_email_link_ambiguity_copy_points_to_visible_settings_action(flow: str) -> None:
    page = render_email_code_page(
        email="user@example.test",
        state_nonce="synthetic-state",
        next_path="/desktop/settings/account" if flow == "desktop_link" else "/settings/account",
        error="ambiguous_email_recovery_required",
        flow=flow,
        csrf_token="synthetic-csrf",
    )

    assert "Вернитесь в настройки" in page
    assert "Выберите ниже" not in page


def test_email_link_callers_select_desktop_flow_for_every_local_render() -> None:
    source = "\n".join(
        (
            inspect.getsource(settings_routes._start_email_link),
            inspect.getsource(settings_routes._verify_email_link),
        )
    )

    assert source.count("render_email_code_page(") == 5
    assert source.count("flow=flow") == 5
    assert 'flow="link"' not in source


class _EmailLinkTransactionProbe:
    def __init__(self, events: list[str]) -> None:
        self.events = events

    async def commit(self) -> None:
        self.events.append("commit")

    async def rollback(self) -> None:
        self.events.append("rollback")


class _EmailLinkRequest:
    def __init__(self) -> None:
        self.url = SimpleNamespace(path="/desktop/settings/account/email-link/verify")

    async def form(self) -> dict[str, str]:
        return {
            "email": "user@example.test",
            "code": "123456",
            "state": "synthetic-state",
        }


async def test_email_link_verify_prepares_response_then_commits_once(monkeypatch) -> None:
    events: list[str] = []
    db = _EmailLinkTransactionProbe(events)

    async def consume(*_args, **_kwargs):
        assert _kwargs["csrf_token"] == "csrf"
        return SimpleNamespace(status="identity_linked", intent_id=None)

    def prepare_response(*args, **kwargs):
        events.append("response")
        return RedirectResponse(*args, **kwargs)

    monkeypatch.setattr(settings_routes, "consume_email_link_code", consume)
    monkeypatch.setattr(settings_routes, "RedirectResponse", prepare_response)
    monkeypatch.setattr(
        settings_routes, "_csrf_token_for_principal", lambda *_args, **_kwargs: "csrf"
    )
    monkeypatch.setattr(
        settings_routes,
        "build_request_browser_provider_context",
        lambda *_args, **_kwargs: {},
    )

    response = await settings_routes._verify_email_link(
        _EmailLinkRequest(),
        principal=SimpleNamespace(),
        tenant_scope=SimpleNamespace(workspace_id=UUID(int=1)),
        db=db,
        embedded=True,
    )

    assert response.headers["location"] == "/desktop/settings/account?provider_link=confirmed"
    assert events == ["response", "commit"]


async def test_email_link_verify_rolls_back_when_response_preparation_fails(monkeypatch) -> None:
    events: list[str] = []
    db = _EmailLinkTransactionProbe(events)

    async def consume(*_args, **_kwargs):
        return SimpleNamespace(status="identity_linked", intent_id=None)

    def fail_response(*_args, **_kwargs):
        raise RuntimeError("synthetic response failure")

    monkeypatch.setattr(settings_routes, "consume_email_link_code", consume)
    monkeypatch.setattr(settings_routes, "RedirectResponse", fail_response)
    monkeypatch.setattr(
        settings_routes, "_csrf_token_for_principal", lambda *_args, **_kwargs: "csrf"
    )

    with pytest.raises(RuntimeError, match="synthetic response failure"):
        await settings_routes._verify_email_link(
            _EmailLinkRequest(),
            principal=SimpleNamespace(),
            tenant_scope=SimpleNamespace(workspace_id=UUID(int=1)),
            db=db,
            embedded=True,
        )

    assert events == ["rollback"]


def test_email_link_verify_has_no_unreachable_auto_merge_completion_branch() -> None:
    source = inspect.getsource(settings_routes._verify_email_link)

    assert source.count("await db.commit()") == 1
    assert source.count("await db.rollback()") == 1
    assert "merge_completed" not in source


def test_destructive_link_and_merge_routes_receive_request_for_cookie_reauth() -> None:
    routes = {
        route.path: route
        for route in (*router.routes, *account_merge_router.routes)
        if isinstance(route, APIRoute)
    }
    for path in (
        "/settings/account/providers/{identity_id}/unlink",
        "/desktop/settings/account/providers/{identity_id}/unlink",
        "/settings/account/merge/{intent_id}/confirm",
        "/desktop/settings/account/merge/{intent_id}/confirm",
        "/settings/account/merge/{intent_id}/cancel",
        "/desktop/settings/account/merge/{intent_id}/cancel",
    ):
        assert "request" in inspect.signature(routes[path].endpoint).parameters


def test_merge_preview_copy_is_bounded_and_never_renders_account_secrets() -> None:
    page = render_account_merge_page(
        None,
        intent_id=UUID("00000000-0000-0000-0000-000000000001"),
        csrf_token="safe-csrf",
        error_message="Предпросмотр устарел.",
    )
    assert "Предпросмотр устарел." in page
    assert page.count("Предпросмотр устарел.") == 1
    assert "Подтверждение больше недоступно" in page
    assert "Вернуться к способам входа" in page
    assert "provider_subject" not in page
    content = page.split('id="cabinet-main"', 1)[-1].lower()
    assert "transcript" not in content
    assert "signed_url" not in page


def test_blocked_merge_prioritizes_recovery_without_burying_it_under_preview() -> None:
    survivor_user_id = UUID("00000000-0000-0000-0000-000000000002")
    source_user_id = UUID("00000000-0000-0000-0000-000000000003")
    preview = build_merge_preview(
        survivor_user_id=survivor_user_id,
        source_user_id=source_user_id,
        counts=MergeEntityCounts(meetings=2),
        role_conflict=True,
    )
    blockers = account_merge_routes.account_merge_blockers(
        preview.blocker_codes,
        intent_id=UUID("00000000-0000-0000-0000-000000000001"),
        embedded=False,
        support_email=None,
    )
    page = render_account_merge_page(
        preview,
        intent_id=UUID("00000000-0000-0000-0000-000000000001"),
        csrf_token="safe-csrf",
        blockers=blockers,
    )

    for copy in (
        "Что нужно сделать",
        "Email пока не подключён. Данные не изменены.",
        "Выберите доступное действие ниже.",
        "Роли профилей нельзя безопасно совместить автоматически",
        "Оставить профили раздельными",
    ):
        assert copy in page
    assert "устраните причину" not in page
    assert "Что изменится" not in page
    assert "После подключения потребуется войти снова" not in page
    assert str(survivor_user_id) not in page
    assert str(source_user_id) not in page


def test_empty_merge_preview_uses_one_quiet_data_summary() -> None:
    preview = build_merge_preview(survivor_user_id=uuid4(), source_user_id=uuid4())

    page = render_account_merge_page(preview, intent_id=uuid4(), csrf_token="safe-csrf")

    assert "Во втором профиле нет встреч, записей и файлов." in page
    assert "0 встреч" not in page


def test_reauth_required_replaces_confirm_with_csrf_protected_login_action() -> None:
    intent_id = UUID("00000000-0000-0000-0000-000000000001")
    preview = build_merge_preview(
        survivor_user_id=UUID("00000000-0000-0000-0000-000000000002"),
        source_user_id=UUID("00000000-0000-0000-0000-000000000003"),
    )

    page = render_account_merge_page(
        preview,
        intent_id=intent_id,
        csrf_token="safe-csrf",
        error_message="Нужно войти снова.",
        requires_reauth=True,
    )

    assert '<form action="/logout" method="post">' in page
    assert 'name="csrf_token" value="safe-csrf"' in page
    assert 'name="next" value="/login?next=/settings/account?provider_link=reauth_required"' in page
    assert ">Войти снова</button>" in page
    assert f'action="/settings/account/merge/{intent_id}/confirm"' not in page

    settings = render_settings_page(category="account", provider_link_result="reauth_required")
    assert "Подключите email ещё раз" in settings
    assert "прежнее подтверждение больше не действует" in settings


def test_merge_cancel_and_success_return_copy_are_outcomes_not_session_errors() -> None:
    settings = render_settings_page(category="account", provider_link_result="merge_cancelled")
    confirm_source = inspect.getsource(account_merge_routes._confirm)

    assert "Профили остались раздельными. Email не подключён к текущему профилю." in settings
    assert "error=email_connected_relogin_required" in confirm_source
    assert "auth_session_invalid" not in confirm_source
    assert "next=/settings/account" in confirm_source
    assert "next=/desktop/settings/account" in confirm_source


def test_expired_merge_copy_is_actionable_without_internal_preview_term() -> None:
    copy = account_merge_routes._error_copy("merge_intent_expired")

    assert copy == "Время подтверждения истекло. Данные не изменены; подключите email заново."
    assert "intent" not in copy.lower()
    assert "предпросмотр" not in copy.lower()


def test_account_security_renders_exact_bulk_and_per_session_actions() -> None:
    page = render_settings_page(category="account", csrf_token="safe-csrf")

    assert "Завершить остальные сеансы" in page
    assert "Выйти на всех устройствах" in page
    assert 'action="/settings/account/sessions/revoke-others"' in page
    assert 'action="/settings/account/devices/revoke-others"' in page


def test_workspace_switch_and_join_routes_are_csrf_protected_in_browser_and_desktop() -> None:
    routes = {route.path: route for route in spaces_router.routes if isinstance(route, APIRoute)}
    expected = {
        "/settings/spaces/{workspace_id}/activate",
        "/desktop/settings/spaces/{workspace_id}/activate",
        "/settings/join-offers/{offer_id}/{action}",
        "/desktop/settings/join-offers/{offer_id}/{action}",
    }
    assert expected <= routes.keys()
    for path in expected:
        dependency_names = {
            getattr(dependency.call, "__name__", "")
            for dependency in routes[path].dependant.dependencies
            if dependency.call is not None
        }
        assert "require_web_csrf" in dependency_names


def test_workspace_settings_copy_keeps_role_boundary_and_no_js_switch_fallback() -> None:
    page = render_settings_page(
        category="workspace",
        csrf_token="safe-csrf",
        workspace_spaces=(
            WorkspaceAccessView(
                id=UUID("00000000-0000-0000-0000-000000000001"),
                name="Команда",
                kind="team",
                role="member",
                active=False,
            ),
        ),
    )

    assert "Участник" in page
    assert "Присоединение добавит рабочее пространство, но не перенесёт личные встречи." in page
    assert "return_to_settings=true" in page
    assert 'method="post"' in page


def test_account_security_renders_bulk_result_as_persistent_status() -> None:
    page = render_settings_page(
        category="account",
        device_revoke_result="others_revoked",
        session_result="others_revoked",
    )

    assert "Доступ на остальных устройствах завершён. Текущее устройство остаётся активным." in page
    assert "Остальные сеансы завершены. Текущая сессия остаётся активной." in page


def test_account_ia_aliases_cover_profile_security_and_notifications() -> None:
    paths = {route.path for route in router.routes if isinstance(route, APIRoute)}
    assert {
        "/account/settings",
        "/account/profile",
        "/account/security",
        "/account/notifications",
        "/desktop/account/profile",
        "/desktop/account/security",
        "/desktop/account/notifications",
    } <= paths


def test_account_menu_has_the_six_canonical_actions_and_csrf_logout_fallback() -> None:
    page = render_settings_page(category="account", csrf_token="safe-csrf")

    for label in (
        "Профиль",
        "Безопасность",
        "Уведомления",
        "Тариф и оплата",
        "Пригласить друзей",
        "Выйти",
    ):
        assert label in page
    assert 'href="/billing"' in page
    assert 'href="/referrals"' in page
    assert '<form class="account-navigation__logout" method="post" action="/logout">' in page
    assert '<input type="hidden" name="csrf_token" value="safe-csrf">' in page
    assert '<input type="hidden" name="next" value="/login?next=/meetings">' in page


def test_embedded_account_menu_keeps_money_and_referrals_as_browser_handoffs() -> None:
    page = render_settings_page(embedded=True, category="account", csrf_token="embedded-csrf")

    assert 'href="/billing"' in page
    assert 'href="/referrals"' in page
    assert (
        '<form class="account-navigation__logout" method="post" action="/desktop/meetings">' in page
    )
    assert '<input type="hidden" name="next" value="/login?next=/desktop/meetings">' in page


def test_referrals_router_exposes_account_alias_without_duplicate_business_flow() -> None:
    paths = {route.path for route in referrals_router.routes if isinstance(route, APIRoute)}
    assert {"/referrals", "/account/referrals"} <= paths


def test_unverified_identity_surface_never_renders_an_unverified_email_as_login() -> None:
    page = render_settings_page(
        category="account",
        account_surface=AccountSettingsSurface(
            profile=AccountProfileView(display_name="Без имени", primary_email=None),
            providers=(
                AccountProviderView(
                    provider="email",
                    label="Email",
                    status_label="Проверка не завершена",
                    primary=True,
                    connected_at=None,
                ),
            ),
        ),
    )

    assert "Подтверждённый email не раскрывается в этой сессии." in page
    assert "Проверка не завершена" in page
    assert "Подключённых способов входа пока нет." not in page
    assert (
        "<input"
        not in page.split("Подключённые способы входа", 1)[-1].split("Для безопасности", 1)[0]
    )


def test_account_page_explains_cooling_window_and_no_js_confirmation() -> None:
    page = render_settings_page(category="account")
    assert "Закрытие аккаунта" in page
    assert "7-дневный период отмены" in page
    assert 'name="confirm_close"' in page
    assert 'method="post"' in page
    assert "/settings/account/close" in page


def test_account_page_projects_scheduled_close_and_cancel_action() -> None:
    close = AccountCloseView(
        state="scheduled",
        requested_at=datetime.now(UTC),
        finalize_at=datetime.now(UTC) + timedelta(days=7),
        policy_version="account-close-v1",
        can_cancel=True,
    )
    page = render_settings_page(
        category="account",
        account_surface=AccountSettingsSurface(account_close=close),
    )
    assert "Закрытие запланировано на" in page
    assert "Будущие списания отключены" in page
    assert "Отменить запланированное закрытие" in page
    assert 'name="confirm_close"' not in page


def test_account_and_notifications_keep_no_js_and_recovery_safe_copy() -> None:
    account = render_settings_page(category="account", csrf_token="safe-csrf")
    notifications = render_settings_page(category="notifications", csrf_token="safe-csrf")

    assert "последний подтверждённый способ входа" in account
    assert "<noscript>" in account
    assert 'method="post"' in account
    assert "<noscript>" in notifications
    assert 'method="post"' in notifications
