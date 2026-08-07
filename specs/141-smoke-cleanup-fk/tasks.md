# Tasks: Надёжная очистка production smoke-данных (Feature 141)

**Input**: Design documents from `specs/141-smoke-cleanup-fk/`

**Prerequisites**: `spec.md`, `plan.md`, `research.md`, `data-model.md`, `quickstart.md`, `checklists/requirements.md`, `checklists/infra.md`

## Phase 1: Setup

- [X] T001 Update the active Spec Kit plan reference in `AGENTS.md` and record the Feature 141 cleanup scope in `CHANGELOG.md`.

## Phase 2: Foundational tests

- [X] T002 [P] [US1] Add a regression assertion in `apps/server/tests/unit/test_smoke_cleanup.py` that revision-linked dependency cleanup is expressed by media revision ownership as well as meeting ownership.
- [X] T003 [P] [US2] Extend `apps/server/tests/integration/test_rls_postgres_policies.py` with a disposable Postgres scenario covering revision-linked cleanup and idempotent rerun without residue.

## Phase 3: User Story 1 - Успешный smoke deploy

**Goal**: Remove revision-linked child rows before their media revisions without weakening smoke identity boundaries.

**Independent Test**: The focused disposable Postgres smoke cleanup scenario completes with no FK exception, empty residue, and a successful second run.

- [X] T004 [US1] Update `apps/server/scripts/cleanup_smoke_artifacts.py` so child rows with `media_revision_id` are deleted when they belong to the discovered smoke meeting or one of its media revisions, before deleting `media_revisions`.
- [X] T005 [US1] Preserve available-table guards, maintenance/request tenant contexts, transaction behavior, storage-prefix cleanup, and residue evidence in `apps/server/scripts/cleanup_smoke_artifacts.py`.

## Phase 4: User Story 2 - Безопасный повторный cleanup

**Goal**: Keep cleanup scoped and idempotent for retries and rollback paths.

**Independent Test**: A second cleanup for the same run returns zero new database/object removals and no residue while unrelated identity rows remain untouched.

- [X] T006 [US2] Verify and, if needed, adjust the residue assertions in `apps/server/tests/integration/test_rls_postgres_policies.py` so revision-linked rows and unrelated smoke identities are both covered.
- [X] T007 [US2] Run the feature quickstart focused commands from `specs/141-smoke-cleanup-fk/quickstart.md` and resolve any cleanup regression failures.

## Phase 5: Polish and release validation

- [X] T008 Run `git diff --check` and `infra/scripts/ci-local.sh` from the clean Feature 141 worktree; record pass evidence without secrets in `CHANGELOG.md` if behavior changed.
- [ ] T009 Run `infra/scripts/cd-remote.sh --dry-run --branch master`, then execute the pinned release deploy with `infra/scripts/cd-remote.sh --execute --branch master`; require backup, restore rehearsal, health, smoke cleanup, and rollback evidence before release completion.
- [ ] T010 Prepare and publish the next CalVer GitHub Release only after deploy reports `deploy_result=pass`, including Russian notes, validation evidence, compatibility/no migration, issue/PR links, and known limitations.

## Dependencies and Execution Order

- T001 precedes all other tasks.
- T002 and T003 are parallel test preparation tasks.
- T004 and T005 depend on T002/T003 and must complete before T006/T007.
- T008 depends on all implementation and focused validation tasks.
- T009 depends on T008 and explicit release approval already granted by the user.
- T010 depends on T009 reporting a successful deploy and smoke.

## Parallel Opportunities

- T002 and T003 touch different test surfaces and can be prepared in parallel.
- T004 is the only production cleanup implementation task; T005 is a same-file safety review and follows it sequentially.

## Implementation Strategy

1. Add the regression coverage that captures the observed FK failure boundary.
2. Make the smallest predicate/order fix in the existing cleanup script.
3. Run focused tests, then the canonical full CI.
4. Rerun the gated production deploy; publish a release only after green smoke.
