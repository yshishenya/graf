# Tasks: Live Route Stability

**Input**: Design documents from `/specs/019-live-route-stability/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md
**Tests**: Required by plan and risk profile. Contract/unit/integration tasks come before implementation tasks in each phase.
**Organization**: Tasks are grouped by user story so each story can be implemented and validated independently.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel because it touches different files and does not depend on incomplete tasks
- **[Story]**: Maps to the user stories in [spec.md](./spec.md)
- Every task includes an exact file path

---

## Phase 1: Setup

**Purpose**: Add shared test/evidence scaffolding used by all `019` tasks.

- [ ] T001 [P] Create live route stability fixture builders in `apps/macos/Shared/Tests/LiveRouteStabilityFixtures.swift`
- [ ] T002 [P] Create sample validation evidence fixtures in `apps/macos/Shared/Tests/Fixtures/LiveRouteStabilityEvidenceFixtures.swift`
- [ ] T003 [P] Add `019` validation output directory documentation in `specs/019-live-route-stability/evidence/README.md`

---

## Phase 2: Foundational

**Purpose**: Define shared metadata-only models, contracts, redaction, and route evidence storage before any user story implementation.

**Critical**: No user story work should begin until these tasks are complete.

- [ ] T004 [P] Add contract tests for route evidence event families and required fields in `apps/macos/Shared/Tests/ContractTests/LiveRouteEvidenceContractTests.swift`
- [ ] T005 [P] Add contract tests for autorepair states, transitions, timing tiers, and non-recoverable reasons in `apps/macos/Shared/Tests/ContractTests/AutorepairStateMachineContractTests.swift`
- [ ] T006 [P] Add contract tests for validation run evidence results, duration gates, and target/device coverage in `apps/macos/Shared/Tests/ContractTests/ValidationRunEvidenceContractTests.swift`
- [ ] T007 [P] Add contract tests for recording timeline evidence fields and alignment bands in `apps/macos/Shared/Tests/ContractTests/RecordingTimelineEvidenceContractTests.swift`
- [ ] T008 Create live route evidence models from data-model.md in `apps/macos/Shared/Sources/Models/LiveRouteEvidenceModels.swift`
- [ ] T009 Create autorepair state machine models from contract in `apps/macos/Shared/Sources/Routing/AutorepairStateMachine.swift`
- [ ] T010 Create metadata-only route evidence event model and serializer in `apps/macos/Shared/Sources/Diagnostics/RouteEvidenceEvent.swift`
- [ ] T011 Create local route evidence writer with JSON Lines output in `apps/macos/RecApp/Sources/Diagnostics/RouteEvidenceStore.swift`
- [ ] T012 Extend diagnostic redaction to cover route evidence fields and forbidden content in `apps/macos/Shared/Sources/Diagnostics/DiagnosticRedactor.swift`
- [ ] T013 Add redaction regression tests for route evidence and validation evidence in `apps/macos/Shared/Tests/DiagnosticRedactionTests.swift`

**Checkpoint**: Shared evidence contracts compile and can be used by every story.

---

## Phase 3: User Story 1 - Keep A Live Meeting Audible And Speakable (Priority: P1) MVP

**Goal**: Preserve an active meeting route for the long-duration window when the meeting target still uses `2brain Rec Microphone` and `2brain Rec Speaker`.

**Independent Test**: A controlled meeting route remains active for the 30-minute development gate with no `Run Check`, no unexpected release, and continuous mic/incoming frame evidence.

### Tests for User Story 1

- [ ] T014 [P] [US1] Add client-activity freshness tests that distinguish active clients from audio energy in `apps/macos/Shared/Tests/LiveRouteClientActivityTests.swift`
- [ ] T015 [P] [US1] Add long-route preservation policy tests for natural silence and one-sided activity windows in `apps/macos/Shared/Tests/LivePassthroughPolicyTests.swift`
- [ ] T016 [P] [US1] Add route engine integration tests for 30-minute simulated active clients with zero unexpected releases in `apps/macos/Shared/Tests/LiveRouteStabilityTests.swift`

### Implementation for User Story 1

- [ ] T017 [US1] Implement per-side client activity snapshots and freshness windows in `apps/macos/Shared/Sources/Routing/LiveRouteClientActivity.swift`
- [ ] T018 [US1] Replace sole route-preservation truth based on aggregate virtual-device running state with client activity evidence in `apps/macos/RecApp/Sources/Capture/PassthroughRouteEngine.swift`
- [ ] T019 [US1] Emit route lifecycle, active, preserved, and frame-continuity events from the live route engine in `apps/macos/RecApp/Sources/Capture/PassthroughRouteEngine.swift`
- [ ] T020 [US1] Add 30-minute development gate validation logic for accepted targets in `apps/macos/Scripts/validate-live-route-readiness.sh`
- [ ] T021 [US1] Document US1 validation evidence requirements in `specs/019-live-route-stability/evidence/us1-live-route-preservation.md`

**Checkpoint**: US1 is independently testable as the MVP slice.

---

## Phase 4: User Story 2 - Repair External Disruptions Automatically (Priority: P1)

**Goal**: Restore supported external disruptions automatically without making `Run Check` the normal recovery path.

**Independent Test**: Supported induced disruptions recover within the required timing tier, require zero normal user actions, and report healthy only after fresh evidence.

### Tests for User Story 2

- [ ] T022 [P] [US2] Add autorepair transition tests for recoverable disruptions and fresh-evidence success in `apps/macos/Shared/Tests/LiveRouteAutorepairTests.swift`
- [ ] T023 [P] [US2] Add non-recoverable blocked-state tests for permissions, unsupported routes, missing devices, and meeting device changes in `apps/macos/Shared/Tests/LiveRouteBlockedStateTests.swift`
- [ ] T024 [P] [US2] Add macOS default route follow tests for built-in, wired, USB, Bluetooth, and AirPods-class outcomes in `apps/macos/Shared/Tests/LiveRouteDefaultRouteTests.swift`

### Implementation for User Story 2

- [ ] T025 [US2] Implement bounded autorepair orchestration in `apps/macos/RecApp/Sources/Capture/LiveRouteAutorepairCoordinator.swift`
- [ ] T026 [US2] Add Core Audio default-route observation handoff outside realtime callbacks in `apps/macos/RecApp/Sources/AudioHealth/AudioEnvironmentMonitor.swift`
- [ ] T027 [US2] Resolve accepted macOS system default input/output snapshots in `apps/macos/RecApp/Sources/AudioSetup/RouteVerificationService.swift`
- [ ] T028 [US2] Integrate autorepair recovery and blocked-state outcomes into `apps/macos/RecApp/Sources/Capture/PassthroughRouteEngine.swift`
- [ ] T029 [US2] Record `Run Check` and other user-action audit events as diagnostic fallback evidence in `apps/macos/RecApp/Sources/AudioSetup/RouteVerificationService.swift`
- [ ] T030 [US2] Add induced autorepair and manual `Run Check` diagnostic fallback scenario support to validation script in `apps/macos/Scripts/validate-live-route-readiness.sh`
- [ ] T031 [US2] Document US2 autorepair validation evidence in `specs/019-live-route-stability/evidence/us2-autorepair.md`

**Checkpoint**: US2 can be validated without pressing `Run Check` in accepted recovery cases.

---

## Phase 5: User Story 3 - Preserve Incoming Track Timeline During Recording (Priority: P1)

**Goal**: Keep local mic and incoming tracks aligned during stable recordings and report truthful degraded evidence when route continuity is lost.

**Independent Test**: A recording-active validation run produces `mic.wav` and `incoming.wav` with `durationDifferenceSeconds <= 3` for accepted runs, and precise route-interruption categories for degraded/failed runs.

### Tests for User Story 3

- [ ] T032 [P] [US3] Add recording timeline alignment band tests for accepted, degraded_warning, and failed thresholds in `apps/macos/Shared/Tests/RecordingTimelineEvidenceTests.swift`
- [ ] T033 [P] [US3] Add manifest correlation tests for route session id, autorepair attempt ids, and route interruption category in `apps/macos/Shared/Tests/LocalRecordingManifestTests.swift`
- [ ] T034 [P] [US3] Add recording-active autorepair safety tests for route-status taxonomy, indicator/stop preservation, and timeline gap truth in `apps/macos/Shared/Tests/RecordingRouteStabilityTests.swift`

### Implementation for User Story 3

- [ ] T035 [US3] Add recording timeline evidence model support in `apps/macos/Shared/Sources/Models/RecordingTimelineEvidence.swift`
- [ ] T036 [US3] Extend recording evidence capture with route gaps and autorepair correlation in `apps/macos/RecApp/Sources/Capture/RecordingEvidenceService.swift`
- [ ] T037 [US3] Extend manifest writing with alignment band and interruption category in `apps/macos/RecApp/Sources/Capture/LocalRecordingManifestService.swift`
- [ ] T038 [US3] Preserve route-status distinctions, visible recording indicator, and one-action stop during live route autorepair in `apps/macos/RecApp/Sources/Capture/CaptureSessionController.swift`
- [ ] T039 [US3] Extend artifact validation for `019` route timeline evidence in `apps/macos/Scripts/validate-recording-artifact-format.sh`
- [ ] T040 [US3] Document US3 recording timeline validation evidence in `specs/019-live-route-stability/evidence/us3-recording-timeline.md`

**Checkpoint**: US3 can be validated from the final local recording package and route evidence alone.

---

## Phase 6: User Story 4 - Prevent Self-Inflicted Route Drops (Priority: P1)

**Goal**: Ensure idle policy, timers, housekeeping, stale cached state, and false silence classification cannot stop a healthy active meeting route.

**Independent Test**: Simulated long-running idle timers and silence windows produce preserved/denied-release evidence instead of route release while client evidence remains active or ambiguous.

### Tests for User Story 4

- [ ] T041 [P] [US4] Add release-denied policy tests for active, ambiguous, and stale client evidence in `apps/macos/Shared/Tests/LiveRouteReleaseDecisionTests.swift`
- [ ] T042 [P] [US4] Add regression tests for the observed approximately 300-second release pattern in `apps/macos/Shared/Tests/LiveRouteIdleRegressionTests.swift`
- [ ] T043 [P] [US4] Add app restart and route-state truth tests for stale/false-ready states in `apps/macos/Shared/Tests/RouteInvalidationTests.swift`

### Implementation for User Story 4

- [ ] T044 [US4] Implement deny-by-default route release decisions in `apps/macos/Shared/Sources/Routing/LiveRouteReleaseDecision.swift`
- [ ] T045 [US4] Replace idle timeout release logic with evidence-gated preservation in `apps/macos/RecApp/Sources/Capture/PassthroughRouteEngine.swift`
- [ ] T046 [US4] Persist stale, preserved, released, blocked, and failed route truth for app restarts in `apps/macos/RecApp/Sources/Capture/PassthroughRouteEngine.swift`
- [ ] T047 [US4] Emit release decision evidence for keep-active, denied, and released-after-client-closed outcomes in `apps/macos/RecApp/Sources/Diagnostics/RouteEvidenceStore.swift`
- [ ] T048 [US4] Document US4 self-inflicted-drop regression evidence in `specs/019-live-route-stability/evidence/us4-self-inflicted-drop-prevention.md`

**Checkpoint**: US4 proves `019` fixed prevention, not just recovery after self-inflicted drops.

---

## Phase 7: User Story 5 - Produce Metadata-Only Evidence For Root Cause (Priority: P2)

**Goal**: Produce local metadata-only diagnostics and validation evidence that can explain route failures without raw audio, meeting content, secrets, or external egress.

**Independent Test**: Accepted validation evidence contains all required event families, target/device-class coverage, redaction-safe diagnostics, user-action audit facts, and not-tested combinations.

### Tests for User Story 5

- [ ] T049 [P] [US5] Add validation run evidence aggregation tests for target and device-class acceptance in `apps/macos/Shared/Tests/ValidationRunEvidenceTests.swift`
- [ ] T050 [P] [US5] Add diagnostic bundle tests for local-first route evidence and forbidden content redaction in `apps/macos/Shared/Tests/LiveRouteDiagnosticBundleTests.swift`
- [ ] T051 [P] [US5] Add acceptance matrix tests for Bluetooth/AirPods backlog and not-tested combinations in `apps/macos/Shared/Tests/LiveRouteAcceptanceMatrixTests.swift`

### Implementation for User Story 5

- [ ] T052 [US5] Implement validation run evidence aggregation in `apps/macos/Shared/Sources/Diagnostics/ValidationRunEvidence.swift`
- [ ] T053 [US5] Attach route evidence JSON to diagnostic bundles without raw content in `apps/macos/RecApp/Sources/Diagnostics/DiagnosticBundleService.swift`
- [ ] T054 [US5] Generate target and device-class acceptance summary in `apps/macos/Scripts/validate-live-route-readiness.sh`
- [ ] T055 [US5] Add release acceptance evidence template for Chrome, Opera, Zoom, Telemost, built-in, wired, USB, Bluetooth, and AirPods-class status in `specs/019-live-route-stability/evidence/acceptance-matrix.md`

**Checkpoint**: US5 gives QA and engineering enough metadata-only evidence to diagnose `019` without expanding privacy scope.

---

## Phase 8: Polish & Cross-Cutting

**Purpose**: Final validation, documentation, and scope guardrails across all stories.

- [ ] T056 [P] Update current product status with `019` planned validation scope in `docs/current-product-status.md`
- [ ] T057 [P] Add `019` quickstart command references and evidence paths in `specs/019-live-route-stability/quickstart.md`
- [ ] T058 Run Swift tests for macOS package and record results in `specs/019-live-route-stability/evidence/test-results.md`
- [ ] T059 Run foundation validation scripts and record results in `specs/019-live-route-stability/evidence/test-results.md`
- [ ] T060 Run 30-minute development gate evidence collection for Chrome, Opera, Zoom, Telemost, built-in, wired, and USB coverage and record accepted, blocked, failed, degraded, and not-tested results in `specs/019-live-route-stability/evidence/development-30-minute.md`
- [ ] T061 Run 75-minute manual release gate evidence for Chrome, Opera, Zoom, Telemost, built-in, wired, and USB coverage and record accepted, blocked, failed, degraded, and not-tested outcomes without counting blocked, failed, degraded, or not-tested outcomes as acceptance in `specs/019-live-route-stability/evidence/release-75-minute.md`
- [ ] T062 Run local-offline validation with backend, network, MediaScribe, Langfuse, and transfer services unavailable and record results in `specs/019-live-route-stability/evidence/local-offline.md`
- [ ] T063 Review all evidence for no speaker-to-mic leakage, backend ingest, upload, transcription, MediaScribe, Langfuse, or Bluetooth implementation scope creep in `specs/019-live-route-stability/evidence/scope-review.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 Setup**: No dependencies.
- **Phase 2 Foundational**: Depends on Phase 1 and blocks all user stories.
- **Phase 3 US1**: Depends on Phase 2 and is the MVP.
- **Phase 4 US2**: Depends on Phase 2; can start after shared evidence/state models exist, but integrates cleanly after US1 route preservation hooks.
- **Phase 5 US3**: Depends on Phase 2; recording manifest work benefits from US1 route session ids and US2 autorepair attempt ids.
- **Phase 6 US4**: Depends on Phase 2; should be completed before final acceptance because prevention is the primary product goal.
- **Phase 7 US5**: Depends on Phase 2 and aggregates evidence from US1-US4.
- **Phase 8 Polish**: Depends on selected story phases being complete.

### User Story Dependencies

- **US1 (P1)**: MVP, no dependency on other user stories after foundation.
- **US2 (P1)**: Depends on foundation; integrates with US1 route lifecycle evidence for clean recovery.
- **US3 (P1)**: Depends on foundation; uses US1 route session ids and US2 autorepair ids for richer correlation.
- **US4 (P1)**: Depends on foundation; should be validated before claiming US1/US2 acceptance.
- **US5 (P2)**: Depends on foundation plus whichever P1 stories are included in the acceptance run.

### Within Each User Story

- Write contract/unit/integration tests before implementation tasks.
- Implement shared models before services/coordinators that consume them.
- Integrate route engine behavior before validation scripts that depend on runtime evidence.
- Complete story checkpoint validation before moving to the next story for sequential delivery.

---

## Parallel Opportunities

- T001-T003 can run in parallel.
- T004-T007 can run in parallel before T008-T013.
- In US1, T014-T016 can run in parallel before T017-T021.
- In US2, T022-T024 can run in parallel before T025-T031.
- In US3, T032-T034 can run in parallel before T035-T040.
- In US4, T041-T043 can run in parallel before T044-T048.
- In US5, T049-T051 can run in parallel before T052-T055.
- T056 and T057 can run in parallel after desired story scope is complete.

## Parallel Example: User Story 2

```text
Task: "T022 [P] [US2] Add autorepair transition tests for recoverable disruptions and fresh-evidence success in apps/macos/Shared/Tests/LiveRouteAutorepairTests.swift"
Task: "T023 [P] [US2] Add non-recoverable blocked-state tests for permissions, unsupported routes, missing devices, and meeting device changes in apps/macos/Shared/Tests/LiveRouteBlockedStateTests.swift"
Task: "T024 [P] [US2] Add macOS default route follow tests for built-in, wired, USB, Bluetooth, and AirPods-class outcomes in apps/macos/Shared/Tests/LiveRouteDefaultRouteTests.swift"
```

## Parallel Example: User Story 5

```text
Task: "T049 [P] [US5] Add validation run evidence aggregation tests for target and device-class acceptance in apps/macos/Shared/Tests/ValidationRunEvidenceTests.swift"
Task: "T050 [P] [US5] Add diagnostic bundle tests for local-first route evidence and forbidden content redaction in apps/macos/Shared/Tests/LiveRouteDiagnosticBundleTests.swift"
Task: "T051 [P] [US5] Add acceptance matrix tests for Bluetooth/AirPods backlog and not-tested combinations in apps/macos/Shared/Tests/LiveRouteAcceptanceMatrixTests.swift"
```

---

## Implementation Strategy

### MVP First: US1 Only

1. Complete Phase 1 setup.
2. Complete Phase 2 foundational models, contracts, and redaction.
3. Complete Phase 3 US1 route preservation.
4. Stop and validate US1 independently with the 30-minute development gate.

### Incremental Delivery

1. Add US1 to preserve active routes.
2. Add US2 to autorepair supported external disruptions.
3. Add US3 to connect live route stability to local recording truth.
4. Add US4 to prove prevention against self-inflicted drops before final acceptance.
5. Add US5 to produce release-ready metadata-only evidence.

### Scope Guardrails

- Do not implement `020` speaker-to-mic leakage or echo policy in `019`.
- Do not add backend ingest, upload queue, MediaScribe, Langfuse, analytics, dashboard, sharing, retention, deletion, or external egress work.
- Do not add Bluetooth/AirPods acceptance; record those routes as backlog/not accepted for `019`.
- Do not add a 2brain Rec physical-device picker; follow macOS system default input/output only for accepted device classes.
