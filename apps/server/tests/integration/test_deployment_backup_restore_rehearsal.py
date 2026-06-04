import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).parents[4]


def _run_script(path: str, *args: str) -> str:
    result = subprocess.run(
        [str(REPO_ROOT / path), *args],
        check=True,
        text=True,
        capture_output=True,
    )
    return result.stdout


def test_backup_helper_dry_run_records_remote_target_without_secret_values() -> None:
    output = _run_script("infra/scripts/backup-rec-stack.sh", "--dry-run")

    assert "2brain.dev" in output
    assert "/opt/projects/2brain-rec" in output
    assert "twobrain-rec-postgres-data" in output
    assert "twobrain-rec-minio-data" in output
    assert "secret" not in output.lower()


def test_restore_rehearsal_dry_run_blocks_without_backup_reference() -> None:
    output = _run_script("infra/scripts/rehearse-rec-restore.sh", "--dry-run")

    assert "restore_rehearsal_result=blocked" in output
    assert "backup_reference_missing" in output
