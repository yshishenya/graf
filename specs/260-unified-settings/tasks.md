# Tasks: Единые настройки GRAF

**Lane**: High-risk product / reference-fidelity UX. Источник: spec.md, plan.md, design-handoff.md, contracts/settings.md.
**Статус**: макет принят владельцем («Подтверждаю, реализовать»); требования приняты независимым reviewer 9/9. Реализация начата.

## Phase 1 — Исследование и проект
- [X] T001 Изучить установленный Krisp и текущие пути GRAF; зафиксировать наблюдения, причины дефектов и ограничения в `specs/260-unified-settings/reference-audit.md` и `research.md`. [FR-001–006/016]
- [X] T002 Подготовить и проверить интерактивный макет `specs/260-unified-settings/prototype.html`, минимальную проверку `prototype-check.cjs` и передачу `design-handoff.md`; выполнить матрицу макета из `quickstart.md`. [FR-004–005/007/014–015]

## Phase 2 — Предпосылки реализации
- [X] T003 Принять независимую проверку требований в `specs/260-unified-settings/checklists/ux-security.md`, выполнить analyze без critical/high и сохранить принятое заключение в `analysis.md`. Автор реализации не отмечает reviewer checklist. [FR-001–017, SC-005]
- [X] T004 Выполнить canonical issue sync через speckit-taskstoissues; сохранить уникальные ссылки задач в `specs/260-unified-settings/issue-map.md`, проверить канон. [SC-005]

## Phase 3 — US1: одна навигация
Цель: каждая обычная точка входа открывает одно основное окно; fallback честно доступен без сервера.
Independent test: меню/Cmd+,/профиль/контекст записи и уведомления, переходы/возврат, loading/offline/recovery.
- [X] T005 [US1] Сначала обновить navigation regression в `apps/server/tests/unit/test_settings_view_models.py`, `apps/server/tests/contract/test_settings_ui_contract.py` и `apps/macos/Shared/Tests/AppControlAccessibilityTests.swift`. [FR-001–003/013]
- [X] T006 [US1] Упростить список/группы и стартовую страницу в `apps/server/src/twobrain_rec_server/cabinet/view_models.py`, `web_routes/settings.py`, `templates/cabinet/components/sections.html`, `templates/cabinet/pages/settings_content.html`, `templates/cabinet/pages/settings_account_content.html`; сохранить действующие операции. [FR-001–002/011]
- [X] T007 [US1] Объединить точки входа и резерв в `apps/macos/RecApp/App/TwoBrainRecApp.swift`; убрать NSTabViewController, добавить единственную sidebar и переход обратно; обновить совместимые маршруты в `apps/macos/RecApp/Sources/Cabinet/DesktopCabinetRoutePolicy.swift` и `EmbeddedCabinetWebView.swift`. [FR-002–003/013/017]

## Phase 4 — US2: читаемые приложения
Цель: имя/правило и поиск для полного реестра, без потери состояния.
Independent test: один target/bulk/mixed/empty/long name/search/save error/повторное открытие.
- [X] T008 [US2] Уточнить проверки в `apps/macos/Shared/Tests/EmbeddedCabinetRecordingSettingsBridgeTests.swift` и `apps/server/tests/contract/test_settings_ui_contract.py` для сохранности правил, поиска и mixed. [FR-004–007/013/017]
- [X] T009 [US2] Заменить три кнопки на Picker и убрать внутренний sidebar в `apps/macos/RecApp/Sources/MeetingDetection/MeetingDetectionSettingsView.swift`; унифицировать `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/settings_recording_content.html` и обработку поиска/подтверждённых значений в `static/cabinet/cabinet.js`. [FR-004–007/013]

## Phase 5 — US3: уведомления в одном разделе
Цель: локальные и аккаунтные правила с разными владельцами на одном экране.
Independent test: четыре local поля, системные статусы, auth A→B→A, pending logout, error/timeout, no-JS/server conflict.
- [X] T010 [US3] Добавить отрицательные/async/WebKit проверки в `apps/macos/Shared/Tests/EmbeddedCabinetNotificationSettingsBridgeTests.swift`; сохранить regression в `DesktopNotificationControlTests.swift` и `DesktopLocalNotificationDeliveryTests.swift`. [FR-008–013]
- [X] T011 [US3] Реализовать `apps/macos/RecApp/Sources/Cabinet/EmbeddedCabinetNotificationSettingsBridge.swift`, проверки authEpoch внутри async enable/test перед побочными действиями, явный save result/context generation в `apps/macos/RecApp/Sources/Notifications/DesktopNotificationPresenter.swift` и lifecycle wiring в `apps/macos/RecApp/Sources/Cabinet/EmbeddedCabinetWebView.swift`. [FR-008–010/012–013/017]
- [X] T012 [US3] Встроить контролы и autosave в `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/settings_notifications_content.html`, `templates/cabinet/components/notifications.html`, `static/cabinet/cabinet.js`; сохранить CSRF/version/no-JS и проверить в `apps/server/tests/integration/test_settings_ia_flow.py`. [FR-007–013]

## Phase 6 — Общий вид и проверка
- [X] T013 Применить согласованную геометрию/темы/responsive/контраст в `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.css`, сохранив остальные страницы; обновить синтетическую fixture `apps/server/tests/fixtures/settings_visual_ui_harness.py`. [FR-014–016]
- [ ] T014 Выполнить матрицу `specs/260-unified-settings/quickstart.md`: профильные Swift/pytest, WebKit, no-JS, темы/200%/keyboard, rollback без сброса; записать реальные результаты в `validation.md`. [FR-001–017, SC-001–004]
- [ ] T015 После авторизованного commit проверить только `/Applications/GRAF Dev.app` через harness; сравнить с Krisp все точки входа/локальный резерв/VoiceOver; записать точный SHA и границы в `specs/260-unified-settings/validation.md`. [SC-001–005]
- [ ] T016 Выполнить Ponytail review сложного diff, convergence и required fast/governance-fast, добавить `changes/unreleased/F260.yaml`, согласовать evidence/PR/issues в `specs/260-unified-settings/validation.md`. Непройденные gates не считать закрытыми. [SC-005]

## Dependencies / Strategy
T001 → принятие макета владельцем → T003 → T004 → T005–T007 → T008–T009 → T010–T012 → T013–T016. Тесты предшествуют реализации своих сценариев. T007/T011 и T009/T012 разделяют файлы и выполняются последовательно. [P] намеренно не используется. После каждой US — независимая проверка по quickstart; выпуск не следует автоматически из локальной готовности. Авторизация на commit и продуктовый reviewer gate остаются отдельными условиями.

T002 завершена после проверки макета через Playwright; недоступность CUA не засчитывалась как визуальная проверка. Начало реализации разрешено владельцем после принятия макета и требований. F260 issues #6858–#6873 проверены напрямую, канон 16/16 PASS. Общая проверка канона блокируется посторонней #6852 (area label и Spec tasks: T000); чужая задача не изменяется.

## Implementation checkpoint — 2026-09-09
T002: Playwright заменил недоступный CUA для проверки макета; 42 сочетания раздела/ширины, 8 сценариев, модель PASS. T005–T013: код реализован, профильные Swift/WebKit 79/79 и server 81/81 PASS, визуальная матрица production templates с синтетическим мостом 36/36 PASS. Существующая settings_visual_ui_harness.py используется без дублирования; сценарии моста вынесены в visual-check.js. T014 остаётся открытой для полной матрицы доступности/системных состояний и VoiceOver. T015 требует авторизованного чистого commit и dev-harness. T016: Ponytail и проверка структуры выполнены; required governance-fast точного SHA и tracker closeout ещё не выполнены.
