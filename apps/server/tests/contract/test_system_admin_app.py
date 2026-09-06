"""The standalone console fails closed without its own deployment settings."""

import pytest
from fastapi.testclient import TestClient

from twobrain_rec_server.system_admin.app import CSRF_COOKIE, create_app, public_origin


def test_disabled_console_requires_no_secrets(monkeypatch):
    monkeypatch.delenv("SYSTEM_ADMIN_ENABLED", raising=False)
    with TestClient(create_app()) as client:
        response = client.get("/health")
        assert response.status_code == 503
        assert response.headers["cache-control"] == "no-store"
        assert "frame-ancestors 'none'" in response.headers["content-security-policy"]


@pytest.mark.parametrize("origin", ["http://admin.example.invalid", "https://a.invalid/path",
                                     "https://user@a.invalid", "https://a.invalid?x=1"])
def test_invalid_origin_rejected(origin):
    with pytest.raises(ValueError):
        public_origin(origin)


def test_origin_csrf_and_no_credentialed_cors(monkeypatch):
    monkeypatch.setenv("SYSTEM_ADMIN_ENABLED", "true")
    monkeypatch.setenv("SYSTEM_ADMIN_PUBLIC_ORIGIN", "https://admin.example.invalid")
    # Middleware proof without starting a DB. Full lifecycle uses PostgreSQL tests.
    client = TestClient(create_app(), base_url="https://admin.example.invalid")
    response = client.get("/api/system-admin/v1/auth/csrf")
    token = response.json()["csrf_token"]
    assert client.get("/api/system-admin/v1/auth/csrf").json()["csrf_token"] == token
    cookie = response.headers["set-cookie"]
    for part in (CSRF_COOKIE, "HttpOnly", "Secure", "SameSite=strict", "Path=/"):
        assert part in cookie
    assert "Domain=" not in cookie
    for origin in (None, "null", "https://product.example.invalid"):
        headers = {"x-csrf-token": token}
        if origin:
            headers["origin"] = origin
        response = client.post("/api/system-admin/v1/auth/login", headers=headers)
        assert response.status_code == 403
        assert "access-control-allow-origin" not in response.headers
    assert client.get("/health", headers={"host": "product.example.invalid"}).status_code == 400
    assert client.get("/openapi.json").status_code == 404


def test_login_body_limit_and_validation_do_not_reflect_secrets(monkeypatch):
    monkeypatch.setenv("SYSTEM_ADMIN_ENABLED", "true")
    monkeypatch.setenv("SYSTEM_ADMIN_PUBLIC_ORIGIN", "https://admin.example.invalid")
    client = TestClient(create_app(), base_url="https://admin.example.invalid")
    token = client.get("/api/system-admin/v1/auth/csrf").json()["csrf_token"]
    client.headers.update({"origin": "https://admin.example.invalid", "x-csrf-token": token})
    response = client.post("/api/system-admin/v1/auth/login", json={"password": "synthetic secret"})
    assert response.status_code == 422
    assert "synthetic secret" not in response.text
    response = client.post("/api/system-admin/v1/auth/login", content=b"x"*70000)
    assert response.status_code == 413
