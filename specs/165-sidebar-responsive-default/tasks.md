# Tasks: Адаптивное стартовое состояние боковой панели

**Input**: Design documents from `/specs/165-sidebar-responsive-default/`

**Prerequisites**: `spec.md`, `clarify.md`, `plan.md`, `research.md`,
`data-model.md`, `contracts/sidebar-responsive-default.md`, `quickstart.md`

**Risk lane**: `high-risk-feature`; shared responsive UX and accessibility
slice. No deploy is in scope.

## Phase 1: Setup and regression contract

**Purpose**: Lock the existing breakpoint contract and create a failing,
focused check before changing the shared initializer.

- [X] T001 [P] Read `specs/165-sidebar-responsive-default/quickstart.md` and record the browser/embedded boundary matrix (981/980 standalone; 1121/1120 embedded) in `specs/165-sidebar-responsive-default/analysis.md`.
- [X] T002 [P] [US1] Add a Node VM regression harness for initial rail state, explicit pinned state, one listener and resize preservation in `apps/server/tests/contract/test_cabinet_static_assets_contract.py`.

## Phase 2: User Story 1 — Получать правильное состояние панели при открытии (Priority: P1) 🎯 MVP

**Goal**: The existing shared shell starts expanded or collapsed according to
the surface-specific breakpoint while preserving manual state and the current
toggle accessibility contract.

**Independent Test**: The Node harness passes for standalone 1280/981/980 px,
embedded 1121/1120/720 px, explicit pinned state and two consecutive toggles; focused
pytest/static checks and the visual matrix pass without horizontal overflow.

### Tests before implementation

- [X] T003 [US1] Add focused source/static assertions for the two `matchMedia` queries, explicit-state precedence and absence of a resize listener in `apps/server/tests/unit/test_cabinet_web_shell.py` and `apps/server/tests/contract/test_cabinet_static_assets_contract.py`.

### Implementation

- [X] T004 [US1] Choose the one-time responsive initial state in `initCabinetRail` while reusing `setRailPinned` and the existing `railReady` guard in `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js`.
- [X] T005 [US1] Preserve the existing CSS breakpoint and compact/full rail presentation contract in `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.css` and update only the focused contract assertions required by the new initialization state.

## Phase 3: Review, validation and documentation

**Purpose**: Review the root-cause diff, validate both surfaces and leave
metadata-only evidence for the later release train.

- [ ] T006 [US1] Run the feature quickstart, `node --check`, `git diff --check`, focused pytest selection and the synthetic wide/narrow/embedded visual review described in `specs/165-sidebar-responsive-default/quickstart.md`.
- [X] T007 [P] Update the Russian `[Unreleased]` `Fixed` entry for responsive sidebar defaults in `CHANGELOG.md`.
- [X] T008 [US1] Perform correctness, accessibility, clean-room and Ponytail review; record findings, focused counts, visual limits and the final SHA in `specs/165-sidebar-responsive-default/analysis.md` and `specs/165-sidebar-responsive-default/quickstart.md`.
- [X] T009 [US1] Run the selected repository closeout lane `infra/scripts/ci-local.sh --fast`, reconcile all task/issue evidence and mark only validated tasks complete in `specs/165-sidebar-responsive-default/tasks.md`.

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1** has no implementation dependency and establishes the regression
  contract.
- **Phase 2** depends on T001–T003; T004 is the root-cause implementation and
  T005 follows it because CSS must remain aligned with the existing contract.
- **Phase 3** depends on the complete MVP story; T009 is the final shared-UX
  closeout gate.

### Parallel Opportunities

- T001 and T002 are independent documentation/test setup tasks.
- T003 can be prepared while T002 is reviewed, but implementation T004 must
  follow the contract decision.
- T007 touches only `CHANGELOG.md` and can be reviewed alongside the code
  diff; T006, T008 and T009 remain ordered by validation evidence.

## Issue mapping

Issues are synchronized after analyze using the Russian project canon:

| Task | GitHub issue |
|---|---|
| T001 | #5295 |
| T002 | #5299 |
| T003 | #5296 |
| T004 | #5300 |
| T005 | #5298 |
| T006 | #5297 |
| T007 | #5302 |
| T008 | #5303 |
| T009 | #5301 |

## Implementation Strategy

MVP is the one P1 story: fix the initial decision in the existing shared path,
prove it with the boundary harness, then run the visual and fast-lane checks.
No new state abstraction, persistence, breakpoint config or dependency is
needed.
