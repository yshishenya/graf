from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType
from uuid import UUID

import pytest

from tests.fixtures.rls import RLS_ALLOWED_MAINTENANCE_OPERATIONS, RLS_COVERED_TABLES
from twobrain_rec_server.db.tenant_context import (
    ALLOWED_MAINTENANCE_OPERATIONS,
    MaintenanceTenantContext,
    require_database_context,
)

REPO_ROOT = Path(__file__).resolve().parents[4]
MIGRATION = (
    REPO_ROOT
    / "apps/server/src/twobrain_rec_server/db/migrations/versions/0022_playback_normalization.py"
)


def _load_migration() -> ModuleType:
    spec = importlib.util.spec_from_file_location("playback_normalization_rls", MIGRATION)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_normalization_tables_are_in_runtime_fixture_and_migration_inventories() -> None:
    migration = _load_migration()
    expected = {
        "playback_normalization_jobs",
        "playback_normalization_attempts",
        "playback_backfill_runs",
    }

    assert expected <= set(RLS_COVERED_TABLES)
    assert expected == set(migration.PLAYBACK_NORMALIZATION_TABLES)


def test_normalization_maintenance_operations_are_narrow_and_consistent() -> None:
    expected = {
        "playback_normalization_inventory",
        "playback_normalization_dispatch",
    }
    assert expected <= set(ALLOWED_MAINTENANCE_OPERATIONS)
    assert expected <= RLS_ALLOWED_MAINTENANCE_OPERATIONS

    for operation_name in expected:
        context = MaintenanceTenantContext(
            operation_name=operation_name,
            actor_id="media-worker",
            reason_category="automatic_reconciliation",
            feature_area="playback_normalization",
        )
        assert context.operation_name == operation_name


def test_migration_policy_is_exact_workspace_or_approved_maintenance() -> None:
    migration = _load_migration()
    predicate = " ".join(migration.NORMALIZATION_RLS_PREDICATE.split())
    maintenance_predicate = " ".join(migration.NORMALIZATION_MAINTENANCE_PREDICATE.split())

    assert "rec_context_kind() in ('request', 'worker')" in predicate
    assert "workspace_id = rec_current_workspace_id()" in predicate
    assert "rec_maintenance_allowed()" not in predicate
    assert "rec_playback_normalization_maintenance_allowed()" in maintenance_predicate
    assert set(migration.NORMALIZATION_MAINTENANCE_SELECT_TABLES) == {
        "playback_normalization_jobs",
        "playback_backfill_runs",
    }


class _PostgresDialect:
    name = "postgresql"


class _PostgresBind:
    dialect = _PostgresDialect()


class _ContextProbeSession:
    def __init__(self, settings: dict[str, str] | None) -> None:
        self.info = {} if settings is None else {"tenant_context": settings}

    def get_bind(self):
        return _PostgresBind()


def test_runtime_context_guard_requires_exact_worker_workspace_and_maintenance_operation() -> None:
    workspace_id = UUID("20000000-0000-0000-0000-000000000001")
    worker = _ContextProbeSession(
        {
            "app.context_kind": "worker",
            "app.workspace_id": str(workspace_id),
        }
    )
    require_database_context(
        worker,
        allowed_context_kinds=frozenset({"worker"}),
        workspace_id=workspace_id,
    )

    with pytest.raises(RuntimeError, match="workspace"):
        require_database_context(
            worker,
            allowed_context_kinds=frozenset({"worker"}),
            workspace_id=UUID("20000000-0000-0000-0000-000000000002"),
        )
    with pytest.raises(RuntimeError, match="required"):
        require_database_context(
            _ContextProbeSession(None),
            allowed_context_kinds=frozenset({"worker"}),
        )
    with pytest.raises(RuntimeError, match="exact"):
        require_database_context(
            _ContextProbeSession(
                {
                    "app.context_kind": "maintenance",
                    "app.maintenance_operation": "playback_normalization_inventory",
                    "app.maintenance_feature_area": "playback_normalization",
                }
            ),
            allowed_context_kinds=frozenset({"maintenance"}),
            maintenance_operation="playback_normalization_dispatch",
        )
