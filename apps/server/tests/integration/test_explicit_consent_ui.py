import json
import os
import shutil
import subprocess
import threading
import time
from datetime import UTC, datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from uuid import uuid4

import pytest

from tests.fakes.auth_contexts import duplicate_account_fixture
from tests.integration.test_account_merge import _seed_empty_source
from tests.integration.test_cabinet_csrf import (
    OWNER_REVIEW_TEST_TOKEN,
    _seed_owner_review_session,
)
from tests.integration.test_explicit_product_funnel import setup
from twobrain_rec_server.auth.dependencies import AUTH_SESSION_COOKIE_NAME
from twobrain_rec_server.auth.sessions import hash_token
from twobrain_rec_server.db.models import AuthSession, AuthSessionDeviceBinding, RegisteredDevice


@pytest.mark.browser
def test_real_notice_cookie_auth_consent_and_postgres(client, monkeypatch):
    node_modules = os.environ.get("GRAF_NODE_MODULES")
    if not node_modules or not shutil.which("node"):
        pytest.skip(
            "Set GRAF_NODE_MODULES to existing Playwright dependencies for headless UI proof"
        )
    original = client.app.state.settings
    cfg, provider = setup(client, monkeypatch)
    cfg = original.model_copy(update={name: getattr(cfg, name) for name in cfg.model_fields_set})
    monkeypatch.setattr(client.app.state, "settings", cfg)
    client.portal.call(_seed_owner_review_session, client)
    client.cookies.set(AUTH_SESSION_COOKIE_NAME, OWNER_REVIEW_TEST_TOKEN)

    async def seed_second_account():
        account = duplicate_account_fixture(7477)
        async with client.app_state["sessionmaker"]() as db:
            await _seed_empty_source(
                db, user_id=account.user_id, workspace_id=account.workspace_id, email=account.email
            )
            device_id = uuid4()
            session_id = uuid4()
            db.add(
                RegisteredDevice(
                    id=device_id,
                    workspace_id=account.workspace_id,
                    user_id=account.user_id,
                    device_public_id="consent-ui-synthetic-B",
                    status="active",
                )
            )
            await db.flush()
            db.add(
                AuthSession(
                    id=session_id,
                    device_id=device_id,
                    user_id=account.user_id,
                    workspace_id=account.workspace_id,
                    provider="consent_ui_test",
                    session_token_hash=hash_token("consent-ui-synthetic-B"),
                    status="active",
                    issued_at=datetime.now(UTC) - timedelta(minutes=1),
                    expires_at=datetime.now(UTC) + timedelta(minutes=15),
                )
            )
            await db.flush()
            db.add(
                AuthSessionDeviceBinding(
                    auth_session_id=session_id,
                    registered_device_id=device_id,
                    device_state="trusted",
                )
            )
            await db.commit()

    client.portal.call(seed_second_account)
    scenario = {"writes": 0}

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *_):
            pass

        def do_POST(self):
            self.forward()

        def do_GET(self):
            self.forward()

        def do_PUT(self):
            self.forward()

        def respond(self, status, body, content_type="application/json"):
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.end_headers()
            self.wfile.write(body)

        def forward(self):
            body = self.rfile.read(int(self.headers.get("Content-Length", 0)))
            if self.path == "/__scenario":
                scenario.update(json.loads(body))
                if "switchAccount" in scenario:
                    token = (
                        "consent-ui-synthetic-B"
                        if scenario["switchAccount"] == "B"
                        else OWNER_REVIEW_TEST_TOKEN
                    )
                    client.cookies.set(AUTH_SESSION_COOKIE_NAME, token)
                monkeypatch.setattr(
                    client.app.state,
                    "settings",
                    cfg.model_copy(update={"public_analytics_consent_copy_version": "synthetic-v2"})
                    if scenario.get("stale")
                    else cfg,
                )
                self.respond(200, b"{}")
                return
            if self.path == "/__stats":
                self.respond(
                    200,
                    json.dumps(
                        {
                            "writes": scenario["writes"],
                            "providerCalls": len(provider.calls),
                            "lastPage": scenario.get("lastPage"),
                        }
                    ).encode(),
                )
                return
            write = self.command == "PUT" and self.path.endswith("/explicit-consent")
            if write:
                scenario["writes"] += 1
                if scenario.get("failWrite"):
                    self.respond(503, b"{}")
                    return
            headers = {
                k: v
                for k, v in self.headers.items()
                if k.lower() not in {"host", "cookie", "content-length"}
            }
            response = client.request(
                self.command, self.path, content=body, headers=headers, follow_redirects=True
            )
            if self.path == "/meetings":
                scenario["lastPage"] = str(response.url)
            if self.path == "/meetings" and response.status_code != 200:
                raise AssertionError(
                    f"Synthetic page unexpected: {response.status_code} {response.headers.get('location')} {response.url}"
                )
            content = response.content
            content_type = response.headers.get("content-type", "application/octet-stream")
            if self.path.endswith("/explicit-context") and scenario.get("identityChanged"):
                context = response.json()
                context["stable_pseudonymous_user_id"] = "graf_pseudo_user_" + "b" * 32
                content = json.dumps(context).encode()
            if "cookieconsent.umd.js" in self.path:
                # Same automation-only guard override as the existing real-modal test.
                content += b";const realRun = CookieConsent.run; CookieConsent.run = opts => realRun({...opts,hideFromBots:false});"
            if self.path == "/meetings":
                content = content.replace(
                    b"<head>",
                    b'<head><script>window.__consentSignals=[];window.addEventListener("graf:explicit-analytics-consent",e=>window.__consentSignals.push(e.detail));</script>',
                )
            if write and scenario.get("delay"):
                time.sleep(1)
            if write and scenario.get("loseReply"):
                self.respond(503, b"{}")  # The real authenticated endpoint has already committed.
                return
            self.respond(response.status_code, content, content_type)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        runner = Path(__file__).parents[1] / "browser/explicit-consent-ui.test.cjs"
        completed = subprocess.run(
            ["node", str(runner), f"http://127.0.0.1:{server.server_port}"],
            text=True,
            capture_output=True,
            timeout=90,
        )
        assert completed.returncode == 0, completed.stdout + completed.stderr
        assert "PASS real vendored notice" in completed.stdout
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


def test_cookie_consent_requires_csrf_and_render_bound_identity(client, monkeypatch):
    original = client.app.state.settings
    cfg, provider = setup(client, monkeypatch)
    cfg = original.model_copy(update={name: getattr(cfg, name) for name in cfg.model_fields_set})
    monkeypatch.setattr(client.app.state, "settings", cfg)
    client.portal.call(_seed_owner_review_session, client)
    client.cookies.set(AUTH_SESSION_COOKIE_NAME, OWNER_REVIEW_TEST_TOKEN)
    route = "/api/v1/product-analytics/"
    context = client.get(route + "explicit-context").json()
    body = {
        "accepted": True,
        "copy_version": cfg.public_analytics_consent_copy_version,
        "expected_pseudonymous_user_id": context["stable_pseudonymous_user_id"],
    }
    assert client.put(route + "explicit-consent", json=body).status_code == 403
    headers = {"X-CSRF-Token": context["csrf_token"]}
    forged = dict(body, expected_pseudonymous_user_id="graf_pseudo_user_" + "b" * 32)
    assert client.put(route + "explicit-consent", headers=headers, json=forged).status_code == 403
    assert client.get(route + "explicit-context").json()["telemetry_gate_state"] == "not_seen"
    assert client.put(route + "explicit-consent", headers=headers, json=body).status_code == 200
    monkeypatch.setattr(
        client.app.state,
        "settings",
        cfg.model_copy(update={"public_analytics_consent_copy_version": "synthetic-v2"}),
    )
    assert client.put(route + "explicit-consent", headers=headers, json=body).status_code == 403
    assert (
        client.put(
            route + "explicit-consent", headers=headers, json=dict(body, accepted=False)
        ).status_code
        == 200
    )
    assert client.get(route + "explicit-context").json()["telemetry_gate_state"] == "withdrawn"
    assert provider.calls == []
