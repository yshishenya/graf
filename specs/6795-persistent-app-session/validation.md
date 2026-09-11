# Validation — F6795

## Planning gates

2026-09-11: specify → clarify (user: Mac; 30 дней без активности) → plan → security checklist → tasks → analyze → taskstoissues выполнены. Independent reviewer auth_investigation: 6/6 security requirements PASS после исправления 304 и уточнения браузерных гонок. Analyze: CRITICAL 0, HIGH 0, MEDIUM 0; 7 FR и 3 SC покрыты 6 задачами, orphan 0. GitHub canon: PASS, 295 issues checked; владельцы T001–T006: #6931–#6936. Implementation/установленное приложение/CI/release ещё не проверены.

## Diagnosis

Рабочий API read-only get_settings().auth_session_ttl_seconds = 86400. Текущий исходный SHA ad71f2ce4db68d846d7c333213961c5f5f7d5e89: issue_auth_session выдаёт фиксированный срок, record_session_activity не продлевает его; cookie имеет тот же срок. Mac использует постоянное WebKit хранилище и отдельную native копию. Логи содержат missing_auth_context/auth_session_invalid, но отдельные прошлые эпизоды не имеют однозначного подтверждения expiry. Явный TWOBRAIN_AUTH_SESSION_TTL_SECONDS в окружении рабочего API отсутствует: применён default. Production/Dev не изменены.

## Implementation validation

- Исходная регрессия до исправления: 5 failed / 5 passed — default сутки, отсутствующее продление и отсутствие передачи срока.
- Итоговый совместный серверный прогон: 172 passed (renewal, session clients, config, auth contracts, stale session/device и настоящая конкурентность revoke/activity). После этого добавлен тест отказа commit именно на стадии продления и проверка фактической роли БД.
- Окончательный дополнительный прогон: 18 passed — 17 renewal cases и exact-app-role PostgreSQL с forced RLS. Включены 304, обе logout-ветки, граница 30 дней, истёкший/отозванный/blocked вход, поздний scope/device отказ, отсутствие неподтверждённого продления после ошибки commit, custom TTL, priority route cookie и cross-tenant isolation.
- Swift: 62 passed (7 новых DesktopCabinetSessionBridgeTests, 49 DesktopUploadClientTests, 6 DesktopUserTimeContextTests). Реальные изолированные WK/Foundation stores; 2xx/304, old generation, завершённый logout/account change, expiry-only notification, Dev loopback, origin и сохранность атрибутов cookie.
- Ruff целевых Python файлов: PASS; git diff --check: PASS; changelog-fragments: PASS.
- Spec Kit governance: PASS с изолированным specify-cli 1.0.1 из точного ref 9118ed15a0ba65053469a94c560ea5d233f75884. Глобальный specify 1.0.4 отличается от lock; его не меняли. Первые вызовы с глобальным CLI и uv ephemeral wrapper не удовлетворяли frozen provenance; отдельная локальная venv с настоящей direct_url.json прошла полную проверку без обхода.

## Review and convergence

Independent auth_investigation review нашёл позднюю проверку device/scope после преждевременного commit продления. Исправлено переносом условного UPDATE в middleware после окончательного 2xx/304; новый test_rejected_device_context_does_not_extend_otherwise_valid_session проверяет неизменность БД. Redirect не продлевает сессию до следующей успешной страницы. Ошибка commit продления сохраняет успешный результат операции, но не публикует новый срок. Проверено отдельной регрессией с реальным rollback PostgreSQL.

Root final code review: проверены все вызовы record_session_activity/requestExecutor, cookie области и значение, порядок revoke/activity locks, committed deadline и false auth-change. Ponytail-review: новых зависимостей, refresh endpoints, таблиц и миграций нет; отдельный response middleware нужен для окончательного результата авторизации и обработки response cookie. Необязательных слоёв не добавлено.

Converge: FR-001–FR-006 покрыты кодом и локальными проверками; локальная часть FR-007/SC-001–SC-003 подтверждена. Новых обязательных задач сверх уже открытой T006 не выявлено. Полная feature acceptance НЕ завершена: T006 ждёт governance-fast на точном PR SHA и установленного GRAF Dev через harness. GitHub issues остаются открыты до соответствующего PR/evidence closeout; release-full/production не выполнялись.

## Limits

Нативная защита проверяет завершённый logout/смену аккаунта и поколение при применении. WebKit не предоставляет атомарную условную запись относительно одновременных сетевых Set-Cookie; абсолютная атомарность с такими ответами не доказана. Отозванная сессия в любом случае не восстанавливает серверный доступ. Ручное прохождение установленного приложения, сна/перезапуска и выпуск не подменяются Swift tests. До этапа установленной приёмки Production и GRAF Dev не менялись; актуальный результат приведён ниже.

## PR validation checkpoint

Коммит реализации: `5b686f0b48f25bebb3fa4445b92fe383f227a485`, PR https://github.com/yshishenya/graf/pull/6941. Независимый final_review: PASS, открытых замечаний нет; это проверка исходного кода без повторного запуска тестов.

- governance-fast: PASS https://github.com/yshishenya/graf/actions/runs/34608004023 — точный SHA реализации; получен штатный metadata-only receipt.
- pr-metadata: PASS https://github.com/yshishenya/graf/actions/runs/34608003376.
- `dev-harness.sh build --sha 5b686f0b48f25bebb3fa4445b92fe383f227a485 --feature-id 6795 --live`: PASS, кандидат ready; promote не выполнялся, поскольку общий стенд занят F6793.
- Read-only Dev подтверждает прежнее поведение: issued_at 2026-09-10T21:55:46Z, last_seen_at 2026-09-11T14:11:59Z, expires_at 2026-09-11T21:55:46Z. Постоянная активность не сдвигала суточный срок. Идентификаторы и токены не сохранялись.

После переключения соседней задачи исходный parent кандидата устарел. Для нового чистого SHA с этим отчётом выполняется штатная новая сборка: существующий manifest не редактируется и не удаляется. Приёмка T006 остаётся открытой.

## Installed GRAF Dev checkpoint — partial

На коммите `7dbcce5f56faaeac8efbc604fddc780e045594f2` изменены только этот отчёт и связи задач. Исходный код идентичен независимо проверенному коммиту реализации.

- governance-fast: PASS https://github.com/yshishenya/graf/actions/runs/34609835767.
- pr-metadata: PASS https://github.com/yshishenya/graf/actions/runs/34609835702.
- Штатный build → promote → smoke: PASS, активирован `dev-7dbcce5f56fa`, schema `0092_recording_origin_cancel`, все 13 live checks. Сохранены единственный `/Applications/GRAF Dev.app`, bundle ID и штатная подпись.
- Переход прежней сессии без нового входа подтверждён metadata-only наблюдением: issued_at `2026-09-10T21:55:46Z`; прежний expires_at `2026-09-11T21:55:46Z`; после установки last_seen_at `2026-09-11T15:16:23Z`, expires_at `2026-10-11T15:16:23Z`.
- Без дальнейшего управления страницей зафиксировано последующее продление: last_seen_at `2026-09-11T15:26:29Z`, expires_at `2026-10-11T15:26:29Z`. Постоянная Foundation cookie имеет совпадающий секундный срок. Значение cookie и идентификаторы не сохранялись. Это не прямое чтение отдельного WebKit-хранилища.
- Повторный promote того же manifest вернул `idempotent: true` без второго перезапуска. Он не считается проверкой повторного запуска приложения.

После установки канал CUA исчез из callable tools; доступный node_repl имеет `typeof cua === "undefined"`. Другой способ управления интерфейсом ограничен прямым разрешением пользователя по правилам CUA. Запрошено использование AppleScript либо ручная проверка пользователем. Обход через другую копию приложения, TCC или подмену тестовых результатов не выполнялся.

Независимый final_review подтвердил границу: T006 и FR-007 остаются частично выполненными; ещё нужны повторный запуск/открытие встречи и выход с ожидающим запросом по quickstart. Автоматические поздние ответы/отзыв PASS, но не заменяют этот установленный сценарий. До завершения ручной приёмки PR остаётся draft, merge/release/deploy не выполняются.
