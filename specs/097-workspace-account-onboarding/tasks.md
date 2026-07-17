# Tasks: Workspace Account Onboarding

**Input**: Design documents from `specs/097-workspace-account-onboarding/`

**Risk / validation lane**: High-risk auth, privacy, data and onboarding feature.
Every completed task requires its named focused check; closeout also requires
the quickstart, `infra/scripts/ci-local.sh`, review and approved deploy gates.

## Phase 1: Setup

- [X] T001 Record the current auth/invitation/session call graph and affected regression suites in `specs/097-workspace-account-onboarding/research.md`.
- [X] T002 Add the Feature 097 Unreleased entry and migration limitation to `CHANGELOG.md`.

## Phase 2: Foundational account, schema and RLS work

- [X] T003 [P] Add personal/corporate workspace fields and user-owned join-offer ORM models in `apps/server/src/twobrain_rec_server/db/models/identity.py`, `apps/server/src/twobrain_rec_server/db/models/onboarding.py`, and `apps/server/src/twobrain_rec_server/db/models/__init__.py`.
- [X] T004 [P] Write model and state-transition tests for personal workspaces and join offers in `apps/server/tests/unit/test_workspace_onboarding.py`.
- [X] T005 Write upgrade/downgrade and legacy-classification assertions for the onboarding schema in `apps/server/tests/integration/test_postgres_migrations.py`.
- [X] T006 Add the reversible personal-workspace/join-offer migration and PostgreSQL RLS policies in `apps/server/src/twobrain_rec_server/db/migrations/versions/0027_workspace_account_onboarding.py`.
- [X] T007 Add PostgreSQL RLS tests proving a user can see only their offers and active spaces in `apps/server/tests/integration/test_rls_postgres_policies.py`.
- [X] T008 Implement the shared idempotent personal-space, offer and active-membership helpers in `apps/server/src/twobrain_rec_server/auth/workspace_onboarding.py`.
- [X] T009 Add metadata-only onboarding audit event helpers and redaction tests in `apps/server/src/twobrain_rec_server/auth/audit.py` and `apps/server/tests/unit/test_auth_audit.py`.

**Checkpoint**: schema migration and RLS receipts pass before altering public login behavior.

## Phase 3: User Story 1 — simple personal registration (P1)

**Goal**: A new person signs up without a workspace ID and receives exactly one
personal space and scoped session.

**Independent test**: new and repeated email/provider registration creates no
duplicate account/workspace, lands in a personal space and cannot read a
corporate workspace.

- [ ] T010 [P] [US1] Add contract tests for new and classified-legacy email registration, retry/idempotency and no implicit bootstrap membership in `apps/server/tests/contract/test_auth_contracts.py`.
- [ ] T011 [P] [US1] Add browser flow tests for sign-up without workspace ID and personal-space landing in `apps/server/tests/integration/test_web_owner_session_context.py`.
- [ ] T012 [P] [US1] Add provider callback parity tests for new and existing identities in `apps/server/tests/contract/test_auth_contracts.py`.
- [ ] T013 [US1] Refactor email registration resolution to use the internal bootstrap only as an auth anchor and issue the personal-space session in `apps/server/src/twobrain_rec_server/cabinet/web_routes/auth_email_flow.py`.
- [ ] T014 [US1] Refactor provider callback account creation/login to use the shared personal-space helper and remove implicit bootstrap membership in `apps/server/src/twobrain_rec_server/auth/callbacks.py`.
- [ ] T015 [US1] Remove raw workspace-ID requirements and copy from public sign-up/login routes and templates in `apps/server/src/twobrain_rec_server/cabinet/web_routes/auth.py`, `apps/server/src/twobrain_rec_server/cabinet/auth_rendering.py`, and `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/auth/`.
- [ ] T016 [US1] Preserve the internal bootstrap configuration validation while documenting that it is not a public enrollment destination in `apps/server/src/twobrain_rec_server/config.py` and `apps/server/tests/unit/test_config_validation.py`.

## Phase 4: User Story 2 — explicit corporate invitation acceptance (P1)

**Goal**: A verified person sees matching invitations as choices and joins only
after explicit acceptance.

**Independent test**: one or multiple invitations create offers after login;
accepting one creates only that membership, while rejection, expiry, revocation
and replay create none.

- [ ] T017 [P] [US2] Add invitation-offer, identity-match, replay and multi-offer tests in `apps/server/tests/unit/test_workspace_onboarding.py`.
- [ ] T018 [P] [US2] Add authenticated browser contract tests for listing, accepting and rejecting offers in `apps/server/tests/contract/test_auth_contracts.py`.
- [ ] T019 [US2] Replace `complete_matching_invitation_after_login` auto-completion with server-side offer creation in `apps/server/src/twobrain_rec_server/admin/invitations.py` and `apps/server/src/twobrain_rec_server/auth/callbacks.py`.
- [ ] T020 [US2] Add CSRF-protected offer list, accept and reject routes in `apps/server/src/twobrain_rec_server/cabinet/web_routes/spaces.py` and register them from `apps/server/src/twobrain_rec_server/cabinet/web.py`.
- [ ] T021 [US2] Render accessible offer status, confirmation and recovery states in `apps/server/src/twobrain_rec_server/cabinet/rendering.py` and `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/settings_content.html`.
- [ ] T022 [US2] Ensure offer/invitation audit entries are metadata-only and no route reveals target contacts or unrelated workspace data in `apps/server/src/twobrain_rec_server/admin/invitations.py` and `apps/server/tests/unit/test_admin_invitations.py`.

## Phase 5: User Story 3 — corporate admin control remains intact (P1)

**Goal**: Corporate admins keep controlled invitations, roles, revocation and
last-owner protection; personal spaces never expose team management.

**Independent test**: admin operations work for corporate spaces; equivalent
personal-space requests are denied and cannot remove the last corporate owner.

- [ ] T023 [P] [US3] Add corporate-versus-personal admin authorization, invitation resend and terminal invitation tests in `apps/server/tests/integration/test_workspace_admin_panel.py` and `apps/server/tests/unit/test_email_login_delivery.py`.
- [ ] T024 [US3] Gate admin invitation and member-management entry points by workspace kind, then add safe resend delivery through `apps/server/src/twobrain_rec_server/admin/permissions.py`, `apps/server/src/twobrain_rec_server/admin/invitations.py`, `apps/server/src/twobrain_rec_server/api/admin.py`, `apps/server/src/twobrain_rec_server/admin/web.py`, and `apps/server/src/twobrain_rec_server/auth/email_delivery.py`.
- [ ] T025 [US3] Hide corporate team-management controls for personal spaces in `apps/server/src/twobrain_rec_server/cabinet/rendering.py` and `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/settings_content.html`.
- [ ] T026 [US3] Recheck last-owner protection, revoked-member access and audit coverage in `apps/server/tests/unit/test_admin_permissions.py` and `apps/server/tests/integration/test_tenant_authorization.py`.

## Phase 6: User Story 4 — privacy-safe corporate discovery (P2)

**Goal**: Corporate email alone never discloses or joins a workspace in v1.

**Independent test**: a matching email domain with no explicit invitation has a
personal space only and receives no corporate existence disclosure.

- [ ] T027 [P] [US4] Add regression tests for disabled-by-default domain discovery and email/provider parity in `apps/server/tests/contract/test_auth_contracts.py`.
- [ ] T028 [US4] Make the workspace enrollment policy reject domain-only automatic joins and return only safe generic outcomes in `apps/server/src/twobrain_rec_server/auth/policy.py` and `apps/server/src/twobrain_rec_server/auth/callbacks.py`.

## Phase 7: User Story 5 — visible and server-verified active space (P2)

**Goal**: People can see and explicitly switch their active personal/corporate
space; revoked access falls back safely without retargeting work.

**Independent test**: a user with two spaces selects one, new work uses it, and
revocation denies its session while preserving personal access.

- [ ] T029 [P] [US5] Add active-space list, switch and revoked-session contract tests in `apps/server/tests/contract/test_auth_contracts.py`.
- [ ] T030 [P] [US5] Add integration tests covering workspace-scoped cabinet access, queued upload non-retargeting and personal fallback in `apps/server/tests/integration/test_tenant_authorization.py` and `apps/server/tests/integration/test_web_owner_session_context.py`.
- [ ] T031 [US5] Implement server-verified accessible-space listing and scoped session replacement in `apps/server/src/twobrain_rec_server/auth/workspace_onboarding.py`, `apps/server/src/twobrain_rec_server/auth/sessions.py`, and `apps/server/src/twobrain_rec_server/cabinet/web_routes/spaces.py`.
- [ ] T032 [US5] Render the active-space selector and unavailable/revoked recovery state with keyboard and screen-reader status in `apps/server/src/twobrain_rec_server/cabinet/rendering.py` and `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/settings_content.html`.
- [ ] T033 [US5] Enforce session/membership revalidation and explicit blocked recovery for desktop-scoped requests in `apps/server/src/twobrain_rec_server/auth/dependencies.py` and `apps/server/tests/integration/test_tenant_authorization.py`.
- [ ] T034 [US5] Handle a revoked embedded-cabinet session as an explicit reauthentication/reselection state in `apps/macos/RecApp/Sources/Cabinet/DesktopCabinetState.swift`, `apps/macos/RecApp/Sources/Cabinet/DesktopCabinetWorkspaceView.swift`, and `apps/macos/Shared/Tests/DesktopCabinetWorkspaceTests.swift`.

## Phase 8: Legacy report, documentation and validation

- [ ] T035 Add and run the read-only metadata-only legacy bootstrap-user classification command before release enablement in `apps/server/src/twobrain_rec_server/cli/workspace_migration_report.py` and `apps/server/tests/unit/test_workspace_migration_report.py`.
- [ ] T036 Document no-move migration operation, backup, rollback and evidence rules in `specs/097-workspace-account-onboarding/quickstart.md` and `docs/agent-guidance/release-and-validation.md` only if a reusable runbook gap remains.
- [ ] T037 Run all quickstart focused tests and record safe receipts in `specs/097-workspace-account-onboarding/validation/local.md`.
- [ ] T038 Run `infra/scripts/ci-local.sh` and record the result in `specs/097-workspace-account-onboarding/validation/local.md`.
- [ ] T039 Review the final diff for requirement coverage, privacy, accessibility and unnecessary complexity; update `specs/097-workspace-account-onboarding/tasks.md` only for verified fixes.
- [ ] T040 Reconcile every completed task with its GitHub issue, update `CHANGELOG.md`, and prepare the PR evidence in `specs/097-workspace-account-onboarding/validation/traceability.md`.
- [ ] T041 After approved release gate, run deploy dry-run, production deploy, metadata-only B2C/invitation/revocation smoke, rollback readiness and tracker closeout in `specs/097-workspace-account-onboarding/validation/release-closeout.md`.

## Dependencies and order

`T001–T009` block all stories. US1 enables a safe personal landing; US2 uses
that identity and can then run. US3 can follow the foundational schema. US4 is
a regression guard. US5 requires US1/US2 session semantics. Phase 8 follows
all implementation tasks.

## Parallel opportunities

- T003/T004 and focused test tasks marked `[P]` touch separate files.
- T010–T012, T017–T018, T023, T027 and T029–T030 may be prepared in parallel
  after foundation, but implementation remains serialized by shared auth files.

## Implementation strategy

Deliver the foundation and US1 first, validate one safe personal onboarding,
then add explicit offers and switching. Do not expose partial corporate joining
or move any legacy data while a later phase is incomplete.
