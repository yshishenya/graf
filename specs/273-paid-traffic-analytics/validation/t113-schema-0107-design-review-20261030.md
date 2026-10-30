# F273/T113: независимый проектный гейт совместимости со схемой 0107

Дата: 30.10.2026. Проверяющий: `/root/f273_release_boundary`.
Рабочая копия: `growth-guide-previews/crisp`, ветка
`codex/f273-local-period-20261029`. Проверяемый HEAD:
`6d84bf22afd2104ed83a4ac51d10f09ddfcc636c`, после переноса на принятый master
`450ff6124c71c54fd5f1b51d42dba64fdbadc35c`. F273, T113/#7804,
`high-risk-product`. Это этап до изменения reader, не приёмка реализации.

## Решение

**SCOPED DESIGN / ANALYZE PASS: CRITICAL 0, HIGH 0; открытых P1 0, P2 0.**
Качество требований: **117 `[x]` / 0 `[ ]`**. Разрешён только минимальный
проект обновления закреплённых эталонов на принятую миграцию
`0107_billing_registry`, добавления её двух точных пользовательских триггеров
в прежний `TRIGGERS` и соответствующих профильных проверок. Код ещё содержит
эталоны 0106 и правильно возвращает HOLD на чистой 0107.

Принятый precode SHA-256:
`63c4ff1733d8941a40fbac63d4a9b75fd6b189fcab134bed3370d6a17ed0826e`.
Нового решения о целях, данных, получателях, хранении или оплате не требуется.
Финансовый импорт, CSV/API, операции оплаты, миграция 0107, её откат и схема
из этого участка не меняются. Общие рабочие ограничения сохраняются.

## Независимо проверенное происхождение эталонов

Полностью прочитаны precode, probe, миграция 0107 и конечный repeat log;
прочитаны источник чистого UUID PG17 fixture и штатный bootstrap, действующие
reader/parser и профильные unit/native тесты. Probe сначала получает свою
схему штатными миграциями до head, затем выполняет стандартный bootstrap на
своём loopback UUID-кластере. Пароли создаются временно и не входят в proof.
Источник, аргумент CLI или рабочая БД не задают expected.

Проверяющий независимо пересчитал SHA-256 из native-baseline JSON по принятой
канонизации `json.dumps(rows, sort_keys=True)`:

| Набор | Число | Пересчитанный SHA-256 |
|---|---:|---|
| routines | 32 | `7563a8dc31e36bb32b916667b9c404b04c2eba0e79befd6e58a94923b41881ff` |
| access | 578 | `3b469e7bad18fcc4ecaf12d28f9190abbeb043d74451e28abf073cdb696dfd43` |

Оба совпали с полями JSON и завершёнными журналами. Сравнение со старыми
проверенными наборами установило: ни одна из прежних 31 routines или 575
access records не исчезла и не изменилась. Добавлена ровно одна функция
`public.rec_registry_history_guard()`, а в access — ровно три записи:
ACL этой функции и две политики `registry_maintenance` для
`billing_registry_imports` / `billing_registry_gaps`. Политики содержат
тот же maintenance/current_user/row_security/context/operation/feature-area
predicate, который создаёт миграция. Других добавлений descriptor нет.

Конечные количества access-разделов: ACL115, column63, constraint30,
database1, edge141, index15, language4, membership3, policy173, role4,
role_settings3, table4, toast4, trigger9, type8, unsupported1. Четыре локальные
аналитические таблицы, их корни/связи и scope фиксированного запроса прежние.
Глобальный exact catalog пользовательских триггеров проверяется отдельно.

Конечный повтор сообщает `independent_native_schema_0107_repeat=pass`,
revision `0107_billing_registry`, те же 32/578, owner→maintenance equality,
два новых type27 triggers и `owned_native_cluster_cleanup=pass`. Его probe
проверяет равенство всего proof прежнему JSON после JSON roundtrip; изменение
канонизации list/tuple в исследовательской probe не меняет приложение.
Неуспешный первый repeat с `AssertionError` сохранён и не считается PASS.
В начальном и конечном успешном журнале оба старых reader дают HOLD.

## Две записи триггеров и граница минимального изменения

В миграции точно два `BEFORE UPDATE OR DELETE ... FOR EACH ROW` триггера:

| Таблица | Имя | Тип | Столбцы | Функция | Миграция |
|---|---|---:|---|---|---|
| billing_registry_imports | registry_history_guard | 27 | `()` | rec_registry_history_guard | 0107_billing_registry |
| billing_registry_gaps | registry_history_guard | 27 | `()` | rec_registry_history_guard | 0107_billing_registry |

27 соответствует ROW + BEFORE + UPDATE + DELETE. В чистом каталоге обе
записи имеют состояние O и одинаковое тело функции. Проверяющий независимо
прочитал AST миграции и применил прежний точный literal regex: внутри
единственного `upgrade` найден ровно один подходящий literal функции;
его тело побайтово равно обоим `prosrc` в native JSON. Расширять parser,
добавлять специальный обход для новой миграции или выполнять миграцию ради
извлечения тела не нужно. Уникальных ожидаемых тел будет восемь.

Допускаются только новый routines digest и точное число32, две записи выше,
новый access digest и соответствующее обозначение принятой схемы. Сам
`ACCESS_QUERY` остаётся прежним SHA-256
`45d345f080e38878dce505a0bb036378e04dfbe50c45056958fcdeef45c9b40d`.
Его guard, scope, сериализация, O/A-нормализация, прежние проверки неизвестных
kind/routine/ACL/DDL и оба callers не меняются. Семь прежних trigger checks
сохраняются с теми же точными свойствами; два новых получают те же полные
проверки, включая body, owner, language, args, flags и O/A binding.

## Зависимость полного backup/restore от sequence inventory

0107 создаёт две BIGINT primary-key последовательности. Прочитаны принятые
из master inventory/verifier: `sequence_state` имеет exact поля и уникальный
ключ `(schema,name)`; набор обязан точно совпасть со всеми relation типа S,
`last_value` должен быть int, `is_called` — bool. Полное сравнение source и
восстановленной цели включает этот набор и его значения. Только сравнение
со schema-only эталоном исключает state вместе с count/revision/activation
state. Источник и restored данные этим исключением не освобождаются.

Inventory прямо указывает, что sequence state не MVCC: расхождение между
pg_dump и inventory должно привести к отказу полного сравнения, а не к
обещанию согласованного snapshot. Контроль product drain и quiet source
остаётся прежним. Этот этап не меняет upstream sequence verifier и не
доказывает его рабочую приёмку. После реализации обязательны прежние native
coherent copy+restore и lifecycle/four-category потребители на head0107.

## Scoped analyze

Использован `speckit-analyze`: текущие prerequisites подтвердили F273,
spec/plan/tasks существуют. Применён поддержанный установленным скриптом
вариант `--json --require-tasks --include-tasks`; неподдержанный
`--require-spec` из шаблона повторно не запускался. В before/after_analyze
только выключенные auto-commit hooks; изменяющие состояние hooks не выполнялись.

| Требование | Покрытие | Вывод этого этапа |
|---|---|---|
| FR-025, SC-006 | T113 | Durable admission/общие fences не меняются; новый schema head не разрешает неизвестный каталог. |
| FR-034/035/053 | T113, полная GRAF DB копия/restore | Актуальный clean baseline и sequence state сохраняют полный источник/restore договор; native приёмка ещё обязательна. |
| FR-036/050 | T113, local retention | `until_decision`, отдельное удаление и отсутствие age purge прежние; источник не может прислать expected/PASS. |
| FR-048 | T113, lifecycle/replay | Фактические удаления и повтор после restore не заменены catalog digest. |
| FR-038 | T113, repository/runtime binding | Принятая схема0107 должна связываться с закреплённым кодом, guards/callers прежние. |
| Конституция III/IV/VI | high-risk-product | Metadata-only proof, lifecycle и независимые before-code ворота сохранены; конфликтов нет. |

Применимых FR в этой матрице8, все покрыты существующей T113: 8/8.
Новых задач без требования, противоречий, дублирования или неопределённостей
этого scoped проекта не найдено. CRITICAL0/HIGH0; прежние открытые рабочие
ворота и бизнес-показатели не объявлены пробелом качества требований и не
объявлены выполненными. Это не глобальный повторный analyze PASS всей фичи.

## Контрольные списки и повторное чтение

Повторно прочитаны все действующие117 вопросов; отметки не менялись.
Применимые границы каждой группы сохраняются: качество/измеримость spec,
основания и запреты данных/получателей, retention/отдельное удаление,
backup/restore и его пределы, ресурсы/отказы, допуск и независимый выпуск.
Новая миграция является зависимостью исполнения, а не новым пользовательским
договором или изменением ответов на эти вопросы.

| Список | Отмечено | Не отмечено | SHA-256 |
|---|---:|---:|---|
| requirements | 16 | 0 | `6755318d0b7a76a9f6439446ad42362272d43859cc6f4b3c045b5c36ad1ed9a2` |
| privacy-measurement | 45 | 0 | `8c390000a2da12cf719348d56c08dcb21d886aac98ba1a90ad3d5c41e141cb4f` |
| security | 27 | 0 | `57f082b0b90faf7a3302db0aa1b9aacd29948641e824578ca4f86eee4dee9cb8` |
| infra | 29 | 0 | `998175e297553cedac7f4d7b2829459fcb3f1b650b3b3b6d072e9065437bfa94` |

Заново прочитаны конституция, применимые полные разделы spec/plan/tasks,
guidance index, document-reading, spec-kit-flow, development-process,
product-gates, новая миграция, sequence inventory/verifier и новые зависимости.
По разрешённому владельцем исключению F273 остальные ранее прочитанные
неизменные документы сверены по SHA: PRD/current status, spec/plan,
operations/data-model и quickstart совпали с предыдущим review snapshot.
Хеши constitution/spec/plan/operations/data-model перечислены в
[предыдущем design review](t113-access-design-review-20261030.md);
tasks/quickstart — в [конечном code review](t113-access-code-review-20261030.md).
Хеши соответствуют действующим байтам после rebase, не только прежнему SHA.

## Контрольные суммы новых источников

| Источник | SHA-256 |
|---|---|
| probe-schema-0107-20261030.py | `355cb80f025f9830a917e90280df6f991a55483f8cad83f002150add7e5b0b01` |
| t113-schema-0107-native-baseline-20261030.json | `a2d390a1e814ab4d51a4ee817927b228f699559609b58adcd5bd3a72738fd990` |
| t113-schema-0107-native-20261030.log | `8f4fecc925e24025612701712e29ae679f731ac682e4e1a4c6a250297ef80027` |
| t113-schema-0107-native-repeat-20261030.log, неуспешный | `21fe9edf97f1232569dbd4c5e5e6d90040a36121a22191533fabdf19ec198f81` |
| t113-schema-0107-native-repeat-final-20261030.log | `5b1dc035579c91b238e09397d4fbe9feef4b8f82b17c22fd139004380597362c` |
| 0107_billing_registry.py | `e8ff8a51ac0acb519f9fd3608e6a481b0b41dde5557107a3d3efbeec766eb614` |
| infra/scripts/rec-db-backup-inventory.sql | `d9e761add12c8504b55624d72c286b2eb3dafd981afa99a01ffe2107d92e0295` |
| infra/scripts/rec-db-verify.py | `9867255f6bf350b1b5222c4f247613ccf184e64002f753c49de31dc59fc58548` |
| local_retention.py, ещё0106 | `600658bdef8dfe5a7c243994647ee84727de26b48099559a008b215a1be249c9` |
| unit/test_local_retention.py, до изменения | `8a46db798c794ef0a73c7f4b1bdcf9eb6c4b79f4d2787c08229ef489c3d17d8c` |
| integration/test_local_retention.py, до изменения | `e32c0fe4ba48f10cbab8f2817ce6bbcaec88162f1c6b137847020b915d270bd3` |

## Обязательный следующий этап и ограничения

После минимального изменения выполнить актуальные unit/catalog/routine/
runtime/access/backup/lifecycle/replay профили на head0107. Включить missing/
wrong-tag literal нового guard, отключение каждого нового trigger с
восстановлением baseline; сохранить прежние unknown function/procedure/
aggregate, ACL, rollback и O/A проверки. Нужны реальный coherent backup/restore
с новым sequence inventory и независимое ревью конечного diff/журналов.
Старые31/575 и исторические журналы не заменять и не выдавать за новую приёмку.

Проверяющий не запускал probe/tests/БД/процессы и изменил только этот отчёт.
Код/spec/plan/tasks/checklists, Git/GitHub, установки/Dev/production не менялись.
`full_preflight_not_implemented`, `activation_recovery_unverified`, полные
T113/#7804/T112, рабочие T0/ready/IP, выпуск и AC01–AC06 остаются открытыми.
После записи отчёт перечитан целиком, итог117/0 и хеши входов сверены повторно.
