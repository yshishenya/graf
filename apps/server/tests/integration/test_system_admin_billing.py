"""Exact historical pins and immutable offers on real PostgreSQL; synthetic money."""

from copy import deepcopy
from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from tests.conftest import PERSONAL_WORKSPACE_ID, USER_ID
from twobrain_rec_server.billing.catalog import validate_plan_version
from twobrain_rec_server.billing.catalog_migration import backfill_subscription_pins
from twobrain_rec_server.db.models.billing import (
    BillingEntitlementGrant,
    BillingInvoice,
    BillingOperation,
    BillingPaymentMethod,
    BillingPlanPrice,
    BillingPlanVersion,
    WorkspaceSubscription,
)

pytestmark = pytest.mark.strict_rls


async def _managed_payment(db, cycle="month"):
    from twobrain_rec_server.db.models.billing import BillingPlan

    plan = BillingPlan(id=uuid4(), code="research_plus", display_name="Synthetic Research")
    db.add(plan)
    await db.flush()
    version = BillingPlanVersion(
        id=uuid4(), plan_id=plan.id, plan_code=plan.code, version=1, status="draft",
        capability_schema_version=1,
        capabilities={**_capabilities(), "processing_unlimited": False, "processing_seconds": 24000},
        display_terms={"name":"Synthetic Research", "description":"", "audience":"admin", "trial_days":0},
        cycle="none", currency="RUB", storage_bytes=4_000_000_000,
        processing_mode="quota", policy_snapshot={"offer_version":"synthetic-research-v1"},
    )
    db.add(version)
    await db.flush()
    prices = [BillingPlanPrice(id=uuid4(), version_id=version.id, cycle=value, currency="RUB", amount_minor=amount)
        for value,amount in (("month", 123400), ("year", 1234000))]
    db.add_all(prices)
    await db.flush()
    version.status = "published"
    version.enabled_for_checkout = True
    await db.flush()
    price = next(row for row in prices if row.cycle == cycle)
    snapshot = {
        "plan_code":plan.code, "cycle":cycle,
        "catalog_snapshot":validate_plan_version(version, price=price).as_dict(),
        "list_amount_minor":price.amount_minor, "payable_amount_minor":price.amount_minor*80//100,
        "billing_actor_user_id":str(USER_ID), "recurring_consent":True,
    }
    operation = BillingOperation(
        id=uuid4(), workspace_id=PERSONAL_WORKSPACE_ID, kind="initial_checkout",
        idempotency_key=f"synthetic:{uuid4()}", state="provider_pending",
        provider_id=f"synthetic-{uuid4()}", request_snapshot=deepcopy(snapshot),
    )
    db.add(operation)
    await db.flush()
    invoice = BillingInvoice(
        id=uuid4(), workspace_id=PERSONAL_WORKSPACE_ID, operation_id=operation.id,
        safe_number=f"SYNTHETIC-{uuid4()}", amount_minor=snapshot["payable_amount_minor"],
        currency="RUB", plan_snapshot=deepcopy(snapshot), receipt_contact_snapshot="synthetic@example.invalid",
    )
    db.add(invoice)
    await db.commit()
    return version, price, operation, invoice


@pytest.mark.asyncio
@pytest.mark.parametrize("cycle", ["month", "year"])
async def test_managed_payment_pins_exact_offer_and_renews_after_sales_close(postgres_seeded_database_url, cycle):
    from cryptography.fernet import Fernet

    from twobrain_rec_server.billing.entitlements import (
        grant_confirmed_payment,
        grant_confirmed_renewal,
        resolve_entitlements,
    )
    from twobrain_rec_server.billing.payment_methods import SavedPaymentMethod
    from twobrain_rec_server.billing.renewal_charge import (
        plan_due_renewals,
        project_renewal_cutoffs,
    )

    engine = create_async_engine(postgres_seeded_database_url)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with sessions() as db:
            version, price, operation, invoice = await _managed_payment(db, cycle)
            original = deepcopy(invoice.plan_snapshot)
            # 31 Jan in Moscow, still 30 Jan UTC: calendar boundaries use the pinned zone.
            paid_at = datetime(2028, 1, 30, 22, tzinfo=UTC)
            kwargs = dict(workspace_id=PERSONAL_WORKSPACE_ID, provider_payment_id=operation.provider_id,
                amount_minor=invoice.amount_minor, currency="RUB", paid_at=paid_at,
                recurring_method_confirmed=True,
                saved_payment_method=SavedPaymentMethod("synthetic-method", "bank_card", "•••• 0000"),
                payment_method_key=Fernet.generate_key())
            # The invoice survives closing sales before its provider confirmation arrives.
            version.status = "retired"
            version.enabled_for_checkout = False
            await db.commit()
            assert await grant_confirmed_payment(db, **kwargs) == "granted"
            await db.commit()
            subscription = await db.get(WorkspaceSubscription, PERSONAL_WORKSPACE_ID, populate_existing=True)
            first_end = datetime(2028, 2, 28, 22, tzinfo=UTC) if cycle == "month" else datetime(2029, 1, 30, 22, tzinfo=UTC)
            assert subscription.paid_through == first_end
            assert subscription.plan_code == "research_plus"
            assert subscription.pinned_plan_version_id == version.id
            assert subscription.pinned_price_id == price.id
            assert subscription.timezone == "Europe/Moscow"
            schedule_version = subscription.schedule_version
            assert await grant_confirmed_payment(db, **kwargs) == "duplicate"
            await db.commit()
            await db.refresh(subscription)
            assert subscription.schedule_version == schedule_version
            assert subscription.paid_through == first_end
            assert invoice.plan_snapshot == original
            access = await resolve_entitlements(db, workspace_id=PERSONAL_WORKSPACE_ID, subject_user_id=USER_ID, now=paid_at)
            assert access.plan_code == "research_plus"
            assert access.capabilities["processing_seconds"] == 24000
            assert access.capabilities["processing_unlimited"] is False
            planned = await plan_due_renewals(db, now=first_end-timedelta(hours=48))
            assert len(planned) == 1
            await db.commit()
            renewal = await db.get(BillingOperation, planned[0])
            renewal_invoice = await db.scalar(select(BillingInvoice).where(BillingInvoice.operation_id == renewal.id))
            assert renewal_invoice.amount_minor == price.amount_minor  # First-payment discount is not recurring.
            assert renewal_invoice.plan_snapshot["catalog_snapshot"] == original["catalog_snapshot"]
            renewal.provider_id = f"synthetic-renewal-{uuid4()}"
            renewal.state = "sent"
            await db.commit()
            assert await project_renewal_cutoffs(db, now=first_end) == 1
            await db.commit()
            renewal_kwargs = dict(workspace_id=PERSONAL_WORKSPACE_ID, provider_payment_id=renewal.provider_id,
                amount_minor=price.amount_minor, currency="RUB", grant_starts_at=first_end)
            assert await grant_confirmed_renewal(db, **renewal_kwargs) == "granted"
            await db.commit()
            assert await grant_confirmed_renewal(db, **renewal_kwargs) == "duplicate"
            await db.commit()
            await db.refresh(subscription)
            assert subscription.plan_code == "research_plus"
            assert subscription.pinned_plan_version_id == version.id
            assert subscription.schedule_version == schedule_version+1
            grants = list(await db.scalars(select(BillingEntitlementGrant).where(BillingEntitlementGrant.workspace_id == PERSONAL_WORKSPACE_ID)))
            assert len(grants) == 2
            assert all(row.plan_version_id == version.id and row.plan_code == "research_plus" for row in grants)
            assert grants[0].invoice_id != grants[1].invoice_id
    finally:
        await engine.dispose()


@pytest.mark.asyncio
@pytest.mark.parametrize("scenario", ["schedule_changed", "legacy_purchase"])
async def test_managed_terms_do_not_survive_an_incompatible_payment(postgres_seeded_database_url, scenario):
    from cryptography.fernet import Fernet

    from twobrain_rec_server.billing.entitlements import (
        grant_confirmed_payment,
        grant_confirmed_renewal,
    )
    from twobrain_rec_server.billing.payment_methods import SavedPaymentMethod
    from twobrain_rec_server.billing.renewal_charge import plan_due_renewals

    engine = create_async_engine(postgres_seeded_database_url)
    try:
        async with async_sessionmaker(engine, expire_on_commit=False)() as db:
            _, _, operation, invoice = await _managed_payment(db)
            method = dict(recurring_method_confirmed=True,
                saved_payment_method=SavedPaymentMethod("synthetic-method", "bank_card", "•••• 0000"),
                payment_method_key=Fernet.generate_key())
            now = datetime.now(UTC)
            assert await grant_confirmed_payment(db, workspace_id=PERSONAL_WORKSPACE_ID,
                provider_payment_id=operation.provider_id, amount_minor=invoice.amount_minor,
                currency="RUB", paid_at=now, **method) == "granted"
            await db.commit()
            subscription = await db.get(WorkspaceSubscription, PERSONAL_WORKSPACE_ID, populate_existing=True)
            due = subscription.paid_through
            if scenario == "schedule_changed":
                planned = await plan_due_renewals(db, now=due-timedelta(hours=24))
                await db.commit()
                renewal = await db.get(BillingOperation, planned[0])
                renewal_invoice = await db.scalar(select(BillingInvoice).where(BillingInvoice.operation_id == renewal.id))
                renewal.provider_id = f"synthetic-renewal-{uuid4()}"
                renewal.state = "sent"
                subscription.schedule_version += 1
                await db.commit()
                assert await grant_confirmed_renewal(db, workspace_id=PERSONAL_WORKSPACE_ID,
                    provider_payment_id=renewal.provider_id, amount_minor=renewal_invoice.amount_minor,
                    currency="RUB", grant_starts_at=due) == "schedule_mismatch"
                await db.commit()
                await db.refresh(subscription)
                assert subscription.paid_through == due
                assert await db.scalar(select(BillingEntitlementGrant.id).where(BillingEntitlementGrant.invoice_id == renewal_invoice.id)) is None
            else:
                # A pre-catalog invoice still settles after a managed subscription.
                snapshot = {"plan_code":"personal", "cycle":"month", "billing_actor_user_id":str(USER_ID), "recurring_consent":True}
                legacy = BillingOperation(id=uuid4(), workspace_id=PERSONAL_WORKSPACE_ID,
                    kind="initial_checkout", state="provider_pending", idempotency_key=f"synthetic:{uuid4()}",
                    provider_id=f"synthetic-legacy-{uuid4()}", request_snapshot=snapshot)
                db.add(legacy)
                await db.flush()
                db.add(BillingInvoice(workspace_id=PERSONAL_WORKSPACE_ID, operation_id=legacy.id,
                    safe_number=f"SYNTHETIC-{uuid4()}", amount_minor=100000, currency="RUB", plan_snapshot=snapshot))
                await db.commit()
                assert await grant_confirmed_payment(db, workspace_id=PERSONAL_WORKSPACE_ID,
                    provider_payment_id=legacy.provider_id, amount_minor=100000,
                    currency="RUB", paid_at=due, **method) == "granted"
                await db.commit()
                await db.refresh(subscription)
                assert subscription.plan_code == "personal"
                assert subscription.pinned_plan_version_id is None and subscription.pinned_price_id is None
                assert subscription.pin_state == "pending"
                assert subscription.capacity_bytes == 2_000_000_000
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_managed_payment_applies_under_actual_request_role(postgres_seeded_database_url):
    from sqlalchemy.ext.asyncio import AsyncSession

    from tests.integration.test_rls_postgres_policies import _exact_app_role_engine
    from twobrain_rec_server.billing.entitlements import (
        grant_confirmed_payment,
        resolve_entitlements,
    )
    from twobrain_rec_server.db.models.identity import Workspace
    from twobrain_rec_server.db.tenant_context import (
        TenantDatabaseContext,
        apply_tenant_context_to_connection,
    )

    engine = create_async_engine(postgres_seeded_database_url)
    try:
        async with async_sessionmaker(engine, expire_on_commit=False)() as db:
            version, _, operation, invoice = await _managed_payment(db)
            organization = (await db.get(Workspace, PERSONAL_WORKSPACE_ID)).organization_id
        async with _exact_app_role_engine(postgres_seeded_database_url) as app, app.connect() as conn:
            await apply_tenant_context_to_connection(conn, TenantDatabaseContext(
                organization_id=organization, workspace_id=PERSONAL_WORKSPACE_ID, user_id=USER_ID))
            assert await conn.scalar(text("select session_user")) == "twobrain_rec_app"
            async with AsyncSession(bind=conn, expire_on_commit=False) as db:
                assert await grant_confirmed_payment(db, workspace_id=PERSONAL_WORKSPACE_ID,
                    provider_payment_id=operation.provider_id, amount_minor=invoice.amount_minor,
                    currency="RUB", paid_at=datetime.now(UTC), defer_referral_reward=True) == "granted"
                await db.flush()
                access = await resolve_entitlements(db, workspace_id=PERSONAL_WORKSPACE_ID,
                    subject_user_id=USER_ID, now=datetime.now(UTC))
                assert access.base_plan_version_id == version.id and access.plan_code == "research_plus"
    finally:
        await engine.dispose()


@pytest.mark.asyncio
@pytest.mark.parametrize("mismatch", ["missing_catalog", "other_price", "boolean_capability", "amount", "payer", "cycle_type", "plan_type"])
async def test_managed_payment_rejects_inconsistent_financial_snapshot(postgres_seeded_database_url, mismatch):
    from twobrain_rec_server.billing.entitlements import grant_confirmed_payment

    engine = create_async_engine(postgres_seeded_database_url)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with sessions() as db:
            _, _, operation, invoice = await _managed_payment(db)
            snapshot = deepcopy(operation.request_snapshot)
            if mismatch == "missing_catalog":
                snapshot.pop("catalog_snapshot")
            elif mismatch == "other_price":
                snapshot["catalog_snapshot"]["price_id"] = str(uuid4())
            elif mismatch == "boolean_capability":
                # Python dict equality considers True == 1; financial equality must not.
                snapshot["catalog_snapshot"]["capabilities"]["audio_archive"] = 1
                invoice.plan_snapshot = deepcopy(snapshot)
            elif mismatch == "amount":
                snapshot["payable_amount_minor"] += 1
                invoice.plan_snapshot = deepcopy(snapshot)
            elif mismatch == "cycle_type":
                snapshot["cycle"] = ["month"]
            elif mismatch == "plan_type":
                snapshot["plan_code"] = {"code":"research_plus"}
            else:
                snapshot["billing_actor_user_id"] = str(uuid4())
            operation.request_snapshot = snapshot
            await db.commit()
            assert await grant_confirmed_payment(db, workspace_id=PERSONAL_WORKSPACE_ID,
                provider_payment_id=operation.provider_id, amount_minor=invoice.amount_minor,
                currency="RUB", paid_at=datetime.now(UTC)) == "snapshot_invalid"
            await db.commit()
            assert operation.state == "reconciliation_gap"
            assert await db.scalar(select(BillingEntitlementGrant.id).where(BillingEntitlementGrant.invoice_id == invoice.id)) is None
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_historical_pin_never_selects_latest_and_catchup_preserves_money(
    postgres_seeded_database_url,
):
    engine = create_async_engine(postgres_seeded_database_url)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    now = datetime.now(UTC)
    try:
        async with sessions() as db:
            old = BillingPlanVersion(
                id=uuid4(),
                plan_code="personal",
                version=25401,
                cycle="month",
                amount_minor=79000,
                currency="RUB",
                storage_bytes=2_000_000_000,
                processing_mode="unlimited",
                enabled_for_checkout=True,
                policy_snapshot={"offer_version": "synthetic-v25401"},
            )
            new = BillingPlanVersion(
                id=uuid4(),
                plan_code="personal",
                version=25402,
                cycle="month",
                amount_minor=99000,
                currency="RUB",
                storage_bytes=3_000_000_000,
                processing_mode="unlimited",
                enabled_for_checkout=True,
                policy_snapshot={"offer_version": "synthetic-v25402"},
            )
            db.add_all([old, new])
            await db.flush()
            catalog = validate_plan_version(old).as_dict()
            snapshot = {
                "plan_code": "personal",
                "cycle": "month",
                "catalog_snapshot": catalog,
                "list_amount_minor": 79000,
                "payable_amount_minor": 63200,
                "billing_actor_user_id": str(USER_ID),
            }
            operation = BillingOperation(
                id=uuid4(),
                workspace_id=PERSONAL_WORKSPACE_ID,
                kind="initial_checkout",
                idempotency_key=f"synthetic:{uuid4()}",
                state="succeeded",
                provider_id="synthetic-payment-254",
                request_snapshot=snapshot,
            )
            db.add(operation)
            await db.flush()
            invoice = BillingInvoice(
                id=uuid4(),
                workspace_id=PERSONAL_WORKSPACE_ID,
                operation_id=operation.id,
                safe_number=f"SYNTHETIC-{uuid4()}",
                amount_minor=63200,
                currency="RUB",
                status="succeeded",
                plan_snapshot=snapshot,
            )
            db.add(invoice)
            await db.flush()
            grant = BillingEntitlementGrant(
                workspace_id=PERSONAL_WORKSPACE_ID,
                invoice_id=invoice.id,
                provider_payment_id=operation.provider_id,
                plan_code="personal",
                cycle="month",
                starts_at=now,
                ends_at=now + timedelta(days=30),
                amount_minor=63200,
                currency="RUB",
            )
            db.add(grant)
            subscription = await db.get(WorkspaceSubscription, PERSONAL_WORKSPACE_ID)
            if subscription is None:
                subscription = WorkspaceSubscription(workspace_id=PERSONAL_WORKSPACE_ID)
                db.add(subscription)
            subscription.billing_owner_id = USER_ID
            subscription.state = "personal"
            subscription.plan_code = "personal"
            subscription.cycle = "month"
            subscription.paid_through = grant.ends_at
            subscription.billing_anchor = now
            subscription.capacity_bytes = 2_000_000_000
            subscription.recurring_allowed = True
            subscription.recurring_authority_version = 7
            subscription.application_version = 9
            await db.commit()
            old_id, invoice_id = old.id, invoice.id
            invoice.receipt_contact_snapshot = "synthetic@example.invalid"
            db.add(
                BillingPaymentMethod(
                    workspace_id=PERSONAL_WORKSPACE_ID,
                    owner_user_id=USER_ID,
                    encrypted_provider_ref="synthetic-never-sent",
                    key_version="billing-v1",
                    state="active",
                    is_default=True,
                    verified_at=now,
                )
            )
            await db.commit()
            assert (await backfill_subscription_pins(db, limit=100))["pinned"] == 1
            await db.commit()
            await db.refresh(subscription)
            assert subscription.pinned_plan_version_id == old_id
            assert subscription.pin_state == "pinned"
            price = await db.get(BillingPlanPrice, subscription.pinned_price_id)
            assert price.amount_minor == 79000  # A one-time discount never changes renewal price.
            assert subscription.recurring_authority_version == 7
            assert subscription.paid_through == grant.ends_at
            assert subscription.application_version == 9
            assert (await db.get(BillingInvoice, invoice_id)).amount_minor == 63200
            from twobrain_rec_server.billing.renewal_charge import plan_due_renewals

            # Close the old sales offer, then exercise the actual invoice planner.
            old.enabled_for_checkout = False
            await db.commit()
            planned = await plan_due_renewals(db, now=grant.ends_at - timedelta(hours=48))
            assert len(planned) == 1
            await db.commit()
            renewal = await db.scalar(
                select(BillingInvoice).where(BillingInvoice.operation_id == planned[0])
            )
            assert renewal.amount_minor == 79000
            assert renewal.plan_snapshot["pinned_plan_version_id"] == str(old_id)
            assert renewal.plan_snapshot["schedule_version"] == subscription.schedule_version
            # Simulate a pre-migration scheduled operation. Only operation metadata
            # is bound; the existing financial invoice snapshot remains untouched.
            scheduled = await db.get(BillingOperation, planned[0])
            pins = {"pinned_plan_version_id", "pinned_price_id", "schedule_version"}
            legacy_snapshot = {key:value for key,value in scheduled.request_snapshot.items() if key not in pins}
            scheduled.request_snapshot = dict(legacy_snapshot)
            renewal.plan_snapshot = dict(legacy_snapshot)
            await db.commit()
            assert await plan_due_renewals(db, now=grant.ends_at-timedelta(hours=24)) == planned
            await db.commit()
            await db.refresh(scheduled)
            await db.refresh(renewal)
            assert scheduled.request_snapshot["schedule_version"] == subscription.schedule_version
            assert scheduled.request_snapshot["pinned_plan_version_id"] == str(old_id)
            assert renewal.plan_snapshot == legacy_snapshot
            assert await plan_due_renewals(db, now=grant.ends_at-timedelta(hours=12)) == planned
            await db.commit()
            from sqlalchemy import func

            from twobrain_rec_server.db.models import BillingAuditEvent
            assert await db.scalar(select(func.count()).select_from(BillingAuditEvent).where(
                BillingAuditEvent.action=="renewal.legacy_schedule_pinned",
                BillingAuditEvent.workspace_id==PERSONAL_WORKSPACE_ID,
            )) == 1
            from twobrain_rec_server.billing.renewal_charge import project_renewal_cutoffs

            scheduled_version = subscription.schedule_version
            assert await project_renewal_cutoffs(db, now=grant.ends_at) == 1
            await db.commit()
            await db.refresh(subscription)
            assert subscription.plan_code == "free"
            assert subscription.schedule_version == scheduled_version
            # Restore the synthetic active projection for subsequent historical catch-up checks.
            subscription.plan_code = "personal"
            subscription.cycle = "month"
            subscription.state = "personal"
            subscription.capacity_bytes = 2_000_000_000
            await db.commit()
            await backfill_subscription_pins(db, limit=100)
            await db.commit()

            assert (await backfill_subscription_pins(db, limit=100))["processed"] == 0
            await db.commit()
            # Writer catch-up: stale pin watermark is not mistaken for a complete migration.
            subscription.application_version += 1
            await db.commit()
            assert (await backfill_subscription_pins(db, limit=100))["pinned"] == 1
            await db.commit()
            # Published/pinned money cannot be edited even by the database owner.
            with pytest.raises(Exception, match="immutable"):
                await db.execute(
                    text("update billing_plan_prices set amount_minor=1 where id=:id"),
                    {"id": price.id},
                )
            await db.rollback()
            # A mismatched historical catalog stays unresolved; never take a newer offer.
            invoice = await db.get(BillingInvoice, invoice_id)
            invoice.plan_snapshot = {
                **snapshot,
                "catalog_snapshot": {**catalog, "catalog_version": 999999},
            }
            subscription = await db.get(WorkspaceSubscription, PERSONAL_WORKSPACE_ID)
            subscription.application_version += 1
            await db.commit()
            assert (await backfill_subscription_pins(db, limit=100))["review_required"] == 1
            await db.commit()
            await db.refresh(subscription)
            assert subscription.pin_state == "legacy_pinned"
            assert subscription.pinned_plan_version_id is None
            assert (
                subscription.legacy_pinned_snapshot["invoice_snapshot"]["catalog_snapshot"][
                    "catalog_version"
                ]
                == 999999
            )
            # Expiration or a display state must not make preserved financial pins disposable.
            from pathlib import Path

            from alembic.migration import MigrationContext
            from alembic.operations import Operations
            from alembic.script import ScriptDirectory
            from sqlalchemy.exc import DBAPIError

            subscription.pin_state = "not_applicable"
            await db.commit()
            directory = (
                Path(__file__).resolve().parents[2] / "src/twobrain_rec_server/db/migrations"
            )
            migration = (
                ScriptDirectory(str(directory)).get_revision("0096_billing_version_pins").module
            )

            def downgrade(connection):
                with Operations.context(MigrationContext.configure(connection)):
                    migration.downgrade()

            with pytest.raises(DBAPIError, match="billing pin records exist"):
                async with db.begin_nested():
                    await (await db.connection()).run_sync(downgrade)

    finally:
        await engine.dispose()


def _capabilities():
    return {
        "processing_unlimited": True,
        "processing_seconds": 18000,
        "processing_window": "calendar_month_moscow",
        "storage_bytes": 4_000_000_000,
        "audio_archive": True,
        "audio_download": True,
        "content_export": True,
        "meeting_sharing": True,
        "ai_summary": True,
        "ai_outcomes": True,
        "export_formats": ["txt", "md"],
    }


@pytest.mark.asyncio
async def test_one_version_has_two_immutable_prices_and_typed_capabilities(
    postgres_seeded_database_url,
):
    from twobrain_rec_server.billing.catalog import CatalogNotApproved, validate_capabilities
    from twobrain_rec_server.db.models.billing import BillingPlan

    engine = create_async_engine(postgres_seeded_database_url)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with sessions() as db:
            plan = BillingPlan(id=uuid4(), code="synthetic_plus", display_name="Synthetic Plus")
            db.add(plan)
            await db.flush()
            version = BillingPlanVersion(
                id=uuid4(),
                plan_id=plan.id,
                plan_code=plan.code,
                version=1,
                status="draft",
                capability_schema_version=1,
                capabilities=_capabilities(),
                display_terms={
                    "name": "Synthetic Plus",
                    "description": "",
                    "audience": "admin",
                    "trial_days": 0,
                },
                cycle="none",
                currency="RUB",
                storage_bytes=4_000_000_000,
                processing_mode="unlimited",
                policy_snapshot={"offer_version": "synthetic-plus-v1"},
            )
            db.add(version)
            await db.flush()
            prices = [
                BillingPlanPrice(
                    id=uuid4(),
                    version_id=version.id,
                    cycle=cycle,
                    currency="RUB",
                    amount_minor=amount,
                )
                for cycle, amount in (("month", 123400), ("year", 1234000))
            ]
            db.add_all(prices)
            await db.flush()
            version.status = "published"
            version.enabled_for_checkout = True
            version.publication_revision = 1
            await db.flush()
            plan.current_version_id = version.id
            plan.sales_state = "open"
            await db.commit()
            month, year = [validate_plan_version(version, price=price) for price in prices]
            assert month.plan_version_id == year.plan_version_id == version.id
            assert month.amount_minor == 123400 and year.amount_minor == 1234000
            assert month.as_dict()["price_id"] != year.as_dict()["price_id"]
            assert month.capabilities == year.capabilities
            for invalid in (
                {**_capabilities(), "capture_hidden": True},
                {**_capabilities(), "storage_bytes": True},
                {**_capabilities(), "export_formats": ["executable"]},
            ):
                with pytest.raises(CatalogNotApproved):
                    validate_capabilities(invalid)
            version_id, price_id, plan_id = version.id, prices[0].id, plan.id
            for sql, params in (
                ("update billing_plan_prices set amount_minor=1 where id=:id", {"id": price_id}),
                (
                    "update billing_plan_versions set storage_bytes=1 where id=:id",
                    {"id": version_id},
                ),
                (
                    "update billing_plan_versions set status='draft' where id=:id",
                    {"id": version_id},
                ),
                ("update billing_plans set code='changed_code' where id=:id", {"id": plan_id}),
            ):
                with pytest.raises(Exception, match="immutable"):
                    await db.execute(text(sql), params)
                await db.rollback()
            # Closing sales preserves the subscriber's immutable, still-readable terms.
            await db.execute(
                text(
                    "update billing_plan_versions set enabled_for_checkout=false, status='retired' where id=:id"
                ),
                {"id": version_id},
            )
            await db.commit()
            version = await db.get(BillingPlanVersion, version_id, populate_existing=True)
            price = await db.get(BillingPlanPrice, price_id)
            with pytest.raises(CatalogNotApproved):
                validate_plan_version(version, price=price)
            assert (
                validate_plan_version(version, price=price, for_checkout=False).amount_minor
                == 123400
            )
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_backfill_operator_command_checks_real_identity_and_only_reports_counts(
    postgres_seeded_database_url, tmp_path
):
    import argparse
    import importlib.util
    from pathlib import Path

    import asyncpg
    from sqlalchemy.engine import make_url

    source = Path(__file__).resolve().parents[2] / "scripts/backfill_billing_catalog.py"
    spec = importlib.util.spec_from_file_location("billing_backfill_cli", source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    owner = await asyncpg.connect(postgres_seeded_database_url.replace("+asyncpg", ""))
    try:
        password = uuid4().hex
        quoted = await owner.fetchval("select quote_literal($1::text)", password)
        await owner.execute(f"alter role twobrain_rec_maintenance login password {quoted}")
        await owner.execute(
            "grant select,insert,update,delete on all tables in schema public to twobrain_rec_maintenance"
        )
        url = tmp_path / "synthetic-database-url"
        url.write_text(postgres_seeded_database_url)
        args = argparse.Namespace(
            database_url_file=str(url), execute=False, max_batches=1, batch_size=10
        )
        with pytest.raises(ValueError, match="роль"):
            await module.run(args)
        url.write_text(
            make_url(postgres_seeded_database_url)
            .set(username="twobrain_rec_maintenance", password=password)
            .render_as_string(hide_password=False)
        )
        dry = await module.run(args)
        assert set(dry) == {
            "processed",
            "pinned",
            "review_required",
            "not_applicable",
            "lag",
            "unresolved",
        }
        assert dry["processed"] == 0
        args.execute = True
        result = await module.run(args)
        assert result["lag"] == 0
        assert all(type(value) is int for value in result.values())
    finally:
        await owner.close()


@pytest.mark.asyncio
@pytest.mark.parametrize("failure_mode", ["crash", "consent_revoked"])
async def test_renewal_dispatch_claim_survives_process_loss(
    postgres_seeded_database_url, tmp_path, monkeypatch, failure_mode
):
    import asyncio

    from tests.unit.test_renewal_charge import _settings
    from twobrain_rec_server.billing.payment_methods import seal_provider_reference
    from twobrain_rec_server.billing.renewal_charge import charge_renewal_operation

    settings = _settings(tmp_path)
    now = datetime.now(UTC)
    engine = create_async_engine(postgres_seeded_database_url)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    operation_id = uuid4()
    calls = []

    class CrashAfterDispatch:
        async def __aenter__(self):
            return self

        async def __aexit__(self, *_args):
            return None

        async def create_payment(self, **kwargs):
            # A different connection must already see the claim before any network effect.
            async with sessions() as observer:
                persisted = await observer.get(BillingOperation, operation_id)
                assert persisted.state == "processing" and persisted.provider_id is None
            calls.append(kwargs["idempotence_key"])
            raise asyncio.CancelledError("synthetic process loss")

    monkeypatch.setattr(
        "twobrain_rec_server.billing.renewal_charge.YooKassaClient",
        lambda _settings: CrashAfterDispatch(),
    )
    try:
        async with sessions() as db:
            subscription = await db.get(WorkspaceSubscription, PERSONAL_WORKSPACE_ID)
            if subscription is None:
                subscription = WorkspaceSubscription(workspace_id=PERSONAL_WORKSPACE_ID)
                db.add(subscription)
            subscription.billing_owner_id = USER_ID
            subscription.plan_code = "personal"
            subscription.state = "personal"
            subscription.cycle = "month"
            subscription.paid_through = now
            subscription.recurring_allowed = True
            subscription.recurring_authority_version = 4
            await db.flush()
            await db.refresh(subscription)
            operation = BillingOperation(
                id=operation_id,
                workspace_id=PERSONAL_WORKSPACE_ID,
                kind="renewal",
                idempotency_key=f"synthetic:{operation_id}",
                state="scheduled",
                provider_key_expires_at=now + timedelta(hours=24),
                request_snapshot={
                    "plan_code": "personal",
                    "cycle": "month",
                    "billing_actor_user_id": str(USER_ID),
                    "recurring_authority_version": 4,
                    "schedule_version": subscription.schedule_version,
                    "paid_through_at": now.isoformat(),
                },
            )
            db.add(operation)
            await db.flush()
            db.add(
                BillingInvoice(
                    workspace_id=PERSONAL_WORKSPACE_ID,
                    operation_id=operation_id,
                    safe_number=f"SYNTHETIC-{operation_id}",
                    amount_minor=79000,
                    currency="RUB",
                    receipt_contact_snapshot="synthetic@example.invalid",
                )
            )
            db.add(
                BillingPaymentMethod(
                    workspace_id=PERSONAL_WORKSPACE_ID,
                    owner_user_id=USER_ID,
                    encrypted_provider_ref=seal_provider_reference(
                        "synthetic-method", settings.credential_encryption_key_file.read_bytes()
                    ),
                    key_version="billing-v1",
                    state="active",
                    is_default=True,
                    verified_at=now,
                )
            )
            await db.commit()
            if failure_mode == "consent_revoked":
                original_commit = db.commit
                changed = False

                async def revoke_after_claim():
                    nonlocal changed
                    await original_commit()
                    if not changed:
                        changed = True
                        async with sessions() as revoker:
                            await revoker.execute(
                                text("""update workspace_subscriptions
                                set recurring_allowed=false, recurring_authority_version=recurring_authority_version+1
                                where workspace_id=:id"""),
                                {"id": PERSONAL_WORKSPACE_ID},
                            )
                            await revoker.commit()

                monkeypatch.setattr(db, "commit", revoke_after_claim)
                result = await charge_renewal_operation(
                    db,
                    settings,
                    operation_id=operation_id,
                    workspace_id=PERSONAL_WORKSPACE_ID,
                    now=now,
                )
                assert result.status == "canceled" and calls == []
            else:
                with pytest.raises(asyncio.CancelledError):
                    await charge_renewal_operation(
                        db,
                        settings,
                        operation_id=operation_id,
                        workspace_id=PERSONAL_WORKSPACE_ID,
                        now=now,
                    )
                await db.rollback()
        async with sessions() as recovered:
            expected = "processing" if failure_mode == "crash" else "canceled"
            assert (await recovered.get(BillingOperation, operation_id)).state == expected
            result = await charge_renewal_operation(
                recovered,
                settings,
                operation_id=operation_id,
                workspace_id=PERSONAL_WORKSPACE_ID,
                now=now,
            )
            assert result.status == expected
            assert len(calls) == (1 if failure_mode == "crash" else 0)
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_renewal_wait_does_not_hold_subscription_before_workspace(postgres_seeded_database_url):
    import asyncio
    from contextlib import suppress

    from twobrain_rec_server.billing.renewal_charge import _lock_renewal_subscription
    from twobrain_rec_server.db.models import Workspace

    engine = create_async_engine(postgres_seeded_database_url)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    pending = None
    try:
        async with sessions() as holder:
            if await holder.get(WorkspaceSubscription, PERSONAL_WORKSPACE_ID) is None:
                holder.add(WorkspaceSubscription(workspace_id=PERSONAL_WORKSPACE_ID))
                await holder.commit()
            # Another product operation owns the workspace while a renewal arrives.
            await holder.scalar(select(Workspace.id).where(
                Workspace.id == PERSONAL_WORKSPACE_ID,
            ).with_for_update())
            pid_ready = asyncio.get_running_loop().create_future()
            async def renewal():
                async with sessions() as db:
                    pid_ready.set_result(await db.scalar(text("select pg_backend_pid()")))
                    workspace, subscription = await _lock_renewal_subscription(db, PERSONAL_WORKSPACE_ID)
                    assert workspace is not None and subscription is not None
                    await db.commit()
            pending = asyncio.create_task(renewal())
            pid = await pid_ready
            async with sessions() as observer:
                async def wait_until_blocked():
                    while await observer.scalar(text(
                        "select wait_event_type from pg_stat_activity where pid=:pid"
                    ), {"pid":pid}) != "Lock":
                        await asyncio.sleep(0.01)
                await asyncio.wait_for(wait_until_blocked(), timeout=5)
                # A reversed lock order would already own this row and fail NOWAIT.
                assert await observer.scalar(select(WorkspaceSubscription.workspace_id).where(
                    WorkspaceSubscription.workspace_id == PERSONAL_WORKSPACE_ID,
                ).with_for_update(nowait=True)) == PERSONAL_WORKSPACE_ID
                await observer.rollback()
            await holder.commit()
            await asyncio.wait_for(pending, timeout=5)
    finally:
        if pending is not None and not pending.done():
            pending.cancel()
            with suppress(asyncio.CancelledError):
                await pending
        await engine.dispose()
