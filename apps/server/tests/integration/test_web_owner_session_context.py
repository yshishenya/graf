from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta
from html import unescape
from urllib.parse import parse_qs, urlsplit
from uuid import UUID, uuid4

import pytest
from cryptography.fernet import Fernet
from sqlalchemy import select

from tests.fakes.auth_contexts import (
    AUTH_BOOTSTRAP_WORKSPACE_ID,
    DEVICE_ID,
    ORG_ID,
    PERSONAL_WORKSPACE_ID,
    USER_ID,
    WORKSPACE_ID,
)
from tests.fakes.auth_providers import fake_provider_map
from tests.fixtures.cabinet import seed_cabinet_meetings
from twobrain_rec_server.api.auth import BROWSER_AUTH_STATE_COOKIE_NAME
from twobrain_rec_server.auth import email_delivery
from twobrain_rec_server.auth.browser_handoff import DESKTOP_BILLING_HANDOFF_PROVIDER
from twobrain_rec_server.auth.csrf import issue_csrf_token
from twobrain_rec_server.auth.dependencies import AUTH_SESSION_COOKIE_NAME
from twobrain_rec_server.auth.sessions import hash_token
from twobrain_rec_server.auth.workspace_onboarding import ensure_personal_workspace
from twobrain_rec_server.cabinet.web_routes import auth as auth_routes
from twobrain_rec_server.cabinet.web_routes import auth_email_flow as auth_email_flow_module
from twobrain_rec_server.cabinet.web_routes import billing as billing_routes
from twobrain_rec_server.db.models import (
    AccountMergeIntent,
    AuthAuditEvent,
    AuthCallbackState,
    AuthSession,
    AuthSessionDeviceBinding,
    BillingInvoice,
    BillingOperation,
    ExternalIdentity,
    RegisteredDevice,
    UserIdentity,
    Workspace,
    WorkspaceAuthPolicy,
    WorkspaceMembership,
    WorkspaceSubscription,
)
from twobrain_rec_server.db.tenant_context import WorkspaceAuthContext, apply_tenant_context

OWNER_REVIEW_TEST_TOKEN = "owner-review-session-cookie-token"
BROWSER_OWNER_EMAIL = "owner@example.test"


async def _link_owner_email_identity(client) -> None:
    async with client.app_state["sessionmaker"]() as db:
        db.add(
            ExternalIdentity(
                user_id=USER_ID,
                provider="email",
                provider_subject=BROWSER_OWNER_EMAIL,
                provider_username=BROWSER_OWNER_EMAIL,
                email=BROWSER_OWNER_EMAIL,
                display_name="Browser Owner",
                is_verified=True,
            )
        )
        await db.commit()


def _login_owner_and_get_settings_csrf(client) -> str:
    client.portal.call(_link_owner_email_identity, client)
    start = client.post(
        "/login/email/start",
        data={"email": BROWSER_OWNER_EMAIL, "next": "/meetings"},
    )
    state = re.search(r'name="state" value="([^"]+)"', start.text)
    code = re.search(r"Код для локальной проверки: <strong>(\d{6})</strong>", start.text)
    assert state is not None and code is not None
    _bind_email_auth_attempt_cookie(client, start, state_nonce=state.group(1))
    callback = client.post(
        "/login/email/verify",
        data={
            "email": BROWSER_OWNER_EMAIL,
            "code": code.group(1),
            "state": state.group(1),
            "next": "/meetings",
        },
        follow_redirects=False,
    )
    assert callback.status_code == 303
    client.cookies.set(
        AUTH_SESSION_COOKIE_NAME,
        callback.cookies.get(AUTH_SESSION_COOKIE_NAME),
    )
    settings = client.get("/settings/account")
    csrf = re.search(r'name="csrf_token" value="([^"]+)"', settings.text)
    assert csrf is not None
    return csrf.group(1)


def _bind_email_auth_attempt_cookie(client, response, *, state_nonce: str) -> tuple[str, str]:
    cookie_name = auth_email_flow_module._email_auth_browser_cookie_name(
        state_nonce=state_nonce,
        secure=True,
    )
    browser_nonce = response.cookies.get(cookie_name)
    assert browser_nonce is not None
    # TestClient uses HTTP and correctly withholds Secure cookies. Re-add only
    # this synthetic cookie without transport attributes so the next request
    # can exercise the server-side production cookie contract.
    client.cookies.set(cookie_name, browser_nonce, domain="testserver.local", path="/")
    return cookie_name, browser_nonce


def _start_email_link(client, *, email: str, csrf_token: str) -> tuple[str, str, str]:
    response = client.post(
        "/settings/account/email-link/start",
        data={"email": email, "csrf_token": csrf_token},
    )
    state = re.search(r'name="state" value="([^"]+)"', response.text)
    code = re.search(r"Код для локальной проверки: <strong>(\d{6})</strong>", response.text)
    csrf = re.search(r'name="csrf_token" value="([^"]+)"', response.text)
    assert state is not None and code is not None and csrf is not None
    return state.group(1), code.group(1), csrf.group(1)


async def _set_workspace_yandex_policy(client, enabled: bool) -> None:
    async with client.app_state["sessionmaker"]() as db:
        policy = await db.scalar(
            select(WorkspaceAuthPolicy).where(
                WorkspaceAuthPolicy.workspace_id == AUTH_BOOTSTRAP_WORKSPACE_ID
            )
        )
        if policy is None:
            policy = WorkspaceAuthPolicy(workspace_id=AUTH_BOOTSTRAP_WORKSPACE_ID)
            db.add(policy)
        policy.allow_yandex = enabled
        await db.commit()


async def _set_workspace_vk_policy(client, enabled: bool) -> None:
    async with client.app_state["sessionmaker"]() as db:
        policy = await db.scalar(
            select(WorkspaceAuthPolicy).where(
                WorkspaceAuthPolicy.workspace_id == AUTH_BOOTSTRAP_WORKSPACE_ID
            )
        )
        if policy is None:
            policy = WorkspaceAuthPolicy(workspace_id=AUTH_BOOTSTRAP_WORKSPACE_ID)
            db.add(policy)
        policy.allow_vk = enabled
        await db.commit()


async def _set_workspace_self_enrollment_policy(client, enabled: bool) -> None:
    async with client.app_state["sessionmaker"]() as db:
        policy = await db.scalar(
            select(WorkspaceAuthPolicy).where(
                WorkspaceAuthPolicy.workspace_id == AUTH_BOOTSTRAP_WORKSPACE_ID
            )
        )
        if policy is None:
            policy = WorkspaceAuthPolicy(workspace_id=AUTH_BOOTSTRAP_WORKSPACE_ID)
            db.add(policy)
        policy.allow_provider_self_enrollment = enabled
        await db.commit()


async def _link_owner_yandex_identity(client, *, subject: str) -> None:
    async with client.app_state["sessionmaker"]() as db:
        db.add(
            ExternalIdentity(
                user_id=USER_ID,
                provider="yandex",
                provider_subject=subject,
                provider_username=subject,
                display_name="Browser Yandex Owner",
                is_verified=True,
            )
        )
        await db.commit()


def _patch_browser_provider_callbacks(monkeypatch) -> None:
    provider_map = fake_provider_map()
    monkeypatch.setattr(
        "twobrain_rec_server.api.auth.build_provider_registry", lambda: provider_map
    )
    monkeypatch.setattr(
        "twobrain_rec_server.auth.callbacks.get_provider_adapter",
        lambda provider: provider_map[provider],
    )
    monkeypatch.setattr(
        "twobrain_rec_server.cabinet.web_routes.auth.build_provider_registry",
        lambda: provider_map,
    )
    monkeypatch.setattr(
        "twobrain_rec_server.cabinet.web_routes.auth.get_provider_adapter",
        lambda provider: provider_map[provider],
    )


def _bind_browser_callback_cookie(client, response) -> None:
    nonce_match = re.search(
        rf"{re.escape(BROWSER_AUTH_STATE_COOKIE_NAME)}=([^;]+)",
        response.headers["set-cookie"],
    )
    assert nonce_match is not None
    client.cookies.clear()
    client.cookies.set(BROWSER_AUTH_STATE_COOKIE_NAME, nonce_match.group(1))


async def _seed_owner_review_session(
    client,
    *,
    token: str = OWNER_REVIEW_TEST_TOKEN,
    expires_delta: timedelta = timedelta(minutes=15),
    status: str = "active",
    device_state: str = "trusted",
) -> AuthSession:
    async with client.app_state["sessionmaker"]() as db:
        session = AuthSession(
            id=uuid4(),
            user_id=USER_ID,
            workspace_id=WORKSPACE_ID,
            device_id=DEVICE_ID,
            provider="owner_review_test",
            session_token_hash=hash_token(token),
            status=status,
            issued_at=datetime.now(UTC) - timedelta(minutes=1),
            expires_at=datetime.now(UTC) + expires_delta,
            claims_fingerprint="feature-036-owner-review",
        )
        db.add(session)
        await db.flush()
        db.add(
            AuthSessionDeviceBinding(
                auth_session_id=session.id,
                registered_device_id=DEVICE_ID,
                device_state=device_state,
            )
        )
        await db.commit()
        return session


def test_web_owner_session_scaffold_defines_cookie_name_contract() -> None:
    assert AUTH_SESSION_COOKIE_NAME == "__Host-twobrain_rec_owner_session"


def test_revoked_workspace_session_is_rejected_before_direct_auth_mutation(client) -> None:
    async def seed() -> tuple[str, UUID]:
        async with client.app_state["sessionmaker"]() as db:
            session = await _seed_owner_review_session(client, token="revoked-direct-auth-session")
            membership = await db.get(
                WorkspaceMembership,
                {"workspace_id": WORKSPACE_ID, "user_id": USER_ID},
            )
            assert membership is not None
            membership.status = "revoked"
            await db.commit()
            return "revoked-direct-auth-session", session.id

    token, session_id = client.portal.call(seed)
    response = client.post(
        "/api/v1/auth/devices/register",
        headers={"X-Auth-Session": token, "X-Workspace-Id": str(WORKSPACE_ID)},
        json={
            "device_public_id": "revoked-session-must-not-register",
            "platform": "macos",
            "client_version": "2026.08.15.1",
        },
    )

    assert response.status_code == 403
    assert response.json()["code"] == "workspace_scope_denied"

    async def read_result() -> tuple[str, bool]:
        async with client.app_state["sessionmaker"]() as db:
            session = await db.get(AuthSession, session_id)
            device = await db.scalar(
                select(RegisteredDevice).where(
                    RegisteredDevice.device_public_id == "revoked-session-must-not-register"
                )
            )
            assert session is not None
            return session.status, device is not None

    assert client.portal.call(read_result) == ("revoked", False)


def test_browser_icon_probe_routes_do_not_pollute_cabinet_with_404(client) -> None:
    for path in ("/favicon.ico", "/apple-touch-icon.png", "/apple-touch-icon-precomposed.png"):
        response = client.get(path)

        assert response.status_code == 200
        assert response.content


def test_meetings_page_accepts_owner_session_cookie_without_legacy_headers(client) -> None:
    seed_cabinet_meetings(client)
    client.portal.call(_seed_owner_review_session, client)
    client.cookies.set(AUTH_SESSION_COOKIE_NAME, OWNER_REVIEW_TEST_TOKEN)

    response = client.get("/meetings")

    assert response.status_code == 200
    assert "Мои встречи" in response.text
    assert "missing_auth_context" not in response.text


def test_meetings_page_exposes_logout_form_with_session_csrf(client) -> None:
    seed_cabinet_meetings(client)
    client.portal.call(_seed_owner_review_session, client)
    client.cookies.set(AUTH_SESSION_COOKIE_NAME, OWNER_REVIEW_TEST_TOKEN)

    response = client.get("/meetings")

    assert response.status_code == 200
    assert 'class="sidebar-logout"' in response.text
    assert 'action="/logout"' in response.text
    assert 'name="csrf_token"' in response.text
    assert 'name="next" value="/login?next=/meetings"' in response.text
    assert "Выйти" in response.text


def test_browser_logout_revokes_session_clears_cookie_and_redirects_to_login(client) -> None:
    seed_cabinet_meetings(client)
    session = client.portal.call(_seed_owner_review_session, client)
    csrf_token = issue_csrf_token(
        session_id=session.id,
        secret=str(client.app.state.web_csrf_secret),
    )
    client.cookies.set(AUTH_SESSION_COOKIE_NAME, OWNER_REVIEW_TEST_TOKEN)

    response = client.post(
        "/logout",
        data={"csrf_token": csrf_token, "next": "/login?next=/meetings"},
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert response.headers["location"] == "/login?next=/meetings"
    set_cookie = response.headers["set-cookie"]
    assert f"{AUTH_SESSION_COOKIE_NAME}=" in set_cookie
    assert "Max-Age=0" in set_cookie
    assert "HttpOnly" in set_cookie
    assert "Secure" in set_cookie

    async def read_logout_state() -> tuple[str, list[AuthAuditEvent]]:
        async with client.app_state["sessionmaker"]() as db:
            auth_session = await db.get(AuthSession, session.id)
            assert auth_session is not None
            events = list(
                (
                    await db.scalars(
                        select(AuthAuditEvent).where(AuthAuditEvent.event_type == "browser_logout")
                    )
                ).all()
            )
            return auth_session.status, events

    status, events = client.portal.call(read_logout_state)
    assert status == "revoked"
    assert len(events) == 1
    assert events[0].user_id == USER_ID

    client.cookies.set(AUTH_SESSION_COOKIE_NAME, OWNER_REVIEW_TEST_TOKEN)
    blocked = client.get("/meetings")
    assert blocked.status_code == 401
    assert blocked.json()["code"] == "auth_session_invalid"


def test_desktop_meetings_page_accepts_owner_session_cookie_without_legacy_headers(client) -> None:
    seed_cabinet_meetings(client)
    client.portal.call(_seed_owner_review_session, client)
    client.cookies.set(AUTH_SESSION_COOKIE_NAME, OWNER_REVIEW_TEST_TOKEN)

    response = client.get("/desktop/meetings")

    assert response.status_code == 200
    assert "desktop-embedded" in response.text
    assert 'class="sidebar-logout"' in response.text
    assert 'action="/desktop/meetings"' in response.text
    assert 'name="next" value="/login?next=/desktop/meetings"' in response.text
    assert "Мои встречи" in response.text
    assert "missing_auth_context" not in response.text


def test_embedded_logout_uses_allowed_meetings_post_route(client) -> None:
    seed_cabinet_meetings(client)
    session = client.portal.call(_seed_owner_review_session, client)
    csrf_token = issue_csrf_token(
        session_id=session.id,
        secret=str(client.app.state.web_csrf_secret),
    )
    client.cookies.set(AUTH_SESSION_COOKIE_NAME, OWNER_REVIEW_TEST_TOKEN)

    response = client.post(
        "/desktop/meetings",
        data={"csrf_token": csrf_token, "next": "/login?next=/desktop/meetings"},
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert response.headers["location"] == "/login?next=/desktop/meetings"
    set_cookie = response.headers["set-cookie"]
    assert f"{AUTH_SESSION_COOKIE_NAME}=" in set_cookie
    assert "Max-Age=0" in set_cookie
    assert "HttpOnly" in set_cookie
    assert "Secure" in set_cookie

    async def read_logout_state() -> tuple[str, list[AuthAuditEvent]]:
        async with client.app_state["sessionmaker"]() as db:
            auth_session = await db.get(AuthSession, session.id)
            assert auth_session is not None
            events = list(
                (
                    await db.scalars(
                        select(AuthAuditEvent).where(AuthAuditEvent.event_type == "browser_logout")
                    )
                ).all()
            )
            return auth_session.status, events

    status, events = client.portal.call(read_logout_state)
    assert status == "revoked"
    assert len(events) == 1
    assert events[0].user_id == USER_ID

    client.cookies.set(AUTH_SESSION_COOKIE_NAME, OWNER_REVIEW_TEST_TOKEN)
    blocked = client.get("/desktop/meetings")
    assert blocked.status_code == 401
    assert blocked.json()["code"] == "auth_session_invalid"


def test_web_meetings_browser_request_redirects_to_login_without_leaking_content(client) -> None:
    response = client.get(
        "/meetings",
        headers={"Accept": "text/html"},
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert response.headers["location"].startswith("/login?")
    assert "next=%2Fmeetings" in response.headers["location"]
    assert "missing_auth_context" in response.headers["location"]


def test_browser_login_page_lists_workspace_providers(client) -> None:
    response = client.get("/login?next=/meetings")

    assert response.status_code == 200
    assert "Войти в кабинет" in response.text
    assert 'action="/login/email/start"' in response.text
    assert 'class="auth-download auth-download--browser"' in response.text
    assert response.text.count('href="/download"') == 1
    assert "Скачать приложение" in response.text
    assert 'type="email"' in response.text
    assert 'class="mini-link" href="/terms"' in response.text
    assert 'class="mini-link" href="/privacy"' in response.text
    assert "Способ входа" in response.text
    assert "Яндекс ID" in response.text
    assert '<a class="auth-provider" href="/login/yandex/start?next=%2Fmeetings">' in response.text
    assert "VK ID" in response.text
    assert '<a class="auth-provider" href="/login/vk/start?next=%2Fmeetings">' in response.text
    assert "Mail.ru" in response.text
    assert "/login/vk/start?next=%2Fmeetings&amp;auth_provider=mail_ru" in response.text
    assert "Одноклассники" in response.text
    assert "/login/vk/start?next=%2Fmeetings&amp;auth_provider=ok_ru" in response.text
    assert "T-Банк ID" in response.text
    assert "Sber ID" in response.text
    assert "Госуслуги" in response.text
    assert "Alfa ID" in response.text


def test_embedded_login_page_hides_download_cta_even_on_auth_error(client) -> None:
    response = client.get("/login?next=/desktop/meetings&error=auth_session_invalid")

    assert response.status_code == 200
    assert "/download" not in response.text
    assert "Скачать приложение" not in response.text
    assert "Сессия не найдена. Войдите снова." in response.text
    assert 'action="/login/email/start"' in response.text
    assert "Яндекс ID" in response.text
    assert 'class="mini-link" href="/terms"' in response.text
    assert 'class="mini-link" href="/privacy"' in response.text
    assert "скоро" in response.text
    assert "Telegram" not in response.text
    assert "TG" not in response.text
    assert "Продолжить через" not in response.text
    assert "Workspace ID" not in response.text
    assert 'name="workspace_id"' not in response.text
    assert str(WORKSPACE_ID) not in response.text


def test_browser_signup_page_matches_email_choice_flow_without_workspace_field(client) -> None:
    first_step = client.get("/sign-up?next=/meetings")
    email_step = client.get("/sign-up?next=/meetings&mode=email")

    assert first_step.status_code == 200
    assert "Зарегистрируйтесь бесплатно" in first_step.text
    assert "Яндекс ID" in first_step.text
    assert (
        '<a class="auth-provider" href="/login/yandex/start?next=%2Fmeetings">' in first_step.text
    )
    assert '<a class="auth-provider" href="/login/vk/start?next=%2Fmeetings">' in first_step.text
    assert "/login/vk/start?next=%2Fmeetings&amp;auth_provider=mail_ru" in first_step.text
    assert "/login/vk/start?next=%2Fmeetings&amp;auth_provider=ok_ru" in first_step.text
    assert "T-Банк ID" in first_step.text
    assert "Sber ID" in first_step.text
    assert "Госуслуги" in first_step.text
    assert "Alfa ID" in first_step.text
    assert "Рабочая почта" in first_step.text
    assert 'class="mini-link" href="/terms"' in first_step.text
    assert 'class="mini-link" href="/privacy"' in first_step.text
    assert "Telegram" not in first_step.text
    assert "Продолжить через" not in first_step.text
    assert "Workspace ID" not in first_step.text
    assert 'name="workspace_id"' not in first_step.text
    assert email_step.status_code == 200
    assert "Продолжить другим способом" in email_step.text
    assert 'action="/sign-up/email/start"' in email_step.text
    assert "Зарегистрироваться" in email_step.text
    assert 'class="mini-link" href="/terms"' in email_step.text
    assert 'class="mini-link" href="/privacy"' in email_step.text


def test_browser_yandex_login_start_redirects_to_provider(client) -> None:
    response = client.get(
        "/login/yandex/start?next=/meetings",
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert response.headers["location"].startswith("https://oauth.yandex.ru/authorize?")
    assert "state=" in response.headers["location"]
    query = parse_qs(urlsplit(response.headers["location"]).query)
    assert query["workspace_id"] == ["public"]
    assert query["force_confirm"] == ["1"]
    assert str(AUTH_BOOTSTRAP_WORKSPACE_ID) not in response.headers["location"]
    assert (
        "redirect_uri=http%3A%2F%2Ftestserver%2Fapi%2Fv1%2Fauth%2Fcallback%2Fyandex"
        in response.headers["location"]
    )
    set_cookie = response.headers["set-cookie"]
    assert f"{BROWSER_AUTH_STATE_COOKIE_NAME}=" in set_cookie
    assert "HttpOnly" in set_cookie
    assert "Secure" in set_cookie
    assert "SameSite=lax" in set_cookie
    assert "Domain=" not in set_cookie


def test_browser_yandex_callback_rejects_missing_browser_state_cookie(client) -> None:
    start = client.get(
        "/login/yandex/start?next=/meetings",
        follow_redirects=False,
    )
    state = parse_qs(urlsplit(start.headers["location"]).query)["state"][0]
    client.cookies.clear()

    callback = client.get(
        "/api/v1/auth/callback/yandex",
        params={"state": state, "code": "TEST-YA-USER"},
        follow_redirects=False,
    )

    assert callback.status_code == 303
    assert callback.headers["location"].startswith("/login?")
    assert "error=callback_state_invalid" in callback.headers["location"]


@pytest.mark.parametrize("cookie_mode", ["correct", "missing", "wrong"])
def test_settings_provider_link_callback_keeps_browser_nonce_binding(
    monkeypatch, client, cookie_mode: str
) -> None:
    _patch_browser_provider_callbacks(monkeypatch)
    provider_map = fake_provider_map()
    monkeypatch.setattr(
        "twobrain_rec_server.cabinet.web_routes.provider_links.build_provider_registry",
        lambda: provider_map,
    )
    monkeypatch.setattr(
        "twobrain_rec_server.cabinet.web_routes.provider_links.get_provider_adapter",
        lambda provider: provider_map[provider],
    )
    csrf = _login_owner_and_get_settings_csrf(client)
    start = client.post(
        "/settings/provider-links/yandex/start",
        data={"csrf_token": csrf},
        follow_redirects=False,
    )
    assert start.status_code == 303
    state = parse_qs(urlsplit(start.headers["location"]).query)["state"][0]
    nonce = re.search(
        rf"{re.escape(BROWSER_AUTH_STATE_COOKIE_NAME)}=([^;]+)",
        start.headers["set-cookie"],
    )
    assert nonce is not None
    client.cookies.delete(BROWSER_AUTH_STATE_COOKIE_NAME)
    if cookie_mode != "missing":
        client.cookies.set(
            BROWSER_AUTH_STATE_COOKIE_NAME,
            nonce.group(1) if cookie_mode == "correct" else "wrong-browser-state",
        )

    callback = client.get(
        "/api/v1/auth/callback/yandex",
        params={"state": state, "code": "settings-provider-link"},
        follow_redirects=False,
    )

    if cookie_mode == "correct":
        assert callback.status_code == 303
        assert callback.headers["location"].endswith("?result=callback_verified")
    else:
        assert callback.status_code == 303
        assert callback.headers["location"].endswith("?result=provider_link_invalid")


def test_browser_provider_callback_keeps_only_authorized_detail_return(monkeypatch, client) -> None:
    seeds = seed_cabinet_meetings(client)
    _patch_browser_provider_callbacks(monkeypatch)
    client.portal.call(lambda: _link_owner_yandex_identity(client, subject="browser-yandex-owner"))

    allowed_start = client.get(
        f"/login/yandex/start?next=/meetings/{seeds.ready_id}?calendar_context_action=change",
        follow_redirects=False,
    )
    allowed_state = parse_qs(urlsplit(allowed_start.headers["location"]).query)["state"][0]
    _bind_browser_callback_cookie(client, allowed_start)
    allowed_callback = client.get(
        "/api/v1/auth/callback/yandex",
        params={"state": allowed_state, "code": "browser-yandex-owner"},
        follow_redirects=False,
    )

    assert allowed_callback.status_code == 303
    assert allowed_callback.headers["location"] == "/meetings"
    assert f"{AUTH_SESSION_COOKIE_NAME}=" in allowed_callback.headers["set-cookie"]

    client.cookies.clear()
    client.portal.call(_set_workspace_self_enrollment_policy, client, True)
    denied_cases = (
        ("yandex", f"/meetings/{seeds.ready_id}", "/meetings", "browser-yandex-new-user"),
        ("vk", f"/desktop/meetings/{seeds.ready_id}", "/desktop/meetings", "browser-vk-new-user"),
    )
    for provider, candidate, expected_fallback, code in denied_cases:
        start = client.get(f"/login/{provider}/start?next={candidate}", follow_redirects=False)
        state = parse_qs(urlsplit(start.headers["location"]).query)["state"][0]
        _bind_browser_callback_cookie(client, start)
        callback = client.get(
            f"/api/v1/auth/callback/{provider}",
            params={"state": state, "code": code},
            follow_redirects=False,
        )

        assert callback.status_code == 303
        assert callback.headers["location"] == expected_fallback
        client.cookies.clear()


def test_browser_vk_login_start_redirects_to_provider(client) -> None:
    response = client.get(
        "/login/vk/start?next=/meetings",
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert response.headers["location"].startswith("https://id.vk.ru/authorize?")
    assert "client_id=twobrain-vk-client-id" in response.headers["location"]
    assert "state=" in response.headers["location"]
    assert parse_qs(urlsplit(response.headers["location"]).query)["workspace_id"] == ["public"]
    assert "force_confirm" not in parse_qs(urlsplit(response.headers["location"]).query)
    assert str(AUTH_BOOTSTRAP_WORKSPACE_ID) not in response.headers["location"]
    assert "scope=email+phone" in response.headers["location"]
    assert "code_challenge_method=S256" in response.headers["location"]
    assert (
        "redirect_uri=http%3A%2F%2Ftestserver%2Fapi%2Fv1%2Fauth%2Fcallback%2Fvk"
        in response.headers["location"]
    )


def test_browser_vk_login_start_supports_mail_and_ok_provider_hints(client) -> None:
    mail = client.get(
        "/login/vk/start?next=/meetings&auth_provider=mail_ru",
        follow_redirects=False,
    )
    ok = client.get(
        "/login/vk/start?next=/meetings&auth_provider=ok_ru",
        follow_redirects=False,
    )

    assert mail.status_code == 303
    assert "provider=mail_ru" in mail.headers["location"]
    assert ok.status_code == 303
    assert "provider=ok_ru" in ok.headers["location"]


def test_browser_telegram_provider_login_route_remains_stub(client) -> None:
    response = client.get(
        "/login/telegram/start?next=/meetings",
        follow_redirects=False,
    )

    assert response.status_code == 501
    assert "Этот способ входа появится позже" in response.text
    assert "location" not in response.headers


def test_browser_yandex_disabled_hides_action_and_fails_closed(client) -> None:
    client.portal.call(_set_workspace_yandex_policy, client, False)

    page = client.get("/login?next=/meetings")
    assert page.status_code == 200
    assert "Яндекс ID" not in page.text
    assert 'action="/login/email/start"' in page.text

    start = client.get("/login/yandex/start?next=/meetings", follow_redirects=False)
    assert start.status_code == 403
    assert "Этот способ входа выключен политикой кабинета" in unescape(start.text)
    assert 'action="/login/email/start"' in start.text


def test_browser_vk_disabled_hides_action_and_fails_closed(client) -> None:
    client.portal.call(_set_workspace_vk_policy, client, False)

    page = client.get("/login?next=/meetings")
    assert page.status_code == 200
    assert "VK ID" not in page.text
    assert 'action="/login/email/start"' in page.text

    start = client.get("/login/vk/start?next=/meetings", follow_redirects=False)
    assert start.status_code == 403
    assert "Этот способ входа выключен политикой кабинета" in unescape(start.text)
    assert 'action="/login/email/start"' in start.text


def test_browser_email_login_ignores_public_workspace_id_and_uses_internal_bootstrap(
    client,
) -> None:
    client.portal.call(_link_owner_email_identity, client)

    response = client.post(
        "/login/email/start",
        data={"email": BROWSER_OWNER_EMAIL, "workspace_id": str(uuid4()), "next": "/meetings"},
    )

    assert response.status_code == 200
    assert "Код для локальной проверки" in response.text
    assert "workspace_id" not in response.text


def test_browser_email_login_start_rejects_unknown_email_without_code(client) -> None:
    response = client.post(
        "/login/email/start",
        data={"email": "missing-owner@example.test", "next": "/meetings"},
    )

    assert response.status_code == 400
    assert "Не удалось отправить код. Проверьте email и попробуйте снова." in response.text
    assert "Код для локальной проверки" not in response.text


def test_browser_email_login_start_is_durably_rate_limited(client) -> None:
    payload = {"email": "rate-limited-owner@example.test", "next": "/meetings"}

    for _ in range(3):
        response = client.post("/login/email/start", data=payload)
        assert response.status_code == 400

    blocked = client.post("/login/email/start", data=payload)

    assert blocked.status_code == 429
    assert blocked.headers["Retry-After"]
    assert "Слишком много попыток" in blocked.text


def test_browser_email_login_flow_sets_cookie_binds_browser_device_and_opens_meetings(
    client,
) -> None:
    seed_cabinet_meetings(client)
    client.portal.call(_link_owner_email_identity, client)

    start = client.post(
        "/login/email/start",
        data={"email": BROWSER_OWNER_EMAIL, "next": "/meetings"},
    )
    assert start.status_code == 200
    state_match = re.search(r'name="state" value="([^"]+)"', start.text)
    code_match = re.search(r"Код для локальной проверки: <strong>(\d{6})</strong>", start.text)
    assert state_match is not None
    assert code_match is not None
    cookie_name, _browser_nonce = _bind_email_auth_attempt_cookie(
        client,
        start,
        state_nonce=state_match.group(1),
    )
    assert 'name="workspace_id"' not in start.text
    assert str(WORKSPACE_ID) not in start.text
    assert 'class="auth-panel"' in start.text
    assert start.text.count('class="code-slot"') == 6
    assert 'class="code-slots"' in start.text
    assert "data-code-hidden" in start.text
    assert 'name="code"' in start.text
    assert "data-code-form" in start.text
    assert 'src="/static/cabinet/cabinet.js?v=' in start.text

    callback = client.post(
        "/login/email/verify",
        data={
            "email": BROWSER_OWNER_EMAIL,
            "code": code_match.group(1),
            "state": state_match.group(1),
            "next": "/meetings",
        },
        follow_redirects=False,
    )

    assert callback.status_code == 303
    assert callback.headers["location"] == "/meetings"
    assert cookie_name not in client.cookies
    session_cookie = callback.cookies.get(AUTH_SESSION_COOKIE_NAME)
    assert session_cookie
    client.cookies.set(AUTH_SESSION_COOKIE_NAME, session_cookie)

    meetings = client.get("/meetings")
    assert meetings.status_code == 200
    assert "Проектный синк" not in meetings.text
    assert "missing_auth_context" not in meetings.text


@pytest.mark.parametrize("cookie_mode", ("missing", "wrong"))
def test_browser_email_login_rejects_relayed_code_without_exact_browser_cookie(
    client,
    cookie_mode: str,
) -> None:
    client.portal.call(_link_owner_email_identity, client)
    start = client.post(
        "/login/email/start",
        data={"email": BROWSER_OWNER_EMAIL, "next": "/meetings"},
    )
    state_match = re.search(r'name="state" value="([^"]+)"', start.text)
    code_match = re.search(r"Код для локальной проверки: <strong>(\d{6})</strong>", start.text)
    assert state_match is not None and code_match is not None
    state_nonce = state_match.group(1)
    cookie_name, _browser_nonce = _bind_email_auth_attempt_cookie(
        client,
        start,
        state_nonce=state_nonce,
    )
    client.cookies.delete(cookie_name)
    if cookie_mode == "wrong":
        client.cookies.set(
            cookie_name,
            "relayed-from-another-browser",
            domain="testserver.local",
            path="/",
        )

    callback = client.post(
        "/login/email/verify",
        data={
            "email": BROWSER_OWNER_EMAIL,
            "code": code_match.group(1),
            "state": state_nonce,
            "next": "/meetings",
        },
        follow_redirects=False,
    )

    assert callback.status_code == 400
    assert callback.cookies.get(AUTH_SESSION_COOKIE_NAME) is None
    assert cookie_name not in client.cookies
    assert "Max-Age=0" in callback.headers["set-cookie"]

    async def read_result() -> tuple[str, str | None, int]:
        async with client.app_state["sessionmaker"]() as db:
            callback_state = await db.scalar(
                select(AuthCallbackState).where(AuthCallbackState.state_nonce == state_nonce)
            )
            sessions = list(
                await db.scalars(
                    select(AuthSession).where(
                        AuthSession.user_id == USER_ID,
                        AuthSession.provider == "email",
                    )
                )
            )
            assert callback_state is not None
            return callback_state.result, callback_state.error_code, len(sessions)

    assert client.portal.call(read_result) == ("failed", "email_code_invalid", 0)


def test_parallel_browser_email_login_attempts_keep_independent_nonce_cookies(client) -> None:
    client.portal.call(_link_owner_email_identity, client)

    attempts: list[tuple[str, str, str, str]] = []
    for _ in range(2):
        start = client.post(
            "/login/email/start",
            data={"email": BROWSER_OWNER_EMAIL, "next": "/meetings"},
        )
        state_match = re.search(r'name="state" value="([^"]+)"', start.text)
        code_match = re.search(r"Код для локальной проверки: <strong>(\d{6})</strong>", start.text)
        assert state_match is not None and code_match is not None
        cookie_name, browser_nonce = _bind_email_auth_attempt_cookie(
            client,
            start,
            state_nonce=state_match.group(1),
        )
        attempts.append((state_match.group(1), code_match.group(1), cookie_name, browser_nonce))

    assert attempts[0][2] != attempts[1][2]
    assert attempts[0][3] != attempts[1][3]

    for index, (state_nonce, code, cookie_name, _browser_nonce) in enumerate(attempts):
        callback = client.post(
            "/login/email/verify",
            data={
                "email": BROWSER_OWNER_EMAIL,
                "code": code,
                "state": state_nonce,
                "next": "/meetings",
            },
            follow_redirects=False,
        )
        assert callback.status_code == 303
        assert cookie_name not in client.cookies
        if index == 0:
            assert attempts[1][2] in client.cookies

    async def count_sessions() -> int:
        async with client.app_state["sessionmaker"]() as db:
            return len(
                list(
                    await db.scalars(
                        select(AuthSession).where(
                            AuthSession.user_id == USER_ID,
                            AuthSession.provider == "email",
                        )
                    )
                )
            )

    assert client.portal.call(count_sessions) == 2


def test_email_login_digest_requires_server_secret_and_browser_nonce(client) -> None:
    client.portal.call(_link_owner_email_identity, client)
    start = client.post(
        "/login/email/start",
        data={"email": BROWSER_OWNER_EMAIL, "next": "/meetings"},
    )
    state_match = re.search(r'name="state" value="([^"]+)"', start.text)
    code_match = re.search(r"Код для локальной проверки: <strong>(\d{6})</strong>", start.text)
    assert state_match is not None and code_match is not None
    state_nonce = state_match.group(1)
    code = code_match.group(1)
    _cookie_name, browser_nonce = _bind_email_auth_attempt_cookie(
        client,
        start,
        state_nonce=state_nonce,
    )

    async def stored_digest() -> str:
        async with client.app_state["sessionmaker"]() as db:
            callback_state = await db.scalar(
                select(AuthCallbackState).where(AuthCallbackState.state_nonce == state_nonce)
            )
            assert callback_state is not None
            return callback_state.expected_state

    digest = client.portal.call(stored_digest)
    code_digest, browser_digest = digest.split(".")
    assert code_digest != hash_token(f"{BROWSER_OWNER_EMAIL}\0{code}")
    assert code_digest == auth_email_flow_module._email_auth_expected_state(
        secret=client.app.state.web_csrf_secret,
        provider="email",
        state_nonce=state_nonce,
        email=BROWSER_OWNER_EMAIL,
        code=code,
        browser_nonce=browser_nonce,
    )
    assert code_digest != auth_email_flow_module._email_auth_expected_state(
        secret="wrong-offline-secret",
        provider="email",
        state_nonce=state_nonce,
        email=BROWSER_OWNER_EMAIL,
        code=code,
        browser_nonce=browser_nonce,
    )
    assert code_digest != auth_email_flow_module._email_auth_expected_state(
        secret=client.app.state.web_csrf_secret,
        provider="email",
        state_nonce=state_nonce,
        email=BROWSER_OWNER_EMAIL,
        code=code,
        browser_nonce="nonce-from-another-browser",
    )
    assert browser_digest == auth_email_flow_module._email_auth_browser_binding_state(
        secret=client.app.state.web_csrf_secret,
        provider="email",
        state_nonce=state_nonce,
        email=BROWSER_OWNER_EMAIL,
        browser_nonce=browser_nonce,
    )


@pytest.mark.parametrize("provider", ("yandex", "vk"))
def test_email_login_rejects_oauth_provider_email_metadata(client, provider: str) -> None:
    email = f"{provider}-metadata-only@example.test"

    async def seed_oauth_metadata() -> None:
        async with client.app_state["sessionmaker"]() as db:
            db.add(
                ExternalIdentity(
                    user_id=USER_ID,
                    provider=provider,
                    provider_subject=f"{provider}:metadata-only",
                    email=email,
                    is_active=True,
                    is_verified=True,
                )
            )
            await db.commit()

    client.portal.call(seed_oauth_metadata)
    response = client.post(
        "/login/email/start",
        data={"email": email, "next": "/meetings"},
    )

    assert response.status_code == 400
    assert "Код для локальной проверки" not in response.text

    async def read_result() -> tuple[int, int]:
        async with client.app_state["sessionmaker"]() as db:
            callbacks = list(
                await db.scalars(
                    select(AuthCallbackState).where(AuthCallbackState.provider == "email")
                )
            )
            sessions = list(
                await db.scalars(
                    select(AuthSession).where(
                        AuthSession.user_id == USER_ID,
                        AuthSession.provider == "email",
                    )
                )
            )
            return len(callbacks), len(sessions)

    assert client.portal.call(read_result) == (0, 0)


def test_browser_email_login_response_failure_rolls_back_session_and_callback(
    monkeypatch,
    client,
) -> None:
    client.portal.call(_link_owner_email_identity, client)
    start = client.post(
        "/login/email/start",
        data={"email": BROWSER_OWNER_EMAIL, "next": "/meetings"},
    )
    state = re.search(r'name="state" value="([^"]+)"', start.text)
    code = re.search(r"Код для локальной проверки: <strong>(\d{6})</strong>", start.text)
    assert state is not None and code is not None
    _bind_email_auth_attempt_cookie(client, start, state_nonce=state.group(1))

    async def fail_response_resolution(*_args, **_kwargs):
        raise RuntimeError("synthetic response resolution failure")

    monkeypatch.setattr(
        auth_routes,
        "resolve_browser_auth_return_path",
        fail_response_resolution,
    )
    with pytest.raises(RuntimeError, match="synthetic response resolution failure"):
        client.post(
            "/login/email/verify",
            data={
                "email": BROWSER_OWNER_EMAIL,
                "code": code.group(1),
                "state": state.group(1),
                "next": "/meetings",
            },
            follow_redirects=False,
        )

    async def read_result() -> tuple[str, int, int]:
        async with client.app_state["sessionmaker"]() as db:
            callback = await db.scalar(
                select(AuthCallbackState).where(AuthCallbackState.state_nonce == state.group(1))
            )
            sessions = list(
                await db.scalars(
                    select(AuthSession).where(
                        AuthSession.user_id == USER_ID,
                        AuthSession.provider == "email",
                    )
                )
            )
            assert callback is not None
            return callback.result, len(sessions)

    assert client.portal.call(read_result) == ("pending", 0)


def test_browser_email_login_verification_uses_state_bound_return_path(client) -> None:
    client.portal.call(_link_owner_email_identity, client)

    start = client.post(
        "/login/email/start",
        data={"email": BROWSER_OWNER_EMAIL, "next": "/meetings"},
    )
    state_match = re.search(r'name="state" value="([^"]+)"', start.text)
    code_match = re.search(r"Код для локальной проверки: <strong>(\d{6})</strong>", start.text)
    assert state_match is not None
    assert code_match is not None
    _bind_email_auth_attempt_cookie(client, start, state_nonce=state_match.group(1))

    callback = client.post(
        "/login/email/verify",
        data={
            "email": BROWSER_OWNER_EMAIL,
            "code": code_match.group(1),
            "state": state_match.group(1),
            "next": f"/desktop/meetings/{uuid4()}",
        },
        follow_redirects=False,
    )

    assert callback.status_code == 303
    assert callback.headers["location"] == "/meetings"


def test_authenticated_email_link_is_passwordless_and_csrf_protected(client) -> None:
    csrf = _login_owner_and_get_settings_csrf(client)
    state, code, link_csrf = _start_email_link(
        client,
        email=BROWSER_OWNER_EMAIL,
        csrf_token=csrf,
    )
    verified = client.post(
        "/settings/account/email-link/verify",
        data={
            "email": BROWSER_OWNER_EMAIL,
            "code": code,
            "state": state,
            "csrf_token": link_csrf,
        },
        follow_redirects=False,
    )

    assert verified.status_code == 303
    assert verified.headers["location"] == "/settings/account?provider_link=confirmed"


def test_authenticated_email_link_delivery_failure_is_recoverable(monkeypatch, client) -> None:
    csrf = _login_owner_and_get_settings_csrf(client)
    client.app.state.settings.env = "production"

    async def fail_send_email_login_code(**_kwargs):
        raise email_delivery.EmailLoginDeliveryError("postal_request_failed")

    monkeypatch.setattr(email_delivery, "send_email_login_code", fail_send_email_login_code)

    response = client.post(
        "/settings/account/email-link/start",
        data={"email": "delivery-failure@example.test", "csrf_token": csrf},
    )

    assert response.status_code == 503
    assert "Почтовая доставка временно недоступна" in response.text
    assert "Код для локальной проверки" not in response.text


def test_authenticated_email_link_reactivates_inactive_identity(client) -> None:
    email = "relink-owner@example.test"
    identity_id = uuid4()
    csrf = _login_owner_and_get_settings_csrf(client)

    async def seed_inactive_identity() -> None:
        async with client.app_state["sessionmaker"]() as db:
            db.add(
                ExternalIdentity(
                    id=identity_id,
                    user_id=USER_ID,
                    provider="email",
                    provider_subject=email,
                    provider_username=email,
                    email=email,
                    is_verified=False,
                    is_active=False,
                )
            )
            await db.commit()

    client.portal.call(seed_inactive_identity)
    state, code, link_csrf = _start_email_link(client, email=email, csrf_token=csrf)
    verified = client.post(
        "/settings/account/email-link/verify",
        data={"email": email, "code": code, "state": state, "csrf_token": link_csrf},
        follow_redirects=False,
    )

    assert verified.status_code == 303

    async def read_result() -> tuple[int, bool, bool, str]:
        async with client.app_state["sessionmaker"]() as db:
            identities = list(
                await db.scalars(
                    select(ExternalIdentity).where(
                        ExternalIdentity.provider == "email",
                        ExternalIdentity.provider_subject == email,
                    )
                )
            )
            callback = await db.scalar(
                select(AuthCallbackState).where(AuthCallbackState.state_nonce == state)
            )
            assert callback is not None
            return (
                len(identities),
                identities[0].is_active,
                identities[0].is_verified,
                callback.result,
            )

    assert client.portal.call(read_result) == (1, True, True, "completed")


def test_authenticated_email_link_digest_requires_server_secret(client) -> None:
    email = "server-keyed-link@example.test"
    csrf = _login_owner_and_get_settings_csrf(client)
    state, code, _link_csrf = _start_email_link(client, email=email, csrf_token=csrf)

    async def stored_digest() -> str:
        async with client.app_state["sessionmaker"]() as db:
            callback = await db.scalar(
                select(AuthCallbackState).where(AuthCallbackState.state_nonce == state)
            )
            assert callback is not None
            return callback.expected_state

    digest = client.portal.call(stored_digest)
    assert digest != hash_token(f"{email}\0{code}")
    assert digest == auth_email_flow_module._email_auth_expected_state(
        secret=client.app.state.web_csrf_secret,
        provider="email_link",
        state_nonce=state,
        email=email,
        code=code,
        browser_nonce="",
    )
    assert digest != auth_email_flow_module._email_auth_expected_state(
        secret="wrong-offline-secret",
        provider="email_link",
        state_nonce=state,
        email=email,
        code=code,
        browser_nonce="",
    )


@pytest.mark.parametrize("provider", ("yandex", "vk"))
def test_email_link_does_not_merge_from_oauth_provider_email_metadata(
    client,
    provider: str,
) -> None:
    email = f"{provider}-merge-metadata@example.test"
    foreign_user_id = uuid4()
    foreign_identity_id = uuid4()

    async def seed_foreign_oauth_metadata() -> None:
        async with client.app_state["sessionmaker"]() as db:
            db.add(
                UserIdentity(
                    id=foreign_user_id,
                    organization_id=ORG_ID,
                    external_subject=str(foreign_user_id),
                )
            )
            await db.flush()
            db.add(
                ExternalIdentity(
                    id=foreign_identity_id,
                    user_id=foreign_user_id,
                    provider=provider,
                    provider_subject=f"{provider}:foreign-metadata",
                    email=email,
                    is_active=True,
                    is_verified=True,
                )
            )
            await db.commit()

    client.portal.call(seed_foreign_oauth_metadata)
    csrf = _login_owner_and_get_settings_csrf(client)
    state, code, link_csrf = _start_email_link(client, email=email, csrf_token=csrf)
    verified = client.post(
        "/settings/account/email-link/verify",
        data={"email": email, "code": code, "state": state, "csrf_token": link_csrf},
        follow_redirects=False,
    )

    assert verified.status_code == 303
    assert verified.headers["location"] == "/settings/account?provider_link=confirmed"

    async def read_result() -> tuple[UUID, str, int]:
        async with client.app_state["sessionmaker"]() as db:
            foreign_identity = await db.get(ExternalIdentity, foreign_identity_id)
            linked_email = await db.scalar(
                select(ExternalIdentity).where(
                    ExternalIdentity.user_id == USER_ID,
                    ExternalIdentity.provider == "email",
                    ExternalIdentity.provider_subject == email,
                )
            )
            intents = list(await db.scalars(select(AccountMergeIntent)))
            assert foreign_identity is not None and linked_email is not None
            return foreign_identity.user_id, linked_email.provider, len(intents)

    assert client.portal.call(read_result) == (foreign_user_id, "email", 0)


def test_authenticated_email_link_rejects_foreign_inactive_identity(client) -> None:
    email = "unlinked-foreign@example.test"
    foreign_user_id = uuid4()
    foreign_identity_id = uuid4()

    async def seed_foreign_inactive_identity() -> None:
        async with client.app_state["sessionmaker"]() as db:
            db.add(
                UserIdentity(
                    id=foreign_user_id,
                    organization_id=ORG_ID,
                    external_subject=str(foreign_user_id),
                )
            )
            await db.flush()
            db.add(
                ExternalIdentity(
                    id=foreign_identity_id,
                    user_id=foreign_user_id,
                    provider="email",
                    provider_subject=email,
                    email=email,
                    is_verified=False,
                    is_active=False,
                )
            )
            await db.commit()

    client.portal.call(seed_foreign_inactive_identity)
    csrf = _login_owner_and_get_settings_csrf(client)
    state, code, link_csrf = _start_email_link(client, email=email, csrf_token=csrf)
    response = client.post(
        "/settings/account/email-link/verify",
        data={"email": email, "code": code, "state": state, "csrf_token": link_csrf},
        follow_redirects=False,
    )

    assert response.status_code == 400

    async def read_result() -> tuple[str | None, int, bool, bool]:
        async with client.app_state["sessionmaker"]() as db:
            callback = await db.scalar(
                select(AuthCallbackState).where(AuthCallbackState.state_nonce == state)
            )
            identity = await db.get(ExternalIdentity, foreign_identity_id)
            intents = list(await db.scalars(select(AccountMergeIntent)))
            assert callback is not None and identity is not None
            return callback.error_code, len(intents), identity.is_active, identity.is_verified

    assert client.portal.call(read_result) == ("provider_link_conflict", 0, False, False)


@pytest.mark.parametrize(
    ("case", "expected_result", "expected_error"),
    (("invalid", "failed", "email_code_invalid"), ("expired", "expired", "email_code_expired")),
)
def test_authenticated_email_link_failure_is_audited_before_terminal_callback(
    client,
    case: str,
    expected_result: str,
    expected_error: str,
) -> None:
    email = f"{case}-email-link@example.test"
    csrf = _login_owner_and_get_settings_csrf(client)
    state, code, link_csrf = _start_email_link(client, email=email, csrf_token=csrf)

    if case == "expired":

        async def expire_state() -> None:
            async with client.app_state["sessionmaker"]() as db:
                callback = await db.scalar(
                    select(AuthCallbackState).where(AuthCallbackState.state_nonce == state)
                )
                assert callback is not None
                callback.expires_at = datetime.now(UTC) - timedelta(seconds=1)
                await db.commit()

        client.portal.call(expire_state)
    else:
        code = "000000" if code != "000000" else "999999"

    response = client.post(
        "/settings/account/email-link/verify",
        data={"email": email, "code": code, "state": state, "csrf_token": link_csrf},
        follow_redirects=False,
    )
    assert response.status_code == 400
    retry_csrf = re.search(r'name="csrf_token" value="([^"]+)"', response.text)
    assert retry_csrf is not None
    retry = client.post(
        "/settings/account/email-link/verify",
        data={
            "email": email,
            "code": code,
            "state": state,
            "csrf_token": retry_csrf.group(1),
        },
        follow_redirects=False,
    )
    assert retry.status_code == 400

    async def read_result() -> tuple[str, str | None, int]:
        async with client.app_state["sessionmaker"]() as db:
            callback = await db.scalar(
                select(AuthCallbackState).where(AuthCallbackState.state_nonce == state)
            )
            audits = list(
                await db.scalars(
                    select(AuthAuditEvent).where(
                        AuthAuditEvent.event_type == "email_identity_link_failed",
                        AuthAuditEvent.outcome == "failure",
                    )
                )
            )
            assert callback is not None
            matching = [
                event for event in audits if event.metadata_json.get("error_code") == expected_error
            ]
            return callback.result, callback.error_code, len(matching)

    assert client.portal.call(read_result) == (expected_result, expected_error, 1)


def test_authenticated_email_link_requires_preview_for_one_other_account(
    monkeypatch, client
) -> None:
    source_user_id = uuid4()
    source_workspace_id = uuid4()
    email = "one-other-account@example.test"

    async def seed_source() -> None:
        async with client.app_state["sessionmaker"]() as db:
            db.add_all(
                [
                    UserIdentity(
                        id=source_user_id,
                        organization_id=ORG_ID,
                        external_subject=str(source_user_id),
                    ),
                    Workspace(
                        id=source_workspace_id,
                        organization_id=ORG_ID,
                        owner_user_id=source_user_id,
                        slug=f"source-{source_user_id.hex}",
                        name="Source account",
                        kind="personal",
                    ),
                ]
            )
            await db.flush()
            db.add_all(
                [
                    WorkspaceMembership(
                        workspace_id=source_workspace_id,
                        user_id=source_user_id,
                        role="owner",
                        status="active",
                    ),
                    ExternalIdentity(
                        user_id=source_user_id,
                        provider="email",
                        provider_subject=email,
                        email=email,
                        is_verified=True,
                        is_active=True,
                    ),
                ]
            )
            await db.commit()

    client.portal.call(seed_source)
    csrf = _login_owner_and_get_settings_csrf(client)
    applied_contexts: list[object] = []

    async def track_context(db, context) -> None:
        applied_contexts.append(context)
        await apply_tenant_context(db, context)

    monkeypatch.setattr(auth_email_flow_module, "apply_tenant_context", track_context)
    state, code, link_csrf = _start_email_link(
        client,
        email=email,
        csrf_token=csrf,
    )
    applied_contexts.clear()
    verified = client.post(
        "/settings/account/email-link/verify",
        data={
            "email": email,
            "code": code,
            "state": state,
            "csrf_token": link_csrf,
        },
        follow_redirects=False,
    )

    assert verified.status_code == 303
    expected_preview_context = WorkspaceAuthContext(
        workspace_id=PERSONAL_WORKSPACE_ID,
        organization_id=ORG_ID,
        user_id=USER_ID,
        context_kind="auth_bootstrap",
    )
    assert applied_contexts.count(expected_preview_context) == 2
    match = re.fullmatch(r"/settings/account/merge/([0-9a-f-]+)", verified.headers["location"])
    assert match is not None, verified.headers["location"]
    intent_id = UUID(match.group(1))

    preview_page = client.get(verified.headers["location"])
    assert preview_page.status_code == 200
    csrf_match = re.search(r'name="csrf_token" value="([^"]+)"', preview_page.text)
    fingerprint_match = re.search(r'name="preview_fingerprint" value="([^"]+)"', preview_page.text)
    idempotency_match = re.search(r'name="idempotency_key" value="([^"]+)"', preview_page.text)
    assert csrf_match is not None
    assert fingerprint_match is not None
    assert idempotency_match is not None

    async def expire_intent() -> None:
        async with client.app_state["sessionmaker"]() as db:
            intent = await db.get(AccountMergeIntent, intent_id)
            assert intent is not None
            intent.expires_at = datetime.now(UTC) - timedelta(seconds=1)
            await db.commit()

    client.portal.call(expire_intent)
    expired = client.post(
        f"/settings/account/merge/{intent_id}/confirm",
        data={
            "csrf_token": csrf_match.group(1),
            "preview_fingerprint": fingerprint_match.group(1),
            "idempotency_key": idempotency_match.group(1),
        },
        follow_redirects=False,
    )
    assert expired.status_code == 303
    assert expired.headers["location"].endswith("?error=merge_intent_expired")

    async def read_result() -> tuple[str, str, str, str | None]:
        async with client.app_state["sessionmaker"]() as db:
            source = await db.get(UserIdentity, source_user_id)
            intent = await db.get(AccountMergeIntent, intent_id)
            callback = await db.scalar(
                select(AuthCallbackState).where(AuthCallbackState.state_nonce == state)
            )
            assert source is not None and intent is not None and callback is not None
            return source.status, intent.status, callback.result, intent.error_code

    assert client.portal.call(read_result) == (
        "active",
        "expired",
        "completed",
        "merge_intent_expired",
    )


def test_real_email_link_callback_merges_after_explicit_preview_confirmation(client) -> None:
    source_user_id = uuid4()
    source_workspace_id = uuid4()
    email = "email-link-merge-success@example.test"

    async def seed_source() -> None:
        async with client.app_state["sessionmaker"]() as db:
            db.add_all(
                [
                    UserIdentity(
                        id=source_user_id,
                        organization_id=ORG_ID,
                        external_subject=str(source_user_id),
                    ),
                    Workspace(
                        id=source_workspace_id,
                        organization_id=ORG_ID,
                        owner_user_id=source_user_id,
                        slug=f"source-{source_user_id.hex}",
                        name="Source account",
                        kind="personal",
                    ),
                ]
            )
            await db.flush()
            db.add_all(
                [
                    WorkspaceMembership(
                        workspace_id=source_workspace_id,
                        user_id=source_user_id,
                        role="owner",
                        status="active",
                    ),
                    ExternalIdentity(
                        user_id=source_user_id,
                        provider="email",
                        provider_subject=email,
                        email=email,
                        is_verified=True,
                        is_active=True,
                    ),
                ]
            )
            await db.commit()

    client.portal.call(seed_source)
    csrf = _login_owner_and_get_settings_csrf(client)
    state, code, link_csrf = _start_email_link(client, email=email, csrf_token=csrf)
    verified = client.post(
        "/settings/account/email-link/verify",
        data={"email": email, "code": code, "state": state, "csrf_token": link_csrf},
        follow_redirects=False,
    )
    assert verified.status_code == 303
    match = re.fullmatch(r"/settings/account/merge/([0-9a-f-]+)", verified.headers["location"])
    assert match is not None

    preview = client.get(verified.headers["location"])
    fields = {
        name: re.search(rf'name="{name}" value="([^"]+)"', preview.text)
        for name in ("csrf_token", "preview_fingerprint", "idempotency_key")
    }
    assert all(match is not None for match in fields.values())
    confirmed = client.post(
        f"{verified.headers['location']}/confirm",
        data={name: match.group(1) for name, match in fields.items() if match is not None},
        follow_redirects=False,
    )
    assert confirmed.status_code == 303
    assert confirmed.headers["location"].startswith(
        "/login?next=/settings/account&error=email_connected_relogin_required"
    )

    async def read_result() -> tuple[str, UUID | None, str, bool]:
        async with client.app_state["sessionmaker"]() as db:
            source = await db.get(UserIdentity, source_user_id)
            callback = await db.scalar(
                select(AuthCallbackState).where(AuthCallbackState.state_nonce == state)
            )
            source_identity = await db.scalar(
                select(ExternalIdentity).where(
                    ExternalIdentity.user_id == USER_ID,
                    ExternalIdentity.provider == "email",
                    ExternalIdentity.provider_subject == email,
                )
            )
            assert source is not None and callback is not None and source_identity is not None
            return (
                source.status,
                source.merged_into_user_id,
                callback.provider,
                callback.verified_external_identity_id == source_identity.id,
            )

    assert client.portal.call(read_result) == (
        "merged",
        USER_ID,
        "email_link",
        True,
    )


def test_blocked_email_link_keeps_completed_proof_for_recovery_page(client) -> None:
    source_user_id = uuid4()
    source_workspace_id = uuid4()
    email = "blocked-other-account@example.test"

    async def seed_source() -> None:
        async with client.app_state["sessionmaker"]() as db:
            db.add_all(
                [
                    UserIdentity(
                        id=source_user_id,
                        organization_id=ORG_ID,
                        external_subject=str(source_user_id),
                    ),
                    Workspace(
                        id=source_workspace_id,
                        organization_id=ORG_ID,
                        owner_user_id=source_user_id,
                        slug=f"source-{source_user_id.hex}",
                        name="Blocked source account",
                        kind="corporate",
                    ),
                ]
            )
            await db.flush()
            db.add_all(
                [
                    WorkspaceMembership(
                        workspace_id=source_workspace_id,
                        user_id=source_user_id,
                        role="owner",
                        status="active",
                    ),
                    ExternalIdentity(
                        user_id=source_user_id,
                        provider="email",
                        provider_subject=email,
                        email=email,
                        is_verified=True,
                        is_active=True,
                    ),
                    WorkspaceSubscription(
                        workspace_id=source_workspace_id,
                        billing_owner_id=source_user_id,
                        state="active",
                        plan_code="pro",
                        cycle="monthly",
                        recurring_allowed=True,
                    ),
                ]
            )
            await db.commit()

    client.portal.call(seed_source)
    csrf = _login_owner_and_get_settings_csrf(client)
    state, code, link_csrf = _start_email_link(client, email=email, csrf_token=csrf)
    verified = client.post(
        "/settings/account/email-link/verify",
        data={"email": email, "code": code, "state": state, "csrf_token": link_csrf},
        follow_redirects=False,
    )

    assert verified.status_code == 303
    match = re.fullmatch(r"/settings/account/merge/([0-9a-f-]+)", verified.headers["location"])
    assert match is not None, verified.headers["location"]
    intent_id = UUID(match.group(1))
    recovery = client.get(verified.headers["location"])
    assert recovery.status_code == 200
    assert "На втором профиле есть активная оплата" in recovery.text

    async def read_result() -> tuple[str, str, str | None]:
        async with client.app_state["sessionmaker"]() as db:
            callback = await db.scalar(
                select(AuthCallbackState).where(AuthCallbackState.state_nonce == state)
            )
            intent = await db.get(AccountMergeIntent, intent_id)
            assert callback is not None and intent is not None
            return callback.result, intent.status, intent.blocker_code

    assert client.portal.call(read_result) == ("completed", "blocked", "billing_conflict")


def test_authenticated_email_link_fails_closed_for_multiple_other_accounts(client) -> None:
    email = "many-other-accounts@example.test"
    other_user_ids = (uuid4(), uuid4())

    async def seed_sources() -> None:
        async with client.app_state["sessionmaker"]() as db:
            for user_id in other_user_ids:
                db.add(
                    UserIdentity(
                        id=user_id,
                        organization_id=ORG_ID,
                        external_subject=str(user_id),
                    )
                )
            await db.flush()
            for user_id in other_user_ids:
                db.add(
                    ExternalIdentity(
                        user_id=user_id,
                        provider="email",
                        provider_subject=f"{user_id}:{email}",
                        email=email,
                        is_verified=True,
                        is_active=True,
                    )
                )
            await db.commit()

    client.portal.call(seed_sources)
    csrf = _login_owner_and_get_settings_csrf(client)
    state, code, link_csrf = _start_email_link(
        client,
        email=email,
        csrf_token=csrf,
    )
    verified = client.post(
        "/settings/account/email-link/verify",
        data={
            "email": email,
            "code": code,
            "state": state,
            "csrf_token": link_csrf,
        },
        follow_redirects=False,
    )

    assert verified.status_code == 400
    assert "несколькими профилями" in verified.text

    async def read_result() -> tuple[str, int]:
        async with client.app_state["sessionmaker"]() as db:
            callback = await db.scalar(
                select(AuthCallbackState).where(AuthCallbackState.state_nonce == state)
            )
            intents = list(await db.scalars(select(AccountMergeIntent)))
            audits = list(
                await db.scalars(
                    select(AuthAuditEvent).where(
                        AuthAuditEvent.event_type == "email_identity_link_failed",
                        AuthAuditEvent.outcome == "failure",
                    )
                )
            )
            assert callback is not None
            matching = [
                event
                for event in audits
                if event.metadata_json.get("error_code") == "ambiguous_email_recovery_required"
            ]
            return callback.error_code or "", len(intents), len(matching)

    assert client.portal.call(read_result) == ("ambiguous_email_recovery_required", 0, 1)


def test_browser_email_signup_verification_uses_state_bound_return_path(client) -> None:
    client.portal.call(_set_workspace_self_enrollment_policy, client, True)
    signup_email = "state-bound-signup@example.test"
    start = client.post(
        "/sign-up/email/start",
        data={"email": signup_email, "next": "/meetings"},
    )
    state_match = re.search(r'name="state" value="([^"]+)"', start.text)
    code_match = re.search(r"Код для локальной проверки: <strong>(\d{6})</strong>", start.text)
    assert state_match is not None
    assert code_match is not None
    _bind_email_auth_attempt_cookie(client, start, state_nonce=state_match.group(1))

    callback = client.post(
        "/sign-up/email/verify",
        data={
            "email": signup_email,
            "code": code_match.group(1),
            "state": state_match.group(1),
            "next": f"/desktop/meetings/{uuid4()}",
        },
        follow_redirects=False,
    )

    assert callback.status_code == 303
    assert callback.headers["location"] == "/meetings"


def test_browser_email_login_wrong_code_keeps_state_for_retry(client) -> None:
    client.portal.call(_link_owner_email_identity, client)

    start = client.post(
        "/login/email/start",
        data={"email": BROWSER_OWNER_EMAIL, "next": "/meetings"},
    )
    assert start.status_code == 200
    state_match = re.search(r'name="state" value="([^"]+)"', start.text)
    code_match = re.search(r"Код для локальной проверки: <strong>(\d{6})</strong>", start.text)
    assert state_match is not None
    assert code_match is not None
    state = state_match.group(1)
    code = code_match.group(1)
    _bind_email_auth_attempt_cookie(client, start, state_nonce=state)
    wrong_code = "000000" if code != "000000" else "999999"

    wrong_attempts = [
        client.post(
            "/login/email/verify",
            data={
                "email": BROWSER_OWNER_EMAIL,
                "code": wrong_code,
                "state": state,
                "next": "/meetings",
            },
            follow_redirects=False,
        )
        for _ in range(2)
    ]
    replay = client.post(
        "/login/email/verify",
        data={"email": BROWSER_OWNER_EMAIL, "code": code, "state": state, "next": "/meetings"},
        follow_redirects=False,
    )

    assert all(response.status_code == 400 for response in wrong_attempts)
    assert all('action="/login/email/verify"' in response.text for response in wrong_attempts)
    assert all("Код введён неверно" in response.text for response in wrong_attempts)
    assert replay.status_code == 303, replay.text
    assert replay.headers["location"] == "/meetings"
    assert replay.cookies.get(AUTH_SESSION_COOKIE_NAME)

    async def state_result() -> tuple[str, str | None]:
        async with client.app_state["sessionmaker"]() as db:
            state_row = await db.scalar(
                select(AuthCallbackState).where(AuthCallbackState.state_nonce == state)
            )
            assert state_row is not None
            return state_row.result, state_row.error_code

    assert client.portal.call(state_result) == ("completed", None)


def test_browser_email_login_blocks_code_after_three_wrong_attempts(client) -> None:
    client.portal.call(_link_owner_email_identity, client)

    start = client.post(
        "/login/email/start",
        data={"email": BROWSER_OWNER_EMAIL, "next": "/meetings"},
    )
    assert start.status_code == 200
    state_match = re.search(r'name="state" value="([^"]+)"', start.text)
    code_match = re.search(r"Код для локальной проверки: <strong>(\d{6})</strong>", start.text)
    assert state_match is not None
    assert code_match is not None
    state = state_match.group(1)
    code = code_match.group(1)
    _bind_email_auth_attempt_cookie(client, start, state_nonce=state)
    wrong_code = "000000" if code != "000000" else "999999"

    wrong_responses = [
        client.post(
            "/login/email/verify",
            data={
                "email": BROWSER_OWNER_EMAIL,
                "code": wrong_code,
                "state": state,
                "next": "/meetings",
            },
            follow_redirects=False,
        )
        for _ in range(3)
    ]
    assert all(response.status_code == 400 for response in wrong_responses)
    assert all('action="/login/email/verify"' in response.text for response in wrong_responses[:2])
    assert 'action="/login/email/verify"' not in wrong_responses[2].text
    assert "Слишком много попыток" in wrong_responses[2].text

    blocked = client.post(
        "/login/email/verify",
        data={"email": BROWSER_OWNER_EMAIL, "code": code, "state": state, "next": "/meetings"},
        follow_redirects=False,
    )

    assert blocked.status_code == 429
    assert "Слишком много попыток" in blocked.text
    assert 'action="/login/email/verify"' not in blocked.text
    assert blocked.cookies.get(AUTH_SESSION_COOKIE_NAME) is None


def test_browser_email_signup_flow_creates_user_and_opens_meetings(client) -> None:
    client.portal.call(_set_workspace_self_enrollment_policy, client, True)
    signup_email = "new-owner@example.test"

    start = client.post(
        "/sign-up/email/start",
        data={"email": signup_email, "next": "/meetings"},
    )
    assert start.status_code == 200
    state_match = re.search(r'name="state" value="([^"]+)"', start.text)
    code_match = re.search(r"Код для локальной проверки: <strong>(\d{6})</strong>", start.text)
    assert state_match is not None
    assert code_match is not None
    _bind_email_auth_attempt_cookie(client, start, state_nonce=state_match.group(1))
    assert 'action="/sign-up/email/verify"' in start.text
    assert 'name="workspace_id"' not in start.text
    assert str(WORKSPACE_ID) not in start.text

    callback = client.post(
        "/sign-up/email/verify",
        data={
            "email": signup_email,
            "code": code_match.group(1),
            "state": state_match.group(1),
            "next": "/meetings",
        },
        follow_redirects=False,
    )

    assert callback.status_code == 303
    assert callback.headers["location"] == "/meetings"
    session_cookie = callback.cookies.get(AUTH_SESSION_COOKIE_NAME)
    assert session_cookie
    client.cookies.set(AUTH_SESSION_COOKIE_NAME, session_cookie)

    meetings = client.get("/meetings")
    assert meetings.status_code == 200
    assert "Мои встречи" in meetings.text

    async def read_created_identity():
        async with client.app_state["sessionmaker"]() as db:
            identity = await db.scalar(
                select(ExternalIdentity).where(ExternalIdentity.email == signup_email)
            )
            assert identity is not None
            user = await db.get(UserIdentity, identity.user_id)
            assert user is not None
            personal_workspace = await db.scalar(
                select(Workspace).where(
                    Workspace.organization_id == user.organization_id,
                    Workspace.owner_user_id == user.id,
                    Workspace.kind == "personal",
                )
            )
            assert personal_workspace is not None
            membership = await db.get(WorkspaceMembership, (personal_workspace.id, user.id))
            assert membership is not None
            bootstrap_membership = await db.get(WorkspaceMembership, (WORKSPACE_ID, user.id))
            session = await db.scalar(
                select(AuthSession).where(
                    AuthSession.session_token_hash == hash_token(session_cookie),
                )
            )
            assert session is not None
            assert session.workspace_id == personal_workspace.id
            assert bootstrap_membership is None
            return identity

    client.portal.call(read_created_identity)


def test_browser_email_login_reuses_personal_space_after_signup(client) -> None:
    signup_email = "personal-login@example.test"
    started = client.post("/sign-up/email/start", data={"email": signup_email, "next": "/meetings"})
    state_match = re.search(r'name="state" value="([^"]+)"', started.text)
    code_match = re.search(r"Код для локальной проверки: <strong>(\d{6})</strong>", started.text)
    assert state_match is not None
    assert code_match is not None
    _bind_email_auth_attempt_cookie(client, started, state_nonce=state_match.group(1))
    completed = client.post(
        "/sign-up/email/verify",
        data={
            "email": signup_email,
            "code": code_match.group(1),
            "state": state_match.group(1),
            "next": "/meetings",
        },
        follow_redirects=False,
    )
    assert completed.status_code == 303

    login_started = client.post(
        "/login/email/start",
        data={"email": signup_email, "next": "/meetings"},
    )
    login_state_match = re.search(r'name="state" value="([^"]+)"', login_started.text)
    login_code_match = re.search(
        r"Код для локальной проверки: <strong>(\d{6})</strong>", login_started.text
    )
    assert login_started.status_code == 200
    assert login_state_match is not None
    assert login_code_match is not None
    _bind_email_auth_attempt_cookie(
        client,
        login_started,
        state_nonce=login_state_match.group(1),
    )

    callback = client.post(
        "/login/email/verify",
        data={
            "email": signup_email,
            "code": login_code_match.group(1),
            "state": login_state_match.group(1),
            "next": "/meetings",
        },
        follow_redirects=False,
    )
    assert callback.status_code == 303

    async def read_login_session() -> tuple[UUID, UUID]:
        async with client.app_state["sessionmaker"]() as db:
            identity = await db.scalar(
                select(ExternalIdentity).where(ExternalIdentity.email == signup_email)
            )
            assert identity is not None
            personal = await db.scalar(
                select(Workspace).where(
                    Workspace.owner_user_id == identity.user_id,
                    Workspace.kind == "personal",
                )
            )
            assert personal is not None
            token = callback.cookies.get(AUTH_SESSION_COOKIE_NAME)
            assert token is not None
            session = await db.scalar(
                select(AuthSession).where(AuthSession.session_token_hash == hash_token(token))
            )
            assert session is not None
            return session.workspace_id, personal.id

    workspace_id, personal_workspace_id = client.portal.call(read_login_session)
    assert workspace_id == personal_workspace_id


def test_browser_email_signup_fails_closed_for_ambiguous_existing_users(client) -> None:
    ambiguous_email = "ambiguous-owner@example.test"
    first_user_id = uuid4()
    second_user_id = uuid4()

    async def seed() -> UUID:
        async with client.app_state["sessionmaker"]() as db:
            db.add_all(
                (
                    UserIdentity(
                        id=first_user_id,
                        organization_id=ORG_ID,
                        external_subject=str(first_user_id),
                        status="active",
                    ),
                    UserIdentity(
                        id=second_user_id,
                        organization_id=ORG_ID,
                        external_subject=str(second_user_id),
                        status="active",
                    ),
                )
            )
            await db.flush()
            db.add_all(
                (
                    ExternalIdentity(
                        user_id=first_user_id,
                        provider="email",
                        provider_subject=ambiguous_email,
                        email=ambiguous_email,
                        is_active=True,
                        is_verified=True,
                    ),
                    ExternalIdentity(
                        user_id=second_user_id,
                        provider="email",
                        provider_subject=f"duplicate:{ambiguous_email}",
                        email=ambiguous_email.upper(),
                        is_active=True,
                        is_verified=True,
                    ),
                )
            )
            personal = await ensure_personal_workspace(
                db,
                organization_id=ORG_ID,
                user_id=first_user_id,
            )
            await db.commit()
            return personal.id

    first_personal_id = client.portal.call(seed)
    login_start = client.post(
        "/login/email/start",
        data={"email": ambiguous_email, "next": "/meetings"},
    )
    assert login_start.status_code == 400
    assert "несколькими профилями" in login_start.text
    assert "чужие встречи" in login_start.text
    assert "Яндекс ID" in login_start.text
    assert "VK ID" in login_start.text
    assert 'href="/login/yandex/start?' in login_start.text
    assert 'href="/login/vk/start?' in login_start.text
    assert "next=%2Fsettings%2Faccount" in login_start.text
    assert "GRAF откроет настройки" in login_start.text
    assert "Восстановить доступ" in login_start.text
    assert 'action="/login/email/start"' not in login_start.text
    assert 'name="state"' not in login_start.text

    start = client.post(
        "/sign-up/email/start",
        data={"email": ambiguous_email, "next": "/meetings"},
    )
    state_match = re.search(r'name="state" value="([^"]+)"', start.text)
    code_match = re.search(r"Код для локальной проверки: <strong>(\d{6})</strong>", start.text)
    assert start.status_code == 200
    assert state_match is not None
    assert code_match is not None
    _bind_email_auth_attempt_cookie(client, start, state_nonce=state_match.group(1))

    completed = client.post(
        "/sign-up/email/verify",
        data={
            "email": ambiguous_email,
            "code": code_match.group(1),
            "state": state_match.group(1),
            "next": "/meetings",
        },
        follow_redirects=False,
    )

    assert completed.status_code == 400
    assert completed.cookies.get(AUTH_SESSION_COOKIE_NAME) is None
    assert str(AUTH_BOOTSTRAP_WORKSPACE_ID) not in completed.text
    assert "несколькими профилями" in completed.text
    assert "Яндекс ID" in completed.text
    assert "VK ID" in completed.text
    assert "Откройте итоги встречи" not in completed.text

    async def read_result() -> tuple[int, int, tuple[str, str | None]]:
        async with client.app_state["sessionmaker"]() as db:
            sessions = list(
                await db.scalars(
                    select(AuthSession).where(
                        AuthSession.user_id.in_((first_user_id, second_user_id))
                    )
                )
            )
            personal_spaces = list(
                await db.scalars(
                    select(Workspace).where(
                        Workspace.owner_user_id.in_((first_user_id, second_user_id)),
                        Workspace.kind == "personal",
                    )
                )
            )
            state = await db.scalar(
                select(AuthCallbackState).where(
                    AuthCallbackState.state_nonce == state_match.group(1)
                )
            )
            assert state is not None
            assert {workspace.id for workspace in personal_spaces} == {first_personal_id}
            return len(sessions), len(personal_spaces), (state.result, state.error_code)

    assert client.portal.call(read_result) == (
        0,
        1,
        ("failed", "ambiguous_email_recovery_required"),
    )

    client.portal.call(_set_workspace_yandex_policy, client, False)
    client.portal.call(_set_workspace_vk_policy, client, False)
    unavailable = client.post(
        "/login/email/start",
        data={"email": ambiguous_email, "next": "/meetings"},
    )
    assert unavailable.status_code == 400
    assert "Яндекс ID и VK сейчас недоступны" in unavailable.text
    assert 'href="/login/yandex/start?' not in unavailable.text
    assert 'href="/login/vk/start?' not in unavailable.text
    assert 'action="/login/email/start"' not in unavailable.text
    assert "T-Банк ID" not in unavailable.text
    assert "Способ входа" not in unavailable.text


def test_browser_email_signup_code_is_bound_to_started_email(client) -> None:
    client.portal.call(_set_workspace_self_enrollment_policy, client, True)
    signup_email = "attacker-controlled@example.test"
    different_email = "victim@example.test"

    start = client.post(
        "/sign-up/email/start",
        data={"email": signup_email, "next": "/meetings"},
    )
    assert start.status_code == 200
    state_match = re.search(r'name="state" value="([^"]+)"', start.text)
    code_match = re.search(r"Код для локальной проверки: <strong>(\d{6})</strong>", start.text)
    assert state_match is not None
    assert code_match is not None

    callback = client.post(
        "/sign-up/email/verify",
        data={
            "email": different_email,
            "code": code_match.group(1),
            "state": state_match.group(1),
            "next": "/meetings",
        },
        follow_redirects=False,
    )

    assert callback.status_code == 400
    assert callback.cookies.get(AUTH_SESSION_COOKIE_NAME) is None

    async def read_rejected_signup():
        async with client.app_state["sessionmaker"]() as db:
            state_row = await db.scalar(
                select(AuthCallbackState).where(
                    AuthCallbackState.state_nonce == state_match.group(1)
                )
            )
            victim_identity = await db.scalar(
                select(ExternalIdentity).where(ExternalIdentity.email == different_email)
            )
            assert state_row is not None
            return state_row.result, state_row.error_code, victim_identity

    assert client.portal.call(read_rejected_signup) == ("failed", "email_code_invalid", None)


def test_browser_email_signup_creates_a_personal_space_when_corporate_enrollment_is_disabled(
    client,
) -> None:
    signup_email = "closed-signup@example.test"

    start = client.post(
        "/sign-up/email/start",
        data={"email": signup_email, "next": "/meetings"},
    )

    assert start.status_code == 200
    assert 'action="/sign-up/email/verify"' in start.text
    assert "Регистрация в этом кабинете закрыта" not in start.text


def test_browser_email_signup_is_not_retargeted_when_corporate_policy_changes(client) -> None:
    client.portal.call(_set_workspace_self_enrollment_policy, client, True)
    signup_email = "stale-policy-signup@example.test"
    start = client.post(
        "/sign-up/email/start",
        data={"email": signup_email, "next": "/meetings"},
    )
    state_match = re.search(r'name="state" value="([^"]+)"', start.text)
    code_match = re.search(r"Код для локальной проверки: <strong>(\d{6})</strong>", start.text)
    assert state_match is not None
    assert code_match is not None
    _bind_email_auth_attempt_cookie(client, start, state_nonce=state_match.group(1))

    client.portal.call(_set_workspace_self_enrollment_policy, client, False)
    callback = client.post(
        "/sign-up/email/verify",
        data={
            "email": signup_email,
            "code": code_match.group(1),
            "state": state_match.group(1),
            "next": "/meetings",
        },
        follow_redirects=False,
    )

    assert callback.status_code == 303
    assert callback.headers["location"] == "/meetings"
    assert callback.cookies.get(AUTH_SESSION_COOKIE_NAME)


def test_browser_email_login_production_delivery_hides_code(monkeypatch, client) -> None:
    client.app.state.settings.env = "production"
    client.portal.call(_link_owner_email_identity, client)
    deliveries: list[dict[str, object]] = []

    async def fake_send_email_login_code(**kwargs):
        deliveries.append(kwargs)

    monkeypatch.setattr(email_delivery, "send_email_login_code", fake_send_email_login_code)

    start = client.post(
        "/login/email/start",
        data={"email": BROWSER_OWNER_EMAIL, "next": "/meetings"},
    )

    assert start.status_code == 200
    assert "Проверьте почту" in start.text
    assert "Код для локальной проверки" not in start.text
    assert len(deliveries) == 1
    assert deliveries[0]["recipient_email"] == BROWSER_OWNER_EMAIL
    assert re.fullmatch(r"\d{6}", deliveries[0]["code"])


def test_browser_email_login_production_delivery_failure_fails_closed(monkeypatch, client) -> None:
    client.app.state.settings.env = "production"
    client.portal.call(_link_owner_email_identity, client)

    async def fail_send_email_login_code(**_kwargs):
        raise email_delivery.EmailLoginDeliveryError("postal_request_failed")

    monkeypatch.setattr(email_delivery, "send_email_login_code", fail_send_email_login_code)

    response = client.post(
        "/login/email/start",
        data={"email": BROWSER_OWNER_EMAIL, "next": "/meetings"},
    )

    assert response.status_code == 503
    assert "Почтовая доставка временно недоступна" in response.text
    assert "Код для локальной проверки" not in response.text


def test_meetings_page_rejects_missing_web_session_without_legacy_headers(client) -> None:
    response = client.get("/meetings")

    assert response.status_code == 401
    assert response.json()["code"] == "missing_auth_context"


def test_billing_page_uses_normal_login_handoff_without_legacy_error(client) -> None:
    response = client.get(
        "/billing",
        headers={"Accept": "text/html"},
        follow_redirects=False,
    )

    assert response.status_code == 303
    location = response.headers["location"]
    assert "next=%2Fbilling" in location
    assert "error=missing_auth_context" in location
    assert "legacy_header_auth_disabled" not in location


def test_desktop_billing_page_renders_embedded_shell_with_validated_session(client) -> None:
    client.portal.call(_seed_owner_review_session, client)
    response = client.get(
        "/billing",
        headers={
            "Accept": "text/html",
            "X-Auth-Session": OWNER_REVIEW_TEST_TOKEN,
            "X-GRAF-Client": "desktop",
        },
    )

    assert response.status_code == 200
    assert 'data-surface-mode="desktop_embedded"' in response.text
    assert 'href="/desktop/settings"' in response.text
    assert "legacy_header_auth_disabled" not in response.text


def test_corporate_workspace_cannot_open_personal_plan_catalog(client) -> None:
    client.portal.call(_seed_owner_review_session, client)
    client.cookies.set(AUTH_SESSION_COOKIE_NAME, OWNER_REVIEW_TEST_TOKEN)

    response = client.get("/billing/plans", follow_redirects=False)

    assert response.status_code == 303
    assert response.headers["location"] == "/billing?result=personal_only"


def test_personal_owner_with_other_billing_owner_can_read_plan_catalog(client) -> None:
    token = "personal-other-billing-owner-token"
    device_id = UUID("70000000-0000-4000-8000-000000000007")
    billing_owner_id = UUID("80000000-0000-4000-8000-000000000008")

    async def seed() -> None:
        async with client.app_state["sessionmaker"]() as db:
            db.add(
                UserIdentity(
                    id=billing_owner_id,
                    organization_id=ORG_ID,
                    external_subject=str(billing_owner_id),
                    display_name="Historical billing owner",
                )
            )
            await db.flush()
            db.add(
                RegisteredDevice(
                    id=device_id,
                    workspace_id=PERSONAL_WORKSPACE_ID,
                    user_id=USER_ID,
                    device_public_id="personal-plan-reader",
                    status="active",
                    registration_state="approved",
                )
            )
            await db.flush()
            session = AuthSession(
                id=uuid4(),
                user_id=USER_ID,
                workspace_id=PERSONAL_WORKSPACE_ID,
                device_id=device_id,
                provider="billing-plan-test",
                session_token_hash=hash_token(token),
                status="active",
                issued_at=datetime.now(UTC) - timedelta(minutes=1),
                expires_at=datetime.now(UTC) + timedelta(minutes=15),
                claims_fingerprint="billing-plan-other-owner",
            )
            db.add(session)
            db.add(
                WorkspaceSubscription(
                    workspace_id=PERSONAL_WORKSPACE_ID,
                    billing_owner_id=billing_owner_id,
                    state="free",
                    plan_code="free",
                )
            )
            await db.flush()
            db.add(
                AuthSessionDeviceBinding(
                    auth_session_id=session.id,
                    registered_device_id=device_id,
                    device_state="trusted",
                )
            )
            await db.commit()

    client.portal.call(seed)
    client.cookies.set(AUTH_SESSION_COOKIE_NAME, token)

    response = client.get("/billing/plans", follow_redirects=False)

    assert response.status_code == 200
    assert "Тарифы" in response.text
    assert 'href="/billing/checkout"' not in response.text


def test_personal_owner_continues_existing_checkout_without_second_operation(
    monkeypatch,
    client,
) -> None:
    token = "personal-checkout-recovery-token"
    device_id = UUID("70000000-0000-4000-8000-000000000009")
    operation_id = UUID("71000000-0000-4000-8000-000000000009")
    calls: list[dict[str, object]] = []

    async def seed() -> AuthSession:
        async with client.app_state["sessionmaker"]() as db:
            db.add(
                RegisteredDevice(
                    id=device_id,
                    workspace_id=PERSONAL_WORKSPACE_ID,
                    user_id=USER_ID,
                    device_public_id="personal-checkout-recovery",
                    status="active",
                    registration_state="approved",
                )
            )
            await db.flush()
            session = AuthSession(
                id=uuid4(),
                user_id=USER_ID,
                workspace_id=PERSONAL_WORKSPACE_ID,
                device_id=device_id,
                provider="billing-recovery-test",
                session_token_hash=hash_token(token),
                status="active",
                issued_at=datetime.now(UTC) - timedelta(minutes=1),
                expires_at=datetime.now(UTC) + timedelta(minutes=15),
                claims_fingerprint="billing-recovery-test",
            )
            db.add(session)
            await db.flush()
            db.add(
                AuthSessionDeviceBinding(
                    auth_session_id=session.id,
                    registered_device_id=device_id,
                    device_state="trusted",
                )
            )
            operation = BillingOperation(
                id=operation_id,
                workspace_id=PERSONAL_WORKSPACE_ID,
                kind="initial_checkout",
                idempotency_key="existing-provider-key",
                state="manual_resolution",
                provider_key_expires_at=datetime.now(UTC) + timedelta(hours=1),
                request_snapshot={
                    "plan_code": "personal",
                    "cycle": "month",
                    "payable_amount_minor": 1_000,
                    "offer_consent": True,
                    "recurring_consent": True,
                    "receipt_config": {
                        "tax_system_code": 2,
                        "vat_code": 1,
                        "payment_subject": "service",
                        "payment_mode": "full_payment",
                    },
                },
            )
            db.add(operation)
            await db.flush()
            db.add(
                BillingInvoice(
                    workspace_id=PERSONAL_WORKSPACE_ID,
                    operation_id=operation_id,
                    safe_number="INV-RECOVERY9",
                    amount_minor=1_000,
                    currency="RUB",
                    status="manual_resolution",
                    receipt_contact_snapshot="owner@example.test",
                )
            )
            await db.commit()
            return session

    class Provider:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

        async def create_payment(self, **kwargs):
            calls.append(kwargs)
            return {
                "id": "payment-recovery-9",
                "confirmation": {"confirmation_url": "https://yookassa.test/checkout/recovery-9"},
            }

    session = client.portal.call(seed)
    monkeypatch.setattr(billing_routes, "YooKassaClient", lambda _settings: Provider())
    client.app.state.settings.billing_checkout_enabled = True
    client.app.state.settings.billing_emergency_stop = False
    client.app.state.settings.public_base_url = "https://rec.example.test"
    client.cookies.set(AUTH_SESSION_COOKIE_NAME, token)
    csrf_token = issue_csrf_token(
        session_id=session.id,
        secret=str(client.app.state.web_csrf_secret),
    )

    response = client.post(
        "/billing/checkout/status/INV-RECOVERY9/continue",
        data={"csrf_token": csrf_token},
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert response.headers["location"] == "https://yookassa.test/checkout/recovery-9"
    assert len(calls) == 1
    assert calls[0]["idempotence_key"] == "existing-provider-key"

    async def read_result() -> tuple[int, int, str, str | None]:
        async with client.app_state["sessionmaker"]() as db:
            operations = tuple(
                await db.scalars(
                    select(BillingOperation).where(
                        BillingOperation.workspace_id == PERSONAL_WORKSPACE_ID
                    )
                )
            )
            invoices = tuple(
                await db.scalars(
                    select(BillingInvoice).where(
                        BillingInvoice.workspace_id == PERSONAL_WORKSPACE_ID
                    )
                )
            )
            return (
                len(operations),
                len(invoices),
                operations[0].state,
                operations[0].provider_id,
            )

    assert client.portal.call(read_result) == (1, 1, "provider_pending", "payment-recovery-9")

    checkout = client.get("/billing/checkout")
    assert checkout.status_code == 200
    assert "https://yookassa.test/checkout/recovery-9" in checkout.text
    assert "Продолжить этот платёж в ЮKassa" in checkout.text
    assert len(calls) == 1


def test_desktop_billing_handoff_sets_browser_session_once(client, tmp_path) -> None:
    client.portal.call(_seed_owner_review_session, client)
    key_file = tmp_path / "credential-encryption-key"
    key_file.write_bytes(Fernet.generate_key())
    client.app.state.settings.credential_encryption_key_file = key_file

    response = client.post(
        "/api/v1/cabinet/billing/handoff",
        headers={"X-Auth-Session": OWNER_REVIEW_TEST_TOKEN},
    )

    assert response.status_code == 200
    state = response.json()["state"]
    assert state
    handoff = client.get(f"/billing/handoff?state={state}", follow_redirects=False)
    assert handoff.status_code == 303
    assert handoff.headers["location"] == "/billing"
    assert f"{AUTH_SESSION_COOKIE_NAME}=" in handoff.headers["set-cookie"]

    async def read_state() -> tuple[str, str | None]:
        async with client.app_state["sessionmaker"]() as db:
            row = await db.scalar(
                select(AuthCallbackState).where(
                    AuthCallbackState.provider == DESKTOP_BILLING_HANDOFF_PROVIDER,
                    AuthCallbackState.state_nonce == state,
                )
            )
            assert row is not None
            return row.result, row.error_code

    assert client.portal.call(read_state) == ("completed", None)
    replay = client.get(f"/billing/handoff?state={state}", follow_redirects=False)
    assert replay.status_code == 303
    assert replay.headers["location"] == "/login?next=%2Fbilling&error=auth_handoff_invalid"


def test_meetings_page_rejects_invalid_owner_session_cookie(client) -> None:
    client.cookies.set(AUTH_SESSION_COOKIE_NAME, "unknown-session-token")
    response = client.get("/meetings")

    assert response.status_code == 401
    assert response.json()["code"] == "auth_session_invalid"


def test_meetings_page_rejects_expired_owner_session_cookie(client) -> None:
    client.portal.call(
        lambda: _seed_owner_review_session(
            client,
            token="expired-owner-review-token",
            expires_delta=timedelta(minutes=-1),
        )
    )

    client.cookies.set(AUTH_SESSION_COOKIE_NAME, "expired-owner-review-token")
    response = client.get("/meetings")

    assert response.status_code == 401
    assert response.json()["code"] == "auth_session_expired"


def test_meetings_page_rejects_denied_owner_session_device_binding(client) -> None:
    client.portal.call(
        lambda: _seed_owner_review_session(
            client,
            token="denied-owner-review-token",
            device_state="blocked",
        )
    )

    client.cookies.set(AUTH_SESSION_COOKIE_NAME, "denied-owner-review-token")
    response = client.get("/meetings")

    assert response.status_code == 403
    assert response.json()["code"] == "device_revoked"
