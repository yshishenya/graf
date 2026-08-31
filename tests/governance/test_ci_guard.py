from __future__ import annotations

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
