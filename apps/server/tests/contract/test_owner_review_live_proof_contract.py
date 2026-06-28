from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
SCRIPT = REPO_ROOT / "apps/server/scripts/prove_owner_review_live.py"


def test_owner_review_live_proof_dry_run_shape_is_metadata_safe(tmp_path: Path) -> None:
    token_file = tmp_path / "owner-review-token"
    result = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            "--api",
            "https://rec.2brain.pro",
            "--token-file",
            str(token_file),
            "--run-id",
            "feature-036-owner-review-contract",
            "--dry-run",
        ],
        check=True,
        text=True,
        capture_output=True,
        env={**os.environ, "PYTHONPATH": str(REPO_ROOT / "apps/server/src")},
    )
    payload = json.loads(result.stdout)

    assert {
        "proof_id",
        "target_origin",
        "run_id",
        "auth_method",
        "session_material_committed",
        "list_state",
        "detail_state",
        "governance_state",
        "cleanup_state",
        "evidence_files",
        "forbidden_content_scan",
    } <= set(payload)
    assert payload["proof_id"] == "feature-036-owner-review-live"
    assert payload["target_origin"] == "https://rec.2brain.pro"
    assert payload["session_material_committed"] is False
    assert payload["auth_method"] in {"session_header", "browser_handoff", "logged_in_browser", "blocked"}
    assert payload["list_state"] in {"ready", "empty", "blocked", "deferred"}
    assert payload["detail_state"] in {"ready", "empty", "blocked", "deferred"}
    assert payload["governance_state"] in {"ready", "blocked", "deferred"}
    assert payload["cleanup_state"] in {"not_needed", "pass", "blocked", "deferred"}

    stdout = result.stdout.lower()
    assert str(token_file).lower() not in stdout
    for forbidden in ["bearer ", "x-auth-session", "cookie", "set-cookie", "session_token", "/users/", "@"]:
        assert forbidden not in stdout


def test_owner_review_live_proof_contract_keeps_private_artifacts_out_of_git() -> None:
    docs = (REPO_ROOT / "specs/036-owner-review-live-polish/contracts/owner-review-live-proof-contract.md").read_text()

    assert "private meeting titles or transcript text" in docs
    assert "bearer/session token values" in docs
    assert "cookies" in docs
    assert "/Applications/GRAF.app" in docs
    assert "Krisp" not in docs
