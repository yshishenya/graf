from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
MIGRATION = (
    REPO_ROOT
    / "apps/server/src/twobrain_rec_server/db/migrations/versions/0005_rls_hardening.py"
)
CALENDAR_AUTO_CONTEXT_MIGRATION = (
    REPO_ROOT
    / "apps/server/src/twobrain_rec_server/db/migrations/versions/0021_calendar_auto_context_match.py"
)


def test_rls_migration_revision_file_exists() -> None:
    assert MIGRATION.exists()


def test_rls_migration_declares_revision_chain() -> None:
    migration_text = MIGRATION.read_text(encoding="utf-8")
    assert 'revision: str = "0005_rls_hardening"' in migration_text
    assert 'down_revision: str | None = "0004_mediascribe_processing"' in migration_text


def test_calendar_auto_context_migration_declares_attempt_rls_policy() -> None:
    assert CALENDAR_AUTO_CONTEXT_MIGRATION.exists()
    migration_text = CALENDAR_AUTO_CONTEXT_MIGRATION.read_text(encoding="utf-8")

    assert 'revision: str = "0021_calendar_auto_context_match"' in migration_text
    assert 'down_revision: str | None = "0020_user_scoped_recording_ids"' in migration_text
    assert '"recording_calendar_match_attempts"' in migration_text
    assert "enable row level security" in migration_text
    assert "force row level security" in migration_text
