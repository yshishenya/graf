from pathlib import Path

import pytest
from sqlalchemy import text

from tests.integration.test_rls_postgres_policies import (
    _request_context,
    _seed_probe_rows,
    apply_tenant_context_to_connection,
)

pytest_plugins = ("tests.integration.test_rls_postgres_policies",)


def test_all_billing_tables_are_in_tenant_policy_inventory() -> None:
    migration_source = next(
        Path(__file__).parents[2].glob(
            "src/twobrain_rec_server/db/migrations/versions/0044_user_account_billing.py"
        )
    ).read_text(encoding="utf-8")
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
        "billing_webhook_events",
        "referral_attributions",
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
