from __future__ import annotations

import re
from datetime import UTC, datetime, timedelta
from uuid import uuid4

from sqlalchemy import select

from tests.fakes.auth_contexts import DEVICE_ID, USER_ID, WORKSPACE_ID
from tests.fixtures.cabinet import seed_cabinet_meetings
from twobrain_rec_server.auth import email_delivery
from twobrain_rec_server.auth.dependencies import AUTH_SESSION_COOKIE_NAME
from twobrain_rec_server.auth.sessions import hash_token
from twobrain_rec_server.db.models import (
    AuthSession,
    AuthSessionDeviceBinding,
    ExternalIdentity,
    UserIdentity,
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

        assert response.status_code == 204
        assert response.content == b""


def test_meetings_page_accepts_owner_session_cookie_without_legacy_headers(client) -> None:
    seed_cabinet_meetings(client)
    client.portal.call(_seed_owner_review_session, client)

    response = client.get(
        "/meetings",
        cookies={AUTH_SESSION_COOKIE_NAME: OWNER_REVIEW_TEST_TOKEN},
    )

    assert response.status_code == 200
    assert "Мои встречи" in response.text
    assert "missing_auth_context" not in response.text


def test_desktop_meetings_page_accepts_owner_session_cookie_without_legacy_headers(client) -> None:
    seed_cabinet_meetings(client)
    client.portal.call(_seed_owner_review_session, client)

    response = client.get(
        "/desktop/meetings",
        cookies={AUTH_SESSION_COOKIE_NAME: OWNER_REVIEW_TEST_TOKEN},
    )

    assert response.status_code == 200
    assert "desktop-embedded" in response.text
    assert "Мои встречи" in response.text
    assert "missing_auth_context" not in response.text


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
    assert 'type="email"' in response.text
    assert "Продолжить" in response.text
    assert "Другие способы входа" in response.text
    assert "Продолжить через Яндекс ID" in response.text
    assert "Продолжить через VK ID" in response.text
    assert "Продолжить через Telegram" in response.text
    assert "скоро" in response.text
    assert "Workspace ID" not in response.text
    assert 'name="workspace_id"' not in response.text
    assert str(WORKSPACE_ID) not in response.text


def test_browser_signup_page_matches_email_choice_flow_without_workspace_field(client) -> None:
    first_step = client.get("/sign-up?next=/meetings")
    email_step = client.get("/sign-up?next=/meetings&mode=email")

    assert first_step.status_code == 200
    assert "Зарегистрируйтесь бесплатно" in first_step.text
    assert "Продолжить через Яндекс ID" in first_step.text
    assert "Продолжить с email" in first_step.text
    assert "Workspace ID" not in first_step.text
    assert 'name="workspace_id"' not in first_step.text
    assert email_step.status_code == 200
    assert "Продолжить другим способом" in email_step.text
    assert 'action="/sign-up/email/start"' in email_step.text
    assert "Зарегистрироваться" in email_step.text


def test_browser_provider_login_routes_are_explicit_stubs(client) -> None:
    response = client.get(
        "/login/yandex/start?next=/meetings",
        follow_redirects=False,
    )

    assert response.status_code == 501
    assert "Этот способ входа появится позже" in response.text
    assert "location" not in response.headers


def test_browser_email_login_start_rejects_unknown_workspace_without_code(client) -> None:
    response = client.post(
        "/login/email/start",
        data={"email": BROWSER_OWNER_EMAIL, "workspace_id": str(uuid4()), "next": "/meetings"},
    )

    assert response.status_code == 400
    assert "Не удалось отправить код для этого кабинета" in response.text
    assert "Код для локальной проверки" not in response.text


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

    meetings = client.get("/meetings", cookies={AUTH_SESSION_COOKIE_NAME: session_cookie})
    assert meetings.status_code == 200
    assert "Проектный синк" in meetings.text
    assert "missing_auth_context" not in meetings.text


def test_browser_email_signup_flow_creates_user_and_opens_meetings(client) -> None:
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

    meetings = client.get("/meetings", cookies={AUTH_SESSION_COOKIE_NAME: session_cookie})
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
            membership = await db.get(WorkspaceMembership, (WORKSPACE_ID, user.id))
            assert membership is not None
            return identity

    client.portal.call(read_created_identity)


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
    response = client.get("/meetings", cookies={AUTH_SESSION_COOKIE_NAME: "unknown-session-token"})

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

    response = client.get("/meetings", cookies={AUTH_SESSION_COOKIE_NAME: "expired-owner-review-token"})

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

    response = client.get("/meetings", cookies={AUTH_SESSION_COOKIE_NAME: "denied-owner-review-token"})

    assert response.status_code == 403
    assert response.json()["code"] == "device_revoked"
