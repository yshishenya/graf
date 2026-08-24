# Tasks: Yandex ID account selection

**Input**: Design documents from `/specs/200-yandex-account-selection/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

## Phase 1: Setup

- [X] T001 Review Feature 200 scope and existing Yandex provider URL builder in `apps/server/src/twobrain_rec_server/auth/providers/base.py`

## Phase 2: Foundational

- [X] T002 Confirm existing callback state, secret custody, and provider isolation requirements in `specs/200-yandex-account-selection/contracts/browser-yandex-account-selection.md`

## Phase 3: User Story 1 - Вход с выбором аккаунта (Priority: P1) 🎯 MVP

**Goal**: Ask Yandex ID for an interactive account/login step without changing
callback verification or other providers.

**Independent Test**: Focused browser-login tests prove Yandex URL construction
and VK URL isolation; manual two-account provider acceptance proves selection.

- [X] T003 [US1] Add a failing focused assertion for Yandex `force_confirm=1` and VK parameter isolation in `apps/server/tests/integration/test_web_owner_session_context.py`
- [X] T004 [US1] Add Yandex-only `force_confirm=1` authorization parameter in `apps/server/src/twobrain_rec_server/auth/providers/base.py`
- [X] T005 [US1] Run the Feature 200 focused quickstart and record the automated result in `specs/200-yandex-account-selection/quickstart.md`
- [X] T006 [US1] Perform the two-account manual browser acceptance and record metadata-only result in `specs/200-yandex-account-selection/quickstart.md`

## Phase 4: Polish & Cross-Cutting Concerns

- [X] T007 [US1] Run `infra/scripts/ci-local.sh --fast` and review the final diff without creating a commit or PR

## Dependencies & Execution Order

- T001 → T002 → T003 → T004 → T005 → T006 → T007
- T003 MUST fail before T004 is implemented.
- T006 depends on the automated checks and requires a browser with two Yandex accounts.

## Parallel Opportunities

- No implementation tasks are parallelizable because the regression test and
  the single provider adapter file are intentionally ordered.

## Implementation Strategy

1. Keep the diff to the Yandex adapter and its existing integration test.
2. Validate the URL contract first, then run the real provider acceptance.
3. Stop before commit, PR, release, or deployment as requested.
