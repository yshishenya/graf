# Tasks: WebRTC AEC3 Speakerphone Spike

**Input**: Design documents from `specs/039-webrtc-aec3-speakerphone-spike/`

**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/`, `quickstart.md`, `checklists/`

**Tests**: Required. This feature is capture-critical and the user requested a larger validation set with sliced windows and full-file validation.

**Organization**: Tasks are grouped by independently testable user story.

## GitHub Issue Sync

- Created: 2026-06-22, 65 issues in `yshishenya/crisp`.
- Scoped canon validation: `feature:039` OK, 65 issues checked.
- Note: the repository-wide canon validator currently reports legacy open issue
  bodies outside `feature:039`; use scoped validation for this feature until
  those legacy issues are normalized.

| Task | GitHub issue |
|---|---|
| T001 | https://github.com/yshishenya/crisp/issues/1393 |
| T002 | https://github.com/yshishenya/crisp/issues/1394 |
| T003 | https://github.com/yshishenya/crisp/issues/1395 |
| T004 | https://github.com/yshishenya/crisp/issues/1396 |
| T005 | https://github.com/yshishenya/crisp/issues/1397 |
| T006 | https://github.com/yshishenya/crisp/issues/1398 |
| T007 | https://github.com/yshishenya/crisp/issues/1399 |
| T008 | https://github.com/yshishenya/crisp/issues/1400 |
| T009 | https://github.com/yshishenya/crisp/issues/1401 |
| T010 | https://github.com/yshishenya/crisp/issues/1402 |
| T011 | https://github.com/yshishenya/crisp/issues/1403 |
| T012 | https://github.com/yshishenya/crisp/issues/1404 |
| T013 | https://github.com/yshishenya/crisp/issues/1405 |
| T014 | https://github.com/yshishenya/crisp/issues/1406 |
| T015 | https://github.com/yshishenya/crisp/issues/1407 |
| T016 | https://github.com/yshishenya/crisp/issues/1408 |
| T017 | https://github.com/yshishenya/crisp/issues/1409 |
| T018 | https://github.com/yshishenya/crisp/issues/1410 |
| T019 | https://github.com/yshishenya/crisp/issues/1411 |
| T020 | https://github.com/yshishenya/crisp/issues/1412 |
| T021 | https://github.com/yshishenya/crisp/issues/1413 |
| T022 | https://github.com/yshishenya/crisp/issues/1414 |
| T023 | https://github.com/yshishenya/crisp/issues/1415 |
| T024 | https://github.com/yshishenya/crisp/issues/1416 |
| T025 | https://github.com/yshishenya/crisp/issues/1417 |
| T026 | https://github.com/yshishenya/crisp/issues/1418 |
| T027 | https://github.com/yshishenya/crisp/issues/1419 |
| T028 | https://github.com/yshishenya/crisp/issues/1420 |
| T029 | https://github.com/yshishenya/crisp/issues/1421 |
| T030 | https://github.com/yshishenya/crisp/issues/1422 |
| T031 | https://github.com/yshishenya/crisp/issues/1423 |
| T032 | https://github.com/yshishenya/crisp/issues/1424 |
| T033 | https://github.com/yshishenya/crisp/issues/1425 |
| T034 | https://github.com/yshishenya/crisp/issues/1426 |
| T035 | https://github.com/yshishenya/crisp/issues/1427 |
| T036 | https://github.com/yshishenya/crisp/issues/1428 |
| T037 | https://github.com/yshishenya/crisp/issues/1429 |
| T038 | https://github.com/yshishenya/crisp/issues/1430 |
| T039 | https://github.com/yshishenya/crisp/issues/1431 |
| T040 | https://github.com/yshishenya/crisp/issues/1432 |
| T041 | https://github.com/yshishenya/crisp/issues/1433 |
| T042 | https://github.com/yshishenya/crisp/issues/1434 |
| T043 | https://github.com/yshishenya/crisp/issues/1435 |
| T044 | https://github.com/yshishenya/crisp/issues/1436 |
| T045 | https://github.com/yshishenya/crisp/issues/1437 |
| T046 | https://github.com/yshishenya/crisp/issues/1438 |
| T047 | https://github.com/yshishenya/crisp/issues/1439 |
| T048 | https://github.com/yshishenya/crisp/issues/1440 |
| T049 | https://github.com/yshishenya/crisp/issues/1441 |
| T050 | https://github.com/yshishenya/crisp/issues/1442 |
| T051 | https://github.com/yshishenya/crisp/issues/1443 |
| T052 | https://github.com/yshishenya/crisp/issues/1444 |
| T053 | https://github.com/yshishenya/crisp/issues/1445 |
| T054 | https://github.com/yshishenya/crisp/issues/1446 |
| T055 | https://github.com/yshishenya/crisp/issues/1447 |
| T056 | https://github.com/yshishenya/crisp/issues/1448 |
| T057 | https://github.com/yshishenya/crisp/issues/1449 |
| T058 | https://github.com/yshishenya/crisp/issues/1450 |
| T059 | https://github.com/yshishenya/crisp/issues/1451 |
| T060 | https://github.com/yshishenya/crisp/issues/1452 |
| T061 | https://github.com/yshishenya/crisp/issues/1453 |
| T062 | https://github.com/yshishenya/crisp/issues/1454 |
| T063 | https://github.com/yshishenya/crisp/issues/1455 |
| T064 | https://github.com/yshishenya/crisp/issues/1456 |
| T065 | https://github.com/yshishenya/crisp/issues/1457 |

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel because it touches a different file or fixture and does not depend on incomplete tasks.
- **[Story]**: Maps to the user story in `spec.md`.
- Every task includes an exact file path.

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create the scaffolding for metadata-only AEC3 validation without introducing a native WebRTC dependency before readiness gates pass.

- [X] T001 Add the `WebRTCAEC3Validation` executable target to `apps/macos/Package.swift`.
- [X] T002 [P] Create the validation tool entry point in `apps/macos/Shared/Tools/WebRTCAEC3Validation/main.swift`.
- [X] T003 [P] Create the validation script shell in `apps/macos/Scripts/validate-webrtc-aec3-speakerphone-spike.sh`.
- [X] T004 [P] Create metadata-only AEC3 fixture directory documentation in `apps/macos/Shared/Tests/Fixtures/WebRTCAEC3/README.md`.
- [X] T005 [P] Create the metadata-only lab corpus fixture in `apps/macos/Shared/Tests/Fixtures/WebRTCAEC3/lab-grade-corpus.json`.
- [X] T006 [P] Create invalid and edge-case corpus fixtures in `apps/macos/Shared/Tests/Fixtures/WebRTCAEC3/invalid-corpus-cases.json`.
- [X] T007 [P] Create controlled real-hardware and supporting-route metadata fixtures in `apps/macos/Shared/Tests/Fixtures/WebRTCAEC3/controlled-real-hardware.json`.

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Shared models and boundaries required before any story can be completed.

**Critical**: No user story implementation can be completed until these tasks are done.

- [X] T008 [P] Add WebRTC AEC3 model test skeletons in `apps/macos/Shared/Tests/WebRTCAEC3ModelsTests.swift`.
- [X] T009 [P] Add WebRTC AEC3 evaluation test skeletons in `apps/macos/Shared/Tests/WebRTCAEC3EvaluationTests.swift`.
- [X] T010 [P] Add WebRTC AEC3 validation corpus test skeletons in `apps/macos/Shared/Tests/WebRTCAEC3ValidationCorpusTests.swift`.
- [X] T011 [P] Add WebRTC AEC3 contract test skeletons in `apps/macos/Shared/Tests/ContractTests/WebRTCAEC3SpikeContractTests.swift`.
- [X] T012 Add AEC3 outcome, threshold-profile, candidate, corpus, row, app-status, rollback, and decision models in `apps/macos/Shared/Sources/Models/SystemAudioCaptureModels.swift`.
- [X] T013 Add the feature-gated WebRTC AEC3 adapter boundary with an adapter-unavailable fail-closed implementation in `apps/macos/RecApp/Sources/Capture/WebRTCAEC3Adapter.swift`.
- [X] T014 Add the AEC3 evaluation service shell that consumes metadata and adapter results without raw audio persistence in `apps/macos/RecApp/Sources/Capture/WebRTCAEC3EvaluationService.swift`.
- [X] T015 Update diagnostic redactor allowed and forbidden AEC3 metadata fields in `apps/macos/Shared/Sources/Diagnostics/DiagnosticRedactor.swift`.

**Checkpoint**: Shared AEC3 types, adapter boundary, and metadata-only fixture scaffolding exist.

---

## Phase 3: User Story 1 - Classify WebRTC AEC3 Feasibility For Built-In Speakerphone (Priority: P1) MVP

**Goal**: Produce a truthful go/no-go classification for built-in Mac microphone plus built-in Mac speakers without claiming clean recording unless every gate passes.

**Independent Test**: Run focused AEC3 model, contract, evaluation, and corpus tests; the built-in route can be classified from metadata-only rows and fails closed for missing thresholds, unsafe reference, unsafe timing, or incomplete corpus coverage.

### Tests for User Story 1

- [X] T016 [P] [US1] Add outcome and promotion-scope tests in `apps/macos/Shared/Tests/WebRTCAEC3ModelsTests.swift`.
- [X] T017 [US1] Add acceptance-threshold profile tests, including profile-change invalidation, in `apps/macos/Shared/Tests/WebRTCAEC3ModelsTests.swift`.
- [X] T018 [P] [US1] Add lab-grade corpus minimum-count tests for ten files per scenario, five slices per file, full-file rows, long-form rows, room/device/volume coverage, and negative controls in `apps/macos/Shared/Tests/WebRTCAEC3ValidationCorpusTests.swift`.
- [X] T019 [US1] Add invalid corpus tests for missing files, missing slices, missing full files, missing long-form rows, missing room/device/volume coverage, and threshold-profile mismatch in `apps/macos/Shared/Tests/WebRTCAEC3ValidationCorpusTests.swift`.
- [X] T020 [P] [US1] Add adapter-unavailable, dependency-blocked, license-blocked, packaging-blocked, missing-reference, late-reference, clipped-reference, unsafe-ordering, drift, sample-format, speech-suppression, CPU, memory, and no-hang fail-closed tests in `apps/macos/Shared/Tests/WebRTCAEC3EvaluationTests.swift`.
- [X] T021 [P] [US1] Add WebRTC AEC3 result-shape contract tests for required fields, allowed values, threshold profile, route scope, dependency readiness, license readiness, packaging readiness, and forbidden content in `apps/macos/Shared/Tests/ContractTests/WebRTCAEC3SpikeContractTests.swift`.

### Implementation for User Story 1

- [X] T022 [US1] Implement AEC3 outcome, route, candidate, threshold-profile, validation-row, corpus, rollback, app-status, and decision validation rules in `apps/macos/Shared/Sources/Models/SystemAudioCaptureModels.swift`.
- [X] T023 [US1] Implement metadata-only corpus parsing and validation helpers in `apps/macos/RecApp/Sources/Capture/WebRTCAEC3EvaluationService.swift`.
- [X] T024 [US1] Implement fail-closed evaluation for dependency, license, packaging, reference, timing, duration, alignment, sample-format, speech preservation, residual leakage, echo/delay metrics, CPU, memory, no-hang, stability, diagnostics, threshold-profile, and route-scope gates in `apps/macos/RecApp/Sources/Capture/WebRTCAEC3EvaluationService.swift`.
- [X] T025 [US1] Implement `--self-test-corpus` and `--self-test-contracts` modes in `apps/macos/Shared/Tools/WebRTCAEC3Validation/main.swift`.
- [X] T026 [US1] Wire `apps/macos/Scripts/validate-webrtc-aec3-speakerphone-spike.sh` to run the validation tool, focused Swift tests, and metadata-only fixture checks.

**Checkpoint**: User Story 1 can classify built-in speakerphone AEC3 feasibility from metadata-only evidence and fail closed.

---

## Phase 4: User Story 2 - Preserve Recording Truth While Comparing Candidate Audio (Priority: P1)

**Goal**: Keep original microphone, incoming reference, candidate lineage, manifest truth, and transcription readiness separate until all promotion gates pass.

**Independent Test**: A recording package can include AEC3 candidate evidence while original `mic.wav`, `incoming.wav`, and `manifest.json` remain traceable and authoritative unless immediate-promotion and package-readiness gates both pass.

### Tests for User Story 2

- [X] T027 [P] [US2] Add manifest encoding and backward-compatibility tests for `webRTCAEC3Outcome` in `apps/macos/Shared/Tests/LocalRecordingManifestTests.swift`.
- [X] T028 [P] [US2] Add local recording writer propagation tests for AEC3 outcome metadata in `apps/macos/Shared/Tests/LocalRecordingWriterSystemAudioTests.swift`.
- [X] T029 [P] [US2] Add recording evidence tests for AEC3 primary outcome, row counts, threshold profile, next-step recommendation, and clean-claim state in `apps/macos/Shared/Tests/RecordingEvidenceTests.swift`.
- [X] T030 [P] [US2] Add lineage contract tests for original-only, candidate-metadata, derived-candidate, promoted-built-in-route, rolled-back, unproven, and blocked states in `apps/macos/Shared/Tests/ContractTests/WebRTCAEC3SpikeContractTests.swift`.
- [X] T031 [P] [US2] Add upload/transcription readiness regression tests proving AEC3 cannot affect readiness before immediate-promotion and package-readiness gates pass in `apps/macos/Shared/Tests/DesktopUploadQueueTests.swift`.

### Implementation for User Story 2

- [X] T032 [US2] Extend `LocalRecordingManifest` with optional `webRTCAEC3Outcome` while preserving decoding compatibility in `apps/macos/Shared/Sources/Models/AudioModels.swift`.
- [X] T033 [US2] Add `webRTCAEC3Outcome` creation, normalization, read, and write support in `apps/macos/RecApp/Sources/Capture/LocalRecordingManifestService.swift`.
- [X] T034 [US2] Propagate optional AEC3 outcome metadata through recording finalization without replacing original artifacts in `apps/macos/RecApp/Sources/Capture/LocalRecordingWriter.swift`.
- [X] T035 [US2] Add AEC3 package-truth and transcription-readiness evidence fields in `apps/macos/RecApp/Sources/Capture/RecordingEvidenceService.swift`.
- [X] T036 [US2] Keep desktop upload readiness tied to package truth and existing leakage finalization unless AEC3 immediate-promotion gates pass in `apps/macos/RecApp/Sources/Upload/DesktopUploadQueueService.swift`.
- [X] T037 [US2] Add local recording diagnostic bundle support for AEC3 outcome rows, threshold profile, echo/delay summaries, lineage, and rollback metadata in `apps/macos/RecApp/Sources/Diagnostics/DiagnosticBundleService.swift`.

**Checkpoint**: User Story 2 preserves package truth and auditability while carrying AEC3 candidate evidence.

---

## Phase 5: User Story 3 - Fail Safely Under Real Speakerphone Conditions (Priority: P1)

**Goal**: Make AEC3 problems, fallbacks, rollback, active capture, Stop, diagnostics, and app statuses visible and safe without raw content or noisy UI.

**Independent Test**: Missing reference, route change, timing uncertainty, quality drop, rollback, Stop/quit, diagnostics, and app-status states all produce bounded metadata and calm local status copy.

### Tests for User Story 3

- [X] T038 [P] [US3] Add app status copy tests for evaluating, original microphone truth, candidate blocked, promoted built-in route, rolled back, fallback relevant, and requires attention states in `apps/macos/Shared/Tests/CaptureControlTests.swift`.
- [X] T039 [US3] Add status priority and no-noisy-alert regression tests in `apps/macos/Shared/Tests/CaptureControlTests.swift`.
- [X] T040 [US3] Add tests that blocked and unproven status copy never uses clean-recording claim words in English or Russian in `apps/macos/Shared/Tests/CaptureControlTests.swift`.
- [X] T041 [P] [US3] Add diagnostic redaction tests for AEC3 forbidden raw audio, transcript text, private paths, credentials, signed URLs, and unbounded logs in `apps/macos/Shared/Tests/DiagnosticRedactionTests.swift`.
- [X] T042 [P] [US3] Add local recording diagnostic bundle tests for AEC3 app status, rollback, threshold summary, and metadata-only fields in `apps/macos/Shared/Tests/LeakageDiagnosticBundleTests.swift`.
- [X] T043 [P] [US3] Add rollback trigger and original-truth restoration tests in `apps/macos/Shared/Tests/WebRTCAEC3EvaluationTests.swift`.

### Implementation for User Story 3

- [X] T044 [US3] Add AEC3 accessibility identifiers for local recording status visibility in `apps/macos/Shared/Sources/Models/SystemAudioCaptureModels.swift`.
- [X] T045 [US3] Add AEC3 app status copy, priority, icon/style mapping, and claim-safety rules in `apps/macos/RecApp/Sources/Capture/CaptureControlView.swift`.
- [X] T046 [US3] Thread optional AEC3 status text through capture-session UI state without hiding active capture or Stop in `apps/macos/RecApp/Sources/Capture/CaptureSessionController.swift`.
- [X] T047 [US3] Implement rollback event construction and original-truth restoration logic in `apps/macos/RecApp/Sources/Capture/WebRTCAEC3EvaluationService.swift`.
- [X] T048 [US3] Add AEC3 diagnostic allowlist, denylist, threshold summaries, echo/delay summaries, app-status state, and rollback metadata to redaction and bundle output in `apps/macos/RecApp/Sources/Diagnostics/DiagnosticBundleService.swift`.
- [X] T049 [US3] Extend `apps/macos/Scripts/validate-webrtc-aec3-speakerphone-spike.sh` with metadata-only diagnostics, app-status, rollback, and Stop/quit self-test modes.

**Checkpoint**: User Story 3 shows careful local statuses for problems and fallbacks while preserving metadata-only diagnostics and Stop.

---

## Phase 6: User Story 4 - Decide Whether To Promote AEC3 Or Move To Fallback (Priority: P2)

**Goal**: Produce one decision record that either promotes the built-in route, limits AEC3 to candidate/guidance evidence, blocks it, or sends the product to 040 fallback planning.

**Independent Test**: The completed validation result selects exactly one primary outcome, links supporting rows, explains limitations, and never broadens the clean-recording claim beyond built-in Mac microphone plus built-in Mac speakers.

### Tests for User Story 4

- [X] T050 [P] [US4] Add decision record tests for exactly one primary outcome and safe next-step recommendation in `apps/macos/Shared/Tests/WebRTCAEC3EvaluationTests.swift`.
- [X] T051 [US4] Add required supporting-route row tests proving favorable USB, wired, Bluetooth, AirPods, and browser evidence is present when available and cannot broaden promotion scope in `apps/macos/Shared/Tests/WebRTCAEC3EvaluationTests.swift`.
- [X] T052 [P] [US4] Add validation tool tests for summary output, metadata-only decision records, and fallback-to-040 recommendations in `apps/macos/Shared/Tests/WebRTCAEC3ValidationCorpusTests.swift`.

### Implementation for User Story 4

- [X] T053 [US4] Implement decision aggregation and single-outcome selection in `apps/macos/RecApp/Sources/Capture/WebRTCAEC3EvaluationService.swift`.
- [X] T054 [US4] Implement metadata-only decision record output in `apps/macos/Shared/Tools/WebRTCAEC3Validation/main.swift`.
- [X] T055 [US4] Add supporting-route row handling and no-broadened-claim decision rules in `apps/macos/RecApp/Sources/Capture/WebRTCAEC3EvaluationService.swift`.
- [X] T056 [US4] Update `CHANGELOG.md` under `[Unreleased]` with the 039 AEC3 validation, status, and QA expectation change.

**Checkpoint**: User Story 4 produces a truthful promotion, block, guidance, or fallback decision.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Finish validation, documentation consistency, and release readiness.

- [X] T057 [P] Update `specs/039-webrtc-aec3-speakerphone-spike/quickstart.md` with final command names, test filters, and manual real-hardware evidence steps after implementation.
- [X] T058 [P] Add metadata-only evidence templates for final 039 closeout in `specs/039-webrtc-aec3-speakerphone-spike/evidence/README.md`.
- [X] T059 Run focused SwiftPM tests for AEC3, capture control, manifest, diagnostics, and upload readiness from `specs/039-webrtc-aec3-speakerphone-spike/quickstart.md`.
- [X] T060 Run `apps/macos/Scripts/validate-webrtc-aec3-speakerphone-spike.sh --self-test-corpus` from `specs/039-webrtc-aec3-speakerphone-spike/quickstart.md`.
- [X] T061 Run `apps/macos/Scripts/validate-webrtc-aec3-speakerphone-spike.sh --self-test-contracts` from `specs/039-webrtc-aec3-speakerphone-spike/quickstart.md`.
- [X] T062 Run existing recording artifact, system-audio pivot, CPU, memory, and no-hang validation scripts listed in `specs/039-webrtc-aec3-speakerphone-spike/quickstart.md`.
- [X] T063 Run `infra/scripts/ci-local.sh` from repository root.
- [X] T064 Review `specs/039-webrtc-aec3-speakerphone-spike/checklists/audio-capture.md`, `specs/039-webrtc-aec3-speakerphone-spike/checklists/security-privacy.md`, and `specs/039-webrtc-aec3-speakerphone-spike/checklists/ux-status.md` against the final implementation.
- [X] T065 Record final metadata-only outcome notes and limitations in `specs/039-webrtc-aec3-speakerphone-spike/evidence/README.md`.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies.
- **Foundational (Phase 2)**: Depends on Setup completion and blocks all user story completion.
- **User Story 1 (Phase 3)**: Depends on Foundational; MVP scope.
- **User Story 2 (Phase 4)**: Depends on Foundational and may run after or alongside US1, but final package-readiness assertions depend on US1 outcome types.
- **User Story 3 (Phase 5)**: Depends on Foundational and may run alongside US1/US2 after shared status models exist.
- **User Story 4 (Phase 6)**: Depends on US1 evidence models and benefits from US2/US3 package/status semantics.
- **Polish (Phase 7)**: Depends on selected user stories being complete.

### User Story Dependencies

- **US1 (P1)**: Independent classification increment after Phase 2.
- **US2 (P1)**: Independent package-truth increment after Phase 2; uses US1 model vocabulary.
- **US3 (P1)**: Independent safe-status and failure increment after Phase 2; uses US1/US2 model vocabulary.
- **US4 (P2)**: Decision-record increment after US1, with final consistency from US2 and US3.

### Within Each User Story

- Write or update tests first and observe the intended failure.
- Implement models before services when the service depends on new types.
- Implement service logic before UI, diagnostics, or script integration.
- Finish each story checkpoint before marking its tasks `[X]`.

## Parallel Execution Examples

### User Story 1

```text
T016, T018, T020, and T021 can be prepared in parallel because they touch different test files.
T017 follows T016, and T019 follows T018 because each pair edits the same test file.
T023 and T025 can proceed in parallel after T022 defines shared model vocabulary.
```

### User Story 2

```text
T027, T028, T029, T030, and T031 can be prepared in parallel because they cover separate test files.
T033, T034, T035, T036, and T037 must be sequenced after T032 updates the manifest model.
```

### User Story 3

```text
T038, T041, T042, and T043 can be prepared in parallel because they touch separate test files.
T039 and T040 follow T038 because they edit the same capture-control test file.
T045 and T048 can proceed in parallel after T044 defines shared status identifiers.
```

### User Story 4

```text
T050 and T052 can be prepared in parallel because they touch different test files.
T051 follows T050 because both edit the AEC3 evaluation test file.
T054 can proceed after T053 exposes decision aggregation.
```

## Implementation Strategy

### MVP First

1. Complete Phase 1 and Phase 2.
2. Complete US1 to get a truthful built-in speakerphone feasibility classifier.
3. Validate US1 with model, contract, evaluation, corpus, and validation-tool tests.
4. Continue US2 and US3 before any user-facing clean-recording claim.

### Incremental Delivery

1. US1 proves whether AEC3 can be classified safely.
2. US2 preserves package truth and transcription readiness.
3. US3 makes problems, rollback, fallback, and Stop status visible in the app.
4. US4 records the final promotion/block/fallback decision.

### Closeout

1. Run all quickstart validation commands.
2. Run `infra/scripts/ci-local.sh`.
3. Update `tasks.md` items to `[X]` only after code and validation evidence pass.
4. Sync GitHub issues through `$speckit-taskstoissues` after analyze is clean and before implementation tracking.
