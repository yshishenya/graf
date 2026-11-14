---

description: "Dependency-ordered implementation tasks for the GRAF personal account and billing slice"
---

# Tasks: Личный кабинет, тарифы и биллинг

**Input**: Design documents from `/specs/140-user-account-billing/`

**Prerequisites**: `spec.md`, `plan.md`, `research.md`, `data-model.md`, `contracts/`, `quickstart.md`

**Validation lane**: significant/high-risk feature. Contract, unit, integration, security, accessibility and test-shop evidence are required before implementation closeout.

**Implementation rule**: Reuse the current cabinet/auth/deletion/Temporal/MinIO patterns. Do not introduce a SPA, generic PSP abstraction, second paid base tier, wallet, dunning/grace path, or product-side refund mutation. Customer storage is projected from active `TrackArtifact.byte_length` for normalized playback objects; do not create a duplicate object inventory.

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Establish the smallest billing package and test configuration without changing customer behavior.

- [X] T001 [P] Add billing package boundaries and typed launch constants in `apps/server/src/twobrain_rec_server/billing/__init__.py` and `apps/server/src/twobrain_rec_server/billing/catalog.py` for `Free`, `Trial Личного`, `Личный`, monthly/yearly cycles, storage capacities, and feature flags.
- [X] T002 [P] Add YooKassa environment, shop, webhook, provider-floor, emergency-stop, and support-email settings using the existing configuration pattern in `apps/server/src/twobrain_rec_server/config.py` and `infra/env/rec.production.env.example`.
- [X] T003 [P] Add deterministic billing factories, Moscow-clock helpers, and masked test identities in `apps/server/tests/fixtures/billing.py` and `apps/server/tests/fixtures/cabinet_access.py`.
- [X] T004 [P] Add Russian-first billing labels, safe-reference formatting, and mailto sanitization fixtures in `apps/server/tests/unit/test_billing_copy_and_redaction.py`.

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Build shared authority, tenancy, persistence, idempotency and provider boundaries. No user story can start before this phase is complete.

### Foundation tests first

- [X] T005 [P] Add model and invariant tests for workspace-bound billing rows, append-only authority, immutable invoices, unique operation keys, and no raw provider payloads in `apps/server/tests/unit/test_billing_models.py`.
- [X] T006 [P] Add cross-workspace RLS and fail-closed tenant-scope tests for every billing table in `apps/server/tests/integration/test_billing_rls.py`.
- [X] T007 [P] Add YooKassa adapter contract tests for hosted redirect, saved-method consent, idempotency-key reuse, provider-floor rejection, and zero-amount binding capability in `apps/server/tests/contract/test_yookassa_adapter.py`.
- [X] T008 [P] Add webhook inbox tests for duplicate, out-of-order, malformed, and replayed events plus authoritative GET/list fallback in `apps/server/tests/integration/test_billing_webhooks.py`.
- [X] T009 [P] Add tests proving the product has no outbound refund mutation and does not persist support-email contents in `apps/server/tests/contract/test_external_refund_boundary.py`.

### Foundation implementation

- [X] T010 Create the billing SQLAlchemy models, enums, immutable snapshots, append-only ledgers, and redacted provider-reference fields in `apps/server/src/twobrain_rec_server/db/models/billing.py` and export them from `apps/server/src/twobrain_rec_server/db/models/__init__.py`.
- [X] T011 Create migration `apps/server/src/twobrain_rec_server/db/migrations/versions/0044_user_account_billing.py` after current revision `0043_initial_outcome_reconcile`, including constraints, indexes, RLS policies, and downgrade safety for all foundational billing tables.
- [X] T012 Implement workspace/owner authorization, recurring-authority version checks, row locks, and metadata-only audit helpers by reusing `apps/server/src/twobrain_rec_server/auth/dependencies.py`, `apps/server/src/twobrain_rec_server/db/tenant_context.py`, and new `apps/server/src/twobrain_rec_server/billing/authority.py`.
- [X] T013 Implement the server-only YooKassa client with allowlisted operations for payment, saved-method binding, GET/list observation, and receipt observation in `apps/server/src/twobrain_rec_server/billing/yookassa.py`; keep credentials out of desktop and browser code.
- [X] T014 Implement idempotent webhook ingestion, signature/allowlist validation, provider GET/list reconciliation hooks, and safe event redaction in `apps/server/src/twobrain_rec_server/api/billing.py` and `apps/server/src/twobrain_rec_server/billing/provider_events.py`.
- [X] T015 Implement shared billing locks, operation outcome classification (`success`, `canceled`, `unknown`), provider-key expiry handling, and emergency-stop checks in `apps/server/src/twobrain_rec_server/billing/operations.py`.
- [X] T016 Register billing routes, workflow modules, and worker dependencies through the existing composition points in `apps/server/src/twobrain_rec_server/main.py`, `apps/server/src/twobrain_rec_server/cabinet/web.py`, and `apps/server/src/twobrain_rec_server/workflows/worker.py`.

**Checkpoint**: Persistence, tenant isolation, provider boundary, idempotency and audit primitives are available; no money mutation is possible without an explicit story implementation.

## Phase 3: User Story 1 — Создать личный аккаунт и безопасно управлять им (Priority: P1)

**Goal**: Give a verified owner a personal workspace, account navigation, profile/security/preferences controls, one explicit seven-day trial, and truthful account-close behavior.

**Independent test**: A new verified identity can open the account center, activate trial once, see owner/member restrictions, rotate sessions, and schedule/cancel account close without affecting capture safety or another workspace.

### Tests for User Story 1

- [X] T017 [P] [US1] Add account-center, personal-workspace bootstrap, authorization, and macOS browser-handoff contract tests for owner, admin, member, unverified identity, workspace switching, expired/offline/browser-unavailable states, and one-time handoff in `apps/server/tests/contract/test_account_routes.py` and `apps/macos/Shared/Tests/DesktopCabinetBillingHandoffTests.swift`.
- [X] T018 [P] [US1] Add trial eligibility, one-per-`UserIdentity`, explicit-consent, expiry-to-Free, and account-close integration tests in `apps/server/tests/integration/test_account_lifecycle.py`.

### Implementation for User Story 1

- [X] T019 [US1] Implement idempotent personal-workspace bootstrap plus account-center view models, owner/member capability projection, and safe navigation using `apps/server/src/twobrain_rec_server/auth/workspace_onboarding.py`, `apps/server/src/twobrain_rec_server/cabinet/view_models.py`, and `apps/server/src/twobrain_rec_server/cabinet/web_routes/settings.py`.
- [X] T020 [P] [US1] Add profile, security, notifications, language/theme, active-session/device screens, recovery-safe login-method unlink guard, and the admin usage label `Использование и лимиты` by extending `apps/server/src/twobrain_rec_server/cabinet/web_routes/settings.py`, `apps/server/src/twobrain_rec_server/auth/provider_links.py`, `apps/server/src/twobrain_rec_server/admin/view_models.py`, `apps/server/src/twobrain_rec_server/admin/templates/admin/balance.html`, and `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/settings_account_content.html`.
- [X] T021 [US1] Implement explicit trial activation, verification gate, one-time identity eligibility, and expiry projection in `apps/server/src/twobrain_rec_server/billing/trial.py` and `apps/server/src/twobrain_rec_server/cabinet/web_routes/billing.py`.
- [X] T022 [US1] Implement account-close scheduling, seven-day cancellation, immediate access/quota revocation at accepted deletion, and Temporal finalization integration by extending `apps/server/src/twobrain_rec_server/deletion/service.py`, `apps/server/src/twobrain_rec_server/db/models/deletion.py`, and `apps/server/src/twobrain_rec_server/workflows/maintenance_worker.py`.
- [ ] T023 [US1] Add Russian-first account templates, keyboard/focus states, no-JS navigation fallback, clean-room visual tokens, and read-only browser handoff/expired/offline states in `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/settings_account_content.html`, `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/components/account_navigation.html`, `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.css`, `apps/macos/RecApp/Sources/Cabinet/DesktopCabinetRoutePolicy.swift`, and `apps/macos/RecApp/Sources/Cabinet/DesktopCabinetWorkspaceView.swift`. (Issue #4877).

**Checkpoint**: Account center and trial are independently usable; account close remains distinct from canceling paid renewal and never disables local Record/Stop.

## Phase 4: User Story 2 — Понять тариф и использование без сюрпризов (Priority: P1)

**Goal**: Show exact processing/storage state and enforce Free seconds plus finite playback storage while paid core capabilities remain commercially unlimited.

**Independent test**: Fixtures can exhaust Free’s exact 18,000-second window, fill playback storage, process without saving audio, add/remove reservation bytes, and verify WAV/internal source bytes never count toward customer quota.

### Tests for User Story 2

- [X] T024 [P] [US2] Add exact-second admission, Moscow-month reservation binding across midnight, 80%/100% Free-threshold copy, overrun rejection, calendar reset, reservation release, partial-success, and no-rollover tests in `apps/server/tests/unit/test_free_usage_ledger.py`.
- [X] T025 [P] [US2] Add playback-only storage projection, 80/95/100% thresholds, exact decimal capacities, reservation/object-stat mismatch and supersede handling, add-on capacity, deletion release, normalized writer byte-size, WAV retention/COGS accounting, retention-gate reopening, and source-lifecycle tests in `apps/server/tests/integration/test_storage_quota.py` and `apps/server/tests/contract/test_storage_lifecycle.py`.
- [X] T026 [P] [US2] Add processing-without-save and paid-unlimited capability contract tests in `apps/server/tests/contract/test_entitlements_and_ingest_limits.py`.

### Implementation for User Story 2

- [X] T027 [US2] Implement Free usage windows, exact-second reservations/commit ledger, and entitlement checks in `apps/server/src/twobrain_rec_server/billing/usage.py`.
- [X] T028 [US2] Implement storage capacity projection and reservation from active normalized `TrackArtifact.byte_length` for `meeting-review.m4a`, with no duplicate object inventory, in `apps/server/src/twobrain_rec_server/billing/storage.py`.
- [X] T029 [US2] Integrate playback quota admission, `Обработать без сохранения аудио`, transient 15-minute purge, and 24-hour hard lifetime into `apps/server/src/twobrain_rec_server/ingest/store.py`, `apps/server/src/twobrain_rec_server/processing/store.py`, and `apps/server/src/twobrain_rec_server/workflows/processing_workflow.py`.
- [X] T030 [US2] Extend current/legacy source lifecycle and deletion purge so WAV is recoverable only under approved policy, exact normalized writer bytes are recorded, COGS/backup retention evidence is available, and every source immediately enters mandatory purge after accepted deletion in `apps/server/src/twobrain_rec_server/db/models/ingest.py`, `apps/server/src/twobrain_rec_server/db/models/lifecycle.py`, `apps/server/src/twobrain_rec_server/billing/source_lifecycle.py`, `apps/server/src/twobrain_rec_server/deletion/service.py`, and `apps/server/src/twobrain_rec_server/normalization/service.py`.
- [X] T031 [US2] Add usage/storage dashboard, capacity explanation, archive-full states, and explicit unlimited-versus-storage copy in `apps/server/src/twobrain_rec_server/cabinet/web_routes/billing.py`, `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/billing_usage_content.html`, and `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js`.

**Checkpoint**: Usage and storage truth are visible and enforceable without limiting paid processing minutes or blocking processing when the user chooses no audio archive.

## Phase 5: User Story 3 — Купить `Личный` через YooKassa (Priority: P1)

**Goal**: Let the billing owner preview a catalog offer, apply one valid discount, pay through hosted YooKassa, and receive a durable entitlement only after authoritative success.

**Independent test**: A test-shop owner can complete monthly and annual hosted checkout, survive duplicate/out-of-order webhooks and browser timeout, see pending/unknown safely, and never be asked to pay twice.

### Tests for User Story 3

- [X] T032 [P] [US3] Add catalog, price snapshot, provider-floor, annual-price, and checkout-preview contract tests in `apps/server/tests/contract/test_checkout.py`.
- [X] T033 [P] [US3] Add hosted success, decline, duplicate webhook, timeout/unknown, late success, and receipt reconciliation tests in `apps/server/tests/integration/test_checkout_yookassa.py`.

### Implementation for User Story 3

- [X] T034 [US3] Implement versioned catalog, checkout intent, immutable invoice snapshot, and payable amount calculation in `apps/server/src/twobrain_rec_server/billing/checkout.py`.
- [X] T035 [US3] Implement owner-only checkout preview, hosted redirect, CSRF protection, safe pending/unknown/error states, and callback projection in `apps/server/src/twobrain_rec_server/cabinet/web_routes/billing.py` and `apps/server/src/twobrain_rec_server/api/billing.py`.
- [X] T036 [US3] Implement authoritative payment/receipt confirmation and append-only entitlement grants in `apps/server/src/twobrain_rec_server/billing/entitlements.py` and `apps/server/src/twobrain_rec_server/billing/receipts.py`.
- [X] T037 [US3] Add billing hub, plan comparison, monthly/yearly confirmation, hosted-return banners, and receipt CTA templates in `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/billing_overview_content.html` and `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/billing_checkout_content.html`.

**Checkpoint**: Initial purchase works in test shop with no client-side credentials, no duplicate payable invoice, and no premature paid entitlement.

## Phase 6: User Story 4 — Управлять подпиской и способом оплаты (Priority: P1)

**Goal**: Allow the owner to bind/replace a bank card, cancel/resume renewal, and purchase exactly one co-termed storage add-on.

**Independent test**: An owner can bind a method with explicit recurring consent, cancel before the next charge, resume with fresh preview, and change total storage with the sole approved positive mid-cycle pro-rata rule, no hidden base-plan proration, and no stacking.

### Tests for User Story 4

- [X] T038 [P] [US4] Add payment-method consent, replacement, owner-loss, cancellation refusal, resume-preview, and row-lock tests in `apps/server/tests/integration/test_subscription_controls.py`.
- [X] T039 [P] [US4] Add one-add-on, co-term, capacity-change, provider-floor, and no-stacking contract tests in `apps/server/tests/contract/test_storage_addon.py`.

### Implementation for User Story 4

- [X] T040 [US4] Implement recurring authority evidence, bank-card binding/replacement, method display masking, and owner-loss revocation in `apps/server/src/twobrain_rec_server/billing/payment_methods.py` and `apps/server/src/twobrain_rec_server/billing/authority.py`.
- [X] T041 [US4] Implement self-service `Отключить автопродление`, refusal timestamp/version checks, resume preview/consent, and non-blocking optional retention copy in `apps/server/src/twobrain_rec_server/billing/subscription.py` and `apps/server/src/twobrain_rec_server/cabinet/web_routes/billing.py`.
- [X] T042 [US4] Implement one co-termed storage add-on, capacity transitions, price snapshots, and entitlement projection in `apps/server/src/twobrain_rec_server/billing/storage_addons.py`. (Issue #4897).
- [X] T043 [US4] Add payment-method, renewal-control, and storage-add-on screens with explicit action labels and accessible confirmation states in `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/billing_payment_method_content.html`, `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/billing_subscription_content.html`, and `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/billing_storage_content.html`.

**Checkpoint**: Renewal authority is explicit, owner-scoped, auditable and can be refused before any provider mutation.

## Phase 7: User Story 5 — Понять немедленный переход на Free и восстановить подписку (Priority: P1)

**Goal**: Resolve renewal exactly once, fail closed on unknown outcomes, and move to Free immediately at the cutoff without grace or silent retries.

**Independent test**: Test-shop renewal success, confirmed failure, transport unknown, late success, cancellation, and emergency stop produce deterministic access/authority states and no second charge key.

### Tests for User Story 5

- [X] T044 [P] [US5] Add renewal boundary tests for cutoff time, one operation per period, confirmed failure, no grace, no retry, and immediate Free projection in `apps/server/tests/integration/test_renewal_lifecycle.py`.
- [X] T045 [P] [US5] Add unknown/late-success precedence and emergency-stop tests in `apps/server/tests/contract/test_renewal_resolution.py`.

### Implementation for User Story 5

- [X] T046 [US5] Implement one-operation renewal scheduling, exact `paid_through` cutoff, and Free projection in `apps/server/src/twobrain_rec_server/billing/renewal.py`.
- [X] T047 [US5] Implement Temporal renewal workflow, provider-key recovery, expiry gap, late-success incident, and refusal precedence in `apps/server/src/twobrain_rec_server/workflows/billing_renewal_workflow.py` and `apps/server/src/twobrain_rec_server/billing/renewal_resolution.py`.
- [ ] T048 [US5] Add renewal reminder, failure-to-Free, unknown, late-success and manual-resume notifications in `apps/server/src/twobrain_rec_server/billing/notifications.py` and their bounded delivery loop in `apps/server/src/twobrain_rec_server/workflows/worker.py`. (Issue #4903).
- [X] T049 [US5] Render next-charge, paid-through, renewal-off, pending-resolution and Free fallback states in `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/billing_overview_content.html` and `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/billing_subscription_content.html`.

**Checkpoint**: A failed or unconfirmed renewal never creates a grace period, an automatic retry, or an ambiguous paid state.

## Phase 8: User Story 6 — Найти платеж, чек и написать о возврате (Priority: P1)

**Goal**: Give the user trustworthy payment/receipt history and a static email-only support path while all refund handling remains outside GRAF.

**Independent test**: A user can open an invoice, copy a safe reference, open a sanitized email draft, and observe provider reconciliation; no product form, case, status, amount calculation, operator screen, CLI, or outbound refund call exists.

### Tests for User Story 6

- [X] T050 [P] [US6] Add payment-history/receipt contract tests for masking, safe references, static support copy, mailto sanitization, and no product-side refund mutation in `apps/server/tests/contract/test_payment_history_support.py`.
- [X] T051 [P] [US6] Add observed provider refund/receipt reconciliation tests for full/partial merchant-cabinet outcomes, missing webhook backstop, referral correction input, and idempotent binding in `apps/server/tests/integration/test_provider_refund_observation.py`.

### Implementation for User Story 6

- [X] T052 [US6] Implement immutable payment history, receipt availability, safe invoice reference, and masked method projection in `apps/server/src/twobrain_rec_server/billing/history.py` and `apps/server/src/twobrain_rec_server/billing/receipts.py`.
- [X] T053 [US6] Implement read-only observed provider refund/receipt reconciliation via webhook signal plus GET/list/registry backstop in `apps/server/src/twobrain_rec_server/billing/reconciliation.py`; do not add a product refund command or mutable user claim entity.
- [X] T054 [US6] Add invoice detail and history screens with `Написать письмо`, `Скопировать email`, `Скопировать номер платежа`, safe warnings, and no submission confirmation in `apps/server/src/twobrain_rec_server/cabinet/web_routes/billing.py`, `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/billing_history_content.html`, and `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js`.
- [X] T055 [US6] Add metadata-only reconciliation audit and ensure support correspondence, card data, meeting content, and raw provider payloads are excluded from logs/analytics in `apps/server/src/twobrain_rec_server/billing/audit.py` and `apps/server/src/twobrain_rec_server/observability/redaction.py`.

**Checkpoint**: Users can find evidence and contact support by email, while refund eligibility, calculation, approval, communication and execution remain an external merchant process.

## Phase 9: User Story 7 — Применить промокод без скрытых условий (Priority: P2)

**Goal**: Validate one normalized, eligible promotion and lock it safely to an invoice without invalidating unknown payment state.

**Independent test**: Valid, expired, ineligible, reused, confusable and provider-floor promo cases return distinct safe copy and reconcile atomically with checkout.

### Tests for User Story 7

- [X] T056 [P] [US7] Add promo normalization, Unicode/confusable, scope, caps, provider-floor, one-discount, and error-copy tests in `apps/server/tests/unit/test_promotions.py`.
- [X] T057 [P] [US7] Add checkout reservation/release and out-of-order payment integration tests in `apps/server/tests/integration/test_promo_checkout.py`.

### Implementation for User Story 7

- [X] T058 [US7] Implement versioned promo catalog, eligibility, normalization, reservation, redemption snapshot and safe error classes in `apps/server/src/twobrain_rec_server/billing/promotions.py`.
- [X] T059 [US7] Integrate promo preview/revalidation with checkout invoice locking and authoritative cancellation release in `apps/server/src/twobrain_rec_server/billing/checkout.py` and `apps/server/src/twobrain_rec_server/cabinet/web_routes/billing.py`.
- [X] T060 [US7] Add promo field, selected-discount explanation, and accessible recoverable error states in `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/billing_checkout_content.html`.

**Checkpoint**: A promo can change only the approved initial payable invoice and never creates a zero-total or ambiguous pending checkout.

## Phase 10: User Story 8 — Пригласить друга и получить дни подписки (Priority: P2)

**Goal**: Attribute one opaque referral link, grant 10% first-period invitee discount, and grant inviter seven or thirty calendar days after maturity with bounded reversal.

**Independent test**: A first-touch referral flows through registration and confirmed payment to maturity, applies exactly once, expires/reverses append-only, and never creates cash or a wallet balance.

### Tests for User Story 8

- [X] T061 [P] [US8] Add attribution, self-referral, duplicate, masked-identity and risk-signal tests in `apps/server/tests/unit/test_referrals.py`.
- [ ] T062 [P] [US8] Add monthly/yearly maturity, 14-day hold, 180-day rolling cap, contiguous credit, cancel-scheduled, and authoritative-observed-refund reversal tests in `apps/server/tests/integration/test_referral_rewards.py`. (Issue #4917).

### Implementation for User Story 8

- [X] T063 [US8] Implement opaque first-touch referral attribution, campaign versioning, identity binding, risk signals, and masked history in `apps/server/src/twobrain_rec_server/billing/referrals.py`.
- [X] T064 [US8] Implement invitee 10% first-period discount and inviter append-only seven/thirty-day credit ledger with maturity, expiry, cap and bounded reversal in `apps/server/src/twobrain_rec_server/billing/referral_rewards.py`.
- [X] T065 [US8] Integrate referral discount selection, paid-success trigger, observed-refund correction, and renewal anchor projection in `apps/server/src/twobrain_rec_server/billing/checkout.py`, `apps/server/src/twobrain_rec_server/billing/reconciliation.py`, and `apps/server/src/twobrain_rec_server/billing/subscription.py`.
- [X] T066 [US8] Add invite link, progress/history, paid-through/bonus-through/next-charge copy and anti-abuse-safe states in `apps/server/src/twobrain_rec_server/cabinet/web_routes/referrals.py` and `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/referrals_content.html`.

**Checkpoint**: Referral incentives reduce paid price or add service time only; no cash payout, withdrawable balance, or separate affiliate cabinet exists.

## Phase 11: User Story 9 — Получать своевременные финансовые уведомления (Priority: P2)

**Goal**: Deliver idempotent, masked, actionable trial, billing, storage, receipt, referral and safety notifications without exposing provider or meeting data.

**Independent test**: Each required lifecycle event produces one localized notification with a safe next action, preference/legal routing, retry state and no sensitive payload.

### Tests for User Story 9

- [X] T067 [P] [US9] Add notification outbox idempotency, preference bypass, delivery failure, masking, and safe-link tests in `apps/server/tests/unit/test_billing_notifications.py`.
- [ ] T068 [P] [US9] Add end-to-end event coverage for trial reminders, payment success/failure, storage thresholds, receipt state, referral credit, unknown and late outcomes in `apps/server/tests/integration/test_billing_notification_flow.py`. (Issue #4922).

### Implementation for User Story 9

- [X] T069 [US9] Implement billing notification event taxonomy, idempotent outbox records, Russian-first templates, and delivery state in `apps/server/src/twobrain_rec_server/billing/notifications.py`, `apps/server/src/twobrain_rec_server/billing/events.py`, and the existing Postal delivery worker.
- [ ] T070 [US9] Implement fair-use classification/review-deadline/appeal state with bounded reason and wire trial, payment, renewal, storage, receipt, referral, fair-use and account-close events to notifications without creating a refund correspondence event in `apps/server/src/twobrain_rec_server/billing/fair_use.py`, `apps/server/src/twobrain_rec_server/billing/events.py`, and `apps/server/src/twobrain_rec_server/workflows/maintenance_worker.py`. (Issue #4926).
- [X] T071 [US9] Add notification preferences, legal/financial override rules, safe deep links and accessible live-status rendering in `apps/server/src/twobrain_rec_server/cabinet/web_routes/settings.py`, `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/components/notifications.html`, and `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js`.

**Checkpoint**: Users receive useful next actions without GRAF receiving or storing support-email content or raw financial identifiers.

## Phase 12: User Story 10 — Оперировать биллинг и доказать готовность к запуску (Priority: P1)

**Goal**: Reconcile provider truth, daily payment/refund registries, storage and notifications, and prove controlled test-shop and real-shop launch gates.

**Independent test**: Operators can run read-only reconciliation and registry checks, inspect metadata-only gaps and metrics, stop new money mutations, and produce launch evidence without a customer-facing refund tool.

### Tests for User Story 10

- [X] T072 [P] [US10] Add reconciliation completeness, registry hash/part identity, configured-empty-report, replacement/missing-file, and gap-owner tests in `apps/server/tests/integration/test_billing_registry.py`.
- [X] T073 [P] [US10] Add monitoring, durable incident lifecycle/owner/deadline, emergency-stop, RLS inventory, redaction, accessibility, four-eyes gate metadata, and launch-canary assertions in `apps/server/tests/contract/test_billing_launch_gates.py`.
- [ ] T074 [P] [US10] Add test-shop E2E coverage for initial/saved payment, recurring decline, timeout-late success, zero binding, provider floor, merchant-cabinet refund observation, receipt observation, and zero product refund mutations in `apps/server/tests/e2e/test_billing_test_shop.py`. (Issue #4928).

### Implementation for User Story 10

- [ ] T075 [US10] Implement provider polling, observed refund/receipt/method reconciliation, separate payments/refunds registry import, completeness hashes and metadata-only gap ownership in `apps/server/src/twobrain_rec_server/billing/reconciliation.py` and `apps/server/src/twobrain_rec_server/billing/registry.py`. (Issue #4930).

  Уточнение исполнения 30.10.2026: сначала [внутренний импорт B1–B3](contracts/registry-operator-import.md)
  через `cli/billing_registry.py`, две ограниченные maintenance-only таблицы,
  миграцию и `db/rls_validation.py`; затем полная CSV/API/ledger сверка.
  Полнота файлов не означает финансовый PASS. До реализации прочитать
  независимое ревью и чистый анализ; до `[X]` выполнить DB/CLI/restart/права,
  отрицательные входы и полный остаток исходной T075. Issue не дробится.
- [X] T076 [US10] Implement Temporal reconciliation, stuck-operation, storage projection, add-on/time-credit and notification maintenance workflows in `apps/server/src/twobrain_rec_server/workflows/billing_reconciliation_workflow.py` and `apps/server/src/twobrain_rec_server/workflows/maintenance_worker.py`.
- [ ] T077 [US10] Add operational metrics, dashboards, emergency stop and read-only launch diagnostics through existing observability patterns in `apps/server/src/twobrain_rec_server/billing/monitoring.py`, `apps/server/src/twobrain_rec_server/readiness/checks.py`, and `apps/server/src/twobrain_rec_server/admin/metrics.py`. (Issue #4932).

  Порядок продолжения J5/J6 после PR7914 — 03.11.2026. Независимое ревью
  `checklists/observation-alerts.md`: 18 отмечены / 0 открыты; приняты только
  требования A1–A7, не код/установка/почта. Ниже уточнение той же US10/P1/T077,
  без новых task IDs, изменения исходных87 полных строк или закрытия #4932.
  Префикс Python-путей — `apps/server/src/twobrain_rec_server/`.

  1. Scoped analyze A1–A7/III/IV/VI → sync существующей #4932. Затем RED в
     `apps/server/tests/unit/test_billing_observation_alerts.py`,
     `apps/server/tests/integration/test_billing_observation_alerts.py`,
     `apps/server/tests/integration/test_billing_monitoring_postgres.py` и
     `apps/server/tests/contract/test_billing_observation_infra.py` по всем
     сценариям quickstart §J5/J6, включая исправления R1/R2/R3.
  2. A1: `billing/observation_probe.py`/`cli/billing_observation_probe.py` —
     один exact-maintenance/FORCE-RLS/READ-ONLY-RR снимок0109 до SQL/hooks;
     counters≤9223372036854775807, частичный охват, nullable last_event_at,
     без identity/частных полей. Бюджеты15с/statement5с/lock2с/output16KiB.
  3. A2–A5: `billing/observation_alerts.py`/`cli/billing_observation_alerts.py`
     — primary/witness/tick/status/local relay в существующем image. Сначала
     закрытая схема и replay одного защищённого append-only журнала, затем
     seven-kind stable basis, поколения/revision и честная реакция. Пределы:
     «record/manifest≤16KiB, journal≤64MiB и≤262144 records,≤500 incident
     generations, строки refs≤255 UTF-8 bytes»; UUID/SHA256 строгие, unknown
     keys/duplicate JSON keys/nonfinite/bool-as-int отклоняются. Lock≤2с,
     fsync/chain/partial-tail/disk-full/лимит → hold/noPOST без удаления.
     Activation create-once, file0600/directory0700, owner/nlink/ancestors/
     NOFOLLOW/identity проверяются. Backup/restore под тем же lock сохраняет
     accepted/consumed/сроки; restore отдельно остаётся hold до сверки.
  4. A4/R1–R3: один Postal POST≤10с за tick; durable reservation до POST,
     retry≥300с incident через basis/binding/restart; только текущие identities
     открытого incident, accepted dedup. Queue_seq переносится в конец доPOST;
     old attempts/late outcomes остаются историей. Success-only не меняет
     failure/conflict basis/owner manifest. Текст metadata-only, адрес/секреты
     только protected configuration; customer sender/retry/F273 не меняются.
     A5: create-once root-custodian manifest конкретного решения в этом чате,
     exact basis/source/incident/message; transition+consumed одним record.
  5. A6: `infra/scripts/billing-observation-probe.sh`,
     `infra/scripts/check-billing-observation.sh`,
     `infra/systemd/graf-billing-observation{,-witness}.{service,timer}`,
     `infra/env/billing-observation.example.json`,
     `infra/docs/billing-observation.md`. Fixed forced SSH/imageID/platform/
     source/no client env/stdin/PTY/forwarding; non-root/read-only/cap-drop/
     no-new-privileges, узкие mounts/секреты/ресурсы; no pull/build/restart.
     Интервал300с/gap≥900с, whole tick≤60с/remote wrapper≤25с с cleanup.
  6. A7: изолированные unit/PG/new-process/двухузловые synthetic проверки
     quickstart1–7, все отрицательные FS/relay/SSH/Docker/crash/retry/restore
     границы и полный limit journal. Затем `changes/unreleased/F140.yaml`,
     независимые code review/converge, профильная валидация и exact-SHA/base
     PR gates/common before-after/tree-parent. Старые68 тестов не повторять
     без затронутой зависимости. Параллельные примеры — независимые файлы
     тестов source и controller; реализация после общего RED/допуска.
  7. Установка, независимый Postal route с обоих узлов при DB/maintenance
     outage, реальные ticks/custody и получение учебного письма владельцем —
     отдельная разрешённая эксплуатационная приёмка A7. Общая потеря узлов/
     сети/Postal остаётся unavailable. Полный FR089/O6/58 gaps/T070/T077[ ]
     и исходные сроки не принимаются этим порядком; initial scope только J5/J6.

  После PR7898: J1–J6 O16, принятые ответы владельца03.11. Первый шаг —
  append-only billing_reconciliation_observations в db/models/billing.py,
  новая миграция от фактического head, db/rls_validation.py, узкий
  billing/reconciliation_observation.py, текущая activity workflows/worker.py
  и агрегат billing/monitoring.py (server prefix прежний). Сначала
  checklists/reconciliation-observations.md/независимый допуск и scoped analyze;
  затем RED и перечисленные в quickstart unit/PG/CLI/ActivityEnvironment,
  restart/конкуренция/constraints/roles/rollback/restore/deadline/privacy,
  независимые code/converge/exact PR gates. Нельзя писать код до допуска.
  Регулярное наблюдение, почта/retry и сохраняемая реакция с owner/severity/
  evidence/deadline остаются обязательным продолжением здесь же; принятый
  порядок5мин/15мин/retry≥5мин и исходные сроки не отменяются. Это не новая
  задача/issue; исходная строка T077 и все87 task lines сохраняются, T077[ ].

  Порядок доработки 01.11.2026: [O1–O8](contracts/operator-observation.md),
  reviewer-owned checklists/operator-observation.md и независимый допуск,
  scoped analyze, подтверждение существующей #4932; затем минимальный
  billing/monitoring.py + cli/billing_monitoring.py и существующий unit test
  плюс tests/integration/test_billing_monitoring_postgres.py (префиксы plan).
  Настоящие CLI/guard/снимок/timeout/privacy/no-write, review/converge и
  три PR gates обязательны. Исходный текст/ID/владелец сохранены; отменённые
  F272/F199 stop/gates не восстанавливаются. Admin/readiness/F254 не меняются.
  Полный FR-089/O6 (все источники/регулярность/тревоги/сохраняемая реакция)
  остаётся здесь; первый отчёт не даёт `[X]` или закрытия issue.

  Следующий срез после PR7884: P1–P6 контракта O9/free_projection,
  reviewer-owned checklists/free-projection.md → независимый допуск →
  scoped analyze/существующая #4932 → новые RED и PostgreSQL/CLI сценарии
  quickstart → минимальная доработка того же monitoring.py и двух названных
  unit/integration test файлов → независимое review/converge/exact PR gates.
  Это порядок исполнения T077, не новая задача; все исходные строки прежние.

  Далее после PR7887: C1–C6 O10/credit-ledger той же T077 в
  apps/server/src/twobrain_rec_server/billing/monitoring.py и существующих
  apps/server/tests/unit/test_billing_monitoring.py,
  apps/server/tests/integration/test_billing_monitoring_postgres.py.
  Сначала reviewer-owned checklists/credit-ledger.md, scoped analyze/issue
  sync; затем RED, ограниченная агрегация и реальные сценарии quickstart,
  независимое review/converge и точные PR gates. Состояния/временные признаки
  строк не принимают add-on/job измерители и полный O6; T077 остаётся [ ].

  После PR7890: R1–R6 O11/refund inventory, reviewer-owned
  checklists/refund-inventory.md → независимый допуск → scoped analyze и
  прежняя #4932 → RED → одна агрегация в том же billing/monitoring.py и
  существующих unit/integration файлах выше → реальные PostgreSQL/CLI,
  no-write/privacy/роли/снимок/ошибка схемы → независимые review/converge и
  точные PR gates. Чеки/финансовая сверка остаются null; T077 [ ] и все
  исходные полные task lines сохраняются без новой задачи или issue.
  После PR7894: Q1–Q6 O13/receipt observation inventory в той же T077;
  checklists/receipt-inventory.md/независимый допуск → analyze/та же #4932 →
  RED → helper в прежнем billing/monitoring.py и случаи в прежних unit/
  integration файлах выше → настоящие SQL JSON/CLI/FORCE RLS/снимки/роли/
  no-write/privacy/схема → review/converge/exact PR gates. До допуска нового
  кода нет. Это порядок исходной задачи, не новая task; все87 task lines,
  T077[ ],58gaps/полный O6/исходные сроки сохраняются.

  После PR7892: F1–F6 O12/fair-use inventory в той же T077; сначала
  checklists/fair-use-inventory.md/независимый допуск → scoped analyze/прежняя
  #4932 → RED → одна агрегация в том же billing/monitoring.py и два названных
  unit/integration файла → реальные PostgreSQL/CLI/constraints/forced RLS,
  границы/снимки/приватность/no-write/схема → независимые review/converge и
  точные PR gates. Это порядок исполнения, не новая задача; все87 полных
  task lines, T077 [ ], полный O6 и58 gaps сохраняются.

  После PR7896: D1–D6 O14/deletion request inventory исходной T077;
  checklists/deletion-inventory.md/независимый допуск → scoped analyze/та же
  #4932 → RED → один helper в прежнем billing/monitoring.py и случаи в прежних
  apps/server/tests/unit/test_billing_monitoring.py,
  apps/server/tests/integration/test_billing_monitoring_postgres.py → реальные
  CLI/PG/forcedRLS/NOTNULL/unknown/privacy/снимки/no-write/схема/роли → независимые
  code/converge/exact PR gates. Это порядок исходной задачи, не новая task.
  Все87полных task lines/T077[ ]/58gaps/полныйO6/T070/сроки остаются открытыми.

  После PR7897: S1–S6 O15/storage projection той же T077; сначала
  checklists/storage-projection.md/независимый допуск → scoped analyze/та же
  #4932 → RED → один collector в прежнем billing/monitoring.py и сценарии в
  apps/server/tests/unit/test_billing_monitoring.py,
  apps/server/tests/integration/test_billing_monitoring_postgres.py. Existing
  effective_paid_storage/_active_reserved_bytes/project_active_playback_storage
  с общим as_of/явными аргументами; настоящие PG/CLI/500–501/forcedRLS/снимки/
  privacy/no-write/schema/helper failures → независимые code/converge/exact
  PR gates. Исходная строка T077 и все87 полных task lines сохраняются, новой
  задачи/issue нет; T077[ ]/T070/полныйO6/58gaps/исходные сроки остаются открытыми.

- [ ] T078 [US10] Add test-shop and controlled real-shop canary runbooks, environment separation, provider capability evidence, legal/finance sign-off records, and rollback/stop procedure in `specs/140-user-account-billing/quickstart.md` and `docs/runbooks/billing-launch.md`.

**Checkpoint**: Launch evidence proves immediate-Free behavior, unlimited paid core, finite storage, provider reconciliation and external merchant refund handling before public enablement.

## Phase 13: Polish & Cross-Cutting Concerns

**Purpose**: Close quality, documentation, accessibility, security, product-market and release gates. Interim evidence tasks may complete while stories remain open; T083 is the final cross-artifact closeout and runs only after every selected story and T084–T087 are resolved.

- [ ] T079 [P] Run accessibility, clean-room, moderated usability (≥90% discovery in 2 minutes), and timed cancel (≤3 screens/60 seconds) review for all account/billing templates, keyboard paths, 200% reflow, reduced motion and disabled-JavaScript fallback; include the separate public landing pass in `docs/evidence/140-user-account-billing/landing-review.md`, plus `apps/server/tests/contract/test_billing_accessibility.py`, `apps/server/tests/integration/test_billing_usability.py`, and `docs/evidence/140-user-account-billing/usability.md`.
- [ ] T080 [P] Run security/redaction review for secrets, RLS, CSRF, provider payloads, PostHog/Yandex masking, audit fields and support-email boundaries in `apps/server/tests/contract/test_billing_security.py` and `docs/agent-guidance/product-gates.md`.
- [X] T081 Update public behavior, migration impact, operational limitations and Russian release notes in `docs/current-product-status.md`, `CHANGELOG.md`, and `specs/140-user-account-billing/quickstart.md`.
- [X] T082 Execute the interim focused quickstart scenarios, `git diff --check`, repository checks and `infra/scripts/ci-local.sh --fast`; record evidence and remaining approved gaps in `specs/140-user-account-billing/quickstart.md`. Completion records an interim baseline and does not close Phase 13.
- [ ] T083 After every selected story and T084–T087, run `$speckit-analyze`, resolve all critical blockers, and attach the selected high-risk validation lane and task evidence to `specs/140-user-account-billing/` before issue synchronization or implementation closeout.
- [ ] T084 [P] Define and evidence the Russia-first primary self-service segment, JTBD, meeting-frequency/problem baseline and testable GRAF value hierarchy in `specs/140-user-account-billing/research.md` and `docs/evidence/140-user-account-billing/product-market.md`.
- [ ] T085 [P] Validate base price, 250 MB/500 MB/2 GB packaging and 5/20/100/500 GB ladder with dated comparable-plan research, target-user comprehension/WTP, p50/p90/p99 accepted usage, compute/storage/egress/backup COGS, gross-margin floor and fair-use sensitivity in `specs/140-user-account-billing/research.md` and `docs/evidence/140-user-account-billing/pricing-economics.md`.
- [X] T086 [P] Define privacy-safe activation/funnel/retention/add-on/manual-reactivation metrics and promo/referral CAC, K-factor, cannibalization, liability, fraud-loss, support-contact and stop/rollback guardrails with owner, cohort, denominator, window, target and decision rule in `specs/140-user-account-billing/contracts/product-metrics.md`.
- [ ] T087 Add non-coercive contextual upgrade requirements for Free 80%/100%, trial T-3/T-1/expiry and blocked archival admission; incorporate approved T084–T086 decisions into `specs/140-user-account-billing/spec.md` and `specs/140-user-account-billing/contracts/account-ia-ux-ui-cx.md`, then re-run `checklists/product-market-2026.md`.

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies; T001–T004 may run in parallel.
- **Foundational (Phase 2)**: Depends on Setup; tests T005–T009 must be written and fail before T010–T016. This phase blocks every user story.
- **User Stories**: US1 and US2 may start after Foundation. US3 depends on catalog/entitlement primitives from US1/US2. US4 depends on US3’s confirmed subscription. US5 depends on US4’s authority. US6 depends on US3’s invoice/receipt and Foundation provider observation. US7 depends on US3 checkout. US8 depends on US3 and US6 observation. US9 depends on lifecycle events from US1–US8. US10 runs after the flows it reconciles and extends US6’s observation with operational registry evidence.
- **Polish (Phase 13)**: Depends on all selected stories and their evidence; T084–T087 must resolve the product-market gates, then T083 must be clean before final GitHub issue sync and `$speckit-implement` closeout.

### User Story Dependencies

- **US1 (P1)**: Foundation only; account and trial are the MVP entry point.
- **US2 (P1)**: Foundation only; uses existing `TrackArtifact` and ingest/deletion flows.
- **US3 (P1)**: Foundation + US1 owner/trial state + US2 catalog/storage projection.
- **US4 (P1)**: US3 confirmed payment and entitlement.
- **US5 (P1)**: US4 recurring authority and method.
- **US6 (P1)**: US3 payment history plus Foundation provider observation; no user refund mutation.
- **US7 (P2)**: US3 checkout intent/invoice locking.
- **US8 (P2)**: US3 confirmed payment, US6 observed provider outcome, US5 subscription anchor.
- **US9 (P2)**: Lifecycle events from US1–US8.
- **US10 (P1)**: All provider operations and lifecycle flows that it reconciles.

### Parallel Execution Examples

- After Foundation: US1 account/trial (T017–T023) and US2 usage/storage (T024–T031) can proceed in parallel on different modules.
- Within US3: T032 and T033 can run in parallel; after they fail, T034 and T037 can proceed in parallel, then T035–T036 integrate them.
- Within US6: T050 and T051 can run in parallel; T052 and T054 can proceed in parallel after Foundation, while T053 remains the read-only reconciliation implementation.
- Within US7/US8/US9: unit/contract tests can run in parallel with separate story tests once their declared predecessor story is complete.
- Within US10: registry tests (T072), launch-gate tests (T073), and test-shop E2E design (T074) can be prepared in parallel before T075–T078.

## Implementation Strategy

### MVP First

1. Complete Setup and Foundation.
2. Deliver US1 account/trial and US2 usage/storage.
3. Deliver US3 hosted YooKassa checkout with receipt and entitlement evidence.
4. Stop and validate the MVP independently with quickstart scenarios before adding subscription controls, support-history, growth and operations slices.

### Incremental Delivery

1. Add US4 and US5 for payment method, cancel/resume and immediate-Free renewal resolution.
2. Add US6 for history and the external email-only support boundary.
3. Add US7–US9 for promos, referrals and notifications.
4. Add US10 and Polish for reconciliation, launch gates, security/accessibility and release evidence.

### Completion Criteria

- Every task above remains unchecked until implementation and its listed validation evidence pass.
- No task may add an in-product refund form, claim/status/timeline, amount calculator, operator refund UI, refund CLI, or outbound refund mutation.
- No task may introduce a second paid base tier, commercial paid-minute cap, renewal grace/retry path, or duplicate storage inventory.


## Сверка отметок — 2026-10-27

У T062/#4917, T068/#4922, T070/#4926, T075/#4930 и T077/#4932 сняты
неподтверждённые отметки выполнения. Исходные требования, порядок и связи
всех 87 задач сохранены; другие отметки не менялись. Причины и границы
проверки: [quickstart](quickstart.md#сверка-пяти-открытых-задач--2026-10-27).
Это исправление учёта, а не отмена задач или приёмка оставшейся реализации.

## Применимость проверки интерфейса — 2026-10-30

В исходных T023/T079 термин `clean-room` означает независимую реализацию
и проверенные права на материалы по текущей FR-081 и конституции §VII.
Он не требует отличия от наблюдаемых Krisp UX/UI/IA или переписывания
функциональных подписей. Исходные ID, описания и отметки всех 87 задач
сохранены. Эта сверка устраняет противоречие X7 в рамках T079/T083;
доступность, ручная приёмка и остальные открытые критерии не принимаются.


## Повторная приёмка T074 — 2026-10-31

Неподтверждённая общая отметка T074 снята; ID, исходное описание и владелец
сохранены. #4928 открыта. Три старых offline provider-boundary проверки не
подтверждают сохраняемую цепочку recurring decline. Уточнение spec/plan и
`checklists/renewal-decline.md` принимают только действующие F278 FR-014
внутри автоматической части; остальные реальные/выпускные критерии остаются.

## Отмена исторической совокупной T023 — 31.10.2026

T023 / #4877: NOT_PLANNED после принятия сверки отдельным PR.
Исходное описание задачи сохранено, отметка `[X]` снята: это не принятие
реализации. Владелец сверки — агент уборки репозитория; владелец нового
продуктового решения о возврате browser-only пути — владелец продукта.
Причина: принятые F210 FR017/F278 FR006 заменили отдельную desktop сводку
и обязательный внешний billing handoff действующим встроенным кабинетом.

Действующая приёмка account UI/клавиатуры/фокуса/no-JS/ошибок не отменена:
T079/#4936, F210 T017/#5961, F278 T017/#7323/T025/#7332 остаются открытыми.
Account-close, внешний refund и денежные/защитные границы сохраняются.
Возврат T023 допускается только по новому явному решению о смене пути оплаты
с отдельными требованиями и проверками. Подробности и пределы —
`reconciliation-t023-20261031.md`. Остальные 86 задач не меняются.


## Текущий срез T048 / #4903 — 01.11.2026

Исходное описание T048 сохранено; отметка выполнения снята по подтверждённому
отсутствию рабочих producers. Порядок внутри существующей задачи:
1. Независимое reviewer-owned `checklists/renewal-unknown.md`, scoped analyze.
2. Причинный PostgreSQL RED для сообщения при cutoff и отсутствие внешнего HTTP.
3. Проверка связи операции/счёта с текущим плательщиком и периодом; запись
   существующего UNKNOWN в той же транзакции, без изменения платежей/доступа.
4. PostgreSQL commit/restart/dedup/rollback и отрицательные границы; профильные
   регрессии, review/converge и точные PR gates.
5. Оставить общую T048/#4903 открытой: reminder, failure-to-Free, late-success,
   manual-resume и фактическая доставка требуют отдельной проверки/доработки.

Следующий срез той же T048: подтверждённый отказ → Free. Сначала требования
и независимый checklists/renewal-final-failure.md, затем RED двух входов,
одна общая безопасная запись события, сохраняемые PostgreSQL границы,
review/converge и обязательные PR SHA/base gates. T048 остаётся `[ ]`.


Следующая часть исходной T048 — напоминание в первом окне. Требования и
reviewer-owned checklists/renewal-reminder.md предшествуют коду; затем RED,
минимальный producer существующей очереди, PostgreSQL/копия/границы,
review/analyze/converge и точные PR gates. Полная T048 остаётся `[ ]`.


Следующая часть T048/#4903 — содержание подтверждения оплаты и включения
продления по FR-047/070/071/105. Порядок: уточнение spec/contract/plan →
независимый checklists/notification-content.md → scoped analyze → RED
настоящих producers → минимальные payload/renderer → PostgreSQL и профильные
регрессии → review/converge → точные PR gates. Пути: billing/notifications.py,
billing/entitlements.py, billing/purchases.py, cabinet/web_routes/billing.py;
существующие тесты unit/test_billing_notifications.py,
integration/test_billing_purchase_journey.py и integration/test_billing_return.py. Все исходные
87 ID/описаний сохраняются; T048/T068 остаются `[ ]`, новых дублей issues нет.

## Уточнение исполнения T075/T077 — регистрация чеков, 10.11.2026

Без новых идентификаторов задач. Исходные T074/T075/T077 остаются открытыми.

1. **T075/T077:** независимое ревью `checklists/receipt-escalation.md`,
   затем analyze требований R1–R6 и сверка #4930/#4932.
2. **T075:** сначала отрицательные сценарии
   `apps/server/tests/integration/test_billing_receipt_escalation.py`;
   затем общий переход в `apps/server/src/twobrain_rec_server/billing/receipts.py`
   и его вызовы в `entitlements.py`, `webhook_reconciliation.py`,
   `reconciliation.py` того же каталога. Подключить ограниченный периодический
   проход в `apps/server/src/twobrain_rec_server/workflows/worker.py`.
3. **T077:** источник сохраняет подтверждённые основания, просрочки и
   неизвестный возраст; после проверки источника — отдельное уточнение
   стыка с независимым O16, без клиентской очереди и без новых внешних служб.
4. **T074:** приёмка всего test-shop сценария и остальных исходных требований
   отдельно от проверок с подставным провайдером. Все исходные строки задач,
   существующие ограничения и сроки остаются в силе.

### Исполнение T077/#4932 — передача фискальных оснований O16

Уточнение прежней задачи, без новых ID и изменения исходной отметки.
Ворота: чеклист `checklists/receipt-o16.md` → независимое ревью →
scoped analyze ROC1–ROC4 → сверка существующей #4932.

1. PostgreSQL, RED до миграции: `apps/server/tests/integration/test_billing_monitoring_postgres.py`
   и отдельные сценарии миграции/ролей. Затем следующая свободная миграция в
   `apps/server/src/twobrain_rec_server/db/migrations/versions/`,
   `apps/server/scripts/bootstrap_runtime_database_roles.py`,
   `apps/server/src/twobrain_rec_server/db/rls_validation.py` и
   `specs/031-rls-hardening/contracts/rls-policy-matrix.md`: анонимный
   append, полный перенос, отказ неполных прав, атомарность и прежнее удаление.
2. Транспорт только после источника: `billing/observation_probe.py` и
   `billing/observation_alerts.py` под `apps/server/src/twobrain_rec_server/`,
   `infra/scripts/billing-observation-probe.sh` и
   `infra/docs/billing-observation.md`: закрытый v2, replay, прежний peer
   status, отдельные виды, recovery/lineage и прежняя очередь/паузы.
   RED в `apps/server/tests/unit/test_billing_observation_alerts.py` и
   `apps/server/tests/contract/test_billing_observation_infra.py`.
3. Пройти quickstart, независимое ревью и converge; связать результат с
   прежней #4932 и PR. GitHub exact SHA/base — отдельно. T074 test-shop,
   release/full, production и фактическая приёмка владельцем не считаются
   пройденными по локальному циклу.

### Граница текущего среза T048/T068: позднее начало оплаченного периода

Сохранить исходные T048 и T068 без отметки выполнения. Производитель
в `billing/entitlements.py`, существующий шаблон в `billing/notifications.py`
и постоянная проверка в `test_billing_notification_flow.py` входят в срез,
описанный в плане и quickstart. #4903/#4922 частично связаны, #7524 требует
отдельного получения. Старый тест, требующий Free только из-за отзыва,
не принимается как свидетельство F278 FR-041; решение по неиспользуемому
помощнику и его потребителям отдельно от добавления фразы в письмо.

## Исполнение US9/P2, T070/#4926 и T068/#4922 — пороги архива

Уточнение существующих задач от 11.11.2026, полоса high-risk-product.
Все 87 исходных строк, ID, описания и отметки сохранены; T070/T068 `[ ]`.
Только S1–S9 Session 2026-11-10, US9/AC4–5, FR-017–019/070–072/093–099
и действующий F278 FR-019/026/028. Новых задач или issues нет.
Независимый `checklists/storage-notices.md`: 14 отмечены / 0 открыты,
основания — `review-storage-notices-requirements.md`. Это качество требований;
перед исходниками ещё обязательны scoped Analyze и синхронизация этих issues.

1. **T068, RED до реализации.** Добавить причинные случаи S9 в
   `apps/server/tests/integration/test_billing_notification_flow.py`,
   единичные проверки текста в `apps/server/tests/unit/test_billing_notifications.py`
   и проверки state/cursor/RLS/конкуренции в
   `apps/server/tests/integration/test_billing_storage_notifications.py`.
   Использовать существующий одноразовый PostgreSQL runner с полным Alembic
   head, настоящими ограниченными ролями и подставным транспортом.
   Начальную синтетическую историю можно подготовить отдельно; сам подъём
   вызвать рабочими upload/finalize/normalization через
   `_accept_first_party_recording`/`FakeNormalizationPipeline` либо настоящим
   expiry/entitlement transition. Прямой enqueue/ручная правка TrackArtifact
   или cache не заменяют причинный переход. До кода зафиксировать ожидаемый RED.
2. **T070, схема и права после RED.** Новая миграция от фактического head в
   `apps/server/src/twobrain_rec_server/db/migrations/versions/`, модели в
   `apps/server/src/twobrain_rec_server/db/models/billing.py`, exports в
   `apps/server/src/twobrain_rec_server/db/models/__init__.py`.
   Две таблицы из `data-model.md` §«Состояние наблюдения архива»:
   `storage_notification_states`: «workspace_id PK/FK workspaces ON DELETE CASCADE»;
   «owner_user_id nullable UUID»; «band normal/80/95/100»;
   «generation bigint >=0»; «observed_at finite UTC». Ошибка не создаёт state,
   generation не сбрасывается при смене владельца A→B→A.
   `storage_notification_scan`: одна system-owned строка; nullable cycle/upper/after,
   все null на границе; finite cycle с upper, after nullable либо <=upper;
   «attempted/observed/skipped/failed — неотрицательные bigint»;
   «attempted=observed+skipped+failed». Закрытый nullable last_error_code;
   last_finished_summary nullable, только started_at/finished_at/четыре
   счётчика/incomplete, finite UTC, finished_at>=started_at, unknown keys denied.
   Summary сохраняется при новом цикле; cursor UUID не FK.
   ENABLE/FORCE RLS, exact maintenance session_user=current_user,
   row_security=on, без superuser/BYPASSRLS. State SELECT/INSERT/UPDATE только
   billing_reconciliation/billing; SELECT/DELETE также для
   billing_reconciliation/account. Cursor SELECT/INSERT/UPDATE только billing.
   Обновить `apps/server/scripts/bootstrap_runtime_database_roles.py`,
   `apps/server/src/twobrain_rec_server/db/rls_validation.py` и
   `specs/031-rls-hardening/contracts/rls-policy-matrix.md`; повтор bootstrap
   не возвращает широкие grants. Непустая таблица запрещает downgrade,
   исторического backfill и сброса поколений нет.
3. **T070, наблюдение.** В
   `apps/server/src/twobrain_rec_server/billing/storage_notifications.py`
   переиспользовать playback projection из `billing/storage.py`, classifier
   из `billing/catalog.py` и effective capacity из `billing/purchases.py`/
   `billing/entitlements.py` по действующим правилам кабинета и допуска.
   При необходимом общем helper обновить всех callers, включая
   `apps/server/src/twobrain_rec_server/cabinet/web_routes/billing.py` и
   `apps/server/src/twobrain_rec_server/normalization/service.py`;
   не создавать второй расчёт или неиспользуемую абстракцию.
   Один fresh as_of после locks; Free без subscription включён, резервы
   исключены. S1/S2: first/highest-only, отдельные 80→95→100, снижение без
   письма, новый подъём и generation; отсутствие права/почты/согласия
   продвигает band без backlog, ошибка его не поглощает. Closed/merged
   owner не создаёт state. Один helper eligibility для observer и claim.
4. **T070, обход и стык.** В том же модуле cursor lock до savepoint →
   workspace advisory → Workspace row → subscription/state → snapshot/outbox
   → advance → commit. Cycle cutoff/upper фиксируют конечный UUID диапазон
   personal workspaces; created_at после cutoff и поздний commit позади cursor
   идут в следующий цикл. До100 кандидатов/вызов, budget60с/query2с/lock1с;
   условная граница ceil((N+L)/100)+1 вызовов по Plan, не календарный SLA
   или единый MVCC. Savepoint failure сохраняет только cursor aggregate/error/
   advance, не пишет state после освобождения Workspace lock; общий DB/commit
   failure не объявляет продвижение. Сохранять cancellation и видимую неполноту.
   В `apps/server/src/twobrain_rec_server/workflows/worker.py` подключить отдельную
   storage транзакцию после предыдущего commit существующей activity,
   guard `require_billing_maintenance_database`; новый workflow не создавать.
5. **T070, доставка.** Тот же `workflows/worker.py` и
   `apps/server/src/twobrain_rec_server/billing/notifications.py`:
   storage включён в выборку без verified address; advisory → Workspace row
   → queue lock, eligibility исходного recipient/marker/member/billing owner/
   active unmerged identity/current address/preference проверяется перед
   committed unknown claim. Подтверждённая потеря → terminal suppressed,
   ошибка → durable retry>=60с/max5; unknown Postal автоматически не повторять.
   Locks не держать через HTTP. Optional STORAGE_THRESHOLD отделить от
   mandatory STORAGE_SELECTION_CHANGED. Payload только storage_level,
   storage_used_bytes, storage_capacity_bytes, storage_observed_at,
   action_path=/billing/usage; «целые used>=0, capacity>0», band соответствует
   классификации. Исторические точные байты/дата МСК; старый malformed snapshot
   подавить, не дополнить текущим. Нет TTL/supersede, текущих обещаний лимита,
   покупки или доступности удалённых данных; один безопасный переход.
6. **T070, жизненный цикл.** В
   `apps/server/src/twobrain_rec_server/auth/account_closure.py` удалить state
   по frozen content_workspace_ids в существующем begin-finalization, атомарно
   с identity=closed до fanout. Workspace сохраняется, одного FK недостаточно.
   Observer/sender не берут closure request после Workspace; после rollback
   savepoint нет даже error-state. Cooling не новый запрет; blocked/retry после
   begin и физический cascade не воскрешают state. Нового finalizer нет.
7. **T068, окончательная матрица до closeout среза.** Полный Quickstart
   §«Storage 80/95/100», пункты1–7: bytes до/на/после, первый/скачок/снижение/
   повторный подъём, Free без subscription, рабочая замена M4A и capacity-only;
   commit/new sessions/rollback/unknown commit/restart/concurrency и один
   сохранённый claim перед одним stub. Отрицательные owner/member/merge/closed/
   email/preference после enqueue и после выборки. N=0/1/100/101/201, новые
   вставки с обеих сторон cursor, поздние commit, lock/query/deadline/cancel/
   DB failures, savepoint-finalizer race и сохранённый summary. Настоящие
   RLS/SET ROLE/ошибочные contexts, повтор bootstrap, CHECK, пустой downgrade/
   upgrade и отказ непустого, synthetic backup/restore с поколениями.
   Проверить template allowlist/исторический текст, retry и unknown no replay.
   Дополнить только затронутые
   `apps/server/tests/unit/test_account_closure.py`,
   `apps/server/tests/unit/test_account_close_fanout.py`,
   `apps/server/tests/integration/test_account_lifecycle.py`,
   `apps/server/tests/unit/test_billing_reconciliation_activity.py`,
   `apps/server/tests/integration/test_storage_quota.py` и проверки ролей
   по фактическим callers; неизменные положительные наборы не повторять.
8. **Общие ворота.** Независимое ревью кода → `$speckit-converge` → профильные
   PostgreSQL/notification/publication/account-close/RLS и Ruff/процесс/diff;
   owned `changes/unreleased/F140.yaml`; обязательные governance-fast,
   macos-pr и pr-metadata на точном source SHA/текущей базе, штатный common
   до/после merge и readback parent/tree. Synthetic container/dump удалить
   finally, сохранить только logs/XML/versions/hashes/results.

Зависимости: review14/0 → Analyze → existing issues → T068 RED → T070
schema/roles → observer → activity/sender/finalizer → T068 причинная матрица
→ code review/converge/PR. Независимые файлы unit renderer и PG observer
могут готовиться параллельно после допуска; общие worker/finalizer последовательно.
Минимальный результат US9 — одна сохраняемая наблюдаемая цепочка всех трёх
уровней без нового сервиса/зависимости. Широкие T070/T068, остальные семейства,
реальное получение #7524, GRAF Dev, выпуск/сервер имеют собственную приёмку.
Этот порядок не меняет исходный `[P]` T068 в обещание независимости от T070.

## Исполнение US9/P2, T070/#4926 и T068/#4922 — операторский fair-use, 11.11.2026

Это порядок исполнения двух существующих task rows, не новые task IDs/issues.
Все87 исходных строк/ID/описаний/отметок сохраняются. T068/T070 остаются `[ ]`:
полный FR107, другие события и реальная приёмка не выполнены. Lane
high-risk-product; Spec FU1–FU8, Plan Phase0/1, data-model и единственный
normative contracts/fair-use-operator.md, включая audit v1. Независимый
review-fair-use-operator-requirements.md:19checked/0unchecked после R1;
это качество требований, не приёмка кода. До выполнения ниже нужны scoped
Analyze и сверка существующих issues по канону, без дубликатов.

**Цель US9 этого среза:** уполномоченная служба вручную принимает проверенное
внешнее основание, субъект подаёт апелляцию, служба сохраняет решение;
каждый первый переход атомарно даёт audit/outbox и одну подставную отправку.
**Независимая проверка:** настоящий CLI create → commit → отдельный LOGIN
сеанс → cabinet POST/CSRF → resolve cleared/confirmed → отдельные commit →
обычный sender/committed claim → один stub на событие/исходного адресата;
повтор и rollback не создают дубликатов, SQL app/maintenance не подделывает
audit. Очередь напрямую в положительном причинном сценарии не заполнять.

### Подготовка и фундамент: T068 RED → T070 PostgreSQL

1. **T068, причинный RED.** В
   `apps/server/tests/integration/test_billing_notification_flow.py` добавить
   рабочий CLI/кабинет→commit→sender сценарий; DB/роль отрицательные случаи
   выделить в `apps/server/tests/integration/test_billing_fair_use_operator.py`,
   CLI format/dry-run в `apps/server/tests/unit/test_billing_fair_use_cli.py`.
   Зафиксировать точные nodeids и ожидаемый предметный отказ до продукта,
   затем исполнять только новые и действительно затронутые прежние случаи.
   Проверить весь контракт Quickstart §операторского источника1–12,
   реальные PostgreSQL17 LOGIN/FORCE RLS и отдельные sessions, без внешней сети.
2. **T070, защита фактических переходов.** От проверенного head0112 добавить
   `apps/server/src/twobrain_rec_server/db/migrations/versions/0113_fair_use_operator_history.py`:
   BEFORE INVOKER review guard, AFTER DEFINER automatic audit и BEFORE INVOKER
   audit namespace guard по выбранному контракту; новая таблица не нужна.
   Физические10столбцов/8metadata keys/типы/null/enum audit v1 — только из
   contracts/fair-use-operator.md, без второй схемы. Operator-ref
   «ASCII `^op-[0-9a-f]{32}$`, ровно35символов», без trim/casefold/coercion;
   maintenance declarations transaction-local и отдельно от actual authority.
   DB задаёт первый starts_at/review_by ровно+24ч, appealed_at/ref, resolved_at;
   original/first/terminal metadata и no-op updated_at неизменны. Resolve
   допустим только при canonical created audit; legacy без backfill/рассылки.
   RLS split SELECT/INSERT/UPDATE убирает старый FOR ALL/DELETE; UPDATE USING
   сохраняет validated F178 SELECT FOR UPDATE/FOR SHARE, WITH CHECK+guard
   запрещают actual merge UPDATE. rec_maintenance_allowed один не authority.
3. **T070, права и совместимость.** В
   `apps/server/scripts/bootstrap_runtime_database_roles.py` и
   `apps/server/src/twobrain_rec_server/db/rls_validation.py` поддержать exact
   роли/схему. NOLOGIN NOINHERIT NOSUPERUSER NOBYPASSRLS NOCREATEDB
   NOCREATEROLE NOREPLICATION writer имеет только schema USAGE и INSERT10
   audit столбцов, без SELECT/UPDATE/DELETE/sequence/membership/ownership
   таблиц/чужих функций. fixed search_path=pg_catalog,pg_temp, qualified public
   refs, row_security=on, REVOKE PUBLIC/runtime EXECUTE, ENABLE ALWAYS и
   TRUNCATE guard; запрет runtime SET session_replication_role/attach/disable.
   Table+column REVOKE после broad bootstrap grants до того же commit;
   проверять definitions/owner/effective ACL/memberships/parameter ACL после
   двух bootstrap и в новой LOGIN session. Частичная схема/небезопасная роль
   отказывает атомарно. Непустая новая история блокирует destructive downgrade;
   старые строки сохраняются без поддельного actor/time/audit.

### Рабочая история US9: T070 create → appeal → resolve → sender

4. **T070, единый операторский путь.** Создать
   `apps/server/src/twobrain_rec_server/cli/billing_fair_use.py` по прежнему
   billing_registry/SafeParser и require_billing_maintenance_database;
   в `apps/server/src/twobrain_rec_server/billing/fair_use.py` использовать
   общие create_review/persist_review и сохраняемое resolve. Default READ ONLY,
   --execute, no backdate/urgent/protected capability; только
   server_processing|storage, четыре прежних reason, непрозрачный evidence-ref,
   точный operator-ref/evidence-reviewed. Конечные поля решения
   «cleared: not_substantiated|no_longer_applicable; confirmed: basis_confirmed».
   Workspace→review→audit/outbox; membership/identity NOWAIT/rollback без
   обратного ожидания с F178/closure. Проверять активную связь/owner/closed/
   finalizing, совместимость replay, неизменные даты и конфликт решения.
   SQL-generated audit Python не вставляет. Вывод только result_code/dry_run/
   status, без аргументов/DSN/SQL/traceback. Повтор после terminal не ставит
   старое notice и не добавляет нового адресата.
5. **T070, апелляция и честный кабинет.** Обновить только нужные стыки
   `apps/server/src/twobrain_rec_server/cabinet/web_routes/fair_use.py`,
   `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/fair_use_content.html`
   и общего billing/fair_use.py. Сохранить session/CSRF/subject/lineage,
   first appeal→один audit/outbox, повтор/terminal→no-op. DB timestamp не должен
   ломать прежний первый result=appealed против already_appealed: не сравнивать
   его с app timestamp как доказательство первого перехода. UI/mail различают
   notice/appeal/result и исторический deadline, не обещают enforcement,
   снятие всех санкций или реальную доставку. Restricted/appealed остаются
   F178 blockers, notice/cleared/confirmed исключены include_confirmed=False.
   Сохранить keyboard/focus/status/CSRF и структуру страницы без новых assets.
6. **T070, очередь и sender.** В
   `apps/server/src/twobrain_rec_server/billing/events.py`,
   `apps/server/src/twobrain_rec_server/billing/notifications.py` и
   `apps/server/src/twobrain_rec_server/workflows/worker.py` сохранить family
   fair_use.review, разные стабильные review/phase keys и неизменного subject/
   отличного owner на момент перехода. Payload только phase/capability/reason/
   исторический review_by МСК/action_path=/account/fair-use; служебная связь
   с review не отображается. До claim вновь проверять источник/исходного
   получателя/active identity/current право/verified email; не следовать merge
   или новому owner. Missing-address строки выбираются для terminal suppression.
   Подтверждённая утрата→suppressed; read error→durable retry «не более пяти
   суммарных попыток и не раньше чем через60секунд» в selector И claim.
   Mandatory mail игнорирует marketing preference, claim commit до HTTP,
   locks не держать через HTTP, unknown после POST не повторять.
7. **T070, безопасная совместимость очистки.** В
   `apps/server/scripts/cleanup_smoke_artifacts.py` actual maintenance+exact
   cleanup context→прежний Workspace root lock→preflight exact scope на любую
   review/reserved audit ДО DML/objects. История/read error даёт только
   protected_fair_use_history/rollback/0changes. Удалить выполнение DELETE
   fair_use_reviews даже пустого. Нет cleanup GUC/depth исключения;
   account-close сохраняет retained metadata. Обычный smoke без истории
   очищается, concurrent source/preflight сериализуется с FK/root lock.

### Проверки T068 и общие ворота

8. **T068, законченная матрица этого среза.** Названные integration файлы,
   `apps/server/tests/unit/test_fair_use.py`,
   `apps/server/tests/contract/test_fair_use_ui.py` и
   `apps/server/tests/unit/test_billing_notifications.py`: create/appeal/оба
   решения, отдельный commit/new session, replay/concurrency/rollback/audit
   error/unknown commit/queue error и исходный recipient. Actual SQL app,
   maintenance spoof/COPY/UPSERT, reserved↔ordinary UPDATE laundering,
   DELETE/TRUNCATE/role/GUC/depth bypass, row_security off/wrong context.
   Operator empty/null/short/overlong/control/whitespace/Unicode/uppercase,
   missing attestation; audit unknown/missing key, wrong type/bool-as-number,
   null/enum/version/UUID/time/interfield mismatch по v1. Trusted setup только
   для старой истории и отрицательной формы guard под NOLOGIN writer;
   положительные пути идут настоящими runtime LOGIN, не schema owner.
   Regression actual F178 row-lock hold и forbidden UPDATE, lineage/stale
   preview; cleanup preflight/source race/0partial/обычная очистка; legacy
   migration/no backfill, bootstrap twice, empty downgrade/upgrade и отказ
   nonempty. Адаптировать только реально затронутые role fixtures/callers
   persist_review/direct FairUseReviewRecord и profile merge/cleanup tests;
   не возвращать app grants ради старого теста. Прежние SQL/платёжные/
   storage положительные наборы повторять лишь при затронутой зависимости.
9. **Общие ворота.** Независимое code review → $speckit-converge FU1–FU8 →
   профильный PG17/RLS/CLI/UI/sender/cleanup/F178 и Ruff/process/diff → owned
   `changes/unreleased/F140.yaml` → commit/push/PR с Refs#4926/#4922,
   governance-fast/macos-pr/pr-metadata точного SHA/текущей базы,
   common до/после merge и readback parent/tree. Временные synthetic БД/
   container/dump убрать finally, оставить версии/hashes/log/XML/results.

Зависимости: checklist19/0→Analyze→existing issues→T068 RED→T070 schema/roles
→CLI/shared transitions→cabinet/outbox/sender→cleanup→T068 actual-role матрица
→independent code review/converge/точные PR gates. После schema/roles renderer
unit cases и отдельный CLI parser test могут готовиться независимо;
fair_use.py/worker.py/migration/bootstrap менять последовательно из-за общих
стыков. Минимальный законченный результат — вся цепочка create/appeal/resolve,
не одна прямая запись очереди. Это не новый automatic abuse detector,
capability enforcement, urgent containment, реальный SLA/оператор/получатель
#7524, выпуск/сервер/Dev и не полные T068/T070. Новых зависимостей/служб нет.


## Детализация существующих T070/T068: account-close notices ACN1–ACN6 — 12.11.2026

Это последовательные шаги исходных T070/#4926 и T068/#4922 (US9/P2),
а не новые task IDs или самостоятельные issues. Все87 исходных task rows/marks
сохраняются. Lane high-risk-product; Legacy Impact: untouched. Независимый
checklist account-close-notices.md:14/0, report requirements PASS; далее
Analyze и существующие issues обязательны до первого теста/кода.
Цель: обязательное историческое письмо нового schedule/cancel от browser
источника через commit/outbox до штатного sender без изменения закрытия.

### Подготовка и причинный RED (T068, US9; источник US1)

1. В `apps/server/tests/integration/test_billing_notification_flow.py`
   добавить browser session+CSRF+explicit confirmation путь существующего
   `cabinet/web_routes/settings.py:_account_close_action`: schedule→commit,
   повтор→тот же request без письма, cancel→commit, новый schedule→новый
   request/event. Проверить из отдельного соединения три исходных snapshots
   вместо нынешних0, не отсутствие нового модуля/collection error. Только
   disposable PostgreSQL17, настоящие app/maintenance LOGIN/NOBYPASSRLS,
   неизменённые policies. RED сохранить прежде минимальной реализации.
   В том же файле проверить rollback до commit, read/enqueue error rollback
   перехода/recurring version/очереди; no permission/address допускает переход
   без письма и без будущего backfill. Отсутствие подтверждения/CSRF/session,
   foreign workspace и неOwner сохраняют отказ без перехода/очереди.

### Источник и историческое письмо (T070, US9)

2. В `apps/server/src/twobrain_rec_server/auth/account_closure.py`
   подключить producer после flush нового schedule и сохранённого cancel,
   сохранив прежний early return. Новый небольшой
   `apps/server/src/twobrain_rec_server/auth/account_closure_notifications.py`
   использует существующие ACCOUNT_CLOSE/outbox и исходного requester:
   active/unmerged identity, personal workspace с исходным Owner marker,
   active Owner membership, active verified nonempty email; выбор адреса —
   минимальный действующий, без хранения в очереди. Mandatory preference bypass,
   отсутствие→no enqueue, ошибка→rollback у caller, без внутреннего commit.
   Event `account.close:<request.id.hex>:scheduled|canceled`, уникальность по
   прежнему delivery key, no replay/backfill/переприсвоение получателя.
3. В `apps/server/src/twobrain_rec_server/billing/notifications.py` и
   `apps/server/tests/unit/test_billing_notifications.py` выполнить строгие
   snapshot builder/renderer по §ACN договора: phase scheduled|canceled,
   canonical UUID hex, aware UTC ISO8601 исходных requested/finalize/canceled
   включая секунды/доли; canceled field только canceled. Неизвестные поля
   отбрасываются; неполный/некорректный снимок пустой для suppression.
   Исторический русский текст с секундами/МСК, одно `/settings/account` на
   configured public origin, без UUID/token/PII/financial/meeting content.
   Поздний scheduled после cancel не обещает текущего закрытия/списаний/очистки.
   Адаптировать только затронутый generic allowlisted-copy integration case,
   не ослаблять отсутствие доказуемого snapshot ради старого ожидания.

### Сохранённый claim и настоящий sender (T070, US9)

4. В новом `auth/account_closure_notifications.py` source/recipient gate
   сверяет event/request/recipient/workspace и весь allowlisted snapshot с
   исходной записью, policy `account-close-v1`, интервал «ровно семь суток»,
   requested<=canceled<finalize. До финализации разрешены scheduled/canceled/
   blocked; canceled notice требует state=canceled. finalized_at,
   content_workspace_ids, finalization_started_at или closed/merged запрещают
   новую отправку. Source locks shared NOWAIT: request→workspace→identity→
   membership→verified identities, затем delivery FOR UPDATE в worker.
   Не следовать merge/new owner/payer; grants/RLS/schema не менять.
5. В `apps/server/src/twobrain_rec_server/workflows/worker.py` включить
   ACCOUNT_CLOSE в bounded notice selector/claim с missing email обработкой;
   strict malformed retry metadata и future not-before gate под lock.
   После source locks сравнить весь poll snapshot с сохранённым delivery;
   mutation→следующий проход без старого body. Terminal отсутствие→suppressed;
   pretransport read/lock error и known retryable Postal failure→сохраняемый
   retry «не раньше60секунд, максимум пять суммарных попыток»; исчерпание→failed.
   Сохранить claim/attempt=failed/postal_outcome_unknown до HTTP, release locks,
   ошибка сохранения→0HTTP, unknown/crash→без автоматического повтора.
   Другие семейства sender сохраняют поведение.

### Независимая приёмка цепочки и общие ворота (T068, US9)

6. В `apps/server/tests/integration/test_billing_notification_flow.py`
   prove actual browser source→separate committed read→ordinary sender с
   test-local transport stub. Mandatory при optional email=false; точные
   snapshots/text, historical scheduled после cancel; old incomplete/tampered/
   foreign/event/recipient/workspace/policy/dates/phase mismatches→0transport.
   Утрата Owner marker/membership/active identity/verified address, merged,
   closed и finalization boundary→terminal suppression. Wrong worker context
   и cross-tenant read не расширяют доступ; другой tenant неизменен.
7. В том же integration файле independent connections проверяют источник
   NOWAIT при hold request/workspace/identity/membership/email и обратный F178/
   closure порядок, rollback/no partial, concurrent senders и poll→claim
   mutation. В callback отдельное соединение видит saved claim+attempt ДО
   HTTP и может взять source/delivery locks. Restart/known failure/due boundary/
   future delay/max5/unknown/crash/claim commit failure покрывают ACN5 без сна
   или реального транспорта. Неверные retry JSON types/ranges не исполняются.
8. Профильные регрессии:
   `apps/server/tests/unit/test_account_closure.py`,
   `apps/server/tests/unit/test_account_close_fanout.py`,
   `apps/server/tests/integration/test_account_lifecycle.py`,
   `apps/server/tests/unit/test_billing_notifications.py`, затронутые cases
   `apps/server/tests/integration/test_account_merge.py` и соседних sender
   families в `test_billing_notification_flow.py`. Запускать выбранные случаи
   штатным `apps/server/scripts/run_local_postgres_tests.sh --focused`;
   не суммировать отдельные прогоны в фиктивную общую проверку.
9. Независимое code review→$speckit-converge ACN1–ACN6→профильный Ruff/
   process/diff→собственный `changes/unreleased/F140.yaml`→commit/push/PR с
   Refs#4926/#4922. Exact head/currentbase, governance-fast/macos-pr/pr-metadata,
   `scripts/validate-pr-checks.py`, открытые замечания, штатный merge и проверка
   результата/parent/tree. Временные синтетические БД/containers убрать штатно;
   hashes/log/results оставить во внешнем каталоге. Dev/release-full/deploy и
   настоящая получательская #7524 отдельно, исходные T068/T070 остаются `[ ]`.

Зависимости: requirements14/0→tasks→Analyze→existing issue canon/sync→RED1
→producer2→copy3→source gate4→sender5→acceptance6/7→regression8→review/converge9.
Реализация общих auth/worker стыков последовательна; независимые renderer unit
cases можно подготовить после RED отдельно от producer при непересекающихся
файлах. Новых агентов-исполнителей/зависимостей/таблиц/служб не требуется.
Минимальный законченный результат — обе исторические фазы с настоящим source
и claim, а не ручная постановка готового delivery. Полный T068/T070, другие
состояния чеков/уведомления, эксплуатационный FR107 и исходные launch gates
этой детализацией не принимаются и не отменяются.

## Детализация существующих T068/T070: правдивый результат продления MRC — 12.11.2026

Продолжение US9/P2 с потребителями US4/US5/P1, FR-110/MRC1–MRC6.
Это подготовка достоверного состояния перед отдельным источником письма
method_required, не новое уведомление. Lane **high-risk-product**; Legacy
Impact: untouched. Исходные87 task rows/marks, включая открытые T068/#4922
и T070/#4926, сохраняются. Независимый requirements checklist
`checklists/method-required-notices.md`:14/0, основания каждого пункта в
`review-method-required-notices-requirements.md`; этот PASS не принимает код.
Штатный setup-tasks использует прежнюю структуру фаз и исторические task IDs.

### Подготовка и причинный RED — T068, US9; US4/US5

1. После `$speckit-analyze` без CRITICAL/HIGH и sync существующих #4922/#4926
   добавить в `apps/server/tests/integration/test_billing_renewal_planner_postgres.py`
   причинные случаи настоящего planner→commit→новая AsyncSession→charge:
   ValueError до POST из недоступного синтетического ключа при существующем
   verified method; ValueError после одного MockTransport POST из неверного
   строкового provider ID. Следующая session должна прочитать operation/invoice
   manual_resolution и subscription pending. Старый handler должен падать
   именно на ожидании pending, не collection/fixture ошибке. Повтор charge
   не меняет число POST:0 до отправки/1 после неё. Сохранять исходные деньги,
   сроки, grants, method, authority/version/key/snapshot/audit; допускаются
   только прежние state/status/audit перехода и renewal_resolution.
   Только disposable PostgreSQL17, настоящие LOGIN/NOBYPASSRLS роли и прежний
   maintenance context; без .env/рабочей DSN/реальной сети, платежей или почты.

### Общий источник и обработчик — T070, US9; US5

2. В `apps/server/src/twobrain_rec_server/billing/renewal_charge.py` добавить
   один query builder периода и один предикат. Ограничения модели:
   «exact workspace, kind=renewal, JSON `paid_through_at`, равный
   UTC ISO8601 текущего subscription.paid_through по существующему формату»;
   «Без paid_through нет такой выборки». `canceled|succeeded` завершены;
   `scheduled` без provider_id ещё не отправлена; `scheduled` с ID и остальные
   неразрешённые состояния, включая manual_resolution, требуют проверки.
   Отсутствие ID само по себе не доказывает отсутствие POST. Planner под
   прежним workspace lock после Owner/initial-checkout читает FOR UPDATE до
   catalog/method/receipt и при незавершённости сохраняет pending без новой
   операции. Ошибку SQL не заменять пустой историей. Сохранить три окна F278,
   immutable successors, дедупликацию и guards. Общий ValueError/TypeError
   оставляет operation/invoice manual_resolution, subscription pending и
   прежний audit reason; saved_method_missing→attempt_failed не дублировать.

### Обе страницы и потребители — T070, US9; US4/US5

3. В `apps/server/src/twobrain_rec_server/cabinet/web_routes/billing.py`
   читать историю периода один раз на страницу, переиспользовать её для
   projection/notice/resume. Сохранить tuple(label, nominal_first) и строковый
   wrapper. Общие query/predicate использовать также в storage preview/resume;
   POST resume заново проверяет историю под workspace lock. В шаблонах
   `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/billing_overview_content.html`
   и `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/billing_subscription_content.html`
   явный unresolved renewal имеет приоритет над blockers/recurring-off и
   верхним result=method_required. Текст/ссылка/действие строго по MRC договору
   `contracts/notifications-support.md`: проверка прежнего результата,
   `/billing/history#billing-help`, «Проверить результат»; при recurring-off
   отдельно запрет будущих автоматических попыток. Скрыть competing primary
   actions новой/досрочной оплаты/resume до разрешения; сохранить cancel,
   историю и помощь. Новых сущностей/миграций/зависимостей/egress/писем нет.

### Причинный GREEN и приёмка — T068, US9; US4/US5

4. В `apps/server/tests/unit/test_renewal_charge.py` отдельно TypeError и
   изменённые ожидания pending; в `apps/server/tests/unit/test_billing_purchases.py`
   общий classifier/query, tuple2/string, storage/resume, SQL failure, без
   paid_through и точные границы workspace/period/kind, finished/unsent/
   scheduled+ID. В PostgreSQL файле шага1 настоящие сохранённые
   manual_resolution/unknown/sent+старый method_required комбинировать с
   missing method, price/catalog/receipt blockers; новое окно не создаёт
   invoice/operation/POST, rollback не сохраняет pending. Контроли другой
   период/canceled/succeeded/unsent и прежние три окна не теряют поведения.
5. В том же PostgreSQL файле вызвать оба настоящих page handlers с сохранённым
   post-POST manual_resolution без ID, старым method_required, каждым blocker,
   recurring_allowed true/false и result=method_required. Не подменять
   projection/query/notice. Проверить статус/баннер, отсутствие ложного совета
   и nominal-first/новой quote/оплаты, наличие истории/помощи/cancel. В
   `apps/server/tests/contract/test_billing_ui.py` и
   `apps/server/tests/contract/test_billing_accessibility.py` закрепить только
   необходимые template/status semantics. Прогоны штатным
   `apps/server/scripts/run_local_postgres_tests.sh --focused`; сохранить
   exact pre/post hashes, команды/exit/logs и штатную очистку temporary DB.
6. Профильная регрессия MRC quickstart→независимое code review→
   `$speckit-converge` MRC1–MRC6→Ruff/diff→собственный
   `changes/unreleased/F140.yaml`→проверенный commit/push/PR с Refs#4922/#4926.
   До merge точные head/current base, governance-fast/macos-pr/pr-metadata,
   `scripts/validate-pr-checks.py`, открытые замечания и проверка результата.
   Единственный свободный GRAF Dev, обе темы, клавиатура/VoiceOver,
   200%/360px — отдельная ручная приёмка; Jinja/handler assertions её не заменяют.
   Выпуск/развёртывание и настоящее получение #7524 отдельно. Исходные
   T068/T070 остаются `[ ]`; SSN retention и прочие семьи не приняты.

Зависимости: requirements14/0→tasks→Analyze→existing issue sync→RED1→
общий источник2→потребители3→GREEN4/5→review/converge/gates6.
Минимальный результат включает обе страницы и все общие потребители, а не
одну заменённую строку. Независимые unit/contract случаи в разных файлах
возможны после RED; общий renewal/routes и PG файл выполняются последовательно.
Это возможность разделения работ, не запуск дополнительных агентов.
