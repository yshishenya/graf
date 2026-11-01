# Quickstart and validation matrix

## T077: внутренний отчёт — 01.11.2026

Первый шаг [O1–O8](contracts/operator-observation.md); пока требования,
не выполненная проверка. Active Spec Kit slice/high-risk. До кода —
независимый reviewer-owned checklists/operator-observation.md и analyze.
Все исходные 87 задач сохраняются, T077/#4932 остаются открытыми.

1. Штатный одноразовый PostgreSQL runner: unit/test_billing_monitoring.py
   и integration/test_billing_monitoring_postgres.py. Реальные restricted
   logins/forced RLS, не подмена guard. Сначала RED отсутствующего CLI;
   затем `python -m twobrain_rec_server.cli.billing_monitoring --date 2026-10-31`
   из apps/server с синтетической конфигурацией через штатное окружение.
2. Пустые подключённые источники дают нули, неподключённые семейства null.
   Набор с разными состояниями/опасными snapshot полями подтверждает
   закрытые группы, unrecognized, operation age/received queue age,
   отсутствие ложного transport lag/unknown duration/суточных успехов.
3. Под настоящими app/worker/superuser/SET ROLE и неверными контекстами
   получить отказ до предметных чтений. Верные maintenance identity/context
   проходят только в READ ONLY REPEATABLE READ. Mutation probe запрещена БД.
4. Два соединения: читатель закрепляет снимок; writer держит registry lock,
   заменяет принятый результат и коммитит. Читатель после lock видит прежний
   согласованный снимок, новый процесс — новый. Единый as_of, отдельный
   finished_at; будущая дата не становится ложным нулевым возрастом.
5. Ошибка подключения/identity, lock/query timeout, >500 detected gaps,
   >64 KiB stdout или несовместимая схема дают exit 1 и только безопасный
   отказ целого отчёта, без частичного результата. Успешно прочитанные
   неизвестные состояния и будущие времена дают завершённый JSON с exit 0,
   coverage=partial, закрытыми unrecognized/null и reason_code по O3/O4.
   В обоих случаях SQL/URL/traceback и сырые значения не выводятся.
6. Новый процесс повторяет чтение без provider HTTP/почты и без изменения
   строк/финансов/прав/согласий. Registry missing/unverified, files_complete
   против financial_status=not_checked, исходные owner/deadline сохранены;
   чужой магазин не попадает в текущую registry-область.
7. Сохранить команды/versions/SHA/counts/ограничения, провести независимое
   кодовое ревью/converge и три точных PR gates. Не повторять прежние498
   тестов PR7877 без новой причины. Full/CD/Dev/реальные деньги не требуются.

O6 сохраняет полный обязательный остаток источников, регулярности, тревог
и реакции. Финансовые/приватностные сроки действуют независимо от того,
подключено ли семейство к первому отчёту. Один удачный JSON не закрывает T077.

## T077: следующий срез free_projection — 01.11.2026

Это план проверки P1–P6 [O9](contracts/operator-observation.md#o9-следующий-срез-события-free_projection),
не её результат. До кода — независимый PASS checklists/free-projection.md,
scoped analyze и существующая #4932. Использовать уже существующий runner
изолированной PostgreSQL/forced RLS, owned apps/server/.venv и PYTHONPATH=src:.
из apps/server; проверить __file__, не чужой editable checkout.

1. RED нового event_window в tests/unit/test_billing_monitoring.py и
   tests/integration/test_billing_monitoring_postgres.py. Затем focused pytest
   через этот же интерпретатор, только новые случаи и реально затронутые
   прежние. Окончательные 26 и 3 повтора PR7884 не складывать и не повторять
   без изменения/отказа. Стенд удалить штатным finally, сохранить XML/log/SHA.
2. В настоящем CLI → maintenance guard → PostgreSQL разместить синтетические
   audit-строки на start−1µs/start/end−1µs/end и as_of−1µs/as_of/as_of+1µs.
   Проверить счётчики, UTC полуночи, day elapsed, current partial и future
   unavailable; будущий день и непредставимые 0001-01-01/9999-12-31 не нули.
   Для исторического смещения Москвы обе полуночи переводятся отдельно.
3. Проверить три допустимые пары, невозможную blocked/unknown_pending,
   NULL reason и неожиданный target_kind; только закрытая unrecognized группа.
   Другой action не входит. Повторить пустой источник и приоритеты reason_code
   при нескольких признаках. count равен сумме групп наблюдаемого интервала.
4. Schema fixture должна повторять nullable created_at миграции0044,
   а не только предположение ORM. NULL создаёт inventory undated_count;
   строки выбранного дня >=as_of — отдельный счётчик без ошибки часов.
   В закрытом дне без gaps — настоящий ноль/complete_declared_source.
5. Два соединения: writer фиксирует PostgreSQL transaction_timestamp(),
   читатель закрепляет RR, writer сохраняет audit-событие с default now()
   и коммитит позднее. Старый снимок неизменен; новый видит новое число.
   Отличие времени начала/commit доказать настоящей транзакцией; закрытый
   отчётный день моделировать явным as_of после end в collector, без ожидания
   реальной полуночи. Это синтетическая временная граница, не реальное
   календарное наблюдение; clock/записи рабочей БД не менять.
   Отдельно видимая запись >=as_of
   остаётся вне основного count даже после подключения читателя.
6. Синтетические запрещённые metadata/target_ref/IDs не попадают в stdout/
   stderr; SQL этого семейства их не выбирает. Сравнить данные до/после,
   повтор из нового процесса, forced RLS/read-only mutation denied и
   отсутствие HTTP/почты. Ошибка схемы даёт безопасный отказ всего отчёта.
7. После фактического PASS — независимое кодовое review/converge, профильные
   repository checks и три точных SHA/base PR gates. PR только Refs #4932;
   O6/FR089/T077 [ ] остаются, Full/CD/Dev/финансовая приёмка отдельно.

## T077: сроки fair-use проверок — 01.11.2026

F1–F6 [O12](contracts/operator-observation.md#o12-следующий-срез-сроки-сохраняемых-fair-use-проверок),
те же unit/integration файлы, настоящий CLI и отдельная PostgreSQL.
Сначала независимый допуск/анализ; это план, ещё не результат тестов.

1. RED нового collector. Пустое: source fair_use_reviews/inventory/current_state,
   partial, count0/groups[], pending_review все0, deletion/reaction null;
   ошибка схемы должна давать отказ всего CLI без частичного JSON/traceback.
2. Все5state, сортировка/сумма; confirmed не включается в pending buckets.
   На едином as_of проверить start ±1мкс/равенство, review_by ±1мкс/равенство,
   нулевой срок, ровно24ч, будущее. Четыре buckets взаимно исключаются и
   суммируются в pending count, независимо от report_date; возраста/дат нет.
3. Реальная схема сохраняет NOT NULL/state/deadline CHECK и ENABLE/FORCE RLS.
   Проверить отказ неверных state/NULL/обратных/>24ч дат. Сохраняемые infinity
   проверить как invalid_schedule без subtraction error. Отдельный синтетический
   SQL-вход проверяет NULL/неизвестные/обратные/>24ч ветви и приоритет
   unrecognized→invalid_schedule→deletion_and_reaction_uninstrumented; не
   ослаблять положительную схему. Проверить24истекших часа на DST timezone.
4. Настоящие CLI/guard/new process/два снимка: конкурентный commit не меняет
   уже зафиксированный RR, новый запуск видит его; повтор не пишет. Fingerprint
   таблиц, частные synthetic sentinels в capability/evidence/appeal/IDs не
   выходят в stdout/stderr. В запросе нет частных столбцов; provider/почта=0.
   Затронутые прежние PG сценарии ролей/SET ROLE/READ ONLY/schema failure
   проверить минимально, сохранив лимиты O2 и cleanup.
5. Owned apps/server/.venv и PYTHONPATH=src:., проверить __file__. Сохранить
   окончательные nodeids/XML/log/hashes, не складывать повторы. Независимые
   review/converge и точные SHA/base PR gates. Только Refs #4932; T077 [ ],
   весь O6/FR089/сроки/финансовая/приватностная приёмка остаются открытыми.

## T077: сохранённые наблюдения возвратов — 01.11.2026

План R1–R6 [O11](contracts/operator-observation.md#o11-следующий-срез-сохранённые-наблюдения-возвратов),
не результат. До кода: независимый checklists/refund-inventory.md,
scoped analyze/прежняя #4932 и собственные чтения текущих оригиналов.
Из apps/server использовать owned .venv/PYTHONPATH=src:. с проверкой __file__;
новые unit/PG случаи выбираются через `-k refund_inventory` в существующих
tests/unit/test_billing_monitoring.py и
tests/integration/test_billing_monitoring_postgres.py. Использовать прежний
изолированный PG runner; не запускать всю старую приёмку без новой причины.

1. Сохранить RED отсутствующего источника. Настоящий CLI→guard→forced RLS
   PostgreSQL: пустое даёт count0/groups[], оба null, partial с причиной
   receipts_and_reconciliation_uninstrumented; это не unavailable/PASS денег.
2. Создать несколько синтетических частичных refund rows одного invoice,
   succeeded/provider_observation и неизвестные status/source, включая
   известный status с неизвестным source. Ровно закрытые sorted status/count,
   count=sum(groups), unrecognized приоритетнее причины неподключённых метрик.
   Реальные status/source NOT NULL не ослаблять; отказ NULL INSERT доказать
   отдельно. CASE NULL-защиту проверить на SQL-форме без изменения схемы.
3. Разные environments, report_date, NULL/будущие observed_at не фильтруют
   inventory и не создают возраст. Между двумя соединениями закрепить RR
   до commit новой строки: старый отчёт неизменен, новый снимок/новый CLI
   процесс видит строку. Повторное чтение не меняет fingerprint таблиц.
4. Синтетические суммы/валюта/IDs/связи/environment/JSON/даты не выбираются
   SQL семейства и не попадают в stdout/stderr. Provider GET/POST, reversal,
   почта=0. Несовместимая схема/нет доступа — безопасный отказ всего отчёта,
   без traceback/SQL/частичного JSON и без нулевой подстановки. Выполнить
   только затронутый минимальный прежний набор identity/SET ROLE/read-only.
5. Сохранить XML/log/hashes, удалить только свой одноразовый контейнер
   штатным finally. Независимые code review/converge и exact-SHA/base PR
   gates обязательны. T077[ ]/#4932 OPEN, весь O6/FR089/сроки и внешние
   приёмки сохраняются; чеков/тревог/финансовой сверки этот срез не принимает.

## T077: сохраняемый реестр бонусных дней — 01.11.2026

План C1–C6 [O10](contracts/operator-observation.md#o10-следующий-срез-сохраняемый-реестр-бонусных-дней),
не результат проверки. До кода обязательны независимый допуск
checklists/credit-ledger.md, scoped analyze и исходная #4932.
Owned apps/server/.venv/PYTHONPATH=src:. и существующий isolated PostgreSQL
runner/forced RLS, проверенный __file__; прежние10/26/3 PASS не повторять
без затронутой зависимости, не складывать новые и повторные случаи.

1. RED нового источника в существующих unit/test_billing_monitoring.py и
   integration/test_billing_monitoring_postgres.py; затем только новые и
   реально затронутые focused случаи. Сохранить XML/log/SHA, удалить свой
   одноразовый PostgreSQL штатным finally; рабочие данные/Dev не использовать.
2. Настоящий CLI→guard→PostgreSQL: пустой источник (count0/groups[], четыре
   нуля/возрастnull, family partial/jobs_uninstrumented), затем все шесть
   состояний, отрицательная reversal и неизвестные приватные строки/NULL
   state там, где это разрешает тест формы SQL. Реальную NOT NULL схему
   не ослаблять ради NULL: PostgreSQL должен отвергнуть такой INSERT.
3. Pending/available с maturity и expiry за1мкс до/ровно/после as_of,
   expires=maturity и expires<maturity, терминальные с совпавшими датами:
   четыре непересекающихся количества, сумма=count только pending/available,
   max возраст из допустимых достигнутых maturity, будущая maturity нормальна.
   Неизвестная группа приоритетнее invalid_schedule, затем jobs_uninstrumented;
   количества сохраняются независимо от выбранной причины.
4. Два соединения: закрепить старый RR-снимок до writer commit новой credit
   строки; прежний отчёт неизменен, новый снимок/новый CLI процесс видит новое.
   Зафиксировать общий as_of; report_date не фильтрует current_state реестр.
5. Синтетические days/source_ref/IDs/capacity/applied interval не выбираются
   SQL семейства и не попадают в stdout/stderr. Сравнить таблицы до/после,
   не запускать начисление/reversal/почту/provider. Настоящие identity/SET ROLE/
   forced RLS/read-only проверки повторить только затронутым минимальным набором.
   Несовместимый столбец/недоступная таблица даёт отказ всего отчёта, не нули.
6. Независимое кодовое review/converge и exact-SHA/base GitHub gates.
   Только Refs #4932; T077[ ], полный O6/FR089/исходные сроки и внешние
   финансовая/приватностная/ручная/выпускная приёмки сохраняются.

## Сверка требований интерфейса — 2026-10-30

Полоса: `active Spec Kit slice`, только согласование документации T079/T083
с действующей конституцией §VII. FR-081, plan, research R6 и два связанных
контракта проверяются вместе: допускаются наблюдаемые Krisp UX/UI/IA
и функциональные подписи; обязательны независимый код, права на материалы,
правдивые тексты GRAF и доступность. Прежний запрет совпадения исключён.
Исторические отчёты и исходные описания задач не переписываются.
Независимый reviewer проверяет четыре затронутых пункта существующих
чеклистов и считает весь набор. Эта правка не является новой визуальной
приёмкой, не завершает T079/T083 и не даёт допуска к реализации T062.
Остальные противоречия и неподтверждённые пункты остаются открытыми.

## Повторная проверка операторского импорта T075 — 2026-10-30

Ограниченная реализация [контракта B1–B3](contracts/registry-operator-import.md)
проверена на синтетических данных и отдельной одноразовой PostgreSQL.
Результаты, исправленные отказы и границы:
[отчёт реализации](t075-import-implementation-20261030.md).
GRAF Dev и рабочий магазин не затрагиваются. Следующие шаги позволяют
повторить приёмку файлов; они не заменяют финансовую сверку всей T075.

1. Выполнить профильные registry tests и проверки
   CLI/DB тем же Python окружением сервера. В argv/stdout/отчёт не выводить
   реальный DB URL, путь исходного экспорта или финансовые данные.
2. Сначала dry-run, затем `python -m twobrain_rec_server.cli.billing_registry
   import --date 2026-10-29 --payments <synthetic-file> --refunds <synthetic-file>
   --owner billing-operations --operator test-operator --execute` под фактической
   служебной ролью. Для корректного zero-row CSV добавить соответствующий
   `--expect-empty`. Указанные пути — условные обозначения, не секреты.
3. Завершить процесс. Новый процесс `...billing_registry status --date
   2026-10-29` обязан вернуть сохранённый receipt/counts/completeness/gaps,
   не читая CSV. Повтор импорта не создаёт второй receipt и не переносит срок.
4. Пропущенная часть/last/вид дают неполноту с owner/deadline; пустой файл без
   ожидания, чужая шапка, duplicate identity, footer mismatch и лишняя часть
   не заменяют предыдущий принятый набор. Исправление требует
   `--replace <current-digest> --reason corrected_export`; устаревший digest и
   два конкурирующих исправления не допускают потерянного обновления.
5. Проверить failure injection до commit и повтор после restart; owner,
   detected/deadline и история gap сохраняются. Только проверенное исправление
   даёт resolved с actor/reason/time/closing receipt. Ошибка сохраняет последний
   принятый набор, но остаётся видимой в последней попытке и открытых gaps.
6. Через настоящие подключения проверить request/worker/maintenance,
   `SET ROLE`, неверные operation/area и `row_security=off`. Отказ нужен до
   чтения входа; app/tenant не видит общие таблицы. Проверить inventory/RLS.
7. В stdout/DB/evidence отсутствуют provider object IDs, суммы, контакты,
   сырой CSV и исходные пути. `files_complete=true` при обоих наборах даёт
   только `financial_status=not_checked`. Для принятия всего T075 отдельно
   пройти CSV ↔ authenticated provider GET/list ↔ ledger, включая обратные
   пропуски, точный день, pagination, неизвестные объекты и provider outage.

После повторной проверки записать команды, версии, результаты и ограничения;
T075/#4930 остаётся открытой. Все исходные задачи и внешние launch gates
сохраняются. Новых issues для этого же остатка не создавать.

## Safety and prerequisites

Use only synthetic users, workspaces, codes, media metadata and provider
objects. Never place real credentials, account/payment ids, emails, receipt
contacts, raw webhook/CSV, screenshots, audio, transcript or meeting content in
committed evidence. Checkout remains disabled outside the isolated approved
environment.

```sh
.specify/scripts/bash/check-prerequisites.sh --json --require-tasks --include-tasks
git diff --check
rg -n 'NEEDS CLARIFICATION|\[FEATURE\]|\[DATE\]|TODO' \
  specs/140-user-account-billing/{spec.md,plan.md,research.md,data-model.md,contracts}
```

Expected: prerequisites resolve feature `140`, diff check is clean and the
implementation-placeholder scan returns no match. Product-market `TBD` markers
are intentionally retained in `research.md`/`plan.md` until external evidence
and approvals exist; they are launch gates, not implementation placeholders.

## Focused implementation validation

Run the smallest changed suite first. Before feature closeout run all four
server groups, the focused macOS handoff regression and the repository fast
lane:

```sh
cd apps/server
uv run playwright install chromium
uv run pytest tests/unit -q
uv run pytest tests/contract -q
uv run pytest tests/integration -q
uv run pytest tests/e2e -q
cd ../..
swift test --package-path apps/macos/Shared --filter DesktopCabinetRoutePolicyTests
infra/scripts/ci-local.sh --fast
```

Use disposable PostgreSQL for RLS/locking/concurrency tests. Provider tests use
YooKassa test shop where supported and synthetic doubles/official-format CSV
elsewhere; real-shop canary is a separate approved release step.

### Runtime verification (2026-08-13)

- Remote `/opt/projects/2brain-rec` is clean at deployed SHA
  `32ce03c2334bc842cbb9871f966432ecf0ac33ca`, migration head
  `0071_fair_use_capability_prefix`; live/ready/root probes return HTTP 200.
- Independent production smoke PASS: config validation, disposable RLS/migration
  probes and metadata-only cleanup (39 database rows, 3 object keys, no residue).
- Live production RLS metadata-only probe PASS: 106/106 application tables in
  the verifier scope are enabled and forced.
- Dedicated YooKassa webhook edge `:8443` PASS: `nginx -t`, TLS 1.2/1.3,
  official IPv4/IPv6 allowlist, `256k`, rate limit and server-side secret
  overwrite. Untrusted probe is 403; direct backend without secret is 401.
- Checkout remains disabled (`TWOBRAIN_BILLING_CHECKOUT_ENABLED=false`). This is
  runtime evidence only; controlled provider delivery/test-shop/real-shop canary and
  four-eyes product/finance/legal/security/QA sign-offs are still required.

### Исторические локальные результаты (2026-08-11)

- `infra/scripts/ci-local.sh --fast`: PASS, 1034 server tests, Ruff and
  Python compile; disposable PostgreSQL container removed after the run.
- `infra/scripts/ci-local.sh --full`: PASS on the current master baseline:
  653 Swift tests, ContractValidation PASS, 2873 server tests passed, 1
  skipped, strict PostgreSQL phase 42 passed (1 skipped), Ruff/Python compile,
  Compose config and deployment evidence scan passed. The local RLS-boundary
  verifier remains intentionally blocked without a production/test database;
  the independent production verifier is recorded above.
- Финальный полный прогон после hardening: PASS, 653 Swift-теста,
  ContractValidation PASS, 2873 серверных теста (1 skipped), strict PostgreSQL,
  Ruff/Python compile, Compose config и deployment evidence scan PASS.
  Дополнительно focused OpenAPI PostgreSQL contract: 10/10 PASS.
- Billing launch contracts and test-shop e2e: PASS, 8 tests. Focused billing
  account/checkout/security/UI contracts: PASS, 57 tests.
- Disposable-PostgreSQL billing lifecycle sample: PASS, 61 tests covering
  account lifecycle, RLS, checkout, webhooks, promos, referrals, renewals,
  storage and subscription controls; the isolated container was removed after
  the run.
- Focused billing lifecycle, notification and subscription tests: PASS; no
  checkout enablement was performed; evidence is committed on the feature
  branch and remains gated from public enablement.
- Latest hardening pass: UI/accessibility/usability contracts 23 passed; focused
  disposable-PostgreSQL billing/account/security suite 72 passed; provider
  refund observation regression test confirms referral reversal uses the
  original payer snapshot after ownership changes. Full fast unit/PostgreSQL
  contour after the latest changes: 1030 passed.
- Public launch remains blocked by the production gates below: real merchant
  test-shop/canary evidence, accessibility/usability and live security review,
  source-retention policy approval, Russia-first JTBD/WTP/COGS evidence and
  finance/legal approval.
- Cross-artifact analyze pass found no unresolved critical implementation blockers; the feature has
  87 tasks (80 validated complete, 7 still open). T036, T047, T053 and
  T075–T077 are implementation-complete with focused evidence; provider IDs and
  anonymous analytics ingress now have explicit boundary guards. T078 remains
  the controlled canary/sign-off gate, alongside T079–T080 and T083–T085/T087.
  This branch is not a public-launch completion claim.
- Billing ownership-loss guard revokes recurring authority under a subscription
  row lock; refund webhook backstop follows YooKassa cursor pages with a bounded
  20-page safety limit. These are covered by focused disposable-PostgreSQL and
  adapter/webhook tests; live provider evidence and manual sign-offs remain open.
- Production migration head is `0071_fair_use_capability_prefix`; fair-use persistence
  is deployed with checkout still disabled. Any future migration must update
  the exact-SHA evidence and rerun the direct RLS probe. Plan and promotion
  catalog rows remain readable in request/worker contexts,
  but inserts/updates require the maintenance role. Webhook bodies are read in
  bounded chunks without relying on `Content-Length`; enabling billing also
  requires non-empty provider, webhook and referral secret files plus a valid
  support address.
- Checkout keeps exact prices out of the rendered page while the store is
  disabled. The discounts screen validates a code without reserving it and
  offers `Применить`/`Удалить`; payment-method removal revokes only GRAF's
  local recurring authority and is refused while renewal remains enabled.
- Лендинг и публичные страницы проверяются отдельным ручным проходом по
  [landing-review.md](../../docs/evidence/140-user-account-billing/landing-review.md);
  серверные тесты не закрывают визуальную, accessibility и moderated-usability
  проверку.
- Registry primitives keep separate payments/refunds report identities,
  completeness hashes and owned metadata-only gaps; notification maintenance
  delivers only verified recipients through the existing Postal sender and
  marks delivery after provider success.
- The post-review hardening pass also passed the chunked-webhook bound,
  non-empty-secret/support-email configuration checks and catalog write-RLS
  contract. These are implementation evidence only; live proxy/RLS and
  merchant canary evidence remain required.
- Финальный локальный hardening-проход после этого evidence: 32 focused
  billing/renewal/maintenance/webhook/security tests passed; renewal не
  переводится generic-stale maintenance в `unknown`, resume требует
  подтверждённую карту и отдельное согласие, webhook без tenant metadata
  возвращает retryable `503`, а checkout CTA скрыт при неутверждённом каталоге.

## Required scenario evidence

### 1. Account, tenancy and trial

1. A new public signup idempotently creates one personal workspace and active
   Owner membership without sharing the configured technical workspace.
2. Owner/Admin/Member and same/cross-tenant matrices prove exact visibility and
   current-role/CSRF/session recheck for every mutation.
3. Unverified identity sees one `Подтвердить email` action and creates zero
   trial activations. After verification, concurrent tabs, linked login methods
   and two personal workspaces still create exactly one explicit seven-day
   activation, no invoice/card/recurring consent, and expiry → Free.
4. Profile/preferences, login methods, session/device revoke and seven-day
   account-close cooling work with re-auth; finalization reuses existing meeting
   deletion/purge and preserves truthful finance/backups/YooKassa boundaries.

### 2. Billing and YooKassa authority

5. Double click, two tabs, return reload and concurrent worker create one
   checkout intent/invoice/operation. Return URL and webhook body alone create
   zero entitlement grants.
6. Test-shop initial payment covers saved=true/false, canceled, 429, timeout/500,
   duplicate/out-of-order webhook, same-key recovery and provider-key expiry.
   Every success is validated through authenticated GET and receipt lines equal
   the provider amount exactly.
7. Zero-amount method replacement remains disabled unless the real/test shop
   proves the required capability; failed replacement preserves the old method.
8. Cancel writes recurring-authority refusal before future provider mutation;
   current term remains. Renewal creates one automatic operation. Confirmed
   failure or unconfirmed cutoff projects Free immediately with no retry/grace;
   unknown blocks pay-again. Late success grants once only without earlier
   refusal; late-after-refusal remains Free and creates one internal incident.

### 3. Free usage, unlimited paid use and storage

9. One Moscow-month Free window is created at `00:00 Europe/Moscow`; timezone
   preference cannot move it. Admission reserves declared whole seconds and
   binds the reservation to that window across midnight; 80%/100% copy is
   separate from storage thresholds. Success commits only unique accepted
   source ranges, an overrun is rejected without negative remaining, overlap/
   retry/chunking adds zero duplicate seconds, and failed/canceled/rejected
   portions release.
10. Trial/`Личный` return `limit_mode=unlimited` for meetings/minutes/
    transcription/AI and never deny from a commercial remaining counter while
    still recording actual-use observability.
11. Catalog/admission assert decimal capacities: Free `250_000_000`, Trial
    `500_000_000`, Personal `2_000_000_000`, add-on totals
    `5_000_000_000`, `20_000_000_000`, `100_000_000_000` and
    `500_000_000_000`. Only active validated canonical
    `meeting-review.m4a` `TrackArtifact.byte_length` counts; current/legacy WAV,
    DB content, replicas, backups, transient/local/deleted artifacts contribute
    zero. Object-stat mismatch, invalid normalization and active-artifact
    supersede are atomic and preserve local custody on rejection; reservation
    races never exceed effective capacity.
12. At 80/95/100% the meter shows used/reserved/available/freshness and text +
    icon. Full/over-capacity preserves read/export/delete/local Record/Stop and
    offers delete, capacity recovery and `Обработать без сохранения аудио`.
    Free consumes accepted seconds; Trial/paid do not. Transient media purges
    within 15 minutes of terminal outcome and no later than 24 hours after
    admission across crash/restart/stuck work.
13. Meeting deletion/account-close finalization immediately revokes access and
    releases playback quota, then places `meeting-review.m4a`, current
    `meeting-transcription.wav` and legacy primary sources into mandatory purge
    without normal recovery-retention delay. Only a formally valid mandatory
    hold may defer physical purge; backups are not user recovery. Normal WAV
    purge starts only after transcript-import and active-playback verification;
    losing either gate reopens recovery and cancels the deadline.
14. Initial base+add-on, positive paid-interval pro-rata upgrade, bonus-interval
    scheduling, downgrade/removal at renewal, concurrent changes and target
    below used bytes all preserve one shared subscription anchor.

### 4. External refund boundary and reconciliation

15. History/invoice detail shows only configured email, safe invoice reference,
    `Написать письмо`, copy actions and warnings. Mailto contains no amount,
    provider id, card data or meeting content. Sending email creates no GRAF row
    or product notification and does not cancel renewal.
16. Source/route/schema tests prove there is no refund form, request/case/status,
    operator mutation endpoint/CLI or YooKassa refund POST in GRAF. The only
    provider refund contract is read-only webhook/GET/list/registry observation.
17. A manual merchant-cabinet full refund and partial refund are each observed
    exactly once via webhook or poll, confirmed by GET, linked to original
    payment/receipt and reconciled with the official refund registry. Missing
    webhook is repaired by poll/registry. No refund status/result appears in
    customer UI; zero refund API mutation calls are issued.
18. Provider-confirmed refund before referral maturity prevents reward; later
    confirmation creates at most one bounded append-only reversal. Entitlement/
    add-on remains unchanged unless a separate explicit audited correction is
    authorized, and recurring authority is never restored.

### 5. Growth, notifications, UX and operations

19. Promo expiry/caps/concurrency/normalization, best-one-only conflict with
    referral discount and payable floor all converge on one immutable invoice.
20. Referral first touch, self-referral/risk review, first monthly/annual
    payment, 14-day maturity, 7/30 days, 180-day rolling cap, Free expiry,
    cancel-scheduled application and reversal produce exactly one ledger truth
    without cash/wallet/negative debt.
21. Transactional notices dedupe by event/recipient/channel/template. Mandatory
    finance/security notices ignore marketing preference; refund correspondence
    is absent from the product outbox.
22. Keyboard-only, screen reader, visible focus, 24×24 targets, compact/mobile,
    200% zoom/reflow, reduced motion, long Russian copy and JS-off critical
    navigation pass. Hosted-provider accessibility blocker has support fallback.
23. Analytics/log/evidence scan finds no amount, raw code/referral token,
    provider/invoice/payment/refund id, method/contact, webhook/CSV payload,
    secret or meeting content. Yandex/session replay are absent on financial
    routes.
24. Missing catalog/add-on price or any required approval fails closed before
    invoice. Stop-all-charges blocks GRAF checkout/binding/renewal while
    preserving cancel/payment-data refusal, history/static support instruction,
    Record/Stop, deletion and export. Backup/restore, migration rollback,
    disk-full and registry-gap drills leave owned metadata-only evidence.

## T078. Canary evidence packet (операционный runbook)

Этот раздел описывает, как собрать доказательства для controlled canary. Он не
является разрешением включить checkout и не заменяет подписи. До выполнения
всех gates `TWOBRAIN_BILLING_CHECKOUT_ENABLED` должен оставаться `false` в
защищённой production-конфигурации; выключенный checkout и есть штатный механизм
остановки оплаты.
В evidence нельзя писать
секреты, содержимое webhook/CSV, реальные payment/refund/provider IDs, номера
карт, email покупателей, аудио или текст встреч. Для связи используется только
локальный `evidence_ref` и хэш/точный SHA релиза.

### A. Разделение окружений

| Граница | Test shop | Production / controlled real shop |
| --- | --- | --- |
| YooKassa | Отдельный тестовый магазин и отдельные API/webhook secrets; идентификатор не коммитится | Магазин `1430118`, отдельные secrets; provider secrets монтируются только в server-side API и maintenance/processing roles |
| Приложение | Изолированный test host, callback и return URL; отдельные DB, object bucket и Temporal namespace | `https://rec.2brain.pro`, production DB/bucket/Temporal namespace; публичный callback принимает только production events |
| Конфигурация | `TWOBRAIN_BILLING_CHECKOUT_ENABLED=false` по умолчанию; включается на короткое окно теста | `TWOBRAIN_BILLING_CHECKOUT_ENABLED=false` до четырёх-eyes approval; выключение checkout остаётся готовым к немедленному применению |
| Данные | Только синтетические пользователи, планы, media metadata и provider doubles/test objects | Только заранее allowlisted synthetic/consented canary identity; не копировать test DB, secrets, receipts или webhook payload в production |
| Ротация | Ротировать test secret после завершения сессии или утечки | Ротировать перед первым включением и после любого инцидента; проверять права файлов (`0600`, владелец deploy operator) |

Перед каждой сессией оператор сверяет `release_sha`, migration head, target
environment и hostname. Несовпадение любой пары останавливает сессию. Test
shop не доказывает production capability: для real shop нужна отдельная запись
своего наблюдения и отдельная подпись.

### B. Формат capability evidence (metadata-only)

Одна запись на одну capability, без provider payload:

```text
evidence_ref: <local-random-ref>
release_sha: <40-char-git-sha>
environment: test-shop | controlled-real-shop
shop_ref: test-shop-<internal-ticket> | production-shop-1430118
observed_at_utc: <RFC3339>
operator_role: <role, no personal secret>
approver_role: <independent role>
capability: initial_payment | saved_method | recurring_charge |
  authoritative_get | webhook_ingest | receipt_observation |
  manual_full_refund_observation | manual_partial_refund_observation |
  zero_amount_binding | renewal_failure_to_free
result: pass | fail | blocked | not_tested
source: contract | provider_test_shop | controlled_real_shop | registry_poll
safe_observation: <bounded outcome, no IDs or payload>
revalidation_due_utc: <RFC3339>
incident_ref: <empty or metadata-only internal reference>
```

`zero_amount_binding` получает `blocked`, если возможность не подтверждена
самим shop; в этом случае self-service replacement остаётся выключенным. Для
каждого `pass` сохраняются только exact SHA, время, bounded result, hash
evidence-файла и владелец gap. Истёкшая запись, смена магазина/secret,
миграции, изменения receipt/VAT/recurring capability или incident автоматически
делают запись `stale` и возвращают checkout в fail-closed состояние.

### C. Test-shop sequence

1. Создать disposable test database/bucket/Temporal namespace и synthetic owner;
   подтвердить, что production hostname и production secret files недоступны.
2. На точном SHA выполнить focused suite и credential-free E2E:

   ```sh
   cd apps/server
   uv run pytest tests/contract/test_billing_launch_gates.py -q
   uv run pytest tests/e2e/test_billing_test_shop.py -q
   cd ../..
   ```

3. В течение разрешённого окна проверить monthly и annual initial payment,
   duplicate/out-of-order webhook, browser timeout, saved-method consent,
   authoritative GET и receipt lines. Объект return URL или webhook сам по себе
   не создаёт entitlement.
4. Проверить один renewal success и один provider-confirmed failure: после
   failure доступ сразу проецируется в Free, без grace/retry; unknown блокирует
   pay-again и не создаёт вторую charge key. Проверить late success/refusal
   precedence и exactly-once grant.
5. В merchant cabinet (не через GRAF) выполнить test-only full и partial refund,
   если shop это поддерживает. GRAF только наблюдает webhook/GET/list/registry;
   ожидается ноль refund mutation calls и отсутствие refund status в UI.
6. Зафиксировать каждую capability в форме B, провести независимую проверку
   redaction/RLS/CSRF и удалить disposable test data по штатной процедуре.

Остановка test-shop сессии обязательна при mismatch amount/currency, receipt,
shop/environment, duplicate grant, unexpected provider mutation, leaked
secret или попытке записать customer content. В таких случаях evidence имеет
`result=fail`, а не `pass`.

### D. Controlled real-shop sequence

Real-shop canary начинается только после заполненных sign-off полей в разделе
E, backup/restore reference и dry-run release gate. Cohort — одна заранее
allowlisted identity и один операторский слот; расширение cohort запрещено до
closeout записи. Обязательная последовательность:

1. Проверить exact SHA, migration/backup evidence, production secret mounts,
   webhook TLS/source filtering, выключенный флаг оплаты и read-only reconciliation.
2. Выполнить base plan + один разрешённый add-on payment. Подтвердить
   authoritative GET, webhook, exact receipt, entitlement и storage projection.
3. Провести согласованный renewal failure → immediate Free (тестовый метод
   провайдера или иной заранее одобренный безопасный сценарий), затем проверить
   no-grace/no-retry и late-outcome precedence. Не создавать вторую операцию.
4. В merchant cabinet вручную выполнить full и partial refund. В GRAF проверить
   только read-only webhook/GET/list/registry convergence, bounded gap ownership
   и отсутствие customer-facing refund result/notification.
5. Сохранить metadata-only packet: exact SHA, capability rows, migration and
   backup references, metrics snapshot, stop/rollback rehearsal result and
   two-person decision. Любая незакрытая gap/неподтверждённая capability
   останавливает rollout и оставляет checkout disabled.

### E. Four-eyes sign-off record

| Gate | Required approver role | Status (`pending/pass/fail`) | `evidence_ref` | Valid until / trigger | Date + initials |
| --- | --- | --- | --- | --- | --- |
| Product: plan, storage ladder, fair-use and cohort | `product` | `pending` | `<ref>` | `<date/trigger>` | `<date / initials>` |
| Finance/accounting: COGS, VAT/54-ФЗ, receipt and ledger retention | `finance/accounting` | `pending` | `<ref>` | `<date/trigger>` | `<date / initials>` |
| Legal: offer, recurring consent, immediate-Free and email-only refund boundary | `legal` | `pending` | `<ref>` | `<date/trigger>` | `<date / initials>` |
| Security/QA: RLS, CSRF, redaction, provider boundary, accessibility and rollback | `security/qa` | `pending` | `<ref>` | `<date/trigger>` | `<date / initials>` |
| Infrastructure/on-call: backup, restore, TLS, secret rotation and stop path | `infrastructure/on-call` | `pending` | `<ref>` | `<date/trigger>` | `<date / initials>` |
| Canary decision: executor and independent approver are different people | `release owner + independent approver` | `pending` | `<ref>` | `<date/trigger>` | `<date / initials>` |

`pass` допустим только при наличии evidence_ref и независимого approver.
Подпись действует только для указанного SHA, магазина и cohort. При изменении
кода, схемы, цены, receipt/VAT, provider capability, secrets, cohort или
unresolved incident все записи становятся `stale`; checkout и renewal снова
выключаются.

### F. Stop/rollback rehearsal

До real-shop canary оператор в test shop выполняет dry-run остановки и записывает
результат. Выключение флага оплаты должно:

- выставить в защищённой deployment-конфигурации
  `TWOBRAIN_BILLING_CHECKOUT_ENABLED=false` и оставить
  `TWOBRAIN_BILLING_PROVIDER_OBSERVATION_ENABLED=true`, чтобы сверка с
  провайдером продолжалась, затем пройти
  `infra/scripts/cd-remote.sh --dry-run`; `--execute` разрешён только отдельным
  release approver;
- заблокировать новые checkout, zero-binding и automatic renewal mutations,
  сохранив cancel/refusal, payment history, support email, Record/Stop,
  deletion и export;
- сохранить только metadata-only incident (`incident_ref`, severity, owner,
  deadline, exact SHA); не удалять ledger, не менять entitlement задним числом
  и не запускать refund из GRAF;
- после устранения причины выполнить backup/restore и migration compatibility
  checks, затем вернуть checkout только новой парой подписей. Для rollback
  приложения использовать [общий rollback runbook](../../docs/deployments/2brain-rec/rollback-runbook.md);
  downgrade схемы без утверждённого backup запрещён.

Evidence rehearsal считается `pass`, если после stop провайдерные mutation
возвращают fail-closed, текущий оплаченный срок не меняется, а локальная запись
инцидента не содержит provider/payment/refund ID или payload. Любой другой
результат блокирует real-shop canary.

## Production gate — separate approved release step

After every product/unit-economics/finance/accounting/legal/security/privacy/
accessibility/QA approval, approved source-retention policy, real-shop recurring
and zero-binding confirmation, and closure of relevant global rollout blockers:

```sh
infra/scripts/cd-remote.sh --dry-run
```

Only explicit release authorization permits `--execute` and checkout enablement.
The controlled canary proves base + one enabled add-on payment, authoritative
GET/webhook, entitlement/storage, payment receipt, one renewal failure→Free,
manual merchant-cabinet full + partial refunds outside GRAF, observed refund
receipt/list/registry convergence and zero product refund mutation. Commit,
push, release and deployment are outside this planning command.


## Сверка пяти открытых задач — 2026-10-27

Полоса: `Docs-only / mechanical`. Исправляется учёт после чтения текущих
исходников и исходных критериев GitHub; код, схема и настройки не меняются.
Прежние результаты выше сохранены как исторические. Их общий итог 80/7 и
утверждение о завершении T075–T077 не являются текущей приёмкой этих задач.
После снятия пяти неподтверждённых отметок: **75 отмечены / 12 открыты**;
это подсчёт отметок всех 87 задач, а не новая проверка остальных 82 задач.

| Задача и issue | Почему остаётся открытой |
| --- | --- |
| T062 / #4917 | Указанный `test_referral_rewards.py` проверяет вспомогательный расчёт месячного/годового начисления и истечение; полная сохраняемая цепочка выдержки 14 дней, предела 180 дней, непрерывного срока, отмены продления и подтверждённого возврата не доказана. |
| T068 / #4922 | `test_billing_notification_flow.py` проверяет тексты всех типов и сохранённую отправку, начиная с прямого помещения события чека/пробного срока в очередь. Полная цепочка от каждого исходного события из T068 до единственного уведомления не покрыта. |
| T070 / #4926 | `fair_use.py` сохраняет проверку и уведомление, принимает апелляцию; вызов `persist_review` из рабочего классификатора или обслуживающего процесса не найден. `resolve_review` меняет только объект в памяти. |
| T075 / #4930 | Функции импорта реестров, проверки полноты и формирования расхождения вызываются внутри `registry.py`, но рабочий вход, сохраняющий результат импорта и назначение ответственного, не найден. |
| T077 / #4932 | `monitoring.py` содержит снимок показателей и его объединение без найденных рабочих потребителей. Существующие ограниченные показатели административной страницы не доказывают весь исходный набор наблюдения и диагностики запуска. |

Для каждой строки перечитаны исходная issue и последние содержательные
комментарии, соответствующий тест или функция и найденные места вызова в
`apps/server/src/twobrain_rec_server/`. Тесты и приложение в этой сверке не
запускались; исторические результаты не выданы за новый прогон. Эти issues
уже открыты и не закрываются этим документальным изменением. Остальные
задачи, приёмка F140, включение оплаты и выпуск не принимаются.


## T074: PostgreSQL и три подтверждённых отказа — 2026-10-31

Переиспользовать одноразовую migrated PostgreSQL штатного test runner.
Запустить existing `test_billing_renewal_planner_postgres.py`,
`unit/test_renewal_charge.py` и `e2e/test_billing_test_shop.py`. Новый сценарий
проходит все три окна через настоящий planner/charge, читает commit из новых
sessions и проверяет ровно один transport POST/notification на отказ; повтор
того же operation не создаёт вторую отправку. Между окнами новой operation нет.
Проверить оплаченный срок и grant/method, после третьего отказа выключенное
согласие и отсутствие четвёртой попытки. HTTP разрешён только существующему
offline MockTransport, внешние сервисы/почта запрещены.

Сохранить числа PASS/SKIP/FAIL и границы. Это дополнение автоматической
матрицы; отсутствие настоящего test shop или другой части FR-090 не прятать
за зелёной PostgreSQL. T074/#4928 закрывается лишь после отдельной полной
сверки исходного объёма.

Предварительный scoped analyze T074: FR-090 recurring-decline + принятое
F278 FR-014/US3 AC4–5 → исходная T074 и один существующий test file.
Проверены6 критериев reviewer checklist,3 окна и границы idempotency/authority/
paid-access/offline. Покрытие100%, несвязанных задач0, CRITICAL/HIGH0,
новых финансовых решений0. Исторические58 открытых checklist items
не принимаются; применимость к test-only отдельно разобрана reviewer.
Baseline до нового тестового кода:116 PASS/0 SKIP/0 FAIL,5.04s;
одноразовый PostgreSQL контейнер штатно удалён.


## T048: UNKNOWN при cutoff — 01.11.2026

Использовать существующий `paid_workspace` и одноразовый PostgreSQL штатного
runner, maintenance role с forced RLS, запрет HTTP. Создать продление настоящим
planner, синтетически отметить неизвестный исход, вызвать cutoff до/ровно
на границе. До исправления отсутствие notification должно дать RED.
После исправления commit и новая session подтверждают Free/unknown_pending,
ровно один pending `renewal_unknown`, attempts=0, того же recipient/workspace,
стабильный event_id, только invoice/action_path; текст явно называет Free и
не предлагает повторно платить. Повтор не создаёт дубликат;
rollback сохраняет прежний тариф и не сохраняет письмо. Дополнительно проверить
sent/processing, отменённое согласие, старый период/другого плательщика,
отсутствующий/несвязанный счёт, неправильный workspace scope и оконченный/
неотправленный платёж. Результаты не заменяют реальные письма/#7524 и не
закрывают исходную совокупную T048. Запуск: существующий server test runner
с `tests/integration/test_billing_renewal_planner_postgres.py` и профильными
`unit/test_renewal_charge.py`, notification event/delivery tests.

Дополнительная проверка T048 перед merge: UNKNOWN должен описывать событие
окончания периода в прошлом. Письмо может доставляться после позднего успеха,
поэтому заголовок/тело не обещают текущий Free или текущую неопределённость.
В PostgreSQL planner cases проверяются исторический текст, отсутствие повторного
списания и указание посмотреть актуальный статус в кабинете.

### T048: подтверждённый отказ → Free

В одноразовом PostgreSQL проверить три синтетических отказа с настоящим
planner/charge и переход в cutoff; отдельно поздний отказ после UNKNOWN/Free
и поздний третий отказ. До cutoff сохранить только attempt notice, после
окончания — один PAYMENT_FAILED на invoice без второй attempt notice.
Отозванное согласие не включается; деньги/grants не меняются письмом.
Проверить оба снимка payer/paid_through и связи, active personal Owner,
отрицательные состояния, rollback/повтор/новый сеанс/конкуренцию и точную
историческую дату МСК в тексте. Никакой настоящей почты/оплаты.


### T048: напоминание до продления

Проверить в существующем PostgreSQL planner одно обязательное upcoming
событие текущему Owner после сохранения первой допустимой операции, точные
принятые сумму/цикл/маску и даты первого окна/конца периода МСК. До commit
событие откатывается вместе с операцией; новый сеанс видит его один раз.
Повтор/конкуренция/local retry и следующие окна не удваивают reminder.
Пропущенное первое окно не создаёт догоняющее письмо. Проверить прежние
отрицательные финансовые границы и безопасный исторический текст, который
не обещает текущего будущего списания при задержанной доставке. Реальных
провайдеров/почты нет; broad T048/T068/#7524 и выпуск остаются открытыми.


### T048: сумма и сроки подтверждённых событий — 01.11.2026

В штатном одноразовом PostgreSQL runner выполнить существующие
integration/test_billing_purchase_journey.py и test_billing_return.py,
unit/test_billing_notifications.py и notification flow/event/delivery tests.

1. Реальный HTTP checkout/подтверждение и новые sessions: initial, early,
   storage upgrade дают по одному payment_succeeded. Сумма совпадает со
   счётом, фактические даты — с grant/segments; отдельные сегменты не
   объединяются. Плановый интервал FR-105 остаётся открытым. Service gap не получает ложного подтверждения предоставления.
2. Поздний unknown/sent renewal после cutoff/cancel даёт один сохранённый
   success с фактическим периодом восстановления, не прежним paid_through;
   recurring authority не возвращается. Повтор/новое чтение не меняют payload.
3. Resume до окна и внутри окна: сумма из потреблённого quote уже включает
   storage, срок точно соответствует принятой дате с зоной/фразе. Последующая
   отмена/изменение подписки не переписывает событие, текст остаётся прошлым.
4. Проверить rollback настоящего производителя, повтор/дубликат без второй
   строки, сохранённого получателя, прежние denial/mismatch/owner границы;
   некорректные поля и старый payload без сумм/сроков безопасны и честны.
5. Сохранить числа PASS/FAIL/SKIP, команды и SHA. Настоящие письма/деньги
   запрещены, MockTransport — только синтетический провайдер. Полные
   T048/T068/#7524 и выпуск сохраняют собственную незавершённую приёмку.


Итог местной проверки содержания 01.11.2026: 498 уникальных окончательных
PASS без окончательных FAIL/ERROR/SKIP; настоящие rollback/dedup/new-session,
раздельные storage periods и resume до/внутри окна. Ошибочные попытки и
контрольные суммы сохранены в
[отчёте](validation-notification-content-20261101.md). Это незакоммиченная
проверка данного среза, до независимого ревью и точных GitHub gates будущего PR;
полные T048/T068/#7524 и FR-105 planned interval остаются открытыми.

Независимое кодовое ревью после этих запусков: APPROVE; все 498 уникальных
окончательных PASS и неизменность четырёх файлов продукта подтверждены.
[Отчёт проверяющего](review-notification-content-code-20261101.md).
Далее допускается локальная фиксация проверенного среза; push/PR/merge
ожидают окончания согласованного окна выпуска. GitHub gates ещё не пройдены.
