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

## Dependencies

- T003 precedes T004-T005 for the preview path.
- T006 precedes T007 for provisioning.
- T009 follows T003-T008; T010 follows T009; T011 follows all implementation and validation.
- T012-T014 follow the current audit; T015 follows T012-T014.
- T078-T080, T083-T085 and T087 from Feature 140 remain external gates and are
  not closed by this slice.
