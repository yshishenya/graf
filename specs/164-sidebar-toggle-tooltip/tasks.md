# Tasks: Понятный toggle боковой панели

## Phase 1: Setup and contract

- [X] T001 Read `quickstart.md`, confirm browser/embedded hover/focus matrix and Feature 165 boundary.
- [X] T002 [P] [US1] Add template/JS/CSS contract assertions for one toggle, matching action labels and tooltip behavior in `apps/server/tests/unit/test_cabinet_web_shell.py` and `apps/server/tests/contract/test_cabinet_static_assets_contract.py`.

## Phase 2: User Story 1 — Понимать действие toggle (Priority: P1)

**Goal**: The existing shared toggle exposes a concise next-action tooltip on hover and focus.

**Independent Test**: Synthetic browser/embedded shell has one toggle, matching
labels/icons/ARIA state, visible tooltip on hover/focus, stable focus after two
activations and no overflow.

- [X] T003 [US1] Add a `data-tooltip` state marker to `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/components/sections.html` without adding a second control.
- [X] T004 [US1] Keep tooltip text synchronized with the existing `setRailPinned` action label in `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js`.
- [X] T005 [US1] Add non-interactive hover/focus tooltip styling with narrow/embedded overflow protection in `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.css`.

## Phase 3: Review and validation

- [X] T006 [US1] Run focused shell/static checks, `node --check`, `git diff --check`, synthetic visual review and `infra/scripts/ci-local.sh --fast`; record metadata-only evidence in `quickstart.md` and `analysis.md`.

## Dependencies & Execution Order

- T001 precedes the story; T002 records the contract before implementation.
- T003–T005 touch different files but share one state contract; review them together.
- T006 closes the slice after implementation and review.

## Issue mapping

| Task | GitHub issue |
|---|---|
| T001 | #5289 |
| T002 | #5290 |
| T003 | #5291 |
| T004 | #5292 |
| T005 | #5293 |
| T006 | #5294 |

## Implementation strategy

Reuse the current shared button. Make the smallest CSS/JS/template change that
adds a truthful hover/focus affordance; leave responsive default state to
Feature 165.
