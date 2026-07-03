from __future__ import annotations

from twobrain_rec_server.readiness.evidence import ReadinessEvidence
from twobrain_rec_server.readiness.feature_ids import (
    FEATURE_049_ID,
    FEATURE_050_ID,
    FEATURE_051_ID,
    FEATURE_052_ID,
)


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

