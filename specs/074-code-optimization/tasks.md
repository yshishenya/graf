# Tasks: Code Optimization

**Input**: Design documents from `/specs/074-code-optimization/`

**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`,
`contracts/`, `quickstart.md`, `audit-candidates.md`

**Tests**: Required. This is a significant/high-risk cleanup slice because
removing runtime code can break implicit product contracts.

## Phase 1: Evidence Baseline

**Purpose**: Prove the cleanup target before deleting code.

- [X] T001 Record runtime LOC baseline, zero-reference scan, and first-batch classifications in `specs/074-code-optimization/audit-candidates.md`.

## Phase 2: First Deletion Batch (User Story 1, Priority: P1)

**Goal**: Remove only server private helpers with zero references and focused
validation coverage.

**Independent Test**: Removed helper names no longer exist, imports still compile,
and focused tests for touched surfaces pass.

- [X] T002 [US1] Delete `_event_has_meeting_link_or_location`, `_load_current_available_set`, and `_first_response_item` from `apps/server/src/twobrain_rec_server/cabinet/view_models.py`, `apps/server/src/twobrain_rec_server/outcomes/service.py`, and `apps/server/src/twobrain_rec_server/auth/providers/base.py`.
- [X] T003 [US1] Run `rg -n "_event_has_meeting_link_or_location|_load_current_available_set|_first_response_item" apps/server/src apps/server/tests apps/macos infra scripts` and confirm there are no matches.

## Phase 3: Validation (User Story 2, Priority: P1)

**Goal**: Prove deletion did not weaken product behavior.

**Independent Test**: Focused tests and repository gate pass without weakening
assertions.

- [X] T004 [US2] Run focused server tests for cabinet, outcomes, and auth provider paths.
- [X] T005 [US2] Run `uv --project apps/server run --extra dev ruff check`, `python3 -m compileall -q`, and `git diff --check` for the touched Python files.
- [X] T006 [US2] Run `infra/scripts/ci-local.sh` before closeout because runtime code changed.

## Phase 4: Closeout (User Story 3, Priority: P2)

**Goal**: Report actual product optimization, not document churn.

- [X] T007 [US3] Update `CHANGELOG.md` and report runtime LOC delta separately from Spec Kit/docs delta.
- [X] T008 [US3] Run a Ponytail review pass over the diff, remove extra complexity if found, and mark completed tasks `[X]` only after validation evidence exists.

## Dependencies And Execution Order

- T001 blocks deletion.
- T002-T003 block validation.
- T004-T006 block closeout.
- T007-T008 are last.

## Implementation Strategy

1. Keep the first batch intentionally tiny.
2. Delete only the three zero-reference helpers.
3. Validate focused paths first.
4. Run full local CI.
5. Stop; do not expand into Swift, dependency, or large-file cleanup in this PR.
