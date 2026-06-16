from __future__ import annotations

import json
from pathlib import Path

from twobrain_rec_server.readiness import (
    build_default_readiness_report,
    render_markdown_report,
    write_readiness_outputs,
)


FEATURE = "035-mvp-loop-live-evidence"


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
    assert "Recommended next action: resolve `live-desktop-evidence` before pilot readiness." in markdown
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
    assert "live-desktop-evidence" in gap_ids
    assert "notes-action-output" in gap_ids
    assert "production-user-rollout-evidence" in gap_ids


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

    assert "installed-app-proof" in validation_log
    assert "/Applications/2brain Rec.app" in validation_log
    assert "latest-artifact-validator" in validation_log
    assert "20260616-163553-91CF43DD-71DA-45BA-9995-0C0788D49D7F" in readme
    assert "meeting-app mute-respecting claim is allowed" in readme
    assert "/Users/" not in validation_log
    assert "/Users/" not in readme


def test_035_clean_room_reference_assertions_stay_metadata_only() -> None:
    report = build_default_readiness_report(feature=FEATURE, generated_at="2026-06-16T00:00:00Z")

    assert report.reference_comparisons
    assert all(comparison.result in {"pass", "needs_polish"} for comparison in report.reference_comparisons)
    assert all(
        "No committed private Krisp screenshots." in comparison.forbidden_similarity_checks
        for comparison in report.reference_comparisons
    )
    assert all(item.safe_to_commit for item in report.evidence)
