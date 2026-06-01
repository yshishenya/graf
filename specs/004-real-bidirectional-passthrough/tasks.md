# Tasks: macOS Real Bidirectional Passthrough

**Input**: Design documents from `specs/004-real-bidirectional-passthrough/`

**Prerequisites**: [spec.md](spec.md), [plan.md](plan.md), [research.md](research.md), [data-model.md](data-model.md), [contracts/](contracts/), [quickstart.md](quickstart.md)

**Tests**: Tests are required because this feature changes realtime audio
routing, driver/app handoff, browser call behavior, diagnostics, fail-closed
recovery, and no-hidden-recording gates.

**Organization**: Tasks are grouped by independently testable user story.

## Post-Review Status - 2026-06-01

The first live-passthrough implementation is treated as an experimental spike,
not accepted release behavior. Completed implementation tasks below represent
modeling, synthetic checks, UI scaffolding, and initial driver/app proof work.
They do not close physical/browser live audio acceptance.

New stabilization tasks T067-T081 are mandatory before any final acceptance task
can be marked complete.

## Phase 1: Setup

**Purpose**: Prepare passthrough evidence, validation, and contracts without
weakening the accepted 003 runtime proof.

- [X] T001 [P] Add passthrough contract fixture in `tests/macos/contract/live-passthrough-events.json`.
- [X] T002 [P] Add browser passthrough evidence fixture in `tests/macos/contract/browser-passthrough-evidence.json`.
- [X] T003 [P] Add passthrough release evidence section in `qa/macos/release-candidate-checklist.md`.
- [X] T004 [P] Add real passthrough scope notes in `apps/macos/AudioDriver/RuntimeProofReport.md`.
- [X] T005 [P] Add validation wrapper for this feature in `apps/macos/Scripts/validate-real-bidirectional-passthrough.sh`.

---

## Phase 2: Foundational

**Purpose**: Shared state, diagnostics, and app/driver contracts required by all
stories.

- [X] T006 Add live passthrough session and path models in `apps/macos/Shared/Sources/Models/AudioModels.swift`.
- [X] T007 Add passthrough status values for inactive/checking/ready/active/stale/degraded/failed/blocked in `apps/macos/Shared/Sources/Models/AudioStates.swift`.
- [X] T008 Add audit event names for passthrough start/stop, pass/fail, stale/degraded, browser validation, and route recovery in `apps/macos/Shared/Sources/Audit/AuditEvents.swift`.
- [X] T009 [P] Add passthrough policy tests in `apps/macos/Shared/Tests/LivePassthroughPolicyTests.swift`.
- [X] T010 [P] Add shared ring-buffer compatibility tests in `apps/macos/Shared/Tests/SharedAudioMemoryCompatibilityTests.swift`.
- [X] T011 [P] Add passthrough diagnostics redaction tests in `apps/macos/Shared/Tests/DiagnosticRedactionTests.swift`.
- [X] T012 [P] Add fail-closed regression tests for active passthrough state in `apps/macos/Shared/Tests/AppIOHealthTests.swift`.
- [X] T013 Keep shared-memory layout stable or add versioned migration tests before any layout change in `apps/macos/Shared/Sources/SharedAudioMemory.swift`.
- [X] T014 Keep driver-side shared-memory layout stable or add matching versioned migration before any layout change in `apps/macos/AudioDriver/Sources/Bridge/SharedAudioBuffer.hpp`.
- [X] T015 Add runtime probe expectations for active/stale/fail-closed passthrough evidence in `apps/macos/AudioDriver/Sources/Proof/RuntimeDeviceProbe.cpp`.
- [X] T016 Add metadata-only passthrough diagnostic bundle contract in `apps/macos/RecApp/Sources/Diagnostics/DiagnosticBundleService.swift`.

**Checkpoint**: Shared evidence and contracts exist, but real passthrough is not
yet enabled.

---

## Phase 3: User Story 1 - Speak Through 2brain Rec Microphone (Priority: P1)

**Goal**: Deliver selected physical microphone audio into `2brain Rec
Microphone` without starting recording.

**Independent Test**: Select a physical mic, select `2brain Rec Microphone` in a
controlled receiver, speak locally, and confirm live speech arrives while app UI
stays non-recording.

### Tests for User Story 1

- [X] T017 [P] [US1] Add microphone passthrough synthetic test in `tests/macos/route-synthetic/live-mic-passthrough-check.swift`.
- [X] T018 [P] [US1] Add microphone silence/empty-frame test in `tests/macos/route-synthetic/live-mic-silence-check.swift`.
- [X] T019 [P] [US1] Add microphone self-routing rejection test in `tests/macos/route-synthetic/live-mic-self-routing-check.swift`.
- [X] T020 [P] [US1] Add physical microphone selection tests in `apps/macos/Shared/Tests/RouteVerificationTests.swift`.

### Implementation for User Story 1

- [X] T021 [US1] Replace heuristic physical input discovery with selected working-device input in `apps/macos/RecApp/Sources/Capture/PassthroughBridge.swift`.
- [X] T022 [US1] Implement physical microphone capture format negotiation and mono/stereo normalization in `apps/macos/RecApp/Sources/Capture/PassthroughBridge.swift`.
- [X] T023 [US1] Write microphone frames into the virtual microphone ring buffer without recording side effects in `apps/macos/RecApp/Sources/Capture/PassthroughBridge.swift`.
- [X] T024 [US1] Read microphone ring buffer from `2brain Rec Microphone` driver callbacks in `apps/macos/AudioDriver/Sources/Plugin/TwoBrainRecProofDriver.cpp`.
- [X] T025 [US1] Map microphone permission, silence, unavailable, and self-routing failures to route state in `apps/macos/RecApp/Sources/AudioSetup/RouteVerificationService.swift`.
- [X] T026 [US1] Render microphone passthrough active/failed states in `apps/macos/RecApp/Sources/AudioSetup/RouteVerificationView.swift`.
- [X] T027 [US1] Record microphone passthrough diagnostics and audit events in `apps/macos/RecApp/Sources/Diagnostics/DiagnosticBundleService.swift`.

**Checkpoint**: US1 has synthetic and experimental implementation coverage.
Physical live microphone acceptance remains pending until the stabilization
phase proves realtime-safe callbacks, valid ring-buffer semantics, and measured
frame continuity.

---

## Phase 4: User Story 2 - Hear 2brain Rec Speaker Through Physical Output (Priority: P1)

**Goal**: Deliver audio sent to `2brain Rec Speaker` into the selected physical
output without leaking it into the virtual microphone.

**Independent Test**: Select a physical output, play remote stimulus into
`2brain Rec Speaker`, hear it locally, and confirm no loopback above threshold.

### Tests for User Story 2

- [X] T028 [P] [US2] Add speaker passthrough synthetic test in `tests/macos/route-synthetic/live-speaker-passthrough-check.swift`.
- [X] T029 [P] [US2] Add speaker unavailable/muted route test in `tests/macos/route-synthetic/live-speaker-failure-check.swift`.
- [X] T030 [P] [US2] Add remote-to-mic loopback regression test in `tests/macos/route-synthetic/live-passthrough-no-loopback-check.swift`.
- [X] T031 [P] [US2] Add speaker output selection policy tests in `apps/macos/Shared/Tests/RouteVerificationTests.swift`.

### Implementation for User Story 2

- [X] T032 [US2] Replace heuristic physical output discovery with selected working-device output in `apps/macos/RecApp/Sources/Capture/PassthroughBridge.swift`.
- [X] T033 [US2] Capture virtual speaker frames from driver callbacks into the shared speaker ring buffer in `apps/macos/AudioDriver/Sources/Plugin/TwoBrainRecProofDriver.cpp`.
- [X] T034 [US2] Implement physical speaker playback format negotiation and stereo normalization in `apps/macos/RecApp/Sources/Capture/PassthroughBridge.swift`.
- [X] T035 [US2] Drain the virtual speaker ring buffer to selected physical output without blocking Core Audio callbacks in `apps/macos/RecApp/Sources/Capture/PassthroughBridge.swift`.
- [X] T036 [US2] Enforce no-loopback, leakage, and latency policy in `apps/macos/Shared/Sources/Routing/SelfRoutingGuard.swift` and `apps/macos/Shared/Sources/Routing/LatencyMonitor.swift`.
- [X] T037 [US2] Map speaker unavailable, muted, aggregate, and self-routing failures to route state in `apps/macos/RecApp/Sources/AudioSetup/RouteVerificationService.swift`.
- [X] T038 [US2] Render speaker passthrough active/failed states in `apps/macos/RecApp/Sources/AudioSetup/RouteVerificationView.swift`.
- [X] T039 [US2] Record speaker passthrough diagnostics and audit events in `apps/macos/RecApp/Sources/Diagnostics/DiagnosticBundleService.swift`.

**Checkpoint**: US1 and US2 have synthetic and experimental implementation
coverage. Bidirectional local passthrough is not accepted until physical output
playback, underrun handling, latency, leakage, and no-loopback evidence pass.

---

## Phase 5: User Story 3 - Join Browser Calls With Both Virtual Devices (Priority: P1)

**Goal**: Validate real browser call usability through both 2brain Rec virtual
devices or record blocked/not accepted evidence.

**Independent Test**: Join required browser targets with 2brain Rec devices,
speak locally, play remote audio, and record pass or blocked/not accepted
metadata-only evidence.

### Tests for User Story 3

- [X] T040 [P] [US3] Add browser passthrough evidence contract tests in `apps/macos/Shared/Tests/BrowserTargetEvidenceTests.swift`.
- [X] T041 [P] [US3] Add backend outage non-interference test in `tests/macos/route-synthetic/live-passthrough-outage-check.swift`.
- [X] T042 [P] [US3] Update browser meeting matrix for real passthrough evidence in `tests/macos/browser-meetings/browser-meeting-matrix.md`.

### Implementation for User Story 3

- [X] T043 [US3] Add live passthrough browser target status to `apps/macos/RecApp/Sources/AudioHealth/AudioEnvironmentMonitor.swift`.
- [X] T044 [US3] Render browser passthrough pass/blocked/not accepted state in `apps/macos/RecApp/Sources/AudioHealth/AudioHealthView.swift`.
- [X] T045 [US3] Keep backend/upload/transcription outage independent from local passthrough in `apps/macos/RecApp/Sources/Capture/PassthroughBridge.swift`.
- [X] T046 [US3] Add browser passthrough diagnostics without meeting content in `apps/macos/RecApp/Sources/Diagnostics/DiagnosticBundleService.swift`.
- [X] T047 [US3] Record Chrome, Opera, Yandex Browser, and Yandex Telemost evidence in `tests/macos/browser-meetings/browser-meeting-matrix.md`.
- [X] T048 [US3] Record browser validation release evidence in `qa/macos/release-candidate-checklist.md`.

**Checkpoint**: Browser target matrix exists. Browser live passthrough remains
blocked/not accepted until physical live-route evidence is recorded per target.

---

## Phase 6: User Story 4 - Fail Closed And Recover During Live Passthrough (Priority: P2)

**Goal**: Stop safely on app/driver/route failure and recover only after fresh
heartbeat and route revalidation.

**Independent Test**: Start a validated route, kill app, restart `coreaudiod`,
change devices, and confirm stale/fail-closed/recovery behavior.

### Tests for User Story 4

- [X] T049 [P] [US4] Add app kill fail-closed live passthrough test in `tests/macos/route-synthetic/live-passthrough-fail-closed-check.swift`.
- [X] T050 [P] [US4] Add `coreaudiod` restart passthrough recovery checklist in `tests/macos/installer-recovery/coreaudiod-passthrough-recovery.md`.
- [X] T051 [P] [US4] Add physical device change passthrough recovery checklist in `tests/macos/physical-devices/live-passthrough-device-change.md`.
- [X] T052 [P] [US4] Add Bluetooth managed passthrough route tests in `apps/macos/Shared/Tests/BluetoothRoutePolicyTests.swift`.

### Implementation for User Story 4

- [X] T053 [US4] Invalidate active passthrough on route changes in `apps/macos/RecApp/Sources/AudioHealth/AudioEnvironmentMonitor.swift`.
- [X] T054 [US4] Stop or degrade app-side bridge safely when heartbeat or physical device path fails in `apps/macos/RecApp/Sources/Capture/PassthroughBridge.swift`.
- [X] T055 [US4] Preserve driver fail-closed behavior during active passthrough in `apps/macos/AudioDriver/Sources/Plugin/TwoBrainRecProofDriver.cpp`.
- [X] T056 [US4] Add stale/recheck recovery UI for active passthrough in `apps/macos/RecApp/Sources/AudioHealth/AudioHealthView.swift`.
- [X] T057 [US4] Record route recovery diagnostics and audit events in `apps/macos/RecApp/Sources/Diagnostics/DiagnosticBundleService.swift`.

**Checkpoint**: Fail-closed models and checklists exist. Runtime recovery
acceptance remains pending until `coreaudiod`, app kill, device-change, and
browser stale-device evidence are recorded.

---

## Phase 7: Stabilization Refactor And Pipeline Gates

**Purpose**: Convert the experimental spike into a safe, reviewable route engine
before accepting live audio behavior.

- [X] T067 [P] Add realtime callback safety static check in `tests/macos/static/audio-rt-safety-check.sh` and wire it into `apps/macos/Scripts/validate-real-bidirectional-passthrough.sh`.
- [X] T068 [P] Add default launch safety validation in `tests/macos/installer-recovery/default-passthrough-disabled-check.sh`.
- [X] T069 [P] Add `coreaudiod` idle/no-hang validation checklist or harness in `tests/macos/installer-recovery/coreaudiod-no-hang-check.md`.
- [X] T070 [P] Define shared ring-buffer behavior contract in `specs/004-real-bidirectional-passthrough/contracts/passthrough-contract.md`.
- [X] T071 Add matching Swift ring-buffer behavior tests in `apps/macos/Shared/Tests/SharedAudioMemoryCompatibilityTests.swift`.
- [X] T072 Add matching C++ ring-buffer proof vectors in `apps/macos/AudioDriver/Sources/Proof/` or `apps/macos/AudioDriver/Tests/`.
- [X] T073 Refactor `apps/macos/RecApp/App/TwoBrainRecApp.swift` so SwiftUI view lifecycle does not own bridge startup, heartbeat, device selection, or delayed Core Audio refresh.
- [X] T074 Add an explicit route-engine coordinator in `apps/macos/RecApp/Sources/Capture/` with start/stop/state ownership separate from UI.
- [X] T075 Refactor `apps/macos/RecApp/Sources/Capture/PassthroughBridge.swift` so AudioUnit callbacks use preallocated buffers and emit only atomic counters on the realtime path.
- [X] T076 Remove speaker partial-read time stretching from `apps/macos/RecApp/Sources/Capture/PassthroughBridge.swift`; replace it with explicit underrun zero-fill and degraded evidence.
- [X] T077 Restore truthful route readiness in `apps/macos/RecApp/App/TwoBrainRecApp.swift` and `apps/macos/RecApp/Sources/AudioSetup/RouteVerificationService.swift` so env flags and device visibility cannot return `.passed` without measured live-route evidence.
- [X] T078 Add parameterized runtime probe expectations for default publication, non-running surface, and visible-alive surface states in `apps/macos/AudioDriver/Sources/Proof/RuntimeDeviceProbe.cpp`.
- [X] T079 Update `specs/004-real-bidirectional-passthrough/tasks.md`, `quickstart.md`, and browser/release evidence files so synthetic checks, experimental checks, physical checks, and browser acceptance cannot be confused.
- [X] T080 Run `$speckit-analyze` after stabilization artifacts are updated and resolve all critical/high findings before continuing implementation.
- [X] T081 Re-run code review for realtime/Core Audio, app-driver architecture, tests/docs, and maintainability before final validation.
- [X] T082 Add an installed-device HAL I/O probe in `apps/macos/AudioDriver/Sources/Proof/HALIOProbe.cpp` and wire `proof-hal-io-probe-run` into `apps/macos/AudioDriver/Makefile`.
- [X] T083 Auto-start the local non-recording passthrough route on app launch in `apps/macos/RecApp/App/TwoBrainRecApp.swift` and `apps/macos/RecApp/Sources/Capture/PassthroughRouteEngine.swift`.
- [X] T084 Update default launch validation and Spec Kit artifacts so `Run Check` is a recheck/repair action, not the normal passthrough activation path.
- [X] T085 Record user acceptance for automatic non-recording passthrough startup without pressing `Run Check` in `tests/macos/browser-meetings/browser-meeting-matrix.md` and `apps/macos/AudioDriver/RuntimeProofReport.md`.

---

## Final Phase: Validation And Release Evidence

- [X] T058 Run `swift build --package-path apps/macos -c release --product TwoBrainRecApp`.
- [X] T059 Run `swift test --package-path apps/macos`.
- [X] T060 Run `make -C apps/macos/AudioDriver proof-plugin-build proof-runtime-probe-build`.
- [X] T061 Run `sh apps/macos/Scripts/validate-real-bidirectional-passthrough.sh` after stabilization gates are wired in.
- [X] T062 Install the local package, restart `coreaudiod`, and record runtime probe evidence in `apps/macos/AudioDriver/RuntimeProofReport.md`.
- [X] T063 Run physical microphone passthrough, speaker passthrough, no-loopback, latency, leakage, outage, and fail-closed checks under `tests/macos/`.
- [X] T064 Record browser target evidence for Chrome, Opera, Yandex Browser, and Yandex Telemost-in-browser in `tests/macos/browser-meetings/browser-meeting-matrix.md`.
- [X] T065 Verify diagnostics contain no raw audio, transcript text, credentials, tokens, signed URLs, or meeting content under `apps/macos/`, `tests/macos/`, `qa/macos/`, and `specs/004-real-bidirectional-passthrough/`.
- [X] T066 Re-run `$speckit-analyze` after implementation and resolve any critical/high findings in `specs/004-real-bidirectional-passthrough/`.

## Dependencies

- Phase 1 before all other phases.
- Phase 2 blocks all user stories.
- US1 and US2 are both required for the MVP bidirectional passthrough slice.
- US3 depends on US1 and US2 for real browser call validation.
- US4 can start after US1/US2 have active passthrough states.
- Phase 7 blocks final live-route acceptance.
- Final validation depends on all selected user stories and Phase 7.
- T021-T024 block T025-T027.
- T032-T035 block T036-T039.
- T043-T046 block T047-T048.
- T053-T055 block T056-T057.

## Parallel Opportunities

- T001-T005 can run in parallel.
- T009-T012 can run in parallel after T006-T008.
- T017-T020 can run in parallel after Phase 2.
- T028-T031 can run in parallel after Phase 2.
- T040-T042 can run in parallel after US1/US2 interfaces exist.
- T049-T052 can run in parallel after active passthrough state exists.

## Implementation Strategy

1. Complete setup and foundational shared contracts.
2. Implement US1 microphone passthrough first and validate independently.
3. Implement US2 speaker passthrough and no-loopback gating.
4. Validate browser call evidence with US3.
5. Add fail-closed and recovery hardening with US4.
6. Complete Phase 7 stabilization/refactor gates.
7. Run quickstart, final validation, and `$speckit-analyze` before accepting
   implementation completion.
