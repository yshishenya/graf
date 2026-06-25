from __future__ import annotations

from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]


def _status_doc() -> str:
    return (ROOT / "docs/current-product-status.md").read_text()


def test_current_status_records_049_as_released_and_deployed_product_behavior() -> None:
    status_doc = _status_doc()

    assert "Feature `049-meeting-outcomes-mvp` is implemented, merged through PR" in status_doc
    assert "released as `v2026.06.25.4`" in status_doc
    assert "deployed to production" in status_doc
    assert "The notes/action output blocker is closed" in status_doc

    stale_phrases = [
        "Feature `049-meeting-outcomes-mvp` is implemented in the current feature branch",
        "it still needs final feature closeout before it can be described as released/deployed product behavior",
        "finish `049` validation/PR/release/deploy closeout",
        "finish validating and closing `049-meeting-outcomes-mvp`",
    ]
    for stale_phrase in stale_phrases:
        assert stale_phrase not in status_doc


def test_current_status_keeps_049_shipped_truth_separate_from_050_launch_gap() -> None:
    status_doc = _status_doc()

    assert "Feature `049-meeting-outcomes-mvp` is implemented, merged through PR `#1706`" in status_doc
    assert "released as `v2026.06.25.4`" in status_doc
    assert "deployed to production" in status_doc
    assert "Feature `050-mvp-launch-proof` is implemented, merged through PR `#1753`" in status_doc
    assert "released as `v2026.06.25.5`" in status_doc
    assert "The allowed current claim remains `pilot_blocked`" in status_doc
    assert "fresh-owner-journey-evidence" in status_doc
    assert "production-stored-outcomes-evidence" in status_doc
    assert "processing-time-target-evidence" in status_doc
    assert "notes/action output blocker is closed" in status_doc
    assert "production_ready" in status_doc

    assert status_doc.index("Feature `049-meeting-outcomes-mvp`") < status_doc.index("Feature `050-mvp-launch-proof`")
    assert "Feature `049-meeting-outcomes-mvp` is implemented in the current feature branch" not in status_doc


def test_current_status_records_050_as_the_closed_mvp_launch_proof_boundary() -> None:
    status_doc = _status_doc()

    assert "Feature `050-mvp-launch-proof` is implemented, merged through PR `#1753`" in status_doc
    assert "released as `v2026.06.25.5`" in status_doc
    assert "launch-proof closeout slice" in status_doc
    assert "The allowed current claim remains `pilot_blocked`" in status_doc
    assert "fresh-owner-journey-evidence" in status_doc
    assert "production-stored-outcomes-evidence" in status_doc
    assert "processing-time-target-evidence" in status_doc
    assert "internal_pilot_candidate" in status_doc
    assert "production_ready" in status_doc
    assert "stored outcomes on a production candidate" in status_doc

    stale_launch_phrases = [
        "045 deploy preflight risk is reduced",
        "post-deploy production smoke/e2e evidence is still required",
        "current-branch desktop build/launch/idle/quit is proven",
        "deployed 045 auto-start/reuse and source-attribution proof are still missing",
        "Feature `050-mvp-launch-proof` is the active MVP launch-proof slice",
    ]
    for stale_phrase in stale_launch_phrases:
        assert stale_phrase not in status_doc


def test_current_status_records_051_as_active_owner_journey_proof_slice() -> None:
    status_doc = _status_doc()

    assert "Feature `050-mvp-launch-proof` is implemented, merged through PR `#1753`" in status_doc
    assert "Feature `051-mvp-owner-journey-proof`" in status_doc
    assert "current proof closeout over the\nfresh owner journey" in status_doc
    assert "fresh owner journey" in status_doc
    assert "production stored" in status_doc
    assert "outcomes" in status_doc
    assert "representative timing gaps" in status_doc
    assert "The allowed current claim remains `pilot_blocked`" in status_doc
    assert "internal_pilot_candidate" in status_doc
    assert status_doc.index("Feature `050-mvp-launch-proof`") < status_doc.index("Feature `051-mvp-owner-journey-proof`")
