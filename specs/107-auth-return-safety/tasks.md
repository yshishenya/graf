# Tasks: Safe Browser Login Returns and Callback Diagnostics

**Input**: Design documents from `specs/107-auth-return-safety/`

**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md), [research.md](research.md), [data-model.md](data-model.md), [browser auth return contract](contracts/browser-auth-return.md), [quickstart.md](quickstart.md)

**Tests**: Required. This is a high-risk auth/privacy/diagnostics slice. Add the focused tests before their behavior change, run the feature quickstart while implementing, and run canonical local CI at closeout.

**Organization**: Tasks are grouped by user story so that safe sign-in returns, direct unavailable recovery, and metadata-only callback diagnostics can be validated independently.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel after its stated dependencies because it touches different files.
- **[Story]**: Maps a task to the corresponding user story in [spec.md](spec.md).
- Every implementation task names its exact target path.

## Phase 1: Setup

**Purpose**: The existing server, database, and test infrastructure already satisfy this feature's setup needs. No dependency, schema, or environment-file task is required.

**Checkpoint**: Do not introduce a database migration, a new package, a client route, or a production operation.

---

## Phase 2: Foundational RLS-Safe Return Resolver

**Purpose**: Establish the small shared post-session decision boundary before any browser login flow invokes it.

- [X] T001 Add a failing authenticated RLS-context resolver test for allowed and denied exact detail candidates in `apps/server/tests/integration/test_rls_postgres_policies.py`.
- [X] T002 Implement the exact regular/embedded detail parser and `decide_meeting_access`-based fallback resolver in `apps/server/src/twobrain_rec_server/cabinet/auth_return.py`, applying `TenantDatabaseContext` and never loading a full meeting review.

**Checkpoint**: The resolver has one privacy-preserving decision surface, retains no content-bearing result, and its RLS-focused test passes.

---

## Phase 3: User Story 1 - Return to a Safe Place After Sign-in (Priority: P1) 🎯 MVP

**Goal**: A new or existing browser/embedded user reaches an authorized detail or the matching neutral list after external or email sign-in, without a stale deep link becoming a raw error.

**Independent Test**: Complete supported browser sign-in from regular and embedded detail candidates as both a viewer with access and a viewer without access; confirm the redirect route only. Complete email login and registration after changing the verification form `next`; confirm the state-bound candidate controls the route and existing replay/browser-state checks remain green.

### Tests for User Story 1 ⚠️

- [X] T003 [US1] Add failing external-provider browser return tests for authorized and denied regular/embedded detail candidates, including representative Yandex/VK shared start routes and existing callback binding/replay coverage, in `apps/server/tests/integration/test_web_owner_session_context.py`.
- [X] T004 [US1] Add failing email login and registration return tests proving a changed verification-form `next` cannot override `AuthCallbackState.requested_redirect` in `apps/server/tests/integration/test_web_owner_session_context.py`.

### Implementation for User Story 1

- [X] T005 [US1] Extend callback completion data with the organization context required for the authenticated RLS return decision in `apps/server/src/twobrain_rec_server/auth/callbacks.py`.
- [X] T006 [US1] Invoke the shared resolver after a user callback session is established and before the browser 303 in `apps/server/src/twobrain_rec_server/api/auth.py`, preserving API and provider-link callback behavior.
- [X] T007 [US1] Return a trusted email completion context containing the consumed state redirect and issued session identity from `apps/server/src/twobrain_rec_server/cabinet/web_routes/auth_email_flow.py`.
- [X] T008 [US1] Resolve both email login and registration browser destinations from the trusted completion context rather than the verification form in `apps/server/src/twobrain_rec_server/cabinet/web_routes/auth.py`.
- [X] T009 [US1] Run and record the focused auth and RLS checks from `specs/107-auth-return-safety/quickstart.md` against `apps/server/tests/integration/test_web_owner_session_context.py` and `apps/server/tests/integration/test_rls_postgres_policies.py`.

**Checkpoint**: User Story 1 is independently complete: allowed deep links remain, unavailable ones converge to their matching list, email form tampering cannot select a destination, and callback protections remain intact.

---

## Phase 4: User Story 3 - Keep Callback Diagnostics Safe (Priority: P1)

**Goal**: Callback support evidence retains useful metadata but never raw callback queries, headers, cookies, or authorization material.

**Independent Test**: Run the real app under Uvicorn with unique synthetic query and header markers; captured stdout/stderr contains none of them while it still includes the structured completion event, UUID-templated path, status, and duration.

### Tests for User Story 3 ⚠️

- [X] T010 [P] [US3] Update metadata-only request-event expectations and redaction boundary checks in `apps/server/tests/unit/test_structured_logging.py`.
- [X] T011 [P] [US3] Add a real-Uvicorn subprocess regression with synthetic query, cookie, authorization, and referer markers in `apps/server/tests/integration/test_runtime_request_logging.py`.
- [X] T012 [P] [US3] Add a source-controlled runtime-command assertion for disabled Uvicorn access logging in `apps/server/tests/integration/test_compose_hardening.py`.

### Implementation for User Story 3

- [X] T013 [US3] Remove arbitrary request-header capture from structured request start/end events while retaining the explicit support metadata allowlist in `apps/server/src/twobrain_rec_server/observability/logging.py`.
- [X] T014 [US3] Disable Uvicorn access logging in the production API command in `infra/server/Dockerfile`.
- [X] T015 [US3] Run and record the focused logging and Docker command checks from `specs/107-auth-return-safety/quickstart.md` against `apps/server/tests/unit/test_structured_logging.py`, `apps/server/tests/integration/test_runtime_request_logging.py`, and `apps/server/tests/integration/test_compose_hardening.py`.

**Checkpoint**: User Story 3 is independently complete: the process boundary retains safe operational metadata but no synthetic authorization material.

---

## Phase 5: User Story 2 - Receive a Useful Unavailable Page (Priority: P2)

**Goal**: Direct regular and embedded unavailable detail links yield a neutral, accessible cabinet page with a matching list action instead of raw problem JSON.

**Independent Test**: As an authenticated user, open denied, missing, and malformed regular/embedded detail routes. Each full-page response is neutral HTML 404 with the matching list action and no identifier or private meeting content; HTMX/API 404 behavior remains machine-readable.

### Tests for User Story 2 ⚠️

- [X] T016 [P] [US2] Add full-page regular/embedded missing, denied, and malformed detail recovery assertions plus HTMX preservation checks in `apps/server/tests/integration/test_cabinet_web_access_states.py`.
- [X] T017 [P] [US2] Add neutral shell, semantic heading, and matching-list-action assertions for both surfaces in `apps/server/tests/unit/test_cabinet_web_shell.py`.

### Implementation for User Story 2

- [X] T018 [US2] Add the neutral unavailable-page renderer and matching content template in `apps/server/src/twobrain_rec_server/cabinet/rendering.py` and `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/meeting_unavailable_content.html`.
- [X] T019 [US2] Route regular full-page missing, denied, and malformed meeting detail identifiers to the neutral renderer while preserving HTMX behavior in `apps/server/src/twobrain_rec_server/cabinet/web_routes/browser.py`.
- [X] T020 [US2] Route embedded full-page missing, denied, and malformed meeting detail identifiers to the neutral renderer while preserving HTMX behavior in `apps/server/src/twobrain_rec_server/cabinet/web_routes/desktop.py`.
- [X] T021 [US2] Run and record the focused unavailable-page checks from `specs/107-auth-return-safety/quickstart.md` against `apps/server/tests/integration/test_cabinet_web_access_states.py` and `apps/server/tests/unit/test_cabinet_web_shell.py`.

**Checkpoint**: User Story 2 is independently complete: unavailable direct links have a useful, non-oracular recovery page on both surfaces without changing fragment/API contracts.

---

## Phase 6: Polish, Evidence, and Closed Release Boundary

**Purpose**: Reconcile cross-story behavior, public change notes, and the high-risk validation lane without crossing the user's closed release gate.

- [X] T022 Update the unreleased auth/privacy/UX and diagnostics change notes in `CHANGELOG.md` without including credentials, meeting content, or live identifiers.
- [X] T023 Run the complete focused scenario set in `specs/107-auth-return-safety/quickstart.md` and mark only evidence-backed completed tasks in `specs/107-auth-return-safety/tasks.md`.
- [X] T024 Run `infra/scripts/ci-local.sh`, record high-risk lane evidence in `specs/107-auth-return-safety/tasks.md`, and explicitly omit deploy, release, tag, production log retention, and cleanup actions.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No generated setup work; the no-schema/no-dependency boundary applies throughout.
- **Foundational resolver (Phase 2)**: T001 must demonstrate the required authenticated RLS decision before T002 provides it.
- **User Story 1 (Phase 3)**: T003 and T004 are written before T005-T008; T009 follows their implementation and the foundational resolver.
- **User Story 3 (Phase 4)**: T010-T012 are written before T013-T014; T015 follows. It can run in parallel with User Story 1 after Phase 2.
- **User Story 2 (Phase 5)**: T016-T017 are written before T018-T020; T021 follows. It can run in parallel with User Story 1 after Phase 2.
- **Polish (Phase 6)**: T022-T024 depend on all desired story checkpoints. T024 is a closeout gate, not release approval.

### User Story Dependencies

- **US1 (P1)**: Depends on the resolver foundation; it is the MVP and covers the reported login path.
- **US3 (P1)**: Independent of US1 implementation after the foundation and may proceed in parallel; it shares the same privacy/diagnostics validation lane.
- **US2 (P2)**: Independent of US1 behavior after the foundation and may proceed in parallel; it completes direct-link recovery.

### Parallel Opportunities

- T003 and T004 intentionally run sequentially because they share the focused auth test file.
- T010, T011, and T012 touch separate test files and can run in parallel.
- T016 and T017 touch separate test files and can run in parallel.
- US3 and US2 can be implemented independently of the remaining US1 route wiring once T002 is complete.

## Parallel Example: Diagnostics and Unavailable Recovery

```text
Task: "T010 Update metadata-only request-event expectations in apps/server/tests/unit/test_structured_logging.py"
Task: "T011 Add process-boundary logging regression in apps/server/tests/integration/test_runtime_request_logging.py"
Task: "T012 Add Docker command assertion in apps/server/tests/integration/test_compose_hardening.py"

Task: "T016 Add unavailable-route integration assertions in apps/server/tests/integration/test_cabinet_web_access_states.py"
Task: "T017 Add unavailable-renderer shell assertions in apps/server/tests/unit/test_cabinet_web_shell.py"
```

## Implementation Strategy

### MVP First

1. Complete T001-T002 so the authenticated RLS return decision is isolated and tested.
2. Complete US1 through T009; this resolves the reported post-Yandex stale detail path and the email return integrity issue.
3. Keep the branch server-only and do not release or deploy.

### Incremental Delivery

1. Add US3 metadata-only diagnostics in parallel with or immediately after US1.
2. Add US2 direct-link recovery after its tests define the neutral page contract.
3. Update the changelog, run the focused quickstart, and run local CI only at the feature closeout boundary.

## Notes

- [P] tasks touch different files and have no incomplete-file dependency.
- All task completion marks require implementation and the named validation evidence.
- GitHub issue synchronization occurs after analysis; do not create a release, deploy, tag, or production-log action from this task list.

## Validation Evidence

- Focused browser-auth suite: `34 passed` in
  `tests/integration/test_web_owner_session_context.py`, including authorized
  and denied external-provider returns, email return integrity, callback-state
  binding, expiry, cancellation, and replay checks.
- Focused unavailable-page suite: `50 passed` across
  `tests/integration/test_cabinet_web_access_states.py` and
  `tests/unit/test_cabinet_web_shell.py`; full regular and embedded responses
  are neutral HTML 404s while HTMX remains machine-readable.
- Focused diagnostics suite: `29 passed` across
  `tests/unit/test_structured_logging.py`,
  `tests/integration/test_runtime_request_logging.py`, and
  `tests/integration/test_compose_hardening.py`; a real Uvicorn child process
  was exercised with synthetic non-secret query/header markers.
- PostgreSQL RLS suite: `17 passed` in
  `tests/integration/test_rls_postgres_policies.py` against an isolated
  disposable local PostgreSQL container; the container was removed after the
  proof.
- High-risk local gate: `infra/scripts/ci-local.sh` passed, including macOS
  build/tests, server tests and lint, compilation, RLS hardening validation,
  Compose configuration, and deployment-evidence scan.
- Implementation closeout completed without a production action. The user then
  explicitly reopened the release/deploy gate; production receipts will be
  recorded in the PR, GitHub closure comments, and release notes after rollout.
