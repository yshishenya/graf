from __future__ import annotations

from tests.fixtures.rls_production_truth import blocked_table_states, passing_table_states
from twobrain_rec_server.db.rls_validation import (
    RLS_COVERED_TABLES,
    evaluate_production_rls_state,
)


def test_production_state_passes_when_every_covered_table_is_enabled_and_forced() -> None:
    report = evaluate_production_rls_state(
        passing_table_states(),
        deployed_commit="3fd2162",
        alembic_revision="0006_access_sharing_downloads",
    )
    output = "\n".join(report.evidence_lines())

    assert report.production_rls_state_result == "pass"
    assert report.live_production_enforcement == "enabled"
    assert f"covered_table_count={len(RLS_COVERED_TABLES)}" in output
    assert f"rls_enabled_and_forced_count={len(RLS_COVERED_TABLES)}" in output
    assert "failed_table_names=none" in output


def test_production_state_blocks_when_a_table_is_not_forced() -> None:
    report = evaluate_production_rls_state(
        blocked_table_states("meetings"),
        deployed_commit="3fd2162",
        alembic_revision="0006_access_sharing_downloads",
    )

    assert report.production_rls_state_result == "blocked"
    assert report.live_production_enforcement == "verification_blocked"
    assert "meetings" in report.failed_table_names
    assert "covered_tables_not_enabled_and_forced" in report.blocking_reasons


def test_production_state_blocks_when_a_covered_table_is_missing() -> None:
    states = [state for state in passing_table_states() if state.table_name != "meetings"]
    report = evaluate_production_rls_state(
        states,
        deployed_commit="3fd2162",
        alembic_revision="0006_access_sharing_downloads",
    )

    assert report.production_rls_state_result == "blocked"
    assert "meetings" in report.failed_table_names


def test_production_state_blocks_before_rls_migration_revision() -> None:
    report = evaluate_production_rls_state(
        passing_table_states(),
        deployed_commit="3fd2162",
        alembic_revision="0004_mediascribe_processing",
    )

    assert report.production_rls_state_result == "blocked"
    assert "alembic_revision_before_rls_hardening" in report.blocking_reasons
