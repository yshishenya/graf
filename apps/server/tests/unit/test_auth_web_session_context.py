from __future__ import annotations

from twobrain_rec_server.auth.dependencies import AUTH_SESSION_COOKIE_NAME, _extract_session_token


def test_session_cookie_name_uses_host_prefix_contract() -> None:
    assert AUTH_SESSION_COOKIE_NAME == "__Host-twobrain_rec_owner_session"


def test_extract_session_token_prefers_explicit_session_header() -> None:
    assert _extract_session_token("Bearer bearer-token", " header-token ", "cookie-token") == "header-token"


def test_extract_session_token_accepts_cookie_before_authorization_fallback() -> None:
    assert _extract_session_token("Bearer bearer-token", None, " cookie-token ") == "cookie-token"


def test_extract_session_token_returns_none_when_session_material_missing() -> None:
    assert _extract_session_token(None, None, None) is None
