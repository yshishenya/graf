# Tasks: App Zoom Shortcuts

**Input**: Design documents from `specs/043-app-zoom-shortcuts/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/embedded-workspace-zoom-contract.md](./contracts/embedded-workspace-zoom-contract.md), [quickstart.md](./quickstart.md)

**Tests**: Required. This slice changes user-visible desktop behavior and must follow TDD.

**Organization**: Tasks are grouped by independently testable user story.

## Phase 1: Setup

**Purpose**: Confirm the existing macOS target and validation surface before writing feature tests.

- [ ] T001 Review current macOS package target membership and existing cabinet test layout in `apps/macos/Package.swift`
- [ ] T002 Review existing desktop app lifecycle, cabinet workspace, and embedded web view entrypoints in `apps/macos/RecApp/App/TwoBrainRecApp.swift`

---

## Phase 2: Foundational

**Purpose**: Add the shared zoom model needed by every user story.

- [ ] T003 [P] Add failing zoom command, step, clamp, and reset tests in `apps/macos/Shared/Tests/WorkspaceZoomTests.swift`
- [ ] T004 Implement `WorkspaceZoomPreference`, `WorkspaceZoomCommand`, and app-local menu metadata in `apps/macos/RecApp/Sources/Cabinet/WorkspaceZoom.swift`

**Checkpoint**: Zoom values and command semantics are modeled and testable.

---

## Phase 3: User Story 1 - Adjust Meeting Workspace Zoom With Keyboard Shortcuts (Priority: P1)

**Goal**: Standard macOS keyboard shortcuts change only the embedded meeting workspace zoom.

**Independent Test**: Run focused tests and confirm increase, decrease, reset, clamping, menu metadata, and web view application pass without a live cabinet.

### Tests for User Story 1

- [ ] T005 [P] [US1] Add failing WebKit zoom bridge tests in `apps/macos/Shared/Tests/EmbeddedCabinetWebViewZoomTests.swift`
- [ ] T006 [P] [US1] Add failing menu command metadata tests in `apps/macos/Shared/Tests/WorkspaceZoomTests.swift`

### Implementation for User Story 1

- [ ] T007 [US1] Wire app menu items, key equivalents, and target actions in `apps/macos/RecApp/App/TwoBrainRecApp.swift`
- [ ] T008 [US1] Pass workspace zoom state through `ContentView`, `AppContentRoot`, and `DesktopCabinetWorkspaceView` in `apps/macos/RecApp/App/TwoBrainRecApp.swift`
- [ ] T009 [US1] Apply zoom updates to the embedded WebKit surface without route reloads in `apps/macos/RecApp/Sources/Cabinet/EmbeddedCabinetWebView.swift`
- [ ] T010 [US1] Accept and forward workspace zoom into the embedded surface in `apps/macos/RecApp/Sources/Cabinet/DesktopCabinetWorkspaceView.swift`

**Checkpoint**: User Story 1 is independently testable with focused Swift tests.

---

## Phase 4: User Story 2 - Preserve Zoom Preference Across App Restarts (Priority: P2)

**Goal**: The selected supported zoom level persists locally and invalid saved values recover to default.

**Independent Test**: Run focused persistence tests with an isolated `UserDefaults` suite.

### Tests for User Story 2

- [ ] T011 [P] [US2] Add failing persistence and invalid-value fallback tests in `apps/macos/Shared/Tests/WorkspaceZoomTests.swift`

### Implementation for User Story 2

- [ ] T012 [US2] Persist supported zoom changes and load saved values through an injectable defaults store in `apps/macos/RecApp/Sources/Cabinet/WorkspaceZoom.swift`
- [ ] T013 [US2] Initialize and inject the workspace zoom store from the app root in `apps/macos/RecApp/App/TwoBrainRecApp.swift`

**Checkpoint**: User Story 2 restores supported values and falls back safely for invalid values.

---

## Phase 5: User Story 3 - Keep Recording Safety Controls Unaffected (Priority: P2)

**Goal**: Zoom changes are constrained to the embedded workspace and never scale or hide native recording safety controls.

**Independent Test**: Run native-shell boundary tests and capture-control regressions.

### Tests for User Story 3

- [ ] T014 [P] [US3] Add failing native shell zoom boundary tests in `apps/macos/Shared/Tests/DesktopCabinetWorkspaceTests.swift`

### Implementation for User Story 3

- [ ] T015 [US3] Extend native shell boundary invariants for workspace zoom in `apps/macos/RecApp/Sources/Cabinet/DesktopCabinetState.swift`

**Checkpoint**: User Story 3 proves Record/Stop/upload truth/local readiness remain outside workspace zoom.

---

## Phase 6: Polish & Cross-Cutting Concerns

**Purpose**: Validate the feature and record release-facing change notes.

- [ ] T016 Add `feature:043` changelog entry for app zoom shortcuts in `CHANGELOG.md`
- [ ] T017 Run quickstart validation commands from `specs/043-app-zoom-shortcuts/quickstart.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies.
- **Foundational (Phase 2)**: Depends on Setup; blocks user story work.
- **User Story 1 (Phase 3)**: Depends on Foundational.
- **User Story 2 (Phase 4)**: Depends on Foundational and integrates with the same zoom store as US1.
- **User Story 3 (Phase 5)**: Depends on Foundational and can be validated after US1 scope wiring exists.
- **Polish (Phase 6)**: Depends on all user stories selected for implementation.

### User Story Dependencies

- **US1**: MVP; can ship independently once model and menu/web bridge tests pass.
- **US2**: Adds persistence on top of the shared model and can be validated independently with isolated defaults.
- **US3**: Adds safety boundary proof and must pass before the feature is called complete.

### Parallel Opportunities

- T003, T005, T006, T011, and T014 are test-authoring tasks in different focused surfaces and can be drafted independently, but each must fail before its paired implementation work is accepted.
- T007, T008, T009, and T010 touch different implementation files but should be integrated sequentially because they pass one state value through the app.
- T016 can be prepared after implementation behavior is known.

## Parallel Example: User Story 1

```text
Task: "T005 [P] [US1] Add failing WebKit zoom bridge tests in apps/macos/Shared/Tests/EmbeddedCabinetWebViewZoomTests.swift"
Task: "T006 [P] [US1] Add failing menu command metadata tests in apps/macos/Shared/Tests/WorkspaceZoomTests.swift"
```

## Implementation Strategy

### MVP First

1. Complete T001-T004 to create the tested zoom model.
2. Complete T005-T010 to wire keyboard shortcuts and embedded workspace zoom.
3. Validate US1 before persistence and safety proof work.

### Full Slice

1. Complete US1 for live shortcut behavior.
2. Complete US2 for persisted preference behavior.
3. Complete US3 for native recording safety boundary proof.
4. Run quickstart validation and update changelog.

## Notes

- Tests must be written and observed failing before production code for each behavior.
- No server, database, deployment, audio capture, upload, or deletion task is in scope.
- Do not add user-facing copy that mentions WebKit or web view.
