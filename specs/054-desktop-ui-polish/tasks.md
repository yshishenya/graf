# Tasks: Desktop UI Polish

**Input**: Design documents from `specs/054-desktop-ui-polish/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/](./contracts/), [quickstart.md](./quickstart.md)

**Tests**: Required for changed layout contracts.

**Organization**: Tasks are grouped by independently testable story. Mark `[X]` only after direct evidence.

## Phase 1: Setup And Baseline

- [X] T001 Create metadata-safe validation log in `specs/054-desktop-ui-polish/evidence/validation-log.md`
- [X] T002 Run 054 prerequisites and record result in `specs/054-desktop-ui-polish/evidence/validation-log.md`
- [X] T003 Record clean-room UI target notes in `specs/054-desktop-ui-polish/evidence/validation-log.md`

---

## Phase 2: User Story 1 - Meeting List Uses The Screen (Priority: P1)

**Goal**: Embedded meeting list uses available space and readable rows.

**Independent Test**: Focused server list/shell tests pass and assert the new width/density contract.

- [X] T004 [P] [US1] Add width and row-density assertions in `apps/server/tests/unit/test_cabinet_web_shell.py`
- [X] T005 [P] [US1] Update embedded list integration assertion in `apps/server/tests/integration/test_cabinet_meeting_list.py`
- [X] T006 [US1] Adjust embedded list width, row grid, row height, and floating search layout in `apps/server/src/twobrain_rec_server/cabinet/web.py`

---

## Phase 3: User Story 2 - Sidebars Feel Like Product Navigation (Priority: P1)

**Goal**: Native shell sidebars preserve central workspace priority.

**Independent Test**: Focused Swift shell tests pass and assert updated widths.

- [X] T007 [P] [US2] Update native shell layout assertions in `apps/macos/Shared/Tests/AppControlAccessibilityTests.swift`
- [X] T008 [US2] Adjust shell/sidebar/inspector constants in `apps/macos/RecApp/Sources/Cabinet/DesktopMeetingShellView.swift`
- [X] T009 [US2] Align embedded workspace max width in `apps/macos/RecApp/Sources/Cabinet/DesktopCabinetWorkspaceView.swift`

---

## Phase 4: User Story 3 - Detail Review Remains Coherent (Priority: P2)

**Goal**: Detail review survives the layout changes.

**Independent Test**: Existing detail shell tests pass.

- [X] T010 [US3] Verify detail CSS still preserves tabs, playback, right panel, and mobile breakpoints in `apps/server/tests/unit/test_cabinet_web_shell.py`

---

## Phase 5: Validation

- [X] T011 Run focused server UI tests from `specs/054-desktop-ui-polish/quickstart.md` and record result in `specs/054-desktop-ui-polish/evidence/validation-log.md`
- [X] T012 Run focused macOS shell tests from `specs/054-desktop-ui-polish/quickstart.md` and record result in `specs/054-desktop-ui-polish/evidence/validation-log.md`
- [X] T013 Run forbidden-content scan for 054 docs/evidence and record result in `specs/054-desktop-ui-polish/evidence/validation-log.md`

## Dependencies & Execution Order

- Phase 1 before implementation.
- US1 and US2 can run in parallel after Phase 1.
- US3 follows US1 because it depends on shared CSS.
- Phase 5 follows all selected implementation tasks.

## Implementation Strategy

1. Reuse existing `web.py` CSS/renderer and SwiftUI shell constants.
2. Change the fewest widths/rows needed to fix the appshot issues.
3. Keep capture/upload/deletion/playback behavior untouched.
