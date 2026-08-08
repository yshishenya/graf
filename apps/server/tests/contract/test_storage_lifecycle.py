from datetime import UTC, datetime, timedelta
from pathlib import Path

from twobrain_rec_server.billing.source_lifecycle import (
    SOURCE_TRACK_ROLES,
    SourceLifecycleState,
    source_lifecycle_state_for_gates,
)

NOW = datetime(2026, 8, 7, 9, 0, tzinfo=UTC)


def test_current_and_legacy_sources_share_two_gate_retention_contract() -> None:
    assert {"media", "microphone", "system"} == SOURCE_TRACK_ROLES
    state, deadline = source_lifecycle_state_for_gates(
        transcript_imported_at=NOW,
        playback_verified_at=NOW + timedelta(hours=1),
        now=NOW + timedelta(days=8),
        retention_period=timedelta(days=7),
    )
    assert state is SourceLifecycleState.PURGE_DUE
    assert deadline == NOW + timedelta(hours=1, days=7)


def test_source_lifecycle_migration_persists_policy_and_purge_evidence() -> None:
    migration = Path(__file__).parents[2] / "src/twobrain_rec_server/db/migrations/versions/0052_source_artifact_lifecycle.py"
    text = migration.read_text()
    for marker in (
        "source_transcript_imported_at",
        "source_playback_verified_at",
        "source_retention_policy_version",
        "source_retention_purge_due_at",
        "metadata_json",
    ):
        assert marker in text
