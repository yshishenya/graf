"""Real browser/HTTP/SQL promo lifecycle; opt in with GRAF_PROMO_BROWSER=1.

The loopback bridge forwards bytes and headers to the existing ASGI TestClient.
It never renders fixtures, follows redirects, or keeps its own cookie state.
"""

import asyncio
import json
import os
import subprocess
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from urllib.parse import urlsplit

import httpx
import pytest
from sqlalchemy import select

from tests.integration.test_billing_discount_presentation import owner as owner
from tests.integration.test_billing_discount_presentation import seed_campaign
from tests.unit.test_billing_money_path_e2e import USER_ID, _FakeYooKassa
from twobrain_rec_server.auth.dependencies import (
    AUTH_SESSION_COOKIE_NAME,
    DEV_AUTH_SESSION_COOKIE_NAME,
)
from twobrain_rec_server.billing.promotions import promo_code_hash
from twobrain_rec_server.billing.yookassa import YooKassaClient
from twobrain_rec_server.cabinet.web_routes import billing as routes
from twobrain_rec_server.db.models import (
    BillingInvoice,
    BillingOperation,
    ExternalIdentity,
    PromotionRedemption,
    WorkspaceSubscription,
)

ENABLED = os.environ.get("GRAF_PROMO_BROWSER") == "1"
pytestmark = [pytest.mark.skipif(not ENABLED, reason="Set GRAF_PROMO_BROWSER=1 for DOM proof")]
if ENABLED:
    pytestmark.append(pytest.mark.browser)

ROOT = Path(__file__).parents[4]
SCRIPT = ROOT / "apps/server/tests/browser/billing-promo-refresh.test.cjs"


@pytest.mark.parametrize("receipt_verified", [True, False], ids=["verified", "unverified"])
def test_promo_survives_real_submit_reload_and_return(
    client, owner, tmp_path, monkeypatch, receipt_verified
):
    workspace, _ = owner
    seed_campaign(client, policy_snapshot={
        "workspace_id": str(workspace), "purposes": ["initial_checkout"],
    })
    seed_campaign(client, code_hash=promo_code_hash("SYNTH-SECOND"), discount_percent=25,
                  policy_snapshot={"workspace_id": str(workspace), "purposes": ["initial_checkout"]})

    async def configure_annual_receipt():
        async with client.app_state["sessionmaker"]() as db:
            subscription = await db.get(WorkspaceSubscription, workspace)
            if subscription is None:
                subscription = WorkspaceSubscription(workspace_id=workspace, billing_owner_id=USER_ID)
                db.add(subscription)
            subscription.cycle = "year"
            identity = await db.scalar(select(ExternalIdentity).where(
                ExternalIdentity.user_id == USER_ID, ExternalIdentity.provider == "email"))
            identity.is_verified = receipt_verified
            await db.commit()

    asyncio.run(configure_annual_receipt())
    provider = _FakeYooKassa()
    if receipt_verified:
        monkeypatch.setattr(routes, "YooKassaClient", lambda settings: YooKassaClient(
            settings, transport=httpx.MockTransport(provider.handle)))

    async def no_money_side_effects():
        async with client.app_state["sessionmaker"]() as db:
            for model in (BillingOperation, BillingInvoice, PromotionRedemption):
                assert await db.scalar(select(model.id)) is None
        assert provider.create_payloads == []
    # Use the project's supported local HTTP cookie, retaining the actual issued
    # database session and CSRF subject. Production __Host cookies require TLS.
    session_token = client.cookies.get(AUTH_SESSION_COOKIE_NAME)
    assert session_token
    monkeypatch.setattr(client.app.state.settings, "env", "development")
    monkeypatch.setattr(client.app.state.settings, "local_http_auth_cookie_enabled", True)
    client.cookies.clear()
    trace = []
    errors = []

    class Bridge(BaseHTTPRequestHandler):
        def log_message(self, *_args):
            pass  # Never log URLs, session cookies, CSRF, or form payloads.

        def forward(self):
            path = urlsplit(self.path).path
            if self.command == "POST" and path not in {"/billing/checkout/preview", "/billing/discounts/apply", "/billing/checkout/start"}:
                errors.append("unexpected_post")
                self.send_error(405)
                return
            request_body = self.rfile.read(int(self.headers.get("Content-Length", "0")))
            headers = {
                key: value for key, value in self.headers.items()
                if key.lower() not in {"host", "connection", "accept-encoding", "content-length"}
            }
            try:
                if self.command == "POST" and path == "/billing/checkout/start":
                    assert receipt_verified
                    asyncio.run(no_money_side_effects())
                # Supplying only browser Cookie prevents TestClient's jar from
                # masking a browser that failed to persist or send the draft.
                client.cookies.clear()
                response = client.request(
                    self.command, f"http://127.0.0.1:{self.server.server_port}{self.path}",
                    headers=headers, content=request_body, follow_redirects=False,
                )
                client.cookies.clear()
            except Exception as exc:
                errors.append(f"asgi_request_failed:{type(exc).__name__}")
                self.send_error(500)
                return
            trace.append((self.command, path, response.status_code))
            self.send_response(response.status_code)
            for key, value in response.headers.multi_items():
                if key.lower() not in {"content-length", "transfer-encoding", "connection", "content-encoding"}:
                    self.send_header(key, value)
            self.send_header("Content-Length", str(len(response.content)))
            self.end_headers()
            self.wfile.write(response.content)

        do_GET = forward
        do_POST = forward

    server = HTTPServer(("127.0.0.1", 0), Bridge)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    config = tmp_path / "synthetic-browser-session.json"
    descriptor = os.open(config, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as output:
        json.dump({
            "base_url": f"http://127.0.0.1:{server.server_port}",
            "cookie_name": DEV_AUTH_SESSION_COOKIE_NAME,
            "session_token": session_token,
            "screenshots_dir": os.environ.get("GRAF_PROMO_BROWSER_SCREENSHOTS"),
            "receipt_verified": receipt_verified,
        }, output)
    thread.start()
    try:
        result = subprocess.run(
            ["node", str(SCRIPT), str(config)], capture_output=True, text=True,
            timeout=240, check=False,
        )
        # The runner emits only synthetic check counts and a named failure stage.
        assert result.returncode == 0, (
            result.stderr + " Bridge errors: " + repr(errors) + " Route statuses: " + repr([
                row for row in trace if row[1] in {"/billing/checkout", "/billing/checkout/preview", "/billing/checkout/start", "/billing/discounts/apply"}
            ])
        )
        proof = json.loads(result.stdout)
        assert proof["engine"] == os.environ.get("GRAF_BROWSER", "chromium")
        assert proof["viewports"] == [320, 1280]
        assert proof["external_requests"] == 0
        assert proof["submit_redirects"] == (38 if receipt_verified else 36)
        assert proof["provider_redirects"] == int(receipt_verified)
        assert proof["receipt_verified"] == receipt_verified
        assert not errors
        assert sum(row == ("POST", "/billing/checkout/preview", 303) for row in trace) == (33 if receipt_verified else 32)
        assert sum(row == ("POST", "/billing/checkout/start", 303) for row in trace) == (2 if receipt_verified else 0)
        assert sum(row == ("POST", "/billing/checkout/start", 409) for row in trace) == int(receipt_verified)
        assert sum(row == ("POST", "/billing/discounts/apply", 303) for row in trace) == 4
        assert sum(row == ("GET", "/billing/checkout", 200) for row in trace) >= 30
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
        config.unlink(missing_ok=True)
        client.cookies.clear()

    async def one_period_payment():
        async with client.app_state["sessionmaker"]() as db:
            operation = (await db.scalars(select(BillingOperation))).one()
            invoice = (await db.scalars(select(BillingInvoice))).one()
            assert operation.request_snapshot["recurring_consent"] is False
            assert invoice.plan_snapshot["recurring_consent"] is False
            assert operation.request_snapshot["offer_consent"] is True
            assert invoice.amount_minor == 900_000
            assert invoice.plan_snapshot["cycle"] == "year"
        assert len(provider.create_payloads) == 1
        assert provider.create_payloads[0]["save_payment_method"] is False

    asyncio.run(one_period_payment() if receipt_verified else no_money_side_effects())
