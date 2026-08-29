# Tasks: Billing page по наблюдаемой модели KRISP

**Input**: Design documents from `specs/210-krisp-billing-page/`

**Validation lane**: High-risk product area / payment UX and reference fidelity

## Phase 1: Foundational contracts

**Goal**: Сначала зафиксировать IA, безопасные состояния, accessibility и реальный responsive-контракт.

- [X] T001 [P] Расширить contract state/IA matrix для free, trial, personal, owner/member, unavailable и pending/reconciliation в `apps/server/tests/contract/test_billing_ui.py`
- [X] T002 [P] Зафиксировать headings/sections, native period/disclosure semantics, errors/live regions, named actions и no-JS fallback в `apps/server/tests/contract/test_billing_accessibility.py`
- [X] T003 [P] Зафиксировать полный немутирующий overview → plans → checkout preview → history flow и отсутствие duplicate checkout в `apps/server/tests/integration/test_billing_usability.py`
- [X] T004 [P] Добавить computed-layout WKWebView matrix для web/desktop widths и 200% zoom в `apps/macos/Shared/Tests/CabinetBillingRuntimeTests.swift`

## Phase 2: User Story 1 — Понятный billing overview (P1)

**Goal**: Владелец или участник за 10 секунд видит реальный план, цену/status, безопасное действие, workspace owner, payment method и последнюю операцию.

**Independent Test**: Отрендерить все FR-006 состояния `/billing` и проверить порядок секций, единственное действие и отсутствие guessed monetary data.

- [X] T005 [US1] Добавить только недостающие safe display fields текущей цены/цикла и latest invoice summary в `apps/server/src/twobrain_rec_server/cabinet/web_routes/billing.py`
- [X] T006 [US1] Перестроить overview в reference-like иерархию с truthful workspace-owner deviation в `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/billing_overview_content.html`
- [X] T007 [US1] Добавить billing-scoped tokens, section hierarchy, compact controls и overview/promo composition в `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.css`

## Phase 3: User Story 2 — Сравнение и безопасный checkout (P1)

**Goal**: Владелец сравнивает только реальные GRAF options, выбирает month/year и видит компактное server-authoritative резюме до оплаты.

**Independent Test**: Пройти plans → checkout для month/year → promo preview, убедиться в согласованной цене/selected state и отсутствии invoice/provider mutation.

- [X] T008 [US2] Перестроить real-plan comparison, period choice и selected states в `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/billing_plans_content.html`
- [X] T009 [US2] Перестроить compact checkout summary, coupon disclosure и consent hierarchy без изменения form semantics в `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/billing_checkout_content.html`
- [X] T010 [US2] Добавить responsive plan/checkout styles без новой JavaScript dependency в `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.css`

## Phase 4: User Story 3 — Полные состояния и единый визуальный язык (P2)

**Goal**: Empty, pending, error, recovery, subscription, payment method, history и invoice detail говорят одним языком и всегда дают безопасный следующий шаг.

**Independent Test**: Отрендерить все FR-012 fixtures и проверить status/action, no-JS recovery, responsive layout и блокировку конкурирующей оплаты.

- [X] T011 [US3] Применить общий billing page/section contract к существующим `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/billing_*_content.html` без изменения route/form semantics
- [X] T012 [US3] Завершить 390–1440 px, embedded inspector, 200% zoom, dark/light, focus, reduced-motion и forced-colors styles в `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.css`

## Phase 5: Validation and closeout

- [X] T013 [P] Добавить русский `[Unreleased]` changelog о billing UX, web/desktop parity и сохраненных payment boundaries в `CHANGELOG.md`
- [X] T014 Запустить focused server billing contract/accessibility/usability tests из `specs/210-krisp-billing-page/quickstart.md`
- [X] T015 Запустить focused macOS route/workspace/zoom/accessibility и новый billing runtime suite из `specs/210-krisp-billing-page/quickstart.md`
- [X] T016 Выполнить Browser QA на пяти viewport, dark/light, keyboard, no-JS и 200% zoom; записать metadata-only fidelity ledger в `specs/210-krisp-billing-page/validation/implementation-evidence.md`
- [ ] T017 Проверить локальный exact-build GRAF через Computer Use на minimum/standard/fullscreen и inspector collapsed/expanded без финальной оплаты; дополнить `specs/210-krisp-billing-page/validation/implementation-evidence.md`
- [X] T018 Запустить `git diff --check` и `infra/scripts/ci-local.sh --fast`, затем сверить задачи/issues с evidence в `specs/210-krisp-billing-page/tasks.md`

## Dependencies

- T001–T004 → T005–T012: regression contracts before implementation.
- T005 → T006: safe display fields before overview template.
- T007 → T010/T012: shared billing composition before responsive refinements.
- T008–T010 → T011–T012: key views establish the shared visual language.
- T005–T012 → T014–T017: runtime validation only after implementation.
- T013 may run in parallel with implementation; T014–T017 → T018.

## Parallel Opportunities

- T001–T004 touch independent test files.
- T005/T006 and T008/T009 are story-separated after contracts, but CSS tasks remain serialized to avoid cascade conflicts.
- T013 is independent of production templates.
- T014 and T015 are independent focused gates; browser and installed-app QA follow both.

## Implementation Strategy

1. Get RED on the smallest state, semantics and computed-layout contracts.
2. Reuse current server projection/forms/routes; add only missing safe display keys.
3. Establish overview hierarchy, then plans/checkout, then shared state styling.
4. Use native HTML/CSS before JavaScript and add no dependency or Swift production path.
5. Close automated, browser and local desktop evidence. Stop before payment, commit, PR, release or deploy without separate authorization.
