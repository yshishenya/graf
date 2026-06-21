# Tasks: Microphone Sample Graph Foundation

**Input**: Design documents from `specs/037-microphone-sample-graph-foundation/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/](./contracts/), [quickstart.md](./quickstart.md)

**Tests**: Required for this high-risk capture slice. Write failing tests before implementation tasks inside each phase.

**Organization**: Tasks are grouped by independently testable user story. User Stories 1-3 are P1; complete them in order because US2 and US3 depend on the app-owned stream foundation from US1. User Story 4 is P2 and can follow once manifest stream metadata exists.

## GitHub Issue Sync

- Repository: `yshishenya/crisp`
- Created: 2026-06-18
- Scoped canon validation: `feature:037` OK, 48 issues checked.
- Note: the repository-wide canon validator currently reports legacy open issue
  formatting failures outside `feature:037`; the scoped 037 sync is valid.

| Task | Issue |
|------|-------|
| T001 | https://github.com/yshishenya/crisp/issues/1294 |
| T002 | https://github.com/yshishenya/crisp/issues/1295 |
| T003 | https://github.com/yshishenya/crisp/issues/1296 |
| T004 | https://github.com/yshishenya/crisp/issues/1297 |
| T005 | https://github.com/yshishenya/crisp/issues/1298 |
| T006 | https://github.com/yshishenya/crisp/issues/1299 |
| T007 | https://github.com/yshishenya/crisp/issues/1300 |
| T008 | https://github.com/yshishenya/crisp/issues/1301 |
| T009 | https://github.com/yshishenya/crisp/issues/1302 |
| T010 | https://github.com/yshishenya/crisp/issues/1303 |
| T011 | https://github.com/yshishenya/crisp/issues/1304 |
| T012 | https://github.com/yshishenya/crisp/issues/1305 |
| T013 | https://github.com/yshishenya/crisp/issues/1306 |
| T014 | https://github.com/yshishenya/crisp/issues/1307 |
| T015 | https://github.com/yshishenya/crisp/issues/1308 |
| T016 | https://github.com/yshishenya/crisp/issues/1309 |
| T017 | https://github.com/yshishenya/crisp/issues/1310 |
| T018 | https://github.com/yshishenya/crisp/issues/1311 |
| T019 | https://github.com/yshishenya/crisp/issues/1312 |
| T020 | https://github.com/yshishenya/crisp/issues/1313 |
| T021 | https://github.com/yshishenya/crisp/issues/1314 |
| T022 | https://github.com/yshishenya/crisp/issues/1315 |
| T023 | https://github.com/yshishenya/crisp/issues/1316 |
| T024 | https://github.com/yshishenya/crisp/issues/1317 |
| T025 | https://github.com/yshishenya/crisp/issues/1318 |
| T026 | https://github.com/yshishenya/crisp/issues/1319 |
| T027 | https://github.com/yshishenya/crisp/issues/1320 |
| T028 | https://github.com/yshishenya/crisp/issues/1321 |
| T029 | https://github.com/yshishenya/crisp/issues/1322 |
| T030 | https://github.com/yshishenya/crisp/issues/1323 |
| T031 | https://github.com/yshishenya/crisp/issues/1324 |
| T032 | https://github.com/yshishenya/crisp/issues/1325 |
| T033 | https://github.com/yshishenya/crisp/issues/1326 |
| T034 | https://github.com/yshishenya/crisp/issues/1327 |
| T035 | https://github.com/yshishenya/crisp/issues/1328 |
| T036 | https://github.com/yshishenya/crisp/issues/1329 |
| T037 | https://github.com/yshishenya/crisp/issues/1330 |
| T038 | https://github.com/yshishenya/crisp/issues/1331 |
| T039 | https://github.com/yshishenya/crisp/issues/1332 |
| T040 | https://github.com/yshishenya/crisp/issues/1333 |
| T041 | https://github.com/yshishenya/crisp/issues/1334 |
| T042 | https://github.com/yshishenya/crisp/issues/1335 |
| T043 | https://github.com/yshishenya/crisp/issues/1336 |
| T044 | https://github.com/yshishenya/crisp/issues/1337 |
| T045 | https://github.com/yshishenya/crisp/issues/1338 |
| T046 | https://github.com/yshishenya/crisp/issues/1339 |
| T047 | https://github.com/yshishenya/crisp/issues/1340 |
| T048 | https://github.com/yshishenya/crisp/issues/1341 |

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Prepare evidence and documentation scaffolding for implementation and validation.

- [X] T001 Create feature evidence directory and safe evidence README in `specs/037-microphone-sample-graph-foundation/evidence/README.md`
- [X] T002 [P] Add manual runtime matrix template for selected/default mic, unavailable mic, virtual mic rejection, Stop, quit, and leakage truth in `specs/037-microphone-sample-graph-foundation/evidence/manual-runtime-matrix.md`
- [X] T003 [P] Add validation results log template for tests, CPU gates, package inspection, and diagnostic redaction in `specs/037-microphone-sample-graph-foundation/evidence/test-results.md`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Add shared models and contracts needed before any user story can be implemented.

**Critical**: No user story work can begin until this phase is complete.

- [X] T004 [P] Add model tests for recording microphone selection, stream session, stream health, and future processing readiness in `apps/macos/Shared/Tests/MicrophoneCaptureServiceTests.swift`
- [X] T005 [P] Add manifest model tests for optional microphone selection and stream metadata backward-compatible decoding in `apps/macos/Shared/Tests/LocalRecordingManifestTests.swift`
- [X] T006 Add recording microphone selection, stream session, stream health, and future processing readiness models in `apps/macos/Shared/Sources/Models/SystemAudioCaptureModels.swift`
- [X] T007 Extend `LocalRecordingManifest` with optional microphone selection and stream health fields while preserving default decoding in `apps/macos/Shared/Sources/Models/AudioModels.swift`
- [X] T008 Thread optional microphone stream metadata through manifest creation and normalization in `apps/macos/RecApp/Sources/Capture/LocalRecordingManifestService.swift`
- [X] T009 Add contract tests for microphone selection, sample graph metadata, and absence of AEC/voice-processing/WebRTC claims in `apps/macos/Shared/Tests/ContractTests/MicrophoneSampleGraphContractTests.swift`

**Checkpoint**: Shared data model compiles and existing manifests remain readable.

---

## Phase 3: User Story 1 - Record With A Selected App-Owned Microphone Stream (Priority: P1)

**Goal**: Record `mic.wav` through an app-owned selected/default microphone sample source while preserving `incoming.wav` and `manifest.json`.

**Independent Test**: Start and stop controlled recordings for selected input and default fallback. Inspect package shape and manifest stream metadata.

### Tests for User Story 1

- [X] T010 [P] [US1] Add tests for default fallback and selected native microphone resolution in `apps/macos/Shared/Tests/MicrophoneCaptureServiceTests.swift`
- [X] T011 [P] [US1] Add tests for rejecting 2brain virtual/self-routing recording inputs in `apps/macos/Shared/Tests/RecordingMicrophoneSelectionTests.swift`
- [X] T012 [P] [US1] Add writer tests proving an injected app-owned microphone source writes `mic.wav`, updates levels, and preserves `incoming.wav` in `apps/macos/Shared/Tests/LocalRecordingWriterSystemAudioTests.swift`
- [X] T013 [P] [US1] Add capture control tests for selected/default microphone status and recovery copy readiness in `apps/macos/Shared/Tests/CaptureControlTests.swift`

### Implementation for User Story 1

- [X] T014 [US1] Implement native recording microphone enumeration, default input resolution, and selection validation in `apps/macos/RecApp/Sources/Capture/MicrophoneCaptureService.swift`
- [X] T015 [US1] Implement app-owned microphone sample source lifecycle and sample buffering in `apps/macos/RecApp/Sources/Capture/MicrophoneCaptureService.swift`
- [X] T016 [US1] Add a recording microphone selection state value for the app shell in `apps/macos/RecApp/App/TwoBrainRecApp.swift`
- [X] T017 [US1] Update manual recording start to resolve selected/default input, start the app-owned microphone source, and pass it to `LocalRecordingWriter` in `apps/macos/RecApp/App/TwoBrainRecApp.swift`
- [X] T018 [US1] Add selected/default microphone status, picker/menu, and rejection/unavailable status presentation to capture controls in `apps/macos/RecApp/Sources/Capture/CaptureControlView.swift`
- [X] T019 [US1] Pass recording microphone selection props and callbacks from the app shell into capture controls in `apps/macos/RecApp/App/TwoBrainRecApp.swift`
- [X] T020 [US1] Include app-owned stream metadata in local manifest creation for successful selected/default recordings in `apps/macos/RecApp/Sources/Capture/LocalRecordingWriter.swift`
- [X] T021 [US1] Update localized/status labels and accessibility identifiers for microphone selection status in `apps/macos/Shared/Sources/Models/SystemAudioCaptureModels.swift`

**Checkpoint**: User Story 1 records via app-owned selected/default microphone source and remains independently package-testable.

---

## Phase 4: User Story 2 - Fail Closed On Microphone Stream Problems (Priority: P1)

**Goal**: Permission, unavailable device, wrong-device, route-change, no-frame, silence, Stop, and quit problems never look like clean accepted recordings.

**Independent Test**: Simulate each failure class and confirm blocked/degraded/failed/unproven truth with no invisible capture.

### Tests for User Story 2

- [X] T022 [P] [US2] Add tests for denied/restricted/stale microphone permission and blocked start metadata in `apps/macos/Shared/Tests/MicrophoneCaptureServiceTests.swift`
- [X] T023 [P] [US2] Add tests for unavailable selected input and route-change/device-loss failure truth in `apps/macos/Shared/Tests/RecordingMicrophoneSelectionTests.swift`
- [X] T024 [P] [US2] Add writer tests for app-owned microphone no-frames, silence, bounded drain, and write failure status in `apps/macos/Shared/Tests/LocalRecordingWriterSystemAudioTests.swift`
- [X] T025 [P] [US2] Add app-exit/Stop cleanup tests for microphone stream release and bounded finalization in `apps/macos/Shared/Tests/CaptureSessionSafetyTests.swift`

### Implementation for User Story 2

- [X] T026 [US2] Add microphone selection and stream failure reason mapping to blocked/degraded/failed/unproven states in `apps/macos/RecApp/Sources/Capture/MicrophoneCaptureService.swift`
- [X] T027 [US2] Propagate microphone permission, unsupported selection, selected input unavailable, and stream start failures into recording blockers in `apps/macos/RecApp/App/TwoBrainRecApp.swift`
- [X] T028 [US2] Record microphone no-frame, silent, route-change, and stream failure truth during writer finalization in `apps/macos/RecApp/Sources/Capture/LocalRecordingWriter.swift`
- [X] T029 [US2] Ensure Stop, failed start, and app quit stop the microphone sample source before clearing local active state in `apps/macos/RecApp/App/TwoBrainRecApp.swift`
- [X] T030 [US2] Update capture health failure normalization for microphone stream failures in `apps/macos/RecApp/Sources/Capture/LocalRecordingManifestService.swift`

**Checkpoint**: User Story 2 proves microphone stream failures fail closed and do not leave invisible capture.

---

## Phase 5: User Story 3 - Preserve Existing Package And Leakage Truth (Priority: P1)

**Goal**: Keep accepted `025` package shape and `020` leakage finalization semantics unchanged while adding graph readiness metadata.

**Independent Test**: Existing package, upload-safety, track alignment, and leakage-finalization tests pass with new microphone metadata.

### Tests for User Story 3

- [X] T031 [P] [US3] Add package compatibility tests for `mic.wav`, `incoming.wav`, `manifest.json`, track roles, and duration difference in `apps/macos/Shared/Tests/SystemAudioRecordingPackageTests.swift`
- [X] T032 [P] [US3] Add leakage-finalization regression tests proving app-owned mic stream does not override leakage truth in `apps/macos/Shared/Tests/LocalRecordingLeakageFinalizationTests.swift`
- [X] T033 [P] [US3] Add upload queue compatibility tests for manifests with optional microphone stream metadata in `apps/macos/Shared/Tests/DesktopUploadQueueTests.swift`

### Implementation for User Story 3

- [X] T034 [US3] Preserve existing local recording package fields while adding optional microphone metadata in `apps/macos/RecApp/Sources/Capture/LocalRecordingManifestService.swift`
- [X] T035 [US3] Preserve upload-safe manifest interpretation for new optional fields in `apps/macos/RecApp/Sources/Upload/DesktopUploadQueueService.swift`
- [X] T036 [US3] Preserve leakage finalization inputs and status mapping for app-owned microphone tracks in `apps/macos/RecApp/Sources/Capture/LeakageFinalizationService.swift`
- [X] T037 [US3] Add contract fixture coverage for microphone stream metadata without raw audio in `apps/macos/Shared/Tests/Fixtures/MicrophoneSampleGraph/manifest-with-stream-metadata.json`

**Checkpoint**: User Story 3 preserves recording package consumers and leakage gates.

---

## Phase 6: User Story 4 - Keep Diagnostics Metadata-Only (Priority: P2)

**Goal**: Expose microphone stream evidence for debugging without raw audio, transcript text, secrets, private paths, or meeting content.

**Independent Test**: Generate success and failure diagnostics and confirm only bounded metadata-safe stream evidence is present.

### Tests for User Story 4

- [X] T038 [P] [US4] Add diagnostic redaction tests for microphone selection, stream health, failure reason, and future readiness fields in `apps/macos/Shared/Tests/DiagnosticRedactionTests.swift`
- [X] T039 [P] [US4] Add diagnostic bundle tests for success, blocked, degraded, and failed microphone stream evidence in `apps/macos/Shared/Tests/LeakageDiagnosticBundleTests.swift`

### Implementation for User Story 4

- [X] T040 [US4] Add metadata-only microphone selection and stream health evidence to diagnostic bundle output in `apps/macos/RecApp/Sources/Diagnostics/DiagnosticBundleService.swift`
- [X] T041 [US4] Extend diagnostic redaction rules for new microphone stream metadata fields in `apps/macos/Shared/Sources/Diagnostics/DiagnosticRedactor.swift`
- [X] T042 [US4] Update recording evidence service to include safe graph readiness and selected/default input truth in `apps/macos/RecApp/Sources/Capture/RecordingEvidenceService.swift`

**Checkpoint**: User Story 4 keeps diagnostics safe and reviewable.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Validation, evidence, changelog, and final readiness.

- [X] T043 [P] Update quickstart with final command outputs and any runtime caveats discovered during implementation in `specs/037-microphone-sample-graph-foundation/quickstart.md`
- [X] T044 [P] Add behavior change entry for microphone sample graph foundation in `CHANGELOG.md`
- [X] T045 Run focused SwiftPM tests and record outputs in `specs/037-microphone-sample-graph-foundation/evidence/test-results.md`
- [X] T046 Run package, diagnostic, and CPU validation from quickstart and record evidence in `specs/037-microphone-sample-graph-foundation/evidence/test-results.md`
- [X] T047 Run `infra/scripts/ci-local.sh` and record final result in `specs/037-microphone-sample-graph-foundation/evidence/test-results.md`
- [X] T048 Reconcile completed tasks with GitHub issue links and Russian closure/status text in `specs/037-microphone-sample-graph-foundation/tasks.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- Phase 1 Setup: no dependencies.
- Phase 2 Foundational: depends on Phase 1 and blocks all user stories.
- Phase 3 US1: depends on Phase 2 and is the MVP scope.
- Phase 4 US2: depends on US1 sample-source and metadata model.
- Phase 5 US3: depends on US1 manifest metadata and should run before final validation.
- Phase 6 US4: depends on US1/US2 metadata and can run after failure truth exists.
- Phase 7 Polish: depends on desired user stories being complete.

### User Story Dependencies

- US1 is the MVP and can be validated independently once Phase 2 is complete.
- US2 depends on US1 because fail-closed behavior needs the app-owned stream path.
- US3 depends on US1 because package/leakage preservation must include new optional metadata.
- US4 depends on US1 and US2 because diagnostic evidence needs success and failure metadata.

### Within Each User Story

- Test tasks precede implementation tasks.
- Model/contract tasks precede service and UI integration.
- App shell integration follows capture service and writer support.
- Story checkpoints must pass before marking story tasks complete.

## Parallel Opportunities

- Setup evidence templates T002 and T003 can run in parallel.
- Foundational tests T004 and T005 can run in parallel.
- US1 tests T010-T013 can run in parallel after Phase 2.
- US2 tests T022-T025 can run in parallel after US1.
- US3 tests T031-T033 can run in parallel after US1.
- US4 tests T038 and T039 can run in parallel after US2 metadata exists.
- Polish docs T043 and T044 can run in parallel after implementation stabilizes.

## Parallel Example: User Story 1

```text
Task: T010 Add tests for default fallback and selected native microphone resolution in apps/macos/Shared/Tests/MicrophoneCaptureServiceTests.swift
Task: T011 Add tests for rejecting 2brain virtual/self-routing recording inputs in apps/macos/Shared/Tests/RecordingMicrophoneSelectionTests.swift
Task: T012 Add writer tests proving an injected app-owned microphone source writes mic.wav in apps/macos/Shared/Tests/LocalRecordingWriterSystemAudioTests.swift
Task: T013 Add capture control tests for selected/default microphone status in apps/macos/Shared/Tests/CaptureControlTests.swift
```

## Implementation Strategy

### MVP First (US1 Only)

1. Complete Phase 1 and Phase 2.
2. Implement US1 tests and code.
3. Validate selected/default microphone stream recording and package shape.
4. Stop for review if only the minimum graph foundation is needed.

### Incremental Delivery

1. US1 creates the selected/default app-owned microphone source path.
2. US2 hardens failures and release behavior.
3. US3 protects package/leakage compatibility.
4. US4 adds metadata-only diagnostics.
5. Polish runs focused tests, quickstart validation, and local CI.

### GitHub Issue Sync

Run `$speckit-taskstoissues` after analyze is clean. Issue titles, bodies,
status comments, and closure comments must be in Russian and follow
`docs/agent-guidance/github-issue-canon.md`.
