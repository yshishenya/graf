import pytest

from tests.fixtures.deployment import smoke_evidence_record
from twobrain_rec_server.config import ALLOWED_READINESS_VERDICTS, FORBIDDEN_READINESS_VERDICTS
from twobrain_rec_server.deployment import ZERO_SIDE_EFFECT_ASSERTIONS, validate_readiness_verdict


def test_deployment_readiness_contract_allows_only_021_verdicts() -> None:
    assert set(ALLOWED_READINESS_VERDICTS) == {"not_ready", "blocked", "infra_smoke_ready"}


@pytest.mark.parametrize("verdict", FORBIDDEN_READINESS_VERDICTS)
def test_deployment_readiness_contract_rejects_rollout_ready_language(verdict: str) -> None:
    with pytest.raises(ValueError, match="forbidden"):
        validate_readiness_verdict(verdict)


def test_smoke_evidence_contract_requires_zero_processing_side_effects() -> None:
    record = smoke_evidence_record()

    assert record.side_effect_assertions == ZERO_SIDE_EFFECT_ASSERTIONS


def test_restore_rehearsal_is_required_for_infra_smoke_ready() -> None:
    with pytest.raises(ValueError, match="restore"):
        smoke_evidence_record(restore_or_rollback_rehearsal_result="blocked")
