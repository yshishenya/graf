# F273/T113: независимая проверка кода каталога функций

Дата: 30.10.2026. Проверяющий: `f273_release_boundary`.
Основа: `91fb51b226710755b1866ee0a7360a40017ec78d`, ветка
`codex/f273-local-period-20261029`, T113/#7804, `high-risk-product`.

## Решение и точный охват

**SCOPED CODE REVIEW PASS. Неразрешённых P1/P2 нет.** Проверены конечные
изменения `local_retention.py`, native-тестов, действующие пояснения, основной
отчёт и журналы. Все 21 запись окончательного перечня контрольных сумм
независимо совпали с файлами. Проверяющий тесты и учебные пробы не запускал.

Принятый проект:
`t113-functions-design-review-20261030.md`, SHA-256
`8054d5b0740568b84bb12c7fb0236275bdc826f1d511f2d6142392575814766a`.
Precode SHA-256:
`c072d9a4448a7f2b8b5caf4b8aefbcc4bb88a02c4b1e9f6067e708d4ff1348af`.

Этот PASS относится к сверке routine catalog с закреплённым эталоном, не
к полной готовности T113. ACL, non-routine dependencies/остальная schema/access,
installed jobs, верхние операции, actual restore/resume, shell/CD/rollback,
T112 и выпуск остаются открытыми. `full_preflight_not_implemented` и
`activation_recovery_unverified` не снимаются. Рабочие T0/ready/IP, включение
аналитики и коммерческие AC01–AC06 этим отчётом не принимаются.

## Что проверено в реализации

1. Ожидаемый routine digest закреплён в исходниках и совпадает с независимым
   descriptor чистой учебной PG17 штатных миграций:
   `f587419462003e7aa9116c51191c23ad7a885867bf880885386a068a7f0f8550`.
   Источник, environment, CLI и receipt не могут передать собственный expected.
   Дополнительного SQL-парсера миграций, импорта/исполнения SQL ради expected
   в runtime или нового подключения не добавлено.
2. Общий фиксированный predicate включает все `p.oid>=16384` в любой схеме,
   в том числе `pg_catalog`, и routines неслужебных схем. Фильтров только
   public/rec_* нет. Предварительный запрос требует ровно31 routine и kind=f.
   Процедура, aggregate и иной неподдерживаемый kind не разрешают deparser.
3. Проверки версии PG17, точного default search_path, полного списка языков
   c/internal/plpgsql/sql и отсутствия event triggers/FDW/foreign servers
   предшествуют deparser. Source search_path не изменяется ради совпадения.
   Имена каталогов/системных deparser квалифицированы через `pg_catalog`.
4. Descriptor включает namespace/name/identity arguments, полный
   pg_get_functiondef, owner/language/kind и заявленные отдельные flags,
   нулевой support, отсутствие probin/prosqlbody. Появление ненулевого значения
   не игнорируется. Return/security/config/defaults/cost и прочие штатные
   параметры покрываются полным определением. Сортировка явно C; сериализация
   совпадает с исходным эталоном. Чистый текущий native schema даёт совпадение.
5. Прежние policy/category/relation/extension и семь точных trigger checks
   сохранены. Новый hash не заменяет проверку trigger columns/args/WHEN/
   enable/constraint/transition, окончательного literal-body и его связи с
   upgrade. В итоговый общий proof добавляется только routine digest;
   тела/SQL/данные из source не возвращаются и не записываются в evidence.
6. Сохраняется существующее физическое read-only соединение, порядок
   owner→reduced и конечная повторная проверка вызывающего оператора. Общая
   RR-транзакция всего preflight не появилась и не заявляется; RR в прежнем
   lifecycle сохраняется. Отказ/несовпадение дают существующий безопасный код
   HOLD без необработанных SQL-ошибок и без разрешения writer.

Код и тесты прочитаны целиком. Прочитанные изменения tasks/quickstart/fragment/
плана роста не закрывают T113 или коммерческие критерии и явно сохраняют
остаток по ACL/зависимостям/установленным заданиям. На данном этапе требуется
именно фиксированный эталон текущих миграций: новая штатная routine требует
явного обновления правила и нового ревью, а не разрешения по новому source.

## Native-сценарии и причинные проверки

Прочитаны baseline script/JSON/log и причинный RED script/log. До исправления
на собственной чистой PG17 создана standalone SQL-функция с DELETE учебной
таблицы; функция не вызывалась. Прежний reader вернул прежний hash, поэтому
причинное утверждение об обнаружении нового routine ожидаемо упало. Это
доказательство неполного обнаружения, а не рабочего удаления данных. В логе
подтверждена очистка собственного кластера.

Новый native-тест выполняет21 обратимое изменение: extra routine,
неисполненная purge function, overload, другая схема, pg_catalog, body,
SECURITY DEFINER, config, owner, parallel, leakproof, strict, cost, procedure,
aggregate, language, FDW, foreign server, event trigger, search_path и default.
После каждого undo снова требуется исходный baseline. Отдельно проверяется
неверная expected-константа и равенство owner→reduced без повышения прав.

ObservedSource делегирует настоящему соединению и записывает фактические
запросы. В процедурах/aggregate/event/language/search_path случаях проверяется,
что pg_get_functiondef не был вызван после отказа предварительных условий.
Это проверка реального порядка reader, а не заранее выданный fake PASS.
Существующая проверка семи триггеров и их повреждений также исполняется.

Первый профиль342PASS/37SKIP/1FAIL сохранён. Его failure произошёл в undo:
PostgreSQL запретил удалить новый parameter default через CREATE OR REPLACE.
В прочитанной конечной редакции только это изменение помещено в собственную
DDL-транзакцию, после DDL ставится READ ONLY для reader, затем выполняется
rollback. Shared helper не удаляется. Повтор всего профиля успешен; прежний
неуспешный журнал не засчитывается как PASS.

## Конечные журналы и привязка к файлам

| Артефакт в `.dev/growth/` | Прочитанный результат | SHA-256 |
|---|---|---|
| `t113-functions-native-baseline-20261030.log` | 31 routine; digest совпал; cleanup PASS | `c20ef8cf880b766a219aff02ad57b5781a0a2e20bdc9338ff4b984fc81c8eccf` |
| `t113-functions-native-red-20261030.log` | Ожидаемый causal RED прежнего reader | `6d0e9e0008f7992ae41ac52e341e78bc0b8f508c74b9131742588a0589f4be3d` |
| `t113-functions-profile-20261030.log` | 342 passed, 37 skipped, 1 failed в undo | `c75a449cc2a2b4fca90f51073bd137c6aea58243f7eaa5e5c072de3eafea7622` |
| `t113-functions-profile-final-20261030.log` | 343 passed, 37 skipped, 2 warnings; 11,03 с | `c695d6f2dba23153813ae77220a8575e8ef45498ef3fcf004085ea639eb9ebb2` |
| `t113-functions-consumers-20261030.log` | 5 passed, 2 warnings; 61,33 с | `31cbdea65a7012ac5af90e0c1b555f388d4bc5ae923b043fb48a0791dcd74e9b` |

Основной профиль сообщает collection_count380, итог343+37. Профиль потребителей
сообщает collection_count5: coherent backup/restore success, source lifecycle,
all-four categories, exact account replay старой копии и category replay с
сохранением непричастных строк. Оба штатных запуска сообщают status=pass,
postgres_test_result=pass и isolated_container_removed. 37 прежних пропусков
Linux root/proc/memfd/ACL на Mac не засчитываются как Linux PASS. Два
предупреждения fixture-import и Starlette/httpx сохранены. Разные наборы не
смешиваются с полным release-profile или exact-SHA GitHub CI.

Полностью прочитан конечный отчёт `t113-functions-20261030.md`, SHA-256
`bc458c44579184c937ebce77b88999b6feb21c7b101566ba75fd8dd3e38bca3d`.
Перечень `.dev/growth/t113-functions-final-hashes-20261030.json` содержит21
запись; все21 независимо совпали. SHA-256 самого перечня:
`f022555a0456fe99061ed2c7d8fdec2966ac21b4a291ed8a843d58c48639fb67`.
Отдельные утверждения исполнителя о Docker inventory и Ruff/governance/
development-process/Markdown-проверках здесь не выдаются за команды,
заново исполненные проверяющим. Cleanup подтверждён прочитанными журналами.

| Конечный файл | SHA-256 |
|---|---|
| `apps/server/src/twobrain_rec_server/product_analytics/local_retention.py` | `760e2a5c9787e71c41116ef590d18ad5b4f3457baf8c899c9dab3f5dd39ddf3b` |
| `apps/server/tests/integration/test_local_retention.py` | `e32c0fe4ba48f10cbab8f2817ce6bbcaec88162f1c6b137847020b915d270bd3` |
| `specs/273-paid-traffic-analytics/quickstart.md` | `28791f1c56b0e77153ffc1efec61985f4dcdfa7c34d3a3cfb6671c6190260e65` |
| `specs/273-paid-traffic-analytics/tasks.md` | `d49b467993b88741bf866488be53f3860741f12fdfd9d33a1d1c9dff385ddf70` |
| `changes/unreleased/F273.yaml` | `61085761f4685ef8260eb93c8d7b485f4b1f9c5c73f20c7af5857501bcafbac2` |
| `docs/growth/organic-growth-plan.md` | `de09d5ff9d5f70f6482cb5601835ebc7e65cf8bd6f3d2861aed1f5bc9d1eb23c` |

## Контрольные списки и исходные требования

Повторно прочитаны все117 вопросов; отметки проверяющий не менял. Состояние
117/0 подтверждает качество требований, а не полноту реализации или выпуск.

| Список | Отмечено | Не отмечено | SHA-256 |
|---|---:|---:|---|
| requirements | 16 | 0 | `6755318d0b7a76a9f6439446ad42362272d43859cc6f4b3c045b5c36ad1ed9a2` |
| privacy-measurement | 45 | 0 | `8c390000a2da12cf719348d56c08dcb21d886aac98ba1a90ad3d5c41e141cb4f` |
| security | 27 | 0 | `57f082b0b90faf7a3302db0aa1b9aacd29948641e824578ca4f86eee4dee9cb8` |
| infra | 29 | 0 | `998175e297553cedac7f4d7b2829459fcb3f1b650b3b3b6d072e9065437bfa94` |

По разрешённому исключению повторного чтения F273 применены прежние полные
чтения с проверкой неизменных хешей и повторным чтением затронутых требований
и зависимостей. Текущие значения базовых документов:

| Документ | SHA-256 |
|---|---|
| constitution | `7616e3d7c8112aa60b1be1cc40594a7dfd25b0870f23b821d7efefd7c23f4ba8` |
| PRD | `0f3ccfcfa60062bb0aae6802eeb0012056a635a30cb9f46f54d1992d0b4f57c2` |
| current status | `25b7f383be47c7160da8e852006ff82019f30a5f9c371fc30baa79238649cd16` |
| product-gates | `9f7072c879490d250053cb7397ad6b9b68fdcde17bdf9367ed874a41e450b5f5` |
| spec | `45bcc14f170951e99813d6aeb0eddbbb413dd64f89cf410da256b6d5e30986b2` |
| plan | `02f4b52274c61fdf69f01415448a28d9509a1c12274a09d5a7382d3fc3db1b19` |
| operations | `733f9c5e4b4ff079ed016974d1f759c3100506a5cfbca8c0e4f301e665c85ced` |
| data-model | `488833fcc4b8e4841672485b35cfa0161e1f02983d10ad98b52eb71d55bb55f5` |

Проверяющий создал только этот отчёт. Код, документы, tests, checklists,
Git/GitHub, БД, процессы, Docker/SSH, GRAF Dev и production проверяющим
не изменялись; тесты и пробы не запускались. Память других диалогов не
использовалась. Отчёт перечитан перед передачей, его хеш сообщается отдельно.
