"""Real browser/HTTP/SQL promo lifecycle; opt in with GRAF_PROMO_BROWSER=1.

The loopback bridge forwards bytes and headers to the existing ASGI TestClient.
It never renders fixtures, follows redirects, or keeps its own cookie state.
"""

import asyncio
import json
import os
import subprocess
import threading
from copy import deepcopy
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


@pytest.mark.parametrize(
    "receipt_verified,error_mode,width",
    [pytest.param(True, None, None, id="verified"),
     pytest.param(False, None, None, id="unverified"),
     *(pytest.param(True, mode, width, id=f"provider_rejection-{mode}-{width}")
       for mode in ("recurring", "generic", "uncertain") for width in (320, 1280))],
)
def test_promo_survives_real_submit_reload_and_return(
    client, owner, tmp_path, monkeypatch, receipt_verified, error_mode, width
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
    dispatched = []

    def reject_recurring(request):
        assert request.method == "POST", "unbound rejection must not query a provider payment"
        payload = json.loads(request.content)
        dispatched.append(payload)
        if payload["save_payment_method"] is True:
            return httpx.Response(503 if error_mode == "uncertain" else 403, json={
                "type": "error", "code": "forbidden",
                "description": (
                    "This store can't make recurring payments. Contact the YooMoney manager to learn more"
                    if error_mode == "recurring" else "Synthetic unrelated provider rejection"
                ),
            })
        assert error_mode != "uncertain", "unknown result must block a new payment"
        return provider.handle(request)

    if receipt_verified:
        monkeypatch.setattr(routes, "YooKassaClient", lambda settings: YooKassaClient(
            settings, transport=httpx.MockTransport(reject_recurring if error_mode else provider.handle)))

    original = {}

    async def rejection_state():
        async with client.app_state["sessionmaker"]() as db:
            operations = list(await db.scalars(select(BillingOperation).order_by(BillingOperation.created_at)))
            invoices = list(await db.scalars(select(BillingInvoice).order_by(BillingInvoice.created_at)))
            redemptions = list(await db.scalars(select(PromotionRedemption)))
            assert len(operations) == len(invoices) == len(dispatched)
            old = operations[0]
            invoice = next(row for row in invoices if row.operation_id == old.id)
            assert old.state == invoice.status == ("manual_resolution" if error_mode == "uncertain" else "canceled")
            assert old.provider_id is None
            assert old.request_snapshot["recurring_consent"] is True
            assert invoice.plan_snapshot["recurring_consent"] is True
            assert old.request_snapshot["offer_consent"] is True
            assert invoice.amount_minor == 900_000
            assert invoice.plan_snapshot["cycle"] == "year"
            failure = old.request_snapshot["provider_failure"]
            assert failure["http_status"] == (503 if error_mode == "uncertain" else 403)
            assert failure.get("reason") == ("recurring_not_available" if error_mode == "recurring" else None)
            assert "YooMoney" not in str(old.request_snapshot)
            assert len(redemptions) == 1
            assert redemptions[0].state == ("reserved" if error_mode == "uncertain" else "released")
            snapshots = deepcopy((old.request_snapshot, invoice.plan_snapshot))
            if original:
                assert snapshots == original["snapshots"], "retry must not rewrite the accepted operation"
            else:
                original["snapshots"] = snapshots
            if len(operations) == 2:
                new = operations[1]
                new_invoice = next(row for row in invoices if row.operation_id == new.id)
                assert new.state == "provider_pending" and new_invoice.status == "pending"
                assert new.provider_id == provider.payment_id
                assert new.request_snapshot["recurring_consent"] is False
                assert new_invoice.plan_snapshot["recurring_consent"] is False
                assert new.request_snapshot["offer_consent"] is True
                assert new_invoice.plan_snapshot["cycle"] == "year"
                assert new_invoice.amount_minor == 1_000_000, "consumed promo draft is not revived"
                assert new.idempotency_key != old.idempotency_key
        assert [payload["save_payment_method"] for payload in dispatched] == [True] + ([False] if len(dispatched) == 2 else [])
        assert len(provider.create_payloads) == len(dispatched) - 1

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
                    if not error_mode or not dispatched:
                        asyncio.run(no_money_side_effects())
                # Supplying only browser Cookie prevents TestClient's jar from
                # masking a browser that failed to persist or send the draft.
                client.cookies.clear()
                response = client.request(
                    self.command, f"http://127.0.0.1:{self.server.server_port}{self.path}",
                    headers=headers, content=request_body, follow_redirects=False,
                )
                client.cookies.clear()
                if error_mode and dispatched:
                    asyncio.run(rejection_state())
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
            **({"provider_rejection": error_mode, "width": width} if error_mode else {}),
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
        if error_mode:
            assert proof["viewports"] == [width]
            assert proof["provider_rejection"] == error_mode
            assert proof["external_requests"] == 0
            assert proof["submit_redirects"] == 2
            assert proof["provider_redirects"] == int(error_mode != "uncertain")
            assert not errors
            assert sum(row == ("POST", "/billing/checkout/preview", 303) for row in trace) == 1
            assert sum(row == ("POST", "/billing/checkout/start", 303) for row in trace) == (1 if error_mode == "uncertain" else 2)
            assert sum(row[0] == "POST" for row in trace) == (2 if error_mode == "uncertain" else 3)
            assert sum(row[0] == "GET" and row[1].startswith("/billing/checkout/status/") for row in trace) >= 3
            asyncio.run(rejection_state())
            return
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
