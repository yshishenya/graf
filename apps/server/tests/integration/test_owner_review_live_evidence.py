from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

FORBIDDEN_EVIDENCE_MARKERS = [
    "Authorization:",
    "Bearer ",
    "X-Auth-Session",
    "session_token",
    "cookie",
    "Set-Cookie",
    "signed_url",
    "presigned",
    "/Users/",
    "@",
]


def assert_metadata_safe_payload(payload: dict[str, object]) -> None:
    serialized = json.dumps(payload, ensure_ascii=False)
    for marker in FORBIDDEN_EVIDENCE_MARKERS:
        assert marker not in serialized


def assert_metadata_safe_file(path: Path) -> None:
    text = path.read_text()
    for marker in FORBIDDEN_EVIDENCE_MARKERS:
        assert marker not in text


def test_metadata_safe_payload_helper_accepts_route_state_only() -> None:
    assert_metadata_safe_payload(
        {
            "proof_id": "feature-036-owner-review-live",
            "target_origin": "https://rec.2brain.pro",
            "list_state": "blocked",
            "failure_code": "missing_auth_context",
            "session_material_committed": False,
        }
    )


def test_metadata_safe_payload_helper_rejects_private_markers() -> None:
    try:
        assert_metadata_safe_payload({"header": "Authorization: Bearer secret"})
    except AssertionError:
        return
    raise AssertionError("private auth marker should be rejected")


def test_owner_review_live_proof_dry_run_stdout_is_metadata_safe(tmp_path: Path) -> None:
    repo_root = Path(__file__).resolve().parents[4]
    script = repo_root / "apps/server/scripts/prove_owner_review_live.py"
    result = subprocess.run(
        [
            sys.executable,
            str(script),
            "--api",
            "https://rec.2brain.pro",
            "--run-id",
            "feature-036-owner-review-safe-output",
            "--token-file",
            str(tmp_path / "owner-review-token"),
            "--dry-run",
        ],
        check=True,
        text=True,
        capture_output=True,
        env={**os.environ, "PYTHONPATH": str(repo_root / "apps/server/src")},
    )
    payload = json.loads(result.stdout)

    assert_metadata_safe_payload(payload)
