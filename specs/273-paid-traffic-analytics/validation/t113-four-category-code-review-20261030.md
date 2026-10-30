# F273/T113: независимая проверка кода четырёх локальных категорий

Дата: 30.10.2026. Проверяющий: `f273_release_boundary`.
База: `7b83ec21998cc24c2d4dc8a59a9d2c2edfcebe65`, ветка
`codex/f273-local-period-20261029`, F273/T113/#7804, `high-risk-product`.

## Решение

**SCOPED CODE REVIEW PASS** для согласованного изменения четырёх локальных
категорий на зафиксированных ниже байтах. Неразрешённых P1/P2 не обнаружено.
Прочитаны изменённые исходники, тесты, действующие описания, конечный отчёт
исполнителя и завершённые журналы; все 39 записей окончательного inventory
независимо сверены с файлами. Сам проверяющий тесты не запускал.

Узкий PASS этого изменения не закрывает T113/#7804,
полную готовность, рабочее включение или выпуск. `full_preflight_not_implemented`
и `activation_recovery_unverified` остаются общими HOLD. Учебные удаления не
являются доказательством рабочего восстановления, соблюдения исторических
сроков или исполнения запросов у внешних провайдеров.

## Проверенное соответствие принятому проекту

Принятый проект: `t113-four-category-design-review-20261030.md`, SHA-256
`bc7dafe5ad769408b62f2eeb40fdd4cee6bff07955296ff1e1b8b30f7c9a6f1a`.
Его precode SHA-256:
`c4fa23863fb9ae82cde073bf563e082808e4288d2c83e69d6cfb931c14ce111d`.

1. Общая фиксированная карта четырёх категорий используется parser,
   catalog/source/replay. Из текста оператора нельзя подставить имя SQL-таблицы.
   Category/all acquisition теперь удаляет полную отдельную аналитическую
   строку, включая bridge; `user_identities` сохраняется. Старое обнуление
   шести campaign-полей не объявляется полным обезличиванием.
2. Точный account helper не делает COMMIT. Finalizer удаляет ledger и
   acquisition и записывает два самостоятельных результата в одной транзакции.
   Существующий ранний возврат completed/canceled сохранён; история старых
   completed не переписывается. Writer блокирует identity и принимает только
   active, тем самым сериализуясь с finalizer. Других прикладных INSERT-путей
   acquisition в дереве серверного кода не найдено.
3. Acquisition metadata проверяется отдельно: наличие хотя бы одного ключа
   включает строгую проверку полноты, числового типа/count и aware-хронологии.
   JSON null не превращается в legacy absence. Полное отсутствие новых ключей
   допускает только проверку текущего отсутствия строк при непроверенной
   истории. Другая replay-операция не обязана иметь прежние count/time.
4. Источник читается reduced-соединением в RR read-only transaction. Closure и
   ledger требуют точной policy, ENABLE/FORCE RLS и SELECT; три остальные
   таблицы требуют SELECT и отсутствия RLS/policies. Ordinary-table catalog
   сохраняется. EXISTS проверяет category/all либо точные completed accounts;
   legacy remnant даёт HOLD без скрытого удаления чужой категории.
5. Withdrawal требует полного локального охвата даже при пустых таблицах:
   aggregate либо acquisition/visit/ledger. Source требует applied category,
   тогда как synthetic replay может исполнить accepted intent. Failed и
   неполный coverage не разрешают исполнение. Provider scope явно остаётся
   вне локального доказательства.
6. В synthetic target quarantine и удаления выполняются одной транзакцией;
   полные survivors всех четырёх таблиц сверяются до COMMIT и новым физическим
   соединением после него. Источник и реестр не изменяются. Неизвестный COMMIT,
   неудачный readback/cleanup или изменение закрытых входов не дают успеха.
   Отчёт наружу содержит безопасные количества/контрольные суммы, без строк,
   payload, селекторов аккаунтов и необработанных SQL-ошибок.
7. Прежняя native предварительная проверка ledger/полной схемы остаётся
   обязательной обязанностью вызывающей процедуры. Новый путь runpy внутри
   server image не добавлен: infra/scripts там отсутствует. Новая проверка
   трёх таблиц не объявляется заменой полной предварительной сертификации.

## Проверки исполнителя, журналы прочитаны проверяющим

Причинные RED подтверждают два разных пробела: реальный finalizer оставлял
9 acquisition-строк вместо 8; отдельный возврат старого six-NULL executor
оставлял фактические остатки и приводил к отказу source-reader. Пять unit RED
показывали отсутствие нового scope/API, а не пять самостоятельных рабочих
дефектов. Проверяющий не запускал и не изменял эти проверки.

| Журнал в `.dev/growth/` | Наблюдаемый результат | SHA-256 |
|---|---|---|
| `t113-four-category-native-red-20261030.log` | 1 expected failure; finalizer remnant | `5896abcb450f63f95114ffb12d699c7d29b64145c7b5f7e7751391bc22e28531` |
| `t113-four-category-legacy-erasure-red-20261030.log` | 1 expected failure; old executor remnant | `d0232e0030a7beda264c5aa1d01df65f9a283047b30ae3943cca09e68f1f3b6e` |
| `t113-four-category-unit-red-20261030.log` | 5 expected failures | `b852b3e26075dc2df46d0338ecc80991290119b1c92410d6183cb4c76c0fd7fe` |
| `t113-four-category-unit-first-20261030.log` | 38 passed | `e6a86974c240a33daeec3bebd9c70242236bf541a018cf2d70ed4418af31ec90` |
| `t113-four-category-native-first-20261030.log` | 4 passed, 37 deselected | `83f797df0a00f1c1529ec7ad1fc8326ecea70adee8bc0e941af7207a273414ab` |
| `t113-four-category-second-20261030.log` | 48 passed, 40 deselected | `5a5afbe7e74cbc70e1a2cf88b9a6075de712b2c4245c77d0f3fcdc777210088d` |

В последних прочитанных тестах дополнительно проверяются legacy all-absent
против partial/null/string metadata, точные acquisition remnants, каждый
локальный scope, отсутствие scope при пустой цели, обе локальные withdrawal
группы, сохранение identities/непричастных строк и повтор. Native finalizer
тест воспроизводит rollback после ошибки второго удаления, наблюдает
`pg_blocking_pids` позднего writer, затем отказ closed-account и неизменность
metadata при повторе completed. Эти утверждения проверены чтением кода тестов;
конечный целевой и общий журналы прочитаны и контрольные суммы сверены:

| Конечный журнал в `.dev/growth/` | Наблюдаемый результат | SHA-256 |
|---|---|---|
| `t113-four-category-final-targeted-20261030.log` | 55 passed, 40 deselected | `a47493df836ac37fcf5418af4d8caaea24cd3c11c9b34d6aa8ff2f41a39b7849` |
| `t113-four-category-unit-profile-20261030.log` | 378 passed, 37 skipped | `6c037e0d09bf33d717a1f5c11bbba211264164c4cd7ff3f1be4c5a692209f21c` |
| `t113-four-category-shared-postgres-20261030.log` | 20 passed; штатный cleanup PASS | `9766ebc89b28adbc3ad3f04bd64d4873feef7dfb785b94759aab55e83a93af36` |
| `t113-four-category-proper-profile-20261030.log` | 392 passed, 37 skipped, 48 deselected; 279,73 с | `0472b531609bbcb45dfccba10c779a10b7203928219e90520877d2438fef5585` |
| `t113-four-category-retention-rules-20261030.log` | 12 passed; 0,02 с | `0032dc63dfb731a59c57699d4aa9e9d2a84ba16d8113b40adbdd1cd90c9f31c5` |

Proper-profile запущен штатной PostgreSQL-оболочкой, сообщает
`collection_count=429`, `status=pass`,
`postgres_test_cleanup=isolated_container_removed` и `postgres_test_result=pass`.
Команда и выбранные пути записаны в отчёте исполнителя. 37 пропусков не
зачитываются как Linux/root/proc/memfd/ACL PASS; 48 исключённых случаев не
входят в проверенное множество. Указанные наборы перекрываются, их результаты
не складываются в число уникальных тестов. Два прежних предупреждения pytest
и Starlette сохранены. Отдельный retention-rules журнал прочитан: 12 passed,
2 warnings, 0,02 с; он включён в окончательный inventory. Исполнителем также
сообщены успешные Ruff/governance/development-process/Markdown-проверки; их
отдельные журналы не включены в данный inventory, поэтому здесь они не
объявляются самостоятельным заново исполненным доказательством проверяющего.

Неуспешные прогоны сохранены и не названы PASS:

- `t113-four-category-profile-20261030.log`: 420 passed, 37 skipped,
  1 failed, 19 setup errors. Spy не поддерживал новый scalar-запрос статуса;
  прочитанная правка добавляет active и четвёртый SQL вызов. Setup errors
  прямо сообщают об отсутствующем TWOBRAIN_DATABASE_URL. Исправленный spy
  и штатная оболочка проверены конечным успешным общим прогоном.
- `t113-four-category-final-profile-20261030.log`: 391 passed, 37 skipped,
  48 deselected, 1 setup error в corrupt_copy на docker network create.
  Точный stderr Docker/первопричина не предъявлены. Конечный proper-profile
  успешно повторил весь выбранный набор, включая corrupt_copy.

Их SHA-256 соответственно
`8b8642026b00c3fc05319056259690cccba17fa67b9dc999ae51986047f72f1d` и
`14c07d1906b04340499e99550a394d44fbfa752362231ecaea7696cc51a22576`.

## Зафиксированные исходники

Семь исходников совпали с начальным inventory исполнителя и не менялись во
время этой проверки. Тесты были усилены после начального inventory и прочитаны
в новой редакции, включая исправленный spy. Конечный inventory содержит
39 записей; все 39 хешей независимо совпали. Его путь:
`.dev/growth/t113-four-category-final-hashes-20261030.json`, SHA-256
`ad170b5c12af18e71fd756a91ff1da7f4daf4d7428708f162cacc81b6cf74b6b`.
Отчёт исполнителя `t113-four-category-20261030.md` перечитан полностью,
SHA-256 `3d4947412ef070e989342f9332f27b220e41bf460a5bf812774584d283775458`.

| Файл относительно корня | SHA-256 |
|---|---|
| `apps/server/src/twobrain_rec_server/auth/account_closure.py` | `fd40d083ce113020983108793e4a6263f2649018ca10a6913a0ed5200c20f6a3` |
| `apps/server/src/twobrain_rec_server/product_analytics/acquisition.py` | `ab3bf82ff8219f49818333aabe0af7c78b686e4fe7231fc50b0b2fab3266ddd4` |
| `apps/server/src/twobrain_rec_server/product_analytics/activation_operator.py` | `389bfe489469672854ae2e2937caee240d3763d25919fc289543529497bb6edc` |
| `apps/server/src/twobrain_rec_server/product_analytics/legal_basis_lifecycle.py` | `4ba719383e35887d6efb9502317a7daea29e2e6b96b5d2374a03253689ea629a` |
| `apps/server/src/twobrain_rec_server/product_analytics/local_retention.py` | `5354606854636adc90f8521361533d988bd2bbb374189ae46a14efd4c54bd510` |
| `apps/server/src/twobrain_rec_server/product_analytics/restore_replay.py` | `5beb31ebac95b05928f95489f93eeb59e9631a0ac67a37d2f9f821fd592a1118` |
| `apps/server/src/twobrain_rec_server/product_analytics/retention.py` | `c4737f2990b1e2449ad0d9d61a0045b6105cac57d8ee39e8beadea1dab76e43a` |
| `apps/server/tests/integration/test_activation_restore_replay.py` | `5fe9bf497de6e774b434dc5d116ad99eea70a7f22e37d110713dad18742f65f2` |
| `apps/server/tests/integration/test_product_analytics_legal_basis_erasure.py` | `ca1b3333dce7032024549ca711f4d5c3e65d9601ed49be30719591ce3bc29e12` |
| `apps/server/tests/unit/test_activation_restore_replay.py` | `1d600d2cd044636e49579332718fcd9e9da7abd60b1dd7e666af011efcfec4e8` |
| `apps/server/tests/unit/test_product_analytics_legal_basis_gate.py` | `5ea66188cc4a140b2092d5b7dc05b7ffa65f9df212f5f6f41a576395cb17f012` |
| `docs/analytics/product-analytics-legal-basis-records.md` | `3019690348df5b0a3ea072481fc48ec9d2075151b61061845bcd867bf21a80f8` |
| `specs/273-paid-traffic-analytics/contracts/operations.md` | `733f9c5e4b4ff079ed016974d1f759c3100506a5cfbca8c0e4f301e665c85ced` |
| `specs/273-paid-traffic-analytics/data-model.md` | `488833fcc4b8e4841672485b35cfa0161e1f02983d10ad98b52eb71d55bb55f5` |
| `specs/273-paid-traffic-analytics/quickstart.md` | `8934b79f9642dcf9718ef2f526de14ad8a38f33d67e1211caf782fb54c9fca86` |

Прочитаны новые записи tasks/growth-plan/changelog. Закрыт только локальный
подэтап учебной проверки; T113 и коммерческие AC01–AC06 остаются открытыми.
Подтверждение cleanup в этом отчёте основано на прочитанных журналах;
сам проверяющий Docker не вызывал. Выпуск и exact-SHA GitHub CI не проверялись.

## Контрольные списки и исходные документы

Все 117 вопросов перечитаны; отметки проверяющий не менял. Их состояние
подтверждает качество требований и не объявляет готовность реализации.

| Список | Отмечено | Не отмечено | SHA-256 |
|---|---:|---:|---|
| requirements | 16 | 0 | `6755318d0b7a76a9f6439446ad42362272d43859cc6f4b3c045b5c36ad1ed9a2` |
| privacy-measurement | 45 | 0 | `8c390000a2da12cf719348d56c08dcb21d886aac98ba1a90ad3d5c41e141cb4f` |
| security | 27 | 0 | `57f082b0b90faf7a3302db0aa1b9aacd29948641e824578ca4f86eee4dee9cb8` |
| infra | 29 | 0 | `998175e297553cedac7f4d7b2829459fcb3f1b650b3b3b6d072e9065437bfa94` |

По разрешённому для F273 исключению сверены прежние полные чтения по хешам,
повторно прочитаны затронутые разделы и зависимости. Baseline неизменен:

| Документ | SHA-256 |
|---|---|
| constitution | `7616e3d7c8112aa60b1be1cc40594a7dfd25b0870f23b821d7efefd7c23f4ba8` |
| PRD | `0f3ccfcfa60062bb0aae6802eeb0012056a635a30cb9f46f54d1992d0b4f57c2` |
| current status | `25b7f383be47c7160da8e852006ff82019f30a5f9c371fc30baa79238649cd16` |
| product-gates | `9f7072c879490d250053cb7397ad6b9b68fdcde17bdf9367ed874a41e450b5f5` |
| spec | `45bcc14f170951e99813d6aeb0eddbbb413dd64f89cf410da256b6d5e30986b2` |
| legal-basis | `f5c8b5ea1bb2a145f438069dc64b0e3816fb46496de86aecd17d02d47db3d423` |
| research | `e1e91d00165b3abafbedf061901400dbc2fc8f6fa70d994d0eeba58de3243d5f` |

Изменён только этот независимый отчёт. Код, spec/plan/tasks, тесты,
контрольные списки, Git/GitHub, БД, процессы, Docker/SSH, GRAF Dev,
рабочая конфигурация и выпуск проверяющим не изменялись. Память других
диалогов не использовалась.
