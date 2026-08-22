from datetime import UTC, datetime, timedelta
from pathlib import Path
from types import SimpleNamespace

from starlette.requests import Request
from starlette.responses import Response

SERVER_ROOT = Path(__file__).resolve().parents[2]
REPO_ROOT = SERVER_ROOT.parents[1]


def test_local_files_and_dev_auth_contract() -> None:
    seed = (SERVER_ROOT / "scripts/seed_dev_identity.py").read_text()
    compose = (REPO_ROOT / "infra/docker-compose.local.yml").read_text()
    start = (REPO_ROOT / "infra/scripts/start-local.sh").read_text()
    app = (REPO_ROOT / "apps/macos/Scripts/run-local-app.sh").read_text()
    bundled_app = (REPO_ROOT / "apps/macos/Scripts/build-local-app.sh").read_text()
    assert "ExternalIdentity" in seed and "local@graf.test" in seed
    assert "127.0.0.1:54330:5432" in compose
    assert "127.0.0.1:9010:9000" in compose
    assert "TWOBRAIN_ENV=development" in start
    assert "TWOBRAIN_LOCAL_HTTP_AUTH_COOKIE_ENABLED=true" in start
    assert "TWOBRAIN_LOCAL_EMAIL_LOGIN_CODE=000000" in start
    assert "GRAF_CREDENTIAL_ENCRYPTION_KEY_FILE" in start
    assert "cd-remote.sh" not in start
    assert "twobrain_rec_server.main:create_app --factory" in start
    assert "GRAF_CABINET_REQUIRE_EXPLICIT_BASE_URL=1" in app
    assert "GRAF_LOCAL_APP=1" in app
    assert 'BUILD_DIR="${GRAF_LOCAL_APP_BUILD_DIR:-$MACOS_DIR/.build/local}"' in bundled_app
    assert "pro.2brain.graf.local" in bundled_app
    assert "GRAF_CABINET_BASE_URL=http://127.0.0.1:8081" in bundled_app
    assert "GRAF_UPLOAD_BASE_URL=http://127.0.0.1:8081" in bundled_app
    assert "GRAF_LOCAL_APP=1" in bundled_app
    assert "SUFeedURL" not in bundled_app
    assert 'open "$APP_BUNDLE"' in bundled_app


def test_local_http_cookie_is_explicit_and_not_secure() -> None:
    from twobrain_rec_server.auth.dependencies import (
        AUTH_SESSION_COOKIE_NAME,
        DEV_AUTH_SESSION_COOKIE_NAME,
        auth_session_cookie_name,
        auth_session_cookie_secure,
    )
    from twobrain_rec_server.cabinet.web_routes.auth_email_flow import _set_browser_auth_cookie

    request = Request({
        "type": "http", "scheme": "http", "server": ("127.0.0.1", 8081),
        "path": "/", "headers": [], "query_string": b"",
        "app": SimpleNamespace(state=SimpleNamespace(settings=SimpleNamespace(
            env="development", local_http_auth_cookie_enabled=True)))
    })
    assert auth_session_cookie_name(request) == DEV_AUTH_SESSION_COOKIE_NAME
    assert not auth_session_cookie_secure(request)
    response = Response()
    _set_browser_auth_cookie(request, response, token="synthetic", expires_at=datetime.now(UTC) + timedelta(minutes=5))
    assert f"{DEV_AUTH_SESSION_COOKIE_NAME}=synthetic" in response.headers["set-cookie"]
    assert "Secure" not in response.headers["set-cookie"]
    ordinary = Request({**request.scope, "app": SimpleNamespace(state=SimpleNamespace(settings=SimpleNamespace(env="development", local_http_auth_cookie_enabled=False)))})
    assert auth_session_cookie_name(ordinary) == AUTH_SESSION_COOKIE_NAME
