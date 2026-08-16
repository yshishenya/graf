# Tasks: Продуктовый раздел настроек

## Phase 1: Setup and baseline

- [X] T001 Review current settings routes in `apps/server/src/twobrain_rec_server/cabinet/web_routes/settings.py`, category metadata in `cabinet/view_models.py`, templates in `cabinet/templates/cabinet/pages/` and CSS in `cabinet/static/cabinet/cabinet.css` against the Open Design reference.
- [X] T002 [P] Add/adjust focused source contract assertions for seven categories, scope labels, active `aria-current` and trust-boundary copy in `apps/server/tests/` or the existing settings contract test file.

## Phase 2: User Story 1 — overview and navigation

- [X] T003 [US1] Align settings overview card geometry, scope badges, grouped navigation and selected state with the existing GRAF design system and Open Design reference in `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.css` and settings templates.
- [X] T004 [US1] Preserve the existing category source and server routes in `apps/server/src/twobrain_rec_server/cabinet/view_models.py`, `cabinet/rendering.py` and `settings_navigation.html`; change metadata only when parity or truthfulness requires it.

## Phase 3: User Story 2 — server-backed sections

- [X] T005 [US2] Align recording, summaries, workspace, account, notifications and billing section presentation without introducing localStorage state, duplicate forms or new persistence in `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/`.
- [X] T006 [US2] Verify account, workspace, notification, calendar and billing result/unavailable states remain truthful and preserve CSRF/tenant/owner/re-auth boundaries in `apps/server/src/twobrain_rec_server/cabinet/web_routes/settings.py` and the existing focused tests under `apps/server/tests/`.

## Phase 4: User Story 3 — responsive and accessible UX

- [X] T007 [US3] Ensure settings rail, overview cards, lists, forms, focus states and forced-colors/reduced-motion behavior pass 390px and keyboard requirements in `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.css`.
- [X] T008 [US3] Add or update browser/source regression checks for desktop and mobile settings surfaces in `apps/server/tests/` and the repository browser harness.

## Phase 5: Validation and closeout

- [X] T009 [P] Update `CHANGELOG.md` with the product settings surface change and validation lane.
- [X] T010 Run the quickstart focused checks and `infra/scripts/ci-local.sh --fast`; record evidence in `specs/151-settings-product-surface/quickstart.md` without committing implementation until user approval.

## Dependencies

- T001 → T002 → T003/T004 → T005/T006 → T007/T008 → T009 → T010.
- T002 and T003 are parallel only after T001 because they touch disjoint test/CSS-template scopes.

## Implementation Strategy

1. MVP: complete US1 overview/navigation with existing category routes and accessibility state.
2. Preserve and visually align US2 server-backed pages without changing their mutation contracts.
3. Close US3 with responsive/browser evidence, then run the repository fast gate.

## Phase 6: Audit remediation

- [X] T011 [US3] Replace the full-height mobile settings rail with a compact, keyboard-reachable horizontal rail in `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.css` while keeping document overflow bounded.
- [X] T012 [P] [US2] Fix notification label grouping, account-close confirmation description and conditional promo removal in `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/components/notifications.html`, `cabinet/templates/cabinet/pages/settings_account_content.html` and `cabinet/templates/cabinet/pages/billing_discounts_content.html`.
- [X] T013 [P] [US1] Keep referrals in the account IA context and redirect legacy `/account/billing` and `/account/settings` links to canonical surfaces in `cabinet/web_routes/referrals.py`, `cabinet/web_routes/billing.py` and `cabinet/web_routes/settings.py`.
- [X] T014 [US3] Add focused contract coverage for mobile navigation, account-close semantics, conditional promo actions and legacy aliases under `apps/server/tests/`.
- [X] T015 [US3] Run the focused settings/billing suites and `infra/scripts/ci-local.sh --fast`; record the evidence in `specs/151-settings-product-surface/quickstart.md`.
