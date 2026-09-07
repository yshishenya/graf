"""Non-monetary assignments cannot fabricate payments or erase consumption."""

from datetime import UTC, datetime, timedelta
from uuid import uuid4

import pytest
from sqlalchemy import func, select, text
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from tests.conftest import PERSONAL_WORKSPACE_ID
from twobrain_rec_server.billing.admin_grants import (
    add_calendar_days,
    create_adjustment,
    resolve_adjustments,
    revoke_adjustment,
)
from twobrain_rec_server.db.models.billing import (
    BillingAccessAdjustment,
    BillingAccessRevocation,
    BillingInvoice,
)

pytestmark = pytest.mark.strict_rls


@pytest.mark.asyncio
async def test_access_sources_are_idempotent_revocable_and_never_paid(postgres_seeded_database_url):
    engine = create_async_engine(postgres_seeded_database_url)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    now = datetime.now(UTC)
    base = {
        "storage_bytes": 250000000,
        "processing_seconds": 18000,
        "processing_unlimited": False,
        "audio_archive": True,
        "audio_download": False,
        "content_export": True,
        "meeting_sharing": True,
        "ai_summary": True,
        "ai_outcomes": True,
        "processing_window": "calendar_month_moscow",
        "export_formats": ["txt"],
    }
    try:
        async with sessions() as db:
            invoices = await db.scalar(select(func.count()).select_from(BillingInvoice))
            args = dict(
                workspace_id=PERSONAL_WORKSPACE_ID,
                source_kind="migration",
                source_ref=f"synthetic:{uuid4()}",
                reason="Synthetic entitlement check",
                starts_at=now,
                ends_at=now + timedelta(days=2),
                kind="extra_quota",
                feature_key="processing_seconds",
                value=300,
                unit="seconds",
            )
            first = await create_adjustment(db, **args)
            await db.commit()
            assert (await create_adjustment(db, **args)).id == first.id
            with pytest.raises(ValueError, match="idempotency"):
                await create_adjustment(db, **{**args, "value": 301})
            await db.rollback()
            for kind, value in (("allow", True), ("deny", False)):
                await create_adjustment(
                    db,
                    **{
                        **args,
                        "source_ref": f"synthetic:{uuid4()}",
                        "kind": kind,
                        "feature_key": "audio_download",
                        "value": value,
                        "unit": "boolean",
                    },
                )
            result = await resolve_adjustments(
                db,
                workspace_id=PERSONAL_WORKSPACE_ID,
                subject_user_id=None,
                base_capabilities=base,
                now=now,
            )
            assert result.capabilities["processing_seconds"] == 18000
            assert sum(source.value for source in result.extra_quotas) == 300
            assert result.capabilities["audio_download"] is False
            assert len(result.applied_ids) == 3
            assert await db.scalar(select(func.count()).select_from(BillingInvoice)) == invoices
            await db.commit()
            first = await db.scalar(
                select(BillingAccessAdjustment).where(
                    BillingAccessAdjustment.source_ref == args["source_ref"]
                )
            )
            revoked = await revoke_adjustment(
                db,
                workspace_id=PERSONAL_WORKSPACE_ID,
                adjustment_id=first.id,
                source_kind="migration",
                source_ref="synthetic:revoke",
                reason="Synthetic explicit revocation",
            )
            await db.commit()
            assert (
                await revoke_adjustment(
                    db,
                    workspace_id=PERSONAL_WORKSPACE_ID,
                    adjustment_id=first.id,
                    source_kind="migration",
                    source_ref="synthetic:revoke",
                    reason="Synthetic explicit revocation",
                )
            ).id == revoked.id
            result = await resolve_adjustments(
                db,
                workspace_id=PERSONAL_WORKSPACE_ID,
                subject_user_id=None,
                base_capabilities=base,
                now=now,
            )
            assert result.extra_quotas == ()
            assert await db.scalar(select(func.count()).select_from(BillingAccessAdjustment)) == 3
            assert await db.scalar(select(func.count()).select_from(BillingAccessRevocation)) == 1
            with pytest.raises(Exception, match="immutable"):
                await db.execute(
                    text("delete from billing_access_adjustments where id=:id"), {"id": first.id}
                )
            await db.rollback()
    finally:
        await engine.dispose()


def test_calendar_gift_days_follow_pinned_timezone_across_dst():
    before = datetime(2026, 3, 28, 11, tzinfo=UTC)
    after = add_calendar_days(before, days=1, timezone="Europe/Berlin")
    assert after == datetime(2026, 3, 29, 10, tzinfo=UTC)
    autumn = add_calendar_days(datetime(2026, 10, 24, 10, tzinfo=UTC), days=1, timezone="Europe/Berlin")
    assert autumn == datetime(2026, 10, 25, 11, tzinfo=UTC)
    with pytest.raises(ValueError):
        add_calendar_days(before, days=True, timezone="UTC")


@pytest.mark.asyncio
async def test_concurrent_exact_limits_conflict_and_never_override_hard_deny(
    postgres_seeded_database_url,
):
    import asyncio

    from sqlalchemy.exc import DBAPIError

    from tests.integration.test_system_admin_billing import _capabilities
    from twobrain_rec_server.billing.catalog import validate_capabilities
    from twobrain_rec_server.db.models.billing import FreeUsageWindow

    engine = create_async_engine(postgres_seeded_database_url)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    now = datetime.now(UTC)

    async def attempt(value):
        async with sessions() as db:
            try:
                row = await create_adjustment(
                    db,
                    workspace_id=PERSONAL_WORKSPACE_ID,
                    kind="exact_limit",
                    starts_at=now,
                    ends_at=now + timedelta(days=1),
                    source_kind="migration",
                    source_ref=f"synthetic:{value}",
                    reason="Synthetic concurrent correction",
                    feature_key="processing_seconds",
                    value=value,
                    unit="seconds",
                )
                await db.commit()
                return row.id
            except DBAPIError:
                await db.rollback()
                return None

    try:
        async with sessions() as db:
            window = FreeUsageWindow(
                workspace_id=PERSONAL_WORKSPACE_ID,
                window_start=now,
                window_end=now + timedelta(days=30),
                committed_seconds=777,
                reserved_seconds=111,
            )
            db.add(window)
            await db.commit()
            window_id = window.id
        outcomes = await asyncio.gather(attempt(900), attempt(1200))
        assert sum(value is not None for value in outcomes) == 1
        async with sessions() as db:
            base = _capabilities()
            for seconds, days in ((400, 2), (300, 1)):
                await create_adjustment(
                    db,
                    workspace_id=PERSONAL_WORKSPACE_ID,
                    kind="extra_quota",
                    starts_at=now,
                    ends_at=now + timedelta(days=days),
                    source_kind="migration",
                    source_ref=f"synthetic:extra:{seconds}",
                    reason="Synthetic additional quota",
                    feature_key="processing_seconds",
                    value=seconds,
                    unit="seconds",
                )
            await db.commit()
            result = await resolve_adjustments(
                db,
                workspace_id=PERSONAL_WORKSPACE_ID,
                subject_user_id=None,
                base_capabilities=base,
                now=now,
            )
            assert result.capabilities["processing_unlimited"] is False
            assert result.capabilities["processing_seconds"] in (900, 1200)
            assert [source.value for source in result.extra_quotas] == [300, 400]
            blocked = await resolve_adjustments(
                db,
                workspace_id=PERSONAL_WORKSPACE_ID,
                subject_user_id=None,
                base_capabilities=base,
                now=now,
                hard_denies=frozenset({"processing_seconds", "content_export"}),
            )
            assert blocked.capabilities["processing_seconds"] == 0
            assert blocked.capabilities["processing_unlimited"] is False
            assert blocked.extra_quotas == ()
            assert blocked.capabilities["content_export"] is False
            assert blocked.capabilities["export_formats"] == []
            expired = await resolve_adjustments(
                db,
                workspace_id=PERSONAL_WORKSPACE_ID,
                subject_user_id=None,
                base_capabilities=base,
                now=now + timedelta(days=3),
            )
            assert expired.capabilities == validate_capabilities(base) and expired.applied_ids == ()
            window = await db.get(FreeUsageWindow, window_id)
            assert (window.committed_seconds, window.reserved_seconds) == (777, 111)
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_ordinary_account_cannot_mint_assignments_or_read_another_subject(
    postgres_seeded_database_url,
):
    from sqlalchemy.exc import DBAPIError

    from tests.conftest import USER_ID
    from tests.integration.test_rls_postgres_policies import _exact_app_role_engine
    from twobrain_rec_server.db.models.identity import Workspace
    from twobrain_rec_server.db.tenant_context import (
        TenantDatabaseContext,
        apply_tenant_context_to_connection,
    )

    owner = create_async_engine(postgres_seeded_database_url)
    now = datetime.now(UTC)
    try:
        async with async_sessionmaker(owner)() as db:
            organization = (await db.get(Workspace, PERSONAL_WORKSPACE_ID)).organization_id
            row = await create_adjustment(
                db,
                workspace_id=PERSONAL_WORKSPACE_ID,
                subject_user_id=USER_ID,
                kind="allow",
                feature_key="audio_download",
                value=True,
                unit="boolean",
                starts_at=now,
                ends_at=now + timedelta(days=1),
                source_kind="migration",
                source_ref=f"synthetic:{uuid4()}",
                reason="Synthetic subject permission",
            )
            row_id = row.id
            await db.commit()
        async with (
            _exact_app_role_engine(postgres_seeded_database_url) as app,
            app.connect() as conn,
        ):
            context = TenantDatabaseContext(
                organization_id=organization, workspace_id=PERSONAL_WORKSPACE_ID, user_id=USER_ID
            )
            await apply_tenant_context_to_connection(conn, context)
            assert await conn.scalar(text("select id from billing_access_adjustments")) == row_id
            with pytest.raises(DBAPIError):
                async with conn.begin_nested():
                    await conn.execute(
                        text("""insert into billing_access_adjustments
                        (workspace_id,kind,feature_key,value,unit,starts_at,ends_at,source_kind,source_ref,reason)
                        values(:workspace,'extra_quota','processing_seconds','900','seconds',now(),now()+interval '1 day',
                        'migration','synthetic:forged','Synthetic forbidden assignment')"""),
                        {"workspace": PERSONAL_WORKSPACE_ID},
                    )
            await apply_tenant_context_to_connection(
                conn,
                TenantDatabaseContext(
                    organization_id=organization,
                    workspace_id=PERSONAL_WORKSPACE_ID,
                    user_id=uuid4(),
                ),
            )
            assert await conn.scalar(text("select count(*) from billing_access_adjustments")) == 0
    finally:
        await owner.dispose()


@pytest.mark.asyncio
async def test_gift_interval_changes_access_without_touching_paid_history(
    postgres_seeded_database_url,
):
    from sqlalchemy.exc import DBAPIError

    from tests.integration.test_system_admin_billing import _capabilities
    from twobrain_rec_server.billing.catalog import validate_capabilities
    from twobrain_rec_server.db.models.billing import (
        BillingPlan,
        BillingPlanVersion,
        WorkspaceSubscription,
    )

    engine = create_async_engine(postgres_seeded_database_url)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    now = datetime.now(UTC)
    base = _capabilities()
    base.update(storage_bytes=250000000, processing_unlimited=False)
    try:
        async with sessions() as db:
            plan = BillingPlan(id=uuid4(), code="synthetic_gift", display_name="Synthetic gift")
            db.add(plan)
            await db.flush()
            version = BillingPlanVersion(
                id=uuid4(),
                plan_id=plan.id,
                plan_code=plan.code,
                version=1,
                status="published",
                capability_schema_version=1,
                capabilities=_capabilities(),
                cycle="none",
                storage_bytes=4000000000,
                processing_mode="unlimited",
                policy_snapshot={"offer_version": "synthetic-gift-v1"},
                display_terms={
                    "name": "Synthetic gift",
                    "description": "",
                    "audience": "admin",
                    "trial_days": 0,
                },
            )
            db.add(version)
            await db.flush()
            subscription = await db.get(WorkspaceSubscription, PERSONAL_WORKSPACE_ID)
            if subscription is None:
                subscription = WorkspaceSubscription(workspace_id=PERSONAL_WORKSPACE_ID)
                db.add(subscription)
            subscription.paid_through = now + timedelta(days=7)
            await db.commit()
            before = subscription.paid_through
            paid_count = await db.scalar(select(func.count()).select_from(BillingInvoice))
            params = dict(
                workspace_id=PERSONAL_WORKSPACE_ID,
                kind="plan_interval",
                plan_version_id=version.id,
                plan_mode="append",
                starts_at=now,
                ends_at=now + timedelta(days=2),
                source_kind="migration",
                source_ref=f"synthetic:gift:{uuid4()}",
                reason="Synthetic plan compensation",
            )
            with pytest.raises(DBAPIError, match="append overlaps"):
                async with db.begin_nested():
                    await create_adjustment(db, **params)
            params["plan_mode"] = "overlay"
            gift = await create_adjustment(db, **params)
            await db.commit()
            active = await resolve_adjustments(
                db,
                workspace_id=PERSONAL_WORKSPACE_ID,
                subject_user_id=None,
                base_capabilities=base,
                now=now,
            )
            assert active.plan_version_id == version.id
            assert active.capabilities["storage_bytes"] == 4000000000
            assert active.capabilities["processing_unlimited"] is True
            expired = await resolve_adjustments(
                db,
                workspace_id=PERSONAL_WORKSPACE_ID,
                subject_user_id=None,
                base_capabilities=base,
                now=params["ends_at"],
            )
            assert expired.capabilities == validate_capabilities(base)
            assert expired.plan_version_id is None
            await revoke_adjustment(
                db,
                workspace_id=PERSONAL_WORKSPACE_ID,
                adjustment_id=gift.id,
                source_kind="migration",
                source_ref="synthetic:gift:revoked",
                reason="Synthetic compensation revocation",
            )
            await db.commit()
            revoked = await resolve_adjustments(
                db,
                workspace_id=PERSONAL_WORKSPACE_ID,
                subject_user_id=None,
                base_capabilities=base,
                now=now,
            )
            assert revoked.capabilities == validate_capabilities(base)
            await db.refresh(subscription)
            assert subscription.paid_through == before
            assert await db.scalar(select(func.count()).select_from(BillingInvoice)) == paid_count
    finally:
        await engine.dispose()
