# Tasks: Low-Resource Reliable macOS Audio

**Input**: Design documents from `specs/006-low-resource-audio/`

**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/`, `quickstart.md`

**Tests**: Tests and validation tasks are required because this feature changes high-risk macOS audio routing, HAL callback behavior, no-hang behavior, diagnostics, and fallback gates.

**Organization**: Tasks are grouped by independently testable user story and ordered so the P1 route, no-hang, recovery, and observability work can be validated before default promotion.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel with other `[P]` tasks in the same phase because it touches different files and has no dependency on incomplete tasks
- **[Story]**: User story label from `spec.md`
- Every task names concrete repository paths

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Establish local gates and shared fixtures before changing route behavior.

- [X] T001 Capture the current 005 app-launch passthrough baseline evidence in `specs/006-low-resource-audio/baseline/005-app-launch-passthrough.md`
- [X] T002 [P] Add low-resource validation fixture schema in `tests/macos/contract/low-resource-validation-evidence.json`
- [X] T003 [P] Add route lifecycle fixture schema in `tests/macos/contract/low-resource-route-truth.json`
- [X] T004 [P] Add startup timeout fixture schema in `tests/macos/contract/low-resource-startup-attempt.json`
- [X] T005 Add low-resource validation command entrypoints to `apps/macos/Scripts/validate-low-resource-audio.sh`
- [X] T006 Document the low-resource validation and clean-room review matrix in `qa/macos/low-resource-audio-gate.md`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Create shared models, contracts, and safety gates that all user stories depend on.

**Critical**: No user story implementation starts until this phase is complete.

- [X] T007 Add `AudioResourceState`, `RouteTruthSnapshot`, `StartupAttemptEvidence`, and `LowResourceValidationRun` models in `apps/macos/Shared/Sources/Models/LowResourceAudioModels.swift`
- [X] T008 Add unit tests for low-resource state transitions and validation serialization in `apps/macos/Shared/Tests/LowResourceAudioModelsTests.swift`
- [X] T009 Extend diagnostic redaction coverage for low-resource route evidence in `apps/macos/Shared/Tests/DiagnosticRedactionTests.swift`
- [X] T010 Add contract validation cases for low-resource evidence fixtures in `apps/macos/Shared/Tests/ContractTests/LowResourceContractTests.swift`
- [X] T011 Add low-resource validation plan registration in `apps/macos/Shared/TestPlans/ContractValidationPlan.swift`
- [X] T012 Add shared route truth helpers in `apps/macos/Shared/Sources/Routing/LowResourceRouteTruth.swift`
- [X] T013 Add static realtime-safety forbidden-operation coverage for low-resource callback paths in `tests/macos/static/audio-rt-safety-check.sh`
- [X] T014 Add no-secret/no-content low-resource evidence scan to `apps/macos/Scripts/validate-low-resource-audio.sh`
- [X] T015 Update package target membership for new shared test/model files in `apps/macos/Package.swift`

**Checkpoint**: Shared models, contract tests, redaction scan, and realtime-safety scan are ready.

---

## Phase 3: User Story 1 - Keep Audio Reliable With A Lightweight Virtual Layer (Priority: P1)

**Goal**: Keep public virtual devices visible and fail-closed while heavy physical passthrough starts only for explicit client IO and never because recording is active.

**Independent Test**: With virtual devices selected and no active client stream, route state is `idle_safe`; opening browser/meeting audio activates passthrough without `Run Check`; silent-but-open streams remain active; no recording/transcription/upload starts.

### Tests for User Story 1

- [X] T016 [P] [US1] Add contract tests for `idle_safe`, `starting`, `ready`, and `active` route transitions in `apps/macos/Shared/Tests/LowResourceRouteLifecycleTests.swift`
- [X] T017 [P] [US1] Add silent-but-open client activity tests in `apps/macos/Shared/Tests/LowResourceClientActivityTests.swift`
- [X] T018 [P] [US1] Add automatic activation smoke fixture in `tests/macos/route-synthetic/low-resource-auto-activation-check.swift`
- [X] T019 [P] [US1] Add no-Run-Check regression validation to `apps/macos/Scripts/validate-low-resource-audio.sh`

### Implementation for User Story 1

- [X] T020 [US1] Add explicit client IO activity aggregation in `apps/macos/AudioDriver/Sources/Device/VirtualDeviceRegistry.cpp`
- [X] T021 [US1] Expose low-resource running/client counters in `apps/macos/AudioDriver/Sources/Device/VirtualDeviceRegistry.hpp`
- [X] T022 [US1] Refactor microphone route idle/active decisions to use explicit client IO state in `apps/macos/AudioDriver/Sources/Routing/MicrophoneRoute.cpp`
- [X] T023 [US1] Refactor speaker route idle/active decisions to use explicit client IO state in `apps/macos/AudioDriver/Sources/Routing/SpeakerRoute.cpp`
- [X] T024 [US1] Add low-resource route lifecycle orchestration in `apps/macos/RecApp/Sources/Capture/PassthroughRouteEngine.swift`
- [X] T025 [US1] Add route truth reporting for idle, starting, ready, and active states in `apps/macos/RecApp/Sources/Diagnostics/DiagnosticBundleService.swift`
- [X] T026 [US1] Update app status text for non-recording low-resource routing in `apps/macos/RecApp/Sources/Shared/AdaptiveStatusText.swift`
- [X] T027 [US1] Wire low-resource route state into the app shell in `apps/macos/RecApp/App/TwoBrainRecApp.swift`

**Checkpoint**: US1 passes route lifecycle, silent stream, automatic activation, diagnostics, and no-recording validation independently.

---

## Phase 4: User Story 2 - Prevent Core Audio And UI Hangs (Priority: P1)

**Goal**: Bound physical Core Audio startup, enumeration, and AudioUnit setup so UI, validation, browser, meeting, and system audio surfaces do not hang.

**Independent Test**: Restart Core Audio and open 2brain Rec plus macOS Sound settings, Chrome, Opera, Zoom, and Telemost audio surfaces; every startup attempt resolves within 3000 ms and surfaces open within 5 seconds or record blocked evidence.

### Tests for User Story 2

- [X] T028 [P] [US2] Add startup timeout unit tests in `apps/macos/Shared/Tests/LowResourceStartupAttemptTests.swift`
- [X] T029 [P] [US2] Add no-hang evidence tests for blocked startup outcomes in `apps/macos/Shared/Tests/CoreAudioNoHangEvidenceTests.swift`
- [X] T030 [P] [US2] Add slow AudioUnit setup synthetic check in `tests/macos/route-synthetic/low-resource-startup-timeout-check.swift`
- [X] T031 [P] [US2] Add low-resource no-hang matrix script in `apps/macos/Scripts/validate-low-resource-no-hang.sh`

### Implementation for User Story 2

- [X] T032 [US2] Isolate physical device enumeration behind bounded startup logic in `apps/macos/RecApp/Sources/AudioSetup/RouteVerificationService.swift`
- [X] T033 [US2] Add cancellable 3000 ms startup attempt tracking in `apps/macos/RecApp/Sources/Capture/PassthroughBridge.swift`
- [X] T034 [US2] Ensure physical AudioUnit binding cannot run through an unbounded UI/main path in `apps/macos/RecApp/Sources/Capture/ExperimentalPassthroughCoordinator.swift`
- [X] T035 [US2] Add blocked/failed startup diagnostics in `apps/macos/RecApp/Sources/Diagnostics/DiagnosticBundleService.swift`
- [X] T036 [US2] Add UI-safe blocked/retry status mapping in `apps/macos/RecApp/Sources/AudioHealth/AudioHealthViewModel.swift`
- [X] T037 [US2] Add no-hang command integration to `apps/macos/Scripts/audio-settings-no-hang-check.sh`

**Checkpoint**: US2 passes startup timeout, no-hang surface, blocked/failure diagnostics, and UI responsiveness validation independently.

---

## Phase 5: User Story 3 - Recover Safely Across System Transitions (Priority: P1)

**Goal**: Recover truthfully after `coreaudiod` restart, sleep/wake, physical device changes, stale browser device IDs, and heartbeat loss.

**Independent Test**: Trigger each recovery case and verify ready state clears within 5 seconds, virtual devices remain visible/fail-closed, and ready returns only after valid route evidence.

### Tests for User Story 3

- [X] T038 [P] [US3] Add low-resource recovery state tests in `apps/macos/Shared/Tests/LowResourceRecoveryTests.swift`
- [X] T039 [P] [US3] Add stale browser device ID recovery fixture in `tests/macos/browser-meetings/low-resource-stale-device-recovery.md`
- [X] T040 [P] [US3] Add sleep/wake low-resource recovery fixture in `tests/macos/physical-devices/low-resource-sleep-wake.md`
- [X] T041 [P] [US3] Add `coreaudiod` restart low-resource validation to `apps/macos/Scripts/validate-low-resource-audio.sh`

### Implementation for User Story 3

- [X] T042 [US3] Add low-resource invalidation handling to `apps/macos/Shared/Sources/Routing/AppIOHealth.swift`
- [X] T043 [US3] Add recovery action mapping for stale heartbeat, restart, sleep/wake, and device changes in `apps/macos/RecApp/Sources/AudioHealth/AudioEnvironmentMonitor.swift`
- [X] T044 [US3] Add physical device change invalidation to `apps/macos/RecApp/Sources/AudioSetup/WorkingDeviceStore.swift`
- [X] T045 [US3] Preserve visible fail-closed public devices during stale heartbeat and app exit in `apps/macos/AudioDriver/Sources/Plugin/TwoBrainRecProofDriver.cpp`
- [X] T046 [US3] Record recovery route truth snapshots in `apps/macos/RecApp/Sources/Diagnostics/DiagnosticBundleService.swift`
- [X] T047 [US3] Add recovery validation coverage to `apps/macos/Scripts/validate-passthrough-release-hardening.sh`

**Checkpoint**: US3 passes restart, sleep/wake, device-change, stale-client, app-exit, and heartbeat-loss recovery validation independently.

---

## Phase 6: User Story 5 - Keep The App/Driver Boundary Observable And Reversible (Priority: P1)

**Goal**: Make publication, client IO, app bridge health, physical device validity, and recording trigger state independently observable and reversible through fallback.

**Independent Test**: Diagnostics after idle, active stream, app quit, stale heartbeat, Core Audio restart, and self-routing attempts show separate evidence planes; failed bridge never records, blocks, or loops silently; fallback restores the 005 lifecycle without driver reinstall.

### Tests for User Story 5

- [X] T048 [P] [US5] Add route truth plane contract tests in `apps/macos/Shared/Tests/LowResourceRouteTruthTests.swift`
- [X] T049 [P] [US5] Add self-routing and chained-device rejection tests in `apps/macos/Shared/Tests/LowResourcePhysicalDevicePolicyTests.swift`
- [X] T050 [P] [US5] Add fallback switch tests in `apps/macos/Shared/Tests/LowResourceFallbackTests.swift`
- [X] T051 [P] [US5] Add HAL realtime-safety regression fixture in `apps/macos/AudioDriver/Sources/Proof/HALIOProbe.cpp`

### Implementation for User Story 5

- [X] T052 [US5] Add physical working-device validity evidence to `apps/macos/Shared/Sources/Routing/SelfRoutingGuard.swift`
- [X] T053 [US5] Reject 2brain virtual, other virtual, aggregate, and multi-output working-device selections in `apps/macos/RecApp/Sources/AudioSetup/WorkingDeviceStore.swift`
- [X] T054 [US5] Add recording trigger boundary state to diagnostics in `apps/macos/Shared/Sources/Models/AudioStates.swift`
- [X] T055 [US5] Remove or isolate forbidden callback-sensitive operations in `apps/macos/AudioDriver/Sources/Plugin/TwoBrainRecProofDriver.cpp`
- [X] T056 [US5] Add fallback mode switch for accepted 005 app-launch lifecycle in `apps/macos/RecApp/Sources/Capture/PassthroughRouteEngine.swift`
- [X] T057 [US5] Add fallback evidence to validation output in `apps/macos/Scripts/validate-low-resource-audio.sh`

**Checkpoint**: US5 passes route truth, physical-device policy, realtime-safety, no-recording boundary, and fallback validation independently.

---

## Phase 7: User Story 4 - Promote Low-Resource Mode After Local Gates Pass (Priority: P2)

**Goal**: Make low-resource mode the local default only when all P1 automated gates pass, and keep the 005 lifecycle available when any P1 gate fails.

**Independent Test**: Run the full local gate suite; passing P1 evidence promotes low-resource default, while any P1 failure blocks promotion and preserves/restores the 005 lifecycle.

### Tests for User Story 4

- [X] T058 [P] [US4] Add promotion eligibility tests in `apps/macos/Shared/Tests/LowResourcePromotionTests.swift`
- [X] T059 [P] [US4] Add full validation bundle sample in `tests/macos/contract/low-resource-promotion-run.json`
- [X] T060 [P] [US4] Add blocked promotion sample in `tests/macos/contract/low-resource-blocked-run.json`

### Implementation for User Story 4

- [X] T061 [US4] Add promotion decision service in `apps/macos/Shared/Sources/Routing/LowResourcePromotionGate.swift`
- [X] T062 [US4] Wire promotion/fallback decision into app launch policy in `apps/macos/RecApp/App/TwoBrainRecApp.swift`
- [X] T063 [US4] Persist local low-resource acceptance/fallback metadata in `apps/macos/RecApp/Sources/AudioSetup/WorkingDeviceStore.swift`
- [X] T064 [US4] Add full P1 gate aggregation to `apps/macos/Scripts/validate-low-resource-audio.sh`
- [X] T065 [US4] Update release candidate checklist with low-resource promotion gate in `qa/macos/release-candidate-checklist.md`

**Checkpoint**: US4 passes promotion, blocked-promotion, fallback, and release-candidate gate validation independently.

---

## Final Phase: Polish & Cross-Cutting Validation

**Purpose**: Run the full quickstart, update QA documentation, and prepare implementation evidence for review.

- [X] T066 Run Swift model/contract tests from `specs/006-low-resource-audio/quickstart.md`
- [X] T067 Run static realtime-safety scan from `tests/macos/static/audio-rt-safety-check.sh`
- [X] T068 Run HAL proof/runtime probes from `apps/macos/AudioDriver/Makefile`
- [X] T069 Run installed package baseline from `specs/006-low-resource-audio/quickstart.md`
- [X] T070 Run no-hang and CPU gates from `apps/macos/Scripts/validate-low-resource-no-hang.sh`
- [X] T071 Run browser/meeting smoke gates from `apps/macos/Scripts/validate-low-resource-audio.sh`
- [X] T072 Run diagnostics redaction gate from `specs/006-low-resource-audio/quickstart.md`
- [X] T073 Update implementation evidence summary in `specs/006-low-resource-audio/implementation-evidence.md`
- [X] T074 Update QA low-resource release notes and clean-room review evidence in `qa/macos/low-resource-audio-gate.md`
- [X] T075 Mark completed task checkboxes in `specs/006-low-resource-audio/tasks.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 Setup**: No dependencies.
- **Phase 2 Foundational**: Depends on Phase 1; blocks all user stories.
- **US1, US2, US3, US5**: Depend on Phase 2; all are P1 and may proceed in parallel by different implementers after shared models/contracts exist.
- **US4**: Depends on all P1 stories because promotion requires the P1 gate bundle.
- **Final Phase**: Depends on desired implementation scope; full promotion requires all prior phases.

### User Story Dependencies

- **US1 (P1)**: Can start after Phase 2; provides lightweight idle and automatic activation behavior.
- **US2 (P1)**: Can start after Phase 2; can run alongside US1 but must integrate before promotion.
- **US3 (P1)**: Can start after Phase 2; can run alongside US1/US2 but must integrate before promotion.
- **US5 (P1)**: Can start after Phase 2; fallback/reversibility tasks must complete before US4.
- **US4 (P2)**: Starts after US1, US2, US3, and US5 P1 gates are green.

## Parallel Opportunities

- T002, T003, T004, and T006 can run in parallel after T001.
- T016, T017, T018, and T019 can run in parallel after Phase 2.
- T028, T029, T030, and T031 can run in parallel after Phase 2.
- T038, T039, T040, and T041 can run in parallel after Phase 2.
- T048, T049, T050, and T051 can run in parallel after Phase 2.
- T058, T059, and T060 can run in parallel after P1 gates are complete.

## Implementation Strategy

### MVP First

1. Complete Phase 1 and Phase 2.
2. Complete US1 to preserve reliable lightweight virtual routing.
3. Complete US2, US3, and US5 before considering any default promotion.
4. Stop and validate all P1 gates before US4.

### Promotion Strategy

1. Low-resource mode stays blocked/not accepted until US1, US2, US3, and US5 validation evidence passes.
2. US4 may promote low-resource mode only after all local P1 gates pass.
3. Any P1 regression restores or preserves the accepted 005 app-launch lifecycle without HAL driver reinstall.

## Notes

- `[P]` tasks touch different files and have no dependency on incomplete tasks in the same phase.
- Test and validation tasks appear before implementation tasks because this slice is high risk.
- Driver callback changes must preserve realtime safety and fail-closed behavior.
- No task may introduce recording, transcription, upload, MediaScribe, Langfuse, analytics, server storage, or external network egress.
