# T113 — независимое ревью проекта DB catalog хранения, 30.10.2026

**SCOPED PASS до кода** для узкого участка: правила четырёх категорий, четыре
отношения и закрытый каталог семи штатных пользовательских триггеров с их
функциями. Блокирующих неоднозначностей в этой согласованной границе нет
(P1=0/P2=0). **Полная DB retention и общая readiness остаются HOLD**.
Отсутствие всех задач возрастной очистки этим участком не доказывается.

База: `bc7fb3b6f2d01daf7a3219e6fa868ed6cbf06eba`, F273/T113/#7804,
`high-risk-product`. Проверен весь
`.dev/growth/t113-retention-precode-20261030.md`, SHA256
`016ece4d849add29663e8b731c9f54c4590616ec5edceb74b8ecd60d6daaf0c2`.
Проект уточнён до начала кода: исключены row counts и изменение протокола
транзакций/SET SESSION AUTHORIZATION; полный охват executable objects,
RLS/lifecycle и jobs не объявляется завершённым.

## Самый короткий принятый алгоритм

1. Новая внутренняя `local_retention_database_catalog(source)` в
   `product_analytics/local_retention.py` сама выполняет фиксированные запросы
   через уже удержанную физическую asyncpg source-сессию. Вызов из существующей
   owner read-only transaction `_runtime_databases`, до `SET SESSION AUTHORIZATION`.
   Нет новых подключений, операций удаления, произвольного SQL/callback,
   supplied expected/PASS/JSON или отдельного источника доверия.
2. Объединение `LEVEL_RETENTION_CATEGORIES` для двух локальных уровней должно
   ровно совпасть с фиксированной картой ниже: нет пропусков, неизвестных
   категорий, дублей или молчаливого расширения. Для каждой `retention_rule`
   подтверждает `graf_postgres`, `decision_required`, `until_decision` и
   minimum/maximum retention days `None`. Окно атрибуции не становится TTL.
3. Из owner `pg_catalog` для всех четырёх таблиц требуются namespace `public`,
   ordinary heap `relkind=r`, persistent `relpersistence=p`, owner `twobrain_rec`.
   Проверяется отсутствие partition/inheritance как в роли родителя, так и
   потомка, и отсутствие rewrite rules. Missing/чужая relation или неизвестный
   каталог даёт отказ. Подсчёт/чтение строк и доказательство полноты RLS в этот
   helper не входят.
4. Весь каталог `NOT tgisinternal` сверяется с закрытой картой семи триггеров.
   Нельзя отфильтровать прочие таблицы, неизвестные схемы или disabled triggers
   до сравнения: extra sibling trigger также должен приводить к HOLD. Для
   каждой записи сверяются table/schema/name, type, UPDATE columns, args,
   WHEN, constraint/deferrability и transition attributes; допускаются только
   enabled `O`/`A`. Internal FK triggers этим утверждением не принимаются как
   полная проверка constraints/cascade/lifecycle.
5. Точные ожидаемые `prosrc` берутся из literal SQL внутри `upgrade` закреплённых
   миграций через `ast` и соответствующую пару dollar quotes. Миграции не
   исполняются ради expected. Неоднозначный/пропавший literal, неизвестный tag,
   несколько подходящих definitions либо несовпадение — HOLD. Пути исходных
   миграций выводятся из доверенного installed package prefix текущего source,
   не принимаются от CLI/caller или environment. Сверяются function namespace,
   owner, language, return/arguments, security/config и остальные явно
   заявленные flags; одного имени или хеша произвольного installed файла мало.
6. В `pg_extension` допускается ровно штатный `plpgsql`; pg_cron/timescaledb/
   pgagent/unknown extension и обнаруженные scheduler namespaces не принимаются.
   Это отрицательная проверка известных механизмов каталога текущей БД,
   не доказательство отсутствия SQL, выполняемого из другого процесса/БД.
7. Helper возвращает только вычисленный digest проверенных policy/catalog
   metadata. `_runtime_databases` включает его в существующий aggregate proof.
   При выходе тот же reader повторяется в read-only transaction уже сниженной
   source-сессии, digest обязан совпасть; повышать права для этого нельзя.
   `pg_catalog` не подменяется таблицами/представлениями приложения и не
   фильтруется RLS. Ошибка доступа повторной проверки также означает HOLD.
   Ошибка чтения/timeout/отмена/несовпадение не даёт готовности. Сохраняются
   существующие физические соединения, последовательность снижения прав,
   окончательный deadline и cleanup; новый RR/RESET протокол не вводится.

| Категория | Таблица public |
| --- | --- |
| activation_milestone_decisions | product_activation_milestones |
| anonymous_page_aggregate | anonymous_page_aggregate_buckets |
| visit_attribution | public_visit_attributions |
| client_acquisition_attribute | client_acquisition_attributes |

Закрытая карта штатных триггеров:

| Таблица | Триггер | type | Функция / окончательный источник тела |
| --- | --- | ---: | --- |
| meeting_outcome_generation_attempts | trg_bump_summary_slot_state_version | 17 | rec_bump_summary_slot_state_version / 0079_summary_state_versions |
| promotion_redemptions | promotion_redemptions_sync_campaign_counter | 21 | rec_sync_promotion_reservation_counter / 0081_secure_promotion_counter_function |
| billing_storage_entitlement_grants | storage_grant_period | 23 | rec_check_storage_grant / 0100_billing_purchases |
| billing_storage_entitlement_grants | storage_grant_immutable | 27 | rec_storage_grant_immutable / 0100_billing_purchases |
| billing_storage_price_versions | storage_price_immutable | 19 | rec_storage_price_immutable / 0100_billing_purchases |
| billing_purchase_quotes | purchase_quote_immutable | 19 | rec_purchase_quote_immutable / 0100_billing_purchases |
| product_activation_milestones | activation_decision_immutable | 19 | rec_activation_decision_immutable / 0106_activation_milestones |

У summary ожидается точный UPDATE OF набор `status`, `failure_code`,
`failure_reason`, `outcome_set_id`, `metadata_json`, `ended_at`; у promotion —
`state`, у остальных — пустой. Сравнение привязано к именам проверенных колонок,
а не к случайным OID эталонной БД. Остальные trigger attributes не выводятся
только из type. Все функции public/owner twobrain_rec/plpgsql/без аргументов/
return trigger. Promotion — SECURITY DEFINER с `search_path=pg_catalog, pg_temp`
и `row_security=off`; остальные — invoker, без config. Требовать invoker от
всех семи ошибочно отклонит штатную схему.

Promotion trigger создаётся 0080. Его окончательное тело берётся из 0081 по
цепочке миграций; в текущем дереве усиленные bodies 0080 и 0081 совпадают.
Раннее предположение ревьюера, что выбор 0080 непременно даст byte mismatch,
после полного чтения исправлено до передачи отчёта. Совпадение исторических
текстов не является причиной игнорировать окончательную миграцию.

## Что этим не принято

Первый вариант «запретить все прочие пользовательские триггеры» неприменим:
у продукта есть штатные billing/summary/promotion triggers. Принята их точная
закрытая карта вместо разрешения по имени или общего запрета.

Существующий `rec-db-verify.py` проверяет source/restore и native schema-only
roundtrip исходной schema.sql. Это полезное средство восстановления, но оно
не превращает уже изменённую source schema в независимый эталон миграций.
Поэтому здесь не добавляется новый native reference lifecycle и не утверждается
полное соответствие всех функций/схем миграциям.

В обязательном остатке полного verifier остаются standalone функции и их
зависимости/вызовы, остальные rules/executable objects, полная schema/constraints/
FK и RLS/maintenance access, фактическая полнота данных, v2 lifecycle/сроки/
остатки удалений, host cron/systemd/installed purge jobs/config и другая
внешняя планировка SQL. Каталог семи trigger functions не доказывает, что
неизвестная standalone функция или внешняя программа не может удалить историю.
Именно поэтому этот срез нельзя назвать завершённой DB retention.

Полные backup/restore/initial/ready/верхние операции и CD остаются открыты.
Безусловные `activation_recovery_unverified` и
`full_preflight_not_implemented` сохраняются. Нет рабочего T0/ready, включения
аналитики/IP/получателей, выпуска или закрытия T112/T113/#7804/AC01–AC06.
Будущий полный retention receipt требует весь ранее принятый охват и свежесть;
этот digest отдельно его не заменяет.

## Проверки после кода

До приёмки реализации нужны причинные RED→GREEN: missing helper/таблица,
конфликт политики, unknown extension/scheduler namespace, inheritance/rule,
extra trigger на sibling relation, смена function body/security/config/
type/columns/args/WHEN/constraint/transition attributes и disabled trigger.
Нельзя принять только пробы самой activation relation. Native PG17 с
актуальными миграциями обязан принять штатные семь triggers, затем отвергнуть
обратимые повреждения и снова принять восстановленную схему. Нужны пробы
неверного/отсутствующего literal и независимое ревью кода. Полнота RLS/данных
проверяется позже соответствующим native/lifecycle сценарием, не фиктивным
`count(*) >= 0` в этом helper.

## Прочитанные требования и контрольные суммы

Полностью перечитан принятый `t113-full-operator-design-20261030.md` (473 строки),
SHA256 `5d1e069f3fe18f31a21c72c9b0abc41614ff8bfc00c3269f27b1f3cb596738ec`.
Повторно прочитаны все 117 вопросов checklist и затронутые разделы текущих
spec (FR-032/036/038/048–050), plan (локальный период и полный оператор), tasks
(T109–T113 и текущие заметки), quickstart (сценарий7 и local period), contracts
operations (хранение/lifecycle), data-model (правило хранения), действующие
retention rules/category map, `_runtime_databases`, rec-db verifier/inventory
и перечисленные миграции. Прежние четыре baseline hash перепроверены в рамках
разрешённого исключения повторного чтения F273; новое полное чтение PRD/истории
статуса не утверждается.

| Checklist | Отмечено | Открыто | SHA256 |
| --- | ---: | ---: | --- |
| requirements | 16 | 0 | `6755318d0b7a76a9f6439446ad42362272d43859cc6f4b3c045b5c36ad1ed9a2` |
| privacy-measurement | 45 | 0 | `8c390000a2da12cf719348d56c08dcb21d886aac98ba1a90ad3d5c41e141cb4f` |
| security | 27 | 0 | `57f082b0b90faf7a3302db0aa1b9aacd29948641e824578ca4f86eee4dee9cb8` |
| infra | 29 | 0 | `998175e297553cedac7f4d7b2829459fcb3f1b650b3b3b6d072e9065437bfa94` |
| Всего | 117 | 0 | Маркеры не менялись |

| Документ/исходник | SHA256 |
| --- | --- |
| constitution | `7616e3d7c8112aa60b1be1cc40594a7dfd25b0870f23b821d7efefd7c23f4ba8` |
| PRD | `0f3ccfcfa60062bb0aae6802eeb0012056a635a30cb9f46f54d1992d0b4f57c2` |
| current-product-status | `25b7f383be47c7160da8e852006ff82019f30a5f9c371fc30baa79238649cd16` |
| product-gates | `9f7072c879490d250053cb7397ad6b9b68fdcde17bdf9367ed874a41e450b5f5` |
| spec | `45bcc14f170951e99813d6aeb0eddbbb413dd64f89cf410da256b6d5e30986b2` |
| plan | `02f4b52274c61fdf69f01415448a28d9509a1c12274a09d5a7382d3fc3db1b19` |
| tasks | `16330cb7c12a3ae7152f476b8c8ab3ed25754a3e87632cb1898c4079a5997690` |
| quickstart | `5bde6a5f388a03b6df1440fca32429f49bd458fdf9203fdc8df880352d249fea` |
| operations contract | `7d68aa7dc06b170508cd8b2858ede6e3e929b2e7155cd03b0895e715cb2b3abb` |
| activation-milestones contract | `9898007a0e87400246f8c95b899dd807fab0424472143e15338429873982f3f9` |
| data-model | `4dba6d438a50cfa20b06e5d8f1d1fdd7fe216f271341c95a1d4bb553e135e962` |
| activation_operator.py | `33fb35d7975feef88e9ea8617afd4c386673239b340001d14f7f5d0a3f0a06b3` |
| retention.py | `c7fb1dd4b2c0e3f1fcf88710e187504b2b0967368ca89d119dd3851c9479d434` |
| legal_basis_lifecycle.py | `ac4eb465afb0c647b0d3501bdbeaca2a8a4b1d9c6cad59d4c9a9953cae5f81f9` |
| rec-db-verify.py | `9878ffa671eacede35b599fe7a8c6fed0a2c8a75561a8d6d7d7911c13e28ebad` |
| 0079_summary_state_versions.py | `15e73e170bf779f1c241c9ffcf2064860a792d3659a9318dceadaa653027896b` |
| 0080_promotion_reservation_counter_trigger.py | `3e3be619f032e362c5b5c8189ebd05b72c3ed921aa321bf768e807bc37245faf` |
| 0081_secure_promotion_counter_function.py | `bfe5ea63c18853f481297fbb717c86ca26b6f0e46cde9bc3d135d0a4a7b5e9f9` |
| 0100_billing_purchases.py | `00de85b46bafe0110ef548939030e939a92c865159a543314dcf4628a89be5de` |
| 0106_activation_milestones.py | `7e464638f72e3fb240e2af048bcdb25022cb9101df3405aaa14068e7b1386898` |

Ревью меняет только этот отчёт; checklist markers и реализация сохранены.
Тестов, Git/GitHub mutations, Docker/SSH/Dev/production не было. Перед передачей
отчёт перечитан целиком, итоговый SHA256 сообщается отдельно.

## Уточнение literal parser до его исправления — 30.10.2026

**SCOPED PASS уточнения, P1=0/P2=0.** Ранее принятое ограничение «literal SQL
только внутри upgrade» было неточным для штатной миграции 0100. Полное чтение
показывает: `upgrade` непосредственно вызывает `_install_policies()` на строке219,
единственный одноимённый module-level helper объявлен на строке257 и содержит
четыре нужных CREATE FUNCTION. Прежний разбор только `upgrade` правильно
отказывал из-за отсутствия expected bodies; убирать эту защиту нельзя.

Разрешённое минимальное уточнение: **только для фиксированной
`0100_billing_purchases`** читать literals из `_install_policies`, подтвердив
ровно одно определение `upgrade`, ровно одно определение `_install_policies`
и ровно один непосредственный вызов `_install_policies()` без аргументов/
keywords в теле `upgrade`. Это существующий прямой statement, а не вызов
в неиспользуемом nested function или поиск имени в строке. Пропавший вызов,
разорванная связь, дубликат/неоднозначное определение или несовместимая форма
дают HOLD. Для 0079/0081/0106 остаётся разбор только `upgrade`. Общий обход
произвольных helpers, исполнение/import миграций и предоставление caller
пути либо expected не добавляются. Закрытый набор четырёх billing definitions
по-прежнему обязан совпасть ровно с ожидаемым, duplicate/missing/extra — отказ.

В 0079 `CREATE FUNCTION` завершается точной меткой `$fn$` без SQL `;` после
неё. Такой штатный конец допустим; точка с запятой после закрывающей метки
может отсутствовать. Разбор обязан сохранить точный `prosrc` между одинаковыми
открывающей/закрывающей метками, включая пробелы/переводы строк; SQL keyword
case-insensitivity не разрешает различный регистр самих dollar tags.
Остальные проверки тела/каталога и defaults не меняются.

До приёмки кода обязательна причинная отрицательная проба disconnected helper
(literal остался, прямой вызов из upgrade удалён → HOLD), а также обычный
штатный baseline с четырьмя billing functions и closing `$fn$` без `;`.
Это уточнение проекта разборщика; текущая реализация и native результаты
этим дополнением не приняты. Полная DB retention/readiness остаётся HOLD.

Повторно проверены исходные байты миграций: 0100
`00de85b46bafe0110ef548939030e939a92c865159a543314dcf4628a89be5de`, 0079
`15e73e170bf779f1c241c9ffcf2064860a792d3659a9318dceadaa653027896b`.
Все четыре checklist и полный проект имеют прежние hashes; состояние
117 отмечено/0 открыто сохранено, маркеры не менялись. База та же
`bc7fb3b6f2d01daf7a3219e6fa868ed6cbf06eba`. Изменения исполнителя в
activation_operator/local_retention и тестах сохранены. Ревьюер добавил
только этот раздел отчёта; тесты/Git/GitHub/Docker/SSH/Dev не выполнял.
