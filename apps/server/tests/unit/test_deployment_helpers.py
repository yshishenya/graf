import pytest

from tests.fixtures.deployment import smoke_evidence_record
from twobrain_rec_server.deployment import validate_readiness_verdict


def test_validate_readiness_verdict_accepts_021_verdicts() -> None:
    assert validate_readiness_verdict("not_ready") == "not_ready"
    assert validate_readiness_verdict("blocked") == "blocked"
    assert validate_readiness_verdict("infra_smoke_ready") == "infra_smoke_ready"


@pytest.mark.parametrize("verdict", ["production_ready", "user_rollout_ready", "internal_user_pilot_ready"])
def test_validate_readiness_verdict_rejects_forbidden_021_verdicts(verdict: str) -> None:
    with pytest.raises(ValueError, match="forbidden"):
        validate_readiness_verdict(verdict)


def test_smoke_evidence_record_emits_safe_metadata_markdown() -> None:
    markdown = smoke_evidence_record().safe_markdown()

    assert "infra_smoke_ready" in markdown
    assert "mediascribe_jobs_created=0" in markdown
    assert "authorization" not in markdown.lower()
