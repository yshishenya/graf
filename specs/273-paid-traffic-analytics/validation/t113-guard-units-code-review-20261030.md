# F273/T113: независимое ревью guard-unit reader

Дата: 30.10.2026. Проверяющий `/root/f273_release_boundary`.
Ветка `codex/f273-local-period-20261029`, основа
`47064a603994bffc889643f1794f44aa51ef2b05`, T113/#7804.
Путь проверки: `high-risk-product`, существующий Spec Kit.

## Решение

**SCOPED CODE REVIEW PASS. Открытых P1: 0, P2: 0.**
Блокирующих дефектов в проверенном ограниченном reader не найдено.
Приняты исходный код и доказательства сверки двух существующих guard units;
полные installed jobs, работающая установка, ready/T0 и T113 не приняты.

Полностью прочитаны diff девяти отслеживаемых файлов, новый reader и его
интеграция с окружающим кодом, оба изменённых теста,
[конечный отчёт исполнителя](t113-guard-units-20261030.md) и
[проектное заключение](t113-guard-units-design-review-20261030.md).
Последнее соответствует SHA-256
`51b52e6bbd01cea90b8d8e6e210d448a7784460347558365c2bfc0b877920612`.
Конечный precode имеет SHA-256
`8b65a6d28fd1144bfd89fcba34a70443b987014444977d5c0ff2893af76bbefc`.

## Проверка реализации против проекта

- `_runtime_guard_units` открывает ровно два фиксированных installed файла
  no-follow/nonblocking read-only FD и удерживает их в ExitStack. Проверяет
  root:root0644, regular/single-link/размер1–65536, отсутствие ACL, безопасные
  root-owned ancestors, identity FD/path и actual bytes против snapshot.
  Эти проверки повторяются до/после каждого property await и при выходе.
  Замена пути или каталога не принимается как тот же удержанный файл.
- Вызывается только фиксированный `/usr/bin/busctl --json=short --system
  get-property` с systemd1, двумя canonical object paths и заданными
  интерфейсами/свойствами. Общий `_command` и его deadline/reap ownership
  сохранены. Непустой DBUS_SYSTEM_BUS_ADDRESS запрещён до/после await.
  Shell, remote/address overrides, install/start/reload/enable отсутствуют.
- `_object` сохраняет отказ на duplicate keys. Требуются ровно type/data и
  точный signature; ответ ограничен65536bytes. Для фиксированных значений
  сравнивается канонический JSON digest: это различает bool/int, int/float,
  строки, массивы и вложенные структуры, где обычное Python equality могло
  бы принять1 заTrue. Динамические числа отдельно требуют `type(v) is int`.
- Source equality не заменяет loaded properties. Проверяются canonical
  Id/Names/FragmentPath, loaded/static/enabled, no SourcePath/dropins/reload/
  transient и допустимые active/sub пары. Некорректные состояния не дают успеха.
- Timer проверяет ровно OnBootUSec120000000 и OnUnitActiveUSec60000000,
  пустой calendar, AccuracyUSec1000000, нулевой random delay и все остальные
  precode boolean ограничения. Next-elapse значения неотрицательны и исключены
  из стабильного отпечатка. В source timer добавлена только AccuracySec=1s;
  частота и предел freshness0≤age<120с не менялись.
- Service проверяет обе формы ExecStart/ExecStartEx: одна запись, прежние
  path/argv, ignore-failure=false и **flags=[] строго list**, семь history
  значений — int, не bool. Дополнительные commands/env/mounts запрещены;
  root/oneshot/env-file/sandbox/write-path ограничения соответствуют precode.
  История исполнения, PID и timestamps не участвуют в digest и не выводятся.
- Effective конфигурация перечитывается после yield, digest сравнивается.
  Разрешённые переходы состояния перепроверяются, а нормальные tick/history
  и перестановка тех же ReadWritePaths не создают ложный config drift.
  Контекст guard расположен снаружи DB context, включая выход из DB и все
  последующие ожидания. После их выходов успех может вернуть только функция,
  прошедшая все проверки. Runtime fingerprint добавляет guard_units_sha256,
  не raw units/argv/env/history; прежние access/config digests сохранены.

Исключение, deadline, повторная отмена или обнаруженный drift не создают
успешного результата. Новых служб, зависимостей, прав, supplied PASS и обходов
общих HOLD нет. Чтение критических свойств не обещает защиты от произвольных
параллельных действий trusted root вне исходного договора.

## Доказательства и привязка к файлам

Независимо пересчитан весь frozen inventory
`.dev/growth/t113-guard-units-inventory-20261030.json`: **25/25 совпадают**.
SHA-256 самого inventory:
`d5470506d35ec8dd4ba5d1b3881f21651294361056f854fc06b5270b4d0e85a1`.

Ключевые конечные хеши:

| Файл | SHA-256 |
| --- | --- |
| activation_operator.py |`f7f8980ad7dd6a2530eebba4cd103c0a09cf130193bfad2230dd2e6f634af678`|
| unit/test_activation_operator.py |`9481867cac06e14d19d3370b4ea62e8f2aad78a6e674679dc8bbbc6e3a49bfbb`|
| contract/test_analytics_degradation_alerting.py |`3a16562530586a55581d2fb77ce754072b35ca8a04b8d31224c5d60bf007a85b`|
| guard.timer |`f173c4552cf84a9a1c245d6e8c30f7ba709011aea9fc4ae1e5d9f710bac04c7c`|
| guard.service, без изменений |`677b6d6612e135d0339e0a7286386f9c1846fefaccb6ecf6419ca6c5c47782d0`|

Сохранённые журналы прочитаны полностью:

| Профиль | Подтверждённый результат |
| --- | --- |
| Конечный unit operator на Mac |287 PASS,96 Linux SKIP,2 прежних предупреждения,2,55с.|
| Конечные полные contracts alerting/retention |222 PASS,2 прежних предупреждения,79,31с.|
| Новые Linux root guard cases |59 PASS,0 SKIP,0,60с; tracked test SHA совпадает с конечным.|
| Linux full bound-files/settings/runtime |167 PASS,0 SKIP,1,05с; включает59 новых, результаты не складываются.|
| Сохранённый общий Mac профиль |509 PASS,96 SKIP,83,87с; перекрывает раздельные unit/contracts, не добавляется к ним.|
| Native source verify |systemd259, exit0; временные конечные source units, без установки/загрузки/запуска.|
| Governance/process |Сохранённые журналы подтверждают governance, agent-context, fragments и development-process.|

Независимый `git diff --check` успешен. Локальные Markdown-ссылки в изменённых
plan/tasks/quickstart и обоих отчётах проверены чтением путей, ошибок нет.
Ruff PASS указан исполнителем; отдельного Ruff-журнала в frozen inventory нет,
поэтому независимый запуск Ruff этим отчётом не заявляется.

Причинный RED подтверждён тремя отдельными журналами: contract отказал именно
на отсутствующем AccuracySec, Linux good — на отсутствии нового helper,
runtime integration good — на входе DB без активного guard context.
RED относится к тогдашним тестовым bytes: Linux RED хеш
`c0835e2abe8acf4d77104ce86424b9a9a2d47a772f042878aba62cfe9e32d6b0`
отличается от конечного, что отражено в отчёте исполнителя. RED не приписан
конечному файлу. Исправление первой ACL попытки58 PASS/1 FAIL описано
исполнителем; этот неуспешный журнал в inventory не представлен и не используется
как самостоятельное доказательство. Конечные actual POSIX ACL cases прошли.

Три Linux runner прочитаны целиком. Существующий образ
`sha256:37d27de327e5876b4c890a7e6c3dd98ab8fd89476180d6deb42d262411c1ccbe`,
`--pull=never --network none --read-only --rm`, source/tests/deps RO,
собственный одноразовый volume, без Docker socket и приложения; временные
pytest modules находятся в TemporaryDirectory. Успех требует реально
выполненных тестов и отсутствия skips. Хеш полного runner:
`c48e2e5cc672f17b156f9d795538783cefe65f0530551ece8104bfd90f691650`.
Reviewer runner не запускал.

Cancellation case ожидает property await, где через исходный `_command`
запущен настоящий собственный child. Тест ждёт его PID, убеждается, что yield
ещё не достигнут, отменяет дважды, требует CancelledError и ProcessLookupError
для завершённого PID. FD count после сценария совпадает с исходным.
Это проверяет реальное владение/reap child внутри property wait;
это **не** native зависший D-Bus запрос и не installed proof systemd.

Native verify сохраняет сторонние предупреждения xfs units о CPUAccounting
и недоступном hermes unit. Exit0 не выдан за полную проверку всех system units;
ошибок временных guard units в журнале нет. D-Bus signatures наблюдались до кода
на безопасных дистрибутивных units. Полный PG-профиль прежнего этапа не
приписывается этому diff: DB SQL/reader не менялись, новая внешняя связь
контекстов проверена unit/integration fake, без утверждения о рабочем PG.

## Контрольные списки и повторное чтение

Все117 вопросов перечитаны в этом code review, отметки не менялись.
Они подтверждают качество требований и не превращаются в installed acceptance.

| Список | Checked | Unchecked | SHA-256 |
| --- | ---: | ---: | --- |
| requirements |16|0|`6755318d0b7a76a9f6439446ad42362272d43859cc6f4b3c045b5c36ad1ed9a2`|
| privacy-measurement |45|0|`8c390000a2da12cf719348d56c08dcb21d886aac98ba1a90ad3d5c41e141cb4f`|
| security |27|0|`57f082b0b90faf7a3302db0aa1b9aacd29948641e824578ca4f86eee4dee9cb8`|
| infra |29|0|`998175e297553cedac7f4d7b2829459fcb3f1b650b3b3b6d072e9065437bfa94`|
| Итого |117|0|Отметки совпали с проектным этапом.|

Применимые требования и полные затронутые зависимости перечитаны при проектном
ревью. Хеши constitution/PRD/current status/product-gates/spec/operations/
data-model повторно совпали. Применено разрешённое исключение F273 для
повторного чтения неизменного baseline; полное чтение600КБ истории не заявляется.

## Открытые границы

`full_preflight_not_implemented`, `activation_recovery_unverified` и отдельный
остаток `posthog_containers_missing` сохранены. Полный host/cron/purge/retention
каталог, shell graf-local, local_only resource policy, верхние
initial/backup/verify/actual-restore/resume, CD/rollback/daily, working T0/ready,
аналитика/IP/получатели, exact-SHA CI/Full/release, T112/T113/#7804 и
коммерческие AC01–AC06 остаются открытыми. Трафик и продажи не доказаны.

Reviewer изменил только этот отчёт; source/spec/plan/tasks/governance/Git/
GitHub/checklist marks не менялись. SSH/DB/Docker/tests/Dev/production не
запускались. После записи отчёт перечитан целиком, inventory и117/0 пересчитаны.
