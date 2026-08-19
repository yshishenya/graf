# Tasks: Одна колонка настроек без legacy gutter

**Input**: Design documents from `/specs/173-settings-single-column/`

**Risk lane**: `high-risk-feature`; shared settings IA, responsive composition
and accessibility. No auth, billing semantics, capture, data or deploy changes.

## Phase 1: Foundational regression contract

**Purpose**: Make the hidden-navigation and column-2 regression fail before the
shared template/CSS owners change.

- [X] T001 Replace legacy-nav/column-2 expectations with one-navigation and single-column settings-mode contracts in `apps/server/tests/unit/test_cabinet_web_shell.py` and `apps/server/tests/contract/test_settings_ui_contract.py`

## Phase 2: User Story 1 — Видеть настройки рядом с единственной навигацией (P1)

**Goal**: Remove the empty second-rail slot from every settings-mode surface
while preserving the real fallback navigation.

**Independent Test**: Overview/form/calendar/billing pages expose one settings
navigation, content in column 1 and no measured 252px legacy offset at wide and
narrow viewports.

- [X] T002 [US1] Make the shared settings navigation macro emit nothing only when outer settings mode already owns navigation in `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/components/settings_navigation.html`
- [X] T003 [US1] Collapse settings and calendar content to the first workspace column without changing content width or breakpoints in `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.css`
- [X] T004 [US1] Run focused settings/shell/template checks and record exact results in `specs/173-settings-single-column/quickstart.md`

## Phase 3: Review and closeout

- [X] T005 [P] Update the Russian Unreleased entry in `CHANGELOG.md`
- [X] T006 Complete in-app Browser and GRAF Dev visual/accessibility matrix and record metadata-only evidence in `specs/173-settings-single-column/quickstart.md`
- [X] T007 Perform correctness, Product Design, accessibility and Ponytail reviews, run `infra/scripts/ci-local.sh --fast` once, synchronize issues and create the validated implementation commit

## Dependencies & Execution Order

- T001 precedes T002 and T003.
- T002 precedes T003 because markup ownership defines the layout contract.
- T004 follows the implementation; T005 may run in parallel with focused checks.
- T006 and T007 close the slice against the final assets.

## Parallel Opportunities

- Only T005 is safely parallel after implementation. Template, CSS and visual
  validation remain sequential because they share one user-visible invariant.

## Issue mapping

| Task | GitHub issue |
|---|---|
| T001 | #5367 |
| T002 | #5365 |
| T003 | #5370 |
| T004 | #5369 |
| T005 | #5364 |
| T006 | #5366 |
| T007 | #5368 |

## Implementation Strategy

One P1 story is the MVP. Reuse one existing macro condition and one existing
layout owner; do not edit all callers, add route classes or introduce JS state.
