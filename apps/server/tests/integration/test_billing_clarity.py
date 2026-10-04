"""Payment recovery and receipt readiness through real routes and disposable PostgreSQL."""

import asyncio
import re
from datetime import UTC, datetime, timedelta
from html import unescape
from urllib.parse import parse_qs, quote, unquote, urlsplit
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
    BillingEntitlementGrant,
    BillingInvoice,
    BillingOperation,
    BillingStorageEntitlementGrant,
    BillingStoragePriceVersion,
    ExternalIdentity,
    Workspace,
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
                 kind="initial_checkout", confirmation_url=None, granted=False):
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
            invoice = BillingInvoice(
                workspace_id=workspace, operation_id=operation.id,
                safe_number="INV-CLARITY", amount_minor=100000, currency="RUB",
                status="succeeded" if state.startswith("succeeded") else
                state if state in {"canceled", "failed", "manual_resolution"} else "pending",
                plan_snapshot={"cycle": cycle},
            )
            db.add(invoice)
            if granted:
                await db.flush()
                db.add(BillingEntitlementGrant(workspace_id=workspace, invoice_id=invoice.id,
                    provider_payment_id=operation.provider_id, plan_code="personal", cycle=cycle,
                    starts_at=datetime(2026, 1, 1, tzinfo=UTC), ends_at=datetime(2027, 1, 1, tzinfo=UTC),
                    amount_minor=invoice.amount_minor, currency=invoice.currency))
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
    assert "Проверяем оплату" in response.text
    assert "Повторно платить не нужно" in response.text
    assert 'id="billing-status-refresh"' in response.text
    assert 'action="/billing/checkout/status/INV-CLARITY/continue"' not in response.text
    checked = client.get("/billing/checkout/status/INV-CLARITY?result=unchanged", headers=headers)
    assert 'action="/billing/checkout/status/INV-CLARITY/continue"' in checked.text
    assert 'class="button quiet" type="submit">Вернуться к оплате' in checked.text
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
    seed_payment(client, workspace, state="succeeded", granted=True)
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


@pytest.mark.parametrize("state", ["succeeded", "canceled", "failed"])
@pytest.mark.parametrize("kind", ["initial_checkout", "storage_upgrade"])
def test_stale_continue_cannot_reopen_terminal_payment(client, owner, state, kind):
    workspace, headers = owner
    seed_payment(client, workspace, kind=kind, state=state,
                 confirmation_url="https://yookassa.test/checkout/synthetic-existing")
    response = client.post("/billing/checkout/status/INV-CLARITY/continue", headers=headers,
                           follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"].startswith("/billing/checkout/status/INV-CLARITY")
    assert payment_counts(client) == (1, 1)


@pytest.mark.parametrize("kind", ["initial_checkout", "storage_upgrade"])
def test_stale_pending_operation_with_terminal_invoice_cannot_continue(client, owner, kind):
    workspace, headers = owner
    seed_payment(client, workspace, kind=kind, state="provider_pending",
                 confirmation_url="https://yookassa.test/checkout/synthetic-existing")
    async def settle_invoice():
        async with client.app_state["sessionmaker"]() as db:
            invoice = await db.scalar(select(BillingInvoice))
            invoice.status = "succeeded"
            await db.commit()
    asyncio.run(settle_invoice())
    response = client.post("/billing/checkout/status/INV-CLARITY/continue", headers=headers,
                           follow_redirects=False)
    assert response.headers["location"].startswith("/billing/checkout/status/INV-CLARITY")
    assert payment_counts(client) == (1, 1)


def test_succeeded_subscription_invoice_requires_linked_grant(client, owner):
    workspace, headers = owner
    seed_payment(client, workspace, state="succeeded")
    response = client.get("/billing/checkout/status/INV-CLARITY", headers=headers)
    assert "Оплата получена. Проверяем доступ" in response.text
    assert "оплаченный доступ предоставлен" not in response.text
    assert "К встречам</a>" not in response.text


def test_paid_historical_invoice_uses_its_grant_period(client, owner):
    workspace, headers = owner
    seed_payment(client, workspace, state="succeeded")
    async def grant():
        async with client.app_state["sessionmaker"]() as db:
            invoice = await db.scalar(select(BillingInvoice))
            operation = await db.scalar(select(BillingOperation))
            db.add(BillingEntitlementGrant(workspace_id=workspace, invoice_id=invoice.id,
                provider_payment_id=operation.provider_id, plan_code="personal", cycle="year",
                starts_at=datetime(2025, 1, 1, tzinfo=UTC), ends_at=datetime(2026, 1, 1, tzinfo=UTC),
                amount_minor=invoice.amount_minor, currency=invoice.currency))
            await db.commit()
    asyncio.run(grant())
    response = client.get("/billing/checkout/status/INV-CLARITY", headers=headers)
    assert ">Оплачено</h2>" in response.text
    assert "01.01.2025" in response.text and "01.01.2026" in response.text
    assert "К встречам</a>" in response.text
    assert payment_counts(client) == (1, 1)


def test_local_status_recovery_never_restarts_payment_check(client, owner):
    workspace, headers = owner
    seed_payment(client, workspace, state="provider_pending",
                 confirmation_url="https://yookassa.test/checkout/synthetic-existing")
    status = "/billing/checkout/status/INV-CLARITY"
    ordinary = client.get(status, headers=headers)
    assert 'data-billing-auto-check="true"' in ordinary.text
    recovered = client.get(status + "?view=local", headers=headers)
    assert recovered.status_code == 200
    assert 'data-billing-auto-check="false"' in recovered.text
    assert 'id="billing-status-refresh"' not in recovered.text
    recovery_main = re.search(r'<main id="cabinet-main".*?</main>', recovered.text, re.S).group()
    assert 'method="post"' not in recovery_main
    assert status + "?view=local" in recovered.text
    assert ">Оплачено</h2>" not in recovered.text
    assert payment_counts(client) == (1, 1)


_STORAGE_PERIODS = [
    (datetime(2025, 1, 1, tzinfo=UTC), datetime(2025, 2, 1, tzinfo=UTC)),
    (datetime(2025, 3, 1, tzinfo=UTC), datetime(2025, 4, 1, tzinfo=UTC)),
]


def seed_storage_status(client, workspace, *, state="succeeded", schema=2,
                        periods=(), snapshot_changes=None, invoice_status="succeeded",
                        kind="storage_upgrade", service_resolution=None):
    """Synthetic purchase proof, independent of the subscription's current capacity."""
    async def run():
        async with client.app_state["sessionmaker"]() as db:
            snapshot = {
                "billing_actor_user_id": str(USER_ID), "cycle": "month",
                "addon_capacity_bytes": 10_000_000_000,
                "effective_at": _STORAGE_PERIODS[0][0].isoformat(),
                "ends_at": _STORAGE_PERIODS[0][1].isoformat(),
            }
            if schema is not None:
                snapshot["purchase_schema"] = schema
            snapshot.update(snapshot_changes or {})
            operation = BillingOperation(workspace_id=workspace, kind=kind, state=state,
                idempotency_key=str(uuid4()), provider_id=f"synthetic-{uuid4().hex}",
                request_snapshot=snapshot)
            db.add(operation)
            await db.flush()
            invoice = BillingInvoice(workspace_id=workspace, operation_id=operation.id,
                safe_number=f"INV-STORAGE-{uuid4().hex}", amount_minor=100000,
                currency="RUB", status=invoice_status,
                plan_snapshot={"cycle": "month", "purpose": "storage_upgrade",
                    **({"service_resolution": service_resolution} if service_resolution else {})})
            db.add(invoice)
            await db.flush()
            if periods:
                price = await db.scalar(select(BillingStoragePriceVersion).where(
                    BillingStoragePriceVersion.capacity_bytes == 10_000_000_000,
                    BillingStoragePriceVersion.cycle == "month"))
                if price is None:
                    price = BillingStoragePriceVersion(version=1, capacity_bytes=10_000_000_000,
                        cycle="month", amount_minor=100000, currency="RUB",
                        effective_from=datetime(2024, 1, 1, tzinfo=UTC))
                    db.add(price)
                    await db.flush()
                # Base periods belong to separate purchases; each storage right is
                # nevertheless bound to this exact storage invoice and workspace.
                for start, end in reversed(periods):
                    base_operation = BillingOperation(workspace_id=workspace, kind="renewal",
                        state="succeeded", idempotency_key=str(uuid4()), request_snapshot={})
                    db.add(base_operation)
                    await db.flush()
                    base_invoice = BillingInvoice(workspace_id=workspace,
                        operation_id=base_operation.id, safe_number=f"INV-BASE-{uuid4().hex}",
                        amount_minor=100000, currency="RUB", status="succeeded", plan_snapshot={})
                    db.add(base_invoice)
                    await db.flush()
                    base = BillingEntitlementGrant(workspace_id=workspace,
                        invoice_id=base_invoice.id, provider_payment_id=f"synthetic-{uuid4().hex}",
                        plan_code="personal", cycle="month", starts_at=start, ends_at=end,
                        amount_minor=100000, currency="RUB")
                    db.add(base)
                    await db.flush()
                    db.add(BillingStorageEntitlementGrant(workspace_id=workspace,
                        invoice_id=invoice.id, base_grant_id=base.id, starts_at=start, ends_at=end,
                        capacity_bytes=10_000_000_000, catalog_version_id=price.id,
                        full_period_amount_minor=price.amount_minor))
            await db.commit()
            return invoice.safe_number
    return asyncio.run(run())


def billing_rows_snapshot(client):
    """Compare persisted billing row values, including timestamps, before/after GET."""
    async def run():
        async with client.app_state["sessionmaker"]() as db:
            result = {}
            for name, table in BillingInvoice.metadata.tables.items():
                if name.startswith("billing_") or name == "workspace_subscriptions":
                    rows = (await db.execute(select(table))).mappings().all()
                    result[name] = sorted(repr(dict(row)) for row in rows)
            return result
    return asyncio.run(run())


@pytest.mark.parametrize("surface", ["web", "desktop", "local", "desktop_local"])
@pytest.mark.parametrize("proof", ["single_grant", "disjoint_grants", "legacy_projected"])
def test_storage_return_shows_only_purchased_historical_periods(client, owner, surface, proof):
    workspace, headers = owner
    set_subscription(client, workspace, plan_code="free", state="free", cycle="year",
        capacity_bytes=5_000_000_000, paid_through=datetime(2024, 1, 1, tzinfo=UTC))
    periods = _STORAGE_PERIODS if proof == "disjoint_grants" else _STORAGE_PERIODS[:1]
    legacy = proof == "legacy_projected"
    number = seed_storage_status(client, workspace,
        state="succeeded_projected" if legacy else "succeeded",
        schema=None if legacy else 2, periods=() if legacy else periods)
    before = billing_rows_snapshot(client)
    if "desktop" in surface:
        headers = {**headers, "X-GRAF-Client": "desktop"}
    query = "?view=local" if "local" in surface else ""
    response = client.get(f"/billing/checkout/status/{number}{query}", headers=headers)
    assert response.status_code == 200
    main = re.search(r'<main id="cabinet-main".*?</main>', response.text, re.S).group()
    assert '>Оплачено</h2>' in main
    assert 'Оплата прошла, оплаченный доступ предоставлен.' in main
    expected = [f"{routes._billing_datetime_label(start)} — {routes._billing_datetime_label(end)}"
                for start, end in periods]
    assert f"Оплаченный срок: {'; '.join(expected)}." in main
    assert "01.01.2024" not in main
    if proof == "disjoint_grants":
        assert f"{routes._billing_datetime_label(periods[0][0])} — {routes._billing_datetime_label(periods[-1][1])}" not in main
    path = "/desktop/meetings" if "desktop" in surface else "/meetings"
    assert f'href="{path}">К встречам</a>' in main
    assert f'data-billing-state="{"succeeded_projected" if legacy else "succeeded"}"' in main
    assert 'data-billing-auto-check="false"' in main
    assert 'method="post"' not in main
    assert 'Написать в поддержку</a>' not in main
    assert billing_rows_snapshot(client) == before


@pytest.mark.parametrize("case", [
    "missing_grant", "other_invoice_grant", "other_workspace_grant", "unprojected",
    "schema2_projected", "other_kind", "pending_invoice", "malformed_start", "missing_end",
    "naive_start", "naive_end", "reversed", "zero_period", "bad_cycle", "bool_capacity",
    "unknown_capacity", "reconciliation_marker", "service_marker",
])
def test_storage_return_requires_proof_for_this_purchase(client, owner, case):
    workspace, headers = owner
    # A large current quota must never stand in for proof of this purchase.
    set_subscription(client, workspace, plan_code="personal", state="personal",
        capacity_bytes=50_000_000_000, paid_through=datetime(2027, 1, 1, tzinfo=UTC))
    legacy = case not in {"missing_grant", "other_invoice_grant", "other_workspace_grant"}
    changes = {
        "malformed_start": {"effective_at": "invalid"}, "missing_end": {"ends_at": None},
        "naive_start": {"effective_at": "2025-01-01T00:00:00"},
        "naive_end": {"ends_at": "2025-02-01T00:00:00"},
        "reversed": {"effective_at": "2025-03-01T00:00:00+00:00"},
        "zero_period": {"ends_at": _STORAGE_PERIODS[0][0].isoformat()},
        "bad_cycle": {"cycle": "week"}, "bool_capacity": {"addon_capacity_bytes": True},
        "unknown_capacity": {"addon_capacity_bytes": 42},
        "reconciliation_marker": {"reconciliation_detail": {"code": "unapplied"}},
    }.get(case, {})
    number = seed_storage_status(client, workspace,
        state="succeeded" if case == "unprojected" or not legacy else "succeeded_projected",
        schema=2 if not legacy or case == "schema2_projected" else None,
        kind="renewal" if case == "other_kind" else "storage_upgrade",
        invoice_status="pending" if case == "pending_invoice" else "succeeded",
        snapshot_changes=changes, service_resolution="unapplied" if case == "service_marker" else None)
    if case in {"other_invoice_grant", "other_workspace_grant"}:
        grant_workspace = workspace
        if case == "other_workspace_grant":
            async def another_workspace():
                async with client.app_state["sessionmaker"]() as db:
                    own = await db.get(Workspace, workspace)
                    other = Workspace(organization_id=own.organization_id,
                        slug=f"synthetic-{uuid4().hex}", name="Synthetic billing scope")
                    db.add(other)
                    await db.commit()
                    return other.id
            grant_workspace = asyncio.run(another_workspace())
        seed_storage_status(client, grant_workspace, periods=_STORAGE_PERIODS[:1])
    before = billing_rows_snapshot(client)
    response = client.get(f"/billing/checkout/status/{number}?view=local", headers=headers)
    assert response.status_code == 200
    main = re.search(r'<main id="cabinet-main".*?</main>', response.text, re.S).group()
    assert '>Оплачено</h2>' not in main
    assert "оплаченный доступ предоставлен" not in main
    assert "Оплаченный срок:" not in main
    assert "К встречам</a>" not in main
    assert 'data-billing-auto-check="false"' in main
    assert 'method="post"' not in main
    assert billing_rows_snapshot(client) == before


def test_storage_return_does_not_expose_another_workspace_invoice(client, owner):
    workspace, headers = owner
    async def another_workspace():
        async with client.app_state["sessionmaker"]() as db:
            own = await db.get(Workspace, workspace)
            other = Workspace(organization_id=own.organization_id,
                slug=f"synthetic-{uuid4().hex}", name="Synthetic isolated billing")
            db.add(other)
            await db.commit()
            return other.id
    other = asyncio.run(another_workspace())
    number = seed_storage_status(client, other, periods=_STORAGE_PERIODS)
    before = billing_rows_snapshot(client)
    response = client.get(f"/billing/checkout/status/{number}", headers=headers,
        follow_redirects=False)
    assert response.status_code == 303
    assert response.headers["location"] == "/billing/history?result=not_found"
    assert number not in response.text
    assert billing_rows_snapshot(client) == before


def test_storage_return_recognizes_actual_legacy_projection_after_subscription_expires(client, owner):
    from twobrain_rec_server.billing.maintenance import _reconcile_storage_addon_operations

    workspace, headers = owner
    set_subscription(client, workspace, plan_code="personal", state="personal", cycle="month",
        capacity_bytes=5_000_000_000, paid_through=_STORAGE_PERIODS[0][1])
    number = seed_storage_status(client, workspace, state="succeeded", schema=None)
    async def project():
        async with client.app_state["sessionmaker"]() as db:
            result = await _reconcile_storage_addon_operations(db,
                current=datetime(2025, 1, 15, tzinfo=UTC), workspace_id=workspace)
            assert result["storage_addon_operations_projected"] == 1
            await db.commit()
    asyncio.run(project())
    set_subscription(client, workspace, plan_code="free", state="free", cycle="year",
        capacity_bytes=5_000_000_000, paid_through=datetime(2024, 1, 1, tzinfo=UTC))
    before = billing_rows_snapshot(client)
    response = client.get(f"/billing/checkout/status/{number}", headers=headers)
    assert response.status_code == 200
    assert '>Оплачено</h2>' in response.text
    assert 'data-billing-state="succeeded_projected"' in response.text
    assert "01.01.2025" in response.text and "01.02.2025" in response.text
    assert billing_rows_snapshot(client) == before


def seed_invoice_projection(client, workspace, snapshot, *, state="succeeded", privacy=None):
    """Insert immutable synthetic purchase data before exercising read-only invoice GET."""
    from twobrain_rec_server.db.models import UserIdentity

    async def seed():
        async with client.app_state["sessionmaker"]() as db:
            viewer = await db.get(UserIdentity, USER_ID)
            viewer.timezone = "Europe/Istanbul"
            target = workspace
            if privacy == "foreign":
                other = Workspace(organization_id=viewer.organization_id,
                    slug=f"invoice-foreign-{uuid4().hex}", name="Synthetic foreign", kind="corporate")
                db.add(other)
                await db.flush()
                target = other.id
            elif privacy == "previous_owner":
                payer = UserIdentity(organization_id=viewer.organization_id,
                    external_subject=f"invoice-previous-{uuid4().hex}")
                db.add(payer)
                await db.flush()
                subscription = await db.scalar(select(WorkspaceSubscription).where(
                    WorkspaceSubscription.workspace_id == workspace))
                if subscription is None:
                    subscription = WorkspaceSubscription(workspace_id=workspace)
                    db.add(subscription)
                subscription.billing_owner_id = payer.id
            operation = BillingOperation(workspace_id=target, kind="initial_checkout",
                state=state, idempotency_key=f"invoice-read-{uuid4().hex}", request_snapshot={})
            db.add(operation)
            await db.flush()
            db.add(BillingInvoice(workspace_id=target, operation_id=operation.id,
                safe_number="INV-PROJECTION", amount_minor=125000, currency="RUB", status=state,
                plan_snapshot=snapshot, receipt_contact_snapshot="synthetic-payer@example.test",
                created_at=datetime(2026, 10, 3, 21, 30, tzinfo=UTC)))
            await db.commit()
    asyncio.run(seed())


def invoice_main(html):
    return re.search(r'<main\b[^>]*>(.*?)</main>', html, re.S)[1]


@pytest.mark.parametrize("year", [2025, 2027])
def test_invoice_projection_short_and_exact_local_dates_are_read_only(client, owner, year):
    workspace, headers = owner
    seed_invoice_projection(client, workspace, {"cycle": "month",
        "service_starts_at": f"{year}-11-03T21:30:00+00:00",
        "service_ends_at": f"{year}-12-03T21:30:00+00:00"})
    before = billing_rows_snapshot(client)
    response = client.get("/billing/invoices/INV-PROJECTION", headers=headers)
    assert response.status_code == 200
    main = invoice_main(response.text)
    overview = main.split("<details", 1)[0]
    assert f"04.11.{year} — 04.12.{year}" in overview
    assert "00:30" not in overview
    assert f"04.11.{year}, 00:30 (UTC+03:00)" in main
    assert f"04.12.{year}, 00:30 (UTC+03:00)" in main
    assert "Дата создания платежа" in main and "04.10.2026, 00:30 (UTC+03:00)" in main
    assert "Тариф действует" not in overview and "Активна" not in overview
    assert billing_rows_snapshot(client) == before


@pytest.mark.parametrize("snapshot,known_cycle", [
    ({}, None), ({"cycle": "week"}, None), ({"cycle": "month"}, "месяц"),
    ({"cycle": "year"}, "год"),
    ({"cycle": "week", "service_starts_at": "garbage", "service_ends_at": "2027-12-03"}, None),
    ({"cycle": "week", "service_starts_at": "2027-12-03T21:30:00+00:00",
      "service_ends_at": "2027-11-03T21:30:00+00:00"}, None),
    ({"cycle": "week", "service_starts_at": "2027-11-03T21:30:00",
      "service_ends_at": "2027-12-03T21:30:00"}, None),
    ({"cycle": "week", "service_starts_at": "9999-12-31T20:00:00+00:00",
      "service_ends_at": "9999-12-31T23:59:59+00:00"}, None),
    ({"cycle": "week", "service_starts_at": "0001-01-01T00:00:00+14:00",
      "service_ends_at": "0001-01-01T01:00:00+14:00"}, None),
])
def test_invoice_projection_invalid_period_never_invents_a_month(client, owner, snapshot, known_cycle):
    workspace, headers = owner
    seed_invoice_projection(client, workspace, snapshot)
    before = billing_rows_snapshot(client)
    response = client.get("/billing/invoices/INV-PROJECTION", headers=headers)
    assert response.status_code == 200
    main = invoice_main(response.text)
    overview = re.sub(r"<[^>]+>", " ", main.split("<details", 1)[0]).lower()
    assert "оплаченный срок" not in overview
    if known_cycle:
        assert known_cycle in overview
    else:
        assert "месяц" not in overview and "год" not in overview
    assert "без даты" not in main.lower() and "garbage" not in main
    assert billing_rows_snapshot(client) == before


@pytest.mark.parametrize("state,registration,url,label", [
    ("succeeded", "succeeded", None, "Чек зарегистрирован"),
    ("pending", "pending", None, "Чек формируется"),
    ("unknown", None, None, "Чек пока не найден"),
    ("canceled", "succeeded", "https://yookassa.ru/synthetic-receipt", "Открыть чек"),
    ("manual_resolution", "succeeded", "https://evil.example.test/receipt", "Чек зарегистрирован"),
])
def test_invoice_projection_receipt_and_recovery_truth_is_read_only(client, owner, state, registration, url, label):
    workspace, headers = owner
    seed_invoice_projection(client, workspace, {"cycle": "month", "receipt_registration": registration,
        "receipt_url": url, "service_resolution": "storage_period_elapsed"}, state=state)
    before = billing_rows_snapshot(client)
    response = client.get("/billing/invoices/INV-PROJECTION", headers=headers)
    assert response.status_code == 200
    main = invoice_main(response.text)
    assert label in main
    assert "услуга требует сверки" in main.split("<details", 1)[0]
    assert ("Открыть чек" in main) == (url == "https://yookassa.ru/synthetic-receipt")
    assert "https://evil.example.test/receipt" not in main
    assert ("/billing/checkout/status/INV-PROJECTION" in main) == (state != "succeeded")
    assert "отправлен на почту" not in main.lower()
    assert billing_rows_snapshot(client) == before


@pytest.mark.parametrize("privacy,gap,expected", [
    ("foreign", None, 303), ("previous_owner", None, 303),
    ("previous_owner", "owner_changed", 200),
    ("previous_owner", "workspace_scope_invalid", 200),
])
def test_invoice_projection_preserves_previous_payer_and_workspace_privacy(client, owner, privacy, gap, expected):
    workspace, headers = owner
    seed_invoice_projection(client, workspace, {"cycle": "month", "service_resolution": gap,
        "receipt_registration": "succeeded", "receipt_url": "https://yookassa.ru/synthetic-private-receipt",
        "payment_method_label": "•••• 4242"}, privacy=privacy)
    before = billing_rows_snapshot(client)
    response = client.get("/billing/invoices/INV-PROJECTION", headers=headers, follow_redirects=False)
    assert response.status_code == expected
    assert "4242" not in response.text and "synthetic-payer" not in response.text
    assert "synthetic-private-receipt" not in response.text
    if expected == 303:
        assert response.headers["location"] == "/billing/history?result=not_found"
    else:
        main = invoice_main(response.text)
        assert "услуга требует сверки" in main.split("<details", 1)[0]
        assert "Чек доступен плательщику" in main
        assert "Открыть чек" not in main
    assert billing_rows_snapshot(client) == before


def test_invoice_projection_preserves_distinct_storage_intervals_without_inventing_invalid_dates(client, owner):
    workspace, headers = owner
    seed_invoice_projection(client, workspace, {"cycle": "month", "storage_segments": [
        {"starts_at": "2027-11-03T21:30:00+00:00", "ends_at": "2027-12-03T21:30:00+00:00",
         "capacity_bytes": 10_000_000_000},
        {"starts_at": "2027-12-03T21:30:00+00:00", "ends_at": "2028-01-03T21:30:00+00:00",
         "capacity_bytes": 15_000_000_000},
        {"starts_at": "bad", "ends_at": "2028-01-03", "capacity_bytes": 20_000_000_000},
    ]})
    before = billing_rows_snapshot(client)
    response = client.get("/billing/invoices/INV-PROJECTION", headers=headers)
    assert response.status_code == 200
    main = invoice_main(response.text)
    assert "Оплаченные интервалы хранения" in main
    intervals = re.search(r"Оплаченные интервалы хранения</dt><dd><ul>(.*?)</ul>", main, re.S)[1]
    rows = re.findall(r"<li>(.*?)</li>", intervals, re.S)
    assert len(rows) == 3
    assert "04.11.2027, 00:30 (UTC+03:00) — 04.12.2027, 00:30 (UTC+03:00): 10 GB" in rows[0]
    assert "04.12.2027, 00:30 (UTC+03:00) — 04.01.2028, 00:30 (UTC+03:00): 15 GB" in rows[1]
    assert rows[2] == "Срок не указан: 20 GB"
    assert billing_rows_snapshot(client) == before


@pytest.mark.parametrize("support,discount", [
    ("billing@example.test", 0), ("billing@example.test", 25),
    ("not-an-email", 0), (None, 0),
])
def test_invoice_projection_support_intents_and_real_discount_are_read_only(client, owner, support, discount):
    workspace, headers = owner
    client.app.state.settings.billing_support_email = support
    seed_invoice_projection(client, workspace, {"cycle": "month", "discount_percent": discount,
        "payment_method_label": "•••• 4242", "provider_payment_id": "synthetic-private-provider"})
    before = billing_rows_snapshot(client)
    response = client.get("/billing/invoices/INV-PROJECTION", headers=headers)
    assert response.status_code == 200
    main = invoice_main(response.text)
    assert ("Скидка 25%" in main) == (discount == 25)
    assert "Скидка 0%" not in main
    mailtos = [unescape(value) for value in re.findall(r'href="(mailto:[^"]+)"', main)]
    if support == "billing@example.test":
        assert "Вопрос об оплате" in main and "Запросить возврат" in main
        assert len(mailtos) == 2
        subjects = {parse_qs(urlsplit(value).query)["subject"][0] for value in mailtos}
        assert subjects == {"Вопрос об оплате INV-PROJECTION", "Возврат по платежу INV-PROJECTION"}
        for value in mailtos:
            assert "4242" not in value and "synthetic-private-provider" not in value
            assert "synthetic-payer" not in value
            assert urlsplit(value).path == support
    else:
        assert mailtos == [] and "Адрес поддержки сейчас недоступен" in main
        assert 'href="/billing/history#billing-help"' in main
        assert "not-an-email" not in main
    assert billing_rows_snapshot(client) == before


@pytest.mark.parametrize("observation", [False, True])
@pytest.mark.parametrize("support,normalized", [
    (None, None), ("not-an-email", None), ("billing%0d%0a@example.test", None),
    ("billing@example.test\r\nBcc:evil@example.test", None),
    ("billing?cc=evil&tag@example.test", "billing?cc=evil&tag@example.test"),
    ("billing+tag%box@example.test", "billing+tag%box@example.test"),
    ("Support <billing@example.test>", "billing@example.test"),
    ("\x00 <billing@example.test>", None), ("Support\x01 <billing@example.test>", None),
    ("Support%00 <billing@example.test>", None), ("Support%7f <billing@example.test>", None),
])
def test_support_help_fallback_and_siblings_are_safe_without_checkout(client, owner, observation, support, normalized):
    workspace, headers = owner
    settings = client.app.state.settings
    settings.billing_checkout_enabled = False
    settings.billing_provider_observation_enabled = observation
    settings.billing_support_email = support
    seed_invoice_projection(client, workspace, {}, state="unknown")
    before = billing_rows_snapshot(client)
    invoice = client.get("/billing/invoices/INV-PROJECTION", headers=headers)
    assert invoice.status_code == 200
    if normalized is None:
        assert 'href="/billing/history#billing-help"' in invoice_main(invoice.text)
    for path in ("/billing/history", "/billing/checkout/status/INV-PROJECTION", "/referrals",
                 "/account/fair-use", "/desktop/account/fair-use"):
        response = client.get(path, headers=headers)
        assert response.status_code == 200, path
        main = invoice_main(response.text)
        links = [unescape(value) for value in re.findall(r'href="(mailto:[^"]+)"', main)]
        if normalized is None:
            assert links == [], path
            assert "Скопировать адрес" not in main
            if support:
                assert support not in unescape(main)
            if path == "/billing/history":
                assert "Контакт поддержки пока не настроен" in main
                assert 'href="/billing"' in main
        else:
            assert len(links) == (2 if path.startswith("/billing/checkout/status/") else 1), path
            assert urlsplit(links[0]).query == "", path
            assert urlsplit(links[0]).path == quote(normalized, safe="@."), path
            assert unquote(urlsplit(links[0]).path) == normalized, path
            if path == "/billing/history":
                assert f'data-copy-value="{normalized}"' in unescape(main)
        assert billing_rows_snapshot(client) == before, path
