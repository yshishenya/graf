from __future__ import annotations

from datetime import UTC, datetime

from twobrain_rec_server.readiness.default_evidence import (
    build_default_evidence as build_default_evidence,
)
from twobrain_rec_server.readiness.evidence import (
    ForbiddenContentScan,
    LaunchGap,
    MvpLoopStage,
    ReferenceComparison,
)
from twobrain_rec_server.readiness.feature_ids import (
    FEATURE_049_ID,
    FEATURE_050_ID,
    FEATURE_051_ID,
    FEATURE_052_ID,
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
