"""Discount presentation through real HTTP/PostgreSQL, without payment dispatch."""

import asyncio
import re
from datetime import UTC, datetime, timedelta
from html import unescape
from uuid import uuid4

import pytest
from sqlalchemy import select

from tests.unit.test_billing_money_path_e2e import (
    ORG_ID,
    _approved_month_catalog,
    _configure_billing,
    _prepare_owner_session,
)
from twobrain_rec_server.billing.promotions import promo_code_hash
from twobrain_rec_server.cabinet.web_routes import billing as routes
from twobrain_rec_server.db.models import (
    BillingInvoice,
    BillingOperation,
    PromotionCampaign,
    PromotionRedemption,
    Workspace,
)


@pytest.fixture
def owner(client, tmp_path, monkeypatch):
    _configure_billing(client, tmp_path)
    _approved_month_catalog(client)
    workspace, headers = _prepare_owner_session(client)

    def no_provider(*_args, **_kwargs):
        pytest.fail("Discount presentation must not dispatch a payment")

    monkeypatch.setattr(routes, "YooKassaClient", no_provider)
    return workspace, headers


def seed_campaign(client, **overrides):
    async def run():
        async with client.app_state["sessionmaker"]() as db:
            values = {
                "code_hash": promo_code_hash("SYNTH-PRESENTATION"),
                "campaign_version": "synthetic-v1",
                "plan_code": "personal",
                "cycle": None,
                "discount_percent": 10,
                "max_redemptions": 10,
                "enabled": True,
                "policy_snapshot": {"purposes": ["initial_checkout"]},
            }
            values.update(overrides)
            campaign = PromotionCampaign(**values)
            db.add(campaign)
            await db.commit()
            return campaign.id

    return asyncio.run(run())


def seed_history(client, workspace, campaign_id, snapshot, *, foreign_invoice=False):
    async def run():
        async with client.app_state["sessionmaker"]() as db:
            invoice_workspace = workspace
            if foreign_invoice:
                other = Workspace(
                    organization_id=ORG_ID, slug="synthetic-other", name="Synthetic other"
                )
                db.add(other)
                await db.flush()
                invoice_workspace = other.id
            operation = BillingOperation(
                workspace_id=invoice_workspace,
                kind="initial_checkout",
                state="succeeded",
                idempotency_key="synthetic-history",
                provider_key_expires_at=datetime.now(UTC) + timedelta(hours=1),
                request_snapshot={},
            )
            db.add(operation)
            await db.flush()
            invoice = BillingInvoice(
                workspace_id=invoice_workspace,
                operation_id=operation.id,
                safe_number=f"INV-SYNTH-{uuid4().hex}",
                amount_minor=900000,
                status="succeeded",
                plan_snapshot=snapshot,
            )
            db.add(invoice)
            await db.flush()
            db.add(PromotionRedemption(
                workspace_id=workspace,
                campaign_id=campaign_id,
                invoice_id=invoice.id,
                reservation_key="synthetic-history",
                code_hash=promo_code_hash("SYNTH-PRESENTATION"),
                list_amount_minor=1000000,
                payable_amount_minor=900000,
                discount_percent=10,
                state="redeemed",
            ))
            await db.commit()

    asyncio.run(run())


def history_text(client):
    response = client.get("/billing/discounts")
    assert response.status_code == 200
    match = re.search(r'<ul[^>]*aria-label="История скидок"[^>]*>(.*?)</ul>',
                      response.text, re.S)
    assert match, "Expected the persisted redemption in the discount history"
    return unescape(re.sub(r"<[^>]+>", " ", match.group(1)))


@pytest.mark.parametrize("cycle,label", [("year", "Год"), ("month", "Месяц")])
def test_universal_campaign_history_uses_purchased_invoice_period(client, owner, cycle, label):
    workspace, _ = owner
    campaign = seed_campaign(client)
    seed_history(client, workspace, campaign, {"cycle": cycle})
    text = history_text(client)
    assert label in text
    assert ("Месяц" if cycle == "year" else "Год") not in text


def test_changing_campaign_does_not_rewrite_purchased_period(client, owner):
    workspace, _ = owner
    campaign_id = seed_campaign(client, cycle="year")
    seed_history(client, workspace, campaign_id, {"cycle": "year"})
    before = history_text(client)
    assert "Год" in before

    async def mutate():
        async with client.app_state["sessionmaker"]() as db:
            campaign = await db.get(PromotionCampaign, campaign_id)
            campaign.cycle = "month"
            campaign.discount_percent = 25
            await db.commit()

    asyncio.run(mutate())
    assert history_text(client) == before


@pytest.mark.parametrize("snapshot", [{}, {"cycle": None}, {"cycle": "unknown"}, None, [], {"cycle": []}, {"cycle": {}}])
def test_unknown_invoice_period_does_not_claim_a_month(client, owner, snapshot):
    workspace, _ = owner
    campaign = seed_campaign(client)
    seed_history(client, workspace, campaign, snapshot)
    text = history_text(client)
    assert "Скидка 10%" in text
    assert "Год" not in text and "Месяц" not in text


def test_discount_history_does_not_read_another_workspace_invoice(client, owner):
    workspace, _ = owner
    campaign = seed_campaign(client, cycle="year")
    seed_history(client, workspace, campaign, {"cycle": "year"}, foreign_invoice=True)
    text = history_text(client)
    assert "Год" not in text and "Месяц" not in text


@pytest.mark.parametrize("ineligible", ["workspace", "exhausted"])
def test_global_ineligible_campaigns_are_not_advertised(client, owner, ineligible):
    values = {"discount_percent": 13}
    if ineligible == "workspace":
        values["policy_snapshot"] = {"workspace_id": str(uuid4())}
    else:
        values.update(max_redemptions=1, redeemed_count=1)
    seed_campaign(client, **values)
    response = client.get("/billing/discounts")
    assert response.status_code == 200
    assert "Действующие предложения" not in response.text
    assert "Скидка 13%" not in response.text
    assert 'action="/billing/discounts/apply"' in response.text
    assert "Примененных промокодов пока нет" in response.text


def assert_checkout(response, *, today, renewal, cycle, promo):
    assert response.status_code == 200
    summary = re.search(r'<dl class="billing-order-summary">(.*?)</dl>', response.text, re.S)
    assert summary
    text = unescape(re.sub(r"<[^>]+>", " ", summary.group(1)))
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"(?<=\d)\s+(?=\d)", "", text)
    assert f"К оплате сегодня {today} ₽" in text
    assert f"При автопродлении {renewal} ₽ за {cycle}" in text
    assert ("Разовая скидка" in text) is bool(promo)
    markup = re.sub(r"(?<=\d)\s+(?=\d)", "", unescape(response.text))
    assert f"Оплатить {today} ₽ в ЮKassa" in markup
    for name in ("offer_consent", "recurring_consent"):
        checkbox = re.search(rf'<input[^>]*name="{name}"[^>]*>', response.text)
        assert checkbox
        assert ("checked" in checkbox.group(0)) is (name == "recurring_consent")
        assert ("required" in checkbox.group(0)) is (name == "offer_consent")
    code = re.search(r'<input[^>]*id="billing-promo"[^>]*>', response.text)
    assert code and f'value="{promo}"' in code.group(0)


def test_apply_switch_month_year_and_clear_show_current_and_renewal_prices(client, owner):
    workspace, headers = owner
    seed_campaign(client, policy_snapshot={
        "workspace_id": str(workspace), "purposes": ["initial_checkout"],
    })
    applied = client.post("/billing/discounts/apply", headers=headers,
                          data={"promo_code": "SYNTH-PRESENTATION"}, follow_redirects=False)
    assert applied.status_code == 303
    assert_checkout(client.get(applied.headers["location"]), today="900", renewal="1000",
                    cycle="месяц", promo="SYNTH-PRESENTATION")
    for cycle, today, renewal, label in [
        ("month", "900", "1000", "месяц"), ("year", "9000", "10000", "год"),
    ]:
        preview = client.post("/billing/checkout/preview", headers=headers,
                              data={"cycle": cycle, "promo_code": "SYNTH-PRESENTATION"})
        assert_checkout(preview, today=today, renewal=renewal,
                        cycle=label, promo="SYNTH-PRESENTATION")
    cleared = client.post("/billing/checkout/preview", headers=headers,
                          data={"cycle": "year", "promo_code": ""})
    assert_checkout(cleared, today="10000", renewal="10000", cycle="год", promo="")

    async def no_dispatch():
        async with client.app_state["sessionmaker"]() as db:
            assert await db.scalar(select(BillingOperation.id)) is None
            assert await db.scalar(select(BillingInvoice.id)) is None
            assert await db.scalar(select(PromotionRedemption.id)) is None

    asyncio.run(no_dispatch())
