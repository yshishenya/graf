# Tasks: Speaker-To-Mic Leakage Control

**Input**: Design documents from `specs/020-speaker-to-mic-leakage/`

**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/`, `quickstart.md`

**Tests**: Included because the specification defines independent tests for every user story and the feature touches high-risk driver/capture/privacy behavior.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel because it touches different files and has no dependency on incomplete tasks
- **[Story]**: User story label from `spec.md`
- Every task includes an exact repository path

## Phase 1: Setup

**Purpose**: Add static contracts and fixture entry points needed by all stories.

- [X] T001 Copy the leakage package schema from `specs/020-speaker-to-mic-leakage/contracts/local-recording-package-leakage.schema.json` into `tests/macos/contract/local-recording-package-leakage.json`
- [X] T002 Copy the leakage event schema from `specs/020-speaker-to-mic-leakage/contracts/leakage-finalization-events.schema.json` into `tests/macos/contract/leakage-finalization-events.json`
- [X] T003 [P] Validate the built-in speakerphone go/no-go and mixed-audio fallback decision record from `specs/020-speaker-to-mic-leakage/speakerphone-go-no-go.md` in `tests/macos/local-recording/speaker-to-mic-leakage-finalization.md`
- [X] T004 [P] Add manual route matrix worksheet for built-in speakers, wired headphones, USB headset, Bluetooth/AirPods-class, aggregate/multi-output, and browser target coverage in `tests/macos/physical-devices/speaker-to-mic-leakage-route-matrix.md`
- [X] T005 Register leakage contract fixture validation in `apps/macos/Shared/Tools/ContractValidation/main.swift`

## Phase 2: Foundational

**Purpose**: Shared models, redaction, thresholds, lifecycle registration, and helper services required before user-story work.

**Critical**: No user story implementation should begin until this phase is complete.

- [X] T006 Add `LeakageStatus`, `LeakageAlignmentStatus`, `LeakageTranscriptionGate`, `LeakageEvidenceRole`, `LeakageRouteVolumeBucket`, and `LeakageRouteMuteState` enums in `apps/macos/Shared/Sources/Models/AudioStates.swift`
- [X] T007 Add `LeakageMeasurement`, `RecordingRouteMetadata`, `LeakageThresholdVersion`, `DerivedCleanedTrackMetadata`, and `LeakageFinalization` models in `apps/macos/Shared/Sources/Models/AudioModels.swift`
- [X] T008 Extend `LocalRecordingTrack` with `evidenceRole`, optional `sourceTrackIds`, optional `processorId`, optional `processorVersion`, optional `residualLeakageStatus`, and optional `eligibleForTranscription` in `apps/macos/Shared/Sources/Models/AudioModels.swift`
- [X] T009 Extend `LocalRecordingManifest` with `finalizedAt`, optional `leakageFinalization`, derived track support, and local deletion-registration fields in `apps/macos/Shared/Sources/Models/AudioModels.swift`
- [X] T010 Add leakage-specific failure reasons while preserving existing values in `apps/macos/Shared/Sources/Models/AudioStates.swift`
- [X] T011 Implement threshold constants for `leakage-threshold.v1` using the numeric gates from `specs/020-speaker-to-mic-leakage/research.md` in `apps/macos/Shared/Sources/Models/AudioModels.swift`
- [X] T012 Update diagnostic redaction allowlist and forbidden-field coverage for leakage finalization metadata in `apps/macos/Shared/Sources/Diagnostics/DiagnosticRedactor.swift`
- [X] T013 Update local recording manifest contract fixture expectations for leakage fields and no-egress fields in `tests/macos/contract/local-recording-manifest.json`
- [X] T014 Update recording artifact contract fixture expectations for original evidence roles, derived evidence roles, and derived artifact retention/deletion accounting in `tests/macos/contract/recording-artifact-format.json`
- [X] T015 Add contract validation checks for leakage finalization, derived-track schema rules, and required local deletion registration before derived transcription eligibility in `apps/macos/Shared/Tools/ContractValidation/main.swift`
- [X] T016 Add derived artifact registration with local retention/deletion accounting before any derived cleaned track can be transcription-eligible in `apps/macos/RecApp/Sources/Capture/LocalRecordingManifestService.swift`

**Checkpoint**: Models, contracts, threshold version, lifecycle registration, and diagnostic safety are ready for user-story implementation.

## Phase 3: User Story 1 - Keep Remote Audio Out Of The Local Mic Track (Priority: P1) MVP

**Goal**: Saved local microphone evidence is never treated as clean local speech when far-end speaker leakage is detected or cannot be proven clean.

**Independent Test**: A far-end-only package finalizes as `clean` only when measured below threshold, otherwise as `leakage_detected`, `unproven`, or not transcription-ready.

### Tests for User Story 1

- [X] T017 [P] [US1] Add leakage model tests for `clean`, `leakage_detected`, `unproven`, `not_measured`, and `not_applicable` status semantics in `apps/macos/Shared/Tests/LeakageFinalizationModelTests.swift`
- [X] T018 [P] [US1] Add far-end-only leakage evaluator tests for clean and contaminated fixtures in `apps/macos/Shared/Tests/LeakageFinalizationServiceTests.swift`
- [X] T019 [P] [US1] Add double-talk confidence downgrade tests in `apps/macos/Shared/Tests/LeakageMeasurementTests.swift`
- [X] T020 [P] [US1] Add package finalization integration tests for local mic leakage readiness blocking in `apps/macos/Shared/Tests/LocalRecordingLeakageFinalizationTests.swift`
- [X] T021 [P] [US1] Add leakage classification fixture tests for silence, ordinary microphone noise, room echo, clipping, and dropout so they are not confused with remote speaker leakage in `apps/macos/Shared/Tests/LeakageMeasurementTests.swift`
- [X] T022 [P] [US1] Add controlled fixture metadata expectations for silence, noise, room echo, clipping, and dropout classifications in `tests/macos/local-recording/speaker-to-mic-leakage-finalization.md`

### Implementation for User Story 1

- [X] T023 [P] [US1] Implement windowed WAV metadata and sample reader helpers for package finalization in `apps/macos/RecApp/Sources/Capture/LeakageWAVReader.swift`
- [X] T024 [P] [US1] Implement leakage measurement result builder and status decision rules in `apps/macos/RecApp/Sources/Capture/LeakageMeasurementService.swift`
- [X] T025 [US1] Implement package-level leakage finalization service using saved `mic.wav` and `incoming.wav` evidence in `apps/macos/RecApp/Sources/Capture/LeakageFinalizationService.swift`
- [X] T026 [US1] Integrate `LeakageFinalizationService` into `LocalRecordingManifestService.manifest` without assigning final leakage status before stop in `apps/macos/RecApp/Sources/Capture/LocalRecordingManifestService.swift`
- [X] T027 [US1] Update `LocalRecordingWriter.stop` to call finalization after both tracks are closed and before writing `manifest.json` in `apps/macos/RecApp/Sources/Capture/LocalRecordingWriter.swift`
- [X] T028 [US1] Ensure contaminated, unproven, or not-measured original local mic evidence cannot produce `transcriptionReadiness=ready` in `apps/macos/RecApp/Sources/Capture/LocalRecordingManifestService.swift`
- [X] T029 [US1] Preserve original `mic.wav` and `incoming.wav` file names and evidence role metadata during finalization in `apps/macos/RecApp/Sources/Capture/LocalRecordingWriter.swift`

**Checkpoint**: User Story 1 is independently testable with far-end-only, double-talk, silence, noise, room echo, clipping, dropout, and package fixtures.

## Phase 4: User Story 2 - Preserve Clean Dual-Track Recording Truth (Priority: P1)

**Goal**: Finalized packages truthfully state clean, contaminated, degraded, unproven, or not measured before any dual-track transcription readiness claim.

**Independent Test**: Stopped packages with aligned clean tracks, misaligned tracks, missing tracks, and contaminated tracks produce distinct manifest truth and readiness outcomes.

### Tests for User Story 2

- [X] T030 [P] [US2] Add manifest tests for leakage readiness gating across clean, contaminated, unproven, not-measured, and not-applicable packages in `apps/macos/Shared/Tests/LocalRecordingManifestTests.swift`
- [X] T031 [P] [US2] Add timeline mismatch regression test for the real evidence package shape in `apps/macos/Shared/Tests/LocalRecordingLeakageFinalizationTests.swift`
- [X] T032 [P] [US2] Add contract tests for `local-recording-manifest.v3` leakage fields and legacy schema degradation in `apps/macos/Shared/Tests/ContractTests/LeakageFinalizationContractTests.swift`
- [X] T033 [P] [US2] Add recording writer tests for stop-time finalization and no in-progress final leakage status in `apps/macos/Shared/Tests/LocalRecordingWriterTests.swift`

### Implementation for User Story 2

- [X] T034 [US2] Bump the local recording manifest schema to `local-recording-manifest.v3` in `apps/macos/Shared/Sources/Models/AudioModels.swift`
- [X] T035 [US2] Add schema-aware transcription readiness for v2 legacy packages and v3 leakage-gated packages in `apps/macos/Shared/Sources/Models/AudioModels.swift`
- [X] T036 [US2] Extend `LocalRecordingManifestService.resolveFailureReason` for leakage, unproven, not-measured, and timeline-misaligned finalization outcomes in `apps/macos/RecApp/Sources/Capture/LocalRecordingManifestService.swift`
- [X] T037 [US2] Add manifest write/read compatibility for optional leakage fields in `apps/macos/RecApp/Sources/Capture/LocalRecordingManifestService.swift`
- [X] T038 [US2] Update local recording evidence summaries to include leakage status, threshold version, alignment status, and transcription gate in `apps/macos/RecApp/Sources/Capture/RecordingEvidenceService.swift`
- [X] T039 [US2] Update `ContractValidation` to require v3 leakage finalization fields while preserving forbidden egress checks in `apps/macos/Shared/Tools/ContractValidation/main.swift`

**Checkpoint**: User Story 2 is independently testable with manifest and writer fixtures.

## Phase 5: User Story 3 - Avoid User-Burden During Recording (Priority: P1)

**Goal**: Normal recording is not blocked by leakage route readiness, and route facts are collected only as finalization metadata when available.

**Independent Test**: Built-in speakers, headphones, USB, Bluetooth/AirPods-class, aggregate/multi-output, and route changes do not create live leakage blockers; stopped packages receive metadata-backed finalization truth.

### Tests for User Story 3

- [X] T040 [P] [US3] Add prerequisite gate tests proving leakage route readiness is not a recording start blocker while self-routing through 2brain Rec virtual devices is still rejected in `apps/macos/Shared/Tests/RecordingPrerequisiteGateTests.swift`
- [X] T041 [P] [US3] Add route metadata mapping tests for physical input/output classes, volume bucket, mute, browser target, route changes, and `selfRoutingRejected` evidence in `apps/macos/Shared/Tests/RecordingRouteMetadataTests.swift`
- [X] T042 [P] [US3] Add UI state tests proving no live leakage warning/status is exposed during active recording in `apps/macos/Shared/Tests/CaptureControlTests.swift`
- [X] T043 [P] [US3] Add route matrix documentation expectations for finalization-only leakage outcomes in `tests/macos/physical-devices/speaker-to-mic-leakage-route-matrix.md`

### Implementation for User Story 3

- [X] T044 [US3] Ensure `RecordingPrerequisiteGate` does not add leakage route readiness as a start blocker but still rejects any 2brain Rec virtual device selected as the physical working microphone or output in `apps/macos/RecApp/Sources/Capture/RecordingPrerequisiteGate.swift`
- [X] T045 [US3] Implement recording route metadata snapshot construction for finalization evidence in `apps/macos/RecApp/Sources/Capture/RecordingRouteMetadataService.swift`
- [X] T046 [US3] Wire route metadata snapshot collection into stop-time finalization in `apps/macos/RecApp/Sources/Capture/LocalRecordingWriter.swift`
- [X] T047 [US3] Keep capture controls limited to recording state and post-finalization truth state, with no live leakage remediation prompt, in `apps/macos/RecApp/Sources/Capture/CaptureControlView.swift`
- [X] T048 [US3] Update audit/evidence event detail to record finalization route metadata without technical user remediation copy in `apps/macos/RecApp/App/TwoBrainRecApp.swift`

**Checkpoint**: User Story 3 is independently testable through prerequisite gate, UI state, and route metadata tests.

## Phase 6: User Story 4 - Detect And Diagnose Leakage Without Leaking Content (Priority: P2)

**Goal**: QA/support can inspect metadata-only leakage evidence without raw meeting content, transcripts, secrets, or live local paths.

**Independent Test**: Diagnostics contain safe leakage metrics, route facts, thresholds, and failure reasons, and redaction removes forbidden fields.

### Tests for User Story 4

- [X] T049 [P] [US4] Add diagnostic redaction tests for leakage finalization metadata and forbidden content fields in `apps/macos/Shared/Tests/DiagnosticRedactionTests.swift`
- [X] T050 [P] [US4] Add diagnostic bundle tests for leakage measurement, route metadata, direct loopback suspicion, and acoustic leakage suspicion in `apps/macos/Shared/Tests/LeakageDiagnosticBundleTests.swift`
- [X] T051 [P] [US4] Add contract validation fixture tests for leakage finalization events in `apps/macos/Shared/Tests/ContractTests/LeakageFinalizationContractTests.swift`
- [X] T052 [P] [US4] Add realtime static check expectations for no HAL callback leakage work in `tests/macos/static/audio-rt-safety-check.sh`

### Implementation for User Story 4

- [X] T053 [US4] Extend diagnostic bundle construction with metadata-only leakage finalization fields in `apps/macos/RecApp/Sources/Diagnostics/DiagnosticBundleService.swift`
- [X] T054 [US4] Add leakage finalization event serialization for audit-safe metadata in `apps/macos/Shared/Sources/Audit/AuditEvents.swift`
- [X] T055 [US4] Add direct-loopback versus acoustic-leakage suspicion fields to diagnostic values in `apps/macos/RecApp/Sources/Diagnostics/DiagnosticBundleService.swift`
- [X] T056 [US4] Update `DiagnosticRedactor` allowlist and recursive forbidden-field handling for leakage nested objects in `apps/macos/Shared/Sources/Diagnostics/DiagnosticRedactor.swift`
- [X] T057 [US4] Document controlled-stimulus fixture boundary and real-meeting no-content rule in `tests/macos/local-recording/speaker-to-mic-leakage-finalization.md`

**Checkpoint**: User Story 4 is independently testable through diagnostic redaction, bundle, contract, and static safety checks.

## Phase 7: User Story 5 - Keep Clean-Room Krisp-Category Behavior (Priority: P2)

**Goal**: The solution remains based on public APIs, original code, approved dependencies, and documented future spike gates.

**Independent Test**: Design and implementation artifacts show no proprietary Krisp assets, copy, behavior, binaries, or protected implementation details.

### Tests for User Story 5

- [X] T058 [P] [US5] Add clean-room dependency decision fixture for Apple/WebRTC/post-processing/mixed-audio gates and speakerphone no-go traceability in `tests/macos/contract/leakage-clean-room-decision.json`
- [X] T059 [P] [US5] Add contract validation for licensing, offline/local processing, CPU, latency, privacy, fallback, and test coverage fields in `apps/macos/Shared/Tools/ContractValidation/main.swift`
- [X] T060 [P] [US5] Add clean-room and speakerphone go/no-go documentation review checklist for leakage implementation artifacts in `tests/macos/local-recording/speaker-to-mic-leakage-finalization.md`

### Implementation for User Story 5

- [X] T061 [US5] Add clean-room dependency decision model fields for future Apple/WebRTC/AEC promotion gates, mixed-audio fallback states, and cited-source/outcome records in `apps/macos/Shared/Sources/Models/AudioModels.swift`
- [X] T062 [US5] Record Apple voice-processing, WebRTC AEC3, post-recording cleanup, mixed-audio, and built-in speakerphone go/no-go decisions as metadata-only evidence without enabling live cleanup in `apps/macos/RecApp/Sources/Capture/LeakageFinalizationService.swift`
- [X] T063 [US5] Update user-facing recording-truth status copy constants to avoid Krisp-specific language and technical remediation burden in `apps/macos/RecApp/Sources/Shared/AdaptiveStatusText.swift`

**Checkpoint**: User Story 5 is independently testable through contract validation and documentation review.

## Phase 8: Polish & Cross-Cutting Concerns

**Purpose**: Final validation, docs, and safety checks across stories.

- [X] T064 [P] Update local recording smoke documentation with leakage finalization expectations in `tests/macos/local-recording/recording-artifact-format-smoke.md`
- [X] T065 [P] Update current product status with 020 leakage finalization truth and remaining live AEC follow-up in `docs/current-product-status.md`
- [X] T066 Run Swift package tests and leakage finalization performance/memory validation for the macOS package, including the 2-hour package, 60-second finalization, and 256 MB memory bounds, then record command/result in `specs/020-speaker-to-mic-leakage/quickstart.md`
- [X] T067 Run `ContractValidation` and record command/result in `specs/020-speaker-to-mic-leakage/quickstart.md`
- [X] T068 Run realtime static safety check and record command/result in `specs/020-speaker-to-mic-leakage/quickstart.md`
- [X] T069 Run manual route matrix smoke or mark unavailable hardware rows explicitly in `tests/macos/physical-devices/speaker-to-mic-leakage-route-matrix.md`
- [X] T070 Review all checklist files for unresolved requirement-quality blockers before `$speckit-implement` in `specs/020-speaker-to-mic-leakage/checklists`
- [X] T071 Run existing bidirectional passthrough regression gates for SC-012 recording-adjacent changes, including visible capture controls, manual `Record`/`Stop`, local artifact format, and non-recording passthrough continuity, then record command/result in `specs/020-speaker-to-mic-leakage/quickstart.md`
- [X] T072 Record installer, signing/notarization, repair, rollback, and uninstall no-change scope for this finalization-only slice in `specs/020-speaker-to-mic-leakage/quickstart.md`
- [X] T073 Record degraded-state driver behavior evidence for route changes, missing tracks, timeline mismatch, and non-recording passthrough continuity in `tests/macos/physical-devices/speaker-to-mic-leakage-route-matrix.md`

## Phase 9: Review Findings Remediation

**Purpose**: Close the security, privacy, UX, validation, and issue-canon gaps found during the full review before marking feature `020` accepted.

- [X] T074 [P] [US1] Add regression coverage proving delayed remote-speaker leakage cannot finalize as `clean` in `apps/macos/Shared/Tests/LeakageMeasurementTests.swift`
- [X] T075 [P] [US1] Add regression coverage proving leakage after the first sampled minute cannot finalize as `clean` in `apps/macos/Shared/Tests/LeakageFinalizationServiceTests.swift`
- [X] T076 [P] [US1] Add malformed WAV regression coverage for `sampleRate == 0`, invalid channel counts, and finite duration math in `apps/macos/Shared/Tests/LeakageFinalizationServiceTests.swift`
- [X] T077 [P] [US2] Add readiness regression coverage proving actual WAV format mismatches are blocked even when manifest track metadata claims 16 kHz mono in `apps/macos/Shared/Tests/LeakageFinalizationServiceTests.swift`
- [X] T078 [P] [US2] Add deletion-truth regression coverage proving degraded or not-measured manifests do not claim registered local deletion without evidence in `apps/macos/Shared/Tests/LocalRecordingManifestTests.swift`
- [X] T079 [US1] Replace full-file `Data(contentsOf:)` leakage reads with bounded WAV metadata and sampled window reads that cover start, middle, and end evidence in `apps/macos/RecApp/Sources/Capture/LeakageWAVReader.swift`
- [X] T080 [US1] Implement lag-aware correlation and fail-closed confidence rules for delayed or incomplete leakage evidence in `apps/macos/RecApp/Sources/Capture/LeakageMeasurementService.swift`
- [X] T081 [US1] Enforce actual WAV format compatibility and malformed-header fail-closed behavior before clean readiness in `apps/macos/RecApp/Sources/Capture/LeakageFinalizationService.swift`
- [X] T082 [US2] Replace unconditional `localDeletionRegistered=true` with truthful deletion registration state for original and derived artifacts in `apps/macos/RecApp/Sources/Capture/LocalRecordingManifestService.swift`
- [X] T083 [US2] Update manifest model defaults and contract validation so deletion registration cannot be accidentally assumed true in `apps/macos/Shared/Sources/Models/AudioModels.swift` and `apps/macos/Shared/Tools/ContractValidation/main.swift`
- [X] T084 [US3] Wire leakage-specific recording truth and transcription gate labels into the post-stop app status surface in `apps/macos/RecApp/App/TwoBrainRecApp.swift`
- [X] T085 [US3] Clarify route matrix wording so self-routing rejection is not described as leakage readiness blocking in `tests/macos/physical-devices/speaker-to-mic-leakage-route-matrix.md`
- [X] T086 [US4] Harden GitHub issue-canon template writes against symlink escapes and out-of-repository resolved paths in `.specify/extensions/github-issue-canon/scripts/issue_canon_common.py`
- [X] T087 [US4] Redact credential-bearing Git remote URLs from issue-canon error messages in `.specify/extensions/github-issue-canon/scripts/issue_canon_common.py`
- [X] T088 Restore executable bits on Spec Kit shell helpers in `.specify/scripts/bash/check-prerequisites.sh`, `.specify/scripts/bash/common.sh`, `.specify/scripts/bash/create-new-feature.sh`, `.specify/scripts/bash/setup-plan.sh`, and `.specify/scripts/bash/setup-tasks.sh`
- [X] T089 Update `docs/current-product-status.md` and `specs/020-speaker-to-mic-leakage/quickstart.md` to record post-review remediation and 2-hour validation acceptance state
- [X] T090 Run focused leakage regression tests and record command/results in `specs/020-speaker-to-mic-leakage/quickstart.md`
- [X] T091 Run Swift package build, available SwiftPM/XCTest validation, `ContractValidation`, realtime static safety, and passthrough regression after remediation in `specs/020-speaker-to-mic-leakage/quickstart.md`
- [X] T092 Run or explicitly defer the 2-hour local-only fixture performance/memory validation with command, elapsed time, memory evidence, and reason in `specs/020-speaker-to-mic-leakage/quickstart.md`
- [X] T093 Create GitHub issues for Phase 9 remediation tasks using the repository issue canon and link them back to feature `020` in `specs/020-speaker-to-mic-leakage/tasks.md`
- [X] T094 Re-run `$speckit-analyze` after Phase 9 fixes and resolve any remaining critical/high gaps before commit in `specs/020-speaker-to-mic-leakage/tasks.md`

### Phase 9 GitHub Issues

- #156 `[020][P1][macos/security] Make leakage finalization fail closed for delayed and late leakage`: T074, T075, T079, T080, T081
- #157 `[020][P1][macos] Bound WAV parsing and reject malformed finalization input`: T076, T077, T079, T081, T092
- #158 `[020][P1][security] Make local deletion registration truthful`: T078, T082, T083
- #159 `[020][P2][ux] Surface leakage-specific post-stop recording truth`: T084
- #160 `[020][P2][security] Harden issue-canon hooks against symlink writes and remote secret logs`: T086, T087
- #161 `[020][P1][tests] Keep feature acceptance blocked until validation evidence is complete`: T089, T090, T091, T092, T094

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 Setup**: No dependencies.
- **Phase 2 Foundational**: Depends on Phase 1; blocks all user stories.
- **US1, US2, US3**: Depend on Phase 2 and together form the P1 MVP.
- **US4**: Depends on US1 and US2 because diagnostics need finalization models and status outcomes.
- **US5**: Depends on Phase 2 and T003's go/no-go decision traceability; it can run alongside US4 once clean-room fixture scope is stable.
- **Polish**: Depends on selected user stories being complete.
- **Phase 9 Remediation**: Depends on the full review report and blocks feature acceptance, PR-ready status, and any final commit claim.

### User Story Dependencies

- **US1 (P1)**: First implementation increment after foundation.
- **US2 (P1)**: Can start after foundation but should integrate with US1 status rules.
- **US3 (P1)**: Can start after foundation and can run alongside US1/US2 after shared route metadata model exists.
- **US4 (P2)**: Starts after US1/US2 finalization fields exist.
- **US5 (P2)**: Starts after foundation and can finish after US4 diagnostics confirm clean-room metadata boundaries.

### Parallel Opportunities

- T003 and T004 can run in parallel after T001/T002 are understood.
- T006 through T016 touch model, redaction, fixture, lifecycle, and validation areas but should be merged carefully because several tasks share model and manifest files.
- US1 test tasks T017-T022 can run in parallel before implementation.
- US2 test tasks T030-T033 can run in parallel before implementation.
- US3 test tasks T040-T043 can run in parallel before implementation.
- US4 test tasks T049-T052 can run in parallel before implementation.
- US5 test tasks T058-T060 can run in parallel before implementation.
- Polish documentation tasks T064 and T065 can run in parallel after relevant story completion.

## Parallel Examples

### User Story 1

```text
Task: "T017 [P] [US1] Add leakage model tests in apps/macos/Shared/Tests/LeakageFinalizationModelTests.swift"
Task: "T018 [P] [US1] Add far-end-only leakage evaluator tests in apps/macos/Shared/Tests/LeakageFinalizationServiceTests.swift"
Task: "T019 [P] [US1] Add double-talk confidence downgrade tests in apps/macos/Shared/Tests/LeakageMeasurementTests.swift"
Task: "T021 [P] [US1] Add silence/noise/room echo/clipping/dropout fixture tests in apps/macos/Shared/Tests/LeakageMeasurementTests.swift"
Task: "T023 [P] [US1] Implement WAV reader helpers in apps/macos/RecApp/Sources/Capture/LeakageWAVReader.swift"
Task: "T024 [P] [US1] Implement leakage measurement rules in apps/macos/RecApp/Sources/Capture/LeakageMeasurementService.swift"
```

### User Story 3

```text
Task: "T040 [P] [US3] Add prerequisite gate tests in apps/macos/Shared/Tests/RecordingPrerequisiteGateTests.swift"
Task: "T041 [P] [US3] Add route metadata mapping tests in apps/macos/Shared/Tests/RecordingRouteMetadataTests.swift"
Task: "T042 [P] [US3] Add UI state tests in apps/macos/Shared/Tests/CaptureControlTests.swift"
```

### User Story 4

```text
Task: "T049 [P] [US4] Add diagnostic redaction tests in apps/macos/Shared/Tests/DiagnosticRedactionTests.swift"
Task: "T050 [P] [US4] Add diagnostic bundle tests in apps/macos/Shared/Tests/LeakageDiagnosticBundleTests.swift"
Task: "T051 [P] [US4] Add contract validation fixture tests in apps/macos/Shared/Tests/ContractTests/LeakageFinalizationContractTests.swift"
```

## Implementation Strategy

### MVP First

1. Complete Phase 1 and Phase 2.
2. Complete US1 to stop treating leaked/ambiguous local mic evidence as clean.
3. Complete US2 to make manifest/readiness truth fail closed.
4. Complete US3 to preserve the normal user flow.
5. Stop and validate P1 with `swift test --package-path apps/macos --disable-swift-testing`, `swift run --package-path apps/macos ContractValidation`, `sh tests/macos/static/audio-rt-safety-check.sh`, and the existing passthrough regression gate.

### Incremental Delivery

1. US1 delivers the first truthful finalization gate.
2. US2 makes package manifests and future MediaScribe readiness safe.
3. US3 preserves the normal user flow.
4. US4 adds support-safe diagnostics.
5. US5 keeps dependency and category behavior clean-room.

### Validation Commands

```sh
swift test --package-path apps/macos --disable-swift-testing
swift run --package-path apps/macos ContractValidation
sh tests/macos/static/audio-rt-safety-check.sh
sh apps/macos/Scripts/validate-real-bidirectional-passthrough.sh
```

## Notes

- No task adds live leakage cleanup during a meeting.
- No task adds route-readiness leakage blockers.
- No task adds direct desktop-to-MediaScribe upload, Langfuse content traces, dashboard publication, or external egress.
- Original `mic.wav` and `incoming.wav` must remain immutable evidence.
- Derived cleaned tracks are optional, separately labeled, registered for local retention/deletion accounting, and never replace original evidence.
