# Tasks: Быстрый и достоверный PostgreSQL test pipeline

**Input**: Design documents from `specs/110-postgres-test-acceleration/`  
**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`,
`contracts/local-postgres-test-pipeline.md`, `quickstart.md`

**Tests**: Required. This is a high-risk PostgreSQL/Docker/RLS test-boundary
change; write or tighten focused tests before each behavioural implementation.

## Format: `[ID] [P?] [Story] Description`

- `[P]` marks independent file work that can run in parallel after its
  prerequisites.
- `[US#]` maps to the user story in `spec.md`.
- A task is complete only after its specified checks pass and it is marked
  `[X]` here.

## Phase 1: Setup

**Purpose**: Freeze the safe PostgreSQL-only contract and expose the
development dependency required for controlled parallel execution.

- [X] T001 [P] Extend runner-safety expectations for generated prefixes, loopback-only targets and metadata-only output in `apps/server/tests/contract/test_local_postgres_test_runner.py`.
- [X] T002 [P] Add the development-only pytest-xdist dependency and registered strict marker in `apps/server/pyproject.toml`, then refresh `apps/server/uv.lock`.
- [X] T003 [P] Add a focused fixture-isolation test module in `apps/server/tests/integration/test_postgres_test_isolation.py` for distinct worker state, seed restoration and clean-schema separation.

## Phase 2: Foundational PostgreSQL Test Boundary

**Purpose**: Build the safe fixture and runner primitives before changing either
user-visible test result or parallel scheduling.

- [X] T004 Implement generated run-prefix, admin/worker/clean URL validation, safe create/drop lifecycle and bounded table-reset helpers in `apps/server/tests/fixtures/postgres_test_database.py`.
- [X] T005 Extract deterministic base seeding and implement the one-schema-per-worker `postgres_seeded_database_url` client path in `apps/server/tests/conftest.py`.
- [X] T006 Implement RLS owner/probe target validation and a host-wide PostgreSQL advisory-lock fixture for fixed cluster-global role tests in `apps/server/tests/fixtures/postgres_rls.py`.
- [X] T007 Implement full-versus-focused phase orchestration, per-worker database ownership, strict-lane execution, exact-prefix cleanup and safe timing/accounting output in `apps/server/scripts/run_local_postgres_tests.sh`.
- [X] T008 Route empty-schema and migration callers to `postgres_clean_database_url` in `apps/server/tests/integration/test_health_readiness.py`, `apps/server/tests/integration/test_postgres_migrations.py`, `apps/server/tests/integration/test_meeting_detection_migrations.py`, `apps/server/tests/integration/test_calendar_auto_context_migrations.py` and `apps/server/tests/integration/test_playback_normalization_migrations.py`.
- [X] T009 Mark and wire the serial/advisory-lock RLS boundary in `apps/server/tests/integration/test_rls_postgres_policies.py` and `apps/server/tests/integration/test_playback_normalization_postgres.py`.
- [X] T010 Run the new runner/fixture contract and focused isolation tests through `apps/server/scripts/run_local_postgres_tests.sh`; keep the foundation red until cross-worker mutation and clean-schema regression cases are proven.

**Checkpoint**: A disposable loopback-only test run has separate worker and
clean states, and no ordinary test path still drops/recreates the full schema.

## Phase 3: User Story 1 — Trust the full local gate (Priority: P1) 🎯 MVP

**Goal**: Normalization tests represent the production worker context and fail
closed when that authority is absent.

**Independent Test**: The two known failing files pass against disposable
PostgreSQL, while the existing missing-context contract remains negative.

### Tests for User Story 1

- [X] T011 [P] [US1] Add/strengthen explicit worker-context regression assertions in `apps/server/tests/integration/test_playback_normalization_failures.py` and `apps/server/tests/integration/test_playback_normalization_deletion.py`.
- [X] T012 [P] [US1] Extend the negative context-boundary assertion only where needed in `apps/server/tests/contract/test_playback_normalization_rls_contract.py` without weakening its production-like contract.

### Implementation for User Story 1

- [X] T013 [US1] Apply the exact job-derived or deterministic `TenantScope` with `context_kind="worker"` before every direct normalization worker invocation in `apps/server/tests/integration/test_playback_normalization_failures.py`.
- [X] T014 [US1] Apply the exact job-derived worker scope before the blocked late-worker execution in `apps/server/tests/integration/test_playback_normalization_deletion.py`.
- [X] T015 [US1] Audit all direct `run_normalization_job` callers and correct only missing worker context in `apps/server/tests/integration/test_playback_normalization_audit_persistence.py`, `apps/server/tests/integration/test_playback_normalization_backfill.py`, `apps/server/tests/integration/test_playback_normalization_finalize.py`, `apps/server/tests/integration/test_playback_normalization_idempotency.py`, `apps/server/tests/integration/test_playback_normalization_retry.py`, `apps/server/tests/integration/test_playback_normalization_restart.py`, `apps/server/tests/integration/test_playback_normalization_workflow.py` and `apps/server/tests/integration/test_playback_normalization_test_rec_e2e.py` when static audit confirms a missing context.
- [X] T016 [US1] Run the focused worker-context, failure-recovery and deletion serialization suite via `apps/server/scripts/run_local_postgres_tests.sh`.

**Checkpoint**: The PostgreSQL guard is still active, the known RuntimeErrors
are corrected by truthful worker context, and the deletion test no longer times
out before its intended upload-lock boundary.

## Phase 4: User Story 2 — Get the complete result much faster (Priority: P1)

**Goal**: Ordinary tests reset data quickly and safely; strict tests remain
real PostgreSQL proofs; full mode may parallelize only independent files.

**Independent Test**: Serial and bounded parallel full server runs have the
same collected/outcome/skip/xfail accounting, strict RLS tests remain present,
and no disposable residue remains.

### Tests for User Story 2

- [X] T017 [P] [US2] Add bounded-truncate, seed-after-failure, worker-database separation and clean-fixture regression cases in `apps/server/tests/integration/test_postgres_test_isolation.py`.
- [X] T018 [P] [US2] Extend phase-union, worker-count validation, strict-lane inclusion and cleanup contracts in `apps/server/tests/contract/test_local_postgres_test_runner.py`.
- [X] T019 [P] [US2] Add the RLS URL-safety and advisory-lock regression coverage in `apps/server/tests/integration/test_rls_postgres_policies.py` and `apps/server/tests/integration/test_playback_normalization_postgres.py`.

### Implementation for User Story 2

- [X] T020 [US2] Complete worker database creation/teardown and clean-fixture isolation in `apps/server/tests/fixtures/postgres_test_database.py` against the focused tests.
- [X] T021 [US2] Complete one-time schema preparation and per-client bounded truncate/reseed in `apps/server/tests/conftest.py`; remove only demonstrably unused test-engine allocation in the same fixture path.
- [X] T022 [US2] Complete xdist setup, full-mode partition accounting, serial strict RLS phase and interruption-safe prefix cleanup in `apps/server/scripts/run_local_postgres_tests.sh`.
- [X] T023 [US2] Complete fixed-role advisory locking and strict module integration in `apps/server/tests/fixtures/postgres_rls.py`, `apps/server/tests/integration/test_rls_postgres_policies.py` and `apps/server/tests/integration/test_playback_normalization_postgres.py`.
- [X] T024 [US2] Validate one-, four-, six- and eight-worker ordinary/strict runs with `apps/server/scripts/run_local_postgres_tests.sh`, proving no schema or data leak between workers and no excluded node IDs from the same-commit pre-partition collection.

**Checkpoint**: Full local PostgreSQL evidence is faster without SQLite,
coverage reduction, role collisions or unsafe cross-worktree interference.

## Phase 5: User Story 3 — Understand cost and failures (Priority: P2)

**Goal**: A developer gets concise, safe timing and isolation evidence instead
of waiting through an opaque run.

**Independent Test**: Full-mode output identifies phase timings and 20 slowest
scenarios, proves collection/outcome equality, and redacts URLs/credentials.

### Tests for User Story 3

- [X] T025 [P] [US3] Add metadata-only timing/accounting/redaction assertions in `apps/server/tests/contract/test_local_postgres_test_runner.py`.
- [X] T026 [P] [US3] Add failure and interrupt cleanup assertions for generated run prefixes in `apps/server/tests/contract/test_local_postgres_test_runner.py` and `apps/server/tests/integration/test_postgres_test_isolation.py`.

### Implementation for User Story 3

- [X] T027 [US3] Emit bounded phase timings, collection digest/count, outcome/skip/xfail counts, `--durations=20` data and cleanup result from `apps/server/scripts/run_local_postgres_tests.sh`.
- [X] T028 [US3] Update the user-facing current behaviour and canonical command in `CHANGELOG.md` and `specs/110-postgres-test-acceleration/quickstart.md` without recording raw logs, URLs or credentials.

**Checkpoint**: A full gate identifies both performance cost and safety failure
class in metadata-only output, and focused output cannot masquerade as full
evidence.

## Phase 6: Polish & Cross-Cutting Validation

- [X] T029 Verify the active PostgreSQL-only guard in `apps/server/tests/contract/test_postgres_only_contract.py` and ensure no SQLite dependency or compatibility path returns.
- [X] T030 Run `bash -n apps/server/scripts/run_local_postgres_tests.sh`, `cd apps/server && uv lock --check`, Ruff, Python compilation, RLS hardening validation and `docker compose -f infra/docker-compose.yml config`.
- [X] T031 Run full server evidence with workers 1, 4, 6 and 8 through `apps/server/scripts/run_local_postgres_tests.sh`; select the fastest stable default and record only safe aggregate measurements in `specs/110-postgres-test-acceleration/validation/local-postgres-test-pipeline.md`.
- [X] T032 Repeat the selected full server gate three times and run `infra/scripts/ci-local.sh`; record final timing/count/cleanup evidence in `specs/110-postgres-test-acceleration/validation/local-ci.md`.
- [X] T033 Run a Ponytail complexity review over `apps/server/scripts/run_local_postgres_tests.sh`, `apps/server/tests/fixtures/postgres_test_database.py`, `apps/server/tests/conftest.py` and `apps/server/tests/fixtures/postgres_rls.py`; record the conclusion in `specs/110-postgres-test-acceleration/validation/ponytail-review.md`.
- [ ] T034 Reconcile completed task evidence in `specs/110-postgres-test-acceleration/tasks.md` with the Feature 110 GitHub issues, remove confirmed obsolete test-pipeline compatibility aliases, and perform final code/Spec Kit review before integration.

## Dependencies & Execution Order

1. T001–T003 define the tests/dependency boundary.
2. T004–T009 establish the safe data, RLS and runner foundations; T010 proves
   them before story work.
3. User Story 1 (T011–T016) fixes the existing failures and can be delivered as
   the first trustworthy vertical slice.
4. User Story 2 (T017–T024) depends on the foundation and preserves US1 while
   accelerating the broad suite.
5. User Story 3 (T025–T028) depends on the runner phase model from US2.
6. T029–T034 close all stories with performance, repository and tracker proof.

## Parallel Opportunities

- T001–T003 affect independent contract/dependency/test files.
- After T004–T009, T011 and T012 can proceed in parallel; T013–T015 should be
  applied serially because they audit the same service boundary.
- T017–T019 cover distinct fixture/contract/RLS surfaces, but their
  implementation T020–T023 must be integrated in dependency order.
- T025 and T026 can be written independently after runner phase semantics are
  stable.

## Implementation Strategy

1. Deliver the safe fixture/running foundation and worker-context repair first.
2. Establish serial fast-reset correctness before enabling xdist.
3. Introduce worker-specific databases and the strict RLS lock, then prove the
   full phase union before making the parallel default.
4. Tune only with completed same-SHA runs; never trade a test/skip/RLS
   assertion for a lower duration.
5. Finish with three stable full gates, the repository gate, review and tracker
   evidence. No production deployment belongs to this slice.
