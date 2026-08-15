# Tasks: Remove Workspace Legacy

**Input**: Design documents from `specs/150-remove-workspace-legacy/`

**Risk / Validation Lane**: high-risk-feature

## Phase 1: Test Context Separation

- [X] T001 Split internal auth anchor, primary customer workspace and personal workspace IDs in `apps/server/tests/fakes/auth_contexts.py` and seed a membership-free internal anchor in `apps/server/tests/conftest.py`.
- [X] T002 [P] Mirror the separated internal auth anchor in `apps/server/tests/fixtures/playback_normalization_ui_harness.py` without changing unrelated media fixtures.

---

## Phase 2: Foundational Auth/Tenant Guards

- [X] T003 Add failing shared-tenant tests for internal-anchor session/device/membership denial in `apps/server/tests/integration/test_tenant_authorization.py`.
- [X] T004 Add the fail-closed internal-anchor check ahead of membership/device validation in `apps/server/src/twobrain_rec_server/auth/dependencies.py`.
- [X] T005 Add failing workspace list/activation tests that omit and reject the configured internal anchor in `apps/server/tests/unit/test_workspace_onboarding.py` and `apps/server/tests/contract/test_auth_contracts.py`.
- [X] T006 Thread the server-owned internal workspace ID through list/activation callers and exclude it in `apps/server/src/twobrain_rec_server/auth/workspace_onboarding.py`, `apps/server/src/twobrain_rec_server/cabinet/web_routes/spaces.py`, and `apps/server/src/twobrain_rec_server/cabinet/web_routes/settings.py`.

**Checkpoint**: Even a stale internal membership cannot become product tenant scope or a selector item.

---

## Phase 3: User Story 1 — One Personal Context (Priority: P1)

**Goal**: Signup/login always resolves the internal auth flow to one personal owner workspace.

**Independent Test**: Repeat and concurrent auth yields one personal workspace/owner membership, sessions on personal, no internal membership or public internal identifier.

- [X] T007 [US1] Replace the legacy-identity fixture with clean repeat/concurrency and stale-internal-membership assertions in `apps/server/tests/contract/test_auth_contracts.py`.
- [X] T008 [US1] Make personal workspace creation uniqueness-race safe and canonicalize its product label in `apps/server/src/twobrain_rec_server/auth/workspace_onboarding.py`.
- [X] T009 [US1] Remove the callback membership-creation parameter and internal-membership fallback while preserving valid non-internal corporate membership in `apps/server/src/twobrain_rec_server/auth/callbacks.py`, `apps/server/src/twobrain_rec_server/api/auth.py`, and `apps/server/src/twobrain_rec_server/auth/policy.py`.
- [X] T010 [US1] Remove email-login internal-membership fallback and pass the configured internal ID through normal login/signup in `apps/server/src/twobrain_rec_server/cabinet/web_routes/auth_email_flow.py` and `apps/server/src/twobrain_rec_server/cabinet/web_routes/auth.py`.

---

## Phase 4: User Story 2 — Explicit Corporate Access (Priority: P1)

**Goal**: Legitimate corporate membership remains explicit and internal/personal workspaces cannot become invitation targets.

**Independent Test**: Pending offer creates no membership; explicit accept creates one corporate membership; personal/internal targets and revoked access are denied.

- [X] T011 [US2] Add negative invitation/offer target-kind and accepted-corporate regression coverage in `apps/server/tests/unit/test_workspace_onboarding.py` and `apps/server/tests/contract/test_auth_contracts.py`.
- [X] T012 [US2] Enforce corporate customer target and internal-anchor exclusion in existing invitation/join-offer services in `apps/server/src/twobrain_rec_server/admin/invitations.py` and `apps/server/src/twobrain_rec_server/auth/workspace_onboarding.py` without adding a new enrollment abstraction.
- [X] T013 [US2] Preserve revoked-corporate personal recovery and no-retarget behavior in `apps/server/tests/integration/test_tenant_authorization.py`.

---

## Phase 5: User Story 3 — Remove Legacy Surface (Priority: P2)

**Goal**: No permanent runtime, CLI or test path classifies or supports pre-097 bootstrap memberships.

**Independent Test**: Obsolete-surface quickstart command finds no legacy report module/import/test; auth behavior passes without legacy fixtures.

- [X] T014 [P] [US3] Delete `apps/server/src/twobrain_rec_server/cli/workspace_migration_report.py` and `apps/server/tests/unit/test_workspace_migration_report.py`.
- [X] T015 [US3] Remove legacy report imports/assertions from `apps/server/tests/integration/test_rls_postgres_policies.py` and update active 097/current-status guidance without rewriting historical evidence in `specs/097-workspace-account-onboarding/quickstart.md` and `docs/current-product-status.md`.

---

## Phase 6: Product Copy And Billing Boundary

- [X] T016 [P] Update canonical selector copy to `Моё пространство`, `Личное · Владелец`, and `Рабочее пространство · <роль>` in `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/settings_workspace_content.html` and `apps/server/tests/contract/test_provider_link_settings_contract.py`.
- [X] T017 Add/adjust self-serve billing tests proving personal-owner only and internal/corporate denial in `apps/server/tests/contract/test_billing_ui.py` and `apps/server/tests/integration/test_web_owner_session_context.py`.
- [X] T018 Reuse the existing personal-owner billing guard and close any internal/corporate gap in `apps/server/src/twobrain_rec_server/cabinet/web_routes/billing.py`.

---

## Phase 7: Validation And Closeout

- [X] T019 [P] Record the clean-cut behavior and one-shot cleanup boundary under `[Unreleased]` in `CHANGELOG.md` and reconcile `docs/current-product-status.md`.
- [X] T020 Run all focused scenarios from `specs/150-remove-workspace-legacy/quickstart.md` and record metadata-only results there.
- [X] T021 Run `infra/scripts/ci-local.sh --fast`, reconcile every completed task, and record the high-risk validation evidence in `specs/150-remove-workspace-legacy/quickstart.md`.
- [X] T022 Run a deletion-focused Ponytail review and code/security review; resolve any auth/tenant/billing blocker before requesting commit approval.
- [X] T023 [US1] Enforce internal-anchor, active-membership and personal-owner invariants for every session-backed principal route, with fail-closed email ambiguity and public auth non-disclosure tests in `apps/server/src/twobrain_rec_server/auth/dependencies.py`, `apps/server/src/twobrain_rec_server/api/auth.py`, and `apps/server/src/twobrain_rec_server/cabinet/web_routes/auth_email_flow.py`.
- [X] T024 [US2] Serialize workspace activation and join-offer decisions, hide non-corporate offers, and add truthful accessible workspace result/UI coverage in `apps/server/src/twobrain_rec_server/auth/workspace_onboarding.py`, `apps/server/src/twobrain_rec_server/cabinet/rendering.py`, and `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/settings_workspace_content.html`.
- [X] T025 Enforce active personal-owner authority across renewal planning, charging, cutoff, reconciliation, entitlement projection and plan navigation; terminalize invalid historical webhooks in `apps/server/src/twobrain_rec_server/billing/`, `apps/server/src/twobrain_rec_server/workflows/worker.py`, and `apps/server/src/twobrain_rec_server/cabinet/web_routes/billing.py`.
- [X] T026 Reconcile validation evidence and remove duplicated repository guidance in `specs/150-remove-workspace-legacy/quickstart.md`, `CHANGELOG.md`, `docs/current-product-status.md`, and `AGENTS.md` after the remediation checks pass.

## Dependencies

- T001–T002 establish trustworthy fixtures before behavior changes.
- T003–T006 block all user stories by enforcing the internal boundary.
- US1 (T007–T010) and US2 (T011–T013) follow the shared guards.
- US3 (T014–T015) follows behavior replacement so removed tests do not hide gaps.
- T016 may run in parallel after T006; T017–T018 follow the tenant guard.
- T019–T022 follow all implementation tasks.
- T023–T025 are remediation gates discovered by the final review and must pass before T022 can close.
- T026 follows T023–T025 and the repeated focused/security validation.

## Parallel Example

After T006, separate workers may execute T007–T010 (US1), T011–T013 (US2), and T016 (copy) because their primary files do not overlap. T014 can run in parallel once replacement coverage exists.

## Implementation Strategy

Start with the shared deny boundary and fixture separation, then replace login behavior, preserve explicit corporate access, delete obsolete code, and finish with copy/billing/validation. No new dependency, table or permanent cleanup command is introduced.
