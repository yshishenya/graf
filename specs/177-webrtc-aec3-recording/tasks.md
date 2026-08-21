# Tasks: WebRTC AEC3 Recording

**Input**: Design documents from `/specs/177-webrtc-aec3-recording/`

**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/`, `quickstart.md`

**Tests**: Required because this is a high-risk capture/integrity feature. Story tests are written first and must fail for the intended reason before implementation.

**Organization**: Tasks are grouped by user story. No commit, push, PR, release or deploy is authorized by this task list.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: May proceed in parallel because it owns different files and has no unfinished dependency
- **[Story]**: User-story traceability label
- Every task names its concrete file or directory

## Phase 1: Setup (Pinned Native Dependency)

**Purpose**: Produce one reproducible, reviewable static dependency without adding a runtime package manager or dynamic component.

- [X] T001 Add the exact WAP v2.1/WebRTC M131 and Abseil source identities, hashes, toolchain provenance fields and license inventory in `apps/macos/Native/GrafAEC3/upstream.lock`
- [X] T002 Implement the deterministic arm64/x86_64 static build and XCFramework assembly with pinned Meson fallback, macOS 14.0 minimum and no LTO in `apps/macos/Scripts/build-graf-aec3-xcframework.sh`
- [X] T003 Add the opaque fixed-width C ABI declarations and module map in `apps/macos/Native/GrafAEC3/include/GrafAEC3.h` and `apps/macos/Native/GrafAEC3/include/module.modulemap`
- [X] T004 Implement C++ lifetime, AEC-only configuration, exception barriers, 480-sample processing and bounded statistics in `apps/macos/Native/GrafAEC3/Sources/GrafAEC3.cpp`
- [X] T005 Build and check in the verified universal artifact under `apps/macos/Vendor/GrafAEC3.xcframework/` and add only its required static-library exception in `.gitignore`
- [X] T006 Add the SwiftPM binary target, app-core dependency and minimal `CoreFoundation`/`c++` linker settings in `apps/macos/Package.swift`

**Checkpoint**: The pinned native component is locally buildable and importable, but production capture behavior is not yet changed.

---

## Phase 2: Foundational (Artifact And Contract Gates)

**Purpose**: Make dependency drift, wrong architecture, accidental dynamic linkage and unsafe licensing fail before story work.

**⚠️ CRITICAL**: Complete this phase before changing the active timeline.

- [X] T007 Add hash, plist, architecture, exported-symbol, native arm64/Rosetta x86_64 C smoke and dynamic-linkage checks in `apps/macos/Scripts/validate-graf-aec3-artifact.sh`
- [X] T008 [P] Add WAP/WebRTC, PATENTS, Abseil and bundled-DSP attribution in `apps/macos/RecApp/Resources/AEC3-THIRD-PARTY-NOTICES.txt` and `docs/third-party-notices.md`
- [X] T009 [P] Add dependency identity, AEC-only configuration and exact-frame C ABI contract assertions in `apps/macos/Shared/Tests/GrafAEC3ArtifactContractTests.swift`
- [X] T010 Run `apps/macos/Scripts/validate-graf-aec3-artifact.sh` and `swift build --package-path apps/macos`, recording only bounded command outcomes in `specs/177-webrtc-aec3-recording/evidence/dependency-validation.md`

**Checkpoint**: Foundation proves the vendored component can be trusted and linked without a shipped WebRTC/Abseil runtime.

---

## Phase 3: User Story 1 — Recording Through Speakers Without Double Voice (Priority: P1) 🎯 MVP

**Goal**: Clean the aligned microphone with the matching system reference before the unchanged canonical mix, preserving local speech and exact timing.

**Independent Test**: A deterministic far-end echo fixture passes at least 20 dB reduction after convergence; near-end-only and double-talk thresholds pass; callback partitioning does not change frame count or output.

### Tests for User Story 1

- [X] T011 [P] [US1] Add failing wrapper tests for exact 480-sample pairs, render-before-capture order, zero stream delay, non-finite rejection and bounded statistics in `apps/macos/Shared/Tests/RecordingEchoProcessorTests.swift`
- [X] T012 [P] [US1] Add failing timeline tests for partitions `1/479/480/481/1024/4096`, random partitions, final trim, valid silent render and unchanged system gain in `apps/macos/Shared/Tests/RecordingAudioTimelineTests.swift`
- [X] T013 [P] [US1] Add failing deterministic far-end, near-end, double-talk, delay/RT60 and callback-jitter quality rows in `apps/macos/Shared/Tests/RecordingAEC3QualityTests.swift`

### Implementation for User Story 1

- [X] T014 [US1] Implement the single Swift owner for processor readiness, paired-frame calls, terminal status and public statistics in `apps/macos/RecApp/Sources/Capture/RecordingEchoProcessor.swift`
- [X] T015 [US1] Integrate 480-sample paired framing after PTS alignment and before the existing `0.5 * (microphone + system)` mix in `apps/macos/RecApp/Sources/Capture/RecordingAudioTimeline.swift`
- [X] T016 [US1] Wire one mandatory processor per new recording and retain exact canonical WAV/M4A output through `apps/macos/RecApp/Sources/Capture/V5LocalRecordingWriter.swift`
- [X] T017 [US1] Prove the normal path creates one manifest, one transcription WAV, one review M4A and no raw/reference artifact in `apps/macos/Shared/Tests/SystemAudioRecordingPackageTests.swift`

**Checkpoint**: User Story 1 is independently functional under stable mic/system routes and passes synthetic quality thresholds.

---

## Phase 4: User Story 2 — Truthful Failure Instead Of Hidden Echo (Priority: P2)

**Goal**: Block startup when AEC is unavailable and expose a terminal degraded result after reference, route, source or processor failure without releasing raw microphone audio.

**Independent Test**: Injected startup and runtime faults never produce a normal package or failed raw-mic frame; only the already-cleaned prefix can remain, and Stop stays idempotent.

### Tests for User Story 2

- [X] T018 [P] [US2] Add failing Codable/state-transition tests for optional processor descriptor, drift/health counters, bounded reasons and historical manifests in `apps/macos/Shared/Tests/CanonicalRecordingManifestTests.swift`
- [X] T019 [P] [US2] Add failing startup/runtime AEC, missing-reference, privacy Pause/Resume continuity and no-salvage tests in `apps/macos/Shared/Tests/LocalRecordingWriterSystemAudioTests.swift`
- [X] T020 [P] [US2] Add failing producer route-generation, ScreenCaptureKit stop-error, microphone disconnect and runtime-error propagation tests in `apps/macos/Shared/Tests/SystemAudioCaptureServiceTests.swift` and `apps/macos/Shared/Tests/MicrophoneCaptureServiceTests.swift`

### Implementation for User Story 2

- [X] T021 [US2] Add optional backward-compatible processor descriptor, echo health with bounded drift estimate and bounded failure enums to `apps/macos/Shared/Sources/Models/AudioModelCore.swift`
- [X] T022 [US2] Publish real monotonic route generations and terminal capture errors from `apps/macos/RecApp/Sources/Capture/RecordingSampleSources.swift` and `apps/macos/RecApp/Sources/Capture/SystemAudioCaptureService.swift`
- [X] T023 [US2] Make timeline/reference gaps, route boundaries and AEC errors terminal while keeping PTS-aligned privacy Pause/Resume on the mandatory processor in `apps/macos/RecApp/Sources/Capture/RecordingAudioTimeline.swift`
- [X] T024 [US2] Replace unsafe salvage re-drain with cleaned-prefix finalization, persist health metadata and block upload/transcription readiness in `apps/macos/RecApp/Sources/Capture/V5LocalRecordingWriter.swift` and `apps/macos/RecApp/Sources/Capture/LocalRecordingManifestService.swift`
- [X] T025 [US2] Block startup with bounded recovery guidance and propagate runtime AEC/source failure immediately to the existing degraded UI while preserving Pause/Resume truth and one-action Stop in `apps/macos/RecApp/Sources/Capture/CaptureSessionController.swift`
- [X] T026 [US2] Add metadata-only echo health fields and forbidden dump/audio guards in `apps/macos/RecApp/Sources/Capture/RecordingEvidenceService.swift`, `apps/macos/RecApp/Sources/Diagnostics/DiagnosticBundleCoreService.swift` and `apps/macos/Shared/Sources/Diagnostics/DiagnosticRedactor.swift`

**Checkpoint**: User Story 2 independently proves there is no hidden raw-microphone fallback before or after recording start.

---

## Phase 5: User Story 3 — One Supported Capture Path (Priority: P3)

**Goal**: Remove active no-AEC assertions and conflicting legacy descriptions while preserving historical package readers and safety guards.

**Independent Test**: Repository and product-surface audit finds one production mic+system+AEC path, no selectable retired runtime, no old prohibition on AEC, and successful historical-package decoding.

### Tests for User Story 3

- [X] T027 [P] [US3] Replace the obsolete no-AEC source scan with an exact one-AEC-path/no-legacy/no-raw-artifact contract in `apps/macos/Shared/Tests/NoAECProductSurfaceTests.swift`
- [X] T028 [P] [US3] Update the v5 contract validator for mandatory new-recording AEC metadata and unchanged historical-reader behavior in `apps/macos/Shared/Tools/ContractValidation/ContractValidationV5.swift`

### Implementation for User Story 3

- [X] T029 [US3] Remove or replace active no-AEC and retired-runtime claims while preserving historical records in `apps/macos/README.md`, `docs/prd-voice-layer-final.md`, `docs/current-product-status.md` and `qa/macos/recording-artifact-format.md`
- [X] T030 [US3] Extend installer/update/package validation for the notice resource, universal executable and absence of WebRTC/Abseil dylibs in `apps/macos/Scripts/validate-app-updates.sh`, `apps/macos/Shared/Tests/InstallerLifecycleEvidenceTests.swift` and `qa/macos/release-candidate-checklist.md`
- [X] T031 [US3] Audit active sources and scripts for reachable Features 038/039/106 processing, fallback selectors, second audio artifacts and contradictory copy; record bounded results in `specs/177-webrtc-aec3-recording/evidence/legacy-audit.md`

**Checkpoint**: User Story 3 leaves one supported production path without deleting compatibility readers or historical feature evidence.

---

## Phase 6: Polish & Cross-Cutting Validation

**Purpose**: Close quality, repository and hardware evidence without publishing a release.

- [X] T032 [P] Update behavior, architecture, QA and known release limitation notes in `CHANGELOG.md`
- [X] T033 Run focused Swift tests, the synthetic quality matrix and exact package checks from `specs/177-webrtc-aec3-recording/quickstart.md`, recording bounded outcomes in `specs/177-webrtc-aec3-recording/evidence/synthetic-validation.md`
- [X] T034 Build the universal local ad-hoc installer, inspect architectures/linkage/signature/notices and run `infra/scripts/ci-local.sh --fast`, recording bounded outcomes in `specs/177-webrtc-aec3-recording/evidence/local-validation.md`
- [ ] T035 Execute the two-Mac/two-room speaker, headphone, double-talk, volume, route-change and 60-minute matrix without committing raw audio in `specs/177-webrtc-aec3-recording/evidence/hardware-validation.md`
- [X] T036 Re-run `speckit-analyze`, `git diff --check`, repository legacy scans and the audio-capture checklist; record the final high-risk/no-release lane in `specs/177-webrtc-aec3-recording/evidence/closeout.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: no dependency.
- **Foundational (Phase 2)**: depends on Setup and blocks capture integration.
- **User Story 1 (Phase 3)**: depends on Foundational.
- **User Story 2 (Phase 4)**: depends on User Story 1's processor/timeline output contract.
- **User Story 3 (Phase 5)**: can begin after Foundational, but its validator assertions must finish after User Stories 1 and 2.
- **Polish (Phase 6)**: depends on all three stories.

### User Story Dependencies

```text
Pinned static dependency + artifact gates
                 |
                 v
US1: cleaned normal path ---> US2: fail-closed/degraded path
                 \             /
                  v           v
                   US3: one supported surface
                              |
                              v
                     full local/hardware validation
```

### Parallel Opportunities

- T008 and T009 can run in parallel after the dependency paths exist.
- T011, T012 and T013 are independent failing-test surfaces.
- T018, T019 and T020 are independent failing-test surfaces after US1.
- T027 and T028 can run in parallel after the target contracts exist.
- T032 can run in parallel with non-document validation preparation.

---

## Parallel Examples

### User Story 1

```text
T011 RecordingEchoProcessor unit contract
T012 RecordingAudioTimeline framing contract
T013 deterministic AEC3 quality contract
```

### User Story 2

```text
T018 manifest compatibility/state tests
T019 writer fail-closed tests
T020 native producer lifecycle tests
```

### User Story 3

```text
T027 active source-surface test replacement
T028 contract validator update
```

---

## Implementation Strategy

### MVP First

1. Complete the pinned static dependency and artifact gate.
2. Complete User Story 1 under stable routes.
3. Stop and prove synthetic echo reduction, speech preservation and exact timing.
4. Do not ship this partial state: User Story 2 is mandatory before any user/release build because AEC is a fail-closed invariant.

### Full Feature

1. Add User Story 2 failure truth and source lifecycle propagation.
2. Remove conflicting active legacy/no-AEC surfaces in User Story 3.
3. Run all local, package and hardware gates.
4. Leave release/notarization/deploy untouched until separately authorized.

## Notes

- `[P]` means file ownership is independent at that point, not that shared-tree edits may overwrite one another.
- Tests are written first and must fail for the intended contract before production changes.
- Use the fewest new types and files that preserve the C ABI, trust boundary and testability; no second audio graph or speculative recovery state machine.
- Never place raw audio, transcript text, private meeting content, credentials or live private paths in evidence.
- A task checkbox is marked complete only after its named check passes; do not infer completion from code presence.
