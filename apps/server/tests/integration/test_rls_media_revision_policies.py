from __future__ import annotations

from pathlib import Path

from tests.fixtures.rls import RLS_DIRECT_WORKSPACE_TABLES, RLS_INHERITED_WORKSPACE_TABLES

REPO_ROOT = Path(__file__).resolve().parents[4]
MIGRATION = (
    REPO_ROOT
    / "apps/server/src/twobrain_rec_server/db/migrations/versions/0008_recording_sync_transcription_loop.py"
)

MEDIA_REVISION_DIRECT_TABLES = {
    "media_revisions",
    "upload_sessions",
    "temporary_upload_objects",
    "track_artifacts",
    "manifest_snapshots",
    "processing_workflows",
    "mediascribe_jobs",
    "processing_results",
    "transcript_segments",
    "diarization_segments",
    "processing_dependency_states",
    "meeting_deletion_artifact_states",
    "meeting_lifecycle_audit_events",
}

MEDIA_REVISION_INHERITED_TABLES = {
    "upload_parts",
}


def test_media_revision_tables_are_classified_for_tenant_isolation() -> None:
    assert RLS_DIRECT_WORKSPACE_TABLES >= MEDIA_REVISION_DIRECT_TABLES
    assert RLS_INHERITED_WORKSPACE_TABLES >= MEDIA_REVISION_INHERITED_TABLES


def test_media_revision_migration_enables_rls_for_new_table() -> None:
    assert MIGRATION.exists()
    migration = MIGRATION.read_text(encoding="utf-8")

    assert "media_revisions" in migration
    assert "media_revisions_tenant_isolation" in migration
    assert "enable row level security" in migration
    assert "force row level security" in migration
    assert "rec_context_kind() in ('request', 'worker')" in migration
    assert "rec_maintenance_allowed()" in migration


def test_media_revision_migration_links_lifecycle_tables_to_revision_identity() -> None:
    assert MIGRATION.exists()
    migration = MIGRATION.read_text(encoding="utf-8")

    assert "REVISION_LINKED_TABLES = [" in migration
    for table_name in [
        "upload_sessions",
        "temporary_upload_objects",
        "track_artifacts",
        "manifest_snapshots",
        "ingest_audit_events",
        "processing_workflows",
        "mediascribe_jobs",
        "processing_results",
        "processing_dependency_states",
    ]:
        assert table_name in migration
    assert 'sa.Column("media_revision_id", sa.Uuid(), sa.ForeignKey("media_revisions.id"))' in migration
