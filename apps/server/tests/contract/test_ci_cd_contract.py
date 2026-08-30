from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[4]
LOCAL_CI = ROOT / "infra/scripts/ci-local.sh"
REMOTE_CD = ROOT / "infra/scripts/cd-remote.sh"


def run(*args: str, cwd: Path = ROOT, env: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        args,
        cwd=cwd,
        env={**os.environ, **(env or {})},
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        check=False,
    )


def run_stubbed_ci(
    changed_files: str,
    mode: str,
    *,
    diff_available: bool = True,
    fail_stage: str = "",
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    script = r'''
source "$1"
changed_files() {
  [[ "$GRAF_TEST_DIFF_AVAILABLE" == "true" ]] || return 9
  printf '%s\n' "$GRAF_TEST_CHANGED_FILES"
}
run_step() {
  local name="$1"
  if [[ "$name" == "server tests" || "$name" == "calendar performance proof" ]]; then
    printf 'server_test_gate=%s\n' "$4"
  fi
  if [[ "$name" == "$GRAF_TEST_FAIL_STAGE" ]]; then
    printf 'ci_stage=%s status=fail duration_seconds=0\n' "$name"
    return 17
  fi
  printf 'ci_stage=%s status=pass duration_seconds=0\n' "$name"
}
main "$2"
'''
    return run(
        "bash",
        "-c",
        script,
        "contract",
        str(LOCAL_CI),
        mode,
        env={
            "GRAF_PERFORMANCE_GATE": "auto",
            "GRAF_TEST_CHANGED_FILES": changed_files,
            "GRAF_TEST_DIFF_AVAILABLE": str(diff_available).lower(),
            "GRAF_TEST_FAIL_STAGE": fail_stage,
            **(env or {}),
        },
    )


def test_local_ci_requires_an_explicit_lane_before_any_stage() -> None:
    result = run(str(LOCAL_CI))

    assert result.returncode == 2
    assert "usage:" in result.stdout
    assert "ci_stage=" not in result.stdout


def test_local_ci_help_is_explicit_and_runs_no_stage() -> None:
    result = run(str(LOCAL_CI), "--help")

    assert result.returncode == 0
    assert "--fast|--full" in result.stdout
    assert "ci_stage=" not in result.stdout


@pytest.mark.parametrize(
    ("path", "expected"),
    [
        ("apps/server/src/twobrain_rec_server/api/app.py", "server"),
        ("apps/server/src/twobrain_rec_server/calendar/matching.py", "server"),
        ("apps/server/src/twobrain_rec_server/domain/statuses.py", "server"),
        ("apps/server/src/twobrain_rec_server/auth/sessions.py", "server"),
        ("apps/server/src/twobrain_rec_server/api/auth.py", "server"),
        ("apps/server/tests/unit/test_sample.py", "server"),
        ("apps/server/tests/contract/test_sample.py", "server"),
        ("apps/server/tests/integration/test_sample.py", "server"),
        ("apps/macos/Sources/App.swift", "macos"),
        ("apps/macos/Package.resolved", "macos"),
        ("docs/user-guide.md", "docs"),
        ("docs/agent-guidance/release-and-validation.md", "docs"),
        ("docs/deployments/2brain-rec/release-v1.md", "docs"),
        ("infra/scripts/ci-local.sh", "infra"),
        (".specify/extensions.yml", "infra"),
        ("unknown/surface.bin", "unknown"),
    ],
)
def test_fast_component_classification_is_fail_closed(path: str, expected: str) -> None:
    result = run(
        "bash",
        "-c",
        'source "$1"; classify_path "$2"',
        "contract",
        str(LOCAL_CI),
        path,
    )

    assert result.returncode == 0, result.stdout
    assert result.stdout.strip() == expected


def test_fast_lane_runs_the_union_of_known_components_once() -> None:
    result = run_stubbed_ci(
        "apps/server/src/twobrain_rec_server/domain/statuses.py\napps/macos/Sources/App.swift\ndocs/user-guide.md",
        "--fast",
    )

    assert result.returncode == 0, result.stdout
    assert "ci_lane requested=fast effective=fast components=server,macos,docs" in result.stdout
    assert result.stdout.count("ci_stage=server tests ") == 1
    assert result.stdout.count("ci_stage=macOS Swift tests ") == 1
    assert result.stdout.count("ci_stage=active CI documentation consistency ") == 1


@pytest.mark.parametrize(
    "changed_files",
    [
        "apps/server/src/twobrain_rec_server/api/app.py",
        "apps/server/tests/contract/test_ci_cd_contract.py",
        "apps/server/tests/integration/test_calendar_auto_context_match.py",
        "infra/scripts/ci-local.sh",
        "unknown/surface.bin",
    ],
)
def test_explicit_fast_never_escalates_to_full(changed_files: str) -> None:
    result = run_stubbed_ci(changed_files, "--fast")

    assert result.returncode == 0, result.stdout
    assert "ci_lane requested=fast effective=fast" in result.stdout
    assert "next_gate=full_before_release" in result.stdout
    assert "effective=full" not in result.stdout


def test_unknown_and_unavailable_diffs_report_partial_fast_coverage() -> None:
    unknown = run_stubbed_ci("unknown/surface.bin", "--fast")
    unavailable = run_stubbed_ci("", "--fast", diff_available=False)

    assert "components=unknown" in unknown.stdout
    assert "coverage=partial next_gate=full_before_release" in unknown.stdout
    assert "reason=unknown_path path=unknown/surface.bin" in unknown.stdout
    assert "components=unknown" in unavailable.stdout
    assert "coverage=partial next_gate=full_before_release" in unavailable.stdout
    assert "reason=diff_unavailable" in unavailable.stdout


def test_changed_contract_and_integration_tests_run_focused_once() -> None:
    result = run_stubbed_ci(
        "apps/server/tests/contract/test_ci_cd_contract.py\n"
        "apps/server/tests/integration/test_calendar_auto_context_match.py",
        "--fast",
    )

    assert result.returncode == 0, result.stdout
    assert result.stdout.count("ci_stage=changed server tests status=pass") == 1
    assert "ci_stage=server tests status=pass" not in result.stdout
    assert "effective=fast components=server" in result.stdout


def test_explicit_full_requires_related_performance_gate() -> None:
    result = run_stubbed_ci(
        "apps/server/src/twobrain_rec_server/calendar/matching.py",
        "--full",
    )

    assert result.returncode == 0, result.stdout
    assert "ci_lane requested=full effective=full components=full" in result.stdout
    assert "performance_gate=required" in result.stdout


def test_synchronized_full_requires_performance_when_the_diff_is_empty() -> None:
    result = run_stubbed_ci("", "--full")

    assert result.returncode == 0, result.stdout
    assert "reason=synchronized_full_requires_performance" in result.stdout
    assert "performance_gate=required" in result.stdout


def test_changed_files_propagates_a_tracked_diff_failure() -> None:
    script = r'''
source "$1"
git() {
  case "$*" in
    *diff*--name-only*) return 9 ;;
    *) command git "$@" ;;
  esac
}
changed_files
'''
    result = run("bash", "-c", script, "contract", str(LOCAL_CI))

    assert result.returncode != 0


def test_changed_files_disables_rename_detection_for_both_endpoints() -> None:
    script = LOCAL_CI.read_text(encoding="utf-8")

    assert "diff --no-renames --name-only" in script


def test_fast_calendar_lane_runs_bounded_required_performance_proof() -> None:
    result = run_stubbed_ci(
        "apps/server/src/twobrain_rec_server/calendar/matching.py",
        "--fast",
    )

    assert result.returncode == 0, result.stdout
    assert "reason=performance_path_requires_focused_proof" in result.stdout
    assert "requested=fast effective=fast components=server" in result.stdout
    assert "performance_gate=required" in result.stdout
    assert "ci_stage=calendar performance proof status=pass" in result.stdout


def test_explicit_required_performance_keeps_fast_bounded() -> None:
    result = run_stubbed_ci(
        "apps/server/src/twobrain_rec_server/domain/statuses.py",
        "--fast",
        env={"GRAF_PERFORMANCE_GATE": "required"},
    )

    assert result.returncode == 0, result.stdout
    assert "reason=explicit_performance_requires_focused_proof" in result.stdout
    assert "requested=fast effective=fast components=server" in result.stdout
    assert "server_test_gate=required" in result.stdout


def test_failing_stage_emits_one_final_failure() -> None:
    result = run_stubbed_ci(
        "apps/server/src/twobrain_rec_server/api/app.py",
        "--fast",
        fail_stage="server tests",
    )

    assert result.returncode == 17
    assert result.stdout.count("ci_local_result=fail") == 1


def test_cd_dry_run_declares_authoritative_full_gate() -> None:
    result = run(str(REMOTE_CD), "--dry-run", "--branch", "211-optimize-ci-cd")

    assert result.returncode == 0, result.stdout
    assert "local_ci=full_required" in result.stdout
    assert "steps=clean_worktree,branch_sync,pinned_sha,local_ci,remote_fetch,backup" in result.stdout


def test_cd_execute_runs_full_after_sync_and_before_remote_gates() -> None:
    script = REMOTE_CD.read_text(encoding="utf-8")

    clean = script.index('git status --porcelain --untracked-files=all')
    sync = script.index('git fetch origin "$BRANCH"')
    full = script.index('ci-local.sh --full')
    post_full_sync = script.index('git fetch origin "$BRANCH"', sync + 1)
    remote = script.index('remote_script=$(cat')
    assert clean < sync < full < post_full_sync < remote
    assert "candidate_changed_during_full" in script
    assert "reason=worktree_status_failed" in script
    assert "reason=worktree_status_failed_after_full" in script
    assert '[[ -n "$(git status' not in script
    assert "local_ci=full_passed" in script
    assert "ci-receipt" not in script
    assert "--skip-local-ci" in script
    assert "cd-remote-runtime.sh" in script


def test_active_documentation_has_no_ambiguous_bare_ci_command() -> None:
    active = [
        ROOT / "AGENTS.md",
        ROOT / ".github/pull_request_template.md",
        ROOT / "docs/agent-guidance/release-and-validation.md",
        ROOT / "docs/agent-guidance/spec-kit-flow.md",
        ROOT / "infra/scripts/README.md",
    ]
    active.extend(path for path in (ROOT / "README.md", ROOT / "CONTRIBUTING.md") if path.is_file())
    active.extend(sorted((ROOT / "docs/agent-guidance").rglob("*.md")))
    ambiguous: list[str] = []
    for path in dict.fromkeys(active):
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            if "infra/scripts/ci-local.sh" in line and "--fast" not in line and "--full" not in line:
                ambiguous.append(f"{path.relative_to(ROOT)}:{line_number}")

    assert ambiguous == []


def test_active_documentation_matches_bounded_fast_contract() -> None:
    release_guidance = (ROOT / "docs/agent-guidance/release-and-validation.md").read_text(
        encoding="utf-8"
    )
    operator_readme = (ROOT / "infra/scripts/README.md").read_text(encoding="utf-8")
    pull_request_template = (ROOT / ".github/pull_request_template.md").read_text(encoding="utf-8")

    assert "always remains bounded" in release_guidance
    assert "never changes to `effective=full`" in operator_readme
    assert "coverage, next gate, result, duration" in pull_request_template
