from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_rollback_requires_exact_target_checkout_and_same_smoke_contract():
    source = (ROOT / "scripts/dev-harness.py").read_text()
    assert "_assert_source_matches_checkout(target)" in source
    assert "_assert_manifest_images(target" in source
    assert "_assert_manifest_images(active" in source
    assert "live rollback smoke failed" in source
    assert "_install_app(target" in source
