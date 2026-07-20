import os
import shlex
import shutil
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).parents[4]
SMOKE_PATH = REPO_ROOT / "infra/scripts/run-product-analytics-provider-smoke.sh"


def test_provider_smoke_script_outputs_metadata_only_posthog_statuses() -> None:
    result = subprocess.run(
        [str(SMOKE_PATH)],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    output = result.stdout

    assert "provider_smoke_result=pass" in output
    assert "posthog_stack=config_valid" in output
    assert "posthog_stack_contract=handoff_valid" in output
    assert "posthog_runtime_source=official_posthog_hobby_generated_compose_required" in output
    assert "posthog_secret=redacted_status_only" in output
    assert "posthog_access_model=metadata_only_pass" in output
    assert "provider_lifecycle=metadata_only_pass" in output
    assert "posthog_deploy_dry_run=pass" in output
    assert "posthog_delivery=dry_run" in output
    assert "posthog_live_safe_delivery=transport_verified" in output
    assert "yandex_counter=runtime_only_redacted" in output
    assert "yandex_public_baseline=preserved" in output
    assert "yandex_render_config=present" in output
    assert "yandex_blocked_pages=pass" in output
    assert "yandex_auth=redacted_status_only" in output
    assert "yandex_offline=dry_run_two_conversions" in output
    assert "yandex_live_safe_upload=transport_verified" in output
    assert "yandex_duplicates=dedupe_key_stable" in output
    assert "dashboard_goal_visibility=metadata_only_contract_verified" in output
    assert "private_payload_status=none_committed" in output
    forbidden_fragments = ("phc_", "oauth", "cookie=", "stable_pseudonymous_user_id", "properties", "raw_payload")
    assert all(fragment not in output.lower() for fragment in forbidden_fragments)


def test_provider_smoke_uses_origin_default_branch_when_head_is_detached(tmp_path: Path) -> None:
    real_git = shutil.which("git")
    assert real_git is not None

    fake_git = tmp_path / "git"
    fake_git.write_text(
        "\n".join(
            (
                "#!/bin/sh",
                'if [ "$1" = "branch" ] && [ "$2" = "--show-current" ]; then',
                "  exit 0",
                "fi",
                'if [ "$1" = "symbolic-ref" ] && [ "$2" = "--quiet" ] && [ "$3" = "--short" ] && [ "$4" = "refs/remotes/origin/HEAD" ]; then',
                "  printf '%s\\n' origin/master",
                "  exit 0",
                "fi",
                f"exec {shlex.quote(real_git)} \"$@\"",
            )
        ),
        encoding="utf-8",
    )
    fake_git.chmod(0o755)

    result = subprocess.run(
        [str(SMOKE_PATH)],
        cwd=REPO_ROOT,
        check=False,
        capture_output=True,
        text=True,
        env={**os.environ, "PATH": f"{tmp_path}{os.pathsep}{os.environ['PATH']}"},
    )

    assert result.returncode == 0, result.stderr
    assert "provider_smoke_result=pass" in result.stdout
