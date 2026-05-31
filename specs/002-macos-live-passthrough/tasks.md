# Tasks: macOS Live Audio Passthrough Foundation

**Input**: Design documents from `specs/002-macos-live-passthrough/`

**Prerequisites**: [spec.md](spec.md), [plan.md](plan.md), [research.md](research.md), [data-model.md](data-model.md), [contracts/](contracts/), [quickstart.md](quickstart.md)

**Tests**: Test and QA tasks are required because this feature gates real call
readiness foundations, live passthrough scaffolding, route invalidation,
diagnostics, private app I/O, driver lifecycle approval, and browser/Bluetooth
matrix evidence. Production browser-call passthrough remains blocked until a
later feature proves real microphone/speaker audio movement end to end.

**Organization**: Tasks are grouped by independently testable user story.

## Phase 1: Setup

**Purpose**: Prepare the live-passthrough feature without weakening the accepted
publication proof or driver governance gates.

- [X] T001 [P] Harden app-side bridge startup errors and microphone render buffer allocation in `apps/macos/RecApp/Sources/Capture/PassthroughBridge.swift`.
- [X] T002 [P] Add live readiness, route evidence, private app I/O, latency, Bluetooth profile, and stream-health value types in `apps/macos/Shared/Sources/Models/AudioModels.swift`.
- [X] T003 [P] Add diagnostic event names for readiness, passthrough lifecycle, stream-health failure, loopback leakage, private app I/O loss, latency degradation, and debug-clip cleanup in `apps/macos/Shared/Sources/Audit/AuditEvents.swift`.
- [X] T004 [P] Add route evidence and private app I/O contract fixtures in `tests/macos/contract/desktop-driver-events.json`.
- [X] T005 [P] Document driver approval gates for privilege model, installer, signing, notarization, update, rollback, repair, uninstall, passthrough failure behavior, and QA matrix in `qa/macos/driver-gate-approval.md`.
- [X] T006 [P] Add driver lifecycle validation checklist for install, update, rollback, repair, uninstall, app-engine crash, and route recovery in `qa/macos/driver-lifecycle-checklist.md`.

---

## Phase 2: Foundational

**Purpose**: Build shared route evidence, private app I/O health, latency
measurement, and safe probe foundations required by all stories.

- [X] T007 Add shared memory read/write counters, 3-second capturability snapshots, empty-buffer counters, latency timestamps, and bounded availability snapshots in `apps/macos/Shared/Sources/SharedAudioMemory.swift`.
- [X] T008 Add matching driver-side shared memory counters for microphone, speaker, capture buffers, empty buffers, dropped frames, latency timestamps, heartbeat state, and last valid frame timing in `apps/macos/AudioDriver/Sources/Bridge/SharedAudioBuffer.hpp`.
- [X] T009 Add route evidence and stream-health state transition tests, including natural silence with valid frames, in `apps/macos/Shared/Tests/RouteVerificationTests.swift`.
- [X] T010 Add private app I/O heartbeat and fail-closed state transition tests in `apps/macos/Shared/Tests/AppIOHealthTests.swift`.
- [X] T011 Add latency threshold tests for built-in/wired `<=30 ms` pass and `>30 ms` degraded outcomes in `apps/macos/Shared/Tests/LatencyGateTests.swift`.
- [X] T012 Add a local readiness validation script that does not require browser QA in `apps/macos/Scripts/validate-live-passthrough-foundation.sh`.
- [X] T013 Add a synthetic route latency harness in `tests/macos/route-synthetic/latency-check.swift`.
- [X] T014 Add private app I/O heartbeat model and recovery state in `apps/macos/Shared/Sources/Routing/AppIOHealth.swift`.

**Checkpoint**: Foundations exist, but the app still must not show ready.

---

## Phase 3: User Story 1 - Prove Call-Ready Audio Routes (Priority: P1)

**Goal**: Keep ready blocked unless both real microphone and speaker paths have
accepted evidence, and provide the user-visible/scaffolded route state needed by
the next real-route feature.

**Independent Test**: Run the readiness check with physical devices selected and
confirm ready is blocked until live audio movement is proven on both paths.

### Tests for User Story 1

- [X] T015 [P] [US1] Add readiness pass/fail unit tests in `apps/macos/Shared/Tests/RouteVerificationTests.swift`.
- [X] T016 [P] [US1] Add self-routing and stale-readiness scenarios in `tests/macos/route-synthetic/mic-route-check.swift` and `tests/macos/route-synthetic/speaker-route-check.swift`.
- [X] T017 [P] [US1] Add guided device management tests for explicit approval, route restore, reversible setup, and no silent route changes in `apps/macos/Shared/Tests/GuidedDeviceManagementTests.swift`.
- [X] T018 [P] [US1] Add volume and mute mapping safety tests for physical-to-virtual route state in `apps/macos/Shared/Tests/VolumeMuteMappingTests.swift`.

### Implementation for User Story 1

- [X] T019 [US1] Implement bounded user-triggered readiness probe scaffolding in `apps/macos/RecApp/Sources/AudioSetup/RouteVerificationService.swift`.
- [X] T020 [US1] Wire the Run Check action to block ready from publication-only evidence without starting capture in `apps/macos/RecApp/App/TwoBrainRecApp.swift`.
- [X] T021 [US1] Render microphone/speaker route evidence and publication-only failure reasons in `apps/macos/RecApp/Sources/AudioSetup/RouteVerificationView.swift`.
- [X] T022 [US1] Update Audio Health to distinguish visible devices, live route evidence, stale readiness, latency degradation, and private app I/O loss in `apps/macos/RecApp/Sources/AudioHealth/AudioHealthViewModel.swift`.
- [X] T023 [US1] Implement explicit user-approved guided device setup and reversible restore in `apps/macos/RecApp/Sources/AudioSetup/GuidedDeviceManagementService.swift`.
- [X] T024 [US1] Implement physical working-device tracking and virtual-vs-physical route distinction in `apps/macos/RecApp/Sources/AudioSetup/WorkingDeviceStore.swift`.
- [X] T025 [US1] Implement visible volume and mute mapping without using volume or mute as a hidden capture signal in `apps/macos/RecApp/Sources/AudioSetup/VolumeMuteMapper.swift`.

**Checkpoint**: Ready remains blocked from publication-only evidence, and guided
route changes are explicit, reversible, and visible. Passing live route evidence
is intentionally deferred to the next feature.

---

## Phase 4: User Story 2 - Preserve Live Call Audio During Capture (Priority: P1)

**Goal**: Add app/driver foundations and evidence gates needed to keep live call
audio usable while capture is active or backend-facing workflows are degraded.

**Independent Test**: Use both virtual devices in a supported browser meeting,
confirm local speech and remote hearing remain usable, confirm remote audio does
not enter the mic path above the leakage threshold, confirm latency gates are
enforced, and confirm public devices fail closed when private app I/O is gone.

### Tests for User Story 2

- [X] T026 [P] [US2] Add no-loopback live evidence expectations, including 45 dB speaker-reference leakage threshold, in `tests/macos/route-synthetic/no-loopback-check.swift`.
- [X] T027 [P] [US2] Add private app I/O kill/crash/relaunch fail-closed validation in `tests/macos/route-synthetic/app-io-fail-closed-check.swift`.
- [X] T028 [P] [US2] Add built-in/wired latency acceptance and degraded route scenarios in `tests/macos/route-synthetic/latency-check.swift`.
- [X] T029 [P] [US2] Add backend/network outage passthrough scenario to `tests/macos/route-synthetic/passthrough-outage-check.swift`.
- [X] T030 [P] [US2] Add browser meeting passthrough checklist updates in `tests/macos/browser-meetings/browser-meeting-matrix.md`.

### Implementation for User Story 2

- [X] T031 [US2] Add microphone-to-virtual-microphone bridge movement scaffolding in `apps/macos/RecApp/Sources/Capture/PassthroughBridge.swift` and `apps/macos/AudioDriver/Sources/Plugin/TwoBrainRecProofDriver.cpp`.
- [X] T032 [US2] Add virtual-speaker-to-physical-speaker bridge movement scaffolding in `apps/macos/RecApp/Sources/Capture/PassthroughBridge.swift` and `apps/macos/AudioDriver/Sources/Plugin/TwoBrainRecProofDriver.cpp`.
- [X] T033 [US2] Implement private app I/O heartbeat exchange and app-engine loss detection in `apps/macos/RecApp/Sources/Capture/PassthroughBridge.swift` and `apps/macos/AudioDriver/Sources/Plugin/TwoBrainRecProofDriver.cpp`.
- [X] T034 [US2] Implement fail-closed public device hidden/unavailable behavior and recovery revalidation in `apps/macos/AudioDriver/Sources/Plugin/TwoBrainRecProofDriver.cpp`.
- [X] T035 [US2] Add AEC/reference-stream loopback rejection metrics and degraded state mapping in `apps/macos/Shared/Sources/Routing/SelfRoutingGuard.swift` and `apps/macos/RecApp/Sources/AudioHealth/AudioHealthViewModel.swift`.
- [X] T036 [US2] Add latency measurement and `>30 ms` degraded state mapping in `apps/macos/Shared/Sources/Routing/LatencyMonitor.swift` and `apps/macos/RecApp/Sources/AudioHealth/AudioHealthViewModel.swift`.
- [X] T037 [US2] Update release checklist with real browser passthrough, private app I/O fail-closed, latency, backend outage, and leakage evidence requirements in `qa/macos/release-candidate-checklist.md`.

**Checkpoint**: Synthetic leakage/latency/outage gates exist and private app I/O
loss fails closed. Real browser meeting audio remains blocked until the next
feature accepts live route movement.

---

## Phase 5: User Story 3 - Produce Separate Track Evidence (Priority: P2)

**Goal**: Produce local evidence for separate, aligned local and remote tracks
while preserving visible capture control.

**Independent Test**: Record a controlled meeting and inspect local/remote track
evidence for presence, separation, alignment, degraded finalization, and a
persistent one-action stop surface.

### Tests for User Story 3

- [X] T038 [P] [US3] Add track evidence tests in `tests/macos/physical-devices/track-integrity-check.swift`.
- [X] T039 [P] [US3] Add active capture visible indicator and one-action stop tests in `apps/macos/RecApp/Tests/CaptureControlTests.swift`.
- [X] T040 [P] [US3] Add development debug clip disable and cleanup validation in `tests/macos/route-synthetic/debug-clip-cleanup-check.swift`.

### Implementation for User Story 3

- [X] T041 [US3] Add capture track evidence records in `apps/macos/RecApp/Sources/Capture/CaptureSessionController.swift`.
- [X] T042 [US3] Add stream-health degraded finalization for missing tracks, no valid frames for one 3-second health interval, repeated empty buffers, and ordinary silence with valid frames in `apps/macos/RecApp/Sources/Capture/CaptureFinalizationService.swift`.
- [X] T043 [US3] Add local diagnostic summaries for track evidence without raw audio in `apps/macos/RecApp/Sources/Diagnostics/DiagnosticBundleService.swift`.
- [X] T044 [US3] Preserve persistent active capture indicator and one-action stop in `apps/macos/RecApp/Sources/Capture/CaptureControlView.swift`.
- [X] T045 [US3] Implement development debug clip registry, release disable flag, and local cleanup path in `apps/macos/RecApp/Sources/Diagnostics/DebugClipCleanupService.swift`.

**Checkpoint**: Track evidence is separate and truthful, debug clips are
release-disabled and cleanable, and active capture has visible one-action stop.

---

## Phase 6: User Story 4 - Recover From Audio Route Changes (Priority: P2)

**Goal**: Invalidate readiness and guide recovery after route/device changes,
including Bluetooth and AirPods-class profile changes.

**Independent Test**: Pass readiness, change or disconnect devices, switch
Bluetooth profiles, and confirm the app blocks ready within 5 seconds with a
specific recovery action and managed-route evidence.

### Tests for User Story 4

- [X] T046 [P] [US4] Add device-change recovery checklist updates in `tests/macos/physical-devices/device-change-recovery.md`.
- [X] T047 [P] [US4] Add Bluetooth/AirPods profile stability, one-sided audio, dropout, valid-frame, and measured-latency pilot checks in `tests/macos/physical-devices/bluetooth-managed-route-check.md`.

### Implementation for User Story 4

- [X] T048 [US4] Implement route invalidation events in `apps/macos/RecApp/Sources/AudioHealth/AudioEnvironmentMonitor.swift`.
- [X] T049 [US4] Update recovery actions for route changes and Bluetooth profile switches in `apps/macos/RecApp/Sources/AudioHealth/AudioHealthView.swift`.
- [X] T050 [US4] Implement Bluetooth and AirPods-class profile detection and bidirectional availability evidence in `apps/macos/RecApp/Sources/AudioHealth/BluetoothRouteMonitor.swift`.
- [X] T051 [US4] Map Bluetooth profile switches, one-sided audio events, valid-frame failures, dropout threshold failures, and measured-latency evidence to warning or degraded state in `apps/macos/RecApp/Sources/AudioHealth/BluetoothRoutePolicy.swift`.

**Checkpoint**: Ready becomes stale after route/device changes, and Bluetooth
routes are treated as managed pilot routes rather than built-in/wired parity.

---

## Final Phase: Validation And Release Evidence

- [X] T052 Run `swift build --package-path apps/macos -c release --product TwoBrainRecApp`.
- [X] T053 Run `swift test --package-path apps/macos`.
- [X] T054 Run `make -C apps/macos/AudioDriver proof-plugin-build`.
- [X] T055 Run `sh apps/macos/Scripts/validate-foundation.sh`.
- [X] T056 Run `sh apps/macos/Scripts/validate-live-passthrough-foundation.sh`.
- [X] T057 Run the updated driver install from an interactive Terminal and record runtime probe outcome in `apps/macos/AudioDriver/RuntimeProofReport.md`.
- [X] T058 Run driver gate and lifecycle checklists and record approval evidence in `qa/macos/driver-gate-approval.md` and `qa/macos/driver-lifecycle-checklist.md`.
- [X] T059 Run private app I/O kill/crash/relaunch validation and record fail-closed evidence in `apps/macos/AudioDriver/RuntimeProofReport.md`.
- [X] T060 Run latency, leakage, stream-health, and debug-clip cleanup checks and record outcomes in `qa/macos/release-candidate-checklist.md`.
- [X] T061 Run backend outage checks and record browser matrix as blocked/not accepted evidence in `qa/macos/release-candidate-checklist.md`.
- [X] T062 Record Bluetooth/AirPods managed-route pilot evidence as blocked/not accepted with current profile/device state in `tests/macos/physical-devices/bluetooth-managed-route-check.md`.
- [X] T063 Run `$speckit-analyze` and resolve critical/high findings in `specs/002-macos-live-passthrough/`.
- [X] T064 Verify no raw audio, transcripts, credentials, tokens, signed URLs, or release-enabled debug clips appear in committed feature files under `apps/macos/`, `tests/macos/`, `qa/macos/`, or `specs/002-macos-live-passthrough/`.

## Dependencies

- Phase 1 before all other phases.
- Phase 2 blocks user stories.
- US1 blocks any ready-state UI acceptance.
- US2 blocks browser meeting release readiness and private app I/O acceptance.
- US3 can start after US2 exposes track evidence hooks.
- US4 can start after US1 readiness state exists.
- Final validation depends on selected user stories.
- T033 blocks T034, T027, T059.
- T036 blocks T028 and T060.
- T045 blocks T040 and T064.
- T050 blocks T047, T051, and T062.

## Parallel Opportunities

- T002-T006 can run in parallel.
- T009-T014 can run in parallel after Phase 2 starts because they touch different test/model files.
- T015-T018 can run in parallel after Phase 2.
- T026-T030 can run in parallel after US1 interfaces exist.
- T038-T040 and T046-T047 can run in parallel with implementation work after Phase 2.
