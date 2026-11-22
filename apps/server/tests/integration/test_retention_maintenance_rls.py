from __future__ import annotations

from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import text

from tests.integration.test_billing_notification_flow import (
    billing_maintenance_probe_url as billing_maintenance_probe_url,
)
from tests.integration.test_billing_notification_flow import rls_engine as rls_engine
from tests.integration.test_rls_postgres_policies import _seed_probe_rows
from twobrain_rec_server.config import Settings
from twobrain_rec_server.db.session import create_sessionmaker
from twobrain_rec_server.db.tenant_context import (
    MaintenanceTenantContext,
    apply_tenant_context,
)
from twobrain_rec_server.deletion.retention import run_retention_scan


@pytest.mark.asyncio
async def test_retention_scan_runs_cross_workspace_under_maintenance_role(rls_engine) -> None:
    """Prove the real maintenance-role/RLS path, not a monkeypatched session.

    The migration 0114 allowlist and the worker both depend on the maintenance
    role being able to read meetings and write retention snapshots across
    workspaces. This test seeds two workspaces, ages one meeting in each, and
    runs the existing dry-run scan under the exact retention_scan context.
    """
    ids = await _seed_probe_rows(rls_engine)
    old_start = datetime.now(UTC) - timedelta(days=400)

    async with rls_engine.begin() as conn:
        await conn.execute(
            text(
                """
                update meetings
                   set started_at = :old_start,
                       retention_policy_state = 'active'
                 where id in (:meeting_a, :meeting_b)
                """
            ),
            {
                "old_start": old_start,
                "meeting_a": ids["meeting_a"],
                "meeting_b": ids["meeting_b"],
            },
        )

    sessions = create_sessionmaker(rls_engine)
    context = MaintenanceTenantContext(
        operation_name="retention_scan",
        actor_id="test-retention-maintenance",
        reason_category="retention_policy",
        feature_area="deletion",
    )
    settings = Settings()

    async with sessions() as db:
        await apply_tenant_context(db, context)
        for workspace_id in (ids["workspace_a"], ids["workspace_b"]):
            result = await run_retention_scan(
                db,
                settings=settings,
                workspace_id=workspace_id,
                limit=10,
                dry_run=True,
                storage=None,
            )
            assert result.evaluated == 1
            assert result.created_requests == 0
            assert result.policy_snapshot_id is not None
        await db.rollback()
