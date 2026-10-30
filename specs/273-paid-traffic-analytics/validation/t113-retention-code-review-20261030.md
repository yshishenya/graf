# T113 — независимое ревью кода каталога хранения, 30.10.2026

**SCOPED PASS. P1=0, P2=0.** Проверенная реализация соответствует согласованному
узкому проекту: четыре локальные категории/таблицы, закрытый каталог семи
пользовательских триггеров и их функций, отрицательная проверка известных
scheduler mechanisms. Полное хранение и readiness остаются **HOLD**.

База `bc7fb3b6f2d01daf7a3219e6fa868ed6cbf06eba`, F273/T113/#7804,
`high-risk-product`. Ревью текущих незакоммиченных байтов, а не будущего
коммита/PR или выпуска. Применён навык `code-reviewer`. Разрешённые изменения
ревьюера ограничены этим отчётом; код, тесты, требования и checklist markers
сохранены.

## Проверенные пути

Целиком прочитаны `local_retention.py`, оба новых файла тестов и принятый
`t113-retention-design-review-20261030.md` с уточнением fixed helper parser.
Прочитаны diff и целые затронутые `_runtime_databases`, его прямой caller
`_runtime_preflight`, `_physical_connection`, `_runtime_database_urls`,
`_database_identity`, `_settled_sql`, native integration test и используемая
fixture подготовки актуальной PG17 schema. Перечитаны все 117 вопросов
reviewer-owned checklist. Предыдущие затронутые требования/полный проект
сохранены в контексте этой независимой проверки; их прежние hashes сохранены.

`local_retention_database_catalog` не принимает expected/PASS/source path.
Категории извлекаются из прежней карты двух локальных уровней; exact set+length
исключают пропуски, extra и duplicate. Каждая прежняя retention rule проверяется
на category/storage/enforcement/mode/оба None. Новая таблица, TTL, очистка,
персональные поля и получатели не добавляются.

Функция требует действующую read-only transaction. Реальные `pg_catalog`
запросы подтверждают четыре `public` persistent ordinary heap relations
owner `twobrain_rec`, отсутствие inheritance в обе стороны, partition и rewrite
rules. Строки приложения не читаются; RLS/data coverage этим не утверждается.
Список extensions должен быть ровно `plpgsql`; cron/pgagent/timescaledb
namespaces и `_timescaledb%` дают отказ. Полного поиска произвольного
scheduler/standalone SQL этот код не обещает.

Запрос триггеров читает **все** `NOT tgisinternal` без отсечения неизвестных
таблиц/схем/disabled записей. Exact count и сравнение tuples защищают от extra
sibling trigger. Проверяются relation/name/type/ordered UPDATE columns,
args/WHEN/constraint/deferrability/parent/transition attributes, enabled O/A;
function schema/name/owner/language/return/arguments/kind/security/leakproof/
strict/set/volatility/parallel/config/binary/support/sqlbody и точный prosrc.
Штатный promotion SECURITY DEFINER с двумя config values сохранён; остальные
шесть функций invoker без config. Закрытая карта соответствует принятому
проекту, включая summary и четыре billing triggers.

## Literal parser и происхождение expected

`_expected_bodies` выводит фиксированную package migration directory из
`__file__`; CLI/environment/caller expected не используются. Доверие к пакету
остаётся существующим prerequisite bootstrap: manifest сравнивает все package
files с закреплённым архивом, поэтому новый модуль и файлы миграций не
выводятся из одного заявления о source SHA. Миграции не импортируются и не
исполняются этим reader.

Для 0079/0081/0106 выбирается единственный `upgrade`. Только у фиксированной
0100 выбирается единственный `_install_policies`, причём проверяется ровно один
непосредственный expression call этого имени в `upgrade`, без args/keywords.
Disconnected helper не предоставляет expected. Набор найденных SQL function
definitions обязан точно совпасть с закрытым набором выбранной миграции;
duplicate/missing/extra отвергаются. `ast.walk` применяется только внутри
выбранного определения, общего обхода произвольных helpers нет.

Regex допускает закрывающий dollar tag без последующего SQL `;`, как в штатной
0079. Backreference вынесен в `(?-i:...)`, поэтому SQL keyword case-insensitivity
не распространяется на совпадение регистра tags. Тело захватывается без strip
и сверяется с pg_proc.prosrc точно. Native baseline подтверждает совместимость
такого извлечения с фактической схемой; unit cases проверяют wrong/tag_case,
missing/duplicate/outside_upgrade/disconnected/call_args.

## Интеграция, повторная проверка и отмена

Первое чтение выполняется в существующей owner read-only transaction source
после role verifier/packaged head/PG17 проверки и до SET SESSION AUTHORIZATION.
Та же физическая сессия затем остаётся reduced maintenance. При выходе после
yield `_database_identity` повторяет связь DB/cluster/role, затем reader
в новой read-only transaction повторяет каталоги без повышения прав; новый
digest должен совпасть с первым. Вызов не открывает ещё одну owner/source
сессию и не делает RESET SESSION AUTHORIZATION.

Proof добавлен только как `retention_catalog_sha256` внутри database aggregate.
Внешние четыре поля `_runtime_preflight` сохранены; их результат возвращается
лишь после выхода DB и файловых контекстов и общего финального deadline.
Digest связывает actual enabled state целиком: допустимая замена O на A тоже
меняет proof и обнаруживается при повторном чтении. Raw function bodies/SQL/
строки приложения не возвращаются и не журналируются.

Обычная ошибка скрывается за фиксированным ActivationHold без driver/private
text. CancelledError не превращается в положительный результат; выход через
исключение не исполняет успешный return. Существующие timeout/AsyncExitStack
и `_physical_connection` продолжают владеть source/owner; close ждёт
`_settled_sql` при повторной отмене, затем при необходимости terminate.
Добавленный reader не создаёт собственного child task/соединения. Native
`cancel_query` и `catalog_changed` проверяют, что после завершения нет сессий
`graf-activation-preflight`. Новая специальная отмена внутри каждого из четырёх
каталожных SQL отдельно не доказывалась; механизм владения общий и не менялся.

## Проверки исполнителя и их пределы

Ревьюер тесты и стенды не запускал. Прочитаны исходники причинных проб и
завершённые журналы исполнителя:

- RED: 8 failed с ModuleNotFoundError до появления модуля. Это отсутствие
  механизма, не восемь независимо воспроизведённых уязвимостей.
- Промежуточный завершённый профиль `third`: 11 passed/2 warnings в4.89s.
  Он не используется вместо последующего расширенного профиля.
- Итоговый профиль: **293 passed, 37 skipped, 27 deselected, 2 warnings
  в41.36s**, исполнитель сообщил exit0; финальная строка журнала проверена.
  11 policy/AST units; native PG17 охват — отдельная catalog проба плюс семь
  runtime database cases, включая catalog_changed и cancellation. Остальные
  проверки — существующий focused набор. Linux skips не объявляются PASS;
  они относятся к прежним границам, не изменённым этой SQL-правкой.

Catalog native test получает реальную актуальную схему через Alembic head,
а не metadata.create_all. Последовательно проверяет missing/unlogged/owner/view,
inheritance с обеих сторон/rule, sibling trigger, disabled/replica-only,
function body/security/owner/strict/parallel/config, cron namespace и неизвестное
extension. После каждого обратимого изменения проверяется восстановленный
baseline digest. Дополнительно проверены type/columns/WHEN/args/transition,
положительный O/A с разными digest и тот же каталог после реального SET SESSION
AUTHORIZATION maintenance. Все поля tuples не имеют отдельного причинного
native сценария; положительная native сверка и явные exact comparisons видны
в коде. Это не принимается за full schema или restore proof.

Ruff с `--ignore E721` и `git diff --check` исполнитель сообщил как PASS;
ревьюер их не повторял. Нового PR, CI/релизной проверки или рабочего результата
этими локальными журналами не подтверждено.

Также прочитан отчёт исполнителя `t113-retention-catalog-20261030.md`: его
граница каталога и общий HOLD сформулированы верно. Указанный там будущий
`.dev/growth/t113-retention-final-20261030.json` в момент ревью ещё отсутствует;
он не использован как evidence. Итоговая передача должна либо создать и
проверить этот metadata файл, либо исправить ссылку. Это не дефект исполнения
reader и не меняет SCOPED PASS кода по уже прочитанным журналам/байтам.

## Что остаётся открытым

Модуль и интеграция не выдают full-retention claim. Standalone executable
functions/dependencies, прочие rules/constraints/FK, RLS/maintenance access и
полнота данных, v2 lifecycle/сроки/остатки, host/systemd/cron/installed purge
jobs/config и полное отсутствие произвольных age jobs остаются обязательным
остатком. Category/catalog digest отдельно не разрешает ready.

Полные initial/backup/verify/restore/resume/CD/T112 и T113/#7804/AC01–AC06
остаются открытыми. `activation_recovery_unverified` и
`full_preflight_not_implemented` найдены в текущих исходниках безусловными.
Нет рабочего T0/аналитики/IP/получателей/выпуска; рост трафика, активации и
продажи этим участком не доказаны.

## Checklist и снимок проверенных байтов

Вопросы повторно прочитаны; маркеры не менялись. Это состояние качества
требований, не количество принятых operational tests.

| Checklist | Отмечено | Открыто | SHA256 |
| --- | ---: | ---: | --- |
| requirements | 16 | 0 | `6755318d0b7a76a9f6439446ad42362272d43859cc6f4b3c045b5c36ad1ed9a2` |
| privacy-measurement | 45 | 0 | `8c390000a2da12cf719348d56c08dcb21d886aac98ba1a90ad3d5c41e141cb4f` |
| security | 27 | 0 | `57f082b0b90faf7a3302db0aa1b9aacd29948641e824578ca4f86eee4dee9cb8` |
| infra | 29 | 0 | `998175e297553cedac7f4d7b2829459fcb3f1b650b3b3b6d072e9065437bfa94` |
| Всего | 117 | 0 | Без изменений |

| Файл | SHA256 |
| --- | --- |
| local_retention.py | `485fffe54314239a45aba06df422e2028d1dd2510b2f8a2df0736ecdc2724abb` |
| activation_operator.py | `76f89d790bbdbaed6db86585d16f735508c767f13be02036e19758c2e8992975` |
| tests/unit/test_local_retention.py | `8a46db798c794ef0a73c7f4b1bdcf9eb6c4b79f4d2787c08229ef489c3d17d8c` |
| tests/integration/test_local_retention.py | `73e43f5d3e6af327360eac16739b3d40d9e99be44a715b6c54644e088ee43dcf` |
| tests/integration/test_activation_product_drain.py | `dd3b69bc07d6c4600cf049f5d2e2f9597967596a9c17c39d29471b8ff4fd64d5` |
| retention-design-review | `3af2d4d724bde3c79f54e79eff05ffee463e0297314c5116d4948aac32436a47` |
| retention-precode | `016ece4d849add29663e8b731c9f54c4590616ec5edceb74b8ecd60d6daaf0c2` |
| retention.py | `c7fb1dd4b2c0e3f1fcf88710e187504b2b0967368ca89d119dd3851c9479d434` |
| legal_basis_lifecycle.py | `ac4eb465afb0c647b0d3501bdbeaca2a8a4b1d9c6cad59d4c9a9953cae5f81f9` |
| legal_basis_gate.py | `578de74b6a8362de6c73de9e2bca79e7fd60774324966dae2086d2b6daf7644e` |
| infra/scripts/activation-operator.py | `e11efddb4001602014977be3dff5e86550978cf81bfe67f23d7ae60a0bdfbfb5` |
| tests/fixtures/postgres_test_database.py | `9975596c2901035e2f58fe16481a19d1bc4d3924e8b3a00b1da69cfe80df505b` |
| retention-red log | `0e134f9db57037c639387db67f549af83e359e68ecbfcec07b447724385db448` |
| retention-third log | `f8d0b3fd2de459dcca95c0217cd9e6aaa41e410feb8eaa9767d93c1a01bf3456` |
| retention-profile log | `517a2adbb55f85730e9bc502d03e8c4ca548e5582eb5a2727d32160a0468c574` |
| retention-catalog report | `b31f93b931dca2c63912dd7102608825a65d1617a4fde8d65c3fcc16b3184a2f` |

Перед передачей отчёт перечитан; totals и hashes перепроверены. Ревью не
меняет исходники, тесты, Git/GitHub, Dev или production. Итоговый hash отчёта
передаётся отдельно, без самоссылки внутри его байтов.
