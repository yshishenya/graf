# F273/T113: независимое ревью кода совместимости со схемой 0107

Дата: 30.10.2026. Проверяющий: `/root/f273_release_boundary`.
Основа: `6d84bf22afd2104ed83a4ac51d10f09ddfcc636c`, master
`450ff6124c71c54fd5f1b51d42dba64fdbadc35c`, ветка
`codex/f273-local-period-20261029`. T113/#7804, `high-risk-product`.

## Решение

**SCOPED CODE REVIEW PASS. Открытых P1: 0, P2: 0.** Фактический diff
соответствует принятому [проекту](t113-schema-0107-design-review-20261030.md).
Приняты только обновление закреплённых эталонов/числа routines, два точных
триггера миграции0107, профильные тесты и согласующие записи документов.
Это приёмка текущих локальных байтов по контрольным суммам, не проверок
будущего коммита, полного оператора или рабочего включения.

Полностью прочитаны diff, итоговый [отчёт исполнителя](t113-schema-0107-20261030.md),
завершённые unit-red/profile/governance журналы, изменённые unit/native
сценарии и окружающий код каталога/извлечения literal. Перечитаны изменения
plan/tasks/quickstart/owned fragment; исторические результаты0106 сохранены.

## Проверенные свойства реализации

- Закреплены именно независимые native эталоны схемы0107. Проверяющий снова
  пересчитал routines и access из baseline JSON; оба результата равны новым
  исходным константам. Никакого expected из checked source/CLI/env не добавлено.
- Строгий предварительный `count(*)=32 AND bool_and(prokind='f')` сохранён
  перед deparser. Дополнительная/изменённая routine, процедура или aggregate
  не допускаются новым числом. Descriptor, сортировка и проверка digest прежние.
- В `TRIGGERS` добавлены ровно `billing_registry_imports` и
  `billing_registry_gaps`, имя `registry_history_guard`, type27, columns `()`,
  функция `rec_registry_history_guard`, источник `0107_billing_registry`.
  Итого9 точных триггеров,8 уникальных тел. Прежние7 записей не изменены.
- Новый guard попадает в прежнее полное сравнение trigger/function свойств:
  owner/language/body/аргументы/флаги/отношение/deferral/transition и O/A.
  Неподдержанные D/R по-прежнему запрещены; фактический O/A включается в digest.
  `_expected_bodies` и regex не менялись; литерал новой миграции извлекается
  прежним правилом, без исполнения миграции или специального обхода.
- `ACCESS_QUERY` не менялся; его независимо вычисленный SHA-256 без первого
  перевода строки — `45d345f080e38878dce505a0bb036378e04dfbe50c45056958fcdeef45c9b40d`.
  Read-only/PG17/search_path guards, scope/сериализация/OA-нормализация,
  безопасные сообщения отказа и распространение отмены прежние.
- `activation_operator.py` не изменён, SHA-256
  `01c5117741d94135978096575ad834902c93bb0e9324e2f28da7b3c472e448c9`.
  Порядок catalog→access, конечное повторное чтение после yield и RR lifecycle
  не меняются. Миграция0107, bootstrap, полный sequence inventory/verifier и
  финансовые операции этой правкой не затронуты.

| Набор | Число | Пересчитанный SHA-256, совпадает с исходной константой |
|---|---:|---|
| routines | 32 | `7563a8dc31e36bb32b916667b9c404b04c2eba0e79befd6e58a94923b41881ff` |
| access | 578 | `3b469e7bad18fcc4ecaf12d28f9190abbeb043d74451e28abf073cdb696dfd43` |

## Доказательства и границы тестов

Новый unit-код проверяет8 тел до подмены, затем missing/wrong-tag нового
`rec_registry_history_guard` наряду с прежними literal отказами. Native-код
отключает каждый из двух новых триггеров на собственном UUID PG17, требует
именно HOLD каталога, выполняет ENABLE в `finally` и проверяет исходный digest
после каждого undo. Нет подмены reader/SQL/expected ради успеха.

Предварительный RED — **9 failed / 4 passed**: все9 literal-сценариев
останавливались на `7 != 8`, до выполнения mutation. Это доказывает отсутствие
нового тела в прежнем коде, но не отдельную причинность каждой mutation;
последующая успешная проверка проходит сами сценарии. RED не выдаётся за PASS.
Runner завершился `container_not_started`, что соответствует unit-only пути.

Окончательный профиль — **362 passed / 37 skipped / 2 warnings,150.26 s**,
399 collected, collection digest
`3bcab7f67e17c973f67abb035698859263b934f529de865fd161c71d269a07c6`.
В журнале есть phase PASS, `isolated_container_removed` и итог runner PASS.
Не приняты промежуточный вывод или незавершённая очистка.

Профиль включает текущие unit retention/operator/replay, оба native каталога,
access reader, runtime cases и пять backup/lifecycle/replay потребителей.
Прежние unknown function/procedure/aggregate, роли/права, ACL/зависимости,
отмена/закрытие соединений, rollback и O/A случаи сохраняются. Native coherent
copy+restore success проходит на принятой0107 с двумя sequence: verifier
требует точный полный набор `sequence_state` и сравнивает source/restore state;
исключение состояний применяется только к отдельному schema-only сравнению.
Проверка закрытого источника и actual lifecycle/four-category postconditions
остаются в существующих сценариях и присутствуют в успешном профиле.

37 Linux root/proc/memfd/FD/ACL пропусков не считаются Linux PASS. Предупреждения
относятся к прежнему pytest plugin import и Starlette/httpx. В governance log
прочитано `spec-kit-governance: OK (bootstrap integrity + GRAF invariants)`.
Ruff/development-process/fragments/whitespace и73 локальные ссылки указаны
исполнителем; проверяющий эти команды повторно не запускал и не подменяет
их своим независимым тестовым прогоном.

| Журнал `.dev/growth/` | SHA-256 |
|---|---|
| t113-schema-0107-unit-red-20261030.log | `8dde5df28fe5be069aaad60102900421ac877bf316d46bfb4648c0c9feb6dc9c` |
| t113-schema-0107-profile-20261030.log | `15306bebb8dcb3178ef9db94f3b598cc460be041c1e6c6420055c172f57eee7c` |
| t113-schema-0107-governance-20261030.log | `59cfeb588ee423427af9f09c0dfe4d3d2b36bbfcca7bbb8b49ba0f0b1ce6bceb` |

## 117 вопросов и контрольные суммы

Все117 действующих вопросов независимо перечитаны вновь; требований нового
основания/получателя/хранения/удаления правка не создаёт. Итог **117 `[x]` /
0 `[ ]`**, без изменения отметок. Это качество требований, не завершение фичи.
Применимые spec/constitution/operations/data-model и прочие требования
сохраняют подтверждённые в предыдущем design review хеши; текущие добавления
plan/tasks/quickstart согласуют только0107 и сохраняют открытые рабочие ворота.

| Список | Отмечено / не отмечено | SHA-256 |
|---|---:|---|
| requirements | 16 / 0 | `6755318d0b7a76a9f6439446ad42362272d43859cc6f4b3c045b5c36ad1ed9a2` |
| privacy-measurement | 45 / 0 | `8c390000a2da12cf719348d56c08dcb21d886aac98ba1a90ad3d5c41e141cb4f` |
| security | 27 / 0 | `57f082b0b90faf7a3302db0aa1b9aacd29948641e824578ca4f86eee4dee9cb8` |
| infra | 29 / 0 | `998175e297553cedac7f4d7b2829459fcb3f1b650b3b3b6d072e9065437bfa94` |

Независимо проверен весь inventory
`.dev/growth/t113-schema-0107-final-hashes-20261030.json`: **22/22 совпали**,
SHA-256 `f8e7c99fbe07537ee48ebbd20616e6a6b1bb71d4a0e0238d3b046c4d591bc369`.
Он включает native JSON/probe/logs/precode, миграцию/verifier/inventory,
неизменённый operator, все изменённые исходники/тесты/документы и design report.

| Изменённый файл | SHA-256 |
|---|---|
| local_retention.py | `a9e50827c463800957738ba0192b6fe9d4c38f5c9c3541428ee5a6b89b0661b6` |
| unit/test_local_retention.py | `c270ca902165158f5ceeab96a8333ac13a6ccbd938c96f7f065a5a8cfbb3c8d1` |
| integration/test_local_retention.py | `549f1af138918ce16205e783f7c16a2847c0c2f57b21b88ba50225f049b632ec` |
| plan.md | `9b8ebcff5e509e1e98a82a0087a276eacff5040a6689e44abdddeb592f1a3207` |
| tasks.md | `d46ace121320f2162eb6b251905b6365af58657793f7d092b8df4aa37c213ed1` |
| quickstart.md | `dd064e738e538a789228304f90c6b2a92e56500e1ffe032fbaa2ad50938c8fb6` |
| changes/unreleased/F273.yaml | `e42d5d9232138484cbb709e077c277074302cc6e53136b109db6357410f53367` |

## Сохранённые ограничения

`full_preflight_not_implemented` и `activation_recovery_unverified` остаются.
T113/#7804/T112, установленное обслуживание, верхние операции/actual
restore/resume/shell/CD/rollback/daily, рабочие T0/ready/IP, аналитика,
выпуск и AC01–AC06 не приняты этим scoped PASS. Новому коммиту нужны отдельные
проверки его полного SHA; местные журналы не заменяют GitHub CI/Full/сервер.

Проверяющий не запускал тесты/БД/процессы и изменил только этот отчёт, не
трогая source/spec/plan/tasks/checklists/Git/GitHub/Dev/сервер. После записи
отчёт целиком перечитан, хеши входов и117/0 повторно сверены.
