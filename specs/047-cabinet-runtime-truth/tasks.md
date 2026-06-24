# Tasks: Cabinet Runtime Truth

**Input**: Design documents from `specs/047-cabinet-runtime-truth/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/cabinet-runtime-state-contract.md](./contracts/cabinet-runtime-state-contract.md), [quickstart.md](./quickstart.md)

**Tests**: Tests are required because this slice fixes user-visible MVP truth during server downtime, session expiry, and embedded cabinet navigation.

**Organization**: Tasks are grouped by independently testable user story.

## Phase 1: Setup

**Purpose**: Establish evidence, feature state, and focused regression target.

- [X] T001 Create metadata-safe 047 validation log in `specs/047-cabinet-runtime-truth/evidence/validation-log.md`
- [X] T002 Confirm stale `045-transcription-results-pipeline` worktree is not used for new 047 implementation in `specs/047-cabinet-runtime-truth/evidence/validation-log.md`
- [X] T003 [P] Add simple Russian unreleased changelog note for cabinet runtime truth in `CHANGELOG.md`

---

## Phase 2: Foundational

**Purpose**: Define shared runtime state and prevent route-success mistakes.

- [X] T004 [P] Add route-finished state tests for login/sign-up not becoming ready in `apps/macos/Shared/Tests/DesktopCabinetWorkspaceTests.swift`
- [X] T005 [P] Add native shell presentation tests for loading, ready, offline, timeout, and expired-session states in `apps/macos/Shared/Tests/DesktopCabinetWorkspaceTests.swift`
- [X] T006 Add optional shared cabinet runtime binding to `apps/macos/RecApp/Sources/Cabinet/DesktopCabinetWorkspaceView.swift`
- [X] T007 Classify finished embedded route kinds in `apps/macos/RecApp/Sources/Cabinet/EmbeddedCabinetWebView.swift`

**Checkpoint**: Embedded navigation can update a shared runtime state and cannot mark login pages as ready.

---

## Phase 3: User Story 1 - Honest Desktop Shell Health (Priority: P1) MVP

**Goal**: Native shell status uses runtime cabinet state, not static configuration.

**Independent Test**: Focused macOS cabinet tests prove configured/loading is neutral, ready is success, and offline/timeout is unavailable.

### Tests for User Story 1

- [X] T008 [P] [US1] Add regression assertions that configured loading state has no success tone or checkmark in `apps/macos/Shared/Tests/DesktopCabinetWorkspaceTests.swift`
- [X] T009 [P] [US1] Add regression assertions that offline/timeout show server unavailable in `apps/macos/Shared/Tests/DesktopCabinetWorkspaceTests.swift`

### Implementation for User Story 1

- [X] T010 [US1] Add cabinet status presentation model in `apps/macos/RecApp/Sources/Cabinet/DesktopMeetingShellView.swift`
- [X] T011 [US1] Replace configuration-driven shell copy/icons with runtime-driven presentation in `apps/macos/RecApp/Sources/Cabinet/DesktopMeetingShellView.swift`
- [X] T012 [US1] Store and pass cabinet runtime state from `apps/macos/RecApp/App/TwoBrainRecApp.swift`

**Checkpoint**: The shell cannot show a green cabinet state until runtime ready is proven.

---

## Phase 4: User Story 2 - Login Pages Are Auth Required (Priority: P1)

**Goal**: Login/sign-up routes are treated as auth-required, not ready.

**Independent Test**: Route-kind tests prove only meeting list/detail routes map to ready.

### Tests for User Story 2

- [X] T013 [P] [US2] Add focused test for login/sign-up finished routes mapping to expired-session in `apps/macos/Shared/Tests/DesktopCabinetWorkspaceTests.swift`

### Implementation for User Story 2

- [X] T014 [US2] Update `EmbeddedCabinetWebView` finished navigation handling so route kind determines final state in `apps/macos/RecApp/Sources/Cabinet/EmbeddedCabinetWebView.swift`

**Checkpoint**: A successful login page load cannot produce a ready cabinet state.

---

## Phase 5: User Story 3 - Web And Desktop Cabinet Parity (Priority: P1)

**Goal**: Recheck web cabinet and embedded desktop review surfaces for truthful ready/unavailable state.

**Independent Test**: Focused server/web tests and browser/runtime checks show matching review truth without private content.

### Validation for User Story 3

- [X] T015 [US3] Run focused server cabinet tests from `specs/047-cabinet-runtime-truth/quickstart.md`
- [X] T016 [US3] Run or re-use fixture-backed browser runtime validation for web and embedded cabinet states and record metadata-only evidence in `specs/047-cabinet-runtime-truth/evidence/validation-log.md`

**Checkpoint**: Web and embedded cabinet review states remain consistent.

---

## Phase 6: User Story 4 - Preserve Local Recording Safety (Priority: P1)

**Goal**: Cabinet failures do not hide local recording controls or upload truth.

**Independent Test**: Existing native shell invariant covers every cabinet state.

- [X] T017 [US4] Re-run native shell active-recording invariant coverage in `apps/macos/Shared/Tests/DesktopCabinetWorkspaceTests.swift`
- [X] T018 [US4] Run full macOS package tests from `specs/047-cabinet-runtime-truth/quickstart.md`

---

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Final validation, docs, release readiness, and production truth check.

- [X] T019 Run production health truth check from `specs/047-cabinet-runtime-truth/quickstart.md`
- [X] T020 Run `infra/scripts/ci-local.sh`
- [X] T021 Run `infra/scripts/cd-remote.sh --dry-run`
- [X] T022 Update `docs/current-product-status.md` with 047 cabinet runtime truth status after validation
- [X] T023 Finalize metadata-safe evidence in `specs/047-cabinet-runtime-truth/evidence/validation-log.md`
- [X] T024 Update root `AGENTS.md` Spec Kit plan reference to `specs/047-cabinet-runtime-truth/plan.md`
- [X] T025 Sync 047 tasks to GitHub issues and validate issue canon in `specs/047-cabinet-runtime-truth/issues.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies.
- **Foundational (Phase 2)**: Depends on setup.
- **US1 and US2 (Phases 3-4)**: Depend on foundational state wiring.
- **US3 and US4 (Phases 5-6)**: Depend on US1/US2 behavior for desktop parity.
- **Polish (Phase 7)**: Depends on all target stories.

### Parallel Opportunities

- T003 can run alongside documentation setup.
- T004 and T005 can be written in parallel.
- T008 and T009 can be written in parallel.
- T015 and T017 can run independently after implementation.

## Implementation Strategy

1. Create docs/evidence and changelog entry.
2. Add regression tests before relying on the implementation.
3. Wire shared runtime state and shell presentation.
4. Validate macOS focused/full tests.
5. Validate web cabinet and production health truth.
6. Update status/evidence and only then prepare PR/release.
