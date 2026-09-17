# Tasks: Единые даты и время пользователя

## Phase 1: Setup and foundational

- [X] T001 Добавить регрессионные проверки и общий контекст пользовательского времени в `apps/server/tests/unit/test_user_time.py`, `apps/server/src/twobrain_rec_server/cabinet/user_time.py`, `apps/server/src/twobrain_rec_server/main.py`, `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/user-time.js`; проверить malformed IANA, UTC fallback, DST и отсутствие повторного POST. [FR-003,004,007,009,010,011]

## Phase 2: US1 — список, сортировка, поиск

Независимая проверка: смешанные local/server/manual uploads при всех доступных сортировках, поиске и фильтрах; стабильность после обновления.

- [X] T002 [US1] Согласовать эффективную дату, сортировку, SQL-поиск и mixed rows в `apps/server/src/twobrain_rec_server/cabinet/{queries.py,view_models.py,rendering.py,static/cabinet/cabinet.js}`; добавить проверки в `apps/server/tests/integration/test_cabinet_meeting_list.py` и существующие unit/UI tests. [FR-001,002,004,005,006,010]

## Phase 3: US2 — все пользовательские поверхности

Независимая проверка: один момент в list/detail/shared/calendar/account/billing/admin, включая HTMX.

- [X] T003 [US2] Подключить общий formatter в `apps/server/src/twobrain_rec_server/cabinet/{templates.py,review_policy_rendering.py,web_routes/billing.py,web_routes/referrals.py,web_routes/fair_use.py,web_routes/settings.py,templates/cabinet/}` и `apps/server/src/twobrain_rec_server/admin/{templates.py,templates/,audit.py,files.py}`, HTML-проекцию shared/invitation в `cabinet/access.py`, `cabinet/web_routes/browser.py`, `api/cabinet.py`; добавить focused rendering checks и синтетический браузерный сценарий. [FR-003,004,006,007,009,010]

## Phase 4: US3 — нативный список и сроки

Независимая проверка: восстановленная запись сортируется по началу, дата/год/пояс читаемы, duration неизменен.

- [X] T004 [US3] Исправить `apps/macos/RecApp/Sources/Cabinet/DesktopMeetingShellView.swift`, `apps/macos/RecApp/Sources/Calendar/CalendarTray.swift`, `apps/macos/RecApp/Sources/Upload/DesktopUploadCustodyProjection.swift`; переиспользовать native formatter/helper и добавить focused Swift regressions в `apps/macos/Shared/Tests/`. [FR-004,006,008,009,010]

## Phase 5: Validation and convergence

- [X] T005 Выполнить focused Python/JS/Swift и синтетические браузерные сценарии из `specs/252-consistent-user-time/quickstart.md`, review/converge, `git diff --check`, обновить evidence и `changes/unreleased/F252.yaml`; зафиксировать high-risk lane и отдельно незапущенные PR/release gates. [SC-001–004, FR-010]

## Dependencies and implementation strategy
T001 → T002/T003/T004 → T005. Тесты добавляются до соответствующего исправления. US1 — первый полезный результат, но закрытие требует всех историй. Отдельный специалист может независимо работать над Swift после T001; серверные rendering/JS файлы имеют одного владельца, пересекающиеся правки согласуются.

## Tracker
Umbrella: https://github.com/yshishenya/graf/issues/6663. Child sync выполняется до implementation.

- T001: https://github.com/yshishenya/graf/issues/6664
- T002: https://github.com/yshishenya/graf/issues/6665
- T003: https://github.com/yshishenya/graf/issues/6666
- T004: https://github.com/yshishenya/graf/issues/6667
- T005: https://github.com/yshishenya/graf/issues/6668

## Phase 6: US4 — одно поле часового пояса (уточнение пользователя)

- [X] T006 [US4] Проверить и расширить хранение настройки и request context в `apps/server/src/twobrain_rec_server/db/models/identity.py`, `db/migrations/versions/0086_user_timezone.py`, `auth/dependencies.py`, `cabinet/user_time.py`, `cabinet/web_routes/settings.py`; добавить проверки миграции, CSRF, атомарности и приоритета аккаунта. [FR-003,011,013,014]
- [X] T007 [US4] Добавить русский каталог и одно поле с поиском/предпросмотром в `apps/server/src/twobrain_rec_server/cabinet/{templates.py,templates/,static/cabinet/user-time.js,static/cabinet/cabinet.js}`, обновить `view_models.py`, `queries.py`, зависимости `apps/server/pyproject.toml`, `uv.lock`, `constraints.txt`; проверить Save/Cancel/no-JS/ошибки/DST. [FR-012,013]
- [X] T008 [US4] Применять настройку аккаунта в `apps/macos/Shared/Sources/UserTime.swift`, `apps/macos/RecApp/Sources/Cabinet/`, `Sources/Calendar/CalendarTray.swift`, `Sources/Upload/DesktopUploadCustodyProjection.swift`, `App/TwoBrainRecApp.swift`; проверить доверенную страницу, изоляцию пользователей, auth reset, offline fallback и обновление дат. [FR-015]
- [X] T009 Повторить focused tests и диагностический fast для high-risk-product lane, синтетический браузерный сценарий, review/converge и обновить `specs/252-consistent-user-time/quickstart.md`, `changes/unreleased/F252.yaml`. [FR-010,012–015, SC-001–004]

T006 → T007; T008 независим от серверных файлов после согласования metadata контракта; T006/T007/T008 → T009.

- T006: https://github.com/yshishenya/graf/issues/6702

- T007: https://github.com/yshishenya/graf/issues/6703

- T008: https://github.com/yshishenya/graf/issues/6704

- T009: https://github.com/yshishenya/graf/issues/6705
