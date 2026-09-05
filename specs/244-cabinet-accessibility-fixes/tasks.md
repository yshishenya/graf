# Tasks: F244 — доступность загрузки и узкой панели

Источник: spec.md, plan.md, contracts/ui.md и quickstart.md.
Режим: high-risk-product. Reviewer-owned checklist 16/16 + UX 6/6 одобрен;
маркеры требований не являются результатами реализации.

## Phase 1: Setup

- [X] T001 Проверить review требований и согласованную базу F240 в specs/244-cabinet-accessibility-fixes/evidence/implementation.md; зафиксировать точный SHA и границы FR-001/FR-002. (Issue #6583)

## Phase 2: Foundational

- [X] T002 Провести analyze и синхронизировать GitHub ownership в specs/244-cabinet-accessibility-fixes/tasks.md до реализации; проверить покрытие всех FR/SC и независимость тестов. (Issue #6583)

## Phase 3: US1 — темы (P1)

Independent test: численный контраст и динамический system/explicit на общей ревизии.

- [ ] T003 [US1] Проверить FR-001/FR-002 и SC-001 на совместном коде финального F240/F244 по quickstart.md; записать SHA и результаты шести сочетаний тем в specs/244-cabinet-accessibility-fixes/evidence/implementation.md. Реализация палитры принадлежит F240; незавершённая общая приёмка оставляет эту задачу открытой. (Issue #6584)

## Phase 4: US2 — загрузка (P1)

Independent test: имя, весь Tab/Shift+Tab, прокрутка и повторное открытие при390×320/640×400 в обеих поверхностях и четырёх состояниях файла/доступа.

- [X] T004 [US2] Добавить failing regression имени и видимого фокуса загрузки в apps/server/tests/contract/test_cabinet_static_assets_contract.py и specs/244-cabinet-accessibility-fixes/evidence/browser-checks.cjs; FR-003, SC-002. (Issue #6585)
- [X] T005 [US2] Исправить aria-labelledby в apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/fragments/manual_upload.html, viewport scroll в cabinet/static/cabinet/cabinet.css и видимый фокус в cabinet/static/cabinet/cabinet.js; сохранить остальных пользователей modal helper и серверные контракты FR-003/FR-005. (Issue #6585)

## Phase 5: US3 — узкая панель (P1)

Independent test: main≥256 при320, focus visible по elementFromPoint, preference сохраняется при640/641/980/981/1120/1121 и resize/reload.

- [X] T006 [US3] Добавить failing runtime regression narrow focus/preferences и геометрии в apps/server/tests/contract/test_cabinet_static_assets_contract.py и specs/244-cabinet-accessibility-fixes/evidence/browser-checks.cjs; FR-004, SC-003. (Issue #6586)
- [X] T007 [US3] Исправить узкую геометрию и временное скрытие панели в apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.css и cabinet.js, используя существующий initCabinetRail; сохранить toggle/Escape, приоритет окон, широкие пороги и sessionStorage FR-004/FR-005. (Issue #6586)

## Phase 6: Validation and handoff

- [X] T008 Выполнить high-risk-product quickstart, production-renderer/runtime/integration и browser проверки собственных изменений, correctness/Ponytail review и converge; записать синтетическое evidence и явные пределы FR-006/SC-004 в specs/244-cabinet-accessibility-fixes/evidence/implementation.md. (Issue #6587)
- [ ] T009 Добавить changes/unreleased/F244.yaml; подготовить commit/push/PR с exact-SHA governance-fast и связями tasks/issues в specs/244-cabinet-accessibility-fixes/tasks.md. Если T003 открыта, PR остаётся зависимым draft. (Issue #6587)

## Dependencies and execution

T001→T002 перед кодом. T004→T005, затем T006→T007: общие JS/CSS не редактируются параллельно. T003 требует итогового совместного кода; её отсутствие не мешает реализовать независимо проверяемые US2/US3, но блокирует полную приёмку и снятие draft. T005/T007→T008→T009. При открытой T003 convergence сохраняет её и добавляет конкретную обязательную доработку, не переписывая историю.

## Parallel opportunities and implementation strategy

Независимый read-only review может идти вместе с подготовкой browser runner; проверки Python/runtime/браузеров не пишут продуктовые файлы. Сначала минимальная реализация US2, затем US3; переиспользовать native dialog, существующие helpers и fixture. Палитру F240 не дублировать. Deployment ведёт отдельный оператор релиза.

## GitHub ownership

Umbrella #6568. Связи задач добавляются после deduplication до реализации.

T001, T002 → #6583.
T003 → #6584.
T004, T005 → #6585.
T006, T007 → #6586.
T008, T009 → #6587.

## Phase 7: Convergence

- [ ] T010 [US1] На окончательном совместном SHA F240/F243/F244 выполнить численный контраст и динамическую смену шести сочетаний тем, повторить затронутые upload/rail/shared JS/CSS проверки; записать exact SHA и результаты в specs/244-cabinet-accessibility-fixes/evidence/implementation.md и PR. FR-001/FR-002, SC-001/SC-004; partial HIGH, зависит от T003 и общей интеграции. До этой проверки PR зависимый draft. (Issue #6584)
