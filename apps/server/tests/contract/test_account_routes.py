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
from twobrain_rec_server.auth.account_merge import (
    AccountMergeError,
    MergeEntityCounts,
    build_merge_preview,
)
from twobrain_rec_server.auth.context import AuthenticatedPrincipal, TenantScope
from twobrain_rec_server.auth.workspace_onboarding import WorkspaceAccessView
from twobrain_rec_server.cabinet.auth_rendering import (
    render_email_code_page,
    render_login_page,
    render_signup_page,
)
from twobrain_rec_server.cabinet.rendering import (
    account_merge_provider_label,
    render_account_merge_page,
    render_settings_page,
)
from twobrain_rec_server.cabinet.view_models import (
    AccountProfileView,
    AccountProviderView,
    AccountSettingsSurface,
    ProviderLinkSettingsSurface,
)
from twobrain_rec_server.cabinet.web_routes import account_merge as account_merge_routes
from twobrain_rec_server.cabinet.web_routes import provider_links as provider_link_routes
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
@pytest.mark.parametrize(
    ("path", "expected"),
    (
        (
            "/settings/account/merge/00000000-0000-0000-0000-000000000001",
            "/settings/account?provider_link=provider_link_unavailable",
        ),
        (
            "/desktop/settings/account/merge/00000000-0000-0000-0000-000000000001",
            "/desktop/settings/account?provider_link=provider_link_unavailable",
        ),
    ),
)
async def test_merge_page_missing_store_redirects_to_first_party_recovery(
    path: str, expected: str
) -> None:
    response = await account_merge_routes.account_merge_page(
        SimpleNamespace(url=SimpleNamespace(path=path)),
        UUID(int=1),
        tenant_scope=SimpleNamespace(),
        principal=SimpleNamespace(),
        db=None,
    )

    assert response.status_code == 303
    assert response.headers["location"] == expected


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("path", "expected"),
    (
        (
            "/settings/provider-links/00000000-0000-0000-0000-000000000001",
            "/settings/account?provider_link=provider_link_unavailable",
        ),
        (
            "/desktop/settings/provider-links/00000000-0000-0000-0000-000000000001",
            "/desktop/settings/account?provider_link=provider_link_unavailable",
        ),
    ),
)
async def test_provider_link_page_missing_store_redirects_to_first_party_recovery(
    path: str, expected: str
) -> None:
    response = await provider_link_routes.provider_link_settings_page(
        SimpleNamespace(url=SimpleNamespace(path=path)),
        UUID(int=1),
        tenant_scope=SimpleNamespace(),
        principal=SimpleNamespace(),
        db=None,
    )

    assert response.status_code == 303
    assert response.headers["location"] == expected


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("status", "expected_provider"),
    (("initiated", None), ("confirmed", None), ("expired", "yandex")),
)
async def test_provider_link_route_only_allows_restart_for_terminal_recovery_states(
    monkeypatch, status: str, expected_provider: str | None
) -> None:
    surface = ProviderLinkSettingsSurface(
        link_state_id=UUID(int=1),
        provider="yandex",
        provider_label="Яндекс ID",
        status=status,
        status_label="Состояние",
        can_confirm=False,
    )
    captured: dict[str, object] = {}

    async def load_surface(*_args, **_kwargs):
        return surface

    def render_surface(rendered_surface, **_kwargs):
        captured["provider"] = rendered_surface.provider
        return "<main>ok</main>"

    monkeypatch.setattr(provider_link_routes, "get_provider_link_settings_surface", load_surface)
    monkeypatch.setattr(provider_link_routes, "render_provider_link_settings_page", render_surface)
    monkeypatch.setattr(provider_link_routes, "_csrf_token_for_principal", lambda *_a, **_k: "csrf")
    monkeypatch.setattr(
        provider_link_routes,
        "build_request_browser_provider_context",
        lambda *_a, **_k: {},
    )

    response = await provider_link_routes.provider_link_settings_page(
        SimpleNamespace(url=SimpleNamespace(path="/settings/provider-links/1")),
        UUID(int=1),
        tenant_scope=SimpleNamespace(),
        principal=SimpleNamespace(),
        db=SimpleNamespace(),
    )

    assert response.status_code == 200
    assert captured["provider"] == expected_provider


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


@pytest.mark.parametrize(
    "error", ["email_invalid", "auth_rate_limited", "email_delivery_unavailable"]
)
def test_email_link_start_errors_do_not_render_a_dead_code_form(error: str) -> None:
    page = render_email_code_page(
        email="" if error == "email_invalid" else "user@example.test",
        state_nonce="failed-state" if error == "email_delivery_unavailable" else "",
        next_path="/settings/account",
        error=error,
        flow="link",
        csrf_token="synthetic-csrf",
    )

    assert 'action="/settings/account/email-link/verify"' not in page
    assert 'action="/settings/account/email-link/start"' in page
    assert "Получить новый код" in page
    assert "мы отправили 6-значный код" not in page
    if error == "email_invalid":
        assert 'name="email" type="email"' in page


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


class _FormMustNotRunRequest:
    async def form(self):
        raise AssertionError("stale email-link request reached form processing")


@pytest.mark.asyncio
@pytest.mark.parametrize(
    ("handler", "embedded", "expected"),
    (
        (
            settings_routes._start_email_link,
            False,
            "/settings/account?provider_link=provider_link_unavailable",
        ),
        (
            settings_routes._start_email_link,
            True,
            "/desktop/settings/account?provider_link=provider_link_unavailable",
        ),
        (
            settings_routes._verify_email_link,
            False,
            "/settings/account?provider_link=provider_link_unavailable",
        ),
        (
            settings_routes._verify_email_link,
            True,
            "/desktop/settings/account?provider_link=provider_link_unavailable",
        ),
    ),
)
async def test_email_link_missing_store_redirects_to_first_party_recovery(
    handler, embedded: bool, expected: str
) -> None:
    response = await handler(
        _FormMustNotRunRequest(),
        principal=SimpleNamespace(),
        tenant_scope=SimpleNamespace(),
        db=None,
        embedded=embedded,
    )

    assert response.status_code == 303
    assert response.headers["location"] == expected


@pytest.mark.asyncio
@pytest.mark.parametrize("embedded", (False, True))
async def test_email_link_stale_session_redirects_before_reusing_old_proof(
    embedded: bool,
) -> None:
    expected = (
        "/desktop/settings/account?provider_link=reauth_required"
        if embedded
        else "/settings/account?provider_link=reauth_required"
    )
    principal = SimpleNamespace(auth_via_session=False, session_id=None)

    for handler in (settings_routes._start_email_link, settings_routes._verify_email_link):
        response = await handler(
            _FormMustNotRunRequest(),
            principal=principal,
            tenant_scope=SimpleNamespace(),
            db=SimpleNamespace(),
            embedded=embedded,
        )
        assert response.status_code == 303
        assert response.headers["location"] == expected


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
        principal=SimpleNamespace(auth_via_session=True, session_id=UUID(int=1)),
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
            principal=SimpleNamespace(auth_via_session=True, session_id=UUID(int=1)),
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
        provider_label="email",
    )
    page = render_account_merge_page(
        preview,
        intent_id=UUID("00000000-0000-0000-0000-000000000001"),
        csrf_token="safe-csrf",
        blockers=blockers,
        provider_id="email",
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
    assert page.count("data-account-linking-primary") == 1
    assert 'class="button primary"' in page
    assert 'data-account-linking-secondary' in page
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
        provider_id="email",
    )

    assert '<form action="/logout" method="post">' in page
    assert 'name="csrf_token" value="safe-csrf"' in page
    assert 'name="next" value="/login?next=/settings/account?provider_link=reauth_required"' in page
    assert ">Войти снова</button>" in page
    assert f'action="/settings/account/merge/{intent_id}/confirm"' not in page

    settings = render_settings_page(
        category="account",
        csrf_token="safe-csrf",
        provider_link_result="reauth_required",
    )
    assert "Войдите снова, затем повторите подключение" in settings
    assert '<form action="/logout" method="post">' in settings
    assert 'name="next" value="/login?next=/settings/account"' in settings


def test_provider_unlink_outcomes_are_first_party_and_actionable() -> None:
    recovery = render_settings_page(
        category="account",
        provider_unlink_result="recovery_path_required",
    )
    reauth = render_settings_page(
        embedded=True,
        category="account",
        csrf_token="safe-csrf",
        provider_unlink_result="reauth_required",
    )

    assert "Сначала подключите другой способ входа" in recovery
    assert "другого подтверждённого способа восстановления" in recovery
    assert '<form action="/desktop/meetings" method="post">' in reauth
    assert 'name="next" value="/login?next=/desktop/settings/account"' in reauth


def test_provider_unlink_revocation_keeps_exact_request_context_and_direct_relogin() -> None:
    unlink_source = inspect.getsource(settings_routes._unlink_account_provider)
    action_source = inspect.getsource(settings_routes._unlink_provider_action)

    assert "principal.workspace_ids" in unlink_source
    assert "AuthSession.provider == identity.provider" in unlink_source
    assert "AuthSession.status == \"active\"" in unlink_source
    assert "await db.flush()" in unlink_source
    assert "await apply_tenant_scope(db, tenant_scope)" in unlink_source
    assert 'binding.device_state = "blocked"' in unlink_source
    assert 'binding.revocation_reason = "provider_unlinked"' in unlink_source
    assert 'metadata={"count": revoked_count, "provider": identity.provider}' in unlink_source
    assert "MaintenanceTenantContext" not in unlink_source
    assert '"/login?next=/desktop/settings/account&error=auth_session_invalid"' in action_source
    assert '"/login?next=/settings/account&error=auth_session_invalid"' in action_source
    assert "response.delete_cookie(" in action_source


def test_merge_cancel_and_success_return_copy_are_outcomes_not_session_errors() -> None:
    settings = render_settings_page(category="account", provider_link_result="merge_cancelled")
    confirm_source = inspect.getsource(account_merge_routes._confirm)

    assert "Профили остались раздельными. Способ входа не подключён к текущему профилю." in settings
    assert "_relogin_result(provider_id)" in confirm_source
    assert "auth_session_invalid" not in confirm_source
    assert "next=/settings/account" in confirm_source
    assert "next=/desktop/settings/account" in confirm_source


def test_expired_merge_copy_is_actionable_without_internal_preview_term() -> None:
    copy = account_merge_routes._error_copy("merge_intent_expired", provider_label="email")

    assert copy == "Время подтверждения истекло. Данные не изменены; подключите email заново."
    assert "intent" not in copy.lower()
    assert "предпросмотр" not in copy.lower()


def test_stale_provider_proof_replaces_old_confirm_with_fresh_provider_start() -> None:
    intent_id = UUID("00000000-0000-0000-0000-000000000001")
    preview = build_merge_preview(survivor_user_id=uuid4(), source_user_id=uuid4())

    page = render_account_merge_page(
        preview,
        intent_id=intent_id,
        csrf_token="safe-csrf",
        error_message="Подтверждение больше не действует.",
        requires_restart=True,
        provider_id="yandex",
    )

    assert '<form action="/settings/provider-links/yandex/start" method="post">' in page
    assert "Подключить Яндекс ID заново" in page
    assert f'action="/settings/account/merge/{intent_id}/confirm"' not in page
    assert 'name="csrf_token" value="safe-csrf"' in page


def test_restart_errors_remain_actionable_before_intent_becomes_terminal() -> None:
    assert {
        "proof_required",
        "merge_preview_stale",
        "merge_intent_expired",
        "merge_restart_required",
    } == account_merge_routes.ACCOUNT_MERGE_RESTART_ERRORS


@pytest.mark.asyncio
async def test_stale_merge_get_hides_confirm_and_offers_fresh_provider_start(
    monkeypatch,
) -> None:
    captured: dict[str, object] = {}
    intent = SimpleNamespace(id=UUID(int=1))

    async def owned_intent(*_args, **_kwargs):
        return intent

    async def intent_provider_id(*_args, **_kwargs):
        return "yandex"

    async def stale_preview(*_args, **_kwargs):
        raise AccountMergeError("merge_preview_stale")

    def render(preview, **kwargs):
        captured["preview"] = preview
        captured.update(kwargs)
        return "<main>recovery</main>"

    monkeypatch.setattr(account_merge_routes, "_owned_intent", owned_intent)
    monkeypatch.setattr(account_merge_routes, "_intent_provider_id", intent_provider_id)
    monkeypatch.setattr(account_merge_routes, "preview_merge_intent", stale_preview)
    monkeypatch.setattr(account_merge_routes, "render_account_merge_page", render)
    monkeypatch.setattr(
        account_merge_routes, "_csrf_token_for_principal", lambda *_args, **_kwargs: "csrf"
    )
    monkeypatch.setattr(
        account_merge_routes,
        "build_request_browser_provider_context",
        lambda *_args, **_kwargs: {},
    )

    response = await account_merge_routes.account_merge_page(
        SimpleNamespace(
            url=SimpleNamespace(path="/settings/account/merge/1"),
            query_params={},
            app=SimpleNamespace(
                state=SimpleNamespace(
                    settings=SimpleNamespace(billing_support_email=None)
                )
            ),
        ),
        intent.id,
        tenant_scope=SimpleNamespace(),
        principal=SimpleNamespace(),
        db=SimpleNamespace(),
    )

    assert response.status_code == 200
    assert captured["preview"] is None
    assert captured["requires_restart"] is True
    assert captured["provider_id"] == "yandex"
    assert "Состояние профилей изменилось" in str(captured["error_message"])


@pytest.mark.asyncio
async def test_email_merge_copy_uses_email_proof_origin_without_identity_lookup() -> None:
    class IdentityLookupMustNotRun:
        async def get(self, *_args, **_kwargs):
            raise AssertionError("email proof origin reached identity provider lookup")

    provider = await account_merge_routes._intent_provider_id(
        IdentityLookupMustNotRun(),
        SimpleNamespace(
            provider_link_state_id=None,
            source_external_identity_id=uuid4(),
            source_user_id=uuid4(),
        ),
    )

    assert provider == "email_link"
    assert account_merge_provider_label(provider) == "Email"


def test_stale_email_proof_returns_to_visible_email_form_without_old_confirm() -> None:
    intent_id = uuid4()
    preview = build_merge_preview(survivor_user_id=uuid4(), source_user_id=uuid4())

    page = render_account_merge_page(
        preview,
        intent_id=intent_id,
        csrf_token="safe-csrf",
        error_message="Подтверждение больше не действует.",
        requires_restart=True,
        provider_id="email",
    )

    assert '<form action="/settings/account/email-link/start" method="post">' in page
    assert ">Получить новый код</button>" in page
    assert 'name="email"' in page
    assert 'name="csrf_token" value="safe-csrf"' in page
    assert f'action="/settings/account/merge/{intent_id}/confirm"' not in page


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
