from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_rollback_requires_exact_target_checkout_and_same_smoke_contract():
    source = (ROOT / "scripts/dev-harness.py").read_text()
    transition = source[source.index("    def _ordinary_transition("):source.index("    def _write_ordinary_receipt(")]
    assert "self._checkout_adapter(Path(record[\"root\"]), manifest)" in transition
    assert "adapter._assert_manifest_images(manifest, env)" in transition
    assert "self._assert_transition_smoke(checks)" in transition
    assert "target_adapter._install_app(target" in transition
    assert "target_adapter._validate_launch_bundle(target" in transition
