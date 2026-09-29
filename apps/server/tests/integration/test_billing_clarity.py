"""Payment recovery and receipt readiness through real routes and disposable PostgreSQL."""

import asyncio
import re
from datetime import UTC, datetime, timedelta
from html import unescape
from urllib.parse import parse_qs, urlsplit
from uuid import uuid4

import pytest
from sqlalchemy import func, select, update

from tests.integration.test_billing_purchase_journey import quote_id
from tests.integration.test_billing_review_regressions import seed_periods
from tests.unit.test_billing_money_path_e2e import (
    USER_ID,
    _approved_month_catalog,
    _configure_billing,
    _prepare_owner_session,
)
from twobrain_rec_server.cabinet.web_routes import billing as routes
from twobrain_rec_server.db.models import (
    BillingInvoice,
    BillingOperation,
    ExternalIdentity,
    WorkspaceSubscription,
)
from twobrain_rec_server.public.offers import PUBLIC_APPROVED_OFFER_VERSION


@pytest.fixture
def owner(client, tmp_path, monkeypatch):
    _configure_billing(client, tmp_path)
    _approved_month_catalog(client)
    workspace, headers = _prepare_owner_session(client)

    def no_provider(*_args, **_kwargs):
        pytest.fail("A presentation or blocked request must not contact the provider")

    monkeypatch.setattr(routes, "YooKassaClient", no_provider)
    return workspace, headers


def set_subscription(client, workspace, **values):
    async def run():
        async with client.app_state["sessionmaker"]() as db:
            row = await db.scalar(select(WorkspaceSubscription).where(
                WorkspaceSubscription.workspace_id == workspace
            ))
            if row is None:
                row = WorkspaceSubscription(workspace_id=workspace, billing_owner_id=USER_ID)
                db.add(row)
            for key, value in values.items():
                setattr(row, key, value)
            await db.commit()

    asyncio.run(run())


def unverify_email(client):
    async def run():
        async with client.app_state["sessionmaker"]() as db:
            await db.execute(update(ExternalIdentity).where(
                ExternalIdentity.user_id == USER_ID
            ).values(is_verified=False))
            await db.commit()

    asyncio.run(run())


def seed_payment(client, workspace, *, state="unknown", cycle="year", detail=None,
                 kind="initial_checkout", confirmation_url=None):
    async def run():
        async with client.app_state["sessionmaker"]() as db:
            snapshot = {"cycle": cycle, "billing_actor_user_id": str(USER_ID)}
            if detail:
                snapshot["reconciliation_detail"] = {"code": detail}
            if confirmation_url:
                snapshot["confirmation_url"] = confirmation_url
            operation = BillingOperation(
                workspace_id=workspace, kind=kind, state=state,
                idempotency_key="clarity-existing", provider_id=f"synthetic-{uuid4().hex}",
                provider_key_expires_at=datetime.now(UTC) + timedelta(hours=12),
                request_snapshot=snapshot,
            )
            db.add(operation)
            await db.flush()
            db.add(BillingInvoice(
                workspace_id=workspace, operation_id=operation.id,
                safe_number="INV-CLARITY", amount_minor=100000, currency="RUB",
                status="succeeded" if state.startswith("succeeded") else
                state if state in {"canceled", "failed", "manual_resolution"} else "pending",
                plan_snapshot={"cycle": cycle},
            ))
            await db.commit()

    asyncio.run(run())


def payment_counts(client):
    async def run():
        async with client.app_state["sessionmaker"]() as db:
            return (
                await db.scalar(select(func.count()).select_from(BillingOperation)),
                await db.scalar(select(func.count()).select_from(BillingInvoice)),
            )

    return asyncio.run(run())


def receipt_account_link(html):
    return urlsplit(unescape(re.search(
        r'href="([^"]*settings/account[^"#]*#account-providers-title)"', html
    ).group(1)))


@pytest.mark.parametrize("query, expected", [("", "year"), ("?cycle=month", "month"), ("?cycle=invalid", "year")])
def test_checkout_keeps_subscription_cycle_unless_explicitly_changed(client, owner, query, expected):
    workspace, headers = owner
    set_subscription(client, workspace, cycle="year")
    response = client.get(f"/billing/checkout{query}", headers=headers)
    assert response.status_code == 200
    form = re.search(r'<form action="/billing/checkout/start".*?</form>', response.text, re.S)
    assert form and f'name="cycle" value="{expected}"' in form.group()


def test_pending_invoice_and_checkout_open_existing_payment_without_new_money(client, owner):
    workspace, headers = owner
    seed_payment(client, workspace)
    for path in ("/billing/invoices/INV-CLARITY", "/billing/checkout", "/billing/history"):
        response = client.get(path, headers=headers)
        assert response.status_code == 200
        assert 'href="/billing/checkout/status/INV-CLARITY"' in response.text
    assert payment_counts(client) == (1, 1)
    missing = client.get("/billing/invoices/INV-OTHER", headers=headers, follow_redirects=False)
    assert missing.headers["location"] == "/billing/history?result=not_found"


@pytest.mark.parametrize("state", ["failed", "canceled"])
def test_terminal_retry_preserves_original_invoice_cycle(client, owner, state):
    workspace, headers = owner
    seed_payment(client, workspace, state=state)
    response = client.get("/billing/checkout/status/INV-CLARITY", headers=headers)
    assert 'href="/billing/checkout?cycle=year"' in response.text


@pytest.mark.parametrize("desktop", [False, True])
def test_missing_verified_email_is_recoverable_before_new_money(client, owner, desktop):
    _, headers = owner
    unverify_email(client)
    if desktop:
        headers = {**headers, "X-GRAF-Client": "desktop"}
    response = client.get("/billing/checkout?cycle=year", headers=headers)
    assert response.status_code == 200
    account = receipt_account_link(response.text)
    assert account.path == ("/desktop/settings/account" if desktop else "/settings/account")
    assert parse_qs(account.query)["next"] == ["/billing/checkout?cycle=year"]
    assert 'action="/billing/checkout/start"' not in response.text
    assert "Подтвердите email" in response.text
    rejected = client.post("/billing/checkout/start", headers=headers, follow_redirects=False, data={
        "cycle": "year", "idempotency_key": "clarity-no-email", "quote_id": str(uuid4()),
        "offer_consent": "true", "recurring_consent": "true", "offer_version": PUBLIC_APPROVED_OFFER_VERSION,
    })
    assert rejected.status_code == 303
    assert rejected.headers["location"] == "/billing/checkout?result=receipt_contact_required&cycle=year"
    assert payment_counts(client) == (0, 0)


def test_missing_email_does_not_obstruct_existing_payment_recovery(client, owner):
    workspace, headers = owner
    seed_payment(client, workspace)
    unverify_email(client)
    response = client.post("/billing/checkout/start", headers=headers, follow_redirects=False, data={
        "cycle": "year", "idempotency_key": "clarity-existing", "offer_consent": "true",
        "recurring_consent": "true", "offer_version": PUBLIC_APPROVED_OFFER_VERSION,
    })
    assert response.status_code == 303
    assert response.headers["location"] == "/billing/checkout/status/INV-CLARITY"
    assert payment_counts(client) == (1, 1)


@pytest.mark.parametrize("kind", ["initial_checkout", "storage_upgrade"])
def test_pending_status_continues_same_hosted_payment(client, owner, kind):
    workspace, headers = owner
    hosted_url = "https://yookassa.test/checkout/synthetic-existing"
    seed_payment(client, workspace, kind=kind, state="provider_pending", confirmation_url=hosted_url)
    response = client.get("/billing/checkout/status/INV-CLARITY", headers=headers)
    assert 'action="/billing/checkout/status/INV-CLARITY/continue"' in response.text
    resumed = client.post("/billing/checkout/status/INV-CLARITY/continue", headers=headers,
                          follow_redirects=False)
    assert resumed.status_code == 303 and resumed.headers["location"] == hosted_url
    assert payment_counts(client) == (1, 1)


@pytest.mark.parametrize("path", [
    "/billing/storage/preview", "/billing/storage/cancel-selection",
    "/billing/subscription/early-preview", "/billing/purchases/confirm",
])
def test_purchase_post_routes_reject_get(client, owner, path):
    _, headers = owner
    response = client.get(path, headers=headers)
    assert response.status_code == 405
    assert payment_counts(client) == (0, 0)


@pytest.mark.parametrize("state, detail", [
    ("succeeded_refused", None), ("succeeded", "owner_changed"),
    ("succeeded", "workspace_scope_invalid"), ("succeeded", "storage_period_elapsed"),
])
def test_confirmed_money_with_service_gap_has_neutral_honest_result(client, owner, state, detail):
    workspace, headers = owner
    seed_payment(client, workspace, state=state, detail=detail)
    response = client.get("/billing/checkout/status/INV-CLARITY", headers=headers)
    assert response.status_code == 200
    assert "Оплата получена. Проверяем доступ" in response.text
    assert "оплаченный доступ предоставлен" not in response.text
    assert "Увеличенный объем не предоставлен" not in response.text
    assert "Не удалось найти платеж" not in response.text
    assert "К встречам</a>" not in response.text
    assert "mailto:billing@2brain.pro" in response.text


@pytest.mark.parametrize("desktop", [False, True])
def test_confirmed_success_returns_to_meetings_in_current_surface(client, owner, desktop):
    workspace, headers = owner
    seed_payment(client, workspace, state="succeeded")
    if desktop:
        headers = {**headers, "X-GRAF-Client": "desktop"}
    response = client.get("/billing/checkout/status/INV-CLARITY?result=unchanged", headers=headers)
    path = "/desktop/meetings" if desktop else "/meetings"
    assert f'href="{path}">К встречам</a>' in response.text
    assert "Подтверждение еще не получено" not in response.text


@pytest.mark.parametrize("resolution, action, message", [
    ("method_required", "/billing/payment-method", "Проверьте способ оплаты"),
    ("receipt_contact_required", "/billing/checkout?cycle=year", "Оплатите следующий период вручную"),
])
def test_renewal_blockers_explain_real_recovery_without_promising_charge(client, owner, resolution, action, message):
    workspace, headers = owner
    set_subscription(client, workspace, plan_code="personal", state="personal", cycle="year",
                     recurring_allowed=True, renewal_resolution=resolution,
                     paid_through=datetime.now(UTC) + timedelta(days=25))
    for path in ("/billing/subscription", "/billing"):
        response = client.get(path, headers=headers)
        assert response.status_code == 200
        assert message in response.text
        assert f'href="{action}"' in response.text
        assert "приостановлено" in response.text


def test_storage_contact_gate_rechecks_before_money_but_allows_no_charge_selection(client, owner):
    workspace, headers = owner
    seed_periods(client, workspace)
    preview = client.post("/billing/storage/preview", headers=headers, data={"package_count": "1"})
    bound = quote_id(preview)
    unverify_email(client)
    before = payment_counts(client)
    rejected = client.post("/billing/purchases/confirm", headers=headers, data={
        "quote_id": bound, "purchase_consent": "true",
    })
    assert rejected.status_code == 409
    assert parse_qs(receipt_account_link(rejected.text).query)["next"] == ["/billing/storage?package_count=1"]
    assert "Подтвердите email" in rejected.text
    assert payment_counts(client) == before
    preview = client.post("/billing/storage/preview", headers=headers, data={"package_count": "1"})
    assert preview.status_code == 200
    assert 'action="/billing/purchases/confirm"' not in preview.text
    deferred = client.post("/billing/storage/preview", headers=headers, data={"package_count": "0"})
    assert deferred.status_code == 200
    assert 'action="/billing/purchases/confirm"' in deferred.text


@pytest.mark.parametrize("selection, expected", [("2", "2"), ("100", "0"), ("not-a-number", "0")])
def test_storage_recovery_restores_only_catalog_selection_without_mutation(client, owner, selection, expected):
    workspace, headers = owner
    seed_periods(client, workspace)
    before = payment_counts(client)
    response = client.get(f"/billing/storage?package_count={selection}", headers=headers)
    assert response.status_code == 200
    selected = re.search(r'<option value="(\d+)"[^>]*\sselected[^>]*>', response.text)
    assert selected and selected.group(1) == expected
    assert payment_counts(client) == before


def test_purchase_conflict_links_to_existing_payment_without_creating_another(client, owner):
    workspace, headers = owner
    seed_periods(client, workspace)
    bound = quote_id(client.post("/billing/storage/preview", headers=headers, data={"package_count": "1"}))
    seed_payment(client, workspace)
    before = payment_counts(client)
    response = client.post("/billing/purchases/confirm", headers=headers, follow_redirects=False,
                           data={"quote_id": bound, "purchase_consent": "true"})
    assert response.status_code == 303
    assert response.headers["location"] == "/billing/checkout/status/INV-CLARITY"
    assert payment_counts(client) == before
