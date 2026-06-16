from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

from tests.fixtures.rls_production_truth import passing_table_state_json

REPO_ROOT = Path(__file__).resolve().parents[4]


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


def test_rls_validation_script_blocks_without_postgres_url_and_does_not_touch_live_production() -> None:
    output = _run_command("python3", "apps/server/scripts/verify_rls_hardening.py")

    assert "rls_validation_result=blocked" in output
    assert "reason=postgres_test_database_required" in output
    assert "live_production_probe=not_attempted" in output
    assert "destructive_probe_database=not_provided" in output
    assert "live_production_enforcement=not_inspected" in output
    assert "not_changed" not in output


def test_rls_validation_script_rejects_live_production_database_url() -> None:
    env = os.environ.copy()
    env["RLS_TEST_DATABASE_URL"] = "postgresql+asyncpg://twobrain_rec:secret@127.0.0.1:5432/twobrain_rec"
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


def test_migration_verification_references_rls_validation_without_enabling_live_enforcement() -> None:
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

    result = _run_command_result("sh", "infra/scripts/verify-rec-migration.sh", "--execute", env=env)
    output = result.stdout + result.stderr

    assert "rls_validation_result=blocked" in output
    assert "migration_verification_result=pass" not in output
    assert result.returncode != 0 or "migration_verification_result=blocked" in output


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
        "0007_retention_deletion_exec",
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
        "0007_retention_deletion_exec",
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
        "0007_retention_deletion_exec",
        env=os.environ.copy(),
    )
    output = result.stdout + result.stderr

    assert result.returncode != 0
    assert "production_rls_state_result=blocked" in output
    assert "live_production_enforcement=verification_blocked" in output
    assert f"failed_table_names={failed_table_name}" in output
    assert "reason=production_rls_state_blocked" in output
