# Tasks: Desktop Upload Custody Architecture

**Input**: Design documents from `/specs/086-desktop-upload-custody-architecture/`

**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`,
`contracts/`, `quickstart.md`

**Tests**: 086 is a significant architecture / high-risk read-only audit.
Tests are artifact validation and consistency checks in this stage. Runtime
tests are listed as gates for later refactor batches.

**Organization**: Tasks are grouped by user story and keep product/runtime code
read-only in stage one.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel because it touches different audit docs.
- **[Story]**: Which user story supports the task.
- Every task includes exact repository paths.

## Phase 1: Setup And Guardrails

**Purpose**: Anchor the slice and prevent accidental implementation work.

- [X] T001 Record the selected lane as significant architecture / high-risk read-only audit in `specs/086-desktop-upload-custody-architecture/plan.md`.
- [X] T002 Confirm 086 is anchored from a clean worktree based on fresh `origin/master` and record the decision in `specs/086-desktop-upload-custody-architecture/audit/upload-custody-map.md`.
- [X] T003 Keep all 086 stage-one deliverables under `specs/086-desktop-upload-custody-architecture/` except the managed `AGENTS.md` Spec Kit pointer.
- [X] T004 Ensure `specs/086-desktop-upload-custody-architecture/quickstart.md` states no production deploy and no product/runtime code changes for stage one.

## Phase 2: Foundational Contracts

**Purpose**: Define evidence contracts before interpreting refactor risk.

- [X] T005 [P] Define upload custody flow contract in `specs/086-desktop-upload-custody-architecture/contracts/upload-custody-boundary-contract.md`.
- [X] T006 [P] Define refactor batch contract in `specs/086-desktop-upload-custody-architecture/contracts/refactor-batch-contract.md`.
- [X] T007 [P] Define metadata-only evidence contract in `specs/086-desktop-upload-custody-architecture/contracts/evidence-safety-contract.md`.
- [X] T008 Model audit entities and relationships in `specs/086-desktop-upload-custody-architecture/data-model.md`.

## Phase 3: User Story 1 - See The Upload Custody Flow (Priority: P1)

**Goal**: Build a repository-backed map of the desktop upload custody flow.

**Independent Test**: A reviewer can follow `quickstart.md`, inspect
`audit/upload-custody-map.md`, and verify that each required flow stage is
represented without changing runtime code.

- [X] T009 [P] Capture local package to queue responsibilities in `specs/086-desktop-upload-custody-architecture/audit/upload-custody-map.md`.
- [X] T010 [P] Capture queue to server upload/ingest responsibilities in `specs/086-desktop-upload-custody-architecture/audit/upload-custody-map.md`.
- [X] T011 [P] Capture custody projection and review-readiness responsibilities in `specs/086-desktop-upload-custody-architecture/audit/upload-custody-map.md`.
- [X] T012 [P] Capture deletion/local purge responsibilities in `specs/086-desktop-upload-custody-architecture/audit/upload-custody-map.md`.
- [X] T013 [P] Capture support incident evidence responsibilities in `specs/086-desktop-upload-custody-architecture/audit/upload-custody-map.md`.

## Phase 4: User Story 2 - Decide What To Split Or Keep (Priority: P1)

**Goal**: Classify upload-custody findings conservatively before code changes.

**Independent Test**: Every roadmap item in
`audit/refactor-roadmap.md` has classification, scope, risk, and validation.

- [X] T014 [US2] Record the current zero-delete result in `specs/086-desktop-upload-custody-architecture/audit/upload-custody-map.md`.
- [X] T015 [US2] Classify split-soon queue, transport, custody projection, and support payload batches in `specs/086-desktop-upload-custody-architecture/audit/refactor-roadmap.md`.
- [X] T016 [US2] Classify local purge acknowledgement and delete-proof sweep as risky/spec-gated in `specs/086-desktop-upload-custody-architecture/audit/refactor-roadmap.md`.
- [X] T017 [US2] Verify each classification follows `specs/086-desktop-upload-custody-architecture/contracts/refactor-batch-contract.md`.

## Phase 5: User Story 3 - Prepare Small Safe Refactor Batches (Priority: P1)

**Goal**: Convert the map into small future PR batches.

**Independent Test**: Each batch has a goal, included/excluded scope, expected
diff shape, validation gates, and stop condition.

- [X] T018 [P] [US3] Define queue persistence/package discovery batch in `specs/086-desktop-upload-custody-architecture/audit/refactor-roadmap.md`.
- [X] T019 [P] [US3] Define upload transport/DTO boundary batch in `specs/086-desktop-upload-custody-architecture/audit/refactor-roadmap.md`.
- [X] T020 [P] [US3] Define custody projection/user copy batch in `specs/086-desktop-upload-custody-architecture/audit/refactor-roadmap.md`.
- [X] T021 [P] [US3] Define local purge acknowledgement boundary batch in `specs/086-desktop-upload-custody-architecture/audit/refactor-roadmap.md`.
- [X] T022 [P] [US3] Define support incident payload boundary batch in `specs/086-desktop-upload-custody-architecture/audit/refactor-roadmap.md`.
- [X] T023 [P] [US3] Define delete-proof sweep batch in `specs/086-desktop-upload-custody-architecture/audit/refactor-roadmap.md`.

## Phase 6: Validation And Analyze

**Purpose**: Validate 086 artifacts as a read-only architecture package.

- [X] T024 Run the placeholder scan from `specs/086-desktop-upload-custody-architecture/quickstart.md` and resolve any template leftovers.
- [X] T025 Run `.specify/scripts/bash/check-prerequisites.sh --json --require-tasks --include-tasks` for the 086 feature directory.
- [X] T026 Run `$speckit-analyze` consistency review across `spec.md`, `plan.md`, `tasks.md`, and supporting docs.
- [X] T027 Confirm final answer states the selected lane, no code/deploy/delete actions, and the five plain-language audit answers.

## Dependencies And Execution Order

- Phase 1 blocks all other work.
- Phase 2 blocks roadmap classification.
- Phase 3 can run in parallel by flow stage after Phase 2.
- Phase 4 depends on Phase 3 evidence.
- Phase 5 depends on Phase 4 classifications.
- Phase 6 is last.

## Parallel Opportunities

- T005-T007 can run in parallel.
- T009-T013 can run in parallel by flow stage.
- T018-T023 can run in parallel by roadmap batch.

## Implementation Strategy

1. Keep 086 stage one read-only for product/runtime code.
2. Map the real upload custody flow before proposing split PRs.
3. Classify conservatively: low reference count is not deletion proof.
4. Convert only proven boundaries into small future PR batches.
5. Move behavior changes into separate Spec Kit slices.
6. Run analyze before calling the architecture package complete.
