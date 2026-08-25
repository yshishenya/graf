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
PLAYBACK_NORMALIZATION_MIGRATION = (
    REPO_ROOT
    / "apps/server/src/twobrain_rec_server/db/migrations/versions/0022_playback_normalization.py"
)
PRODUCTION_SMOKE_SETUP_MIGRATION = (
    REPO_ROOT
    / "apps/server/src/twobrain_rec_server/db/migrations/versions/0023_production_smoke_setup.py"
)
PROVIDER_LINK_MIGRATION = (
    REPO_ROOT
    / "apps/server/src/twobrain_rec_server/db/migrations/versions/0024_provider_link_verified_callback.py"
)
PROMOTION_COUNTER_MIGRATION = (
    REPO_ROOT
    / "apps/server/src/twobrain_rec_server/db/migrations/versions/0080_promotion_reservation_counter_trigger.py"
)
PROMOTION_COUNTER_HARDENING_MIGRATION = (
    REPO_ROOT
    / "apps/server/src/twobrain_rec_server/db/migrations/versions/0081_secure_promotion_counter_function.py"
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


def test_playback_normalization_migration_declares_force_rls_and_narrow_maintenance() -> None:
    assert PLAYBACK_NORMALIZATION_MIGRATION.exists()
    migration_text = PLAYBACK_NORMALIZATION_MIGRATION.read_text(encoding="utf-8")

    assert 'revision: str = "0022_playback_normalization"' in migration_text
    assert 'down_revision: str | None = "0021_calendar_auto_context_match"' in migration_text
    assert "enable row level security" in migration_text
    assert "force row level security" in migration_text
    assert "rec_playback_normalization_maintenance_allowed" in migration_text
    assert "for select" in migration_text


def test_production_smoke_setup_migration_preserves_trusted_role_boundary() -> None:
    assert PRODUCTION_SMOKE_SETUP_MIGRATION.exists()
    migration_text = PRODUCTION_SMOKE_SETUP_MIGRATION.read_text(encoding="utf-8")

    assert 'revision: str = "0023_production_smoke_setup"' in migration_text
    assert 'down_revision: str | None = "0022_playback_normalization"' in migration_text
    assert "production_smoke_setup" in migration_text
    assert "session_user = 'twobrain_rec_maintenance'" in migration_text


def test_provider_link_migration_binds_callback_lookup_to_exact_nonce() -> None:
    assert PROVIDER_LINK_MIGRATION.exists()
    migration_text = PROVIDER_LINK_MIGRATION.read_text(encoding="utf-8")

    assert 'revision: str = "0024_provider_link_callback"' in migration_text
    assert 'down_revision: str | None = "0023_production_smoke_setup"' in migration_text
    assert "callback_state_id" in migration_text
    assert "initiating_auth_session_id" in migration_text
    assert "rec_auth_callback_state_nonce()" in migration_text


def test_promotion_counter_migration_keeps_counter_updates_inside_trigger() -> None:
    assert PROMOTION_COUNTER_MIGRATION.exists()
    migration_text = PROMOTION_COUNTER_MIGRATION.read_text(encoding="utf-8")

    assert 'revision: str = "0080_promo_counter_trigger"' in migration_text
    assert 'down_revision: str | None = "0079_remove_billing_launch_gates"' in migration_text
    assert "security definer" in migration_text
    assert "set search_path = pg_catalog, pg_temp" in migration_text
    assert migration_text.count("update public.promotion_campaigns") == 2
    assert "promotion_redemptions_sync_campaign_counter" in migration_text
    assert "reserved_count = reserved_count + 1" in migration_text


def test_promotion_counter_hardening_upgrades_existing_0080_database() -> None:
    assert PROMOTION_COUNTER_HARDENING_MIGRATION.exists()
    migration_text = PROMOTION_COUNTER_HARDENING_MIGRATION.read_text(encoding="utf-8")

    assert 'revision: str = "0081_secure_promo_counter"' in migration_text
    assert 'down_revision: str | None = "0080_promo_counter_trigger"' in migration_text
    assert "set search_path = pg_catalog, pg_temp" in migration_text
    assert migration_text.count("update public.promotion_campaigns") == 2
