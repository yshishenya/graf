# Tasks: Cabinet Login Polish

**Input**: Design documents from `specs/070-cabinet-login-polish/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/

**Tests**: Required because this is a high-risk auth and user-facing UX lane.

**Organization**: Tasks are grouped by independently testable user story.

**GitHub Issue Sync**: #2534 tracks feature 070 closeout and validation evidence.

## Phase 1: Setup

- [X] T001 Set active Spec Kit feature pointer in `.specify/feature.json`
- [X] T002 Update the root plan reference in `AGENTS.md`

---

## Phase 2: Foundational

- [X] T003 [P] Add desktop auth-provider route policy expectations in `apps/macos/Shared/Tests/DesktopCabinetRoutePolicyTests.swift`
- [X] T004 [P] Add server-rendered auth asset regression expectations in `apps/server/tests/integration/test_web_owner_session_context.py`

---

## Phase 3: User Story 1 - Provider Login Works In The App (Priority: P1)

**Goal**: Provider OAuth no longer fails at the app route boundary while web works.

**Independent Test**: `swift test --package-path apps/macos --filter DesktopCabinetRoutePolicyTests`

- [X] T005 [US1] Add auth-provider continuation and callback route classification in `apps/macos/RecApp/Sources/Cabinet/DesktopCabinetRoutePolicy.swift`
- [X] T006 [US1] Verify focused desktop route policy tests in `apps/macos/Shared/Tests/DesktopCabinetRoutePolicyTests.swift`

---

## Phase 4: User Story 2 - Login Panel Feels Narrower And Cleaner (Priority: P2)

**Goal**: Auth panel and provider tiles use a narrower shared responsive layout.

**Independent Test**: Render `/login` and inspect shared auth CSS expectations.

- [X] T007 [US2] Narrow shared auth panel and provider-grid sizing in `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.css`
- [X] T008 [US2] Verify focused server auth rendering tests in `apps/server/tests/integration/test_web_owner_session_context.py`

---

## Phase 5: User Story 3 - Code Entry Completes Without Extra Clicks (Priority: P2)

**Goal**: Complete typed or pasted six-digit email codes submit once.

**Independent Test**: Focused auth rendering plus code-form asset regression and manual smoke from quickstart.

- [X] T009 [US3] Add guarded code auto-submit behavior in `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js`
- [X] T010 [US3] Keep code panel width aligned through shared auth CSS in `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.css`
- [X] T011 [US3] Verify focused server auth rendering tests in `apps/server/tests/integration/test_web_owner_session_context.py`

---

## Phase 6: Polish And Validation

- [X] T012 Run `cd apps/server && PYTHONPATH=src uv run --extra dev pytest -q tests/integration/test_web_owner_session_context.py`
- [X] T013 Run `swift test --package-path apps/macos --filter DesktopCabinetRoutePolicyTests`
- [X] T014 Record lane and validation evidence in `specs/070-cabinet-login-polish/quickstart.md`

## Dependencies & Execution Order

- Setup tasks T001-T002 before implementation.
- Foundational test tasks T003-T004 before corresponding implementation tasks.
- US1 is the MVP blocker and can complete before US2/US3.
- US2 and US3 both touch `cabinet.css`; run them sequentially.
- Final validation T012-T014 after implementation tasks.

## Parallel Execution Examples

- T003 and T004 can run in parallel because they touch Swift and Python tests separately.
- T005 and T007 cannot run in parallel with validation against the same files.

## Implementation Strategy

Ship US1 first, then the shared CSS polish, then the code auto-submit. Keep the diff to existing policy/assets/tests only.
