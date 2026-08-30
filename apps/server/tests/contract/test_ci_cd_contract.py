from __future__ import annotations

import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[4]
LOCAL_CI = ROOT / "infra/scripts/ci-local.sh"
RECEIPT = ROOT / "infra/scripts/ci-receipt.py"
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


def run_stubbed_ci(changed_files: str, mode: str, *, fail_stage: str = "") -> subprocess.CompletedProcess[str]:
    script = r'''
source "$1"
changed_files() { printf '%s\n' "$GRAF_TEST_CHANGED_FILES"; }
run_step() {
  local name="$1"
  if [[ "$name" == "server tests" ]]; then
    printf 'server_test_gate=%s\n' "$4"
    printf 'collection_count=1 collection_digest=%s\n' "$(printf 'a%.0s' {1..64})" > "$server_log"
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
        env={"GRAF_TEST_CHANGED_FILES": changed_files, "GRAF_TEST_FAIL_STAGE": fail_stage},
    )


def git(repo: Path, *args: str) -> None:
    subprocess.run(("git", *args), cwd=repo, check=True, capture_output=True)


def make_receipt_repo(tmp_path: Path) -> tuple[Path, Path]:
    repo = tmp_path / "repo"
    paths = (
        "infra/scripts/ci-local.sh",
        "infra/scripts/ci-receipt.py",
        "apps/server/scripts/run_local_postgres_tests.sh",
        "apps/server/uv.lock",
        "apps/macos/Package.resolved",
        "apps/server/tests/unit/test_sample.py",
        "apps/macos/Tests/SampleTests.swift",
    )
    for relative in paths:
        target = repo / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        if relative == "infra/scripts/ci-receipt.py":
            shutil.copy2(RECEIPT, target)
        else:
            target.write_text(f"fixture:{relative}\n", encoding="utf-8")
    git(repo, "init", "-q")
    git(repo, "config", "user.email", "ci-contract@example.test")
    git(repo, "config", "user.name", "CI Contract")
    git(repo, "add", ".")
    git(repo, "commit", "-qm", "fixture")
    helper = repo / "infra/scripts/ci-receipt.py"
    start_snapshot = tmp_path / "full-ci-start.json"
    captured = run("python3", str(helper), "snapshot", "--output", str(start_snapshot), cwd=repo)
    assert captured.returncode == 0, captured.stdout
    evidence = tmp_path / "full-ci-evidence.tsv"
    stages = ["macOS legacy audio architecture guard"]
    if os.uname().sysname == "Darwin":
        stages.extend(("macOS Swift build", "macOS Swift tests", "macOS contract validation"))
    stages.extend(
        (
            "server tests",
            "server lint",
            "python compile",
            "rls hardening validation boundary",
            "production compose config",
            "deployment evidence scan",
            "active CI documentation consistency",
        )
    )
    evidence.write_text("".join(f"{stage}\tpass\n" for stage in stages), encoding="utf-8")
    evidence.chmod(0o600)
    created = run(
        "python3",
        str(helper),
        "create",
        "--started-at-epoch",
        "1",
        "--collection-count",
        "3",
        "--collection-digest",
        "a" * 64,
        "--evidence-file",
        str(evidence),
        "--start-snapshot",
        str(start_snapshot),
        cwd=repo,
    )
    assert created.returncode == 0, created.stdout
    path_result = run("python3", str(helper), "path", cwd=repo)
    assert path_result.returncode == 0
    return repo, Path(path_result.stdout.strip())


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
        ("apps/server/src/twobrain_rec_server/api/app.py", "full"),
        ("apps/server/src/twobrain_rec_server/calendar/matching.py", "server"),
        ("apps/server/src/twobrain_rec_server/domain/statuses.py", "server"),
        ("apps/server/src/twobrain_rec_server/auth/sessions.py", "full"),
        ("apps/server/src/twobrain_rec_server/api/auth.py", "full"),
        ("apps/server/tests/unit/test_sample.py", "server"),
        ("apps/macos/Sources/App.swift", "macos"),
        ("docs/user-guide.md", "docs"),
        ("docs/agent-guidance/release-and-validation.md", "full"),
        ("docs/deployments/2brain-rec/release-v1.md", "full"),
        ("apps/macos/Package.resolved", "full"),
        ("infra/scripts/ci-local.sh", "full"),
        ("apps/server/tests/integration/test_sample.py", "full"),
        ("unknown/surface.bin", "full"),
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


def test_fast_lane_escalates_unknown_paths_to_full() -> None:
    result = run_stubbed_ci("unknown/surface.bin", "--fast")

    assert result.returncode == 0, result.stdout
    assert "ci_fast_escalation reason=high_risk_or_unknown_path path=unknown/surface.bin" in result.stdout
    assert "ci_lane requested=fast effective=full components=full" in result.stdout


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
    *"diff --name-only"*) return 9 ;;
    *) command git "$@" ;;
  esac
}
changed_files
'''
    result = run("bash", "-c", script, "contract", str(LOCAL_CI))

    assert result.returncode != 0


def test_fast_calendar_lane_forwards_required_performance_gate() -> None:
    result = run_stubbed_ci(
        "apps/server/src/twobrain_rec_server/calendar/matching.py",
        "--fast",
    )

    assert result.returncode == 0, result.stdout
    assert "performance_gate=required" in result.stdout
    assert "server_test_gate=required" in result.stdout


def test_failing_stage_emits_one_final_failure_and_no_receipt() -> None:
    result = run_stubbed_ci(
        "apps/server/src/twobrain_rec_server/api/app.py",
        "--fast",
        fail_stage="server tests",
    )

    assert result.returncode == 17
    assert result.stdout.count("ci_local_result=fail") == 1
    assert "ci_receipt_result=" not in result.stdout


def test_receipt_create_and_validate_for_the_same_clean_inputs(tmp_path: Path) -> None:
    repo, receipt_path = make_receipt_repo(tmp_path)
    result = run("python3", "infra/scripts/ci-receipt.py", "validate", cwd=repo)

    assert result.returncode == 0, result.stdout
    assert "ci_receipt_result=valid" in result.stdout
    assert receipt_path.is_relative_to(repo / ".git")
    assert receipt_path.stat().st_mode & 0o777 == 0o600
    assert str(repo) not in receipt_path.read_text(encoding="utf-8")


def test_receipt_rejects_dirty_and_stale_state(tmp_path: Path) -> None:
    repo, receipt_path = make_receipt_repo(tmp_path)
    (repo / "untracked.txt").write_text("dirty\n", encoding="utf-8")
    dirty = run("python3", "infra/scripts/ci-receipt.py", "validate", cwd=repo)
    assert dirty.returncode == 1
    assert "reason=dirty_worktree" in dirty.stdout
    (repo / "untracked.txt").unlink()

    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    receipt["started_at_epoch"] = 1
    receipt["created_at_epoch"] = 2
    receipt["duration_seconds"] = 1
    receipt_path.write_text(json.dumps(receipt), encoding="utf-8")
    stale = run(
        "python3",
        "infra/scripts/ci-receipt.py",
        "validate",
        "--max-age-seconds",
        "1",
        cwd=repo,
    )
    assert stale.returncode == 1
    assert "reason=stale" in stale.stdout


def test_receipt_create_rejects_incomplete_stage_evidence(tmp_path: Path) -> None:
    repo, receipt_path = make_receipt_repo(tmp_path)
    receipt_path.unlink()
    evidence = tmp_path / "incomplete-evidence.tsv"
    evidence.write_text("server tests\tpass\n", encoding="utf-8")
    evidence.chmod(0o600)

    result = run(
        "python3",
        "infra/scripts/ci-receipt.py",
        "create",
        "--started-at-epoch",
        "1",
        "--collection-count",
        "3",
        "--collection-digest",
        "a" * 64,
        "--evidence-file",
        str(evidence),
        "--start-snapshot",
        str(tmp_path / "full-ci-start.json"),
        cwd=repo,
    )

    assert result.returncode == 1
    assert "reason=evidence_invalid" in result.stdout


def test_receipt_create_rejects_a_commit_after_the_start_snapshot(tmp_path: Path) -> None:
    repo, receipt_path = make_receipt_repo(tmp_path)
    receipt_path.unlink()
    (repo / "changed-after-start.txt").write_text("new commit\n", encoding="utf-8")
    git(repo, "add", "changed-after-start.txt")
    git(repo, "commit", "-qm", "change after start")

    result = run(
        "python3",
        "infra/scripts/ci-receipt.py",
        "create",
        "--started-at-epoch",
        "1",
        "--collection-count",
        "3",
        "--collection-digest",
        "a" * 64,
        "--evidence-file",
        str(tmp_path / "full-ci-evidence.tsv"),
        "--start-snapshot",
        str(tmp_path / "full-ci-start.json"),
        cwd=repo,
    )

    assert result.returncode == 1
    assert "reason=snapshot_mismatch" in result.stdout


@pytest.mark.parametrize(
    ("mutator", "reason"),
    [
        (lambda value: value.update(version=99), "unsupported_version"),
        (lambda value: value.update(result="fail"), "not_pass"),
        (lambda value: value.update(commit_sha="0" * 40), "commit_mismatch"),
        (lambda value: value.update(tree_sha="0" * 40), "tree_mismatch"),
        (lambda value: value.update(runner_inputs={}), "runner_mismatch"),
        (lambda value: value.update(dependency_inputs={}), "dependency_mismatch"),
        (lambda value: value.update(test_surface_digest="0" * 64), "test_surface_mismatch"),
        (lambda value: value.update(toolchain={}), "toolchain_mismatch"),
        (lambda value: value.update(completed_stages=[]), "evidence_invalid"),
        (lambda value: value.update(server_collection_digest="bad"), "collection_invalid"),
        (lambda value: value.update(started_at_epoch=value["created_at_epoch"] + 1), "malformed"),
        (lambda value: value.update(duration_seconds=value["duration_seconds"] + 1), "malformed"),
        (lambda value: value.update(created_at_epoch=value["created_at_epoch"] + 3600), "malformed"),
    ],
)
def test_receipt_rejects_every_bound_input_mismatch(tmp_path: Path, mutator, reason: str) -> None:
    repo, receipt_path = make_receipt_repo(tmp_path)
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    mutator(receipt)
    receipt_path.write_text(json.dumps(receipt), encoding="utf-8")

    result = run("python3", "infra/scripts/ci-receipt.py", "validate", cwd=repo)

    assert result.returncode == 1
    assert f"reason={reason}" in result.stdout


def test_receipt_rejects_missing_and_malformed_files(tmp_path: Path) -> None:
    repo, receipt_path = make_receipt_repo(tmp_path)
    receipt_path.unlink()
    missing = run("python3", "infra/scripts/ci-receipt.py", "validate", cwd=repo)
    assert missing.returncode == 1
    assert "reason=missing" in missing.stdout

    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.write_text("not json", encoding="utf-8")
    malformed = run("python3", "infra/scripts/ci-receipt.py", "validate", cwd=repo)
    assert malformed.returncode == 1
    assert "reason=malformed" in malformed.stdout


def test_cd_dry_run_declares_receipt_reuse_or_full_fallback() -> None:
    result = run(str(REMOTE_CD), "--dry-run", "--branch", "211-optimize-ci-cd")

    assert result.returncode == 0, result.stdout
    assert "local_ci=valid_full_receipt_or_full_fallback" in result.stdout
    assert "steps=clean_worktree,branch_sync,pinned_sha,local_ci,remote_fetch,backup" in result.stdout


def test_cd_execute_preserves_release_gates_around_receipt_reuse() -> None:
    script = REMOTE_CD.read_text(encoding="utf-8")

    clean = script.index('git status --porcelain --untracked-files=all')
    sync = script.index('git fetch origin "$BRANCH"')
    validate = script.index('ci-receipt.py validate')
    fallback = script.index('ci-local.sh --full')
    remote = script.index('remote_script=$(cat')
    assert clean < sync < validate < fallback < remote
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
