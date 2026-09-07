# Проверка реализации Feature 254

Это инструкция для полной реализации. Уже появились проверки `test_system_admin_{security,authority,operations,login,management,users,content}.py`; их фактические результаты перечислены в [implementation-evidence.md](implementation-evidence.md). Остальные тестовые файлы ниже ещё должны быть созданы задачами. Данные только синтетические, платежи — тестовый магазин, рассылка приглашений — локальный перехватчик почты.

## Предварительные условия

Актуальная ветка фичи, зависимости из lock-файлов, Docker и локальный PostgreSQL с реальными runtime ролями; Temporal/MinIO и тестовые adapters по существующим инструкциям `apps/server/README.md`. Отдельный console service с собственным секретом БД, только тестовые auth credentials. Секреты вводятся штатной конфигурацией и не печатаются. Профиль нагрузки и клиентский аппаратный профиль закреплены plan/research.

```sh
.specify/scripts/bash/check-prerequisites.sh --json --require-tasks --include-tasks
python3 scripts/check_spec_kit_governance.py
```

До тестов зафиксировать reviewer-owned checklist review. Скрипт bootstrap первого админа создаёт synthetic identity, второй приглашён обычным потоком; обычные owner/admin/member и две personal+одна corporate области не повышаются.

## Серверная проверка

Из корня репозитория после появления тестов:

```sh
apps/server/scripts/run_local_postgres_tests.sh --focused tests/integration/test_system_admin_security.py tests/integration/test_system_admin_content.py tests/integration/test_system_admin_recovery_deletion.py
apps/server/scripts/run_local_postgres_tests.sh --focused tests/integration/test_system_admin_billing.py tests/integration/test_system_admin_promotions.py tests/integration/test_system_admin_migration.py
apps/server/scripts/run_local_postgres_tests.sh --focused tests/integration/test_system_admin_diagnostics.py tests/integration/test_system_admin_metrics.py tests/integration/test_system_admin_audit_exports.py
```

Проверки делятся на группы, чтобы failure был понятен. Сценарии в [acceptance.md](acceptance.md) — обязательные expected outcomes; тесты не заменять на проверку наличия кнопок.

- Auth: чужая cookie, preauth, expired/revoked role, CSRF, TOTP replay, last-admin race, actual DB-role/GUC/SET ROLE, повторный bootstrap и pool reuse. Все запрещённые чтения не раскрывают поля.
- Контент: весь текст и один выбранный revision, Range revoke/delete, retained-view отдельно, no-speech без выдуманного аудио, безопасный renderer/CSV.
- Операции: retry той же команды возвращает тот же ID, role revoke до effect-start, Temporal start после commit, старый published результат сохранён, quota charged один раз, late result не воскрешает удалённое.
- Деньги: новый code `research_plus` с month/year; purchase→duplicate webhook→access→gift→renewal→expiry→promo, old pinned price после новой публикации, sent/unknown блокирует несовместимый gift. Gift без payment/receipt/revenue.
- Promos: два клиента спорят за последний code/budget, only one reserve; lost response, late paid после pause, refund не возрождает код, merged identities, legacy counter reconciliation.
- Telemetry: foreign user links/oversized/unknown schema rejected; ordinary events не подтверждают paid/deleted. Snapshot/history capped, различаются event/received times, late correction и missing coverage.

Обязательно прогнать затронутые существующие suites, перечисленные research: billing webhooks/renewal/referral/storage, user reprocess/egress/deletion, RLS/production boundary. Точный набор записать после изменения callers; не утверждать, что только новые тесты доказывают отсутствие регрессии.

## Клиент и браузер

```sh
swift test --package-path apps/macos --filter SystemAdminDiagnosticsTests
```

Проверить фактический test target в Package.swift при добавлении тестов. Три 60-минутных сравнения telemetry on/off, M1/8GiB: <=20MiB дополнительной памяти, <=1 percentage point CPU, ни одного синхронного ожидания сети в capture path. 60min недоступности collector, переполнение queue, restart, смена аккаунта, old support v2, отказ от product analytics и истечение extended mode.

Browser suite T036 запускается существующим pytest/e2e runner проекта с настроенным локальным base URL, не против production. Ручной проход: keyboard-only, 200%, 1024px и узкий экран; focus/dialog, конфликт версии с сохранением ввода, stale/partial/error, скрытие контента <=15s при revoke, no-store/back cache. Десять synthetic жалоб: найти пользователя/объект/причину либо пробел данных <=2min каждая.

## Нагрузка и отключение

Fixture T038 создаёт 10k users/100k meetings/1M events. На стенде из plan выполнить 20 concurrent sessions, warm-up 10min + measurement 30min. p95 list/search<=2s, detail<=3s без media. Параллельно baseline capture/upload/processing: нет отказов/исчерпания соединений из-за отчётов. Проверить timeout/pool/batch limits, refresh processing<=15s, aggregates<=5min с маркировкой lag. Команды выполнения и безопасные aggregate results добавить в evidence после реализации теста, не подставлять вымышленные измерения.

Migration rehearsal: additive upgrade, resumable backfill, repeat bootstrap, exact equality денег/согласий/IDs, no auto superadmin; disable console and admissions, pending obligations продолжаются; несовместимый billing binary rollback запрещён. Backup restore проверяется отдельно со сверкой внешних результатов.

## Закрытие

После всех AC: `$speckit-converge`, профильные проверки и `infra/scripts/ci-local.sh --fast`; required GitHub `governance-fast` на точном SHA. Применимые full/release проверки — по `docs/agent-guidance/release-and-validation.md`. Для production сначала `infra/scripts/cd-remote.sh --dry-run`; исполнение и commit требуют отдельного разрешения. Публичный macOS выпуск проходит все notarization/Sparkle gates.

В evidence: SHA, среда, команда, дата, passed/failed/skipped и причина, synthetic IDs, агрегаты. Без аудио, расшифровок, реальных адресов/токенов/secret paths. Не отмечать future test как passed на основании анализа документа.

## Локальная браузерная консоль

Использовать только новую одноразовую PostgreSQL на loopback с именем `twobrain_rec_test_*`. Путь к файлу URL передаётся без печати содержимого. Из `apps/server`:

```sh
PYTHONPATH=src:. .venv/bin/python -m tests.fixtures.system_admin_ui_harness --database-url-file /path/to/disposable-db-url
```

Адрес `https://localhost:8943/system-admin/login`, самоподписанный тестовый TLS. Учётная запись `browser@example.invalid`, пароль `Synthetic browser password 254`, синтетический TOTP seed — base32 от ASCII `12345678901234567890`. Эти константы относятся только к тестовому процессу. Перехватчик почты ничего не отправляет. Обычные продуктовые маршруты в нём не публикуются. После проверки остановить процесс и удалить только его одноразовый контейнер.

## Серверная выдача аудио

Необязательный `SYSTEM_ADMIN_STORAGE_CONFIG_FILE` содержит JSON с ровно пятью полями: `endpoint`, `access_key`, `secret_key`, `bucket` (непустые строки) и `secure` (boolean). Файл монтируется только в процесс консоли, не коммитится и не печатается. Отсутствующая конфигурация закрывает выдачу аудио, сохраняя остальные страницы.

Использовать отдельную учётную запись MinIO с `s3:GetObject` на настроенный bucket: шаблон `infra/minio/system-admin-media-readonly.json`. Если bucket отличается, оператор меняет только ресурс политики. Прав на запись, удаление, listing и управление MinIO нет. Продуктовый writer credential для консоли не используется.

POST media-ticket выдаёт токен активации на 60 секунд, привязанный к административной сессии/праву/обращению/версии и точному источнику. Первый GET потребляет активацию и устанавливает Secure HttpOnly host-only cookie с отдельным именем для этого просмотра. Последующие Range-запросы требуют и этой cookie, и исходной действующей административной сессии; предел просмотра — 15 минут, каждый запрос и блок потока проверяют полномочия/удаление. Browser URL сам по себе не является доступом. Одновременно процесс выдаёт до четырёх потоков; превышение — 429 с Retry-After. Вкладка очищает плеер при скрытии и проверяет право каждые 10 секунд. Отзыв уже скачанных байтов невозможен.

Активация фиксирует `playback_stream_prepared`/`download_stream_prepared` в существующем журнале выдачи; id совпадает с подтверждённым system audit event. Product actor остаётся пустым, системный actor сохраняется в аудите. Это подготовленная выдача, не утверждение о полном скачивании.

### Перенос точных условий старых подписок

После миграции 0096, сначала на изолированной восстановленной БД, запустить из `apps/server`:

```sh
PYTHONPATH=src .venv/bin/python scripts/backfill_billing_catalog.py --database-url-file "$F254_MAINTENANCE_URL_FILE"
PYTHONPATH=src .venv/bin/python scripts/backfill_billing_catalog.py --database-url-file "$F254_MAINTENANCE_URL_FILE" --execute --batch-size 100 --max-batches 100
```

Переменная указывает на операторский файл секрета с DSN роли `twobrain_rec_maintenance`; сам DSN не передаётся аргументом. Без `--execute` выводятся только счётчики. Каждый пакет коммитится отдельно; повтор продолжает незавершённые/изменённые подписки. `lag=0` означает отсутствие непроверенных текущих версий подписки на момент запроса; `unresolved>0` означает сохранённые истории, требующие разбора. Нулевой lag до остановки старых billing writers не заменяет обязательный повтор после барьера из contracts/migration.md. Новые catalog writers и продажи не включать до подключения всех consumers и прохождения полного жизненного цикла. Команда не меняет платежи, согласия и paid_through, не отправляет запросов провайдеру.

Перед выпуском дополнительно закрыть T018 для уже существующих scheduled renewal operations без schedule_version: текущий исполнитель направляет их на разбор и не отправляет платёж. Расширение денежных колонок до bigint проверить на восстановленной базе с замером блокировок; этот локальный прогон не доказывает миграционное окно production.
