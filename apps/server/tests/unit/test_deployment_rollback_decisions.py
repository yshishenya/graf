import pytest

from twobrain_rec_server.deployment import rollback_decision_for_trigger


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
