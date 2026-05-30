# Tasks: macOS Live Audio Passthrough

**Input**: Design documents from `specs/002-macos-live-passthrough/`

**Prerequisites**: [spec.md](spec.md), [plan.md](plan.md), [research.md](research.md), [data-model.md](data-model.md), [contracts/](contracts/), [quickstart.md](quickstart.md)

**Tests**: Test and QA tasks are required because this feature gates real call
readiness, live passthrough, route invalidation, diagnostics, and browser matrix
evidence.

**Organization**: Tasks are grouped by independently testable user story.

## Phase 1: Setup

**Purpose**: Prepare the live-passthrough feature without weakening the accepted
publication proof.

- [X] T001 [P] Harden app-side bridge startup errors and microphone render buffer allocation in `apps/macos/RecApp/Sources/Capture/PassthroughBridge.swift`.
- [ ] T002 [P] Add live readiness and route evidence value types in `apps/macos/Shared/Sources/Models/AudioModels.swift`.
- [ ] T003 [P] Add diagnostic event names for readiness and passthrough lifecycle in `apps/macos/Shared/Sources/Audit/AuditEvents.swift`.
- [ ] T004 [P] Add route evidence contract fixtures in `tests/macos/contract/desktop-driver-events.json`.

---

## Phase 2: Foundational

**Purpose**: Build shared route evidence and safe probe foundations required by
all stories.

- [ ] T005 Add shared memory read/write counters and bounded availability snapshots in `apps/macos/Shared/Sources/SharedAudioMemory.swift`.
- [ ] T006 Add matching driver-side shared memory counters for microphone, speaker, and capture buffers in `apps/macos/AudioDriver/Sources/Bridge/SharedAudioBuffer.hpp`.
- [ ] T007 Add route evidence state transition tests in `apps/macos/Shared/Tests/RouteVerificationTests.swift`.
- [ ] T008 Add a local readiness validation script that does not require browser QA in `apps/macos/Scripts/validate-live-passthrough-foundation.sh`.

**Checkpoint**: Foundations exist, but the app still must not show ready.

---

## Phase 3: User Story 1 - Prove Call-Ready Audio Routes (Priority: P1)

**Goal**: Show ready only after both real microphone and speaker paths pass.

**Independent Test**: Run the readiness check with physical devices selected and
confirm ready is blocked until live audio movement is proven on both paths.

### Tests for User Story 1

- [ ] T009 [P] [US1] Add readiness pass/fail unit tests in `apps/macos/Shared/Tests/RouteVerificationTests.swift`.
- [ ] T010 [P] [US1] Add self-routing and stale-readiness scenarios in `tests/macos/route-synthetic/mic-route-check.swift` and `tests/macos/route-synthetic/speaker-route-check.swift`.

### Implementation for User Story 1

- [ ] T011 [US1] Implement bounded user-triggered readiness probe service in `apps/macos/RecApp/Sources/AudioSetup/RouteVerificationService.swift`.
- [ ] T012 [US1] Wire the Run Check action to live route evidence without starting capture in `apps/macos/RecApp/App/TwoBrainRecApp.swift`.
- [ ] T013 [US1] Render microphone/speaker route evidence and failure reasons in `apps/macos/RecApp/Sources/AudioSetup/RouteVerificationView.swift`.
- [ ] T014 [US1] Update Audio Health to distinguish visible devices, live route evidence, and stale readiness in `apps/macos/RecApp/Sources/AudioHealth/AudioHealthViewModel.swift`.

**Checkpoint**: Ready can pass only from live route evidence, not publication.

---

## Phase 4: User Story 2 - Preserve Live Call Audio During Capture (Priority: P1)

**Goal**: Keep live call audio usable while capture is active or backend-facing
workflows are degraded.

**Independent Test**: Use both virtual devices in a supported browser meeting,
confirm local speech and remote hearing remain usable, and confirm remote audio
does not enter the mic path.

### Tests for User Story 2

- [ ] T015 [P] [US2] Add no-loopback live evidence expectations in `tests/macos/route-synthetic/no-loopback-check.swift`.
- [ ] T016 [P] [US2] Add browser meeting passthrough checklist updates in `tests/macos/browser-meetings/browser-meeting-matrix.md`.

### Implementation for User Story 2

- [ ] T017 [US2] Complete microphone-to-virtual-microphone bridge movement in `apps/macos/RecApp/Sources/Capture/PassthroughBridge.swift` and `apps/macos/AudioDriver/Sources/Plugin/TwoBrainRecProofDriver.cpp`.
- [ ] T018 [US2] Complete virtual-speaker-to-physical-speaker bridge movement in `apps/macos/RecApp/Sources/Capture/PassthroughBridge.swift` and `apps/macos/AudioDriver/Sources/Plugin/TwoBrainRecProofDriver.cpp`.
- [ ] T019 [US2] Add loopback rejection metrics and degraded state mapping in `apps/macos/Shared/Sources/Routing/SelfRoutingGuard.swift` and `apps/macos/RecApp/Sources/AudioHealth/AudioHealthViewModel.swift`.
- [ ] T020 [US2] Update release checklist with real browser passthrough evidence requirements in `qa/macos/release-candidate-checklist.md`.

**Checkpoint**: Browser meeting audio remains usable with no remote-to-mic loop.

---

## Phase 5: User Story 3 - Produce Separate Track Evidence (Priority: P2)

**Goal**: Produce local evidence for separate, aligned local and remote tracks.

**Independent Test**: Record a controlled meeting and inspect local/remote track
evidence for presence, separation, alignment, and degraded finalization.

### Tests for User Story 3

- [ ] T021 [P] [US3] Add track evidence tests in `tests/macos/physical-devices/track-integrity-check.swift`.

### Implementation for User Story 3

- [ ] T022 [US3] Add capture track evidence records in `apps/macos/RecApp/Sources/Capture/CaptureSessionController.swift`.
- [ ] T023 [US3] Add missing/silent track degraded finalization in `apps/macos/RecApp/Sources/Capture/CaptureFinalizationService.swift`.
- [ ] T024 [US3] Add local diagnostic summaries for track evidence without raw audio in `apps/macos/RecApp/Sources/Diagnostics/DiagnosticBundleService.swift`.

**Checkpoint**: Track evidence is separate and truthful.

---

## Phase 6: User Story 4 - Recover From Audio Route Changes (Priority: P2)

**Goal**: Invalidate readiness and guide recovery after route/device changes.

**Independent Test**: Pass readiness, change or disconnect devices, and confirm
the app blocks ready within 5 seconds with a specific recovery action.

### Tests for User Story 4

- [ ] T025 [P] [US4] Add device-change recovery checklist updates in `tests/macos/physical-devices/device-change-recovery.md`.

### Implementation for User Story 4

- [ ] T026 [US4] Implement route invalidation events in `apps/macos/RecApp/Sources/AudioHealth/AudioEnvironmentMonitor.swift`.
- [ ] T027 [US4] Update recovery actions for route changes and Bluetooth profile switches in `apps/macos/RecApp/Sources/AudioHealth/AudioHealthView.swift`.

**Checkpoint**: Ready becomes stale after route/device changes.

---

## Final Phase: Validation And Release Evidence

- [ ] T028 Run `swift build --package-path apps/macos -c release --product TwoBrainRecApp`.
- [ ] T029 Run `swift test --package-path apps/macos`.
- [ ] T030 Run `make -C apps/macos/AudioDriver proof-plugin-build`.
- [ ] T031 Run `sh apps/macos/Scripts/validate-foundation.sh`.
- [ ] T032 Run the updated driver install from an interactive Terminal and record runtime probe outcome in `apps/macos/AudioDriver/RuntimeProofReport.md`.
- [ ] T033 Run browser matrix checks and record evidence in `qa/macos/release-candidate-checklist.md`.
- [ ] T034 Run `$speckit-analyze` and resolve critical/high findings in `specs/002-macos-live-passthrough/`.
- [ ] T035 Verify no raw audio, transcripts, credentials, tokens, or signed URLs appear in committed feature files under `apps/macos/`, `tests/macos/`, `qa/macos/`, or `specs/002-macos-live-passthrough/`.

## Dependencies

- Phase 1 before all other phases.
- Phase 2 blocks user stories.
- US1 blocks any ready-state UI acceptance.
- US2 blocks browser meeting release readiness.
- US3 can start after US2 exposes track evidence hooks.
- US4 can start after US1 readiness state exists.
- Final validation depends on selected user stories.

## Parallel Opportunities

- T002-T004 can run in parallel.
- T009-T010 can run in parallel after Phase 2.
- T015-T016 can run in parallel after US1 interfaces exist.
- T021 and T025 can run in parallel with implementation work after Phase 2.
