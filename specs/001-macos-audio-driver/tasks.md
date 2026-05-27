# Tasks: macOS Virtual Audio Driver MVP

**Input**: Design documents from `specs/001-macos-audio-driver/`

**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md), [data-model.md](data-model.md), [contracts/](contracts/), [quickstart.md](quickstart.md)

**Tests**: Test and QA tasks are required because the specification defines route verification, long-run audio integrity, installer recovery, diagnostic redaction, and browser/device matrix success criteria.

**Organization**: Tasks are grouped by user story so each story can be implemented and validated independently after shared foundations are complete.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel because it touches different files and has no dependency on incomplete tasks.
- **[Story]**: Maps to user stories from [spec.md](spec.md).
- Every task includes an exact target path.

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create the macOS workspace, shared conventions, and QA folders used by all stories.

- [X] T001 Create macOS workspace directories from the plan in `apps/macos/RecApp/`, `apps/macos/AudioDriver/`, `apps/macos/Shared/`, `apps/macos/Installer/`, `tests/macos/`, and `qa/macos/`.
- [X] T002 Create the initial Swift package/workspace manifest for shared app code in `apps/macos/Package.swift`.
- [X] T003 [P] Add shared Swift lint and formatting configuration in `apps/macos/.swiftlint.yml`.
- [X] T004 [P] Add audio component build notes and required Apple signing/notarization prerequisites in `apps/macos/AudioDriver/README.md`.
- [X] T005 [P] Add installer packaging notes and local signing placeholder policy in `apps/macos/Installer/README.md`.
- [X] T006 [P] Add QA matrix placeholders for OS, browsers, and physical devices in `qa/macos/device-matrix.md` and `qa/macos/browser-targets.md`.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Establish contracts, value types, security boundaries, and the first virtual-device proof before user story implementation.

**CRITICAL**: No user story work can begin until this phase is complete.

- [X] T007 Create shared value types for `VirtualAudioDevice`, `PhysicalAudioDevice`, `RouteVerification`, `CaptureSession`, `AudioTrack`, `LocalBufferItem`, `DriverHealthReport`, and `InstallerState` in `apps/macos/Shared/Sources/Models/AudioModels.swift`.
- [X] T008 [P] Create shared enums for route, capture, installer, passthrough, continuity, and redaction states in `apps/macos/Shared/Sources/Models/AudioStates.swift`.
- [X] T009 [P] Create contract fixtures for desktop-driver events in `tests/macos/contract/desktop-driver-events.json`.
- [X] T010 [P] Create diagnostic redaction forbidden-field fixtures in `tests/macos/contract/diagnostic-forbidden-fields.json`.
- [X] T011 Create the desktop-driver contract validator skeleton in `apps/macos/Shared/Tests/ContractTests/DesktopDriverContractTests.swift`.
- [X] T012 Create the diagnostics redaction validator skeleton in `apps/macos/Shared/Tests/ContractTests/DiagnosticsRedactionTests.swift`.
- [X] T013 Create a Phase 0 virtual-device proof harness for publishing `2brain Rec Microphone` and `2brain Rec Speaker` in `apps/macos/AudioDriver/Sources/Proof/VirtualDeviceProof.cpp`.
- [X] T014 Create a passthrough and mirror timing proof harness in `apps/macos/AudioDriver/Sources/Proof/PassthroughTimingProof.cpp`.
- [X] T015 Document the Phase 0 proof result, selected implementation path, and rejected alternatives in `apps/macos/AudioDriver/README.md`.
- [X] T016 Create local diagnostic redaction utilities in `apps/macos/Shared/Sources/Diagnostics/DiagnosticRedactor.swift`.
- [X] T017 Create local encrypted buffer interface definitions without upload implementation in `apps/macos/Shared/Sources/Buffering/LocalBufferContracts.swift`.
- [X] T018 Create audit event name definitions for driver and capture lifecycle events in `apps/macos/Shared/Sources/Audit/AuditEvents.swift`.

**Checkpoint**: Foundation ready - contracts, shared models, redaction policy, local buffer boundaries, and virtual-device proof are ready for story implementation.

---

## Phase 3: User Story 1 - Complete Driver Setup And Route Verification (Priority: P1) MVP

**Goal**: Install the macOS audio layer, expose both virtual devices, select physical devices, and show `ready` only after valid mic and speaker route verification.

**Independent Test**: Install on a supported Apple Silicon Mac, grant permissions, verify both virtual devices appear, select physical input/output, complete route verification, and confirm `ready` is blocked until both paths pass.

### Tests for User Story 1

- [ ] T019 [P] [US1] Add contract tests for route verification state transitions in `apps/macos/Shared/Tests/RouteVerificationTests.swift`.
- [ ] T020 [P] [US1] Add synthetic mic route QA harness in `tests/macos/route-synthetic/mic-route-check.swift`.
- [ ] T021 [P] [US1] Add synthetic speaker route QA harness in `tests/macos/route-synthetic/speaker-route-check.swift`.
- [ ] T022 [P] [US1] Add installer smoke test checklist for fresh install and restart-required states in `tests/macos/installer-recovery/fresh-install.md`.

### Implementation for User Story 1

- [ ] T023 [US1] Implement virtual device publication wrapper for `2brain Rec Microphone` and `2brain Rec Speaker` in `apps/macos/AudioDriver/Sources/Device/VirtualDeviceRegistry.cpp`.
- [ ] T024 [US1] Implement self-routing detection and rejection in `apps/macos/Shared/Sources/Routing/SelfRoutingGuard.swift`.
- [ ] T025 [US1] Implement physical input/output selection state in `apps/macos/RecApp/Sources/AudioSetup/PhysicalDeviceSelectionViewModel.swift`.
- [ ] T026 [US1] Implement mic and speaker route verification orchestration in `apps/macos/RecApp/Sources/AudioSetup/RouteVerificationService.swift`.
- [ ] T027 [US1] Implement onboarding route verification UI state in `apps/macos/RecApp/Sources/AudioSetup/RouteVerificationView.swift`.
- [ ] T028 [US1] Implement driver install, permission, and virtual-device status surface in `apps/macos/RecApp/Sources/AudioSetup/DriverSetupView.swift`.
- [ ] T029 [US1] Implement interactive signed/notarized installer package definition for install and repair flows in `apps/macos/Installer/Packages/2brain-rec.pkgproj`.
- [ ] T030 [US1] Update QA browser/device matrix with US1 route verification acceptance coverage in `qa/macos/device-matrix.md` and `qa/macos/browser-targets.md`.

**Checkpoint**: User Story 1 is independently functional and validates install plus route readiness.

---

## Phase 4: User Story 2 - Capture Separate Tracks Without Breaking The Call (Priority: P1)

**Goal**: Capture local mic and remote speaker audio as separate aligned tracks while live mic/speaker passthrough remains usable during network or server failure.

**Independent Test**: Join a supported browser meeting using both virtual devices, record for 30 minutes, verify separate local/remote tracks, no remote-to-mic loopback, and stable passthrough during a 5-minute outage.

### Tests for User Story 2

- [ ] T031 [P] [US2] Add remote-to-mic loopback detection test harness in `tests/macos/route-synthetic/no-loopback-check.swift`.
- [ ] T032 [P] [US2] Add track alignment and dropped-frame test harness in `tests/macos/physical-devices/track-integrity-check.swift`.
- [ ] T033 [P] [US2] Add browser meeting QA script for Chrome, Opera, Yandex Browser, and Yandex Telemost in `tests/macos/browser-meetings/browser-meeting-matrix.md`.
- [ ] T034 [P] [US2] Add network/server outage acceptance scenario in `tests/macos/browser-meetings/offline-passthrough.md`.

### Implementation for User Story 2

- [ ] T035 [US2] Implement microphone passthrough path excluding remote audio in `apps/macos/AudioDriver/Sources/Routing/MicrophoneRoute.cpp`.
- [ ] T036 [US2] Implement virtual speaker receive, physical output passthrough, and capture mirror path in `apps/macos/AudioDriver/Sources/Routing/SpeakerRoute.cpp`.
- [ ] T037 [US2] Implement track timing and continuity event emission in `apps/macos/AudioDriver/Sources/Timing/TrackClock.cpp`.
- [ ] T038 [US2] Implement desktop capture session state machine, `detecting` state, policy snapshot reference, and trigger evidence readiness hooks for audio-recording and transcript-only modes in `apps/macos/RecApp/Sources/Capture/CaptureSessionController.swift`.
- [ ] T039 [US2] Implement local encrypted buffer writer interface and degraded threshold states in `apps/macos/RecApp/Sources/Buffering/LocalBufferService.swift`.
- [ ] T040 [US2] Implement visible capture indicator and one-action stop state in `apps/macos/RecApp/Sources/Capture/CaptureStatusItem.swift`.
- [ ] T041 [US2] Implement missing-track degraded finalization rules in `apps/macos/RecApp/Sources/Capture/CaptureFinalizationService.swift`.
- [ ] T042 [US2] Update quickstart validation notes with US2 measured thresholds in `qa/macos/release-candidate-checklist.md`.

**Checkpoint**: User Story 2 is independently functional and validates separate capture plus passthrough integrity.

---

## Phase 5: User Story 3 - Recover From Driver, Permission, And Device Failures (Priority: P2)

**Goal**: Make driver, permission, physical device, route, server, network, and buffer failures visible, distinct, and recoverable.

**Independent Test**: Revoke permissions, switch/disconnect devices, restart the app and meeting target, simulate backend outage and buffer pressure, and confirm each state has a distinct diagnosis and recovery path.

### Tests for User Story 3

- [ ] T043 [P] [US3] Add permission denied/revoked scenario checklist in `tests/macos/physical-devices/permission-recovery.md`.
- [ ] T044 [P] [US3] Add physical device disconnect and Bluetooth profile switch checklist in `tests/macos/physical-devices/device-change-recovery.md`.
- [ ] T045 [P] [US3] Add local buffer pressure checklist in `tests/macos/physical-devices/local-buffer-pressure.md`.
- [ ] T046 [P] [US3] Add diagnostic redaction sample expectations for failure families in `tests/macos/installer-recovery/diagnostic-redaction.md`.

### Implementation for User Story 3

- [ ] T047 [US3] Implement Audio Health view model for driver, permission, physical device, route, meters, test recording, and playback states in `apps/macos/RecApp/Sources/AudioHealth/AudioHealthViewModel.swift`.
- [ ] T048 [US3] Implement Audio Health UI surface with accessible state labels and non-color cues in `apps/macos/RecApp/Sources/AudioHealth/AudioHealthView.swift`.
- [ ] T049 [US3] Implement permission and device-change monitors in `apps/macos/RecApp/Sources/AudioHealth/AudioEnvironmentMonitor.swift`.
- [ ] T050 [US3] Implement diagnostic bundle manifest generation with redaction status in `apps/macos/RecApp/Sources/Diagnostics/DiagnosticBundleService.swift`.
- [ ] T051 [US3] Implement app restart recovery and truthful local capture/buffer state reporting in `apps/macos/RecApp/Sources/Capture/CaptureRecoveryService.swift`.
- [ ] T052 [US3] Implement long-name-safe and best-effort status labels for devices, browsers, meetings, unsupported targets, and recovery actions in `apps/macos/RecApp/Sources/Shared/AdaptiveStatusText.swift`.

**Checkpoint**: User Story 3 is independently functional and validates explicit recoverability.

---

## Phase 6: User Story 4 - Uninstall Cleanly And Restore User Confidence (Priority: P3)

**Goal**: Remove app-managed virtual audio artifacts, attempt restoration of previous physical devices, and truthfully report manual cleanup or partial failure.

**Independent Test**: Install, select virtual devices, uninstall, confirm app-managed artifacts are removed where OS permits, prior physical devices are restored when possible, and remaining cleanup is explicitly reported.

### Tests for User Story 4

- [ ] T053 [P] [US4] Add uninstall and reinstall acceptance checklist in `tests/macos/installer-recovery/uninstall-reinstall.md`.
- [ ] T054 [P] [US4] Add active-call update deferral checklist in `tests/macos/installer-recovery/active-call-update-deferral.md`.
- [ ] T055 [P] [US4] Add rollback and partial cleanup checklist in `tests/macos/installer-recovery/rollback-partial-cleanup.md`.

### Implementation for User Story 4

- [ ] T056 [US4] Implement installer update deferral state when capture is active in `apps/macos/Installer/Scripts/update-preflight.sh`.
- [ ] T057 [US4] Implement rollback and repair script skeletons in `apps/macos/Installer/Scripts/rollback.sh` and `apps/macos/Installer/Scripts/repair.sh`.
- [ ] T058 [US4] Implement uninstall cleanup and manual remediation reporting in `apps/macos/Installer/Scripts/uninstall.sh`.
- [ ] T059 [US4] Implement previous physical device restoration attempt in `apps/macos/RecApp/Sources/Installer/AudioDeviceRestorationService.swift`.
- [ ] T060 [US4] Implement uninstall result UI copy and state mapping in `apps/macos/RecApp/Sources/Installer/UninstallResultView.swift`.

**Checkpoint**: User Story 4 is independently functional and validates clean recovery/removal.

---

## Final Phase: Polish & Cross-Cutting Concerns

**Purpose**: Final gates that affect multiple stories before private-alpha release candidate.

- [ ] T061 [P] Update macOS architecture notes with final implementation decisions in `apps/macos/README.md`.
- [ ] T062 [P] Update release-candidate checklist with all quickstart scenarios in `qa/macos/release-candidate-checklist.md`.
- [ ] T063 Run all requirement-quality checklists and record final status in `specs/001-macos-audio-driver/checklists/`.
- [ ] T064 Run quickstart validation scenarios and record outcomes in `qa/macos/release-candidate-checklist.md`.
- [ ] T065 Run `$speckit-analyze` and resolve critical/high findings in `specs/001-macos-audio-driver/`.
- [ ] T066 Verify no secrets, tokens, signed URLs, raw transcript text, or raw audio appear in committed files under `apps/macos/`, `tests/macos/`, `qa/macos/`, and `specs/001-macos-audio-driver/`.
- [ ] T067 Verify UI changes pass visible-state, accessibility, localization-safety, and brand-distance gates in `qa/macos/release-candidate-checklist.md`.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies.
- **Foundational (Phase 2)**: Depends on Setup completion and blocks all user stories.
- **User Story 1 (Phase 3)**: Depends on Foundational and is the MVP setup/readiness slice.
- **User Story 2 (Phase 4)**: Depends on Foundational; can start after US1 interfaces exist, but remains independently testable through browser meeting validation.
- **User Story 3 (Phase 5)**: Depends on Foundational and can run in parallel with US2 after shared state models exist.
- **User Story 4 (Phase 6)**: Depends on installer foundations and can run after US1 installer skeleton exists.
- **Final Phase**: Depends on all desired stories for the release candidate.

### User Story Dependencies

- **US1**: No dependency on other user stories.
- **US2**: Uses route/device foundations and benefits from US1 onboarding, but validation is independent.
- **US3**: Uses route/capture state from US1/US2, but failure surfaces can be tested independently with simulated states.
- **US4**: Uses installer state from US1 and capture-active state from US2 for update deferral.

### Parallel Opportunities

- Setup tasks T003-T006 can run in parallel after T001.
- Foundational fixture/model tasks T008-T010 can run in parallel after T007.
- US1 test tasks T019-T022 can run in parallel.
- US2 test tasks T031-T034 can run in parallel.
- US3 test tasks T043-T046 can run in parallel.
- US4 test tasks T053-T055 can run in parallel.
- Final documentation tasks T061-T062 can run in parallel.

---

## Parallel Example: User Story 2

```text
Task: "T031 [US2] Add remote-to-mic loopback detection test harness in tests/macos/route-synthetic/no-loopback-check.swift"
Task: "T032 [US2] Add track alignment and dropped-frame test harness in tests/macos/physical-devices/track-integrity-check.swift"
Task: "T033 [US2] Add browser meeting QA script for Chrome, Opera, Yandex Browser, and Yandex Telemost in tests/macos/browser-meetings/browser-meeting-matrix.md"
Task: "T034 [US2] Add network/server outage acceptance scenario in tests/macos/browser-meetings/offline-passthrough.md"
```

---

## Implementation Strategy

### MVP First

1. Complete Setup and Foundational phases.
2. Complete US1 and validate install plus route readiness.
3. Complete US2 and validate separate tracks plus passthrough integrity.
4. Stop before private-alpha RC if US1 or US2 fails route, loopback, visible-control, or diagnostic redaction gates.

### Incremental Delivery

1. US1 proves installation and readiness.
2. US2 proves capture integrity.
3. US3 makes failures recoverable.
4. US4 makes removal and rollback trustworthy.

### Required Gates Before Implementation Is Considered Complete

- All tasks for selected stories are marked `[x]`.
- Quickstart scenarios have recorded outcomes in `qa/macos/release-candidate-checklist.md`.
- `$speckit-analyze` has no critical blockers.
- Requirement-quality checklists remain complete.
- No committed artifact contains secrets, tokens, signed URLs, raw transcript text, or raw audio.
