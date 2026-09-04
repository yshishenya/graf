# Tasks: Безопасный запуск macOS после обновления

**Input**: Design documents from `specs/232-macos-resource-bundle-hotfix/`

**Prerequisites**: `spec.md`, `plan.md`, `research.md`, `data-model.md`,
`contracts/packaged-startup.md`, `quickstart.md`, reviewed
`checklists/release-safety.md`

**Tests**: This release-deploy/high-risk slice uses test-first resolver and
process-lifecycle checks plus exact-artifact release validation.

## Phase 1: Foundation

**Purpose**: Freeze the narrow scope and prove the failing paths before code.

- [X] T001 [US1] Add failing packaged-layout and missing-resource resolver tests in `apps/macos/Shared/Tests/MeetingTargetRegistryTests.swift` (Issue #6339)
- [X] T002 [US3] Add failing direct-child launch, immediate-exit and unrelated-process isolation fixtures in `apps/macos/Installer/Scripts/test-packaged-app-launch.sh` (Issue #6340)

**Checkpoint**: Both regressions fail for the current `.1` behavior/release tooling.

## Phase 2: User Story 1 - GRAF снова запускается (Priority: P1)

**Goal**: Remove the shared fatal packaged-resource path without changing capture or detection policy.

**Independent Test**: XCTest resolves a standard packaged resource and returns `nil` for a missing packaged resource without invoking `Bundle.module`.

- [X] T003 [US1] Implement packaged-first and SwiftPM-development resource resolution in `apps/macos/RecApp/Sources/MeetingDetection/MeetingDetectionAppModule.swift` (Issue #6341)
- [X] T004 [US1] Run the focused resolver and existing registry fallback regressions from `apps/macos/Shared/Tests/MeetingTargetRegistryTests.swift` (Issue #6342)

**Checkpoint**: User Story 1 passes independently and existing registry policy is unchanged.

## Phase 3: User Story 3 - Релиз ловит startup-crash (Priority: P1)

**Goal**: Block release signing before appcast staging when the exact packaged candidate cannot stay alive.

**Independent Test**: The smoke passes only for its living direct child and fails for malformed/early-exit candidates without touching unrelated processes.

- [X] T005 [US3] Implement the bounded direct-child gate in `apps/macos/Scripts/validate-packaged-app-launch.sh` (Issue #6343)
- [X] T006 [US3] Make `apps/macos/Installer/Scripts/test-packaged-app-launch.sh` pass against the implemented gate (Issue #6344)
- [X] T007 [US3] Invoke packaged startup validation before appcast preparation in `apps/macos/Installer/Scripts/sign-graf-app-update-local.sh` (Issue #6345)
- [X] T008 [US3] Extend signing-custody regression coverage for the startup gate in `apps/macos/Installer/Scripts/test-release-signing-custody.sh` (Issue #6346)

**Checkpoint**: A crashing candidate cannot reach signed appcast generation or draft upload.

## Phase 4: Cross-cutting release preparation

**Purpose**: Document the user repair path and validate the complete local slice.

- [X] T009 [US1] Add the Russian user-facing hotfix and manual-repair changelog fragment in `changes/unreleased/F232.yaml` (Issue #6347)
- [X] T010 [US1] Run ten production-like candidate launches, arm64/x86_64 checks and missing-resource launch per `specs/232-macos-resource-bundle-hotfix/quickstart.md` (Issue #6348)
- [X] T011 [US3] Run the feature quickstart and `infra/scripts/ci-local.sh --fast`, recording metadata-only results in `specs/232-macos-resource-bundle-hotfix/validation/pre-pr.md` (Issue #6349)

## Phase 5: PR and exact-SHA candidate

**Purpose**: Merge only reviewed, current-master code and freeze immutable release bytes.

- [X] T012 [US3] Open and merge the Russian PR with moving-master/exact-SHA guards, recording the merged SHA in `specs/232-macos-resource-bundle-hotfix/validation/release.md`
- [X] T013 [US2] Prepare CalVer `2026.09.04.1`, freeze the clean merged candidate and run exactly one authoritative full CI, recording immutable evidence paths in `specs/232-macos-resource-bundle-hotfix/validation/release.md`
- [X] T014 [US2] Run `infra/scripts/cd-remote.sh --dry-run --branch master`, complete the approved release-train deploy and record the result in `specs/232-macos-resource-bundle-hotfix/validation/release.md`

## Phase 6: User Story 2 - Безопасная публичная доставка (Priority: P1)

**Goal**: Publish trusted final bytes and repair both affected and unaffected installations.

**Independent Test**: Manual `.1 -> .2` installation and healthy-predecessor Sparkle update both produce a launching exact-version GRAF.

- [X] T015 [US2] Build, Developer ID sign, notarize, staple and Gatekeeper-validate final ZIP/PKG from the exact release SHA; record metadata-only Apple evidence in `specs/232-macos-resource-bundle-hotfix/validation/release.md`
- [X] T016 [US2] Validate manual install over `v2026.09.02.1` and Sparkle update from the confirmed healthy predecessor using `apps/macos/Scripts/validate-app-updates.sh`
- [X] T017 [US2] Publish GitHub Release and versioned download assets/checksums/release notes, then replace `graf-appcast.xml` last; record URLs and final hashes in `specs/232-macos-resource-bundle-hotfix/validation/release.md`
- [X] T018 [US2] Re-download public artifacts and verify version, sizes, SHA-256, Sparkle signature, UUID, staples, Gatekeeper and startup in `specs/232-macos-resource-bundle-hotfix/validation/release.md`
- [ ] T019 [US2] Add Russian closure evidence to Feature 232 task issues and umbrella issue `#6338`, then reconcile completed markers in `specs/232-macos-resource-bundle-hotfix/tasks.md`

## Phase 7: Release gate remediation

**Purpose**: Remove two deterministic governance-fixture failures discovered by the Feature 232 diagnostic fast gate.

- [X] T020 [US3] Make the Feature 229 pointer test ignore unrelated active feature pointers in `tests/governance/test_dev_runtime.py` (Issue #6358)
- [X] T021 [US3] Replace the already published CalVer fixture with a collision-free synthetic CalVer in `tests/governance/test_release_candidate.py` (Issue #6359)
- [X] T022 [US3] Keep `infra/scripts/ci-local.sh --help` independent from the uninitialized worktree snapshot while preserving fast/full cleanliness checks in `infra/scripts/ci-local.sh` (Issue #6360)

## Dependencies & Execution Order

- T001-T002 are test-first and precede all implementation.
- T003-T004 complete the shared root-cause fix before the release gate is wired.
- T005-T008 complete the packaged startup gate before release preparation.
- T009-T011 complete before PR; T012 completes before candidate freeze.
- T013 is the sole authoritative full-CI run for the frozen SHA; T014 follows
  its go decision and does not deploy backend changes.
- T015-T016 complete before any public mutation. T017 publishes appcast last.
- T018 must pass before T019 closes release work.
- T020-T022 are pre-PR blockers and must pass before T011 can complete.

## Implementation Strategy

Use the smallest existing/native path: one resolver branch and one POSIX shell
gate. No new dependency, registry implementation, process abstraction, backend
change or UI change belongs in this feature.
