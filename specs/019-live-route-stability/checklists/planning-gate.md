# Planning Gate Checklist: Live Route Stability

**Purpose**: Validate post-plan requirement quality and planning readiness before generating implementation tasks.
**Created**: 2026-06-04
**Feature**: [spec.md](../spec.md)

**Note**: This checklist tests the English requirements and planning artifacts, not the implementation.

## Driver Route Stability Requirements

- [ ] CHK001 Are active-route preservation requirements complete for microphone-only, speaker-only, both-sides-active, and naturally silent meeting intervals? [Completeness, Spec §US1, Spec §FR-005, Spec §FR-006, Plan §Phase 1]
- [ ] CHK002 Is idle release defined with enough evidence requirements to prevent release when the meeting target still uses either 2brain Rec virtual device? [Clarity, Spec §FR-022, Spec §FR-023, Research §Idle Release]
- [ ] CHK003 Are requirements consistent between automatic route preservation and bounded resource release after fresh proof that the meeting client closed the virtual route? [Consistency, Spec §FR-022, Data Model §RouteReleaseDecision]
- [ ] CHK004 Are route states and transitions specified clearly enough for tasks to distinguish `active`, `preserved`, `released`, `stale`, `recovering`, `blocked`, and `failed`? [Clarity, Data Model §LiveRouteState, Contract §Autorepair]
- [ ] CHK005 Are macOS system default input/output requirements complete enough to prevent 2brain Rec from independently choosing a physical device? [Completeness, Spec §FR-026, Spec §FR-027, Data Model §MacOSDefaultRouteSnapshot]

## Autorepair Requirements

- [ ] CHK006 Are recoverable and non-recoverable route conditions completely enumerated and mutually exclusive enough for task decomposition? [Completeness, Spec §Autorepair Product Rule, Contract §Autorepair]
- [ ] CHK007 Are `<= 2 seconds` and `<= 10 seconds` recovery targets defined with clear start/stop measurement points? [Measurability, Spec §FR-046, Spec §FR-047, Contract §Autorepair]
- [ ] CHK008 Are requirements clear that autorepair can report healthy only after fresh route, client activity, and frame-continuity evidence? [Clarity, Spec §FR-028, Contract §Autorepair]
- [ ] CHK009 Are retry budget and retry-exhaustion requirements sufficient to prevent infinite repair churn? [Coverage, Spec §FR-029, Contract §Autorepair]
- [ ] CHK010 Are successful-autorepair UX requirements consistent with passive status/history evidence and no required modal or user action? [Consistency, Spec §FR-044, Spec §SC-022]
- [ ] CHK011 Are manual `Run Check` requirements clear enough to keep it as diagnostic fallback rather than clean acceptance recovery? [Clarity, Spec §US2, Spec §SC-007, Quickstart §Autorepair Scenarios]

## Evidence And Diagnostics Requirements

- [ ] CHK012 Are all required route evidence event families defined consistently across spec, data model, contracts, and quickstart? [Consistency, Spec §FR-035, Data Model §RouteEvidenceEvent, Contract §Route Evidence Events]
- [ ] CHK013 Are event payload requirements complete enough to reconstruct route start, release decision, external disruption, autorepair attempt, final outcome, and user action audit? [Completeness, Spec §Logging And Evidence Contract, Contract §Route Evidence Events]
- [ ] CHK014 Are metadata-only requirements precise enough to exclude raw audio, transcript text, meeting content, credentials, tokens, signed URLs, passwords, API keys, and live credential paths? [Security, Spec §FR-019, Contract §Route Evidence Events]
- [ ] CHK015 Are safe device identity requirements defined clearly enough to allow debug reproduction without exposing private paths or secrets? [Privacy, Spec §Logging And Evidence Contract, Data Model §MacOSDefaultRouteSnapshot]
- [ ] CHK016 Are correlation requirements complete for linking route session, autorepair attempts, user-action audit, and final recording manifest evidence? [Traceability, Spec §FR-036, Data Model §LiveRouteSession, Contract §Recording Timeline Evidence]

## Recording Timeline Requirements

- [ ] CHK017 Are timeline alignment bands specified consistently across spec, data model, recording contract, and quickstart? [Consistency, Spec §FR-033, Data Model §RecordingTimelineIntegrityEvidence, Contract §Recording Timeline Evidence]
- [ ] CHK018 Are route-interruption categories complete enough to distinguish incoming route stop, microphone route stop, both-route stop, default-route change, browser recreation, and unknown route gap? [Completeness, Contract §Recording Timeline Evidence]
- [ ] CHK019 Are requirements clear that degraded/warning timeline evidence cannot count as clean acceptance? [Clarity, Spec §SC-015, Quickstart §Recording Timeline Validation]
- [ ] CHK020 Are manifest truth requirements complete enough to improve over generic `timeline_misaligned` without adding meeting content storage? [Completeness, Research §Recording Timeline Evidence, Contract §Recording Timeline Evidence]
- [ ] CHK021 Are recording-active autorepair requirements specified so repair cannot hide route gaps or corrupt artifact alignment? [Coverage, Spec §FR-030, Contract §Recording Timeline Evidence]

## Validation Matrix Requirements

- [ ] CHK022 Are the Chrome, Opera, Zoom, and Telemost target acceptance requirements complete for both 30-minute and 75-minute gates? [Completeness, Spec §SC-012a, Quickstart §Development Gate, Quickstart §Release Gate]
- [ ] CHK023 Are built-in, wired, and USB device-class acceptance requirements complete without implying a full `4 x 3` cross-product? [Clarity, Spec §FR-051, Research §Validation Coverage]
- [ ] CHK024 Are not-tested target/device-class combinations required to be listed clearly enough to prevent release-ready overclaiming? [Acceptance Criteria, Spec §SC-021, Contract §Validation Run Evidence]
- [ ] CHK025 Are Bluetooth/AirPods-class route requirements consistently deferred as backlog/not accepted rather than silently grouped with unknown devices? [Consistency, Spec §FR-042, Spec §FR-043, Research §Bluetooth/AirPods]
- [ ] CHK026 Are validation result labels (`accepted`, `degraded`, `failed`, `blocked`, `not_tested`) defined clearly enough for future release evidence? [Clarity, Data Model §ValidationRunEvidence, Contract §Validation Run Evidence]
- [ ] CHK027 Are user-action audit requirements complete enough to prove no `Run Check`, meeting device reselect, app relaunch, or settings reopen occurred in accepted runs? [Completeness, Spec §SC-007b, Contract §Validation Run Evidence]

## Realtime And Platform Requirements

- [ ] CHK028 Are realtime-safety requirements complete for Core Audio/HAL callbacks, property listeners, route repair dispatch, and evidence logging boundaries? [Realtime Safety, Spec §FR-018, Research §Realtime Audio Paths]
- [ ] CHK029 Are Core Audio property-listener requirements documented with enough constraints to avoid doing repair or logging work in realtime/IO callback contexts? [Clarity, Research §macOS System Default Routes]
- [ ] CHK030 Are Apple Silicon/macOS-native platform constraints reflected in all plan artifacts that affect virtual-device lifecycle and route monitoring? [Platform, Plan §Technical Context, Constitution §Product And Platform Constraints]
- [ ] CHK031 Are fallback polling requirements specified as a safety net without making polling the only route-change detection mechanism? [Coverage, Research §macOS System Default Routes]

## Scope And Constitution Requirements

- [ ] CHK032 Are out-of-scope boundaries complete for speaker-to-mic leakage, meeting mute truth, assisted auto-recording, backend ingest, upload, MediaScribe, Langfuse, dashboard, retention, and deletion? [Scope, Spec §Scope Boundary, Plan §Constraints]
- [ ] CHK033 Are constitution checks in the plan traceable to concrete requirements and contracts rather than broad assertions? [Traceability, Plan §Constitution Check, Plan §Post Design]
- [ ] CHK034 Are privacy and data-boundary requirements consistent between local-first diagnostics and future export redaction requirements? [Consistency, Spec §Logging And Evidence Contract, Contract §Route Evidence Events]
- [ ] CHK035 Are deletion/lifecycle implications clear enough for metadata evidence without introducing new content retention promises? [Lifecycle, Plan §Constitution Check, Constitution §IV]

## Task Readiness

- [ ] CHK036 Are plan artifacts sufficient to generate tasks by independently testable user story without bundling unrelated implementation decisions? [Task Readiness, Spec §User Scenarios, Plan §Implementation Approach]
- [ ] CHK037 Are contract-test requirements clear enough to place tests before implementation in tasks.md? [Task Readiness, Plan §Implementation Approach, Contracts]
- [ ] CHK038 Are validation script and quickstart requirements specific enough for future tasks to name exact files and expected evidence outputs? [Task Readiness, Quickstart]
- [ ] CHK039 Are research decisions explicit enough that `$speckit-tasks` does not need to reopen architecture choices before task generation? [Planning Readiness, Research]
- [ ] CHK040 Are remaining risks, if any, better suited to tasks/analyze rather than additional clarification? [Ambiguity, Spec §Clarifications, Plan §Phase 1]
