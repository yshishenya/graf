# Tasks: macOS Virtual Audio Driver MVP

**Input**: Design documents from `specs/001-macos-audio-driver/`

**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md), [data-model.md](data-model.md), [contracts/](contracts/), [quickstart.md](quickstart.md)

**Tests**: Test and QA tasks are required because the specification defines route verification, long-run audio integrity, installer recovery, diagnostic redaction, and browser/device matrix success criteria.

**Organization**: Tasks are grouped by user story so each story can be implemented and validated independently after shared foundations are complete.

## Reality Alignment (2026-06-01)

Current accepted runtime evidence proves macOS Core Audio publication,
low-resource default-safe behavior, and non-recording bidirectional passthrough
smoke for the current local development build:

- the local installer can deploy the app and HAL driver for development use;
- `2brain Rec Microphone` and `2brain Rec Speaker` are visible to macOS;
- idle runtime proof reports both virtual devices visible/alive and non-running;
- physical routes are opened on virtual-device client I/O or explicit recheck,
  not eagerly on app launch;
- Telemost, Chrome, Opera, and Zoom manual smoke passed without starting
  recording, transcription, upload, MediaScribe, or Langfuse activity.

The release-critical recording path is still open:

- separate local/remote capture tracks are not accepted;
- 30/60 minute recorded track integrity is not accepted;
- active recording indicator/one-action stop still needs a dedicated feature;
- backend upload/transcription/dashboard/retention/deletion are not part of
  this closed audio-route slice.

Tasks marked complete before this alignment may represent scaffolding,
contracts, or synthetic validation. Release acceptance still requires the open
runtime passthrough tasks below plus the release-candidate checklist evidence.

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
- [X] T011 Create the desktop-driver contract validator scaffold in `apps/macos/Shared/TestPlans/ContractValidationPlan.swift`.
- [X] T012 Create the diagnostics redaction validator scaffold in `apps/macos/Shared/TestPlans/ContractValidationPlan.swift`.
- [X] T013 Create a scaffold for the Phase 0 virtual-device proof harness for `2brain Rec Microphone` and `2brain Rec Speaker` in `apps/macos/AudioDriver/Sources/Proof/VirtualDeviceProof.cpp`.
- [X] T014 Create a scaffold for the passthrough and mirror timing proof harness in `apps/macos/AudioDriver/Sources/Proof/PassthroughTimingProof.cpp`.
- [X] T015 Document the current scaffolded Phase 0 proof status, selected implementation path, and remaining runtime proof gate in `apps/macos/AudioDriver/README.md`.
- [X] T016 Create local diagnostic redaction utilities in `apps/macos/Shared/Sources/Diagnostics/DiagnosticRedactor.swift`.
- [X] T017 Create local encrypted buffer interface definitions without upload implementation in `apps/macos/Shared/Sources/Buffering/LocalBufferContracts.swift`.
- [X] T018 Create audit event name definitions for driver and capture lifecycle events in `apps/macos/Shared/Sources/Audit/AuditEvents.swift`.

**Checkpoint**: Foundation scaffold ready - contracts, shared models, redaction policy, local buffer boundaries, and proof scaffolds exist. Runtime Core Audio proof remains blocking before any US1 task that publishes real virtual devices or installer behavior.

---

## Phase 2.5: Blocking Remediation Gate Before US1

**Purpose**: Close review findings before the first user-story implementation. IDs continue after the generated task list to preserve traceability for existing T019-T067 references.

**CRITICAL**: US1 implementation tasks T023-T030 MUST NOT start until T068-T077 are complete and `apps/macos/AudioDriver/RuntimeProofReport.md` records an `ACCEPTED` Core Audio publication result. Execution order follows document order, not numeric ID order.

- [X] T068 Add an executable SwiftPM contract validation command in `apps/macos/Shared/Tools/ContractValidation/main.swift`.
- [X] T069 Complete desktop-driver fixture coverage for all required events in `tests/macos/contract/desktop-driver-events.json`.
- [X] T070 Add a reproducible proof-only C++ build/run command in `apps/macos/AudioDriver/Makefile`.
- [X] T071 Add an explicit macOS 14.5 Apple Silicon support gate model in `apps/macos/Shared/Sources/Models/PlatformSupport.swift`.
- [X] T072 Run the runtime Core Audio visibility probe on Apple Silicon macOS and record the observed BLOCKED result in `apps/macos/AudioDriver/RuntimeProofReport.md`.
- [X] T073 Add a capture visibility and one-action stop invariant validator in `apps/macos/Shared/Sources/Models/CaptureSessionSafetyValidator.swift`.
- [X] T074 Add baseline key/value forbidden-pattern diagnostic redaction coverage in `apps/macos/Shared/Sources/Diagnostics/DiagnosticRedactor.swift`.
- [X] T075 Extend diagnostic redaction to recursive/schema allowlist behavior before diagnostic bundle implementation in `apps/macos/RecApp/Sources/Diagnostics/DiagnosticBundleService.swift`.
- [X] T076 Add local validation scripts for foundation and US1 readiness gates in `apps/macos/Scripts/validate-foundation.sh` and `apps/macos/Scripts/validate-us1-gate.sh`.
- [X] T077 Produce an ACCEPTED runtime Core Audio publication proof with both MVP virtual devices visible to macOS in `apps/macos/AudioDriver/RuntimeProofReport.md`.

---

## Phase 3: User Story 1 - Complete Driver Setup And Route Verification (Priority: P1) MVP

**Goal**: Install the macOS audio layer, expose both virtual devices, select physical devices, and show `ready` only after valid mic and speaker route verification.

**Independent Test**: Install on a supported Apple Silicon Mac, grant permissions, verify both virtual devices appear, select physical input/output, complete route verification, and confirm `ready` is blocked until both paths pass.

### Tests for User Story 1

- [X] T019 [P] [US1] Add contract tests for route verification state transitions in `apps/macos/Shared/Tests/RouteVerificationTests.swift`.
- [X] T020 [P] [US1] Add synthetic mic route QA harness in `tests/macos/route-synthetic/mic-route-check.swift`.
- [X] T021 [P] [US1] Add synthetic speaker route QA harness in `tests/macos/route-synthetic/speaker-route-check.swift`.
- [X] T022 [P] [US1] Add installer smoke test checklist for fresh install and restart-required states in `tests/macos/installer-recovery/fresh-install.md`.

### Implementation for User Story 1

- [X] T023 [US1] Implement virtual device publication wrapper for `2brain Rec Microphone` and `2brain Rec Speaker` in `apps/macos/AudioDriver/Sources/Device/VirtualDeviceRegistry.cpp`.
- [X] T024 [US1] Implement self-routing detection and rejection in `apps/macos/Shared/Sources/Routing/SelfRoutingGuard.swift`.
- [X] T025 [US1] Implement physical input/output selection state in `apps/macos/RecApp/Sources/AudioSetup/PhysicalDeviceSelectionViewModel.swift`.
- [X] T026 [US1] Implement mic and speaker route verification orchestration in `apps/macos/RecApp/Sources/AudioSetup/RouteVerificationService.swift`.
- [X] T027 [US1] Implement onboarding route verification UI state in `apps/macos/RecApp/Sources/AudioSetup/RouteVerificationView.swift`.
- [X] T028 [US1] Implement driver install, permission, and virtual-device status surface in `apps/macos/RecApp/Sources/AudioSetup/DriverSetupView.swift`.
- [X] T029 [US1] Implement interactive signed/notarized installer package definition for install and repair flows in `apps/macos/Installer/Packages/2brain-rec.pkgproj`.
- [X] T030 [US1] Update QA browser/device matrix with US1 route verification acceptance coverage in `qa/macos/device-matrix.md` and `qa/macos/browser-targets.md`.

**Checkpoint**: User Story 1 publishes the required virtual devices and exposes
the readiness surface. Full route readiness remains blocked until live audio
passthrough is implemented and verified.

---

## Phase 4: User Story 2 - Capture Separate Tracks Without Breaking The Call (Priority: P1)

**Goal**: Capture local mic and remote speaker audio as separate aligned tracks while live mic/speaker passthrough remains usable during network or server failure.

**Independent Test**: Join a supported browser meeting using both virtual devices, record for 30 minutes, verify separate local/remote tracks, no remote-to-mic loopback, and stable passthrough during a 5-minute outage.

### Tests for User Story 2

- [X] T031 [P] [US2] Add remote-to-mic loopback detection test harness in `tests/macos/route-synthetic/no-loopback-check.swift`.
- [X] T032 [P] [US2] Add track alignment and dropped-frame test harness in `tests/macos/physical-devices/track-integrity-check.swift`.
- [X] T033 [P] [US2] Add browser meeting QA script for Chrome, Opera, Yandex Browser, and Yandex Telemost in `tests/macos/browser-meetings/browser-meeting-matrix.md`.
- [X] T034 [P] [US2] Add network/server outage acceptance scenario in `tests/macos/browser-meetings/offline-passthrough.md`.

### Implementation for User Story 2

- [X] T035 [US2] Implement and wire live microphone passthrough excluding remote audio in `apps/macos/AudioDriver/Sources/Routing/MicrophoneRoute.cpp` and `apps/macos/AudioDriver/Sources/Plugin/TwoBrainRecProofDriver.cpp`.
- [X] T036 [US2] Implement and wire live virtual speaker receive, physical output passthrough, and capture mirror path in `apps/macos/AudioDriver/Sources/Routing/SpeakerRoute.cpp` and `apps/macos/AudioDriver/Sources/Plugin/TwoBrainRecProofDriver.cpp`.
- [ ] T037 [US2] Implement runtime track timing and continuity event emission for the live driver path in `apps/macos/AudioDriver/Sources/Timing/TrackClock.cpp`.
- [X] T038 [US2] Implement desktop capture session state machine, `detecting` state, policy snapshot reference, and trigger evidence readiness hooks for audio-recording and transcript-only modes in `apps/macos/RecApp/Sources/Capture/CaptureSessionController.swift`.
- [X] T039 [US2] Implement local encrypted buffer writer interface and degraded threshold states in `apps/macos/RecApp/Sources/Buffering/LocalBufferService.swift`.
- [X] T040 [US2] Implement visible capture indicator and one-action stop state in `apps/macos/RecApp/Sources/Capture/CaptureStatusItem.swift`.
- [X] T041 [US2] Implement missing-track degraded finalization rules in `apps/macos/RecApp/Sources/Capture/CaptureFinalizationService.swift`.
- [X] T042 [US2] Update quickstart validation notes with US2 measured thresholds in `qa/macos/release-candidate-checklist.md`.

### Runtime Acceptance Gap for User Story 2

- [X] T078 [US2] Wire AudioServerPlugIn `StartIO` and `StopIO` to the physical-device bridge without starting hidden capture in `apps/macos/AudioDriver/Sources/Plugin/TwoBrainRecProofDriver.cpp`.
- [X] T079 [US2] Add a user-triggered passthrough readiness probe that never reports ready from device visibility alone in `apps/macos/RecApp/App/TwoBrainRecApp.swift` and `apps/macos/RecApp/Sources/Capture/PassthroughBridge.swift`.
- [X] T080 [US2] Add real runtime passthrough proof commands and failure diagnostics in `apps/macos/AudioDriver/Makefile` and `apps/macos/AudioDriver/RuntimeProofReport.md`.
- [X] T081 [US2] Record browser meeting validation evidence for Chrome, Opera, Yandex Browser, and Yandex Telemost in `tests/macos/browser-meetings/browser-meeting-matrix.md` and `qa/macos/release-candidate-checklist.md`.
- [ ] T082 [US2] Record 30-minute track integrity and 5-minute outage evidence in `tests/macos/physical-devices/track-integrity-check.swift` and `qa/macos/release-candidate-checklist.md`.
- [X] T083 [US1] Disable high-frequency proof-driver callback trace by default and prevent publication-only virtual devices from becoming system defaults in `apps/macos/AudioDriver/Sources/Plugin/TwoBrainRecProofDriver.cpp` and `apps/macos/AudioDriver/Makefile`.

**Checkpoint**: The non-recording passthrough portion of User Story 2 is
accepted for local smoke coverage. User Story 2 is not production complete until
T037 and T082 close the durable recorded-track timing/continuity and long-run
evidence.

---

## Phase 5: User Story 3 - Recover From Driver, Permission, And Device Failures (Priority: P2)

**Goal**: Make driver, permission, physical device, route, server, network, and buffer failures visible, distinct, and recoverable.

**Independent Test**: Revoke permissions, switch/disconnect devices, restart the app and meeting target, simulate backend outage and buffer pressure, and confirm each state has a distinct diagnosis and recovery path.

### Tests for User Story 3

- [X] T043 [P] [US3] Add permission denied/revoked scenario checklist in `tests/macos/physical-devices/permission-recovery.md`.
- [X] T044 [P] [US3] Add physical device disconnect and Bluetooth profile switch checklist in `tests/macos/physical-devices/device-change-recovery.md`.
- [X] T045 [P] [US3] Add local buffer pressure checklist in `tests/macos/physical-devices/local-buffer-pressure.md`.
- [X] T046 [P] [US3] Add diagnostic redaction sample expectations for failure families in `tests/macos/installer-recovery/diagnostic-redaction.md`.

### Implementation for User Story 3

- [X] T047 [US3] Implement Audio Health view model for driver, permission, physical device, route, meters, test recording, and playback states in `apps/macos/RecApp/Sources/AudioHealth/AudioHealthViewModel.swift`.
- [X] T048 [US3] Implement Audio Health UI surface with accessible state labels and non-color cues in `apps/macos/RecApp/Sources/AudioHealth/AudioHealthView.swift`.
- [X] T049 [US3] Implement permission and device-change monitors in `apps/macos/RecApp/Sources/AudioHealth/AudioEnvironmentMonitor.swift`.
- [X] T050 [US3] Implement diagnostic bundle manifest generation with redaction status in `apps/macos/RecApp/Sources/Diagnostics/DiagnosticBundleService.swift`.
- [X] T051 [US3] Implement app restart recovery and truthful local capture/buffer state reporting in `apps/macos/RecApp/Sources/Capture/CaptureRecoveryService.swift`.
- [X] T052 [US3] Implement long-name-safe and best-effort status labels for devices, browsers, meetings, unsupported targets, and recovery actions in `apps/macos/RecApp/Sources/Shared/AdaptiveStatusText.swift`.

**Checkpoint**: User Story 3 is independently functional and validates explicit recoverability.

---

## Phase 6: User Story 4 - Uninstall Cleanly And Restore User Confidence (Priority: P3)

**Goal**: Remove app-managed virtual audio artifacts, attempt restoration of previous physical devices, and truthfully report manual cleanup or partial failure.

**Independent Test**: Install, select virtual devices, uninstall, confirm app-managed artifacts are removed where OS permits, prior physical devices are restored when possible, and remaining cleanup is explicitly reported.

### Tests for User Story 4

- [X] T053 [P] [US4] Add uninstall and reinstall acceptance checklist in `tests/macos/installer-recovery/uninstall-reinstall.md`.
- [X] T054 [P] [US4] Add active-call update deferral checklist in `tests/macos/installer-recovery/active-call-update-deferral.md`.
- [X] T055 [P] [US4] Add rollback and partial cleanup checklist in `tests/macos/installer-recovery/rollback-partial-cleanup.md`.

### Implementation for User Story 4

- [X] T056 [US4] Implement installer update deferral state when capture is active in `apps/macos/Installer/Scripts/update-preflight.sh`.
- [X] T057 [US4] Implement rollback and repair script skeletons in `apps/macos/Installer/Scripts/rollback.sh` and `apps/macos/Installer/Scripts/repair.sh`.
- [X] T058 [US4] Implement uninstall cleanup and manual remediation reporting in `apps/macos/Installer/Scripts/uninstall.sh`.
- [X] T059 [US4] Implement previous physical device restoration attempt in `apps/macos/RecApp/Sources/Installer/AudioDeviceRestorationService.swift`.
- [X] T060 [US4] Implement uninstall result UI copy and state mapping in `apps/macos/RecApp/Sources/Installer/UninstallResultView.swift`.

**Checkpoint**: User Story 4 is independently functional and validates clean recovery/removal.

---

## Final Phase: Polish & Cross-Cutting Concerns

**Purpose**: Final gates that affect multiple stories before production release candidate.

- [X] T061 [P] Update macOS architecture notes with final implementation decisions in `apps/macos/README.md`.
- [X] T062 [P] Update release-candidate checklist with all quickstart scenarios in `qa/macos/release-candidate-checklist.md`.
- [X] T063 Run all requirement-quality checklists and record final status in `specs/001-macos-audio-driver/checklists/`.
- [ ] T064 Run quickstart validation scenarios and record outcomes in `qa/macos/release-candidate-checklist.md`.
- [ ] T065 Run `$speckit-analyze` and resolve critical/high findings in `specs/001-macos-audio-driver/`.
- [X] T066 Verify no secrets, tokens, signed URLs, raw transcript text, or raw audio appear in committed files under `apps/macos/`, `tests/macos/`, `qa/macos/`, and `specs/001-macos-audio-driver/`.
- [ ] T067 Verify UI changes pass visible-state, accessibility, localization-safety, and brand-distance gates in `qa/macos/release-candidate-checklist.md`.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies.
- **Foundational (Phase 2)**: Depends on Setup completion and blocks all user stories.
- **Blocking Remediation Gate (Phase 2.5)**: Depends on Foundational and blocks US1 implementation tasks T023-T030 until T068-T077 are complete and `apps/macos/Scripts/validate-us1-gate.sh` passes.
- **User Story 1 (Phase 3)**: Depends on Foundational plus the Blocking Remediation Gate and is the MVP setup/readiness slice.
- **User Story 2 (Phase 4)**: Depends on Foundational; can start after US1 interfaces exist, but remains independently testable through browser meeting validation. As of 2026-05-31, T035-T037 and T078-T082 remain open and block US2 acceptance.
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
- Blocking remediation tasks T068-T071 can run in parallel after T018; T072 depends on T070 and an available Apple Silicon runtime environment; T077 depends on a working Core Audio publication implementation or installed proof component. T023-T030 remain blocked until `apps/macos/Scripts/validate-us1-gate.sh` passes.
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
2. Complete Blocking Remediation Gate tasks T068-T077.
3. Complete US1 publication/onboarding foundation and keep readiness blocked until live route evidence exists.
4. Complete US2 runtime acceptance gap tasks T078-T082 and validate separate tracks plus passthrough integrity.
5. Stop before production release candidate if US1 or US2 fails route, loopback, visible-control, or diagnostic redaction gates.

### Incremental Delivery

1. Blocking Remediation Gate proves the foundation is honest enough to start US1.
2. US1 proves installation, virtual-device visibility, and truthful readiness blocking.
3. US2 proves live passthrough and capture integrity.
4. US3 makes failures recoverable.
5. US4 makes removal and rollback trustworthy.

### Required Gates Before Implementation Is Considered Complete

- All tasks for selected stories are marked `[X]`.
- Quickstart scenarios have recorded outcomes in `qa/macos/release-candidate-checklist.md`.
- `$speckit-analyze` has no critical blockers.
- Requirement-quality checklists remain complete.
- No committed artifact contains secrets, tokens, signed URLs, raw transcript text, or raw audio.
