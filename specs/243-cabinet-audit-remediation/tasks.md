# Tasks: F243 cabinet audit remediation

**Input**: [spec.md](spec.md), [plan.md](plan.md), research/data-model/contracts/quickstart.
**Tests**: Обязательны из-за high-risk-feature. Сначала regression, затем fix.

## Phase 1: Setup

- [X] T001 Зафиксировать границы и отдельный review требований в specs/243-cabinet-audit-remediation/checklists/ и plan.md.

## Phase 2: Foundational

- [X] T002 Проверить соответствие требований и задач, синхронизировать GitHub ownership в specs/243-cabinet-audit-remediation/tasks.md.

## Phase 3: US1 — нативные действия (P1)

**Independent Test**: Swift confirmation/cabinet routes, отрицательные trust cases.

- [X] T003 [US1] Добавить regression-тесты confirm lifecycle и точных маршрутов в apps/macos/Shared/Tests/, а full/summary/unavailable с/без desktop hint и права скачивания — в apps/server/tests/integration/test_shared_with_me.py и test_recording_share_public_link.py.
- [X] T004 [US1] Исправить безопасные нативные подтверждения в apps/macos/RecApp/Sources/Cabinet/EmbeddedCabinetWebView.swift. FR-001, FR-010.
- [X] T005 [US1] Исправить точные маршруты и surface-aware ссылки в apps/macos/RecApp/Sources/Cabinet/DesktopCabinetRoutePolicy.swift, apps/server/src/twobrain_rec_server/cabinet/web_routes/browser.py, rendering.py и templates/cabinet/pages/{billing_usage_content,shared_meeting_summary_content}.html. FR-002, FR-010.

## Phase 4: US2 — доступная поверхность (P1)

**Independent Test**: Chrome/WebKit viewport/theme matrix; keyboard and resize.

- [ ] T006 [US2] Добавить executable regression для подсказок/подменю и сохранения темы в apps/server/tests/contract/test_cabinet_static_assets_contract.py и текущем synthetic harness. FR-003–FR-005.
- [X] T007 [US2] Исправить tooltip/submenu overflow и предупреждающую рамку в apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.css и cabinet.js. FR-005, FR-009.
- [ ] T008 [US2] Проверить совместимость согласованных исправлений тем F240, accessibility F244 и autosave F242 в specs/243-cabinet-audit-remediation/validation/implementation-evidence.md; если external ownership не подтверждён, реализовать соответствующую часть здесь. FR-003, FR-004.

## Phase 5: US3 — точные тексты и каталог (P2)

**Independent Test**: production renderer/privacy coverage, summary focus, consumer scan.

- [X] T009 [US3] Добавить regression фокуса/текстов и production-renderer privacy coverage в apps/server/tests/unit/test_cabinet_web_shell.py и apps/server/tests/contract/test_cabinet_static_assets_contract.py. FR-006–FR-008.
- [X] T010 [US3] Исправить summary focus, пользовательские тексты, locale notice и role/status labels в apps/server/src/twobrain_rec_server/cabinet/ и apps/server/src/twobrain_rec_server/admin/. FR-006, FR-007.
- [X] T011 [US3] Удалить доказанно неиспользуемые19 макросов и20 CSS tokens в apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/components/{sections,primitives}.html и static/cabinet/cabinet.css с обновлением каталоговых тестов. FR-008, FR-010.

## Phase 6: Validation and PR

- [ ] T012 Выполнить high-risk-feature quickstart, correctness/Ponytail review и converge; записать команды, результаты и ограничения в specs/243-cabinet-audit-remediation/validation/implementation-evidence.md.
- [ ] T013 Добавить changes/unreleased/F243.yaml, commit/push/PR с exact-SHA governance-fast и согласовать статусы tasks/issues в specs/243-cabinet-audit-remediation/tasks.md.

## Dependencies & Execution Order

T001→T002 блокируют реализацию. T003→T004→T005; T006→T007→T008;
T009→T010→T011; все три истории→T012→T013. Проверки US1 независимы от
браузерного кода; Python/Swift проверки могут идти параллельно без записи в
одни файлы. F242/F244 не редактируются из этой задачи.

## Implementation Strategy

Инкрементально US1→US2→US3. Не завершать пользовательскую задачу только US1.
Не менять checklist markers в implementation. Новые обязательные находки
добавлять отдельными задачами при converge, не переписывая историю.

## GitHub ownership

Umbrella: https://github.com/yshishenya/graf/issues/6567.
- T001,T002: https://github.com/yshishenya/graf/issues/6567
- T003,T004,T005: https://github.com/yshishenya/graf/issues/6573
- T006,T007: https://github.com/yshishenya/graf/issues/6574
- T008: https://github.com/yshishenya/graf/issues/6575
- T009,T010: https://github.com/yshishenya/graf/issues/6576
- T011: https://github.com/yshishenya/graf/issues/6577
- T012,T013: https://github.com/yshishenya/graf/issues/6578

## Phase 7: Convergence

- [ ] T014 [US2] После финального коммита F240 проверить полный контраст списка, меню и диалогов в шести сочетаниях тем, записать точный SHA и совместные результаты в specs/243-cabinet-audit-remediation/validation/implementation-evidence.md по FR-003, SC-001, US2/AC1 (partial, HIGH). Владелец реализации F240; отслеживание совместной приёмки: #6575.
- [ ] T015 [US2] После финального коммита F242 проверить сохранение темы и неизменность locale/timezone через серверную форму и перезагрузку, записать точный SHA в specs/243-cabinet-audit-remediation/validation/implementation-evidence.md по FR-004, SC-003, US2/AC2 (missing, HIGH). Владелец реализации F242; отслеживание совместной приёмки: #6575.
- [ ] T016 [US2] После финального коммита F244 проверить совместные изменения upload/rail/focus и отсутствие конфликтов в cabinet.js/cabinet.css, записать точные SHA и результаты в specs/243-cabinet-audit-remediation/validation/implementation-evidence.md по plan: Coordination, SC-004 (partial, MEDIUM). Владелец реализации F244; отслеживание совместной приёмки: #6575. До T014–T016 разрешён только зависимый draft PR, не готовность к merge/release.
