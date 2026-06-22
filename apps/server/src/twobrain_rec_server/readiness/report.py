from __future__ import annotations

import json
from pathlib import Path

from twobrain_rec_server.readiness.evidence import ClaimSummary, ReadinessReport
from twobrain_rec_server.readiness.matrix import (
    build_default_evidence,
    build_default_launch_gaps,
    build_default_reference_comparisons,
    build_default_stages,
    p0_p1_blocker_count,
    passed_forbidden_content_scan,
    utc_now_iso,
)


def build_default_readiness_report(
    *,
    feature: str = "034-mvp-loop-readiness",
    generated_at: str | None = None,
    deployed_commit: str = "unknown",
) -> ReadinessReport:
    generated_at = generated_at or utc_now_iso()
    launch_gaps = build_default_launch_gaps(feature=feature)
    p0_p1_count = p0_p1_blocker_count(launch_gaps)
    summary = ClaimSummary(
        outcome="pilot_blocked" if p0_p1_count else "internal_pilot_candidate",
        bounded_claims=["infra_smoke_ready"],
        excluded_claims=[
            "mvp_loop_ready",
            "internal_pilot_candidate",
            "user_rollout_ready",
            "production_ready",
        ],
        p0_p1_blockers=p0_p1_count,
    )
    return ReadinessReport(
        feature=feature,
        generated_at=generated_at,
        deployed_commit=deployed_commit,
        claim_summary=summary,
        stages=build_default_stages(feature=feature),
        evidence=build_default_evidence(generated_at, deployed_commit, feature=feature),
        launch_gaps=launch_gaps,
        reference_comparisons=build_default_reference_comparisons(feature=feature),
        forbidden_content_scan=passed_forbidden_content_scan(feature),
    )


def render_markdown_report(report: ReadinessReport) -> str:
    lines: list[str] = [
        "# MVP Loop Readiness",
        "",
        "## Claim Summary",
        "",
        f"- Feature: `{report.feature}`",
        f"- Generated at: `{report.generated_at}`",
        f"- Deployed commit: `{report.deployed_commit}`",
        f"- Outcome: `{report.claim_summary.outcome}`",
        f"- Bounded claims: {', '.join(f'`{claim}`' for claim in report.claim_summary.bounded_claims) or '`none`'}",
        f"- Excluded claims: {', '.join(f'`{claim}`' for claim in report.claim_summary.excluded_claims) or '`none`'}",
        f"- P0/P1 blockers: `{report.claim_summary.p0_p1_blockers}`",
        "",
        "infra_smoke_ready is not user rollout readiness, internal pilot readiness, or production readiness.",
        "",
        "## MVP Loop Matrix",
        "",
        "| Stage | Surface | Status | Evidence | Gaps | Claim Impact |",
        "|-------|---------|--------|----------|------|--------------|",
    ]
    for stage in report.stages:
        evidence = ", ".join(f"`{item}`" for item in stage.evidence_ids) or "`none`"
        gaps = ", ".join(f"`{item}`" for item in stage.launch_gap_ids) or "`none`"
        impact = ", ".join(f"`{item}`" for item in stage.claim_impact) or "`none`"
        lines.append(
            f"| `{stage.id}` | `{stage.owner_surface}` | `{stage.status}` | "
            f"`{stage.evidence_strength}` {evidence} | {gaps} | {impact} |"
        )
    lines.extend(
        [
            "",
            "## Desktop App Evidence",
            "",
            _stage_notes(report, ["local-recording-visible-stop", "desktop-embedded-cabinet"]),
            "",
            _evidence_details(
                report,
                [
                    "desktop-shell-regression-tests",
                    "desktop-first-surface-blocker-note",
                    "desktop-embedded-detail-blocker-note",
                    "feature-036-installed-app-visual-polish",
                    "feature-036-clean-room-reference",
                ],
            ),
            "",
            "## Web And Embedded Cabinet Evidence",
            "",
            _stage_notes(
                report,
                [
                    "meeting-list",
                    "meeting-detail-transcript-playback",
                    "notes-action-output",
                    "desktop-embedded-cabinet",
                ],
            ),
            "",
            _evidence_details(
                report,
                [
                    "web-cabinet-regression-tests",
                    "web-meeting-list-blocker-note",
                    "web-meeting-detail-blocker-note",
                    "feature-035-web-live-auth-blocker",
                    "feature-035-web-list-evidence",
                    "feature-035-web-detail-evidence",
                    "feature-035-web-governance-evidence",
                    "feature-036-owner-review-live",
                    "feature-036-notes-action-truth",
                    "feature-036-validation-log",
                    "reference-comparison-note",
                ],
            ),
            "",
            "## Access, Egress, Retention, And Deletion Truth",
            "",
            _stage_notes(report, ["access-sharing-download-export", "retention-deletion-local-purge"]),
            "",
            _evidence_details(
                report,
                [
                    "policy-lifecycle-regression-tests",
                    "policy-lifecycle-evidence-note",
                ],
            ),
            "",
            "## Production Evidence",
            "",
            _stage_notes(report, ["production-deployment-smoke"]),
            "",
            "## Clean-Room Reference Comparison",
            "",
        ]
    )
    for comparison in report.reference_comparisons:
        lines.extend(
            [
                f"### `{comparison.id}`",
                "",
                f"- Surface: `{comparison.surface}`",
                f"- Result: `{comparison.result}`",
                f"- Alignment: {comparison.implementation_alignment}",
                f"- Allowed lessons: {', '.join(comparison.allowed_lessons)}",
                f"- Intentional differences: {', '.join(comparison.intentional_differences) or 'none'}",
                f"- Forbidden similarity checks: {', '.join(comparison.forbidden_similarity_checks)}",
                "",
            ]
        )
    lines.extend(
        [
            "## Forbidden Content Scan",
            "",
            f"- Status: `{report.forbidden_content_scan.status}`",
            f"- Commands: {', '.join(f'`{command}`' for command in report.forbidden_content_scan.commands) or '`none`'}",
            f"- Matches: {', '.join(report.forbidden_content_scan.matches) or '`none`'}",
            "",
            "## Launch Gap Register",
            "",
            _launch_gap_table(report),
            "",
            "## Next Slice Recommendation",
            "",
            _next_slice_recommendation(report),
            "",
        ]
    )
    return "\n".join(lines)


def _evidence_details(report: ReadinessReport, evidence_ids: list[str]) -> str:
    evidence = {item.id: item for item in report.evidence}
    lines = ["Evidence records:"]
    for evidence_id in evidence_ids:
        if evidence_id not in evidence:
            continue
        item = evidence[evidence_id]
        limitations = "; ".join(item.limitations) or "none"
        lines.append(
            f"- `{item.id}`: `{item.strength}` from `{item.source}`. "
            f"Scope: {item.scope} "
            f"Scan: `{item.forbidden_content_scan}`. Limitations: {limitations}"
        )
    return "\n".join(lines)


def render_launch_gap_register(report: ReadinessReport) -> str:
    return "\n".join(
        [
            "# Launch Gap Register",
            "",
            f"Feature: `{report.feature}`",
            "",
            _launch_gap_table(report),
            "",
            "P0/P1 gaps block `mvp_loop_ready` and `internal_pilot_candidate` until closed.",
            "",
        ]
    )


def write_readiness_outputs(report: ReadinessReport, output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "readiness-report.json").write_text(
        json.dumps(report.model_dump(mode="json"), indent=2, ensure_ascii=False) + "\n"
    )
    (output_dir / "readiness-report.md").write_text(render_markdown_report(report))
    (output_dir / "launch-gap-register.md").write_text(render_launch_gap_register(report))


def _stage_notes(report: ReadinessReport, stage_ids: list[str]) -> str:
    stages = {stage.id: stage for stage in report.stages}
    parts = []
    for stage_id in stage_ids:
        stage = stages[stage_id]
        parts.append(f"- `{stage.id}`: `{stage.status}` / `{stage.evidence_strength}`. {stage.notes}")
    return "\n".join(parts)


def _launch_gap_table(report: ReadinessReport) -> str:
    lines = [
        "| Gap | Severity | Journey | Missing Evidence | Next Action |",
        "|-----|----------|---------|------------------|-------------|",
    ]
    for gap in report.launch_gaps:
        lines.append(
            f"| `{gap.id}` | `{gap.severity}` | {gap.affected_journey} | "
            f"{gap.missing_evidence} | {gap.recommended_next_action} |"
        )
    return "\n".join(lines)


def _next_slice_recommendation(report: ReadinessReport) -> str:
    p1_gaps = [gap for gap in report.launch_gaps if gap.severity == "P1"]
    if report.feature == "034-mvp-loop-readiness" and any(
        gap.id in {"live-desktop-evidence", "production-user-rollout-evidence"} for gap in p1_gaps
    ):
        return (
            "Recommended next product slice: `035-mvp-loop-live-evidence`. "
            "Before any pilot claim, close metadata-safe live desktop/web evidence "
            "and production user-journey proof, while keeping notes/action output "
            "truthful if it remains deferred."
        )
    if report.feature == "035-mvp-loop-live-evidence" and p1_gaps:
        return (
            "Recommended next product slice: `036-owner-review-live-polish`. "
            "Close `web-owner-live-auth-context`, decide `notes-action-output`, "
            "and keep production rollout capped until a commit-safe owner journey passes."
        )
    if report.feature == "036-owner-review-live-polish" and p1_gaps:
        if not any(gap.id == "web-owner-live-auth-context" for gap in p1_gaps):
            return (
                "Recommended next action: keep the 036 claim at `pilot_blocked`; "
                "decide `notes-action-output` through stored generated output or an accepted "
                "pilot deferral, and keep production rollout capped until a live user journey passes."
            )
        return (
            "Recommended next action: keep the 036 claim at `pilot_blocked`; "
            "close `web-owner-live-auth-context` only after metadata-safe live owner "
            "list/detail/governance proof, and keep `notes-action-output` excluded "
            "until stored generated output or an accepted pilot deferral exists."
        )
    if p1_gaps:
        return f"Recommended next action: resolve `{p1_gaps[0].id}` before pilot readiness."
    return "Recommended next action: prepare an internal pilot runbook and production user-journey smoke."
