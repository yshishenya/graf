from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]


def test_product_public_url_is_rec_2brain_pro_across_governance_sources() -> None:
    constitution = (ROOT / ".specify/memory/constitution.md").read_text()
    product_gates = (ROOT / "docs/agent-guidance/product-gates.md").read_text()
    prd = (ROOT / "docs/prd-voice-layer-final.md").read_text()
    deploy_script = (ROOT / "infra/scripts/cd-remote.sh").read_text()

    canonical = "https://rec.2brain.pro"

    assert "- MVP server target is `2brain.dev` with public URL `https://rec.2brain.pro`." in constitution
    assert "- MVP server target is `2brain.dev` with public URL\n  `https://rec.2brain.pro`." in product_gates
    assert "- Public web/API domain: `https://rec.2brain.pro`." in prd
    assert "curl -fsS https://rec.2brain.pro/api/v1/health/live" in deploy_script
    assert "curl -fsS https://rec.2brain.pro/api/v1/health/ready" in deploy_script

    assert canonical in constitution
    assert canonical in product_gates
    assert canonical in prd
    assert canonical in deploy_script
    assert "https://rec.2brain.dev" not in product_gates
    assert "https://rec.2brain.dev" not in prd
    assert "https://rec.2brain.dev" not in deploy_script
