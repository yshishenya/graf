from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta
from html import unescape
from urllib.parse import parse_qs, urlsplit
from uuid import uuid4

from sqlalchemy import select

from tests.fakes.auth_contexts import DEVICE_ID, USER_ID, WORKSPACE_ID
from tests.fakes.auth_providers import fake_provider_map
from tests.fixtures.cabinet import seed_cabinet_meetings
from twobrain_rec_server.api.auth import BROWSER_AUTH_STATE_COOKIE_NAME
from twobrain_rec_server.auth import email_delivery
from twobrain_rec_server.auth.csrf import issue_csrf_token
from twobrain_rec_server.auth.dependencies import AUTH_SESSION_COOKIE_NAME
from twobrain_rec_server.auth.sessions import hash_token
from twobrain_rec_server.db.models import (
    AuthAuditEvent,
    AuthCallbackState,
    AuthSession,
    AuthSessionDeviceBinding,
    ExternalIdentity,
    UserIdentity,
    Workspace,
    WorkspaceAuthPolicy,
    WorkspaceMembership,
)

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


async def _set_workspace_yandex_policy(client, enabled: bool) -> None:
    async with client.app_state["sessionmaker"]() as db:
        policy = await db.scalar(select(WorkspaceAuthPolicy).where(WorkspaceAuthPolicy.workspace_id == WORKSPACE_ID))
        if policy is None:
            policy = WorkspaceAuthPolicy(workspace_id=WORKSPACE_ID)
            db.add(policy)
        policy.allow_yandex = enabled
        await db.commit()


async def _set_workspace_vk_policy(client, enabled: bool) -> None:
    async with client.app_state["sessionmaker"]() as db:
        policy = await db.scalar(select(WorkspaceAuthPolicy).where(WorkspaceAuthPolicy.workspace_id == WORKSPACE_ID))
        if policy is None:
            policy = WorkspaceAuthPolicy(workspace_id=WORKSPACE_ID)
            db.add(policy)
        policy.allow_vk = enabled
        await db.commit()


async def _set_workspace_self_enrollment_policy(client, enabled: bool) -> None:
    async with client.app_state["sessionmaker"]() as db:
        policy = await db.scalar(select(WorkspaceAuthPolicy).where(WorkspaceAuthPolicy.workspace_id == WORKSPACE_ID))
        if policy is None:
            policy = WorkspaceAuthPolicy(workspace_id=WORKSPACE_ID)
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
    assert 'href="/download">Скачать GRAF</a>' in response.text
    assert 'type="email"' in response.text
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
    assert '<a class="auth-provider" href="/login/yandex/start?next=%2Fmeetings">' in first_step.text
    assert '<a class="auth-provider" href="/login/vk/start?next=%2Fmeetings">' in first_step.text
    assert "/login/vk/start?next=%2Fmeetings&amp;auth_provider=mail_ru" in first_step.text
    assert "/login/vk/start?next=%2Fmeetings&amp;auth_provider=ok_ru" in first_step.text
    assert "T-Банк ID" in first_step.text
    assert "Sber ID" in first_step.text
    assert "Госуслуги" in first_step.text
    assert "Alfa ID" in first_step.text
    assert "Рабочая почта" in first_step.text
    assert "Telegram" not in first_step.text
    assert "Продолжить через" not in first_step.text
    assert "Workspace ID" not in first_step.text
    assert 'name="workspace_id"' not in first_step.text
    assert email_step.status_code == 200
    assert "Продолжить другим способом" in email_step.text
    assert 'action="/sign-up/email/start"' in email_step.text
    assert "Зарегистрироваться" in email_step.text


def test_browser_yandex_login_start_redirects_to_provider(client) -> None:
    response = client.get(
        "/login/yandex/start?next=/meetings",
        follow_redirects=False,
    )

    assert response.status_code == 303
    assert response.headers["location"].startswith("https://oauth.yandex.ru/authorize?")
    assert "state=" in response.headers["location"]
    assert "redirect_uri=http%3A%2F%2Ftestserver%2Fapi%2Fv1%2Fauth%2Fcallback%2Fyandex" in response.headers["location"]
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

    assert callback.status_code == 400
    assert callback.json()["code"] == "callback_state_invalid"


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
    assert allowed_callback.headers["location"] == (
        f"/meetings/{seeds.ready_id}?calendar_context_action=change"
    )

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
    assert "scope=email+phone" in response.headers["location"]
    assert "code_challenge_method=S256" in response.headers["location"]
    assert "redirect_uri=http%3A%2F%2Ftestserver%2Fapi%2Fv1%2Fauth%2Fcallback%2Fvk" in response.headers["location"]


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


def test_browser_email_login_ignores_public_workspace_id_and_uses_internal_bootstrap(client) -> None:
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
    assert "Не удалось отправить код для этого кабинета" in response.text
    assert "Код для локальной проверки" not in response.text


def test_browser_email_login_flow_sets_cookie_binds_browser_device_and_opens_meetings(client) -> None:
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
    assert 'name="workspace_id"' not in start.text
    assert str(WORKSPACE_ID) not in start.text
    assert 'class="auth-panel"' in start.text
    assert 'class="code-grid"' in start.text
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
    session_cookie = callback.cookies.get(AUTH_SESSION_COOKIE_NAME)
    assert session_cookie
    client.cookies.set(AUTH_SESSION_COOKIE_NAME, session_cookie)

    meetings = client.get("/meetings")
    assert meetings.status_code == 200
    assert "Проектный синк" in meetings.text
    assert "missing_auth_context" not in meetings.text


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


def test_browser_email_login_wrong_code_consumes_state(client) -> None:
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
    wrong_code = "000000" if code != "000000" else "999999"

    wrong = client.post(
        "/login/email/verify",
        data={"email": BROWSER_OWNER_EMAIL, "code": wrong_code, "state": state, "next": "/meetings"},
        follow_redirects=False,
    )
    replay = client.post(
        "/login/email/verify",
        data={"email": BROWSER_OWNER_EMAIL, "code": code, "state": state, "next": "/meetings"},
        follow_redirects=False,
    )

    assert wrong.status_code == 400
    assert replay.status_code == 400
    assert replay.cookies.get(AUTH_SESSION_COOKIE_NAME) is None

    async def state_result() -> tuple[str, str | None]:
        async with client.app_state["sessionmaker"]() as db:
            state_row = await db.scalar(select(AuthCallbackState).where(AuthCallbackState.state_nonce == state))
            assert state_row is not None
            return state_row.result, state_row.error_code

    assert client.portal.call(state_result) == ("failed", "email_code_invalid")


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
                select(AuthCallbackState).where(AuthCallbackState.state_nonce == state_match.group(1))
            )
            victim_identity = await db.scalar(select(ExternalIdentity).where(ExternalIdentity.email == different_email))
            assert state_row is not None
            return state_row.result, state_row.error_code, victim_identity

    assert client.portal.call(read_rejected_signup) == ("failed", "email_code_invalid", None)


def test_browser_email_signup_creates_a_personal_space_when_corporate_enrollment_is_disabled(client) -> None:
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
