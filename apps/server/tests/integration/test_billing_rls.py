from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import select, text
from sqlalchemy.ext.asyncio import async_sessionmaker

from tests.integration.test_rls_postgres_policies import (
    _request_context,
    _seed_probe_rows,
    apply_tenant_context_to_connection,
)
from twobrain_rec_server.billing.referral_rewards import (
    create_pending_credit,
    reverse_credit_for_payment,
)
from twobrain_rec_server.db.models import TimeCreditLedgerEntry
from twobrain_rec_server.db.tenant_context import MaintenanceTenantContext, apply_tenant_context

pytest_plugins = ("tests.integration.test_rls_postgres_policies",)


def test_all_billing_tables_are_in_tenant_policy_inventory() -> None:
    migration_root = Path(__file__).parents[2] / "src/twobrain_rec_server/db/migrations/versions"
    migration_source = "\n".join(
        (migration_root / name).read_text(encoding="utf-8")
        for name in ("0044_user_account_billing.py", "0045_billing_entitlement_grants.py", "0058_referral_links_many_invitees.py")
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
