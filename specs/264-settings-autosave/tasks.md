# Tasks: F264 — Понятные настройки с автосохранением

Ветка: `264-settings-autosave`. Lane: high-risk reference-fidelity UX. Источник реализации — этот файл. GitHub umbrella #6961; задачи связаны ниже. Пользователь разрешил коммит, проверку GRAF Dev и подготовку PR. Позднее владелец прямо разрешил завершение разработки, merge и выпуск в production. VoiceOver он проверяет самостоятельно после выпуска.

## Phase 1 — Проверка требований

- [X] T001 Проверить требования и reviewer-owned checklists в specs/264-settings-autosave/checklists/ux.md и security.md; записать review.md и устранить CRITICAL/HIGH до кода. [FR-001–013]
- [X] T002 Выполнить analyze и синхронизировать задачи specs/264-settings-autosave/tasks.md с GitHub по project canon. [FR-012]

## Phase 2 — US2 Автосохранение

- [X] T003 [US2] Добавить проверку очереди/IME/навигации/ошибок/конфликтов, двух точек темы, тайм-аута/read-back, валидного пустого имени и выхода из невалидного черновика в apps/server/tests/browser/settings-autosave.test.cjs; адаптировать apps/server/tests/browser/timezone-settings.test.cjs под автоматическое сохранение. [FR-003/005/006/007/011]
- [X] T004 [US2] Объединить сохранение обычных форм в apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js; удалить конкурирующие обработчики уведомлений/ручного сохранения настроек; подключить тему и календарные формы. [FR-003/005/006/012]
- [X] T005 [US2] Обеспечить явный проверяемый результат, проверку ожидаемого владельца/области до записи и частичные записи либо сравнение исходной неделимой календарной группы под блокировкой в apps/server/src/twobrain_rec_server/cabinet/web_routes/settings.py и calendar.py; расширить существующие tests/unit/test_settings_view_models.py, tests/contract/test_settings_ui_contract.py и tests/integration/test_calendar_settings_flow.py соответствующими сценариями. [FR-005/007/009]
- [X] T006 [US2] Применить тот же протокол состояний к текущему выбору формата и редактированию существующего личного формата в apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js и templates/cabinet/pages/settings_summaries_content.html; создание оставить явным; сохранить expected_version, проверить конфликт/валидность и все пути закрытия диалога в apps/server/tests/contract/test_summary_template_ui_contract.py и существующих браузерных проверках. [FR-003/004/005/006/007]

## Phase 3 — US1 Единая структура

- [X] T007 [US1] Привести существующие строки, группы и элементы к общей системе в apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.css и templates/cabinet/components/primitives.html; удалить противоречащие настройки старых селекторов. [FR-002/010/012]
- [X] T008 [US1] Упростить все settings_*_content.html в apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/ и components/notifications.html; убрать обычные Save/Reset и повторяющийся текст, реализовать no-JS состояние. [FR-001/002/003/004/011]
- [X] T009 [US1] Упростить apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/fragments/calendar_settings.html: прямые группы фильтров/отображения/подсказок, без шести абзацев; contextual errors и выбор календарей остаются. [FR-001/002/003/009]
- [X] T010 [US1] Проверить и унифицировать billing_*_content.html и связанные вложенные формы в apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/; убрать дублирующий рекламный/поясняющий текст, сохранить действительные условия и явные финансовые действия. [FR-001/002/004]

## Phase 4 — US3 Поверхности и приёмка

- [X] T011 [US3] Привести резервные локальные настройки записи/уведомлений apps/macos/RecApp/Sources/MeetingDetection/MeetingDetectionSettingsView.swift и apps/macos/RecApp/Sources/Notifications/DesktopNotificationPresenter.swift к общей структуре и правдивым состояниям; проверить отказ записи/моста и tests в apps/macos/Shared/Tests/; в apps/macos/RecApp/Sources/Cabinet/EmbeddedCabinetWebView.swift и существующем контроллере окна обеспечить штатную защиту закрытия/перехода с незавершённой записью. [FR-001/005/006/008/010/012/013]
- [X] T012 [US3] Проверить семь разделов с синтетическими данными через apps/server/tests/fixtures/settings_visual_ui_harness.py: все ширины/темы/клавиатура/no-JS/ошибки из specs/264-settings-autosave/quickstart.md. [SC-001–004]
- [X] T013 [US3] После чтения docs/agent-guidance/local-development.md проверить только /Applications/GRAF Dev.app через dev-harness: настройки, сохранение, переходы, локальные отказы и доступность; записать реальные пределы в specs/264-settings-autosave/validation.md. [SC-002–005, FR-008/010]

## Phase 5 — Завершение

- [X] T014 Выполнить focused проверки и converge, добавить changes/unreleased/F264.yaml; записать незавершённое в specs/264-settings-autosave/validation.md, не закрывать issues без требуемой приёмки. [SC-001–005]

## Зависимости

T001 → T002 → T003 → T004/T005 → T006. T002 → T007 → T008/T009/T010; подключение автосохранения требует T004/T005. T011 после T004–T006; T012 после всех страниц и T011, T013 после T012, T014 после приёмки. Никаких параллельных писателей cabinet.js. Доставка в этом запросе — весь объём, не только первая история.

## Покрытие после проверки требований

FR-001: T001/T008–T013; FR-002: T007–T010; FR-003: T003/T004/T006/T008/T009; FR-004: T006/T008/T010; FR-005: T003–T006/T011; FR-006: T003/T004/T006/T011; FR-007: T003/T005/T006; FR-008: T011/T013; FR-009: T005/T009; FR-010: T007/T011–T013; FR-011: T003/T008/T012; FR-012: T002/T004/T007/T011; FR-013: T011/T013. SC-001–005: T012–T014. Сценарии из quickstart.md входят в критерии соответствующих задач, включая повтор после потерянного ответа и осознанный выход без сохранения.

## GitHub

- T001 (Issue #6962): https://github.com/yshishenya/graf/issues/6962
- T002 (Issue #6963): https://github.com/yshishenya/graf/issues/6963
- T003 (Issue #6964): https://github.com/yshishenya/graf/issues/6964
- T004 (Issue #6965): https://github.com/yshishenya/graf/issues/6965
- T005 (Issue #6966): https://github.com/yshishenya/graf/issues/6966
- T006 (Issue #6967): https://github.com/yshishenya/graf/issues/6967
- T007 (Issue #6968): https://github.com/yshishenya/graf/issues/6968
- T008 (Issue #6969): https://github.com/yshishenya/graf/issues/6969
- T009 (Issue #6970): https://github.com/yshishenya/graf/issues/6970
- T010 (Issue #6971): https://github.com/yshishenya/graf/issues/6971
- T011 (Issue #6972): https://github.com/yshishenya/graf/issues/6972
- T012 (Issue #6973): https://github.com/yshishenya/graf/issues/6973
- T013 (Issue #6974): https://github.com/yshishenya/graf/issues/6974
- T014 (Issue #6975): https://github.com/yshishenya/graf/issues/6975
- T015 (Issue #6978): https://github.com/yshishenya/graf/issues/6978

## Phase 6: Convergence

- [X] T015 [US3] Завершить оставшуюся приёмку T012/T013 в единственном /Applications/GRAF Dev.app после отдельно одобренного коммита: проверить каждую страницу, 200% масштаб, клавиатуру/VoiceOver, закрытие окна и переходы при незавершённой записи, локальные отказы; получить визуальную оценку владельца и записать evidence в specs/264-settings-autosave/validation.md. HIGH; FR-008/010/013, SC-002/004/005 (partial). Браузерный макет и Swift tests не заменяют эту проверку; коммит и проверка GRAF Dev разрешены следующим сообщением пользователя; публикация релиза остаётся отдельным этапом. [GitHub #6978](https://github.com/yshishenya/graf/issues/6978)

## Закрытие владельцем — 2026-09-15

Владелец после выпуска и проверки установленной версии прямо поручил закрыть фичу и все связанные issues. T013–T015 закрыты в согласованном объёме: агентская приёмка GRAF Dev, исправления, CI, production и публичный выпуск подтверждены в validation.md. VoiceOver ранее явно передан владельцу и не объявляется пройденным; отдельной новой визуальной оценки в этом запросе не было. Запрос на закрытие принят как решение владельца завершить работу с указанными ограничениями. Историческая формулировка T015 выше сохраняется для прослеживаемости, объём проверки уточнён этим решением.
