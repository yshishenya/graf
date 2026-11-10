import asyncio
from pathlib import Path
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import delete, select, text, update
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from twobrain_rec_server.config import get_settings
from twobrain_rec_server.db.models import (
    BillingInvoice,
    BillingOperation,
    BillingReceiptIdentity,
    Organization,
    Workspace,
)

PREVIOUS = "0109_reconciliation_observations"
CURRENT = "0110_billing_receipt_identities"
RECEIPT = "synthetic-shared-receipt"


@pytest.mark.strict_rls
def test_receipt_identity_backfill_roundtrip_refusal_and_cascade(
    postgres_clean_database_url, monkeypatch,
):
    root = Path(__file__).resolve().parents[2]
    config = Config(str(root / "alembic.ini"))
    config.set_main_option("script_location", str(root / "src/twobrain_rec_server/db/migrations"))
    monkeypatch.setenv("TWOBRAIN_DATABASE_URL", postgres_clean_database_url)
    get_settings.cache_clear()
    workspace_id = uuid4()
    invoices = [uuid4(), uuid4()]

    def snapshot(parent):
        return {"receipt_observations": {f"test:shop-1:{RECEIPT}": {
            "environment": "test", "shop_id": "shop-1", "provider_receipt_id": RECEIPT,
            "parent_kind": "payment", "provider_parent_id": parent, "status": "succeeded",
        }}}

    async def seed():
        engine = create_async_engine(postgres_clean_database_url)
        try:
            sessions = async_sessionmaker(engine)
            async with sessions.begin() as db:
                organization = Organization(id=uuid4(), name="Synthetic", slug="synthetic")
                db.add(organization)
                await db.flush()
                db.add(Workspace(
                    id=workspace_id, organization_id=organization.id,
                    name="Synthetic", slug="synthetic", kind="linked",
                ))
                await db.flush()
                for i, invoice_id in enumerate(invoices):
                    payment_id = f"synthetic-payment-{i}"
                    operation = BillingOperation(
                        workspace_id=workspace_id, kind="initial_checkout", state="succeeded",
                        idempotency_key=payment_id, provider_id=payment_id, request_snapshot={},
                    )
                    db.add(operation)
                    await db.flush()
                    db.add(BillingInvoice(
                        id=invoice_id, workspace_id=workspace_id, operation_id=operation.id,
                        safe_number=f"SYNTHETIC-{i}", amount_minor=1000, status="succeeded",
                        plan_snapshot=snapshot(payment_id),
                    ))
        finally:
            await engine.dispose()

    async def execute(statement):
        engine = create_async_engine(postgres_clean_database_url)
        try:
            async with engine.begin() as conn:
                result = await conn.execute(statement)
                return result.all() if result.returns_rows else None
        finally:
            await engine.dispose()

    select_cards = select(BillingInvoice.id, BillingInvoice.plan_snapshot).order_by(BillingInvoice.id)
    select_identities = select(BillingReceiptIdentity.__table__)
    marker = text("select version_num, to_regclass('billing_receipt_identities')::text from alembic_version")
    change_second = update(BillingInvoice).where(BillingInvoice.id == invoices[1])
    try:
        command.upgrade(config, PREVIOUS)
        asyncio.run(seed())
        old_cards = asyncio.run(execute(select_cards))
        with pytest.raises(DBAPIError, match="Historical receipt identities are inconsistent") as duplicate:
            command.upgrade(config, CURRENT)
        assert RECEIPT not in str(duplicate.value)
        assert asyncio.run(execute(marker)) == [(PREVIOUS, None)]
        assert asyncio.run(execute(select_cards)) == old_cards

        change_first = update(BillingInvoice).where(BillingInvoice.id == invoices[0])
        asyncio.run(execute(change_first.values(plan_snapshot={})))
        asyncio.run(execute(change_second.values(plan_snapshot=snapshot("wrong-parent"))))
        with pytest.raises(DBAPIError, match="Historical receipt identities are inconsistent"):
            command.upgrade(config, CURRENT)
        assert asyncio.run(execute(marker)) == [(PREVIOUS, None)]

        operation_id = asyncio.run(execute(
            select(BillingInvoice.operation_id).where(BillingInvoice.id == invoices[1])
        ))[0][0]
        conflict = {
            **snapshot("synthetic-payment-1"),
            "receipt_payment_binding": {
                "workspace_id": str(workspace_id), "operation_id": str(operation_id),
                "payment_id": "synthetic-payment-1", "environment": "test", "shop_id": "another-shop",
            },
        }
        asyncio.run(execute(change_second.values(plan_snapshot=conflict)))
        conflict_cards = asyncio.run(execute(select_cards))
        with pytest.raises(DBAPIError, match="Historical receipt identities are inconsistent"):
            command.upgrade(config, CURRENT)
        assert asyncio.run(execute(marker)) == [(PREVIOUS, None)]
        assert asyncio.run(execute(select_cards)) == conflict_cards

        asyncio.run(execute(change_second.values(plan_snapshot={})))
        asyncio.run(execute(change_first.values(plan_snapshot=snapshot("synthetic-payment-0"))))
        cards = asyncio.run(execute(select_cards))
        command.upgrade(config, CURRENT)
        binding = [("test", "shop-1", RECEIPT, workspace_id, invoices[0], "payment", "synthetic-payment-0")]
        assert asyncio.run(execute(select_identities)) == binding
        command.downgrade(config, PREVIOUS)
        assert asyncio.run(execute(marker)) == [(PREVIOUS, None)]
        assert asyncio.run(execute(select_cards)) == cards
        command.upgrade(config, CURRENT)
        assert asyncio.run(execute(select_cards)) == cards
        assert asyncio.run(execute(select_identities)) == binding
        asyncio.run(execute(delete(BillingInvoice).where(BillingInvoice.id == invoices[0])))
        assert asyncio.run(execute(select_identities)) == []
        # Upgrade from 0110, not a clean database: refuse malformed history
        # without recording a partial transfer, then carry all three classes.
        observation_revision = "0111_receipt_observation_deltas"
        delta_table = "billing_receipt_observation_deltas"
        delta_marker = text(f"select version_num, to_regclass('{delta_table}')::text from alembic_version")
        sums = text(f"select sum(canceled_delta), sum(overdue_confirmed_delta), sum(overdue_unknown_delta) from {delta_table}")
        start, due = "2026-11-01T12:00:00+00:00", "2026-11-04T12:00:00+00:00"
        payment_timing = {
            "first_confirmed_pending_at": start,
            "canceled": {"freshness": "confirmed", "detected_at": due, "due_at": due},
            "pending_overdue": {"freshness": "confirmed", "detected_at": due, "due_at": due},
        }
        refund = {
            "parent_kind": "refund", "provider_receipt_id": "synthetic-refund",
            "provider_parent_id": "synthetic-parent", "environment": "test", "shop_id": "shop-1",
            "first_confirmed_pending_at": start,
            "pending_overdue": {"freshness": "unknown", "detected_at": due, "due_at": due},
        }
        with_refund = {"receipt_registration_timing": payment_timing,
                       "receipt_observations": {"test:shop-1:synthetic-refund": refund}}
        asyncio.run(execute(change_second.values(plan_snapshot={
            **with_refund, "receipt_registration_timing": {**payment_timing, "pending_overdue": {}},
        })))
        with pytest.raises(DBAPIError, match="Receipt observation basis is invalid"):
            command.upgrade(config, observation_revision)
        assert asyncio.run(execute(delta_marker)) == [(CURRENT, None)]

        asyncio.run(execute(change_second.values(plan_snapshot={
            **with_refund, "receipt_observations": {"test:shop-1:synthetic-refund": {
                **refund, "provider_parent_id": None,
            }},
        })))
        with pytest.raises(DBAPIError, match="Receipt observation basis is invalid"):
            command.upgrade(config, observation_revision)
        assert asyncio.run(execute(delta_marker)) == [(CURRENT, None)]

        asyncio.run(execute(change_second.values(plan_snapshot=with_refund)))
        async def prove_refusal_under_force_rls():
            from importlib import import_module

            from alembic.migration import MigrationContext
            from alembic.operations import Operations

            migration = import_module(
                "twobrain_rec_server.db.migrations.versions.0111_receipt_observation_deltas"
            )
            limited = f"receipt_limited_{uuid4().hex}"
            engine = create_async_engine(postgres_clean_database_url)
            try:
                async with engine.begin() as conn:
                    await conn.execute(text(f"CREATE ROLE {limited} NOLOGIN NOINHERIT"))
                    await conn.execute(text(f"GRANT USAGE, CREATE ON SCHEMA public TO {limited}"))
                    await conn.execute(text(f"GRANT SELECT, UPDATE ON billing_invoices TO {limited}"))
                    await conn.execute(text("""
                        DO $$ BEGIN
                            IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'twobrain_rec_receipt_observation_writer') THEN
                                CREATE ROLE twobrain_rec_receipt_observation_writer NOLOGIN NOINHERIT;
                            END IF;
                        END $$
                    """))
                with pytest.raises(DBAPIError, match='query would be affected by row-level security policy for table "billing_invoices"'):
                    async with engine.begin() as conn:
                        await conn.execute(text(f"SET LOCAL ROLE {limited}"))

                        def upgrade(sync_conn):
                            with Operations.context(MigrationContext.configure(sync_conn)):
                                migration.upgrade()

                        await conn.run_sync(upgrade)
                async with engine.begin() as conn:
                    await conn.execute(text(f"DROP OWNED BY {limited}"))
                    await conn.execute(text(f"DROP ROLE {limited}"))
            finally:
                await engine.dispose()

        asyncio.run(prove_refusal_under_force_rls())
        assert asyncio.run(execute(delta_marker)) == [(CURRENT, None)]
        command.upgrade(config, observation_revision)
        assert asyncio.run(execute(sums)) == [(1, 1, 1)]
        with pytest.raises(DBAPIError, match="Receipt observation basis cannot change"):
            asyncio.run(execute(change_second.values(plan_snapshot={"receipt_registration_timing": payment_timing})))
        with pytest.raises(DBAPIError, match="downgrade blocked: receipt observation history exists"):
            command.downgrade(config, CURRENT)
        assert asyncio.run(execute(delta_marker)) == [(observation_revision, delta_table)]
        assert asyncio.run(execute(sums)) == [(1, 1, 1)]
    finally:
        get_settings.cache_clear()
