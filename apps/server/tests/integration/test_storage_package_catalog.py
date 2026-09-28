import asyncio
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import select

from tests.fakes.auth_contexts import WORKSPACE_ID
from tests.unit.test_billing_money_path_e2e import _approved_month_catalog, _prepare_owner_session
from twobrain_rec_server.billing.purchases import effective_paid_storage, storage_catalog
from twobrain_rec_server.db.models import BillingStoragePriceVersion, WorkspaceSubscription


@pytest.mark.parametrize("legacy_gb,legacy_price", [(100, 199000), (5, 29000)])
def test_new_catalog_preserves_legacy_price_and_blocks_unaccepted_renewal(
    client, tmp_path, legacy_gb, legacy_price
):
    from tests.fakes.auth_contexts import USER_ID
    from tests.integration.test_billing_purchase_journey import quote_id
    from tests.unit.test_billing_money_path_e2e import _configure_billing
    from twobrain_rec_server.billing.renewal_charge import plan_due_renewals

    workspace, headers = _prepare_owner_session(client)
    _configure_billing(client, tmp_path)
    legacy_id = uuid4()
    now = datetime.now(UTC)

    async def seed_legacy():
        async with client.app_state["sessionmaker"]() as db:
            db.add(
                BillingStoragePriceVersion(
                    id=legacy_id,
                    version=1,
                    capacity_bytes=legacy_gb * 1_000_000_000,
                    cycle="month",
                    amount_minor=legacy_price,
                    currency="RUB",
                    enabled_for_checkout=True,
                    effective_from=now - timedelta(days=60),
                    policy_snapshot={"legacy": True},
                )
            )
            sub = await db.scalar(
                select(WorkspaceSubscription).where(WorkspaceSubscription.workspace_id == workspace)
            )
            if sub is None:
                sub = WorkspaceSubscription(workspace_id=workspace)
                db.add(sub)
            sub.plan_code = sub.state = "personal"
            sub.billing_owner_id = USER_ID
            sub.cycle = "month"
            sub.paid_through = now + timedelta(days=2)
            sub.capacity_bytes = legacy_gb * 1_000_000_000
            sub.recurring_allowed = True
            await db.commit()

    asyncio.run(seed_legacy())
    _approved_month_catalog(client)

    async def verify():
        async with client.app_state["sessionmaker"]() as db:
            legacy = await db.get(BillingStoragePriceVersion, legacy_id)
            assert legacy.amount_minor == legacy_price and legacy.policy_snapshot == {
                "legacy": True
            }
            assert legacy.enabled_for_checkout is False
            assert await plan_due_renewals(db, now=now) == ()
            sub = await db.scalar(
                select(WorkspaceSubscription).where(WorkspaceSubscription.workspace_id == workspace)
            )
            assert sub.renewal_resolution == "price_changed"
            assert sub.capacity_bytes == legacy_gb * 1_000_000_000 and sub.recurring_allowed is True
            await db.commit()

    asyncio.run(verify())
    preview = client.post(
        "/billing/storage/preview", headers=headers, data={"package_count": str(legacy_gb // 5 - 1)}
    )
    assert preview.status_code == 200
    confirmed = client.post(
        "/billing/purchases/confirm",
        headers=headers,
        follow_redirects=False,
        data={"quote_id": quote_id(preview), "purchase_consent": "true"},
    )
    assert confirmed.status_code == 303

    async def verify_accepted():
        async with client.app_state["sessionmaker"]() as db:
            assert await plan_due_renewals(db, now=now) == ()
            sub = await db.scalar(
                select(WorkspaceSubscription).where(WorkspaceSubscription.workspace_id == workspace)
            )
            # Price is now accepted durably. The next independent safeguard
            # rejects this synthetic account without a verified payment method.
            assert sub.renewal_resolution == "method_required"

    asyncio.run(verify_accepted())


def test_migrated_package_catalog_covers_every_quantity_and_cycle(client):
    base = _approved_month_catalog(client)
    assert base.storage_bytes == 5_000_000_000 and base.amount_minor == 100000

    async def check():
        async with client.app_state["sessionmaker"]() as db:
            prices = await storage_catalog(db, now=datetime.now(UTC))
            assert len(prices) == 198
            for count in range(1, 100):
                for cycle, unit_price in [("month", 25000), ("year", 250000)]:
                    price = prices[((count + 1) * 5_000_000_000, cycle)]
                    assert price.amount_minor == count * unit_price
                    assert price.policy_snapshot["package_count"] == count
                    assert price.policy_snapshot["package_amount_minor"] == unit_price
            rows = list(await db.scalars(select(BillingStoragePriceVersion)))
            assert all(row.capacity_bytes % 5_000_000_000 == 0 for row in rows)

    asyncio.run(check())


def test_legacy_paid_base_gets_five_gb_without_rewriting_cache(client):
    async def check():
        now = datetime.now(UTC)
        async with client.app_state["sessionmaker"]() as db:
            subscription = WorkspaceSubscription(
                workspace_id=WORKSPACE_ID,
                plan_code="personal",
                state="personal",
                capacity_bytes=2_000_000_000,
                paid_through=now + timedelta(days=10),
            )
            assert (
                await effective_paid_storage(db, subscription=subscription, now=now)
                == 5_000_000_000
            )
            assert subscription.capacity_bytes == 2_000_000_000
            assert (
                await effective_paid_storage(
                    db, subscription=subscription, now=now + timedelta(days=10)
                )
                == 250_000_000
            )

    asyncio.run(check())


@pytest.mark.parametrize("quantity", ["-1", "100", "1.5", "invalid"])
def test_http_rejects_invalid_package_counts_before_creating_purchase(client, quantity):
    _workspace, headers = _prepare_owner_session(client)
    response = client.post(
        "/billing/storage/preview", headers=headers, data={"package_count": quantity}
    )
    assert response.status_code == 422


@pytest.mark.parametrize("cycle,days,base_price,unit_price", [("month", 30, 100000, 25000), ("year", 366, 1000000, 250000)])
@pytest.mark.parametrize("quantity", [1, 2, 99])
def test_http_package_quote_prorates_remaining_period_and_shows_full_renewal(
    client, tmp_path, monkeypatch, cycle, days, base_price, unit_price, quantity
):
    from uuid import UUID

    from tests.fakes.auth_contexts import USER_ID
    from tests.integration.test_billing_purchase_journey import quote_id
    from tests.unit.test_billing_money_path_e2e import _configure_billing
    from twobrain_rec_server.cabinet.web_routes import billing as routes
    from twobrain_rec_server.db.models import (
        BillingEntitlementGrant,
        BillingInvoice,
        BillingOperation,
        BillingPurchaseQuote,
    )

    workspace, headers = _prepare_owner_session(client)
    _configure_billing(client, tmp_path)
    _approved_month_catalog(client)
    now = datetime.now(UTC)

    class FixedDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            return now if tz else now.replace(tzinfo=None)

    monkeypatch.setattr(routes, "datetime", FixedDateTime)

    async def seed():
        async with client.app_state["sessionmaker"]() as db:
            operation_id, invoice_id = uuid4(), uuid4()
            db.add(BillingOperation(
                id=operation_id, workspace_id=workspace, kind="initial_checkout",
                idempotency_key=str(operation_id), state="succeeded", request_snapshot={},
            ))
            await db.flush()
            db.add(BillingInvoice(
                id=invoice_id, workspace_id=workspace, operation_id=operation_id,
                safe_number=str(invoice_id), amount_minor=base_price, currency="RUB",
                status="paid", plan_snapshot={"purchase_schema": 2},
            ))
            await db.flush()
            db.add(BillingEntitlementGrant(
                workspace_id=workspace, invoice_id=invoice_id,
                provider_payment_id=str(uuid4()), plan_code="personal", cycle=cycle,
                starts_at=now - timedelta(days=days / 2),
                ends_at=now + timedelta(days=days / 2), amount_minor=base_price,
                currency="RUB",
            ))
            sub = await db.scalar(select(WorkspaceSubscription).where(
                WorkspaceSubscription.workspace_id == workspace
            ))
            if sub is None:
                sub = WorkspaceSubscription(workspace_id=workspace)
                db.add(sub)
            sub.plan_code = sub.state = "personal"
            sub.billing_owner_id = USER_ID
            sub.cycle = cycle
            sub.capacity_bytes = 5_000_000_000
            sub.paid_through = now + timedelta(days=days / 2)
            sub.recurring_allowed = False
            await db.commit()

    asyncio.run(seed())
    response = client.post("/billing/storage/preview", headers=headers, data={"package_count": str(quantity)})
    bound_id = UUID(quote_id(response))

    async def check():
        async with client.app_state["sessionmaker"]() as db:
            quote = await db.get(BillingPurchaseQuote, bound_id)
            assert quote.purpose == "storage_upgrade"
            assert quote.snapshot["list_amount_minor"] == quantity * unit_price // 2
            assert quote.snapshot["payable_amount_minor"] == quantity * unit_price // 2
            assert quote.snapshot["next_amount_minor"] == base_price + quantity * unit_price
            assert quote.snapshot["target_capacity_bytes"] == (quantity + 1) * 5_000_000_000
            assert quote.snapshot["recurring_allowed"] is False

    asyncio.run(check())
