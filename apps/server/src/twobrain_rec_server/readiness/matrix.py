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


def build_default_evidence(captured_at: str, deployed_commit: str) -> list[ReadinessEvidence]:
    return [
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


def build_default_launch_gaps() -> list[LaunchGap]:
    return sort_launch_gaps(
        [
            LaunchGap(
                id="live-desktop-evidence",
                severity="P1",
                affected_journey="desktop-embedded-cabinet",
                current_evidence="Feature 033 synthetic evidence plus 034 local macOS regression evidence and blocker notes.",
                missing_evidence="Fresh metadata-safe live desktop screenshots or explicit product-owner acceptance of the blocker.",
                recommended_next_action="Capture desktop first-surface and embedded detail screenshots without private content.",
                owner_area="desktop",
            ),
            LaunchGap(
                id="notes-action-output",
                severity="P1",
                affected_journey="notes-action-output",
                current_evidence="Meeting detail shows truthful planned notes/assistant placeholders.",
                missing_evidence="Notes/action output availability or truthful blocked state in review surfaces.",
                recommended_next_action="Decide whether the next slice is assistant notes/actions or explicit MVP deferral.",
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


def build_default_stages() -> list[MvpLoopStage]:
    return [
        MvpLoopStage(
            id="local-recording-visible-stop",
            label="Local recording and visible stop",
            owner_surface="macos_native",
            status="ready",
            evidence_strength="local_runtime",
            evidence_ids=[
                "feature-025-system-audio",
                "feature-022-meeting-mute-truth",
                "desktop-shell-regression-tests",
            ],
            claim_impact=["desktop_loop_verified", "mvp_loop_ready"],
            notes=(
                "System-audio capture, visible stop, product-owned Pause/Resume "
                "privacy truth, and installed /Applications runtime evidence are accepted."
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
            status="ready",
            evidence_strength="local_runtime",
            evidence_ids=[
                "feature-016-web-review",
                "feature-017-access-egress",
                "web-cabinet-regression-tests",
                "web-meeting-list-blocker-note",
            ],
            claim_impact=["web_review_verified", "mvp_loop_ready"],
            notes="List route has fixture and local regression evidence with authorized access states; live private list evidence is not committed.",
        ),
        MvpLoopStage(
            id="meeting-detail-transcript-playback",
            label="Meeting detail transcript, playback, and provenance",
            owner_surface="web_cabinet",
            status="ready",
            evidence_strength="local_runtime",
            evidence_ids=[
                "feature-016-web-review",
                "web-cabinet-regression-tests",
                "web-meeting-detail-blocker-note",
            ],
            claim_impact=["web_review_verified", "mvp_loop_ready"],
            notes="Ready/partial/processing/failed detail states have local fixture evidence for transcript, playback, and provenance.",
        ),
        MvpLoopStage(
            id="notes-action-output",
            label="Notes and action output",
            owner_surface="web_cabinet",
            status="blocked",
            evidence_strength="local_runtime",
            evidence_ids=["web-cabinet-regression-tests", "web-meeting-detail-blocker-note"],
            launch_gap_ids=["notes-action-output"],
            claim_impact=["mvp_loop_ready"],
            notes="The interface shows truthful planned notes/assistant placeholders; launchable notes/action output remains missing.",
        ),
        MvpLoopStage(
            id="desktop-embedded-cabinet",
            label="Desktop embedded cabinet",
            owner_surface="desktop_embedded_web",
            status="degraded",
            evidence_strength="local_runtime",
            evidence_ids=[
                "feature-033-desktop-embedding",
                "desktop-shell-regression-tests",
                "desktop-first-surface-blocker-note",
                "desktop-embedded-detail-blocker-note",
            ],
            launch_gap_ids=["live-desktop-evidence"],
            claim_impact=["desktop_loop_verified", "mvp_loop_ready"],
            notes="Embedding has synthetic and local regression evidence; fresh metadata-safe live screenshots are still required.",
        ),
        MvpLoopStage(
            id="access-sharing-download-export",
            label="Access, sharing, download, and export",
            owner_surface="web_cabinet",
            status="ready",
            evidence_strength="local_runtime",
            evidence_ids=[
                "feature-017-access-egress",
                "policy-lifecycle-regression-tests",
                "policy-lifecycle-evidence-note",
            ],
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
            evidence_ids=["current-product-status-034-next-slice"],
            claim_impact=["partial_readiness"],
            notes="The status document records the 034 bounded outcome and next evidence-based product slice.",
        ),
    ]


def build_default_reference_comparisons() -> list[ReferenceComparison]:
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
            implementation_alignment="033 establishes the desktop cabinet shell and 034 adds local regression evidence; live screenshots are still blocked.",
            intentional_differences=["2brain keeps Record/Stop as native trust controls."],
            forbidden_similarity_checks=checks,
            result="needs_polish",
            evidence_ids=[
                "feature-033-desktop-embedding",
                "desktop-shell-regression-tests",
                "desktop-first-surface-blocker-note",
                "reference-clean-room-contract",
                "reference-comparison-note",
            ],
        ),
        ReferenceComparison(
            id="web-list-workspace",
            surface="web_list",
            allowed_lessons=["Meeting list, filters, sort, upload slot, and future action slots are discoverable"],
            implementation_alignment="034 verifies the web list and desktop-embedded list with fixture-backed local tests.",
            intentional_differences=["2brain keeps capture creation out of embedded web content."],
            forbidden_similarity_checks=checks,
            result="pass",
            evidence_ids=["web-cabinet-regression-tests", "web-meeting-list-blocker-note", "reference-comparison-note"],
        ),
        ReferenceComparison(
            id="web-review-workspace",
            surface="web_detail",
            allowed_lessons=["Transcript/playback/provenance are discoverable in one review workspace"],
            implementation_alignment="016/017/018 provide the server-owned review/governance surfaces; 034 verifies placeholders and embedded boundaries.",
            intentional_differences=["2brain uses its own design language and truthful placeholder policy."],
            forbidden_similarity_checks=checks,
            result="pass",
            evidence_ids=[
                "feature-016-web-review",
                "feature-017-access-egress",
                "web-cabinet-regression-tests",
                "web-meeting-detail-blocker-note",
                "reference-comparison-note",
            ],
        ),
        ReferenceComparison(
            id="governance-actions",
            surface="governance",
            allowed_lessons=["Share, export/download, deletion, and lifecycle truth must be visible by policy"],
            implementation_alignment="017/018 cover policy-owned access, egress, retention, deletion, and purge truth.",
            intentional_differences=["External public links remain out of scope."],
            forbidden_similarity_checks=checks,
            result="pass",
            evidence_ids=[
                "feature-017-access-egress",
                "feature-018-retention-deletion",
                "policy-lifecycle-regression-tests",
                "policy-lifecycle-evidence-note",
            ],
        ),
    ]


def passed_forbidden_content_scan() -> ForbiddenContentScan:
    return ForbiddenContentScan(
        status="pass",
        commands=[
            "rg -n -i real private-value patterns specs/034-mvp-loop-readiness docs/evidence/034-mvp-loop-readiness docs/current-product-status.md CHANGELOG.md",
            "find docs/evidence/034-mvp-loop-readiness/screenshots -type f -name '*.png' -o -name '*.jpg' -o -name '*.jpeg' -o -name '*.webp'",
            "rg -n -i evidence payload-id patterns docs/evidence/034-mvp-loop-readiness",
        ],
        matches=[],
    )
