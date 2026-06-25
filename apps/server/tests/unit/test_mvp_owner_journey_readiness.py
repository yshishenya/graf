from __future__ import annotations

from twobrain_rec_server.readiness import build_default_readiness_report, render_markdown_report


def test_051_keeps_all_three_owner_journey_p1_proofs_open() -> None:
    report = build_default_readiness_report(feature="051-mvp-owner-journey-proof", generated_at="2026-06-25T00:00:00Z")
    gaps = {gap.id: gap for gap in report.launch_gaps}

    assert report.claim_summary.outcome == "pilot_blocked"
    assert report.claim_summary.bounded_claims == ["infra_smoke_ready"]
    assert report.claim_summary.p0_p1_blockers == 3
    assert "production-user-rollout-evidence" not in gaps
    assert "notes-action-output" not in gaps
    assert gaps["fresh-owner-journey-evidence"].severity == "P1"
    assert gaps["production-stored-outcomes-evidence"].severity == "P1"
    assert gaps["processing-time-target-evidence"].severity == "P1"


def test_052_keeps_only_unproven_owner_journey_p1_proofs_open_after_timing_pass() -> None:
    report = build_default_readiness_report(feature="052-mvp-live-ui-proof", generated_at="2026-06-25T00:00:00Z")
    gaps = {gap.id: gap for gap in report.launch_gaps}

    assert report.claim_summary.outcome == "pilot_blocked"
    assert report.claim_summary.bounded_claims == ["infra_smoke_ready"]
    assert report.claim_summary.p0_p1_blockers == 2
    assert "production-user-rollout-evidence" not in gaps
    assert "notes-action-output" not in gaps
    assert "processing-time-target-evidence" not in gaps
    assert gaps["fresh-owner-journey-evidence"].severity == "P1"
    assert gaps["production-stored-outcomes-evidence"].severity == "P1"


def test_051_records_owner_journey_evidence_without_reopening_049_or_050() -> None:
    report = build_default_readiness_report(feature="051-mvp-owner-journey-proof", generated_at="2026-06-25T00:00:00Z")
    evidence_ids = {item.id for item in report.evidence}
    stages = {stage.id: stage for stage in report.stages}

    assert {
        "feature-049-stored-outcomes",
        "feature-050-closeout-report",
        "feature-051-validation-log",
        "feature-051-owner-journey-probe",
        "feature-051-browser-runtime",
        "feature-051-closeout-report",
        "feature-051-timing-proof",
        "current-product-status-051",
        "changelog-051",
    } <= evidence_ids

    assert stages["notes-action-output"].status == "ready"
    assert stages["notes-action-output"].launch_gap_ids == []
    assert "feature-049-stored-outcomes" in stages["notes-action-output"].evidence_ids

    production_stage = stages["production-deployment-smoke"]
    assert production_stage.status == "degraded"
    assert production_stage.launch_gap_ids == [
        "fresh-owner-journey-evidence",
        "processing-time-target-evidence",
        "production-stored-outcomes-evidence",
    ]

    assert stages["product-status-next-slice"].status == "ready"
    assert "current-product-status-051" in stages["product-status-next-slice"].evidence_ids


def test_markdown_names_the_remaining_p1_proofs() -> None:
    report_051 = build_default_readiness_report(feature="051-mvp-owner-journey-proof", generated_at="2026-06-25T00:00:00Z")
    markdown_051 = render_markdown_report(report_051)

    assert "feature-051-closeout-report" in markdown_051
    assert "feature-051-timing-proof" in markdown_051
    assert "fresh-owner-journey-evidence" in markdown_051
    assert "production-stored-outcomes-evidence" in markdown_051
    assert "processing-time-target-evidence" in markdown_051
    assert "Recommended next action: keep 051 capped at `pilot_blocked`" in markdown_051

    report_052 = build_default_readiness_report(feature="052-mvp-live-ui-proof", generated_at="2026-06-25T00:00:00Z")
    markdown_052 = render_markdown_report(report_052)

    assert "feature-052-closeout-report" in markdown_052
    assert "feature-052-timing-proof" in markdown_052
    assert "fresh-owner-journey-evidence" in markdown_052
    assert "production-stored-outcomes-evidence" in markdown_052
    assert "processing-time-target-evidence" not in {gap.id for gap in report_052.launch_gaps}
    assert "Recommended next action: keep 052 capped at `pilot_blocked`" in markdown_052


def test_051_timing_target_stays_blocking_until_representative_proof_exists() -> None:
    report = build_default_readiness_report(feature="051-mvp-owner-journey-proof", generated_at="2026-06-25T00:00:00Z")
    gaps = {gap.id: gap for gap in report.launch_gaps}
    stages = {stage.id: stage for stage in report.stages}
    evidence = {item.id: item for item in report.evidence}

    gap = gaps["processing-time-target-evidence"]
    assert gap.severity == "P1"
    assert "Representative one-hour or near-one-hour production timing evidence" in gap.missing_evidence
    assert "Record queue, workflow, provider, and finalize-to-review timing" in gap.recommended_next_action
    assert stages["production-deployment-smoke"].launch_gap_ids == [
        "fresh-owner-journey-evidence",
        "processing-time-target-evidence",
        "production-stored-outcomes-evidence",
    ]
    assert evidence["feature-051-timing-proof"].limitations == [
        "Timing target remains unproven until a representative run is recorded."
    ]


def test_052_timing_target_is_no_longer_a_launch_gap_after_hour_proof() -> None:
    report = build_default_readiness_report(feature="052-mvp-live-ui-proof", generated_at="2026-06-25T00:00:00Z")
    gaps = {gap.id: gap for gap in report.launch_gaps}
    stages = {stage.id: stage for stage in report.stages}
    evidence = {item.id: item for item in report.evidence}

    assert "processing-time-target-evidence" not in gaps
    assert stages["production-deployment-smoke"].launch_gap_ids == [
        "fresh-owner-journey-evidence",
        "production-stored-outcomes-evidence",
    ]
    assert evidence["feature-052-timing-proof"].limitations == [
        "Synthetic production-safe hour timing passed; fresh installed-app owner journey timing remains a separate gate."
    ]


def test_052_records_ui_reference_review_as_part_of_interface_proof() -> None:
    report = build_default_readiness_report(feature="052-mvp-live-ui-proof", generated_at="2026-06-25T00:00:00Z")
    evidence_ids = {item.id for item in report.evidence}
    comparisons = {comparison.id: comparison for comparison in report.reference_comparisons}
    stages = {stage.id: stage for stage in report.stages}

    assert "feature-052-ui-reference-review" in evidence_ids
    assert "feature-052-ui-reference-review" in comparisons["web-review-workspace"].evidence_ids
    assert "feature-052-browser-runtime" in comparisons["desktop-first-viewport"].evidence_ids
    assert stages["meeting-list"].status == "degraded"
    assert stages["meeting-detail-transcript-playback"].status == "degraded"
    assert stages["notes-action-output"].status == "degraded"
    assert stages["desktop-embedded-cabinet"].status == "degraded"
    assert stages["meeting-detail-transcript-playback"].launch_gap_ids == [
        "fresh-owner-journey-evidence",
        "production-stored-outcomes-evidence",
    ]
