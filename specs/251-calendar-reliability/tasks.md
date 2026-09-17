# Tasks: Надёжные календари
## Setup and gates
- [X] T001 Утвердить требования, clarify, план, checklist review и analyze в `specs/251-calendar-reliability/`; синхронизировать GitHub issues. (Issue #6652)
## US1: Полные сведения и правильные события
- [X] T002 [P] [US1] Добавить регрессии и исправить полные данные, CalDAV recurrence/TZID/participants, Google tombstones/links в `apps/server/src/twobrain_rec_server/calendar/{normalize,caldav,google,providers,conference_links}.py`, `apps/server/tests/unit/test_{calendar_normalization,caldav_provider,google_calendar_provider,calendar_participants,calendar_conference_links}.py`; обновить `apps/server/{pyproject.toml,uv.lock,constraints.txt}`. FR-001,002,003,009. (Issue #6653)
## US2: Синхронизация и восстановление
- [X] T003 [P] [US2] Добавить регрессии и исправить scheduler/claims/catalog/tombstone apply в `apps/server/src/twobrain_rec_server/calendar/{worker,sync,service}.py`, `apps/server/tests/unit/test_calendar_worker.py`, `apps/server/tests/integration/test_calendar_provider_runtime.py`; проверить selection/disconnect races. FR-004,005,008,009. (Issue #6654)
- [X] T004 [US1] Сохранить полный owner content с защищённым roundtrip, обновить модели/миграцию в `apps/server/src/twobrain_rec_server/db/`, owner projections в `apps/server/src/twobrain_rec_server/api/calendar.py`, `apps/server/src/twobrain_rec_server/calendar/service.py`; full refresh representation version и миграционные проверки. FR-001,009. (Issue #6655)
## US3: Пользовательский путь
- [X] T005 [P] [US3] Добавить регрессии и исправить owner display, empty/live refresh, dirty/focus, per-source errors, selection sync в `apps/server/src/twobrain_rec_server/cabinet/{view_models.py,rendering.py,web_routes/calendar.py,web_routes/calendar_helpers.py,templates/cabinet/fragments/calendar_settings.html,static/cabinet/cabinet.js}` и соответствующих UI tests. FR-006,007,008,010. (Issue #6656)
- [X] T006 [US3] Проверить и уточнить обновление native календаря в `apps/macos/RecApp/Sources/Calendar/CalendarTray.swift` и `apps/macos/Shared/Tests/DesktopCalendarReminderTests.swift`, выполнить synthetic browser/embedded полный путь. FR-006,010. (Issue #6657)
## Validation and closeout
- [X] T007 Выполнить calendar-focused PostgreSQL, JS/browser, Swift, fast gate, независимую проверку diff и converge; записать доказательства и границы в `specs/251-calendar-reliability/validation.md`. FR-001..010, SC-001..004. (Issue #6658)
- [X] T008 Подготовить `changes/unreleased/F251.yaml`, сверить issues/tasks и итоговые ограничения; код не коммитить и не выпускать без дальнейшего разрешения. (Issue #6659)
## Dependencies and parallel execution
T001 -> T002/T003/T005 (parallel independent ownership); T004 after provider shape agreed, no concurrent service.py writer; T006 after T005; T007 -> T008. Root owns sync/persistence and final integration. Provider and UI work may execute in parallel per speckit-implement phase/file coordination. Tests precede each implementation and old policy assertions change only for owner view.

## Implementation evidence — 2026-09-06
T002–T006 реализованы. Дополнительные затронутые части T003: независимый старт `workflows/maintenance_worker.py` и двух Compose-файлов, ежедневное обновление Google horizon и восстановление конфигурации. T002 использует `calendar/caldav_parse.py` для завершаемого процесса разбора. T004 расширяет owner API без скрытия содержимого и требует ключ до записи. Подробные доказательства и границы — `validation.md`.

GitHub issues связаны с PR #6692. Отметки реализации и локальной проверки не означают выпуск или завершение production-проверки. Перед merge обязательна новая успешная проверка governance-fast на текущем SHA PR; итоговая ссылка фиксируется в PR.

## Local closeout
T007/T008: локальные проверки завершены, фрагмент changelog и отчёт подготовлены. Первый официальный governance-fast прошёл на `548f658835b3113c0d0ecf812530fea070aa3fd0` (run 34037269028). После обновления ветки и исправлений T009/T010 этот run — историческое свидетельство, не разрешение merge текущего SHA. Reviewer-owned checklist не менялся реализацией.

## Phase 1: Convergence — подготовка PR к выпуску
- [X] T009 [US1] Применять отмену экземпляра Google по provider_event_id при отсутствии iCalUID в `calendar/google.py`, проверить минимальный cancelled payload в `tests/unit/test_google_calendar_provider.py` и существующий путь удаления в `tests/integration/test_calendar_reliability.py`; FR-003/008, US1/AC3 (partial, HIGH). (Issue #6700)
- [X] T010 [US2] Отклонять неполный CalDAV Multi-Status и неверный XML до reconciliation в `calendar/caldav.py`; проверить REPORT/catalog errors и сохранность кеша в `tests/unit/test_caldav_provider.py` и `tests/integration/test_calendar_reliability.py`; FR-004/007/009 (contradicts, HIGH). (Issue #6701)

Все пути T009/T010 находятся под `apps/server/src/twobrain_rec_server/` либо `apps/server/` для `tests/`. Замечания найдены независимым release_review, подтверждены красными регрессионными тестами. Разрешение пользователя на коммит/публикацию PR получено после первоначального планирования; текущая команда разрешает довести этот PR до готовности, production execution остаётся отдельным шагом.

## Проверка исправлений convergence
T009: минимальный Google cancelled instance без iCalUID воспроизвёл дефект; все отмены переведены в существующий путь удаления по provider ID. T010: шесть новых отрицательных CalDAV сценариев сначала падали, теперь неполные REPORT/catalog отклоняются, полноценный пустой ответ и отсутствующие необязательные свойства проходят. Google/CalDAV: 37 passed; PostgreSQL reliability/provider runtime: 40 passed, включая отмены и сохранение кеша при ошибке. Повторный browser: PASS. Итоговый exact-SHA gate фиксируется в PR #6692.
