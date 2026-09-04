from __future__ import annotations

import json
import os
import re
import subprocess
import uuid
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[4]
LOCAL_CI = ROOT / "infra/scripts/ci-local.sh"
REMOTE_CD = ROOT / "infra/scripts/cd-remote.sh"
FULL_CI_WORKFLOW = ROOT / ".github/workflows/release-full.yml"
FULL_CI_VALIDATOR = ROOT / "scripts/validate-full-ci-workflow.py"
MACOS_DIAGNOSTIC_WORKFLOW = ROOT / ".github/workflows/macos-diagnostic.yml"
MACOS_TEST_RUNNER = ROOT / "apps/macos/Scripts/run-swift-tests.sh"
SIGNING_CUSTODY_TEST = ROOT / "apps/macos/Installer/Scripts/test-release-signing-custody.sh"


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
uname() {
  # The lane-selection contract is platform-independent; model the macOS
  # branch explicitly so the contract is deterministic on GitHub's Linux runner.
  printf 'Darwin\n'
}
git() {
  # The fixture supplies a synthetic classified diff. Keep the checkout
  # snapshot clean so assertions exercise lane selection, not this test file's
  # own uncommitted edit.
  if [[ "$*" == "status --porcelain --untracked-files=all" ]]; then
    return 0
  fi
  command git "$@"
}
changed_files() {
  [[ "$GRAF_TEST_DIFF_AVAILABLE" == "true" ]] || return 9
  printf '%s\n' "$GRAF_TEST_CHANGED_FILES"
}
calendar_performance_test_path() {
  printf '%s\n' "$GRAF_TEST_PERFORMANCE_PROOF"
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
            "GRAF_TEST_PERFORMANCE_PROOF": (
                "tests/integration/test_calendar_auto_context_match.py"
            ),
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
        ("docs/agent-guidance/release-and-validation.md", "governance"),
        ("AGENTS.md", "governance"),
        (".github/pull_request_template.md", "governance"),
        ("docs/deployments/2brain-rec/release-v1.md", "infra"),
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


def test_macos_xctest_process_boundary_matches_local_and_github() -> None:
    command = "bash apps/macos/Scripts/run-swift-tests.sh"
    local_ci = LOCAL_CI.read_text(encoding="utf-8")
    workflow = FULL_CI_WORKFLOW.read_text(encoding="utf-8")
    runner = MACOS_TEST_RUNNER.read_text(encoding="utf-8")

    assert local_ci.count(command) == 2
    assert command in workflow
    assert 'swift-version: "6.0.3"' in workflow
    assert "unset _SWIFTPM_SKIP_TESTS_LIST" in runner
    assert "swift test --package-path apps/macos list" in runner
    assert '[[ -z "$test_list" ]]' in runner
    assert "swift test --package-path apps/macos --skip-build" in runner
    assert "--parallel" not in runner


def test_macos_signing_scan_uses_native_runner_tooling() -> None:
    custody = SIGNING_CUSTODY_TEST.read_text(encoding="utf-8")

    assert "/usr/bin/grep -ERnI -e" in custody
    assert "if rg " not in custody


def test_macos_xctest_runner_rejects_empty_discovery(tmp_path: Path) -> None:
    fake_swift = tmp_path / "swift"
    fake_swift.write_text("#!/bin/sh\nexit 0\n", encoding="utf-8")
    fake_swift.chmod(0o755)

    result = run(str(MACOS_TEST_RUNNER), env={"PATH": f"{tmp_path}:{os.environ['PATH']}"})

    assert result.returncode == 1
    assert "no tests discovered" in result.stdout


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


@pytest.mark.parametrize(
    "changed_file",
    [
        "apps/server/src/twobrain_rec_server/api/app.py",
        "apps/server/src/twobrain_rec_server/auth/sessions.py",
        "apps/macos/Sources/App.swift",
        "infra/scripts/ci-local.sh",
        "AGENTS.md",
        "docs/agent-guidance/release-and-validation.md",
    ],
)
def test_high_risk_and_shared_diffs_report_partial_fast_coverage(changed_file: str) -> None:
    result = run_stubbed_ci(changed_file, "--fast")

    assert result.returncode == 0, result.stdout
    assert "effective=fast" in result.stdout
    assert "coverage=partial next_gate=full_before_release" in result.stdout
    assert "reason=high_risk_or_shared_path" in result.stdout


def test_deployment_evidence_runs_its_bounded_scanner() -> None:
    result = run_stubbed_ci(
        "docs/deployments/2brain-rec/release-v2026.08.31.2.md",
        "--fast",
    )

    assert result.returncode == 0, result.stdout
    assert "effective=fast components=infra" in result.stdout
    assert "coverage=partial next_gate=full_before_release" in result.stdout
    assert "ci_stage=deployment evidence scan status=pass" in result.stdout


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


def test_removed_server_test_uses_bounded_unit_fallback() -> None:
    result = run_stubbed_ci("apps/server/tests/contract/test_removed.py", "--fast")

    assert result.returncode == 0, result.stdout
    assert "reason=removed_server_test_path" in result.stdout
    assert "effective=fast components=server" in result.stdout
    assert "coverage=partial next_gate=full_before_release" in result.stdout
    assert "ci_stage=server tests status=pass" in result.stdout
    assert "ci_stage=changed server tests status=pass" not in result.stdout


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


def test_whitespace_check_covers_commits_since_the_merge_base(tmp_path: Path) -> None:
    run("git", "init", "-q", cwd=tmp_path)
    run("git", "config", "user.email", "ci-contract@example.test", cwd=tmp_path)
    run("git", "config", "user.name", "CI Contract", cwd=tmp_path)
    tracked = tmp_path / "tracked.txt"
    tracked.write_text("clean\n", encoding="utf-8")
    run("git", "add", "tracked.txt", cwd=tmp_path)
    run("git", "commit", "-qm", "base", cwd=tmp_path)
    tracked.write_text("trailing whitespace \n", encoding="utf-8")
    run("git", "add", "tracked.txt", cwd=tmp_path)
    run("git", "commit", "-qm", "bad whitespace", cwd=tmp_path)

    result = run(
        "bash",
        "-c",
        'source "$1"; repo_root="$2"; check_diff_whitespace',
        "contract",
        str(LOCAL_CI),
        str(tmp_path),
        env={"GRAF_CI_BASE_REF": "HEAD~1"},
    )

    assert result.returncode != 0
    assert "trailing whitespace" in result.stdout


def test_shell_syntax_check_includes_untracked_changed_scripts(tmp_path: Path) -> None:
    valid_script = tmp_path / "infra/scripts/a-valid.sh"
    invalid_script = tmp_path / "infra/scripts/z-invalid.sh"
    valid_script.parent.mkdir(parents=True)
    valid_script.write_text("#!/usr/bin/env bash\ntrue\n", encoding="utf-8")
    invalid_script.write_text("if then\n", encoding="utf-8")
    run("git", "init", "-q", cwd=tmp_path)
    run("git", "add", "infra/scripts/a-valid.sh", cwd=tmp_path)

    result = run(
        "bash",
        "-c",
        'source "$1"; repo_root="$2"; cd "$repo_root"; check_shell_syntax "$3"',
        "contract",
        str(LOCAL_CI),
        str(tmp_path),
        "infra/scripts/z-invalid.sh",
    )

    assert result.returncode != 0
    assert "syntax error" in result.stdout


def test_whitespace_check_includes_untracked_non_shell_files(tmp_path: Path) -> None:
    run("git", "init", "-q", cwd=tmp_path)
    untracked = tmp_path / "docs/new-guide.md"
    untracked.parent.mkdir(parents=True)
    untracked.write_text("trailing whitespace \n", encoding="utf-8")

    result = run(
        "bash",
        "-c",
        'source "$1"; repo_root="$2"; check_diff_whitespace "$3"',
        "contract",
        str(LOCAL_CI),
        str(tmp_path),
        "docs/new-guide.md",
    )

    assert result.returncode != 0
    assert "trailing whitespace" in result.stdout


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


def test_missing_calendar_performance_proof_is_not_passed_to_pytest() -> None:
    result = run_stubbed_ci(
        "apps/server/src/twobrain_rec_server/calendar/matching.py\n"
        "apps/server/tests/integration/test_removed.py",
        "--fast",
        env={"GRAF_TEST_PERFORMANCE_PROOF": "tests/integration/test_removed.py"},
    )

    assert result.returncode == 0, result.stdout
    assert "ci_stage=server tests status=pass" in result.stdout
    assert "ci_stage=calendar performance proof" not in result.stdout
    assert "coverage=partial next_gate=full_before_release" in result.stdout


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


def test_local_full_remains_diagnostic_with_candidate_file(tmp_path: Path) -> None:
    token = uuid.uuid4().hex[:12]
    source_sha = subprocess.check_output(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True
    ).strip()
    passed_candidate = tmp_path / "passed-candidate.json"
    failed_candidate = tmp_path / "failed-candidate.json"
    passed_id = f"rc-20260901T000001Z-{token}"
    failed_id = f"rc-20260901T000002Z-{token}"
    passed_candidate.write_text(
        json.dumps({"candidate_id": passed_id, "source_sha": source_sha}) + "\n",
        encoding="utf-8",
    )
    failed_candidate.write_text(
        json.dumps({"candidate_id": failed_id, "source_sha": source_sha}) + "\n",
        encoding="utf-8",
    )
    passed = run_stubbed_ci(
        "",
        "--full",
        env={
            "GRAF_CI_CANDIDATE_ID": passed_id,
            "GRAF_CI_CANDIDATE_FILE": str(passed_candidate),
            "GRAF_CI_EVIDENCE_PATH": str(tmp_path / "passed-evidence.json"),
        },
    )
    diagnostic = run_stubbed_ci("", "--full")
    failed = run_stubbed_ci(
        "",
        "--full",
        fail_stage="server tests",
        env={
            "GRAF_CI_CANDIDATE_ID": failed_id,
            "GRAF_CI_CANDIDATE_FILE": str(failed_candidate),
            "GRAF_CI_EVIDENCE_PATH": str(tmp_path / "failed-evidence.json"),
        },
    )

    assert passed.returncode == 0, passed.stdout
    assert "ci_lane requested=full effective=full" in passed.stdout
    assert "next_gate=full_in_progress" in passed.stdout
    assert "ci_local_result=pass mode=full" in passed.stdout
    assert "next_gate=full_diagnostic_only" in passed.stdout
    assert "authoritative-full" not in passed.stdout
    passed_evidence = json.loads((tmp_path / "passed-evidence.json").read_text(encoding="utf-8"))
    assert passed_evidence["candidate_id"] == passed_id
    assert "authoritative_full" not in passed_evidence
    assert (tmp_path / "passed-evidence.json").name != f"authoritative-{passed_id}.json"

    blocked_path = tmp_path / f"authoritative-{passed_id}.json"
    rewritten = run_stubbed_ci(
        "",
        "--full",
        env={
            "GRAF_CI_CANDIDATE_ID": passed_id,
            "GRAF_CI_CANDIDATE_FILE": str(passed_candidate),
            "GRAF_CI_EVIDENCE_PATH": str(blocked_path),
        },
    )
    assert rewritten.returncode == 0, rewritten.stdout
    assert not blocked_path.exists()
    assert "reason=local_full_never_authoritative" in rewritten.stdout

    assert diagnostic.returncode == 0, diagnostic.stdout
    assert "ci_local_result=pass mode=full" in diagnostic.stdout
    assert "next_gate=full_diagnostic_only" in diagnostic.stdout

    assert failed.returncode == 17
    assert "ci_lane requested=full effective=full" in failed.stdout
    assert "next_gate=full_in_progress" in failed.stdout
    assert "ci_local_result=fail mode=full" in failed.stdout
    assert "next_gate=full_failed" in failed.stdout
    assert "release_ready" not in failed.stdout


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
    quickstart = (ROOT / "specs/211-optimize-ci-cd/quickstart.md").read_text(encoding="utf-8")

    assert "always remains bounded" in release_guidance
    assert "never changes to `effective=full`" in operator_readme
    assert "coverage, next gate, result, duration" in pull_request_template
    assert 'git diff --check "$(git merge-base origin/master HEAD)" HEAD' in quickstart
    assert 'bash -n "$script"' in quickstart


def test_github_full_workflow_contract_is_self_validating() -> None:
    result = run("python3", str(FULL_CI_VALIDATOR), "--self-test")

    assert result.returncode == 0, result.stdout
    assert "full-ci-workflow self-test: OK" in result.stdout


def test_github_full_workflow_is_manual_exact_sha_and_metadata_only() -> None:
    workflow = FULL_CI_WORKFLOW.read_text(encoding="utf-8")

    assert "workflow_dispatch:" in workflow
    assert "pull_request:" not in workflow
    assert "candidate_id:" in workflow and "requested_sha:" in workflow
    assert "cancel-in-progress: false" in workflow
    assert "permissions:\n  contents: read\n  actions: read" in workflow
    assert "ref: ${{ inputs.requested_sha }}" in workflow
    assert '[[ "${master_sha,,}" == "${REQUESTED_SHA,,}" ]]' in workflow
    assert "actions/upload-artifact@v4" in workflow
    assert "actions/download-artifact@v4" in workflow
    assert "candidate_already_reserved" in workflow
    assert "graf-full-lock-${{ steps.identity.outputs.artifact_key }}" in workflow
    assert "graf-full-ci-${{ needs.reserve.outputs.artifact_key }}" in workflow
    assert 'result_path="$RUNNER_TEMP/server-result.json"' in workflow
    assert 'path: ${{ runner.temp }}/server-result.json' in workflow
    assert 'result_path="$RUNNER_TEMP/macos-result.json"' in workflow
    assert 'path: ${{ runner.temp }}/macos-result.json' in workflow
    assert 'expected = {"server-result.json": "server", "macos-result.json": "macos_app"}' in workflow
    assert '--artifact "server-result=$component_dir/server-result.json"' in workflow
    assert '--artifact "macos-result=$component_dir/macos-result.json"' in workflow
    assert "timeout-minutes: 10" in workflow
    assert "timeout-minutes: 60" in workflow
    assert "timeout-minutes: 45" in workflow
    assert '[[ "$(uname -m)" == "arm64" ]]' in workflow
    assert '"skipped_gates": [],' in workflow
    assert "--authoritative-full" in workflow
    assert "--component-sha" in workflow
    assert "gh release" not in workflow
    assert "cd-remote.sh" not in workflow


def test_macos_diagnostic_workflow_is_exact_sha_and_non_authoritative() -> None:
    workflow = MACOS_DIAGNOSTIC_WORKFLOW.read_text(encoding="utf-8")

    assert "workflow_dispatch:" in workflow
    assert "requested_sha:" in workflow
    assert "pull_request:" not in workflow
    assert "candidate_id:" not in workflow
    assert "permissions:\n  contents: read" in workflow
    assert "ref: ${{ inputs.requested_sha }}" in workflow
    assert "persist-credentials: false" in workflow
    assert '[[ "$REQUESTED_SHA" =~ ^[0-9a-f]{40}$ ]]' in workflow
    assert '[[ "$checkout_sha" == "$REQUESTED_SHA" ]]' in workflow
    assert not re.search(r"\$\{[^}\n]*,,[^}\n]*\}", workflow)
    assert "runs-on: macos-14" in workflow
    assert 'swift-version: "6.0.3"' in workflow
    assert "bash apps/macos/Scripts/run-swift-tests.sh" in workflow
    assert "run_local_postgres_tests.sh" not in workflow
    assert "emit-ci-evidence.py" not in workflow
    assert "authoritative-full" not in workflow
    assert "upload-artifact" not in workflow
    assert "cd-remote.sh" not in workflow
    assert "secrets." not in workflow
    assert "environment:" not in workflow
    assert "id-token:" not in workflow
