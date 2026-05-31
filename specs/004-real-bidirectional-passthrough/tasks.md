# Tasks: macOS Real Bidirectional Passthrough

**Input**: Design documents from `specs/004-real-bidirectional-passthrough/`

**Prerequisites**: [spec.md](spec.md), [plan.md](plan.md), [research.md](research.md), [data-model.md](data-model.md), [contracts/](contracts/), [quickstart.md](quickstart.md)

**Tests**: Tests are required because this feature changes realtime audio
routing, driver/app handoff, browser call behavior, diagnostics, fail-closed
recovery, and no-hidden-recording gates.

**Organization**: Tasks are grouped by independently testable user story.

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

- [ ] T017 [P] [US1] Add microphone passthrough synthetic test in `tests/macos/route-synthetic/live-mic-passthrough-check.swift`.
- [ ] T018 [P] [US1] Add microphone silence/empty-frame test in `tests/macos/route-synthetic/live-mic-silence-check.swift`.
- [ ] T019 [P] [US1] Add microphone self-routing rejection test in `tests/macos/route-synthetic/live-mic-self-routing-check.swift`.
- [ ] T020 [P] [US1] Add physical microphone selection tests in `apps/macos/Shared/Tests/RouteVerificationTests.swift`.

### Implementation for User Story 1

- [ ] T021 [US1] Replace heuristic physical input discovery with selected working-device input in `apps/macos/RecApp/Sources/Capture/PassthroughBridge.swift`.
- [ ] T022 [US1] Implement physical microphone capture format negotiation and mono/stereo normalization in `apps/macos/RecApp/Sources/Capture/PassthroughBridge.swift`.
- [ ] T023 [US1] Write microphone frames into the virtual microphone ring buffer without recording side effects in `apps/macos/RecApp/Sources/Capture/PassthroughBridge.swift`.
- [ ] T024 [US1] Read microphone ring buffer from `2brain Rec Microphone` driver callbacks in `apps/macos/AudioDriver/Sources/Plugin/TwoBrainRecProofDriver.cpp`.
- [ ] T025 [US1] Map microphone permission, silence, unavailable, and self-routing failures to route state in `apps/macos/RecApp/Sources/AudioSetup/RouteVerificationService.swift`.
- [ ] T026 [US1] Render microphone passthrough active/failed states in `apps/macos/RecApp/Sources/AudioSetup/RouteVerificationView.swift`.
- [ ] T027 [US1] Record microphone passthrough diagnostics and audit events in `apps/macos/RecApp/Sources/Diagnostics/DiagnosticBundleService.swift`.

**Checkpoint**: US1 proves local mic audio can feed the virtual microphone
without starting recording.

---

## Phase 4: User Story 2 - Hear 2brain Rec Speaker Through Physical Output (Priority: P1)

**Goal**: Deliver audio sent to `2brain Rec Speaker` into the selected physical
output without leaking it into the virtual microphone.

**Independent Test**: Select a physical output, play remote stimulus into
`2brain Rec Speaker`, hear it locally, and confirm no loopback above threshold.

### Tests for User Story 2

- [ ] T028 [P] [US2] Add speaker passthrough synthetic test in `tests/macos/route-synthetic/live-speaker-passthrough-check.swift`.
- [ ] T029 [P] [US2] Add speaker unavailable/muted route test in `tests/macos/route-synthetic/live-speaker-failure-check.swift`.
- [ ] T030 [P] [US2] Add remote-to-mic loopback regression test in `tests/macos/route-synthetic/live-passthrough-no-loopback-check.swift`.
- [ ] T031 [P] [US2] Add speaker output selection policy tests in `apps/macos/Shared/Tests/RouteVerificationTests.swift`.

### Implementation for User Story 2

- [ ] T032 [US2] Replace heuristic physical output discovery with selected working-device output in `apps/macos/RecApp/Sources/Capture/PassthroughBridge.swift`.
- [ ] T033 [US2] Capture virtual speaker frames from driver callbacks into the shared speaker ring buffer in `apps/macos/AudioDriver/Sources/Plugin/TwoBrainRecProofDriver.cpp`.
- [ ] T034 [US2] Implement physical speaker playback format negotiation and stereo normalization in `apps/macos/RecApp/Sources/Capture/PassthroughBridge.swift`.
- [ ] T035 [US2] Drain the virtual speaker ring buffer to selected physical output without blocking Core Audio callbacks in `apps/macos/RecApp/Sources/Capture/PassthroughBridge.swift`.
- [ ] T036 [US2] Enforce no-loopback, leakage, and latency policy in `apps/macos/Shared/Sources/Routing/SelfRoutingGuard.swift` and `apps/macos/Shared/Sources/Routing/LatencyMonitor.swift`.
- [ ] T037 [US2] Map speaker unavailable, muted, aggregate, and self-routing failures to route state in `apps/macos/RecApp/Sources/AudioSetup/RouteVerificationService.swift`.
- [ ] T038 [US2] Render speaker passthrough active/failed states in `apps/macos/RecApp/Sources/AudioSetup/RouteVerificationView.swift`.
- [ ] T039 [US2] Record speaker passthrough diagnostics and audit events in `apps/macos/RecApp/Sources/Diagnostics/DiagnosticBundleService.swift`.

**Checkpoint**: US1 and US2 together prove bidirectional local passthrough.

---

## Phase 5: User Story 3 - Join Browser Calls With Both Virtual Devices (Priority: P1)

**Goal**: Validate real browser call usability through both 2brain Rec virtual
devices or record blocked/not accepted evidence.

**Independent Test**: Join required browser targets with 2brain Rec devices,
speak locally, play remote audio, and record pass or blocked/not accepted
metadata-only evidence.

### Tests for User Story 3

- [ ] T040 [P] [US3] Add browser passthrough evidence contract tests in `apps/macos/Shared/Tests/BrowserTargetEvidenceTests.swift`.
- [ ] T041 [P] [US3] Add backend outage non-interference test in `tests/macos/route-synthetic/live-passthrough-outage-check.swift`.
- [ ] T042 [P] [US3] Update browser meeting matrix for real passthrough evidence in `tests/macos/browser-meetings/browser-meeting-matrix.md`.

### Implementation for User Story 3

- [ ] T043 [US3] Add live passthrough browser target status to `apps/macos/RecApp/Sources/AudioHealth/AudioEnvironmentMonitor.swift`.
- [ ] T044 [US3] Render browser passthrough pass/blocked/not accepted state in `apps/macos/RecApp/Sources/AudioHealth/AudioHealthView.swift`.
- [ ] T045 [US3] Keep backend/upload/transcription outage independent from local passthrough in `apps/macos/RecApp/Sources/Capture/PassthroughBridge.swift`.
- [ ] T046 [US3] Add browser passthrough diagnostics without meeting content in `apps/macos/RecApp/Sources/Diagnostics/DiagnosticBundleService.swift`.
- [ ] T047 [US3] Record Chrome, Opera, Yandex Browser, and Yandex Telemost evidence in `tests/macos/browser-meetings/browser-meeting-matrix.md`.
- [ ] T048 [US3] Record browser validation release evidence in `qa/macos/release-candidate-checklist.md`.

**Checkpoint**: Browser target matrix is explicit and truthful.

---

## Phase 6: User Story 4 - Fail Closed And Recover During Live Passthrough (Priority: P2)

**Goal**: Stop safely on app/driver/route failure and recover only after fresh
heartbeat and route revalidation.

**Independent Test**: Start a validated route, kill app, restart `coreaudiod`,
change devices, and confirm stale/fail-closed/recovery behavior.

### Tests for User Story 4

- [ ] T049 [P] [US4] Add app kill fail-closed live passthrough test in `tests/macos/route-synthetic/live-passthrough-fail-closed-check.swift`.
- [ ] T050 [P] [US4] Add `coreaudiod` restart passthrough recovery checklist in `tests/macos/installer-recovery/coreaudiod-passthrough-recovery.md`.
- [ ] T051 [P] [US4] Add physical device change passthrough recovery checklist in `tests/macos/physical-devices/live-passthrough-device-change.md`.
- [ ] T052 [P] [US4] Add Bluetooth managed passthrough route tests in `apps/macos/Shared/Tests/BluetoothRoutePolicyTests.swift`.

### Implementation for User Story 4

- [ ] T053 [US4] Invalidate active passthrough on route changes in `apps/macos/RecApp/Sources/AudioHealth/AudioEnvironmentMonitor.swift`.
- [ ] T054 [US4] Stop or degrade app-side bridge safely when heartbeat or physical device path fails in `apps/macos/RecApp/Sources/Capture/PassthroughBridge.swift`.
- [ ] T055 [US4] Preserve driver fail-closed behavior during active passthrough in `apps/macos/AudioDriver/Sources/Plugin/TwoBrainRecProofDriver.cpp`.
- [ ] T056 [US4] Add stale/recheck recovery UI for active passthrough in `apps/macos/RecApp/Sources/AudioHealth/AudioHealthView.swift`.
- [ ] T057 [US4] Record route recovery diagnostics and audit events in `apps/macos/RecApp/Sources/Diagnostics/DiagnosticBundleService.swift`.

**Checkpoint**: Live passthrough fails closed and recovers visibly.

---

## Final Phase: Validation And Release Evidence

- [ ] T058 Run `swift build --package-path apps/macos -c release --product TwoBrainRecApp`.
- [ ] T059 Run `swift test --package-path apps/macos`.
- [ ] T060 Run `make -C apps/macos/AudioDriver proof-plugin-build proof-runtime-probe-build`.
- [ ] T061 Run `sh apps/macos/Scripts/validate-real-bidirectional-passthrough.sh`.
- [ ] T062 Install the local package, restart `coreaudiod`, and record runtime probe evidence in `apps/macos/AudioDriver/RuntimeProofReport.md`.
- [ ] T063 Run microphone passthrough, speaker passthrough, no-loopback, latency, leakage, outage, and fail-closed checks under `tests/macos/`.
- [ ] T064 Record browser target evidence for Chrome, Opera, Yandex Browser, and Yandex Telemost-in-browser in `tests/macos/browser-meetings/browser-meeting-matrix.md`.
- [ ] T065 Verify diagnostics contain no raw audio, transcript text, credentials, tokens, signed URLs, or meeting content under `apps/macos/`, `tests/macos/`, `qa/macos/`, and `specs/004-real-bidirectional-passthrough/`.
- [ ] T066 Re-run `$speckit-analyze` after implementation and resolve any critical/high findings in `specs/004-real-bidirectional-passthrough/`.

## Dependencies

- Phase 1 before all other phases.
- Phase 2 blocks all user stories.
- US1 and US2 are both required for the MVP bidirectional passthrough slice.
- US3 depends on US1 and US2 for real browser call validation.
- US4 can start after US1/US2 have active passthrough states.
- Final validation depends on all selected user stories.
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
6. Run quickstart, final validation, and `$speckit-analyze` before accepting
   implementation completion.
