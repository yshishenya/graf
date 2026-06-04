import pytest

from tests.fixtures.deployment import smoke_evidence_record
from twobrain_rec_server.deployment import scan_deployment_evidence_text


def test_deployment_evidence_scan_accepts_safe_smoke_markdown() -> None:
    scan_deployment_evidence_text(smoke_evidence_record().safe_markdown())


@pytest.mark.parametrize(
    "content",
    [
        "Authorization: Bearer abc",
        "aws_access_key_id=abc",
        "readiness_verdict=production_ready",
    ],
)
def test_deployment_evidence_scan_rejects_forbidden_content(content: str) -> None:
    with pytest.raises(ValueError):
        scan_deployment_evidence_text(content)
