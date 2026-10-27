# Независимое ревью промежуточной реализации T113 — 28.10.2026

**Решение: SCOPED PASS реализованного фундамента T113.** После исправления R1 открытых Critical/High/Medium дефектов в рассмотренном коде не обнаружено. Это не завершение T113, не включение аналитики, не выпуск и не подтверждение роста/продаж.

Проверяющий: `/root/activation_requirements_gate`. Дата UTC: 2026-10-27T21:17:08.291420+00:00. Lane: независимое ревью активного high-risk Spec Kit среза F273. Навык code-reviewer прочитан и применён. По назначению изменён только этот отдельный отчёт; предварительная история находки сохранена в локальном `.dev/growth/t113-ledger-code-review.md`. Reviewer-owned checklist не изменялся: это проверка кода, прежний PASS требований не подменён новым runtime PASS.

HEAD основы: `b83a82be32f935358440df9083246fc06a94131f`, ветка `codex/273-activation-ledger`. Реализация находится в незакоммиченном diff; SHA основы не идентифицирует изменённые байты. Точный снимок файлов указан контрольными суммами ниже. Digest10 файлов кода/теста/inventory: `d8942bebe95592c474cc8329023f9ab247864bde9852c35b74bf3a1f56c65d86`. Формат digest — SHA256 компактного JSON mapping path→SHA256 с sort_keys=True.

## Границы назначения

Проверены model/export, tenant-context allowlist, migration0106, SQL admission/claim/finish/quarantine и focused ledger tests. Дополнительно по назначению проверены retention-категория, level2/local-delete disposition, purge в finalize_account_close и active-account FOR SHARE, storage-relations. Сверены принятые activation/data/operations/quickstart контракты, смысл own changelog fragment и сохранение G015 открытым.

Ingress/реальные product triggers/principal/legal/readiness wiring и maintenance delivery в этот участок не входят и ещё не подключены. Старый ingest и runtime flags рассмотренным diff не заменены. Реальные копии/restore, внешние провайдеры, production, пользовательские аккаунты/встречи/платежи не проверялись и не менялись. Другие участники работают в общей копии; их изменения сохранены.

## Проверенные выводы

| Область | Независимый вывод и основание |
| --- | --- |
| Уникальность | Unique(account_id,event_name) + закрытые5 account events ограничивают число строк5 на аккаунт. event_id unique и детерминированный UUIDv5 по namespace/account/event. First_open не принимается как account-веха. |
| Неизменность | BEFORE UPDATE trigger в0106 фиксирует id/account/event/event_id/occurred_at/accepted_at/safe_payload/source_kind. Повтор admission читает прежнее решение и не заменяет campaign/time/payload. |
| Атомарность | Один INSERT ON CONFLICT DO NOTHING создаёт решение и2 fixed intents в транзакции вызывающего кода. helper не делает commit и не вызывает транспорт. Rollback до commit не является принятием. |
| Payload | Trusted account UUID сверяется с серверным псевдонимом; source_kind только browser/desktop/server; unknown provider/event отклоняются. Payload заново проходит существующий build_activation_event allowlist/forbidden-fields boundary; future/naive timestamp и JSON>16KiB отвергаются. DB отдельно ограничивает JSONB object/UTF8 size16384 и state/reason. Это сохранение существующей проверки полей, не обещание семантически распознать частный текст, спрятанный в разрешённое поле; будущий ingress должен формировать проверенные метаданные по контракту. |
| Право попытки | claim — условный UPDATE pending/pre_send_retry→dispatching с новым attempt_id; блокировка и повторная проверка WHERE исключают вторую конкурентную claim. До транспорта будущий worker обязан commit. |
| Завершение | finish требует id + dispatching + точный attempt_id. Technical pre-send допускает retry, HTTP success остаётся submitted, timeout/неоднозначность не повторяются автоматически. Второй получатель не изменяется. |
| Recovery | Обычный quarantine переводит dispatching старше60с в ambiguous. После restore переводит pending/pre_send_retry/dispatching/submitted в ambiguous. Не открывает admission и прямо не претендует обнаружить missing post-backup rows. |
| RLS | Account branch сравнивает account_id с rec_current_user_id. Оба cross-account maintenance branches требуют точный session_user twobrain_rec_maintenance; существующий app account_merge путь rec_maintenance_allowed не обходит этот guard. USING и WITH CHECK заданы вместе; FORCE RLS включён. |
| Retention/lifecycle | activation_milestone_decisions зарегистрирована until_decision/graf_postgres, включена в level2 и DISPOSITION_DELETE/local statement. Отдельный deadline обязателен для category erasure; нет возврата возрастной очистки. |
| Account close | Purge WHERE account_id=request.requested_by_user_id в той же транзакции; сохраняются count/time. Admission берёт активный UserIdentity FOR SHARE, close использует FOR UPDATE: статически поздняя вставка после closed не разрешается. Текущий тест проверяет последовательный late admission; обе очередности конкурентных транзакций ещё отдельно не испытаны. |
| Inventory | Relation зарегистрирована в storage-relations; это регистрация, а не рабочий размер/рост/backup receipt. |

## Исправленное замечание R1 — P2, rollback и FORCE RLS

Первоначальная downgrade0106 делала SELECT EXISTS под FORCE RLS без гарантии полной видимости. Non-superuser/NOBYPASSRLS owner без контекста мог видеть0 строк, сохраняя право DROP TABLE; непустой ledger мог быть принят за пустой. Текущий production compose использует rec-migrate пользователя twobrain_rec, поэтому находка не являлась утверждением о наблюдаемой production-потере.

Исполнитель добавил SET LOCAL row_security=off после ACCESS EXCLUSIVE lock и до EXISTS. При применении RLS запрос теперь завершается ошибкой вместо ложного «пусто». В новом DB-тесте реальному owner передано владение таблицей, проверены0 видимых строк, RLS-ошибка downgrade, сохранение обеих строк и версии0106. SQL и тест перечитаны; текущий законченный focused журнал подтверждает выполнение. R1 закрыт в этом снимке.

## Проверки и доказательства

Самостоятельно прочитан законченный `.dev/growth/t113-ledger-focused-20261028.log`:

- **89 passed,2 warnings in19.97s**;
- runner focused status=pass, duration23с;
- isolated_container_removed и postgres_test_result=pass;
- collection_count89, digest e03e86210efacb4b51245a8e995a11e1fb18042147575d1a2870506725cc4943;
- warnings: повторный импорт pytest fixture module и Starlette/httpx deprecation.

Команда исполнителя из его прочитанного implementation-report:

```sh
bash apps/server/scripts/run_local_postgres_tests.sh --focused \
  tests/contract/test_activation_milestone_ledger.py \
  tests/unit/test_product_analytics_milestone_dedupe.py \
  tests/unit/test_account_closure.py \
  tests/unit/test_product_analytics_retention_rules.py \
  tests/unit/test_product_analytics_legal_basis_lifecycle.py \
  tests/integration/test_product_analytics_legal_basis_erasure.py -q
```

Проверяющий тесты не запускал; независимо сверены текущий код, полный ledger test, relevant fixture sections и завершённый журнал исполнителя. prepare_schema применяет настоящие Alembic migrations; это не только metadata.create_all. Дополнительный fixed-role тест использует собственный loopback-only PostgreSQL cluster и cleanup fixture, не рабочий сервер.

В tests действительно есть8 concurrent admissions, rollback,6 outcome-вариантов finish с attempt-owner/independent-provider checks, quarantine/retry deny, identity/event/source/provider/time/size rejection, immutable trigger/reason checks,2 аккаунта×5 событий, category deadline, account-close isolation/late rejection, empty round-trip и populated downgrade guard.

Новый role-test подключается отдельными login URL app/maintenance и проверяет session_user. Без контекста строки не видны; точный maintenance видит2 строки; app не получает cross-account чтение через подставленный maintenance context. Настоящий app request видит/обновляет свою строку; чужие UPDATE/DELETE дают0 на существующей второй строке, чужой INSERT получает RLS-отказ; транзакция откатывается. Non-bypass owner guard описан выше.

Граница account_merge test: перебирается operation=account_merge при context_kind=maintenance; это не полноценный валидный app account_merge proof/context_kind=account_merge. Статически обязательный session_user maintenance оборачивает rec_maintenance_allowed целиком и закрывает app даже при true merge-helper. Полный валидный merge regression можно добавить в следующей интеграционной приёмке; текущий тест не назван таким доказательством.

git diff --check выполнен проверяющим после финальных изменений: PASS. Исполнитель сообщает ruff check PASS в implementation-report; самостоятельного запуска ruff в этом read-only назначении не было. Исходные29 PASS и ранний89/21.59с относятся к предыдущим снимкам и не использованы вместо последнего журнала. Журнал не содержит самостоятельного source-SHA receipt; ниже он привязан к текущим байтам, а exact-SHA PR CI остаётся отдельным gate.

## Обязательный остаток до завершения T113 и рабочего включения

1. Единая trusted admission boundary обоих HTTP ingress, server-auth и реальных product triggers; browser/desktop совместимость. Наличие SQL helper не доказывает вызов отправителя.
2. Текущие legal/readiness/provider/advertising-purpose gates перед admission и каждым side effect, отсутствие fallback при unknown, защита продукта при analytics/DB failure. Примитивы намеренно полагаются на будущего trusted caller и не являются законченным публичным API.
3. Ограниченный maintenance dispatcher, commit claim до сети, per-provider transport classification и отдельный readback confirmed. Функция finish сама не доказывает отсутствие отправленных байтов для technical_pre_send.
4. Реальные GRAF DB backup/restore receipts, quarantine и refusal missing account+event при unknown gap, повторное применение category/account deletion после restore, актуальные retention/runtime/inventory/capacity receipts. SQL quarantine один не открывает readiness.
5. Параллельный account-close/admission тест в обеих очередностях; полноценный валидный app account_merge regression и сквозная role/principal проверка в интеграции. Прямые DB тесты не заменяют пользовательскую приёмку.
6. Converge, exact-SHA GitHub checks, общий замороженный кандидат/full CI, выпуск/выкладка и рабочее чтение результата. T113/T112 и G015 остаются открытыми; аналитика/IP автоматически не включаются.

Own fragment и implementation-report описывают промежуточную основу и ограничения. В growth plan G015 остался `[ ]`; новая ссылка/89 проверок не названы работающим отчётом, трафиком или продажей. В текущем ограниченном назначении нет основания закрывать задачу целиком.

## SHA-256 проверенного снимка

- `apps/server/src/twobrain_rec_server/db/models/product_analytics.py` — `fbf089996f1a6c611c5549524d52832608e78e8eae9a77cf70ed2c49972e897d`
- `apps/server/src/twobrain_rec_server/db/models/__init__.py` — `aa485e85834435a51c2bf1a0589685e0dffd9544dfaac696d20da6455d873c01`
- `apps/server/src/twobrain_rec_server/db/tenant_context.py` — `a7dc09e2b153344d5d3cf2f71dedaffba875995460d13342ad19389885b1762c`
- `apps/server/src/twobrain_rec_server/db/migrations/versions/0106_activation_milestones.py` — `e73a4b8777d759323e372197671d4e56451ae7cc5759f95dd19982f46d7a4c6d`
- `apps/server/src/twobrain_rec_server/product_analytics/milestones.py` — `66cfaf82dbecba8bd52b1136d5eafe107715cb70314d50c630f4c0b20c37f3f9`
- `apps/server/src/twobrain_rec_server/product_analytics/legal_basis_lifecycle.py` — `e6da1fb9eb14b34c2663448691f79a35dac0effb006d721967a08394dea1c69c`
- `apps/server/src/twobrain_rec_server/product_analytics/retention.py` — `c7fb1dd4b2c0e3f1fcf88710e187504b2b0967368ca89d119dd3851c9479d434`
- `apps/server/src/twobrain_rec_server/auth/account_closure.py` — `dda69cfb695cc77e50819db40b2cca56a85767454bd7b94012e7764ddb603b71`
- `apps/server/tests/contract/test_activation_milestone_ledger.py` — `4d4d34e5f0fc1c7c7c5201afcd6c4939dbf9bf58f934a3d30cce6b10bc792035`
- `infra/posthog/storage-relations.txt` — `5d38676a2c489724637bd613ad40d479bff4d47833f363453365da5b12c22d13`
- `specs/273-paid-traffic-analytics/contracts/activation-milestones.md` — `2bba8a3fa0a7040591664343158e4d0b3b1045cfe356a96e3e30e2f93fa4adc5`
- `specs/273-paid-traffic-analytics/data-model.md` — `52fb96e3dd9c399c741a9c982916fd755a056580efdd36539bfc7f1a91cc74be`
- `specs/273-paid-traffic-analytics/contracts/operations.md` — `f696f7b87024783dad0a28ab84af0c7b3dc2329a595eb470c256232a3797c0fb`
- `specs/273-paid-traffic-analytics/quickstart.md` — `c8fdc2c68ffc8e3aa86ed32b250603022e643df4e4f3ede3091a073fe1b05479`
- `apps/server/tests/fixtures/postgres_test_database.py` — `9975596c2901035e2f58fe16481a19d1bc4d3924e8b3a00b1da69cfe80df505b`
- `changes/unreleased/F273.yaml` — `fa8d5287ef269fb735be5add15c243f73c67357ff69abe77a2df3a9c3f6cc84b`
- `docs/growth/organic-growth-plan.md` — `b69e22803b42d5187d8bce86df0d0c824d04fdfeacdb238e159d18a5217452fb`
- `specs/273-paid-traffic-analytics/validation/t113-ledger-implementation-2026-10-28.md` — `130915709724e09528bad976362188bb38bd2f78a75b0fbfb54229646eb375c5`
- Локальный завершённый журнал `.dev/growth/t113-ledger-focused-20261028.log` — `2133d6d00b9ce54e32d8f725335437e66ff1e80005d2b8e58329665b1b84ebbe`.

До и после записи отчёта контрольные суммы входов повторно совпали. Изменён только этот отдельный отчёт; код, требования, tasks, checklist markers, Git/GitHub, commits, runtime и данные проверяющий не менял.


## Повторное независимое ревью после CI — 28.10.2026

**Решение: SCOPED PASS узкого исправления регрессий CI.** Новых замечаний в этом дополнении нет; все перечисленные выше обязательные остатки T113 сохраняются. Проверка не закрывает T113, account-merge/deletion-lineage приёмку, включение аналитики, выпуск или доказательство трафика/продаж.

Основа: HEAD `7a674b2a44d97b34a761f8500d21f3359ad918a9`, ветка `codex/273-activation-ledger`, PR #7774; ниже проверен ещё незакоммиченный follow-up. Проверяющий независимо перечитал точный diff трёх тестов и двух аннотаций миграции, необходимые реализации и оба законченных журнала. Самостоятельного повторного запуска тестов в этом назначении не было. Сохранено ограничение записи только в этот отчёт.

1. В `test_worker_schema_head_is_derived_from_packaged_migrations` ожидание0105 заменено на0106. Реальная `packaged_schema_head` читает Alembic ScriptDirectory из поставляемой конфигурации и требует ровно один head; production-проверка сравнивает фактическую версию БД именно с ним. Ожидание0106 соответствует добавленной миграции; проверка не ослаблена.
2. В FK inventory добавлена `product_activation_milestones.account_id: historical_only`. Inventory тест сравнивает полный набор FK к user_identities с явной таблицей политик. Финализация `confirm_merge_intent` сохраняет source UserIdentity, меняет статус на merged и merged_into_user_id на survivor; ledger там не переносится. Admission принимает только status=active, а immutable trigger сохраняет исходный account_id решения. Следовательно историческая ссылка на исходный аккаунт корректна; эта классификация сама по себе не даёт права новой доставки и не доказывает полный merge/deletion-lineage сценарий.
3. В интеграционном `test_production_share_head_upgrades_to_regeneration_merge` ожидание результата upgrade legacy0037→head обновлено на0106. Остальные утверждения схемы не удалены. Проверка отдельного регионального перехода0104→0105 не изменена.
4. В0106 только `revision` и `down_revision` получили аннотации `str` и `str | None`. Значения и SQL остались прежними. Это соответствует существующей проверке всех файлов миграций через regex `^revision: str = ...`; сама проверка не ослаблена.

Независимо прочитаны завершённые журналы:

- `.dev/growth/t113-ci-regressions-20261028.log`: **17 passed,2 warnings in0.30s**, runner3с, collection_count17/digest `1aa6557130d83257d0aa25e6ce978fff7ee82062bd4abea676aebf150d3889c3`; cleanup=`container_not_started`, result=pass. БД-контейнер для этого прогона не запускался.
- `.dev/growth/t113-migration-regressions-20261028.log`: **17 passed,2 warnings in23.20s**, runner27с, collection_count17/digest `0c9114d65f08bcd03ae260fc594d8033752ccf395fd6aaad1d0c45ab57dcc3c4`; cleanup=`isolated_container_removed`, result=pass. Это весь integration/test_postgres_migrations.py, включая upgrade до head и проверку формата revision.

Оба предупреждения — прежние pytest fixture import rewrite и Starlette/httpx deprecation. Ruff четырёх затронутых файлов сообщил исполнитель; в этом read-only назначении проверяющий его не запускал.

Основной журнал89 проверок и9 из10 исходных файлов сохранили ранее записанные хеши. Единственное изменение10-го файла — рассмотренные выше две аннотации миграции; исходный digest `d8942bebe95592c474cc8329023f9ab247864bde9852c35b74bf3a1f56c65d86` остаётся историческим. Текущий digest10 (тот же формат sort_keys=True, compact JSON path→SHA256): `f16880a13480a2c9eaff936f9b173eed4467506afbbb3cacd10e7ee776aa9493`. Основные89 проверок не называются повторным прогоном нового полного снимка.

### SHA-256 узкого дополнения

- `apps/server/tests/unit/test_playback_normalization_worker.py` — `aea4ed490f63240a54c98dc81136713613202016442d5ad5083a226671f1b296`
- `apps/server/tests/unit/test_account_merge_policy.py` — `04575f95327618ffb52bd927c4ba2883a31501ab2276f3823d0bd59913632c89`
- `apps/server/tests/integration/test_postgres_migrations.py` — `2cb8fed7f25066dbddb3ba17b17e7deee27243ba40d5c84569b12aebd0a5841a`
- `apps/server/src/twobrain_rec_server/db/migrations/versions/0106_activation_milestones.py` — `7e464638f72e3fb240e2af048bcdb25022cb9101df3405aaa14068e7b1386898`
- `apps/server/src/twobrain_rec_server/normalization/worker.py` — `ab50b798c107f888bf0aa8488a58b12d5029c2d4e720f3eccefef3890eca6b63`
- `apps/server/src/twobrain_rec_server/auth/account_merge.py` — `7840869e398b8f621d78c27119a7ecbba15f4f6058fac1d7f54e1dd4f598e205`
- `.dev/growth/t113-ci-regressions-20261028.log` — `ff7061bae961874b80886add19ed04ec7997fba31b01e0ec542637b38dd0b115`
- `.dev/growth/t113-migration-regressions-20261028.log` — `5723bdffe7aac18a45a36c54b45eb251111e7736a05cc2b2c40ed73ecc1552b3`
- `.dev/growth/t113-ledger-focused-20261028.log` — `2133d6d00b9ce54e32d8f725335437e66ff1e80005d2b8e58329665b1b84ebbe`

До и после записи дополнения хеши входов сверены и совпали. `git diff --check` выполнен проверяющим. Новый commit изменит SHA; GitHub governance-fast/macos-pr/pr-metadata и проверку актуальной базы требуется принять для нового точного SHA. Это дополнение не подменяет полную проверку кандидата и рабочую приёмку.
