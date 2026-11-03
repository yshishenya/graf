"""Actual browser→loopback HTTP→ASGI→PostgreSQL payment return, synthetic provider.

Only provider network answers and explicitly named browser fault responses are
controlled. Prices, CSRF, redirects, grants and status HTML use the real routes.
"""

import asyncio
import json
import os
import subprocess
import threading
from contextlib import suppress
from datetime import UTC, datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from time import monotonic
from urllib.parse import urlsplit

import httpx
import pytest
from sqlalchemy import func, select

from tests.unit.test_billing_money_path_e2e import _FakeYooKassa, _money_state, _open_checkout
from twobrain_rec_server.auth.dependencies import (
    AUTH_SESSION_COOKIE_NAME,
    DEV_AUTH_SESSION_COOKIE_NAME,
)
from twobrain_rec_server.db.models import (
    BillingEntitlementGrant,
    BillingInvoice,
    BillingOperation,
    WorkspaceSubscription,
)

ENABLED = os.environ.get("GRAF_PAYMENT_RETURN_BROWSER") == "1"
pytestmark = [pytest.mark.skipif(not ENABLED, reason="Set GRAF_PAYMENT_RETURN_BROWSER=1 for DOM proof")]
if ENABLED:
    pytestmark.append(pytest.mark.browser)
ROOT = Path(__file__).resolve().parents[4]
SCRIPT = ROOT / "apps/server/tests/browser/billing-payment-return.test.cjs"
CASES = ["success", "historical", "pending", "canceled", "cancel-on-check", "refused", "service-gap",
         "errors", "guards", "lifecycle", "timeout", "native", "a11y", "provider-unavailable", "deadline-success", "deadline-pending", "deadline-timeout", "idle-five", "six-final-cooldown", "manual-cooldown", "focus-controls", "focus-latest", "focus-success", "current-context-in-flight-user", "current-context-in-flight-workspace", "current-context-in-flight-session", "current-context-in-flight-invoice", "current-context-in-flight-replacement"]


@pytest.mark.parametrize("width", [320, 1280])
@pytest.mark.parametrize("case", CASES)
def test_real_payment_return(client, tmp_path, monkeypatch, width, case):
    deadline_case = case.startswith("deadline-")
    deadline_ready_path = tmp_path / "sixth-provider-ready"
    deadline_release_path = tmp_path / "sixth-provider-release"
    deadline_complete_path = tmp_path / "sixth-server-complete"
    deadline_completed = threading.Event()

    class Provider(_FakeYooKassa):
        def handle(self, request):
            response = super().handle(request)
            if request.method == "GET" and deadline_case and self.read_count == 6:
                # Hold the actual provider transport before ASGI applies success;
                # the browser controls only static fixture phase marker files.
                deadline_ready_path.write_text("1", encoding="utf-8")
                until = monotonic() + 20
                while not deadline_release_path.exists() and monotonic() < until:
                    deadline_completed.wait(0.02)
                if not deadline_release_path.exists():
                    return httpx.Response(503, json={"code": "fixture_gate_timeout"})
            if request.method != "GET" or case in {"success", "native", "historical"} or (
                case == "focus-success" and self.read_count >= 2
            ) or (
                deadline_case and self.read_count >= 6 and case != "deadline-pending"
            ):
                return response
            if case == "provider-unavailable":
                return httpx.Response(503, json={"type": "error", "code": "internal_server_error"})
            payload = response.json()
            payload["status"] = "canceled" if case == "cancel-on-check" else "pending"
            if payload["status"] == "canceled":
                payload["cancellation_details"] = {"party": "payment_network", "reason": "canceled_by_merchant"}
            return httpx.Response(200, json=payload)

    provider = Provider()
    key = "payment-return-synthetic"
    checkout = _open_checkout(client, monkeypatch, tmp_path, provider, key, recurring_consent=False)
    invoice_number = checkout.state.invoice.safe_number
    status_path = f"/billing/checkout/status/{invoice_number}"
    if case == "historical":
        response = client.post(status_path + "/refresh", headers=checkout.headers, follow_redirects=False)
        assert response.status_code == 303
        assert len(_money_state(client, checkout.workspace_id, key).grants) == 1

    async def seed_special_state():
        async with client.app_state["sessionmaker"]() as db:
            operation = await db.get(BillingOperation, checkout.state.operation.id)
            invoice = await db.get(BillingInvoice, checkout.state.invoice.id)
            if case in {"canceled", "refused", "service-gap"}:
                operation.state = {"canceled": "canceled", "refused": "succeeded_refused", "service-gap": "succeeded"}[case]
                invoice.status = "canceled" if case == "canceled" else "succeeded"
            if case == "historical":
                subscription = await db.scalar(select(WorkspaceSubscription).where(
                    WorkspaceSubscription.workspace_id == checkout.workspace_id))
                subscription.state = "free"
                subscription.plan_code = "free"
                subscription.paid_through = datetime.now(UTC) - timedelta(days=1)
            await db.commit()

    asyncio.run(seed_special_state())
    # Checkout may rotate the issued cookie. Select its scoped latest value,
    # avoiding TestClient's unscoped seed/rotated duplicate-name CookieConflict.
    token = next((cookie.value for cookie in client.cookies.jar
                  if cookie.name == AUTH_SESSION_COOKIE_NAME and cookie.domain == "testserver.local"),
                 next(cookie.value for cookie in client.cookies.jar if cookie.name == AUTH_SESSION_COOKIE_NAME))
    monkeypatch.setattr(client.app.state.settings, "env", "development")
    monkeypatch.setattr(client.app.state.settings, "local_http_auth_cookie_enabled", True)
    client.cookies.clear()
    trace = []
    errors = []
    lock = threading.Lock()
    delay_release = threading.Event()
    refresh_completed = threading.Event()
    provider_reads_before_browser = provider.read_count

    async def count_rows():
        async with client.app_state["sessionmaker"]() as db:
            return [await db.scalar(select(func.count()).select_from(model))
                    for model in (BillingOperation, BillingInvoice, BillingEntitlementGrant)]

    assert asyncio.run(count_rows()) == [1, 1, int(case == "historical")]

    class Bridge(BaseHTTPRequestHandler):
        def log_message(self, *_args):
            pass  # Never log cookie, CSRF, form bytes or synthetic payment URL.

        def forward(self):
            path = urlsplit(self.path).path
            is_refresh = self.command == "POST" and path == status_path + "/refresh"
            if self.command == "POST" and not is_refresh:
                errors.append("unexpected_post")
                self.send_error(405)
                return
            body = self.rfile.read(int(self.headers.get("Content-Length", "0")))
            headers = {name: value for name, value in self.headers.items()
                       if name.lower() not in {"host", "connection", "accept-encoding", "content-length"}}
            # A real slow response exercises XHR's actual15s timeout. Its thread
            # stays alive, so a concurrent local GET cannot imply POST cancellation.
            if is_refresh and case == "timeout":
                delay_release.wait(17)
            try:
                client.cookies.clear()
                response = client.request(self.command, f"http://127.0.0.1:{self.server.server_port}{self.path}",
                                          headers=headers, content=body, follow_redirects=False)
                client.cookies.clear()
            except Exception as exc:
                errors.append(type(exc).__name__)
                with suppress(BrokenPipeError, ConnectionResetError):
                    self.send_error(500)
                return
            with lock:
                trace.append((self.command, is_refresh, response.status_code))
            if is_refresh:
                refresh_completed.set()
                if deadline_case and provider.read_count == 6:
                    deadline_complete_path.write_text("1", encoding="utf-8")
                    deadline_completed.set()
            with suppress(BrokenPipeError, ConnectionResetError):
                self.send_response(response.status_code)
                for name, value in response.headers.multi_items():
                    if name.lower() not in {"content-length", "transfer-encoding", "connection", "content-encoding"}:
                        self.send_header(name, value)
                self.send_header("Content-Length", str(len(response.content)))
                self.end_headers()
                self.wfile.write(response.content)

        do_GET = forward
        do_POST = forward

    class Server(ThreadingHTTPServer):
        # Join even a timed-out POST before PostgreSQL fixtures are destroyed.
        daemon_threads = False
        block_on_close = True

    server = Server(("127.0.0.1", 0), Bridge)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    config_path = tmp_path / "synthetic-browser-session.json"
    descriptor = os.open(config_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as output:
        json.dump({"base_url": f"http://127.0.0.1:{server.server_port}", "cookie_name": DEV_AUTH_SESSION_COOKIE_NAME,
                   "session_token": token, "status_path": status_path, "width": width, "case": case,
                   "deadline_ready_path": str(deadline_ready_path), "deadline_release_path": str(deadline_release_path),
                   "deadline_complete_path": str(deadline_complete_path)}, output)
    thread.start()
    try:
        result = subprocess.run(["node", str(SCRIPT), str(config_path)], capture_output=True, text=True,
                                check=False, timeout=180)
        if deadline_case:
            deadline_release_path.touch(exist_ok=True)
            assert deadline_completed.wait(5), "sixth provider/ASGI transaction completes before SQL assertions"
        if case == "timeout":
            delay_release.set()
            assert refresh_completed.wait(5), "original timed-out server POST finishes before financial assertions"
        assert result.returncode == 0, result.stderr + " bridge_errors=" + repr(errors) + " route_statuses=" + repr(trace)
        proof = json.loads(result.stdout)
        assert proof["case"] == case and proof["width"] == width
        assert proof["refresh_document_navigations"] == proof["external_requests"] == 0
        assert proof["initial_document_requests"] == len(proof["scenarios"])
        assert not errors
        assert len(provider.create_payloads) == 1, "browser return never creates a second payment"
        expected_grants = int(case in {"success", "native", "historical", "deadline-success", "deadline-timeout", "focus-success"})
        assert asyncio.run(count_rows()) == [1, 1, expected_grants]
        state = _money_state(client, checkout.workspace_id, key)
        if expected_grants:
            assert state.invoice.status == state.operation.state == "succeeded"
            assert state.grants[0].invoice_id == state.invoice.id
            assert state.grants[0].provider_payment_id == provider.payment_id
            assert len(state.grants) == 1
            if case != "historical":
                assert state.subscription.paid_through == state.grants[0].ends_at
            assert state.subscription.recurring_allowed is False
        elif case in {"canceled", "cancel-on-check"}:
            assert state.invoice.status == state.operation.state == "canceled"
        elif case not in {"refused", "service-gap"}:
            assert state.invoice.status == "pending"
        browser_posts = sum(method == "POST" for method, _refresh, _status in trace)
        assert browser_posts == proof["refresh_posts"]
        if case != "timeout":
            assert provider.read_count - provider_reads_before_browser == browser_posts
    finally:
        deadline_release_path.touch(exist_ok=True)
        delay_release.set()
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
