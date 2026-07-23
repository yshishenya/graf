# Tasks: Понятное меню действий со встречей

**Input**: Design documents from `specs/123-meeting-actions-menu/`

**Prerequisites**: `spec.md`, `plan.md`, `research.md`, `data-model.md`,
`contracts/meeting-actions-menu.md`, `quickstart.md`

**Tests**: Required before implementation because this slice touches
permission-derived visibility, deletion UX, accessibility and shared
browser/embedded behavior.

## Phase 1: Setup

**Purpose**: Lock the selected visual target and current shared flow before code.

- [X] T001 Record the selected single-level menu target, current-code evidence and high-risk validation lane in `specs/123-meeting-actions-menu/plan.md` and `specs/123-meeting-actions-menu/research.md`
- [X] T002 Confirm the no-persistence/no-new-egress boundary and action authority map in `specs/123-meeting-actions-menu/data-model.md` and `specs/123-meeting-actions-menu/contracts/meeting-actions-menu.md`

---

## Phase 2: Foundational Tests And Shared Semantics

**Purpose**: Make the expected markup, capability filtering and focus contract executable before changing presentation.

- [X] T003 [P] Add contract expectations for the compact ordered menu, helper copy, details separation, absent cockpit content and no empty disabled rows in `apps/server/tests/contract/test_recording_governance_ui_contract.py`
- [X] T004 [P] Add accessibility contract expectations for menu-button state, arrow/Home/End/Escape behavior, visible opener fallback, details dialog naming/focus trap and 40px targets in `apps/server/tests/contract/test_recording_workflow_accessibility.py`
- [X] T005 [P] Update ready/processing/browser/embedded integration expectations for the new menu/details IA in `apps/server/tests/integration/test_cabinet_meeting_detail.py`

**Checkpoint**: Focused tests fail only for the intended new UI contract.

---

## Phase 3: User Story 1 — Быстро выбрать нужное действие (Priority: P1) 🎯 MVP

**Goal**: Replace the large technical modal with one compact action menu using existing server capability truth.

**Independent Test**: A ready owner opens `Ещё` and sees only available export/audio/details/delete actions in the specified order, with no files, status or activity content inside the menu.

- [X] T006 [US1] Move the governance fragment beside the top action trigger and render the compact ordered action rows with existing icons and capability branches in `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/meeting_detail_content.html` and `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/fragments/meeting_governance.html`
- [X] T007 [US1] Expose menu semantics and omit the trigger when no secondary action exists in `apps/server/src/twobrain_rec_server/cabinet/rendering.py`
- [X] T008 [US1] Replace the former modal styling with the selected anchored 280px menu, helper hierarchy, target sizes, divider and danger row in `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.css`
- [X] T009 [US1] Extend the existing meeting-panel controller with first/last entry, arrow/Home/End navigation, outside-click dismissal and visible focus return in `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js`

**Checkpoint**: US1 works for every partial capability set without a new endpoint, dependency or client capability model.

---

## Phase 4: User Story 2 — Посмотреть сведения без перегрузки меню (Priority: P1)

**Goal**: Keep all existing trust/provenance information reachable in a separate, accessible details dialog.

**Independent Test**: `Ещё → Сведения о встрече` opens a named dialog containing the prior files/revision/calendar/speaker/activity truth, then closes back to visible `Ещё`.

- [X] T010 [US2] Move existing files, lifecycle truth, revision, calendar context, speakers and activity into a separately named details dialog with an explicit close control in `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/fragments/meeting_governance.html`
- [X] T011 [US2] Reuse the shared modal focus trap and add details-dialog close/backdrop/Escape/visible-opener return behavior in `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js`
- [X] T012 [US2] Style the details dialog with existing GRAF modal tokens, responsive bounds, scroll containment, theme and contrast support in `apps/server/src/twobrain_rec_server/cabinet/static/cabinet.css`

**Checkpoint**: All former governance information remains reachable without appearing in the quick menu.

---

## Phase 5: User Story 3 — Безопасно удалить встречу (Priority: P1)

**Goal**: Put delete last in the quick menu while preserving the existing bounded confirmation and server lifecycle behavior.

**Independent Test**: An allowed owner opens delete from the menu, cancels and returns to visible `Ещё`; a denied actor never sees the action and direct requests still fail closed.

- [X] T013 [US3] Render the existing delete opener as the final separated menu item without changing confirmation copy, report link, form or authorization in `apps/server/src/twobrain_rec_server/cabinet/review_policy_rendering.py` and `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/fragments/meeting_governance.html`
- [X] T014 [US3] Make export and delete dialog close paths fall back from hidden menu items to the visible `Ещё` trigger in `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js`

**Checkpoint**: Destructive action is easy to find but impossible to trigger without the existing confirmation.

---

## Phase 6: User Story 4 — Управлять меню мышью, клавиатурой и VoiceOver (Priority: P2)

**Goal**: Prove equivalent, accessible behavior across browser and embedded cabinet states.

**Independent Test**: Complete every menu and dialog flow keyboard-only at 200% zoom in browser and embedded cabinet with correct names, focus and no clipping.

- [X] T015 [US4] Add/adjust existing reviewed icon-source entries and ensure decorative icons remain hidden while text labels carry accessible names in `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/components/icons.html` and `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/fragments/meeting_governance.html`
- [X] T016 [US4] Cover partial capability, no-action, focus-return and browser/embedded parity scenarios in `apps/server/tests/unit/test_cabinet_web_shell.py` and `apps/server/tests/integration/test_cabinet_meeting_detail.py`
- [X] T017 [US4] Run the focused automated and manual keyboard/zoom/theme/contrast/reduced-motion scenarios from `specs/123-meeting-actions-menu/quickstart.md`

**Checkpoint**: No P0/P1/P2 accessibility or shared-surface defect remains.

---

## Phase 7: Polish And Closeout

**Purpose**: Complete product evidence, review and repository gates.

- [X] T018 Capture the implemented open-menu state, compare it with the selected first visual target, fix P0/P1/P2 findings and record `final result: passed` in `specs/123-meeting-actions-menu/design-qa.md`
- [X] T019 Update the user-visible change under `[Unreleased]` in `CHANGELOG.md`
- [X] T020 Run `git diff --check`, focused Ruff if Python changed, and all automated commands from `specs/123-meeting-actions-menu/quickstart.md`
- [X] T021 Run `infra/scripts/ci-local.sh` and record metadata-safe evidence in `specs/123-meeting-actions-menu/tasks.md`
- [X] T022 Run Ponytail review over the complete diff and remove unjustified dependency, persistence, abstraction or duplicated policy logic while preserving security, accessibility and lifecycle truth
- [ ] T023 Reconcile completed tasks with GitHub issues, PR links and release/deploy evidence in `specs/123-meeting-actions-menu/issues.md` and `specs/123-meeting-actions-menu/tasks.md`

---

## Dependencies And Execution Order

- Phase 1 precedes every implementation task.
- T003–T005 may run in parallel and must fail for the intended contract before T006.
- US1 is the MVP and blocks US2–US4 because it creates the shared menu surface.
- US2 and US3 may proceed after US1; both must finish before US4 parity validation.
- Closeout starts only after all story checkpoints pass.

## Parallel Example: Foundational Tests

```text
T003: governance markup/capability contract
T004: keyboard/focus/accessibility contract
T005: ready/processing/browser/embedded integration expectations
```

## Implementation Strategy

1. Lock tests around existing server truth and the selected IA.
2. Ship the compact menu as the smallest useful increment.
3. Move, rather than duplicate, the existing details content.
4. Reuse the delete/export dialogs and shared focus helper.
5. Validate every capability and accessibility state before repository closeout.

## Format Validation

All 23 tasks use the required checkbox, sequential ID, optional `[P]`, required
story label inside story phases, and exact repository paths.

## Validation Evidence

- Focused feature suite: `88 passed, 2 warnings` via
  `apps/server/scripts/run_local_postgres_tests.sh --focused`.
- Canonical closeout gate: `infra/scripts/ci-local.sh` returned
  `ci_local_result=pass`; Swift build and 608 tests passed, server matrix
  passed with `2193 passed, 1 skipped` in parallel mode and `41 passed, 1
  skipped` in strict mode, plus lint, Python compilation, compose validation and
  deployment evidence scans.
- The local postgres job reports `rls_validation_result=blocked` because its
  isolated environment does not attempt the live production RLS probe. This is
  an explicit validation boundary, not a feature failure; production release
  still requires the remote deploy gate.
- Browser QA used a synthetic metadata-safe fixture at desktop and mobile
  widths. Menu keyboard navigation, dialog focus trap/return, outside-click
  dismissal and console cleanliness passed; `design-qa.md` ends with
  `final result: passed`.
- `git diff --check`, targeted Ruff and `node --check` passed. Ponytail review:
  lean already; no new dependency, persistence, egress, client capability
  model or unjustified abstraction remains.
