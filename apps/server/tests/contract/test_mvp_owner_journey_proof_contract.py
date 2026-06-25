from __future__ import annotations

import re
from pathlib import Path

from twobrain_rec_server.readiness import build_default_readiness_report

ROOT = Path(__file__).resolve().parents[4]
FEATURES = ["051-mvp-owner-journey-proof", "052-mvp-live-ui-proof"]
REQUIRED_GATE_IDS = {
    "release-deployed",
    "installed-app-current",
    "fresh-record-stop-upload",
    "finalize-processing",
    "transcript-diarization",
    "playback-seek-timeline",
    "stored-outcomes-production",
    "embedded-parity",
    "processing-time-target",
    "interface-quality",
    "truth-docs-current",
    "forbidden-content-scan",
}
ALLOWED_STATUSES = {"pass", "fail", "blocked", "unproven"}
FORBIDDEN_PRIVATE_MARKERS = {
    "set-cookie",
    "authorization:",
    "signed_url=",
    "x-amz-",
    "storage_object_key=",
    "/users/",
}


def test_owner_journey_closeout_report_covers_every_gate_safely() -> None:
    for feature in FEATURES:
        contract = (ROOT / f"specs/{feature}/contracts/owner-journey-proof-contract.md").read_text()
        closeout = (ROOT / f"specs/{feature}/evidence/mvp-closeout-report.md").read_text()

        for gate_id in REQUIRED_GATE_IDS:
            assert f"`{gate_id}`" in contract
            assert f"`{gate_id}`" in closeout

        rows = re.findall(r"^\| `([^`]+)` \| `([^`]+)` \|", closeout, flags=re.MULTILINE)
        assert {gate_id for gate_id, _status in rows} == REQUIRED_GATE_IDS
        for _gate_id, status in rows:
            assert status in ALLOWED_STATUSES

        if any(status != "pass" for _gate_id, status in rows):
            assert "fresh-owner-journey-evidence" in closeout
            assert "production-stored-outcomes-evidence" in closeout
            assert "processing-time-target-evidence" in closeout

        lower = closeout.lower()
        for marker in FORBIDDEN_PRIVATE_MARKERS:
            assert marker not in lower


def test_timing_template_matches_timing_contract_without_private_content() -> None:
    for feature in FEATURES:
        contract = (ROOT / f"specs/{feature}/contracts/timing-proof-contract.md").read_text()
        timing = (ROOT / f"specs/{feature}/evidence/timing-proof.md").read_text()

        for phrase in [
            "redacted production candidate reference",
            "recording duration",
            "queue/wait duration",
            "workflow processing duration",
            "provider processing duration",
            "finalize-to-review duration",
            "`180` seconds per one hour of audio",
            "result: `pass`, `fail`, or `unproven`",
        ]:
            assert phrase in contract

        for field in [
            "candidate_ref",
            "recording_duration_seconds",
            "queue_wait_seconds",
            "workflow_processing_seconds",
            "provider_processing_seconds",
            "finalize_to_review_seconds",
            "target_seconds_per_hour",
            "result",
        ]:
            assert f"- {field}:" in timing

        assert "result: `unproven`" in timing
        lower = timing.lower()
        for marker in FORBIDDEN_PRIVATE_MARKERS:
            assert marker not in lower


def test_readiness_report_matches_owner_journey_claim_boundary() -> None:
    for feature in FEATURES:
        report = build_default_readiness_report(
            feature=feature,
            generated_at="2026-06-25T00:00:00Z",
        )
        gap_ids = {gap.id for gap in report.launch_gaps}

        assert report.claim_summary.outcome == "pilot_blocked"
        assert report.claim_summary.bounded_claims == ["infra_smoke_ready"]
        assert {
            "fresh-owner-journey-evidence",
            "production-stored-outcomes-evidence",
            "processing-time-target-evidence",
        } <= gap_ids
        assert "internal_pilot_candidate" in report.claim_summary.excluded_claims
        assert "production_ready" in report.claim_summary.excluded_claims
