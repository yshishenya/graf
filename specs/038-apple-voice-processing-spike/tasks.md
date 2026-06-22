# Tasks: Apple Voice Processing Spike

**Input**: Design documents from `specs/038-apple-voice-processing-spike/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/](./contracts/), [quickstart.md](./quickstart.md)

**Tests**: Required for this high-risk capture slice. Write failing tests before implementation tasks inside each phase.

**Organization**: Tasks are grouped by independently testable user story. User Stories 1-3 are P1 and must be implemented before the final decision story can close. User Story 4 is P2 and depends on evidence produced by the first three stories.

## GitHub Issue Sync

- Repository: `yshishenya/crisp`
- Created: 2026-06-22
- Scoped canon validation: `feature:038` OK, 48 issues checked.
- Note: the repository-wide canon validator currently reports legacy open issue
  formatting failures outside `feature:038`; the scoped 038 sync is the validation target.

| Task | Issue |
|------|-------|
| T001 | https://github.com/yshishenya/crisp/issues/1343 |
| T002 | https://github.com/yshishenya/crisp/issues/1344 |
| T003 | https://github.com/yshishenya/crisp/issues/1345 |
| T004 | https://github.com/yshishenya/crisp/issues/1346 |
| T005 | https://github.com/yshishenya/crisp/issues/1347 |
| T006 | https://github.com/yshishenya/crisp/issues/1348 |
| T007 | https://github.com/yshishenya/crisp/issues/1349 |
| T008 | https://github.com/yshishenya/crisp/issues/1350 |
| T009 | https://github.com/yshishenya/crisp/issues/1351 |
| T010 | https://github.com/yshishenya/crisp/issues/1352 |
| T011 | https://github.com/yshishenya/crisp/issues/1353 |
| T012 | https://github.com/yshishenya/crisp/issues/1354 |
| T013 | https://github.com/yshishenya/crisp/issues/1355 |
| T014 | https://github.com/yshishenya/crisp/issues/1356 |
| T015 | https://github.com/yshishenya/crisp/issues/1357 |
| T016 | https://github.com/yshishenya/crisp/issues/1358 |
| T017 | https://github.com/yshishenya/crisp/issues/1359 |
| T018 | https://github.com/yshishenya/crisp/issues/1360 |
| T019 | https://github.com/yshishenya/crisp/issues/1361 |
| T020 | https://github.com/yshishenya/crisp/issues/1362 |
| T021 | https://github.com/yshishenya/crisp/issues/1363 |
| T022 | https://github.com/yshishenya/crisp/issues/1364 |
| T023 | https://github.com/yshishenya/crisp/issues/1365 |
| T024 | https://github.com/yshishenya/crisp/issues/1366 |
| T025 | https://github.com/yshishenya/crisp/issues/1367 |
| T026 | https://github.com/yshishenya/crisp/issues/1368 |
| T027 | https://github.com/yshishenya/crisp/issues/1369 |
| T028 | https://github.com/yshishenya/crisp/issues/1370 |
| T029 | https://github.com/yshishenya/crisp/issues/1371 |
| T030 | https://github.com/yshishenya/crisp/issues/1372 |
| T031 | https://github.com/yshishenya/crisp/issues/1373 |
| T032 | https://github.com/yshishenya/crisp/issues/1374 |
| T033 | https://github.com/yshishenya/crisp/issues/1375 |
| T034 | https://github.com/yshishenya/crisp/issues/1376 |
| T035 | https://github.com/yshishenya/crisp/issues/1377 |
| T036 | https://github.com/yshishenya/crisp/issues/1378 |
| T037 | https://github.com/yshishenya/crisp/issues/1379 |
| T038 | https://github.com/yshishenya/crisp/issues/1380 |
| T039 | https://github.com/yshishenya/crisp/issues/1381 |
| T040 | https://github.com/yshishenya/crisp/issues/1382 |
| T041 | https://github.com/yshishenya/crisp/issues/1383 |
| T042 | https://github.com/yshishenya/crisp/issues/1384 |
| T043 | https://github.com/yshishenya/crisp/issues/1385 |
| T044 | https://github.com/yshishenya/crisp/issues/1386 |
| T045 | https://github.com/yshishenya/crisp/issues/1387 |
| T046 | https://github.com/yshishenya/crisp/issues/1388 |
| T047 | https://github.com/yshishenya/crisp/issues/1389 |
| T048 | https://github.com/yshishenya/crisp/issues/1390 |

## GitHub Completion Sync

- Pre-merge checked: 2026-06-22 with
  `gh issue list --repo yshishenya/crisp --search 'feature:038' --state open --limit 60`.
- Pre-merge result: 48 open `feature:038` issues matched the task table range
  `#1343`-`#1390`.
- Post-merge result: PR #1391
  (`https://github.com/yshishenya/crisp/pull/1391`) merged feature 038 at
  commit `f5a8a8f56bd06933181aae1b409d2f218d171d5e`; issues `#1343`-`#1390`
  were closed with per-task Russian closure comments and validation evidence.
- Post-merge review recheck: `gh issue list --repo yshishenya/crisp --search
  'feature:038' --state open --limit 100 --json number,title,state` returned
  no open issues; direct issue views for `#1343`-`#1390` all returned `CLOSED`.
- Closure rule status: satisfied after PR merge. Each closure comment includes
  the merged PR URL, the task id, the metadata-only outcome
  `defer_to_webrtc_aec3`, validation commands, preserved package-truth scope,
  excluded work, and the 039 follow-up.

## Phase 1: Setup (Shared Evidence)

**Purpose**: Prepare metadata-only evidence surfaces for Apple processing validation.

- [X] T001 Create feature evidence directory and safe evidence README in `specs/038-apple-voice-processing-spike/evidence/README.md`
- [X] T002 [P] Add manual runtime matrix template for built-in speakerphone, wired/headset, USB, browser target, double-talk, loud speaker, route change, Stop, quit, and diagnostics in `specs/038-apple-voice-processing-spike/evidence/manual-runtime-matrix.md`
- [X] T003 [P] Add validation results log template for Swift tests, package inspection, CPU/no-hang, redaction, and manual runtime evidence in `specs/038-apple-voice-processing-spike/evidence/test-results.md`
- [X] T004 [P] Add outcome decision record template for accepted, guidance-only, blocked, or deferred Apple states in `specs/038-apple-voice-processing-spike/evidence/decision-record.md`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Add shared model and contract coverage needed before candidate processing work can begin.

**Critical**: No user story work can begin until this phase is complete.

- [X] T005 [P] Add model tests for `AppleProcessingCandidate`, `AppleProcessingValidationRow`, `ProcessedMicrophoneEvidence`, and `AppleProcessingOutcome` in `apps/macos/Shared/Tests/AppleVoiceProcessingModelsTests.swift`
- [X] T006 [P] Add contract tests for Apple processing result states, lineage labels, metadata-only evidence, and no clean claims in `apps/macos/Shared/Tests/ContractTests/AppleVoiceProcessingSpikeContractTests.swift`
- [X] T007 Add Apple processing candidate, validation row, processed evidence, and outcome models in `apps/macos/Shared/Sources/Models/SystemAudioCaptureModels.swift`
- [X] T008 Thread optional Apple processing spike evidence through local recording manifest decoding/encoding without breaking legacy manifests in `apps/macos/Shared/Sources/Models/AudioModels.swift`
- [X] T009 Add manifest service support for optional Apple processing candidate evidence in `apps/macos/RecApp/Sources/Capture/LocalRecordingManifestService.swift`
- [X] T010 Add diagnostic redaction allowlist and forbidden-field coverage for Apple processing metadata keys in `apps/macos/Shared/Sources/Diagnostics/DiagnosticRedactor.swift`

**Checkpoint**: Shared models compile, contracts pin outcome vocabulary, and existing manifests remain readable.

---

## Phase 3: User Story 1 - Classify Apple Processing Feasibility For Built-In Speakerphone (Priority: P1)

**Goal**: Evaluate Apple processing on built-in mic/speakers and classify the route as accepted, guidance-only, blocked, or deferred without a false clean claim.

**Independent Test**: Run model/service tests for baseline versus candidate evidence and inspect the decision record for exactly one primary outcome.

### Tests for User Story 1

- [X] T011 [P] [US1] Add tests for required validation rows and mutually exclusive Apple outcome states in `apps/macos/Shared/Tests/AppleVoiceProcessingModelsTests.swift`
- [X] T012 [P] [US1] Add tests for baseline-versus-candidate leakage comparison and blocked quality/stability mapping in `apps/macos/Shared/Tests/LeakageMeasurementTests.swift`
- [X] T013 [P] [US1] Add tests for feature-gated Apple candidate probing and built-in speakerphone decision gating with far-end-only, near-end-only, double-talk, loud speaker, route change, and Stop/quit rows in `apps/macos/Shared/Tests/AppleVoiceProcessingEvaluationTests.swift`

### Implementation for User Story 1

- [X] T014 [US1] Implement feature-gated Apple processing candidate probing, availability/enable-state capture, validation matrix aggregation, and outcome selection in `apps/macos/RecApp/Sources/Capture/AppleVoiceProcessingEvaluationService.swift`
- [X] T015 [US1] Implement baseline and candidate leakage comparison helpers using existing leakage measurement summaries in `apps/macos/RecApp/Sources/Capture/AppleVoiceProcessingEvaluationService.swift`
- [X] T016 [US1] Add built-in speakerphone outcome mapping to recording evidence summaries without changing leakage finalization authority in `apps/macos/RecApp/Sources/Capture/RecordingEvidenceService.swift`
- [X] T017 [US1] Add metadata-only decision record generation helper for manual evidence files in `apps/macos/RecApp/Sources/Capture/AppleVoiceProcessingEvaluationService.swift`

**Checkpoint**: User Story 1 can classify Apple feasibility for built-in speakerphone from metadata-only rows and cannot emit a clean claim without all gates.

---

## Phase 4: User Story 2 - Prove Processed Signal Lineage Matches Product Truth (Priority: P1)

**Goal**: Prove whether Apple-processed near-end evidence feeds live microphone behavior, persisted `mic.wav`, incoming reference, and manifest truth.

**Independent Test**: Generate controlled candidate manifest data and confirm lineage cannot be accepted when any live/persisted/reference/manifest link is missing.

### Tests for User Story 2

- [X] T018 [P] [US2] Add manifest tests for original-only, candidate metadata, derived candidate, guidance-only, unproven, and blocked lineage labels in `apps/macos/Shared/Tests/LocalRecordingManifestTests.swift`
- [X] T019 [P] [US2] Add writer tests proving candidate processed evidence cannot overwrite original `mic.wav` or bypass `incoming.wav` alignment in `apps/macos/Shared/Tests/LocalRecordingWriterSystemAudioTests.swift`
- [X] T020 [P] [US2] Add leakage-finalization regression tests proving Apple candidate evidence does not override `020` clean/leakage/unproven truth in `apps/macos/Shared/Tests/LocalRecordingLeakageFinalizationTests.swift`
- [X] T021 [P] [US2] Add package contract fixture coverage for Apple candidate metadata without raw audio in `apps/macos/Shared/Tests/Fixtures/AppleVoiceProcessing/manifest-with-apple-candidate.json`

### Implementation for User Story 2

- [X] T022 [US2] Extend `LocalRecordingManifest` with optional Apple candidate lineage metadata while preserving backward-compatible decoding in `apps/macos/Shared/Sources/Models/AudioModels.swift`
- [X] T023 [US2] Thread candidate lineage metadata through manifest creation and normalization in `apps/macos/RecApp/Sources/Capture/LocalRecordingManifestService.swift`
- [X] T024 [US2] Preserve original microphone and incoming track writing while attaching candidate metadata in `apps/macos/RecApp/Sources/Capture/LocalRecordingWriter.swift`
- [X] T025 [US2] Preserve leakage finalization inputs and status mapping when Apple candidate metadata is present in `apps/macos/RecApp/Sources/Capture/LeakageFinalizationService.swift`
- [X] T026 [US2] Add fixture decoding coverage for Apple candidate manifest metadata in `apps/macos/Shared/Tests/ContractTests/AppleVoiceProcessingSpikeContractTests.swift`

**Checkpoint**: User Story 2 proves Apple candidate evidence stays traceable and cannot silently redefine local package truth.

---

## Phase 5: User Story 3 - Keep Failures Safe, Visible, And Metadata-Only (Priority: P1)

**Goal**: Ensure candidate processing failures fail closed, preserve visible recording controls, and export only bounded diagnostics.

**Independent Test**: Simulate unavailable processing, missing reference, route topology changes, user/system Mic Mode changes, Stop/quit, and diagnostic export.

### Tests for User Story 3

- [X] T027 [P] [US3] Add tests for unavailable, failed-to-enable, user/system-controlled, missing-reference, and route-topology-blocked candidate states in `apps/macos/Shared/Tests/AppleVoiceProcessingEvaluationTests.swift`
- [X] T028 [P] [US3] Add capture safety tests proving candidate processing cannot hide active capture or remove one-action Stop in `apps/macos/Shared/Tests/CaptureSessionSafetyTests.swift`
- [X] T029 [P] [US3] Add diagnostic bundle tests for accepted, blocked, guidance-only, unproven, and deferred Apple evidence states in `apps/macos/Shared/Tests/LeakageDiagnosticBundleTests.swift`
- [X] T030 [P] [US3] Add diagnostic redaction tests for forbidden Apple processing evidence fields in `apps/macos/Shared/Tests/DiagnosticRedactionTests.swift`

### Implementation for User Story 3

- [X] T031 [US3] Implement Apple candidate failure reason mapping and fail-closed state normalization in `apps/macos/RecApp/Sources/Capture/AppleVoiceProcessingEvaluationService.swift`
- [X] T032 [US3] Add feature-gated candidate processing lifecycle coordination that releases resources on Stop, failed start, and app quit in `apps/macos/RecApp/App/TwoBrainRecApp.swift`
- [X] T033 [US3] Add metadata-only Apple processing evidence to diagnostic bundle output in `apps/macos/RecApp/Sources/Diagnostics/DiagnosticBundleService.swift`
- [X] T034 [US3] Extend diagnostic redaction rules for Apple processing route, lineage, outcome, CPU, and failure fields in `apps/macos/Shared/Sources/Diagnostics/DiagnosticRedactor.swift`
- [X] T035 [US3] Add capture control status copy for guidance-only, blocked, and unproven Apple spike states without claiming clean recording in `apps/macos/RecApp/Sources/Capture/CaptureControlView.swift`

**Checkpoint**: User Story 3 keeps failures safe, visible, bounded, and metadata-only.

---

## Phase 6: User Story 4 - Decide The Next Clean-Recording Step (Priority: P2)

**Goal**: Produce a decision record that tells whether to promote Apple processing, use it only as guidance, defer to WebRTC AEC3, or move to fallback planning.

**Independent Test**: Review the completed evidence record and confirm it selects exactly one primary outcome with no contradictory clean-recording claim.

### Tests for User Story 4

- [X] T036 [P] [US4] Add tests for exactly-one primary outcome and next-step recommendation mapping in `apps/macos/Shared/Tests/AppleVoiceProcessingEvaluationTests.swift`
- [X] T037 [P] [US4] Add contract tests ensuring release-facing and user-facing summaries cannot claim clean speakerphone unless accepted built-in speakerphone gates pass in `apps/macos/Shared/Tests/ContractTests/AppleVoiceProcessingSpikeContractTests.swift`

### Implementation for User Story 4

- [X] T038 [US4] Implement final outcome summary generation with accepted, guidance-only, blocked, and deferred next-step recommendations in `apps/macos/RecApp/Sources/Capture/AppleVoiceProcessingEvaluationService.swift`
- [X] T039 [US4] Update `docs/current-product-status.md` with the 038 decision boundary and follow-up state after evidence is available in `docs/current-product-status.md`
- [X] T040 [US4] Update `docs/audio-capture-backlog.md` to record the 038 result and whether `039`, `040`, or guidance-only work is next in `docs/audio-capture-backlog.md`

**Checkpoint**: User Story 4 leaves a single, reviewable Apple decision and a clear next step.

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Validation, evidence, changelog, issue sync, and final readiness.

- [X] T041 [P] Add behavior change entry for Apple voice processing spike in `CHANGELOG.md`
- [X] T042 [P] Add feature registry note for 038 accepted/blocked/deferred state in `docs/feature-registry.md`
- [X] T043 Add validation helper script for the metadata-only 038 quickstart checks in `apps/macos/Scripts/validate-apple-voice-processing-spike.sh`
- [X] T044 Run focused SwiftPM tests and record outputs in `specs/038-apple-voice-processing-spike/evidence/test-results.md`
- [X] T045 Run package, diagnostic, CPU, and artifact validation from quickstart and record evidence in `specs/038-apple-voice-processing-spike/evidence/test-results.md`
- [X] T046 Run manual runtime matrix or record blocked/unavailable hardware rows in `specs/038-apple-voice-processing-spike/evidence/manual-runtime-matrix.md`
- [X] T047 Run `infra/scripts/ci-local.sh` and record final result in `specs/038-apple-voice-processing-spike/evidence/test-results.md`
- [X] T048 Reconcile completed tasks with GitHub issue links and Russian closure/status text in `specs/038-apple-voice-processing-spike/tasks.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- Phase 1 Setup: no dependencies.
- Phase 2 Foundational: depends on Phase 1 and blocks all user stories.
- Phase 3 US1: depends on Phase 2 and is the MVP decision-classification scope.
- Phase 4 US2: depends on Phase 2 and should complete before any candidate acceptance.
- Phase 5 US3: depends on Phase 2 and must complete before runtime evidence is trusted.
- Phase 6 US4: depends on US1, US2, and US3 evidence.
- Phase 7 Polish: depends on desired user stories being complete.

### User Story Dependencies

- US1 is independently testable after Phase 2 but cannot close accepted state without US2/US3 evidence.
- US2 can start after Phase 2 and protects package truth for all candidate outcomes.
- US3 can start after Phase 2 and protects safety/diagnostics for all candidate outcomes.
- US4 depends on US1-US3 because the decision record needs complete evidence.

### Within Each User Story

- Test tasks precede implementation tasks.
- Shared model/contract tasks precede service, writer, manifest, and UI integration.
- Candidate acceptance cannot be recorded until lineage, diagnostics, and safety tasks are complete.
- Story checkpoints must pass before marking story tasks complete.

## Parallel Opportunities

- Setup templates T002-T004 can run in parallel.
- Foundational tests T005-T006 can run in parallel.
- US1 tests T011-T013 can run in parallel after Phase 2.
- US2 tests T018-T021 can run in parallel after Phase 2.
- US3 tests T027-T030 can run in parallel after Phase 2.
- US4 tests T036-T037 can run in parallel after US1-US3 evidence exists.
- Polish docs T041-T042 can run in parallel after implementation stabilizes.

## Parallel Example: User Story 1

```text
Task: T011 Add tests for required validation rows and mutually exclusive Apple outcome states in apps/macos/Shared/Tests/AppleVoiceProcessingModelsTests.swift
Task: T012 Add tests for baseline-versus-candidate leakage comparison in apps/macos/Shared/Tests/LeakageMeasurementTests.swift
Task: T013 Add tests for built-in speakerphone decision gating in apps/macos/Shared/Tests/AppleVoiceProcessingEvaluationTests.swift
```

## Implementation Strategy

### MVP First (US1 Classification Only)

1. Complete Phase 1 and Phase 2.
2. Implement US1 tests and evidence aggregation.
3. Validate built-in speakerphone classification cannot emit a clean claim without all gates.
4. Stop for review if only planning/evidence scaffolding is needed.

### Full Spike

1. Complete Setup + Foundational.
2. Implement US1 classification.
3. Implement US2 lineage/package truth.
4. Implement US3 fail-closed diagnostics and visible-control safety.
5. Implement US4 decision record.
6. Run automated and manual quickstart validation before any PR/merge claim.

### Follow-Up Boundary

- If outcome is `defer_to_webrtc_aec3`, continue with `039-webrtc-aec3-speakerphone-spike`.
- If outcome is guidance-only or headset-only, continue with `040-speakerphone-recording-fallback-decision` or `041` onboarding as appropriate.
- Do not merge clean speakerphone wording unless `accepted_for_builtin_speakerphone` is proven.
