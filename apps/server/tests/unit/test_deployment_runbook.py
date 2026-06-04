import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).parents[4]


def _run_script(path: str, *args: str, env: dict[str, str] | None = None) -> str:
    result = subprocess.run(
        [str(REPO_ROOT / path), *args],
        check=True,
        text=True,
        capture_output=True,
        env=env,
    )
    return result.stdout


def test_migration_verification_dry_run_reports_remote_compose_context() -> None:
    output = _run_script("infra/scripts/verify-rec-migration.sh", "--dry-run")

    assert "migration_verification_result=blocked" in output
    assert "2brain.dev" in output
    assert "/opt/projects/2brain-rec" in output


def test_rollback_helper_dry_run_records_halt_decision_without_claiming_ready() -> None:
    output = _run_script("infra/scripts/rollback-rec-stack.sh", "--dry-run", "--trigger", "health")

    assert "rollback_decision=halt" in output
    assert "trigger=health" in output
    assert "rollback_execution=decision_only_no_state_change" in output
    assert "infra_smoke_ready" not in output


def test_rollback_helper_preserves_late_arguments_before_remote_execution() -> None:
    output = _run_script(
        "infra/scripts/rollback-rec-stack.sh",
        "--dry-run",
        "--trigger",
        "migration",
        "--prior-state-reference",
        "backup-123",
    )

    assert "rollback_decision=restore" in output
    assert "trigger=migration" in output
    assert "prior_state_reference=backup-123" in output
