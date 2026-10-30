# F273/T113: независимое ревью кода соединений с БД

30.10.2026, `/root/f273_release_boundary`, база
`5501d2ba65ae7d383c511b46bba8ce0a002b0cbb`, T113/#7804,
полоса `high-risk-product`.

**Текущий результат: HOLD. P1: 0; P2: 1.**

Проверены полный diff трёх файлов, фактические вызывающие контексты,
принятый проект `2ce581a1ecb66110f6750cf58231c7e12bfeb8a4cd28c2bb248c5a1f20cd52a6`,
журналы и сценарии дополнительных Linux-проб. Ревьюер не запускал тесты,
SQL, Docker, SSH, сборки, Dev или production; изменён только этот отчёт.
Изменения других участников сохранены. Исполнитель сообщил о своей отдельной
найденной гонке connect_error/cancellation и готовит исправление; новые байты
после такого изменения и их доказательства требуют повторного ревью.

## P2-01: успех возможен после истечения общего deadline при закрытии БД

`_runtime_databases` открывает `AsyncExitStack` **до** `asyncio.timeout_at(deadline)`.
При выходе timeout завершается первым, а оба `_physical_connection.close(timeout=3)`
выполняются затем, вне общего deadline, с сохранением владения. Это правильно
для обязательного cleanup, но нет проверки истечения срока после такого cleanup.

`_runtime_preflight` проверяет monotonic < deadline и готовит `return
runtime=verified` **внутри** DB-контекста (в рассматриваемой редакции строки
2504–2510). Далее выполняются финальный `_database_identity`, выход timeout,
close source/owner и проверки файлов при выходе ExitStack. Если проверки
закончили до deadline, а штатное закрытие одного соединения пересекло его,
исключения не будет: уже подготовленный verified возвращается после срока.
Внешний bootstrap имеет другой предел35с; превышение внутренних30с на1–2с
он тоже может принять. Это не обход unconditional HOLD и не утечка данных,
а нарушение принятого конечного срока и правила отсутствия успеха после него.

Принятый full-operator-design явно оставляет cleanup возможность длиться
дольше ради владения ресурсами, но запрещает успех после исчерпания срока;
database precode сохраняет общий существующий30с, без продления бюджета.

Минимальное исправление: завершить оба DB и файловые контексты, затем перед
окончательным return проверить исходный deadline. Достаточно сохранить результат
в локальной переменной вместо внутреннего return и выполнить одну завершающую
проверку после cleanup. Не ограничивать cleanup принудительным выходом, не
отпускать ресурсы раньше и не добавлять новый timeout/retry budget.

Нужен причинный тест: все проверки успевают, успешный close/выход контекста
переводит monotonic за исходный deadline; cleanup подтверждён, результат —
конечный HOLD, verified отсутствует. Положительный случай до срока сохраняется.
Этот тест можно сделать без задержки, управляя часами/событием закрытия.

## Остальной рассмотренный код

- Закрытые service URL проверяются до connect: exact driver, rec-postgres:5432,
  canonical DB, ожидаемая роль, непустой password, отсутствие query и полный
  обязательный набор writers. IP приходит из двух согласованных actual Docker
  network views, а не из DNS, host environment или нового CLI endpoint.
- PostgreSQL PID проверяется четырьмя UID/GID70, mapping/starttime/groups;
  прежние значения100/101 для GRAF сохранены. Owner Env имеет exact user/DB/file,
  дубликаты и пароль непосредственно в Env отвергаются.
- Общий `_bound_runtime_file` сохраняет source/ancestor/ACL/no-follow/single-link/
  mode/size/inode/bytes и проверку через настоящий proc-root. Для GRAF сохраняется
  group-read/optional placeholder; owner leaf читает доверенный root, без
  требования daemon70 group-read и без изменения прав. Проверки при успешном
  выходе обоих потребителей и FD cleanup сохранены.
- Source сначала выполняет настоящий existing readonly verifier и exact packaged
  head под owner в read-only transaction. Затем transaction завершается,
  SESSION AUTHORIZATION понижается до maintenance и row_security=on, после чего
  `_database_identity` проверяет source/owner. Прежняя ловушка information_schema
  видимости устранена. `_bootstrap` в продуктовом операторе не вызывается.
- Настоящие подключения каждого URL проверяют DB/OID/cluster/revision,
  session/current roles, login, опасные атрибуты и memberships. Owner/source
  удерживаются до последней runtime сверки. PG major17 и единственный actual
  Alembic head сравниваются с пакетным. Это не полный schema/ledger inventory.
- Connect имеет отдельный bounded task и shield; успешный поздний результат
  при отмене становится принадлежащим connection и закрывается. Close использует
  `_settled_sql` и terminate fallback. Ошибка не печатает DSN/secret.
  Указанная исполнителем гонка извлечения уже завершившегося failed task
  отдельно требует финальной проверки после его исправления.
- Внешний successful runtime ответ остаётся ровно из четырёх полей. Только
  aggregate runtime digest включает закрытые database/owner secret proofs.
  Новый source код не добавляет DDL/DML/grants/stop/revoke/T0/ready/restore,
  зависимости, framework или фичу. Общий bootstrap по-прежнему возвращает
  `HOLD/full_preflight_not_implemented`; recovery blocker сохранён.

Иных конкретных P1/P2 в прочитанной реализации не обнаружено. Неопределённые
рабочие права/UID1003 и весь полный оператор не повышаются до приёмки этим срезом.

## Прочитанные доказательства и пределы

Исходный итоговый профиль: **468 passed, 6 skipped, 2 warnings**.
Прочитанный общий native журнал: **23 passed, 2 warnings**, включая шесть новых
настоящих случаев на полной migrated собственной PostgreSQL со штатным
подготовительным bootstrap: good, wrong revision, лишний media DELETE,
фактический owner вместо app, membership, повторная отмена настоящего pg_sleep.
Существующий readonly verifier не подменяется. После случаев проверяется0
операторских backend PID. На Mac подменён только транспорт host/port на свой
loopback; это не доказательство рабочего Docker bridge маршрута.

Linux extraction: **38 passed**, четыре точных тела прежних GRAF Settings тестов
из tracked unit-файла, настоящие ancestry/ACL/memfd/FD на своём Linux-томе.
Сценарий прочитан; используется candidate source через PYTHONPATH. JSON содержит
хеш tracked tests, но не отдельный operator hash; это не самостоятельное
доказательство установленных неизменяемых байтов или всего runtime preflight.

Дополнительный owner bind сценарий и окончательный JSON прочитаны целиком:
настоящий собственный PostgreSQL17 UID/GID70, Linux-том, exact RO file bind.
Проверяющий контейнер входит в тот же собственный PID namespace, поэтому PID1
обозначает тот же PostgreSQL процесс; выдан SYS_PTRACE для proc-root. Проверяются
настоящие `_runtime_owner_password`, `_process_identity`, `_settings_destination`
и `_bound_runtime_file`, без подмены этих функций. Подтверждены положительный
mode640 root:1001 при daemon70/group70, отказ при замене source inode с прежним
bind и отказ traversal после chmod700 собственного `/run/secrets`.

Этот пробел доказательства owner wrapper теперь закрыт для механизма actual
proc-root bind. Проба не проверяет весь Compose policy, host PID namespace,
установленный неизменяемый оператор или рабочую установку. Candidate source
подключён через PYTHONPATH; JSON сам не записывает operator hash. Ошибочный
первый запуск без `--interactive` потерял stdin, его exit1/пустой stdout не
считаются причинным продуктовым RED. Артефакт сообщает удаление собственных
ресурсов/production_touched=false; ревьюер инвентаризацию Docker не выполнял.

468/38/23 относятся к прочитанным исходным байтам ниже. Изменения unit-файла,
которые начались во время завершения ревью для connect_error, этим старым
профилем не принимаются. Повторные окончательные хеши и результаты потребуются.

## Требования и scoped analyze

Все117 действующих вопросов перечитаны; отметки не менялись:
requirements16/0, privacy-measurement45/0, security27/0, infra29/0,
**всего117 отмечено /0 открыто**. Хеши списков прежние. Это качество требований,
а не выполненные продуктовые проверки. Неизменность baseline/spec/plan/tasks/
quickstart/contracts проверена хешами по разрешённому исключению F273.

Алгоритм соответствует принятому проекту по endpoint/roles/secret/понижению;
scoped analyze реализации — **HOLD по P2-01**. Требование соблюдения общего
deadline уже принято; нового уточнения владельца или изменения требований
для исправления не нужно. Полные T113/T112/AC01–AC06, schema/constraints/RLS/
ledger/lifecycle, остальные preflight gates, верхние операции, рабочая
аналитика, выпуск, трафик и продажи этим отчётом не принимаются.

## SHA-256 первоначального снимка ревью

```text
apps/server/src/twobrain_rec_server/product_analytics/activation_operator.py
0c9f6c5bd6bd03f02069439574304e9a2a80df45f7230b63da71d60adfd11748
apps/server/tests/unit/test_activation_operator.py
ab1bf12b69bd6dd7048fbab83317bd0643e5424cc730769a55349ef96332d18c
apps/server/tests/integration/test_activation_product_drain.py
71265a9098abdeb64e31e21b6f8a998cffb7e53c9b9d1682c8b4a85b09c07f84
.dev/growth/t113-database-precode-20261030.md
2ce581a1ecb66110f6750cf58231c7e12bfeb8a4cd28c2bb248c5a1f20cd52a6
.dev/growth/t113-database-profile-20261030.log
db9ea5ddbd9266d62faa4bceb333de9ce1da1fabc0e748d6efa129a27d6f44b8
.dev/growth/t113-database-full-native-20261030.log
dc2376f65ed316974eefec0110f5be12e19e49a4b762acb7577c6ed07f621c49
.dev/growth/t113-database-linux-20261030.json
446d223640dff4ebc55c0b04e69209a310acdc789006204da0dfde7718df88fb
.dev/growth/t113-settings-native-20261030.py
01a3000750fbc88020224073877fb3dcd6fc9a8292f42014aed0dd03054a75fb
.dev/growth/t113-database-owner-bind-native-20261030.py
88a27d7190a072d540babaf18b3eeaf79d2edd79326ff68bd78b6e77ac2b3f69
.dev/growth/t113-database-owner-bind-native-20261030.json
039fc8a51badfdefb44df9ffdfe9f53e5cafd4a57a885f82bbb2dfae0a74c928
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
