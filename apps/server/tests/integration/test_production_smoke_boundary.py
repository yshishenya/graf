import json
import os
import subprocess
import sys
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


def test_production_smoke_runner_mints_auth_session_and_cleans_it_up() -> None:
    script = (REPO_ROOT / "infra/scripts/run-production-smoke.sh").read_text()

    assert "python scripts/seed_smoke_identity.py" in script
    assert "python scripts/issue_smoke_auth_session.py" in script
    assert "python scripts/cleanup_smoke_auth_session.py" in script
    assert "run --rm --no-deps -T rec-maintenance" in script
    assert "require_json_status \"$SMOKE_AUTH_CLEANUP_JSON\" auth_cleanup_result pass" in script
    assert "require_json_status \"$SMOKE_ARTIFACT_CLEANUP_JSON\" cleanup_result pass" in script
    assert "trap cleanup_on_exit EXIT" in script
    assert "trap - EXIT" in script
    assert 'SMOKE_TOKEN_FILE="${TWOBRAIN_SMOKE_TOKEN_FILE:-/tmp/twobrain-rec-smoke-auth-token-${RUN_ID}}"' in script
    assert "--auth-session-id" in script
    assert '--token-file "$SMOKE_TOKEN_FILE"' in script
    assert '--run-id "$RUN_ID"' in script
    assert "TWOBRAIN_SMOKE_CREDENTIAL_FILE" not in script
    assert "--token " not in script
    assert "cat $SMOKE_TOKEN_FILE" not in script
    assert "--ttl-seconds 600" in script
    assert script.index("python scripts/seed_smoke_identity.py") < script.index(
        "python scripts/issue_smoke_auth_session.py"
    )


def test_remote_cd_deploys_processing_runtime_services() -> None:
    wrapper = (REPO_ROOT / "infra/scripts/cd-remote.sh").read_text()
    runtime = (REPO_ROOT / "infra/scripts/cd-remote-runtime.sh").read_text()

    assert 'bash infra/scripts/cd-remote-runtime.sh "$branch" "$expected_sha" "$previous_sha"' in wrapper
    assert '"${compose[@]}" build' in runtime
    assert "rec-temporal" in runtime
    assert "rec-processing-worker" in runtime
    assert "rec-maintenance" in runtime
    assert "rec-reprocess-maintenance" in runtime
    assert "rec-media-worker" in runtime


def test_remote_cd_finishes_production_smoke_before_opening_dispatch() -> None:
    wrapper = (REPO_ROOT / "infra/scripts/cd-remote.sh").read_text()
    runtime = (REPO_ROOT / "infra/scripts/cd-remote-runtime.sh").read_text()

    smoke_step = "infra/scripts/run-production-smoke.sh --execute"
    dispatch_step = "dispatch_opened=1"
    assert runtime.count(smoke_step) == 1
    assert runtime.index(smoke_step) < runtime.index(dispatch_step)
    dry_run_steps = next(line for line in wrapper.splitlines() if line.startswith("steps="))
    assert dry_run_steps.index("production_smoke") < dry_run_steps.index(
        "automatic_dispatch_open"
    )


def test_issue_smoke_auth_session_dry_run_never_writes_raw_token(tmp_path: Path) -> None:
    token_file = tmp_path / "smoke-token"
    script = REPO_ROOT / "apps/server/scripts/issue_smoke_auth_session.py"
    result = subprocess.run(
        [
            sys.executable,
            str(script),
            "--run-id",
            "smoke-014-dry-run",
            "--token-file",
            str(token_file),
        ],
        check=True,
        text=True,
        capture_output=True,
        env={**os.environ, "PYTHONPATH": str(REPO_ROOT / "apps/server/src")},
    )
    payload = json.loads(result.stdout)

    assert payload["auth_session_result"] == "dry_run"
    assert payload["token_written"] is False
    assert payload["token_file"] == str(token_file)
    assert not token_file.exists()
    assert "bearer" not in result.stdout.lower()


def test_issue_smoke_auth_session_owner_review_purpose_is_metadata_only(tmp_path: Path) -> None:
    token_file = tmp_path / "owner-review-token"
    script = REPO_ROOT / "apps/server/scripts/issue_smoke_auth_session.py"
    result = subprocess.run(
        [
            sys.executable,
            str(script),
            "--run-id",
            "feature-036-owner-review",
            "--purpose",
            "owner_review",
            "--token-file",
            str(token_file),
        ],
        check=True,
        text=True,
        capture_output=True,
        env={**os.environ, "PYTHONPATH": str(REPO_ROOT / "apps/server/src")},
    )
    payload = json.loads(result.stdout)

    assert payload["auth_session_result"] == "dry_run"
    assert payload["auth_session_purpose"] == "owner_review"
    assert payload["token_written"] is False
    assert not token_file.exists()
    forbidden = ["bearer ", "authorization:", "x-auth-session", "session_token", "cookie", "set-cookie"]
    assert all(marker not in result.stdout.lower() for marker in forbidden)


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
