# Tasks: Ponytail Refactor Audit

**Input**: Design documents from `/specs/071-ponytail-refactor/`
**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/audit-batch-contract.md, quickstart.md
**Tests**: Required where tasks touch behavior, shared code, high-risk surfaces, dependencies, or scripts.

## Phase 1: Setup

- [X] T001 Record current worktree separation for unrelated `.specify/*`, `AGENTS.md`, and `.agents/*` changes in `specs/071-ponytail-refactor/research.md`.
- [X] T002 Confirm active feature context with `SPECIFY_FEATURE_DIRECTORY=specs/071-ponytail-refactor .specify/scripts/bash/check-prerequisites.sh --json --require-tasks --include-tasks`.
- [X] T003 Create a Batch A audit note for the existing server cleanup in `specs/071-ponytail-refactor/audit/batch-a-server-cleanup.md`.

## Phase 2: Foundational Audit

- [X] T004 [P] Generate Python dependency usage evidence for `apps/server/pyproject.toml` and `apps/server/uv.lock` in `specs/071-ponytail-refactor/audit/dependencies-python.md`.
- [X] T005 [P] Generate Swift package target evidence for `apps/macos/Package.swift` in `specs/071-ponytail-refactor/audit/dependencies-swift.md`.
- [X] T006 [P] Generate script and Docker runtime reference evidence for `infra/`, `scripts/`, and `.specify/scripts/` in `specs/071-ponytail-refactor/audit/dependencies-infra.md`.
- [X] T007 [P] Generate large-file and entrypoint inventory for `apps/server/`, `apps/macos/`, `infra/`, and `scripts/` in `specs/071-ponytail-refactor/audit/code-inventory.md`.
- [X] T008 Run baseline static checks from `specs/071-ponytail-refactor/quickstart.md` and record results in `specs/071-ponytail-refactor/audit/baseline-validation.md`.

## Phase 3: User Story 1 - Preserve A Safe Cleanup Baseline (P1)

**Goal**: Keep the existing validated cleanup as a reviewable batch.

**Independent Test**: Batch A has a complete audit note and its validation evidence matches the current diff.

- [X] T009 [US1] Document removed `structlog` dependency evidence in `specs/071-ponytail-refactor/audit/batch-a-server-cleanup.md`.
- [X] T010 [US1] Document removed internal parameters and local shrink changes in `specs/071-ponytail-refactor/audit/batch-a-server-cleanup.md`.
- [X] T011 [US1] Re-run Batch A focused tests from `specs/071-ponytail-refactor/quickstart.md` and append results to `specs/071-ponytail-refactor/audit/batch-a-server-cleanup.md`.
- [X] T012 [US1] Re-run `infra/scripts/ci-local.sh`, `cd apps/macos && swift test`, and `git diff --check`, then append results to `specs/071-ponytail-refactor/audit/batch-a-server-cleanup.md`.

## Phase 4: User Story 2 - Audit Dependencies And Dead Code Before Editing (P2)

**Goal**: Produce candidate lists with keep/remove decisions before any new cleanup patch.

**Independent Test**: Each candidate has caller evidence, runtime exception review, decision, and validation requirement.

- [X] T013 [P] [US2] Audit Python server candidates from Ruff/Vulture/import analysis in `specs/071-ponytail-refactor/audit/candidates-python.md`.
- [X] T014 [P] [US2] Audit cabinet presentation candidates, including `apps/server/src/twobrain_rec_server/cabinet/web.py`, in `specs/071-ponytail-refactor/audit/candidates-cabinet.md`.
- [X] T015 [P] [US2] Audit macOS Swift/C/C++ candidates in `specs/071-ponytail-refactor/audit/candidates-macos.md`.
- [X] T016 [P] [US2] Audit shell, JavaScript, Docker, and release script candidates in `specs/071-ponytail-refactor/audit/candidates-infra.md`.
- [X] T017 [US2] Consolidate retained high-risk candidates and reasons in `specs/071-ponytail-refactor/audit/retained-candidates.md`.

## Phase 5: User Story 3 - Execute Small Refactor Batches With Proof (P3)

**Goal**: Apply only candidate batches that are proven safe and independently validatable.

**Independent Test**: A batch is complete only when its audit note includes patch scope, validation, and retained-candidate decisions.

- [X] T018 [US3] Select the next smallest approved Python/server cleanup batch from `specs/071-ponytail-refactor/audit/candidates-python.md`.
- [X] T019 [US3] Apply the selected Python/server cleanup in the minimal touched files under `apps/server/`.
- [X] T020 [US3] Run focused server validation for the selected batch and record results in `specs/071-ponytail-refactor/audit/batch-b-server.md`.
- [X] T021 [US3] Run `infra/scripts/ci-local.sh` after the selected server cleanup and record the result in `specs/071-ponytail-refactor/audit/batch-b-server.md`.
- [X] T022 [US3] Record that no macOS cleanup batch is selected because `specs/071-ponytail-refactor/audit/candidates-macos.md` proves no safe deletion candidate.
- [X] T023 [US3] Leave `apps/macos/` source unchanged for this slice.
- [X] T024 [US3] Record that full `cd apps/macos && swift test` passed and no macOS patch-specific validation is required.

## Final Phase: Closeout

- [X] T025 Update `CHANGELOG.md` only if completed cleanup changes behavior, architecture, UX expectations, operations, release readiness, or dependency footprint.
- [X] T026 Run final `git diff --check`.
- [X] T027 Record final risk/validation lane, validation evidence, removed items, retained candidates, and no-deploy status in `specs/071-ponytail-refactor/audit/final-closeout.md`.

## Dependencies

- Phase 1 must complete before all other phases.
- Phase 2 must complete before selecting any new cleanup batch.
- US1 can complete before US2/US3 because Batch A already exists.
- US3 depends on candidate decisions from US2.

## Parallel Examples

- T004, T005, T006, and T007 can run in parallel because they write separate audit files.
- T013, T014, T015, and T016 can run in parallel after baseline validation because they write separate candidate files.

## Implementation Strategy

1. Preserve and prove Batch A.
2. Audit before editing.
3. Apply one minimal batch at a time.
4. Stop when evidence is insufficient.
