from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
ADR = REPO_ROOT / "docs/adr/003-tenant-isolation-rls.md"


def test_future_tenant_table_adr_exists() -> None:
    assert ADR.exists()


def test_future_tenant_table_adr_requires_isolation_classification() -> None:
    text = ADR.read_text(encoding="utf-8")

    for phrase in (
        "Every new tenant-owned table",
        "isolation class",
        "owner column or parent relationship",
        "allowed context kinds",
        "read access outcome",
        "mutation access outcome",
        "metadata-only evidence",
    ):
        assert phrase in text


def test_future_product_surfaces_must_reuse_rls_contract() -> None:
    text = ADR.read_text(encoding="utf-8")

    for future_surface in ("016", "017", "018"):
        assert future_surface in text
