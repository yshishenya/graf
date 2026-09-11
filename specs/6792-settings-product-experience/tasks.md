# Tasks: Понятные настройки GRAF

**Input**: spec.md, plan.md, research.md, data-model.md, contracts/settings-ux.md, quickstart.md.
**Lane**: high-risk-feature. Все checkbox реализации отмечаются только после соответствующей проверки. Reviewer-owned checklist отдельно.

## Phase 1: Исследование
- [X] T001 Зафиксировать осмотр GRAF Dev, наблюдаемый Krisp и карту путей в specs/6792-settings-product-experience/research.md и contracts/settings-ux.md; создать и проверить интерактивный макет specs/6792-settings-product-experience/prototype.html. (Issue #6916)

## Phase 2: Условия начала
- [X] T002 Завершить независимую проверку specs/6792-settings-product-experience/checklists/ux.md и analyze; связать задачи с GitHub в specs/6792-settings-product-experience/tasks.md. (Issue #6916)

## Phase 3: US1 — Найти настройку
Независимая проверка: семь разделов доступны по тексту; в настройках есть место; Start/Stop доступны.
- [X] T003 [US1] Расширить проверки меню и правой панели в apps/macos/Shared/Tests/DesktopMeetingShellWebViewBoundaryTests.swift и CabinetSidebarRuntimeTests.swift до изменения поведения (FR-001, FR-003, FR-011). (Issue #6917)
- [X] T004 [US1] Согласовать состояние настроек и панели в apps/macos/RecApp/Sources/Cabinet/DesktopMeetingShellView.swift и apps/macos/RecApp/App/TwoBrainRecApp.swift (FR-003). (Issue #6917)
- [X] T005 [US1] Привести меню и общую композицию к наблюдаемому Krisp в apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.css и cabinet.js (FR-001–002, FR-010–011). (Issue #6917)

## Phase 4: US2 — Подготовить встречи
Независимая проверка: поиск приложения, формат итогов, подключение календаря и напоминания достижимы; данные и правила сохранены.
- [X] T006 [US2] Уточнить контрактные проверки семи разделов и состояний в apps/server/tests/contract/test_settings_ui_contract.py и test_calendar_settings_contract.py (FR-004–012). (Issue #6918)
- [X] T007 [US2] Упростить запись, итоги и уведомления в apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/settings_recording_content.html, settings_summaries_content.html, settings_notifications_content.html и существующих сообщениях cabinet.js (FR-004, FR-006, FR-009–010). (Issue #6918)
- [X] T008 [US2] Перестроить подключение календарей и тексты в apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/fragments/calendar_settings.html и cabinet/view_models.py (FR-005, FR-010, FR-012). (Issue #6919)

## Phase 5: US3 — Профиль, пространство и тариф
Независимая проверка: имя/оформление/время можно сохранить и отменить; защищённые действия остаются защищёнными.
- [X] T009 [US3] Упростить аккаунт, пространства и вложенные формы в apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/settings_account_content.html, settings_workspace_content.html и cabinet/fragments/provider_link_settings.html (FR-007–008, FR-010, FR-012). (Issue #6920)
- [X] T010 [US3] Переписать технические пояснения оплаты в apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/billing_overview_content.html и связанных billing_*_content.html без изменения финансовых форм (FR-008, FR-012). (Issue #6920)

## Phase 6: Проверка и завершение
- [X] T011 Выполнить целевые проверки и независимый обзор упрощения, записать факты в specs/6792-settings-product-experience/validation.md и changes/releases/v2026.09.11.2/F6792.yaml (SC-001–004). (Issue #6921)
- [X] T012 После разрешённого коммита проверить все разделы и состояния в GRAF Dev по specs/6792-settings-product-experience/quickstart.md; зафиксировать точный SHA, CI и converge в validation.md (SC-005). (Issue #6921)

## Dependencies
T001 → T002 → T003 → T004 → T005 → T006 → T007/T008/T009/T010 → T011 → T012.
Общий CSS/JS имеет одного автора. Параллельные изменения не требуются; независимый reviewer проверяет требования и итоговый diff, не реализует свой список проверки.

## Implementation Strategy
Сначала навигация, затем повседневные сценарии, затем редкие действия, далее общая приёмка. Все семь разделов входят в результат; промежуточная готовность одного раздела не означает завершение фичи.

## GitHub ownership

- T001, T002: https://github.com/yshishenya/graf/issues/6916
- T003, T004, T005: https://github.com/yshishenya/graf/issues/6917
- T006, T007: https://github.com/yshishenya/graf/issues/6918
- T008: https://github.com/yshishenya/graf/issues/6919
- T009, T010: https://github.com/yshishenya/graf/issues/6920
- T011, T012: https://github.com/yshishenya/graf/issues/6921
