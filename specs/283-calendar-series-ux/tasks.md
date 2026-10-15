# Tasks: Понятная повторяющаяся встреча (F283)

**Input**: spec.md, plan.md, research.md, data-model.md, contracts/calendar-series.md, quickstart.md.
**Prerequisites**: clarify completed; independent UX8/8 + security6/6 PASS (checklist-review.md).
**Tests**: high-risk-feature, meaningful temporal/permission/browser/visual checks required.

## Phase 1: Setup

- [X] T001 Сверить требования, независимое ревью и карту FR/SC в specs/283-calendar-series-ux/validation.md перед реализацией. (Issue #7436) — [#7436](https://github.com/yshishenya/graf/issues/7436)

## Phase 2: Foundational

- [X] T002 Добавить проверки периодов, текущей встречи, сортировки, cursor и обратной совместимости в apps/server/tests/unit/test_calendar_series.py и apps/server/tests/contract/test_calendar_join_series_contract.py (FR-002/007, SC-004). (Issue #7423) — [#7423](https://github.com/yshishenya/graf/issues/7423)
- [X] T003 Добавить optional view и стабильный signed anchor без изменения legacy all в apps/server/src/twobrain_rec_server/api/calendar.py, api/schemas.py и calendar/series.py (FR-002/007). (Issue #7423) — [#7423](https://github.com/yshishenya/graf/issues/7423)

## Phase 3: US1 — Ближайшая встреча

**Goal**: компактный обзор и конкретные будущие даты.
**Independent test**: upcoming view, ongoing/cancelled/no-link, permitted title runs, renamed first date/history/page boundary/refresh, same-day actions, trusted Join.

- [X] T004 [US1] Переработать обзор, переключатели и строки расписания в apps/server/src/twobrain_rec_server/cabinet/rendering.py, static/cabinet/calendar-series.js и static/cabinet/cabinet.css (FR-001/002/003/004/009, SC-001/002). (Issue #7424) — [#7424](https://github.com/yshishenya/graf/issues/7424)

## Phase 4: US2 — История результатов

**Goal**: последнее событие первым, контекстные записи и правдивая справка.
**Independent test**: history ordering, one/multiple/partial recording, no historical Join.

- [X] T005 [US2] Реализовать историю с различимыми записями и единой справкой в apps/server/src/twobrain_rec_server/cabinet/static/cabinet/calendar-series.js и rendering.py (FR-004/005, SC-001/002). (Issue #7424) — [#7424](https://github.com/yshishenya/graf/issues/7424)

## Phase 5: US3 — Состояния и приватность

**Goal**: ясные пустые/ошибочные состояния и безопасное обновление.
**Independent test**: failure/retry, expiry, switch/close late response, scope masks and refresh focus.

- [X] T006 [US3] Сохранить выбранный период/фокус, отмену запросов и очистку при обновлении прав в apps/server/src/twobrain_rec_server/cabinet/static/cabinet/calendar-series.js и общий refresh в cabinet.js; обеспечить формат даты/часового пояса и privacy DOM (FR-003/006/007/008, SC-004). (Issue #7424) — [#7424](https://github.com/yshishenya/graf/issues/7424)
- [X] T007 [US3] Обновить production browser checks apps/server/tests/browser/calendar_series.mjs для всех периодов/состояний, сохранив Join guards и численные бюджеты (FR-001–010, SC-001–004). (Issue #7424) — [#7424](https://github.com/yshishenya/graf/issues/7424)

## Phase 6: Validation and delivery

- [X] T008 Проверить production синтетические screenshots в двух темах,1280px/320px/200%, клавиатуру и видимый focus; записать только безопасное evidence в specs/283-calendar-series-ux/validation.md и changes/unreleased/F283.yaml (FR-009/010, SC-003). (Issue #7424) — [#7424](https://github.com/yshishenya/graf/issues/7424)
- [X] T009 Выполнить quickstart server/browser, converge и обязательные exact-SHA/base PR checks; после одобренного commit проверить единственный GRAF Dev через harness; зафиксировать gates и остаток в specs/283-calendar-series-ux/validation.md (SC-003/004). (Issue #7425) — [#7425](https://github.com/yshishenya/graf/issues/7425)

## Dependencies & Execution Order

T001→T002→T003→T004→T005→T006→T007→T008→T009. Story tests independently select upcoming/history/recovery fixtures. No parallel code ownership: same shared UI files. Independent checklist reviewer owns only custom checklists/report. Reads and server/browser runs may be parallel; no duplicate agents required.

## Implementation Strategy

Extend existing scoped query/cursor and native controls, reuse theme/time/security helpers. No new packages, storage schema, recurrence editor, provider or recording behavior. Mark tasks [X] only after respective validation. T009 accepted on d0edffddfd766179ff46feb5bd8a5a71682015b1 with exact-SHA/base PR proof and installed GRAF Dev acceptance; final documentation-only head must retain verified code proof and current Dev identity. GitHub closeout follows merge; production release is a separate authorised operation.

## Phase 7: Convergence before release

- [X] T010 Согласовать canonical OpenAPI с уже реализованными optional view/temporal_state, привести новые подписи Python/JS к словарю GRAF без «ё», включить owned JS в существующую словарную проверку и проверить контракт/браузер до нового кандидата (FR-002/007/009, SC-003/004). (Issue #7439) — [#7439](https://github.com/yshishenya/graf/issues/7439)
