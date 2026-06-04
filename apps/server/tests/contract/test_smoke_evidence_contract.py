import pytest

from tests.fixtures.deployment import smoke_evidence_payload, smoke_evidence_record
from twobrain_rec_server.deployment import REQUIRED_SMOKE_EVIDENCE_FIELDS, SmokeEvidenceRecord


def test_smoke_evidence_contract_requires_all_metadata_fields() -> None:
    payload = smoke_evidence_payload()

    for field in REQUIRED_SMOKE_EVIDENCE_FIELDS:
        assert field in payload


def test_smoke_evidence_contract_is_metadata_only_markdown() -> None:
    markdown = smoke_evidence_record().safe_markdown()

    assert "https://rec.2brain.pro" in markdown
    assert "infra_smoke_ready" in markdown
    assert "token" not in markdown.lower()
    assert "secret" not in markdown.lower()


@pytest.mark.parametrize("verdict", ["production_ready", "user_rollout_ready", "internal_user_pilot_ready"])
def test_smoke_evidence_contract_rejects_forbidden_readiness_verdicts(verdict: str) -> None:
    payload = smoke_evidence_payload(readiness_verdict=verdict)

    with pytest.raises(ValueError, match="readiness"):
        SmokeEvidenceRecord(**payload)
