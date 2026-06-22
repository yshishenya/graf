from __future__ import annotations

import pytest

from twobrain_rec_server.readiness import build_default_readiness_report
from twobrain_rec_server.readiness.evidence import (
    LaunchGap,
    MvpLoopStage,
    ReadinessEvidence,
    ReadinessReport,
    ReferenceComparison,
)
from twobrain_rec_server.readiness.matrix import (
    REQUIRED_MVP_LOOP_STAGE_IDS,
    p0_p1_blocker_count,
    sort_launch_gaps,
)


def test_default_matrix_covers_required_mvp_loop_stage_ids() -> None:
    report = build_default_readiness_report()

    assert [stage.id for stage in report.stages] == REQUIRED_MVP_LOOP_STAGE_IDS


def test_ready_stage_requires_evidence_record() -> None:
    with pytest.raises(ValueError, match="ready stage"):
        MvpLoopStage(
            id="meeting-detail",
            label="Meeting detail review",
            owner_surface="web_cabinet",
            status="ready",
            evidence_strength="synthetic",
            claim_impact=["web_review_verified"],
        )


def test_blocked_stage_requires_launch_gap_reference() -> None:
    with pytest.raises(ValueError, match="blocked stage"):
        MvpLoopStage(
            id="notes-action-output",
            label="Notes and action output",
            owner_surface="web_cabinet",
            status="blocked",
            evidence_strength="missing",
            evidence_ids=[],
            claim_impact=["mvp_loop_ready"],
        )


def test_p0_p1_blockers_are_counted_and_sorted_before_lower_severity() -> None:
    gaps = [
        LaunchGap(
            id="installer",
            severity="P2",
            affected_journey="installer",
            current_evidence="Ad hoc package exists.",
            missing_evidence="Signed installer evidence.",
            recommended_next_action="Plan installer signing slice.",
            owner_area="ops",
        ),
        LaunchGap(
            id="mute-truth",
            severity="P1",
            affected_journey="local-recording",
            current_evidence="Known backlog item.",
            missing_evidence="Mute truth implementation.",
            recommended_next_action="Run 022 mute truth slice.",
            owner_area="desktop",
        ),
    ]

    assert p0_p1_blocker_count(gaps) == 1
    assert [gap.id for gap in sort_launch_gaps(gaps)] == ["mute-truth", "installer"]


def test_private_screenshot_evidence_is_rejected() -> None:
    with pytest.raises(ValueError, match="unsafe screenshot"):
        ReadinessEvidence(
            id="private-reference-screenshot",
            type="screenshot",
            source="private local capture",
            captured_at="2026-06-16T00:00:00Z",
            scope="Unsafe reference capture.",
            strength="live",
            safe_to_commit=False,
            forbidden_content_scan="blocked",
        )


def test_reference_comparison_has_no_blocked_records_by_default() -> None:
    report = build_default_readiness_report()

    assert {comparison.result for comparison in report.reference_comparisons} <= {
        "pass",
        "needs_polish",
    }


def test_reference_comparison_rejects_unknown_evidence_ids() -> None:
    with pytest.raises(ValueError, match="reference comparison web-list references unknown evidence"):
        ReadinessReport(
            reference_comparisons=[
                ReferenceComparison(
                    id="web-list",
                    surface="web_list",
                    allowed_lessons=["Meeting list is discoverable."],
                    implementation_alignment="Fixture comparison.",
                    forbidden_similarity_checks=["No copied reference copy."],
                    result="pass",
                    evidence_ids=["missing-web-evidence"],
                )
            ]
        )


def test_desktop_shell_evidence_is_local_runtime_but_keeps_live_gap_open() -> None:
    report = build_default_readiness_report()
    stages = {stage.id: stage for stage in report.stages}
    evidence_ids = {item.id for item in report.evidence}
    gaps = {gap.id: gap for gap in report.launch_gaps}

    desktop_stage = stages["desktop-embedded-cabinet"]

    assert desktop_stage.evidence_strength == "local_runtime"
    assert "desktop-shell-regression-tests" in desktop_stage.evidence_ids
    assert "desktop-first-surface-blocker-note" in evidence_ids
    assert "desktop-embedded-detail-blocker-note" in evidence_ids
    assert "live-desktop-evidence" in desktop_stage.launch_gap_ids
    assert "metadata-safe live desktop screenshots" in gaps["live-desktop-evidence"].missing_evidence


def test_web_cabinet_evidence_is_local_runtime_but_notes_output_stays_blocked() -> None:
    report = build_default_readiness_report()
    stages = {stage.id: stage for stage in report.stages}
    evidence_ids = {item.id for item in report.evidence}

    assert stages["meeting-list"].evidence_strength == "local_runtime"
    assert stages["meeting-detail-transcript-playback"].evidence_strength == "local_runtime"
    assert "web-cabinet-regression-tests" in stages["meeting-list"].evidence_ids
    assert "web-meeting-list-blocker-note" in evidence_ids
    assert "web-meeting-detail-blocker-note" in evidence_ids
    assert stages["notes-action-output"].status == "blocked"
    assert "notes-action-output" in stages["notes-action-output"].launch_gap_ids


def test_035_closes_stale_live_desktop_gap_and_adds_web_auth_gap() -> None:
    report = build_default_readiness_report(feature="035-mvp-loop-live-evidence")
    stages = {stage.id: stage for stage in report.stages}
    evidence_ids = {item.id for item in report.evidence}
    gaps = {gap.id: gap for gap in report.launch_gaps}

    assert "live-desktop-evidence" not in gaps
    assert "web-owner-live-auth-context" in gaps
    assert "feature-035-live-evidence-pack" in stages["local-recording-visible-stop"].evidence_ids
    assert "feature-035-web-live-auth-blocker" in evidence_ids
    assert stages["meeting-list"].status == "degraded"
    assert "web-owner-live-auth-context" in stages["meeting-list"].launch_gap_ids


def test_036_keeps_live_owner_and_output_gaps_but_closes_visual_polish_gap() -> None:
    report = build_default_readiness_report(feature="036-owner-review-live-polish")
    stages = {stage.id: stage for stage in report.stages}
    evidence_ids = {item.id for item in report.evidence}
    gaps = {gap.id: gap for gap in report.launch_gaps}
    comparisons = {comparison.id: comparison for comparison in report.reference_comparisons}

    assert report.claim_summary.outcome == "pilot_blocked"
    assert "web-owner-live-auth-context" in gaps
    assert "notes-action-output" in gaps
    assert "production-user-rollout-evidence" in gaps
    assert "desktop-runtime-walkthrough-evidence" not in gaps
    assert "desktop-product-surface-polish" not in gaps
    assert "live-desktop-evidence" not in gaps

    assert "feature-036-owner-review-live" in evidence_ids
    assert "feature-036-notes-action-truth" in evidence_ids
    assert "feature-036-installed-app-visual-polish" in evidence_ids
    assert "feature-036-installed-app-final-walkthrough" in evidence_ids
    assert stages["meeting-list"].status == "degraded"
    assert stages["meeting-detail-transcript-playback"].status == "degraded"
    assert "web-owner-live-auth-context" in stages["meeting-list"].launch_gap_ids
    assert stages["notes-action-output"].status == "blocked"
    assert "feature-036-notes-action-truth" in stages["notes-action-output"].evidence_ids
    assert stages["desktop-embedded-cabinet"].status == "ready"
    assert stages["desktop-embedded-cabinet"].launch_gap_ids == []
    assert comparisons["desktop-first-viewport"].result == "pass"


def test_policy_lifecycle_evidence_is_local_runtime_and_keeps_external_limits_visible() -> None:
    report = build_default_readiness_report()
    stages = {stage.id: stage for stage in report.stages}
    evidence_ids = {item.id for item in report.evidence}

    access_stage = stages["access-sharing-download-export"]
    deletion_stage = stages["retention-deletion-local-purge"]

    assert access_stage.evidence_strength == "local_runtime"
    assert deletion_stage.evidence_strength == "local_runtime"
    assert "policy-lifecycle-regression-tests" in access_stage.evidence_ids
    assert "policy-lifecycle-regression-tests" in deletion_stage.evidence_ids
    assert "policy-lifecycle-evidence-note" in evidence_ids


def test_required_launch_blockers_have_severity_owner_and_next_actions() -> None:
    report = build_default_readiness_report()
    evidence_ids = {item.id for item in report.evidence}
    gaps = {gap.id: gap for gap in report.launch_gaps}

    assert "feature-022-meeting-mute-truth" in evidence_ids
    assert {
        "signed-installer-evidence",
        "browser-target-gaps",
        "live-desktop-evidence",
        "notes-action-output",
        "production-user-rollout-evidence",
    } <= set(gaps)
    assert "meeting-app-mute-truth" not in gaps
    assert "product-status-next-slice-drift" not in gaps
    for gap in gaps.values():
        assert gap.recommended_next_action
        assert gap.owner_area
        assert gap.severity in {"P0", "P1", "P2", "P3"}
