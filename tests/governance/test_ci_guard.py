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
