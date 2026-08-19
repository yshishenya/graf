# Tasks: Надёжный вход по email и восстановление аккаунта

**Input**: Design documents from `specs/175-fix-email-auth-recovery/`

**Prerequisites**: `spec.md`, `plan.md`, `research.md`, `data-model.md`,
`contracts/email-auth-recovery.md`, `quickstart.md`, `checklists/requirements.md`,
`checklists/security.md`, `checklists/ux.md`

**Risk lane**: high-risk-feature. Test-first forced-RLS, transaction, auth UX
and web/embedded parity checks are mandatory.

## Phase 1: Setup

- [X] T001 [P] Add reusable synthetic email-auth seed/assert helpers for app-role PostgreSQL scenarios in `apps/server/tests/integration/test_rls_postgres_policies.py`
- [X] T002 [P] Extend the localized auth outcome and provider-action contract matrix in `apps/server/tests/contract/test_auth_contracts.py`

---

## Phase 2: Foundational transaction boundary

- [X] T003 Add failing forced-RLS regressions for exact callback completion, audit write contexts and all-or-nothing rollback in `apps/server/tests/integration/test_rls_postgres_policies.py`
- [X] T004 Implement one shared callback terminal-state helper and remove helper-owned commits in `apps/server/src/twobrain_rec_server/cabinet/web_routes/auth_email_flow.py`
- [X] T005 Move successful/error response preparation and the single commit to email login/signup endpoints in `apps/server/src/twobrain_rec_server/cabinet/web_routes/auth.py`

**Checkpoint**: Existing-user login, wrong/expired/replayed code and injected
failure are atomic under the non-owner app role before recovery UX changes.

---

## Phase 3: User Story 1 — Завершить вход по email без серверной ошибки (Priority: P0) 🎯 MVP

**Goal**: A valid email code creates one usable session and consumes the exact
callback without HTTP 500 or orphan state.

**Independent Test**: Run the forced-RLS existing-user matrix and ordinary HTTP
route test; expect `303`, one session/binding, completed callback and rejected replay.

### Tests for User Story 1

- [X] T006 [P] [US1] Extend HTTP integration coverage for success, response-resolution rollback, replay and no orphan session in `apps/server/tests/integration/test_web_owner_session_context.py`
- [X] T007 [P] [US1] Add concurrent valid-code and invalid/expired audit regressions under the app role in `apps/server/tests/integration/test_rls_postgres_policies.py`

### Implementation for User Story 1

- [X] T008 [US1] Finalize success, invalid, expired and ambiguous callback rows through exact nonce context while writing audit under the owning workspace in `apps/server/src/twobrain_rec_server/cabinet/web_routes/auth_email_flow.py`

---

## Phase 4: User Story 2 — Получить понятный путь при нескольких аккаунтах (Priority: P0)

**Goal**: Early and late ambiguous email states show working configured
Яндекс ID/VK recovery actions without issuing a session.

**Independent Test**: Seed duplicate users, exercise web and embedded-safe next
paths before and after code verification, and assert localized explanation,
active provider links, no account details and no session.

### Tests for User Story 2

- [X] T009 [P] [US2] Add early/late ambiguity, provider availability, disabled-provider fallback and settings-safe-next HTTP coverage in `apps/server/tests/integration/test_web_owner_session_context.py`
- [X] T010 [P] [US2] Add accessible recovery-copy and configured-provider rendering contracts in `apps/server/tests/contract/test_auth_contracts.py`

### Implementation for User Story 2

- [X] T011 [US2] Reuse one provider-aware ambiguous recovery response in start and verify paths in `apps/server/src/twobrain_rec_server/cabinet/web_routes/auth.py` and `apps/server/src/twobrain_rec_server/cabinet/web_routes/auth_email_flow.py`
- [X] T012 [US2] Refine the Russian recovery copy without exposing account metadata in `apps/server/src/twobrain_rec_server/cabinet/auth_rendering.py`

---

## Phase 5: User Story 3 — Корректно связать или предложить объединение аккаунтов (Priority: P1)

**Goal**: 0/1/>1 other-user classification, email/OAuth linking and web/embedded
preview flows remain RLS-safe and never auto-confirm a cross-account merge.

**Independent Test**: Run the candidate matrix, forced-RLS merge/link completion,
empty-other preview and embedded route assertions; no data changes before POST confirm.

### Tests for User Story 3

- [X] T013 [P] [US3] Add 0/1/>1 candidate, empty-other preview, replay and merge-error rollback cases in `apps/server/tests/integration/test_account_merge.py`
- [X] T014 [P] [US3] Add forced-RLS email-link, OAuth provider-link terminal context, same-state single-winner and different-state active-intent race regressions in `apps/server/tests/integration/test_rls_postgres_policies.py`
- [X] T015 [P] [US3] Add embedded verify/resend/back and preview/confirm/cancel route parity contracts in `apps/server/tests/contract/test_account_routes.py` and `apps/server/tests/integration/test_web_owner_session_context.py`

### Implementation for User Story 3

- [X] T016 [US3] Exclude the current user before cardinality, wrap merge intent work in a savepoint, remove auto-confirm and finalize email callback by exact nonce in `apps/server/src/twobrain_rec_server/cabinet/web_routes/auth_email_flow.py`
- [X] T017 [US3] Flush merge intent work, restore authorized link-state context and remove OAuth-link auto-confirm in `apps/server/src/twobrain_rec_server/auth/provider_links.py`
- [X] T018 [US3] Keep embedded email-link rendering on `desktop_link` routes and let the endpoint own commit/rollback in `apps/server/src/twobrain_rec_server/cabinet/web_routes/settings.py` and `apps/server/src/twobrain_rec_server/cabinet/auth_rendering.py`
- [X] T019 [US3] Complete bounded merge preview copy for survivor, sign-in methods, preserved data, separate workspaces, sessions/devices and blockers in `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/account_merge_content.html` and `apps/server/tests/contract/test_account_routes.py`

---

## Phase 6: Polish and cross-cutting validation

- [X] T020 [P] Update user-facing `[Unreleased]` auth/recovery notes in `CHANGELOG.md`
- [X] T021 Run focused quickstart PostgreSQL/RLS tests and Ruff checks from `specs/175-fix-email-auth-recovery/quickstart.md`; record metadata-only results in `specs/175-fix-email-auth-recovery/evidence.md`
- [ ] T022 Run independent correctness, auth/security, UX/accessibility and Ponytail reviews; fix every actionable finding and repeat focused regressions
- [X] T023 Run `infra/scripts/ci-local.sh --fast` once on the final implementation and reconcile `tasks.md`, GitHub issues and evidence before PR
- [ ] T024 After validation and explicit user approval, prepare a separate logical implementation commit, Russian PR with high-risk evidence, independent review and merge; do not deploy until the production gate is separately approved

## Dependencies and execution order

- Phase 1 is independent setup.
- Phase 2 blocks all user stories because every path needs the atomic callback
  boundary and endpoint-owned transaction.
- US1 and US2 may proceed in parallel after Phase 2; US3 depends on the same
  terminal helper and should land after its contract is stable.
- T013–T015 are parallel test files; T016–T019 are sequential where they share
  rendering/route contracts.
- Phase 6 starts only after all selected stories pass independently.

## Implementation strategy

1. Reproduce the production failure under forced RLS before code changes.
2. Fix transaction/context ownership once and prove US1.
3. Reuse the existing provider renderer for US2; do not add a recovery wizard.
4. Apply the explicit 0/1/>1 contract and remove both auto-confirm calls for US3.
5. Run focused checks during iteration, one fast lane at closeout, and full CI
   only at the approved release/deploy boundary.
