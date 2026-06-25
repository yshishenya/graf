from __future__ import annotations

from twobrain_rec_server.readiness import build_default_readiness_report, render_markdown_report

FEATURE = "051-mvp-owner-journey-proof"


def test_051_keeps_pilot_blocked_until_exact_p1_proofs_exist() -> None:
    report = build_default_readiness_report(feature=FEATURE, generated_at="2026-06-25T00:00:00Z")
    gaps = {gap.id: gap for gap in report.launch_gaps}

    assert report.claim_summary.outcome == "pilot_blocked"
    assert report.claim_summary.bounded_claims == ["infra_smoke_ready"]
    assert report.claim_summary.p0_p1_blockers == 3
    assert "production-user-rollout-evidence" not in gaps
    assert "notes-action-output" not in gaps
    assert gaps["fresh-owner-journey-evidence"].severity == "P1"
    assert gaps["production-stored-outcomes-evidence"].severity == "P1"
    assert gaps["processing-time-target-evidence"].severity == "P1"


def test_051_records_owner_journey_evidence_without_reopening_049_or_050() -> None:
    report = build_default_readiness_report(feature=FEATURE, generated_at="2026-06-25T00:00:00Z")
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


def test_051_markdown_names_the_three_remaining_p1_proofs() -> None:
    report = build_default_readiness_report(feature=FEATURE, generated_at="2026-06-25T00:00:00Z")
    markdown = render_markdown_report(report)

    assert "feature-051-closeout-report" in markdown
    assert "feature-051-timing-proof" in markdown
    assert "fresh-owner-journey-evidence" in markdown
    assert "production-stored-outcomes-evidence" in markdown
    assert "processing-time-target-evidence" in markdown
    assert "Recommended next action: keep 051 capped at `pilot_blocked`" in markdown


def test_051_timing_target_stays_blocking_until_representative_proof_exists() -> None:
    report = build_default_readiness_report(feature=FEATURE, generated_at="2026-06-25T00:00:00Z")
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
