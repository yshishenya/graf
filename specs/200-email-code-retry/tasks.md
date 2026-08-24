# Tasks: Повторный ввод email-кода с лимитом попыток

**Input**: Design documents from `/specs/200-email-code-retry/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md,
contracts/email-code-retry.md, quickstart.md

**Risk lane**: `high-risk-feature` — auth/session security and shared auth UX.

## Phase 1: Setup

**Purpose**: Confirm the active slice and shared source-of-truth files.

- [X] T001 Confirm Feature 200 paths and existing email-code flow in `specs/200-email-code-retry/plan.md`, `apps/server/src/twobrain_rec_server/cabinet/web_routes/auth_email_flow.py`, and `apps/server/src/twobrain_rec_server/auth/rate_limit.py`

## Phase 2: User Story 1 — Повторный ввод после опечатки (P1)

**Goal**: First and second wrong codes remain recoverable; a correct code then
completes the normal login.

**Independent test**: One wrong code followed by the real local code returns the
normal successful redirect and creates one session.

### Tests first

- [X] T002 [P] [US1] Update the browser login regression in `apps/server/tests/integration/test_web_owner_session_context.py` so one and two wrong submissions keep the state pending, show the recoverable form, and allow the correct code to succeed
- [X] T003 [P] [US1] Add rendering assertions for recoverable wrong-code and blocked-code states in `apps/server/tests/contract/test_account_routes.py`

### Implementation

- [X] T004 [US1] Keep a wrong HMAC/code submission pending in `apps/server/src/twobrain_rec_server/cabinet/web_routes/auth_email_flow.py`, return a distinct recoverable `email_code_wrong` error, and preserve audit without sensitive values
- [X] T005 [US1] Add recoverable and blocked-state copy/form rules in `apps/server/src/twobrain_rec_server/cabinet/auth_rendering.py` and `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/auth/email_code.html`

## Phase 3: User Story 2 — Блокировка после трёх ошибок (P2)

**Goal**: Three failed checks exhaust one state; subsequent verification cannot
create a session and resend remains the recovery path.

**Independent test**: Three wrong checks followed by the real code are blocked;
resend is still available under existing send limits.

### Tests first

- [X] T006 [P] [US2] Add the three-failure and resend regression scenarios in `apps/server/tests/integration/test_web_owner_session_context.py`, including no session after the blocked correct-code attempt

### Implementation

- [X] T007 [US2] Change only `email_code_verify_state` from 10 to 3 in `apps/server/src/twobrain_rec_server/auth/rate_limit.py`, preserving all other auth rate limits

## Phase 4: User Story 3 — Сохранение соседних auth-flow (P3)

**Goal**: Signup gets retry parity while expiry, replay, browser binding and
account-linking remain fail-closed.

**Independent test**: Existing signup, expiry, replay, relay and account-linking
focused tests pass with no sensitive output.

- [X] T009 [P] [US3] Extend signup and protected-flow assertions in `apps/server/tests/integration/test_web_owner_session_context.py` for retry parity and unchanged expiry/replay/browser-binding behavior
- [X] T010 [US3] Verify `apps/server/tests/integration/test_rls_postgres_policies.py` still proves auth audit and callback-state RLS behavior without adding code/token/state data to evidence

## Phase 5: Polish & validation

- [X] T011 [P] Update `CHANGELOG.md` with the Russian user-facing email-code retry and three-attempt lockout behavior
- [X] T012 Run the focused Feature 200 checks from `specs/200-email-code-retry/quickstart.md` and record pass/fail evidence without committing or deploying
- [X] T013 Run `infra/scripts/ci-local.sh --fast` for the selected high-risk lane and reconcile every task with evidence

## Dependencies & Execution Order

- T001 precedes all implementation work.
- T002 and T003 can run in parallel and must be written before T004/T005.
- T006 can run after T002 and before T007; T007 is independent of T004/T005.
- T009/T010 validate shared auth boundaries after T004–T007.
- T011 can run in parallel with T009/T010; T012 and T013 are final gates.

## Parallel Opportunities

- T002, T003, T006 and T011 touch different files and can be prepared in
  parallel when their dependencies are met.
- T004, T005 and T007 touch different implementation surfaces but T005 depends
  on the `email_code_wrong` contract from T004.

## Implementation Strategy

1. Write and run the failing retry regression tests.
2. Implement the smallest shared-flow fix and state rate-limit change.
3. Validate signup and fail-closed neighboring flows.
4. Run focused checks, then the repository fast lane; do not deploy.
