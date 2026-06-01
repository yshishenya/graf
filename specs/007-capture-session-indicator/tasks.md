# Tasks: Manual Capture Session And Visible Indicator

**Input**: Design documents from `specs/007-capture-session-indicator/`

**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md), [data-model.md](data-model.md), [contracts/](contracts/), [quickstart.md](quickstart.md)

**Tests**: Tests are required because the feature touches recording start/stop behavior, visible capture indication, privacy boundaries, diagnostics redaction, and driver route safety.

**Organization**: Tasks are grouped by independently testable user story and ordered so manual recording can be validated without upload, transcription, or dashboard work.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel because it touches different files and has no dependency on incomplete tasks.
- **[Story]**: Maps to user stories from [spec.md](spec.md).
- Every task includes an exact target path.

## Phase 1: Setup

**Purpose**: Add feature evidence scaffolding and validation entry points.

- [X] T001 Create manual recording smoke evidence document in `tests/macos/browser-meetings/manual-recording-smoke.md`.
- [X] T002 Create QA gate document in `qa/macos/capture-session-indicator.md`.
- [X] T003 Add capture-session validation script shell in `apps/macos/Scripts/validate-capture-session-indicator.sh`.

---

## Phase 2: Foundational Models And Contracts

**Purpose**: Add shared model and contract support required by all recording stories.

- [X] T004 [P] Add recording prerequisite states and failure categories in `apps/macos/Shared/Sources/Models/AudioStates.swift`.
- [X] T005 [P] Extend capture session and add recording evidence models in `apps/macos/Shared/Sources/Models/AudioModels.swift`.
- [X] T006 [P] Add recording audit event names in `apps/macos/Shared/Sources/Audit/AuditEvents.swift`.
- [X] T007 Add contract validation fixtures for recording evidence in `tests/macos/contract/recording-session-evidence.json`.
- [X] T008 Update contract validation checks for recording evidence in `apps/macos/Shared/Tools/ContractValidation/main.swift`.

**Checkpoint**: Shared model layer can represent manual recording lifecycle, blockers, indicator state, and metadata-only evidence.

---

## Phase 3: User Story 1 - Start And Stop Manual Recording Safely (Priority: P1)

**Goal**: User can explicitly start recording only from valid route prerequisites and stop it in one action without upload/transcription.

**Independent Test**: Start from valid low-resource route, press Record, observe active recording, press Stop once, and confirm stopped state plus no external egress.

### Tests for User Story 1

- [X] T009 [P] [US1] Add start/stop transition tests in `apps/macos/Shared/Tests/CaptureControlTests.swift`.
- [X] T010 [P] [US1] Add prerequisite gate tests in `apps/macos/Shared/Tests/RecordingPrerequisiteGateTests.swift`.

### Implementation for User Story 1

- [X] T011 [US1] Implement recording prerequisite gate in `apps/macos/RecApp/Sources/Capture/RecordingPrerequisiteGate.swift`.
- [X] T012 [US1] Extend capture session controller with manual start/stop blocker handling in `apps/macos/RecApp/Sources/Capture/CaptureSessionController.swift`.
- [X] T013 [US1] Wire Record/Stop controls into the app shell in `apps/macos/RecApp/App/TwoBrainRecApp.swift`.
- [X] T014 [US1] Update capture control view for Record, Stop, blocked, starting, active, stopping, and stopped states in `apps/macos/RecApp/Sources/Capture/CaptureControlView.swift`.
- [X] T015 [US1] Preserve non-recording passthrough after stop in `apps/macos/RecApp/Sources/Capture/PassthroughRouteEngine.swift` or document no code change in `qa/macos/capture-session-indicator.md`.

**Checkpoint**: Manual start and one-action stop work locally without upload, transcription, MediaScribe, Langfuse, or dashboard activity.

---

## Phase 4: User Story 2 - Keep Active Capture Always Visible And Controllable (Priority: P1)

**Goal**: Every active recording has persistent visible local indication and one-action stop; invisible recording fails closed.

**Independent Test**: Start recording, close/background main window, verify a visible local indicator remains or recording stops/fails closed.

### Tests for User Story 2

- [X] T016 [P] [US2] Add visible indicator safety tests in `apps/macos/Shared/Tests/CaptureSessionSafetyTests.swift`.
- [X] T017 [P] [US2] Add capture status item accessibility/label tests in `apps/macos/Shared/Tests/CaptureIndicatorTests.swift`.

### Implementation for User Story 2

- [X] T018 [US2] Strengthen active-state visible stop validation in `apps/macos/Shared/Sources/Models/CaptureSessionSafetyValidator.swift`.
- [X] T019 [US2] Update capture status item copy, icons, accessibility labels, and stop affordance in `apps/macos/RecApp/Sources/Capture/CaptureStatusItem.swift`.
- [X] T020 [US2] Add fail-closed handling for visible-indicator loss in `apps/macos/RecApp/Sources/Capture/CaptureRecoveryService.swift`.
- [X] T021 [US2] Surface persistent capture status in the app layout in `apps/macos/RecApp/App/TwoBrainRecApp.swift`.

**Checkpoint**: Active recording cannot continue with hidden/unavailable visible indicators.

---

## Phase 5: User Story 3 - Preserve Honest Local Recording Evidence (Priority: P2)

**Goal**: Recording start, stop, blockers, failures, and indicator state generate metadata-only evidence.

**Independent Test**: Start/stop a short session and inspect local evidence bundle without meeting content or secrets.

### Tests for User Story 3

- [X] T022 [P] [US3] Add recording evidence model tests in `apps/macos/Shared/Tests/RecordingEvidenceTests.swift`.
- [X] T023 [P] [US3] Extend diagnostic redaction tests for recording evidence in `apps/macos/Shared/Tests/DiagnosticRedactionTests.swift`.

### Implementation for User Story 3

- [X] T024 [US3] Implement recording evidence service in `apps/macos/RecApp/Sources/Capture/RecordingEvidenceService.swift`.
- [X] T025 [US3] Add recording evidence diagnostic bundle support in `apps/macos/RecApp/Sources/Diagnostics/DiagnosticBundleService.swift`.
- [X] T026 [US3] Emit recording lifecycle evidence from controller/app actions in `apps/macos/RecApp/Sources/Capture/CaptureSessionController.swift` and `apps/macos/RecApp/App/TwoBrainRecApp.swift`.
- [X] T027 [US3] Update diagnostic redactor allowlist for safe recording evidence fields in `apps/macos/Shared/Sources/Diagnostics/DiagnosticRedactor.swift`.

**Checkpoint**: Recording evidence is complete enough for QA and remains metadata-only.

---

## Phase 6: User Story 4 - Block Unsafe Or Policy-Disallowed Recording (Priority: P2)

**Goal**: Unsafe recording starts are blocked before capture begins with concrete reason and recovery copy.

**Independent Test**: Simulate stale route, policy disabled, permission missing, storage pressure, and indicator unavailable; each case blocks start with evidence.

### Tests for User Story 4

- [X] T028 [P] [US4] Add blocked-start tests for policy, route, storage, permission, and indicator prerequisites in `apps/macos/Shared/Tests/RecordingPrerequisiteGateTests.swift`.
- [X] T029 [P] [US4] Add blocked-start diagnostic bundle tests in `apps/macos/Shared/Tests/RecordingEvidenceTests.swift`.

### Implementation for User Story 4

- [X] T030 [US4] Connect route, policy, permission, storage, and indicator prerequisite snapshot inputs in `apps/macos/RecApp/Sources/Capture/RecordingPrerequisiteGate.swift`.
- [X] T031 [US4] Add blocked-start user-facing copy and recovery actions in `apps/macos/RecApp/Sources/Capture/CaptureControlView.swift`.
- [X] T032 [US4] Record blocked-start audit/evidence events in `apps/macos/RecApp/Sources/Capture/RecordingEvidenceService.swift`.

**Checkpoint**: No invalid route/policy/permission/storage/indicator case can start recording.

---

## Final Phase: Polish And Validation

**Purpose**: Validate the complete 007 feature and update evidence.

- [X] T033 Run Swift package tests and record result in `qa/macos/capture-session-indicator.md`.
- [X] T034 Run contract validation and record result in `qa/macos/capture-session-indicator.md`.
- [X] T035 Run realtime safety scan and record result in `qa/macos/capture-session-indicator.md`.
- [X] T036 Run `apps/macos/Scripts/validate-capture-session-indicator.sh` and record result in `qa/macos/capture-session-indicator.md`.
- [X] T037 Update release-candidate checklist with 007 status in `qa/macos/release-candidate-checklist.md`.
- [X] T038 Verify diagnostics contain no raw audio, transcript text, meeting content, credentials, tokens, signed URLs, passwords, or live secret paths across `apps/macos/`, `tests/macos/`, `qa/macos/`, and `specs/007-capture-session-indicator/`.
- [X] T039 Mark completed tasks in `specs/007-capture-session-indicator/tasks.md`.

---

## Dependencies & Execution Order

1. Phase 1 setup must complete before model/contract work.
2. Phase 2 foundational models must complete before user story implementation.
3. US1 and US2 are both P1. US1 can start first; US2 must complete before any recording acceptance claim.
4. US3 depends on US1 model/controller state.
5. US4 depends on the prerequisite gate introduced by US1.
6. Final validation runs after all user story phases.

## Parallel Execution Examples

- T004, T005, and T006 can run in parallel because they touch separate shared files.
- T009 and T010 can run in parallel before US1 implementation.
- T016 and T017 can run in parallel before US2 implementation.
- T022 and T023 can run in parallel before US3 implementation.
- T028 and T029 can run in parallel before US4 implementation.

## Implementation Strategy

MVP first: complete US1 and US2 together so recording can only ship when manual
start/stop and visible one-action stop both work. Then add US3 evidence and US4
blocked-start coverage. Do not add upload, transcription, dashboard, retention,
deletion, or assisted auto-start in this feature.
