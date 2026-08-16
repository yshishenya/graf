# Tasks: Связанные способы входа

**Input**: Design documents from `specs/157-account-auth-linking/`

**Prerequisites**: `spec.md`, `plan.md`, `research.md`, `data-model.md`,
`contracts/`, `quickstart.md`, `checklists/security.md`,
`checklists/ux.md`

**Risk lane**: high-risk-feature. Tests are mandatory for auth, data movement,
RLS, rollback and web/desktop parity.

## Phase 1: Setup

- [X] T001 [P] Add disposable duplicate-account fixtures and safe identity seed helpers in `apps/server/tests/fakes/auth_contexts.py` and `apps/server/tests/fakes/auth_providers.py`
- [X] T002 [P] Add the account-linking error-code and localized-copy fixture matrix in `apps/server/tests/contract/test_auth_contracts.py`
- [X] T003 [P] Record the merge policy version and validation scenario mapping in `specs/157-account-auth-linking/quickstart.md`

## Phase 2: Foundational

- [X] T004 Add additive merge-intent and merge-journal models with source archival state in `apps/server/src/twobrain_rec_server/db/models/federated_auth.py` and `apps/server/src/twobrain_rec_server/db/models/identity.py`
- [X] T005 Create Alembic migration `apps/server/src/twobrain_rec_server/db/migrations/versions/0073_account_auth_linking.py` for merge intent/journal, source redirect state, active-pair uniqueness and required indexes
- [X] T006 [P] Define pure entity merge policy, blocker codes, bounded preview counts and deterministic survivor ordering in `apps/server/src/twobrain_rec_server/auth/account_merge.py`
- [X] T007 [P] Add unit coverage for merge policy, role/billing/calendar/deletion blockers and zero-mutation terminal states in `apps/server/tests/unit/test_account_merge_policy.py`
- [X] T008 Add row-lock, RLS and foreign-key inventory helpers for all user-owned references used by the merge preflight in `apps/server/tests/integration/test_account_merge.py`

## Phase 3: User Story 1 — Вход существующего пользователя вторым способом (Priority: P1) 🎯 MVP

**Goal**: Email-code and verified OAuth proofs converge on one canonical
account without passwords or duplicate creation.

**Independent Test**: Complete email→OAuth and OAuth→email on disposable data;
both methods issue access to the same account and meetings.

### Tests for User Story 1

- [X] T009 [P] [US1] Add contract cases for email→OAuth, OAuth→email, idempotent link, proof failure and provider identity conflict in `apps/server/tests/unit/test_provider_links.py`
- [X] T010 [P] [US1] Add end-to-end email/OAuth linking scenarios with no duplicate user in `apps/server/tests/integration/test_account_merge.py`

### Implementation for User Story 1

- [X] T011 [US1] Extend the existing provider-link service in `apps/server/src/twobrain_rec_server/auth/provider_links.py` to accept the second verified proof without creating a new identity owner
- [X] T012 [US1] Route OAuth→email confirmation through the existing passwordless email state and single-use code handling in `apps/server/src/twobrain_rec_server/cabinet/web_routes/auth_email_flow.py`
- [X] T013 [US1] Preserve CSRF/state/nonce/rate-limit checks and map proof, replay, expiry and provider conflicts to the shared localized contract in `apps/server/src/twobrain_rec_server/auth/callbacks.py` and `apps/server/src/twobrain_rec_server/cabinet/web_routes/auth.py`
- [X] T014 [US1] Add browser and desktop route parity coverage for successful and rejected linking in `apps/server/tests/contract/test_provider_link_settings_contract.py`

## Phase 4: User Story 2 — Понятное разрешение конфликта аккаунтов (Priority: P1)

**Goal**: An ambiguous email never gives an arbitrary session; a fully verified
user can preview, confirm or safely cancel a data-preserving merge.

**Independent Test**: Seed two active accounts with one email and meetings;
verify the recovery reason, preview, successful merge, cancel, blocker and
replay outcomes.

### Tests for User Story 2

- [X] T015 [P] [US2] Add contract coverage for ambiguous-email, merge-preview, stale-preview, blocker and completion outcomes in `apps/server/tests/contract/test_account_merge_contract.py`
- [X] T016 [P] [US2] Add integration coverage for empty duplicate auto-link, both-sides-data merge, cancellation, expiry and replay in `apps/server/tests/integration/test_account_merge.py`
- [X] T017 [P] [US2] Add regression coverage proving email login start and verify return a localized recovery state instead of HTTP 500 in `apps/server/tests/integration/test_web_owner_session_context.py` and `apps/server/tests/contract/test_auth_contracts.py`

### Implementation for User Story 2

- [X] T018 [US2] Implement read-only merge preflight and bounded preview fingerprint in `apps/server/src/twobrain_rec_server/auth/account_merge.py`
- [X] T019 [US2] Implement one-use proof-bound merge confirmation with deterministic row locks, idempotency and transaction rollback in `apps/server/src/twobrain_rec_server/auth/account_merge.py`
- [X] T020 [US2] Apply the entity policy: preserve meetings/content/workspaces, transfer only eligible user references, block role/billing/calendar/deletion conflicts, and archive the source in `apps/server/src/twobrain_rec_server/auth/account_merge.py`
- [X] T021 [US2] Revoke affected sessions and device trust, preserve append-only audit lineage and emit metadata-only merge outcomes in `apps/server/src/twobrain_rec_server/auth/account_merge.py` and `apps/server/src/twobrain_rec_server/auth/audit.py`
- [X] T022 [US2] Add authenticated recovery, preview, confirm and cancel routes with safe Russian error copy in `apps/server/src/twobrain_rec_server/cabinet/web_routes/auth.py` and `apps/server/src/twobrain_rec_server/cabinet/web_routes/account_merge.py`
- [X] T023 [US2] Catch `_AmbiguousEmailIdentityError` consistently in login start and verify callers and render `ambiguous_email_recovery_required` in `apps/server/src/twobrain_rec_server/cabinet/web_routes/auth.py` and `apps/server/src/twobrain_rec_server/cabinet/web_routes/auth_email_flow.py`

## Phase 5: User Story 3 — Управление способами входа в настройках (Priority: P2)

**Goal**: Users can inspect, add and safely remove OAuth methods without losing
the last recovery path.

**Independent Test**: Open account security settings, add OAuth, re-authenticate
for unlink and verify last-method protection on browser and desktop routes.

### Tests for User Story 3

- [X] T024 [P] [US3] Add requirements-driven settings contract cases for provider labels, verification state, unlink guard and last-method blocking in `apps/server/tests/contract/test_provider_link_settings_contract.py` and `apps/server/tests/contract/test_account_routes.py`

### Implementation for User Story 3

- [X] T025 [US3] Extend account security view models and rendering with safe linked-method state, recovery guidance and merge conflict action in `apps/server/src/twobrain_rec_server/cabinet/view_models.py` and `apps/server/src/twobrain_rec_server/cabinet/rendering.py`
- [X] T026 [US3] Add authenticated OAuth unlink routes and enforce the last-usable-method guard in `apps/server/src/twobrain_rec_server/cabinet/web_routes/settings.py` and `apps/server/src/twobrain_rec_server/auth/provider_links.py`
- [X] T027 [US3] Add Russian accessible status/error copy in `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/settings_account_content.html` and existing provider-link settings templates, with keyboard/focus contract coverage in `apps/server/tests/contract/test_provider_link_settings_contract.py`

## Phase 6: User Story 4 — Одинаковый безопасный поток в вебе и macOS-приложении (Priority: P2)

**Goal**: The server-owned outcome and safe return behavior are identical in
the browser and GRAF Local WebView.

**Independent Test**: Repeat success, conflict, cancel and provider-error
scenarios in browser and embedded app without external idle navigation.

### Tests for User Story 4

- [X] T028 [P] [US4] Add browser/desktop route parity and localized-outcome matrix in `apps/server/tests/contract/test_account_routes.py` and `apps/server/tests/contract/test_provider_link_settings_contract.py`
- [X] T029 [P] [US4] Add WebView auth-return and external-navigation boundary coverage in `apps/macos/Shared/Tests/DesktopCabinetRoutePolicyTests.swift`

### Implementation for User Story 4

- [X] T030 [US4] Update only the existing WebView auth route allowlist/error handoff needed for merge recovery in `apps/macos/RecApp/Sources/Cabinet/DesktopCabinetRoutePolicy.swift`
- [X] T031 [US4] Keep embedded settings and recovery actions on server-owned `/desktop/...` routes through the existing WebView boundary

## Phase 7: Polish and cross-cutting validation

- [X] T032 [P] Update Russian behavior/architecture/release-readiness notes in `CHANGELOG.md`
- [X] T033 Run focused auth/link/merge/settings tests and quickstart disposable-data scenarios; record metadata-only evidence in `specs/157-account-auth-linking/`
- [X] T034 Run `infra/scripts/ci-local.sh --fast` and then full `infra/scripts/ci-local.sh`; resolve all auth, RLS, migration and WebView regressions before PR
- [X] T035 Perform the final security-diff and Ponytail review of changed auth/data paths and reconcile every completed task with its evidence before implementation closeout

## Open implementation blocker

- [X] T036 [US2] Execute the merge transaction through a production-safe, narrowly scoped maintenance boundary; the current web app role must not be granted the general maintenance role, and the current in-process implementation is only validated with the owner-role disposable test harness.

## Dependencies and execution order

### Phase dependencies

- Setup is independent.
- Foundational tasks depend on Setup and block all user stories.
- US1 and US2 are both P1; US2 depends on the proof/error contracts from US1
  but its preflight tests can be prepared in parallel after foundation.
- US3 depends on US1 link semantics and US2 conflict action.
- US4 depends on server contracts from US1–US3 but its parity tests can be
  prepared in parallel.
- Polish depends on all selected stories.

### Parallel opportunities

- T001–T003 are independent documentation/fixture setup.
- T006–T007 can proceed in parallel with T004–T005 because they use pure policy
  contracts and do not alter schema.
- T009–T010, T015–T017 and T028–T029 are independent test files within their
  story phases.
- T024 can be written while US2 server work is in progress.

## Implementation strategy

1. Deliver MVP as US1 plus the ambiguous-email fail-closed regression.
2. Add US2 only after the preview/policy tests prove zero mutation and stable
   IDs on disposable PostgreSQL.
3. Add settings and WebView parity, then run the full high-risk validation lane.
4. Do not deploy or repair a real production duplicate in this slice; that is a
   separate release-gated operation after evidence and explicit approval.
