# Tasks: Единый интерфейс настроек

## Phase 1 — Требования и контроль
- [X] T001 Подготовить и проверить spec/plan/research/contracts/checklists в `specs/246-settings-experience/`, синхронизировать задачи и выполнить analyze.

## Phase 2 — US1: единая композиция
- [X] T002 [US1] Обновить регрессионные проверки геометрии и сохранить маршруты в `apps/server/tests/contract/test_settings_ui_contract.py`; нормализовать колонки, строки и удалить мёртвые стили в `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.css`; уточнить шаблоны `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/settings_content.html`, `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/settings_account_content.html`, `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/settings_recording_content.html`, `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/settings_summaries_content.html`, `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/settings_notifications_content.html`, `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/settings_workspace_content.html` и `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/fragments/calendar_settings.html`.

## Phase 3 — US2: правдивые результаты
- [X] T003 [P] [US2] Добавить regression checks и исправить forwarding/classification в `apps/server/src/twobrain_rec_server/cabinet/web_routes/settings.py`, `apps/server/src/twobrain_rec_server/cabinet/rendering.py` и `apps/server/tests/unit/test_settings_outcomes.py`.

## Phase 4 — US3: нативная автозапись
- [X] T004 [P] [US3] Согласовать размеры и пояснения в `apps/macos/RecApp/Sources/MeetingDetection/MeetingDetectionSettingsView.swift`, `apps/macos/RecApp/App/TwoBrainRecApp.swift`; удалить мёртвую константу `apps/macos/RecApp/Sources/Cabinet/DesktopCabinetWorkspaceView.swift` с проверкой, выполнить связанные Swift tests.

## Phase 5 — Проверка и завершение
- [ ] T005 Выполнить synthetic visual/functional matrix, профильные suites, independent review и convergence; записать evidence в `specs/246-settings-experience/quickstart.md` и `changes/unreleased/F246.yaml`.

## Dependencies
T001 → T002/T003/T004 → T005. T003/T004 независимы и владеют отдельными файлами; T002/CSS и визуальная проверка последовательны. Каждый US имеет independent test в spec. Начать с центрирования, затем выполнить весь согласованный объём.

Общие формы T002 также используют `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js` и `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/components/notifications.html`.

## Issue mapping
Umbrella: #6597. Связи зарегистрированы до реализации.

- T001: https://github.com/yshishenya/graf/issues/6599
- T002: https://github.com/yshishenya/graf/issues/6600
- T003: https://github.com/yshishenya/graf/issues/6601
- T004: https://github.com/yshishenya/graf/issues/6602
- T005: https://github.com/yshishenya/graf/issues/6603

## Локальное выполнение — 2026-09-06
T002–T004 реализованы и прошли профильные проверки, evidence в quickstart.md. T005: автоматическая матрица, suites, независимый review и convergence выполнены; проверка нативной ошибки и AX выполнена после master sync; остаётся звуковой прогон VoiceOver. Сохраняемый preview: `apps/server/tests/fixtures/settings_visual_ui_harness.py`; браузерная проверка: `specs/246-settings-experience/visual-check.cjs`. Issues не закрываются без полного acceptance/PR evidence.
