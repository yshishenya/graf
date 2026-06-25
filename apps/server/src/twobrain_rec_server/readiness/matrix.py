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
FEATURE_049_ID = "049-meeting-outcomes-mvp"
FEATURE_050_ID = "050-mvp-launch-proof"
FEATURE_051_ID = "051-mvp-owner-journey-proof"
FEATURE_052_ID = "052-mvp-live-ui-proof"


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
    if feature in {FEATURE_049_ID, FEATURE_050_ID, FEATURE_051_ID, FEATURE_052_ID}:
        evidence.extend(
            [
                ReadinessEvidence(
                    id="feature-035-live-evidence-pack",
                    type="document",
                    source="docs/evidence/035-mvp-loop-live-evidence/README.md",
                    captured_at=captured_at,
                    scope=(
                        "Accepted installed /Applications desktop loop evidence reused as the "
                        "recording-control foundation for 049-051 readiness."
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
                        "Production Chrome owner session proves the meeting list, one detail route, "
                        "notes/transcript state, access/share summary, delete panel, and governance "
                        "controls with metadata-safe labels and counts only."
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
                    id="feature-036-clean-room-reference",
                    type="reference_review",
                    source="docs/evidence/036-owner-review-live-polish/clean-room-reference.md",
                    captured_at=captured_at,
                    scope="Records V8 clean-room alignment, accepted runtime polish, and remaining live proof gaps.",
                    strength="local_runtime",
                    forbidden_content_scan="pass",
                ),
                ReadinessEvidence(
                    id="feature-048-real-playback-availability",
                    type="document",
                    source="specs/048-real-playback-availability/evidence/validation-log.md",
                    captured_at=captured_at,
                    scope=(
                        "Records real visible review playback, timestamp seek, range playback, "
                        "and web/desktop embedded parity after the 048 release."
                    ),
                    strength="local_runtime",
                    forbidden_content_scan="pass",
                ),
                ReadinessEvidence(
                    id="feature-049-stored-outcomes",
                    type="command",
                    source=(
                        "uv run --extra dev pytest -q tests/unit/test_meeting_outcomes_generator.py "
                        "tests/integration/test_meeting_outcomes_generation.py "
                        "tests/integration/test_cabinet_meeting_outcomes.py "
                        "tests/integration/test_meeting_outcomes_orchestration_benchmark.py"
                    ),
                    captured_at=captured_at,
                    scope=(
                        "Focused local runtime coverage proves deterministic stored meeting outcomes, "
                        "category truth, transcript evidence, idempotent reuse, failure truth, and "
                        "one-hour orchestration under the processing budget."
                    ),
                    strength="local_runtime",
                    forbidden_content_scan="not_applicable",
                ),
                ReadinessEvidence(
                    id="feature-049-browser-runtime",
                    type="runtime",
                    source="specs/049-meeting-outcomes-mvp/evidence/browser-runtime-check.cjs",
                    captured_at=captured_at,
                    scope=(
                        "Browser runtime validation covers web, mobile, and desktop embedded outcome review "
                        "with playback coexistence, timestamp seek, speaker timeline, no overflow, and "
                        "matching stored outcome states."
                    ),
                    strength="local_runtime",
                    forbidden_content_scan="pass",
                ),
                ReadinessEvidence(
                    id="feature-049-privacy-deletion-rls",
                    type="command",
                    source=(
                        "uv run --extra dev pytest -q tests/contract/test_rls_tenant_isolation_contract.py "
                        "tests/contract/test_cabinet_no_secret_content_egress.py "
                        "tests/integration/test_meeting_outcomes_deletion.py "
                        "tests/integration/test_deletion_lifecycle_blocks_access.py "
                        "tests/integration/test_meeting_deletion_workflow.py "
                        "tests/integration/test_rls_meeting_content_policies.py "
                        "tests/contract/test_rls_table_inventory_contract.py"
                    ),
                    captured_at=captured_at,
                    scope=(
                        "Outcome content follows access denial, list egress, deletion lifecycle, "
                        "artifact accounting, RLS inventory, and metadata-only evidence boundaries."
                    ),
                    strength="local_runtime",
                    forbidden_content_scan="not_applicable",
                ),
                ReadinessEvidence(
                    id="feature-049-validation-log",
                    type="document",
                    source="specs/049-meeting-outcomes-mvp/evidence/validation-log.md",
                    captured_at=captured_at,
                    scope="Records 049 RED/GREEN validation evidence and remaining launch boundaries.",
                    strength="docs_only",
                    forbidden_content_scan="pass",
                ),
                ReadinessEvidence(
                    id="feature-049-github-issues",
                    type="github",
                    source="specs/049-meeting-outcomes-mvp/issues.md",
                    captured_at=captured_at,
                    scope="Maps 049 Spec Kit tasks to GitHub issues for tracked implementation and closeout.",
                    strength="docs_only",
                    forbidden_content_scan="pass",
                ),
                ReadinessEvidence(
                    id="current-product-status-049-outcomes",
                    type="document",
                    source="docs/current-product-status.md#next-product-slice",
                    captured_at=captured_at,
                    scope=(
                        "Current status records 049 stored outcomes as closing the notes/action output blocker "
                        "while keeping production rollout evidence separate."
                    ),
                    strength="docs_only",
                    forbidden_content_scan="pass",
                ),
                ReadinessEvidence(
                    id="changelog-049",
                    type="document",
                    source="CHANGELOG.md#unreleased",
                    captured_at=captured_at,
                    scope="Changelog records the 049 stored outcomes behavior and remaining rollout boundary.",
                    strength="docs_only",
                    forbidden_content_scan="pass",
                ),
            ]
        )
    if feature in {FEATURE_050_ID, FEATURE_051_ID, FEATURE_052_ID}:
        evidence.extend(
            [
                ReadinessEvidence(
                    id="feature-050-validation-log",
                    type="document",
                    source="specs/050-mvp-launch-proof/evidence/validation-log.md",
                    captured_at=captured_at,
                    scope=(
                        "Records 050 Spec Kit gates, RED/GREEN readiness checks, UI/runtime proof, "
                        "release evidence, and remaining launch boundaries."
                    ),
                    strength="docs_only",
                    forbidden_content_scan="pass",
                ),
                ReadinessEvidence(
                    id="feature-050-browser-runtime",
                    type="runtime",
                    source="specs/050-mvp-launch-proof/evidence/browser-runtime-check.cjs",
                    captured_at=captured_at,
                    scope=(
                        "Runtime verifier covers web, desktop-embedded, and mobile-width review with "
                        "active transcript tab, persistent playback, timestamp seek, speaker timeline, "
                        "stored outcomes, and overflow/console checks."
                    ),
                    strength="local_runtime",
                    forbidden_content_scan="pass",
                ),
                ReadinessEvidence(
                    id="feature-050-closeout-report",
                    type="document",
                    source="specs/050-mvp-launch-proof/evidence/mvp-closeout-report.md",
                    captured_at=captured_at,
                    scope="Metadata-only gate table for the final 050 MVP claim decision.",
                    strength="docs_only",
                    forbidden_content_scan="pass",
                ),
                ReadinessEvidence(
                    id="feature-050-github-issues",
                    type="github",
                    source="specs/050-mvp-launch-proof/issues.md",
                    captured_at=captured_at,
                    scope="Maps 050 Spec Kit tasks to GitHub issues for tracked launch-proof closeout.",
                    strength="docs_only",
                    forbidden_content_scan="pass",
                ),
                ReadinessEvidence(
                    id="feature-050-readiness-report-json",
                    type="document",
                    source="docs/evidence/050-mvp-launch-proof/readiness-report.json",
                    captured_at=captured_at,
                    scope="Structured 050 readiness report generated from the current evidence matrix.",
                    strength="docs_only",
                    forbidden_content_scan="pass",
                ),
                ReadinessEvidence(
                    id="feature-050-readiness-report-md",
                    type="document",
                    source="docs/evidence/050-mvp-launch-proof/readiness-report.md",
                    captured_at=captured_at,
                    scope="Reviewer-facing 050 readiness summary with the current bounded claim.",
                    strength="docs_only",
                    forbidden_content_scan="pass",
                ),
                ReadinessEvidence(
                    id="feature-050-launch-gap-register",
                    type="document",
                    source="docs/evidence/050-mvp-launch-proof/launch-gap-register.md",
                    captured_at=captured_at,
                    scope="050 launch gap register with the remaining P1 rollout proof boundary.",
                    strength="docs_only",
                    forbidden_content_scan="pass",
                ),
                ReadinessEvidence(
                    id="current-product-status-050-closeout",
                    type="document",
                    source="docs/current-product-status.md#next-product-slice",
                    captured_at=captured_at,
                    scope=(
                        "Current status records 049 as shipped product behavior and 050 as the active "
                        "MVP launch-proof boundary without inflating pilot or production claims."
                    ),
                    strength="docs_only",
                    forbidden_content_scan="pass",
                ),
                ReadinessEvidence(
                    id="changelog-050",
                    type="document",
                    source="CHANGELOG.md#unreleased",
                    captured_at=captured_at,
                    scope="Changelog records the 050 MVP proof/status-truth closeout.",
                    strength="docs_only",
                    forbidden_content_scan="pass",
                ),
            ]
        )
    if feature == FEATURE_051_ID:
        evidence.extend(
            [
                ReadinessEvidence(
                    id="feature-051-validation-log",
                    type="document",
                    source="specs/051-mvp-owner-journey-proof/evidence/validation-log.md",
                    captured_at=captured_at,
                    scope=(
                        "Records 051 Spec Kit gates, production/app proof attempts, "
                        "runtime validation, and final readiness boundary."
                    ),
                    strength="docs_only",
                    forbidden_content_scan="pass",
                ),
                ReadinessEvidence(
                    id="feature-051-installed-app-check",
                    type="document",
                    source="specs/051-mvp-owner-journey-proof/evidence/installed-app-check.md",
                    captured_at=captured_at,
                    scope="Metadata-only installed app identity, launch, and codesign check for the current MVP owner journey.",
                    strength="docs_only",
                    forbidden_content_scan="pass",
                    limitations=["This check proves installed app identity/runtime safety, not a fresh record-to-review journey."],
                ),
                ReadinessEvidence(
                    id="feature-051-owner-journey-probe",
                    type="endpoint",
                    source="specs/051-mvp-owner-journey-proof/evidence/production-owner-journey-probe.py",
                    captured_at=captured_at,
                    scope=(
                        "Metadata-only production probe for health, owner review state, transcript, "
                        "speaker timeline, playback, and outcome category counts."
                    ),
                    strength="blocked",
                    forbidden_content_scan="pass",
                    limitations=["Owner-review proof remains blocked until a redacted production candidate and session are provided."],
                ),
                ReadinessEvidence(
                    id="feature-051-browser-runtime",
                    type="runtime",
                    source="specs/051-mvp-owner-journey-proof/evidence/browser-runtime-check.cjs",
                    captured_at=captured_at,
                    scope=(
                        "Runtime verifier reuses the accepted 050 playback/outcome/speaker timeline checks "
                        "for web, mobile, and embedded review surfaces."
                    ),
                    strength="local_runtime",
                    forbidden_content_scan="pass",
                ),
                ReadinessEvidence(
                    id="feature-051-closeout-report",
                    type="document",
                    source="specs/051-mvp-owner-journey-proof/evidence/mvp-closeout-report.md",
                    captured_at=captured_at,
                    scope="Metadata-only gate table for the 051 MVP owner journey decision.",
                    strength="docs_only",
                    forbidden_content_scan="pass",
                ),
                ReadinessEvidence(
                    id="feature-051-timing-proof",
                    type="document",
                    source="specs/051-mvp-owner-journey-proof/evidence/timing-proof.md",
                    captured_at=captured_at,
                    scope="Metadata-only processing timing proof against the three-minute-per-hour target.",
                    strength="docs_only",
                    forbidden_content_scan="pass",
                    limitations=["Timing target remains unproven until a representative run is recorded."],
                ),
                ReadinessEvidence(
                    id="feature-051-github-issues",
                    type="github",
                    source="specs/051-mvp-owner-journey-proof/issues.md",
                    captured_at=captured_at,
                    scope="Maps 051 Spec Kit tasks to GitHub issues for tracked owner-journey proof.",
                    strength="docs_only",
                    forbidden_content_scan="pass",
                ),
                ReadinessEvidence(
                    id="feature-051-readiness-report-json",
                    type="document",
                    source="docs/evidence/051-mvp-owner-journey-proof/readiness-report.json",
                    captured_at=captured_at,
                    scope="Structured 051 readiness report generated from the current evidence matrix.",
                    strength="docs_only",
                    forbidden_content_scan="pass",
                ),
                ReadinessEvidence(
                    id="feature-051-readiness-report-md",
                    type="document",
                    source="docs/evidence/051-mvp-owner-journey-proof/readiness-report.md",
                    captured_at=captured_at,
                    scope="Reviewer-facing 051 readiness summary with the current bounded claim.",
                    strength="docs_only",
                    forbidden_content_scan="pass",
                ),
                ReadinessEvidence(
                    id="feature-051-launch-gap-register",
                    type="document",
                    source="docs/evidence/051-mvp-owner-journey-proof/launch-gap-register.md",
                    captured_at=captured_at,
                    scope="051 launch gap register with exact remaining P1 owner journey proof gates.",
                    strength="docs_only",
                    forbidden_content_scan="pass",
                ),
                ReadinessEvidence(
                    id="current-product-status-051",
                    type="document",
                    source="docs/current-product-status.md#next-product-slice",
                    captured_at=captured_at,
                    scope=(
                        "Current status records 051 as the active proof slice over fresh owner journey, "
                        "production outcomes, timing, and interface quality."
                    ),
                    strength="docs_only",
                    forbidden_content_scan="pass",
                ),
                ReadinessEvidence(
                    id="changelog-051",
                    type="document",
                    source="CHANGELOG.md#unreleased",
                    captured_at=captured_at,
                    scope="Changelog records the 051 MVP owner journey proof slice.",
                    strength="docs_only",
                    forbidden_content_scan="pass",
                ),
            ]
        )
    if feature == FEATURE_052_ID:
        evidence.extend(
            [
                ReadinessEvidence(
                    id="feature-052-validation-log",
                    type="document",
                    source="specs/052-mvp-live-ui-proof/evidence/validation-log.md",
                    captured_at=captured_at,
                    scope=(
                        "Records 052 Spec Kit gates, production/app proof attempts, "
                        "UI reference review, and final readiness boundary."
                    ),
                    strength="docs_only",
                    forbidden_content_scan="pass",
                ),
                ReadinessEvidence(
                    id="feature-052-installed-app-check",
                    type="document",
                    source="specs/052-mvp-live-ui-proof/evidence/installed-app-check.md",
                    captured_at=captured_at,
                    scope="Metadata-only installed app identity, launch, and code-sign check for the current MVP proof.",
                    strength="docs_only",
                    forbidden_content_scan="pass",
                    limitations=["This check proves installed app identity/runtime safety, not a fresh record-to-review journey."],
                ),
                ReadinessEvidence(
                    id="feature-052-owner-journey-probe",
                    type="endpoint",
                    source="specs/052-mvp-live-ui-proof/evidence/production-owner-journey-probe.py",
                    captured_at=captured_at,
                    scope=(
                        "Metadata-only production probe for health, owner review state, transcript, "
                        "speaker timeline, playback, and outcome category counts on a synthetic production-safe candidate."
                    ),
                    strength="production_smoke",
                    forbidden_content_scan="pass",
                    limitations=[
                        "Synthetic smoke proof does not replace a fresh installed-app owner journey on the current production release."
                    ],
                ),
                ReadinessEvidence(
                    id="feature-052-browser-runtime",
                    type="runtime",
                    source="specs/052-mvp-live-ui-proof/evidence/browser-runtime-check.cjs",
                    captured_at=captured_at,
                    scope=(
                        "Runtime verifier reuses the accepted playback/outcome/speaker timeline checks "
                        "for web, compact, and embedded review surfaces."
                    ),
                    strength="local_runtime",
                    forbidden_content_scan="pass",
                ),
                ReadinessEvidence(
                    id="feature-052-ui-reference-review",
                    type="reference_review",
                    source="specs/052-mvp-live-ui-proof/evidence/ui-reference-review.md",
                    captured_at=captured_at,
                    scope="Clean-room KRISP reference and 2brain web/macOS UI review notes.",
                    strength="docs_only",
                    forbidden_content_scan="pass",
                    limitations=["Reference review does not prove authenticated live owner detail access."],
                ),
                ReadinessEvidence(
                    id="feature-052-closeout-report",
                    type="document",
                    source="specs/052-mvp-live-ui-proof/evidence/mvp-closeout-report.md",
                    captured_at=captured_at,
                    scope="Metadata-only gate table for the 052 MVP live owner journey decision.",
                    strength="docs_only",
                    forbidden_content_scan="pass",
                ),
                ReadinessEvidence(
                    id="feature-052-timing-proof",
                    type="document",
                    source="specs/052-mvp-live-ui-proof/evidence/timing-proof.md",
                    captured_at=captured_at,
                    scope="Metadata-only processing timing proof against the three-minute-per-hour target.",
                    strength="docs_only",
                    forbidden_content_scan="pass",
                    limitations=[
                        "Synthetic production-safe hour timing passed; fresh installed-app owner journey timing remains a separate gate."
                    ],
                ),
                ReadinessEvidence(
                    id="feature-052-github-issues",
                    type="github",
                    source="specs/052-mvp-live-ui-proof/issues.md",
                    captured_at=captured_at,
                    scope="Maps 052 Spec Kit tasks to GitHub issues for tracked MVP proof.",
                    strength="docs_only",
                    forbidden_content_scan="pass",
                ),
                ReadinessEvidence(
                    id="feature-052-readiness-report-json",
                    type="document",
                    source="docs/evidence/052-mvp-live-ui-proof/readiness-report.json",
                    captured_at=captured_at,
                    scope="Structured 052 readiness report generated from the current evidence matrix.",
                    strength="docs_only",
                    forbidden_content_scan="pass",
                ),
                ReadinessEvidence(
                    id="feature-052-readiness-report-md",
                    type="document",
                    source="docs/evidence/052-mvp-live-ui-proof/readiness-report.md",
                    captured_at=captured_at,
                    scope="Reviewer-facing 052 readiness summary with the current bounded claim.",
                    strength="docs_only",
                    forbidden_content_scan="pass",
                ),
                ReadinessEvidence(
                    id="feature-052-launch-gap-register",
                    type="document",
                    source="docs/evidence/052-mvp-live-ui-proof/launch-gap-register.md",
                    captured_at=captured_at,
                    scope="052 launch gap register with exact remaining P1 MVP proof gates.",
                    strength="docs_only",
                    forbidden_content_scan="pass",
                ),
                ReadinessEvidence(
                    id="current-product-status-052",
                    type="document",
                    source="docs/current-product-status.md#next-product-slice",
                    captured_at=captured_at,
                    scope=(
                        "Current status records 052 as the proof slice for live owner journey, "
                        "production outcomes, production-safe timing, and interface quality."
                    ),
                    strength="docs_only",
                    forbidden_content_scan="pass",
                ),
                ReadinessEvidence(
                    id="changelog-052",
                    type="document",
                    source="CHANGELOG.md#unreleased",
                    captured_at=captured_at,
                    scope="Changelog records the 052 MVP live owner journey and UI proof slice.",
                    strength="docs_only",
                    forbidden_content_scan="pass",
                ),
            ]
        )
    return evidence


def build_default_launch_gaps(feature: str = "034-mvp-loop-readiness") -> list[LaunchGap]:
    is_036 = feature == "036-owner-review-live-polish"
    has_stored_outcomes = feature in {FEATURE_049_ID, FEATURE_050_ID, FEATURE_051_ID, FEATURE_052_ID}
    live_desktop_gap = (
        []
        if feature
        in {
            "035-mvp-loop-live-evidence",
            "036-owner-review-live-polish",
            FEATURE_049_ID,
            FEATURE_050_ID,
            FEATURE_051_ID,
            FEATURE_052_ID,
        }
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
    production_gaps = (
        [
            LaunchGap(
                id="fresh-owner-journey-evidence",
                severity="P1",
                affected_journey="fresh-owner-journey",
                current_evidence="051 proved release/deploy, browser runtime, and one production metadata baseline, but not a fresh installed-app journey.",
                missing_evidence="Fresh installed-app record, stop, upload, finalization, processing, and review proof on the current production release.",
                recommended_next_action="Run the installed app owner journey and record metadata-only gate states in the active closeout report.",
                owner_area="ops",
            ),
            LaunchGap(
                id="production-stored-outcomes-evidence",
                severity="P1",
                affected_journey="stored-outcomes-production",
                current_evidence=(
                    "Synthetic production-safe proof produced stored outcome counts; current installed-app production outcome proof remains required."
                    if feature == FEATURE_052_ID
                    else "049 stored outcomes are accepted locally; current production outcome proof remains required."
                ),
                missing_evidence=(
                    "Stored outcome category states and counts on a current installed-app production candidate."
                    if feature == FEATURE_052_ID
                    else "Stored outcome category states and counts on a current production candidate."
                ),
                recommended_next_action="Run the production owner journey probe and record outcome category states without private text.",
                owner_area="web",
            ),
            *(
                [
                    LaunchGap(
                        id="processing-time-target-evidence",
                        severity="P1",
                        affected_journey="processing-time-target",
                        current_evidence="051 recorded only short-candidate timing, which cannot prove the three-minute-per-hour target.",
                        missing_evidence="Representative one-hour or near-one-hour production timing evidence.",
                        recommended_next_action="Record queue, workflow, provider, and finalize-to-review timing for a representative run.",
                        owner_area="server",
                    )
                ]
                if feature == FEATURE_051_ID
                else []
            ),
        ]
        if feature in {FEATURE_051_ID, FEATURE_052_ID}
        else [
            LaunchGap(
                id="production-user-rollout-evidence",
                severity="P1",
                affected_journey="production-deployment-smoke",
                current_evidence="Production smoke proves infra_smoke_ready only.",
                missing_evidence="Internal pilot or user rollout validation with live app journey evidence.",
                recommended_next_action="Keep production claim capped until a pilot runbook or live loop validation passes.",
                owner_area="ops",
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
    notes_action_gap = (
        []
        if has_stored_outcomes
        else [
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
            )
        ]
    )
    return sort_launch_gaps(
        [
            *live_desktop_gap,
            *feature_035_gaps,
            *feature_036_gaps,
            *notes_action_gap,
            *production_gaps,
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
    is_049 = feature == FEATURE_049_ID
    is_050 = feature == FEATURE_050_ID
    is_051 = feature == FEATURE_051_ID
    is_052 = feature == FEATURE_052_ID
    is_051_or_later = is_051 or is_052
    is_050_or_later = is_050 or is_051_or_later
    has_stored_outcomes = is_049 or is_050_or_later
    owner_review_polished = is_036 or has_stored_outcomes
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
    if has_stored_outcomes:
        desktop_capture_evidence.extend(
            [
                "feature-035-live-evidence-pack",
                "feature-036-validation-log",
                "feature-036-installed-app-final-walkthrough",
                "feature-049-validation-log",
                *(["feature-050-validation-log"] if is_050_or_later else []),
                *(["feature-051-validation-log", "feature-051-installed-app-check"] if is_051 else []),
                *(["feature-052-validation-log", "feature-052-installed-app-check"] if is_052 else []),
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
    if has_stored_outcomes:
        meeting_list_evidence.extend(
            [
                "feature-036-owner-review-live",
                "feature-036-validation-log",
                "feature-049-validation-log",
                *(["feature-050-validation-log"] if is_050_or_later else []),
                *(["feature-051-validation-log", "feature-051-owner-journey-probe"] if is_051 else []),
                *(["feature-052-validation-log", "feature-052-owner-journey-probe"] if is_052 else []),
            ]
        )
        meeting_detail_evidence.extend(
            [
                "feature-036-owner-review-live",
                "feature-036-validation-log",
                "feature-048-real-playback-availability",
                "feature-049-browser-runtime",
                "feature-049-validation-log",
                *(["feature-050-browser-runtime", "feature-050-validation-log"] if is_050_or_later else []),
                *(["feature-051-browser-runtime", "feature-051-owner-journey-probe"] if is_051 else []),
                *(["feature-052-browser-runtime", "feature-052-owner-journey-probe"] if is_052 else []),
            ]
        )
        notes_evidence.extend(
            [
                "feature-049-stored-outcomes",
                "feature-049-browser-runtime",
                "feature-049-privacy-deletion-rls",
                "feature-049-validation-log",
                *(["feature-050-closeout-report"] if is_050_or_later else []),
                *(["feature-051-closeout-report", "feature-051-owner-journey-probe"] if is_051 else []),
                *(["feature-052-closeout-report", "feature-052-owner-journey-probe"] if is_052 else []),
            ]
        )
        governance_evidence.extend(["feature-036-owner-review-live", "feature-049-privacy-deletion-rls"])
        product_status_evidence = (
            [
                "feature-051-validation-log",
                "feature-051-owner-journey-probe",
                "feature-051-browser-runtime",
                "feature-051-closeout-report",
                "feature-051-timing-proof",
                "feature-051-github-issues",
                "feature-051-readiness-report-json",
                "feature-051-readiness-report-md",
                "feature-051-launch-gap-register",
                "current-product-status-051",
                "changelog-051",
            ]
            if is_051
            else [
                "feature-052-validation-log",
                "feature-052-owner-journey-probe",
                "feature-052-browser-runtime",
                "feature-052-ui-reference-review",
                "feature-052-closeout-report",
                "feature-052-timing-proof",
                "feature-052-github-issues",
                "feature-052-readiness-report-json",
                "feature-052-readiness-report-md",
                "feature-052-launch-gap-register",
                "current-product-status-052",
                "changelog-052",
            ]
            if is_052
            else [
                "feature-050-validation-log",
                "feature-050-github-issues",
                "feature-050-readiness-report-json",
                "feature-050-readiness-report-md",
                "feature-050-launch-gap-register",
                "feature-050-closeout-report",
                "current-product-status-050-closeout",
                "changelog-050",
            ]
            if is_050
            else [
                "feature-049-validation-log",
                "feature-049-github-issues",
                "current-product-status-049-outcomes",
                "changelog-049",
            ]
        )

    meeting_list_status = "degraded" if is_035 or is_052 else "ready"
    meeting_list_gaps = ["web-owner-live-auth-context"] if is_035 else (["fresh-owner-journey-evidence"] if is_052 else [])
    if is_052:
        meeting_list_notes = (
            "Production list route was visible in Chrome, but the same owner session redirected on detail navigation; "
            "keep live owner review proof open until auth context is stable."
        )
    elif owner_review_polished:
        meeting_list_notes = "Production Chrome owner session proves the list route with metadata-safe counts and state labels."
    elif is_035:
        meeting_list_notes = (
            "Production list/auth polish exists and fixture evidence is safe, but live owner "
            "list proof remains blocked until a commit-safe owner session is available."
        )
    else:
        meeting_list_notes = (
            "List route has fixture and local regression evidence with authorized access states; "
            "live private list evidence is not committed."
        )

    meeting_detail_status = "degraded" if is_035 or is_052 else "ready"
    meeting_detail_gaps = (
        ["web-owner-live-auth-context"]
        if is_035
        else (["fresh-owner-journey-evidence", "production-stored-outcomes-evidence"] if is_052 else [])
    )
    if is_052:
        meeting_detail_notes = (
            "Fixture-backed review has transcript, playback, timestamp seek, speaker lanes, "
            "and outcome rows, but live production detail redirected to login with missing auth context."
        )
    elif has_stored_outcomes:
        meeting_detail_notes = (
            "Ready owner review now has transcript, real review playback, timestamp seek, "
            "and stored outcome evidence in web and embedded routes."
        )
    elif is_036:
        meeting_detail_notes = (
            "Production Chrome owner session proves one detail route, transcript panel, "
            "notes/action truth states, and governance surface metadata-safely."
        )
    elif is_035:
        meeting_detail_notes = (
            "Ready/partial/processing/failed detail states are fixture-backed; live "
            "private detail and governance proof remains blocked by missing approved owner-session evidence."
        )
    else:
        meeting_detail_notes = (
            "Ready/partial/processing/failed detail states have local fixture evidence for transcript, "
            "playback, and provenance."
        )

    notes_status = "degraded" if is_052 else ("ready" if has_stored_outcomes else "blocked")
    notes_gaps = ["production-stored-outcomes-evidence"] if is_052 else ([] if has_stored_outcomes else ["notes-action-output"])
    if is_052:
        notes_notes = "Stored outcome UI is fixture-backed, but production currently has no stored outcome sets/items for a current owner candidate."
    elif has_stored_outcomes:
        notes_notes = "Stored meeting outcomes are available with category truth, transcript evidence, retry safety, and privacy/deletion boundaries."
    elif is_036:
        notes_notes = "The interface exposes structured notes/action truth states; launchable generated notes/action output remains unaccepted."
    else:
        notes_notes = "The interface shows truthful planned notes/assistant placeholders; launchable notes/action output remains missing."

    embedded_status = "degraded" if is_052 else ("ready" if owner_review_polished else "degraded")
    embedded_gaps = (
        ["fresh-owner-journey-evidence"]
        if is_052
        else ([] if owner_review_polished else (["desktop-product-surface-polish"] if is_035 else ["live-desktop-evidence"]))
    )
    if is_052:
        embedded_notes = (
            "Installed macOS shell truth is visible and fixture-backed embedded review passes, "
            "but live embedded owner review is blocked by expired or missing auth context."
        )
    elif has_stored_outcomes:
        embedded_notes = (
            "Installed desktop polish remains current, and the server-owned embedded route "
            "shows the same stored outcome truth as web review."
        )
    elif is_035 or owner_review_polished:
        embedded_notes = (
            "Installed desktop product polish and final /Applications capture-state "
            "walkthrough evidence are current; broad launch remains blocked by web, "
            "notes/action, and production rollout gaps."
        )
    else:
        embedded_notes = "Embedding has synthetic and local regression evidence; fresh metadata-safe live screenshots are still required."

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
                if not (is_035 or owner_review_polished)
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
            status=meeting_list_status,
            evidence_strength="local_runtime",
            evidence_ids=meeting_list_evidence,
            launch_gap_ids=meeting_list_gaps,
            claim_impact=["web_review_verified", "mvp_loop_ready"],
            notes=meeting_list_notes,
        ),
        MvpLoopStage(
            id="meeting-detail-transcript-playback",
            label="Meeting detail transcript, playback, and provenance",
            owner_surface="web_cabinet",
            status=meeting_detail_status,
            evidence_strength="local_runtime",
            evidence_ids=meeting_detail_evidence,
            launch_gap_ids=meeting_detail_gaps,
            claim_impact=["web_review_verified", "mvp_loop_ready"],
            notes=meeting_detail_notes,
        ),
        MvpLoopStage(
            id="notes-action-output",
            label="Notes and action output",
            owner_surface="web_cabinet",
            status=notes_status,
            evidence_strength="local_runtime",
            evidence_ids=notes_evidence,
            launch_gap_ids=notes_gaps,
            claim_impact=["mvp_loop_ready"],
            notes=notes_notes,
        ),
        MvpLoopStage(
            id="desktop-embedded-cabinet",
            label="Desktop embedded cabinet",
            owner_surface="desktop_embedded_web",
            status=embedded_status,
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
                    if owner_review_polished
                    else []
                ),
                *(["feature-049-browser-runtime"] if has_stored_outcomes else []),
                *(["feature-050-browser-runtime"] if is_050_or_later else []),
                *(["feature-051-browser-runtime"] if is_051 else []),
                *(["feature-052-browser-runtime"] if is_052 else []),
            ],
            launch_gap_ids=embedded_gaps,
            claim_impact=["desktop_loop_verified", "mvp_loop_ready"],
            notes=embedded_notes,
        ),
        MvpLoopStage(
            id="access-sharing-download-export",
            label="Access, sharing, download, and export",
            owner_surface="web_cabinet",
            status="ready",
            evidence_strength="local_runtime",
            evidence_ids=governance_evidence,
            claim_impact=["policy_lifecycle_verified", "mvp_loop_ready"],
            notes=(
                "Access/egress policy is accepted and locally regressed with bounded artifact actions; "
                "049 keeps outcome text out of list egress and denied states."
                if has_stored_outcomes
                else "Access/egress policy is accepted and locally regressed with bounded artifact actions."
            ),
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
                *(["feature-049-privacy-deletion-rls"] if has_stored_outcomes else []),
            ],
            claim_impact=["policy_lifecycle_verified", "mvp_loop_ready"],
            notes=(
                "Deletion reports, dependency limits, post-egress limits, outcome lifecycle marking, "
                "and local purge acknowledgements are locally regressed as metadata-only truth."
                if has_stored_outcomes
                else "Deletion reports, dependency limits, post-egress limits, and local purge acknowledgements are locally regressed as metadata-only truth."
            ),
        ),
        MvpLoopStage(
            id="production-deployment-smoke",
            label="Production deployment and smoke boundary",
            owner_surface="production_infra",
            status="degraded",
            evidence_strength="production_smoke",
            evidence_ids=["production-018-infra-smoke"],
            launch_gap_ids=(
                [
                    "fresh-owner-journey-evidence",
                    "production-stored-outcomes-evidence",
                ]
                if is_052
                else [
                    "fresh-owner-journey-evidence",
                    "processing-time-target-evidence",
                    "production-stored-outcomes-evidence",
                ]
                if is_051
                else ["production-user-rollout-evidence"]
            ),
            claim_impact=["infra_smoke_ready"],
            notes=(
                "The active proof slice keeps fresh owner journey and production outcomes open; production-safe hour timing is recorded separately."
                if is_052
                else "The active proof slice splits the old rollout blocker into fresh owner journey, production outcomes, and timing proof gates."
                if is_051
                else "Production evidence proves infra_smoke_ready, not pilot or user rollout readiness."
            ),
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
                if not (is_035 or owner_review_polished)
                else (
                    (
                        "The 052 readiness truth records exact P1 owner journey, timing, and UI proof gates before any pilot claim."
                        if is_052
                        else "The 051 readiness truth records exact P1 owner journey proof gates before any pilot claim."
                        if is_051
                        else "The 050 readiness truth records shipped 049 outcomes and the remaining production rollout proof boundary."
                        if is_050
                        else "The 049 readiness truth records stored outcomes as accepted while keeping production rollout evidence separate."
                    )
                    if has_stored_outcomes
                    else (
                        "The generated 036 readiness pack records the current bounded claim and remaining live-proof gaps."
                    )
                    if is_036
                    else "The generated 035 readiness pack records the current bounded claim and next product slice."
                )
            ),
        ),
    ]


def build_default_reference_comparisons(feature: str = "034-mvp-loop-readiness") -> list[ReferenceComparison]:
    is_035 = feature == "035-mvp-loop-live-evidence"
    is_036 = feature == "036-owner-review-live-polish"
    is_049 = feature == FEATURE_049_ID
    is_050 = feature == FEATURE_050_ID
    is_051 = feature == FEATURE_051_ID
    is_052 = feature == FEATURE_052_ID
    is_051_or_later = is_051 or is_052
    is_050_or_later = is_050 or is_051_or_later
    has_stored_outcomes = is_049 or is_050_or_later
    owner_review_polished = is_036 or has_stored_outcomes
    checks = [
        "No committed private Krisp screenshots.",
        "No copied Krisp visual expression, brand assets, colors, or icons.",
        "No exact Krisp product copy beyond short category labels.",
    ]
    if is_052:
        web_review_result = "needs_polish"
    elif has_stored_outcomes:
        web_review_result = "pass"
    elif is_035 or is_036:
        web_review_result = "needs_polish"
    else:
        web_review_result = "pass"
    return [
        ReferenceComparison(
            id="desktop-first-viewport",
            surface="desktop_home",
            allowed_lessons=["Meeting workspace first", "Native capture authority remains local"],
            implementation_alignment=(
                "033 establishes the desktop cabinet shell and 034 adds local regression evidence; live screenshots are still blocked."
                if not (is_035 or owner_review_polished)
                else (
                    "036 installed-app screenshots and final walkthrough prove native/WebView "
                    "visual parity, product-workspace polish, and idle/active/paused/resumed/stopped "
                    "local control states."
                    if owner_review_polished
                    else (
                        "035 proves the installed local capture loop, but the visible desktop "
                        "surface is still an operational local-mode workspace that needs the "
                        "accepted V8 meeting-workspace polish."
                    )
                )
            ),
            intentional_differences=["2brain keeps Record/Stop as native trust controls."],
            forbidden_similarity_checks=checks,
            result="pass" if owner_review_polished else "needs_polish",
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
                *(["feature-049-browser-runtime", "feature-036-clean-room-reference"] if has_stored_outcomes else []),
                *(["feature-050-browser-runtime"] if is_050_or_later else []),
                *(["feature-051-browser-runtime"] if is_051 else []),
                *(["feature-052-browser-runtime", "feature-052-ui-reference-review"] if is_052 else []),
            ],
        ),
        ReferenceComparison(
            id="web-list-workspace",
            surface="web_list",
            allowed_lessons=["Meeting list, filters, sort, upload slot, and future action slots are discoverable"],
            implementation_alignment=(
                "034 verifies the web list and desktop-embedded list with fixture-backed local tests."
                if not (is_035 or owner_review_polished)
                else (
                    (
                        (
                            "052 observed the production list route, but detail navigation lost owner auth context; "
                            "keep the live list/detail proof degraded until the owner session is stable."
                        )
                        if is_052
                        else "Stored outcome proof keeps the 036 owner-review truth and adds outcome review coverage "
                        "without committing private meeting content."
                    )
                    if has_stored_outcomes
                    else (
                        "036 improves browser auth/list polish and records the remaining "
                        "metadata-safe live owner list proof without committing private meeting content."
                    )
                    if is_036
                    else (
                        "035 keeps the web list fixture-backed and records the production "
                        "auth-context blocker before live owner screenshots can be committed."
                    )
                )
            ),
            intentional_differences=["2brain keeps capture creation out of embedded web content."],
            forbidden_similarity_checks=checks,
            result="needs_polish" if (is_035 or is_036 or is_052) else "pass",
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
                *(["feature-036-owner-review-live", "feature-049-browser-runtime"] if has_stored_outcomes else []),
                *(["feature-050-browser-runtime"] if is_050_or_later else []),
                *(["feature-051-browser-runtime"] if is_051 else []),
                *(["feature-052-browser-runtime", "feature-052-ui-reference-review"] if is_052 else []),
            ],
        ),
        ReferenceComparison(
            id="web-review-workspace",
            surface="web_detail",
            allowed_lessons=["Transcript/playback/provenance are discoverable in one review workspace"],
            implementation_alignment=(
                "016/017/018 provide the server-owned review/governance surfaces; 034 verifies placeholders and embedded boundaries."
                if not (is_035 or owner_review_polished)
                else (
                    (
                        (
                            "052 fixture runtime proves playback, speaker lanes, seek, and outcomes, "
                            "but live production owner detail remains blocked by missing auth context."
                        )
                        if is_052
                        else "049 adds stored outcome categories, transcript evidence, failure truth, "
                        "privacy/deletion boundaries, and web/embedded parity on top of the "
                        "server-owned review surface."
                    )
                    if has_stored_outcomes
                    else (
                        "016/017/018 provide the server-owned review/governance surfaces; "
                        "036 records structured notes/action truth and visual polish while "
                        "live owner detail/governance proof is metadata-safe; generated notes/actions remain blocked."
                    )
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
            result=web_review_result,
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
                *(
                    [
                        "feature-048-real-playback-availability",
                        "feature-049-stored-outcomes",
                        "feature-049-browser-runtime",
                        "feature-049-privacy-deletion-rls",
                    ]
                    if has_stored_outcomes
                    else []
                ),
                *(["feature-050-browser-runtime", "feature-050-closeout-report"] if is_050_or_later else []),
                *(["feature-051-browser-runtime", "feature-051-closeout-report"] if is_051 else []),
                *(
                    ["feature-052-browser-runtime", "feature-052-ui-reference-review", "feature-052-closeout-report"]
                    if is_052
                    else []
                ),
            ],
        ),
        ReferenceComparison(
            id="governance-actions",
            surface="governance",
            allowed_lessons=["Share, export/download, deletion, and lifecycle truth must be visible by policy"],
            implementation_alignment=(
                "017/018 cover policy-owned access, egress, retention, deletion, and purge truth."
                if not (is_035 or owner_review_polished)
                else (
                    (
                        "017/018 cover policy-owned access, egress, retention, deletion, and "
                        "purge truth; 049 adds stored outcome denial, deletion, and RLS coverage."
                    )
                    if has_stored_outcomes
                    else (
                        "017/018 cover policy-owned access, egress, retention, deletion, and "
                        "purge truth; 036 now records live owner governance panel states "
                        "without clicking destructive actions."
                    )
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
                *(["feature-049-privacy-deletion-rls"] if has_stored_outcomes else []),
                *(["feature-050-closeout-report"] if is_050_or_later else []),
                *(["feature-051-closeout-report"] if is_051 else []),
                *(["feature-052-closeout-report"] if is_052 else []),
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
