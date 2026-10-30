# F273/T113: независимое повторное ревью соединений с БД

30.10.2026. Рабочая копия: `/Users/yshishenya/.codex/worktrees/growth-guide-previews/crisp`.
Ветка `codex/f273-local-period-20261029`, HEAD/база
`5501d2ba65ae7d383c511b46bba8ce0a002b0cbb`, T113/#7804,
полоса `high-risk-product`.

**SCOPED PASS окончательных байтов принятого участка. P1: 0; P2: 0.**

Это обязательное независимое повторное ревью реализации уже принятого проекта
соединений БД, включая два окончательных исправления. Оно не является новым
проектом T113 или приёмкой полного оператора. Проверены фактический diff к базе,
код затронутых функций, их вызывающие контексты и зависимости, тестовые сценарии,
предоставленные журналы и контрольные суммы. Предыдущие независимые отчёты
[t113-database-design-review-20261030.md](t113-database-design-review-20261030.md)
и [t113-database-code-review-20261030.md](t113-database-code-review-20261030.md)
прочитаны. Исторический **HOLD/P2-01** первого code review сохраняется как
результат прежних байтов; этот новый отчёт фиксирует результат повторной проверки.

Ревьюер выполнял только чтение локальных файлов/Git, подсчёт отметок и SHA-256.
Тесты, SQL, Docker, SSH, приложения, сборки, выпуск и рабочий root operator
не запускались; агенты не создавались. Единственная запись — этот новый отчёт.
Код, требования, отметки, Git/GitHub и изменения других участников не менялись.

## Повторная проверка исправлений

1. **P2-01 закрыта на окончательном коде.** В
   `activation_operator.py:2475–2512` результат формируется внутри удерживаемых
   Settings/owner-secret/DB контекстов, но возвращается после их полного выхода.
   Сначала выполняется заключительная `_database_identity`, затем закрываются
   source/owner, затем завершаются проверки и освобождение файловых ресурсов.
   Только после этого `_require(time.monotonic() < deadline,
   "activation_operator_runtime_timeout")` разрешает `return result`.
   Равенство сроку тоже отклоняется. Предел не пересоздаётся и не продлевается.
   Cleanup сохраняет владение ресурсами, даже если длится дольше бюджета;
   подготовленный `runtime="verified"` наружу при просрочке не возвращается.

   Два окончательных случая `late_database_close` и `late_secret_close`
   переводят часы за исходный deadline при нормальном выходе соответствующего
   контекста. Прочитанный причинный RED прежней редакции содержит два
   `DID NOT RAISE ActivationHold`; на окончательных тестах оба должны и,
   согласно итоговому профилю исполнителя, действительно дают отказ.
   Это проверка причины прежнего дефекта без продления срока или обрыва cleanup.

2. **Гонка failed connect/отмена закрыта.** В
   `activation_operator.py:1966–2001` connect task удерживается через shield
   до завершения. Если ожидатель уже получил отмену, а `task.result()`
   поднимает обычное исключение соединения, новый обработчик передаёт
   `CancelledError`, без прежней подмены на `OSError`. Если connect успел
   вернуть соединение, оно сначала записывается в принадлежащую контексту
   переменную, затем передаётся отмена и выполняется закрытие в finally.
   Повторная отмена не оставляет позднее успешное соединение без владельца.

   `_settled_sql(connection.close(timeout=3))` дожидается закрытия при повторной
   отмене; отсутствие подтверждённого закрытия приводит к terminate fallback.
   Ошибка close не становится успехом. Прочитаны причинный RED
   `connect_race` с прежним `OSError` из `task.result()` и окончательная
   матрица connect/connect_error/connect_race/body/close/close_error:
   **6 passed** по журналу исполнителя. Отдельно проверена реализация общего
   `_settled_sql`; это сохранение сигнала отмены, без заявления о сохранении
   того же объекта исключения или его сообщения.

## Реальные пути и отсутствие обнаруженных регрессий

- `_runtime_main` по-прежнему задаёт один исходный срок **30 секунд**.
  Весь runtime preflight и последующие проверки получают тот же deadline.
  Connect ограничен `min(3, остаток)`; timeout DB-области не заменяется новым
  полным бюджетом. Последняя проверка срока выполняется также после синхронного
  файлового cleanup. Внешние35 секунд bootstrap не разрешают внутренний
  просроченный verified.
- `_runtime_preflight` получает actual Settings только работающих writers,
  удерживает все их контексты и owner password до конца DB-области. PostgreSQL
  процесс читается отдельно с четырьмя UID/GID70, mapping/starttime/groups;
  прежние defaults100/101 для GRAF не расширены. После DB-подготовки повторяются
  actual inspect, process identity, network inventory, postal identity,
  release bytes, HEAD, Compose/volume policy и socket identity.
- Адрес берётся из согласованных actual PRIVATE endpoint и network Containers:
  IP/NetworkID/prefix должны совпадать; DNS, loopback, multicast, unspecified,
  непригодные специальные адреса и адрес сети/broadcast не допускаются.
  URL разбираются штатным `make_url` до connect: exact driver, host, port,
  canonical DB, роль службы, password и отсутствие query. Обязательные writers
  должны присутствовать. Второй URL prompt worker также проверяется;
  в закреплённом Compose оба его URL используют maintenance.
- `_bound_runtime_file` имеет двух настоящих потребителей:
  `_runtime_settings` и `_runtime_owner_password`. Сохранены canonical paths,
  защищённые source ancestors, ACL, O_NOFOLLOW, single link, owner/mode/size,
  exact RO file bind, сравнение фактического proc-root inode и bytes,
  повторные проверки при успешном выходе и закрытие FD при любом выходе.
  GRAF сохраняет group-read, optional placeholder и sealed memfd с обычными
  production Settings validators. Actual Env остаётся единственным источником
  настроек; duplicate/case collision и inline database password не принимаются.
- Owner Env требует exact POSTGRES_USER/DB/PASSWORD_FILE, без прямого
  POSTGRES_PASSWORD/HOST_AUTH_METHOD. Для owner leaf доверенный root читает
  mode600/640 без требования daemon70 group-read; traversal каталогов
  проверяется для UID70. Права не меняются. Время жизни proc-root/file FD
  включает весь DB preflight; замена процесса/root/source/bind исключает успех.
- Owner физически подключён к postgres; отдельный source сначала подключён как
  owner к canonical twobrain_rec. Штатный readonly `_verify_runtime_roles`
  выполняется до понижения source, в read-only transaction, с необходимой
  видимостью information_schema. После завершения transaction выполняются
  SESSION AUTHORIZATION maintenance, row_security=on и `_database_identity`.
  Продуктовый preflight не вызывает `_bootstrap`; тот вызывается только при
  подготовке собственной БД в интеграционном тесте.
- Каждый actual Settings URL проверяется настоящим физическим соединением:
  DB/OID/cluster/revision, session_user=current_user=ожидаемая роль,
  row_security, login, отсутствие опасных атрибутов и memberships.
  Штатный verifier дополнительно проверяет все три runtime роли и grants.
  Source/owner удерживаются до заключительной runtime/DB сверки.
  PG major17 и единственная actual Alembic revision сопоставляются с
  единственным packaged head. Проверка head не объявляется полной проверкой
  schema/constraints/RLS/ledger/lifecycle.
- Внешний успешный runtime ответ имеет прежние **четыре поля**:
  `runtime`, `source_sha`, `container_count`, `runtime_sha256`.
  DB/owner-secret proofs входят только в aggregate digest.
  Bootstrap по-прежнему строго проверяет этот набор и оставляет общий
  `HOLD/full_preflight_not_implemented`; unconditional
  `activation_recovery_unverified` в legal gate сохранён.
  Новых DDL/DML/grants, stop/revoke/export/initial/T0/ready, зависимостей,
  framework или новой фичи этот diff не вводит.

Иных конкретных P1/P2 в рассмотренном принятом участке не обнаружено.
Согласованность реализации с принятым precode и затронутыми требованиями —
**scoped analyze PASS**; новых решений владельца для этих исправлений не требуется.

## Прочитанные доказательства исполнителя и их пределы

Все результаты ниже — из предоставленных файлов, **не собственные запуски ревьюера**.

| Артефакт в `.dev/growth/` | Фактическое содержание |
| --- | --- |
| `t113-database-profile-final-20261030.log` | 472 passed, 6 skipped, 2 warnings; окончательный профиль |
| `t113-database-native-final-20261030.log` | 6 passed, 17 deselected, 2 warnings; повтор шести migrated native DB preflight случаев после исправлений |
| `t113-database-full-native-20261030.log` | 23 passed, 2 warnings на редакции до двух окончательных исправлений; не выдаётся за повтор23 на финальных байтах |
| `t113-database-linux-final-20261030.json` | exit0, 38 passed; четыре извлечённых tracked Settings теста, hash unit-файла совпадает с окончательным |
| `t113-database-owner-bind-native-20261030.{py,json}` | Настоящий свой PostgreSQL17 UID/GID70 и exact bind; положительный leaf640 root:1001, HOLD при source replacement и при запрете traversal |
| `t113-database-connect-race-red-20261030.log` | Причинный прежний failed connect: OSError вместо CancelledError |
| `t113-database-deadline-red-20261030.log` | Два причинных прежних отказа тестов: DID NOT RAISE для DB/file cleanup после deadline |
| `t113-database-connect-cancel-20261030.log` | 6 passed, 277 deselected, 2 warnings |

Окончательные native6 используют полные migrations собственной PostgreSQL и
штатный bootstrap только для подготовки стенда. SQL и readonly verifier
не подменены. Матрица включает успех, wrong revision, лишний media DELETE,
фактический owner вместо app, membership и повторную отмену настоящего pg_sleep;
код теста требует0 backend с application_name оператора после каждого случая.
Остальные17 старых drain/export/stop случаев кодом этого diff не изменены,
но на окончательном запуске они были deselected, а не повторно выполнены.

На Mac native DB-профиль перенаправляет **только host/port транспорта** на
собственный loopback port. Это подтверждает настоящий SQL/права/закрытие,
но не рабочий Docker bridge маршрут. Выбор IP и согласованность двух network
views отдельно покрыты прочитанной причинной матрицей.

Linux38 проверяет настоящие ACL/memfd/ancestry/FD на собственном томе.
Сценарий извлечения прочитан: берёт точные тела четырёх тестов из tracked unit
файла; candidate source подключён через PYTHONPATH. JSON фиксирует tracked
test hash, но отдельного operator hash в нём нет. Это ограниченное
доказательство shared Settings extraction, не всего установленного оператора.

Сценарий owner bind прочитан целиком. Проверяющий контейнер входит в
**собственное пространство PID** PostgreSQL, с **SYS_PTRACE** для proc-root:
PID1 обозначает тот же реальный PG-процесс. Он не подменяет функции
owner/file/process/traversal. Это подтверждает механизм exact proc-root bind,
но не полный Compose policy, host PID namespace, рабочую установку или запуск
неизменяемого установленного пакета. Candidate source здесь тоже подключён
через PYTHONPATH; JSON не содержит отдельного operator hash.
JSON сообщает owned_resources_removed=true и production_touched=false;
ревьюер не выполнял независимую инвентаризацию Docker. Исторический первый
запуск без --interactive с пустым stdout/exit1 не принимается как причинный RED.

Журналы pytest сами не содержат отдельной криптографической привязки operator
bytes; их сопоставление основано на отчёте исполнителя, окончательных файлах
и хешах ниже. Они не заменяют точные PR/CI/release gates.

## Требования, отметки и границы решения

AGENTS.md, guidance index, document-reading, development-process и spec-kit-flow
прочитаны. Активные пути подтверждены feature.json и
`check-prerequisites.sh --json --paths-only`; вложенных AGENTS для затронутых
путей не найдено. Полоса остаётся high-risk-product существующей F273/T113.

Применено явное разрешение владельца для повторного ревью F273:
четыре принятых baseline сверены по SHA-256 вместо нового полного чтения.
Все четыре значения совпали с назначением. Текущие spec/plan/tasks/quickstart
сверены по фактическим файлам и хешам; перечитаны затронутые полные разделы
Functional Requirements и пробелов требований, продолжение T112/T113 и первый
локальный период в plan, T112/T113 и операторские примечания tasks,
сценарии4/7 и дополнение первого периода quickstart. Перечитаны применимые
разделы activation-milestones, operations, устойчивая account-веха data-model,
команды/доверие/владение/initial/staged rehearsal и обязательные границы
full-operator-design; полностью прочитан принятый database precode.
Неизменные прочие baseline/зависимости используются в разрешённой владельцем
границе прежних независимых ревью, без заявления об их новом полном чтении.

Все117 действующих checklist вопросов перечитаны; markers не изменялись:

| Список | Отмечено | Открыто |
| --- | ---: | ---: |
| requirements | 16 | 0 |
| privacy-measurement | 45 | 0 |
| security | 27 | 0 |
| infra | 29 | 0 |
| **Всего** | **117** | **0** |

Хеши всех четырёх списков совпали с предыдущими независимыми отчётами.
Это качество требований, не подтверждение исполнения продукта.
Статусные добавления tasks/organic-growth-plan/F273 fragment прочитаны:
T113/T112/AC01–AC06 не закрываются и рабочий результат не объявляется.

**Общие HOLD сохраняются.** Полные schema/constraints/RLS/ledger/lifecycle,
legal/register/local retention/access/resource preflight, верхние
initial/backup/verify/actual restore/resume, shell/CD/rollback/daily и T112
этим решением не принимаются. UID1003 не подтверждён; рабочий root operator
не запускался. Никакого разрешения production/T0/ready/аналитики/IP/получателей,
выпуска, трафика или продаж этот SCOPED PASS не даёт.

## Фактические SHA-256 снимка

Три окончательных исходных файла совпадают с ожидаемыми хешами назначения.
Значения review-input JSON на момент чтения также совпали; источником решения
были фактические файлы. Все49 входных файлов ниже повторно сверены перед
созданием отчёта: изменений между чтением и записью не обнаружено.

```text
24c0767f2223bb21e969079ec1ec09e0dec7c3fd3d85d02e78832f17e0775958  AGENTS.md
2f3e0339a89d3ccdf0878026920955a189584d6a985116b069584cd78b3c75bb  docs/agent-guidance/README.md
5263860b1974df022826ac81c2482e6ee92100bc0bb718ab5a29b32e2422e411  docs/agent-guidance/document-reading.md
41fa13de8addaec6cc7c13c8be9da53c2c5527a302247d85b738f20c3155e864  docs/agent-guidance/development-process.md
afb816ce48624eb79fcd7fd44d09f0986296e87ef1cfecd790228ac70a5b9b9e  docs/agent-guidance/spec-kit-flow.md
5163998f85273617c02f1f0142995819014da9d6b313a3532731271b8191d2e8  .specify/feature.json
7616e3d7c8112aa60b1be1cc40594a7dfd25b0870f23b821d7efefd7c23f4ba8  .specify/memory/constitution.md
0f3ccfcfa60062bb0aae6802eeb0012056a635a30cb9f46f54d1992d0b4f57c2  docs/prd-voice-layer-final.md
25b7f383be47c7160da8e852006ff82019f30a5f9c371fc30baa79238649cd16  docs/current-product-status.md
9f7072c879490d250053cb7397ad6b9b68fdcde17bdf9367ed874a41e450b5f5  docs/agent-guidance/product-gates.md
45bcc14f170951e99813d6aeb0eddbbb413dd64f89cf410da256b6d5e30986b2  specs/273-paid-traffic-analytics/spec.md
02f4b52274c61fdf69f01415448a28d9509a1c12274a09d5a7382d3fc3db1b19  specs/273-paid-traffic-analytics/plan.md
09b008e44b51c0820aac6d090053f70d7d6902fb3aa5e5f8c300f2f9f49d9481  specs/273-paid-traffic-analytics/tasks.md
5bde6a5f388a03b6df1440fca32429f49bd458fdf9203fdc8df880352d249fea  specs/273-paid-traffic-analytics/quickstart.md
4dba6d438a50cfa20b06e5d8f1d1fdd7fe216f271341c95a1d4bb553e135e962  specs/273-paid-traffic-analytics/data-model.md
9898007a0e87400246f8c95b899dd807fab0424472143e15338429873982f3f9  specs/273-paid-traffic-analytics/contracts/activation-milestones.md
7d68aa7dc06b170508cd8b2858ede6e3e929b2e7155cd03b0895e715cb2b3abb  specs/273-paid-traffic-analytics/contracts/operations.md
5d1e069f3fe18f31a21c72c9b0abc41614ff8bfc00c3269f27b1f3cb596738ec  specs/273-paid-traffic-analytics/validation/t113-full-operator-design-20261030.md
6ae27f745d1ea65a74fcd7f222792394aa1db562d988019d3d043b3ebd3d4cfe  specs/273-paid-traffic-analytics/validation/t113-database-design-review-20261030.md
836b4c88dc24501e51f098fd85b8d9ad6afcfdce7a5ae876d5a38e6bab772ff0  specs/273-paid-traffic-analytics/validation/t113-database-code-review-20261030.md
6447fe78a32c538a270d63ac6714e9a5e32f2777982ebc413f3ecbd5547d3d46  specs/273-paid-traffic-analytics/validation/t113-database-preflight-20261030.md
6c2144a01a4b20a4fa3d89e13ecb54b34fec457cee5f1d2e0d64b27e4c380cef  apps/server/src/twobrain_rec_server/product_analytics/activation_operator.py
80faf87396e21bf1b7640dd3a9633dc7b6e28791ca31a1f6c78f10e82a47bb4c  apps/server/tests/unit/test_activation_operator.py
71265a9098abdeb64e31e21b6f8a998cffb7e53c9b9d1682c8b4a85b09c07f84  apps/server/tests/integration/test_activation_product_drain.py
2cd24aff502295b9eabbdf5ddbdbf853466f63b10c67cf3cbdf00fd426e3cfeb  apps/server/src/twobrain_rec_server/config.py
eef89121ad607503d99ab3dd2c70b4bc6cdedb7a3ff551b24850ac91ee78adba  apps/server/scripts/bootstrap_runtime_database_roles.py
e11efddb4001602014977be3dff5e86550978cf81bfe67f23d7ae60a0bdfbfb5  infra/scripts/activation-operator.py
9098cb15c8c4a675beae529664e128d46a2dc50671dee8171d05b659b482bcc6  infra/docker-compose.yml
9975596c2901035e2f58fe16481a19d1bc4d3924e8b3a00b1da69cfe80df505b  apps/server/tests/fixtures/postgres_test_database.py
9878ffa671eacede35b599fe7a8c6fed0a2c8a75561a8d6d7d7911c13e28ebad  infra/scripts/rec-db-verify.py
3638e1d9279656a1864a5229a2210af8812499747108e37d16b33c763a419cdd  infra/scripts/rec-db-backup-inventory.sql
b5ee4700348fc8fd293ca2527d7d27fde5aa1d9b472cab866eb03df88f688486  changes/unreleased/F273.yaml
bdff88ea5da4accdee4fa7dea42302be99087792d98504f033fd9afe8bbd6e48  docs/growth/organic-growth-plan.md
998175e297553cedac7f4d7b2829459fcb3f1b650b3b3b6d072e9065437bfa94  specs/273-paid-traffic-analytics/checklists/infra.md
8c390000a2da12cf719348d56c08dcb21d886aac98ba1a90ad3d5c41e141cb4f  specs/273-paid-traffic-analytics/checklists/privacy-measurement.md
6755318d0b7a76a9f6439446ad42362272d43859cc6f4b3c045b5c36ad1ed9a2  specs/273-paid-traffic-analytics/checklists/requirements.md
57f082b0b90faf7a3302db0aa1b9aacd29948641e824578ca4f86eee4dee9cb8  specs/273-paid-traffic-analytics/checklists/security.md
2ce581a1ecb66110f6750cf58231c7e12bfeb8a4cd28c2bb248c5a1f20cd52a6  .dev/growth/t113-database-precode-20261030.md
b452dbc555d0d391ecf47f8a083aa3a4ce9ba53e48596cf06d1c9fdbe75a90b7  .dev/growth/t113-database-review-input-20261030.json
35e84fdd57785b4a7e5634c42fd11c554c10a0b7b1332e4de7d4d1ba908da486  .dev/growth/t113-database-profile-final-20261030.log
10d3dafd922d39e324369d699fb83b28e9c1367b898d08b914dcdab9c0b2cf02  .dev/growth/t113-database-native-final-20261030.log
dc2376f65ed316974eefec0110f5be12e19e49a4b762acb7577c6ed07f621c49  .dev/growth/t113-database-full-native-20261030.log
58a9494888cc9108a0254efaa6b13749a0f9d5cbb59c2087f8663d439089f00d  .dev/growth/t113-database-linux-final-20261030.json
01a3000750fbc88020224073877fb3dcd6fc9a8292f42014aed0dd03054a75fb  .dev/growth/t113-settings-native-20261030.py
88a27d7190a072d540babaf18b3eeaf79d2edd79326ff68bd78b6e77ac2b3f69  .dev/growth/t113-database-owner-bind-native-20261030.py
039fc8a51badfdefb44df9ffdfe9f53e5cafd4a57a885f82bbb2dfae0a74c928  .dev/growth/t113-database-owner-bind-native-20261030.json
31f1e7fe9917c6aa15b84023219f6cfdecea04c3f9984c96ae57caca65dd6c2c  .dev/growth/t113-database-connect-race-red-20261030.log
28d74ae711612c609a7c88fdf842a7a9ccefd5c72371b0b33a6e0ea2808996e0  .dev/growth/t113-database-deadline-red-20261030.log
d85fbee67944936cdc2ba86ab23dcbc04d40bb60cebbfdc3c18a84459e32253d  .dev/growth/t113-database-connect-cancel-20261030.log
```
