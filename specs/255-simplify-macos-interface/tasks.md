# Tasks: Единая и простая оболочка GRAF

**Input**: spec.md, plan.md, research.md, data-model.md, contracts/interface.md, journeys.md, inventory.md, quickstart.md.
**Lane**: high-risk-feature. Все задачи открыты до выполнения и evidence. Custom checklist оценивает рецензент; реализация его не отмечает.

## Phase 1: Допуск и исходная точка

- [ ] T001 Завершить review требований в `specs/255-simplify-macos-interface/checklists/ux.md` и `checklists/security.md`, проверить analyze и владельцев зависимостей в `inventory.md`, закрепить допуск в `validation/readiness.md`. FR-013/FR-016; это review рецензента, не самоодобрение реализации.

## Phase 2: Проверяемая основа

- [ ] T002 Подтвердить системную sidebar со стабильным WebView и текущим titlebar в `apps/macos/RecApp/Sources/Cabinet/DesktopCabinetWorkspaceView.swift`; записать нативный прототип macOS 26, minimum window и matte в `specs/255-simplify-macos-interface/validation/native-prototype.md`. FR-003/FR-004/FR-015. До расширения интеграции материал должен быть доказан.
- [ ] T003 Добавить сначала падающие проверки допуска версии/origin/main frame/payload/поколения/сессии и стабильности navigation в `apps/macos/Shared/Tests/EmbeddedCabinetShellBridgeTests.swift` и `apps/macos/Shared/Tests/DesktopCabinetWorkspaceTests.swift`. FR-008/FR-015; не подменять runtime компоновку source-string assertions.

## Phase 3: US1 — короткая и рабочая навигация (P1)

**Independent Test**: journeys.md для основных разделов/профиля; ноль заглушек и пустых подменю; HTML fallback и формы работают без native.

- [ ] T004 [US1] Обновить сначала падающие контракты меню и форм в `apps/server/tests/unit/test_cabinet_navigation_model.py`, `apps/server/tests/unit/test_cabinet_web_shell.py`, `apps/server/tests/contract/test_cabinet_shell_response_contract.py`: основные разделы в настройках, отсутствие постоянных заглушек, сохранение рабочих команд и no-JS. FR-001/FR-002/FR-007/FR-011.
- [ ] T005 [US1] Реализовать ограниченный desktop-shell/v1 в `apps/macos/RecApp/Sources/Cabinet/EmbeddedCabinetShellBridge.swift`, подключить в `EmbeddedCabinetWebView.swift` и `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js`; сохранить route controller, поколение, fallback и формы/CSRF. FR-005/FR-008/FR-015.
- [ ] T006 [US1] Согласовать источник меню и профиль в `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/components/sections.html` и при необходимости `cabinet/view_models.py`: удалить 10 заглушек/2 пустых подменю, сохранить рабочие входы, основные разделы в настройках; связать native snapshot в `apps/macos/RecApp/Sources/Cabinet/DesktopCabinetWorkspaceView.swift`. FR-001/FR-002/FR-007/FR-008.

## Phase 4: US2 — два материала с одинаковым поведением (P1)

**Independent Test**: macOS 14.5/26, темы/доступность, system glass и matte; одинаковые команды и identity WebView/capture. US2 использует контракт US1, но имеет отдельную матрицу приёмки.

- [ ] T007 [US2] Дополнить `apps/macos/Shared/Tests/DesktopCabinetWorkspaceTests.swift` и `DesktopMeetingShellWebViewBoundaryTests.swift` проверками темы/system, очистки snapshot и неизменности существующей границы записи при смене оболочки; ожидания runtime закрепить в `specs/255-simplify-macos-interface/validation/acceptance.md`. FR-004/FR-005/FR-009/FR-015.
- [ ] T008 [US2] Встроить системный материал и непрозрачное исполнение, синхронизацию темы и семантические цвета в `apps/macos/RecApp/Sources/Cabinet/DesktopCabinetWorkspaceView.swift`, `DesktopMeetingShellView.swift`, `EmbeddedCabinetWebView.swift`; при необходимости передать существующее предпочтение из `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/base.html`. FR-003/FR-004/FR-005/FR-009/FR-015; без нового хранения и capture изменений.
- [ ] T009 [US2] Применить матовую геометрию и роли границ в `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.css`; обеспечить профиль/навигацию, фокус и 200% в `cabinet.js` и native workspace без второго набора контролов. FR-003/FR-006/FR-010/FR-011.

## Phase 5: US3 — согласованность и адресная чистка (P2)

**Independent Test**: inventory.md покрыт результатами; для каждого удаления найден весь круг потребителей и есть профильная проверка, рабочий local mode сохранён.

- [ ] T010 [US3] Повторно найти все потребители и убрать только перекрытые CSS декларации и доказанно недостижимую queue-ветку в `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.css` и `apps/macos/RecApp/Sources/Cabinet/DesktopMeetingShellView.swift`; обновить затронутые проверки и `specs/255-simplify-macos-interface/validation/cleanup.md`. FR-012/SC-005; .card и local mode не удалять без отдельного доказательства.
- [ ] T011 [US3] Завершить общие роли заголовков/действий/состояний в `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.css` и согласовать реальные F245–F253, admin/public/no-JS, ресурсы и отклонения reference в `specs/255-simplify-macos-interface/inventory.md` и `validation/acceptance.md`. FR-010/FR-011/FR-013/FR-014.

## Phase 6: Приёмка, PR и выпуск

- [ ] T012 Выполнить всю матрицу `specs/255-simplify-macos-interface/quickstart.md`, записать версии/SHA, сценарии/контраст/снимки и ограничения в `validation/acceptance.md`. FR-001–FR-016/SC-001–SC-006. Реальное native evidence и смешанные версии обязательны; незакрытые строки блокируют готовность.
- [ ] T013 Провести converge и review простоты, обновить `specs/255-simplify-macos-interface/tasks.md`, записать `validation/convergence.md`, подготовить `changes/unreleased/255-simplify-macos-interface.md`; после разрешения владельца на коммит оформить PR с exact-SHA governance-fast и согласовать закрытие выполненных issues. FR-012/FR-013/FR-014/FR-016.
- [ ] T014 После допуска к выпуску пройти frozen candidate/Full CI/CD dry-run и релизные проверки, Developer ID/notarization/stapling/Gatekeeper/Sparkle/live appcast, smoke и русский CalVer release по `docs/agent-guidance/release-and-validation.md` и `docs/agent-guidance/macos-notarization.md`; сохранить evidence в `specs/255-simplify-macos-interface/validation/release.md`. FR-016/SC-006; без разрешения/gates не публиковать.

## Dependencies & Execution Order

T001 → T002 → T003 → T004 → T005 → T006 → T007 → T008 → T009 → T010 → T011 → T012 → T013 → T014.

Тесты T003/T004/T007 сначала фиксируют ожидаемое новое поведение, затем соответствующая реализация. Связанные пути существующих тестов расширяются, а не создают параллельную тестовую систему. US1 — первый полезный этап; затем два материала, затем зачистка и общая приёмка. Частичный этап не считается выполнением запроса о двух материалах.

## Parallel opportunities

У задач нет [P]: изменения затрагивают одни shell/CSS/JS файлы, последовательность уменьшает конфликты. После реализации можно независимо прогнать Swift и pytest; внутри US1 сравнить web/native сценарии, US2 — матрицы обеих ОС, US3 — web/admin потребителей. Параллельные прогоны не означают разрешение делегировать implementation review.

## GitHub ownership

Umbrella/reservation: #6752. Task ownership синхронизировано 2026-09-06; T001 остаётся открытой до фактического review. Открытые задачи не закрываются за наличие документа. Чужие F245–F253 и #5804 не присваиваются F255.


| Spec tasks | GitHub issue |
|---|---|
| T001, T014 | [#6752](https://github.com/yshishenya/graf/issues/6752) |
| T002, T003 | [#6753](https://github.com/yshishenya/graf/issues/6753) |
| T004, T005, T006 | [#6754](https://github.com/yshishenya/graf/issues/6754) |
| T007, T008, T009 | [#6755](https://github.com/yshishenya/graf/issues/6755) |
| T010, T011 | [#6756](https://github.com/yshishenya/graf/issues/6756) |
| T012, T013 | [#6757](https://github.com/yshishenya/graf/issues/6757) |

#6752 сохраняет reservation/umbrella и не закрывается после одного T001: владеет также T014. Остальные issues закрываются только после выполнения всей группы и closure evidence.
