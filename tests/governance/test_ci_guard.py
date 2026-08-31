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
