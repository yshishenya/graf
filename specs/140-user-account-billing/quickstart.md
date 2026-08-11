# Quickstart and validation matrix

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

### Runtime verification (2026-08-11)

- Remote `/opt/projects/2brain-rec` is clean at deployed SHA
  `83c46fcf8cf8283b40080994cec3b9969e1a7da6`, migration head
  `0069_fair_use_review_constraints`; live/ready/root probes return HTTP 200.
- Independent production smoke PASS: config validation, disposable RLS/migration
  probes and metadata-only cleanup (39 database rows, 3 object keys, no residue).
- Live production RLS metadata-only probe PASS: 106/106 application tables in
  the verifier scope are enabled and forced. This does not replace edge
  webhook allowlist/header verification.
- Checkout remains disabled (`TWOBRAIN_BILLING_CHECKOUT_ENABLED=false`). This is
  runtime evidence only; test-shop/real-shop canary, edge/live-RLS review and
  four-eyes product/finance/legal/security/QA sign-offs are still required.

### Latest local evidence (2026-08-11)

- `infra/scripts/ci-local.sh --fast`: PASS, 1030 server tests, Ruff and
  Python compile; disposable PostgreSQL container removed after the run.
- `infra/scripts/ci-local.sh --full`: PASS on the billing/master integration
  branch: 650 Swift tests, ContractValidation PASS, 2833 server tests passed,
  1 skipped, strict PostgreSQL phase 42 passed, Ruff/Python compile passed and
  deployment evidence scan passed. A prior full run had one transient SC-017
  p95 performance miss; the isolated rerun passed and the clean full run did
  not change the threshold.
- Финальный полный прогон после hardening: PASS, 650 Swift-тестов,
  ContractValidation PASS, 2833 серверных теста (1 skipped), strict PostgreSQL,
  Ruff/Python compile и deployment evidence scan PASS. Дополнительно focused
  OpenAPI PostgreSQL contract: 10/10 PASS.
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
- Production migration head is `0069_fair_use_review_constraints`; fair-use persistence
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
защищённой production-конфигурации; `TWOBRAIN_BILLING_EMERGENCY_STOP` обычно
`false` при выключенном checkout и переключается в `true` при остановке.
В evidence нельзя писать
секреты, содержимое webhook/CSV, реальные payment/refund/provider IDs, номера
карт, email покупателей, аудио или текст встреч. Для связи используется только
локальный `evidence_ref` и хэш/точный SHA релиза.

### A. Разделение окружений

| Граница | Test shop | Production / controlled real shop |
| --- | --- | --- |
| YooKassa | Отдельный тестовый магазин и отдельные API/webhook secrets; идентификатор не коммитится | Магазин `1430118`, отдельные secrets; provider secrets монтируются только в server-side API и maintenance/processing roles |
| Приложение | Изолированный test host, callback и return URL; отдельные DB, object bucket и Temporal namespace | `https://rec.2brain.pro`, production DB/bucket/Temporal namespace; публичный callback принимает только production events |
| Конфигурация | `TWOBRAIN_BILLING_CHECKOUT_ENABLED=false` по умолчанию; включается на короткое окно теста | `TWOBRAIN_BILLING_CHECKOUT_ENABLED=false` до четырёх-eyes approval; emergency stop остаётся готовым к немедленному включению |
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
   webhook TLS/source filtering, emergency-stop и read-only reconciliation.
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
результат. Emergency stop должен:

- выставить в защищённой deployment-конфигурации
  `TWOBRAIN_BILLING_CHECKOUT_ENABLED=false` и
  `TWOBRAIN_BILLING_EMERGENCY_STOP=true`, затем пройти
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
