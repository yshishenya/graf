from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

from tests.fixtures.rls import RLS_COVERED_TABLES as TEST_RLS_COVERED_TABLES
from twobrain_rec_server.db.rls_validation import RLS_COVERED_TABLES

REPO_ROOT = Path(__file__).resolve().parents[4]
MIGRATION = (
    REPO_ROOT
    / "apps/server/src/twobrain_rec_server/db/migrations/versions/0005_rls_hardening.py"
)
ACCESS_MIGRATION = (
    REPO_ROOT
    / "apps/server/src/twobrain_rec_server/db/migrations/versions/0006_access_sharing_downloads.py"
)


def _load_migration_module(path: Path, module_name: str) -> ModuleType:
    spec = importlib.util.spec_from_file_location(module_name, path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_rls_validation_inventory_is_sorted_and_unique() -> None:
    assert tuple(sorted(RLS_COVERED_TABLES)) == RLS_COVERED_TABLES
    assert len(set(RLS_COVERED_TABLES)) == len(RLS_COVERED_TABLES)


def test_rls_validation_inventory_matches_test_fixture() -> None:
    assert set(RLS_COVERED_TABLES) == TEST_RLS_COVERED_TABLES


def test_rls_validation_inventory_matches_031_migration_policy_maps() -> None:
    migration = _load_migration_module(MIGRATION, "rls_hardening_migration")
    access_migration = _load_migration_module(ACCESS_MIGRATION, "access_sharing_downloads_migration")
    migration_tables = (
        set(migration.AUTH_PUBLIC_WORKSPACE_POLICIES)
        | set(migration.AUTH_REQUEST_WORKSPACE_POLICIES)
        | set(migration.CONTENT_WORKSPACE_POLICIES)
        | set(migration.ORGANIZATION_POLICIES)
        | set(migration.INHERITED_POLICIES)
        | set(access_migration.CONTENT_WORKSPACE_POLICIES)
    )

    assert set(RLS_COVERED_TABLES) == migration_tables
