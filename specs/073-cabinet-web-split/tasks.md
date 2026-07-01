# Tasks: Cabinet Web Split

**Input**: Design documents from `/specs/073-cabinet-web-split/`

**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`,
`contracts/`, `quickstart.md`

**Tests**: Required. This is a behavior-preserving refactor across auth/session,
CSRF, deletion/reporting, calendar, desktop WebView, and cabinet web routes.

## Phase 1: Baseline

**Purpose**: Prove the current route contracts before moving code.

- [X] T001 Run focused baseline pytest command from `specs/073-cabinet-web-split/quickstart.md` and stop if it fails before code changes.
- [X] T002 Inspect current route ownership in `apps/server/src/twobrain_rec_server/cabinet/web.py`.

## Phase 2: Route Split (User Story 1, Priority: P1)

**Goal**: Split cabinet web route families into readable modules while keeping the public router import stable.

**Independent Test**: `twobrain_rec_server.cabinet.web.router` still imports, and route families are visible by file path.

- [X] T003 [US1] Create `apps/server/src/twobrain_rec_server/cabinet/web_routes/` with shared support in `apps/server/src/twobrain_rec_server/cabinet/web_routes/support.py`.
- [X] T004 [US1] Move static icon and browser auth route families from `apps/server/src/twobrain_rec_server/cabinet/web.py` into `apps/server/src/twobrain_rec_server/cabinet/web_routes/`.
- [X] T005 [US1] Move browser meeting/settings and calendar route families from `apps/server/src/twobrain_rec_server/cabinet/web.py` into `apps/server/src/twobrain_rec_server/cabinet/web_routes/`.
- [X] T006 [US1] Move desktop embedded and deletion route families from `apps/server/src/twobrain_rec_server/cabinet/web.py` into `apps/server/src/twobrain_rec_server/cabinet/web_routes/`.
- [X] T007 [US1] Keep `apps/server/src/twobrain_rec_server/cabinet/web.py` as the public router assembly exporting `router` without changing `apps/server/src/twobrain_rec_server/main.py`.

## Phase 3: Behavior Preservation (User Story 2, Priority: P1)

**Goal**: Prove existing browser and desktop behavior survived the split.

**Independent Test**: Focused cabinet tests pass after the split.

- [X] T008 [US2] Run focused cabinet pytest command from `specs/073-cabinet-web-split/quickstart.md`.
- [X] T009 [US2] Run calendar-specific pytest command from `specs/073-cabinet-web-split/quickstart.md` because calendar route code moves.
- [X] T010 [US2] Fix only route-split regressions in `apps/server/src/twobrain_rec_server/cabinet/web_routes/` or `apps/server/src/twobrain_rec_server/cabinet/web.py`.

## Phase 4: Security And Privacy Preservation (User Story 3, Priority: P1)

**Goal**: Prove auth/session, CSRF, tenant scope, deletion truth, and no-secret behavior were not weakened.

**Independent Test**: Security/privacy-focused cabinet tests pass without assertion weakening.

- [X] T011 [US3] Confirm moved POST routes still use existing CSRF dependency and protected routes still use existing principal/tenant/session dependencies in `apps/server/src/twobrain_rec_server/cabinet/web_routes/`.
- [X] T012 [US3] Do not weaken existing tests under `apps/server/tests/`.

## Phase 5: Final Validation

**Purpose**: Keep the diff small and ready for PR.

- [X] T013 Run `git diff --check` and `uv --project apps/server run --extra dev pytest -q apps/server/tests/unit/test_cabinet_web_shell.py`.
- [X] T014 Run `infra/scripts/ci-local.sh` after focused tests pass because runtime files changed.
- [X] T015 Mark completed tasks `[X]` in `specs/073-cabinet-web-split/tasks.md` only after each task's validation passes.

## Dependencies And Execution Order

- Phase 1 blocks all implementation.
- T003 blocks T004-T007.
- T004-T007 run sequentially because helpers and imports overlap.
- Phase 3 blocks Phase 4.
- Phase 5 is last.

## Parallel Opportunities

- None for route moves; the shared helper/import surface makes sequential work safer.
- Test commands can be split across shells only after the route split imports cleanly.

## Implementation Strategy

1. Prove baseline first.
2. Move shared dependencies once.
3. Move route families one at a time.
4. Run focused tests after the split.
5. Stop instead of widening scope if behavior coupling crosses auth, deletion, egress, DB, infra, or deploy boundaries.
