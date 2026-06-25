from __future__ import annotations

import re
from pathlib import Path

from twobrain_rec_server.readiness import build_default_readiness_report

ROOT = Path(__file__).resolve().parents[4]
REQUIRED_GATE_IDS = {
    "release-deployed",
    "installed-app-current",
    "record-stop-upload",
    "finalize-processing",
    "transcript-diarization",
    "playback-seek-timeline",
    "stored-outcomes",
    "embedded-parity",
    "processing-time-target",
    "truth-docs-current",
    "forbidden-content-scan",
}
ALLOWED_STATUSES = {"pass", "fail", "blocked", "unproven", "pending"}
FORBIDDEN_PRIVATE_MARKERS = {
    "set-cookie",
    "authorization:",
    "signed_url=",
    "x-amz-",
    "storage_object_key=",
    "/Users/",
}


def test_050_closeout_report_covers_every_contract_gate_with_safe_status() -> None:
    contract = (ROOT / "specs/050-mvp-launch-proof/contracts/mvp-readiness-contract.md").read_text()
    closeout = (ROOT / "specs/050-mvp-launch-proof/evidence/mvp-closeout-report.md").read_text()

    for gate_id in REQUIRED_GATE_IDS:
        assert f"`{gate_id}`" in contract
        assert f"`{gate_id}`" in closeout

    rows = re.findall(r"^\| `([^`]+)` \| `([^`]+)` \|", closeout, flags=re.MULTILINE)
    assert {gate_id for gate_id, _status in rows} == REQUIRED_GATE_IDS
    for _gate_id, status in rows:
        assert status in ALLOWED_STATUSES

    if any(status != "pass" for _gate_id, status in rows):
        assert "production-user-rollout-evidence" in closeout

    lower = closeout.lower()
    for marker in FORBIDDEN_PRIVATE_MARKERS:
        assert marker not in lower


def test_050_readiness_report_matches_contract_claim_boundary() -> None:
    report = build_default_readiness_report(
        feature="050-mvp-launch-proof",
        generated_at="2026-06-25T00:00:00Z",
    )
    gap_ids = {gap.id for gap in report.launch_gaps}

    assert report.claim_summary.outcome == "pilot_blocked"
    assert report.claim_summary.bounded_claims == ["infra_smoke_ready"]
    assert "production-user-rollout-evidence" in gap_ids
    assert "internal_pilot_candidate" in report.claim_summary.excluded_claims
    assert "production_ready" in report.claim_summary.excluded_claims
