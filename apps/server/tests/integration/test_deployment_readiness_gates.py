import pytest

from tests.fixtures.deployment import smoke_evidence_record


@pytest.mark.parametrize(
    "overrides",
    [
        {"restore_or_rollback_rehearsal_result": "blocked"},
        {"cleanup_result": "blocked"},
        {"log_redaction_result": "failed"},
        {"no_forbidden_side_effects_result": "failed"},
    ],
)
def test_blocked_deployment_gates_prevent_infra_smoke_ready(overrides: dict[str, str]) -> None:
    payload = {
        "readiness_verdict": "infra_smoke_ready",
        **overrides,
    }

    with pytest.raises(ValueError):
        smoke_evidence_record(**payload)
