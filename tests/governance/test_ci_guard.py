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
    assert 'dirty_worktree=1' in script
    assert 'through the selected stages' in script


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


def test_ci_runs_final_cleanliness_before_success_evidence() -> None:
    script = (ROOT / "infra/scripts/ci-local.sh").read_text(encoding="utf-8")
    assert "check_final_cleanliness()" in script
    assert 'run_step "final cleanliness" check_final_cleanliness' in script
    assert script.index('run_step "final cleanliness" check_final_cleanliness') < script.rindex('pipeline_result="pass"')
    assert "initial_tree_state=\"$(git status --porcelain --untracked-files=all)\"" in script
    assert '[[ "$status" != "$initial_tree_state" ]]' in script


def test_full_without_candidate_is_diagnostic_only() -> None:
    script = (ROOT / "infra/scripts/ci-local.sh").read_text(encoding="utf-8")
    assert 'next_gate="full_diagnostic_only"' in script
    assert 'next_gate="release_ready"' in script
    assert '[[ -n "$candidate_id" ]]' in script


def test_candidate_file_source_sha_is_checked_before_pipeline() -> None:
    script = (ROOT / "infra/scripts/ci-local.sh").read_text(encoding="utf-8")
    assert 'candidate_file="${GRAF_CI_CANDIDATE_FILE:-}"' in script
    assert 'candidate_source_sha=""' in script
    assert '"${candidate_source_sha,,}" != "${observed_sha_start,,}"' in script
    assert "candidate_source_sha_mismatch" in script


def test_candidate_file_mismatch_emits_stale_evidence_without_running_pipeline(tmp_path: Path) -> None:
    candidate = tmp_path / "candidate.json"
    candidate.write_text(
        json.dumps({"candidate_id": "rc-test-source-mismatch", "source_sha": "0" * 40}) + "\n",
        encoding="utf-8",
    )
    evidence = tmp_path / "evidence.json"
    env = os.environ.copy()
    env["GRAF_CI_CANDIDATE_FILE"] = str(candidate)
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
    assert "candidate_source_sha_mismatch" in result.stderr
    record = json.loads(evidence.read_text(encoding="utf-8"))
    assert record["status"] == "stale"
    assert record["reason"] == "candidate_source_sha_mismatch"


def test_dirty_candidate_full_run_is_blocked_but_direct_full_is_diagnostic() -> None:
    script = (ROOT / "infra/scripts/ci-local.sh").read_text(encoding="utf-8")
    assert 'reason=dirty_worktree_before_run' in script
    assert 'reason=release_candidate_required_for_clean_gate' in script
    assert '[[ "$requested_mode" == "full" && -n "$candidate_file" && -n "$initial_tree_state" ]]' in script


def test_dev_installer_parses_and_validates_both_loopback_origins() -> None:
    script = (ROOT / "apps/macos/Scripts/install-dev-app.sh").read_text(encoding="utf-8")
    assert "urlsplit" in script
    assert "GRAF_CABINET_BASE_URL" in script and "GRAF_UPLOAD_BASE_URL" in script
    assert "parsed.username" in script and "parsed.hostname" in script
