from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]


def test_smoke_auth_cleanup_uses_maintenance_context() -> None:
    script = REPO_ROOT / "apps/server/scripts/cleanup_smoke_auth_session.py"
    text = script.read_text(encoding="utf-8")

    assert "MaintenanceTenantContext" in text
    assert "production_smoke_cleanup" in text


def test_smoke_artifact_cleanup_uses_maintenance_context() -> None:
    script = REPO_ROOT / "apps/server/scripts/cleanup_smoke_artifacts.py"
    text = script.read_text(encoding="utf-8")

    assert "MaintenanceTenantContext" in text
    assert "production_smoke_cleanup" in text
