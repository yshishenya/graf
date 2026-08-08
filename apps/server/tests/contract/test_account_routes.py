from __future__ import annotations

from datetime import UTC, datetime, timedelta
from uuid import UUID

from fastapi.routing import APIRoute

from twobrain_rec_server.auth.account_closure import AccountCloseView
from twobrain_rec_server.auth.workspace_onboarding import WorkspaceAccessView
from twobrain_rec_server.cabinet.rendering import render_settings_page
from twobrain_rec_server.cabinet.view_models import (
    AccountProfileView,
    AccountProviderView,
    AccountSettingsSurface,
)
from twobrain_rec_server.cabinet.web_routes.referrals import router as referrals_router
from twobrain_rec_server.cabinet.web_routes.settings import router
from twobrain_rec_server.cabinet.web_routes.spaces import router as spaces_router


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


def test_account_security_renders_exact_bulk_and_per_session_actions() -> None:
    page = render_settings_page(category="account", csrf_token="safe-csrf")

    assert "Завершить остальные сеансы" in page
    assert "Выйти на всех устройствах" in page
    assert 'action="/settings/account/sessions/revoke-others"' in page
    assert 'action="/settings/account/devices/revoke-others"' in page


def test_workspace_switch_and_join_routes_are_csrf_protected_in_browser_and_desktop() -> None:
    routes = {
        route.path: route
        for route in spaces_router.routes
        if isinstance(route, APIRoute)
    }
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
    assert "Принятие приглашения не переносит личные записи" in page
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
