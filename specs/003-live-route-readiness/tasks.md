# Tasks: macOS Live Route Readiness

**Input**: Design documents from `specs/003-live-route-readiness/`

**Prerequisites**: [spec.md](spec.md), [plan.md](plan.md), [research.md](research.md), [data-model.md](data-model.md), [contracts/](contracts/), [quickstart.md](quickstart.md)

**Tests**: Tests are required because this feature gates real route readiness,
browser-call behavior, driver fail-closed recovery, latency/leakage thresholds,
diagnostics redaction, and visible non-recording route state.

**Organization**: Tasks are grouped by independently testable user story.

## Phase 1: Setup

**Purpose**: Prepare live-route readiness without weakening the accepted 002
foundation.

- [X] T001 [P] Add live route readiness evidence contract fixtures in `tests/macos/contract/live-route-readiness-events.json`.
- [X] T002 [P] Add browser target evidence fixture schema in `tests/macos/contract/browser-target-evidence.json`.
- [X] T003 [P] Add route readiness QA evidence sections in `qa/macos/release-candidate-checklist.md`.
- [X] T004 [P] Add live route readiness runtime proof notes in `apps/macos/AudioDriver/RuntimeProofReport.md`.
- [X] T005 [P] Add quick validation wrapper for this feature in `apps/macos/Scripts/validate-live-route-readiness.sh`.

---

## Phase 2: Foundational

**Purpose**: Add shared models, measurement contracts, and safe evidence storage
used by all stories.

- [X] T006 Add live route readiness models in `apps/macos/Shared/Sources/Models/AudioModels.swift`.
- [X] T007 Add readiness state values for checking/ready/stale/degraded/failed in `apps/macos/Shared/Sources/Models/AudioStates.swift`.
- [X] T008 Add audit event names for live route readiness, browser target evidence, latency/leakage measurement, and route invalidation in `apps/macos/Shared/Sources/Audit/AuditEvents.swift`.
- [X] T009 Add route readiness policy tests in `apps/macos/Shared/Tests/RouteVerificationTests.swift`.
- [X] T010 [P] Add latency and leakage policy tests in `apps/macos/Shared/Tests/LatencyGateTests.swift`.
- [X] T011 [P] Add browser target evidence tests in `apps/macos/Shared/Tests/BrowserTargetEvidenceTests.swift`.
- [X] T012 [P] Add route invalidation state transition tests in `apps/macos/Shared/Tests/RouteInvalidationTests.swift`.
- [X] T013 Add metadata-only diagnostics tests for readiness evidence in `apps/macos/Shared/Tests/DiagnosticRedactionTests.swift`.
- [X] T014 Keep shared-memory heartbeat layout stable and add stale-layout resize handling in `apps/macos/Shared/Sources/SharedAudioMemory.swift`.
- [X] T015 Keep driver-side shared-memory heartbeat layout stable and add stale-layout resize handling in `apps/macos/AudioDriver/Sources/Plugin/TwoBrainRecProofDriver.cpp`.
- [X] T016 Keep runtime probe output focused on Core Audio publication, hidden, alive, and running state in `apps/macos/AudioDriver/Sources/Proof/RuntimeDeviceProbe.cpp`.

**Checkpoint**: Shared evidence exists, but the app still must not show ready.

---

## Phase 3: User Story 1 - Pass Real Route Readiness (Priority: P1)

**Goal**: Show ready only after microphone and speaker live route evidence pass.

**Independent Test**: Run the user-triggered readiness check with physical
devices selected and confirm ready appears only after both live paths pass.

### Tests for User Story 1

- [X] T017 [P] [US1] Add microphone live path synthetic test in `tests/macos/route-synthetic/live-mic-readiness-check.swift`.
- [X] T018 [P] [US1] Add speaker live path synthetic test in `tests/macos/route-synthetic/live-speaker-readiness-check.swift`.
- [X] T019 [P] [US1] Add self-routing rejection test for live readiness in `tests/macos/route-synthetic/live-self-routing-check.swift`.
- [X] T020 [P] [US1] Add readiness UI state tests in `apps/macos/Shared/Tests/RouteVerificationTests.swift`.

### Implementation for User Story 1

- [X] T021 [US1] Implement physical microphone live evidence collection and self-routing rejection in `apps/macos/RecApp/Sources/AudioSetup/RouteVerificationService.swift`.
- [X] T022 [US1] Implement physical speaker stimulus, aggregate/multi-output handling, and self-routing rejection in `apps/macos/RecApp/Sources/AudioSetup/RouteVerificationService.swift`.
- [X] T023 [US1] Prevent publication-only checks from producing ready in `apps/macos/RecApp/App/TwoBrainRecApp.swift`.
- [X] T024 [US1] Render checking/ready/stale/degraded/failed states with path-specific failure reasons in `apps/macos/RecApp/Sources/AudioSetup/RouteVerificationView.swift`.
- [X] T025 [US1] Update Audio Health route summary for live readiness in `apps/macos/RecApp/Sources/AudioHealth/AudioHealthViewModel.swift`.
- [X] T026 [US1] Add metadata-only readiness diagnostics in `apps/macos/RecApp/Sources/Diagnostics/DiagnosticBundleService.swift`.
- [X] T027 [US1] Record readiness pass/fail audit events in `apps/macos/RecApp/Sources/AudioSetup/RouteVerificationService.swift`.

**Checkpoint**: US1 alone delivers a trustworthy ready state for selected
physical devices without starting recording.

---

## Phase 4: User Story 2 - Keep Browser Call Audio Usable (Priority: P1)

**Goal**: Prove browser targets can use the ready route or record blocked/not
accepted evidence.

**Independent Test**: Join required browser targets with 2brain Rec devices and
record pass or blocked/not accepted evidence without starting recording.

### Tests for User Story 2

- [X] T028 [P] [US2] Add browser target evidence contract test in `apps/macos/Shared/Tests/BrowserTargetEvidenceTests.swift`.
- [X] T029 [P] [US2] Add backend/network outage live-route test in `tests/macos/route-synthetic/live-route-outage-check.swift`.
- [X] T030 [P] [US2] Update browser meeting matrix requirements in `tests/macos/browser-meetings/browser-meeting-matrix.md`.

### Implementation for User Story 2

- [X] T031 [US2] Add browser target evidence model handling in `apps/macos/RecApp/Sources/AudioHealth/AudioEnvironmentMonitor.swift`.
- [X] T032 [US2] Add browser target validation status rendering in `apps/macos/RecApp/Sources/AudioHealth/AudioHealthView.swift`.
- [X] T033 [US2] Preserve private app I/O fail-closed readiness invalidation in `apps/macos/AudioDriver/Sources/Plugin/TwoBrainRecProofDriver.cpp`.
- [X] T034 [US2] Add browser pass/blocked/not accepted diagnostics in `apps/macos/RecApp/Sources/Diagnostics/DiagnosticBundleService.swift`.
- [X] T035 [US2] Record browser matrix and backend outage evidence in `qa/macos/release-candidate-checklist.md`.

**Checkpoint**: Required browser targets have explicit pass or blocked/not
accepted evidence and backend outage does not break live route readiness.

---

## Phase 5: User Story 3 - Enforce Leakage And Latency Gates (Priority: P1)

**Goal**: Block release-ready route status when built-in/wired latency or
remote-to-mic leakage exceeds thresholds.

**Independent Test**: Run controlled route stimulus and confirm latency/leakage
threshold failures produce degraded state.

### Tests for User Story 3

- [X] T036 [P] [US3] Add live latency measurement synthetic test in `tests/macos/route-synthetic/live-latency-check.swift`.
- [X] T037 [P] [US3] Add live leakage measurement synthetic test in `tests/macos/route-synthetic/live-leakage-check.swift`.
- [X] T038 [P] [US3] Add latency/leakage degraded state tests in `apps/macos/Shared/Tests/LatencyGateTests.swift`.

### Implementation for User Story 3

- [X] T039 [US3] Implement added route latency evidence in `apps/macos/Shared/Sources/Routing/LatencyMonitor.swift`.
- [X] T040 [US3] Implement leakage evidence model and policy in `apps/macos/Shared/Sources/Routing/SelfRoutingGuard.swift`.
- [X] T041 [US3] Map latency/leakage failures to degraded route state in `apps/macos/RecApp/Sources/AudioHealth/AudioHealthViewModel.swift`.
- [X] T042 [US3] Add latency/leakage evidence to diagnostics without raw audio in `apps/macos/RecApp/Sources/Diagnostics/DiagnosticBundleService.swift`.
- [X] T043 [US3] Record live latency/leakage evidence in `qa/macos/release-candidate-checklist.md`.

**Checkpoint**: Built-in/wired release readiness is blocked unless latency and
leakage gates pass.

---

## Phase 6: User Story 4 - Invalidate And Recover Routes (Priority: P2)

**Goal**: Mark readiness stale after route/device/browser/profile changes and
guide recovery.

**Independent Test**: Pass readiness, change a relevant route input, and confirm
readiness becomes stale within 5 seconds with a recovery action.

### Tests for User Story 4

- [X] T044 [P] [US4] Add route invalidation synthetic test in `tests/macos/physical-devices/live-route-invalidation-check.md`.
- [X] T045 [P] [US4] Add Bluetooth managed route readiness tests in `apps/macos/Shared/Tests/BluetoothRoutePolicyTests.swift`.
- [X] T046 [P] [US4] Add `coreaudiod` restart recovery checklist in `tests/macos/installer-recovery/coreaudiod-route-recovery.md`.

### Implementation for User Story 4

- [X] T047 [US4] Implement live route invalidation events in `apps/macos/RecApp/Sources/AudioHealth/AudioEnvironmentMonitor.swift`.
- [X] T048 [US4] Add stale/recheck recovery actions in `apps/macos/RecApp/Sources/AudioHealth/AudioHealthView.swift`.
- [X] T049 [US4] Extend Bluetooth profile policy for live readiness in `apps/macos/RecApp/Sources/AudioHealth/BluetoothRoutePolicy.swift`.
- [X] T050 [US4] Record route invalidation diagnostics and audit events in `apps/macos/RecApp/Sources/Diagnostics/DiagnosticBundleService.swift`.

**Checkpoint**: Ready state becomes stale after route-changing events and
recovery is visible.

---

## Final Phase: Validation And Release Evidence

- [X] T051 Run `swift build --package-path apps/macos -c release --product TwoBrainRecApp`.
- [X] T052 Run `swift test --package-path apps/macos`.
- [X] T053 Run `make -C apps/macos/AudioDriver proof-plugin-build proof-runtime-probe-build`.
- [X] T054 Run `sh apps/macos/Scripts/validate-live-route-readiness.sh`.
- [X] T055 Run live microphone, speaker, self-routing, latency, leakage, outage, and invalidation checks under `tests/macos/`.
- [X] T056 Install the local package, restart `coreaudiod`, and record runtime probe evidence in `apps/macos/AudioDriver/RuntimeProofReport.md`.
- [X] T057 Record browser target evidence for Chrome, Opera, Yandex Browser, and Yandex Telemost-in-browser in `tests/macos/browser-meetings/browser-meeting-matrix.md`.
- [X] T058 Verify diagnostics contain no raw audio, transcript text, credentials, tokens, or signed URLs under `apps/macos/`, `tests/macos/`, `qa/macos/`, and `specs/003-live-route-readiness/`.
- [X] T059 Re-run `$speckit-analyze` after implementation and resolve any critical/high findings in `specs/003-live-route-readiness/`.

## Dependencies

- Phase 1 before all other phases.
- Phase 2 blocks all user stories.
- US1 is the MVP and blocks US2/US3 release evidence.
- US2 and US3 can proceed in parallel after US1 readiness evidence exists.
- US4 can proceed after US1 readiness state exists.
- Final validation depends on all selected user stories.
- T021 and T022 block T023-T027.
- T031 blocks T034-T035.
- T039 and T040 block T041-T043.
- T047 blocks T048 and T050.

## Parallel Opportunities

- T001-T005 can run in parallel.
- T010-T013 can run in parallel after T006-T009.
- T017-T020 can run in parallel after Phase 2.
- T028-T030 can run in parallel after US1 readiness interfaces exist.
- T036-T038 can run in parallel after US1 readiness interfaces exist.
- T044-T046 can run in parallel after US1 readiness state exists.

## Implementation Strategy

1. Complete setup and foundational evidence models.
2. Implement US1 first to achieve trustworthy ready state.
3. Add browser evidence and outage resilience.
4. Add latency/leakage release gates.
5. Add route invalidation/recovery.
6. Run full validation and analyze before implementation completion.
