import asyncio
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError

from tests.fakes.auth_contexts import USER_ID, WORKSPACE_ID
from twobrain_rec_server.billing.purchases import (
    PurchaseError,
    create_purchase_quote,
    validate_purchase_quote,
)
from twobrain_rec_server.db.models import WorkspaceSubscription


def test_quote_binds_money_owner_state_and_expiry(client):
    async def scenario():
        async with client.app_state["sessionmaker"]() as db:
            now = datetime.now(UTC)
            sub = WorkspaceSubscription(
                workspace_id=WORKSPACE_ID,
                application_version=7,
                next_capacity_version=2,
                plan_code="personal",
                cycle="month",
                paid_through=now + timedelta(days=10),
                capacity_bytes=2_000_000_000,
                recurring_allowed=False,
                recurring_authority_version=1,
            )
            snapshot = {
                "cycle": "month",
                "list_amount_minor": 100000,
                "payable_amount_minor": 1000,
                "catalog_version": 1,
                "promo_code_hash": "synthetic-hash",
            }
            quote = await create_purchase_quote(
                db,
                workspace_id=WORKSPACE_ID,
                owner_user_id=USER_ID,
                purpose="initial_checkout",
                subscription=sub,
                snapshot=snapshot,
                now=now,
            )
            common = dict(
                quote_id=quote.id,
                workspace_id=WORKSPACE_ID,
                owner_user_id=USER_ID,
                purpose="initial_checkout",
                subscription=sub,
                now=now,
                expected_snapshot=snapshot,
            )
            assert await validate_purchase_quote(db, **common) is quote
            for assignment in [
                "snapshot = '{}'::json",
                "expires_at = expires_at + interval '1 hour'",
            ]:
                with pytest.raises(IntegrityError):
                    async with db.begin_nested():
                        await db.execute(
                            text(f"UPDATE billing_purchase_quotes SET {assignment} WHERE id = :id"),
                            {"id": quote.id},
                        )
            for change in [
                {"owner_user_id": uuid4()},
                {"workspace_id": uuid4()},
                {"now": now + timedelta(minutes=10)},
                {"purpose": "early_renewal"},
                {"expected_snapshot": {**snapshot, "payable_amount_minor": 2000}},
            ]:
                with pytest.raises(PurchaseError):
                    await validate_purchase_quote(db, **{**common, **change})
            sub.application_version += 1
            with pytest.raises(PurchaseError):
                await validate_purchase_quote(db, **common)
            await db.rollback()

    asyncio.run(scenario())


def test_last_promo_use_is_reserved_once_by_concurrent_transactions(client):

    from twobrain_rec_server.cabinet.web_routes.billing import _reserve_purchase_promo
    from twobrain_rec_server.db.models import (
        BillingInvoice,
        BillingOperation,
        PromotionCampaign,
        PromotionRedemption,
    )

    async def scenario():
        factory = client.app_state["sessionmaker"]
        now, campaign_id = datetime.now(UTC), uuid4()
        pairs = [(uuid4(), uuid4()), (uuid4(), uuid4())]
        async with factory() as db:
            db.add(
                PromotionCampaign(
                    id=campaign_id,
                    code_hash="synthetic-hash",
                    campaign_version="v1",
                    plan_code="personal",
                    cycle="month",
                    discount_percent=99,
                    max_redemptions=1,
                    enabled=True,
                    policy_snapshot={"purposes": ["storage_upgrade"]},
                )
            )
            for op_id, invoice_id in pairs:
                db.add(
                    BillingOperation(
                        id=op_id,
                        workspace_id=WORKSPACE_ID,
                        kind="storage_upgrade",
                        idempotency_key=str(op_id),
                        state="processing",
                        request_snapshot={},
                    )
                )
                await db.flush()
                db.add(
                    BillingInvoice(
                        id=invoice_id,
                        workspace_id=WORKSPACE_ID,
                        operation_id=op_id,
                        safe_number=f"INV-{invoice_id}",
                        amount_minor=290,
                        currency="RUB",
                        status="pending",
                    )
                )
            await db.commit()

        async def reserve(pair):
            async with factory() as db:
                operation = await db.get(BillingOperation, pair[0])
                invoice = await db.get(BillingInvoice, pair[1])
                try:
                    await _reserve_purchase_promo(
                        db,
                        workspace_id=WORKSPACE_ID,
                        invoice=invoice,
                        operation=operation,
                        now=now,
                        quote_snapshot={
                            "campaign_id": str(campaign_id),
                            "promo_code_hash": "synthetic-hash",
                            "campaign_version": "v1",
                            "discount_percent": 99,
                            "cycle": "month",
                            "list_amount_minor": 29000,
                        },
                    )
                    await db.commit()
                    return True
                except PurchaseError:
                    await db.rollback()
                    return False

        assert sorted(await asyncio.gather(*(reserve(pair) for pair in pairs))) == [False, True]
        async with factory() as db:
            campaign = await db.get(PromotionCampaign, campaign_id)
            assert (campaign.reserved_count, campaign.redeemed_count) == (1, 0)
            reservations = list(
                await db.scalars(
                    select(PromotionRedemption).where(
                        PromotionRedemption.campaign_id == campaign_id
                    )
                )
            )
            assert len(reservations) == 1 and reservations[0].state == "reserved"

    asyncio.run(scenario())


def test_quote_cleanup_is_bounded_and_preserves_consumed_financial_evidence(client):
    from sqlalchemy import func

    from twobrain_rec_server.db.models import BillingOperation, BillingPurchaseQuote

    async def run():
        async with client.app_state["sessionmaker"]() as db:
            now = datetime.now(UTC)
            op = BillingOperation(
                workspace_id=WORKSPACE_ID,
                kind="initial_checkout",
                state="succeeded",
                idempotency_key=str(uuid4()),
                request_snapshot={},
            )
            db.add(op)
            await db.flush()
            consumed_id = uuid4()
            for index in range(102):
                db.add(
                    BillingPurchaseQuote(
                        id=consumed_id if index == 0 else uuid4(),
                        workspace_id=WORKSPACE_ID,
                        owner_user_id=USER_ID,
                        purpose="initial_checkout",
                        subscription_version=0,
                        selection_version=0,
                        snapshot={"synthetic": index},
                        created_at=now - timedelta(days=2),
                        expires_at=now - timedelta(days=1),
                        consumed_operation_id=op.id if index == 0 else None,
                    )
                )
            await db.flush()
            await create_purchase_quote(
                db,
                workspace_id=WORKSPACE_ID,
                owner_user_id=USER_ID,
                purpose="initial_checkout",
                subscription=None,
                snapshot={"synthetic": "new"},
                now=now,
            )
            assert await db.get(BillingPurchaseQuote, consumed_id) is not None
            assert await db.scalar(select(func.count()).select_from(BillingPurchaseQuote)) == 3
            await db.commit()

    asyncio.run(run())
