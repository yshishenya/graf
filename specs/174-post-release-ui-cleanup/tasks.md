# Tasks: Пострелизная очистка интерфейса

**Input**: Design documents from `/specs/174-post-release-ui-cleanup/`

**Risk lane**: `significant-feature`; shared responsive cabinet, settings IA and native/web accessibility composition. Focused checks during implementation, one fast repository gate at closeout, no deploy.

## Phase 1: Foundational evidence

- [X] T001 Record the reproduced 720px embedded profile `0×0` failure, exact cascade cause and pre-change focused results in `specs/174-post-release-ui-cleanup/quickstart.md`

---

## Phase 2: User Story 1 — Доступный профиль при любом размере (P1)

**Goal**: One responsive state owner keeps compact profile, controls and toggle geometry usable at every supported width.

**Independent Test**: Render web/embedded shells at 640/720/980/981/1120/1121/1280, require visible 40×40 compact profile/control boxes, 64/176 rail widths, ≤1px axis tolerance, no overflow and same-coordinate double toggle.

- [X] T002 [US1] Replace brittle sidebar declaration expectations with exact regression guards for the narrow profile visibility defect and preserved semantic boundaries in `apps/server/tests/contract/test_cabinet_static_assets_contract.py` and `apps/server/tests/unit/test_cabinet_web_shell.py`
- [X] T003 [US1] Consolidate compact/expanded state ownership, remove conflicting breakpoint declarations and delete the unused tooltip attribute/update in `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.css`, `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/components/sections.html`, and `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js`
- [X] T004 [US1] Run focused sidebar/rail/tooltip pytest and Node checks and record exact results in `specs/174-post-release-ui-cleanup/quickstart.md`

---

## Phase 3: User Story 2 — Настройки с одной навигацией и одной колонкой (P1)

**Goal**: Remove the unsupported inner settings navigation without changing routes, forms or fragment boundaries.

**Independent Test**: Overview, form, calendar fragment and billing render one outer navigation landmark, one active settings link and one content column in web and embedded modes.

- [X] T005 [US2] Replace synthetic fallback and legacy selector assertions with primary-sidebar, single-column and fragment-boundary contracts in `apps/server/tests/contract/test_settings_ui_contract.py`, `apps/server/tests/unit/test_cabinet_web_shell.py`, and `apps/server/tests/integration/test_settings_ia_flow.py`
- [X] T006 [US2] Remove inner navigation imports/calls, delete the unused macro and obsolete selectors, and mark Feature 173 fallback superseded in `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/`, `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/fragments/`, `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/components/settings_navigation.html`, `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.css`, and `specs/173-settings-single-column/`
- [X] T007 [US2] Run focused settings/template tests plus the isolated PostgreSQL settings matrix and record exact results in `specs/174-post-release-ui-cleanup/quickstart.md`

---

## Phase 4: User Story 3 — Стабильный native inspector (P2)

**Goal**: Keep the accepted top toggle and inspector geometry while removing unused layout and duplicate tests.

**Independent Test**: Focused Swift tests/build and GRAF Dev show unchanged 52/308px widths, top-trailing 44px toggle, scroll behavior, accessibility and same-coordinate double toggle.

- [X] T008 [US3] Consolidate duplicate inspector source assertions into one semantic layout contract and one accessibility contract in `apps/macos/Shared/Tests/AppControlAccessibilityTests.swift` and `apps/macos/Shared/Tests/DesktopMeetingShellWebViewBoundaryTests.swift`
- [X] T009 [US3] Remove the unused inspector `GeometryReader` while preserving the existing VStack, frame, background and header hit region in `apps/macos/RecApp/Sources/Cabinet/DesktopMeetingShellView.swift`
- [X] T010 [US3] Run focused Swift tests and build and record exact results in `specs/174-post-release-ui-cleanup/quickstart.md`

---

## Phase 5: Cross-surface closeout

- [X] T011 Complete the in-app Browser computed matrix and GRAF Dev visual/accessibility interaction matrix from `specs/174-post-release-ui-cleanup/quickstart.md`
- [X] T012 Perform correctness, frontend UX/accessibility, clean-room and Ponytail reviews; resolve all actionable findings and record them in `specs/174-post-release-ui-cleanup/analysis.md`
- [ ] T013 Update `[Unreleased]` in `CHANGELOG.md`, run `git diff --check` and `infra/scripts/ci-local.sh --fast` once, reconcile tasks/issues and record closeout evidence in `specs/174-post-release-ui-cleanup/quickstart.md`

## Dependencies

- T001 precedes every implementation task.
- T002 precedes T003; T003 precedes T004.
- T005 precedes T006; T006 precedes T007.
- T008 precedes T009; T009 precedes T010.
- US1 and US3 touch disjoint source files and may proceed in parallel after T001.
- US2 follows US1 because both edit `cabinet.css` and cabinet shell tests.
- T011 follows T004, T007 and T010. T012 follows T011. T013 is last.

### T006 exact write set

- `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/fragments/calendar_settings.html`
- `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/fragments/provider_link_settings.html`
- `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/billing_checkout_content.html`
- `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/billing_discounts_content.html`
- `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/billing_history_content.html`
- `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/billing_invoice_content.html`
- `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/billing_operation_status_content.html`
- `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/billing_overview_content.html`
- `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/billing_payment_method_content.html`
- `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/billing_plans_content.html`
- `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/billing_storage_content.html`
- `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/billing_subscription_content.html`
- `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/billing_usage_content.html`
- `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/fair_use_content.html`
- `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/referrals_content.html`
- `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/settings_account_content.html`
- `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/settings_content.html`
- `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/settings_notifications_content.html`
- `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/settings_recording_content.html`
- `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/settings_summaries_content.html`
- `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/settings_workspace_content.html`
- `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/components/settings_navigation.html`
- `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.css`
- `specs/173-settings-single-column/spec.md`
- `specs/173-settings-single-column/clarify.md`
- `specs/173-settings-single-column/plan.md`
- `specs/173-settings-single-column/research.md`
- `specs/173-settings-single-column/contracts/settings-single-column.md`
- `specs/173-settings-single-column/quickstart.md`

## Parallel execution examples

- After T001, T002 and T008 can run in parallel because server and macOS files are disjoint.
- T004 and T010 can run in parallel after their respective implementation tasks.
- Documentation evidence updates remain sequential to avoid conflicting edits to `quickstart.md`.

## Implementation strategy

1. Fix the user-blocking 720px profile defect with one state owner and exact guard.
2. Delete the now-unsupported settings fallback and its CSS/tests.
3. Simplify native inspector structure without changing layout.
4. Validate rendered behavior across surfaces, review, then run the fast gate once.
