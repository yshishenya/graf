from __future__ import annotations

import importlib.util
from pathlib import Path
from types import ModuleType

from tests.fixtures.rls import RLS_ALLOWED_MAINTENANCE_OPERATIONS, RLS_COVERED_TABLES

REPO_ROOT = Path(__file__).resolve().parents[4]
MIGRATION = (
    REPO_ROOT
    / "apps/server/src/twobrain_rec_server/db/migrations/versions/0005_rls_hardening.py"
)
ACCESS_MIGRATION = (
    REPO_ROOT
    / "apps/server/src/twobrain_rec_server/db/migrations/versions/0006_access_sharing_downloads.py"
)
DELETION_MIGRATION = (
    REPO_ROOT
    / "apps/server/src/twobrain_rec_server/db/migrations/versions/0007_retention_deletion_execution.py"
)
RECORDING_SYNC_MIGRATION = (
    REPO_ROOT
    / "apps/server/src/twobrain_rec_server/db/migrations/versions/0008_recording_sync_transcription_loop.py"
)
OUTCOMES_MIGRATION = (
    REPO_ROOT
    / "apps/server/src/twobrain_rec_server/db/migrations/versions/0009_meeting_outcomes_mvp.py"
)
CALENDAR_CONTEXT_MIGRATION = (
    REPO_ROOT
    / "apps/server/src/twobrain_rec_server/db/migrations/versions/0010_calendar_context_ingestion.py"
)
SUPPORT_INCIDENT_MIGRATION = (
    REPO_ROOT
    / "apps/server/src/twobrain_rec_server/db/migrations/versions/0012_support_incidents.py"
)
ADMIN_MIGRATION = (
    REPO_ROOT
    / "apps/server/src/twobrain_rec_server/db/migrations/versions/0013_workspace_admin_panel.py"
)
CONTRACT = REPO_ROOT / "specs/031-rls-hardening/contracts/rls-policy-matrix.md"


def test_rls_migration_covers_every_current_tenant_table() -> None:
    migration_text = (
        MIGRATION.read_text(encoding="utf-8")
        + ACCESS_MIGRATION.read_text(encoding="utf-8")
        + DELETION_MIGRATION.read_text(encoding="utf-8")
        + RECORDING_SYNC_MIGRATION.read_text(encoding="utf-8")
        + OUTCOMES_MIGRATION.read_text(encoding="utf-8")
        + CALENDAR_CONTEXT_MIGRATION.read_text(encoding="utf-8")
        + SUPPORT_INCIDENT_MIGRATION.read_text(encoding="utf-8")
        + ADMIN_MIGRATION.read_text(encoding="utf-8")
    )

    for table_name in sorted(RLS_COVERED_TABLES):
        assert table_name in migration_text


def test_rls_policy_contract_names_every_covered_table() -> None:
    contract_text = CONTRACT.read_text(encoding="utf-8")

    for table_name in sorted(RLS_COVERED_TABLES):
        assert f"`{table_name}`" in contract_text


def test_migration_and_contract_share_maintenance_operations() -> None:
    migration_text = MIGRATION.read_text(encoding="utf-8")

    for operation_name in sorted(RLS_ALLOWED_MAINTENANCE_OPERATIONS):
        assert operation_name in migration_text


def _load_migration_module() -> ModuleType:
    spec = importlib.util.spec_from_file_location("rls_hardening_migration", MIGRATION)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_content_policy_context_is_explicit_not_inferred_by_substring() -> None:
    migration_text = MIGRATION.read_text(encoding="utf-8")
    migration = _load_migration_module()

    assert 'if "workspace_id = rec_current_workspace_id()" in expression' not in migration_text
    for expression in migration.CONTENT_WORKSPACE_POLICIES.values():
        assert expression.startswith(migration.CONTENT_CONTEXT)


def test_uuid_setting_helper_is_sql_only_for_postgres_migration_stability() -> None:
    migration_text = MIGRATION.read_text(encoding="utf-8")
    helper_block = migration_text.split("create or replace function rec_setting_uuid", maxsplit=1)[1].split(
        "create or replace function rec_context_kind",
        maxsplit=1,
    )[0]

    assert "language sql" in helper_block
    assert "language plpgsql" not in helper_block
    assert "exception when" not in helper_block
