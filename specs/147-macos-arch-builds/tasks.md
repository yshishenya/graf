# Tasks: Universal macOS Installer

**Input**: Design documents from `/specs/147-macos-arch-builds/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: Required because this is a significant architecture/release slice
that changes the native desktop artifact, supported platform contract,
installer validation, public download surface, and release documentation.

## Phase 1: Setup

**Purpose**: Establish the universal artifact contract and identify active
surfaces without changing historical evidence.

- [X] T001 Review the universal installer contract and affected active files in `specs/147-macos-arch-builds/contracts/universal-installer-contract.md` and `specs/147-macos-arch-builds/plan.md`
- [X] T002 [P] Record the active release/download/source-of-truth paths in `specs/147-macos-arch-builds/data-model.md`

## Phase 2: Foundational

**Purpose**: Add focused checks that define the universal and Intel-supported
platform contract before implementation.

- [X] T003 [P] [US1] Add platform support tests for macOS 14.5+ on `appleSilicon` and `intel`, and rejection of `unknown`, in `apps/macos/Shared/Tests/PlatformSupportTests.swift`
- [X] T004 [P] [US2] Extend public download tests to require one universal installer link and reject architecture-specific choices in `apps/server/tests/unit/test_public_landing.py`
- [X] T005 [P] [US2] Update public static asset contract tests for the canonical universal installer asset `apps/server/tests/contract/test_public_landing_contract.py`

**Checkpoint**: The expected universal behavior is represented by focused
tests before production build and page changes.

## Phase 3: User Story 1 - One universal installer (Priority: P1) 🎯 MVP

**Goal**: Produce and validate one app-only installer containing native ARM and
Intel slices, with the legacy driver absent from the active build.

**Independent Test**: Run the installer build with a fixed version, inspect the
staged app and package for `arm64` plus `x86_64`, and confirm no driver package
or reference exists.

### Implementation

- [X] T006 [US1] Update `apps/macos/Shared/Sources/Models/PlatformSupport.swift` so supported macOS accepts both `appleSilicon` and `intel` while retaining the macOS 14.5 minimum
- [X] T007 [US1] Update the platform assertion and architecture field expectations in `apps/macos/Shared/Tools/ContractValidation/main.swift` for both supported native architectures
- [X] T008 [US1] Refactor `apps/macos/Installer/Scripts/build-local-installer.sh` to build `arm64-apple-macosx14.5` and `x86_64-apple-macosx14.5` with isolated SwiftPM scratch paths, merge the app executable with `lipo`, and validate both slices before packaging
- [X] T009 [US1] Remove legacy driver component flags, driver package branches, and driver distribution references from the active app-only installer path in `apps/macos/Installer/Scripts/build-local-installer.sh`
- [X] T010 [US1] Extend the installer validation path in `apps/macos/Scripts/validate-system-audio-capture-pivot.sh` to require the universal app slices and reject driver artifacts/references
- [X] T011 [US1] Remove obsolete driver build steps from `apps/macos/Scripts/validate-us1-regression.sh` while preserving native system-audio and app-only validation

**Checkpoint**: A single local `graf.pkg` is universal, app-only, and fails
closed when either required slice is absent.

## Phase 4: User Story 2 - Simple public download flow (Priority: P1)

**Goal**: Make the public page present one truthful universal installer link.

**Independent Test**: Render `/download` and verify one accessible link points
to `/static/public/downloads/graf.pkg`, with no ARM/Intel selection or stale
architecture-specific filename.

### Implementation

- [X] T012 [US2] Update `apps/server/src/twobrain_rec_server/public/templates/public/download.html` to label the single link as the universal GRAF installer and retain a no-JavaScript fallback
- [X] T013 [US2] Update download-page assertions in `apps/server/tests/unit/test_public_landing.py` for the one-link universal contract, analytics attributes, and unavailable-artifact wording
- [X] T014 [US2] Place the validated universal release asset at `apps/server/src/twobrain_rec_server/public/static/public/downloads/graf.pkg` and keep its URL fingerprintable through `apps/server/src/twobrain_rec_server/public/templates.py`

**Checkpoint**: The public page and static asset expose exactly one current
universal download path.

## Phase 5: User Story 3 - Repeatable documented release process (Priority: P2)

**Goal**: Align active product, installer, status, changelog, and Spec Kit
documentation with the universal installer and Intel support decision.

**Independent Test**: Search active documentation and run the quickstart to
confirm one universal installer, both native slices, macOS 14.5 minimum, and no
active driver-build promise are described consistently.

### Implementation

- [X] T015 [P] [US3] Update active installer/release instructions and compatibility wording in `apps/macos/Installer/README.md`
- [X] T016 [P] [US3] Update the macOS support, architecture matrix, and installer statements in `docs/prd-voice-layer-final.md` and `docs/current-product-status.md`
- [X] T017 [P] [US3] Update the user-facing release note in `CHANGELOG.md` with the universal installer and Intel support decision
- [X] T018 [US3] Reconcile active Spec Kit guidance and the feature anchor in `AGENTS.md`, `specs/147-macos-arch-builds/plan.md`, and `specs/147-macos-arch-builds/quickstart.md`

## Phase 6: Polish and validation

**Purpose**: Run the feature gate and repository gate, then record evidence
without publishing or deploying.

- [X] T019 [US1] Run the universal installer quickstart from `specs/147-macos-arch-builds/quickstart.md` and record metadata-only build, slice, package, and public-link evidence
- [X] T020 [US2] Run focused server tests for `apps/server/tests/unit/test_public_landing.py` and `apps/server/tests/contract/test_public_landing_contract.py`
- [ ] T021 [US1] Run focused SwiftPM platform/contract tests and the cross-architecture release build for `apps/macos/Package.swift`
- [ ] T022 [US3] Run `infra/scripts/ci-local.sh`, review the resulting status, and mark this task list complete only after all required validation passes

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1**: Complete; documentation-only setup is already recorded.
- **Phase 2**: Depends on Phase 1 and blocks implementation until focused
  expectations exist.
- **Phase 3 (US1)**: Depends on Phase 2 and is the MVP foundation for the
  package and validation flow.
- **Phase 4 (US2)**: Depends on the canonical artifact path from US1; focused
  page tests may be prepared in Phase 2.
- **Phase 5 (US3)**: Depends on the final behavior and filenames from US1/US2.
- **Phase 6**: Depends on all implementation phases.

### Parallel Opportunities

- T003, T004, and T005 touch different test surfaces and can be prepared in
  parallel.
- T015, T016, and T017 touch different documentation surfaces and can be
  updated in parallel after implementation behavior is settled.
- T020 and T021 can run in parallel after the build and page changes land.

## Implementation Strategy

1. Establish failing platform and download contracts.
2. Implement the universal app-only build and fail-closed validation.
3. Update the single public download path.
4. Align active documentation and changelog.
5. Run quickstart, focused checks, then `infra/scripts/ci-local.sh`.

## Notes

- `[P]` means the task touches a different file/surface and has no dependency
  on incomplete work.
- Historical evidence files are not rewritten for this slice; active product,
  installer, release, and Spec Kit guidance are the source of truth.
- No production deploy, public upload, tag, GitHub Release, or commit is
  authorized by this task list.
