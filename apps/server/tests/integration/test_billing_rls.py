import hashlib
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import async_sessionmaker
from twobrain_rec_server.billing.referral_binding import bind_referral_attribution
from twobrain_rec_server.billing.referral_rewards import (
    create_pending_credit,
    mature_pending_credits,
    reverse_credit_for_payment,
)
from twobrain_rec_server.billing.referrals import ReferralRiskSignals
from twobrain_rec_server.db.models import (
    ReferralAttribution,
    TimeCreditLedgerEntry,
    WorkspaceSubscription,
)
from twobrain_rec_server.db.tenant_context import (
    MaintenanceTenantContext,
    ReferralLandingLookupContext,
    WorkspaceAuthContext,
    apply_tenant_context,
)

from tests.integration.test_rls_postgres_policies import (
    _request_context,
    _seed_probe_rows,
    apply_tenant_context_to_connection,
)

pytest_plugins = ("tests.integration.test_rls_postgres_policies",)


def test_all_billing_tables_are_in_tenant_policy_inventory() -> None:
    migration_root = Path(__file__).parents[2] / "src/twobrain_rec_server/db/migrations/versions"
    migration_source = "\n".join(
        (migration_root / name).read_text(encoding="utf-8")
        for name in (
            "0044_user_account_billing.py",
            "0045_billing_entitlement_grants.py",
            "0058_referral_links_many_invitees.py",
            "0060_referral_user_history_rls.py",
        )
    )
    for table_name in (
        "workspace_subscriptions",
        "trial_activations",
        "billing_operations",
        "billing_invoices",
        "billing_payment_methods",
        "observed_provider_refunds",
        "free_usage_windows",
        "usage_reservations",
        "usage_ledger_entries",
        "storage_reservations",
        "time_credit_ledger_entries",
        "billing_audit_events",
        "billing_notification_deliveries",
        "billing_entitlement_grants",
        "billing_webhook_events",
        "referral_attributions",
        "referral_links",
    ):
        assert table_name in migration_source
        assert "_tenant_isolation" in migration_source


@pytest.mark.asyncio
async def test_workspace_subscription_isolated_and_missing_context_denied(rls_engine) -> None:
    ids = await _seed_probe_rows(rls_engine)
    for label in ("a", "b"):
        async with rls_engine.begin() as conn:
            await apply_tenant_context_to_connection(conn, _request_context(ids, label))
            await conn.execute(
                text("insert into workspace_subscriptions (workspace_id) values (:workspace_id)"),
                {"workspace_id": ids[f"workspace_{label}"]},
            )
    async with rls_engine.begin() as conn:
        assert await conn.scalar(text("select count(*) from workspace_subscriptions")) == 0
    async with rls_engine.begin() as conn:
        await apply_tenant_context_to_connection(conn, _request_context(ids, "a"))
        assert await conn.scalar(text("select count(*) from workspace_subscriptions")) == 1
        assert (
            await conn.scalar(
                text("select count(*) from workspace_subscriptions where workspace_id=:workspace_id"),
                {"workspace_id": ids["workspace_b"]},
            )
            == 0
        )


@pytest.mark.asyncio
async def test_referral_link_owner_can_issue_under_authenticated_web_context(rls_engine) -> None:
    ids = await _seed_probe_rows(rls_engine)
    async with rls_engine.begin() as conn:
        await apply_tenant_context_to_connection(
            conn,
            WorkspaceAuthContext(workspace_id=ids["workspace_a"], user_id=ids["user_a"]),
        )
        await conn.execute(
            text(
                "insert into referral_links "
                "(id, workspace_id, inviter_user_id, token_hash, campaign_version, state) "
                "values (:id, :workspace_id, :inviter_user_id, :token_hash, 'referral-v1', 'active')"
            ),
            {
                "id": uuid4(),
                "workspace_id": ids["workspace_a"],
                "inviter_user_id": ids["user_a"],
                "token_hash": ("b" * 63) + "1",
            },
        )
        assert await conn.scalar(text("select count(*) from referral_links")) == 1


@pytest.mark.asyncio
async def test_referral_signup_binder_can_insert_registered_attribution_under_rls(rls_engine) -> None:
    ids = await _seed_probe_rows(rls_engine)
    token = "r1_" + ("e" * 64)
    token_hash = hashlib.sha256(token.encode()).hexdigest()
    link_id = uuid4()
    async with rls_engine.begin() as conn:
        await apply_tenant_context_to_connection(
            conn,
            MaintenanceTenantContext(
                operation_name="billing_reconciliation",
                actor_id="test_referral_signup",
                reason_category="referral_signup_bind",
                feature_area="billing",
            ),
        )
        await conn.execute(
            text(
                "insert into referral_links "
                "(id, workspace_id, inviter_user_id, token_hash, campaign_version, expires_at, state) "
                "values (:id, :workspace_id, :inviter_user_id, :token_hash, 'referral-v1', now() + interval '1 day', 'active')"
            ),
            {
                "id": link_id,
                "workspace_id": ids["workspace_a"],
                "inviter_user_id": ids["user_a"],
                "token_hash": token_hash,
            },
        )
    async with async_sessionmaker(rls_engine, expire_on_commit=False)() as session:
        assert await bind_referral_attribution(
            session,
            workspace_id=ids["workspace_b"],
            user_id=ids["user_b"],
            token=token,
            now=datetime.now(UTC),
        )
        await session.commit()
    async with rls_engine.begin() as conn:
        await apply_tenant_context_to_connection(
            conn,
            MaintenanceTenantContext(
                operation_name="billing_reconciliation",
                actor_id="test_referral_signup_verify",
                reason_category="referral_signup_bind",
                feature_area="billing",
            ),
        )
        row = await conn.execute(
            text(
                "select state, invitee_user_id, referral_link_id from referral_attributions "
                "where referral_link_id=:link_id"
            ),
            {"link_id": link_id},
        )
        state, invitee_user_id, referral_link_id = row.one()
        assert state == "registered"
        assert invitee_user_id == ids["user_b"]
        assert referral_link_id == link_id


@pytest.mark.asyncio
async def test_public_referral_landing_lookup_is_token_and_expiry_scoped(rls_engine) -> None:
    ids = await _seed_probe_rows(rls_engine)
    token_hash = ("c" * 63) + "1"
    expired_token_hash = ("d" * 63) + "1"
    async with rls_engine.begin() as conn:
        await apply_tenant_context_to_connection(
            conn,
            MaintenanceTenantContext(
                operation_name="billing_reconciliation",
                actor_id="test_referral_landing",
                reason_category="referral_landing_probe",
                feature_area="billing",
            ),
        )
        await conn.execute(
            text(
                "insert into referral_links "
                "(id, workspace_id, inviter_user_id, token_hash, campaign_version, expires_at, state) "
                "values (:id, :workspace_id, :inviter_user_id, :token_hash, 'referral-v1', now() + interval '1 day', 'active')"
            ),
            {
                "id": uuid4(),
                "workspace_id": ids["workspace_a"],
                "inviter_user_id": ids["user_a"],
                "token_hash": token_hash,
            },
        )
        await conn.execute(
            text(
                "insert into referral_links "
                "(id, workspace_id, inviter_user_id, token_hash, campaign_version, expires_at, state) "
                "values (:id, :workspace_id, :inviter_user_id, :token_hash, 'referral-v1', now() - interval '1 day', 'active')"
            ),
            {
                "id": uuid4(),
                "workspace_id": ids["workspace_a"],
                "inviter_user_id": ids["user_a"],
                "token_hash": expired_token_hash,
            },
        )
    async with rls_engine.connect() as conn:
        await apply_tenant_context_to_connection(conn, ReferralLandingLookupContext(token_hash=token_hash))
        assert await conn.scalar(text("select count(*) from referral_links")) == 1
        await apply_tenant_context_to_connection(conn, ReferralLandingLookupContext(token_hash=expired_token_hash))
        assert await conn.scalar(text("select count(*) from referral_links")) == 0


@pytest.mark.asyncio
async def test_referral_reward_pending_and_reversal_cross_workspace_in_billing_maintenance(
    rls_engine,
) -> None:
    """Provider reconciliation may reward the inviter's workspace safely."""
    ids = await _seed_probe_rows(rls_engine)
    payment_id = f"pay-referral-{ids['slug']}"
    attribution_id = uuid4()
    link_id = uuid4()
    async with rls_engine.begin() as conn:
        await apply_tenant_context_to_connection(
            conn,
            MaintenanceTenantContext(
                operation_name="billing_reconciliation",
                actor_id="test_billing_rls",
                reason_category="referral_reward_probe",
                feature_area="billing",
            ),
        )
        await conn.execute(
            text(
                """
                insert into referral_links
                    (id, workspace_id, inviter_user_id, token_hash, campaign_version, state)
                values (:id, :workspace_id, :inviter_user_id, :token_hash, 'referral-v1', 'active')
                """
            ),
            {
                "id": link_id,
                "workspace_id": ids["workspace_a"],
                "inviter_user_id": ids["user_a"],
                "token_hash": ("a" * 63) + "1",
            },
        )
        await conn.execute(
            text(
                """
                insert into referral_attributions
                    (id, workspace_id, inviter_user_id, invitee_user_id, referral_link_id, token_hash, campaign_version, state)
                values (:id, :workspace_id, :inviter_user_id, :invitee_user_id, :referral_link_id, :token_hash, 'referral-v1', 'bound')
                """
            ),
            {
                "id": attribution_id,
                "workspace_id": ids["workspace_a"],
                "inviter_user_id": ids["user_a"],
                "invitee_user_id": ids["user_b"],
                "referral_link_id": link_id,
                "token_hash": ("a" * 63) + "1",
            },
        )

    sessionmaker = async_sessionmaker(rls_engine, expire_on_commit=False)
    async with sessionmaker() as db:
        await apply_tenant_context(
            db,
            MaintenanceTenantContext(
                operation_name="billing_reconciliation",
                actor_id="test_billing_rls",
                reason_category="referral_reward_probe",
                feature_area="billing",
            ),
        )
        assert (
            await create_pending_credit(
                db,
                workspace_id=ids["workspace_b"],
                invitee_user_id=ids["user_b"],
                provider_payment_id=payment_id,
                paid_at=datetime.now(UTC),
                cycle="month",
                risk_signals=ReferralRiskSignals(same_device=True, same_payment_profile=True),
            )
            == "created"
        )
        await db.commit()

        ledger = await db.scalar(
            select(TimeCreditLedgerEntry).where(
                TimeCreditLedgerEntry.workspace_id == ids["workspace_a"],
                TimeCreditLedgerEntry.source_ref == f"referral:payment:{payment_id}",
            )
        )
        assert ledger is not None
        assert ledger.state == "pending"
        assert ledger.referral_attribution_id == attribution_id
        attribution = await db.get(ReferralAttribution, attribution_id)
        assert attribution is not None
        assert attribution.state == "pending_maturity"
        assert attribution.risk_signal == "review"
        assert (
            await create_pending_credit(
                db,
                workspace_id=ids["workspace_b"],
                invitee_user_id=ids["user_b"],
                provider_payment_id=payment_id,
                paid_at=datetime.now(UTC),
                cycle="month",
            )
            == "duplicate"
        )

        paid_at = datetime(2026, 8, 1, tzinfo=UTC)
        subscription = WorkspaceSubscription(
            workspace_id=ids["workspace_a"],
            billing_owner_id=ids["user_a"],
            plan_code="personal",
            state="active",
            cycle="month",
            paid_through=paid_at + timedelta(days=30),
        )
        db.add(subscription)
        await db.flush()
        # Use the persisted maturity timestamp so the worker transition is
        # exercised without relying on the wall clock.
        ledger.maturity_at = paid_at + timedelta(days=14)
        ledger.expires_at = paid_at + timedelta(days=379)
        assert await mature_pending_credits(db, now=paid_at + timedelta(days=14)) == 7
        assert ledger.state == "applied"
        assert attribution.state == "applied"

        assert (
            await reverse_credit_for_payment(
                db,
                workspace_id=ids["workspace_b"],
                invitee_user_id=ids["user_b"],
                provider_payment_id=payment_id,
                now=datetime.now(UTC),
            )
            == "reversed"
        )
        await db.commit()
        assert ledger.state == "reversed"
        assert attribution.state == "reversed"
