# Tasks: Единые настройки GRAF

**Lane**: High-risk product / reference-fidelity UX. Источник: spec.md, plan.md, design-handoff.md, contracts/settings.md.
**Статус**: макет принят владельцем («Подтверждаю, реализовать»); требования приняты независимым reviewer 9/9. Реализация и профильная матрица выполнены; итоговые exact-SHA receipts публикуются в PR #6900.

## Phase 1 — Исследование и проект
- [X] T001 Изучить установленный Krisp и текущие пути GRAF; зафиксировать наблюдения, причины дефектов и ограничения в `specs/260-unified-settings/reference-audit.md` и `research.md`. [FR-001–006/016] (Issue #6858)
- [X] T002 Подготовить и проверить интерактивный макет `specs/260-unified-settings/prototype.html`, минимальную проверку `prototype-check.cjs` и передачу `design-handoff.md`; выполнить матрицу макета из `quickstart.md`. [FR-004–005/007/014–015] (Issue #6859)

## Phase 2 — Предпосылки реализации
- [X] T003 Принять независимую проверку требований в `specs/260-unified-settings/checklists/ux-security.md`, выполнить analyze без critical/high и сохранить принятое заключение в `analysis.md`. Автор реализации не отмечает reviewer checklist. [FR-001–017, SC-005] (Issue #6860)
- [X] T004 Выполнить canonical issue sync через speckit-taskstoissues; сохранить уникальные ссылки задач в `specs/260-unified-settings/issue-map.md`, проверить канон. [SC-005] (Issue #6861)

## Phase 3 — US1: одна навигация
Цель: каждая обычная точка входа открывает одно основное окно; fallback честно доступен без сервера.
Independent test: меню/Cmd+,/профиль/контекст записи и уведомления, переходы/возврат, loading/offline/recovery.
- [X] T005 [US1] Сначала обновить navigation regression в `apps/server/tests/unit/test_settings_view_models.py`, `apps/server/tests/contract/test_settings_ui_contract.py` и `apps/macos/Shared/Tests/AppControlAccessibilityTests.swift`. [FR-001–003/013] (Issue #6862)
- [X] T006 [US1] Упростить список/группы и стартовую страницу в `apps/server/src/twobrain_rec_server/cabinet/view_models.py`, `web_routes/settings.py`, `templates/cabinet/components/sections.html`, `templates/cabinet/pages/settings_content.html`, `templates/cabinet/pages/settings_account_content.html`; сохранить действующие операции. [FR-001–002/011] (Issue #6863)
- [X] T007 [US1] Объединить точки входа и резерв в `apps/macos/RecApp/App/TwoBrainRecApp.swift`; убрать NSTabViewController, добавить единственную sidebar и переход обратно; обновить совместимые маршруты в `apps/macos/RecApp/Sources/Cabinet/DesktopCabinetRoutePolicy.swift` и `EmbeddedCabinetWebView.swift`. [FR-002–003/013/017] (Issue #6864)

## Phase 4 — US2: читаемые приложения
Цель: имя/правило и поиск для полного реестра, без потери состояния.
Independent test: один target/bulk/mixed/empty/long name/search/save error/повторное открытие.
- [X] T008 [US2] Уточнить проверки в `apps/macos/Shared/Tests/EmbeddedCabinetRecordingSettingsBridgeTests.swift` и `apps/server/tests/contract/test_settings_ui_contract.py` для сохранности правил, поиска и mixed. [FR-004–007/013/017] (Issue #6865)
- [X] T009 [US2] Заменить три кнопки на Picker и убрать внутренний sidebar в `apps/macos/RecApp/Sources/MeetingDetection/MeetingDetectionSettingsView.swift`; унифицировать `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/settings_recording_content.html` и обработку поиска/подтверждённых значений в `static/cabinet/cabinet.js`. [FR-004–007/013] (Issue #6866)

## Phase 5 — US3: уведомления в одном разделе
Цель: локальные и аккаунтные правила с разными владельцами на одном экране.
Independent test: четыре local поля, системные статусы, auth A→B→A, pending logout, error/timeout, no-JS/server conflict.
- [X] T010 [US3] Добавить отрицательные/async/WebKit проверки в `apps/macos/Shared/Tests/EmbeddedCabinetNotificationSettingsBridgeTests.swift`; сохранить regression в `DesktopNotificationControlTests.swift` и `DesktopLocalNotificationDeliveryTests.swift`. [FR-008–013] (Issue #6867)
- [X] T011 [US3] Реализовать `apps/macos/RecApp/Sources/Cabinet/EmbeddedCabinetNotificationSettingsBridge.swift`, проверки authEpoch внутри async enable/test перед побочными действиями, явный save result/context generation в `apps/macos/RecApp/Sources/Notifications/DesktopNotificationPresenter.swift` и lifecycle wiring в `apps/macos/RecApp/Sources/Cabinet/EmbeddedCabinetWebView.swift`. [FR-008–010/012–013/017] (Issue #6868)
- [X] T012 [US3] Встроить контролы и autosave в `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/settings_notifications_content.html`, `templates/cabinet/components/notifications.html`, `static/cabinet/cabinet.js`; сохранить CSRF/version/no-JS и проверить в `apps/server/tests/integration/test_settings_ia_flow.py`. [FR-007–013] (Issue #6869)

## Phase 6 — Общий вид и проверка
- [X] T013 Применить согласованную геометрию/темы/responsive/контраст в `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.css`, сохранив остальные страницы; обновить синтетическую fixture `apps/server/tests/fixtures/settings_visual_ui_harness.py`. [FR-014–016] (Issue #6870)
- [X] T014 Выполнить матрицу `specs/260-unified-settings/quickstart.md`: профильные Swift/pytest, WebKit, no-JS, темы/200%/keyboard, rollback без сброса; записать реальные результаты в `validation.md`. [FR-001–017, SC-001–004] (Issue #6871)
- [X] T015 После авторизованного commit проверить только `/Applications/GRAF Dev.app` через harness; сравнить с Krisp все точки входа/локальный резерв/VoiceOver; записать точный SHA и границы в `specs/260-unified-settings/validation.md`. [SC-001–005] (Issue #6872)
- [X] T016 Выполнить Ponytail review сложного diff, convergence и required fast/governance-fast, добавить `changes/unreleased/F260.yaml`, согласовать evidence/PR/issues в `specs/260-unified-settings/validation.md`. Непройденные gates не считать закрытыми. [SC-005] (Issue #6873)

## Dependencies / Strategy
T001 → принятие макета владельцем → T003 → T004 → T005–T007 → T008–T009 → T010–T012 → T013–T016. Тесты предшествуют реализации своих сценариев. T007/T011 и T009/T012 разделяют файлы и выполняются последовательно. [P] намеренно не используется. После каждой US — независимая проверка по quickstart; выпуск не следует автоматически из локальной готовности. Авторизация на commit и продуктовый reviewer gate остаются отдельными условиями.

T002 завершена после проверки макета через Playwright; недоступность CUA не засчитывалась как визуальная проверка. Начало реализации разрешено владельцем после принятия макета и требований. F260 issues #6858–#6873 проверены напрямую, канон 16/16 PASS. Общая проверка канона блокируется посторонней #6852 (area label и Spec tasks: T000); чужая задача не изменяется.

## Проверка реализации — 2026-09-09

T014: 100 Swift/WebKit, 81 PostgreSQL, 126 shell/settings и 36 production-template сочетаний PASS. T015: единственный GRAF Dev на 113abd487180241b322f2716aa35e2eabb007abc, harness 13/13, входы/сохранение/200%/offline/возврат PASS; VoiceOver включение, AX и клавиатура проверены, озвученный текст не записывался. Полный новый аудиоцикл не заявляется: согласованная граница FR-006 — 20 capture regressions и неизменённый аудиотракт. Подробности и ограничения в validation.md. Повтор последнего SHA обязателен перед готовностью PR.

T016: независимый итоговый review d5aba78c1 принят, CRITICAL 0 / HIGH 0; governance-fast run 34389811229 и pr-metadata run 34389811157 PASS на d5aba78c1f5e2f8dbb693d3ec03c153ac5e547c1. Все 16 issues связаны с PR #6900 и остаются открыты до merge. Документационный коммит потребует нового exact-SHA CI и Dev; окончательные receipts сохраняются в PR до снятия draft.

## Исправление по автоматическому review — 2026-09-10

P2 в discussion_r3971976053: тест создавал graf.local.test.<UUID>, а willPresent/openResponse распознавали только прежний exact ID. Оба пути теперь используют общий predicate: legacy ID или префикс с валидным UUID. Регрессия проверяет сформированный request, banner/list/sound, открытие настроек, тишину при active capture, неверные ID и dismiss. Все101 Swift/WebKit/capture-тестов PASS после правки. Независимый review принят, CRITICAL0/HIGH0. Новый commit требует повторных exact-SHA CI и установленного Dev; окончательное evidence публикуется в PR #6900. Предыдущее заключение о готовности f9200a95d заменяется этим уточнением; отсутствие прежнего системного баннера не считалось PASS.
