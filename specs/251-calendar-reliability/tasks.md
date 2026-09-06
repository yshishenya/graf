# Tasks: Надёжные календари
## Setup and gates
- [X] T001 Утвердить требования, clarify, план, checklist review и analyze в `specs/251-calendar-reliability/`; синхронизировать GitHub issues.
## US1: Полные сведения и правильные события
- [X] T002 [P] [US1] Добавить регрессии и исправить полные данные, CalDAV recurrence/TZID/participants, Google tombstones/links в `apps/server/src/twobrain_rec_server/calendar/{normalize,caldav,google,providers,conference_links}.py`, `apps/server/tests/unit/test_{calendar_normalization,caldav_provider,google_calendar_provider,calendar_participants,calendar_conference_links}.py`; обновить `apps/server/{pyproject.toml,uv.lock,constraints.txt}`. FR-001,002,003,009.
## US2: Синхронизация и восстановление
- [X] T003 [P] [US2] Добавить регрессии и исправить scheduler/claims/catalog/tombstone apply в `apps/server/src/twobrain_rec_server/calendar/{worker,sync,service}.py`, `apps/server/tests/unit/test_calendar_worker.py`, `apps/server/tests/integration/test_calendar_provider_runtime.py`; проверить selection/disconnect races. FR-004,005,008,009.
- [X] T004 [US1] Сохранить полный owner content с защищённым roundtrip, обновить модели/миграцию в `apps/server/src/twobrain_rec_server/db/`, owner projections в `apps/server/src/twobrain_rec_server/api/calendar.py`, `apps/server/src/twobrain_rec_server/calendar/service.py`; full refresh representation version и миграционные проверки. FR-001,009.
## US3: Пользовательский путь
- [X] T005 [P] [US3] Добавить регрессии и исправить owner display, empty/live refresh, dirty/focus, per-source errors, selection sync в `apps/server/src/twobrain_rec_server/cabinet/{view_models.py,rendering.py,web_routes/calendar.py,web_routes/calendar_helpers.py,templates/cabinet/fragments/calendar_settings.html,static/cabinet/cabinet.js}` и соответствующих UI tests. FR-006,007,008,010.
- [X] T006 [US3] Проверить и уточнить обновление native календаря в `apps/macos/RecApp/Sources/Calendar/CalendarTray.swift` и `apps/macos/Shared/Tests/DesktopCalendarReminderTests.swift`, выполнить synthetic browser/embedded полный путь. FR-006,010.
## Validation and closeout
- [ ] T007 Выполнить calendar-focused PostgreSQL, JS/browser, Swift, fast gate, независимую проверку diff и converge; записать доказательства и границы в `specs/251-calendar-reliability/validation.md`. FR-001..010, SC-001..004.
- [X] T008 Подготовить `changes/unreleased/F251.yaml`, сверить issues/tasks и итоговые ограничения; код не коммитить и не выпускать без дальнейшего разрешения.
## Dependencies and parallel execution
T001 -> T002/T003/T005 (parallel independent ownership); T004 after provider shape agreed, no concurrent service.py writer; T006 after T005; T007 -> T008. Root owns sync/persistence and final integration. Provider and UI work may execute in parallel per speckit-implement phase/file coordination. Tests precede each implementation and old policy assertions change only for owner view.

## Implementation evidence — 2026-09-06
T002–T006 реализованы. Дополнительные затронутые части T003: независимый старт `workflows/maintenance_worker.py` и двух Compose-файлов, ежедневное обновление Google horizon и восстановление конфигурации. T002 использует `calendar/caldav_parse.py` для завершаемого процесса разбора. T004 расширяет owner API без скрытия содержимого и требует ключ до записи. Подробные доказательства и границы — `validation.md`.

GitHub issues остаются открыты до привязки разрешённого PR/точного SHA и closure evidence; отметка реализации в этом файле не означает выпуск или завершение production-проверки. T007/T008 закрываются после итоговой сверки в текущей задаче; формальная проверка PR и выпуск выполняются отдельным разрешённым шагом.

## Local closeout
T008: changelog fragment и итоговый отчёт подготовлены; GitHub issue map сверена. T007: все исполняемые локальные проверки завершены успешно, включая 1 428 server unit, 154 PostgreSQL contract/integration, 802 Swift и browser. Формальная запись fast остаётся `ambiguous` для незакоммиченного дерева; задача оставлена открытой до разрешённого коммита и exact-SHA проверки PR. Production и macOS release не выполнены. Reviewer-owned checklist не менялся реализацией.
