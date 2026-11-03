import asyncio
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import async_sessionmaker

from tests.fakes.auth_contexts import WORKSPACE_ID
from tests.integration.test_rls_postgres_policies import (
    _exact_app_role_engine,
    _request_context,
    _seed_probe_rows,
    apply_tenant_context_to_connection,
)
from twobrain_rec_server.billing.purchases import (
    PurchaseError,
    reserve_acceptance_budget,
    settle_acceptance_budget,
)
from twobrain_rec_server.db.models import BillingAcceptanceBudget, BillingOperation
from twobrain_rec_server.db.tenant_context import apply_tenant_context

pytest_plugins = ("tests.integration.test_rls_postgres_policies",)


def test_two_concurrent_operations_cannot_overdraw_budget_and_unknown_keeps_reserve(client):
    async def scenario():
        factory = client.app_state["sessionmaker"]
        budget_id = uuid4()
        operation_ids = [uuid4(), uuid4()]
        now = datetime.now(UTC)
        async with factory() as db:
            db.add(
                BillingAcceptanceBudget(
                    id=budget_id,
                    workspace_id=WORKSPACE_ID,
                    limit_minor=20_000,
                    reserved_minor=0,
                    spent_minor=0,
                    enabled=True,
                    expires_at=now + timedelta(hours=1),
                )
            )
            db.add_all(
                [
                    BillingOperation(
                        id=op,
                        workspace_id=WORKSPACE_ID,
                        kind="storage_upgrade",
                        idempotency_key=str(op),
                        state="unknown",
                        request_snapshot={},
                    )
                    for op in operation_ids
                ]
            )
            await db.commit()

        async def attempt(operation_id):
            async with factory() as db:
                try:
                    await reserve_acceptance_budget(
                        db,
                        workspace_id=WORKSPACE_ID,
                        operation_id=operation_id,
                        amount_minor=12_000,
                        now=now,
                    )
                    await db.commit()
                    return operation_id
                except PurchaseError:
                    await db.rollback()
                    return None

        outcomes = await asyncio.gather(*(attempt(op) for op in operation_ids))
        assert outcomes.count(None) == 1
        winner = next(op for op in outcomes if op)
        async with factory() as db:
            budget = await db.scalar(
                select(BillingAcceptanceBudget).where(BillingAcceptanceBudget.id == budget_id)
            )
            assert (budget.reserved_minor, budget.spent_minor) == (12_000, 0)
            await settle_acceptance_budget(
                db, workspace_id=WORKSPACE_ID, operation_id=winner, succeeded=True
            )
            await settle_acceptance_budget(
                db, workspace_id=WORKSPACE_ID, operation_id=winner, succeeded=True
            )
            await db.commit()
            await db.refresh(budget)
            assert (budget.reserved_minor, budget.spent_minor) == (0, 12_000)
            # A repeated cancel/refund observation cannot erase spent money.
            await settle_acceptance_budget(
                db, workspace_id=WORKSPACE_ID, operation_id=winner, succeeded=False
            )
            await db.commit()
            await db.refresh(budget)
            assert budget.spent_minor == 12_000

    asyncio.run(scenario())


@pytest.mark.strict_rls
@pytest.mark.asyncio
async def test_new_financial_tables_are_tenant_isolated_and_catalog_is_read_only(
    rls_engine, migrated_postgres_urls
):
    from twobrain_rec_server.db.models import BillingPurchaseQuote

    ids = await _seed_probe_rows(rls_engine)
    now = datetime.now(UTC)
    quote_id = uuid4()
    async with async_sessionmaker(rls_engine, expire_on_commit=False)() as db:
        await apply_tenant_context(db, _request_context(ids, "a"))
        db.add(
            BillingPurchaseQuote(
                id=quote_id,
                workspace_id=ids["workspace_a"],
                owner_user_id=ids["user_a"],
                purpose="storage_upgrade",
                subscription_version=0,
                selection_version=0,
                snapshot={},
                created_at=now,
                expires_at=now + timedelta(minutes=10),
            )
        )
        await db.commit()
    async with _exact_app_role_engine(migrated_postgres_urls.migration_url) as engine:
        for scope in (None, "b", "a"):
            async with engine.begin() as conn:
                if scope:
                    await apply_tenant_context_to_connection(conn, _request_context(ids, scope))
                assert await conn.scalar(
                    select(BillingPurchaseQuote.id).where(BillingPurchaseQuote.id == quote_id)
                ) == (quote_id if scope == "a" else None)
                for name in (
                    "billing_purchase_quotes",
                    "billing_acceptance_budgets",
                    "billing_acceptance_reservations",
                    "billing_storage_entitlement_grants",
                ):
                    assert await conn.scalar(
                        text(
                            "SELECT relrowsecurity AND relforcerowsecurity FROM pg_class WHERE relname=:name"
                        ),
                        {"name": name},
                    )
                if scope:
                    assert (
                        await conn.scalar(
                            text("SELECT count(*) FROM billing_storage_price_versions")
                        )
                        == 206
                    )
                    result = await conn.execute(text("DELETE FROM billing_storage_price_versions"))
                    assert result.rowcount == 0
                    result = await conn.execute(
                        text("UPDATE billing_storage_price_versions SET amount_minor=1")
                    )
                    assert result.rowcount == 0


def test_future_capacity_starts_at_boundary_and_expired_grant_never_downgrades_newer(client):
    from twobrain_rec_server.billing.purchases import (
        calculate_storage_purchase,
        compose_personal_catalog,
        effective_paid_storage,
        grant_confirmed_storage,
        storage_period_timeline,
    )
    from twobrain_rec_server.db.models import (
        BillingEntitlementGrant,
        BillingInvoice,
        BillingStorageEntitlementGrant,
        BillingStoragePriceVersion,
        WorkspaceSubscription,
    )

    async def scenario():
        factory = client.app_state["sessionmaker"]
        now = datetime(2026, 10, 1, tzinfo=UTC)
        async with factory() as db:
            subscription = await db.scalar(
                select(WorkspaceSubscription).where(
                    WorkspaceSubscription.workspace_id == WORKSPACE_ID
                )
            )
            if subscription is None:
                subscription = WorkspaceSubscription(workspace_id=WORKSPACE_ID)
                db.add(subscription)
            subscription.plan_code = subscription.state = "personal"
            subscription.capacity_bytes = 20_000_000_000
            subscription.paid_through = now + timedelta(days=60)
            for index, (gb, start, end) in enumerate(
                [
                    (20, now - timedelta(days=30), now),
                    (5, now, now + timedelta(days=30)),
                    (100, now + timedelta(days=30), now + timedelta(days=60)),
                ]
            ):
                price = await db.scalar(
                    select(BillingStoragePriceVersion).where(
                        BillingStoragePriceVersion.capacity_bytes == gb * 1_000_000_000,
                        BillingStoragePriceVersion.cycle == "month",
                    )
                )
                # The client fixture truncates every mapped table between cases.
                # Migration seeding itself is checked by the strict-RLS test above.
                if price is None:
                    price = BillingStoragePriceVersion(
                        version=1,
                        capacity_bytes=gb * 1_000_000_000,
                        cycle="month",
                        amount_minor={5: 29000, 20: 79000, 100: 199000}[gb],
                        currency="RUB",
                        enabled_for_checkout=True,
                        effective_from=now - timedelta(days=60),
                        policy_snapshot={},
                    )
                    db.add(price)
                    await db.flush()
                op_id, inv_id, grant_id = uuid4(), uuid4(), uuid4()
                db.add(
                    BillingOperation(
                        id=op_id,
                        workspace_id=WORKSPACE_ID,
                        kind="renewal",
                        idempotency_key=str(op_id),
                        request_snapshot={},
                    )
                )
                await db.flush()
                db.add(
                    BillingInvoice(
                        id=inv_id,
                        workspace_id=WORKSPACE_ID,
                        operation_id=op_id,
                        safe_number=f"INV-SYN-{inv_id.hex}",
                        amount_minor=price.amount_minor + 100000,
                        currency="RUB",
                    )
                )
                await db.flush()
                db.add(
                    BillingEntitlementGrant(
                        id=grant_id,
                        workspace_id=WORKSPACE_ID,
                        invoice_id=inv_id,
                        provider_payment_id=f"synthetic-{index}",
                        plan_code="personal",
                        cycle="month",
                        starts_at=start,
                        ends_at=end,
                        amount_minor=price.amount_minor + 100000,
                        currency="RUB",
                    )
                )
                await db.flush()
                db.add(
                    BillingStorageEntitlementGrant(
                        workspace_id=WORKSPACE_ID,
                        invoice_id=inv_id,
                        base_grant_id=grant_id,
                        capacity_bytes=gb * 1_000_000_000,
                        starts_at=start,
                        ends_at=end,
                        catalog_version_id=price.id,
                        full_period_amount_minor=price.amount_minor,
                    )
                )
            await db.flush()
            assert (
                await effective_paid_storage(
                    db, subscription=subscription, now=now - timedelta(microseconds=1)
                )
                == 20_000_000_000
            )
            assert (
                await effective_paid_storage(db, subscription=subscription, now=now)
                == 5_000_000_000
            )
            assert (
                await effective_paid_storage(
                    db, subscription=subscription, now=now + timedelta(days=30)
                )
                == 100_000_000_000
            )
            assert (
                await effective_paid_storage(
                    db, subscription=subscription, now=now + timedelta(days=60)
                )
                == 250_000_000
            )
            # Buy 20 GB for the current 5 GB period while preserving the
            # already prepaid 100 GB period. The next unpaid period is 20 GB.
            subscription.next_capacity_version = 0
            calculation = await calculate_storage_purchase(
                db, subscription=subscription, target_capacity_bytes=20_000_000_000, now=now
            )
            assert calculation.payable_amount_minor == 50000
            assert len(calculation.segments) == 1
            projected = await storage_period_timeline(
                db, subscription=subscription, now=now, upgraded_segments=calculation.segments
            )
            assert [item["capacity_bytes"] for item in projected] == [
                20_000_000_000,
                100_000_000_000,
            ]
            operation = BillingOperation(
                workspace_id=WORKSPACE_ID,
                kind="storage_upgrade",
                idempotency_key="synthetic-20-100-20",
                request_snapshot={
                    "storage_segments": [item.as_dict() for item in calculation.segments],
                    "target_capacity_bytes": 20_000_000_000,
                    "selection_version": 0,
                },
            )
            db.add(operation)
            await db.flush()
            invoice = BillingInvoice(
                workspace_id=WORKSPACE_ID,
                operation_id=operation.id,
                safe_number="INV-SYNTH2010020",
                amount_minor=50000,
                currency="RUB",
            )
            db.add(invoice)
            await db.flush()
            assert (
                await grant_confirmed_storage(db, operation=operation, invoice=invoice, now=now)
                == "granted"
            )
            assert (
                await grant_confirmed_storage(db, operation=operation, invoice=invoice, now=now)
                == "duplicate"
            )
            assert subscription.capacity_bytes == subscription.next_capacity_bytes == 20_000_000_000
            assert (
                await effective_paid_storage(
                    db, subscription=subscription, now=now + timedelta(days=30)
                )
                == 100_000_000_000
            )
            from twobrain_rec_server.billing.catalog import PlanCatalogSnapshot
            from twobrain_rec_server.public.offers import PUBLIC_APPROVED_OFFER_VERSION

            base = PlanCatalogSnapshot(
                plan_code="personal",
                cycle="month",
                version=1,
                amount_minor=100000,
                currency="RUB",
                storage_bytes=2_000_000_000,
                offer_version=PUBLIC_APPROVED_OFFER_VERSION,
                processing_mode="unlimited",
                policy_snapshot={},
            )
            composed, _ = await compose_personal_catalog(
                db, base=base, subscription=subscription, now=now
            )
            assert composed.amount_minor == 179000 and composed.storage_bytes == 20_000_000_000
            # Immutable money snapshots are protected even against direct SQL.
            from sqlalchemy.exc import DBAPIError

            for statement in (
                "UPDATE billing_storage_entitlement_grants SET capacity_bytes = 2",
                "DELETE FROM billing_storage_entitlement_grants",
                "UPDATE billing_storage_price_versions SET amount_minor = 1",
            ):
                with pytest.raises(DBAPIError):
                    async with db.begin_nested():
                        await db.execute(text(statement))
            await db.rollback()

    asyncio.run(scenario())


def test_late_storage_success_keeps_money_and_opens_one_remedy_without_fake_access(client):
    from tests.fakes.auth_contexts import USER_ID
    from twobrain_rec_server.billing.purchases import grant_confirmed_storage
    from twobrain_rec_server.db.models import BillingInvoice, WorkspaceSubscription

    async def scenario():
        now = datetime.now(UTC)
        async with client.app_state["sessionmaker"]() as db:
            subscription = await db.scalar(
                select(WorkspaceSubscription).where(
                    WorkspaceSubscription.workspace_id == WORKSPACE_ID
                )
            )
            if subscription is None:
                subscription = WorkspaceSubscription(workspace_id=WORKSPACE_ID)
                db.add(subscription)
            subscription.billing_owner_id = USER_ID
            subscription.plan_code = "personal"
            subscription.capacity_bytes = 2_000_000_000
            subscription.paid_through = now - timedelta(hours=1)
            operation = BillingOperation(
                workspace_id=WORKSPACE_ID,
                kind="storage_upgrade",
                idempotency_key="synthetic-expired-storage",
                state="unknown",
                request_snapshot={
                    "storage_segments": [{"ends_at": (now - timedelta(hours=1)).isoformat()}],
                },
            )
            db.add(operation)
            db.add(
                BillingAcceptanceBudget(
                    workspace_id=WORKSPACE_ID,
                    limit_minor=20000,
                    enabled=True,
                    expires_at=now + timedelta(days=1),
                )
            )
            await db.flush()
            invoice = BillingInvoice(
                workspace_id=WORKSPACE_ID,
                operation_id=operation.id,
                safe_number="INV-SYNTHETICEXPIRED",
                amount_minor=290,
                currency="RUB",
                plan_snapshot={},
            )
            db.add(invoice)
            await db.flush()
            await reserve_acceptance_budget(
                db, workspace_id=WORKSPACE_ID, operation_id=operation.id, amount_minor=290, now=now
            )
            await settle_acceptance_budget(
                db, workspace_id=WORKSPACE_ID, operation_id=operation.id, succeeded=True
            )
            assert (
                await grant_confirmed_storage(db, operation=operation, invoice=invoice, now=now)
                == "service_expired"
            )
            review_by = operation.request_snapshot["reconciliation_detail"]["review_by"]
            assert (
                await grant_confirmed_storage(
                    db, operation=operation, invoice=invoice, now=now + timedelta(hours=2)
                )
                == "service_expired"
            )
            assert operation.request_snapshot["reconciliation_detail"]["review_by"] == review_by
            assert invoice.status == "succeeded" and operation.state == "reconciliation_gap"
            assert subscription.capacity_bytes == 2_000_000_000
            assert subscription.paid_through == now - timedelta(hours=1)
            budget = await db.scalar(
                select(BillingAcceptanceBudget).where(
                    BillingAcceptanceBudget.workspace_id == WORKSPACE_ID
                )
            )
            assert budget.spent_minor == 290 and budget.reserved_minor == 0
            await db.commit()

    asyncio.run(scenario())
