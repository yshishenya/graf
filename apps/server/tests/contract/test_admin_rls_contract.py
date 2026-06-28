from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

from tests.fixtures.rls import RLS_DIRECT_WORKSPACE_TABLES as TEST_RLS_DIRECT_WORKSPACE_TABLES
from twobrain_rec_server.db.rls_validation import RLS_DIRECT_WORKSPACE_TABLES

REPO_ROOT = Path(__file__).resolve().parents[4]
ADMIN_MIGRATION = (
    REPO_ROOT
    / "apps/server/src/twobrain_rec_server/db/migrations/versions/0013_workspace_admin_panel.py"
)

ADMIN_TABLES = {
    "workspace_invitations",
    "workspace_quota_policies",
    "workspace_usage_daily",
    "user_usage_daily",
    "admin_audit_events",
}


def _load_migration_module(path: Path, module_name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(module_name, path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_admin_migration_declares_expected_tables_and_revision_chain() -> None:
    migration = _load_migration_module(ADMIN_MIGRATION, "workspace_admin_panel_migration")

    assert migration.revision == "0013_workspace_admin_panel"
    assert migration.down_revision == "0012_support_incidents"
    assert set(migration.ADMIN_TABLES) == ADMIN_TABLES


def test_admin_tables_are_in_rls_inventory_and_fixture() -> None:
    assert set(RLS_DIRECT_WORKSPACE_TABLES) >= ADMIN_TABLES
    assert TEST_RLS_DIRECT_WORKSPACE_TABLES >= ADMIN_TABLES


def test_admin_migration_enables_and_forces_rls_for_each_admin_table() -> None:
    migration = _load_migration_module(ADMIN_MIGRATION, "workspace_admin_panel_migration_rls")

    assert set(migration.POLICY_NAMES) == ADMIN_TABLES
    for table_name in ADMIN_TABLES:
        assert migration.POLICY_NAMES[table_name] == f"{table_name}_tenant_isolation"


def test_admin_invitation_completion_rls_allows_only_required_auth_bootstrap_tables() -> None:
    migration = _load_migration_module(
        ADMIN_MIGRATION, "workspace_admin_panel_migration_auth_bootstrap"
    )

    for table_name in {"workspace_invitations", "admin_audit_events"}:
        predicate = migration._policy_predicate(table_name)
        assert "auth_bootstrap" in predicate
        assert "rec_auth_bootstrap_workspace_in_organization()" in predicate
        assert "workspace_id = rec_current_workspace_id()" in predicate
    for table_name in sorted(ADMIN_TABLES - {"workspace_invitations", "admin_audit_events"}):
        assert "auth_bootstrap" not in migration._policy_predicate(table_name)
