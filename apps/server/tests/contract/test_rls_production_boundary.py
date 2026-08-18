from __future__ import annotations

import asyncio
import importlib.util
import json
import os
import subprocess
import sys
from pathlib import Path
from types import ModuleType

import pytest

from tests.fixtures.rls_production_truth import passing_table_state_json

REPO_ROOT = Path(__file__).resolve().parents[4]
RLS_SCRIPT = REPO_ROOT / "apps/server/scripts/verify_rls_hardening.py"


def _load_rls_script() -> ModuleType:
    module_name = "verify_rls_hardening_contract_test"
    spec = importlib.util.spec_from_file_location(module_name, RLS_SCRIPT)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def _run_command(*args: str) -> str:
    env = os.environ.copy()
    env.pop("RLS_TEST_DATABASE_URL", None)
    result = subprocess.run(
        [*args],
        cwd=REPO_ROOT,
        check=True,
        text=True,
        capture_output=True,
        env=env,
    )
    return result.stdout


def _run_command_result(*args: str, env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [*args],
        cwd=REPO_ROOT,
        check=False,
        text=True,
        capture_output=True,
        env=env,
    )


def test_rls_validation_script_blocks_without_postgres_url_and_does_not_touch_live_production() -> (
    None
):
    output = _run_command("python3", "apps/server/scripts/verify_rls_hardening.py")

    assert "rls_validation_result=blocked" in output
    assert "reason=postgres_test_database_required" in output
    assert "live_production_probe=not_attempted" in output
    assert "destructive_probe_database=not_provided" in output
    assert "live_production_enforcement=not_inspected" in output
    assert "not_changed" not in output


def test_rls_validation_script_rejects_live_production_database_url() -> None:
    env = os.environ.copy()
    env["RLS_TEST_DATABASE_URL"] = (
        "postgresql+asyncpg://twobrain_rec:secret@127.0.0.1:5432/twobrain_rec"
    )
    env.pop("RLS_TEST_PROBE_DATABASE_URL", None)

    result = _run_command_result("python3", "apps/server/scripts/verify_rls_hardening.py", env=env)
    output = result.stdout + result.stderr

    assert result.returncode != 0
    assert "rls_validation_result=blocked" in output
    assert "live_production_probe=not_attempted" in output
    assert "destructive_probe_database=explicit_test" in output
    assert "live_production_enforcement=not_inspected" in output
    assert "reason=live_production_database_probe_forbidden" in output
    assert "database_name=twobrain_rec" in output
    assert "twobrain_rec:secret" not in output
    assert "not_changed" not in output


def test_migration_verification_references_rls_validation_without_enabling_live_enforcement() -> (
    None
):
    output = _run_command("sh", "infra/scripts/verify-rec-migration.sh", "--dry-run")

    assert "rls_validation_result=blocked" in output
    assert "live_production_enforcement=not_inspected" in output
    assert "live_production_enforcement=enabled" not in output
    assert "not_changed" not in output


def test_migration_execute_blocks_when_rls_validation_is_blocked(tmp_path: Path) -> None:
    docker_stub = tmp_path / "docker"
    docker_stub.write_text("#!/usr/bin/env sh\nexit 0\n", encoding="utf-8")
    docker_stub.chmod(0o755)
    env = os.environ.copy()
    env.pop("RLS_TEST_DATABASE_URL", None)
    env["PATH"] = f"{tmp_path}:{env['PATH']}"

    result = _run_command_result(
        "sh", "infra/scripts/verify-rec-migration.sh", "--execute", env=env
    )
    output = result.stdout + result.stderr

    assert "rls_validation_result=blocked" in output
    assert "migration_verification_result=pass" not in output
    assert result.returncode != 0 or "migration_verification_result=blocked" in output


def test_migration_verification_reuses_runtime_maintenance_secret() -> None:
    script = (REPO_ROOT / "infra/scripts/verify-rec-migration.sh").read_text()

    assert "rec-db-runtime-bootstrap" in script
    assert "TWOBRAIN_DB_OWNER_PASSWORD_FILE" in script
    assert "TWOBRAIN_DB_MAINTENANCE_PASSWORD_FILE" in script
    assert "--runtime-owner-password-file" in script
    assert "--runtime-maintenance-password-file" in script
    assert "--destructive-probe-database disposable" in script
    assert 'owner_password="' not in script
    assert 'maintenance_password="' not in script
    assert '"$owner_password"' not in script
    assert '"$maintenance_password"' not in script


def test_existing_probe_role_urls_must_target_the_same_disposable_database(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    script = _load_rls_script()
    migration_url = (
        "postgresql+asyncpg://twobrain_rec:owner@rec-postgres:5432/twobrain_rec_rls_fixture"
    )
    probe_url = (
        "postgresql+asyncpg://twobrain_rec_maintenance:probe@rec-postgres:5432/"
        "twobrain_rec_rls_fixture"
    )
    granted: list[tuple[str, str]] = []

    async def grant_existing_role(database_url: str, role_name: str) -> None:
        granted.append((database_url, role_name))

    monkeypatch.setattr(script, "_grant_existing_probe_role", grant_existing_role)
    script._validate_existing_probe_url(
        migration_url,
        probe_url,
        destructive_probe_database="disposable",
    )
    urls = asyncio.run(script._prepare_urls(migration_url, existing_probe_url=probe_url))

    assert urls.probe_url == probe_url
    assert urls.probe_role is None
    assert granted == [(migration_url, "twobrain_rec_maintenance")]

    with pytest.raises(ValueError, match="same database"):
        script._validate_existing_probe_url(
            migration_url,
            probe_url.replace("twobrain_rec_rls_fixture", "twobrain_rec_rls_other"),
            destructive_probe_database="disposable",
        )

    with pytest.raises(ValueError, match="maintenance runtime role"):
        script._validate_existing_probe_url(
            migration_url,
            probe_url.replace("twobrain_rec_maintenance", "twobrain_rec_app"),
            destructive_probe_database="disposable",
        )


@pytest.mark.parametrize(
    ("database_name", "probe_database_name", "probe_role", "database_class"),
    [
        (
            "twobrain_rec_rls_fixture",
            "twobrain_rec_rls_fixture",
            "twobrain_rec_maintenance",
            "explicit_test",
        ),
        (
            "unsafe_fixture",
            "unsafe_fixture",
            "twobrain_rec_maintenance",
            "disposable",
        ),
        (
            "twobrain_rec_rls_fixture",
            "twobrain_rec_rls_other",
            "twobrain_rec_maintenance",
            "disposable",
        ),
        (
            "twobrain_rec_rls_fixture",
            "twobrain_rec_rls_fixture",
            "twobrain_rec_app",
            "disposable",
        ),
    ],
)
def test_existing_probe_role_preflight_blocks_before_migration(
    database_name: str,
    probe_database_name: str,
    probe_role: str,
    database_class: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    script = _load_rls_script()
    calls: list[str] = []
    monkeypatch.setenv(
        "RLS_TEST_DATABASE_URL",
        f"postgresql+asyncpg://twobrain_rec:owner@rec-postgres:5432/{database_name}",
    )
    monkeypatch.setenv(
        "RLS_TEST_PROBE_DATABASE_URL",
        f"postgresql+asyncpg://{probe_role}:probe@rec-postgres:5432/{probe_database_name}",
    )
    monkeypatch.setenv("RLS_DESTRUCTIVE_PROBE_DATABASE_CLASS", database_class)
    monkeypatch.setattr(script, "_load_probe_dependencies", lambda: calls.append("dependencies"))
    monkeypatch.setattr(script, "_run_migrations", lambda _url: calls.append("migrations"))

    assert script.main([]) == 1
    assert calls == []


def test_rls_validation_script_uses_runtime_safe_direct_sql_probes() -> None:
    script = (REPO_ROOT / "apps/server/scripts/verify_rls_hardening.py").read_text(encoding="utf-8")

    assert "direct_sql_rls_probes" in script
    assert "uv run" not in script
    assert "pytest" not in script
    assert "rls_probe_execution_not_implemented_in_script" not in script


def test_rls_validation_probe_url_keeps_generated_password_visible_to_driver() -> None:
    script = (REPO_ROOT / "apps/server/scripts/verify_rls_hardening.py").read_text(encoding="utf-8")

    assert "render_as_string(hide_password=False)" in script
    assert "str(make_url(database_url).set(username=probe_role, password=password))" not in script


def test_postgres_policy_probes_use_non_owner_role_for_rls_enforcement() -> None:
    probes = (REPO_ROOT / "apps/server/tests/integration/test_rls_postgres_policies.py").read_text(
        encoding="utf-8"
    )

    assert "RLS_TEST_PROBE_DATABASE_URL" in probes
    assert "create role" in probes.lower()
    assert "probe_url" in probes


def test_local_ci_includes_rls_validation_command() -> None:
    script = (REPO_ROOT / "infra/scripts/ci-local.sh").read_text(encoding="utf-8")

    assert "verify_rls_hardening.py" in script


def test_local_ci_runs_rls_validation_with_project_runtime() -> None:
    script = (REPO_ROOT / "infra/scripts/ci-local.sh").read_text(encoding="utf-8")

    assert "cd apps/server && PYTHONPATH=src uv run python scripts/verify_rls_hardening.py" in script


def test_production_read_only_cli_accepts_metadata_fixture(tmp_path: Path) -> None:
    fixture = tmp_path / "rls-state.json"
    fixture.write_text(json.dumps(passing_table_state_json()), encoding="utf-8")

    result = _run_command_result(
        sys.executable,
        "apps/server/scripts/verify_rls_hardening.py",
        "--production-read-only",
        "--table-state-json",
        str(fixture),
        "--deployed-commit",
        "3fd2162",
        "--alembic-revision",
        "0008_recording_sync_loop",
        env=os.environ.copy(),
    )
    output = result.stdout + result.stderr

    assert result.returncode == 0
    assert "production_rls_state_result=pass" in output
    assert "environment=live_production" in output
    assert "live_production_probe=read_only_metadata" in output
    assert "live_production_enforcement=enabled" in output
    assert "failed_table_names=none" in output
    assert "not_changed" not in output


def test_production_read_only_cli_does_not_require_git_binary(tmp_path: Path) -> None:
    fixture = tmp_path / "rls-state.json"
    fixture.write_text(json.dumps(passing_table_state_json()), encoding="utf-8")

    result = _run_command_result(
        sys.executable,
        "apps/server/scripts/verify_rls_hardening.py",
        "--production-read-only",
        "--table-state-json",
        str(fixture),
        "--alembic-revision",
        "0008_recording_sync_loop",
        env={**os.environ.copy(), "PATH": str(tmp_path)},
    )
    output = result.stdout + result.stderr

    assert result.returncode == 0
    assert "production_rls_state_result=pass" in output
    assert "deployed_commit=unknown" in output


def test_production_read_only_cli_blocks_failed_metadata_fixture(tmp_path: Path) -> None:
    fixture_data = passing_table_state_json()
    fixture_data["table_states"][0]["rls_forced"] = False
    failed_table_name = fixture_data["table_states"][0]["table_name"]
    fixture = tmp_path / "rls-state.json"
    fixture.write_text(json.dumps(fixture_data), encoding="utf-8")

    result = _run_command_result(
        "python3",
        "apps/server/scripts/verify_rls_hardening.py",
        "--production-read-only",
        "--table-state-json",
        str(fixture),
        "--deployed-commit",
        "3fd2162",
        "--alembic-revision",
        "0008_recording_sync_loop",
        env=os.environ.copy(),
    )
    output = result.stdout + result.stderr

    assert result.returncode != 0
    assert "production_rls_state_result=blocked" in output
    assert "live_production_enforcement=verification_blocked" in output
    assert f"failed_table_names={failed_table_name}" in output
    assert "reason=production_rls_state_blocked" in output
