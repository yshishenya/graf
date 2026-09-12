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

## Installed acceptance completed — 2026-09-12

Проверка выполнена через CUA в единственном `/Applications/GRAF Dev.app`, bundle ID `pro.2brain.graf.dev`, на ранее собранном и подписанном `dev-7dbcce5f56fa` / `7dbcce5f56faaeac8efbc604fddc780e045594f2`. Продуктовый код совпадает с PR SHA `1309d8b6b4904a351196d10ca64daf74163b09e6`: между ними изменён только этот отчёт; относительно коммита реализации изменены только отчёт и связи задач.

Повторная сборка HEAD остановилась на внешнем `pull access denied` для датированных образов MinIO. Установленный кандидат восстановлен штатно: чистый checkout активного SHA → promote неизменного активного manifest → rollback на сохранённый кандидат с чистым target checkout. SHA, digest образов, подпись, схема и проверки восстановления сохранены; manifest, runtime definition, TCC и установленный bundle вручную не изменялись. Это приёмка ранее собранного идентичного кода, а не заявление об успешной новой сборке HEAD.

- Переход старого входа: сессия выдана `2026-09-10T21:55:46Z`, пережила первоначальную суточную границу и отсутствие работающего Dev API. После восстановления last_seen_at и expires_at составили `2026-09-12T10:21:35Z` / `2026-10-12T10:21:35Z`; постоянная Foundation cookie имеет совпадающий секундный срок. Ввод данных входа для этого не потребовался.
- Настоящий повторный запуск: Cmd+Q завершил установленный процесс (отсутствие процесса проверено); запуск того же bundle открыл «Мои встречи» без входа. Существующая тестовая встреча открылась. Функционально проверено постоянное WebKit-хранилище; прямое чтение его числового expiry не выполнялось.
- Выход с ожидающим нативным запросом: короткая транзакция Dev PostgreSQL удерживала ACCESS EXCLUSIVE только на `meeting_target_registry_versions`, с lock_timeout 2s и idle timeout 45s. После запуска приложения подтверждён один ожидающий AccessShareLock. Штатный выход завершился, пока запрос ещё ожидал: БД показала revoked и прежний expires_at, число ожидающих оставалось 1. Затем выполнен ROLLBACK и закрыто удерживающее соединение.
- Поздний штатный `GET /api/v1/desktop/meeting-detection/target-registry` завершился HTTP 304 за 37779.36 ms, до клиентского тайм-аута. Следующий запрос получил 401. Foundation cookie отсутствовала; интерфейс оставался на входе. Нажатие «Домой» повторно открыло вход с missing_auth_context. Отозванная сессия не получила нового срока.
- Повторный `dev-harness.sh smoke --json --live`: PASS, все 13 проверок, source SHA `7dbcce5f56faaeac8efbc604fddc780e045594f2`.
- После проверки обычным Dev email-code flow восстановлен тестовый вход, открыт список встреч. Записи не создавались и не удалялись; настройки записи не менялись.

Границы доказательства: задержанный установленный ответ после отзыва не получает заголовок продления, поэтому этот сценарий не заменяет Swift-тест позднего ответа с уже подтверждённым сроком. Прямое чтение срока отдельной установленной WebKit cookie не заявляется: подтверждение двух хранилищ опирается на реальные изолированные WK/Foundation tests, совпадение Foundation/БД и открытие встроенного кабинета после исходной суточной границы и настоящего перезапуска. Сон компьютера отдельно не воспроизводился.

T006: установленная приёмка завершена; governance-fast и pr-metadata на SHA `1309d8b6b4904a351196d10ca64daf74163b09e6` — PASS (runs 34616557824 / 34616557825). После финального коммита отчёта обязательны успешные проверки именно нового SHA, ссылки фиксируются в PR. Issues остаются открыты до принятия/выпуска и соответствующего closeout. Merge, release и production deploy не выполнялись.

Independent final_review: PASS по достаточности установленной приёмки и FR-007; граница прямого наблюдения WebKit принята явно. Итоговый converge: 7 FR, 3 SC, 6 acceptance scenarios и 6 задач сопоставлены с кодом и доказательствами; новых работ по реализации не выявлено, открытых замечаний по коду нет. Завершение T006 в этом коммите требует успешного governance-fast именно на его SHA до перевода PR в ready.

## Повторное ревью после ready — 2026-09-12

После успешных checks SHA `ba054207ee929b61bccdec1e54a6758302eadb2f` автоматическое ревью добавило два замечания; статус GitHub стал BLOCKED из-за неразрешённых обсуждений. Предыдущее ready-состояние было промежуточным, не окончательной готовностью к Merge.

- P1 (discussion_r3995966637): независимый final_review подтвердил пересечение `allCookies → setCookie` с сетевой сменой значения cookie. Guard после записи не восстанавливает новый токен. В convergence добавлена T007 / #6955; до исправления и повторной проверки готовность не заявляется.
- P2 (discussion_r3995966636): независимый auth_investigation подтвердил соответствие текущему контракту. Допущенный запрос может завершиться после срока, но окончательное продление не возобновляет истёкшую сессию. Изменение времени проверки потребовало бы иной серверной и нативной политики. Добавлен управляемый тест для native/cookie; `bash apps/server/scripts/run_local_postgres_tests.sh tests/unit/test_auth_session_renewal.py -q`: 19 PASS, изолированный PostgreSQL удалён штатно. Серверная логика не менялась.

Analyze T007: исправление относится к существующим FR-004/FR-007, SC-003, новых продуктовых решений нет; security checklist 6/6 сохраняется. План дополнен порядком барьера навигации и обработкой завершения/отмены. Canon issue sync: PASS. Независимое ревью кода, новая validation и exact-SHA проверки T007 ещё предстоят.

### T007: исправление и локальная проверка

Нативное продление согласовано с отправкой переходов WebKit: начало перехода повышает поколение и запрещает новые записи, отправка ждёт уже начатую запись, окончание снимает запрет после свежего согласования cookie. Каждый координатор владеет отдельным запретом. Старые ответы до/во время перехода не применяются после его завершения. Устаревший снимок наблюдателя перечитывается.

Независимый final_review дополнительно выявил раннее снятие запрета старым `didFinish` на тот же URL и отсутствие фактической остановки WebKit при отмене. Исправлено: идентичность предыдущей навигации снимается перед отправкой новой формы/ссылки с сохранением history fence; явная отмена останавливает загрузку до согласования. Добавлены регрессии с настоящими WKNavigationAction, полученными из синтетического HTML, и управляемыми продолжениями; внешние запросы отменяются до отправки.

- Swift кабинет: 88 PASS, включая 13 session bridge tests, правила запросов, пространство, боковую панель, подтверждения и реальный reload. Лог `/tmp/graf-t007-cabinet-tests.log`.
- Swift upload/time context: 55 PASS; `.dev/review/swift-upload-context-final.log`.
- PostgreSQL renewal: 19 PASS, включая два новых случая окончательного истечения; `.dev/review/server-renewal.log`.
- Ruff, diff whitespace, changelog fragments: PASS. Frozen governance использует существующую `.dev/specify-validation`; глобальная версия specify отличается от lock и не считается корректной проверкой.
- Независимый final_review: PASS текущему Swift diff после исправлений; Ponytail-review не выявил лишних зависимостей или безопасно удаляемых элементов.

Это новые проверки исходного кода. Ранее установленный `7dbcce5f...` подтверждает исходную приёмку T006; новый барьер T007 на нём отсутствовал, поэтому тождество с новым продуктовым кодом больше не заявляется. Установка нового кандидата и финальный exact-SHA GitHub gate пока не выполнены. Merge/release/production не выполнялись.
