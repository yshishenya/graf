from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
MIGRATION = (
    REPO_ROOT
    / "apps/server/src/twobrain_rec_server/db/migrations/versions/0005_rls_hardening.py"
)


def test_rls_migration_revision_file_exists() -> None:
    assert MIGRATION.exists()


def test_rls_migration_declares_revision_chain() -> None:
    migration_text = MIGRATION.read_text(encoding="utf-8")
    assert 'revision: str = "0005_rls_hardening"' in migration_text
    assert 'down_revision: str | None = "0004_mediascribe_processing"' in migration_text
