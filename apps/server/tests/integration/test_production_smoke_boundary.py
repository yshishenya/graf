import json
import os
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pytest

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
    assert 'TWOBRAIN_SMOKE_RUN_ID=\'$RUN_ID\'' not in script
    assert "od -An -N8 -tx1 /dev/urandom" in script
    assert 'SMOKE_RUN_DIR="$(mktemp -d "/tmp/twobrain-rec-smoke-${RUN_ID}.' in script
    assert 'SMOKE_ARTIFACT_DIR="${SMOKE_ARTIFACT_BASE%/}-${RUN_ID}"' in script
    assert "must be a direct child name under /tmp" in script
    assert "cleanup_smoke_container_files required" in script
    assert "cleanup_smoke_container_files best_effort" in script


def test_default_smoke_run_ids_are_unique_for_parallel_invocations() -> None:
    def invoke() -> str:
        env = os.environ.copy()
        env.pop("TWOBRAIN_SMOKE_RUN_ID", None)
        return subprocess.run(
            [str(REPO_ROOT / "infra/scripts/run-production-smoke.sh"), "--dry-run"],
            check=True,
            text=True,
            capture_output=True,
            env=env,
        ).stdout

    with ThreadPoolExecutor(max_workers=4) as executor:
        outputs = list(executor.map(lambda _: invoke(), range(4)))

    run_ids = {
        line.split("=", 1)[1]
        for output in outputs
        for line in output.splitlines()
        if line.startswith("run_id=")
    }
    assert len(run_ids) == 4


@pytest.mark.parametrize(
    ("artifact_dir", "token_file"),
    [
        ("/tmp/../etc", "/tmp/token-smoke-014"),
        ("/tmp/safe/nested", "/tmp/token-smoke-014"),
        ("/tmp/safe", "/tmp/../var/run/token-smoke-014"),
    ],
)
def test_smoke_execute_rejects_paths_that_escape_direct_tmp_children(
    artifact_dir: str,
    token_file: str,
) -> None:
    result = subprocess.run(
        [str(REPO_ROOT / "infra/scripts/run-production-smoke.sh"), "--execute"],
        check=False,
        text=True,
        capture_output=True,
        env={
            **os.environ,
            "TWOBRAIN_SMOKE_RUN_ID": "smoke-014",
            "TWOBRAIN_SMOKE_ARTIFACT_DIR": artifact_dir,
            "TWOBRAIN_SMOKE_TOKEN_FILE": token_file,
        },
    )

    assert result.returncode == 2
    assert "direct child" in result.stderr


def test_test_artifact_generator_refuses_preexisting_symlink(tmp_path: Path) -> None:
    target = tmp_path / "target"
    target.mkdir()
    output = tmp_path / "artifact"
    output.symlink_to(target, target_is_directory=True)

    result = subprocess.run(
        [
            sys.executable,
            str(REPO_ROOT / "apps/server/scripts/create_test_artifact.py"),
            "--duration-seconds",
            "3",
            "--out",
            str(output),
        ],
        check=False,
        text=True,
        capture_output=True,
        env={**os.environ, "PYTHONPATH": str(REPO_ROOT / "apps/server/src")},
    )

    assert result.returncode != 0
    assert not (target / "mic.wav").exists()


@pytest.mark.parametrize(
    "run_id",
    ["", "../escape", "bad;touch /tmp/pwned", "bad value", "ключ", "a" * 129],
)
def test_smoke_run_id_rejects_shell_and_path_injection(run_id: str) -> None:
    result = subprocess.run(
        [str(REPO_ROOT / "infra/scripts/run-production-smoke.sh"), "--dry-run"],
        check=False,
        text=True,
        capture_output=True,
        env={**os.environ, "TWOBRAIN_SMOKE_RUN_ID": run_id},
    )

    assert result.returncode == 2
    assert "run_id" in result.stderr


@pytest.mark.parametrize("run_id", ["smoke-014", "run.2026_07-20", "A" + "x" * 127])
def test_smoke_run_id_accepts_bounded_safe_identifiers(run_id: str) -> None:
    result = subprocess.run(
        [sys.executable, str(REPO_ROOT / "apps/server/scripts/smoke_target.py"), "--validate-run-id", run_id],
        check=False,
        text=True,
        capture_output=True,
        env={**os.environ, "PYTHONPATH": str(REPO_ROOT / "apps/server/src")},
    )

    assert result.returncode == 0, result.stderr


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
    assert 'if [[ "${TWOBRAIN_GOOGLE_CALENDAR_ENABLED:-false}" == "true" ]]' in runtime
    assert 'export TWOBRAIN_GOOGLE_CALENDAR_CLIENT_SECRET_FILE="$disabled_billing_secret"' in runtime


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


def test_production_smoke_runs_metadata_only_outcome_value_path() -> None:
    runtime = (REPO_ROOT / "infra/scripts/run-production-smoke.sh").read_text()
    assert "seed_smoke_outcome.py" in runtime
    assert "prove_meeting_outcome_live.py" in runtime
    assert 'OUTCOME_SMOKE_ENABLED="${TWOBRAIN_OUTCOME_SMOKE_ENABLED:-false}"' in runtime
    assert 'if [[ "$OUTCOME_SMOKE_ENABLED" == "true" ]]' in runtime
    assert "candidate_state ready" in runtime
    assert "slot_state unpublished" in runtime


def test_outcome_live_proof_dry_run_is_metadata_safe(tmp_path: Path) -> None:
    script = REPO_ROOT / "apps/server/scripts/prove_meeting_outcome_live.py"
    result = subprocess.run(
        [
            sys.executable,
            str(script),
            "--api",
            "https://rec.2brain.pro",
            "--token-file",
            str(tmp_path / "outcome-token"),
            "--run-id",
            "feature-139-outcome-dry-run",
            "--meeting-id",
            "10000000-0000-0000-0000-000000000139",
        ],
        check=True,
        text=True,
        capture_output=True,
        env={**os.environ, "PYTHONPATH": str(REPO_ROOT / "apps/server/src")},
    )
    payload = json.loads(result.stdout)
    assert payload["proof_id"] == "feature-183-trusted-outcome-lifecycle"
    assert payload["candidate_state"] == "deferred"
    assert payload["cleanup_state"] == "deferred"
    assert "bearer" not in result.stdout.lower()
    assert "cookie" not in result.stdout.lower()


def test_outcome_prompt_manifest_is_versioned_and_hash_only() -> None:
    manifest = json.loads(
        (REPO_ROOT / "specs/139-meeting-outcome-value/evidence/prompt-promotion.json").read_text()
    )
    assert len(manifest["prompts"]) == 10
    assert all(len(item["target_hash"]) == 64 for item in manifest["prompts"])
    assert all(len(item["rollback_hash"]) == 64 for item in manifest["prompts"])
    assert "content" not in json.dumps(manifest).lower()
