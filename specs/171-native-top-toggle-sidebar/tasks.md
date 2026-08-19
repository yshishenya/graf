# Tasks: Единый верхний toggle и аккуратный rail

**Input**: Design documents from `/specs/171-native-top-toggle-sidebar/`

**Prerequisites**: `spec.md`, `clarify.md`, `plan.md`, `research.md`,
`data-model.md`, `contracts/`, `quickstart.md`

**Risk lane**: `high-risk-feature`; shared native/web navigation UX and
accessibility. No capture, auth, permissions, packaging or deploy changes.

## Phase 1: Regression contracts

**Purpose**: Lock the two reported regressions before implementation with the
smallest existing source/static harnesses.

- [X] T001 [P] [US1] Update native top-slot source contracts for shared top inset,
  one disclosure control per mode, reserved content space, 44px target and
  unchanged accessibility labels in `apps/macos/Shared/Tests/AppControlAccessibilityTests.swift` and `apps/macos/Shared/Tests/DesktopMeetingShellWebViewBoundaryTests.swift`.
- [X] T002 [P] [US2] Extend the cabinet rail VM/static regression harness for
  981px embedded defaults, content/nav click state preservation, named compact
  links, hidden compact header and one-handler idempotency in `apps/server/tests/contract/test_cabinet_static_assets_contract.py` and `apps/server/tests/unit/test_cabinet_web_shell.py`.

## Phase 2: User Story 1 — Сворачивать native-панель в том же месте (P1)

**Goal**: The collapsed and expanded native inspector expose one fixed top-right
disclosure action that can be clicked twice without pointer travel.

**Independent Test**: Focused XCTest/source contracts pass and Computer Use shows
the same top-trailing slot, no overlap, truthful labels and two-click behavior.

### Implementation

- [X] T003 [US1] Replace the bottom disclosure helper/insets with a shared fixed
  top-trailing header slot, place it in `compactInspector` and `inspector`, and
  reserve the slot above the expanded scroll content in `apps/macos/RecApp/Sources/Cabinet/DesktopMeetingShellView.swift`.
- [X] T004 [US1] Run the focused native source/XCTest selection and update only
  the metadata-only native geometry evidence in `specs/171-native-top-toggle-sidebar/quickstart.md`.

## Phase 3: User Story 2 — Получать ясное стартовое и ручное состояние web-меню (P1)

**Goal**: Wide embedded shells start expanded, narrow shells stay compact, and
the user-selected rail state survives unrelated page interaction.

**Independent Test**: The Node VM matrix, focused pytest/static tests and in-app
Browser wide/narrow audit pass without unnamed links, empty compact bands or
horizontal overflow.

### Implementation

- [X] T005 [US2] Reuse `setRailPinned` and change `initCabinetRail` to use the
  practical 981px default for both surfaces while removing outside-click and
  navigation-link auto-collapse handlers in `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js`.
- [X] T006 [US2] Add matching `aria-label` values to ordinary and settings
  navigation anchors without changing existing hrefs or active-state semantics
  in `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/components/sections.html`.
- [X] T007 [US2] Remove the compact workspace-header layout slot while keeping
  the toggle, profile/update/download targets, focus styles and 64px/176px rail
  geometry intact in `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.css`.
- [X] T008 [US2] Run the focused rail pytest/Node checks, `node --check` and
  `git diff --check`; record the web evidence in `specs/171-native-top-toggle-sidebar/quickstart.md`.

## Phase 4: Review, closeout and repository gate

**Purpose**: Review the combined diff, verify both surfaces visually, and leave
the feature ready for a later release train.

- [X] T009 [P] Update the Russian `[Unreleased]` user-facing entry for the fixed
  native/web navigation behavior in `CHANGELOG.md`.
- [X] T010 Perform correctness, accessibility, clean-room and
  Ponytail review; add any directly related regression check and record findings,
  visual limits and exact validation counts in `specs/171-native-top-toggle-sidebar/analysis.md`.
- [X] T011 Rebuild/launch `GRAF Dev` and complete the in-app Browser
  and Computer Use visual matrix from `specs/171-native-top-toggle-sidebar/quickstart.md`, then mark only validated tasks complete in `specs/171-native-top-toggle-sidebar/tasks.md`.
- [X] T012 Run the selected closeout gate `infra/scripts/ci-local.sh --fast`, reconcile Spec Kit/GitHub evidence and record the final SHA in `specs/171-native-top-toggle-sidebar/quickstart.md`.

## Dependencies & Execution Order

### Phase Dependencies

- Phase 1 has no implementation dependency and establishes the regression
  contracts.
- Phase 2 depends on T001; T003 is the native root-cause implementation and T004
  follows it.
- Phase 3 depends on T002 and can proceed independently of the native source
  change, but its visual closeout is shared with Phase 2.
- Phase 4 depends on both user stories and their focused checks; T012 is the
  final repository gate before the implementation commit.

### User Story Dependencies

- **US1 (P1)**: Starts after T001; no dependency on US2.
- **US2 (P1)**: Starts after T002; no dependency on US1.
- Cross-surface visual review waits for both stories so geometry is not judged
  against a stale build.

### Parallel Opportunities

- T001 and T002 touch different test stacks and can be prepared in parallel.
- T009 touches only `CHANGELOG.md` and can be reviewed alongside focused tests.
- T004 and T008 are sequential within their own stories; T010/T011/T012 remain
  ordered because evidence must describe the final implementation.

## Issue mapping

GitHub issues are synchronized after analyze using the Russian project canon;
task IDs remain the source of truth.

| Task | GitHub issue |
|---|---|
| T001 | #5343 |
| T002 | #5344 |
| T003 | #5345 |
| T004 | #5346 |
| T005 | #5347 |
| T006 | #5348 |
| T007 | #5349 |
| T008 | #5350 |
| T009 | #5351 |
| T010 | #5352 |
| T011 | #5353 |
| T012 | #5354 |

## Implementation Strategy

MVP is both P1 stories because the native control and shared left rail are the
two parts of the same reported navigation regression. Write the narrow
contracts first, apply the smallest native/web changes, run focused checks, then
perform one combined visual review and one fast lane. No full CI or release
deploy is needed for this isolated slice.
