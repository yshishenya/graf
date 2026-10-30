# F273/T113: независимое ревью проекта соединений с БД

30.10.2026, `/root/f273_release_boundary`, основа
`5501d2ba65ae7d383c511b46bba8ce0a002b0cbb`, существующие T113/#7804,
полоса `high-risk-product`.

**SCOPED PASS проекта следующего участка для реализации. P1: 0, P2: 0.**
Это решение по конкретному алгоритму до кода. Реализация, native проверки,
полная схема и готовность аналитики этим отчётом не приняты.

Окончательный проект прочитан целиком:
`.dev/growth/t113-database-precode-20261030.md`, SHA-256
`2ce581a1ecb66110f6750cf58231c7e12bfeb8a4cd28c2bb248c5a1f20cd52a6`.
Он продолжает принятый полный алгоритм, а не создаёт отдельную фичу,
framework, роль, grants, HBA, сервис или helper PR. Ревьюер выполнял только
чтение локальных файлов/Git и проверку хешей; тесты, Docker, SQL, SSH,
GRAF Dev и рабочий сервис не запускал. Записан только этот отчёт.

## Минимальный следующий алгоритм

1. В существующем ExitStack runtime preflight удержать фактические Settings
   всех работающих writers. До соединений разобрать URL штатным `make_url`:
   точные driver/host/port/database, отсутствие query и точная роль для службы,
   включая второй URL prompt optimization при наличии. Не получать endpoint
   или учётные данные из произвольной среды/CLI.
2. Взять IPv4 только у проверенного `rec-postgres` в PRIVATE network.
   Сверить IP, NetworkID и запись network Containers. Проверить настоящий
   PID PostgreSQL тем же `_process_identity`, с фиксированными UID/GID70;
   прежние UID100/GID101 для GRAF не расширять. Повторить identity/inventory
   после удерживаемой области, чтобы не принять смену процесса или адреса.
3. Из существующего чтения mapped secret выделить один внутренний
   contextmanager без ослабления ACL, предков, no-follow, единственной ссылки,
   owner/mode/size и повторных inode/bytes. Для owner PostgreSQL читать только
   exact bind заданного `POSTGRES_PASSWORD_FILE` через настоящий proc-root.
   Проверка исходного файла без сравнения фактически подключённого не подходит.
   GRAF group-read и исключения пустого optional placeholder сохраняются.
4. Открыть два физических asyncpg-соединения без пула: owner в `postgres`
   и source в canonical `twobrain_rec`, первоначально как тот же owner.
   Source до понижения выполняет только существующий readonly verifier ролей
   и проверку packaged head в read-only transaction. После её завершения
   выполнить `SET SESSION AUTHORIZATION twobrain_rec_maintenance`, явно
   `SET row_security=on` и существующий `_database_identity`. До yield source
   уже понижена; replay не получает owner credentials/factory и не повышает её.
5. Через реальные credentials каждого фактического Settings role URL открыть
   отдельное соединение к тому же проверенному адресу. В read-only transaction
   сверить canonical DB/OID/cluster/revision, session_user=current_user,
   row_security, login и закрытые атрибуты/отсутствие memberships.
   Одна строка имени пользователя в URL не является таким доказательством.
6. Единственный packaged Alembic head должен существовать и точно совпадать
   с единственной строкой actual revision. Принять PG major17. Это проверка
   версии схемы, а не доказательство полного набора constraints/RLS/данных.
   Для последнего остаются прежние native inventory/schema/backup средства.
7. Один владелец держит connect tasks и все соединения, включая гонку успешного
   connect с отменой. Родитель не выходит при повторной отмене раньше закрытия
   известных ресурсов. Close ограничен, fallback terminate не даёт успешного
   результата после ошибки. Общий срок прежние30с, connect≤3с/остатка,
   никаких новых полных таймаутов для следующего запроса. Source/owner удержаны
   до последней runtime сверки и закрыты до выдачи прежних четырёх полей.

DB binding и итог проверок включаются только в aggregate runtime digest.
Raw URL, password, secret bytes, исключения драйвера и частные строки не
становятся stdout/evidence. Ни одного DDL/DML/GRANT или продуктового stop,
revoke, export, initial, ready, T0 в этом участке нет.

## Найденные вопросы и их исправление до кода

**R1 — видимость information_schema, первоначально P2: закрыта проектом.**
`_verify_runtime_roles` читает `information_schema.role_table_grants` и
`role_column_grants` для media. Эти представления ограничены enabled roles.
После понижения до maintenance и при запрещённых memberships штатные media
grants могут оказаться невидимыми; корректная установка получила бы ложный HOLD.
В существующем bootstrap verifier вызывается с owner connection.

Окончательная редакция вызывает тот же verifier на ещё owner source в
read-only transaction, затем завершает её, понижает source и проверяет
идентичность. Расширение grants, memberships или изменение verifier не нужно.
Обратимость SET SESSION AUTHORIZATION остаётся уже принятой границей доверенного
оператора; обещание песочницы не вводится.

**R2 — права файла пароля PostgreSQL: конкретизировано до реализации.**
CD `secure_runtime_secret_file` задаёт owner/installation group/mode640 также
owner PostgreSQL secret. У daemon UID/GID70 нет `group_add` этой группы.
Механический перенос требования GRAF group-read на leaf для daemon70 дал бы
ложный отказ или подтолкнул к ненужному изменению прав.

Проект теперь явно различает traversal каталогов proc-root для UID70 и
чтение leaf доверенным root operator, как у начального root entrypoint.
Leaf остаётся защищённым owner/mode600|640/ACL и exact mount inode+bytes;
новых прав файлу не выдаётся. Для GRAF прежняя проверка доступности сохраняется.

Прочитанная окончательная редакция закрывает оба вопроса. Других блокирующих
P1/P2 или противоречий требованиям в этом алгоритме не обнаружено.

## Требуемые проверки реализации

Сначала RED по отсутствующему механизму и конкретным неверным URL/query/role,
IP/network, PG identity/version/schema, полномочиям/memberships, PID/secret
drift и отказу verifier. Отдельно нужны отмена при connect, завершение connect
в гонке с отменой, query и close, повторная отмена родителя и отсутствие
оставшихся принадлежащих backend PID. Не маскировать ошибки DSN/secret выводом.

Native профиль должен использовать существующий
`postgres_isolated_cluster_database_url` с полными migrations и штатным bootstrap
**только собственной** БД, по образцу
`test_full_migrated_database_restore_comparison`. Это позволяет выполнить
настоящий `_verify_runtime_roles` без подмены, успешные owner/reduced/app/media/
maintenance соединения, exact packaged head и отрицательные role/revision/grants.
Fixture и образец прочитаны; сам профиль ревьюер не запускал.

На Mac перенаправление только host/port транспорта на собственный loopback port
нужно раскрыть: оно не является native доказательством маршрута по production
Docker IP. Выбор IP и binding покрываются отдельной причинной матрицей inventory;
существующий Linux-профиль проверяет extraction/FD/ACL и настоящий PG UID/GID.
Нельзя заменять readonly verifier mock-ответом в native положительном случае
и выдавать такой результат за настоящую проверку grants.

Исполнитель сообщил о собственной PG17-пробе UID/GID70 и доступности
`pg_control_system()` у app/maintenance. Эти сведения не перепроверены
ревьюером и не принимаются здесь за приёмку нового кода. Новые grants этим
участком не требуются; ошибку прав реального соединения следует закрыто
отклонять, а не автоматически исправлять.

## Requirements и scoped analyze

Повторно прочитаны все117 действующих вопросов четырёх reviewer-owned списков.
Отметки не изменялись; контрольные суммы прежние:

| Список | Отмечено | Открыто |
| --- | ---: | ---: |
| requirements | 16 | 0 |
| privacy-measurement | 45 | 0 |
| security | 27 | 0 |
| infra | 29 | 0 |
| **Всего** | **117** | **0** |

Это состояние качества требований. Оно не означает выполнение продукта.
Применено разрешённое владельцем исключение повторного чтения F273: хеши
базовых документов/неизменных зависимостей сверены, затронутые полные разделы
spec, plan, tasks, quickstart, operations и activation-milestones перечитаны.
Активный путь подтверждён feature.json и check-prerequisites; физическое имя
worktree не использовано как источник выбора.

Проверены FR-008/025/032/034–038/048–053 и договоры первого локального периода,
принятый full-operator-design, текущий runtime preflight/Settings/identity,
readonly роль-verifier, native inventory и backup metadata verifier.
Алгоритм остаётся внутри существующего T113 и не меняет хранение, получателей,
основания, T0, удаления, replay или правила полного восстановления.
Новых critical/high и P1/P2 после двух уточнений нет: **scoped analyze PASS
только проекта этого участка**. До приёмки кода требуются независимое code review
и доказательства на окончательных байтах.

`HOLD/full_preflight_not_implemented` и `activation_recovery_unverified`
сохраняются. Полные schema/constraints/RLS/ledger/lifecycle проверки, прочие
preflight gates, верхний оператор, T113/#7804/T112, рабочие T0/ready/измерение,
релиз, трафик и продажи не закрыты. Подтверждение UID1003 этим не получено.

## SHA-256 прочитанного снимка

```text
.dev/growth/t113-database-precode-20261030.md
2ce581a1ecb66110f6750cf58231c7e12bfeb8a4cd28c2bb248c5a1f20cd52a6
specs/273-paid-traffic-analytics/validation/t113-full-operator-design-20261030.md
5d1e069f3fe18f31a21c72c9b0abc41614ff8bfc00c3269f27b1f3cb596738ec
apps/server/src/twobrain_rec_server/product_analytics/activation_operator.py
93ed892c7f92c537222d37f1b47d4054b37361e0809913daef8d578492427245
apps/server/tests/unit/test_activation_operator.py
968afb642fd910774653c36276ebf8c91f5b727608d6e83ae5c1bb3c4efd60d9
apps/server/scripts/bootstrap_runtime_database_roles.py
eef89121ad607503d99ab3dd2c70b4bc6cdedb7a3ff551b24850ac91ee78adba
infra/scripts/rec-db-verify.py
9878ffa671eacede35b599fe7a8c6fed0a2c8a75561a8d6d7d7911c13e28ebad
infra/scripts/rec-db-backup-inventory.sql
3638e1d9279656a1864a5229a2210af8812499747108e37d16b33c763a419cdd
specs/273-paid-traffic-analytics/tasks.md
4930e004556d0b9e4eae7c83887fa2f09d543c99e8a44166f138587d29945d6a
checklists/requirements.md
6755318d0b7a76a9f6439446ad42362272d43859cc6f4b3c045b5c36ad1ed9a2
checklists/privacy-measurement.md
8c390000a2da12cf719348d56c08dcb21d886aac98ba1a90ad3d5c41e141cb4f
checklists/security.md
57f082b0b90faf7a3302db0aa1b9aacd29948641e824578ca4f86eee4dee9cb8
checklists/infra.md
998175e297553cedac7f4d7b2829459fcb3f1b650b3b3b6d072e9065437bfa94
```

Короткие checklist пути относятся к `specs/273-paid-traffic-analytics/`.
