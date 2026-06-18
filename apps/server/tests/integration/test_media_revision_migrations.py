from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
MIGRATION = (
    REPO_ROOT
    / "apps/server/src/twobrain_rec_server/db/migrations/versions/0008_recording_sync_transcription_loop.py"
)


def test_media_revision_model_is_exported() -> None:
    from twobrain_rec_server import db
    from twobrain_rec_server.db import models

    assert hasattr(models, "MediaRevision")
    assert hasattr(db.models, "MediaRevision")


def test_recording_sync_migration_declares_media_revision_boundaries() -> None:
    assert MIGRATION.exists()
    migration = MIGRATION.read_text(encoding="utf-8")

    for needle in [
        'revision: str = "0008_recording_sync_loop"',
        'down_revision: str | None = "0007_retention_deletion_exec"',
        '"media_revisions"',
        '"media_revision_id"',
        '"local_media_revision_id"',
        "uq_media_revisions_workspace_meeting_revision",
        "uq_media_revisions_workspace_local_revision",
        '"upload_sessions"',
        '"track_artifacts"',
        '"manifest_snapshots"',
        '"processing_workflows"',
        '"mediascribe_jobs"',
        '"processing_results"',
    ]:
        assert needle in migration
