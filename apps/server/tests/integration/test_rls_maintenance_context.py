from __future__ import annotations

from pathlib import Path

from tests.fixtures.rls import RLS_ALLOWED_MAINTENANCE_OPERATIONS
from twobrain_rec_server.db.tenant_context import (
    MaintenanceTenantContext,
    maintenance_context_settings,
)

REPO_ROOT = Path(__file__).resolve().parents[4]


def test_production_smoke_cleanup_is_allowlisted_maintenance_context() -> None:
    assert "production_smoke_cleanup" in RLS_ALLOWED_MAINTENANCE_OPERATIONS

    context = MaintenanceTenantContext(
        operation_name="production_smoke_cleanup",
        actor_id="smoke-cleanup",
        reason_category="smoke_cleanup",
        feature_area="ops",
    )

    assert maintenance_context_settings(context)["app.maintenance_operation"] == "production_smoke_cleanup"


def test_maintenance_sql_requires_metadata_gucs() -> None:
    migration_path = (
        REPO_ROOT / "apps/server/src/twobrain_rec_server/db/migrations/versions/0005_rls_hardening.py"
    )
    text = migration_path.read_text(encoding="utf-8")

    assert "rec_setting('app.maintenance_actor') is not null" in text
    assert "rec_setting('app.maintenance_reason') is not null" in text
    assert "rec_setting('app.maintenance_feature_area') is not null" in text
