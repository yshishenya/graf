from __future__ import annotations

import json
import os
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_ci_rejects_requested_sha_mismatch_before_running_pipeline() -> None:
    env = os.environ.copy()
    env["GRAF_CI_REQUESTED_SHA"] = "0" * 40
    result = subprocess.run(
        ["bash", "infra/scripts/ci-local.sh", "--fast"],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 2
    assert "ci_evidence_status=stale" in result.stderr


def test_ci_script_rejects_dirty_sha_evidence_and_marks_opt_in_diagnostic_ambiguous() -> None:
    script = (ROOT / "infra/scripts/ci-local.sh").read_text(encoding="utf-8")
    assert 'git status --porcelain --untracked-files=all' in script
    assert 'reason=dirty_worktree' in script
    assert 'reason=dirty_worktree_opt_in' in script
    assert 'evidence_status_override="ambiguous"' in script
    assert 'GRAF_CI_ALLOW_DIRTY' in script


def test_ci_records_requested_sha_mismatch_as_stale_evidence(tmp_path: Path) -> None:
    evidence = tmp_path / "stale.json"
    env = os.environ.copy()
    env["GRAF_CI_REQUESTED_SHA"] = "0" * 40
    env["GRAF_CI_EVIDENCE_PATH"] = str(evidence)
    result = subprocess.run(
        ["bash", "infra/scripts/ci-local.sh", "--fast"],
        cwd=ROOT,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 2
    assert evidence.exists()
    record = json.loads(evidence.read_text(encoding="utf-8"))
    assert record["status"] == "stale"
    assert record["reason"] == "target_changed"


def test_cd_requires_machine_readable_skip_ci_approval_before_checkout(tmp_path: Path) -> None:
    candidate = tmp_path / "candidate.json"
    candidate.write_text("{}\n", encoding="utf-8")
    result = subprocess.run(
        [
            "bash",
            "infra/scripts/cd-remote.sh",
            "--execute",
            "--branch",
            "master",
            "--candidate",
            str(candidate),
            "--skip-local-ci",
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode != 0
    assert "reason=skip_local_ci_approval_evidence_required" in result.stdout


def test_cd_exposes_reuse_contract_for_authoritative_full_evidence() -> None:
    script = (ROOT / "infra/scripts/cd-remote.sh").read_text(encoding="utf-8")
    assert "--evidence" in script
    assert "authoritative_full_evidence_invalid" in script
    assert "local_ci=authoritative_full_reused" in script
    assert "REUSE_AUTHORITATIVE_FULL=1" in script


def test_ci_runs_governance_suite_for_process_contract_changes() -> None:
    script = (ROOT / "infra/scripts/ci-local.sh").read_text(encoding="utf-8")
    assert 'run_step "governance tests" pytest -q tests/governance' in script
    assert '[[ "$path" == tests/governance/* ]] && has_governance_tests=1' in script


def test_ci_checks_shell_syntax_for_macos_changes_and_full_runs() -> None:
    script = (ROOT / "infra/scripts/ci-local.sh").read_text(encoding="utf-8")
    assert 'run_step "shell syntax" check_shell_syntax "$changed_list"' in script
    assert 'if [[ "$has_infra" -eq 1 || "$has_macos" -eq 1 ]]; then' in script
    assert script.count('run_step "shell syntax" check_shell_syntax "$changed_list"') >= 2


def test_github_fast_workflow_cancels_superseded_sha_and_validates_pr_metadata() -> None:
    workflow = (ROOT / ".github/workflows/governance-fast.yml").read_text(encoding="utf-8")
    assert "cancel-in-progress: true" in workflow
    assert "GRAF_CI_REQUESTED_SHA" in workflow
    assert "infra/scripts/ci-local.sh --fast" in workflow
    assert "validate-pr-metadata.py" in workflow
    assert "--expected-sha" in workflow


def test_dev_installer_parses_and_validates_both_loopback_origins() -> None:
    script = (ROOT / "apps/macos/Scripts/install-dev-app.sh").read_text(encoding="utf-8")
    assert "urlsplit" in script
    assert "GRAF_CABINET_BASE_URL" in script and "GRAF_UPLOAD_BASE_URL" in script
    assert "parsed.username" in script and "parsed.hostname" in script
