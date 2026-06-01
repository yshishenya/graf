# Tasks: macOS Passthrough Release Hardening

**Input**: Design documents from `specs/005-macos-passthrough-release-hardening/`

**Prerequisites**: [spec.md](spec.md), [plan.md](plan.md), [research.md](research.md), [data-model.md](data-model.md), [contracts/](contracts/), [quickstart.md](quickstart.md), [checklists/](checklists/)

**Tests**: Tests and validation harnesses are required because this feature hardens Core Audio driver stability, app launch behavior, route recovery, installer lifecycle, diagnostics redaction, and non-recording UX before recording is added.

**Organization**: Tasks are grouped by independently testable user story and preserve the decision that full long-duration/manual replay acceptance is deferred until local recording exists.

## Phase 1: Setup

**Purpose**: Establish release-hardening fixtures, evidence locations, and validation entry points without changing runtime behavior yet.

- [X] T001 [P] Add release-hardening evidence fixture in `tests/macos/contract/release-hardening-evidence.json`.
- [X] T002 [P] Add no-hang evidence fixture in `tests/macos/contract/core-audio-no-hang-evidence.json`.
- [X] T003 [P] Add route recovery evidence fixture in `tests/macos/contract/route-recovery-evidence.json`.
- [X] T004 [P] Add installer lifecycle evidence fixture in `tests/macos/contract/installer-lifecycle-evidence.json`.
- [X] T005 [P] Add UX readiness evidence fixture in `tests/macos/contract/ux-readiness-evidence.json`.
- [X] T006 [P] Add release-hardening QA section in `qa/macos/release-candidate-checklist.md`.
- [X] T007 [P] Add 005 validation wrapper skeleton in `apps/macos/Scripts/validate-passthrough-release-hardening.sh`.
- [X] T008 [P] Add future recording-assisted acceptance placeholder in `qa/macos/recording-assisted-acceptance.md`.

---

## Phase 2: Foundational

**Purpose**: Shared metadata-only evidence models, redaction rules, and validation helpers that block all user stories.

**Critical**: No user story work should be accepted until this phase is complete.

- [X] T009 Add release-hardening evidence models in `apps/macos/Shared/Sources/Models/ReleaseHardeningEvidence.swift`.
- [X] T010 Add release-hardening evidence model tests in `apps/macos/Shared/Tests/ReleaseHardeningEvidenceTests.swift`.
- [X] T011 [P] Extend contract validation coverage for 005 fixtures in `apps/macos/Shared/Tests/ContractTests/ReleaseHardeningContractTests.swift`.
- [X] T012 [P] Extend diagnostic redaction denylist and allowlist fixtures for release evidence in `apps/macos/Shared/Tests/DiagnosticRedactionTests.swift`.
- [X] T013 Add metadata-only evidence writer support in `apps/macos/RecApp/Sources/Diagnostics/DiagnosticBundleService.swift`.
- [X] T014 Add release-hardening audit event names in `apps/macos/Shared/Sources/Audit/AuditEvents.swift`.
- [X] T015 Add release-hardening result mapping for passed/blocked/not_accepted in `apps/macos/Shared/Sources/Models/AudioStates.swift`.
- [X] T016 Wire build, runtime probe, static realtime check, and existing passthrough validation into `apps/macos/Scripts/validate-passthrough-release-hardening.sh`.
- [X] T017 Update `apps/macos/AudioDriver/RuntimeProofReport.md` with a 005 section for pre-recording hardening evidence.

**Checkpoint**: Shared evidence and validation scaffolding exist, with no recording, transcription, upload, or external egress.

---

## Phase 3: User Story 1 - Prove Pre-Recording Stability Gates (Priority: P1) MVP

**Goal**: Prove installed non-recording passthrough remains stable and measurable before local recording work begins.

**Independent Test**: Build/install locally, run runtime probes and short smoke evidence capture, and record metadata-only stability results without long-duration replay.

### Tests for User Story 1

- [X] T018 [P] [US1] Add default non-recording startup regression tests in `apps/macos/Shared/Tests/LivePassthroughPolicyTests.swift`.
- [X] T019 [P] [US1] Add short smoke evidence contract tests in `apps/macos/Shared/Tests/ShortSmokeEvidenceTests.swift`.
- [X] T020 [P] [US1] Add idle running-state expectation coverage in `apps/macos/AudioDriver/Sources/Proof/RuntimeDeviceProbe.cpp`.
- [X] T021 [P] [US1] Add no-recording/no-upload policy scan notes in `tests/macos/browser-meetings/offline-passthrough.md`.

### Implementation for User Story 1

- [X] T022 [US1] Ensure automatic startup remains limited to non-recording passthrough in `apps/macos/RecApp/Sources/Capture/PassthroughRouteEngine.swift`.
- [X] T023 [US1] Add short smoke evidence collection fields to `apps/macos/Shared/Sources/Models/ReleaseHardeningEvidence.swift`.
- [X] T024 [US1] Record short smoke metadata without audio payloads in `apps/macos/RecApp/Sources/Diagnostics/DiagnosticBundleService.swift`.
- [X] T025 [US1] Add installed runtime baseline command path to `apps/macos/Scripts/validate-passthrough-release-hardening.sh`.
- [X] T026 [US1] Update `qa/macos/browser-targets.md` to distinguish short smoke evidence from future long-duration acceptance.
- [X] T027 [US1] Update `qa/macos/release-candidate-checklist.md` with pre-recording stability gate acceptance and blocker states.

**Checkpoint**: US1 is independently testable with installed runtime probes and metadata-only short smoke evidence.

---

## Phase 4: User Story 2 - Prove Core Audio And App Surfaces Do Not Hang (Priority: P1)

**Goal**: Prove common macOS, browser, Zoom, and Telemost audio settings surfaces remain responsive while the driver is installed and passthrough is active.

**Independent Test**: Launch each target surface through the local no-hang harness and record open-time, CPU, and route-state evidence.

### Tests for User Story 2

- [X] T028 [P] [US2] Add no-hang evidence model tests in `apps/macos/Shared/Tests/CoreAudioNoHangEvidenceTests.swift`.
- [X] T029 [P] [US2] Add no-hang checklist contract in `tests/macos/installer-recovery/coreaudiod-no-hang-check.md`.
- [X] T030 [P] [US2] Add CPU threshold fixture coverage in `tests/macos/contract/core-audio-no-hang-evidence.json`.
- [X] T031 [P] [US2] Add settings-surface target matrix in `tests/macos/browser-meetings/audio-settings-no-hang-matrix.md`.

### Implementation for User Story 2

- [X] T032 [US2] Add `coreaudiod` CPU sampler helper in `apps/macos/Scripts/coreaudiod-cpu-sample.sh`.
- [X] T033 [US2] Add local target launch timing helper in `apps/macos/Scripts/audio-settings-no-hang-check.sh`.
- [X] T034 [US2] Wire no-hang and CPU gates into `apps/macos/Scripts/validate-passthrough-release-hardening.sh`.
- [X] T035 [US2] Record no-hang evidence through `apps/macos/RecApp/Sources/Diagnostics/DiagnosticBundleService.swift`.
- [X] T036 [US2] Update `qa/macos/release-candidate-checklist.md` with macOS Sound, Chrome, Opera, Zoom, and Telemost no-hang outcomes.
- [X] T037 [US2] Update `apps/macos/AudioDriver/RuntimeProofReport.md` with no-hang and CPU evidence fields.

**Checkpoint**: US2 is independently testable by running no-hang targets and CPU sampling without recording or upload.

---

## Phase 5: User Story 3 - Recover From Route And System Changes (Priority: P1)

**Goal**: Prove device changes, stale browser IDs, `coreaudiod` restart, and sleep/wake fail clearly and recover only after valid route evidence.

**Independent Test**: Trigger route/system changes and record stale/degraded/blocked or ready-after-evidence transitions within the required window.

### Tests for User Story 3

- [X] T038 [P] [US3] Add route recovery evidence tests in `apps/macos/Shared/Tests/RouteRecoveryEvidenceTests.swift`.
- [X] T039 [P] [US3] Add `coreaudiod` restart recovery checklist in `tests/macos/installer-recovery/coreaudiod-release-hardening-recovery.md`.
- [X] T040 [P] [US3] Add sleep/wake release-hardening checklist in `tests/macos/physical-devices/sleep-wake-release-hardening.md`.
- [X] T041 [P] [US3] Add stale browser device-ID checklist in `tests/macos/browser-meetings/stale-device-id-recovery.md`.
- [X] T042 [P] [US3] Add aggregate and multi-output route checklist in `tests/macos/physical-devices/aggregate-multi-output-route.md`.

### Implementation for User Story 3

- [X] T043 [US3] Ensure route invalidation emits stale/degraded/blocked within 5 seconds in `apps/macos/RecApp/Sources/AudioHealth/AudioEnvironmentMonitor.swift`.
- [X] T044 [US3] Ensure `coreaudiod` restart clears stale ready state before recovery in `apps/macos/RecApp/Sources/Capture/PassthroughRouteEngine.swift`.
- [X] T045 [US3] Add sleep/wake route recheck handling in `apps/macos/RecApp/Sources/AudioHealth/AudioEnvironmentMonitor.swift`.
- [X] T046 [US3] Add route recovery evidence fields to `apps/macos/Shared/Sources/Models/ReleaseHardeningEvidence.swift`.
- [X] T047 [US3] Record route recovery diagnostics in `apps/macos/RecApp/Sources/Diagnostics/DiagnosticBundleService.swift`.
- [X] T048 [US3] Wire recovery checklist prompts into `apps/macos/Scripts/validate-passthrough-release-hardening.sh`.
- [X] T049 [US3] Update `qa/macos/device-matrix.md` with physical, aggregate, Bluetooth, stale-ID, `coreaudiod`, and sleep/wake result semantics.

**Checkpoint**: US3 is independently testable through route recovery metadata and truthful route state transitions.

---

## Phase 6: User Story 4 - Trust Installer And Repair Flows After Passthrough (Priority: P2)

**Goal**: Prove install, update, repair, rollback, uninstall, and reinstall remain safe after passthrough work.

**Independent Test**: Run each installer lifecycle scenario and record passed/blocked/not_accepted evidence without hidden manual cleanup.

### Tests for User Story 4

- [ ] T050 [P] [US4] Add installer lifecycle evidence tests in `apps/macos/Shared/Tests/InstallerLifecycleEvidenceTests.swift`.
- [ ] T051 [P] [US4] Add install/update/repair checklist in `tests/macos/installer-recovery/install-update-repair-release-hardening.md`.
- [ ] T052 [P] [US4] Add rollback/uninstall/reinstall checklist in `tests/macos/installer-recovery/rollback-uninstall-reinstall-release-hardening.md`.
- [ ] T053 [P] [US4] Add installer lifecycle fixture coverage in `tests/macos/contract/installer-lifecycle-evidence.json`.

### Implementation for User Story 4

- [ ] T054 [US4] Add installer lifecycle command wrapper in `apps/macos/Scripts/installer-lifecycle-release-hardening.sh`.
- [ ] T055 [US4] Wire installer lifecycle gate into `apps/macos/Scripts/validate-passthrough-release-hardening.sh`.
- [ ] T056 [US4] Add installer lifecycle evidence fields to `apps/macos/Shared/Sources/Models/ReleaseHardeningEvidence.swift`.
- [ ] T057 [US4] Record installer lifecycle diagnostics in `apps/macos/RecApp/Sources/Diagnostics/DiagnosticBundleService.swift`.
- [ ] T058 [US4] Update `qa/macos/driver-lifecycle-checklist.md` with 005 passed/blocked/not_accepted evidence rules.
- [ ] T059 [US4] Audit `apps/macos/Installer/Scripts/repair.sh`, `apps/macos/Installer/Scripts/rollback.sh`, and `apps/macos/Installer/Scripts/uninstall.sh`; either fix stale Core Audio cleanup gaps or record no-change rationale in `qa/macos/driver-lifecycle-checklist.md`.

**Checkpoint**: US4 is independently testable through installer lifecycle commands and metadata-only evidence.

---

## Phase 7: User Story 5 - Show Truthful Non-Recording UX And Diagnostics (Priority: P2)

**Goal**: Make app status and diagnostics truthful: passthrough may be active, recording is not, degraded states are not presented as safe, and shared artifacts contain no secrets or meeting content.

**Independent Test**: Review ready/active/stale/degraded/failed/repair states and scan diagnostics/evidence for forbidden content.

### Tests for User Story 5

- [ ] T060 [P] [US5] Add UX readiness evidence tests in `apps/macos/Shared/Tests/UXReadinessEvidenceTests.swift`.
- [ ] T061 [P] [US5] Extend diagnostic redaction tests for release-hardening evidence in `apps/macos/Shared/Tests/DiagnosticRedactionTests.swift`.
- [ ] T062 [P] [US5] Add non-recording copy review checklist in `qa/macos/non-recording-passthrough-ux.md`.
- [ ] T063 [P] [US5] Add diagnostics forbidden-field fixture coverage in `tests/macos/contract/diagnostic-forbidden-fields.json`.

### Implementation for User Story 5

- [ ] T064 [US5] Update non-recording passthrough status copy in `apps/macos/RecApp/Sources/AudioHealth/AudioHealthView.swift`.
- [ ] T065 [US5] Update readiness and repair action copy in `apps/macos/RecApp/Sources/AudioSetup/RouteVerificationView.swift`.
- [ ] T066 [US5] Ensure visibility-only device publication cannot render ready UI in `apps/macos/RecApp/Sources/AudioSetup/RouteVerificationService.swift`.
- [ ] T067 [US5] Add UX readiness evidence fields to `apps/macos/Shared/Sources/Models/ReleaseHardeningEvidence.swift`.
- [ ] T068 [US5] Add diagnostics redaction scan command to `apps/macos/Scripts/validate-passthrough-release-hardening.sh`.
- [ ] T069 [US5] Update `qa/macos/driver-gate-approval.md` with non-recording UX and diagnostics acceptance gates.

**Checkpoint**: US5 is independently testable through UI evidence review and diagnostics redaction scans.

---

## Phase 8: User Story 6 - Define Recording-Assisted Acceptance For The Next Slice (Priority: P3)

**Goal**: Preserve the future long-duration acceptance matrix without making it a blocker before recording exists.

**Independent Test**: Review the future checklist and confirm every recording-derived evidence item is blocked until local recording, retention, and deletion rules exist.

### Tests for User Story 6

- [ ] T070 [P] [US6] Add deferred recording acceptance tests in `apps/macos/Shared/Tests/DeferredRecordingAcceptanceTests.swift`.
- [ ] T071 [P] [US6] Add deferred acceptance contract fixture in `tests/macos/contract/deferred-recording-acceptance.json`.

### Implementation for User Story 6

- [ ] T072 [US6] Complete future recording-assisted checklist in `qa/macos/recording-assisted-acceptance.md`.
- [ ] T073 [US6] Add deferred recording gate state to `apps/macos/Shared/Sources/Models/ReleaseHardeningEvidence.swift`.
- [ ] T074 [US6] Update `specs/005-macos-passthrough-release-hardening/quickstart.md` with the blocked-until-recording rule after implementation details settle.
- [ ] T075 [US6] Update `qa/macos/release-candidate-checklist.md` so long-duration replay is visible as a future gate, not a current blocker.

**Checkpoint**: US6 is independently testable as documentation/model coverage without creating recording artifacts.

---

## Final Phase: Polish & Cross-Cutting Validation

**Purpose**: Run complete validation, analyze consistency, and prepare review artifacts.

- [ ] T076 Run `swift build --package-path apps/macos -c release --product TwoBrainRecApp` and record result in `apps/macos/AudioDriver/RuntimeProofReport.md`.
- [ ] T077 Run `swift test --package-path apps/macos --disable-swift-testing` and record result in `apps/macos/AudioDriver/RuntimeProofReport.md`.
- [ ] T078 Run `sh tests/macos/static/audio-rt-safety-check.sh` and record result in `apps/macos/AudioDriver/RuntimeProofReport.md`.
- [ ] T079 Run `make -C apps/macos/AudioDriver proof-plugin-build proof-runtime-probe-build proof-hal-io-probe-build` and record result in `apps/macos/AudioDriver/RuntimeProofReport.md`.
- [ ] T080 Run `sh apps/macos/Scripts/validate-real-bidirectional-passthrough.sh` and record result in `apps/macos/AudioDriver/RuntimeProofReport.md`.
- [ ] T081 Run `sh apps/macos/Scripts/validate-passthrough-release-hardening.sh` and record result in `apps/macos/AudioDriver/RuntimeProofReport.md`.
- [ ] T082 Scan `apps/macos`, `tests/macos`, `qa/macos`, and `specs/005-macos-passthrough-release-hardening` for raw audio, transcript text, credentials, tokens, signed URLs, passwords, and meeting content.
- [ ] T083 Re-run `$speckit-analyze` and resolve all critical/high findings in `specs/005-macos-passthrough-release-hardening/`.
- [ ] T084 Update `specs/005-macos-passthrough-release-hardening/tasks.md` so completed tasks are marked `[X]` only after validation evidence exists.

---

## Dependencies & Execution Order

### Phase Dependencies

- Phase 1 Setup has no dependencies.
- Phase 2 Foundational depends on Phase 1 and blocks all user stories.
- User Stories 1, 2, and 3 are P1 and should be completed before P2/P3 acceptance.
- User Story 4 depends on Foundational and can run after the installed runtime baseline from US1 exists.
- User Story 5 depends on Foundational and can run in parallel with US4 after route states are modeled.
- User Story 6 depends on Foundational and can run after evidence models exist.
- Final validation depends on all selected user stories and must run before implementation acceptance.

### User Story Dependencies

- US1 has no dependency on other user stories after Foundational.
- US2 can start after Foundational but needs US1's validation wrapper path for final integration.
- US3 can start after Foundational but needs US1/US2 route state semantics for complete evidence.
- US4 can start after US1 installed runtime baseline tasks T025-T027.
- US5 can start after Foundational but final copy must align with US3 route states.
- US6 can start after Foundational and remains documentation/model-only for this slice.

### Task Dependencies

- T009-T017 block all user-story implementation tasks.
- T022-T027 depend on T018-T021.
- T032-T037 depend on T028-T031.
- T043-T049 depend on T038-T042.
- T054-T059 depend on T050-T053 and T025.
- T064-T069 depend on T060-T063 and route state definitions from T015.
- T072-T075 depend on T070-T071 and T009.
- T076-T084 depend on all implemented story tasks selected for the slice.

## Parallel Opportunities

- T001-T008 can run in parallel because they touch separate fixture, QA, and script files.
- T010-T012 and T014-T015 can run in parallel after T009 is started.
- T018-T021 can run in parallel for US1 test coverage.
- T028-T031 can run in parallel for US2 test/checklist coverage.
- T038-T042 can run in parallel for US3 recovery checklist coverage.
- T050-T053 can run in parallel for US4 installer evidence coverage.
- T060-T063 can run in parallel for US5 UX and diagnostics coverage.
- T070-T071 can run in parallel for US6 deferred-gate coverage.

## Parallel Example: User Story 2

```text
Task: "T028 [P] [US2] Add no-hang evidence model tests in apps/macos/Shared/Tests/CoreAudioNoHangEvidenceTests.swift"
Task: "T029 [P] [US2] Add no-hang checklist contract in tests/macos/installer-recovery/coreaudiod-no-hang-check.md"
Task: "T030 [P] [US2] Add CPU threshold fixture coverage in tests/macos/contract/core-audio-no-hang-evidence.json"
Task: "T031 [P] [US2] Add settings-surface target matrix in tests/macos/browser-meetings/audio-settings-no-hang-matrix.md"
```

## Implementation Strategy

### MVP First

1. Complete Phase 1 Setup.
2. Complete Phase 2 Foundational.
3. Complete Phase 3 US1 for installed pre-recording stability evidence.
4. Stop and validate US1 independently before no-hang/recovery work is accepted.

### Incremental Delivery

1. Add US1 pre-recording stability gates.
2. Add US2 no-hang and CPU evidence.
3. Add US3 route and system recovery evidence.
4. Add US4 installer lifecycle evidence.
5. Add US5 truthful UX and diagnostics gates.
6. Add US6 deferred recording-assisted acceptance artifact.
7. Run full quickstart validation and `$speckit-analyze`.

### Quality Gates

- Do not add recording, transcription, upload, MediaScribe, Langfuse, MinIO, Postgres, Temporal, Docker, analytics, or server workflows in this feature.
- Do not mark skipped targets as passed.
- Do not mark long-duration call replay accepted until local recording, retention, and deletion rules exist.
- Do not commit raw audio, transcript text, credentials, tokens, signed URLs, passwords, or meeting content.
