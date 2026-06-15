from __future__ import annotations

import re
from pathlib import Path

from tests.fixtures.rls import RLS_ORGANIZATION_TABLES

REPO_ROOT = Path(__file__).resolve().parents[4]
MIGRATION = (
    REPO_ROOT
    / "apps/server/src/twobrain_rec_server/db/migrations/versions/0005_rls_hardening.py"
)


def test_identity_and_auth_tables_have_policy_groups() -> None:
    migration_text = MIGRATION.read_text(encoding="utf-8")

    for table_name in RLS_ORGANIZATION_TABLES:
        assert table_name in migration_text
    for table_name in (
        "external_identities",
        "auth_sessions",
        "auth_session_device_bindings",
        "workspace_memberships",
        "registered_devices",
    ):
        assert table_name in migration_text


def test_auth_public_context_is_limited_to_auth_bootstrap_tables() -> None:
    migration_text = MIGRATION.read_text(encoding="utf-8")

    assert "AUTH_PUBLIC_WORKSPACE_POLICIES" in migration_text
    assert "rec_context_kind() in ('auth_public', 'auth_bootstrap')" in migration_text
    for content_table in ("meetings", "upload_sessions", "processing_workflows", "transcript_segments"):
        table_section = migration_text.split(f'"{content_table}":', maxsplit=1)[1].split("\n", maxsplit=1)[0]
        assert "auth_public" not in table_section


def test_callback_lookup_policy_is_bound_to_state_nonce() -> None:
    migration_text = MIGRATION.read_text(encoding="utf-8")

    assert "rec_auth_callback_state_nonce()" in migration_text
    assert "state_nonce = rec_auth_callback_state_nonce()" in migration_text


def test_auth_session_lookup_policy_requires_lookup_context_kind() -> None:
    migration_text = MIGRATION.read_text(encoding="utf-8")

    assert "rec_context_kind() = 'auth_session_lookup'" in migration_text
    assert (
        "rec_context_kind() = 'auth_session_lookup' "
        "and session_token_hash = rec_auth_session_token_hash()"
    ) in migration_text


def test_organization_scoped_policies_require_membership_or_bootstrap_exception() -> None:
    migration_text = MIGRATION.read_text(encoding="utf-8")

    assert "rec_current_user_has_active_workspace_membership()" in migration_text
    assert "rec_auth_bootstrap_workspace_in_organization()" in migration_text
    assert re.search(
        r"rec_context_kind\(\) = 'request'.*"
        r"and id = rec_current_organization_id\(\).*"
        r"and rec_current_user_has_active_workspace_membership\(\)",
        migration_text,
        re.DOTALL,
    )
    assert re.search(
        r"rec_context_kind\(\) = 'request'.*"
        r"and organization_id = rec_current_organization_id\(\).*"
        r"and rec_current_user_has_active_workspace_membership\(\)",
        migration_text,
        re.DOTALL,
    )
    assert re.search(
        r"rec_context_kind\(\) = 'auth_bootstrap'.*"
        r"and organization_id = rec_current_organization_id\(\).*"
        r"and rec_auth_bootstrap_workspace_in_organization\(\)",
        migration_text,
        re.DOTALL,
    )
