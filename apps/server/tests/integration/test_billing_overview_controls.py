"""Overview controls reuse existing billing authority and never create money on GET."""

import asyncio
from datetime import UTC, datetime
from urllib.parse import parse_qs, urlsplit

import pytest
from sqlalchemy import func, select

from tests.integration import test_billing_clarity as clarity
from tests.integration.test_billing_clarity import (
    payment_counts,
    seed_payment,
    set_subscription,
    unverify_email,
)
from tests.integration.test_billing_purchase_journey import quote_id, seed_catalog_and_budget
from tests.integration.test_billing_review_regressions import seed_periods
from twobrain_rec_server.cabinet.web_routes import billing as routes
from twobrain_rec_server.db.models import BillingPaymentMethod, BillingPurchaseQuote

owner = clarity.owner


@pytest.fixture
def contexts(monkeypatch):
    rendered = []
    render = routes._page_shell

    def capture(*args, **kwargs):
        rendered.append(kwargs)
        return render(*args, **kwargs)

    monkeypatch.setattr(routes, "_page_shell", capture)
    return rendered


def seed_saved_card(client, workspace):
    async def run():
        async with client.app_state["sessionmaker"]() as db:
            db.add(BillingPaymentMethod(
                workspace_id=workspace, owner_user_id=clarity.USER_ID,
                encrypted_provider_ref="synthetic-unopened-reference", key_version="billing-v1",
                masked_label="•••• 4242", state="active", is_default=True,
                verified_at=datetime.now(UTC),
            ))
            await db.commit()
    asyncio.run(run())


def test_overview_reuses_storage_choices_without_preparing_quotes(client, owner, contexts):
    workspace, headers = owner
    seed_catalog_and_budget(client, workspace)
    seed_periods(client, workspace)
    set_subscription(client, workspace, next_capacity_bytes=15_000_000_000)

    async def quote_count():
        async with client.app_state["sessionmaker"]() as db:
            return await db.scalar(select(func.count()).select_from(BillingPurchaseQuote))

    seed_saved_card(client, workspace)
    before = (asyncio.run(quote_count()), payment_counts(client))
    client.get("/billing/storage?package_count=1", headers=headers)
    legacy = contexts[-1]
    for _ in range(3):
        assert client.get("/billing?package_count=1", headers=headers).status_code == 200
        current = contexts[-1]
        assert current["storage_options"] == legacy["storage_options"]
        assert current["selected_package_count"] == 1
        assert current["subscription"].next_capacity_bytes == 15_000_000_000
        assert current["next_capacity_label"] == "15 GB"
        assert current["storage_return_to"] == "overview"
        assert current["request_storage_editor_open"] is True
        assert current["paid_through_short_label"]
    assert (asyncio.run(quote_count()), payment_counts(client)) == before


@pytest.mark.parametrize("marker,overview", [("overview", True), ("", False), ("https://wrong.test", False)])
def test_storage_preview_error_preserves_editor_and_only_fixed_return_marker(
    client, owner, contexts, marker, overview,
):
    workspace, headers = owner
    seed_catalog_and_budget(client, workspace)
    seed_periods(client, workspace)
    before = payment_counts(client)
    response = client.post("/billing/storage/preview", headers=headers, data={
        "package_count": "2", "promo_code": "UNKNOWN-SYNTHETIC", "return_to": marker,
    })
    assert response.status_code == 409
    current = contexts[-1]
    assert current["content_template"].endswith(
        "billing_overview_content.html" if overview else "billing_storage_content.html"
    )
    assert current["selected_package_count"] == 2
    assert current["storage_promo_code"] == "UNKNOWN-SYNTHETIC"
    assert current["storage_preview_error"]
    assert current["storage_promo_invalid"] is True
    if overview:
        assert current["storage_return_to"] == "overview"
    assert payment_counts(client) == before


@pytest.mark.parametrize("marker,location", [
    ("overview", "/billing?subscription_result=cancelled#billing-renewal-settings"),
    ("", "/billing/subscription?result=cancelled"),
    ("https://wrong.test", "/billing/subscription?result=cancelled"),
])
def test_cancel_renewal_returns_to_origin_without_changing_paid_access(client, owner, marker, location):
    workspace, headers = owner
    seed_periods(client, workspace)
    set_subscription(client, workspace, recurring_allowed=True, recurring_authority_version=4)
    response = client.post("/billing/subscription/cancel", headers=headers, follow_redirects=False, data={
        "expected_authority_version": "4", "return_to": marker,
    })
    assert response.status_code == 303
    assert response.headers["location"] == location


@pytest.mark.parametrize("path,data,key,result", [
    ("/billing/subscription/cancel", {"expected_authority_version": "0"}, "subscription", "conflict"),
    ("/billing/payment-method/delete", {}, "payment", "renewal_on"),
    ("/billing/storage/cancel-selection", {"selection_version": "99"}, "storage", "conflict"),
])
def test_overview_control_failures_return_feedback_without_money(client, owner, path, data, key, result):
    workspace, headers = owner
    seed_periods(client, workspace)
    set_subscription(client, workspace, recurring_allowed=True, recurring_authority_version=4)
    before = payment_counts(client)
    response = client.post(path, headers=headers, follow_redirects=False, data={**data, "return_to": "overview"})
    assert response.status_code == 303
    assert response.headers["location"].startswith(f"/billing?{key}_result={result}#")
    assert payment_counts(client) == before


@pytest.mark.parametrize("marker", ["overview", "", "https://wrong.test"])
def test_deferred_storage_returns_to_overview_without_email_or_money(client, owner, contexts, marker):
    workspace, headers = owner
    seed_catalog_and_budget(client, workspace)
    seed_periods(client, workspace)
    unverify_email(client)
    preview = client.post("/billing/storage/preview", headers=headers, data={
        "package_count": "0", "return_to": marker,
    })
    bound = quote_id(preview)
    assert contexts[-1]["purchase"]["return_to"] == ("overview" if marker == "overview" else "")
    response = client.post("/billing/purchases/confirm", headers=headers, follow_redirects=False, data={
        "quote_id": bound, "purchase_consent": "true", "return_to": marker,
    })
    assert response.headers["location"] == (
        "/billing?storage_result=scheduled#billing-storage-title" if marker == "overview"
        else "/billing/storage?result=scheduled"
    )
    replay = client.post("/billing/purchases/confirm", headers=headers, follow_redirects=False, data={
        "quote_id": bound, "purchase_consent": "true", "return_to": marker,
    })
    assert replay.headers["location"] == response.headers["location"]
    canceled = client.post("/billing/storage/cancel-selection", headers=headers, follow_redirects=False, data={
        "selection_version": "1", "return_to": marker,
    })
    assert canceled.headers["location"] == (
        "/billing?storage_result=schedule_canceled#billing-storage-title" if marker == "overview"
        else "/billing/storage?result=schedule_canceled"
    )
    assert payment_counts(client)[1] == 2  # Only seed_periods' historical paid invoices.


def test_pending_purchase_confirmation_keeps_status_recovery_for_overview_origin(client, owner):
    workspace, headers = owner
    seed_catalog_and_budget(client, workspace)
    seed_periods(client, workspace)
    bound = quote_id(client.post("/billing/storage/preview", headers=headers, data={
        "package_count": "1", "return_to": "overview",
    }))
    seed_payment(client, workspace)
    before = payment_counts(client)
    response = client.post("/billing/purchases/confirm", headers=headers, follow_redirects=False, data={
        "quote_id": bound, "purchase_consent": "true", "return_to": "overview",
    })
    assert response.headers["location"] == "/billing/checkout/status/INV-CLARITY"
    assert payment_counts(client) == before


def test_overview_card_deletion_revokes_only_saved_authority(client, owner, contexts):
    workspace, headers = owner
    seed_periods(client, workspace)
    set_subscription(client, workspace, recurring_allowed=False)
    seed_saved_card(client, workspace)
    before = payment_counts(client)
    for result in ("removed", "none"):
        response = client.post("/billing/payment-method/delete", headers=headers,
                               data={"return_to": "overview"}, follow_redirects=False)
        assert response.headers["location"] == f"/billing?payment_result={result}#billing-payment-method"
    client.get("/billing", headers=headers)
    assert contexts[-1]["method_present"] is False
    assert contexts[-1]["plan_code"] == "personal"
    assert contexts[-1]["paid_through_short_label"]
    assert payment_counts(client) == before


def test_missing_receipt_contact_returns_to_overview_editor_without_money(client, owner, contexts):
    workspace, headers = owner
    seed_catalog_and_budget(client, workspace)
    seed_periods(client, workspace)
    preview = client.post("/billing/storage/preview", headers=headers, data={
        "package_count": "1", "return_to": "overview",
    })
    bound = quote_id(preview)
    unverify_email(client)
    before = payment_counts(client)
    response = client.post("/billing/purchases/confirm", headers=headers, data={
        "quote_id": bound, "purchase_consent": "true", "return_to": "overview",
    })
    assert response.status_code == 409
    context = contexts[-1]
    assert context["content_template"].endswith("billing_overview_content.html")
    assert context["selected_package_count"] == 1
    assert context["receipt_contact_ready"] is False
    assert parse_qs(urlsplit(context["receipt_contact_action_url"]).query)["next"] == ["/billing?package_count=1"]
    assert payment_counts(client) == before


@pytest.mark.parametrize("path,data", [
    ("/billing/storage/preview", {"package_count": "1"}),
    ("/billing/purchases/confirm", {"quote_id": "synthetic"}),
])
def test_overview_purchase_database_unavailable_fails_closed(client, owner, contexts, monkeypatch, path, data):
    _, headers = owner

    async def no_db():
        yield None

    monkeypatch.setitem(client.app.dependency_overrides, routes.WebDbDependency.dependency, no_db)
    response = client.post(path, headers=headers, data={**data, "return_to": "overview"})
    assert response.status_code == 409
    assert contexts[-1]["billing_data_available"] is False
    assert contexts[-1]["storage_options"] == []
    assert contexts[-1]["subscription"] is None
    assert contexts[-1]["method_present"] is False


@pytest.mark.parametrize("reason", ["purchase", "disabled"])
def test_storage_service_error_does_not_mark_valid_promo_input_invalid(client, owner, contexts, monkeypatch, reason):
    workspace, headers = owner
    seed_catalog_and_budget(client, workspace)
    seed_periods(client, workspace)
    if reason == "disabled":
        monkeypatch.setattr(routes, "billing_checkout_allowed", lambda *_args: False)
    else:
        async def unavailable(*_args, **_kwargs):
            raise routes.PurchaseError("Цена временно недоступна")
        monkeypatch.setattr(routes, "calculate_storage_purchase", unavailable)
    response = client.post("/billing/storage/preview", headers=headers, data={
        "package_count": "1", "return_to": "overview",
    })
    assert response.status_code == 409
    assert contexts[-1]["storage_preview_error"]
    assert contexts[-1]["storage_promo_invalid"] is False
    assert contexts[-1]["selected_package_count"] == 1
