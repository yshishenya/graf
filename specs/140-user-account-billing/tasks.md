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

- [ ] T017 [P] [US1] Add account-center, personal-workspace bootstrap, authorization, and macOS browser-handoff contract tests for owner, admin, member, unverified identity, workspace switching, expired/offline/browser-unavailable states, and one-time handoff in `apps/server/tests/contract/test_account_routes.py` and `apps/macos/Shared/Tests/DesktopCabinetBillingHandoffTests.swift`.
- [ ] T018 [P] [US1] Add trial eligibility, one-per-`UserIdentity`, explicit-consent, expiry-to-Free, and account-close integration tests in `apps/server/tests/integration/test_account_lifecycle.py`.

### Implementation for User Story 1

- [X] T019 [US1] Implement idempotent personal-workspace bootstrap plus account-center view models, owner/member capability projection, and safe navigation using `apps/server/src/twobrain_rec_server/auth/workspace_onboarding.py`, `apps/server/src/twobrain_rec_server/cabinet/view_models.py`, and `apps/server/src/twobrain_rec_server/cabinet/web_routes/account.py`.
- [ ] T020 [P] [US1] Add profile, security, notifications, language/theme, active-session/device screens, recovery-safe login-method unlink guard, and the admin usage label `Использование и лимиты` by extending `apps/server/src/twobrain_rec_server/cabinet/web_routes/settings.py`, `apps/server/src/twobrain_rec_server/auth/provider_links.py`, `apps/server/src/twobrain_rec_server/admin/view_models.py`, `apps/server/src/twobrain_rec_server/admin/templates/admin/balance.html`, and `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/settings_account_content.html`.
- [X] T021 [US1] Implement explicit trial activation, verification gate, one-time identity eligibility, and expiry projection in `apps/server/src/twobrain_rec_server/billing/trial.py` and `apps/server/src/twobrain_rec_server/cabinet/web_routes/billing.py`.
- [X] T022 [US1] Implement account-close scheduling, seven-day cancellation, immediate access/quota revocation at accepted deletion, and Temporal finalization integration by extending `apps/server/src/twobrain_rec_server/deletion/service.py`, `apps/server/src/twobrain_rec_server/db/models/deletion.py`, and `apps/server/src/twobrain_rec_server/workflows/maintenance_worker.py`.
- [ ] T023 [US1] Add Russian-first account templates, keyboard/focus states, no-JS navigation fallback, clean-room visual tokens, and read-only browser handoff/expired/offline states in `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/account_content.html`, `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/components/account_navigation.html`, `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.css`, `apps/macos/RecApp/Sources/Cabinet/DesktopCabinetRoutePolicy.swift`, and `apps/macos/RecApp/Sources/Cabinet/DesktopCabinetWorkspaceView.swift`.

**Checkpoint**: Account center and trial are independently usable; account close remains distinct from canceling paid renewal and never disables local Record/Stop.

## Phase 4: User Story 2 — Понять тариф и использование без сюрпризов (Priority: P1)

**Goal**: Show exact processing/storage state and enforce Free seconds plus finite playback storage while paid core capabilities remain commercially unlimited.

**Independent test**: Fixtures can exhaust Free’s exact 18,000-second window, fill playback storage, process without saving audio, add/remove reservation bytes, and verify WAV/internal source bytes never count toward customer quota.

### Tests for User Story 2

- [X] T024 [P] [US2] Add exact-second admission, Moscow-month reservation binding across midnight, 80%/100% Free-threshold copy, overrun rejection, calendar reset, reservation release, partial-success, and no-rollover tests in `apps/server/tests/unit/test_free_usage_ledger.py`.
- [ ] T025 [P] [US2] Add playback-only storage projection, 80/95/100% thresholds, exact decimal capacities, reservation/object-stat mismatch and supersede handling, add-on capacity, deletion release, normalized writer byte-size, WAV retention/COGS accounting, retention-gate reopening, and source-lifecycle tests in `apps/server/tests/integration/test_storage_quota.py` and `apps/server/tests/contract/test_storage_lifecycle.py`.
- [X] T026 [P] [US2] Add processing-without-save and paid-unlimited capability contract tests in `apps/server/tests/contract/test_entitlements_and_ingest_limits.py`.

### Implementation for User Story 2

- [X] T027 [US2] Implement Free usage windows, exact-second reservations/commit ledger, and entitlement checks in `apps/server/src/twobrain_rec_server/billing/usage.py`.
- [X] T028 [US2] Implement storage capacity projection and reservation from active normalized `TrackArtifact.byte_length` for `meeting-review.m4a`, with no duplicate object inventory, in `apps/server/src/twobrain_rec_server/billing/storage.py`.
- [ ] T029 [US2] Integrate playback quota admission, `Обработать без сохранения аудио`, transient 15-minute purge, and 24-hour hard lifetime into `apps/server/src/twobrain_rec_server/ingest/store.py`, `apps/server/src/twobrain_rec_server/processing/store.py`, and `apps/server/src/twobrain_rec_server/workflows/processing_workflow.py`.
- [ ] T030 [US2] Extend current/legacy source lifecycle and deletion purge so WAV is recoverable only under approved policy, exact normalized writer bytes are recorded, COGS/backup retention evidence is available, and every source immediately enters mandatory purge after accepted deletion in `apps/server/src/twobrain_rec_server/db/models/lifecycle.py`, `apps/server/src/twobrain_rec_server/deletion/retention.py`, `apps/server/src/twobrain_rec_server/deletion/report.py`, and `apps/server/src/twobrain_rec_server/normalization/service.py`.
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
- [X] T042 [US4] Implement one co-termed storage add-on, capacity transitions, price snapshots, and entitlement projection in `apps/server/src/twobrain_rec_server/billing/storage_addons.py`.
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
- [X] T048 [US5] Add renewal reminder, failure-to-Free, unknown, late-success and manual-resume notifications in `apps/server/src/twobrain_rec_server/billing/notifications.py` and `apps/server/src/twobrain_rec_server/support/outbox.py`.
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
- [X] T062 [P] [US8] Add monthly/yearly maturity, 14-day hold, 180-day rolling cap, contiguous credit, cancel-scheduled, and authoritative-observed-refund reversal tests in `apps/server/tests/integration/test_referral_rewards.py`.

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
- [X] T068 [P] [US9] Add end-to-end event coverage for trial reminders, payment success/failure, storage thresholds, receipt state, referral credit, unknown and late outcomes in `apps/server/tests/integration/test_billing_notification_flow.py`.

### Implementation for User Story 9

- [X] T069 [US9] Implement billing notification event taxonomy, idempotent outbox records, Russian-first templates, and delivery state in `apps/server/src/twobrain_rec_server/billing/notifications.py`, `apps/server/src/twobrain_rec_server/billing/events.py`, and the existing Postal delivery worker.
- [X] T070 [US9] Implement fair-use classification/review-deadline/appeal state with bounded reason and wire trial, payment, renewal, storage, receipt, referral, fair-use and account-close events to notifications without creating a refund correspondence event in `apps/server/src/twobrain_rec_server/billing/fair_use.py`, `apps/server/src/twobrain_rec_server/billing/events.py`, and `apps/server/src/twobrain_rec_server/workflows/maintenance_worker.py`.
- [X] T071 [US9] Add notification preferences, legal/financial override rules, safe deep links and accessible live-status rendering in `apps/server/src/twobrain_rec_server/cabinet/web_routes/settings.py`, `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/components/notifications.html`, and `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js`.

**Checkpoint**: Users receive useful next actions without GRAF receiving or storing support-email content or raw financial identifiers.

## Phase 12: User Story 10 — Оперировать биллинг и доказать готовность к запуску (Priority: P1)

**Goal**: Reconcile provider truth, daily payment/refund registries, storage and notifications, and prove controlled test-shop and real-shop launch gates.

**Independent test**: Operators can run read-only reconciliation and registry checks, inspect metadata-only gaps and metrics, stop new money mutations, and produce launch evidence without a customer-facing refund tool.

### Tests for User Story 10

- [X] T072 [P] [US10] Add reconciliation completeness, registry hash/part identity, configured-empty-report, replacement/missing-file, and gap-owner tests in `apps/server/tests/integration/test_billing_registry.py`.
- [X] T073 [P] [US10] Add monitoring, durable incident lifecycle/owner/deadline, emergency-stop, RLS inventory, redaction, accessibility, four-eyes gate metadata, and launch-canary assertions in `apps/server/tests/contract/test_billing_launch_gates.py`.
- [ ] T074 [P] [US10] Add test-shop E2E coverage for initial/saved payment, recurring decline, timeout-late success, zero binding, provider floor, merchant-cabinet refund observation, receipt observation, and zero product refund mutations in `apps/server/tests/e2e/test_billing_test_shop.py`.

### Implementation for User Story 10

- [X] T075 [US10] Implement provider polling, observed refund/receipt/method reconciliation, separate payments/refunds registry import, completeness hashes and metadata-only gap ownership in `apps/server/src/twobrain_rec_server/billing/reconciliation.py` and `apps/server/src/twobrain_rec_server/billing/registry.py`.
- [ ] T076 [US10] Implement Temporal reconciliation, stuck-operation, storage projection, add-on/time-credit and notification maintenance workflows in `apps/server/src/twobrain_rec_server/workflows/billing_reconciliation_workflow.py` and `apps/server/src/twobrain_rec_server/workflows/maintenance_worker.py`.
- [X] T077 [US10] Add operational metrics, dashboards, emergency stop and read-only launch diagnostics through existing observability patterns in `apps/server/src/twobrain_rec_server/billing/monitoring.py`, `apps/server/src/twobrain_rec_server/readiness/checks.py`, and `apps/server/src/twobrain_rec_server/admin/metrics.py`.
- [X] T078 [US10] Add test-shop and controlled real-shop canary runbooks, environment separation, provider capability evidence, legal/finance sign-off records, and rollback/stop procedure in `specs/140-user-account-billing/quickstart.md` and `docs/runbooks/billing-launch.md`.

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
- Implementation changes require explicit user approval before commit, push, merge or production release.
