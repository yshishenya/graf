# Tasks: Meeting-App Mute Truth

**Input**: Design documents from `specs/022-meeting-mute-truth/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/](./contracts/), [quickstart.md](./quickstart.md)

**Tests**: Required. This feature touches privacy, microphone capture, artifact truth, UI warning copy, diagnostics, and release claims. Test tasks must be written first and fail before implementation.

**Organization**: Tasks are grouped by user story to enable independent implementation and testing.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel because it touches a different file and has no dependency on incomplete tasks.
- **[Story]**: Maps to user stories in [spec.md](./spec.md).
- Every task includes an exact file path.

## Phase 1: Setup

**Purpose**: Prepare evidence and fixture locations used by implementation and validation.

- [ ] T001 [P] Create mute-truth evidence scaffold in `specs/022-meeting-mute-truth/evidence/README.md`
- [ ] T002 [P] Create fixture documentation for mute-truth validation in `apps/macos/Shared/Tests/Fixtures/MeetingMuteTruth/README.md`
- [ ] T003 [P] Create validation script scaffold with usage text in `apps/macos/Scripts/validate-meeting-mute-truth.sh`

---

## Phase 2: Foundational Models And Contracts

**Purpose**: Add shared metadata types and manifest extension points required by every user story.

**Critical**: No user story implementation starts until the shared models, manifest wiring, and redaction contract are in place.

- [ ] T004 [P] Add failing shared model tests for `ProductPrivacySegment`, `MeetingMuteTruthEvidence`, `TargetMuteCapability`, and `MuteTruthDecision` in `apps/macos/Shared/Tests/MeetingMuteTruthTests.swift`
- [ ] T005 [P] Add failing manifest extension tests for privacy segments and mute-truth decision fields in `apps/macos/Shared/Tests/LocalRecordingManifestTests.swift`
- [ ] T006 [P] Add failing metadata-only redaction tests for mute-truth evidence in `apps/macos/Shared/Tests/MeetingMuteTruthDiagnosticTests.swift`
- [ ] T007 Implement shared mute-truth model types in `apps/macos/Shared/Sources/Models/MeetingMuteTruthModels.swift`
- [ ] T008 Extend local recording manifest fields for privacy segments, target capability, mute-truth decision, and limitation timestamp in `apps/macos/Shared/Sources/Models/AudioModels.swift`
- [ ] T009 Extend local recording failure/status enums for mute-truth degraded and unproven states where needed in `apps/macos/Shared/Sources/Models/AudioStates.swift`
- [ ] T010 Wire manifest creation, normalization, and JSON round-trip support for mute-truth fields in `apps/macos/RecApp/Sources/Capture/LocalRecordingManifestService.swift`
- [ ] T011 Extend diagnostic redaction coverage for mute-truth metadata while preserving forbidden content removal in `apps/macos/Shared/Sources/Diagnostics/DiagnosticRedactor.swift`

**Checkpoint**: Shared model and manifest foundation is ready; user story phases may begin.

---

## Phase 3: User Story 1 - Product Privacy Pause Is Not Recorded As Spoken Audio (Priority: P1) MVP

**Goal**: `2brain Pause` suppresses/redacts local microphone audio, records metadata-only privacy segments, and preserves visible Stop during pause.

**Independent Test**: Start a local recording fixture, enter `2brain Pause`, feed local mic samples, resume, and assert that the pause interval is silent/redacted in metadata and ordinary mic samples resume after the pause.

### Tests for User Story 1

- [ ] T012 [P] [US1] Add failing pause/resume state and Stop-available tests in `apps/macos/Shared/Tests/CaptureControlTests.swift`
- [ ] T013 [P] [US1] Add failing capture indicator tests for paused visible state in `apps/macos/Shared/Tests/CaptureIndicatorTests.swift`
- [ ] T014 [P] [US1] Add failing local writer suppression tests for paused mic samples in `apps/macos/Shared/Tests/LocalRecordingWriterTests.swift`
- [ ] T015 [P] [US1] Add failing manifest privacy-segment acceptance tests in `apps/macos/Shared/Tests/MeetingMuteTruthTests.swift`

### Implementation for User Story 1

- [ ] T016 [US1] Add privacy suppressing sample source for local microphone capture in `apps/macos/RecApp/Sources/Capture/PrivacySuppressingSampleSource.swift`
- [ ] T017 [US1] Integrate pause-aware mic sample suppression and privacy segment collection in `apps/macos/RecApp/Sources/Capture/LocalRecordingWriter.swift`
- [ ] T018 [US1] Persist pause/resume transitions through capture session state in `apps/macos/RecApp/Sources/Capture/CaptureSessionController.swift`
- [ ] T019 [US1] Add paused visible state, pause/resume actions, and Stop availability to native capture controls in `apps/macos/RecApp/Sources/Capture/CaptureControlView.swift`
- [ ] T020 [US1] Add paused state labels, accessibility identifiers, and localization-safe copy in `apps/macos/Shared/Sources/Models/SystemAudioCaptureModels.swift`
- [ ] T021 [US1] Integrate pause/resume actions and privacy segment finalization in `apps/macos/RecApp/App/TwoBrainRecApp.swift`

**Checkpoint**: User Story 1 can be validated independently with focused Swift tests and a local artifact fixture.

---

## Phase 4: User Story 2 - Fail Closed For Unproven Meeting-App Mute Claims (Priority: P1)

**Goal**: Unsupported or unobservable meeting-app mute truth shows limitation copy and creates an unproven/degraded artifact truth state instead of a mute-respecting claim.

**Independent Test**: Create a fixture for an unsupported target and assert that limitation copy is required, target status is unsupported/deferred, and the artifact never claims meeting-app-mute-respecting acceptance.

### Tests for User Story 2

- [ ] T022 [P] [US2] Add failing target matrix tests for Zoom native, Chrome/Telemost, Opera/Telemost, Yandex Browser, and unknown targets in `apps/macos/Shared/Tests/MeetingMuteTruthValidationTests.swift`
- [ ] T023 [P] [US2] Add failing limitation copy and accessibility tests in `apps/macos/Shared/Tests/SystemAudioLocalizationTests.swift`
- [ ] T024 [P] [US2] Add failing desktop warning visibility tests in `apps/macos/Shared/Tests/CaptureControlTests.swift`
- [ ] T025 [P] [US2] Add failing manifest decision tests for `meeting_mute_unproven`, `unsupported`, and `deferred` states in `apps/macos/Shared/Tests/MeetingMuteTruthTests.swift`

### Implementation for User Story 2

- [ ] T026 [US2] Implement target capability resolution and mute-truth decisions in `apps/macos/RecApp/Sources/Capture/MeetingMuteTruthService.swift`
- [ ] T027 [US2] Add required limitation copy, target warning labels, and accessibility text in `apps/macos/Shared/Sources/Models/SystemAudioCaptureModels.swift`
- [ ] T028 [US2] Show limitation warning without obscuring Pause/Resume/Stop in `apps/macos/RecApp/Sources/Capture/CaptureControlView.swift`
- [ ] T029 [US2] Attach target capability and mute-truth decision metadata during recording finalization in `apps/macos/RecApp/App/TwoBrainRecApp.swift`
- [ ] T030 [US2] Preserve unproven/degraded mute-truth state in manifest normalization in `apps/macos/RecApp/Sources/Capture/LocalRecordingManifestService.swift`

**Checkpoint**: User Story 2 can be validated independently from target fixtures and UI/static label tests.

---

## Phase 5: User Story 3 - Preserve Existing Capture Safety Boundaries (Priority: P1)

**Goal**: Existing visible capture, one-action Stop, local artifact persistence, role mapping, diagnostics, and no-egress boundaries still hold after mute-truth implementation.

**Independent Test**: Re-run existing capture/session, local recording, artifact format, diagnostic redaction, and no-egress checks with mute-truth metadata present.

### Tests for User Story 3

- [ ] T031 [P] [US3] Add regression tests proving existing recording evidence remains metadata-only with mute-truth fields in `apps/macos/Shared/Tests/DiagnosticRedactionTests.swift`
- [ ] T032 [P] [US3] Add regression tests proving upload queue completeness does not invent mute-respecting claims in `apps/macos/Shared/Tests/DesktopUploadQueueTests.swift`
- [ ] T033 [P] [US3] Add regression tests proving dual-track role mapping remains unchanged with mute-truth manifest fields in `apps/macos/Shared/Tests/LocalRecordingManifestTests.swift`

### Implementation for User Story 3

- [ ] T034 [US3] Add mute-truth metadata to diagnostic bundle safe fields without content-bearing payloads in `apps/macos/RecApp/Sources/Diagnostics/DiagnosticBundleService.swift`
- [ ] T035 [US3] Preserve existing upload queue dual-track completeness behavior and ensure mute-truth fields do not add or reinterpret upload decisions in `apps/macos/RecApp/Sources/Upload/DesktopUploadQueueService.swift`
- [ ] T036 [US3] Ensure capture status text distinguishes paused, degraded, failed, and local recording outcomes in `apps/macos/RecApp/Sources/Shared/AdaptiveStatusText.swift`
- [ ] T037 [US3] Re-run and update existing local recording contract validation coverage in `apps/macos/Shared/TestPlans/ContractValidationPlan.swift`

**Checkpoint**: User Story 3 can be validated with regression tests and existing local scripts.

---

## Phase 6: User Story 4 - Provide QA With Target-Specific Mute Truth Evidence (Priority: P2)

**Goal**: QA has a target matrix, safe fixture validation, and metadata-only evidence proving which targets are pause-validated, unsupported, or deferred.

**Independent Test**: Run the validation script against fixtures and a latest local artifact and confirm every matrix row has an explicit status without raw content.

### Tests for User Story 4

- [ ] T038 [P] [US4] Add fixture manifest JSON files for pause-validated, unsupported, deferred, and unsafe cases in `apps/macos/Shared/Tests/Fixtures/MeetingMuteTruth/pause-validated.json`, `apps/macos/Shared/Tests/Fixtures/MeetingMuteTruth/unsupported.json`, `apps/macos/Shared/Tests/Fixtures/MeetingMuteTruth/deferred.json`, and `apps/macos/Shared/Tests/Fixtures/MeetingMuteTruth/unsafe.json`
- [ ] T039 [P] [US4] Add failing validation script tests or fixture assertions in `apps/macos/Shared/Tests/MeetingMuteTruthValidationTests.swift`

### Implementation for User Story 4

- [ ] T040 [US4] Implement fixture and latest-artifact validation modes in `apps/macos/Scripts/validate-meeting-mute-truth.sh`
- [ ] T041 [US4] Document target matrix evidence expectations in `specs/022-meeting-mute-truth/evidence/target-matrix.md`
- [ ] T042 [US4] Document manual validation results template in `specs/022-meeting-mute-truth/evidence/manual-validation.md`

**Checkpoint**: User Story 4 can be validated through script output and committed metadata-only evidence templates.

---

## Final Phase: Polish, Documentation, And Validation

**Purpose**: Complete cross-cutting documentation, changelog, and quickstart evidence.

- [ ] T043 [P] Update current product status for meeting-app mute truth scope and remaining future adapter boundary in `docs/current-product-status.md`
- [ ] T044 [P] Add unreleased changelog entry for feature 022 in `CHANGELOG.md`
- [ ] T045 Run static forbidden-content and stale-marker scans from quickstart and record results in `specs/022-meeting-mute-truth/evidence/test-results.md`
- [ ] T046 Run `swift build`, `swift test`, and `swift run ContractValidation` in `apps/macos` and record results in `specs/022-meeting-mute-truth/evidence/test-results.md`
- [ ] T047 Run `apps/macos/Scripts/validate-meeting-mute-truth.sh --fixtures` and record results in `specs/022-meeting-mute-truth/evidence/test-results.md`
- [ ] T048 Run preserved capture/local-artifact scripts from quickstart and record results in `specs/022-meeting-mute-truth/evidence/test-results.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies.
- **Foundational (Phase 2)**: Depends on Setup completion and blocks all user stories.
- **US1 (Phase 3)**: Depends on Foundation; MVP privacy-control slice.
- **US2 (Phase 4)**: Depends on Foundation; can start after US1 tests exist, but final UI integration shares `CaptureControlView.swift` and `TwoBrainRecApp.swift` with US1.
- **US3 (Phase 5)**: Depends on US1 and US2 metadata behavior.
- **US4 (Phase 6)**: Depends on Foundation and can finalize after US1/US2 metadata is stable.
- **Final Phase**: Depends on all implemented user stories.

### User Story Dependencies

- **US1**: Must complete first for MVP because product-owned Pause is the canonical privacy truth.
- **US2**: May be implemented after shared foundation, but must integrate with US1 before validation.
- **US3**: Requires US1/US2 fields to preserve existing boundaries.
- **US4**: Requires final metadata fields and target decisions from US1/US2.

### Parallel Opportunities

- T001-T003 can run in parallel.
- T004-T006 can run in parallel before T007-T011.
- US1 test tasks T012-T015 can run in parallel.
- US2 test tasks T022-T025 can run in parallel.
- US3 test tasks T031-T033 can run in parallel.
- T043 and T044 can run in parallel after implementation stabilizes.

## Parallel Example: User Story 1

```text
Task: "Add failing pause/resume state and Stop-available tests in apps/macos/Shared/Tests/CaptureControlTests.swift"
Task: "Add failing capture indicator tests for paused visible state in apps/macos/Shared/Tests/CaptureIndicatorTests.swift"
Task: "Add failing local writer suppression tests for paused mic samples in apps/macos/Shared/Tests/LocalRecordingWriterTests.swift"
Task: "Add failing manifest privacy-segment acceptance tests in apps/macos/Shared/Tests/MeetingMuteTruthTests.swift"
```

## Implementation Strategy

### MVP First

1. Complete Phase 1 and Phase 2.
2. Complete US1 so product-owned Pause suppresses local mic speech and records privacy segments.
3. Validate US1 independently.
4. Add US2 claim fail-closed behavior and limitation copy.
5. Add US3 regression protection and US4 target evidence.

### Validation Strategy

1. Focused Swift tests first.
2. Contract validation second.
3. Script fixture validation third.
4. Existing capture/local-artifact regression scripts last.

## Notes

- `[P]` tasks touch different files and can be parallelized after dependencies.
- Every implementation task must update tests or validation evidence before being marked complete.
- Do not broaden scope into server upload, MediaScribe, Langfuse, retention, deletion, sharing, download, assisted recording, or third-party meeting-app mute adapters.
