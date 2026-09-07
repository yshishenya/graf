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


@pytest.mark.parametrize("source,role", [("paid", "owner"), ("gift", "owner"), ("gift", "member")])
def test_profile_uses_catalog_assignments_and_hides_member_usage(client, source, role):
    from tests.fakes.auth_contexts import DEVICE_ID, USER_ID, WORKSPACE_ID
    from tests.integration.test_account_lifecycle import (
        _issue_web_session,
        _seed_personal_workspace,
    )
    from tests.integration.test_system_admin_billing import _managed_payment
    from twobrain_rec_server.billing.entitlements import grant_confirmed_payment
    from twobrain_rec_server.billing.usage import (
        SourceRange,
        commit_free_usage_ranges,
        reserve_processing_usage,
    )
    from twobrain_rec_server.db.models import WorkspaceMembership

    now = datetime.now(UTC)

    async def seed():
        workspace, device = await _seed_personal_workspace(client)
        if role == "member":
            workspace, device = WORKSPACE_ID, DEVICE_ID
        async with client.app_state["sessionmaker"]() as db:
            version, _, operation, invoice = await _managed_payment(db)
            if source == "paid":
                assert await grant_confirmed_payment(db, workspace_id=workspace,
                    provider_payment_id=operation.provider_id, amount_minor=invoice.amount_minor,
                    currency="RUB", paid_at=now) == "granted"
            else:
                await create_adjustment(db, workspace_id=workspace, kind="plan_interval",
                    plan_version_id=version.id, plan_mode="overlay", starts_at=now-timedelta(seconds=1),
                    ends_at=now+timedelta(days=2), source_kind="migration",
                    source_ref=f"synthetic:{uuid4()}", reason="Synthetic profile gift")
            for feature,kind,value,unit in (("processing_seconds","extra_quota",6000,"seconds"),
                ("storage_bytes","extra_quota",1000000000,"bytes"),
                ("audio_download","deny",False,"boolean")):
                await create_adjustment(db, workspace_id=workspace, kind=kind, feature_key=feature,
                    value=value, unit=unit, starts_at=now-timedelta(seconds=1), ends_at=now+timedelta(days=2),
                    source_kind="migration", source_ref=f"synthetic:{uuid4()}", reason="Synthetic profile assignment")
            reservation = await reserve_processing_usage(db, workspace_id=workspace,
                subject_user_id=USER_ID, reservation_key="synthetic:profile", declared_seconds=120,
                now=now, expires_at=now+timedelta(hours=1))
            await commit_free_usage_ranges(db, reservation_id=reservation.id,
                ranges=[SourceRange("synthetic:profile",0,60)])
            if role == "member":
                membership = await db.get(WorkspaceMembership, {"workspace_id":workspace,"user_id":USER_ID})
                membership.role = "member"
            await db.commit()
        token, _ = await _issue_web_session(client,user_id=USER_ID,workspace_id=workspace,device_id=device)
        return workspace, token

    workspace, token = client.portal.call(seed)
    headers = {"X-Workspace-Id":str(workspace), "Authorization":f"Bearer {token}"}
    response = client.get("/api/v1/auth/me", headers=headers)
    assert response.status_code == 200, response.text
    billing = response.json()["billing"]
    assert billing["plan_code"] == "research_plus" and billing["access_source"] == source
    assert billing["plan_label"] == "Synthetic Research"
    assert billing["processing_unlimited"] is False
    assert billing["commercial_capabilities"]["audio_download"] is False
    assert billing["commercial_capabilities"]["export_formats"] == ["md","txt"]
    assert "storage_bytes" not in billing["commercial_capabilities"]
    if role == "member":
        for key in ("storage_used_bytes","storage_capacity_bytes","processing_used_seconds",
            "processing_reserved_seconds","processing_available_seconds","processing_window_start",
            "processing_window_end","access_until","paid_through","bonus_until","renewal_resolution","usage_freshness"):
            assert billing[key] is None, key
        assert billing["state"] == "active"
    else:
        assert billing["storage_capacity_bytes"] == 5000000000
        assert (billing["processing_used_seconds"],billing["processing_reserved_seconds"],
            billing["processing_available_seconds"]) == (60,60,29880)
        assert billing["usage_freshness"] == "fresh" and billing["access_until"] is not None
        assert bool(billing["paid_through"]) == (source == "paid")

    from twobrain_rec_server.auth.dependencies import AUTH_SESSION_COOKIE_NAME

    client.cookies.set(AUTH_SESSION_COOKIE_NAME, token)
    overview = client.get("/billing", headers=headers)
    assert overview.status_code == 200, overview.text
    assert "Synthetic Research" in overview.text
    assert "Без лимита по минутам и встречам" not in overview.text
    if role == "owner":
        assert "498 мин 0 сек" in overview.text
        storage_page = client.get("/billing/storage", headers=headers)
        assert storage_page.status_code == 200 and "5 GB" in storage_page.text
        assert "с учётом тарифа и индивидуальных назначений" in storage_page.text
        assert "250 MB" not in storage_page.text
        subscription_page = client.get("/billing/subscription", headers=headers)
        assert subscription_page.status_code == 200, subscription_page.text
        assert "Synthetic Research" in subscription_page.text
        if source == "paid":
            assert "1 234 ₽" in subscription_page.text
        else:
            assert "назначенный доступ" in overview.text
    else:
        assert "498 мин 0 сек" not in overview.text
        storage_page = client.get("/billing/storage", headers=headers, follow_redirects=False)
        assert storage_page.status_code == 303 and "owner_only" in storage_page.headers["location"]

    async def revoke():
        async with client.app_state["sessionmaker"]() as db:
            rows = list(await db.scalars(select(BillingAccessAdjustment).where(
                BillingAccessAdjustment.workspace_id == workspace)))
            for row in rows:
                await revoke_adjustment(db,workspace_id=workspace,adjustment_id=row.id,
                    source_kind="migration",source_ref=f"synthetic:{uuid4()}",reason="Synthetic profile revoke")
            await db.commit()
    client.portal.call(revoke)
    refreshed = client.get("/api/v1/auth/me",headers=headers).json()["billing"]
    assert refreshed["plan_code"] == ("research_plus" if source == "paid" else "free")
    assert refreshed["commercial_capabilities"]["audio_download"] is True
    if role == "owner":
        assert refreshed["processing_available_seconds"] == (23880 if source == "paid" else 17880)
    if source == "paid":
        async def update_subscription(*, missing_pin=False):
            from twobrain_rec_server.db.models import WorkspaceSubscription

            async with client.app_state["sessionmaker"]() as db:
                subscription = await db.get(WorkspaceSubscription, workspace)
                subscription.paid_through = now+timedelta(days=1) if missing_pin else now-timedelta(seconds=1)
                if missing_pin:
                    subscription.pinned_price_id = None
                    subscription.pinned_plan_version_id = None
                    subscription.pin_state = "pending"
                await db.commit()
        client.portal.call(update_subscription)
        expired = client.get("/api/v1/auth/me", headers=headers).json()["billing"]
        assert expired["plan_code"] == "free" and expired["paid_through"] is None
        assert expired["processing_available_seconds"] == 17880
        client.portal.call(lambda: update_subscription(missing_pin=True))
        unavailable = client.get("/api/v1/auth/me", headers=headers)
        assert unavailable.status_code == 503
        assert unavailable.json()["code"] == "billing_entitlements_unavailable"
        for path in ("/billing", "/billing/usage", "/billing/subscription", "/billing/storage"):
            unavailable_page = client.get(path, headers=headers)
            assert unavailable_page.status_code == 503
            assert "Условия тарифа временно недоступны" in unavailable_page.text
            assert unavailable_page.headers["cache-control"] == "private, no-store"



def test_usage_page_shows_assigned_capacity_and_source_balances(client):
    from tests.fakes.auth_contexts import USER_ID
    from tests.integration.test_account_lifecycle import (
        _bind_web_session,
        _issue_web_session,
        _seed_personal_workspace,
    )

    async def seed():
        workspace, device = await _seed_personal_workspace(client)
        token, session_id = await _issue_web_session(client,user_id=USER_ID,workspace_id=workspace,device_id=device)
        async with client.app_state["sessionmaker"]() as db:
            for key, value, unit in (("processing_seconds",6000,"seconds"),("storage_bytes",1000000000,"bytes")):
                await create_adjustment(db,workspace_id=workspace,kind="extra_quota",feature_key=key,
                    value=value,unit=unit,starts_at=datetime.now(UTC)-timedelta(days=1),
                    ends_at=datetime.now(UTC)+timedelta(days=1),source_kind="migration",
                    source_ref=f"synthetic:{uuid4()}",reason="Synthetic billing page")
            await db.commit()
        return token, session_id
    token, session_id = client.portal.call(seed)
    _bind_web_session(client,token=token,session_id=session_id)
    response = client.get("/billing/usage")
    assert response.status_code == 200
    assert "400 мин 0 сек" in response.text and "100 мин 0 сек" in response.text
    assert "Дополнительная квота 1" in response.text
    assert "1,25 GB" in response.text


@pytest.mark.asyncio
async def test_usage_projection_shares_admission_balances_without_resetting_sources(postgres_seeded_database_url):
    from twobrain_rec_server.billing.entitlements import resolve_entitlements
    from twobrain_rec_server.billing.usage import (
        SourceRange,
        commit_free_usage_ranges,
        moscow_window_for,
        processing_usage_projection,
        reserve_processing_usage,
    )
    from twobrain_rec_server.db.models import FreeUsageWindow

    engine = create_async_engine(postgres_seeded_database_url)
    _, end = moscow_window_for(datetime.now(UTC))
    now = end-timedelta(days=1)
    try:
        async with async_sessionmaker(engine, expire_on_commit=False)() as db:
            gift = await create_adjustment(db, workspace_id=PERSONAL_WORKSPACE_ID,
                kind="extra_quota", feature_key="processing_seconds", value=6000, unit="seconds",
                starts_at=now, ends_at=end+timedelta(days=3), source_kind="migration",
                source_ref=f"synthetic:{uuid4()}", reason="Synthetic usage projection")
            reservation = await reserve_processing_usage(db, workspace_id=PERSONAL_WORKSPACE_ID,
                reservation_key="synthetic:usage-projection", declared_seconds=20000, now=now,
                expires_at=now+timedelta(minutes=10))
            assert await commit_free_usage_ranges(db, reservation_id=reservation.id,
                ranges=[SourceRange("synthetic:projection",0,19000)]) == 19000
            await db.commit()
            async def view(at):
                access = await resolve_entitlements(db, workspace_id=PERSONAL_WORKSPACE_ID,
                    subject_user_id=None, now=at)
                return await processing_usage_projection(db, workspace_id=PERSONAL_WORKSPACE_ID,
                    now=at, access=access)
            current = await view(now)
            assert (current.used,current.reserved,current.limit,current.available)==(19000,1000,24000,4000)
            assert (current.sources[0].used,current.sources[0].reserved)==(18000,0)
            assert (current.sources[1].source_id,current.sources[1].used,current.sources[1].reserved)==(gift.id,1000,1000)
            expired = await view(now+timedelta(minutes=11))
            assert (expired.used,expired.reserved,expired.available)==(19000,0,5000)
            # A read does not release/renew the persisted reservation or reset counters.
            window = await db.get(FreeUsageWindow,reservation.window_id)
            assert window.committed_seconds == 19000 and reservation.state == "active"
            next_month = await view(end+timedelta(seconds=1))
            assert (next_month.used,next_month.reserved,next_month.available)==(0,0,23000)
            assert next_month.sources[1].used == 1000
            await revoke_adjustment(db,workspace_id=PERSONAL_WORKSPACE_ID,adjustment_id=gift.id,
                source_kind="migration",source_ref=f"synthetic:{uuid4()}",reason="Synthetic revoke")
            revoked = await view(now+timedelta(minutes=11))
            assert revoked.limit == 18000 and revoked.available == 0 and len(revoked.sources) == 1
    finally:
        await engine.dispose()


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
            from sqlalchemy.ext.asyncio import AsyncSession

            from twobrain_rec_server.billing.entitlements import resolve_entitlements
            from twobrain_rec_server.billing.usage import reserve_processing_usage

            async with AsyncSession(bind=conn) as session:
                access = await resolve_entitlements(session, workspace_id=PERSONAL_WORKSPACE_ID,
                    subject_user_id=USER_ID, now=now)
                assert row_id in access.applied_ids
                await reserve_processing_usage(session, workspace_id=PERSONAL_WORKSPACE_ID,
                    subject_user_id=USER_ID, reservation_key="synthetic:actual-role", declared_seconds=60, now=now)
                await session.flush()

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


@pytest.mark.asyncio
async def test_processing_allocates_extra_once_and_honors_expired_source(postgres_seeded_database_url):
    from twobrain_rec_server.billing.usage import (
        QuotaExceeded,
        SourceRange,
        commit_free_usage_ranges,
        reserve_processing_usage,
    )
    from twobrain_rec_server.db.models.billing import FreeUsageWindow

    engine = create_async_engine(postgres_seeded_database_url)
    now = datetime.now(UTC)
    try:
        async with async_sessionmaker(engine, expire_on_commit=False)() as db:
            gift = await create_adjustment(
                db, workspace_id=PERSONAL_WORKSPACE_ID, kind="extra_quota",
                feature_key="processing_seconds", value=6000, unit="seconds",
                starts_at=now-timedelta(days=1), ends_at=now+timedelta(seconds=1),
                source_kind="migration", source_ref=f"synthetic:quota:{uuid4()}",
                reason="Synthetic processing compensation",
            )
            first = await reserve_processing_usage(
                db, workspace_id=PERSONAL_WORKSPACE_ID, reservation_key="synthetic:24k",
                declared_seconds=24000, now=now,
            )
            await db.commit()
            with pytest.raises(QuotaExceeded):
                await reserve_processing_usage(
                    db, workspace_id=PERSONAL_WORKSPACE_ID, reservation_key="synthetic:over",
                    declared_seconds=1, now=now,
                )
            # Source expires/revokes, while the accepted reservation is still valid.
            await revoke_adjustment(
                db, workspace_id=PERSONAL_WORKSPACE_ID, adjustment_id=gift.id,
                source_kind="migration", source_ref=f"synthetic:revoke:{uuid4()}",
                reason="Synthetic compensation revoked",
            )
            replay = await reserve_processing_usage(
                db, workspace_id=PERSONAL_WORKSPACE_ID, reservation_key="synthetic:24k",
                declared_seconds=24000, now=now+timedelta(seconds=2),
            )
            assert replay.id == first.id
            assert await commit_free_usage_ranges(
                db, reservation_id=first.id, ranges=[SourceRange("synthetic:source",0,24000)]
            ) == 24000
            await db.commit()
            window = await db.get(FreeUsageWindow, first.window_id)
            assert (window.committed_seconds,window.reserved_seconds)==(24000,0)
            with pytest.raises(QuotaExceeded):
                await reserve_processing_usage(
                    db, workspace_id=PERSONAL_WORKSPACE_ID, reservation_key="synthetic:over-expired",
                    declared_seconds=1, now=now+timedelta(seconds=2),
                )
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_processing_measures_unlimited_and_preserves_usage_on_limit_change(postgres_seeded_database_url):
    from twobrain_rec_server.billing.usage import (
        QuotaExceeded,
        SourceRange,
        commit_free_usage_ranges,
        reserve_processing_usage,
    )
    from twobrain_rec_server.db.models.billing import WorkspaceSubscription

    engine = create_async_engine(postgres_seeded_database_url)
    now = datetime.now(UTC)
    try:
        async with async_sessionmaker(engine, expire_on_commit=False)() as db:
            subscription = await db.get(WorkspaceSubscription, PERSONAL_WORKSPACE_ID)
            if subscription is None:
                subscription=WorkspaceSubscription(workspace_id=PERSONAL_WORKSPACE_ID)
                db.add(subscription)
            subscription.plan_code="personal"
            subscription.state="personal"
            subscription.paid_through=now+timedelta(days=1)
            await db.flush()
            first = await reserve_processing_usage(
                db, workspace_id=PERSONAL_WORKSPACE_ID, reservation_key="synthetic:unlimited",
                declared_seconds=20000, now=now,
            )
            assert await commit_free_usage_ranges(
                db,reservation_id=first.id,ranges=[SourceRange("synthetic:paid",0,20000)]
            ) == 20000
            # Switching to a finite limit never resets already measured seconds.
            await create_adjustment(
                db, workspace_id=PERSONAL_WORKSPACE_ID,kind="exact_limit",
                feature_key="processing_seconds",value=21000,unit="seconds",
                starts_at=now,ends_at=now+timedelta(days=2),source_kind="migration",
                source_ref=f"synthetic:limit:{uuid4()}",reason="Synthetic processing limit",
            )
            await reserve_processing_usage(
                db,workspace_id=PERSONAL_WORKSPACE_ID,reservation_key="synthetic:remaining",
                declared_seconds=1000,now=now,
            )
            with pytest.raises(QuotaExceeded):
                await reserve_processing_usage(
                    db,workspace_id=PERSONAL_WORKSPACE_ID,reservation_key="synthetic:exhausted",
                    declared_seconds=1,now=now,
                )
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_extra_allocation_order_release_and_concurrent_source_dedup(postgres_seeded_database_url):
    import asyncio

    from twobrain_rec_server.billing.usage import (
        SourceRange,
        commit_free_usage_ranges,
        release_free_usage,
        reserve_processing_usage,
    )
    from twobrain_rec_server.db.models.billing import UsageQuotaAllocation

    engine = create_async_engine(postgres_seeded_database_url)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    now = datetime.now(UTC)
    try:
        async with sessions() as db:
            args = dict(
                workspace_id=PERSONAL_WORKSPACE_ID,feature_key="processing_seconds",unit="seconds",
                starts_at=now,source_kind="migration",reason="Synthetic quota allocation order",
            )
            await create_adjustment(db,**args,kind="exact_limit",value=0,
                ends_at=now+timedelta(days=3),source_ref=f"synthetic:{uuid4()}")
            early = await create_adjustment(db,**args,kind="extra_quota",value=300,
                ends_at=now+timedelta(days=1),source_ref=f"synthetic:{uuid4()}")
            late = await create_adjustment(db,**args,kind="extra_quota",value=300,
                ends_at=now+timedelta(days=2),source_ref=f"synthetic:{uuid4()}")
            first = await reserve_processing_usage(db,workspace_id=PERSONAL_WORKSPACE_ID,
                reservation_key="synthetic:partial",declared_seconds=450,now=now)
            assert await commit_free_usage_ranges(db,reservation_id=first.id,
                ranges=[SourceRange("synthetic:partial-source",0,350)])==350
            allocations = {row.adjustment_id: row.committed_seconds for row in await db.scalars(
                select(UsageQuotaAllocation).where(UsageQuotaAllocation.reservation_id==first.id)
            )}
            assert allocations=={early.id:300,late.id:50}
            assert await release_free_usage(db,reservation_id=first.id)
            # Only the unused 100 seconds are reacquired; prior consumption survives release.
            replay = await reserve_processing_usage(db,workspace_id=PERSONAL_WORKSPACE_ID,
                reservation_key="synthetic:partial",declared_seconds=450,now=now)
            assert replay.id==first.id
            second = await reserve_processing_usage(db,workspace_id=PERSONAL_WORKSPACE_ID,
                reservation_key="synthetic:duplicate",declared_seconds=100,now=now)
            await db.commit()
        async def consume(reservation_id):
            async with sessions() as db:
                value = await commit_free_usage_ranges(db,reservation_id=reservation_id,
                    ranges=[SourceRange("synthetic:concurrent-source",0,100)])
                await db.commit()
                return value
        assert sorted(await asyncio.gather(consume(first.id),consume(second.id)))==[0,100]
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_concurrent_processing_admission_cannot_overspend(postgres_seeded_database_url):
    import asyncio

    from twobrain_rec_server.billing.usage import QuotaExceeded, reserve_processing_usage

    engine = create_async_engine(postgres_seeded_database_url)
    sessions = async_sessionmaker(engine, expire_on_commit=False)
    now = datetime.now(UTC)
    try:
        async def admit(key):
            async with sessions() as db:
                try:
                    await reserve_processing_usage(db,workspace_id=PERSONAL_WORKSPACE_ID,
                        reservation_key=key,declared_seconds=15000,now=now)
                    await db.commit()
                    return True
                except QuotaExceeded:
                    await db.rollback()
                    return False
        assert sorted(await asyncio.gather(admit("synthetic:first"),admit("synthetic:second")))==[False,True]
    finally:
        await engine.dispose()


@pytest.mark.asyncio
async def test_expired_hold_cleanup_preserves_other_live_reservations(postgres_seeded_database_url):
    from twobrain_rec_server.billing.usage import (
        release_expired_free_usage,
        reserve_processing_usage,
    )
    from twobrain_rec_server.db.models.billing import FreeUsageWindow

    engine = create_async_engine(postgres_seeded_database_url)
    now = datetime.now(UTC)
    try:
        async with async_sessionmaker(engine, expire_on_commit=False)() as db:
            await reserve_processing_usage(db, workspace_id=PERSONAL_WORKSPACE_ID,
                reservation_key="synthetic:expired", declared_seconds=100,
                now=now-timedelta(seconds=2), expires_at=now-timedelta(seconds=1))
            current = await reserve_processing_usage(db, workspace_id=PERSONAL_WORKSPACE_ID,
                reservation_key="synthetic:live", declared_seconds=60, now=now)
            assert await release_expired_free_usage(db,workspace_id=PERSONAL_WORKSPACE_ID,now=now)==1
            window = await db.get(FreeUsageWindow,current.window_id)
            assert window.reserved_seconds==60
    finally:
        await engine.dispose()


def test_resume_uses_rendered_immutable_terms_and_rejects_stale_schedule(client):
    import html
    import re

    from cryptography.fernet import Fernet

    from tests.fakes.auth_contexts import USER_ID
    from tests.integration.test_account_lifecycle import (
        _bind_web_session,
        _issue_web_session,
        _seed_personal_workspace,
    )
    from tests.integration.test_system_admin_billing import _managed_payment
    from twobrain_rec_server.billing.entitlements import grant_confirmed_payment
    from twobrain_rec_server.billing.payment_methods import SavedPaymentMethod
    from twobrain_rec_server.db.models import (
        WorkspaceSubscription,
    )

    async def seed():
        workspace, device = await _seed_personal_workspace(client)
        token, session_id = await _issue_web_session(client, user_id=USER_ID, workspace_id=workspace, device_id=device)
        async with client.app_state["sessionmaker"]() as db:
            version, _, operation, invoice = await _managed_payment(db)
            await grant_confirmed_payment(db, workspace_id=workspace,
                provider_payment_id=operation.provider_id, amount_minor=invoice.amount_minor,
                currency="RUB", paid_at=datetime.now(UTC), recurring_method_confirmed=True,
                saved_payment_method=SavedPaymentMethod("synthetic-resume", "bank_card", "•••• 0000"),
                payment_method_key=Fernet.generate_key())
            subscription = await db.get(WorkspaceSubscription, workspace)
            subscription.recurring_allowed = False
            version.status = "retired"
            version.enabled_for_checkout = False
            await db.commit()
            return workspace, token, session_id, version.id
    workspace, token, session_id, version_id = client.portal.call(seed)
    headers = _bind_web_session(client,token=token,session_id=session_id)

    def form():
        response = client.get("/billing/subscription")
        assert response.status_code == 200
        assert "1 234 ₽" in response.text and "Возобновить автопродление" in response.text
        return {name:html.unescape(value) for name,value in re.findall(
            r'<input type="hidden" name="([^"]+)" value="([^"]*)"',response.text)} | {"resume_consent":"true"}

    original = form()
    for key in ("expected_price_id", "expected_plan_version_id", "expected_schedule_version", "expected_paid_through"):
        changed = {k:v for k,v in original.items() if k != key}
        refused = client.post("/billing/subscription/resume",headers=headers,data=changed,follow_redirects=False)
        assert refused.status_code == 303 and refused.headers["location"].endswith("result=conflict")

    async def move_schedule():
        async with client.app_state["sessionmaker"]() as db:
            subscription = await db.get(WorkspaceSubscription, workspace)
            subscription.paid_through += timedelta(days=1)
            subscription.next_charge_at = subscription.paid_through
            subscription.schedule_version += 1
            subscription.application_version += 1
            await db.commit()
    client.portal.call(move_schedule)
    stale = client.post("/billing/subscription/resume",headers=headers,data=original,follow_redirects=False)
    assert stale.headers["location"].endswith("result=conflict")
    current = form()
    before = client.portal.call(lambda: _subscription_resume_state(client, workspace))
    resumed = client.post("/billing/subscription/resume",headers=headers,data=current,follow_redirects=False)
    assert resumed.headers["location"].endswith("result=resumed")
    duplicate = client.post("/billing/subscription/resume",headers=headers,data=current,follow_redirects=False)
    assert duplicate.headers["location"].endswith("result=already_active")
    after = client.portal.call(lambda: _subscription_resume_state(client, workspace))
    assert before[0] is False and after[0] is True
    assert after[1] == before[1]+1 and after[2:] == before[2:]
    assert str(version_id) == current["expected_plan_version_id"]

    async def remove_pin():
        async with client.app_state["sessionmaker"]() as db:
            subscription = await db.get(WorkspaceSubscription, workspace)
            subscription.recurring_allowed = False
            subscription.pinned_price_id = None
            subscription.pinned_plan_version_id = None
            subscription.pin_state = "pending"
            await db.commit()
    client.portal.call(remove_pin)
    current["expected_authority_version"] = str(after[1])
    unavailable = client.post("/billing/subscription/resume",headers=headers,data=current,follow_redirects=False)
    assert unavailable.headers["location"].endswith("result=terms_unavailable")
    assert client.portal.call(lambda: _subscription_resume_state(client, workspace))[0] is False


async def _subscription_resume_state(client, workspace):
    from twobrain_rec_server.db.models import BillingOperation, WorkspaceSubscription

    async with client.app_state["sessionmaker"]() as db:
        subscription = await db.get(WorkspaceSubscription, workspace)
        return (subscription.recurring_allowed, subscription.recurring_authority_version,
            subscription.paid_through, subscription.schedule_version,
            await db.scalar(select(func.count()).select_from(BillingInvoice)),
            await db.scalar(select(func.count()).select_from(BillingOperation)))


@pytest.mark.asyncio
@pytest.mark.parametrize("role_name", ["twobrain_rec_app", "twobrain_rec_media"])
async def test_worker_workspace_lock_serializes_quota_without_granting_workspace_updates(
    postgres_seeded_database_url, role_name,
):
    import asyncio
    from contextlib import asynccontextmanager

    from sqlalchemy.exc import DBAPIError

    from tests.conftest import USER_ID
    from tests.fixtures.postgres_test_database import ensure_disposable_media_role
    from tests.integration.test_rls_postgres_policies import _exact_app_role_engine
    from twobrain_rec_server.db.models import Workspace
    from twobrain_rec_server.db.tenant_context import (
        TenantDatabaseContext,
        apply_tenant_context_to_connection,
    )

    @asynccontextmanager
    async def worker_engine():
        if role_name == "twobrain_rec_app":
            async with _exact_app_role_engine(postgres_seeded_database_url) as engine:
                yield engine
        else:
            url = await ensure_disposable_media_role(postgres_seeded_database_url)
            engine = create_async_engine(url)
            try:
                yield engine
            finally:
                await engine.dispose()

    owner = create_async_engine(postgres_seeded_database_url)
    try:
        async with owner.connect() as connection:
            organization = await connection.scalar(select(Workspace.organization_id).where(Workspace.id == PERSONAL_WORKSPACE_ID))
        async with worker_engine() as app, app.connect() as conn:
            await apply_tenant_context_to_connection(conn, TenantDatabaseContext(
                organization_id=organization, workspace_id=PERSONAL_WORKSPACE_ID,
                user_id=USER_ID, context_kind="worker",
            ))
            assert await conn.scalar(text("select session_user")) == role_name
            assert await conn.scalar(select(Workspace.id).where(Workspace.id == PERSONAL_WORKSPACE_ID).with_for_update()) == PERSONAL_WORKSPACE_ID
            assert await conn.scalar(select(Workspace.id).where(Workspace.id != PERSONAL_WORKSPACE_ID).limit(1)) is None
            with pytest.raises(DBAPIError):
                async with conn.begin_nested():
                    await conn.execute(text("update workspaces set name='Forbidden synthetic update' where id=:w"), {"w":PERSONAL_WORKSPACE_ID})
            with pytest.raises(DBAPIError):
                async with conn.begin_nested():
                    await conn.execute(text("update workspaces set id=id where id=:w"), {"w":PERSONAL_WORKSPACE_ID})
            # A concurrent entitlement writer must wait for this actual lock.
            async def writer():
                async with owner.begin() as mutation:
                    await mutation.execute(text("set local lock_timeout='3s'"))
                    await mutation.execute(select(Workspace.id).where(Workspace.id == PERSONAL_WORKSPACE_ID).with_for_update())
                    return True
            task = asyncio.create_task(writer())
            try:
                with pytest.raises(TimeoutError):
                    await asyncio.wait_for(asyncio.shield(task), timeout=0.15)
                await conn.commit()
                assert await asyncio.wait_for(task, timeout=3)
            finally:
                await conn.rollback()
                if not task.done():
                    task.cancel()
                await asyncio.gather(task, return_exceptions=True)
    finally:
        await owner.dispose()
