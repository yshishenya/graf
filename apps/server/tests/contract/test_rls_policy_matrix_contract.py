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
CALENDAR_SETTINGS_MIGRATION = (
    REPO_ROOT
    / "apps/server/src/twobrain_rec_server/db/migrations/versions/0014_calendar_settings_preferences.py"
)
MEETING_DETECTION_MIGRATION = (
    REPO_ROOT
    / "apps/server/src/twobrain_rec_server/db/migrations/versions/0017_meeting_detection_registry.py"
)
CALENDAR_AUTO_CONTEXT_MIGRATION = (
    REPO_ROOT
    / "apps/server/src/twobrain_rec_server/db/migrations/versions/0021_calendar_auto_context_match.py"
)
PLAYBACK_NORMALIZATION_MIGRATION = (
    REPO_ROOT
    / "apps/server/src/twobrain_rec_server/db/migrations/versions/0022_playback_normalization.py"
)
MEETING_SPEAKER_MIGRATION = (
    REPO_ROOT
    / "apps/server/src/twobrain_rec_server/db/migrations/versions/0029_meeting_speaker_names.py"
)
RECORDING_WORKFLOW_MIGRATION = (
    REPO_ROOT
    / "apps/server/src/twobrain_rec_server/db/migrations/versions/0031_recording_workflow_templates_sharing.py"
)
MEETING_SHARE_SECURITY_MIGRATION = (
    REPO_ROOT
    / "apps/server/src/twobrain_rec_server/db/migrations/versions/0035_meeting_share_security_hardening.py"
)
CONTENT_REGENERATION_MIGRATION = (
    REPO_ROOT
    / "apps/server/src/twobrain_rec_server/db/migrations/versions/0032_content_regeneration_lineage.py"
)
DELETION_PURGE_MIGRATION = (
    REPO_ROOT
    / "apps/server/src/twobrain_rec_server/db/migrations/versions/0033_deletion_purge_journal.py"
)
LIFECYCLE_RECONCILIATION_MIGRATION = (
    REPO_ROOT
    / "apps/server/src/twobrain_rec_server/db/migrations/versions/0035_content_lifecycle_reconciliation.py"
)
LEGACY_LINEAGE_MIGRATION = (
    REPO_ROOT
    / "apps/server/src/twobrain_rec_server/db/migrations/versions/0039_legacy_lineage_backfill.py"
)
OUTCOME_BASELINE_MIGRATION = (
    REPO_ROOT
    / "apps/server/src/twobrain_rec_server/db/migrations/versions/0043_outcome_initial_baseline_reconciliation.py"
)
SHARE_INVITATION_AUTH_LOOKUP_MIGRATION = (
    REPO_ROOT
    / "apps/server/src/twobrain_rec_server/db/migrations/versions/0036_share_invitation_auth_lookup.py"
)
AUTH_RATE_LIMIT_MIGRATION = (
    REPO_ROOT
    / "apps/server/src/twobrain_rec_server/db/migrations/versions/0037_auth_rate_limit_buckets.py"
)
BILLING_FOUNDATION_MIGRATION = (
    REPO_ROOT
    / "apps/server/src/twobrain_rec_server/db/migrations/versions/0044_user_account_billing.py"
)
BILLING_ENTITLEMENT_MIGRATION = (
    REPO_ROOT
    / "apps/server/src/twobrain_rec_server/db/migrations/versions/0045_billing_entitlement_grants.py"
)
BILLING_PROMOTIONS_MIGRATION = (
    REPO_ROOT
    / "apps/server/src/twobrain_rec_server/db/migrations/versions/0046_billing_promotions.py"
)
BILLING_NOTIFICATION_MIGRATION = (
    REPO_ROOT
    / "apps/server/src/twobrain_rec_server/db/migrations/versions/0048_billing_notification_preferences.py"
)
ACCOUNT_CLOSURE_MIGRATION = (
    REPO_ROOT
    / "apps/server/src/twobrain_rec_server/db/migrations/versions/0049_account_closure_requests.py"
)
REFERRAL_LINKS_MIGRATION = (
    REPO_ROOT
    / "apps/server/src/twobrain_rec_server/db/migrations/versions/0058_referral_links_many_invitees.py"
)
FAIR_USE_MIGRATION = (
    REPO_ROOT
    / "apps/server/src/twobrain_rec_server/db/migrations/versions/0068_fair_use_reviews.py"
)
PRODUCTION_SMOKE_SETUP_MIGRATION = (
    REPO_ROOT
    / "apps/server/src/twobrain_rec_server/db/migrations/versions/0023_production_smoke_setup.py"
)
PROMPT_OPTIMIZATION_MAINTENANCE_MIGRATION = (
    REPO_ROOT
    / "apps/server/src/twobrain_rec_server/db/migrations/versions/0033_prompt_optimization_maintenance.py"
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
        + CALENDAR_SETTINGS_MIGRATION.read_text(encoding="utf-8")
        + MEETING_DETECTION_MIGRATION.read_text(encoding="utf-8")
        + CALENDAR_AUTO_CONTEXT_MIGRATION.read_text(encoding="utf-8")
        + PLAYBACK_NORMALIZATION_MIGRATION.read_text(encoding="utf-8")
        + MEETING_SPEAKER_MIGRATION.read_text(encoding="utf-8")
        + RECORDING_WORKFLOW_MIGRATION.read_text(encoding="utf-8")
        + MEETING_SHARE_SECURITY_MIGRATION.read_text(encoding="utf-8")
        + CONTENT_REGENERATION_MIGRATION.read_text(encoding="utf-8")
        + DELETION_PURGE_MIGRATION.read_text(encoding="utf-8")
        + LIFECYCLE_RECONCILIATION_MIGRATION.read_text(encoding="utf-8")
        + LEGACY_LINEAGE_MIGRATION.read_text(encoding="utf-8")
        + SHARE_INVITATION_AUTH_LOOKUP_MIGRATION.read_text(encoding="utf-8")
        + AUTH_RATE_LIMIT_MIGRATION.read_text(encoding="utf-8")
        + BILLING_FOUNDATION_MIGRATION.read_text(encoding="utf-8")
        + BILLING_ENTITLEMENT_MIGRATION.read_text(encoding="utf-8")
        + BILLING_PROMOTIONS_MIGRATION.read_text(encoding="utf-8")
        + BILLING_NOTIFICATION_MIGRATION.read_text(encoding="utf-8")
        + ACCOUNT_CLOSURE_MIGRATION.read_text(encoding="utf-8")
        + REFERRAL_LINKS_MIGRATION.read_text(encoding="utf-8")
        + FAIR_USE_MIGRATION.read_text(encoding="utf-8")
    )

    for table_name in sorted(RLS_COVERED_TABLES):
        assert table_name in migration_text


def test_rls_policy_contract_names_every_covered_table() -> None:
    contract_text = CONTRACT.read_text(encoding="utf-8")

    for table_name in sorted(RLS_COVERED_TABLES):
        assert f"`{table_name}`" in contract_text


def test_migration_and_contract_share_maintenance_operations() -> None:
    migration_text = (
        MIGRATION.read_text(encoding="utf-8")
        + PLAYBACK_NORMALIZATION_MIGRATION.read_text(encoding="utf-8")
        + PRODUCTION_SMOKE_SETUP_MIGRATION.read_text(encoding="utf-8")
        + PROMPT_OPTIMIZATION_MAINTENANCE_MIGRATION.read_text(encoding="utf-8")
        + LIFECYCLE_RECONCILIATION_MIGRATION.read_text(encoding="utf-8")
        + LEGACY_LINEAGE_MIGRATION.read_text(encoding="utf-8")
        + OUTCOME_BASELINE_MIGRATION.read_text(encoding="utf-8")
        + BILLING_FOUNDATION_MIGRATION.read_text(encoding="utf-8")
    )

    for operation_name in sorted(RLS_ALLOWED_MAINTENANCE_OPERATIONS):
        assert operation_name in migration_text


def test_invitation_lookup_context_is_read_only() -> None:
    migration_text = SHARE_INVITATION_AUTH_LOOKUP_MIGRATION.read_text(encoding="utf-8")
    check_expression = migration_text.split("check_expression =", maxsplit=1)[1].split(
        "op.execute", maxsplit=1
    )[0]

    assert "SHARE_INVITATION_LOOKUP_POLICY" not in check_expression
    assert "SHARE_INVITATION_LOOKUP_POLICY" in migration_text


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
