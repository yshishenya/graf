from __future__ import annotations

from pathlib import Path

from tests.fixtures.rls import RLS_DIRECT_WORKSPACE_TABLES, RLS_INHERITED_WORKSPACE_TABLES

REPO_ROOT = Path(__file__).resolve().parents[4]
MIGRATION = (
    REPO_ROOT
    / "apps/server/src/twobrain_rec_server/db/migrations/versions/0005_rls_hardening.py"
)
MEETING_OUTCOMES_MIGRATION = (
    REPO_ROOT
    / "apps/server/src/twobrain_rec_server/db/migrations/versions/0009_meeting_outcomes_mvp.py"
)

MEETING_CONTENT_TABLES = {
    "meetings",
    "upload_sessions",
    "upload_parts",
    "temporary_upload_objects",
    "track_artifacts",
    "manifest_snapshots",
    "ingest_audit_events",
    "processing_placeholders",
    "processing_workflows",
    "mediascribe_jobs",
    "processing_results",
    "transcript_segments",
    "diarization_segments",
    "processing_audit_events",
    "processing_dependency_states",
    "meeting_outcome_sets",
    "meeting_outcome_items",
    "meeting_outcome_generation_attempts",
}


def test_meeting_content_tables_are_in_rls_scope_fixture() -> None:
    scoped_tables = RLS_DIRECT_WORKSPACE_TABLES | RLS_INHERITED_WORKSPACE_TABLES

    assert scoped_tables >= MEETING_CONTENT_TABLES


def test_meeting_content_migration_enables_and_forces_rls() -> None:
    migration_text = MIGRATION.read_text(encoding="utf-8")

    assert "enable row level security" in migration_text
    assert "force row level security" in migration_text
    for table_name in sorted(MEETING_CONTENT_TABLES):
        assert table_name in migration_text or table_name in MEETING_OUTCOMES_MIGRATION.read_text(encoding="utf-8")
