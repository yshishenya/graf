import pytest

from twobrain_rec_server.deployment import (
    PlaybackNormalizationRollingVersionState,
    rollback_decision_for_trigger,
)


@pytest.mark.parametrize(
    ("trigger", "decision"),
    [
        ("dns_tls", "halt"),
        ("secrets", "halt"),
        ("health", "halt"),
        ("migration", "restore"),
        ("backup", "blocked"),
        ("restore_rehearsal", "blocked"),
        ("storage", "halt"),
        ("disk_full", "halt"),
        ("unsafe_exposure", "halt"),
        ("smoke_upload", "rollback"),
        ("forbidden_content", "halt"),
        ("cleanup", "blocked"),
    ],
)
def test_rollback_failure_classes_map_to_non_ready_decisions(trigger: str, decision: str) -> None:
    record = rollback_decision_for_trigger(
        trigger,
        prior_state_reference="backup-20260604-0001",
        residue_owner="deployment-operator",
        residue_follow_up_reason="required by rollback trigger",
    )

    assert record.decision == decision


def test_restore_or_rollback_trigger_requires_prior_state_reference() -> None:
    with pytest.raises(ValueError, match="prior state"):
        rollback_decision_for_trigger("migration")


def test_smoke_residue_triggers_require_owner_and_follow_up() -> None:
    with pytest.raises(ValueError, match="cleanup obligations"):
        rollback_decision_for_trigger("cleanup")


def test_rolling_version_order_allows_only_additive_099_sequence() -> None:
    migration = PlaybackNormalizationRollingVersionState(
        migration_0022_present=True,
        api_contract="pre_099",
        media_worker_contract="absent",
        automatic_dispatch_enabled=False,
    )
    new_api = migration.model_copy(update={"api_contract": "099"})
    capable_worker = new_api.model_copy(
        update={
            "media_worker_contract": "099",
            "api_runtime_sha": "candidate-sha",
            "media_worker_runtime_sha": "candidate-sha",
        }
    )
    dispatch = capable_worker.model_copy(update={"automatic_dispatch_enabled": True})

    for state in (migration, new_api, capable_worker, dispatch):
        PlaybackNormalizationRollingVersionState.model_validate(state.model_dump())


def test_rolling_version_rejects_new_api_before_migration() -> None:
    with pytest.raises(ValueError, match="migration 0022"):
        PlaybackNormalizationRollingVersionState(
            migration_0022_present=False,
            api_contract="099",
            media_worker_contract="absent",
            automatic_dispatch_enabled=False,
        )


def test_rolling_version_rejects_dispatch_before_compatible_worker() -> None:
    with pytest.raises(ValueError, match="compatible media worker"):
        PlaybackNormalizationRollingVersionState(
            migration_0022_present=True,
            api_contract="099",
            media_worker_contract="absent",
            automatic_dispatch_enabled=True,
        )


def test_rolling_version_rejects_unexpected_runtime_sha_mix() -> None:
    with pytest.raises(ValueError, match="runtime SHA"):
        PlaybackNormalizationRollingVersionState(
            migration_0022_present=True,
            api_contract="099",
            media_worker_contract="099",
            automatic_dispatch_enabled=False,
            api_runtime_sha="api-sha",
            media_worker_runtime_sha="worker-sha",
        )


def test_normalization_rollback_rejects_raw_pre_099_target() -> None:
    with pytest.raises(ValueError, match="raw pre-099"):
        rollback_decision_for_trigger(
            "playback_normalization_compatibility",
            prior_state_reference="backup-20260714-0001",
            rollback_target="raw_pre_099",
            dispatch_stopped=True,
            legacy_playback_guard_retained=False,
        )


def test_normalization_rollback_requires_stopped_dispatch_and_guarded_target() -> None:
    with pytest.raises(ValueError, match="dispatch must stop"):
        rollback_decision_for_trigger(
            "playback_normalization_compatibility",
            prior_state_reference="backup-20260714-0001",
            rollback_target="compatibility_099",
            dispatch_stopped=False,
            legacy_playback_guard_retained=True,
        )

    record = rollback_decision_for_trigger(
        "playback_normalization_compatibility",
        prior_state_reference="backup-20260714-0001",
        rollback_target="compatibility_099",
        dispatch_stopped=True,
        legacy_playback_guard_retained=True,
        residue_owner="deployment-operator",
        residue_follow_up_reason="registered attempts require safe cleanup",
    )

    assert record.decision == "rollback"
    assert record.rollback_target == "compatibility_099"
    assert record.dispatch_stopped is True
    assert record.legacy_playback_guard_retained is True
