import os
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).parents[4]


def _run_script(path: str, *args: str) -> str:
    env = os.environ.copy()
    env["PYTHONPATH"] = str(REPO_ROOT / "apps/server/src")
    result = subprocess.run(
        [str(REPO_ROOT / path), *args],
        check=True,
        text=True,
        capture_output=True,
        env=env,
    )
    return result.stdout


def test_production_smoke_runner_dry_run_is_remote_first_and_non_ready() -> None:
    output = _run_script("infra/scripts/run-production-smoke.sh", "--dry-run")

    assert "smoke_result=blocked" in output
    assert "remote_host=2brain.dev" in output
    assert "remote_path=/opt/projects/2brain-rec" in output
    assert "production_ready" not in output
    assert "user_rollout_ready" not in output


def test_smoke_upload_wrapper_dry_run_uses_internal_smoke_identity(tmp_path: Path) -> None:
    artifact = tmp_path / "artifact"
    artifact.mkdir()

    output = _run_script(
        "apps/server/scripts/upload_test_artifact.py",
        "--api",
        "https://rec.2brain.pro",
        "--organization",
        "21000000-0000-0000-0000-000000000001",
        "--workspace",
        "22000000-0000-0000-0000-000000000001",
        "--user",
        "23000000-0000-0000-0000-000000000001",
        "--device",
        "24000000-0000-0000-0000-000000000001",
        "--artifact",
        str(artifact),
        "--smoke-dry-run",
    )

    assert '"smoke_identity_class": "internal_smoke"' in output
    assert '"would_upload": true' in output
