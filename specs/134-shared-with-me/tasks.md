# Tasks: «Поделились со мной»

**Input**: Design documents from `/specs/134-shared-with-me/`

**Prerequisites**: [plan.md](plan.md), [spec.md](spec.md),
[research.md](research.md), [data-model.md](data-model.md),
[contracts/shared-with-me.md](contracts/shared-with-me.md),
[quickstart.md](quickstart.md)

**Risk / validation lane**: Significant, auth- and privacy-sensitive feature.
Run the selected server, RLS, route-contract and macOS route checks before
handoff, then `infra/scripts/ci-local.sh`.

**Organization**: Tasks are grouped by user story. Tests are required by the
chosen validation lane and must fail before the associated implementation.

## Phase 1: Setup

**Purpose**: Establish route and migration test coverage before new behavior.

- [ ] T001 [P] Add route and navigation expectations to `apps/server/tests/contract/test_shared_with_me_contract.py`.
- [ ] T002 [P] Add browser and embedded recipient-list scenarios to `apps/server/tests/integration/test_shared_with_me.py`.
- [ ] T003 [P] Add desktop path parity expectations to `apps/macos/Shared/Tests/DesktopCabinetRoutePolicyTests.swift`.

---

## Phase 2: Foundational recipient lookup boundary

**Purpose**: Provide the narrow cross-workspace candidate lookup required by
all stories without granting source-workspace membership or broad meeting reads.

**⚠️ CRITICAL**: Complete this phase before implementing the collection routes.

- [ ] T004 [P] Add unit coverage for the new context kind and rejected misuse in `apps/server/tests/unit/test_rls_tenant_context.py`.
- [ ] T005 [P] Add forced-RLS isolation coverage for direct active recipient grants in `apps/server/tests/integration/test_shared_with_me.py`.
- [ ] T006 Add `SharedWithMeLookupContext` and its exact settings/application support in `apps/server/src/twobrain_rec_server/db/tenant_context.py`.
- [ ] T007 Add a reversible SELECT-only active-direct-grant policy and supporting index in `apps/server/src/twobrain_rec_server/db/migrations/versions/0042_shared_with_me_lookup.py`.
- [ ] T008 Prove the new policy does not expose another recipient's grant, expired/revoked grant, grant mutation or source meeting row in `apps/server/tests/integration/test_shared_with_me.py`.

**Checkpoint**: Cross-workspace candidate discovery is narrow, read-only and
protected by regression tests.

---

## Phase 3: User Story 1 — открыть доступные мне встречи (Priority: P1) 🎯 MVP

**Goal**: A recipient can find and reopen every meeting they may currently
open, from a separate browser or embedded menu item.

**Independent Test**: Give one account an active grant; it sees one card and
opens the existing restricted page, while an unrelated account sees no card.

### Tests for User Story 1

- [ ] T009 [P] [US1] Specify the browser and embedded collection HTML contract, safe card fields and restricted target in `apps/server/tests/contract/test_shared_with_me_contract.py`.
- [ ] T010 [P] [US1] Specify active grant, empty state and unrelated-recipient journeys in `apps/server/tests/integration/test_shared_with_me.py`.
- [ ] T011 [P] [US1] Specify the macOS embedded route and menu target in `apps/macos/Shared/Tests/DesktopCabinetRoutePolicyTests.swift`.

### Implementation for User Story 1

- [ ] T012 [US1] Add recipient-safe shared-meeting card view models and the `Поделились со мной` navigation item in `apps/server/src/twobrain_rec_server/cabinet/view_models.py`.
- [ ] T013 [US1] Add candidate-grant lookup, per-candidate authoritative access recheck, safe-card construction and deterministic deduplication in `apps/server/src/twobrain_rec_server/cabinet/queries.py`.
- [ ] T014 [P] [US1] Add a recipient-only list page without owner actions in `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/shared_with_me_list_content.html`.
- [ ] T015 [US1] Render `GET /shared-with-me` through the existing browser cabinet shell in `apps/server/src/twobrain_rec_server/cabinet/web_routes/browser.py`.
- [ ] T016 [US1] Render `GET /desktop/shared-with-me` through the embedded cabinet shell in `apps/server/src/twobrain_rec_server/cabinet/web_routes/desktop.py`.
- [ ] T017 [US1] Verify the existing local return-path guard preserves both recipient-list routes without expanding its allowlist in `apps/server/src/twobrain_rec_server/cabinet/auth_return.py` and its focused tests.

**Checkpoint**: A confirmed recipient can independently discover and open a
shared meeting in both cabinet shells.

---

## Phase 4: User Story 2 — видеть только текущий разрешённый доступ (Priority: P1)

**Goal**: Revoked, expired, deleted or no-longer-verifiable shares never remain
visible as a usable recipient card.

**Independent Test**: Revoke or expire an active share after the initial list;
refresh omits it and the existing target remains denied.

### Tests for User Story 2

- [ ] T018 [P] [US2] Add revoked, expired, deleted, changed-proof and duplicate-grant cases to `apps/server/tests/integration/test_shared_with_me.py`.
- [ ] T019 [P] [US2] Add contract coverage for omission without source-meeting error detail in `apps/server/tests/contract/test_shared_with_me_contract.py`.

### Implementation for User Story 2

- [ ] T020 [US2] Ensure the recipient-list query omits failed rechecks and selects the most complete valid grant per meeting in `apps/server/src/twobrain_rec_server/cabinet/queries.py`.
- [ ] T021 [US2] Keep inaccessible cards absent and expose only a Russian neutral unavailable/empty state in `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/shared_with_me_list_content.html`.

**Checkpoint**: Recipient list is not a bypass for changed access state.

---

## Phase 5: User Story 3 — не получить рабочую область отправителя (Priority: P2)

**Goal**: The recipient has a useful list but receives no owner workspace,
resharing capability or source administrative details.

**Independent Test**: An external accepted recipient sees only safe card fields
and the existing restricted result page, with no workspace or owner controls.

### Tests for User Story 3

- [ ] T022 [P] [US3] Add recipient-safe metadata and no-owner-action assertions to `apps/server/tests/contract/test_shared_with_me_contract.py`.
- [ ] T023 [P] [US3] Add accepted-external-grant and no-workspace-membership scenarios to `apps/server/tests/integration/test_shared_with_me.py`.

### Implementation for User Story 3

- [ ] T024 [US3] Restrict shared card fields and link generation to recipient-safe values in `apps/server/src/twobrain_rec_server/cabinet/view_models.py` and `apps/server/src/twobrain_rec_server/cabinet/queries.py`.
- [ ] T025 [US3] Keep the dedicated page free of upload, delete, workspace, owner, export escalation and reshare controls in `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/shared_with_me_list_content.html`.

**Checkpoint**: The list improves discovery without adding authority.

---

## Phase 6: Polish and release readiness

**Purpose**: Run the full selected validation lane and document the user-facing
change. No commit, PR, release or deployment is included without fresh user
approval.

- [ ] T026 [P] Add the recipient-list behavior and access boundary to `CHANGELOG.md`.
- [ ] T027 Run focused server tests from `apps/server/tests/unit/test_rls_tenant_context.py`, `apps/server/tests/contract/test_shared_with_me_contract.py` and `apps/server/tests/integration/test_shared_with_me.py`.
- [ ] T028 Run the documented SwiftPM target for `apps/macos/Shared/Tests/DesktopCabinetRoutePolicyTests.swift`.
- [ ] T029 Run `infra/scripts/ci-local.sh` and record the result in the feature handoff.

---

## Dependencies and Execution Order

1. Phase 1 creates the test skeletons.
2. Phase 2 establishes the RLS lookup boundary and blocks all collection work.
3. User Story 1 delivers the usable list and navigation.
4. User Story 2 hardens freshness and deduplication on top of that list.
5. User Story 3 confirms that convenience does not add authority.
6. Phase 6 validates and documents the complete slice.

## Parallel Opportunities

- T001–T003 can be prepared independently.
- T004–T005 and T009–T011 can run in parallel because they use separate test
  areas.
- T014 can be authored while T012–T013 establish the view model and query
  contract.
- T018–T019 and T022–T023 are parallel test work after the MVP route exists.

## Implementation Strategy

Start with the existing grant/access-decision code rather than adding a new
sharing subsystem. The MVP is Phase 2 plus User Story 1; subsequent phases
only make the authorization result more robust and its surface more tightly
bounded.
