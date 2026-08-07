from __future__ import annotations

from datetime import UTC, datetime, timedelta

from fastapi.routing import APIRoute

from twobrain_rec_server.auth.account_closure import AccountCloseView
from twobrain_rec_server.cabinet.rendering import render_settings_page
from twobrain_rec_server.cabinet.view_models import AccountSettingsSurface
from twobrain_rec_server.cabinet.web_routes.settings import router


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


def test_account_ia_aliases_cover_profile_security_and_notifications() -> None:
    paths = {
        route.path
        for route in router.routes
        if isinstance(route, APIRoute)
    }
    assert {
        "/account/profile",
        "/account/security",
        "/account/notifications",
        "/desktop/account/profile",
        "/desktop/account/security",
        "/desktop/account/notifications",
    } <= paths


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
