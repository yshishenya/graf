from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
MIGRATION = (
    REPO_ROOT
    / "apps/server/src/twobrain_rec_server/db/migrations/versions/0005_rls_hardening.py"
)


def test_rls_migration_downgrade_removes_policies_and_force_rls() -> None:
    migration_text = MIGRATION.read_text(encoding="utf-8")

    assert "drop policy if exists" in migration_text
    assert "alter table {table} no force row level security" in migration_text
    assert "alter table {table} disable row level security" in migration_text


def test_rls_migration_downgrade_drops_helper_functions() -> None:
    migration_text = MIGRATION.read_text(encoding="utf-8")

    for function_name in (
        "rec_maintenance_allowed()",
        "rec_auth_callback_state_nonce()",
        "rec_auth_session_token_hash()",
        "rec_context_kind()",
        "rec_setting_uuid(text)",
        "rec_setting(text)",
    ):
        assert function_name in migration_text
