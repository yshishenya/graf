# Tasks: Локальная разработка только с PostgreSQL

**Input**: Design documents from `specs/108-local-postgres-only/`  
**Prerequisites**: `plan.md`, `research.md`, `data-model.md`, `contracts/local-postgres-test-runner.md`, `quickstart.md`

**Tests**: Required. This is a high-risk PostgreSQL/Docker/migration change.

## Format: `[ID] [P?] [Story] Description`

- `[P]` marks a task that can be completed in parallel with other tasks in its phase.
- `[US#]` maps to the corresponding user story in `spec.md`.

## Phase 1: Setup

**Purpose**: Preserve scope and establish the executable local PostgreSQL boundary.

- [X] T001 Record the current active SQLite inventory and archival exclusion boundary in `specs/108-local-postgres-only/research.md`.
- [X] T002 [P] Add runner contract tests in `apps/server/tests/contract/test_local_postgres_test_runner.py` for loopback-only targets, generated names, safe failure and cleanup commands.
- [X] T003 [P] Add PostgreSQL-only settings tests in `apps/server/tests/unit/test_config.py` for accepted production-compatible URLs and rejected SQLite URLs.

## Phase 2: Foundational Test Infrastructure

**Purpose**: Build the reusable isolated test database boundary before converting test callers.

- [X] T004 Implement safe URL validation and generated disposable database lifecycle helpers in `apps/server/tests/fixtures/postgres_test_database.py`.
- [X] T005 Implement `apps/server/scripts/run_local_postgres_tests.sh` to start only `rec-postgres`, await readiness, create and clean a generated test database, export test-only URLs and run pytest.
- [X] T006 Update `apps/server/tests/conftest.py` to create, reset and dispose PostgreSQL-only test engines without sharing a developer database.
- [X] T007 Update `infra/scripts/ci-local.sh` to use `apps/server/scripts/run_local_postgres_tests.sh` for the canonical server test path.
- [X] T008 Add the runner and fixture lifecycle coverage required by `apps/server/tests/contract/test_local_postgres_test_runner.py` and `apps/server/tests/conftest.py`.

**Checkpoint**: A focused pytest invocation has one safe local PostgreSQL entry point and rejects any non-local or non-disposable target.

## Phase 3: User Story 1 — Предсказуемый локальный запуск (Priority: P1)

**Goal**: A developer can prepare and use an isolated local PostgreSQL test database through one documented command.

**Independent Test**: Start only `rec-postgres`; run `bash apps/server/scripts/run_local_postgres_tests.sh tests/unit/test_config.py -q`; confirm a generated database is removed after success and after a forced test failure.

- [X] T009 [US1] Add readiness, interrupted-run cleanup and occupied-port diagnostics to `apps/server/scripts/run_local_postgres_tests.sh`.
- [X] T010 [US1] Update the local developer instructions in `specs/108-local-postgres-only/quickstart.md` and active server documentation to use only the runner.
- [X] T011 [US1] Run and record the User Story 1 lifecycle proof in `specs/108-local-postgres-only/validation/local-runner.md`.

## Phase 4: User Story 2 — Реалистичные серверные проверки (Priority: P2)

**Goal**: Server tests and migrations use PostgreSQL semantics, including upgrade/downgrade and RLS paths.

**Independent Test**: The focused migration, health and client fixtures pass through the runner; migration upgrade and downgrade occur in the generated PostgreSQL database.

- [X] T012 [US2] Enforce PostgreSQL async URLs in `apps/server/src/twobrain_rec_server/config.py` and remove the SQLite development dependency from `apps/server/pyproject.toml`, `apps/server/uv.lock` and `apps/server/constraints.txt`.
- [X] T013 [P] [US2] Replace SQLite-specific partial-index declarations in `apps/server/src/twobrain_rec_server/db/models/admin.py`, `apps/server/src/twobrain_rec_server/db/models/identity.py` and `apps/server/src/twobrain_rec_server/db/models/ingest.py`.
- [X] T014 [P] [US2] Replace SQLite-specific partial-index migration declarations in `apps/server/src/twobrain_rec_server/db/migrations/versions/0013_workspace_admin_panel.py` and `apps/server/src/twobrain_rec_server/db/migrations/versions/0022_playback_normalization.py`.
- [X] T015 [US2] Convert the shared application fixture and direct app-path tests in `apps/server/tests/conftest.py`, `apps/server/tests/unit/test_app_lifecycle.py`, `apps/server/tests/unit/test_public_landing.py`, `apps/server/tests/integration/test_health_readiness.py`, `apps/server/tests/integration/test_production_docs_exposure.py` and `apps/server/tests/contract/test_public_analytics_contract.py` to PostgreSQL-only URLs.
- [X] T016 [US2] Convert migration coverage in `apps/server/tests/integration/test_postgres_migrations.py` and `apps/server/tests/integration/test_meeting_detection_migrations.py` to generated PostgreSQL databases.
- [X] T017 [US2] Convert calendar migration coverage in `apps/server/tests/integration/test_calendar_auto_context_migrations.py` to PostgreSQL async queries and PostgreSQL-compatible assertions.
- [X] T018 [US2] Convert playback migration and UI harness coverage in `apps/server/tests/integration/test_playback_normalization_migrations.py` and `apps/server/tests/fixtures/playback_normalization_ui_harness.py` to PostgreSQL-only setup.
- [X] T019 [US2] Remove the SQLite-specific normalization comment and validate real locking behavior in `apps/server/src/twobrain_rec_server/normalization/service.py` and its focused tests.
- [X] T020 [US2] Extend `apps/server/tests/integration/test_postgres_migrations.py` with clean upgrade, downgrade and seeded request proofs against the runner-provided database.
- [X] T021 [US2] Run and record focused PostgreSQL migration, RLS and fixture evidence in `specs/108-local-postgres-only/validation/postgres-test-proof.md`.

## Phase 5: User Story 3 — Отсутствие устаревшей альтернативы (Priority: P3)

**Goal**: Active server code, tests, dependencies and instructions no longer expose SQLite as a supported path.

**Independent Test**: The active-path regression scan returns no SQLite match and the canonical local gate invokes only the PostgreSQL runner.

- [X] T022 [US3] Add an active-path SQLite regression guard in `apps/server/tests/contract/test_postgres_only_contract.py` covering dependencies, server source, tests, local scripts and local Compose instructions.
- [X] T023 [US3] Remove remaining active SQLite references discovered by the guard from `apps/server/`, `infra/scripts/ci-local.sh` and `infra/docker-compose.dev.yml` without changing archival evidence.
- [X] T024 [US3] Update `CHANGELOG.md` with the PostgreSQL-only local development and test migration plus its compatibility boundary.
- [X] T025 [US3] Run and record the zero-active-SQLite proof in `specs/108-local-postgres-only/validation/active-surface.md`.

## Phase 6: Polish & Cross-Cutting Validation

- [X] T026 Run the feature quickstart, focused runner tests and `infra/scripts/ci-local.sh`; record results in `specs/108-local-postgres-only/validation/local-ci.md`.
- [X] T027 Run a Ponytail complexity review over the final database-runner diff and record conclusions in `specs/108-local-postgres-only/validation/ponytail-review.md`.
- [X] T028 Reconcile every completed task with the Feature 108 GitHub issue, add Russian evidence comments and leave incomplete work open.
- [X] T029 Perform final code review and Spec Kit artifact review; resolve all Critical/High findings before integration.

## Dependencies & Execution Order

1. Setup (T001–T003) → Foundational test infrastructure (T004–T008).
2. User Story 1 (T009–T011) can be validated first and delivers the supported local entry point.
3. User Story 2 (T012–T021) depends on the runner and fixture boundary.
4. User Story 3 (T022–T025) depends on all active-path conversions.
5. Final validation (T026–T029) depends on all stories.

## Parallel Opportunities

- T002 and T003 touch separate test paths.
- T013 and T014 touch separate model/migration files after T004–T008.
- T015–T019 can be split by owning test/module group after T012, but not edited concurrently in the same checkout.

## Implementation Strategy

1. Deliver the runner and isolation guard first; it is the minimum safe vertical slice.
2. Convert active tests and schema declarations in bounded groups, keeping the regression guard red until all SQLite support is removed.
3. Run the canonical local gate, review the minimal diff, reconcile issues and integrate only after evidence is complete.
