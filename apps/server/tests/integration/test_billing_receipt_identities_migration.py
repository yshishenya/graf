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
    finally:
        get_settings.cache_clear()
