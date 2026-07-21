# Tasks: Recording Selection And Delete

**Input**: Design documents from `specs/053-recording-selection-delete/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: Focused tests are required because this slice changes deletion UX and list state.

**Organization**: Tasks are grouped by independently testable user story.

## Phase 1: Setup

**Purpose**: Confirm existing paths and contracts before code changes.

- [X] T001 Confirm existing deletion endpoint and bounded confirmation copy in `apps/server/src/twobrain_rec_server/api/cabinet.py` and `apps/server/src/twobrain_rec_server/deletion/service.py`

---

## Phase 2: User Story 1 - Delete One Recording From The List (Priority: P1)

**Goal**: A user can delete one visible meeting row from the list after Russian confirmation.

**Independent Test**: The web shell exposes a row delete control and existing deletion workflow still persists lifecycle rows.

### Tests for User Story 1

- [X] T002 [US1] Add row delete and Russian dialog assertions in `apps/server/tests/unit/test_cabinet_web_shell.py`
- [X] T003 [US1] Keep single-meeting lifecycle assertions green in `apps/server/tests/integration/test_meeting_deletion_workflow.py`

### Implementation for User Story 1

- [X] T004 [US1] Add direct row delete control, Russian confirmation dialog, and existing deletion endpoint call in `apps/server/src/twobrain_rec_server/cabinet/web.py`

---

## Phase 3: User Story 2 - Select Recordings And Delete Them Together (Priority: P1)

**Goal**: A user can select rows, see a selection toolbar, and delete selected rows together.

**Independent Test**: The web shell contains selectable rows, toolbar copy, disabled download, and batch delete state.

### Tests for User Story 2

- [X] T005 [US2] Add selection toolbar, disabled download, and batch delete assertions in `apps/server/tests/unit/test_cabinet_web_shell.py`

### Implementation for User Story 2

- [X] T006 [US2] Add selection state, disabled download feedback, batch delete loop, and selection clearing in `apps/server/src/twobrain_rec_server/cabinet/web.py`

---

## Phase 4: User Story 3 - Deletion Copy Stays Truthful (Priority: P2)

**Goal**: All new deletion UI copy is Russian and bounded to `2brain Rec` control.

**Independent Test**: Focused tests prove bounded copy and no private-content leakage in list HTML.

### Tests for User Story 3

- [X] T007 [US3] Add bounded-copy and no-private-egress assertions for list delete UI in `apps/server/tests/unit/test_cabinet_web_shell.py`

### Implementation for User Story 3

- [X] T008 [US3] Ensure all new list selection/delete strings in `apps/server/src/twobrain_rec_server/cabinet/web.py` are Russian and bounded

---

## Phase 5: Validation

**Purpose**: Prove the slice locally and record what remains out of scope.

- [X] T009 Run focused quickstart validation from `specs/053-recording-selection-delete/quickstart.md`
- [X] T010 Update `CHANGELOG.md` for the selection/delete UX fix

---

## Dependencies & Execution Order

- Phase 1 blocks implementation.
- US1 and US2 touch the same files, so execute sequentially.
- US3 follows US1/US2 because it validates the final copy surface.
- Validation runs last.

## Parallel Opportunities

- None for this slice. The same test and web shell files carry the change, so sequential execution is cheaper and safer.

## Implementation Strategy

1. Complete T001.
2. Add/adjust focused tests first.
3. Implement the smallest `cabinet/web.py` change that satisfies row delete and selection toolbar.
4. Run focused quickstart validation.
5. Update `CHANGELOG.md`.

The follow-up phase keeps the existing lifecycle/report internals and changes
only the owner feedback fragment, fallback redirect, and browser row state.

---

## Phase 6: Follow-up - Keep Owner Delete On The List (Priority: P1)

**Goal**: After confirmation, the owner sees the selected recording disappear from the list with a short status instead of a detailed deletion report.

**Independent Test**: A web delete request returns concise Russian feedback with no report link; the browser removes accepted rows, keeps failed rows, and stays on the list; direct lifecycle/report endpoints still pass.

### Tests

- [X] T011 [US1] Extend `apps/server/tests/integration/test_cabinet_hx_delete_feedback.py` to require concise Russian feedback and explicitly reject a report URL or report link in the owner fragment.
- [X] T012 [US1] Add list-shell assertions in `apps/server/tests/unit/test_cabinet_web_shell.py` for accepted-row removal and no owner-flow report hand-off.

### Implementation

- [X] T013 [US1] Change `apps/server/src/twobrain_rec_server/cabinet/deletion_rendering.py` and `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/fragments/deletion_feedback.html` to render only concise bounded status copy.
- [X] T014 [US1] Change `apps/server/src/twobrain_rec_server/cabinet/web_routes/deletion.py` to return the concise fragment for asynchronous requests and redirect non-JavaScript form submits back to the current meeting list instead of the report.
- [X] T015 [US2] Change `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js` to remove each accepted row immediately, keep failed rows visible, clear successful selection, and preserve the existing partial-failure path.

### Documentation And Validation

- [X] T016 [US3] Record the owner-flow/report boundary and Russian status copy in `specs/053-recording-selection-delete/contracts/cabinet-selection-delete-contract.md`, `specs/053-recording-selection-delete/quickstart.md`, and `CHANGELOG.md`.
- [X] T017 Run the focused quickstart checks from `specs/053-recording-selection-delete/quickstart.md` and the deletion lifecycle regression suite; mark this follow-up complete only after all checks pass.

## Follow-up Dependencies

- T011 and T012 establish the visible contract before T013-T015 implementation.
- T013 and T014 share the feedback fragment contract and run sequentially.
- T015 depends on T013 because the browser parses the concise fragment.
- T016 follows the final copy and route behavior.
- T017 is the closeout gate for the follow-up.
