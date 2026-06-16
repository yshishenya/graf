from __future__ import annotations

import pytest

from twobrain_rec_server.readiness import build_default_readiness_report, render_markdown_report
from twobrain_rec_server.readiness.evidence import ClaimSummary, LaunchGap, ReadinessReport


def test_mvp_loop_readiness_json_contract_has_required_top_level_shape() -> None:
    report = build_default_readiness_report(
        generated_at="2026-06-16T00:00:00Z",
        deployed_commit="ab875e7ba50f15ff57323581ba0edfa7abd5ad5c",
    )
    payload = report.model_dump(mode="json")

    assert payload["feature"] == "034-mvp-loop-readiness"
    assert payload["generated_at"] == "2026-06-16T00:00:00Z"
    assert payload["deployed_commit"] == "ab875e7ba50f15ff57323581ba0edfa7abd5ad5c"
    assert set(payload) == {
        "feature",
        "generated_at",
        "deployed_commit",
        "claim_summary",
        "stages",
        "evidence",
        "launch_gaps",
        "reference_comparisons",
        "forbidden_content_scan",
    }


def test_mvp_loop_readiness_markdown_contract_sections_are_in_order() -> None:
    markdown = render_markdown_report(build_default_readiness_report())
    required_sections = [
        "# MVP Loop Readiness",
        "## Claim Summary",
        "## MVP Loop Matrix",
        "## Desktop App Evidence",
        "## Web And Embedded Cabinet Evidence",
        "## Access, Egress, Retention, And Deletion Truth",
        "## Production Evidence",
        "## Clean-Room Reference Comparison",
        "## Forbidden Content Scan",
        "## Launch Gap Register",
        "## Next Slice Recommendation",
    ]

    positions = [markdown.index(section) for section in required_sections]
    assert positions == sorted(positions)


@pytest.mark.parametrize(
    "outcome",
    [
        "mvp_loop_ready",
        "internal_pilot_candidate",
        "partial_readiness",
        "pilot_blocked",
        "evidence_blocked",
    ],
)
def test_claim_summary_accepts_only_contract_outcomes(outcome: str) -> None:
    summary = ClaimSummary(outcome=outcome, p0_p1_blockers=0)

    assert summary.outcome == outcome


def test_mvp_loop_ready_rejects_open_p0_p1_launch_gaps() -> None:
    gap = LaunchGap(
        id="live-desktop-private-safe-capture",
        severity="P1",
        affected_journey="desktop-embedding",
        current_evidence="Synthetic desktop evidence exists.",
        missing_evidence="Fresh live app capture or explicit blocked reason.",
        recommended_next_action="Capture metadata-safe desktop app screenshots.",
        owner_area="desktop",
    )

    with pytest.raises(ValueError, match="mvp_loop_ready"):
        ReadinessReport(
            claim_summary=ClaimSummary(outcome="mvp_loop_ready", p0_p1_blockers=1),
            launch_gaps=[gap],
        )

