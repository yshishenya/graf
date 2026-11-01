# Implementation Plan: Личный кабинет, тарифы и биллинг

**Branch**: `codex/140-user-account-billing` | **Date**: 2026-08-06 | **Spec**: [spec.md](spec.md)

## Summary

Активная доработка 01.11.2026 — T077/#4932: внутренний read-only отчёт
по [контракту O1–O8](contracts/operator-observation.md). Полоса:
active Spec Kit slice, high-risk (диагностика/финансы/PostgreSQL).
Предыдущие срезы T048 ниже сохраняют собственные результаты и остаток.

Первый шаг T077: заменить непотребляемую модель снимка в billing/monitoring.py
конкретным read-only сбором и добавить cli/billing_monitoring.py по образцу
cli/billing_registry.py; argparse, SQLAlchemy и существующий maintenance guard.
Пути имеют префикс apps/server/src/twobrain_rec_server/. Новых таблиц,
миграций, зависимостей, scheduler и публичного API нет. Admin/readiness/F254
не менять. PostgreSQL isolation/read-only установить на connection до hooks;
общий timeout включает setup/lock. registry_status использовать после bounded
preflight и проецировать только разрешённые поля, без raw ответа.

Порядок внутри исходной T077: O1–O8 и reviewer-owned
checklists/operator-observation.md → независимый допуск → scoped analyze →
подтверждение #4932 → RED → минимальный collector/CLI → unit плюс настоящая
изолированная PostgreSQL CLI/guard/snapshot/timeout/privacy/no-write проверка
в tests/unit/test_billing_monitoring.py и
tests/integration/test_billing_monitoring_postgres.py → независимое кодовое
ревью/converge → три обязательных exact-SHA/base PR gates.

Предварительный Constitution Check: проект сохраняет maintenance/RLS,
metadata-only вывод, source/deletion truth, capture/Stop, деньги, согласие
и права; нет egress/production/Dev. После независимого review повторить.
Полный остаток FR-089/O6 — та же T077, не новая задача/отмена; частичный
JSON не закрывает issue и не является доказательством работающих тревог.

Предыдущая доработка 30.10.2026 — F140/T075/#4930, операторский импорт
по [контракту B1–B3](contracts/registry-operator-import.md). Полоса:
`active Spec Kit slice`, high-risk gates для PostgreSQL, полномочий и денег.
Прежний план ниже сохраняет историю; заменённые каталог/renewal/emergency-stop/
launch-table/brand-distance требования не восстанавливаются (см. §Scope Summary
`spec.md`). Новая служба, интерфейс, SDK и финансовая mutation не нужны.

Порядок: уточнение → независимое ревью B1–B3 → анализ → существующая #4930 →
parser/CLI/storage → изолированная PostgreSQL/права/restart → converge →
проверенный commit/PR → `governance-fast`, `macos-pr`, `pr-metadata` и общий
валидатор точного SHA/основы. До scoped PASS код не меняется. Частичный импорт
с `financial_status=not_checked` оставляет T075 открытой.

Пути реализации: существующий `billing/registry.py`, один внутренний
`cli/billing_registry.py`, два определения metadata-таблиц рядом с billing
models, одна миграция от фактического Alembic head, `db/rls_validation.py` и
профильные parser/CLI/DB tests. До миграции проверить head, grants и существующий
advisory-lock pattern. Новых зависимостей нет. Финансовую сверку продолжать в
том же T075 после полного импорта, используя authenticated API time; локальные
`created_at/observed_at` не подходят для дня подтверждения.

Предварительная конституционная проверка: PASS для дизайна — доступ только
maintenance, не меняются charge/entitlement, client secrets, capture/deletion
или production. После независимого ревью повторить оценку; runtime/RLS/release
gates этим не принимаются.

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

### T077: реестр бонусных дней (01.11.2026)

High-risk-product/active Spec Kit slice в исходной T077, после PR7887.
Реализовать C1–C6 [O10](contracts/operator-observation.md#o10-следующий-срез-сохраняемый-реестр-бонусных-дней)
одной ограниченной агрегацией существующего TimeCreditLedgerEntry в
apps/server/src/twobrain_rec_server/billing/monitoring.py. Переиспользовать
закрытую SQL-группировку и форму семейства; generic _groups не подходит:
у реестра нет created_at, будущая maturity нормальна. Группировать state,
считать четыре фильтра и MIN maturity только допустимого достигнутого окна.
Не загружать ORM-строки, не суммировать days и не вызывать финансовые helpers.
Семейство addon_and_time_credit всегда partial; add-on/job метрики null.

Проверка конституции до исследования и после проектирования: границы
сохранены — read-only metadata, прежний maintenance/RLS и единый снимок,
ограниченные запросы/вывод, без финансовых/пользовательских изменений,
новых зависимостей/служб/схемы/полномочий. Это решение проектирования,
независимый допуск и приёмка реализации ещё не получены.

Порядок: уточнение C1–C6 → research/model/quickstart → reviewer-owned
checklists/credit-ledger.md и независимый PASS → scoped analyze/существующая
#4932 → RED → минимальный collector и новые случаи в существующих
apps/server/tests/unit/test_billing_monitoring.py и
apps/server/tests/integration/test_billing_monitoring_postgres.py →
независимое кодовое review/converge → три точных SHA/base GitHub gates.
Все87 исходных полных task lines, T077 [ ], полный O6/FR089 и58старых gaps
сохраняются. Legacy Impact untouched; нет Full/CD/Dev/выпуска.

### T077: следующий срез free_projection (01.11.2026)

Требования P1–P6 [O9](contracts/operator-observation.md#o9-следующий-срез-события-free_projection)
выполняются в той же T077; первый read-only CLI принят PR7884.
High-risk-product/active Spec Kit slice. Реализация только в существующем
billing/monitoring.py: отдельная ограниченная SQL-агрегация BillingAuditEvent,
построение двух полуночей через stdlib date/datetime/ZoneInfo и
event_window вместо заглушки free_projection. usage.moscow_window_for
возвращает месяц и здесь не переиспользуется. CLI/guard/снимок/cleanup,
остальные семейства и их current_state остаются действующими.
Новых служб/таблиц/миграций/зависимостей/флагов/egress нет.

Порядок: уточнение P1–P6 → research/model/quickstart → reviewer-owned
checklists/free-projection.md и независимый PASS → scoped analyze и
подтверждение прежней #4932 → RED для нового семейства → минимальный
collector → содержательные unit и реальные PostgreSQL/CLI проверки в
существующих tests/unit/test_billing_monitoring.py и
tests/integration/test_billing_monitoring_postgres.py → независимое
кодовое review/converge → три exact-SHA/base GitHub gates. Полные пути
исходников/тестов имеют существующий префикс apps/server/.

Constitution Check до исследования и после проектирования: PASS по
границам проекта — metadata-only, действующий maintenance/RLS, read-only
снимок, ограниченные запросы/вывод, без изменения финансовых/пользовательских
данных. Независимое принятие требований ещё обязательно. Legacy Impact
следующего среза untouched: новых путей совместимости нет; удаление
непотребляемого снимка относится к уже принятому PR7884 и остаётся историей.
O6/FR089 и исходная T077 [ ] сохраняются. Своих Full/CD/Dev/выпуска нет.

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
external provider, accessibility и reference-fidelity UX

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

**Unresolved Clarifications**: архитектурных нет. Product-market gates
остаются открытыми: primary Russia-first segment/JTBD, проверяемая
value hierarchy, WTP/comprehension для base/storage packaging, full usage-cohort
COGS/gross-margin floor, campaign guardrails и business launch thresholds.
Неутверждённые цены add-on, retention deadline, fiscal/legal wording и
real-shop capabilities также являются fail-closed launch gates.

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
- UX/reference fidelity: используется текущий GRAF shell/tokens; наблюдаемые
  Krisp UX/UI/IA и функциональные подписи допускают точное воспроизведение
  по FR-081 и конституции §VII. Проверяются независимый код, права на материалы,
  WCAG 2.2 AA, Russian-first localization и явные degraded states.
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
  zoom/reduced-motion/JS-off states, Russian copy, reference fidelity,
  independent implementation and third-party asset rights under FR-081.
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


## T074: сохраняемый отказ продления — 2026-10-31

Полоса: active Spec Kit slice, test-only. Владелец — repository-audit; #4928.
Только существующий `apps/server/tests/integration/test_billing_renewal_planner_postgres.py`:
переиспользовать paid_workspace, maintenance context, настоящий planner/charge
и проверенный offline MockTransport pattern. Новые зависимости, фабрики
платежей, службы, миграции и продуктовые изменения не нужны.

До тестового кода — независимый `checklists/renewal-decline.md` и scoped analyze.
Далее существующий baseline → один последовательный PostgreSQL сценарий
трёх отказов → профильные unit/contract/integration/E2E → independent review
и converge → точные PR checks. При найденном дефекте продукта остановить
его зависимую приёмку и оформить требования отдельно, не ослаблять assertion.
Constitution Check: сохраняются полномочия, scope, согласие, оплаченный доступ,
сохранность истории и запрет реальных запросов; release/Dev/production не входят.

## Историческая T023 — сверка 31.10.2026

Полоса этой сверки: docs-only / mechanical; Legacy Impact: untouched.
Принятые требования F210 FR017/F278 FR006 заменили browser-only billing
часть F140 FR012. Старую совокупную T023 не реализуем повторно: сохраняем
исходный текст и владельца, снимаем неподтверждённую отметку выполнения и
отдельно фиксируем отмену. #4877 можно закрыть только NOT_PLANNED после
принятия этой сверки обычным PR и индивидуального повторного чтения issue.

Действующие account UI/доступность/ошибки остаются в T079/#4936, F210
T017/#5961, F278 T017/#7323/T025/#7332. Account-close, внешний refund,
изоляция и серверная власть над оплатой сохраняются; код, платёжные настройки,
приложение и выпуск не меняются. Возврат к старой отдельной native сводке
и внешнему handoff возможен только после нового решения владельца о пути
оплаты; отмена не доказывает текущий installed-app или финансовый результат.


## T048: уведомление unknown при cutoff — 01.11.2026

Полоса: active Spec Kit slice, серверная финансовая область; Legacy Impact: untouched.
До кода — независимая проверка `checklists/renewal-unknown.md` и scoped analyze.
В `billing/renewal_charge.py::project_renewal_cutoffs` сохранить существующую
проекцию доступа, блокировку пространства и транзакцию. Перед `_project_free`
использовать сохранённую `paid_through`; после `unknown_pending` проверить снимки
операции и счёта (workspace, operation, payer, paid_through), затем вызвать
существующий `enqueue_billing_notification` с `RENEWAL_UNKNOWN`, стабильным
`renewal:<invoice UUID>:unknown`, безопасным номером и относительным путём.
Не проверять равенство текущего согласия историческому: отменённая отправленная
операция всё ещё требует выяснения исхода, а письмо не разрешает новую отправку.
Сохраняются существующие paid-through, grant, provider state и consent semantics.

Проверки в существующем PostgreSQL planner test: первоначальный RED, сохранение
после commit/новой session; повтор/rollback; sent/processing/unknown; отменённое
согласие; старый период, другой плательщик, отсутствие/несовпадение счёта,
неподходящее пространство и оконченная/неотправленная операция. HTTP запрещён
fixture. Затем профильные billing unit/contract/integration, review/converge,
обязательные три PR проверки точного SHA/основы. Новые зависимости, очереди,
миграции и финансовые изменения не требуются. T048/#4903 остаётся открытой
до остальных producers и полной проверки исходного объёма; #7524 отдельно.
Constitution Check: изоляция, полномочия, сохранность финансовой истории,
отсутствие повторной оплаты и атомарность сохранены; секреты и реальные
письма/платежи/Dev/production в проверку не входят.

Уточнение текста до merge: сохранённое событие может доставляться после позднего
успеха. Заголовок и тело описывают состояние на границе периода в прошлом,
ссылаются на текущий статус в кабинете и не предлагают повторное списание.
Достаточно исправления существующего шаблона и его предметной проверки;
нового фильтра доставки, состояния или службы не требуется.

## T048: итоговый подтверждённый отказ — 01.11.2026

Active Spec Kit slice; Legacy Impact untouched. До кода: уточнение выше,
reviewer-owned checklists/renewal-final-failure.md, scoped analyze и исходная
#4903. Переиспользовать PAYMENT_FAILED, существующую очередь и безопасное
форматирование даты, без новой службы/таблицы/миграции/платежа.

Сначала подтвердить отсутствие notice после трёх реальных синтетических
отказов и cutoff. Общую проверку связей UNKNOWN/итогового отказа держать
в одном узком helper в renewal_charge.py, вызываемом из cutoff и общей
record_renewal_decline для позднего исхода. Сам финансовый guard отзыва
согласия и проекцию доступа не менять; письмо о сохранённом исходе
не является разрешением на новое списание. До cutoff оставить попытку,
после Free — только итоговое письмо.

Проверки: сохраняемая PostgreSQL цепочка трёх отказов→cutoff; неизвестность→
Free→подтверждённый отказ; поздний третий отказ с переходом; отозванное
согласие; сохранение после нового сеанса, повтор, rollback, конкуренция,
отрицательные payer/period/operation/invoice/owner/status связи. Новые
сценарии не обращаются к настоящим провайдерам/почте. Затем профильные
renewal/notification tests, независимые review/converge и три точных PR gate.
Конституционные деньги/изоляция/история/сохранность/секреты сохранены;
полная T048 не принимается. Выпуск/Dev/Full/CD отсутствуют.

Общий helper сохраняет UNKNOWN без восстановленного provider_id; этот guard
применяется только к canceled/canceled. Отдельная регрессия сохранит границу.


## T048: напоминание в первом окне продления — 01.11.2026

Active Spec Kit slice, Legacy Impact untouched. До кода — независимый
checklists/renewal-reminder.md и ограниченный analyze. Использовать
plan_due_renewals после всех действующих проверок и создания первой
operation/invoice. Существующая транзакционная очередь, новый конкретный
вид сообщения в notifications.py; не создавать таблицу, службу или scheduler.
Stable event на workspace/payer/paid_through, без номера попытки/операции.
Тариф/цикл и сумма берутся из принятого снимка, даты — из текущего периода
и первого окна. В payload только minor units, RUB, month/year, даты МСК,
последние4цифры безопасной маски и путь кабинета. Случай отсутствующей маски
показывает «сохранённый способ оплаты», а не provider ID.

RED на настоящем PostgreSQL planner, затем одна минимальная запись в том же
commit. Проверки: first-window commit/rollback/new session/repeat/concurrent;
local retry и следующие окна без дубликата; no consent/method/current scope,
unknown/newer payment; точная историческая копия и allowlist. Финансовое
планирование/отправка не меняются. Предыдущий итоговый отказ хранится в
отдельном коммите; исходная T048/#4903 остаётся владельцем остатка без дублей.


## T048: содержание подтверждений — 01.11.2026

Active Spec Kit slice, financial notification content; Legacy Impact untouched.
До кода — независимый checklists/notification-content.md и scoped analyze.
Меняются только payload существующих производителей: два в entitlements.py,
успешное предоставление storage segments в purchases.py и resume route
cabinet/web_routes/billing.py. notifications.py сохраняет allowlist и renderer;
существующие форматирование/очередь/Postal переиспользуются без новой таблицы,
миграции, зависимости или службы. Общая подготовка полей подтверждения оплаты
не дублирует форматирование в трёх местах. Сумма — invoice, фактический срок —
grant/segments, без объединения отдельных сегментов. Плановый интервал
FR-105 пока не подтверждён во всех снимках счетов и остаётся открытым. Resume использует
потреблённый quote, полную catalog amount без повторного сложения storage и
точный принятый next_attempt_label (дата с UTC offset или закрытая фраза окна).
Старые строки без данных не дополняются из текущей подписки при доставке.

RED → настоящие producer/commit/new-session проверки в существующих
integration тестах → минимальная правка → повтор/rollback/отрицательные
границы/профильные notification и billing tests → независимое ревью и
converge → обязательные три GitHub gates точного SHA/основы. Деньги, права,
согласие и event identity не меняются; Dev/production/почта не затрагиваются.
Constitution Check: изоляция, серверные секреты, история и атомарность
сохранены. T048/T068/#7524 этим срезом не завершаются.
