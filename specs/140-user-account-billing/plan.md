# Implementation Plan: Личный кабинет, тарифы и биллинг

**Branch**: `codex/140-user-account-billing` | **Date**: 2026-08-06 | **Spec**: [spec.md](spec.md)

## Summary

Расширить существующий Jinja/HTMX-кабинет GRAF личным account-and-billing
контуром. GRAF остаётся источником истины для каталога, согласий, invoice,
subscription schedule, entitlement, точных Free-секунд, playback-storage,
промокодов и 7/30-дневных реферальных начислений. YooKassa выполняет hosted
payment/binding, хранит opaque payment method и остаётся источником истины о
платеже, чеке и уже выполненном merchant refund.

Возврат не становится функцией продукта: кабинет показывает отдельный email,
safe invoice reference и `Написать письмо`; переписка, решение, расчёт и ручной
возврат происходят вне GRAF. GRAF не содержит refund case/form/status/operator
UI/API/CLI и не вызывает refund API. Он только идемпотентно сверяет
authoritative provider refund/receipt truth, чтобы финансовый ledger,
entitlement и referral credit не расходились.

Переиспользуются текущие `Organization`/`Workspace`/`UserIdentity`/
`WorkspaceMembership`, personal-workspace bootstrap, session rotation, CSRF,
tenant context/RLS, cabinet shell, MinIO lifecycle, Temporal, Postal и `httpx`.
Не добавляются SPA, YooKassa SDK, generic payment-provider abstraction, wallet,
dunning engine или второй платный тариф только ради хранения.

## Technical Context

**Language/Version**: Python 3.13; HTML/Jinja, CSS, HTMX 2.0.10 и минимальный
JavaScript; Swift 6 только для существующей macOS route/handoff policy

**Primary Dependencies**: FastAPI, SQLAlchemy/Alembic, Jinja2/HTMX, `httpx`,
Temporal Python SDK, Postal, existing cryptography/Fernet convention; только
уже установленные runtime dependencies

**Storage**: PostgreSQL как коммерческий ledger; существующий MinIO/object
lifecycle как источник exact `meeting-review.m4a` bytes; текущие и legacy
transcription sources учитываются в lifecycle, но не в customer quota;
provider payment-method reference хранится только в versioned encrypted envelope

**Testing**: pytest unit/contract/integration/E2E, disposable PostgreSQL RLS,
YooKassa test shop и синтетические doubles/CSV; Playwright/Chromium через уже
имеющийся dev stack; SwiftPM focused route-policy tests

**Risk / Validation Lane**: `high-risk-feature` — деньги, auth/session,
tenant isolation, secrets, Postgres/MinIO/Temporal, retention/deletion,
external provider, accessibility и brand-distance UX

**Release Gate**: `no deploy` для planning slice. Реализация требует feature
quickstart и `infra/scripts/ci-local.sh --fast` перед PR; production требует
full exact-SHA deploy gate, письменные product/unit-economics/finance/
accounting/legal/security/QA approvals и отдельное разрешение пользователя

**Target Platform**: Linux Docker server и современный browser; macOS Apple
Silicon desktop показывает read-only summary и открывает денежные действия во
внешнем browser, не передавая finance data в URL

**Project Type**: существующий FastAPI server-rendered cabinet + native macOS
handoff; YooKassa — единственный launch provider

**Performance Goals**: webhook edge acknowledgement ≤2 s в focused test;
provider GET/reconciliation выполняются вне request path; entitlement/quota
decision использует локальную server projection и не зависит синхронно от
YooKassa

**Constraints**: RUB; `bank_card`; hosted redirect; no PAN/CVC; no entitlement
from return URL/webhook body; одна automatic renewal operation и no grace/no
automatic retry; checkout default-off; local Record/Stop и существующие
read/export/delete не зависят от billing state

**Scale/Scope**: `Free` — 18 000 exact accepted seconds per Moscow calendar
month + 250 MB playback; explicit 7-day cardless Trial — unlimited core + 500
MB; `Личный` — 790 ₽/month or 7 900 ₽/year, unlimited core + 2 GB; ровно один
co-termed total-capacity add-on 5/20/100/500 GB. Add-on prices и checkout
остаются выключены до утверждения COGS/value и обязательных launch gates

**Unresolved Clarifications**: none. Неутверждённые цены add-on, retention
deadline, fiscal/legal wording и real-shop capabilities — явные fail-closed
launch gates, а не проектные неизвестные.

## Constitution Check

### Pre-research gate

**Status**: PASS.

- Capture-first/visible control: billing не меняет native capture, persistent
  indicator и one-action Stop; storage/payment никогда не блокируют локальную
  запись.
- Data/secret boundary: YooKassa credentials и opaque method остаются на
  server; desktop не получает provider secret/reference; financial routes не
  отправляют content в Langfuse и исключены из Yandex/session replay.
- Deletion truth: logical meeting deletion сразу закрывает доступ и освобождает
  playback quota, а current/legacy primary audio проходит существующий purge;
  finance retention, backups, YooKassa, Langfuse и Temporal описываются
  отдельно без обещания universal erasure.
- Spec-driven delivery: выбран полный high-risk lane; clarify завершён, этот
  planning pass создаёт research, model, contracts и runnable quickstart;
  checklist/tasks/analyze остаются обязательными до implementation.
- UX/brand distance: используется текущий GRAF shell/tokens, clean-room
  hierarchy, WCAG 2.2 AA, Russian-first localization и явные degraded states.
- Deployment: planning не выполняет deploy и не повышает текущий
  `pilot_blocked` status.

## Architecture And Delivery Sequence

1. **Tenant/account foundation**: расширить существующий personal-workspace
   bootstrap и account routes; profile/preferences/session/device actions
   используют текущие auth, CSRF, membership switch и RLS boundaries.
2. **Commercial ledger**: добавить versioned catalog/gates, trial activation,
   checkout intent, immutable invoice, consent/recurring-authority evidence,
   provider operation/payment/method/receipt observation, workspace
   subscription и append-only entitlement grants.
3. **Quota truth**: проецировать plan в existing quota decision; добавить
   exact source-range ledger для Free, exact normalized-playback
   reservation/projection для storage на основе `TrackArtifact.byte_length`,
   co-termed add-on и transient no-archive lifecycle. Не использовать
   display-only daily aggregates или отдельный object inventory как
   enforcement.
4. **YooKassa boundary**: один прямой `httpx` adapter для payment, zero-amount
   binding, authoritative GET/list и bounded webhook inbox. Refund mutation
   отсутствует; `refund.succeeded`/refund registry — read/reconcile inputs only.
5. **Customer P1**: account/security/preferences, overview/usage/plans,
   checkout/return, method, cancel/resume/cycle/storage, history/receipt и
   static email refund instruction. Desktop получает только summary/handoff.
6. **Growth P2**: promo reservation/redemption, opaque first-touch referral и
   append-only 7/30-day time-credit ledger with maturity/cap/reversal.
7. **Durable operations**: Temporal-backed one-attempt renewal resolution,
   trial/time-credit/notice/account-close timers, transient purge and
   reconciliation. Existing deletion services own primary purge; external
   backoffice owns refund decisions/execution.
8. **Launch gates**: emergency stop for GRAF-originated checkout/binding/charge,
   official payment/refund CSV reconciliation, backup/restore, accessibility,
   clean-room review, test-shop and controlled real-shop canary.

The database is authoritative for GRAF commercial state. A return URL changes
only presentation. A webhook stores a bounded reference; worker performs
authoritative YooKassa read, validates environment/shop/amount/currency/
metadata and applies one monotonic transaction. Unknown operation keeps its
same persisted request/key and blocks pay-again until resolved.

## Validation Plan

- **Static planning checks**: `git diff --check`; no unresolved research marker;
  no product refund-case/form/execution language; no legacy 1/10 GB catalog;
  cross-links and managed AGENTS plan pointer valid.
- **Account/security contracts**: personal workspace idempotency, verified
  trial uniqueness, Owner/Admin/Member matrices, current-role recheck, CSRF,
  session rotation/revocation and same/cross-tenant RLS.
- **Money contracts**: server amount/receipt equality, double click/two tabs,
  permanent internal uniqueness, provider 24-hour key expiry, duplicate/
  out-of-order webhook, authoritative GET, saved=true/false, cancellation
  authority race, one renewal attempt, exact cutoff→Free and late outcome.
- **Storage/usage contracts**: one Moscow Free window bound at reservation,
  unique accepted source ranges, distinct 80%/100% Free thresholds,
  overrun rejection, 250 MB/500 MB/2 GB/5–500 GB exact decimal capacity,
  object-stat mismatch/supersede handling, only active `meeting-review.m4a`
  bytes charged, delete precedence, source-retention gate reopening,
  add-on serialization and no-archive 15-minute/24-hour purge.
- **External refund boundary**: route/schema/source scan proves zero refund
  form/case/status/operator mutation/CLI and zero refund API calls; static
  `mailto:` contains only configured address + safe reference; manual
  merchant-cabinet full/partial refund is observed once through provider/
  registry reconciliation and never rendered as product status.
- **Growth/CX**: promo atomicity/no stacking, referral first touch/maturity/
  7-or-30-day/cap/reversal, notification dedupe, keyboard/screen-reader/200%
  zoom/reduced-motion/JS-off states, Russian copy and brand-distance review.
- **Operations**: stop-all-charges, test/prod isolation, secret rotation,
  webhook/poller/CSV gaps, billing backup/restore, migration rollback,
  disk-full fail-closed and metadata-only evidence scan.
- **Closeout**: [quickstart.md](quickstart.md) then
  `infra/scripts/ci-local.sh --fast`; full lane and `cd-remote.sh --dry-run`
  belong to the separately approved release boundary.

## Project Structure

### Documentation

```text
specs/140-user-account-billing/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
├── checklists/
└── tasks.md
```

### Source Code

```text
apps/server/src/twobrain_rec_server/
├── billing/                       # catalog/lifecycle/entitlement/usage/storage/reconciliation
│   └── yookassa.py                # direct read/pay/bind adapter; no refund mutation
├── cabinet/
│   ├── web_routes/account.py      # account pages over existing auth/session/device services
│   ├── web_routes/billing.py      # server-rendered billing pages and POST actions
│   └── templates/cabinet/         # existing shell/components/fragments
├── api/billing.py                 # bounded YooKassa webhook ingress only
├── db/models/billing.py           # new workspace/identity-scoped entities
├── db/migrations/versions/        # next Alembic migration + RLS policies
├── deletion/                      # reuse: primary purge and truthful lifecycle
└── workflows/                     # durable renewal/reconciliation/timers

apps/macos/RecApp/Sources/Cabinet/ # existing external-browser handoff policy
apps/macos/Shared/Tests/            # focused route-policy regression
apps/server/tests/{unit,contract,integration,e2e}/
infra/{env,docker-compose.yml,scripts/}
docs/runbooks/
```

**Structure Decision**: один cohesive `billing/` package и один account layer
поверх существующего cabinet/auth. Прямой YooKassa adapter достаточен для
единственного provider. Exact storage bytes переиспользуют active normalized
playback/object lifecycle; отдельный storage engine не создаётся. Refund
backoffice намеренно не моделируется в source tree.

## Phase 0 Research Output

Все решения и отклонённые альтернативы зафиксированы в
[research.md](research.md). Неразрешённых исследовательских маркеров нет;
неизвестные
commercial/legal/provider параметры превращены в default-off launch gates.

## Phase 1 Design Output

- [data-model.md](data-model.md)
- [account-ia-ux-ui-cx.md](contracts/account-ia-ux-ui-cx.md)
- [billing-lifecycle.md](contracts/billing-lifecycle.md)
- [entitlement-degradation.md](contracts/entitlement-degradation.md)
- [http-interface.md](contracts/http-interface.md)
- [operations-reconciliation.md](contracts/operations-reconciliation.md)
- [security-privacy-compliance.md](contracts/security-privacy-compliance.md)
- [yookassa-integration.md](contracts/yookassa-integration.md)
- [quickstart.md](quickstart.md)

## Post-Design Constitution Check

**Status**: PASS.

- Customer/account/payment interfaces preserve Owner authority, CSRF,
  workspace/session recheck and deny-by-default RLS.
- Append-only invoice/operation/authority/grant/usage/referral records plus
  uniqueness/locks make money and access recoverable without provider-owned
  subscription state.
- Finite playback quota is adjacent to every unlimited claim; transcription
  WAV remains lifecycle-accounted at zero customer quota; accepted deletion
  overrides recovery retention and enters mandatory purge.
- Refund design has the smallest truthful boundary: a static external-email
  instruction plus read-only provider reconciliation. No product case,
  execution endpoint, operator surface, status/SLA or duplicate authority was
  introduced.
- Capture, deletion/export, analytics/observability, external dependency,
  accessibility, clean-room, deployment and evidence gates are preserved.
- Production remains fail-closed until catalog, storage COGS/retention,
  YooKassa real-shop, fiscal/legal, security/QA and global rollout gates pass.

## Complexity Tracking

Конституционных исключений нет. Намеренно не создаются generic provider layer,
SPA, dunning/grace engine, wallet, stacked add-ons, seats/team billing,
usage-overage и GRAF refund backoffice. Добавлять их можно только отдельной
проверенной feature slice, когда появится подтверждённая потребность.
