from __future__ import annotations

import json
from pathlib import Path

from twobrain_rec_server.readiness import (
    build_default_readiness_report,
    render_markdown_report,
    write_readiness_outputs,
)


def test_default_readiness_report_contains_all_contract_sections_and_stage_rows() -> None:
    report = build_default_readiness_report(generated_at="2026-06-16T00:00:00Z")
    markdown = render_markdown_report(report)

    assert report.feature == "034-mvp-loop-readiness"
    assert len(report.stages) >= 12
    assert "infra_smoke_ready is not user rollout readiness" in markdown
    assert "mvp_loop_ready" in markdown
    assert "product-owned Pause/Resume privacy truth" in markdown
    assert "signed installer evidence" in markdown
    assert "desktop-shell-regression-tests" in markdown
    assert "desktop-first-surface-blocker-note" in markdown
    assert "web-cabinet-regression-tests" in markdown
    assert "reference-comparison-note" in markdown
    assert "policy-lifecycle-regression-tests" in markdown


def test_write_readiness_outputs_creates_json_markdown_and_gap_register(tmp_path: Path) -> None:
    report = build_default_readiness_report(generated_at="2026-06-16T00:00:00Z")

    write_readiness_outputs(report, tmp_path)

    payload = json.loads((tmp_path / "readiness-report.json").read_text())
    markdown = (tmp_path / "readiness-report.md").read_text()
    gaps = (tmp_path / "launch-gap-register.md").read_text()

    assert payload["claim_summary"]["outcome"] == "pilot_blocked"
    assert payload["forbidden_content_scan"]["status"] == "pass"
    assert "# MVP Loop Readiness" in markdown
    assert "# Launch Gap Register" in gaps
    assert "metadata-safe live desktop screenshots" in gaps


def test_next_slice_recommendation_and_status_doc_do_not_repeat_completed_018() -> None:
    report = build_default_readiness_report(generated_at="2026-06-16T00:00:00Z")
    markdown = render_markdown_report(report)
    status_doc = (Path(__file__).resolve().parents[4] / "docs/current-product-status.md").read_text()

    assert "Recommended next product slice: `035-mvp-loop-live-evidence`" in markdown
    assert "metadata-safe live desktop/web evidence and production user-journey proof" in markdown
    assert "Recommended next feature: `018-retention-deletion-execution`" not in status_doc
    assert "Recommended next feature: `022-meeting-mute-truth`" not in status_doc
    assert "Recommended next feature: validation-only `035-mvp-loop-live-evidence`" not in status_doc
    assert "Recommended next action before starting another feature: close out" in status_doc
    assert "`042-recording-sync-transcription-loop`" in status_doc
    assert "034-mvp-loop-readiness" in status_doc


def test_035_report_does_not_recommend_completed_035_as_next_slice() -> None:
    report = build_default_readiness_report(
        feature="035-mvp-loop-live-evidence",
        generated_at="2026-06-16T00:00:00Z",
    )
    markdown = render_markdown_report(report)

    assert "Recommended next product slice: `035-mvp-loop-live-evidence`" not in markdown
    assert "Recommended next product slice: `036-owner-review-live-polish`" in markdown
    assert "resolve `live-desktop-evidence`" not in markdown


def test_035_report_keeps_web_owner_review_truthful_when_live_auth_is_blocked() -> None:
    report = build_default_readiness_report(
        feature="035-mvp-loop-live-evidence",
        generated_at="2026-06-16T00:00:00Z",
    )
    evidence = {item.id: item for item in report.evidence}
    gaps = {gap.id: gap for gap in report.launch_gaps}
    stages = {stage.id: stage for stage in report.stages}

    assert evidence["feature-035-web-live-auth-blocker"].strength == "blocked"
    assert "401 missing_auth_context" in evidence["feature-035-web-live-auth-blocker"].scope
    assert stages["meeting-list"].status == "degraded"
    assert "web-owner-live-auth-context" in stages["meeting-list"].launch_gap_ids
    assert stages["notes-action-output"].status == "blocked"
    assert "notes-action-output" in stages["notes-action-output"].launch_gap_ids
    assert gaps["notes-action-output"].owner_area == "web"
    assert gaps["web-owner-live-auth-context"].owner_area == "web"


def test_036_report_closes_owner_review_truthfully_and_keeps_output_blockers() -> None:
    report = build_default_readiness_report(
        feature="036-owner-review-live-polish",
        generated_at="2026-06-22T00:00:00Z",
    )
    markdown = render_markdown_report(report)
    evidence = {item.id: item for item in report.evidence}
    gaps = {gap.id: gap for gap in report.launch_gaps}
    stages = {stage.id: stage for stage in report.stages}

    assert report.claim_summary.outcome == "pilot_blocked"
    assert evidence["feature-036-owner-review-live"].strength == "live"
    assert "proves the meeting list, one detail route" in evidence["feature-036-owner-review-live"].scope
    assert evidence["feature-036-notes-action-truth"].strength == "local_runtime"
    assert "web-owner-live-auth-context" not in gaps
    assert "notes-action-output" in gaps
    assert "desktop-runtime-walkthrough-evidence" not in gaps
    assert "desktop-product-surface-polish" not in gaps
    assert stages["meeting-list"].status == "ready"
    assert stages["meeting-list"].launch_gap_ids == []
    assert stages["meeting-detail-transcript-playback"].status == "ready"
    assert stages["meeting-detail-transcript-playback"].launch_gap_ids == []
    assert stages["desktop-embedded-cabinet"].status == "ready"
    assert stages["desktop-embedded-cabinet"].launch_gap_ids == []
    assert "Recommended next action: keep the 036 claim at `pilot_blocked`" in markdown
    assert "feature-036-notes-action-truth" in markdown


def test_035_status_and_changelog_record_current_next_slice() -> None:
    root = Path(__file__).resolve().parents[4]
    status_doc = (root / "docs/current-product-status.md").read_text()
    changelog = (root / "CHANGELOG.md").read_text()

    assert "Feature `035-mvp-loop-live-evidence`" in status_doc
    assert "Recommended next action before starting another feature: close out" in status_doc
    assert "`042-recording-sync-transcription-loop`" in status_doc
    assert "Recommended next feature: validation-only `035-mvp-loop-live-evidence`" not in status_doc
    assert "`401 missing_auth_context`" in status_doc
    assert "feature:035" in changelog
    assert "036-owner-review-live-polish" in changelog
    assert "feature:042" in changelog
