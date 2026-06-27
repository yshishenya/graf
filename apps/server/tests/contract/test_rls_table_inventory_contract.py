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
RETENTION_DELETION_MIGRATION = (
    REPO_ROOT
    / "apps/server/src/twobrain_rec_server/db/migrations/versions/0007_retention_deletion_execution.py"
)
RECORDING_SYNC_MIGRATION = (
    REPO_ROOT
    / "apps/server/src/twobrain_rec_server/db/migrations/versions/0008_recording_sync_transcription_loop.py"
)
MEETING_OUTCOMES_MIGRATION = (
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
    retention_deletion_migration = _load_migration_module(
        RETENTION_DELETION_MIGRATION,
        "retention_deletion_execution_migration",
    )
    recording_sync_migration = _load_migration_module(
        RECORDING_SYNC_MIGRATION,
        "recording_sync_transcription_loop_migration",
    )
    meeting_outcomes_migration = _load_migration_module(
        MEETING_OUTCOMES_MIGRATION,
        "meeting_outcomes_mvp_migration",
    )
    calendar_context_migration = _load_migration_module(
        CALENDAR_CONTEXT_MIGRATION,
        "calendar_context_ingestion_migration",
    )
    support_incident_migration = _load_migration_module(
        SUPPORT_INCIDENT_MIGRATION,
        "support_incident_migration",
    )
    migration_tables = (
        set(migration.AUTH_PUBLIC_WORKSPACE_POLICIES)
        | set(migration.AUTH_REQUEST_WORKSPACE_POLICIES)
        | set(migration.CONTENT_WORKSPACE_POLICIES)
        | set(migration.ORGANIZATION_POLICIES)
        | set(migration.INHERITED_POLICIES)
        | set(access_migration.CONTENT_WORKSPACE_POLICIES)
        | set(retention_deletion_migration.CONTENT_WORKSPACE_POLICIES)
        | set(recording_sync_migration.CONTENT_WORKSPACE_POLICIES)
        | set(meeting_outcomes_migration.CONTENT_WORKSPACE_POLICIES)
        | set(calendar_context_migration.CONTENT_WORKSPACE_POLICIES)
        | set(support_incident_migration.SUPPORT_TABLES)
    )

    assert set(RLS_COVERED_TABLES) == migration_tables
