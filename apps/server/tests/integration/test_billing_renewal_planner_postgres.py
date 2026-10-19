"""Real PostgreSQL transaction proof, with synthetic purchase truth and no API."""

from contextlib import asynccontextmanager
from copy import deepcopy
from datetime import UTC, datetime, timedelta
from types import SimpleNamespace
from uuid import uuid4

import httpx
import pytest
from cryptography.fernet import Fernet
from sqlalchemy import select, text, update

from tests.integration.test_rls_postgres_policies import _seed_probe_rows
from twobrain_rec_server.billing.catalog import validate_plan_version
from twobrain_rec_server.billing.purchases import accept_base_price
from twobrain_rec_server.billing.reconciliation import ProviderScope
from twobrain_rec_server.billing.renewal_charge import (
    pending_renewal_charge_candidates,
    plan_due_renewals,
)
from twobrain_rec_server.billing.webhook_reconciliation import apply_confirmed_purchase
from twobrain_rec_server.config import Settings
from twobrain_rec_server.db.models import (
    BillingAuditEvent,
    BillingEntitlementGrant,
    BillingInvoice,
    BillingOperation,
    BillingPaymentMethod,
    BillingPlanVersion,
    ExternalIdentity,
    Workspace,
    WorkspaceSubscription,
)
from twobrain_rec_server.db.session import create_engine, create_sessionmaker
from twobrain_rec_server.db.tenant_context import MaintenanceTenantContext, apply_tenant_context

pytest_plugins = ("tests.integration.test_rls_postgres_policies",)
pytestmark = [pytest.mark.strict_rls, pytest.mark.asyncio]

CONTEXT = MaintenanceTenantContext(
    operation_name="billing_reconciliation",
    actor_id="test-renewal-planner",
    reason_category="renewal_transaction_regression",
    feature_area="billing",
)


@asynccontextmanager
async def _session(factory):
    async with factory() as db:
        await apply_tenant_context(db, CONTEXT)
        yield db


def _row_snapshot(row):
    return deepcopy({column.name: getattr(row, column.name) for column in row.__table__.columns})


async def _original_purchase(db, case):
    """Compare original money, rights, price consent and saved method exactly."""
    subscription = await db.get(WorkspaceSubscription, case.workspace)
    operation = await db.get(BillingOperation, case.initial_id)
    invoice = await db.get(BillingInvoice, case.invoice_id)
    grants = list(
        await db.scalars(
            select(BillingEntitlementGrant)
            .where(BillingEntitlementGrant.workspace_id == case.workspace)
            .order_by(BillingEntitlementGrant.id)
        )
    )
    methods = list(
        await db.scalars(
            select(BillingPaymentMethod)
            .where(BillingPaymentMethod.workspace_id == case.workspace)
            .order_by(BillingPaymentMethod.id)
        )
    )
    return {
        "subscription": _row_snapshot(subscription),
        "operation": _row_snapshot(operation),
        "invoice": _row_snapshot(invoice),
        "grants": [_row_snapshot(row) for row in grants],
        "methods": [_row_snapshot(row) for row in methods],
    }


async def _renewal_rows(db, workspace):
    operations = list(
        await db.scalars(
            select(BillingOperation)
            .where(BillingOperation.workspace_id == workspace, BillingOperation.kind == "renewal")
            .order_by(BillingOperation.id)
        )
    )
    invoices = list(
        await db.scalars(
            select(BillingInvoice)
            .join(BillingOperation, BillingOperation.id == BillingInvoice.operation_id)
            .where(BillingInvoice.workspace_id == workspace, BillingOperation.kind == "renewal")
            .order_by(BillingInvoice.id)
        )
    )
    audits = list(
        await db.scalars(
            select(BillingAuditEvent)
            .where(
                BillingAuditEvent.workspace_id == workspace,
                BillingAuditEvent.action == "renewal.operation_scheduled",
            )
            .order_by(BillingAuditEvent.id)
        )
    )
    return operations, invoices, audits


def _assert_linked_renewal(rows, case, operation_id):
    operations, invoices, audits = rows
    assert tuple(map(len, rows)) == (1, 1, 1)
    operation, invoice, audit = operations[0], invoices[0], audits[0]
    assert operation.id == invoice.operation_id == operation_id
    assert operation.workspace_id == invoice.workspace_id == audit.workspace_id == case.workspace
    assert operation.state == "scheduled" and operation.provider_id is None
    assert invoice.status == "pending" and invoice.amount_minor == case.amount
    assert invoice.currency == "RUB"
    assert invoice.plan_snapshot == operation.request_snapshot
    assert operation.request_snapshot["catalog_snapshot"] == case.catalog
    assert operation.request_snapshot["renewal_attempt"] == 1
    assert audit.target_kind == "billing_operation" and audit.target_ref == invoice.safe_number
    assert audit.outcome == "scheduled" and audit.actor_user_id == case.owner


@pytest.fixture
async def paid_workspace(migrated_postgres_urls, tmp_path, monkeypatch):
    requests = []

    def forbid_http(*args, **kwargs):
        requests.append(True)
        raise AssertionError("PostgreSQL planner regression must not call an external service")

    # Both httpx clients stop before outbound I/O; no provider transport is substituted.
    monkeypatch.setattr(httpx.AsyncClient, "send", forbid_http)
    monkeypatch.setattr(httpx.Client, "send", forbid_http)
    key = tmp_path / "synthetic-payment-method-key"
    key.write_bytes(Fernet.generate_key())
    key.chmod(0o600)
    settings = Settings(
        _env_file=None,
        env="test",
        database_url=migrated_postgres_urls.probe_url,
        credential_encryption_key_file=key,
        billing_checkout_enabled=False,
        billing_provider_observation_enabled=False,
    )
    engine = create_engine(settings)
    factory = create_sessionmaker(engine)
    try:
        async with engine.connect() as conn:
            role = (
                await conn.execute(
                    text(
                        """
                select current_user, r.rolsuper, r.rolbypassrls,
                       current_user = pg_get_userbyid(c.relowner),
                       current_setting('row_security')
                from pg_roles r cross join pg_class c
                where r.rolname = current_user and c.relname = 'billing_operations'
                  and c.relnamespace = 'public'::regnamespace
            """
                    )
                )
            ).one()
            assert tuple(role) == ("twobrain_rec_maintenance", False, False, False, "on")
        ids = await _seed_probe_rows(engine)
        case = SimpleNamespace(factory=factory, workspace=ids["workspace_a"], owner=ids["user_a"])
        now = datetime.now(UTC)
        async with _session(factory) as db:
            base = await db.scalar(
                select(BillingPlanVersion)
                .where(
                    BillingPlanVersion.plan_code == "personal", BillingPlanVersion.cycle == "month"
                )
                .order_by(BillingPlanVersion.version.desc())
                .limit(1)
            )
            assert base is not None
            # Approve the existing migrated catalog only in this disposable fixture.
            base.enabled_for_checkout = True
            base.effective_until = None
            catalog = validate_plan_version(base, now=now)
            case.catalog, case.amount = catalog.as_dict(), catalog.amount_minor
            await db.execute(
                update(Workspace)
                .where(Workspace.id == case.workspace)
                .values(kind="personal", owner_user_id=case.owner)
            )
            subscription = WorkspaceSubscription(
                workspace_id=case.workspace, billing_owner_id=case.owner
            )
            db.add(subscription)
            await db.flush()
            accept_base_price(subscription, case.catalog)
            snapshot = {
                "plan_code": "personal",
                "cycle": "month",
                "catalog_snapshot": case.catalog,
                "storage_price_snapshot": None,
                "storage_capacity_bytes": 5_000_000_000,
                "purchase_schema": 2,
                "purchase_purpose": "initial_checkout",
                "provider_environment": "test",
                "provider_shop_id": "1",
                "list_amount_minor": case.amount,
                "payable_amount_minor": case.amount,
                "offer_consent": True,
                "recurring_consent": True,
                "recurring_authority_version": subscription.recurring_authority_version,
                "selection_version": subscription.next_capacity_version,
                "billing_actor_user_id": str(case.owner),
                "offer_version": catalog.offer_version,
            }
            initial = BillingOperation(
                id=uuid4(),
                workspace_id=case.workspace,
                kind="initial_checkout",
                idempotency_key="synthetic-initial-" + uuid4().hex,
                state="processing",
                provider_id=str(uuid4()),
                request_snapshot=snapshot,
            )
            db.add(initial)
            # Initial checkout precondition only; never flush a renewal parent in the test.
            await db.flush()
            invoice = BillingInvoice(
                workspace_id=case.workspace,
                operation_id=initial.id,
                safe_number="INV-SYNTHETIC-" + uuid4().hex,
                amount_minor=case.amount,
                currency="RUB",
                status="pending",
                plan_snapshot=deepcopy(snapshot),
                receipt_contact_snapshot="planner@example.invalid",
            )
            db.add(invoice)
            db.add(
                ExternalIdentity(
                    user_id=case.owner,
                    provider="synthetic-planner",
                    provider_subject=uuid4().hex,
                    email="planner@example.invalid",
                    is_verified=True,
                    is_active=True,
                )
            )
            await db.commit()
            # Explicitly synthetic truth, without HTTP or a provider transport double.
            payload = {
                "id": initial.provider_id,
                "status": "succeeded",
                "paid": True,
                "test": True,
                "created_at": now.isoformat(),
                "captured_at": now.isoformat(),
                "receipt_registration": "succeeded",
                "recipient": {"account_id": "1"},
                "amount": {
                    "value": f"{case.amount // 100}.{case.amount % 100:02d}",
                    "currency": "RUB",
                },
                "metadata": {
                    "workspace_id": str(case.workspace),
                    "operation_id": str(initial.id),
                    "invoice_number": invoice.safe_number,
                },
                "payment_method": {
                    "id": "synthetic-no-provider-method",
                    "type": "bank_card",
                    "saved": True,
                    "card": {"last4": "4444"},
                },
            }
            result = await apply_confirmed_purchase(
                db,
                settings,
                operation=initial,
                payload=payload,
                scope=ProviderScope(environment="test", shop_id="1"),
            )
            assert result == "granted"
            await db.commit()
            case.initial_id, case.invoice_id = initial.id, invoice.id
        # Re-read committed rows: onupdate columns are expired in the bootstrap
        # identity map and must not trigger implicit async I/O during snapshots.
        async with _session(factory) as db:
            case.original = await _original_purchase(db, case)
            original = case.original["subscription"]
            case.t0 = original["paid_through"] - timedelta(hours=72)
            assert original["state"] == original["plan_code"] == "personal"
            assert original["cycle"] == "month" and original["recurring_allowed"] is True
            assert len(case.original["grants"]) == len(case.original["methods"]) == 1
            assert case.original["methods"][0]["state"] == "active"
            assert case.original["methods"][0]["key_version"] == "billing-v1"
        yield case
        assert requests == []
    finally:
        await engine.dispose()


async def test_due_renewal_commits_parent_invoice_audit_once(paid_workspace):
    case = paid_workspace
    async with _session(case.factory) as db:
        assert (
            await plan_due_renewals(
                db,
                now=case.t0 - timedelta(seconds=1),
                allowed_workspace_ids=frozenset({case.workspace}),
            )
            == ()
        )
        await db.commit()
    async with _session(case.factory) as db:
        planned = await plan_due_renewals(
            db, now=case.t0, allowed_workspace_ids=frozenset({case.workspace})
        )
        assert len(planned) == 1
        _assert_linked_renewal(await _renewal_rows(db, case.workspace), case, planned[0])
        # A flush must not commit: another transaction still sees no new rows.
        async with _session(case.factory) as observer:
            assert tuple(map(len, await _renewal_rows(observer, case.workspace))) == (0, 0, 0)
        await db.commit()
    async with _session(case.factory) as db:
        rows = await _renewal_rows(db, case.workspace)
        _assert_linked_renewal(rows, case, planned[0])
        stable = tuple([_row_snapshot(row) for row in group] for group in rows)
        candidates = await pending_renewal_charge_candidates(db, now=case.t0)
        assert tuple(candidate for candidate in candidates if candidate[1] == case.workspace) == (
            (planned[0], case.workspace),
        )
        assert await _original_purchase(db, case) == case.original
        assert (
            await plan_due_renewals(
                db, now=case.t0, allowed_workspace_ids=frozenset({case.workspace})
            )
            == planned
        )
        await db.commit()
    async with _session(case.factory) as db:
        assert (
            tuple(
                [_row_snapshot(row) for row in group]
                for group in await _renewal_rows(db, case.workspace)
            )
            == stable
        )
        assert await _original_purchase(db, case) == case.original


async def test_caller_rollback_removes_entire_renewal_then_retry_succeeds(paid_workspace):
    case = paid_workspace
    async with _session(case.factory) as db:
        planned = await plan_due_renewals(
            db, now=case.t0, allowed_workspace_ids=frozenset({case.workspace})
        )
        assert len(planned) == 1
        _assert_linked_renewal(await _renewal_rows(db, case.workspace), case, planned[0])
        await db.rollback()
    async with _session(case.factory) as db:
        assert tuple(map(len, await _renewal_rows(db, case.workspace))) == (0, 0, 0)
        assert await _original_purchase(db, case) == case.original
        candidates = await pending_renewal_charge_candidates(db, now=case.t0)
        assert tuple(candidate for candidate in candidates if candidate[1] == case.workspace) == ()
        retried = await plan_due_renewals(
            db, now=case.t0, allowed_workspace_ids=frozenset({case.workspace})
        )
        assert retried == planned
        await db.commit()
    async with _session(case.factory) as db:
        _assert_linked_renewal(await _renewal_rows(db, case.workspace), case, planned[0])
        assert await _original_purchase(db, case) == case.original


async def test_unknown_attempt_blocks_next_window_without_new_rows(paid_workspace):
    case = paid_workspace
    async with _session(case.factory) as db:
        planned = await plan_due_renewals(
            db, now=case.t0, allowed_workspace_ids=frozenset({case.workspace})
        )
        operation = await db.get(BillingOperation, planned[0])
        operation.state = "unknown"  # Isolated precondition, not a simulated provider result.
        await db.commit()
    async with _session(case.factory) as db:
        rows = await _renewal_rows(db, case.workspace)
        stable = tuple([_row_snapshot(row) for row in group] for group in rows)
        assert (
            await plan_due_renewals(
                db,
                now=case.t0 + timedelta(hours=24),
                allowed_workspace_ids=frozenset({case.workspace}),
            )
            == ()
        )
        await db.commit()
    async with _session(case.factory) as db:
        assert (
            tuple(
                [_row_snapshot(row) for row in group]
                for group in await _renewal_rows(db, case.workspace)
            )
            == stable
        )
        assert await _original_purchase(db, case) == case.original
