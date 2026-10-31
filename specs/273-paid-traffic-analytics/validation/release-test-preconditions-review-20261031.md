# Независимое ревью предусловий тестов выпуска — 31.10.2026

Проверяющий: `/root/public_counter_readiness_review`.
Ветка: `codex/release-rls-tests-20261031`.
Exact source SHA: `914dc291bf4e3b832c1575b657280f9e1ebbd1b8`.

## Вердикт

**PASS до реализации только описанного ниже исправления тестовых предусловий и связанных описаний.** Новые продуктовые требования, права, миграции и включение измерения не предлагаются. Это узкий проверочный срез существующей F273/T113 и механическое согласование принятой 0107 с тестовой описью. Все выпускные проверки сохраняются. Сообщённый основным агентом неуспешный Full `41236519294` остаётся неуспешным: его журналы в этом ревью самостоятельно не получались. Реализация исправлений и успешное повторное выполнение тестов этим вердиктом не подтверждены.

## Непосредственно установленные факты

1. `_run_alembic` в `test_product_analytics_anonymous_aggregate_contract.py` при наличии `downgrade_to` вызывает только `command.downgrade`. Параметр `upgrade_to` в этой ветви не задаёт начальную revision. Общий helper менять не требуется.
2. `postgres_isolated_cluster_database_url` создаёт новый случайно названный PostgreSQL-контейнер с tmpfs и loopback-портом, новую БД и применяет текущий `head`. Контейнер удаляется в `finally`. Его схема до `_seed_database` не содержит созданных тестом пользователей или billing registry history. Миграция 0107 разрешает свой downgrade только после блокировки таблиц, `row_security=off` и проверки отсутствия history.
3. `postgres_schema_database_url` имеет session scope; `postgres_seeded_database_url` обнуляет и заполняет данные, но не пересоздаёт схему. Поэтому откатывать этот общий seeded URL до 0106 нельзя. `postgres_clean_database_url` имеет function scope, создаёт отдельную чистую случайную БД и удаляет только её при завершении.
4. `_seed_database` пишет базовые организации, пространства, пользователей, устройства и учебный registry встреч. Ему не нужны таблицы 0107. После самостоятельного round trip чистая БД на 0106 подходит для сценария запрета удаления принятой вехи.
5. 0106 включает и принудительно применяет RLS. Её downgrade под `row_security=off` запрещает потерю видимой и скрытой истории. Проверка с настоящими login-ролями, чужими строками и владельцем таблицы сохраняет самостоятельную ценность; подмена ошибки RLS ошибкой прав на таблицы 0107 не проверяет это свойство.
6. Runtime `RLS_COVERED_TABLES` уже включает `billing_registry_imports` и `billing_registry_gaps`. Fixture, ожидаемый набор migration policy maps, совокупный текст migration и матрица F031 пока их не перечисляют. 0107 содержит обе константы `IMPORTS/GAPS`, ENABLE/FORCE RLS и узкий существующий predicate.
7. `landing-review.md` уже говорит «код независимый, права на сторонние материалы подтверждены» и сохраняет статус «не выполнено», 200% reflow и отдельный ручной проход. Ожидание буквального `clean-room` в тесте устарело; менять нужно его строковую проверку на актуальный смысл документа.

## Допустимая реализация

- В owner/RLS тесте привести **только его собственный изолированный кластер** с пустой 0107 к 0106 существующим `_run_alembic(... downgrade_to="0106_activation_milestones")` до seed/ролей/строк. Явно проверить реальную `alembic_version=0106_activation_milestones` до подмены владельца. Сохранить настоящие `session_user`, read/write/delete/insert ограничения, maintenance-boundary, невидимость чужих строк, точную ожидаемую ошибку RLS и две сохранённые строки/revision после отказа.
- В `test_empty_migration_round_trip_and_populated_downgrade_guard` убрать зависимость от shared seeded URL. На собственной `postgres_clean_database_url` выполнить уже существующий 0106→0105→0106 round trip; затем `_seed_database(empty)`, admission и проверку отказа populated downgrade на том же URL. Сохранить точную ошибку `activation decisions exist`, одну строку и revision 0106 после отказа. Это исключает влияние теста на схему соседних тестов.
- В inventory contract загрузить 0107 существующим `_load_migration_module` и добавить её `IMPORTS/GAPS` в ожидаемое множество. Строгое равенство runtime, fixture и migration-derived набора сохраняется. В fixture добавить только эти две уже защищённые таблицы.
- Зависимые `test_rls_policy_matrix_contract.py` должны читать также существующую 0107. В `specs/031-rls-hardening/contracts/rls-policy-matrix.md` описать обе таблицы как отдельные maintenance-only registry tables с фактическим условием `session_user=current_user=twobrain_rec_maintenance`, `row_security=on`, `rec_context_kind()=maintenance`, `rec_maintenance_allowed()`, operation `billing_reconciliation` и feature area `billing`. Не приписывать им обычную tenant/worker политику или разрешение DELETE: принятые grants/immutability остаются источником поведения.
- В billing usability test заменить устаревшее слово проверкой существующего русского требования о независимом коде. Сохранить отдельный manual gate и 200% reflow. Утверждение о правах должно оставаться в документе.

## Принятые требования и границы ревью

Непосредственно перечитаны затронутые FR-021–025, план продолжения T112/T113 от 27.10, task T113 с его зависимостями, сценарий 4 и дополнение первого локального периода quickstart, разделы доверенной стороны/единого решения/доставки/хранения/restore в activation-milestones и соответствующая модель ledger. Они требуют одной устойчивой вехи, проверенного аккаунта, сохранения истории и прав, запрета повторного принятия после потери истории, самостоятельной проверки восстановления и выключенного runtime до отдельной приёмки. Предложенные правки исполняют прежние требования и не меняют их.

Прочитаны текущие определения fixture, seed и общего Alembic helper, оба целевых теста со всеми проверками, обе миграции 0106/0107, runtime/fixture inventory, два inventory/matrix contract файла и вся F031 policy matrix, billing landing review и его целевой тест. Индекс guidance, document-reading и spec-kit-flow прочитаны. Для четырёх базовых документов применено подтверждённое основным агентом пользовательское исключение F273: совпали контрольные суммы ранее прочитанных документов; здесь не заявляется их новое полное чтение после сжатия контекста.

## Все четыре checklist

Повторно прочитан каждый действующий вопрос, включая добавленные security CHK026–027 и infra CHK026–029. Отметки проверяют качество требований. В описанном тестовом срезе новые неоднозначности требований не найдены; состояние отметок не изменено. Действующие остальные требования не переоткрываются лишь из-за исправления тестовых предусловий; их прежние отметки не выдаются за новую приёмку реализации.

| Файл | Отмечены | Открыты | Вывод для этого среза |
| --- | ---: | ---: | --- |
| security | 27 | 0 | Сохраняются категории, ограничения получателей, until_decision, точные удаления, основания, права и отсутствие вывода частных данных. |
| infra | 29 | 0 | Изменяется только состояние одноразовых тестовых целей; общая схема, recovery/ingress/ресурсные требования сохранены. |
| privacy-measurement | 45 | 0 | Каталог, атрибуция, один account-first счёт, основания и незавершённые рабочие проверки не меняются. |
| requirements | 16 | 0 | Новых целей, пользовательских сценариев, критериев или расширения области нет. |
| Всего | 117 | 0 | PASS требований только указанного исправления. |

## Минимальная последующая проверка

1. Отдельное ревью фактического diff: только тестовые предусловия, опись, её необходимая матрица, формулировка теста, фрагмент изменений и отчёт; migrations/runtime/helpers/общие fixture lifecycle без изменений.
2. На одноразовой PostgreSQL выполнить весь `test_activation_milestone_ledger.py`, включая оба downgrade сценария. Убедиться, что schema-head тесты после них по-прежнему используют 0107; shared БД не откатывается. Очистку собственных БД/контейнера проверить штатными fixture.
3. Выполнить `test_rls_table_inventory_contract.py`, `test_rls_policy_matrix_contract.py` и `test_billing_usability.py`, профильный Ruff и `git diff --check`.
4. После успешной узкой проверки обязательны действующие PR/metadata/governance/macOS и новый Full для нового точного SHA по принятому выпускному пути. Старый failed Full нельзя переименовать в PASS. Рабочее включение F273/T0, восстановление, внешние публикации и результаты продвижения остаются отдельной приёмкой.

## SHA-256 прочитанных источников

- `.specify/memory/constitution.md`: `7616e3d7c8112aa60b1be1cc40594a7dfd25b0870f23b821d7efefd7c23f4ba8`.
- `docs/prd-voice-layer-final.md`: `0f3ccfcfa60062bb0aae6802eeb0012056a635a30cb9f46f54d1992d0b4f57c2`.
- `docs/current-product-status.md`: `25b7f383be47c7160da8e852006ff82019f30a5f9c371fc30baa79238649cd16`.
- `docs/agent-guidance/product-gates.md`: `9f7072c879490d250053cb7397ad6b9b68fdcde17bdf9367ed874a41e450b5f5`.
- `specs/273-paid-traffic-analytics/spec.md`: `0058816587634dc8235c0d2fa44a02218a5978488e37d001a0c909342401155d`.
- `specs/273-paid-traffic-analytics/plan.md`: `ec8c56970d71c8dc76d864c4218d653c1ba4e7efaef98a2d99c27b10d25bfb6f`.
- `specs/273-paid-traffic-analytics/tasks.md`: `08080dd6034d0e1c3cb4bfb6d9e414e697a9bb1350e32bdad9fa250ffc0cf61e`.
- `specs/273-paid-traffic-analytics/quickstart.md`: `d2359d0bf604bd62410c73f5be7a695eb414bcc9a174dcd50677ce3df49a15df`.
- `specs/273-paid-traffic-analytics/data-model.md`: `52fb96e3dd9c399c741a9c982916fd755a056580efdd36539bfc7f1a91cc74be`.
- `specs/273-paid-traffic-analytics/contracts/activation-milestones.md`: `8f7e7d0ca401c14ff443846c3c0a86e28f081998994ad7489cc89ef3e9fa41e1`.
- `apps/server/tests/contract/test_activation_milestone_ledger.py`: `4d4d34e5f0fc1c7c7c5201afcd6c4939dbf9bf58f934a3d30cce6b10bc792035`.
- `apps/server/tests/fixtures/postgres_test_database.py`: `9975596c2901035e2f58fe16481a19d1bc4d3924e8b3a00b1da69cfe80df505b`.
- `apps/server/tests/conftest.py`: `5cad4be139be77c18e6810387167da90c317732a7269c88949a8b87b41f46f8a`.
- `apps/server/tests/contract/test_product_analytics_anonymous_aggregate_contract.py`: `86126200f5124d8126315f6308b725a424ebb1672f1bcfa8b663ad44032db044`.
- `apps/server/tests/contract/test_rls_table_inventory_contract.py`: `3bc8b850b47fdea445a4651280e45ba3664faa87688e3e1c0b99740da21d3164`.
- `apps/server/tests/contract/test_rls_policy_matrix_contract.py`: `7320dac1e2d445ce01048b6443631d035554ed021af6b22fc273065b681bde1e`.
- `apps/server/tests/fixtures/rls.py`: `f9a5a394ac9f8eac7b170220bbfebcd1b9327f4a1ab2f7b058f66e0acc5fc4a4`.
- `apps/server/src/twobrain_rec_server/db/rls_validation.py`: `5aa325a6b18af3a604025c5818863e504b63cc83eca0626fed78dccdd5e6a368`.
- `apps/server/src/twobrain_rec_server/db/migrations/versions/0106_activation_milestones.py`: `7e464638f72e3fb240e2af048bcdb25022cb9101df3405aaa14068e7b1386898`.
- `apps/server/src/twobrain_rec_server/db/migrations/versions/0107_billing_registry.py`: `e8ff8a51ac0acb519f9fd3608e6a481b0b41dde5557107a3d3efbeec766eb614`.
- `specs/031-rls-hardening/contracts/rls-policy-matrix.md`: `8f9bf5b37bccbbaf4bef28fb6d1de9c9e6920a0c1751300865edbc407a5b16fd`.
- `docs/evidence/140-user-account-billing/landing-review.md`: `60885aaa1a1536c24227905708f8bb64a598125193e97b332a00bf86b75489fc`.
- `apps/server/tests/integration/test_billing_usability.py`: `bbbc320dba10c79305d9e1c3067338b6021ff0e132b5472e497f4649763517a7`.
- `specs/273-paid-traffic-analytics/checklists/security.md`: `57f082b0b90faf7a3302db0aa1b9aacd29948641e824578ca4f86eee4dee9cb8`.
- `specs/273-paid-traffic-analytics/checklists/infra.md`: `998175e297553cedac7f4d7b2829459fcb3f1b650b3b3b6d072e9065437bfa94`.
- `specs/273-paid-traffic-analytics/checklists/privacy-measurement.md`: `8c390000a2da12cf719348d56c08dcb21d886aac98ba1a90ad3d5c41e141cb4f`.
- `specs/273-paid-traffic-analytics/checklists/requirements.md`: `6755318d0b7a76a9f6439446ad42362272d43859cc6f4b3c045b5c36ad1ed9a2`.

## Повторное ревью фактических исправлений — 31.10.2026

**PASS кода в описанном узком объёме и завершённой профильной проверки.**
Основа остаётся `914dc291bf4e3b832c1575b657280f9e1ebbd1b8`; проверялись несохранённые в коммит изменения поверх неё. Исходный перечень SHA-256 выше относится к состоянию до реализации; текущее состояние связано хешами ниже. Это не PASS полного выпуска или рабочего измерения.

Непосредственно просмотрен весь фактический diff шести отслеживаемых файлов и полный новый `changes/unreleased/F273.yaml`. Находок, требующих исправления, нет:

- Оба downgrade сценария теперь используют собственные одноразовые цели на 0106. Shared seeded URL удалён из первого сценария; его round trip, seed, admission и запрет потери строки выполняются на одной function-scoped чистой БД. Второй сценарий явно откатывает только свой пустой isolated cluster до seed. В обоих проверена фактическая revision до admission/смены владельца.
- Все прежние проверки реальных runtime login-ролей, точного допуска maintenance, невозможности чтения/изменения чужих строк, ошибки INSERT/RLS, скрытой истории у table owner и сохранения обеих строк/revision после отказа сохранены. Миграции, runtime inventory, общий Alembic helper и lifecycle общих fixture не менялись.
- Inventory contract загружает существующую 0107 и использует её IMPORTS/GAPS, оставляя точное равенство; matrix contract читает её текст. Fixture добавляет обе таблицы в `RLS_OPERATOR_TABLES`: поиск всех потребителей показал, что подмножество применяется только в итоговом union `RLS_COVERED_TABLES`; новых исключений, прав или поведения это не создаёт. Матрица F031 верно описывает отдельный узкий maintenance-only predicate, grants без DELETE и неизменность history.
- Billing test теперь требует обе действующие формулировки: независимый код и подтверждённые права на материалы. Незавершённость отдельного ручного gate и 200% проверка остались.
- Фрагмент F273/T113 описывает только проверочные исправления, явно сохраняет отсутствие изменений рабочего кода/миграций/прав и отдельную приёмку выпуска/измерения.

### Доказательства проверок

Прочитан завершённый `.dev/release/prep-20261031/focused-fixed.txt`: collection_count=44, collection_digest=`beb3e1cf66f895cbf925ff1324b9512bcbe33a1714f2ce5cc61b8b2c36873921`; `44 passed, 2 warnings in 15.06s`; `postgres_test_phase=focused status=pass`; `postgres_test_cleanup=isolated_container_removed`; `postgres_test_result=pass`. В slowest durations явно присутствуют оба исправленных downgrade сценария. Журнал получен выполнением основного агента; повторно запускать тот же набор без новых изменений оснований нет.

Первый `focused-fix.txt` с 43 passed/1 failed не засчитывается: пропущенный обязательный аргумент `upgrade_to` исправлен в текущем diff, где он указан явно. Два предупреждения успешного прогона относятся к pytest assert rewriting уже импортированного fixture-модуля и deprecated httpx TestClient; это не пропущенные проверки.

Проверяющий независимо выполнил `apps/server/.venv/bin/python -m ruff check` для всех пяти изменённых Python-файлов: `All checks passed!`. Независимый `git diff --check` также PASS. Код, Git/GitHub и рабочие настройки проверяющим не менялись.

Все четыре checklist повторно прочитаны по действующим вопросам; отметки не менялись. Итог сохранён: security 27/0, infra29/0, privacy-measurement45/0, requirements16/0; всего117 отмеченных/0 открытых. Это качество требований, а не доказательство выполнения всех F273 задач. Неуспешный старый Full остаётся неуспешным; новые PR/Full/CD и рабочая приёмка продолжают требоваться по штатному пути.

### Точное состояние после реализации

- SHA-256 полного diff шести отслеживаемых файлов: `f839919e561a9ef844e5f2a54aea5b84f7aca55781b8953049505fab7f7d3422`.
- `apps/server/tests/contract/test_activation_milestone_ledger.py`: `b4449bcc8443ad6a357bc4bd6ae071c56af19dda129befa5f2e40b7ff843680d`.
- `apps/server/tests/contract/test_rls_policy_matrix_contract.py`: `6eff3a6dd0bef97d073ffe9cadef39d2db7459e1db55c2021820f415662c761a`.
- `apps/server/tests/contract/test_rls_table_inventory_contract.py`: `299f90cbba36294227ef8f1ce9200bd63568905a44fbf4e65f71eb6b8dc88b7f`.
- `apps/server/tests/fixtures/rls.py`: `50427961b2badf2682a076290295b85e61531eae24994049201f69d31999759e`.
- `apps/server/tests/integration/test_billing_usability.py`: `c32168f5120efb5a7f13c3ec3e7693886abaf393bd5956a152f635221bd4a7f1`.
- `specs/031-rls-hardening/contracts/rls-policy-matrix.md`: `bb16ee4155b495d91421aafd13aca3451a86252f51a2fdae01347ffaa510e202`.
- `changes/unreleased/F273.yaml`: `c0ac7a55384dcea479d34a82ecf5145fdde9fb24df0fd66cdf5f26bd69dd43a7`.
- `.dev/release/prep-20261031/focused-fixed.txt`: `b65e1208a798bb5cf42aebb04f9ca620ab4092dec601d28c2e4248b08d889599`.
