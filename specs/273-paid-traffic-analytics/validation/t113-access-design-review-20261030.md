# F273/T113: независимое ревью прав и зависимостей

Дата: 30.10.2026. Проверяющий: `f273_release_boundary`.
Основа: `24cf069c869dfc71d1bd5a2d534e34f42a078398`, ветка
`codex/f273-local-period-20261029`, T113/#7804, `high-risk-product`.

## Текущее решение

**SCOPED DESIGN / ANALYZE PASS. Открытых P1:0, P2:0; CRITICAL:0, HIGH:0.**
Разрешена реализация ровно уточнённого фиксированного reader и его интеграции
по конечному precode SHA-256
`a1d8b84f36443c6fbe62085d8d9f4c91053a2fbf2c2f66f416a606c52de8949b`.
Полный пре-релизный допуск, рабочая запись и выпуск этим не разрешаются.
Первоначальный HOLD и его находки сохранены ниже как история, а не текущие
блокеры. До этого PASS исходники local_retention/activation_operator неизменны.

**Качество требований — PASS: 117 отмечено, 0 не отмечено.** Все117 действующих
вопросов перечитаны; исходные требования и зависимости сверены по неизменным
контрольным суммам с разрешённым исключением повторного чтения F273. Отметки
контрольных списков не менялись. Их состояние не означает готовность кода,
оператора, аналитики, выпуска или достигнутые показатели роста.

## Первоначальные находки до реализации — устранены

| ID | Уровень | Источник | Проблема | Минимальное исправление |
|---|---|---|---|---|
| A1 | P2 / HIGH | precode, пункт pg_depend | «Любая сторона в четырёх relations, включая defaults/indices/types/constraints» не определяет набор корней и рёбер. Прямые зависимости relations не описывают зависимости их defaults/index/type объектов от routines/operators/collations. Символическая identity сама по себе не описывает изменяемое определение объекта. | Фиксировать закрытый набор корней и поддержанных метаданных из чистой PG17: четыре relations и columns, их defaults, indices, constraints, rowtypes; incoming FK. Точно задать выбор связанных edges, identity обеих сторон, subobject и deptype, правила проверенных исключений. Неизвестный класс/identity — HOLD. Использовать конечный descriptor нынешней схемы, без универсального рекурсивного framework. |
| A2 | P2 / HIGH | precode, исключение internal FK triggers; actual local_retention.py | Прежний reader читает `WHERE NOT t.tgisinternal`. Его семь точных trigger checks не подтверждают состояние внутренних FK-триггеров. Отключение такого триггера может не изменить pg_get_constraintdef или convalidated. | Случайный tgname/OID исключать только при проверке стабильной связи с parent constraint и фактических tgtype/tgenabled/pg_catalog function/relations/deferral/args/parent. Либо отдельный точный invariant этого же охвата. Native mutation отключения FK-trigger должна дать HOLD без DELETE. |
| A3 | P2 / HIGH | precode, metadata descriptor | Не закреплены точные правила ACL NULL/default, нормализация имени текущей БД, identities типов/collations и пользовательских объектов в системных схемах. Пока нельзя воспроизвести один и тот же expected после собственного UUID bootstrap и сравнить owner→reduced. | Указать canonical tuple/поля и выбор объектов; PUBLIC явно, grantor/grantee именами, default ACL owner/namespace/object type; NULL ACL через явное правило `acldefault` либо строгий отдельный null marker. Имя БД нормализовать только в identity текущей БД, не произвольным replace текста. User objects определять включая новые OID в pg_catalog. Предъявить native baseline/repeat/owner→reduced. |

P1:0. P2:3 в начальном предложении SHA-256
`a081f2af87c2634ca879f45838ee2deea0182b15ccaa56bdd99f0c6c5d5758b0`.
На том проходе реализация была заблокирована. Решение ниже закрывает A1–A3
без новых ролей/грантов рабочего сервера, изменения оснований или общего
механизма безопасности.

## Повторное ревью точного алгоритма и закрытие замечаний

Полностью прочитаны конечные precode и SQL. SQL SHA-256:
`35b014ae4857bfeed77ee47599c5d17370af2b49a2c8e53c5956dfe51a00c428`.
Это ignored исследовательский прототип; установленного reader ещё нет.
Принято встроить тот же фиксированный запрос константой прежнего модуля,
без загрузки внешнего SQL или supplied expected.

- A1 закрыта. Набор roots явно включает четыре таблицы со всеми column subids,
  их indices/defaults/constraints и incoming FK, rowtypes+arrays, triggers,
  local policies/rules. Выбираются все edges с любой стороной в roots,
  с обоими class/subids и deptype; identity разрешает PG17. Ничего не
  отбрасывается по неизвестному имени/классу; иной descriptor или ошибка дают
  HOLD. Отдельные строки закрепляют определения defaults/indices/constraints/
  types/columns/collations и исполняемых поверхностей; полного рекурсивного
  обхода не добавлено.
- A2 закрыта. Внутренние FK-триггеры включены, их связь с constraint и actual
  table/function/type/enabled/deferral/args/parent/qual/transition фиксируется.
  Случайное имя не влияет на identity, но семантика не исключается. Native
  disable ALL доказанно меняет descriptor без исполнения DELETE.
- A3 закрыта. NULL ACL разрешается по object type через acldefault; column
  NULL остаётся пустым явным column ACL. Empty ACL не превращается в default
  или полные права. Даже пустой ACL сохраняет object/owner; PUBLIC, grantor/
  grantee/privilege/grant option фиксируются и сортируются C. Defaults всех
  owners и symbolically resolved role flags/memberships/settings включены.
  Только identity текущей БД нормализована в current_db. Canonical serialization
  точно задана: json.loads value::text → сортировка по json.dumps(row,
  sort_keys=True) → sha256 json.dumps(rows,sort_keys=True). Новый baseline
  воспроизведён во втором самостоятельном UUID-кластере.
- Во время чтения первого SQL дополнительно найден конфликт datallowconn/
  datconnlimit с controlled export: эти поля штатно меняет существующий
  оператор. Из конечного SQL они исключены; их реальные проверки сохраняются
  в drain/export/resume. Статические DB owner/ACL/encoding/locale сохранены.
  Coherent backup при false/limit0 остаётся обязательным тестом реализации.

Перед SQL reader сам требует активную транзакцию, transaction_read_only=on,
PG17 и точный search_path `"$user", public`. Порядок callers: прежний catalog
с policy/routine/seven-trigger guards → access reader. Роль задаётся и
проверяется прежними actual callers; reader её не меняет. Конечная сверка
повторяет оба reader через тот же reduced source; lifecycle сохраняет прежний
RR. Внешний результат — только retention_access_sha256; ошибка имеет стабильный
ActivationHold activation_operator_retention_access_unverified без SQL/данных.

Это минимальное продолжение существующего каталога. Новых таблиц, roles,
grants, внешних получателей, fixture-служб или security framework не нужно.

## Принятая граница минимального решения

Один фиксированный внутренний reader в прежнем local_retention.py через
существующую физическую read-only сессию. Его ожидаемый digest принадлежит
проверенному исходному коду, получен только из чистой собственной PG17 штатных
миграций и bootstrap; source/CLI/environment/receipt не задают expected.
Необходимы текущие вызовы до снижения прав и при выходе `_runtime_databases`,
а также внутри прежнего RR `_backup_lifecycle`. Сам helper не выдаёт ready
и не разрешает writer. Общая RR-транзакция всего preflight не заявляется.

Существующий `_verify_runtime_roles` полезен и сохраняется: проверяет три
runtime-роли, их атрибуты/memberships и ряд требуемых privileges. Он не равен
полному ACL descriptor четырёх локальных таблиц и всех пользовательских routines:
дополнительный column grant или EXECUTE WITH GRANT OPTION не обязан нарушить
нынешние положительные has_* проверки. Ожидаемые получатели/роли не меняются.

Поддержанные категории остаются ровно из LOCAL_CATEGORY_TABLES:

| Категория | Relation |
|---|---|
| activation_milestone_decisions | public.product_activation_milestones |
| anonymous_page_aggregate | public.anonymous_page_aggregate_buckets |
| visit_attribution | public.public_visit_attributions |
| client_acquisition_attribute | public.client_acquisition_attributes |

Вне этого helper не требуются полный аудит столбцов и строк всех продуктовых
таблиц, новый SQL-парсер, пользовательский язык описания проверок или попытка
обойти unknown новой общей dependency-системой. Фиксированные метаданные
исполняемых поверхностей, policies/rules и incoming FK допустимы, если их
охват и отказ на неизвестном названы явно. Полная native schema/source/restore
сверка всей GRAF DB остаётся отдельной обязательной проверкой.

## Scoped analyze и соответствие договорам

| Требование/договор | Существующая задача | Оценка этого участка |
|---|---|---|
| FR-036/050, operations «Хранение и удаление» | T113, локальный retention gate | Проверять фактический режим и пути удаления; не удалять по возрасту. Права и зависимости нужны как продолжение каталога, не новая политика. |
| FR-034/035/048/053, operations «Приёмка первого локального периода» | T113 | Backup/restore и точные удаления сохраняются; новый metadata hash не заменяет реальные lifecycle/restore proof. |
| activation-milestones «Единственное состояние готовности» | T113 | Источник не присылает PASS; digest связывается с проверенным runtime/DB, повторно читается после ожиданий. |
| Конституция III/IV/VI | T113, high-risk-product | Без нового внешнего получателя, секретов/данных в отчётах или ослабления удаления; независимый checklist/analyze до реализации. |
| FR-021/025, T112 и AC01–AC06 | T112/T113, остаются открыты | Этот участок не доказывает видимый результат, трафик или продажи. |

Новое уточнение цели/рынка/срока хранения не требуется; конфликтов с
конституцией не найдено. Первоначально было CRITICAL:0, HIGH:3; после
устранения A1–A3 текущий итог CRITICAL:0, HIGH:0. Дублирующая задача/feature
не нужна. Анализ ограничен
этим продолжением T113 и не объявляет повторный PASS всех работ фичи.

Скрипт prerequisites из skill сначала отклонил `--require-spec` как неизвестный
ключ. Поддержанный `.specify/scripts/bash/check-prerequisites.sh --json
--require-tasks --include-tasks` успешно подтвердил active F273 и документы.
В before/after_analyze настроены только выключенные auto-commit hooks;
исполнение изменяющих состояние hooks не производилось.

## 117 вопросов и привязка к требованиям

Перечитаны все вопросы requirements16, privacy-measurement45, security27,
infra29. Проверенные определения оснований/целей/получателей/данных, отдельного
удаления/его срока, восстановления, ресурсов и рабочей приёмки не изменились.
Конкретные A1–A3 относятся к достаточности реализации проверок принятого
договора; они не превращают однозначный пользовательский договор в неизвестный.

| Список | Отмечено | Не отмечено | SHA-256 |
|---|---:|---:|---|
| requirements | 16 | 0 | `6755318d0b7a76a9f6439446ad42362272d43859cc6f4b3c045b5c36ad1ed9a2` |
| privacy-measurement | 45 | 0 | `8c390000a2da12cf719348d56c08dcb21d886aac98ba1a90ad3d5c41e141cb4f` |
| security | 27 | 0 | `57f082b0b90faf7a3302db0aa1b9aacd29948641e824578ca4f86eee4dee9cb8` |
| infra | 29 | 0 | `998175e297553cedac7f4d7b2829459fcb3f1b650b3b3b6d072e9065437bfa94` |

## Прочитанные источники и контрольные суммы

Прочитаны целиком precode, принятый473-строчный full-operator algorithm,
local_retention.py, `_verify_runtime_roles` и `_bootstrap`, существующие
`_runtime_databases`/`_backup_lifecycle`; заново прочитаны затронутые полные
разделы spec/plan/operations/activation-milestones/quickstart, конституция
и правила storage/deletion. Хеши прежних обязательных документов совпали.

| Источник | SHA-256 |
|---|---|
| full-operator-design | `5d1e069f3fe18f31a21c72c9b0abc41614ff8bfc00c3269f27b1f3cb596738ec` |
| local_retention.py | `760e2a5c9787e71c41116ef590d18ad5b4f3457baf8c899c9dab3f5dd39ddf3b` |
| activation_operator.py | `389bfe489469672854ae2e2937caee240d3763d25919fc289543529497bb6edc` |
| bootstrap_runtime_database_roles.py | `eef89121ad607503d99ab3dd2c70b4bc6cdedb7a3ff551b24850ac91ee78adba` |
| spec | `45bcc14f170951e99813d6aeb0eddbbb413dd64f89cf410da256b6d5e30986b2` |
| plan | `02f4b52274c61fdf69f01415448a28d9509a1c12274a09d5a7382d3fc3db1b19` |
| operations | `733f9c5e4b4ff079ed016974d1f759c3100506a5cfbca8c0e4f301e665c85ced` |
| data-model | `488833fcc4b8e4841672485b35cfa0161e1f02983d10ad98b52eb71d55bb55f5` |
| tasks | `d49b467993b88741bf866488be53f3860741f12fdfd9d33a1d1c9dff385ddf70` |
| quickstart | `28791f1c56b0e77153ffc1efec61985f4dcdfa7c34d3a3cfb6671c6190260e65` |
| constitution | `7616e3d7c8112aa60b1be1cc40594a7dfd25b0870f23b821d7efefd7c23f4ba8` |
| PRD | `0f3ccfcfa60062bb0aae6802eeb0012056a635a30cb9f46f54d1992d0b4f57c2` |
| current status | `25b7f383be47c7160da8e852006ff82019f30a5f9c371fc30baa79238649cd16` |
| product-gates | `9f7072c879490d250053cb7397ad6b9b68fdcde17bdf9367ed874a41e450b5f5` |

## Границы

При первоначальном HOLD native baseline ещё не был предъявлен. На повторном
проходе прочитаны probe script и журналы двух самостоятельных чистых PG17
с штатными migration+bootstrap, включая конечный repeat log целиком.
Оба дают575 records, owner/repeat/reduced PASS и cleanup PASS. Второй журнал
явно содержит independent_native_cluster_repeat=pass. Проверяющий независимо
пересчитал descriptor SHA-256 из baseline JSON:
`bfb2080813ca48347c03e453b1e52195d4b5d21d69915d207fe518d12f554ddc`;
он равен записанному и привязан к точному query SHA-256 выше.

Прочитаны все132 исходных dependency edges в компактной форме и их классы;
конечный более широкий descriptor содержит141 edge, включая local trigger/
policy roots. Его разделы: ACL114, column63, constraint30, database1, edge141,
index15, language4, membership3, policy171, role4, role_settings3, table4,
toast4, trigger9, type8, unsupported1. Никакая исходная рабочая строка не
проверялась и в evidence не включалась.

В обоих журналах6 причинных случаев: column grant, function EXECUTE grant
option, default ACL, incoming CASCADE FK, sibling rule, internal FK disable.
Существующий reader не менялся, новый descriptor менялся, undo возвращал
baseline. Дополнительные rules/DELETE не исполнялись. Это подтверждает
причину расширения каталога, но ещё не реализацию нового reader.

| Артефакт в .dev/growth | SHA-256 |
|---|---|
| t113-access-precode-20261030.md | `a1d8b84f36443c6fbe62085d8d9f4c91053a2fbf2c2f66f416a606c52de8949b` |
| t113-access-descriptor-20261030.sql | `35b014ae4857bfeed77ee47599c5d17370af2b49a2c8e53c5956dfe51a00c428` |
| probe-access-20261030.py | `d0162d2a71cdcb47176209fde331f4e35e9327f4e5694b9dbeb5bc81f546acf0` |
| t113-access-native-baseline-20261030.json | `a94d862f0a662038e34c9e412bb0e81bb5b694af9a9158f51f53a3b976074212` |
| t113-access-native-20261030.log | `c417fbf10a7c52757af59ebd299bdaaf73c50b2dfcf3fdde936a9cf4f7447e44` |
| t113-access-native-repeat-20261030.log | `e588e908222d85873e1c1c0dc49ec315f8080010184274c73b248b2a0dec8f3a` |
| t113-access-edges-native-20261030.json | `54f6dca47db61aa0d2efef7fb4c7ca834e669686f5da5f95e580f020fecc8e03` |

Перед передачей повторно перечитаны все117 вопросов. Счёт и хеши списков
снова совпали:117 `[x]`/0 `[ ]`, без изменения маркеров. Новых замечаний
P1/P2 в конечном алгоритме нет. Обязательны native-тесты actual reader:
guards/wrong expected/query failure, ACL/dependency mutations/undo,
owner→reduced, initial и after-yield access mutations, оба final readers,
coherent backup/lifecycle/four-category consumers и очистка; затем независимое
ревью конечного кода и доказательств. Этот design PASS их не заменяет.

Тесты и пробы проверяющий не запускал. Проверяющий пишет
только этот отчёт, не меняет код/spec/plan/tasks/checklists, Git/GitHub, данные,
процессы, Docker/SSH, GRAF Dev или production. Полные T113, installed jobs,
верхний оператор, actual restore/resume, shell/CD/rollback, T112, рабочие T0/
ready/IP, аналитика, выпуск и бизнес-критерии остаются открытыми;
`full_preflight_not_implemented` и `activation_recovery_unverified` сохраняются.
