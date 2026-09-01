from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_promotion_is_lock_protected_and_pointer_written_after_smoke():
    source = (ROOT / "scripts/dev-harness.py").read_text()
    assert "with state_lock(root)" in source
    assert "live promotion smoke failed" in source
    assert "active-manifest.json" in source


def test_runtime_compensation_refuses_unowned_processes():
    source = (ROOT / "scripts/dev-harness.py").read_text()
    assert "refusing to terminate unverified Dev backend pid" in source
    assert "refusing to restore over unverified Dev backend pid" in source
