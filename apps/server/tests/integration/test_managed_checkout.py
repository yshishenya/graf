"""Synthetic hosted checkout through HTTP and PostgreSQL; no provider network calls."""

import html
import re
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import async_sessionmaker

from tests.fakes.auth_contexts import USER_ID
from tests.integration.test_account_lifecycle import (
    _bind_web_session,
    _issue_web_session,
    _seed_personal_workspace,
)
from tests.integration.test_system_admin_billing import _capabilities
from twobrain_rec_server.cabinet.web_routes import billing
from twobrain_rec_server.db.models import ExternalIdentity
from twobrain_rec_server.db.models.billing import (
    BillingInvoice,
    BillingOperation,
    BillingPlan,
    BillingPlanPrice,
    BillingPlanVersion,
    WorkspaceSubscription,
)

pytestmark = pytest.mark.strict_rls


@pytest.fixture
def checkout(client, monkeypatch):
    settings = client.app.state.settings
    for key, value in {
        "public_base_url": "https://rec.example.test",
        "billing_checkout_enabled": True,
        "billing_emergency_stop": False,
        "billing_yookassa_environment": "test",
        "billing_receipt_tax_system_code": 2,
        "billing_receipt_vat_code": 1,
    }.items():
        monkeypatch.setattr(settings, key, value)
    calls = []

    class Provider:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

        async def create_payment(self, **kwargs):
            calls.append(kwargs)
            return {
                "id": "synthetic-managed-payment",
                "confirmation": {"confirmation_url": "https://yookassa.ru/checkout/synthetic-managed"},
            }

    monkeypatch.setattr(billing, "YooKassaClient", lambda _settings: Provider())

    async def seed():
        workspace, device = await _seed_personal_workspace(client)
        token, session_id = await _issue_web_session(
            client, user_id=USER_ID, workspace_id=workspace, device_id=device,
        )
        async with client.app_state["sessionmaker"]() as db:
            db.add(ExternalIdentity(
                user_id=USER_ID, provider="email", provider_subject="synthetic-checkout",
                email="synthetic@example.invalid", is_verified=True, is_active=True,
            ))
            plan = BillingPlan(id=uuid4(), code="research_plus", display_name="Исследования")
            db.add(plan)
            await db.flush()
            versions = []
            for number, amount in ((1, 123400), (2, 234500)):
                version = BillingPlanVersion(
                    id=uuid4(), plan_id=plan.id, plan_code=plan.code, version=number, status="draft",
                    capability_schema_version=1,
                    capabilities={**_capabilities(), "processing_unlimited": False, "processing_seconds": 24000},
                    display_terms={"name": "Исследования", "description": "", "audience": "public", "trial_days": 0},
                    cycle="none", currency="RUB", storage_bytes=4_000_000_000,
                    processing_mode="quota", policy_snapshot={"offer_version": f"synthetic-research-v{number}"},
                )
                db.add(version)
                await db.flush()
                db.add_all([BillingPlanPrice(
                    id=uuid4(), version_id=version.id, cycle=cycle, currency="RUB", amount_minor=amount*factor,
                ) for cycle, factor in (("month", 1), ("year", 10))])
                await db.flush()
                version.status = "published"
                version.enabled_for_checkout = True
                await db.flush()
                versions.append(version.id)
            plan.current_version_id = versions[0]
            plan.sales_state = "open"
            await db.commit()
        return workspace, token, session_id, plan.id, versions

    workspace, token, session, plan_id, versions = client.portal.call(seed)
    headers = _bind_web_session(client, token=token, session_id=session)
    from tests.integration.test_rls_postgres_policies import _exact_app_role_engine

    role_context = _exact_app_role_engine(str(settings.database_url))
    app_engine = client.portal.call(role_context.__aenter__)

    async def grant_lock():
        async with client.app_state["sessionmaker"]() as db:
            await db.execute(text("grant execute on function billing_lock_checkout_catalog(text) to twobrain_rec_app"))
            await db.execute(text("revoke insert, update, delete on billing_plans,billing_plan_versions,billing_plan_prices from twobrain_rec_app"))
            await db.commit()
        async with app_engine.connect() as conn:
            assert await conn.scalar(text("select session_user")) == "twobrain_rec_app"
    client.portal.call(grant_lock)
    monkeypatch.setattr(client.app.state, "db_sessionmaker", async_sessionmaker(app_engine, expire_on_commit=False))
    try:
        yield client, headers, calls, workspace, plan_id, versions
    finally:
        client.portal.call(role_context.__aexit__, None, None, None)


def _form(client, cycle="month"):
    page = client.get(f"/billing/checkout?plan_code=research_plus&cycle={cycle}")
    assert page.status_code == 200
    assert "Исследования" in page.text and "400 мин" in page.text
    assert "Без лимита по минутам" not in page.text
    fields = {name: html.unescape(value) for name, value in re.findall(
        r'<input type="hidden" name="([^"]+)" value="([^"]*)"', page.text,
    )}
    assert len(fields["expected_quote"]) == 64 and fields["plan_code"] == "research_plus"
    return fields | {"offer_consent": "true", "recurring_consent": "true"}


async def _state(client):
    async with client.app_state["sessionmaker"]() as db:
        return list(await db.scalars(select(BillingOperation))), list(await db.scalars(select(BillingInvoice)))


@pytest.mark.parametrize("cycle", ["month", "year"])
def test_checkout_exact_offer_retry_and_confirmation_after_close(checkout, cycle):
    client, headers, calls, workspace, plan_id, versions = checkout
    form = _form(client, cycle)
    response = client.post("/billing/checkout/start", data=form, headers=headers, follow_redirects=False)
    assert response.headers["location"] == "https://yookassa.ru/checkout/synthetic-managed"
    amount = 123400 if cycle == "month" else 1234000
    assert len(calls) == 1 and calls[0]["amount_minor"] == amount
    assert calls[0]["description"] == f"GRAF Исследования, {cycle}"
    operations, invoices = client.portal.call(lambda: _state(client))
    assert len(operations) == len(invoices) == 1
    snapshot = invoices[0].plan_snapshot
    assert snapshot["catalog_snapshot"]["plan_version_id"] == str(versions[0])
    assert snapshot["payable_amount_minor"] == amount

    async def close():
        async with client.app_state["sessionmaker"]() as db:
            plan = await db.get(BillingPlan, plan_id)
            plan.sales_state = "closed"
            version = await db.get(BillingPlanVersion, versions[0])
            version.enabled_for_checkout = False
            version.status = "retired"
            await db.commit()
    client.portal.call(close)
    retry = client.post("/billing/checkout/start", data=form, headers=headers, follow_redirects=False)
    assert retry.headers["location"] == response.headers["location"] and len(calls) == 1
    for changed in ({"cycle": "year" if cycle == "month" else "month"}, {"plan_code": "personal"}, {"promo_code": "CHANGED"}):
        refused = client.post("/billing/checkout/start", data=form | changed, headers=headers, follow_redirects=False)
        assert "result=conflict" in refused.headers["location"]
    assert len(calls) == 1

    async def confirm():
        from twobrain_rec_server.billing.entitlements import grant_confirmed_payment
        async with client.app_state["sessionmaker"]() as db:
            result = await grant_confirmed_payment(
                db, workspace_id=workspace, provider_payment_id="synthetic-managed-payment",
                amount_minor=amount, currency="RUB", paid_at=datetime.now(UTC),
            )
            await db.commit()
            subscription = await db.get(WorkspaceSubscription, workspace)
            return result, subscription.plan_code, subscription.pinned_plan_version_id
    assert client.portal.call(confirm) == ("granted", "research_plus", versions[0])


@pytest.mark.parametrize("change", ["missing_quote", "cycle", "price", "close", "expiry", "consent", "promo"])
def test_checkout_rejects_changed_or_unapproved_terms_without_invoice(checkout, change):
    client, headers, calls, _, plan_id, versions = checkout
    form = _form(client)
    if change == "missing_quote":
        form.pop("expected_quote")
    elif change == "cycle":
        form["cycle"] = "year"
    elif change == "consent":
        form.pop("recurring_consent")
    elif change == "promo":
        form["promo_code"] = "UNKNOWN"
    else:
        async def alter():
            async with client.app_state["sessionmaker"]() as db:
                plan = await db.get(BillingPlan, plan_id)
                if change == "price":
                    plan.current_version_id = versions[1]
                elif change == "close":
                    plan.sales_state = "closed"
                else:
                    version = await db.get(BillingPlanVersion, versions[0])
                    version.effective_until = datetime.now(UTC) - timedelta(seconds=1)
                await db.commit()
        client.portal.call(alter)
    response = client.post("/billing/checkout/start", data=form, headers=headers, follow_redirects=False)
    result = "catalog_not_approved" if change in {"close", "expiry"} else "consent_required" if change == "consent" else "promo_invalid" if change == "promo" else "terms_changed"
    assert f"result={result}" in response.headers["location"]
    assert "plan_code=research_plus" in response.headers["location"]
    assert calls == [] and client.portal.call(lambda: _state(client)) == ([], [])
    if change == "price":
        updated = _form(client)
        response = client.post("/billing/checkout/start", data=updated, headers=headers, follow_redirects=False)
        assert response.headers["location"] == "https://yookassa.ru/checkout/synthetic-managed"
        assert calls[0]["amount_minor"] == 234500


@pytest.mark.parametrize("target", ["plan", "version"])
def test_catalog_close_serializes_with_admission_without_catalog_write_grant(checkout, target):
    from sqlalchemy.exc import DBAPIError

    from tests.fakes.auth_contexts import ORG_ID
    from twobrain_rec_server.billing.catalog import lock_checkout_catalog, read_public_catalog
    from twobrain_rec_server.db.tenant_context import TenantDatabaseContext, apply_tenant_context

    client, _, _, workspace, plan_id, versions = checkout

    async def race():
        async with client.app.state.db_sessionmaker() as buyer:
            with pytest.raises(DBAPIError):
                await lock_checkout_catalog(buyer, plan_code="research_plus")
            await buyer.rollback()
            await apply_tenant_context(buyer, TenantDatabaseContext(
                organization_id=ORG_ID, workspace_id=workspace, user_id=USER_ID,
            ))
            assert await lock_checkout_catalog(buyer, plan_code="research_plus")
            assert "research_plus" in await read_public_catalog(buyer, now=datetime.now(UTC))
            statement = (
                "update billing_plans set sales_state='closed' where id=:id" if target == "plan" else
                "update billing_plan_versions set enabled_for_checkout=false where id=:id"
            )
            params = {"id": plan_id if target == "plan" else versions[0]}
            async with client.app_state["sessionmaker"]() as writer:
                await writer.execute(text("set local lock_timeout='150ms'"))
                with pytest.raises(DBAPIError) as blocked:
                    await writer.execute(text(statement), params)
                assert blocked.value.orig.sqlstate == "55P03"
                await writer.rollback()
            await buyer.commit()
            async with client.app_state["sessionmaker"]() as writer:
                await writer.execute(text(statement), params)
                await writer.commit()
            await apply_tenant_context(buyer, TenantDatabaseContext(
                organization_id=ORG_ID, workspace_id=workspace, user_id=USER_ID,
            ))
            assert await lock_checkout_catalog(buyer, plan_code="research_plus")
            assert await read_public_catalog(buyer, now=datetime.now(UTC), plan_code="research_plus") == {}
            with pytest.raises(DBAPIError) as forbidden:
                await buyer.execute(text("update billing_plans set sales_state='open' where id=:id"), {"id": plan_id})
            assert forbidden.value.orig.sqlstate == "42501"
    client.portal.call(race)


def test_public_plans_use_managed_name_price_quota_and_selected_period(checkout):
    client, _, _, _, plan_id, _ = checkout
    page = client.get("/billing/plans?cycle=year")
    assert page.status_code == 200
    assert "Исследования" in page.text and "12 340 ₽" in page.text
    assert "400 мин 0 сек в календарный месяц" in page.text
    assert 'href="/billing/checkout?plan_code=research_plus&amp;cycle=year"' in page.text
    assert "Платная обработка не ограничена" not in page.text
    async def close():
        async with client.app_state["sessionmaker"]() as db:
            plan = await db.get(BillingPlan, plan_id)
            plan.sales_state = "closed"
            await db.commit()
    client.portal.call(close)
    page = client.get("/billing/plans")
    assert page.status_code == 200 and "research_plus" not in page.text
    assert "Исследования" not in page.text


def test_concurrent_same_checkout_creates_one_invoice_and_one_provider_call(checkout):
    from concurrent.futures import ThreadPoolExecutor

    client, headers, calls, _, _, _ = checkout
    form = _form(client)
    def submit():
        return client.post("/billing/checkout/start", data=form, headers=headers, follow_redirects=False)
    with ThreadPoolExecutor(max_workers=2) as executor:
        responses = list(executor.map(lambda _: submit(), range(2)))
    assert all(response.status_code == 303 for response in responses)
    assert len(calls) == 1
    operations, invoices = client.portal.call(lambda: _state(client))
    assert len(operations) == len(invoices) == 1
    assert all(response.headers["location"] in {
        "https://yookassa.ru/checkout/synthetic-managed",
        f"/billing/checkout/status/{invoices[0].safe_number}",
    } for response in responses)


def test_managed_promo_changed_discount_requires_new_confirmation_and_reserves_once(checkout):
    from twobrain_rec_server.billing.promotions import promo_code_hash
    from twobrain_rec_server.db.models import PromotionCampaign, PromotionRedemption

    client, headers, calls, _, _, _ = checkout
    campaign_id = uuid4()
    async def seed_campaign():
        async with client.app_state["sessionmaker"]() as db:
            db.add(PromotionCampaign(
                id=campaign_id, code_hash=promo_code_hash("SYNTHETIC20"), campaign_version="synthetic-v1",
                plan_code="research_plus", cycle="month", discount_percent=20, max_redemptions=10, enabled=True,
            ))
            await db.commit()
    client.portal.call(seed_campaign)
    result = client.post("/billing/checkout/preview", data={
        "plan_code": "research_plus", "cycle": "month", "promo_code": "SYNTHETIC20",
    }, headers=headers, follow_redirects=False)
    assert "promo_applied" in result.headers["location"] and "SYNTHETIC20" not in result.headers["location"]
    form = _form(client)
    assert form["promo_code"] == "SYNTHETIC20"
    async def edit_campaign():
        async with client.app_state["sessionmaker"]() as db:
            campaign = await db.get(PromotionCampaign, campaign_id)
            campaign.discount_percent = 10
            campaign.campaign_version = "synthetic-v2"
            await db.commit()
    client.portal.call(edit_campaign)
    stale = client.post("/billing/checkout/start", data=form, headers=headers, follow_redirects=False)
    assert "terms_changed" in stale.headers["location"]
    assert calls == [] and client.portal.call(lambda: _state(client)) == ([], [])
    updated = _form(client)
    assert updated["promo_code"] == "SYNTHETIC20" and updated["expected_quote"] != form["expected_quote"]
    paid = client.post("/billing/checkout/start", data=updated, headers=headers, follow_redirects=False)
    assert paid.headers["location"] == "https://yookassa.ru/checkout/synthetic-managed"
    assert len(calls) == 1 and calls[0]["amount_minor"] == 111060
    replay = client.post("/billing/checkout/start", data=updated, headers=headers, follow_redirects=False)
    assert replay.headers["location"] == paid.headers["location"] and len(calls) == 1
    async def counters():
        async with client.app_state["sessionmaker"]() as db:
            campaign = await db.get(PromotionCampaign, campaign_id)
            redemptions = list(await db.scalars(select(PromotionRedemption)))
            invoice = await db.scalar(select(BillingInvoice))
            return campaign.reserved_count, len(redemptions), invoice.plan_snapshot
    reserved, count, snapshot = client.portal.call(counters)
    assert reserved == count == 1
    assert snapshot["campaign_version"] == "synthetic-v2" and snapshot["discount_percent"] == 10


def test_legacy_personal_catalog_remains_payable_with_new_consent_form(checkout):
    client, headers, calls, _, _, _ = checkout
    async def seed_legacy():
        async with client.app_state["sessionmaker"]() as db:
            plan = BillingPlan(id=uuid4(), code="personal", display_name="Личный")
            db.add(plan)
            await db.flush()
            for number, cycle, amount in ((1, "month", 79000), (2, "year", 790000)):
                db.add(BillingPlanVersion(
                    id=uuid4(), plan_id=plan.id, plan_code="personal", version=number, status="legacy",
                    cycle=cycle, amount_minor=amount, currency="RUB", storage_bytes=2000000000,
                    processing_mode="unlimited", enabled_for_checkout=True,
                    policy_snapshot={"offer_version": "synthetic-legacy-v1"},
                ))
            await db.commit()
    client.portal.call(seed_legacy)
    page = client.get("/billing/checkout")
    assert page.status_code == 200 and "790 ₽" in page.text
    form = {name: html.unescape(value) for name, value in re.findall(
        r'<input type="hidden" name="([^"]+)" value="([^"]*)"', page.text,
    )} | {"offer_consent": "true", "recurring_consent": "true"}
    response = client.post("/billing/checkout/start", data=form, headers=headers, follow_redirects=False)
    assert response.headers["location"] == "https://yookassa.ru/checkout/synthetic-managed"
    assert len(calls) == 1 and calls[0]["amount_minor"] == 79000
    assert calls[0]["description"] == "GRAF Личный, month"
    _, invoices = client.portal.call(lambda: _state(client))
    assert invoices[0].plan_snapshot["plan_code"] == "personal"
    assert "plan_version_id" not in invoices[0].plan_snapshot["catalog_snapshot"]


def test_anonymous_public_offer_cannot_revive_legacy_prices_after_managed_close(checkout):
    from twobrain_rec_server.public.offers import PUBLIC_APPROVED_OFFER_VERSION

    client, _, _, _, _, _ = checkout
    plan_id, version_id = uuid4(), uuid4()
    async def seed():
        async with client.app_state["sessionmaker"]() as db:
            plan = BillingPlan(id=plan_id, code="personal", display_name="Личный")
            db.add(plan)
            await db.flush()
            for number, cycle, amount in ((1, "month", 100000), (2, "year", 1000000)):
                db.add(BillingPlanVersion(
                    id=uuid4(), plan_id=plan.id, plan_code="personal", version=number, status="legacy",
                    cycle=cycle, amount_minor=amount, currency="RUB", storage_bytes=2000000000,
                    processing_mode="unlimited", enabled_for_checkout=True,
                    policy_snapshot={"offer_version": PUBLIC_APPROVED_OFFER_VERSION},
                ))
            version = BillingPlanVersion(
                id=version_id, plan_id=plan.id, plan_code="personal", version=3, status="draft",
                capability_schema_version=1, capabilities={**_capabilities(), "storage_bytes": 2000000000},
                display_terms={"name": "Личный", "description": "", "audience": "public", "trial_days": 0},
                cycle="none", currency="RUB", storage_bytes=2000000000, processing_mode="unlimited",
                policy_snapshot={"offer_version": PUBLIC_APPROVED_OFFER_VERSION},
            )
            db.add(version)
            await db.flush()
            db.add_all([BillingPlanPrice(
                id=uuid4(), version_id=version.id, cycle=cycle, amount_minor=amount, currency="RUB",
            ) for cycle, amount in (("month", 100000), ("year", 1000000))])
            await db.flush()
            version.status = "published"
            version.enabled_for_checkout = True
            await db.flush()
            plan.current_version_id = version.id
            plan.sales_state = "open"
            await db.commit()
    client.portal.call(seed)
    client.cookies.clear()
    available = client.get("/")
    assert available.status_code == 200 and 'id="price"' in available.text
    assert "10\u00a0000 ₽" in available.text
    async def close():
        async with client.app_state["sessionmaker"]() as db:
            plan = await db.get(BillingPlan, plan_id)
            plan.sales_state = "closed"
            await db.commit()
    client.portal.call(close)
    unavailable = client.get("/")
    assert unavailable.status_code == 200 and 'id="price"' not in unavailable.text
    offer = client.get("/offer")
    assert offer.status_code == 200
    assert "Условия публичного предложения сейчас недоступны" in offer.text
    assert 'href="/billing/plans"' in offer.text
    assert "ГРАФ не принимает" not in offer.text
