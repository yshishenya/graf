# Tasks: Предсказуемая скорость страниц кабинета

**Фича**: 270-cabinet-query-efficiency
**Вход**: [spec.md](spec.md), [plan.md](plan.md), [research.md](research.md), [quickstart.md](quickstart.md)
**Umbrella issue**: #7127

**Правила**: `[P]` — задача может выполняться параллельно с другими отмеченными;
`[US1]`/`[US2]`/`[US3]` — к какой пользовательской истории относится задача.

## Фаза 1. Подготовка

- [x] T001 [US1] Добавить в `.specify/feature.json` пути, которые фича имеет право менять: `apps/server/src/twobrain_rec_server/cabinet`, `apps/server/tests/integration`, `changes/unreleased`, и обновить `source_sha` после коммита артефактов. (Issue #7130)

## Фаза 2. Основа — пакетная предвыборка данных страницы (US1, P1)

Цель: число обращений к базе для страницы списка перестаёт зависеть от числа встреч.
Каждая задача добавляет пакетный вариант рядом с существующим одиночным помощником в
`apps/server/src/twobrain_rec_server/cabinet/queries.py` и не удаляет одиночный, пока
все потребители не переведены.

- [x] T002 [US1] Добавить пакетное чтение последней ревизии медиа для набора встреч (`DISTINCT ON (meeting_id) ... ORDER BY meeting_id, revision DESC`) в `apps/server/src/twobrain_rec_server/cabinet/queries.py`. Требования: FR-001. (Issue #7131)
- [x] T003 [P] [US1] Добавить пакетное чтение последнего workflow для набора пар (встреча, ревизия) в `apps/server/src/twobrain_rec_server/cabinet/queries.py`. Требования: FR-001. (Issue #7132)
- [x] T004 [P] [US1] Добавить пакетное чтение последнего результата обработки для набора пар (встреча, ревизия) в `apps/server/src/twobrain_rec_server/cabinet/queries.py`. Требования: FR-001. (Issue #7133)
- [x] T005 [P] [US1] Добавить пакетное чтение текущего набора итогов и прогресса итогов для набора результатов в `apps/server/src/twobrain_rec_server/cabinet/queries.py`. Требования: FR-001. (Issue #7134)
- [x] T006 [P] [US1] Добавить пакетное чтение состояний артефактов и состояния воспроизведения для набора встреч в `apps/server/src/twobrain_rec_server/cabinet/queries.py`. Требования: FR-001. (Issue #7135)
- [x] T007 [P] [US1] Добавить пакетное чтение прогресса загрузки для набора встреч в `apps/server/src/twobrain_rec_server/cabinet/queries.py`. Требования: FR-001. (Issue #7136)
- [x] T008 [P] [US1] Добавить пакетное чтение связи с календарём и предыдущей повторяющейся встречи для набора встреч в `apps/server/src/twobrain_rec_server/cabinet/queries.py`. Требования: FR-001. (Issue #7137)
- [x] T009 [US1] Переписать цикл `for meeting in meetings:` в `list_cabinet_meetings` (`apps/server/src/twobrain_rec_server/cabinet/queries.py:462`) на чтение из пакетного контекста без обращений к базе внутри цикла, сохранив порядок проверок: доступ → ревизия → поиск → рабочий процесс → результат → итоги → артефакты → воспроизведение → загрузка → календарь. Требования: FR-001, FR-005, FR-007, FR-008. (Issue #7138)
- [x] T010 [US1] Убедиться, что одиночные помощники, оставшиеся без потребителей, удалены, а используемые другими путями чтения сохранены; прогнать `ruff check` по `apps/server`. Требования: FR-001. (Issue #7139)

## Фаза 3. Доступ и общие потребители (US2, P2)

- [x] T011 [US2] Читать членство зрителя один раз на запрос в `decide_meeting_access` (`apps/server/src/twobrain_rec_server/cabinet/access.py:474`), сохранив `populate_existing=True` и ту же семантику роли и привилегий. Требования: FR-003. (Issue #7140)
- [x] T012 [US2] Добавить пакетное чтение активных грантов для набора встреч и использовать его при формировании решений для страницы списка в `apps/server/src/twobrain_rec_server/cabinet/access.py`. Требования: FR-003, FR-009. (Issue #7141)
- [x] T013 [US2] Проверить и при необходимости подключить исправленный путь к производным экранам: встроенный список (`apps/server/src/twobrain_rec_server/cabinet/web_routes/desktop.py`), раздел «поделились со мной» и деталь встречи; зафиксировать замеры до и после. Требования: FR-006. (Issue #7142)

## Фаза 4. Предохранитель (US3, P3)

- [x] T014 [US3] Создать `apps/server/tests/integration/test_cabinet_meeting_list_query_budget.py`: считать обращения к базе слушателем `before_cursor_execute` на `client.app_state["engine"].sync_engine`, создавать встречи напрямую через `client.app_state["sessionmaker"]`, сравнивать число обращений при 5 и при 50 встречах и падать при росте более 25 процентов с указанием экрана. Требования: FR-010, SC-001, SC-006. (Issue #7143)
- [x] T015 [US3] Доказать, что предохранитель работает: временно внести обращение к базе внутри цикла, убедиться в падении с понятным сообщением, убрать нарушение. Требования: FR-010, SC-006. (Issue #7144)

## Фаза 5. Проверка результата

- [x] T016 [US1] Замерить число обращений и время для `/meetings` при 5, 10, 20 и 50 встречах и для `/meetings/{id}`; сравнить с эталоном из `research.md`; результат внести в отчёт. Требования: SC-001, SC-002, SC-003. (Issue #7145)
- [x] T017 [US1] Прогнать полный серверный прогон `GRAF_TEST_WORKERS=4 GRAF_PERFORMANCE_GATE=required GRAF_TEST_REPORT_DIR=/tmp/graf-after bash apps/server/scripts/run_local_postgres_tests.sh --full -q` и сравнить с эталоном `/tmp/graf-baseline/parallel.jsonl`. Требования: SC-005. (Issue #7146)
- [x] T018 [US2] Прогнать фокусированные проверки доступа, приватности, удаления и выгрузки по `quickstart.md`, сценарий 4, без правки ожиданий. Требования: FR-003, FR-004, FR-011, FR-012, SC-004. (Issue #7147)
- [x] T019 [US1] Создать `changes/unreleased/F270.yaml` по формату `changes/unreleased/README.md`. Требования: FR-011. (Issue #7148)

## Фаза 6. Закрытие

- [X] T020 [US1] Прогнать `$speckit-analyze` и убедиться, что CRITICAL и HIGH равны нулю. Требования: SC-005. (Issue #7149)
- [X] T021 [US1] Получить обязательные GitHub-проверки `governance-fast`, `macos-pr`, `pr-metadata` на точном SHA пул-реквеста. Требования: SC-004. (Issue #7150)
- [X] T022 [US1] Обновить `docs/current-product-status.md`, если поведение продукта описано там, и `specs/270-cabinet-query-efficiency/tasks.md` по факту выполнения. Требования: SC-005. (Issue #7151)

## Зависимости

- T002–T008 независимы между собой и могут выполняться параллельно.
- T009 зависит от T002–T008.
- T010 зависит от T009.
- T011 и T012 зависят от T009.
- T013 зависит от T012.
- T014 не зависит от реализации и может быть написана первой.
- T015 зависит от T014.
- T016–T019 зависят от T009 и T012.
- T020–T022 зависят от T016–T019.
