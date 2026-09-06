from unittest.mock import AsyncMock

import pytest
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from fastapi.testclient import TestClient

from twobrain_rec_server.cabinet import rendering
from twobrain_rec_server.cabinet.web_routes import settings


@pytest.mark.parametrize("prefix", ["", "/desktop"])
@pytest.mark.parametrize(
    "path", ["/settings/account", "/account", "/account/profile", "/account/security"]
)
def test_account_routes_forward_existing_result_markers(monkeypatch, prefix, path):
    app = FastAPI()
    app.include_router(settings.router)
    for dependency in (
        settings.PrincipalDependency,
        settings.WebTenantDependency,
        settings.WebDbDependency,
    ):
        app.dependency_overrides[dependency.dependency] = lambda: None
    render = AsyncMock(return_value=HTMLResponse("synthetic account"))
    monkeypatch.setattr(settings, "_render_settings", render)

    with TestClient(app) as client:
        response = client.get(prefix + path + "?profile=saved&account_close=canceled")

    assert response.status_code == 200
    assert render.await_args.kwargs["profile"] == "saved"
    assert render.await_args.kwargs["account_close"] == "canceled"
    assert render.await_args.kwargs["embedded"] is bool(prefix)


@pytest.mark.parametrize("embedded", [False, True])
@pytest.mark.parametrize(
    ("marker", "value", "kind"),
    [
        ("device_revoke_result", "failed", "error"),
        ("device_revoke_result", "revoked", "success"),
        ("device_revoke_result", "others_revoked", "success"),
        ("session_result", "revoked", "success"),
        ("session_result", "others_revoked", "success"),
        ("account_close_result", "scheduled", "success"),
        ("account_close_result", "canceled", "success"),
        *[
            (marker, "reauth_required", "warning")
            for marker in (
                "device_revoke_result",
                "session_result",
                "account_close_result",
                "provider_link_result",
                "provider_unlink_result",
            )
        ],
    ],
)
def test_account_outcomes_are_truthful_and_reauth_is_actionable(
    monkeypatch, embedded, marker, value, kind
):
    with monkeypatch.context() as capture:
        capture.setattr(rendering, "_page_shell", lambda _title, **context: context)
        context = rendering.render_settings_page(
            embedded=embedded, category="account", **{marker: value}
        )
    assert context["account_outcome"]["kind"] == kind
    assert context["requires_account_reauth"] is (value == "reauth_required")

    page = rendering.render_settings_page(
        embedded=embedded, category="account", csrf_token="synthetic-csrf", **{marker: value}
    )
    if kind == "error":
        assert "settings-status--error" in page
        assert 'role="alert"' in page
        assert "Настройки обновлены" not in page
    if value == "reauth_required":
        action = "/desktop/meetings" if embedded else "/logout"
        destination = "/desktop/settings/account" if embedded else "/settings/account"
        assert f'<form action="{action}" method="post">' in page
        assert 'name="csrf_token" value="synthetic-csrf"' in page
        assert f'name="next" value="/login?next={destination}"' in page
        assert ">Войти снова</button>" in page
        assert "Настройки обновлены" not in page


def test_unknown_results_do_not_claim_success_and_success_cannot_hide_errors(monkeypatch):
    monkeypatch.setattr(rendering, "_page_shell", lambda _title, **context: context)
    context = rendering.render_settings_page(
        category="account", device_revoke_result="unknown", account_close_result="unknown"
    )
    assert context["account_outcome"] is None
    assert context["requires_account_reauth"] is False

    context = rendering.render_settings_page(
        category="account", provider_unlink_result="success", device_revoke_result="failed"
    )
    assert context["account_outcome"]["kind"] == "error"
    assert "Не удалось отозвать устройство" in context["account_outcome"]["detail"]
