from pathlib import Path

REPO_ROOT = Path(__file__).parents[4]
DASHBOARD_EVIDENCE_PATH = (
    REPO_ROOT / "specs/096-product-analytics-provider-rollout/validation/dashboard-evidence.md"
)


def test_dashboard_evidence_records_metadata_only_owners_caveats_and_blockers() -> None:
    evidence = DASHBOARD_EVIDENCE_PATH.read_text(encoding="utf-8")

    required_fragments = (
        "product analytics operator",
        "growth analytics operator",
        "privacy/security reviewer",
        "provider delivery-gap caveat",
        "retention/deletion caveat",
        "RBAC/audit",
        "No content-bearing provider exports",
        "paid campaign launch remains blocked",
        "product rollout readiness remains blocked",
        "rollback_status=ready_not_executed",
    )
    for fragment in required_fragments:
        assert fragment in evidence

    forbidden_fragments = ("phc_", "OAuth token:", "ClientID=", "Yclid=", "cookie=", "raw_payload=")
    assert all(fragment.lower() not in evidence.lower() for fragment in forbidden_fragments)
