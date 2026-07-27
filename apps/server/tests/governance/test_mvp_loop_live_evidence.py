from __future__ import annotations

import json
from pathlib import Path

import pytest

from twobrain_rec_server.readiness import (
    build_default_readiness_report,
    render_markdown_report,
    write_readiness_outputs,
)

FEATURE = "035-mvp-loop-live-evidence"
FEATURE_036 = "036-owner-review-live-polish"
pytestmark = pytest.mark.governance


def test_035_live_evidence_report_uses_feature_contract_and_caps_claims(tmp_path: Path) -> None:
    report = build_default_readiness_report(
        feature=FEATURE,
        generated_at="2026-06-16T00:00:00Z",
        deployed_commit="035-test-commit",
    )
    write_readiness_outputs(report, tmp_path)

    payload = json.loads((tmp_path / "readiness-report.json").read_text())
    markdown = (tmp_path / "readiness-report.md").read_text()
    gap_register = (tmp_path / "launch-gap-register.md").read_text()

    assert payload["feature"] == FEATURE
    assert payload["claim_summary"]["outcome"] == "pilot_blocked"
    assert payload["claim_summary"]["bounded_claims"] == ["infra_smoke_ready"]
    assert payload["claim_summary"]["p0_p1_blockers"] > 0
    assert {item["id"] for item in payload["evidence"]} >= {
        "feature-035-live-evidence-pack",
        "feature-035-validation-log",
        "feature-035-clean-room-reference",
        "feature-035-github-issues",
    }
    assert "Recommended next product slice: `035-mvp-loop-live-evidence`" not in markdown
    assert "Recommended next product slice: `036-owner-review-live-polish`" in markdown
    assert "P0/P1 gaps block `mvp_loop_ready` and `internal_pilot_candidate`" in gap_register
    assert any("specs/035-mvp-loop-live-evidence" in command for command in payload["forbidden_content_scan"]["commands"])
    assert any(
        "docs/evidence/035-mvp-loop-live-evidence" in command
        for command in payload["forbidden_content_scan"]["commands"]
    )


def test_035_report_contains_no_forbidden_rollout_claims_while_p1_gaps_remain() -> None:
    report = build_default_readiness_report(feature=FEATURE, generated_at="2026-06-16T00:00:00Z")
    markdown = render_markdown_report(report)

    assert report.claim_summary.outcome == "pilot_blocked"
    assert "Outcome: `pilot_blocked`" in markdown
    assert "mvp_loop_ready" in report.claim_summary.excluded_claims
    assert "internal_pilot_candidate" in report.claim_summary.excluded_claims
    assert "user_rollout_ready" in report.claim_summary.excluded_claims
    assert "production_ready" in report.claim_summary.excluded_claims


def test_035_launch_gap_register_keeps_accepted_022_evidence_and_current_p1_gaps() -> None:
    report = build_default_readiness_report(feature=FEATURE, generated_at="2026-06-16T00:00:00Z")

    evidence_ids = {item.id for item in report.evidence}
    gap_ids = {gap.id for gap in report.launch_gaps}

    assert "feature-022-meeting-mute-truth" in evidence_ids
    assert "meeting-app-mute-truth" not in gap_ids
    assert "live-desktop-evidence" not in gap_ids
    assert "web-owner-live-auth-context" in gap_ids
    assert "notes-action-output" in gap_ids
    assert "production-user-rollout-evidence" in gap_ids


def test_035_readiness_output_generation_contains_current_claim_and_next_slice(tmp_path: Path) -> None:
    report = build_default_readiness_report(
        feature=FEATURE,
        generated_at="2026-06-16T00:00:00Z",
        deployed_commit="035-us3-test",
    )
    write_readiness_outputs(report, tmp_path)

    payload = json.loads((tmp_path / "readiness-report.json").read_text())
    markdown = (tmp_path / "readiness-report.md").read_text()
    gap_register = (tmp_path / "launch-gap-register.md").read_text()

    assert payload["feature"] == FEATURE
    assert payload["claim_summary"]["outcome"] == "pilot_blocked"
    assert "web-owner-live-auth-context" in gap_register
    assert "live-desktop-evidence" not in gap_register
    assert "Recommended next product slice: `036-owner-review-live-polish`" in markdown


def test_035_installed_desktop_evidence_files_are_present_and_metadata_safe() -> None:
    evidence_dir = Path(__file__).resolve().parents[4] / "docs/evidence/035-mvp-loop-live-evidence"
    screenshot_dir = evidence_dir / "screenshots"
    expected_screenshots = {
        "2026-06-16-desktop-idle-ready-applications.png",
        "2026-06-16-desktop-active-recording-applications.png",
        "2026-06-16-desktop-paused-recording-applications.png",
        "2026-06-16-desktop-resumed-recording-applications.png",
        "2026-06-16-desktop-stopped-list-applications.png",
    }

    for file_name in expected_screenshots:
        screenshot = screenshot_dir / file_name
        assert screenshot.exists(), file_name
        assert screenshot.stat().st_size > 10_000, file_name

    validation_log = (evidence_dir / "validation-log.md").read_text()
    readme = (evidence_dir / "README.md").read_text()
    current_status = (
        Path(__file__).resolve().parents[4] / "docs/current-product-status.md"
    ).read_text()

    assert "installed-app-proof" in validation_log
    assert "latest-artifact-validator" in validation_log
    assert "/Applications/GRAF.app" in current_status
    assert "20260616-163553-91CF43DD-71DA-45BA-9995-0C0788D49D7F" in readme
    assert "meeting-app mute-respecting claim is allowed" in readme
    assert "/Users/" not in validation_log
    assert "/Users/" not in readme


def test_035_web_owner_review_evidence_files_are_present_and_metadata_safe() -> None:
    evidence_dir = Path(__file__).resolve().parents[4] / "docs/evidence/035-mvp-loop-live-evidence"
    screenshot_dir = evidence_dir / "screenshots"
    expected_notes = {
        "web-meeting-list-evidence.md",
        "web-meeting-detail-evidence.md",
        "web-governance-evidence.md",
    }

    combined = ""
    for file_name in expected_notes:
        evidence_file = screenshot_dir / file_name
        assert evidence_file.exists(), file_name
        text = evidence_file.read_text()
        assert "rec.2brain.pro" in text
        assert "Fixture-Backed Coverage" in text or "Fixture-backed" in text
        assert "/Users/" not in text
        assert "@" not in text
        combined += text

    validation_log = (evidence_dir / "validation-log.md").read_text()
    readme = (evidence_dir / "README.md").read_text()

    assert "missing_auth_context" in combined
    assert "notes/action" in combined
    assert "No production share, export, delete" in combined
    assert "prod-meetings-route" in validation_log
    assert "chrome-meetings-route" in validation_log
    assert "401 missing_auth_context" in readme


def test_035_report_includes_web_auth_blocker_and_fixture_backed_evidence() -> None:
    report = build_default_readiness_report(
        feature=FEATURE,
        generated_at="2026-06-16T00:00:00Z",
    )
    markdown = render_markdown_report(report)
    evidence_ids = {item.id for item in report.evidence}

    assert {
        "feature-035-web-live-auth-blocker",
        "feature-035-web-list-evidence",
        "feature-035-web-detail-evidence",
        "feature-035-web-governance-evidence",
    } <= evidence_ids
    assert "401 missing_auth_context" in markdown
    assert "Fixture-backed list evidence does not prove a live private owner account." in markdown
    assert "No destructive production sharing, export, or deletion action was performed." in markdown


def test_035_clean_room_reference_assertions_stay_metadata_only() -> None:
    report = build_default_readiness_report(feature=FEATURE, generated_at="2026-06-16T00:00:00Z")
    evidence_dir = Path(__file__).resolve().parents[4] / "docs/evidence/035-mvp-loop-live-evidence"
    clean_room_note = (evidence_dir / "clean-room-reference.md").read_text()

    assert report.reference_comparisons
    assert all(comparison.result in {"pass", "needs_polish"} for comparison in report.reference_comparisons)
    assert all(
        "No committed private Krisp screenshots." in comparison.forbidden_similarity_checks
        for comparison in report.reference_comparisons
    )
    assert any(
        "feature-035-clean-room-reference" in comparison.evidence_ids
        for comparison in report.reference_comparisons
    )
    assert all(item.safe_to_commit for item in report.evidence)
    assert "Product Polish Gaps" in clean_room_note
    assert "036-owner-review-live-polish" in clean_room_note
    assert "No committed private Krisp screenshots." in clean_room_note
    assert "layout-specific instructions" in clean_room_note
    assert "/Users/" not in clean_room_note


def test_036_readiness_output_generation_contains_current_claim_and_open_gaps(tmp_path: Path) -> None:
    report = build_default_readiness_report(
        feature=FEATURE_036,
        generated_at="2026-06-22T00:00:00Z",
        deployed_commit="036-closeout-test",
    )
    write_readiness_outputs(report, tmp_path)

    payload = json.loads((tmp_path / "readiness-report.json").read_text())
    markdown = (tmp_path / "readiness-report.md").read_text()
    gap_register = (tmp_path / "launch-gap-register.md").read_text()

    assert payload["feature"] == FEATURE_036
    assert payload["claim_summary"]["outcome"] == "pilot_blocked"
    assert payload["claim_summary"]["bounded_claims"] == ["infra_smoke_ready"]
    assert {item["id"] for item in payload["evidence"]} >= {
        "feature-036-owner-review-live",
        "feature-036-validation-log",
        "feature-036-notes-action-truth",
        "feature-036-installed-app-final-walkthrough",
        "feature-036-clean-room-reference",
        "feature-036-github-issues",
    }
    assert "web-owner-live-auth-context" not in gap_register
    assert "notes-action-output" in gap_register
    assert "desktop-runtime-walkthrough-evidence" not in gap_register
    assert "desktop-product-surface-polish" not in gap_register
    assert "Recommended next action: keep the 036 claim at `pilot_blocked`" in markdown


def test_036_existing_evidence_files_are_metadata_safe_and_bound_open_claims() -> None:
    evidence_dir = Path(__file__).resolve().parents[4] / "docs/evidence/036-owner-review-live-polish"

    validation_log = (evidence_dir / "validation-log.md").read_text()
    clean_room_note = (evidence_dir / "clean-room-reference.md").read_text()
    notes_truth = (evidence_dir / "screenshots/web-notes-action-truth-evidence.md").read_text()
    owner_evidence = (evidence_dir / "screenshots/web-owner-review-evidence.md").read_text()
    installed_walkthrough = (
        evidence_dir / "screenshots/installed-app-final-walkthrough-2026-06-22.md"
    ).read_text()

    assert "owner-session-live-proof-2026-06-22" in validation_log
    assert "list `uniqueMeetingLinkCount=8`" in validation_log
    assert "real owner list/detail/governance content still needs metadata-safe live" in clean_room_note
    assert "idle/active/paused/resumed/stopped recording walkthrough is now" in clean_room_note
    assert "missing_auth_context" in owner_evidence
    assert "Owner list | pass" in owner_evidence
    assert "Owner detail | pass" in owner_evidence
    assert "Governance actions | pass" in owner_evidence
    assert "`T047` is complete" in installed_walkthrough
    assert "paused, resumed, stopped, configured, missing-auth" in installed_walkthrough
    assert "Summary" in notes_truth
    assert "Action Items" in notes_truth
    assert "/Users/" not in validation_log
    assert "/Users/" not in clean_room_note
    assert "/Users/" not in notes_truth
    assert "/Users/" not in owner_evidence
    assert "/Users/" not in installed_walkthrough
