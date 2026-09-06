# Реализация: первый участок системного доступа

Дата: 2026-09-06. Ветка: `codex/254-system-admin-console`. Уровень риска: `high-risk-product`. Legacy impact: `untouched`.

## Коммит и готовность к началу

Пользователь разрешил коммит подготовленных документов и начало реализации. Документы сохранены коммитом `e8286572b` (`[F254] Подготовить спецификацию и план системной консоли`), исходная база — `a389657e607ef8389fcf947b26b158cee6928884`. Перед началом выполнен fetch: новых коммитов `origin/master` относительно базы ветки не было. Проверены все контрольные списки: requirements 5/5; security 6/6; billing 6/6; diagnostics 5/5; UX 5/5; infra 5/5. Исполнитель их состояния не менял. Все 39 задач имели открытые GitHub issues; повторно прочитана #6712.

T001 выполнена в части предусмотренной подготовительной проверки: актуальная база, независимое ревью требований, матрица FR/SC/AC/tasks и владельцы задач. Runtime AC не объявляются пройденными. Issue #6712 остаётся открытой до PR, проверки точного SHA и предусмотренного tracker-policy закрытия.

Новые изменения реализации находятся в рабочем дереве после этого коммита. Push, PR, выпуск, развёртывание и изменения реальных данных не выполнялись.

## Что реализовано в T002

- Добавочная миграция `0086_system_admin_boundary` после фактического единственного head `0085_merge_summary_mediascribe`. Исторические миграции не менялись. Alembic учитывает отдельные схемы при сравнении metadata.
- Схема `system_control`: `principals`, `role_assignments`, `sessions`. UUID системной личности не является UUID пользовательской сессии. Не создаются администраторы из существующих владельцев пространств.
- PostgreSQL-роли `twobrain_rec_system` и `twobrain_rec_system_authority` создаются без входа, повышенных атрибутов и членств. Включение login требует отдельного необязательного секрета bootstrap; обычное развёртывание его не требует. У app/maintenance/media нет USAGE новой схемы.
- Проверяющая SQL-функция принадлежит ограниченной NOLOGIN роли, с фиксированным `search_path`, без PUBLIC EXECUTE. Ей доступны только id/status/auth_version личности и данные сессии/назначения; password_hash ей не выдаётся.
- Для чтения разрешённого набора столбцов `meetings` проверяются настоящий `session_user`, ID личности/сессии, хеш сессионного токена, актуальные статус/auth_version, срок назначения, абсолютный и неактивный срок сессии. Проверка не опирается только на присланную строку роли или GUC.
- Restrictive RLS обязательна поверх старых разрешающих PUBLIC policies. Даже искусственно добавленная permissive allow-all policy не даёт неавторизованное чтение. INSERT/UPDATE/DELETE системной роли отдельно запрещены до реализации команд.
- Выданы только столбцы метаданных встречи. `SELECT *`, title и любые изменения недоступны; текст, аудио, секреты и финансы не подключены.
- Отдельный engine: PostgreSQL system login обязателен, пул 4, overflow 0, ожидание 5 s, statement timeout 2 s. Новый контекст отделён от tenant context; нельзя заменить личность в одной сессии. После commit/rollback восстанавливается прежний проверяемый контекст; новая session не наследует полномочия из pool.
- Повторный bootstrap проверяет атрибуты/членства, точный набор столбцов, наличие обязательной RLS и отсутствие широких табличных прав. Он не выдаёт общий SELECT/DML системной роли.
- Откат пустой схемы проверен. При наличии системной личности миграция отказывается удалять данные атрибуции; оператору потребуется отдельная согласованная миграция.

На момент первого участка T002 оставалась открытой: permission_grants/case context ещё не были реализованы. Текущее состояние после продолжения приведено в последнем разделе; предметные проекции остальных таблиц и права команд остаются в последующих задачах. Переход к публичному входу или выдаче контента до соответствующих аудита/авторизации не выполнялся.

## Совместимость тестового стенда

Старый playback UI harness использовал `Base.metadata.create_all`, который не создаёт отдельные схемы и SQL-политики. Он переведён на существующий `prepare_schema`. При реальном запуске дополнительно выявлены нарушения порядка вставки FK и использование asyncpg pool между разными event loops. Подготовка родительских строк отделена flush; применён существующий в проекте `NullPool` для тестового процесса. Новый тест создаёт этот стенд целиком на чистой БД и проверяет встречи и пустую системную область. Сетевые провайдеры и реальная запись не используются.

## Выполненные проверки

Среда: macOS, Python 3.14 из `uv`, PostgreSQL 17 в одноразовом Docker-контейнере на loopback. Использованы реальные ограниченные роли, миграции и транзакции, синтетические личности/встречи; секреты тестовые. Каждый контейнер удалён штатным runner.

| Проверка | Результат |
|---|---|
| Новый тест до реализации | Ожидаемая ошибка: отсутствует `twobrain_rec_system`; это зафиксированная исходная неготовность |
| `test_system_admin_security.py` + `test_rls_maintenance_context.py` + `test_rls_production_boundary.py` | 38 passed на первом участке |
| `test_rls_postgres_policies.py` + `test_playback_normalization_postgres.py` + `test_rls_tenant_context.py` | 63 passed, 1 skipped: общая тестовая область ролей уже занята предыдущим модулем |
| Пропущенный `test_runtime_role_bootstrap_is_idempotent_and_verifies_privileges` в новом изолированном запуске | passed; причина пропуска проверена отдельно |
| Финальный `test_system_admin_security.py` (19 сценариев) + существующий тест metadata/create_all для summary slots | 20 passed; исправленный playback harness включён |
| Ruff на девяти изменённых Python-файлах | passed |
| `uv run alembic heads` | Единственный head `0086_system_admin_boundary` |
| `git diff --check` | passed |
| Проверка документов Feature 254 и governance проекта | passed |

Команды PostgreSQL запускались из корня репозитория:

```sh
apps/server/scripts/run_local_postgres_tests.sh --focused tests/integration/test_system_admin_security.py tests/integration/test_rls_maintenance_context.py tests/contract/test_rls_production_boundary.py -x -q
apps/server/scripts/run_local_postgres_tests.sh --focused tests/integration/test_rls_postgres_policies.py tests/integration/test_playback_normalization_postgres.py tests/unit/test_rls_tenant_context.py -x -q
apps/server/scripts/run_local_postgres_tests.sh --focused tests/integration/test_playback_normalization_postgres.py::test_runtime_role_bootstrap_is_idempotent_and_verifies_privileges -x -q
apps/server/scripts/run_local_postgres_tests.sh --focused tests/integration/test_system_admin_security.py tests/integration/test_meeting_summary_slots.py::test_mapped_metadata_create_all_is_compatible_with_migrated_slot_schema -x -q
```

Одиночная проверка bootstrap фактически также выполнялась первой в запуске с новым harness; bootstrap прошла, обнаруженные затем ошибки harness устранены и проверены финальным запуском. Два предупреждения pytest связаны с уже существующими import rewrite и Starlette/httpx deprecation; не скрывались.

Это проверки начатой реализации. Полный CI, `ci-local --fast`, браузерная приёмка консоли, MFA/last-admin гонки, операции с контентом, финансы/акции, нагрузка, converge и release gates не выполнялись. Они требуются на следующих этапах; эти результаты не являются разрешением выпуска.

## Продолжение: полномочия на объекты и аудит чтения

После следующего поручения пользователя работа продолжена в том же дереве без нового коммита. Прочитаны актуальные контракты, проверены открытые владельцы #6713/T002 и #6714/T003, состояние reviewer-owned списков не менялось.

**Текущее состояние:** основание T002 выполнено. Все отношения, к которым системная роль сейчас имеет доступ, защищены ограниченными grants/RLS. Дополнительные предметные проекции добавляются вместе с их функциональностью в T008–T035; отсутствие преждевременно выданного SELECT на них не является готовым пользовательским экраном. T003 выполнена только в части аудита чтений; предпросмотры, долговечные команды, worker claim/continuation, диспетчер и аудит результатов команд ещё не реализованы. Полная приёмка AC-001/003/036/041 и всей фичи не заявляется.

Добавлена миграция `0087_system_scoped_authority` и серверный модуль `system_admin`:

- Фиксированная матрица шести ролей и 36 известных разрешений. Неизвестное разрешение не получает даже суперадминистратор; временные grants ограничены разрешёнными сочетаниями роли, действия и типа объекта.
- `permission_grants`: точные principal/assignment/version/permission/target, срок не более 24 часов. Замена версии назначения, отзыв и истечение немедленно закрывают grant. Управление выдачей grants и защита последнего администратора остаются T006; обычные роли не могут писать в таблицу grants.
- `SystemDatabaseContext` содержит тип/UUID цели, контекст обращения и ссылку на событие аудита. Неполные и неизвестные сочетания отклоняются; глобальный запрос допускает отсутствие обоих полей цели. Если метаданные запрошены с конкретной целью, RLS не выдаёт другие встречи.
- `case_contexts` в текущем внутреннем сервисе связывает одну точную цель, причину и административную сессию; несколько объектов обслуживаются отдельными контекстами. Срок не длиннее абсолютного срока сессии. Такой контекст не даёт разрешений: администратор с доступом только к метаданным может открыть обращение, но не прочитать расшифровку.
- `audit_events` сохраняет фактические actor/session/role/permission/target, результат и снимок причины. Автор и результат выводятся SQL-функцией из подтверждённой сессии и текущих полномочий, не передаются свободными полями. Системный runtime не получает INSERT/UPDATE/DELETE/TRUNCATE этой таблицы; запись идёт только через узкую функцию, чтение — по `audit.read`.
- Разрешённое и запрещённое чтение записываются отдельной транзакцией. Отказы по известной отозванной сессии сохраняют фактического автора, но не создают действующее полномочие. Неизвестные токены остаются ответственностью будущего аудита входа T005.
- `authorize_access` возвращает контекст только после commit. Дополнительно SQL-проверка отвергает событие, записанное текущей ещё не завершённой транзакцией (`writer_transaction`), поэтому собственного незакоммиченного INSERT недостаточно.
- Разрешение на содержимое связано с сессией, обращением, конкретной целью, действием и событием не старше 60 секунд. Прослушивание не разрешает скачивание; перенос контекста в другую сессию и использование старого события запрещены. Действующая роль/grant проверяются снова при каждом обращении.
- Недоступность аудита распространяется как ошибка БД и не выдаёт разрешение. На этом этапе это проверенный механизм полномочий: реальные текстовые/аудио endpoints и проверки ревизии/удаления подключаются в T010–T012, сами байты ещё не выдаются.
- Bootstrap проверяет новый точный набор столбцов аудита. Общие права app/maintenance/media не расширены, секреты и прямые grants системных учётных записей им не выданы.

Новые проверки сначала воспроизвели отсутствие функции системных разрешений; затем выполнены на PostgreSQL 17:

```sh
apps/server/scripts/run_local_postgres_tests.sh --focused tests/integration/test_system_admin_authority.py tests/integration/test_system_admin_security.py tests/integration/test_rls_maintenance_context.py tests/contract/test_rls_production_boundary.py tests/unit/test_rls_tenant_context.py -x -q
# 78 passed; до последнего добавления снимка причины в audit event.

apps/server/scripts/run_local_postgres_tests.sh --focused tests/integration/test_playback_normalization_postgres.py::test_runtime_role_bootstrap_is_idempotent_and_verifies_privileges tests/integration/test_system_admin_authority.py tests/integration/test_system_admin_security.py tests/integration/test_meeting_summary_slots.py::test_mapped_metadata_create_all_is_compatible_with_migrated_slot_schema -x -q
# 44 passed, без skipped; финальная схема и снимок причины включены.
```

Ruff, документный validator, project governance и `git diff --check` прошли. Единственный Alembic head: `0087_system_scoped_authority`. Полный CI и выпуск не выполнялись. Задачи #6712/#6713 остаются открыты до PR и его проверок; новые изменения не закоммичены и не опубликованы.

## Продолжение реализации: команды, вход и первые страницы

Добавлены миграции 0088–0091. Это рабочий промежуточный участок, а не завершение T003–T008 или всей фичи.

- Предпросмотр двух команд встречи хранится 5 минут; проверяется монотонная версия встречи. Commit сохраняет команду и аудит вместе, повтор ключа возвращает прежнюю операцию. Узкие worker-функции проверяют текущую роль/сессию до начала и точную цель/ссылку/fence при продолжении; SQL-проверки покрывают отзыв и конфликт версии. Реальный Temporal dispatcher, доменные handlers, batch и scheduled approvals ещё не подключены.
- Отдельный ASGI entrypoint, изолированные файлы секретов, выключенные по умолчанию флаги, host/Origin/CSRF, host-only cookies, no-store/CSP, ограничение тела 64 KiB. Добавлен необязательный Compose overlay и шаблон отдельного nginx virtual host; production не изменён.
- Пароль scrypt N=131072/r=8/p=1; два параллельных вычисления и очередь 10. Отмена HTTP-запроса не освобождает вычислительный слот до завершения потока. TOTP проверен по RFC6238, seed шифруется AES-GCM с AAD principal UUID. Счётчик одноразового кода и версии challenges проверяются под блокировкой. Предусмотрены enrolment/recovery/password reset/step-up и CLI init/recover. Recovery не выдаёт прикладную сессию до нового MFA. Ротация ключей, повторные приглашения, все лимиты/отказы и полная эксплуатационная проверка ещё требуют завершения T005–T007.
- SQL-назначения административных ролей сериализуются на singleton и principal locks; есть защита последнего бессрочного суперадминистратора и запрет изменения собственной роли. Проверена конкурентная попытка снять два последних назначения. Runtime API выдачи временных grants ещё не подключён.
- Страницы входа/активации/сброса пароля, текущего доступа, встреч, пользователей, администраторов и аудита. Существующие страницы ещё не покрывают все требуемые поля/фильтры/сортировки/действия. Полная браузерная приёмка T036 не выполнялась.
- Пользовательская проекция показывает назначенный тариф и состояние личной подписки. Суммы подтверждённых счетов и наблюдаемых возвратов доступны только billing.read; корпоративные платежи не попадают в личные итоги участника. Это ещё не общий resolver возможностей и не управление каталогом/подписками/акциями.
- Для совместимости со старыми public RLS-функциями user projection использует фиксированный `pg_catalog,public,pg_temp`; все собственные отношения квалифицированы схемой. Bootstrap запрещает runtime-ролям CREATE в доверенной public schema; прямые SELECT системной роли на users/payment tables не выдавались.

Подтверждённые проверки на изолированном PostgreSQL 17, только синтетические данные:

```sh
apps/server/scripts/run_local_postgres_tests.sh --focused tests/integration/test_system_admin_operations.py tests/integration/test_system_admin_authority.py tests/integration/test_system_admin_security.py -x -q
# 49 passed: операции + прежняя граница доступа до последующих auth-миграций.

apps/server/scripts/run_local_postgres_tests.sh --focused tests/integration/test_system_admin_login.py tests/integration/test_system_admin_management.py tests/contract/test_system_admin_app.py -x -q
# 14 passed: сброс пароля, последний администратор под гонкой, вход и HTTP boundary.

apps/server/scripts/run_local_postgres_tests.sh --focused tests/integration/test_system_admin_login.py tests/integration/test_system_admin_management.py tests/integration/test_system_admin_operations.py tests/integration/test_system_admin_authority.py tests/integration/test_system_admin_security.py tests/contract/test_system_admin_auth.py tests/contract/test_system_admin_app.py tests/integration/test_rls_maintenance_context.py tests/unit/test_rls_tenant_context.py -x -q
# 92 passed: версия до добавления user projection и почтовых HTTP-маршрутов.

apps/server/scripts/run_local_postgres_tests.sh --focused tests/integration/test_system_admin_users.py tests/integration/test_system_admin_login.py tests/integration/test_system_admin_security.py tests/contract/test_system_admin_app.py -x -q
# 35 passed: user projection, финансовая изоляция и миграции до 0091 включительно.
```

Не было реальных писем, приглашений, платежей или чтения пользовательского содержимого. Полный CI, нагрузка, Temporal/MinIO сценарии, converge и PR ещё предстоят. Контрольная проверка origin/master не показала новых исходных коммитов относительно базы ветки на этом этапе.

## Продолжение: административные формы и защищённая расшифровка

Добавлена миграция `0092_system_meeting_content`. Новые задачи не отмечались завершёнными: это продолжение T003–T013, все оставшиеся требования сохраняются.

- Исправлена нестабильная выдача сессии: обе SQL-функции фиксируют один момент времени для issued/MFA/interaction/12-hour expiry. Проверяются точное равенство границ, успешный вход и enrolment.
- Работают HTTP и формы приглашения/повтора, изменения назначения, временных объектных прав и отзыва. Результат отправки хранится на challenge; разрыв после отправки оставляет `sending` с понятной неопределённостью. Повтор отзывает старые ссылки, ограничен по частоте. Реальных писем не отправляли.
- После ожидания блокировки повторно проверяется свежесть MFA в административных изменениях. Изменение роли приглашённого не активирует его автоматически.
- Отдельные POST-маршруты контекста разбора, чтения и проверки текущего права. Контент требует role/grant + конкретную встречу + case + ранее закоммиченный аудит. RLS закрывает текст при отзыве или начале удаления, даже при permissive PUBLIC policy. Не выдаются downloads/provenance или полный SELECT таблиц.
- Расшифровка использует общий `effective_processing_result_query`, последнюю принятую неизменяемую ревизию и 100 фрагментов на страницу. Переход страниц закреплён за результатом; смена версии даёт конфликт. Поиск идёт через POST, `%` трактуется буквально. JS использует textContent и очищает содержимое при закрытии/скрытии вкладки/отзыве; запоздалый ответ поиска не заменяет более новый.
- Bootstrap и старт процесса проверяют обязательные restrictive RLS gates новых таблиц. Необязательная почтовая конфигурация добавлена в отдельный Compose service. Обычное приложение не получает системные секреты.
- Запуск созданной попытки вынесен из HTTP-обработчика в общий `processing/dispatch.py`. Пользовательский маршрут использует прежнее поведение; общая функция сохраняет WORKFLOW_STARTED до Temporal. Административные доменные handlers и dispatcher пока не подключены.

Проверки на одноразовом PostgreSQL 17:

```sh
apps/server/scripts/run_local_postgres_tests.sh --focused tests/integration/test_system_admin_content.py tests/integration/test_system_admin_users.py tests/integration/test_system_admin_login.py tests/integration/test_system_admin_management.py tests/integration/test_system_admin_operations.py tests/integration/test_system_admin_authority.py tests/integration/test_system_admin_security.py tests/contract/test_system_admin_auth.py tests/contract/test_system_admin_app.py tests/integration/test_rls_maintenance_context.py tests/unit/test_rls_tenant_context.py -x -q
# 104 passed, до последующих CSRF/UI исправлений и общего dispatch extraction.

apps/server/scripts/run_local_postgres_tests.sh --focused tests/contract/test_system_admin_app.py tests/integration/test_system_admin_login.py tests/integration/test_system_admin_management.py tests/integration/test_system_admin_content.py -x -q
# 23 passed, включая стабильный CSRF для нескольких вкладок.

apps/server/scripts/run_local_postgres_tests.sh --focused tests/integration/test_processing_attempts.py tests/integration/test_media_revision_reprocess.py tests/contract/test_processing_status_contract.py -x -q
# 36 passed после вынесения общей отправки в Temporal.
```

Playwright/установленный Chrome, отдельный локальный HTTPS harness с синтетической почтой и существующими тестовыми встречами: пароль → TOTP → консоль; приглашение → почтовый сервис принял; причина разбора → текст с таймкодами; literal `%` → пустая выдача; поиск фрагмента → совпадение; экран 375×812; отзыв сессии → очистка и возврат ко входу <=15 секунд. При первом отзыве найдена JS-гонка обновления отсоединённой страницы; исправлена и повторно проверена: переход ко входу выполнен без JS pageerror. Это частичная браузерная проверка, не полная T036/доступность/10 support cases. Снимок узкого экрана сохранён локально вне git.

Ruff, `node --check`, документный validator и project governance проходят. Полный CI, нагрузка/60min outage, Temporal/MinIO административные сценарии, billing/каталог/промокоды, converge и release-ready PR остаются незавершёнными. Нельзя выдавать этот участок за готовую Feature 254.

## Продолжение: выполнение команд и история встречи

Миграции `0093_system_domain_lineage` и `0094_system_meeting_overview` добавляют привязку существующих предметных процессов к системным операциям и ограниченные проекции истории. Это промежуточная реализация T003/T010/T013/T014/T015; фича и PR ещё не готовы к выпуску.

- Исправлено тестовое окружение maintenance: оно воспроизводит штатные public grants bootstrap, сохраняя RLS и настоящий отдельный login. Первое падение проверяло отсутствие grants, а не новый trigger.
- `processing_workflows` и `meeting_deletion_requests` содержат неизменяемую ссылку на системную операцию. Создание проверяет claim, target, domain_ref и тип команды; системное удаление не допускает подстановки product user/device ни при INSERT, ни при UPDATE.
- Служебный процесс читает только узкий список системных команд. Claim и предметная запись фиксируются вместе до внешнего эффекта. При откате до commit операция остаётся в очереди и может быть отменена отзывом полномочий. После фиксации повтор наблюдает тот же domain_ref, не создавая новую обработку/удаление.
- Запуск обработки использует общее ядро допуска и dispatch. Оригинальные owner/device нужны только для исполнения существующего pipeline; инициатор закреплён через system_operation_id. Ошибки допуска сохраняются разрешёнными кодами. Старый опубликованный результат остаётся в БД.
- Удаление использует существующую saga, отчёт и purge reconciler. Отзыв browser session не мешает завершить уже зафиксированное удаление. Состояния резервных и локальных копий не сводятся к безусловному успеху.
- Добавлены HTTP preview/commit/status и формы причины, последствий, свежего MFA, подтверждения и просмотра состояния. Повтор после потерянного ответа сохраняет idempotency key. Прямой произвольный callback/SQL/type запрещён.
- Добавлена карточка метаданных, отдельные постраничные версии и попытки обработки, времена, технические причины и состояния отчёта удаления. Проекции не содержат заголовок, расшифровку, storage keys или provider credentials.

Проверки:

```sh
apps/server/scripts/run_local_postgres_tests.sh --focused tests/integration/test_system_admin_operations.py tests/integration/test_system_admin_security.py tests/integration/test_system_admin_login.py tests/integration/test_processing_attempts.py tests/integration/test_meeting_deletion_workflow.py -x -q
# 58 passed: команды/claim, реальная предметная обработка с FakeTemporal, удаления,
# crash до commit, отзыв до/после эффекта, старые processing/deletion сценарии; схема до 0093.

apps/server/scripts/run_local_postgres_tests.sh --focused tests/integration/test_system_admin_login.py tests/contract/test_system_admin_app.py -x -q
# 16 passed: HTTP preview/commit/idempotency/status, отключённые команды, cookie/CSRF.

apps/server/scripts/run_local_postgres_tests.sh --focused tests/integration/test_system_admin_login.py tests/integration/test_system_admin_security.py -x -q
# 28 passed: миграция 0094, downgrade, bootstrap и вход.

apps/server/scripts/run_local_postgres_tests.sh --focused tests/integration/test_system_admin_content.py tests/integration/test_system_admin_login.py -x -q
# 12 passed: карточка, HTTP история и 105 попыток без пропусков/дубликатов;
# отсутствие содержимого и storage secret в метаданных, отзыв доступа.
```

Это не реальный Temporal/MinIO прогон и не полная браузерная приёмка новых форм. Аудио/экспорт/retained diagnostics, account closure, полный billing/тарифы/акции, телеметрия, метрики и общие release gates остаются обязательной работой. Реальные письма, платежи и production действия не выполнялись.
