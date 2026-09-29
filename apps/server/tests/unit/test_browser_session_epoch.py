from datetime import UTC, datetime, timedelta
from http.cookies import SimpleCookie

from fastapi import Request
from starlette.responses import Response

from twobrain_rec_server.api.auth import _set_auth_cookie
from twobrain_rec_server.auth.session_epoch import (
    DEV_SESSION_EPOCH_COOKIE,
    SESSION_EPOCH_COOKIE,
    rotate_browser_session_epoch,
)
from twobrain_rec_server.cabinet.web_routes.auth_email_flow import _set_browser_auth_cookie


def _cookies(response):
    result = SimpleCookie()
    for header in response.headers.getlist("set-cookie"):
        result.load(header)
    return result


def test_epoch_is_random_non_authorizing_host_cookie_and_logout_rotates_legacy_session():
    response = Response()
    rotate_browser_session_epoch(response, secure=True)
    marker = _cookies(response)[SESSION_EPOCH_COOKIE]
    assert len(marker.value) == 32
    assert marker["secure"] and not marker["httponly"]
    assert marker["path"] == "/" and not marker["domain"]
    assert marker["samesite"] == "lax" and marker["max-age"] == "60"
    second = Response()
    rotate_browser_session_epoch(second, secure=True)
    assert _cookies(second)[SESSION_EPOCH_COOKIE].value != marker.value
    development = Response()
    rotate_browser_session_epoch(development, secure=False)
    assert DEV_SESSION_EPOCH_COOKIE in _cookies(development)
    assert not _cookies(development)[DEV_SESSION_EPOCH_COOKIE]["secure"]


def test_both_cookie_issuers_rotate_epoch_without_exposing_auth_token():
    expires = datetime.now(UTC) + timedelta(hours=1)
    for issue in [
        lambda response: _set_auth_cookie(
            response, token="synthetic-auth-secret", expires_at=expires
        ),
        lambda response: _set_browser_auth_cookie(
            Request(
                {"type": "http", "scheme": "https", "headers": [], "server": ("graf.test", 443)}
            ),
            response,
            token="synthetic-auth-secret",
            expires_at=expires,
        ),
    ]:
        response = Response()
        issue(response)
        cookies = _cookies(response)
        assert cookies["__Host-twobrain_rec_owner_session"]["httponly"]
        epoch = cookies[SESSION_EPOCH_COOKIE]
        assert epoch.value != "synthetic-auth-secret"
        assert int(epoch["max-age"]) > 3500
