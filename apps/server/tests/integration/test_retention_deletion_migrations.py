from __future__ import annotations

from pathlib import Path

from tests.fixtures.rls import RLS_COVERED_TABLES as TEST_RLS_COVERED_TABLES
from twobrain_rec_server.db.rls_validation import RLS_COVERED_TABLES

REPO_ROOT = Path(__file__).resolve().parents[4]
MIGRATION = (
    REPO_ROOT
    / "apps/server/src/twobrain_rec_server/db/migrations/versions/0007_retention_deletion_execution.py"
)

RETENTION_DELETION_TABLES = {
    "meeting_deletion_requests",
    "meeting_deletion_artifact_states",
    "meeting_deletion_reports",
    "retention_policy_snapshots",
    "local_purge_tasks",
    "meeting_lifecycle_audit_events",
}


def test_retention_deletion_migration_declares_revision_chain_and_tables() -> None:
    migration_text = MIGRATION.read_text(encoding="utf-8")

    assert 'revision: str = "0007_retention_deletion_exec"' in migration_text
    assert 'down_revision: str | None = "0006_access_sharing_downloads"' in migration_text
    for table_name in RETENTION_DELETION_TABLES:
        assert f'"{table_name}"' in migration_text


def test_retention_deletion_tables_are_in_rls_inventory_and_test_fixture() -> None:
    assert RETENTION_DELETION_TABLES.issubset(set(RLS_COVERED_TABLES))
    assert RETENTION_DELETION_TABLES.issubset(TEST_RLS_COVERED_TABLES)
