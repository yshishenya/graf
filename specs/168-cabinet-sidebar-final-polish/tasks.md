# Tasks: Финальная геометрия боковой панели кабинета

**Input**: Design documents from `/specs/168-cabinet-sidebar-final-polish/`

**Risk lane**: `high-risk-feature`; shared responsive navigation and fixed
playback UX. No deploy.

## Phase 1: User Story 1 — Понимать состояние левого меню (Priority: P1)

**Independent Test**: Existing responsive Node harness plus static assertions
for collapsed/expanded playback alignment and visual synthetic matrix.

- [ ] T001 [P] [US1] Add focused assertions for one web rail toggle, paired
  rail/playback widths and no extra resize listener in
  `apps/server/tests/contract/test_cabinet_static_assets_contract.py`
- [ ] T002 [US1] Align ready-state collapsed and expanded grid/playback selectors
  in `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.css`
- [ ] T003 [US1] Preserve the existing breakpoint initializer and top toggle
  accessibility contract in
  `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js`

## Phase 2: Review and validation

- [ ] T004 [US1] Run focused web checks, `node --check`, `git diff --check`, and
  browser/embedded visual states; record synthetic evidence in
  `specs/168-cabinet-sidebar-final-polish/quickstart.md` and `analysis.md`

## Dependencies & Execution Order

- T001 defines the regression contract; T002 is the root-cause CSS change; T003
  confirms JS state ownership; T004 closes the story.

## Implementation Strategy

Use the existing CSS tokens and class state. Do not add JS measurements,
storage, a second toggle or a layout abstraction.
