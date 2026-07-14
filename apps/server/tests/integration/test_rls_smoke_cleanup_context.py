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


def test_production_smoke_executes_cleanup_only_in_the_maintenance_runtime() -> None:
    script = REPO_ROOT / "infra/scripts/run-production-smoke.sh"
    text = script.read_text(encoding="utf-8")

    assert text.count("run --rm --no-deps -T rec-maintenance") == 4
    assert 'exec -T rec-api "${cleanup_args[@]}"' not in text
