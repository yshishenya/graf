from __future__ import annotations

from pathlib import Path
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from tests.integration.test_rls_postgres_policies import (
    _request_context,
    _seed_content_export_rows,
    _seed_probe_rows,
    apply_tenant_context_to_connection,
)
from twobrain_rec_server.db.tenant_context import MaintenanceTenantContext

pytest_plugins = ("tests.integration.test_rls_postgres_policies",)

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


@pytest.mark.asyncio
async def test_summary_slots_are_workspace_isolated_and_null_current_is_visible(
    rls_engine,
) -> None:
    ids = await _seed_probe_rows(rls_engine)

    async with rls_engine.begin() as conn:
        await apply_tenant_context_to_connection(
            conn,
            MaintenanceTenantContext(
                operation_name="migration_verification",
                actor_id="test_rls_postgres_migrations",
                reason_category="summary_slot_rls_seed",
                feature_area="security",
            ),
        )
        for label in ("a", "b"):
            await conn.execute(
                text(
                    """
                    insert into meeting_summary_slots
                        (id, workspace_id, meeting_id, template_key)
                    values (:id, :workspace_id, :meeting_id, :template_key)
                    """
                ),
                {
                    "id": uuid4(),
                    "workspace_id": ids[f"workspace_{label}"],
                    "meeting_id": ids[f"meeting_{label}"],
                    "template_key": f"empty-{label}",
                },
            )

    async with rls_engine.connect() as conn:
        await apply_tenant_context_to_connection(conn, _request_context(ids, "a"))
        visible_a = await conn.execute(
            text(
                """
                select workspace_id, meeting_id, template_key, current_outcome_set_id
                  from meeting_summary_slots
                 order by template_key
                """
            )
        )
        rows_a = visible_a.mappings().all()

    async with rls_engine.connect() as conn:
        await apply_tenant_context_to_connection(conn, _request_context(ids, "b"))
        visible_b = await conn.execute(
            text(
                """
                select workspace_id, meeting_id, template_key, current_outcome_set_id
                  from meeting_summary_slots
                 order by template_key
                """
            )
        )
        rows_b = visible_b.mappings().all()

    assert rows_a == [
        {
            "workspace_id": ids["workspace_a"],
            "meeting_id": ids["meeting_a"],
            "template_key": "empty-a",
            "current_outcome_set_id": None,
        }
    ]
    assert rows_b == [
        {
            "workspace_id": ids["workspace_b"],
            "meeting_id": ids["meeting_b"],
            "template_key": "empty-b",
            "current_outcome_set_id": None,
        }
    ]


@pytest.mark.asyncio
async def test_summary_slot_composite_target_rejects_cross_scope_meeting_and_type(
    rls_engine,
) -> None:
    ids = await _seed_probe_rows(rls_engine)
    await _seed_content_export_rows(rls_engine, ids)
    second_meeting_id = uuid4()

    async with rls_engine.begin() as conn:
        await apply_tenant_context_to_connection(
            conn,
            MaintenanceTenantContext(
                operation_name="migration_verification",
                actor_id="test_rls_postgres_migrations",
                reason_category="summary_slot_target_seed",
                feature_area="security",
            ),
        )
        outcome_a_id = await conn.scalar(
            text(
                """
                select id
                  from meeting_outcome_sets
                 where processing_result_id = :processing_result_id
                """
            ),
            {"processing_result_id": ids["result_a"]},
        )
        outcome_b_id = await conn.scalar(
            text(
                """
                select id
                  from meeting_outcome_sets
                 where processing_result_id = :processing_result_id
                """
            ),
            {"processing_result_id": ids["result_b"]},
        )
        assert outcome_a_id is not None
        assert outcome_b_id is not None
        await conn.execute(
            text(
                """
                update meeting_outcome_sets
                   set template_key = 'type-a'
                 where id in (:outcome_a, :outcome_b)
                """
            ),
            {
                "outcome_a": outcome_a_id,
                "outcome_b": outcome_b_id,
            },
        )
        await conn.execute(
            text(
                """
                insert into meetings
                    (id, workspace_id, created_by_user_id, device_id,
                     local_recording_id, duration_seconds, status)
                values
                    (:meeting_id, :workspace_id, :user_id, :device_id,
                     :local_recording_id, 60, 'ingested_pending_processing')
                """
            ),
            {
                "meeting_id": second_meeting_id,
                "workspace_id": ids["workspace_a"],
                "user_id": ids["user_a"],
                "device_id": ids["device_a"],
                "local_recording_id": f"rls-summary-slot-{second_meeting_id}",
            },
        )

    invalid_targets = (
        # The slot and meeting are in A, but the target outcome is in B.
        {
            "slot_workspace_id": ids["workspace_a"],
            "slot_meeting_id": ids["meeting_a"],
            "slot_template_key": "type-a",
            "target_outcome_set_id": outcome_b_id,
            "current_binding_class": "verified_complete",
            "context_label": "a",
            "expected_constraint": "fk_meeting_summary_slots_current_outcome_target",
        },
        # The slot is in A and the target is also in A, but belongs to another meeting.
        {
            "slot_workspace_id": ids["workspace_a"],
            "slot_meeting_id": second_meeting_id,
            "slot_template_key": "type-a",
            "target_outcome_set_id": outcome_a_id,
            "current_binding_class": "verified_complete",
            "context_label": "a",
            "expected_constraint": "fk_meeting_summary_slots_current_outcome_target",
        },
        # The slot and target share workspace and meeting, but not the stable type.
        {
            "slot_workspace_id": ids["workspace_a"],
            "slot_meeting_id": ids["meeting_a"],
            "slot_template_key": "type-b",
            "target_outcome_set_id": outcome_a_id,
            "current_binding_class": "verified_complete",
            "context_label": "a",
            "expected_constraint": "fk_meeting_summary_slots_current_outcome_target",
        },
        # A null current pointer is still bound to its meeting/workspace pair.
        {
            "slot_workspace_id": ids["workspace_b"],
            "slot_meeting_id": ids["meeting_a"],
            "slot_template_key": "empty-mismatched-meeting",
            "target_outcome_set_id": None,
            "current_binding_class": None,
            "context_label": "b",
            "expected_constraint": "fk_meeting_summary_slots_meeting_workspace",
        },
    )

    for invalid_target in invalid_targets:
        async with rls_engine.begin() as conn:
            await apply_tenant_context_to_connection(
                conn,
                _request_context(ids, invalid_target["context_label"]),
            )
            with pytest.raises(IntegrityError) as error:
                await conn.execute(
                    text(
                        """
                        insert into meeting_summary_slots
                            (id, workspace_id, meeting_id, template_key,
                             current_outcome_set_id, current_binding_class)
                        values
                            (:id, :slot_workspace_id, :slot_meeting_id,
                             :slot_template_key, :target_outcome_set_id,
                             :current_binding_class)
                        """
                    ),
                    {"id": uuid4(), **invalid_target},
                )
            assert invalid_target["expected_constraint"] in str(error.value)
