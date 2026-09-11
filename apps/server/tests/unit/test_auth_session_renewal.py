from datetime import UTC, datetime, timedelta
from unittest.mock import patch

import pytest
from sqlalchemy import select

from tests.fakes.auth_contexts import DEVICE_ID, USER_ID, WORKSPACE_ID
from twobrain_rec_server.auth.dependencies import AUTH_SESSION_COOKIE_NAME
from twobrain_rec_server.auth.sessions import hash_token, record_session_activity, session_expiry
from twobrain_rec_server.config import Settings
from twobrain_rec_server.db.models import AuthSession, AuthSessionDeviceBinding

TOKEN = "synthetic-renewal-session"


def seed(client, *, status="active", expires=None, binding_state=None):
    async def create():
        async with client.app_state["sessionmaker"]() as db:
            row = AuthSession(user_id=USER_ID, workspace_id=WORKSPACE_ID, provider="email",
                session_token_hash=hash_token(TOKEN), status=status,
                issued_at=datetime.now(UTC) - timedelta(days=1),
                last_seen_at=datetime.now(UTC) - timedelta(minutes=10),
                expires_at=expires or datetime.now(UTC) + timedelta(minutes=10))
            db.add(row)
            await db.flush()
            if binding_state:
                db.add(AuthSessionDeviceBinding(auth_session_id=row.id,
                    registered_device_id=DEVICE_ID, device_state=binding_state))
            await db.commit()
            return row.id
    return client.portal.call(create)


def deadline(client, session_id):
    async def read():
        async with client.app_state["sessionmaker"]() as db:
            return await db.scalar(select(AuthSession.expires_at).where(AuthSession.id == session_id))
    return client.portal.call(read)


def test_default_is_thirty_days_and_upload_remains_one_day():
    now = datetime.now(UTC)
    assert Settings().auth_session_ttl_seconds == 30 * 86400
    assert session_expiry(now) == now + timedelta(days=30)
    assert Settings().upload_session_ttl_seconds == 86400


@pytest.mark.parametrize("transport", ["native", "cookie"])
def test_active_daily_session_renews_and_redelivers_lost_response(client, transport):
    session_id = seed(client)
    headers = {"X-Workspace-Id": str(WORKSPACE_ID)}
    headers["X-Auth-Session" if transport == "native" else "Cookie"] = (
        TOKEN if transport == "native" else f"{AUTH_SESSION_COOKIE_NAME}={TOKEN}")
    response = client.get("/api/v1/auth/me", headers=headers)
    assert response.status_code == 200
    expires = deadline(client, session_id)
    assert datetime.now(UTC) + timedelta(days=29) < expires < datetime.now(UTC) + timedelta(days=30)
    if transport == "native":
        assert int(response.headers["X-GRAF-Auth-Expires-At"]) == int(expires.timestamp())
        assert "set-cookie" not in response.headers
    else:
        cookie = response.headers["set-cookie"]
        assert f"{AUTH_SESSION_COOKIE_NAME}={TOKEN}" in cookie
        assert "HttpOnly" in cookie and "Secure" in cookie and "SameSite=lax" in cookie
        assert "Path=/" in cookie and "Domain=" not in cookie
    repeated = client.get("/api/v1/auth/me", headers=headers)
    assert repeated.status_code == 200
    assert deadline(client, session_id) == expires
    assert repeated.headers.get("X-GRAF-Auth-Expires-At") == response.headers.get("X-GRAF-Auth-Expires-At")
    assert repeated.headers["cache-control"] == "no-store"


@pytest.mark.parametrize(("status", "expiry_delta", "binding", "expected"), [
    ("active", -1, None, 401), ("active", 0, None, 401),
    ("revoked", 600, None, 401), ("active", 600, "blocked", 403),
])
def test_expired_revoked_or_blocked_never_renew(client, status, expiry_delta, binding, expected):
    expires = datetime.now(UTC) + timedelta(seconds=expiry_delta)
    session_id = seed(client, status=status, expires=expires, binding_state=binding)
    response = client.get("/api/v1/auth/me", headers={"X-Auth-Session": TOKEN,
        "X-Workspace-Id": str(WORKSPACE_ID)})
    assert response.status_code == expected
    assert "X-GRAF-Auth-Expires-At" not in response.headers
    assert "set-cookie" not in response.headers
    assert deadline(client, session_id) == expires


def test_activity_survives_original_thirty_days_but_not_idle_boundary(client):
    session_id = seed(client)
    async def exercise():
        async with client.app_state["sessionmaker"]() as db:
            row = await db.get(AuthSession, session_id)
            now = datetime.now(UTC)
            for day in (0, 20, 40):
                expires = await record_session_activity(db, row, None,
                    now=now + timedelta(days=day), ttl_seconds=30 * 86400)
                assert expires == now + timedelta(days=day + 30)
            assert await record_session_activity(db, row, None,
                now=now + timedelta(days=70), ttl_seconds=30 * 86400) is None
    client.portal.call(exercise)


def test_custom_short_ttl_and_out_of_order_requests_do_not_shorten(client):
    session_id = seed(client)
    async def exercise():
        async with client.app_state["sessionmaker"]() as db:
            row = await db.get(AuthSession, session_id)
            now = datetime.now(UTC)
            row.expires_at = now + timedelta(seconds=60)
            row.last_seen_at = now
            await db.flush()
            expires = await record_session_activity(db, row, None,
                now=now + timedelta(seconds=40), ttl_seconds=60)
            assert expires == now + timedelta(seconds=100)
            assert await record_session_activity(db, row, None,
                now=now + timedelta(seconds=35), ttl_seconds=60) == expires
    client.portal.call(exercise)


def test_commit_failure_does_not_deliver_renewal(client):
    from sqlalchemy.ext.asyncio import AsyncSession

    seed(client)
    with (
        patch.object(AsyncSession, "commit", side_effect=RuntimeError("synthetic commit failure")),
        pytest.raises(RuntimeError, match="synthetic commit failure"),
    ):
        client.get("/api/v1/auth/me", headers={"X-Auth-Session": TOKEN,
            "X-Workspace-Id": str(WORKSPACE_ID)})


def test_registry_repeated_304_delivers_committed_deadline(client):
    session_id = seed(client, binding_state="trusted")
    headers = {"X-Auth-Session": TOKEN, "X-Workspace-Id": str(WORKSPACE_ID)}
    path = "/api/v1/desktop/meeting-detection/target-registry"
    response = client.get(path, headers=headers)
    assert response.status_code == 200
    headers["If-None-Match"] = response.headers["ETag"]
    for _ in range(2):
        response = client.get(path, headers=headers)
        assert response.status_code == 304
        assert int(response.headers["X-GRAF-Auth-Expires-At"]) == int(deadline(client, session_id).timestamp())


@pytest.mark.parametrize("path", ["/logout", "/desktop/meetings"])
def test_logout_does_not_renew_and_late_token_remains_rejected(client, path):
    from twobrain_rec_server.auth.csrf import issue_csrf_token

    session_id = seed(client)
    expires = deadline(client, session_id)
    csrf = issue_csrf_token(session_id=session_id, secret=client.app.state.web_csrf_secret)
    headers = {"Cookie": f"{AUTH_SESSION_COOKIE_NAME}={TOKEN}", "X-CSRF-Token": csrf}
    response = client.post(path, headers=headers, follow_redirects=False)
    assert response.status_code == 303
    assert "Max-Age=0" in response.headers["set-cookie"]
    assert "X-GRAF-Auth-Expires-At" not in response.headers
    assert deadline(client, session_id) == expires
    response = client.get("/api/v1/auth/me", headers={"X-Auth-Session": TOKEN})
    assert response.status_code == 401


@pytest.mark.parametrize("delete", [False, True])
def test_route_cookie_takes_priority_over_renewal(delete):
    import asyncio
    from types import SimpleNamespace

    from starlette.requests import Request
    from starlette.responses import Response

    from twobrain_rec_server.auth.session_renewal import session_renewal_middleware

    request = Request({"type": "http", "method": "GET", "path": "/",
        "headers": [(b"cookie", f"{AUTH_SESSION_COOKIE_NAME}={TOKEN}".encode())],
        "app": SimpleNamespace(state=SimpleNamespace(settings=Settings()))})
    request.state.auth_session_renewal = (TOKEN, datetime.now(UTC) + timedelta(days=30))
    response = Response(status_code=200)
    if delete:
        response.delete_cookie(AUTH_SESSION_COOKIE_NAME)
    else:
        response.set_cookie(AUTH_SESSION_COOKIE_NAME, "synthetic-new-login")
    original = response.headers.getlist("set-cookie")
    async def next_response(_):
        return response
    result = asyncio.run(session_renewal_middleware(request, next_response))
    assert result.headers.getlist("set-cookie") == original
    assert "X-GRAF-Auth-Expires-At" not in result.headers


def test_rejected_device_context_does_not_extend_otherwise_valid_session(client):
    session_id = seed(client)
    expires = deadline(client, session_id)
    response = client.get("/api/v1/desktop/meeting-detection/target-registry",
        headers={"X-Auth-Session": TOKEN, "X-Workspace-Id": str(WORKSPACE_ID)})
    assert response.status_code == 401
    assert response.json()["code"] == "auth_session_mismatched"
    assert deadline(client, session_id) == expires
    assert "X-GRAF-Auth-Expires-At" not in response.headers


def test_renewal_commit_failure_preserves_success_without_publishing_deadline(client):
    from sqlalchemy.exc import SQLAlchemyError
    from sqlalchemy.ext.asyncio import AsyncSession

    session_id = seed(client)
    expires = deadline(client, session_id)
    original_commit = AsyncSession.commit

    async def mark_renewal(db, *args, **kwargs):
        result = await record_session_activity(db, *args, **kwargs)
        db.info["synthetic_renewal"] = True
        return result

    async def fail_renewal_commit(db):
        if db.info.get("synthetic_renewal"):
            raise SQLAlchemyError("synthetic renewal commit failure")
        return await original_commit(db)

    with patch("twobrain_rec_server.auth.session_renewal.record_session_activity", mark_renewal), \
         patch.object(AsyncSession, "commit", fail_renewal_commit):
        response = client.get("/api/v1/auth/me", headers={"X-Auth-Session": TOKEN,
            "X-Workspace-Id": str(WORKSPACE_ID)})
    assert response.status_code == 200
    assert "X-GRAF-Auth-Expires-At" not in response.headers
    assert deadline(client, session_id) == expires
