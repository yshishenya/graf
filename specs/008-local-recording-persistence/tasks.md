# Tasks: Local Recording Persistence

**Input**: Design documents from `specs/008-local-recording-persistence/`

**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md), [data-model.md](data-model.md), [contracts/](contracts/), [quickstart.md](quickstart.md)

**Tests**: Tests are required because this feature creates local meeting-content artifacts, touches recording state, reads shared audio buffers, and must preserve realtime safety and metadata-only diagnostics.

**Organization**: Tasks are grouped by independently testable user story and ordered so the first implemented slice produces a discoverable local recording after `Stop`.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel because it touches different files and has no dependency on incomplete tasks.
- **[Story]**: Maps to user stories from [spec.md](spec.md).
- Every task includes an exact target path.

## Phase 1: Setup

**Purpose**: Add fixtures, QA evidence files, and validation entry points.

- [X] T001 Create local recording smoke evidence document in `tests/macos/local-recording/local-recording-smoke.md`.
- [X] T002 Create QA gate document in `qa/macos/local-recording-persistence.md`.
- [X] T003 Add validation script shell in `apps/macos/Scripts/validate-local-recording-persistence.sh`.
- [X] T004 Add local recording manifest contract fixture in `tests/macos/contract/local-recording-manifest.json`.

---

## Phase 2: Foundational Models And Contracts

**Purpose**: Add shared model and contract support required by all persistence stories.

- [X] T005 [P] Add local recording persistence states in `apps/macos/Shared/Sources/Models/AudioStates.swift`.
- [X] T006 [P] Add local recording session, track, manifest, and evidence models in `apps/macos/Shared/Sources/Models/AudioModels.swift`.
- [X] T007 [P] Add local recording audit event names in `apps/macos/Shared/Sources/Audit/AuditEvents.swift`.
- [X] T008 Update contract validation for local recording manifest in `apps/macos/Shared/Tools/ContractValidation/main.swift`.

**Checkpoint**: Shared model layer can represent saved, degraded, failed, and metadata-only local recording artifacts.

---

## Phase 3: User Story 1 - Find The Recording After Stop (Priority: P1)

**Goal**: User can stop a valid manual recording and see where local recording artifacts were saved.

**Independent Test**: Start a short local recording, stop it, confirm the UI shows a local recording location, and confirm manifest plus non-empty track artifact exists.

### Tests for User Story 1

- [X] T009 [P] [US1] Add local recording store tests in `apps/macos/Shared/Tests/LocalRecordingStoreTests.swift`.
- [X] T010 [P] [US1] Add local writer lifecycle tests in `apps/macos/Shared/Tests/LocalRecordingWriterTests.swift`.
- [X] T011 [P] [US1] Add manifest serialization tests in `apps/macos/Shared/Tests/LocalRecordingManifestTests.swift`.

### Implementation for User Story 1

- [X] T012 [US1] Implement app-owned local recording directory store in `apps/macos/RecApp/Sources/Capture/LocalRecordingStore.swift`.
- [X] T013 [US1] Implement local recording manifest service in `apps/macos/RecApp/Sources/Capture/LocalRecordingManifestService.swift`.
- [X] T014 [US1] Implement non-realtime local recording writer in `apps/macos/RecApp/Sources/Capture/LocalRecordingWriter.swift`.
- [X] T015 [US1] Wire local writer start/stop into manual recording flow in `apps/macos/RecApp/App/TwoBrainRecApp.swift`.
- [X] T016 [US1] Show saved local recording location in `apps/macos/RecApp/Sources/Capture/CaptureControlView.swift`.

**Checkpoint**: Manual `Record`/`Stop` produces a discoverable local recording artifact.

---

## Phase 4: User Story 2 - Preserve Recording Truth When A Track Is Missing (Priority: P1)

**Goal**: Missing or failed required tracks are marked degraded/failed and never shown as complete saved recordings.

**Independent Test**: Simulate missing remote speaker frames or write failure and confirm degraded/failed status, concrete reason, and no complete acceptance.

### Tests for User Story 2

- [X] T017 [P] [US2] Add missing-track finalization tests in `apps/macos/Shared/Tests/LocalRecordingManifestTests.swift`.
- [X] T018 [P] [US2] Add writer failure tests in `apps/macos/Shared/Tests/LocalRecordingWriterTests.swift`.

### Implementation for User Story 2

- [X] T019 [US2] Add track-level degraded and failed finalization in `apps/macos/RecApp/Sources/Capture/LocalRecordingManifestService.swift`.
- [X] T020 [US2] Block or fail closed when local recording directory is unavailable in `apps/macos/RecApp/App/TwoBrainRecApp.swift`.
- [X] T021 [US2] Surface saved, degraded, and failed copy in `apps/macos/RecApp/Sources/Capture/CaptureControlView.swift`.
- [X] T022 [US2] Preserve non-recording passthrough after local writer stop in `apps/macos/RecApp/Sources/Capture/PassthroughBridge.swift` or document no code change in `qa/macos/local-recording-persistence.md`.

**Checkpoint**: Partial recordings are truthful and cannot be mistaken for complete acceptance.

---

## Phase 5: User Story 3 - Keep Local Recording Evidence Metadata-Only (Priority: P2)

**Goal**: Diagnostics and QA can prove local artifact creation without leaking content or sensitive paths.

**Independent Test**: Generate local recording diagnostic evidence and verify safe ids, basenames, statuses, byte counts, and durations are present while raw content and live paths are absent.

### Tests for User Story 3

- [X] T023 [P] [US3] Add local recording diagnostic redaction tests in `apps/macos/Shared/Tests/DiagnosticRedactionTests.swift`.
- [X] T024 [P] [US3] Add local recording evidence tests in `apps/macos/Shared/Tests/RecordingEvidenceTests.swift`.

### Implementation for User Story 3

- [X] T025 [US3] Add local recording evidence generation in `apps/macos/RecApp/Sources/Capture/RecordingEvidenceService.swift`.
- [X] T026 [US3] Add diagnostic bundle support for local recording manifests in `apps/macos/RecApp/Sources/Diagnostics/DiagnosticBundleService.swift`.
- [X] T027 [US3] Extend diagnostic redactor safe allowlist for local recording metadata in `apps/macos/Shared/Sources/Diagnostics/DiagnosticRedactor.swift`.
- [X] T028 [US3] Record local recording saved/degraded/failed audit events in `apps/macos/RecApp/App/TwoBrainRecApp.swift`.

**Checkpoint**: Evidence proves local recording status without content leakage.

---

## Final Phase: Polish And Validation

**Purpose**: Validate the complete 008 feature and update evidence.

- [X] T029 Run Swift package tests and record result in `qa/macos/local-recording-persistence.md`.
- [X] T030 Run contract validation and record result in `qa/macos/local-recording-persistence.md`.
- [X] T031 Run realtime safety scan and record result in `qa/macos/local-recording-persistence.md`.
- [X] T032 Run `apps/macos/Scripts/validate-local-recording-persistence.sh` and record result in `qa/macos/local-recording-persistence.md`.
- [X] T033 Update release-candidate checklist with 008 status in `qa/macos/release-candidate-checklist.md`.
- [X] T034 Verify diagnostics contain no raw audio, transcript text, meeting content, credentials, tokens, signed URLs, passwords, or live secret paths in `qa/macos/local-recording-persistence.md`.
- [X] T035 Rebuild and launch local app bundle in `apps/macos/RecApp/.build/2brain Rec.app`.
- [X] T036 Mark completed tasks in `specs/008-local-recording-persistence/tasks.md`.

---

## Dependencies & Execution Order

1. Phase 1 setup must complete before contract validation.
2. Phase 2 foundational models must complete before user story implementation.
3. US1 and US2 are both P1. US1 creates files; US2 prevents false success.
4. US3 depends on the local manifest and track models from US1/US2.
5. Final validation runs after all user story phases.

## Parallel Execution Examples

- T005, T006, and T007 can run in parallel because they touch separate shared files.
- T009, T010, and T011 can run in parallel before US1 implementation.
- T017 and T018 can run in parallel before US2 implementation.
- T023 and T024 can run in parallel before US3 implementation.

## Implementation Strategy

MVP first: complete US1 and US2 together so pressing `Record` creates a local
recording artifact and incomplete recordings are truthful. Then add US3 evidence
and validation. Do not add upload, transcription, dashboard, retention,
deletion, encryption, or assisted auto-start in this feature.
