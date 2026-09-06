# Tasks: Billing acquiring and promo closeout

**Input**: Design documents from `/specs/199-billing-acquiring-promo/`.

**Risk lane**: high-risk active Spec Kit slice. Production provider mutation is
out of scope until Feature 140 launch evidence is complete.

## Phase 1: Audit and contracts

- [X] T001 [US1] Reconcile Feature 140 checkout/promo implementation against its spec, contracts and open-gaps evidence in `specs/140-user-account-billing/`.
- [X] T002 [US1] Record the preview, provisioning and no-production-enable boundaries in `specs/199-billing-acquiring-promo/`.

## Phase 2: User Story 1 — Checkout preview

- [X] T003 [P] [US1] Add focused preview/render/error assertions in `apps/server/tests/contract/test_billing_ui.py` and `apps/server/tests/integration/test_promo_checkout.py`.
- [X] T004 [US1] Implement server-side promo preview context and POST/Redirect/GET route in `apps/server/src/twobrain_rec_server/cabinet/web_routes/billing.py`.
- [X] T005 [US1] Render list, discount, payable and next-period amounts with accessible recoverable states in `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/billing_checkout_content.html`.

## Phase 3: User Story 2 — Operator campaign provisioning

- [X] T006 [P] [US2] Add validation/output tests for hidden/stdin code handling, dry-run metadata and invalid campaign parameters in `apps/server/tests/unit/test_promo_campaign_cli.py`.
- [X] T007 [US2] Implement metadata-only create/disable provisioning through the existing maintenance/RLS boundary in `apps/server/scripts/manage_promo_campaign.py`.
- [X] T008 [US2] Document the operator command and raw-code handling in `apps/server/scripts/README.md` and `specs/199-billing-acquiring-promo/quickstart.md`.

## Phase 4: Validation and closeout

- [X] T009 [US1] Run the Feature 199 quickstart, focused tests and `git diff --check`; update task evidence only after passing.
- [X] T010 [US2] Run `infra/scripts/ci-local.sh --fast` and record exact result in the feature evidence.
- [X] T011 [US3] Re-run cross-artifact analysis, update `CHANGELOG.md`, and record that Feature 140 canary/approval gates remain open.

## Phase 5: Remove obsolete runtime approval registry

- [X] T012 [US3] Remove active launch-gate calls, model and readiness helper while preserving provider/shop, emergency-stop, ledger, receipt, webhook and reconciliation safeguards.
- [X] T013 [US3] Add migration `0079_remove_billing_launch_gates` and update active RLS/test contracts without rewriting historical migration `0072`.
- [X] T014 [US3] Update active billing copy, runbook, Spec Kit artifacts and changelog so the former registry is not described as a checkout prerequisite.
- [X] T015 [US3] Run focused billing/RLS/migration checks and record that full CI and provider payment were intentionally not run.
- [X] T016 [US3] Fix production checkout promo reservation RLS by moving campaign counter transitions to a database trigger in `apps/server/src/twobrain_rec_server/db/migrations/versions/0080_promotion_reservation_counter_trigger.py` and removing duplicate ORM counter writes.
- [X] T017 [US3] Re-run focused billing/migration checks and verify the test-shop checkout path without repeating an unresolved payment operation.
- [X] T018 [US3] Make production deploy, migration verification, smoke and the production migration entrypoint fail closed outside a merged `master` release with one shared lock.

## Phase 6: Recover checkout before provider reference

- [X] T019 [US4] Add RED tests for provider reject before `provider_id`, same-key continuation, expired-key blocking, metadata-safe diagnostics and truthful status refresh in `apps/server/tests/unit/test_initial_checkout_recovery.py` and `apps/server/tests/contract/test_billing_ui.py`.
- [X] T020 [US4] Reuse one immutable hosted-payment helper for initial create and explicit continuation in `apps/server/src/twobrain_rec_server/cabinet/web_routes/billing.py`.
- [X] T021 [US4] Render the real local state and only the valid continue/refresh action in `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/billing_operation_status_content.html` and `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/billing_overview_content.html`.
- [X] T022 [US4] Run the focused billing/RLS quickstart, fast lane and release-candidate full CI; update `CHANGELOG.md` with exact evidence.
- [X] T023 [US4] Merge through PR, deploy only clean synchronized `master`, then repeat one payment against the test shop without enabling the production shop.

Validation evidence (2026-08-25, candidate based on `origin/master` `104bd2dd`):
focused billing `47 passed`; focused infra `89 passed`; FastAPI/PostgreSQL
continue route `1 passed`; fast CI `1241 passed`; full CI `766` Swift tests,
`3438 passed, 1 skipped` server tests and `52 passed, 1 skipped` strict RLS
tests, with lint, compile, Compose and deployment evidence scan PASS.

Test-shop canary diagnosis (2026-08-26): YooKassa rejected the initial request
before creating a payment because the internal checkout key exceeded the
provider's 64-character `Idempotence-Key` limit. The shared adapter now keeps
valid short keys and deterministically hashes longer keys; focused billing
`60 passed`, fast CI `1241 passed`. T023 remains open until the fix is merged,
deployed and one test-shop payment reaches confirmed entitlement state.

Test-shop payment evidence (2026-08-26): invoice
`INV-41CF58F0C2114670948F` reached provider payment/receipt `succeeded`, local
invoice/operation/entitlement/subscription `succeeded`, recurring enabled and
promo redeemed. A remaining duplicate-reconciliation defect left only the local
receipt projection at `pending`; the shared entitlement path now merges the
later receipt state monotonically and preserves one receipt notification.
Focused Feature 199 plus receipt lifecycle suite: `70 passed`; fast CI:
`1241 passed`, lint/compile PASS. T023 remains open until this follow-up is
merged, deployed and the same payment is reconciled.

Post-deploy UI diagnosis (2026-08-26): database reconciliation correctly moved
the existing invoice receipt to `succeeded`, but history/detail routes parsed
the provider registration value as the presentation enum and rendered it as
unknown. Both routes now reuse `receipt_state_for_registration`; a succeeded
receipt without a safe URL says «Чек зарегистрирован», and a URL is exposed only
for that state. Focused UI and receipt lifecycle tests: `29 passed`; full focused
Feature 199 and receipt suite: `74 passed`. At that checkpoint T023 remained
open until the final UI fix was merged, deployed and visible in the browser.

Final closeout (2026-08-26): PRs #5853 and #5854 merged; exact release SHA
`7eb7cf3d` passed full CI (`766` Swift, `3444 passed / 1 skipped` server,
performance PASS, `52 passed / 1 skipped` strict RLS), backup/restore,
migration verification, production smoke and health. Runtime remains the
production application with YooKassa `test`, shop suffix `6758`, checkout
enabled and emergency stop disabled. Browser E2E reused invoice
`INV-41CF58F0C2114670948F` without creating another payment and confirmed the
active monthly subscription, 99% redemption, paid status and «Чек
зарегистрирован» in both history and detail. T023 is complete.

## Dependencies

- T003 precedes T004-T005 for the preview path.
- T006 precedes T007 for provisioning.
- T009 follows T003-T008; T010 follows T009; T011 follows all implementation and validation.
- T012-T014 follow the current audit; T015 follows T012-T014; T016 follows
  T015; T017 follows T016; T018 follows T017.
- T019 precedes T020-T021; T022 follows T019-T021; T023 follows T022 and explicit
  release approval already recorded for this test-shop canary.
- T078-T080, T083-T085 and T087 from Feature 140 remain external gates and are
  not closed by this slice.
