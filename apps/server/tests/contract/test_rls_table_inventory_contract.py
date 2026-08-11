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
AUTH_RATE_LIMIT_MIGRATION = (
    REPO_ROOT
    / "apps/server/src/twobrain_rec_server/db/migrations/versions/0037_auth_rate_limit_buckets.py"
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
    admin_migration = _load_migration_module(
        ADMIN_MIGRATION,
        "workspace_admin_panel_migration",
    )
    calendar_settings_migration = _load_migration_module(
        CALENDAR_SETTINGS_MIGRATION,
        "calendar_settings_preferences_migration",
    )
    meeting_detection_migration = _load_migration_module(
        MEETING_DETECTION_MIGRATION,
        "meeting_detection_registry_migration",
    )
    calendar_auto_context_migration = _load_migration_module(
        CALENDAR_AUTO_CONTEXT_MIGRATION,
        "calendar_auto_context_match_migration",
    )
    playback_normalization_migration = _load_migration_module(
        PLAYBACK_NORMALIZATION_MIGRATION,
        "playback_normalization_migration",
    )
    meeting_speaker_migration = _load_migration_module(
        MEETING_SPEAKER_MIGRATION,
        "meeting_speaker_names_migration",
    )
    recording_workflow_migration = _load_migration_module(
        RECORDING_WORKFLOW_MIGRATION,
        "recording_workflow_migration",
    )
    meeting_share_security_migration = _load_migration_module(
        MEETING_SHARE_SECURITY_MIGRATION,
        "meeting_share_security_migration",
    )
    content_regeneration_migration = _load_migration_module(
        CONTENT_REGENERATION_MIGRATION,
        "content_regeneration_migration",
    )
    deletion_purge_migration = _load_migration_module(
        DELETION_PURGE_MIGRATION,
        "deletion_purge_migration",
    )
    lifecycle_reconciliation_migration = _load_migration_module(
        LIFECYCLE_RECONCILIATION_MIGRATION,
        "lifecycle_reconciliation_migration",
    )
    legacy_lineage_migration = _load_migration_module(
        LEGACY_LINEAGE_MIGRATION,
        "legacy_lineage_migration",
    )
    auth_rate_limit_migration = _load_migration_module(
        AUTH_RATE_LIMIT_MIGRATION,
        "auth_rate_limit_migration",
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
        | set(admin_migration.ADMIN_TABLES)
        | set(calendar_settings_migration.CONTENT_WORKSPACE_POLICIES)
        | set(meeting_detection_migration.MEETING_DETECTION_TABLES)
        | set(calendar_auto_context_migration.CONTENT_WORKSPACE_POLICIES)
        | set(playback_normalization_migration.PLAYBACK_NORMALIZATION_TABLES)
        | set(meeting_speaker_migration.MEETING_SPEAKER_TABLES)
        | set(recording_workflow_migration.TENANT_TABLE_POLICIES)
        | set(recording_workflow_migration.GLOBAL_OPERATOR_TABLES)
        | set(meeting_share_security_migration.CONTENT_WORKSPACE_POLICIES)
        | set(content_regeneration_migration.CONTENT_WORKSPACE_POLICIES)
        | set(deletion_purge_migration.CONTENT_WORKSPACE_POLICIES)
        | set(lifecycle_reconciliation_migration.__dict__.get("CONTENT_WORKSPACE_POLICIES", {}))
        | set(legacy_lineage_migration.__dict__.get("CONTENT_WORKSPACE_POLICIES", {}))
        | set(auth_rate_limit_migration.AUTH_RATE_LIMIT_TABLES)
        | {
            "billing_plan_versions",
            "promotion_campaigns",
            "promotion_redemptions",
            "workspace_subscriptions",
            "trial_activations",
            "billing_operations",
            "billing_invoices",
            "billing_payment_methods",
            "billing_entitlement_grants",
            "observed_provider_refunds",
            "free_usage_windows",
            "usage_reservations",
            "usage_ledger_entries",
            "storage_reservations",
            "time_credit_ledger_entries",
            "billing_audit_events",
            "billing_notification_deliveries",
            "billing_notification_preferences",
            "billing_webhook_events",
            "referral_links",
            "referral_attributions",
            "account_closure_requests",
        }
    )

    assert set(RLS_COVERED_TABLES) == migration_tables


def test_meeting_detection_registry_and_candidate_policy_predicates_are_tenant_scoped() -> None:
    migration = _load_migration_module(
        MEETING_DETECTION_MIGRATION,
        "meeting_detection_registry_policy_predicates",
    )

    registry_predicate = migration._policy_predicate("meeting_target_registry_versions")
    entry_predicate = migration._policy_predicate("meeting_target_registry_entries")
    candidate_predicate = migration._policy_predicate("meeting_detection_candidates")

    assert "workspace_id is null or workspace_id = rec_current_workspace_id()" in registry_predicate
    assert "parent.workspace_id is null or parent.workspace_id = rec_current_workspace_id()" in entry_predicate
    assert "workspace_id = rec_current_workspace_id()" in candidate_predicate
    assert "workspace_id is null" not in candidate_predicate
