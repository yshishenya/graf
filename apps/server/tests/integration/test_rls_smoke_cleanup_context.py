from __future__ import annotations

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]


def test_smoke_identity_seed_uses_exact_maintenance_setup_context() -> None:
    script = REPO_ROOT / "apps/server/scripts/seed_smoke_identity.py"
    text = script.read_text(encoding="utf-8")

    assert "MaintenanceTenantContext" in text
    assert 'operation_name="production_smoke_setup"' in text


def test_smoke_auth_cleanup_uses_maintenance_context() -> None:
    script = REPO_ROOT / "apps/server/scripts/cleanup_smoke_auth_session.py"
    text = script.read_text(encoding="utf-8")

    assert "MaintenanceTenantContext" in text
    assert "production_smoke_cleanup" in text


def test_smoke_artifact_cleanup_uses_maintenance_context() -> None:
    script = REPO_ROOT / "apps/server/scripts/cleanup_smoke_artifacts.py"
    text = script.read_text(encoding="utf-8")

    assert "MaintenanceTenantContext" in text
    assert "TenantDatabaseContext" in text
    assert "production_smoke_cleanup" in text
    assert 'context_kind="request"' in text


def test_production_smoke_executes_setup_and_cleanup_only_in_maintenance_runtime() -> None:
    script = REPO_ROOT / "infra/scripts/run-production-smoke.sh"
    text = script.read_text(encoding="utf-8")

    assert text.count("run --rm --no-deps -T rec-maintenance") == 6
    assert "python scripts/seed_smoke_identity.py" in text
    assert "exec -T rec-api \\\n+  python scripts/seed_smoke_identity.py" not in text
    assert 'exec -T rec-api "${cleanup_args[@]}"' not in text
