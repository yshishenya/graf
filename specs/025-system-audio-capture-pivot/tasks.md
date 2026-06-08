# Tasks: System Audio Capture Pivot

**Input**: Design documents from `specs/025-system-audio-capture-pivot/`

**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/`, `quickstart.md`

**Tests**: Required. This feature changes high-risk macOS recording, permissions,
system-audio capture, local artifact truth, diagnostics, and runtime stability.
Test and contract tasks appear before implementation tasks in each story.

**Organization**: Tasks are grouped by independently testable user story.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel because it touches different files and has no dependency on incomplete tasks.
- **[Story]**: Maps task to a user story from `spec.md`.
- Every task includes an exact repository path.

## Phase 1: Setup

**Purpose**: Prepare feature scaffolding, evidence directories, and package visibility.

- [ ] T001 Create feature evidence directory with README in `specs/025-system-audio-capture-pivot/evidence/README.md`
- [ ] T002 [P] Add system-audio validation script placeholder and usage contract in `apps/macos/Scripts/validate-system-audio-capture-pivot.sh`
- [ ] T003 [P] Add CPU gate sampling script placeholder and output contract in `apps/macos/Scripts/sample-system-audio-cpu-gate.sh`
- [ ] T004 [P] Add no-HAL validation script placeholder and output contract in `apps/macos/Scripts/validate-system-audio-no-hal-probe.sh`
- [ ] T005 [P] Add system-audio capture model file placeholder in `apps/macos/Shared/Sources/Models/SystemAudioCaptureModels.swift`
- [ ] T006 [P] Add system-audio capture service file placeholder in `apps/macos/RecApp/Sources/Capture/SystemAudioCaptureService.swift`
- [ ] T007 [P] Add microphone capture service file placeholder in `apps/macos/RecApp/Sources/Capture/MicrophoneCaptureService.swift`

---

## Phase 2: Foundational

**Purpose**: Shared models, contracts, redaction, permission state, and writer abstractions that block all user stories.

**CRITICAL**: No user story implementation starts until this phase is complete.

- [ ] T008 [P] Add `SystemAudioCaptureSession`, `MicrophoneCaptureSession`, `CaptureScopeApproval`, and `CaptureHealthSnapshot` models in `apps/macos/Shared/Sources/Models/SystemAudioCaptureModels.swift`
- [ ] T009 [P] Add capture state and failure reason enum extensions for system-audio MVP in `apps/macos/Shared/Sources/Models/AudioStates.swift`
- [ ] T010 [P] Add contract tests for system-audio models and state transitions in `apps/macos/Shared/Tests/SystemAudioCaptureContractTests.swift`
- [ ] T011 [P] Add diagnostic redaction tests for system-audio capture metadata in `apps/macos/Shared/Tests/SystemAudioDiagnosticRedactionTests.swift`
- [ ] T012 Update diagnostic redaction allow/deny lists for system-audio evidence in `apps/macos/Shared/Sources/Diagnostics/DiagnosticRedactor.swift`
- [ ] T013 Refactor `LocalRecordingWriter` to accept independent microphone and incoming sample sources without requiring `SharedAudioMemory` in `apps/macos/RecApp/Sources/Capture/LocalRecordingWriter.swift`
- [ ] T014 [P] Add unit tests for independent local recording sample sources in `apps/macos/Shared/Tests/LocalRecordingWriterSystemAudioTests.swift`
- [ ] T015 [P] Add manifest model tests for `incomingSystemAudio`, scope approval, permission state, and CPU evidence in `apps/macos/Shared/Tests/SystemAudioManifestContractTests.swift`
- [ ] T016 Update local recording manifest models for system-audio source metadata in `apps/macos/Shared/Sources/Models/LocalRecordingModels.swift`
- [ ] T017 Update contract validation tool to require system-audio manifest fields in `apps/macos/Shared/Tools/ContractValidation/main.swift`
- [ ] T018 Run `swift build` for the macOS package and record result in `specs/025-system-audio-capture-pivot/evidence/test-results.md`

**Checkpoint**: Foundation ready. Models, redaction, manifest contract, and writer seam exist before story work.

---

## Phase 3: User Story 1 - Record A Meeting Without Virtual Devices (Priority: P1) MVP

**Goal**: Record local microphone and incoming/system audio without selecting virtual 2brain Rec devices.

**Independent Test**: Controlled recording produces `manifest.json`, `mic.wav`, and `incoming.wav` without virtual device selection.

### Tests for User Story 1

- [ ] T019 [P] [US1] Add ScreenCaptureKit incoming-audio service tests with fake sample buffers in `apps/macos/Shared/Tests/SystemAudioCaptureServiceTests.swift`
- [ ] T020 [P] [US1] Add microphone capture service tests with fake permission/device states in `apps/macos/Shared/Tests/MicrophoneCaptureServiceTests.swift`
- [ ] T021 [P] [US1] Add capture scope approval tests for app/window/display selection in `apps/macos/Shared/Tests/CaptureScopeApprovalTests.swift`
- [ ] T022 [P] [US1] Add integration-style writer test for dual sources producing `mic.wav` and `incoming.wav` in `apps/macos/Shared/Tests/SystemAudioRecordingPackageTests.swift`

### Implementation for User Story 1

- [ ] T023 [US1] Implement ScreenCaptureKit system-audio capture lifecycle in `apps/macos/RecApp/Sources/Capture/SystemAudioCaptureService.swift`
- [ ] T024 [US1] Implement microphone capture lifecycle and permission preflight in `apps/macos/RecApp/Sources/Capture/MicrophoneCaptureService.swift`
- [ ] T025 [US1] Implement user-confirmed capture scope approval service in `apps/macos/RecApp/Sources/Capture/CaptureScopeApprovalService.swift`
- [ ] T026 [US1] Integrate system-audio and microphone services into local recording start/stop in `apps/macos/RecApp/App/TwoBrainRecApp.swift`
- [ ] T027 [US1] Update `CaptureControlView` to show system-audio-first recording controls and no virtual-device requirement in `apps/macos/RecApp/Sources/Capture/CaptureControlView.swift`
- [ ] T028 [US1] Add metadata-only start/stop evidence for scope approval and no-egress recording in `apps/macos/RecApp/Sources/Capture/RecordingEvidenceService.swift`
- [ ] T029 [US1] Update manual controlled recording quickstart evidence template in `specs/025-system-audio-capture-pivot/evidence/artifact-matrix.md`

**Checkpoint**: US1 independently records dual-track local artifacts without virtual-device selection.

---

## Phase 4: User Story 2 - Make Permissions And Blockers Obvious (Priority: P1)

**Goal**: Block or label missing permissions truthfully with specific recovery actions.

**Independent Test**: Permission matrix records correct blocker/degraded state and no false success.

### Tests for User Story 2

- [ ] T030 [P] [US2] Add permission gate unit tests for microphone/system-audio combinations in `apps/macos/Shared/Tests/SystemAudioPermissionGateTests.swift`
- [ ] T031 [P] [US2] Add UI state tests for permission blocker copy and recovery actions in `apps/macos/Shared/Tests/SystemAudioPermissionUXTests.swift`
- [ ] T032 [P] [US2] Add manifest tests for explicit degraded attempts with missing permissions in `apps/macos/Shared/Tests/SystemAudioDegradedAttemptTests.swift`

### Implementation for User Story 2

- [ ] T033 [US2] Implement combined microphone and Screen/System Audio permission gate in `apps/macos/RecApp/Sources/Capture/SystemAudioPermissionGate.swift`
- [ ] T034 [US2] Wire permission gate into recording start blocker flow in `apps/macos/RecApp/App/TwoBrainRecApp.swift`
- [ ] T035 [US2] Add user-facing permission/degraded state copy models in `apps/macos/Shared/Sources/Models/SystemAudioCaptureModels.swift`
- [ ] T036 [US2] Update `CaptureControlView` permission blocker and degraded-attempt UI in `apps/macos/RecApp/Sources/Capture/CaptureControlView.swift`
- [ ] T037 [US2] Record permission matrix evidence template and expected outcomes in `specs/025-system-audio-capture-pivot/evidence/permission-matrix.md`

**Checkpoint**: US2 independently proves missing permissions cannot create false accepted recordings.

---

## Phase 5: User Story 3 - Preserve Dual-Track Truth (Priority: P1)

**Goal**: Ensure artifacts truthfully report saved, degraded, blocked, failed, and aligned track states.

**Independent Test**: Manifest scenarios cover both tracks, mic-only, incoming-only, no incoming, protected/blocked, late-start, early-stop, and misalignment.

### Tests for User Story 3

- [ ] T038 [P] [US3] Add manifest tests for both tracks saved and aligned in `apps/macos/Shared/Tests/SystemAudioManifestContractTests.swift`
- [ ] T039 [P] [US3] Add manifest tests for silent, protected, blocked, missing, and dropped incoming audio in `apps/macos/Shared/Tests/SystemAudioManifestFailureReasonTests.swift`
- [ ] T040 [P] [US3] Add track alignment tolerance tests for `durationDifferenceSeconds <= 3` in `apps/macos/Shared/Tests/SystemAudioTrackAlignmentTests.swift`

### Implementation for User Story 3

- [ ] T041 [US3] Extend `LocalRecordingManifestService` to write scope, permission, failure reason, and CPU metadata in `apps/macos/RecApp/Sources/Capture/LocalRecordingManifestService.swift`
- [ ] T042 [US3] Update `LocalRecordingWriter` to mark incoming/system audio as degraded or blocked for no frames, silent frames, protected frames, and misalignment in `apps/macos/RecApp/Sources/Capture/LocalRecordingWriter.swift`
- [ ] T043 [US3] Add `CaptureHealthMonitor` for frame continuity, levels, dropped frames, silence windows, and alignment metadata in `apps/macos/RecApp/Sources/Capture/CaptureHealthMonitor.swift`
- [ ] T044 [US3] Update `RecordingEvidenceService` to emit safe local recording evidence for system-audio degraded states in `apps/macos/RecApp/Sources/Capture/RecordingEvidenceService.swift`
- [ ] T045 [US3] Record artifact matrix evidence template for saved/degraded/blocked/failed outcomes in `specs/025-system-audio-capture-pivot/evidence/artifact-matrix.md`

**Checkpoint**: US3 independently proves artifact truth for all required track outcomes.

---

## Phase 6: User Story 4 - Keep The Mac Responsive And Cool (Priority: P1)

**Goal**: Prevent CoreAudio/HAL hangs and prove CPU/resource gates for idle, active recording, stop, and quit.

**Independent Test**: CPU/no-hang evidence shows no HAL probes and CPU below gates.

### Tests for User Story 4

- [ ] T046 [P] [US4] Add CPU gate model tests for idle, active, stop, quit, and sustained threshold semantics in `apps/macos/Shared/Tests/SystemAudioCPUGateTests.swift`
- [ ] T047 [P] [US4] Add no-HAL validation tests for evidence models in `apps/macos/Shared/Tests/SystemAudioNoHALValidationTests.swift`
- [ ] T048 [P] [US4] Add capture resource release tests for stop and quit outcomes in `apps/macos/Shared/Tests/SystemAudioResourceReleaseTests.swift`

### Implementation for User Story 4

- [ ] T049 [US4] Implement CPU gate evidence model and sustained sample evaluation in `apps/macos/Shared/Sources/Models/SystemAudioCaptureModels.swift`
- [ ] T050 [US4] Implement `sample-system-audio-cpu-gate.sh` using metadata-only process sampling in `apps/macos/Scripts/sample-system-audio-cpu-gate.sh`
- [ ] T051 [US4] Implement `validate-system-audio-no-hal-probe.sh` to fail on HAL probe dependency in `apps/macos/Scripts/validate-system-audio-no-hal-probe.sh`
- [ ] T052 [US4] Ensure app termination releases system-audio and microphone resources in `apps/macos/RecApp/App/TwoBrainRecApp.swift`
- [ ] T053 [US4] Record CPU gate evidence template in `specs/025-system-audio-capture-pivot/evidence/cpu-gates.md`
- [ ] T054 [US4] Record no-HAL evidence template in `specs/025-system-audio-capture-pivot/evidence/no-hal-probe.md`

**Checkpoint**: US4 independently proves runtime stability gates are measurable and no-HAL validation is enforceable.

---

## Phase 7: User Story 5 - Keep Driver Work Parked Safely (Priority: P2)

**Goal**: Separate future driver experiments from normal MVP recording.

**Independent Test**: MVP recording status and validation do not require driver repair, runtime probes, or virtual devices.

### Tests for User Story 5

- [ ] T055 [P] [US5] Add tests that MVP readiness ignores unavailable driver diagnostics in `apps/macos/Shared/Tests/SystemAudioDriverParkedTests.swift`
- [ ] T056 [P] [US5] Add tests that UI copy does not require virtual devices for MVP recording in `apps/macos/Shared/Tests/SystemAudioNoVirtualDeviceCopyTests.swift`

### Implementation for User Story 5

- [ ] T057 [US5] Update `DriverSetupView` or surrounding composition so driver repair is not presented as an MVP recording prerequisite in `apps/macos/RecApp/Sources/DriverSetup/DriverSetupView.swift`
- [ ] T058 [US5] Update `LocalAudioSnapshot.summary` for system-audio MVP readiness language in `apps/macos/RecApp/App/TwoBrainRecApp.swift`
- [ ] T059 [US5] Add future-driver boundary notes to macOS README in `apps/macos/README.md`
- [ ] T060 [US5] Record driver-parked validation evidence template in `specs/025-system-audio-capture-pivot/evidence/driver-parked.md`

**Checkpoint**: US5 independently proves driver work is parked and cannot regress MVP recording status.

---

## Phase 8: Cross-Cutting UX, Accessibility, And Localization

**Purpose**: Complete UI quality gates that apply across P1 stories.

- [ ] T061 [P] Add accessibility tests for recording indicator, Stop, level meters, blockers, scope picker, and degraded banners in `apps/macos/Shared/Tests/SystemAudioAccessibilityTests.swift`
- [ ] T062 [P] Add localization-safe state label tests in `apps/macos/Shared/Tests/SystemAudioLocalizationTests.swift`
- [ ] T063 [P] Add long-name and small-window UI state tests in `apps/macos/Shared/Tests/SystemAudioResponsiveStateTests.swift`
- [ ] T064 Update `CaptureControlView` accessibility labels, keyboard focus, long-name handling, and small-window state behavior in `apps/macos/RecApp/Sources/Capture/CaptureControlView.swift`
- [ ] T065 Update shared state labels for localization-safe system-audio status in `apps/macos/Shared/Sources/Models/SystemAudioCaptureModels.swift`

---

## Phase 9: Final Validation And Evidence

**Purpose**: Run and record release gates required by quickstart and contracts.

- [ ] T066 Run `swift build` from `apps/macos` and record result in `specs/025-system-audio-capture-pivot/evidence/test-results.md`
- [ ] T067 Run `swift test` from `apps/macos` or record the local XCTest/toolchain blocker in `specs/025-system-audio-capture-pivot/evidence/test-results.md`
- [ ] T068 Run `swift run ContractValidation` from `apps/macos` and record result in `specs/025-system-audio-capture-pivot/evidence/test-results.md`
- [ ] T069 Run `apps/macos/Scripts/validate-system-audio-no-hal-probe.sh` and record result in `specs/025-system-audio-capture-pivot/evidence/no-hal-probe.md`
- [ ] T070 Run permission matrix validation and record results in `specs/025-system-audio-capture-pivot/evidence/permission-matrix.md`
- [ ] T071 Run controlled artifact validation and record results in `specs/025-system-audio-capture-pivot/evidence/artifact-matrix.md`
- [ ] T072 Run CPU gate validation for idle, active recording, stop, and quit and record results in `specs/025-system-audio-capture-pivot/evidence/cpu-gates.md`
- [ ] T073 Run 30-minute development validation and record accepted, blocked, failed, degraded, and not-tested results in `specs/025-system-audio-capture-pivot/evidence/development-30-minute.md`
- [ ] T074 Run 75-minute manual release validation and record accepted, blocked, failed, degraded, and not-tested results in `specs/025-system-audio-capture-pivot/evidence/release-75-minute.md`
- [ ] T075 Run forbidden-content scan across code, specs, diagnostics, and evidence and record result in `specs/025-system-audio-capture-pivot/evidence/test-results.md`
- [ ] T076 Review all evidence against quickstart and contracts and record final scope review in `specs/025-system-audio-capture-pivot/evidence/scope-review.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 Setup**: No dependencies.
- **Phase 2 Foundational**: Depends on Phase 1 and blocks all user stories.
- **US1, US2, US3, US4**: Depend on Phase 2. They may proceed in parallel after shared writer/model seams exist, but file conflicts in `TwoBrainRecApp.swift`, `CaptureControlView.swift`, and `LocalRecordingWriter.swift` require coordination.
- **US5**: Depends on Phase 2 and can proceed after US1/US2 clarify the new readiness language.
- **Phase 8 UX/Accessibility**: Depends on US1/US2 UI state model.
- **Phase 9 Final Validation**: Depends on all selected implementation phases.

### User Story Dependencies

- **US1**: MVP path; should complete first for a runnable recording slice.
- **US2**: Can be implemented after foundation, but final UI integration depends on US1 recording start flow.
- **US3**: Can be implemented after foundation, but final manifest integration depends on US1 writer changes.
- **US4**: Can be implemented after foundation; final resource-release checks depend on US1 capture services.
- **US5**: Depends on the new MVP readiness model from US1/US2.

### Parallel Opportunities

- T002-T007 can run in parallel.
- T008-T011 and T014-T015 can run in parallel after setup.
- T019-T022 can run in parallel.
- T030-T032 can run in parallel.
- T038-T040 can run in parallel.
- T046-T048 can run in parallel.
- T055-T056 can run in parallel.
- T061-T063 can run in parallel.

## Parallel Example: US1

```text
Task: T019 Add ScreenCaptureKit incoming-audio service tests in apps/macos/Shared/Tests/SystemAudioCaptureServiceTests.swift
Task: T020 Add microphone capture service tests in apps/macos/Shared/Tests/MicrophoneCaptureServiceTests.swift
Task: T021 Add capture scope approval tests in apps/macos/Shared/Tests/CaptureScopeApprovalTests.swift
Task: T022 Add integration-style writer test in apps/macos/Shared/Tests/SystemAudioRecordingPackageTests.swift
```

## Implementation Strategy

### MVP First

1. Complete Phase 1 and Phase 2.
2. Complete US1 enough to record dual tracks without virtual devices.
3. Complete US2 permission blockers before any user-facing trial.
4. Complete US3 manifest truth before claiming recording success.
5. Complete US4 CPU/no-HAL gates before long-duration validation.

### Quality Gate

Do not claim the feature accepted until Phase 9 evidence exists and blocked,
failed, degraded, or not-tested rows are not counted as acceptance.
