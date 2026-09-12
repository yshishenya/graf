from __future__ import annotations

import json
import os
import re
import shlex
import shutil
import subprocess
import sys
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
  [[ "$GRAF_TEST_DIFF_AVAILABLE" == "true" ]] || return 1
  printf '%s\n' "$GRAF_TEST_CHANGED_FILES"
}
calendar_performance_test_path() {
  printf '%s\n' "$GRAF_TEST_PERFORMANCE_PROOF"
}
run_step() {
  local name="$1"
  if [[ "$name" == "related behavior tests" ]]; then
    # Use the real selector while leaving actual product execution to its
    # separate focused acceptance. Drop only --run from this fixture call.
    shift 2
    local paths="$1"
    shift 2
    behavior_tests "$paths" "$@" || return $?
  fi
  if [[ "$name" == "server lint" || "$name" == "python compile" ]]; then
    printf 'static_command=%s\n' "$*"
  fi
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


def test_shared_cabinet_change_selects_unchanged_behavior_proofs() -> None:
    result = run_stubbed_ci(
        "apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js",
        "--fast",
    )

    assert result.returncode == 0, result.stdout
    assert "ci_stage=related behavior tests status=pass" in result.stdout
    plan = next(json.loads(line) for line in result.stdout.splitlines() if line.startswith('{"'))
    assert plan["tests"] == [
        "tests/contract/test_cabinet_static_assets_contract.py",
        "tests/contract/test_settings_ui_contract.py",
    ]
    assert plan["covered_tests"] == ["tests/unit/test_settings_view_models.py"]
    assert "ci_stage=server tests status=pass" in result.stdout
    assert "coverage=partial next_gate=full_before_release" in result.stdout


def behavior_repo(tmp_path: Path) -> Path:
    """Small real Git/pytest fixture, without product imports or a database."""
    for relative in ("infra/scripts/ci-local.sh", "scripts/ci-behavior-tests.py"):
        target = tmp_path / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / relative, target)
    for relative in (
        "contract/test_cabinet_static_assets_contract.py",
        "contract/test_settings_ui_contract.py",
        "unit/test_settings_view_models.py",
    ):
        target = tmp_path / "apps/server/tests" / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        name = ("test_cabinet_rail_node_harness_keeps_responsive_defaults_and_manual_state"
                if "static_assets" in relative else "test_fixture")
        target.write_text(f"def {name}():\n    assert True\n")
    (tmp_path / ".gitignore").write_text(".venv/\n.pytest_cache/\n__pycache__/\n")
    for args in (("init", "-q"), ("config", "user.email", "ci-contract@example.test"),
                 ("config", "user.name", "CI Contract"), ("add", "."), ("commit", "-qm", "base")):
        assert run("git", *args, cwd=tmp_path).returncode == 0
    return tmp_path / "infra/scripts/ci-local.sh"


def test_local_plan_and_fast_share_groups_without_repeating_changed_files() -> None:
    paths = (
        "apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js\n"
        "apps/server/src/twobrain_rec_server/cabinet/web_routes/settings.py\n"
        "apps/server/tests/contract/test_cabinet_static_assets_contract.py\n"
        "apps/server/tests/contract/test_settings_ui_contract.py\n"
        "unknown/other.bin"
    )
    local = run_stubbed_ci(paths, "--plan")
    fast = run_stubbed_ci(paths, "--fast")
    assert local.returncode == fast.returncode == 0
    local_plan = json.loads(local.stdout)
    fast_plan = next(json.loads(line) for line in fast.stdout.splitlines() if line.startswith('{"'))
    assert local_plan["groups"] == fast_plan["groups"]
    assert set(local_plan["tests"]) == set(fast_plan["tests"] + fast_plan["covered_tests"])
    assert local_plan["scope"] == "working_tree_diagnostic"
    assert local_plan["coverage"] == "partial"
    assert fast.stdout.count("ci_stage=related behavior tests status=pass") == 1
    assert "ci_stage=changed server tests" not in fast.stdout
    assert fast.stdout.index("ci_stage=python compile") < fast.stdout.index("ci_stage=related behavior tests")
    assert fast.stdout.index("ci_stage=related behavior tests") < fast.stdout.index("ci_stage=server tests")


def test_plan_is_read_only_and_preserves_real_git_rename_and_special_paths(tmp_path: Path) -> None:
    runner = behavior_repo(tmp_path)
    original = tmp_path / "apps/server/src/twobrain_rec_server/cabinet/templates/old file.html"
    original.parent.mkdir(parents=True)
    original.write_text("before\n")
    assert run("git", "add", ".", cwd=tmp_path).returncode == 0
    assert run("git", "commit", "-qm", "source", cwd=tmp_path).returncode == 0
    base = run("git", "rev-parse", "HEAD", cwd=tmp_path).stdout.strip()
    renamed = original.with_name("меню $() `touch injected` ' \".html")
    original.rename(renamed)
    spies = tmp_path / ".venv/bin"
    spies.mkdir(parents=True)
    for name in ("docker", "uv", "pytest", "node", "curl", "gh", "swift"):
        executable = spies / name
        executable.write_text("#!/bin/sh\ntouch injected\nexit 99\n")
        executable.chmod(0o755)
    before = set(tmp_path.rglob("*"))
    result = run(str(runner), "--plan", cwd=tmp_path,
                 env={"GRAF_CI_BASE_REF": base, "PATH": f"{spies}:{os.environ['PATH']}"})
    assert result.returncode == 0, result.stdout
    plan = json.loads(result.stdout)
    assert plan["changed_paths"] == sorted([str(original.relative_to(tmp_path)), str(renamed.relative_to(tmp_path))])
    assert [group["name"] for group in plan["groups"]] == ["cabinet-shell", "settings"]
    assert plan["dirty_worktree"] is True
    assert len(plan["tests"]) == 3
    assert set(tmp_path.rglob("*")) == before
    assert "ci_local_result" not in result.stdout and "ci_evidence_path" not in result.stdout
    invalid = renamed.with_name("line\nbreak.html")
    renamed.rename(invalid)
    rejected = run(str(runner), "--plan", cwd=tmp_path, env={"GRAF_CI_BASE_REF": base})
    assert rejected.returncode != 0
    assert "unsupported_changed_path" in rejected.stdout
    assert "ci_focused_result=pass" not in rejected.stdout


@pytest.mark.parametrize("condition", ["missing", "empty", "rail_removed"])
def test_missing_mandatory_behavior_proof_fails_before_execution(tmp_path: Path, condition: str) -> None:
    runner = behavior_repo(tmp_path)
    target = tmp_path / "apps/server/tests/contract/test_cabinet_static_assets_contract.py"
    if condition == "missing":
        target.unlink()
    else:
        target.write_text("" if condition == "empty" else "def test_other():\n    pass\n")
    result = run(str(runner), "--focused", cwd=tmp_path, env={"GRAF_CI_BASE_REF": "HEAD"})
    assert result.returncode != 0
    assert "required_test_" in result.stdout
    assert "server_venv_missing" not in result.stdout
    assert not (tmp_path / "apps/server/.venv").exists()


@pytest.mark.parametrize("condition", ["pass", "skip", "deselect", "failure"])
def test_focused_requires_executed_proof_despite_pytest_filters(tmp_path: Path, condition: str) -> None:
    runner = behavior_repo(tmp_path)
    target = tmp_path / "apps/server/tests/contract/test_cabinet_static_assets_contract.py"
    original = target.read_text()
    if condition == "skip":
        target.write_text("import pytest\n@pytest.mark.skip(reason='fixture')\n" + original)
    elif condition == "failure":
        target.write_text(original.replace("assert True", "assert False"))
    if condition == "deselect":
        (target.parent / "conftest.py").write_text(
            "def pytest_collection_modifyitems(items):\n    items[:] = [i for i in items if 'rail_node' not in i.name]\n"
        )
    source = tmp_path / "apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js"
    source.parent.mkdir(parents=True)
    source.write_text("// fixture\n")
    python = tmp_path / "apps/server/.venv/bin/python"
    python.parent.mkdir(parents=True)
    python.write_text(f'#!/bin/sh\nexec {shlex.quote(sys.executable)} "$@"\n')
    python.chmod(0o755)
    result = run(str(runner), "--focused", cwd=tmp_path, env={
        "GRAF_CI_BASE_REF": "HEAD", "PYTEST_ADDOPTS": "-k should_never_select_anything",
    })
    if condition == "pass":
        assert result.returncode == 0, result.stdout
        assert "3 passed" in result.stdout
        assert "ci_focused_result=pass" in result.stdout
    else:
        assert result.returncode != 0, result.stdout
        assert "ci_focused_result=fail" in result.stdout
        expected = {"skip": "required_behavior_test_skipped", "deselect": "required_test_file_not_executed",
                    "failure": "AssertionError"}
        assert expected[condition] in result.stdout
    assert not (tmp_path / ".dev/ci-evidence").exists()


def test_focused_empty_missing_runtime_and_bad_base_do_not_pass(tmp_path: Path) -> None:
    runner = behavior_repo(tmp_path)
    (tmp_path / "unknown.bin").write_text("fixture\n")
    empty = run(str(runner), "--focused", cwd=tmp_path, env={"GRAF_CI_BASE_REF": "HEAD"})
    assert empty.returncode == 2 and "no_focused_tests_selected" in empty.stdout
    invalid = run(str(runner), "--plan", cwd=tmp_path, env={"GRAF_CI_BASE_REF": "f" * 40})
    assert invalid.returncode != 0 and "invalid_diff_or_explicit_base" in invalid.stdout
    missing = run(str(runner), "--plan", cwd=tmp_path, env={"GRAF_CI_BASE_REF": ""})
    assert missing.returncode == 0 and json.loads(missing.stdout)["diff_available"] is False
    target = tmp_path / "apps/server/tests/contract/test_settings_ui_contract.py"
    target.write_text(target.read_text() + "\n")
    runtime = run(str(runner), "--focused", cwd=tmp_path, env={"GRAF_CI_BASE_REF": "HEAD"})
    assert runtime.returncode != 0 and "server_venv_missing" in runtime.stdout
    explicit_fast = run_stubbed_ci("", "--fast", diff_available=False, env={"GRAF_CI_BASE_REF": "f" * 40})
    assert explicit_fast.returncode != 0 and "ci_stage=" not in explicit_fast.stdout


@pytest.mark.parametrize("mode", ["--fast", "--full"])
@pytest.mark.parametrize("fail_stage", ["", "server lint", "python compile"])
def test_server_static_checks_precede_tests_and_fail_fast(mode: str, fail_stage: str) -> None:
    result = run_stubbed_ci(
        "apps/server/src/twobrain_rec_server/calendar/matching.py\n"
        "apps/server/tests/contract/test_ci_cd_contract.py",
        mode, fail_stage=fail_stage,
    )
    stages = re.findall(r"ci_stage=(.*?) status=", result.stdout)
    server_tests = {"server tests", "changed server tests", "calendar performance proof"}
    assert stages.count("server lint") == 1
    assert "static_command=server lint bash -c cd apps/server && PYTHONPATH=src uv run --extra dev ruff check ." in result.stdout
    if fail_stage != "server lint":
        assert stages.count("python compile") == 1
        assert "static_command=python compile python3 -m compileall -q apps/server/src apps/server/tests apps/server/scripts" in result.stdout
    if fail_stage:
        assert result.returncode == 17, result.stdout
        assert not server_tests.intersection(stages)
        assert result.stdout.count("ci_local_result=fail") == 1
    else:
        assert result.returncode == 0, result.stdout
        selected = server_tests if mode == "--fast" else {"server tests"}
        assert selected.issubset(stages)
        assert stages.index("server lint") < stages.index("python compile")
        assert all(stages.index("python compile") < stages.index(stage) for stage in selected)


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


@pytest.mark.parametrize("command", ["diff", "ls-files"])
@pytest.mark.parametrize("mode", ["--plan", "--focused"])
def test_git_collection_failure_never_selects_partial_behavior_tests(command: str, mode: str) -> None:
    script = r'''
source "$1"
merge_base_commit() { printf 'HEAD\n'; }
git() {
  case "$*" in
    *diff*--name-only*)
      [[ "$GRAF_TEST_GIT_FAILURE" != "diff" ]] || return 128
      printf '%s\0' 'apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js'
      ;;
    *ls-files*--others*) return 128 ;;
    *) command git "$@" ;;
  esac
}
behavior_tests() { printf 'unexpected_behavior_selection\n'; }
focused_main "$2"
'''
    result = run("bash", "-c", script, "contract", str(LOCAL_CI), mode,
                 env={"GRAF_TEST_GIT_FAILURE": command, "GRAF_CI_BASE_REF": ""})

    assert result.returncode == 2, result.stdout
    assert "ci_selection_error=invalid_diff_or_explicit_base" in result.stdout
    assert "unexpected_behavior_selection" not in result.stdout


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
            if "infra/scripts/ci-local.sh" in line and not any(mode in line for mode in ("--fast", "--full", "--plan", "--focused")):
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
    flow = (ROOT / "docs/agent-guidance/spec-kit-flow.md").read_text(encoding="utf-8")
    for lane in ("Active Spec Kit slice", "Significant feature / architecture", "High-risk product area"):
        row = next(line for line in flow.splitlines() if line.startswith(f"| {lane} |"))
        assert "GitHub `governance-fast`" in row
        assert "ci-local.sh --fast" not in row
    assert "then the fast lane before the PR" not in release_guidance
    assert "finish with `infra/scripts/ci-local.sh --fast`" not in release_guidance
    assert "ready slice or PR: required GitHub `governance-fast`" in release_guidance
    assert "обязательный authoritative PR" in pull_request_template
    assert "только ручная диагностика/offline fallback" in pull_request_template


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
