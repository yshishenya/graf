from __future__ import annotations

from twobrain_rec_server.readiness import build_default_readiness_report


def test_050_keeps_launch_claim_blocked_until_rollout_proof_exists() -> None:
    report = build_default_readiness_report(
        feature="050-mvp-launch-proof",
        generated_at="2026-06-25T00:00:00Z",
    )
    gaps = {gap.id: gap for gap in report.launch_gaps}

    assert report.claim_summary.outcome == "pilot_blocked"
    assert report.claim_summary.bounded_claims == ["infra_smoke_ready"]
    assert report.claim_summary.p0_p1_blockers == 1
    assert "mvp_loop_ready" in report.claim_summary.excluded_claims
    assert "internal_pilot_candidate" in report.claim_summary.excluded_claims
    assert "user_rollout_ready" in report.claim_summary.excluded_claims
    assert "production_ready" in report.claim_summary.excluded_claims

    assert "production-user-rollout-evidence" in gaps
    assert gaps["production-user-rollout-evidence"].severity == "P1"
    assert "notes-action-output" not in gaps
    assert "live-desktop-evidence" not in gaps
    assert "web-owner-live-auth-context" not in gaps


def test_050_records_mvp_launch_proof_evidence_without_reopening_049() -> None:
    report = build_default_readiness_report(
        feature="050-mvp-launch-proof",
        generated_at="2026-06-25T00:00:00Z",
    )
    evidence_ids = {item.id for item in report.evidence}
    stages = {stage.id: stage for stage in report.stages}
    comparisons = {comparison.id: comparison for comparison in report.reference_comparisons}

    assert {
        "feature-050-validation-log",
        "feature-050-browser-runtime",
        "feature-050-closeout-report",
        "current-product-status-050-closeout",
        "changelog-050",
    } <= evidence_ids

    assert stages["notes-action-output"].status == "ready"
    assert stages["notes-action-output"].launch_gap_ids == []
    assert "feature-049-stored-outcomes" in stages["notes-action-output"].evidence_ids

    assert stages["meeting-detail-transcript-playback"].status == "ready"
    assert "feature-050-browser-runtime" in stages["meeting-detail-transcript-playback"].evidence_ids
    assert stages["desktop-embedded-cabinet"].status == "ready"
    assert "feature-050-browser-runtime" in stages["desktop-embedded-cabinet"].evidence_ids

    assert stages["product-status-next-slice"].status == "ready"
    assert "current-product-status-050-closeout" in stages["product-status-next-slice"].evidence_ids

    assert comparisons["desktop-first-viewport"].result == "pass"
    assert comparisons["web-list-workspace"].result == "pass"
    assert comparisons["web-review-workspace"].result == "pass"
