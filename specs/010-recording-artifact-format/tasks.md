# Tasks: Recording Artifact Format

**Input**: Design documents from `specs/010-recording-artifact-format/`

**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md), [data-model.md](data-model.md), [contracts/](contracts/), [quickstart.md](quickstart.md)

**Tests**: Tests are required because this feature changes local meeting-content artifacts, audio format, diagnostic metadata, and future MediaScribe boundary contracts.

**Organization**: Tasks are grouped by independently testable user story and ordered so the first implemented slice produces MediaScribe-ready local dual tracks after `Stop`.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel because it touches different files and has no dependency on incomplete tasks.
- **[Story]**: Maps to user stories from [spec.md](spec.md).
- Every task includes an exact target path.

## Phase 1: Setup

**Purpose**: Add fixtures, QA evidence files, and validation entry points.

- [X] T001 Create artifact-format QA gate document in `qa/macos/recording-artifact-format.md`.
- [X] T002 Create manual smoke evidence document in `tests/macos/local-recording/recording-artifact-format-smoke.md`.
- [X] T003 Add artifact format validation script shell in `apps/macos/Scripts/validate-recording-artifact-format.sh`.
- [X] T004 Add recording artifact format contract fixture in `tests/macos/contract/recording-artifact-format.json`.

---

## Phase 2: Foundational Models And Contracts

**Purpose**: Extend shared contracts required by all artifact-format stories.

- [X] T005 [P] Add transcription readiness and artifact-format failure states in `apps/macos/Shared/Sources/Models/AudioStates.swift`.
- [X] T006 [P] Extend local recording track and manifest metadata for MediaScribe-ready fields in `apps/macos/Shared/Sources/Models/AudioModels.swift`.
- [X] T007 Update local recording manifest fixture for schema/readiness fields in `tests/macos/contract/local-recording-manifest.json`.
- [X] T008 Update contract validation for recording artifact format in `apps/macos/Shared/Tools/ContractValidation/main.swift`.

**Checkpoint**: Shared model layer can represent MediaScribe-ready, degraded, failed, and legacy/not-ready local artifacts.

---

## Phase 3: User Story 1 - Save Transcription-Ready Dual Tracks (Priority: P1)

**Goal**: Manual `Record`/`Stop` produces `mic.wav` and `incoming.wav` ready for future MediaScribe dual-track submission.

**Independent Test**: Start a short local recording, stop it, inspect track headers, and confirm both files are WAV PCM signed 16-bit little-endian, mono, 16000 Hz with correct manifest role mapping.

### Tests for User Story 1

- [X] T009 [P] [US1] Add WAV header and format validation tests in `apps/macos/Shared/Tests/LocalRecordingWriterTests.swift`.
- [X] T010 [P] [US1] Add manifest role mapping tests in `apps/macos/Shared/Tests/LocalRecordingManifestTests.swift`.

### Implementation for User Story 1

- [X] T011 [US1] Rename canonical local artifact file paths to `mic.wav` and `incoming.wav` in `apps/macos/RecApp/Sources/Capture/LocalRecordingStore.swift`.
- [X] T012 [US1] Change microphone recorder output to WAV PCM signed 16-bit mono 16000 Hz in `apps/macos/RecApp/Sources/Capture/LocalRecordingWriter.swift`.
- [X] T013 [US1] Replace remote float/stereo writer with PCM signed 16-bit mono 16000 Hz WAV writer in `apps/macos/RecApp/Sources/Capture/LocalRecordingWriter.swift`.
- [X] T014 [US1] Populate `mediaScribeField`, format, sample rate, channel count, bits per sample, and readiness fields in `apps/macos/RecApp/Sources/Capture/LocalRecordingWriter.swift`.

**Checkpoint**: New manual recordings produce the two required WAV files and a manifest that maps them to MediaScribe fields.

---

## Phase 4: User Story 2 - Preserve Timeline Truth For Diarization (Priority: P1)

**Goal**: Tracks preserve shared recording timeline and silence, or the package is marked degraded/failed.

**Independent Test**: Simulate missing or late source frames and confirm the manifest reports aligned ready output or concrete degraded/failed reasons without claiming readiness.

### Tests for User Story 2

- [X] T015 [P] [US2] Add timeline alignment and silence preservation tests in `apps/macos/Shared/Tests/LocalRecordingWriterTests.swift`.
- [X] T016 [P] [US2] Add degraded readiness tests for missing/misaligned tracks in `apps/macos/Shared/Tests/LocalRecordingManifestTests.swift`.

### Implementation for User Story 2

- [X] T017 [US2] Add timeline metadata and alignment validation in `apps/macos/RecApp/Sources/Capture/LocalRecordingManifestService.swift`.
- [X] T018 [US2] Preserve silence or record degraded alignment when source frames are absent in `apps/macos/RecApp/Sources/Capture/LocalRecordingWriter.swift`.
- [X] T019 [US2] Mark legacy or non-conforming local artifacts as not transcription-ready in `apps/macos/RecApp/Sources/Capture/LocalRecordingManifestService.swift`.

**Checkpoint**: The app never claims MediaScribe readiness for missing, empty, misaligned, legacy, or incorrectly formatted artifacts.

---

## Phase 5: User Story 3 - Keep Artifact Metadata Safe And Useful (Priority: P2)

**Goal**: Manifest and diagnostics expose safe readiness metadata without content or secrets.

**Independent Test**: Generate diagnostic/evidence metadata and confirm it includes safe readiness fields while excluding raw audio, transcript text, meeting content, credentials, tokens, signed URLs, passwords, live paths, and full MediaScribe keys.

### Tests for User Story 3

- [X] T020 [P] [US3] Add diagnostic redaction tests for artifact readiness fields in `apps/macos/Shared/Tests/DiagnosticRedactionTests.swift`.
- [X] T021 [P] [US3] Add local recording evidence readiness tests in `apps/macos/Shared/Tests/RecordingEvidenceTests.swift`.

### Implementation for User Story 3

- [X] T022 [US3] Include readiness and MediaScribe field mapping metadata in diagnostic bundles in `apps/macos/RecApp/Sources/Diagnostics/DiagnosticBundleService.swift`.
- [X] T023 [US3] Extend local recording evidence summary with artifact format readiness in `apps/macos/RecApp/Sources/Capture/RecordingEvidenceService.swift`.
- [X] T024 [US3] Ensure redactor safe allowlist covers readiness fields but excludes MediaScribe secrets in `apps/macos/Shared/Sources/Diagnostics/DiagnosticRedactor.swift`.

**Checkpoint**: QA can prove artifact format readiness without leaking content or secrets.

---

## Final Phase: Polish And Validation

**Purpose**: Validate the complete 010 feature and update evidence.

- [X] T025 Run Swift package tests and record result in `qa/macos/recording-artifact-format.md`.
- [X] T026 Run contract validation and record result in `qa/macos/recording-artifact-format.md`.
- [X] T027 Run realtime safety scan and record result in `qa/macos/recording-artifact-format.md`.
- [X] T028 Run `apps/macos/Scripts/validate-recording-artifact-format.sh` and record result in `qa/macos/recording-artifact-format.md`.
- [X] T029 Verify forbidden-content scan finds no raw audio, transcript text, meeting content, credentials, tokens, signed URLs, passwords, live secret paths, or full MediaScribe keys in `qa/macos/recording-artifact-format.md`.
- [X] T030 Re-run `apps/macos/Scripts/validate-capture-session-indicator.sh` and `apps/macos/Scripts/validate-local-recording-persistence.sh` to prove `007` and `008` gates still pass.
- [X] T031 Rebuild and launch local app bundle in `apps/macos/RecApp/.build/2brain Rec.app`.
- [X] T032 Run short manual smoke and record metadata-only result in `tests/macos/local-recording/recording-artifact-format-smoke.md`.
- [X] T033 Update release-candidate checklist with 010 status in `qa/macos/release-candidate-checklist.md`.
- [X] T034 Mark completed tasks in `specs/010-recording-artifact-format/tasks.md`.

---

## Dependencies & Execution Order

1. Phase 1 setup must complete before contract validation.
2. Phase 2 shared model updates must complete before manifest/writer implementation.
3. US1 and US2 are both P1. US1 creates the correct files; US2 prevents false readiness.
4. US3 depends on the manifest/readiness fields from US1/US2.
5. Final validation runs after all user story phases.

## Parallel Execution Examples

- T005 and T006 can run in parallel because they touch separate shared model concerns.
- T009 and T010 can run in parallel before US1 implementation.
- T015 and T016 can run in parallel before US2 implementation.
- T020 and T021 can run in parallel before US3 implementation.

## Implementation Strategy

MVP first: complete US1 and US2 together so pressing `Record` creates two
MediaScribe-ready local track files and never falsely claims readiness when
format/timeline requirements fail. Then add US3 evidence and validation. Do not
add upload, MediaScribe job submission, polling, result import, dashboard,
retention, deletion, or assisted auto-start in this feature.
