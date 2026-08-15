from __future__ import annotations

from starlette.requests import Request

from twobrain_rec_server.auth.dependencies import (
    AUTH_SESSION_COOKIE_NAME,
    _extract_session_token,
    is_web_cookie_session,
)


def test_session_cookie_name_uses_host_prefix_contract() -> None:
    assert AUTH_SESSION_COOKIE_NAME == "__Host-twobrain_rec_owner_session"


def test_extract_session_token_prefers_explicit_session_header() -> None:
    assert _extract_session_token("Bearer bearer-token", " header-token ", "cookie-token") == "header-token"


def test_extract_session_token_accepts_cookie_before_authorization_fallback() -> None:
    assert _extract_session_token("Bearer bearer-token", None, " cookie-token ") == "cookie-token"


def test_extract_session_token_returns_none_when_session_material_missing() -> None:
    assert _extract_session_token(None, None, None) is None


def _request(*, cookie: str | None = None, headers: list[tuple[bytes, bytes]] = ()) -> Request:
    raw_headers = list(headers)
    if cookie is not None:
        raw_headers.append((b"cookie", f"{AUTH_SESSION_COOKIE_NAME}={cookie}".encode()))
    return Request({"type": "http", "method": "POST", "path": "/settings/account/close", "headers": raw_headers})


def test_destructive_web_actions_require_cookie_transport() -> None:
    assert is_web_cookie_session(_request(cookie="session")) is True
    assert is_web_cookie_session(_request(headers=[(b"x-auth-session", b"session")])) is False
    assert is_web_cookie_session(_request(headers=[(b"authorization", b"Bearer session")])) is False
    assert is_web_cookie_session(
        _request(cookie="session", headers=[(b"x-auth-session", b"session")])
    ) is False
