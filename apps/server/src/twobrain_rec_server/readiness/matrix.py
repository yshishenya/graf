from __future__ import annotations

from datetime import UTC, datetime

from twobrain_rec_server.readiness.evidence import (
    ForbiddenContentScan,
    LaunchGap,
    MvpLoopStage,
    ReadinessEvidence,
    ReferenceComparison,
)

REQUIRED_MVP_LOOP_STAGE_IDS = [
    "local-recording-visible-stop",
    "local-artifact-finalization",
    "upload-server-ingest",
    "mediascribe-processing-import",
    "meeting-list",
    "meeting-detail-transcript-playback",
    "notes-action-output",
    "desktop-embedded-cabinet",
    "access-sharing-download-export",
    "retention-deletion-local-purge",
    "production-deployment-smoke",
    "product-status-next-slice",
]

SEVERITY_ORDER = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}


def utc_now_iso() -> str:
    return datetime.now(UTC).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def sort_launch_gaps(gaps: list[LaunchGap]) -> list[LaunchGap]:
    return sorted(gaps, key=lambda gap: (SEVERITY_ORDER[gap.severity], gap.id))


def p0_p1_blocker_count(gaps: list[LaunchGap]) -> int:
    return sum(1 for gap in gaps if gap.severity in {"P0", "P1"})


def build_default_evidence(
    captured_at: str,
    deployed_commit: str,
    feature: str = "034-mvp-loop-readiness",
) -> list[ReadinessEvidence]:
    evidence = [
        ReadinessEvidence(
            id="spec-034",
            type="document",
            source="specs/034-mvp-loop-readiness/spec.md",
            captured_at=captured_at,
            scope="Defines the MVP loop readiness requirements and forbidden evidence boundaries.",
            strength="docs_only",
            forbidden_content_scan="pass",
        ),
        ReadinessEvidence(
            id="plan-034",
            type="document",
            source="specs/034-mvp-loop-readiness/plan.md",
            captured_at=captured_at,
            scope="Defines the server-side readiness harness and validation strategy.",
            strength="docs_only",
            forbidden_content_scan="pass",
        ),
        ReadinessEvidence(
            id="tasks-034",
            type="github",
            source="specs/034-mvp-loop-readiness/issues.md",
            captured_at=captured_at,
            scope="Maps Spec Kit tasks to GitHub issues #956-#1014.",
            strength="docs_only",
            forbidden_content_scan="pass",
        ),
        ReadinessEvidence(
            id="feature-016-web-review",
            type="document",
            source="docs/current-product-status.md#feature-016-meeting-dashboard-review",
            captured_at=captured_at,
            scope="Accepted server-owned meeting list/detail review cabinet.",
            strength="docs_only",
            forbidden_content_scan="not_applicable",
            limitations=["Synthetic and fixture evidence cannot prove live private meeting review."],
        ),
        ReadinessEvidence(
            id="feature-017-access-egress",
            type="document",
            source="docs/current-product-status.md#feature-017-access-sharing-downloads",
            captured_at=captured_at,
            scope="Accepted browser/server-owned access, sharing, download, and export layer.",
            strength="docs_only",
            forbidden_content_scan="not_applicable",
        ),
        ReadinessEvidence(
            id="feature-018-retention-deletion",
            type="document",
            source="docs/current-product-status.md#feature-018-retention-deletion-execution",
            captured_at=captured_at,
            scope="Accepted retention/deletion execution and local purge truth.",
            strength="docs_only",
            forbidden_content_scan="not_applicable",
        ),
        ReadinessEvidence(
            id="feature-020-finalization",
            type="document",
            source="docs/current-product-status.md#feature-020-speaker-to-mic-leakage",
            captured_at=captured_at,
            scope="Accepted finalization truth gate for dual-track recording packages.",
            strength="docs_only",
            forbidden_content_scan="not_applicable",
        ),
        ReadinessEvidence(
            id="feature-025-system-audio",
            type="document",
            source="docs/current-product-status.md#feature-025-system-audio-capture-pivot",
            captured_at=captured_at,
            scope="Accepted system-audio-first macOS MVP capture path.",
            strength="docs_only",
            forbidden_content_scan="not_applicable",
        ),
        ReadinessEvidence(
            id="feature-022-meeting-mute-truth",
            type="document",
            source="specs/022-meeting-mute-truth/evidence/test-results.md",
            captured_at=captured_at,
            scope=(
                "Accepted product-owned Pause/Resume mute truth, privacy segment "
                "metadata, fail-closed unsupported target handling, and installed "
                "/Applications runtime evidence."
            ),
            strength="local_runtime",
            forbidden_content_scan="pass",
        ),
        ReadinessEvidence(
            id="feature-014-desktop-upload",
            type="document",
            source="CHANGELOG.md#unreleased",
            captured_at=captured_at,
            scope="Accepted desktop upload queue and server-mediated ingest mapping.",
            strength="docs_only",
            forbidden_content_scan="not_applicable",
        ),
        ReadinessEvidence(
            id="feature-015-processing",
            type="document",
            source="docs/current-product-status.md#feature-015-mediascribe-processing-pipeline",
            captured_at=captured_at,
            scope="Accepted server-side MediaScribe processing/import path.",
            strength="docs_only",
            forbidden_content_scan="not_applicable",
        ),
        ReadinessEvidence(
            id="feature-033-desktop-embedding",
            type="document",
            source="docs/current-product-status.md#feature-033-desktop-cabinet-embedding",
            captured_at=captured_at,
            scope="Accepted desktop shell bridge for embedded cabinet routes using synthetic evidence.",
            strength="synthetic",
            forbidden_content_scan="not_applicable",
            limitations=["Fresh live app screenshot evidence is still required for launch claims."],
        ),
        ReadinessEvidence(
            id="desktop-shell-regression-tests",
            type="command",
            source="swift test --package-path apps/macos --disable-swift-testing --filter 'DesktopCabinet|DesktopLocalPurge'",
            captured_at=captured_at,
            scope=(
                "Local macOS regression coverage for workspace-first routing, native capture "
                "boundaries, embedded route policy, upload review identity, and local purge truth."
            ),
            strength="local_runtime",
            forbidden_content_scan="not_applicable",
            limitations=["Command evidence does not replace metadata-safe live desktop screenshots."],
        ),
        ReadinessEvidence(
            id="desktop-first-surface-blocker-note",
            type="document",
            source="docs/evidence/034-mvp-loop-readiness/screenshots/desktop-first-surface-evidence.md",
            captured_at=captured_at,
            scope="Documents safe first-surface desktop evidence and the remaining live screenshot blocker.",
            strength="docs_only",
            forbidden_content_scan="pass",
            limitations=["No live screenshot is committed."],
        ),
        ReadinessEvidence(
            id="desktop-embedded-detail-blocker-note",
            type="document",
            source="docs/evidence/034-mvp-loop-readiness/screenshots/desktop-embedded-detail-evidence.md",
            captured_at=captured_at,
            scope="Documents safe embedded detail evidence and the remaining live screenshot blocker.",
            strength="docs_only",
            forbidden_content_scan="pass",
            limitations=["No live embedded detail screenshot is committed."],
        ),
        ReadinessEvidence(
            id="web-cabinet-regression-tests",
            type="command",
            source=(
                "uv run --extra dev pytest -q tests/unit/test_cabinet_web_shell.py "
                "tests/integration/test_cabinet_meeting_list.py tests/integration/test_cabinet_meeting_detail.py"
            ),
            captured_at=captured_at,
            scope=(
                "Local fixture coverage for web list/detail IA, embedded cabinet boundaries, "
                "transcript/playback/provenance, notes placeholders, and governance slots."
            ),
            strength="local_runtime",
            forbidden_content_scan="not_applicable",
            limitations=["Fixture web tests do not prove live private meeting screenshots."],
        ),
        ReadinessEvidence(
            id="web-meeting-list-blocker-note",
            type="document",
            source="docs/evidence/034-mvp-loop-readiness/screenshots/web-meeting-list-evidence.md",
            captured_at=captured_at,
            scope="Documents metadata-safe web list evidence and live screenshot boundary.",
            strength="docs_only",
            forbidden_content_scan="pass",
            limitations=["No live browser screenshot is committed."],
        ),
        ReadinessEvidence(
            id="web-meeting-detail-blocker-note",
            type="document",
            source="docs/evidence/034-mvp-loop-readiness/screenshots/web-meeting-detail-evidence.md",
            captured_at=captured_at,
            scope="Documents metadata-safe meeting detail evidence and live screenshot boundary.",
            strength="docs_only",
            forbidden_content_scan="pass",
            limitations=["No live browser screenshot is committed."],
        ),
        ReadinessEvidence(
            id="reference-comparison-note",
            type="reference_review",
            source="docs/evidence/034-mvp-loop-readiness/reference-comparison.md",
            captured_at=captured_at,
            scope="Clean-room comparison of allowed IA lessons and forbidden Krisp similarity.",
            strength="docs_only",
            forbidden_content_scan="pass",
        ),
        ReadinessEvidence(
            id="policy-lifecycle-regression-tests",
            type="command",
            source=(
                "uv run --extra dev pytest -q tests/contract/test_access_sharing_downloads_contract.py "
                "tests/contract/test_retention_deletion_contract.py "
                "tests/unit/test_deletion_report_view_models.py "
                "tests/integration/test_local_purge_coordination.py"
            ),
            captured_at=captured_at,
            scope=(
                "Local fixture coverage for login-required sharing, bounded download/export, "
                "deletion report partitioning, dependency truth, post-egress limits, and local purge acknowledgements."
            ),
            strength="local_runtime",
            forbidden_content_scan="not_applicable",
            limitations=["Fixture lifecycle tests do not perform destructive production deletion."],
        ),
        ReadinessEvidence(
            id="policy-lifecycle-evidence-note",
            type="document",
            source="docs/evidence/034-mvp-loop-readiness/policy-lifecycle-evidence.md",
            captured_at=captured_at,
            scope="Documents metadata-safe policy, egress, retention, deletion, and local purge evidence boundaries.",
            strength="docs_only",
            forbidden_content_scan="pass",
        ),
        ReadinessEvidence(
            id="production-018-infra-smoke",
            type="production_smoke",
            source=f"master deploy/smoke for commit {deployed_commit}",
            captured_at=captured_at,
            scope="Production deployment reached infra_smoke_ready after 018 merge.",
            strength="production_smoke",
            forbidden_content_scan="not_applicable",
            limitations=["infra_smoke_ready is not user rollout readiness."],
        ),
        ReadinessEvidence(
            id="reference-clean-room-contract",
            type="reference_review",
            source="specs/034-mvp-loop-readiness/contracts/reference-comparison-contract.md",
            captured_at=captured_at,
            scope="Defines allowed IA/category reference lessons and forbidden Krisp copy/private content.",
            strength="docs_only",
            forbidden_content_scan="not_applicable",
        ),
        ReadinessEvidence(
            id="current-product-status-034-next-slice",
            type="document",
            source="docs/current-product-status.md#next-product-slice",
            captured_at=captured_at,
            scope="Current status records the 034 readiness outcome and evidence-based next product slice.",
            strength="docs_only",
            forbidden_content_scan="pass",
        ),
    ]
    if feature == "035-mvp-loop-live-evidence":
        evidence.extend(
            [
                ReadinessEvidence(
                    id="feature-035-live-evidence-pack",
                    type="document",
                    source="docs/evidence/035-mvp-loop-live-evidence/README.md",
                    captured_at=captured_at,
                    scope="Defines metadata-safe evidence boundaries and the strongest truthful 035 claim.",
                    strength="docs_only",
                    forbidden_content_scan="pass",
                ),
                ReadinessEvidence(
                    id="feature-035-validation-log",
                    type="document",
                    source="docs/evidence/035-mvp-loop-live-evidence/validation-log.md",
                    captured_at=captured_at,
                    scope="Records 035 command/manual validation evidence and blockers.",
                    strength="docs_only",
                    forbidden_content_scan="pass",
                ),
                ReadinessEvidence(
                    id="feature-035-clean-room-reference",
                    type="reference_review",
                    source="docs/evidence/035-mvp-loop-live-evidence/clean-room-reference.md",
                    captured_at=captured_at,
                    scope="Records allowed reference lessons and forbidden similarity checks for 035.",
                    strength="docs_only",
                    forbidden_content_scan="pass",
                ),
                ReadinessEvidence(
                    id="feature-035-github-issues",
                    type="github",
                    source="specs/035-mvp-loop-live-evidence/issues.md",
                    captured_at=captured_at,
                    scope="Maps all 035 Spec Kit tasks to GitHub issues #1064-#1106.",
                    strength="docs_only",
                    forbidden_content_scan="pass",
                ),
                ReadinessEvidence(
                    id="feature-035-web-live-auth-blocker",
                    type="endpoint",
                    source="https://rec.2brain.pro/meetings",
                    captured_at=captured_at,
                    scope=(
                        "Production web route exists but live Chrome owner review returned "
                        "401 missing_auth_context without a committed private session."
                    ),
                    strength="blocked",
                    forbidden_content_scan="pass",
                    limitations=[
                        "No private screenshots, cookies, tokens, or account content are committed.",
                        "Route availability is proven separately from authenticated owner review.",
                    ],
                ),
                ReadinessEvidence(
                    id="feature-035-web-list-evidence",
                    type="document",
                    source="docs/evidence/035-mvp-loop-live-evidence/screenshots/web-meeting-list-evidence.md",
                    captured_at=captured_at,
                    scope="Documents production list route blocker and fixture-backed meeting list coverage.",
                    strength="local_runtime",
                    forbidden_content_scan="pass",
                    limitations=["Fixture-backed list evidence does not prove a live private owner account."],
                ),
                ReadinessEvidence(
                    id="feature-035-web-detail-evidence",
                    type="document",
                    source="docs/evidence/035-mvp-loop-live-evidence/screenshots/web-meeting-detail-evidence.md",
                    captured_at=captured_at,
                    scope="Documents production detail route blocker and fixture-backed transcript/playback coverage.",
                    strength="local_runtime",
                    forbidden_content_scan="pass",
                    limitations=["Fixture-backed detail evidence does not include private meeting content."],
                ),
                ReadinessEvidence(
                    id="feature-035-web-governance-evidence",
                    type="document",
                    source="docs/evidence/035-mvp-loop-live-evidence/screenshots/web-governance-evidence.md",
                    captured_at=captured_at,
                    scope="Documents fixture-backed share/export/deletion governance coverage and live auth blocker.",
                    strength="local_runtime",
                    forbidden_content_scan="pass",
                    limitations=["No destructive production sharing, export, or deletion action was performed."],
                ),
                ReadinessEvidence(
                    id="feature-035-readiness-report-json",
                    type="document",
                    source="docs/evidence/035-mvp-loop-live-evidence/readiness-report.json",
                    captured_at=captured_at,
                    scope="Structured 035 readiness report generated from the current evidence matrix.",
                    strength="docs_only",
                    forbidden_content_scan="pass",
                ),
                ReadinessEvidence(
                    id="feature-035-readiness-report-md",
                    type="document",
                    source="docs/evidence/035-mvp-loop-live-evidence/readiness-report.md",
                    captured_at=captured_at,
                    scope="Reviewer-facing 035 readiness summary with the current bounded claim.",
                    strength="docs_only",
                    forbidden_content_scan="pass",
                ),
                ReadinessEvidence(
                    id="feature-035-launch-gap-register",
                    type="document",
                    source="docs/evidence/035-mvp-loop-live-evidence/launch-gap-register.md",
                    captured_at=captured_at,
                    scope="035 launch gap register with remaining P1/P2 blockers and next actions.",
                    strength="docs_only",
                    forbidden_content_scan="pass",
                ),
                ReadinessEvidence(
                    id="current-product-status-035-next-slice",
                    type="document",
                    source="docs/current-product-status.md#next-product-slice",
                    captured_at=captured_at,
                    scope="Current status records the 035 outcome and the next evidence-based product slice.",
                    strength="docs_only",
                    forbidden_content_scan="pass",
                ),
                ReadinessEvidence(
                    id="changelog-035",
                    type="document",
                    source="CHANGELOG.md#unreleased",
                    captured_at=captured_at,
                    scope="Changelog records the 035 validation-only evidence pack and claim boundary.",
                    strength="docs_only",
                    forbidden_content_scan="pass",
                ),
            ]
        )
    if feature == "036-owner-review-live-polish":
        evidence.extend(
            [
                ReadinessEvidence(
                    id="feature-035-live-evidence-pack",
                    type="document",
                    source="docs/evidence/035-mvp-loop-live-evidence/README.md",
                    captured_at=captured_at,
                    scope=(
                        "Accepted installed /Applications desktop loop evidence reused as the "
                        "recording-control foundation for 036 readiness."
                    ),
                    strength="local_runtime",
                    forbidden_content_scan="pass",
                ),
                ReadinessEvidence(
                    id="feature-036-owner-review-live",
                    type="endpoint",
                    source="docs/evidence/036-owner-review-live-polish/screenshots/web-owner-review-evidence.md",
                    captured_at=captured_at,
                    scope=(
                        "Production Chrome owner session proves the meeting list, one detail "
                        "route, notes/transcript state, access/share summary, delete panel, "
                        "and governance controls with metadata-safe labels and counts only."
                    ),
                    strength="live",
                    forbidden_content_scan="pass",
                    limitations=[
                        "No screenshots, cookies, tokens, account identifiers, meeting titles, meeting ids, or transcript text are committed.",
                        "Destructive governance actions were not clicked; only visible disabled/available states were recorded.",
                    ],
                ),
                ReadinessEvidence(
                    id="feature-036-validation-log",
                    type="document",
                    source="docs/evidence/036-owner-review-live-polish/validation-log.md",
                    captured_at=captured_at,
                    scope="Records 036 command/manual validation evidence and remaining blockers.",
                    strength="docs_only",
                    forbidden_content_scan="pass",
                ),
                ReadinessEvidence(
                    id="feature-036-notes-action-truth",
                    type="document",
                    source="docs/evidence/036-owner-review-live-polish/screenshots/web-notes-action-truth-evidence.md",
                    captured_at=captured_at,
                    scope=(
                        "Records structured Summary, Decisions, Action Items, and Follow-ups "
                        "truth states with processing, blocked, deferred, unavailable, and available contracts."
                    ),
                    strength="local_runtime",
                    forbidden_content_scan="pass",
                    limitations=["Launchable generated notes/actions remain unaccepted until stored output is proven."],
                ),
                ReadinessEvidence(
                    id="feature-036-clean-room-reference",
                    type="reference_review",
                    source="docs/evidence/036-owner-review-live-polish/clean-room-reference.md",
                    captured_at=captured_at,
                    scope="Records V8 clean-room alignment, accepted runtime polish, and remaining live proof gaps.",
                    strength="local_runtime",
                    forbidden_content_scan="pass",
                ),
                ReadinessEvidence(
                    id="feature-036-installed-app-visual-polish",
                    type="screenshot",
                    source="docs/evidence/036-owner-review-live-polish/screenshots/installed-app-ui-parity-2026-06-17.png",
                    captured_at=captured_at,
                    scope=(
                        "Installed app visual parity evidence for native/WebView palette, compact rail, "
                        "responsive sidebar, and product workspace polish."
                    ),
                    strength="local_runtime",
                    forbidden_content_scan="pass",
                    limitations=["Final capture-state walkthrough is recorded separately as cropped native-inspector evidence."],
                ),
                ReadinessEvidence(
                    id="feature-036-installed-app-final-walkthrough",
                    type="document",
                    source=(
                        "docs/evidence/036-owner-review-live-polish/screenshots/"
                        "installed-app-final-walkthrough-2026-06-22.md"
                    ),
                    captured_at=captured_at,
                    scope=(
                        "Installed /Applications app idle, active, paused, resumed, stopped, "
                        "configured, missing-auth, and local-only walkthrough evidence."
                    ),
                    strength="local_runtime",
                    forbidden_content_scan="pass",
                    limitations=["Full-window captures were not committed; only metadata-safe native-inspector crops are linked."],
                ),
                ReadinessEvidence(
                    id="feature-036-github-issues",
                    type="github",
                    source="specs/036-owner-review-live-polish/issues.md",
                    captured_at=captured_at,
                    scope="Maps 036 Spec Kit tasks to GitHub issues and records remaining open closeout tails.",
                    strength="docs_only",
                    forbidden_content_scan="pass",
                ),
                ReadinessEvidence(
                    id="feature-036-readiness-report-json",
                    type="document",
                    source="docs/evidence/036-owner-review-live-polish/readiness-report.json",
                    captured_at=captured_at,
                    scope="Structured 036 readiness report generated from the current evidence matrix.",
                    strength="docs_only",
                    forbidden_content_scan="pass",
                ),
                ReadinessEvidence(
                    id="feature-036-readiness-report-md",
                    type="document",
                    source="docs/evidence/036-owner-review-live-polish/readiness-report.md",
                    captured_at=captured_at,
                    scope="Reviewer-facing 036 readiness summary with the current bounded claim.",
                    strength="docs_only",
                    forbidden_content_scan="pass",
                ),
                ReadinessEvidence(
                    id="feature-036-launch-gap-register",
                    type="document",
                    source="docs/evidence/036-owner-review-live-polish/launch-gap-register.md",
                    captured_at=captured_at,
                    scope="036 launch gap register with remaining P1/P2 blockers and next actions.",
                    strength="docs_only",
                    forbidden_content_scan="pass",
                ),
                ReadinessEvidence(
                    id="current-product-status-036-closeout",
                    type="document",
                    source="docs/current-product-status.md#next-product-slice",
                    captured_at=captured_at,
                    scope="Current status records 036 as a visual/auth baseline while keeping pilot claims blocked.",
                    strength="docs_only",
                    forbidden_content_scan="pass",
                ),
                ReadinessEvidence(
                    id="changelog-036",
                    type="document",
                    source="CHANGELOG.md#unreleased",
                    captured_at=captured_at,
                    scope="Changelog records the 036 readiness closeout and remaining live proof boundaries.",
                    strength="docs_only",
                    forbidden_content_scan="pass",
                ),
            ]
        )
    return evidence


def build_default_launch_gaps(feature: str = "034-mvp-loop-readiness") -> list[LaunchGap]:
    is_036 = feature == "036-owner-review-live-polish"
    live_desktop_gap = (
        []
        if feature in {"035-mvp-loop-live-evidence", "036-owner-review-live-polish"}
        else [
            LaunchGap(
                id="live-desktop-evidence",
                severity="P1",
                affected_journey="desktop-embedded-cabinet",
                current_evidence="Feature 033 synthetic evidence plus 034 local macOS regression evidence and blocker notes.",
                missing_evidence="Fresh metadata-safe live desktop screenshots or explicit product-owner acceptance of the blocker.",
                recommended_next_action="Capture desktop first-surface and embedded detail screenshots without private content.",
                owner_area="desktop",
            )
        ]
    )
    feature_035_gaps = (
        [
            LaunchGap(
                id="web-owner-live-auth-context",
                severity="P1",
                affected_journey="meeting-list",
                current_evidence=(
                    "Production /meetings route exists and fixture-backed list/detail/governance "
                    "evidence is committed, but live Chrome owner review returned missing auth context."
                ),
                missing_evidence=(
                    "Commit-safe authenticated owner review proof on rec.2brain.pro for list, "
                    "detail, and governance states."
                ),
                recommended_next_action=(
                    "Implement or validate the owner auth/session path for rec.2brain.pro, then "
                    "capture metadata-safe owner review evidence."
                ),
                owner_area="web",
            ),
            LaunchGap(
                id="desktop-product-surface-polish",
                severity="P2",
                affected_journey="desktop-embedded-cabinet",
                current_evidence="Installed desktop screenshots prove the local capture loop but show an operational local-mode surface.",
                missing_evidence="Accepted desktop/web product surface polish against the clean-room V8 implementation baseline.",
                recommended_next_action="Use the accepted 030 V8 baseline in the next UI implementation slice.",
                owner_area="ux",
            ),
        ]
        if feature == "035-mvp-loop-live-evidence"
        else []
    )
    feature_036_gaps: list[LaunchGap] = []
    return sort_launch_gaps(
        [
            *live_desktop_gap,
            *feature_035_gaps,
            *feature_036_gaps,
            LaunchGap(
                id="notes-action-output",
                severity="P1",
                affected_journey="notes-action-output",
                current_evidence=(
                    "Meeting detail records structured notes/action truth states."
                    if is_036
                    else "Meeting detail shows truthful planned notes/assistant placeholders."
                ),
                missing_evidence=(
                    "Stored/generated launchable notes and action output, or explicit owner-approved pilot deferral."
                    if is_036
                    else "Notes/action output availability or truthful blocked state in review surfaces."
                ),
                recommended_next_action=(
                    "Either implement stored generated notes/actions or record an accepted narrower pilot deferral."
                    if is_036
                    else "Decide whether the next slice is assistant notes/actions or explicit MVP deferral."
                ),
                owner_area="web",
            ),
            LaunchGap(
                id="production-user-rollout-evidence",
                severity="P1",
                affected_journey="production-deployment-smoke",
                current_evidence="Production smoke proves infra_smoke_ready only.",
                missing_evidence="Internal pilot or user rollout validation with live app journey evidence.",
                recommended_next_action="Keep production claim capped until a pilot runbook or live loop validation passes.",
                owner_area="ops",
            ),
            LaunchGap(
                id="signed-installer-evidence",
                severity="P2",
                affected_journey="desktop-distribution",
                current_evidence="Local/ad-hoc development package evidence exists.",
                missing_evidence="signed installer evidence for broader pilot distribution.",
                recommended_next_action="Plan installer signing/notarization as a follow-up slice if pilot distribution needs it.",
                owner_area="ops",
            ),
            LaunchGap(
                id="browser-target-gaps",
                severity="P2",
                affected_journey="capture-target-coverage",
                current_evidence="Yandex Browser remains intentionally skipped/not accepted.",
                missing_evidence="Target matrix decision for browser coverage before pilot promises.",
                recommended_next_action="Keep unsupported targets explicit or run a browser target hardening slice.",
                owner_area="desktop",
            ),
        ]
    )


def build_default_stages(feature: str = "034-mvp-loop-readiness") -> list[MvpLoopStage]:
    is_035 = feature == "035-mvp-loop-live-evidence"
    is_036 = feature == "036-owner-review-live-polish"
    desktop_capture_evidence = [
        "feature-025-system-audio",
        "feature-022-meeting-mute-truth",
        "desktop-shell-regression-tests",
    ]
    if is_035:
        desktop_capture_evidence.extend(["feature-035-live-evidence-pack", "feature-035-validation-log"])
    if is_036:
        desktop_capture_evidence.extend(
            [
                "feature-035-live-evidence-pack",
                "feature-036-validation-log",
                "feature-036-installed-app-final-walkthrough",
            ]
        )

    meeting_list_evidence = [
        "feature-016-web-review",
        "feature-017-access-egress",
        "web-cabinet-regression-tests",
        "web-meeting-list-blocker-note",
    ]
    meeting_detail_evidence = [
        "feature-016-web-review",
        "web-cabinet-regression-tests",
        "web-meeting-detail-blocker-note",
    ]
    notes_evidence = ["web-cabinet-regression-tests", "web-meeting-detail-blocker-note"]
    governance_evidence = [
        "feature-017-access-egress",
        "policy-lifecycle-regression-tests",
        "policy-lifecycle-evidence-note",
    ]
    product_status_evidence = ["current-product-status-034-next-slice"]
    if is_035:
        meeting_list_evidence.extend(
            [
                "feature-035-web-live-auth-blocker",
                "feature-035-web-list-evidence",
            ]
        )
        meeting_detail_evidence.extend(
            [
                "feature-035-web-live-auth-blocker",
                "feature-035-web-detail-evidence",
            ]
        )
        notes_evidence.extend(["feature-035-web-detail-evidence"])
        governance_evidence.extend(["feature-035-web-governance-evidence"])
        product_status_evidence = [
            "feature-035-readiness-report-json",
            "feature-035-readiness-report-md",
            "feature-035-launch-gap-register",
            "current-product-status-035-next-slice",
            "changelog-035",
        ]
    if is_036:
        meeting_list_evidence.extend(["feature-036-owner-review-live", "feature-036-validation-log"])
        meeting_detail_evidence.extend(["feature-036-owner-review-live", "feature-036-validation-log"])
        notes_evidence.extend(["feature-036-notes-action-truth"])
        governance_evidence.extend(["feature-036-owner-review-live"])
        product_status_evidence = [
            "feature-036-readiness-report-json",
            "feature-036-readiness-report-md",
            "feature-036-launch-gap-register",
            "current-product-status-036-closeout",
            "changelog-036",
        ]

    return [
        MvpLoopStage(
            id="local-recording-visible-stop",
            label="Local recording and visible stop",
            owner_surface="macos_native",
            status="ready",
            evidence_strength="local_runtime",
            evidence_ids=desktop_capture_evidence,
            claim_impact=["desktop_loop_verified", "mvp_loop_ready"],
            notes=(
                "System-audio capture, visible stop, product-owned Pause/Resume "
                "privacy truth, and installed /Applications runtime evidence are accepted."
                if not (is_035 or is_036)
                else (
                    "Installed /Applications runtime evidence covers Record, Pause, Resume, "
                    "Stop, latest artifact validation, and visible local capture truth."
                )
            ),
        ),
        MvpLoopStage(
            id="local-artifact-finalization",
            label="Local artifact finalization and leakage gate",
            owner_surface="macos_native",
            status="ready",
            evidence_strength="docs_only",
            evidence_ids=["feature-020-finalization"],
            claim_impact=["desktop_loop_verified", "mvp_loop_ready"],
            notes="Finalization truth gate is accepted for dual-track packages.",
        ),
        MvpLoopStage(
            id="upload-server-ingest",
            label="Upload queue and server ingest",
            owner_surface="server_backend",
            status="ready",
            evidence_strength="docs_only",
            evidence_ids=["feature-014-desktop-upload"],
            claim_impact=["web_review_verified", "mvp_loop_ready"],
            notes="Desktop upload queue and server-mediated ingest are accepted foundations.",
        ),
        MvpLoopStage(
            id="mediascribe-processing-import",
            label="MediaScribe processing and result import",
            owner_surface="server_backend",
            status="ready",
            evidence_strength="docs_only",
            evidence_ids=["feature-015-processing"],
            claim_impact=["web_review_verified", "mvp_loop_ready"],
            notes="Processing pipeline is accepted; desktop clients still do not hold MediaScribe credentials.",
        ),
        MvpLoopStage(
            id="meeting-list",
            label="Meeting list",
            owner_surface="web_cabinet",
            status="degraded" if is_035 else "ready",
            evidence_strength="local_runtime",
            evidence_ids=meeting_list_evidence,
            launch_gap_ids=["web-owner-live-auth-context"] if is_035 else [],
            claim_impact=["web_review_verified", "mvp_loop_ready"],
            notes=(
                "List route has fixture and local regression evidence with authorized access states; live private list evidence is not committed."
                if not (is_035 or is_036)
                else (
                    "Production Chrome owner session proves the list route with metadata-safe counts and state labels."
                    if is_036
                    else (
                        "Production list/auth polish exists and fixture evidence is safe, but live owner "
                        "list proof remains blocked until a commit-safe owner session is available."
                    )
                )
            ),
        ),
        MvpLoopStage(
            id="meeting-detail-transcript-playback",
            label="Meeting detail transcript, playback, and provenance",
            owner_surface="web_cabinet",
            status="degraded" if is_035 else "ready",
            evidence_strength="local_runtime",
            evidence_ids=meeting_detail_evidence,
            launch_gap_ids=["web-owner-live-auth-context"] if is_035 else [],
            claim_impact=["web_review_verified", "mvp_loop_ready"],
            notes=(
                "Ready/partial/processing/failed detail states have local fixture evidence for transcript, playback, and provenance."
                if not (is_035 or is_036)
                else (
                    "Production Chrome owner session proves one detail route, transcript panel, notes/action truth states, and governance surface metadata-safely."
                    if is_036
                    else (
                        "Ready/partial/processing/failed detail states are fixture-backed; live "
                        "private detail and governance proof remains blocked by missing approved owner-session evidence."
                    )
                )
            ),
        ),
        MvpLoopStage(
            id="notes-action-output",
            label="Notes and action output",
            owner_surface="web_cabinet",
            status="blocked",
            evidence_strength="local_runtime",
            evidence_ids=notes_evidence,
            launch_gap_ids=["notes-action-output"],
            claim_impact=["mvp_loop_ready"],
            notes=(
                "The interface exposes structured notes/action truth states; launchable generated notes/action output remains unaccepted."
                if is_036
                else "The interface shows truthful planned notes/assistant placeholders; launchable notes/action output remains missing."
            ),
        ),
        MvpLoopStage(
            id="desktop-embedded-cabinet",
            label="Desktop embedded cabinet",
            owner_surface="desktop_embedded_web",
            status="ready" if is_036 else "degraded",
            evidence_strength="local_runtime",
            evidence_ids=[
                "feature-033-desktop-embedding",
                "desktop-shell-regression-tests",
                "desktop-first-surface-blocker-note",
                "desktop-embedded-detail-blocker-note",
                *(
                    [
                        "feature-036-installed-app-visual-polish",
                        "feature-036-installed-app-final-walkthrough",
                        "feature-036-clean-room-reference",
                    ]
                    if is_036
                    else []
                ),
            ],
            launch_gap_ids=(
                [] if is_036 else (["desktop-product-surface-polish"] if is_035 else ["live-desktop-evidence"])
            ),
            claim_impact=["desktop_loop_verified", "mvp_loop_ready"],
            notes=(
                "Embedding has synthetic and local regression evidence; fresh metadata-safe live screenshots are still required."
                if not (is_035 or is_036)
                else (
                    "Installed desktop product polish and final /Applications capture-state "
                    "walkthrough evidence are current; broad launch remains blocked by web, "
                    "notes/action, and production rollout gaps."
                )
            ),
        ),
        MvpLoopStage(
            id="access-sharing-download-export",
            label="Access, sharing, download, and export",
            owner_surface="web_cabinet",
            status="ready",
            evidence_strength="local_runtime",
            evidence_ids=governance_evidence,
            claim_impact=["policy_lifecycle_verified", "mvp_loop_ready"],
            notes="Access/egress policy is accepted and locally regressed with bounded artifact actions.",
        ),
        MvpLoopStage(
            id="retention-deletion-local-purge",
            label="Retention, deletion, and local purge truth",
            owner_surface="server_backend",
            status="ready",
            evidence_strength="local_runtime",
            evidence_ids=[
                "feature-018-retention-deletion",
                "policy-lifecycle-regression-tests",
                "policy-lifecycle-evidence-note",
            ],
            claim_impact=["policy_lifecycle_verified", "mvp_loop_ready"],
            notes="Deletion reports, dependency limits, post-egress limits, and local purge acknowledgements are locally regressed as metadata-only truth.",
        ),
        MvpLoopStage(
            id="production-deployment-smoke",
            label="Production deployment and smoke boundary",
            owner_surface="production_infra",
            status="degraded",
            evidence_strength="production_smoke",
            evidence_ids=["production-018-infra-smoke"],
            launch_gap_ids=["production-user-rollout-evidence"],
            claim_impact=["infra_smoke_ready"],
            notes="Production evidence proves infra_smoke_ready, not pilot or user rollout readiness.",
        ),
        MvpLoopStage(
            id="product-status-next-slice",
            label="Product status and next-slice truth",
            owner_surface="docs_status",
            status="ready",
            evidence_strength="docs_only",
            evidence_ids=product_status_evidence,
            claim_impact=["partial_readiness"],
            notes=(
                "The status document records the 034 bounded outcome and next evidence-based product slice."
                if not (is_035 or is_036)
                else (
                    "The generated 036 readiness pack records the current bounded claim and remaining live-proof gaps."
                    if is_036
                    else "The generated 035 readiness pack records the current bounded claim and next product slice."
                )
            ),
        ),
    ]


def build_default_reference_comparisons(feature: str = "034-mvp-loop-readiness") -> list[ReferenceComparison]:
    is_035 = feature == "035-mvp-loop-live-evidence"
    is_036 = feature == "036-owner-review-live-polish"
    checks = [
        "No committed private Krisp screenshots.",
        "No copied Krisp visual expression, brand assets, colors, or icons.",
        "No exact Krisp product copy beyond short category labels.",
    ]
    return [
        ReferenceComparison(
            id="desktop-first-viewport",
            surface="desktop_home",
            allowed_lessons=["Meeting workspace first", "Native capture authority remains local"],
            implementation_alignment=(
                "033 establishes the desktop cabinet shell and 034 adds local regression evidence; live screenshots are still blocked."
                if not (is_035 or is_036)
                else (
                    "036 installed-app screenshots and final walkthrough prove native/WebView "
                    "visual parity, product-workspace polish, and idle/active/paused/resumed/stopped "
                    "local control states."
                    if is_036
                    else (
                        "035 proves the installed local capture loop, but the visible desktop "
                        "surface is still an operational local-mode workspace that needs the "
                        "accepted V8 meeting-workspace polish."
                    )
                )
            ),
            intentional_differences=["2brain keeps Record/Stop as native trust controls."],
            forbidden_similarity_checks=checks,
            result="pass" if is_036 else "needs_polish",
            evidence_ids=[
                "feature-033-desktop-embedding",
                "desktop-shell-regression-tests",
                "desktop-first-surface-blocker-note",
                "reference-clean-room-contract",
                "reference-comparison-note",
                *(
                    [
                        "feature-035-live-evidence-pack",
                        "feature-035-clean-room-reference",
                    ]
                    if is_035
                    else []
                ),
                *(
                    [
                        "feature-036-installed-app-visual-polish",
                        "feature-036-installed-app-final-walkthrough",
                        "feature-036-clean-room-reference",
                    ]
                    if is_036
                    else []
                ),
            ],
        ),
        ReferenceComparison(
            id="web-list-workspace",
            surface="web_list",
            allowed_lessons=["Meeting list, filters, sort, upload slot, and future action slots are discoverable"],
            implementation_alignment=(
                "034 verifies the web list and desktop-embedded list with fixture-backed local tests."
                if not (is_035 or is_036)
                else (
                    "036 improves browser auth/list polish and records the remaining "
                    "metadata-safe live owner list proof without committing private meeting content."
                    if is_036
                    else (
                        "035 keeps the web list fixture-backed and records the production "
                        "auth-context blocker before live owner screenshots can be committed."
                    )
                )
            ),
            intentional_differences=["2brain keeps capture creation out of embedded web content."],
            forbidden_similarity_checks=checks,
            result="needs_polish" if (is_035 or is_036) else "pass",
            evidence_ids=[
                "web-cabinet-regression-tests",
                "web-meeting-list-blocker-note",
                "reference-comparison-note",
                *(
                    [
                        "feature-035-web-live-auth-blocker",
                        "feature-035-web-list-evidence",
                        "feature-035-clean-room-reference",
                    ]
                    if is_035
                    else []
                ),
                *(["feature-036-owner-review-live", "feature-036-clean-room-reference"] if is_036 else []),
            ],
        ),
        ReferenceComparison(
            id="web-review-workspace",
            surface="web_detail",
            allowed_lessons=["Transcript/playback/provenance are discoverable in one review workspace"],
            implementation_alignment=(
                "016/017/018 provide the server-owned review/governance surfaces; 034 verifies placeholders and embedded boundaries."
                if not (is_035 or is_036)
                else (
                    "016/017/018 provide the server-owned review/governance surfaces; "
                    "036 records structured notes/action truth and visual polish while "
                    "live owner detail/governance proof is metadata-safe; generated notes/actions remain blocked."
                    if is_036
                    else (
                        "016/017/018 provide the server-owned review/governance surfaces; "
                        "035 records fixture-backed detail evidence while live owner review "
                        "and generated notes/actions remain blocked."
                    )
                )
            ),
            intentional_differences=["2brain uses its own design language and truthful placeholder policy."],
            forbidden_similarity_checks=checks,
            result="needs_polish" if (is_035 or is_036) else "pass",
            evidence_ids=[
                "feature-016-web-review",
                "feature-017-access-egress",
                "web-cabinet-regression-tests",
                "web-meeting-detail-blocker-note",
                "reference-comparison-note",
                *(
                    ["feature-035-web-detail-evidence", "feature-035-clean-room-reference"]
                    if is_035
                    else []
                ),
                *(["feature-036-notes-action-truth", "feature-036-clean-room-reference"] if is_036 else []),
            ],
        ),
        ReferenceComparison(
            id="governance-actions",
            surface="governance",
            allowed_lessons=["Share, export/download, deletion, and lifecycle truth must be visible by policy"],
            implementation_alignment=(
                "017/018 cover policy-owned access, egress, retention, deletion, and purge truth."
                if not (is_035 or is_036)
                else (
                    "017/018 cover policy-owned access, egress, retention, deletion, and "
                    "purge truth; 036 now records live owner governance panel states "
                    "without clicking destructive actions."
                )
            ),
            intentional_differences=["External public links remain out of scope."],
            forbidden_similarity_checks=checks,
            result="pass",
            evidence_ids=[
                "feature-017-access-egress",
                "feature-018-retention-deletion",
                "policy-lifecycle-regression-tests",
                "policy-lifecycle-evidence-note",
                *(
                    ["feature-035-web-governance-evidence", "feature-035-clean-room-reference"]
                    if is_035
                    else []
                ),
                *(["feature-036-owner-review-live", "feature-036-clean-room-reference"] if is_036 else []),
            ],
        ),
    ]


def passed_forbidden_content_scan(feature: str = "034-mvp-loop-readiness") -> ForbiddenContentScan:
    evidence_dir = f"docs/evidence/{feature}"
    return ForbiddenContentScan(
        status="pass",
        commands=[
            f"rg -n -i real private-value patterns specs/{feature} {evidence_dir} docs/current-product-status.md CHANGELOG.md",
            f"find {evidence_dir}/screenshots -type f -name '*.png' -o -name '*.jpg' -o -name '*.jpeg' -o -name '*.webp'",
            f"rg -n -i evidence payload-id patterns {evidence_dir}",
        ],
        matches=[],
    )
