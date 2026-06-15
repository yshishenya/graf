from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]

CURRENT_TRUTH_SURFACES = [
    REPO_ROOT / "docs/current-product-status.md",
    REPO_ROOT / "docs/deployments/2brain-rec/rls-hardening-runbook.md",
    REPO_ROOT / "docs/adr/003-tenant-isolation-rls.md",
    REPO_ROOT / "CHANGELOG.md",
]

STALE_CURRENT_CLAIMS = (
    "live production enforcement is not enabled by this slice",
    "live production enforcement of `031-rls-hardening` rls policies is not accepted automatically",
    "live production enforcement remains a separate operator decision",
    "requires a separate explicit operator decision",
    "live_production_enforcement=not_changed",
)


def test_current_rls_truth_surfaces_do_not_keep_stale_production_claims() -> None:
    for path in CURRENT_TRUTH_SURFACES:
        text = path.read_text(encoding="utf-8").lower()
        for stale_claim in STALE_CURRENT_CLAIMS:
            assert stale_claim not in text, f"{path} keeps stale RLS production claim: {stale_claim}"


def test_current_product_status_records_verified_production_rls_truth() -> None:
    text = (REPO_ROOT / "docs/current-product-status.md").read_text(encoding="utf-8")
    normalized = " ".join(text.split())

    assert "Feature `032-rls-live-enforcement`" in text
    assert "production RLS enforcement is verified enabled and forced" in text
    assert "read-only PostgreSQL catalog metadata" in normalized
    assert "0005_rls_hardening" in text


def test_031_quickstart_scopes_old_test_gate_wording_to_history() -> None:
    text = (REPO_ROOT / "specs/031-rls-hardening/quickstart.md").read_text(encoding="utf-8")

    assert "032 correction note" in text
    assert "live_production_enforcement=not_inspected" in text
    assert "live_production_enforcement=not_changed" not in text
