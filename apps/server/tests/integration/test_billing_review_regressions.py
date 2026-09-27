"""Payment review edge cases exercised against PostgreSQL and HTTP."""

import asyncio
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import select

from tests.integration.test_billing_purchase_journey import seed_catalog_and_budget
from tests.unit.test_billing_money_path_e2e import (
    USER_ID,
    _approved_month_catalog,
    _configure_billing,
    _prepare_owner_session,
)
from twobrain_rec_server.billing.purchases import calculate_storage_purchase
from twobrain_rec_server.db.models import (
    BillingEntitlementGrant,
    BillingInvoice,
    BillingOperation,
    PromotionCampaign,
    TimeCreditLedgerEntry,
    WorkspaceSubscription,
)


def seed_periods(client, workspace, *, bonus=False, mixed=False):
    now = datetime.now(UTC)

    async def run():
        async with client.app_state["sessionmaker"]() as db:
            subscription = await db.scalar(
                select(WorkspaceSubscription).where(WorkspaceSubscription.workspace_id == workspace)
            )
            if subscription is None:
                subscription = WorkspaceSubscription(workspace_id=workspace)
                db.add(subscription)
            subscription.plan_code = subscription.state = "personal"
            subscription.billing_owner_id = USER_ID
            subscription.cycle = "year" if mixed else "month"
            subscription.capacity_bytes = 5_000_000_000
            subscription.next_capacity_version = 0
            boundary = now + timedelta(days=15)
            next_start = boundary + timedelta(days=7 if bonus else 0)
            subscription.paid_through = next_start + timedelta(days=365 if mixed else 30)
            for cycle, start, end in [
                ("month", now - timedelta(days=15), boundary),
                (subscription.cycle, next_start, subscription.paid_through),
            ]:
                operation = BillingOperation(
                    workspace_id=workspace,
                    kind="renewal",
                    state="succeeded",
                    idempotency_key=str(uuid4()),
                    request_snapshot={},
                )
                db.add(operation)
                await db.flush()
                invoice = BillingInvoice(
                    workspace_id=workspace,
                    operation_id=operation.id,
                    safe_number=f"INV-{uuid4().hex}",
                    amount_minor=100000,
                    currency="RUB",
                    status="succeeded",
                    plan_snapshot={"purchase_schema": 2, "cycle": cycle},
                )
                db.add(invoice)
                await db.flush()
                db.add(
                    BillingEntitlementGrant(
                        workspace_id=workspace,
                        invoice_id=invoice.id,
                        provider_payment_id=str(uuid4()),
                        plan_code="personal",
                        cycle=cycle,
                        starts_at=start,
                        ends_at=end,
                        amount_minor=100000,
                        currency="RUB",
                    )
                )
            if bonus:
                db.add(
                    TimeCreditLedgerEntry(
                        workspace_id=workspace,
                        source_ref=str(uuid4()),
                        days=7,
                        state="applied",
                        maturity_at=now,
                        expires_at=now + timedelta(days=90),
                        applied_start=boundary,
                        applied_end=next_start,
                        capacity_snapshot_bytes=5_000_000_000,
                    )
                )
            await db.commit()

    asyncio.run(run())
    return now


def test_future_bonus_defers_whole_upgrade_without_charging_paid_segments(client, tmp_path):
    _configure_billing(client, tmp_path)
    _approved_month_catalog(client)
    workspace, _ = _prepare_owner_session(client)
    seed_catalog_and_budget(client, workspace)
    now = seed_periods(client, workspace, bonus=True)

    async def run():
        async with client.app_state["sessionmaker"]() as db:
            subscription = await db.scalar(
                select(WorkspaceSubscription).where(WorkspaceSubscription.workspace_id == workspace)
            )
            quote = await calculate_storage_purchase(
                db, subscription=subscription, target_capacity_bytes=10_000_000_000, now=now
            )
            assert quote.deferred_to_renewal
            assert quote.payable_amount_minor == 0
            assert quote.segments == ()

    asyncio.run(run())


@pytest.mark.parametrize("campaign_cycle", ["year", None])
def test_storage_promo_applies_only_when_all_charged_periods_are_eligible(
    client, tmp_path, campaign_cycle
):
    _configure_billing(client, tmp_path)
    _approved_month_catalog(client)
    workspace, headers = _prepare_owner_session(client)
    seed_catalog_and_budget(client, workspace)
    seed_periods(client, workspace, mixed=True)

    async def campaign():
        async with client.app_state["sessionmaker"]() as db:
            rows = list(await db.scalars(select(PromotionCampaign)))
            row = next(r for r in rows if r.policy_snapshot["purposes"] == ["storage_upgrade"])
            row.cycle = campaign_cycle
            await db.commit()

    asyncio.run(campaign())
    response = client.post(
        "/billing/storage/preview",
        headers=headers,
        data={"package_count": "1", "promo_code": "SYNTHSTORE"},
    )
    assert response.status_code == (409 if campaign_cycle else 200)
    if campaign_cycle:
        assert "Промокод не подходит ко всем оплачиваемым периодам" in response.text, response.text[-4000:]


def test_storage_invoice_explains_capacity_and_each_prorated_period(client, tmp_path):
    _configure_billing(client, tmp_path)
    workspace, headers = _prepare_owner_session(client)

    async def seed():
        async with client.app_state["sessionmaker"]() as db:
            operation = BillingOperation(
                workspace_id=workspace,
                kind="storage_upgrade",
                state="succeeded",
                idempotency_key=str(uuid4()),
                request_snapshot={},
            )
            db.add(operation)
            await db.flush()
            db.add(
                BillingInvoice(
                    workspace_id=workspace,
                    operation_id=operation.id,
                    safe_number="INV-STORAGE-DETAIL",
                    amount_minor=40000,
                    currency="RUB",
                    status="succeeded",
                    plan_snapshot={
                        "purpose": "storage_upgrade",
                        "cycle": "month",
                        "target_capacity_bytes": 10_000_000_000,
                        "storage_segments": [
                            {
                                "starts_at": "2026-09-27T00:00:00+00:00",
                                "ends_at": "2026-10-12T00:00:00+00:00",
                                "capacity_bytes": 10_000_000_000,
                            },
                            {
                                "starts_at": "2026-10-12T00:00:00+00:00",
                                "ends_at": "2026-11-12T00:00:00+00:00",
                                "capacity_bytes": 10_000_000_000,
                            },
                        ],
                    },
                )
            )
            await db.commit()

    asyncio.run(seed())
    response = client.get("/billing/invoices/INV-STORAGE-DETAIL", headers=headers)
    assert response.status_code == 200
    assert "10 GB" in response.text
    assert "Оплаченные интервалы хранения" in response.text
    assert "27.09.2026" in response.text and "12.11.2026" in response.text


def test_campaign_cycle_change_after_preview_cannot_discount_ineligible_segments(client, tmp_path):
    from tests.integration.test_billing_purchase_journey import quote_id

    _configure_billing(client, tmp_path)
    _approved_month_catalog(client)
    workspace, headers = _prepare_owner_session(client)
    seed_catalog_and_budget(client, workspace)
    seed_periods(client, workspace, mixed=True)

    async def set_cycle(value):
        async with client.app_state["sessionmaker"]() as db:
            rows = list(await db.scalars(select(PromotionCampaign)))
            row = next(r for r in rows if r.policy_snapshot["purposes"] == ["storage_upgrade"])
            row.cycle = value
            await db.commit()

    asyncio.run(set_cycle(None))
    preview = client.post(
        "/billing/storage/preview",
        headers=headers,
        data={"package_count": "1", "promo_code": "SYNTHSTORE"},
    )
    bound = quote_id(preview)
    asyncio.run(set_cycle("year"))
    response = client.post(
        "/billing/purchases/confirm",
        headers=headers,
        data={"quote_id": bound, "purchase_consent": "true"},
    )
    assert response.status_code == 409
    assert "Промокод не подходит ко всем оплачиваемым периодам" in response.text, response.text[-4000:]

    async def verify():
        async with client.app_state["sessionmaker"]() as db:
            invoices = list(
                await db.scalars(
                    select(BillingInvoice).where(BillingInvoice.workspace_id == workspace)
                )
            )
            assert len(invoices) == 2  # Only the previously paid periods, no attempted charge.

    asyncio.run(verify())


def test_explicit_base_only_renewal_projects_five_gb_despite_old_capacity_cache(client, tmp_path):
    from twobrain_rec_server.billing.purchases import effective_paid_storage

    _configure_billing(client, tmp_path)
    workspace, _ = _prepare_owner_session(client)
    now = seed_periods(client, workspace)

    async def verify():
        async with client.app_state["sessionmaker"]() as db:
            subscription = await db.scalar(
                select(WorkspaceSubscription).where(WorkspaceSubscription.workspace_id == workspace)
            )
            subscription.capacity_bytes = 20_000_000_000
            assert (
                await effective_paid_storage(
                    db, subscription=subscription, now=now + timedelta(days=16)
                )
                == 5_000_000_000
            )

    asyncio.run(verify())
