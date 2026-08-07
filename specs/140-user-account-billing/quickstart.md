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
rg -n 'NEEDS CLARIFICATION|\[FEATURE\]|\[DATE\]|TODO|TBD' \
  specs/140-user-account-billing/{spec.md,plan.md,research.md,data-model.md,contracts}
```

Expected: prerequisites resolve feature `140`, diff check is clean and the
placeholder scan returns no match.

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

### Latest local evidence (2026-08-07)

- `infra/scripts/ci-local.sh --fast`: PASS, 996 server unit tests, Ruff and
  Python compile; disposable PostgreSQL container removed after the run.
- Focused PostgreSQL billing RLS, migration, OpenAPI and settings contracts:
  PASS, 40 tests.
- Focused billing lifecycle, notification and subscription tests: PASS; no
  commit, push or checkout enablement was performed.
- Public launch remains blocked by the production gates below: durable provider
  registry/reconciliation worker, account-close and full notification flows,
  test-shop evidence, accessibility/usability review and finance/legal approval.
- Cross-artifact analyze pass found no unresolved implementation placeholders; the feature has
  87 tasks (74 validated complete, 13 still open), including explicit product-market
  closeout tasks T084–T087 and the remaining account, storage-lifecycle, reconciliation,
  UX/security and real test-shop tasks, so this branch is not a public-launch completion
  claim.
- Лендинг и публичные страницы проверяются отдельным ручным проходом по
  [landing-review.md](../../docs/evidence/140-user-account-billing/landing-review.md);
  серверные тесты не закрывают визуальную, accessibility и moderated-usability
  проверку.
- Registry primitives keep separate payments/refunds report identities,
  completeness hashes and owned metadata-only gaps; notification maintenance
  delivers only verified recipients through the existing Postal sender and
  marks delivery after provider success.

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
