# Tasks: Надёжный RLS release gate

**Input**: Design documents from `/specs/167-rls-ci-runtime/`

**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `quickstart.md`

**Tests**: Required because this is a release-readiness boundary and the plan
selects the `release-deploy` validation lane.

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Reuse the existing server lockfile, RLS validator, disposable
PostgreSQL boundary, and release runner. No new dependency or service setup is
required.

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Preserve the existing fail-closed and metadata-only boundaries
before changing the runner invocation.

## Phase 3: User Story 1 - Выполнить полный release gate (Priority: P1) 🎯 MVP

**Goal**: The full gate reaches RLS validation with the project-managed runtime
and continues through the remaining release-only stages.

**Independent Test**: The contract test identifies the managed-runtime command,
and a full gate against a loopback disposable database reports RLS pass without
an import error.

### Tests for User Story 1

- [X] T001 [US1] Add a regression assertion for the project-managed RLS invocation in `apps/server/tests/contract/test_rls_production_boundary.py`.

### Implementation for User Story 1

- [X] T002 [US1] Run `verify_rls_hardening.py` from the server project with `PYTHONPATH=src uv run python` in `infra/scripts/ci-local.sh`, preserving the existing full-gate stage order.
- [X] T003 [P] [US1] Record the release-readiness runner fix in the `2026.08.18.2` Operations section of `CHANGELOG.md`.
- [X] T004 [US1] Run the focused RLS contract selection and the no-URL boundary scenario from `specs/167-rls-ci-runtime/quickstart.md`.

**Checkpoint**: The full gate can enter the RLS stage using declared server
dependencies, while no production probe behavior changes.

## Phase 4: User Story 2 - Сохранить безопасное блокирующее поведение (Priority: P1)

**Goal**: Missing or production database targets remain blocked before any
migration or destructive probe, and disposable resources are cleaned up.

**Independent Test**: Run the missing-URL and production-name scenarios, then
run the disposable pass path and verify the database and probe role are gone.

### Validation for User Story 2

- [X] T005 [US2] Run the missing-URL and `twobrain_rec` production-target scenarios from `apps/server/tests/contract/test_rls_production_boundary.py` and `specs/167-rls-ci-runtime/quickstart.md`.
- [X] T006 [US2] Run the disposable pass path from `specs/167-rls-ci-runtime/quickstart.md` with an explicit cleanup trap and verify no generated database or probe role remains in the local PostgreSQL cluster.

**Checkpoint**: The runtime fix does not weaken RLS or secret-safety guards.

## Phase 5: Polish & Cross-Cutting Concerns

**Purpose**: Validate the exact release candidate and retain only metadata-only
evidence.

- [ ] T007 Run `git diff --check` and `infra/scripts/scan-deployment-evidence.sh docs/deployments/2brain-rec` for the exact candidate commit.
- [ ] T008 Run `infra/scripts/ci-local.sh --full` once on the exact release-candidate SHA with the disposable RLS URL; record macOS, server, strict RLS, lint, compile, compose, and evidence results in `docs/deployments/2brain-rec/release-v2026.08.18.2.md`.
- [ ] T009 Run `infra/scripts/cd-remote.sh --dry-run --branch master` after the exact-SHA full gate and record the dry-run result in `docs/deployments/2brain-rec/release-v2026.08.18.2.md` without executing production deployment.

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: Existing project setup; no new dependency task.
- **Foundational (Phase 2)**: Existing safety boundaries remain prerequisites.
- **User Story 1 (Phase 3)**: T001 precedes T002; T003 may run in parallel with T001 because it touches a different file; T004 follows T002.
- **User Story 2 (Phase 4)**: T005 and T006 follow the runner fix and are independently verifiable; T006 owns disposable resource cleanup.
- **Polish (Phase 5)**: T007 follows implementation; T008 must run after all release metadata changes and is the authoritative exact-SHA full gate; T009 follows T008.

### User Story Dependencies

- **User Story 1 (P1)**: Independent; delivers the MVP runner fix.
- **User Story 2 (P1)**: Independent safety validation of existing boundaries; depends only on the shared runner and disposable PostgreSQL setup.

### Parallel Opportunities

- T001 and T003 can be prepared in parallel because they touch different files.
- T005 can be prepared while T004 is reviewed, but both execute after T002 and must not share a disposable database concurrently.

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Add the regression assertion (T001).
2. Change the runner invocation (T002).
3. Run focused checks (T004).
4. Validate the safety path (T005–T006).
5. Run the exact-SHA full gate before release dry-run (T007–T009).

No production deploy is part of this slice; production execution remains behind
the separate release approval gate.
