# Tasks: Remove Legacy Separate Audio Driver

**Input**: Design documents from
`/specs/102-remove-legacy-audio-driver/`

**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`,
`contracts/`, all requirement-quality checklists.

**Tests**: Required because this is a high-risk capture-architecture removal and
the user explicitly requires repeated proof that the current recording scheme
does not regress.

**Organization**: Tasks are grouped by user story. Deletion is dependency-driven:
first lock current invariants, then cut mixed callers, then delete leaf clusters.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel with other tasks in the same phase when its
  listed files do not overlap.
- **[Story]**: User story from `spec.md`.
- Tasks are marked `[X]` only after their stated validation evidence exists.

## Phase 1: Setup and Baseline

**Purpose**: Establish a comparison point for the supported recording graph.

- [X] T001 Record the pre-change 62-test zero-failure baseline for `LocalRecordingWriterSystemAudioTests`, `SystemAudioCaptureServiceTests`, `MicrophoneCaptureServiceTests`, `RecordingPrerequisiteGateTests`, `SystemAudioRecordingPackageTests`, and `CaptureSessionSafetyTests` in `specs/102-remove-legacy-audio-driver/plan.md` and `specs/102-remove-legacy-audio-driver/quickstart.md`

---

## Phase 2: Foundational Safety Gates

**Purpose**: Protect current capture/data contracts before broad deletion.

**⚠️ CRITICAL**: Complete this phase before deleting source clusters.

- [X] T002 [P] Add a read-only failing-first retirement guard for exact forbidden paths, symbols, payloads, flags, and active roots in `apps/macos/Scripts/validate-no-legacy-audio-driver.sh`
- [X] T003 [P] Add backward-read coverage for unknown removed manifest keys, retained `legacy_recorder_fallback`, and the legacy recording root in `apps/macos/Shared/Tests/LocalRecordingManifestTests.swift` and `apps/macos/Shared/Tests/LocalRecordingStoreTests.swift`
- [X] T004 Refactor `PhysicalWorkingDeviceKind` into `apps/macos/Shared/Sources/Models/SystemAudioCaptureModels.swift`, replace driver-specific self-routing logic with a generic fail-closed microphone-input policy in `apps/macos/Shared/Sources/Capture/RecordingMicrophoneInputPolicy.swift` and `apps/macos/RecApp/Sources/Capture/MicrophoneCaptureService.swift`, and update `apps/macos/Shared/Tests/RecordingMicrophoneSelectionTests.swift` plus `apps/macos/Shared/Tests/MicrophoneCaptureServiceTests.swift`
- [X] T005 Remove `SharedMemoryRecordingSampleSource`, `sharedMemoryFactory`, and the implicit shared-memory incoming fallback while preserving explicit injected sources and current meters in `apps/macos/RecApp/Sources/Capture/LocalRecordingWriter.swift`, `apps/macos/Shared/Tests/LocalRecordingWriterTests.swift`, and `apps/macos/Shared/Tests/LocalRecordingWriterSystemAudioTests.swift`
- [X] T006 Replace `LiveRouteSignalLevels` with existing `LiveRecordingLevels` throughout `apps/macos/RecApp/Sources/Capture/CaptureControlView.swift`, `apps/macos/RecApp/App/TwoBrainRecApp.swift`, and `apps/macos/Shared/Tests/CaptureControlTests.swift`

**Checkpoint**: Current source ownership, compatibility, and meters are protected
without shared memory; the retirement guard still fails on known legacy code.

---

## Phase 3: User Story 1 - Ship Only The System-Audio-First Product (Priority: P1) 🎯 MVP

**Goal**: Remove every executable/build/install/UI path that can publish or use
the separate driver while keeping the app and app-only installer buildable.

**Independent Test**: Build `TwoBrainRecApp` and the local installer from a clean
scratch directory; inspect the distribution and observe one desktop component,
zero HAL payloads/choices, and no driver startup/setup surface.

### Tests for User Story 1

- [X] T007 [P] [US1] Rewrite app packaging assertions to require exactly one desktop component and reject any HAL/driver distribution entry in `apps/macos/Shared/Tests/InstallerPackagingTests.swift` and `apps/macos/Shared/Tests/InstallerLifecycleEvidenceTests.swift`

### Implementation for User Story 1

- [X] T008 [US1] Remove passthrough coordinator state, launch flags, termination hooks, driver/route diagnostics, route trigger evidence, and the driver-shaped `LocalAudioSnapshot`/private virtual-device enumeration while retaining current shell status and recording composition in `apps/macos/RecApp/App/TwoBrainRecApp.swift`
- [X] T009 [P] [US1] Delete legacy capture/diagnostic/setup/installer source files in `apps/macos/RecApp/Sources/Capture/PassthroughBridge.swift`, `apps/macos/RecApp/Sources/Capture/PassthroughRouteEngine.swift`, `apps/macos/RecApp/Sources/Capture/ExperimentalPassthroughCoordinator.swift`, `apps/macos/RecApp/Sources/Capture/LiveAudioSignalMonitor.swift`, `apps/macos/RecApp/Sources/Capture/LiveRouteAutorepairCoordinator.swift`, `apps/macos/RecApp/Sources/Diagnostics/RouteEvidenceStore.swift`, `apps/macos/RecApp/Sources/AudioSetup/`, `apps/macos/RecApp/Sources/AudioHealth/`, and `apps/macos/RecApp/Sources/Installer/`
- [X] T010 [US1] Prune driver, virtual-device, passthrough, live-route, low-resource, app-bridge, installer, and parked-readiness types while retaining physical-device, leakage, meeting-detection, and current capture entities in `apps/macos/Shared/Sources/Models/AudioModels.swift`, `apps/macos/Shared/Sources/Models/AudioStates.swift`, `apps/macos/Shared/Sources/Models/SystemAudioCaptureModels.swift`, `apps/macos/Shared/Sources/Audit/AuditEvents.swift`, `apps/macos/Shared/Sources/Diagnostics/DiagnosticRedactor.swift`, and `apps/macos/RecApp/Sources/Shared/AdaptiveStatusText.swift`
- [X] T011 [P] [US1] Delete the obsolete route/model/runtime cluster in `apps/macos/Shared/Sources/Models/LowResourceAudioModels.swift`, `apps/macos/Shared/Sources/Models/LiveRouteEvidenceModels.swift`, `apps/macos/Shared/Sources/Models/RecordingTimelineEvidence.swift`, `apps/macos/Shared/Sources/Diagnostics/RouteEvidenceEvent.swift`, and `apps/macos/Shared/Sources/Routing/` except the generalized current microphone-input policy retained by T004
- [X] T012 [US1] Remove the `CShmHelpers` target/dependency from `apps/macos/Package.swift`, preserve `apps/macos/AudioDriver/RuntimeProofReport.md` under `docs/evidence/legacy-audio-driver/RuntimeProofReport.md`, then delete `apps/macos/AudioDriver/`, `apps/macos/Shared/CShmHelpers/`, and `apps/macos/Shared/Sources/SharedAudioMemory.swift`
- [X] T013 [P] [US1] Make local packaging and uninstall strictly app-only in `apps/macos/Installer/Scripts/build-local-installer.sh`, `apps/macos/Installer/Scripts/uninstall.sh`, and `apps/macos/Installer/README.md`, and delete `apps/macos/Installer/Scripts/postinstall.sh`, `apps/macos/Installer/Scripts/repair.sh`, and `apps/macos/Installer/Scripts/rollback.sh`
- [X] T014 [US1] Build `TwoBrainRecApp`, build the installer into a scratch directory, expand it with `pkgutil`, and record metadata-only component/payload evidence in `specs/102-remove-legacy-audio-driver/quickstart.md`

**Checkpoint**: A clean build and installer expose only the accepted app-owned
system-audio product; no legacy component is executable or packageable.

---

## Phase 4: User Story 2 - Preserve Accepted Recording Truth (Priority: P1)

**Goal**: Remove obsolete route semantics from current start/stop evidence while
proving the native dual-source recording path is unchanged.

**Independent Test**: Re-run the same six-suite baseline selection plus current permission,
resource-release, alignment, artifact-format, and diagnostic-redaction checks.

### Tests for User Story 2

- [X] T015 [P] [US2] Rewrite prerequisite/evidence tests around combined current capture permissions and `CaptureSessionState`, removing live-route/publication cases in `apps/macos/Shared/Tests/RecordingPrerequisiteGateTests.swift`, `apps/macos/Shared/Tests/RecordingEvidenceTests.swift`, and `apps/macos/Shared/Tests/CaptureSessionSafetyTests.swift`
- [X] T016 [P] [US2] Add a manifest round-trip assertion that new current recordings emit no route lifecycle, HAL, driver, shared-memory, or passthrough keys in `apps/macos/Shared/Tests/LocalRecordingManifestTests.swift` and `apps/macos/Shared/Tests/SystemAudioManifestContractTests.swift`

### Implementation for User Story 2

- [X] T017 [US2] Simplify `RecordingPrerequisiteSnapshot`, `RecordingPrerequisiteGate`, current meeting-detection prerequisites, and blocker/stop enums to current capture policy/permission/storage/indicator/source truth in `apps/macos/Shared/Sources/Models/AudioModels.swift`, `apps/macos/Shared/Sources/Models/AudioStates.swift`, `apps/macos/RecApp/Sources/Capture/RecordingPrerequisiteGate.swift`, `apps/macos/RecApp/Sources/Capture/CaptureRecoveryService.swift`, and `apps/macos/RecApp/App/TwoBrainRecApp.swift`
- [X] T018 [US2] Replace recording evidence route state with current capture session state, remove obsolete timeline evidence from the current manifest/service, and keep generic leakage route metadata in `apps/macos/RecApp/Sources/Capture/RecordingEvidenceService.swift`, `apps/macos/RecApp/Sources/Capture/LocalRecordingManifestService.swift`, `apps/macos/RecApp/Sources/Capture/RecordingRouteMetadataService.swift`, and `apps/macos/Shared/Sources/Models/AudioModels.swift`
- [X] T019 [US2] Delete driver/live-route bundle builders and keys while retaining current capture, artifact, upload, mute, leakage, and metadata-only diagnostic builders in `apps/macos/RecApp/Sources/Diagnostics/DiagnosticBundleService.swift` and `apps/macos/Shared/Tests/DiagnosticRedactionTests.swift`
- [X] T020 [US2] Re-run the baseline suite and current `SystemAudioPermission*`, `SystemAudioResourceReleaseTests`, `SystemAudioTrackAlignmentTests`, `CaptureIndicatorTests`, and recording artifact validators; document any intentional driver-only test-count reduction in `specs/102-remove-legacy-audio-driver/quickstart.md`

**Checkpoint**: Current capture start, live state, Stop, dual-track finalization,
and diagnostics pass without legacy route fields or fallback behavior.

---

## Phase 5: User Story 3 - Leave No Active Legacy Maintenance Surface (Priority: P1)

**Goal**: Remove obsolete active tests/commands/docs and make the retirement
boundary continuously enforceable.

**Independent Test**: Run the retirement guard with its narrow historical
allowlist, all remaining Swift tests/contracts, and repository CI; zero
unexplained active references remain.

### Implementation and Validation for User Story 3

- [X] T021 [P] [US3] Prune legacy validations/call sites while retaining current recording, permission, artifact, redaction, upload, mute, and safety contracts in `apps/macos/Shared/Tools/ContractValidation/main.swift` and delete obsolete JSON fixtures under `tests/macos/contract/`
- [X] T022 [P] [US3] Delete driver/passthrough/live-route/low-resource/shared-memory XCTest families under `apps/macos/Shared/Tests/` and obsolete route-synthetic/driver-installer scenarios under `tests/macos/`, preserving current system-audio, microphone, artifact, device, upload, and meeting-detection coverage
- [X] T023 [US3] Replace obsolete driver validators with the retirement guard, adapt current capture/package validators, and delete legacy scripts in `apps/macos/Scripts/validate-foundation.sh`, `apps/macos/Scripts/validate-system-audio-capture-pivot.sh`, `apps/macos/Scripts/validate-system-audio-no-hal-probe.sh`, and the driver/passthrough/low-resource script families under `apps/macos/Scripts/`
- [X] T024 [US3] Run the no-driver guard unconditionally and the macOS Swift build/test/contracts conditionally on Darwin from `infra/scripts/ci-local.sh` without changing existing server/RLS/Docker gates
- [X] T025 [P] [US3] Remove obsolete runnable QA gates and reconcile current system-audio/device/indicator/release guidance in `qa/macos/` and `tests/macos/browser-meetings/` without rewriting completed Spec Kit history
- [X] T026 [US3] Update active architecture truth and retirement evidence in `AGENTS.md`, `apps/macos/README.md`, `docs/current-product-status.md`, `docs/prd-voice-layer-final.md`, `docs/agent-guidance/product-gates.md`, `docs/adr/002-system-audio-first-mvp-pivot.md`, new `docs/adr/004-remove-legacy-separate-audio-driver.md`, `specs/072-deep-architecture-audit/findings-register.md`, `specs/072-deep-architecture-audit/dependency-graphs.md`, and `CHANGELOG.md`

**Checkpoint**: Active code, packaging, tests, QA, docs, and CI describe and
enforce one capture architecture; history remains explicitly historical.

---

## Phase 6: User Story 4 - Handle Existing Local Proof Installations Safely (Priority: P2)

**Goal**: Make source retirement truthful for Macs that may still contain an
old proof bundle without adding automatic privileged cleanup code.

**Independent Test**: Review the bounded operator procedure for absent and exact
known component cases; static validation proves normal build/test/install paths
contain no removal, `sudo`, broad HAL mutation, or `coreaudiod` restart.

- [X] T027 [P] [US4] Document read-only inspection and explicit exact-component cleanup boundaries, preservation rules, and active-call precautions in `docs/agent-guidance/legacy-audio-driver-cleanup.md` and link it from `docs/agent-guidance/README.md`
- [X] T028 [US4] Add normal-path host-mutation absence patterns to `apps/macos/Scripts/validate-no-legacy-audio-driver.sh` and document absent/exact/lookalike cases in `specs/102-remove-legacy-audio-driver/quickstart.md`

**Checkpoint**: Repository and host state are not conflated; no automated
privileged migration is introduced.

---

## Phase 7: Polish and Cross-Cutting Closeout

**Purpose**: Prove the complete diff, simplify it, and prepare review evidence.

- [X] T029 Apply the Ponytail deletion/reuse review from `docs/agent-guidance/ponytail-upstream.md`, remove leftover abstractions/dependencies, and record any intentional ceiling/upgrade path in `specs/102-remove-legacy-audio-driver/plan.md`
- [X] T030 Run every command in `specs/102-remove-legacy-audio-driver/quickstart.md` except privileged host cleanup/manual recording, run a clean scratch Swift build/test/package expansion, and record metadata-only results in `specs/102-remove-legacy-audio-driver/quickstart.md`
- [X] T031 Run `infra/scripts/ci-local.sh`, re-run `apps/macos/Scripts/validate-no-legacy-audio-driver.sh`, and require zero failures and zero unexplained active matches before marking implementation tasks complete
- [X] T032 Reconcile `[X]` task status with actual evidence, add GitHub issue/PR references and the selected high-risk/no-deploy lane to `specs/102-remove-legacy-audio-driver/tasks.md`, then request explicit user approval before any implementation commit

## Implementation Closeout

- **Risk / validation lane**: high-risk capture-architecture removal; full Spec
  Kit, focused recording proof, clean-scratch Swift/package proof, and canonical
  local CI. No deploy, install, uninstall, privileged host cleanup, or audio
  service restart.
- **GitHub issues**: T002-T032 are tracked by open issues
  [#3191](https://github.com/yshishenya/crisp/issues/3191) through
  [#3221](https://github.com/yshishenya/crisp/issues/3221); exact task mappings
  are encoded in their canonical titles.
- **Pull request**: [#3222](https://github.com/yshishenya/crisp/pull/3222),
  opened ready for review against `master` with closing references for
  #3191–#3221.
- **Implementation commit**:
  [`9a9179d3`](https://github.com/yshishenya/crisp/commit/9a9179d3ca5495bb31db2084e818ea16d0cafd7f),
  created and pushed after explicit user approval on 2026-07-13.

---

## Dependencies and Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: Complete.
- **Foundational (Phase 2)**: Blocks broad deletion and all story closeout.
- **US1 (Phase 3)**: Depends on T004–T006 so current types/sources no longer live
  inside files being deleted.
- **US2 (Phase 4)**: Its tests T015–T016 may begin after Phase 2; final
  implementation/validation runs after US1 mixed-call-site cleanup.
- **US3 (Phase 5)**: Depends on US1 and US2 so only truly obsolete tests and
  commands are removed.
- **US4 (Phase 6)**: Documentation can begin after Phase 2; guard integration
  depends on T023.
- **Polish (Phase 7)**: Depends on all four user stories.

### User Story Dependencies

- **US1 (P1)**: Delivers the app-only executable/package architecture.
- **US2 (P1)**: Protects current recording truth; tests can be prepared in
  parallel, but closeout depends on US1's composition-root cleanup.
- **US3 (P1)**: Depends on US1/US2 classification and removes the remaining
  maintenance surface.
- **US4 (P2)**: Does not alter product runtime and can be reviewed independently.

### Parallel Opportunities

- T002 and T003 touch independent guard/data-test surfaces.
- T007, T009, T011, and T013 operate on distinct packaging/source clusters once
  foundational type moves are complete.
- T015 and T016 prepare independent gate/evidence and manifest contract tests.
- T021, T022, and T025 cover separate contract/test/QA surfaces after runtime
  deletion stabilizes.
- T027 can proceed alongside US3 documentation cleanup with coordination on the
  guidance index.

## Parallel Example: User Story 1

```text
Task T007: app-only installer contract tests
Task T009: delete app-side legacy-only source clusters
Task T011: delete shared route/model/runtime cluster
Task T013: simplify installer scripts
```

## Parallel Example: User Story 2

```text
Task T015: current prerequisite/evidence tests
Task T016: no-legacy-key manifest round-trip tests
```

## Implementation Strategy

### MVP First

1. Complete foundational safety gates T002–T006.
2. Complete US1 T007–T014.
3. Stop and prove app-only build/package before pruning broader historical test
   and documentation surfaces.

### Incremental Delivery

1. Lock current capture and compatibility invariants.
2. Remove executable/packageable driver surface.
3. Remove legacy semantics from current recording evidence.
4. Remove active maintenance/QA/docs surface and enforce absence.
5. Document separate local proof cleanup truth.
6. Run full closeout gates and request commit approval.

## Notes

- Do not mark a deletion task complete merely because files are absent; its
  dependent current tests/build must pass.
- Do not delete generic Core Audio, `PhysicalAudioDevice`, current microphone
  input rejection, leakage route metadata, meeting-detection ownership, or
  system-audio CPU/resource evidence based on terminology alone.
- Do not rename persisted non-driver enum raw values.
- Do not run install, uninstall, `sudo`, HAL mutation, or `coreaudiod` restart.
- Do not commit implementation without explicit user approval after validation.
