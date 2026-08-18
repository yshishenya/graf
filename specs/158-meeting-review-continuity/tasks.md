---
description: "Dependency-ordered implementation tasks for Meeting Review Continuity"
---

# Tasks: Meeting Review Continuity

**Input**: Design documents from `/specs/158-meeting-review-continuity/`

**Prerequisites**: `spec.md`, `plan.md`, `research.md`, `data-model.md`, `contracts/`, `quickstart.md`

**Risk lane**: `high-risk-feature`; focused checks, manual synthetic visual review, and `infra/scripts/ci-local.sh --fast` are required before slice closeout.

## Phase 1: Setup and guardrails

**Purpose**: Establish the exact shared paths and metadata-only validation boundary.

- [X] T001 Review `specs/158-meeting-review-continuity/spec.md`, `plan.md`, `research.md`, `data-model.md`, `contracts/meeting-review-continuity.md`, and `quickstart.md`; record the selected `high-risk-feature` lane and no-deploy gate in the implementation notes.
- [X] T002 [P] Add the slice's focused validation selectors and synthetic-only boundary to `specs/158-meeting-review-continuity/quickstart.md` and `CHANGELOG.md` without adding private meeting data.

## Phase 2: Foundational contract coverage

**Purpose**: Add regression checks before changing shared rendering or static behavior.

- [X] T003 Extend `apps/server/tests/unit/test_cabinet_web_shell.py` with synthetic speaker-count cases that distinguish one/fitting/overflowing/viewport-limited rows and assert the shared browser/embedded markup contract.
- [X] T004 Extend `apps/server/tests/contract/test_cabinet_static_assets_contract.py` with a Node harness for resize initialization, default/natural/viewport bounds, keyboard actions, and single-listener guards.
- [X] T005 Extend `apps/server/tests/contract/test_cabinet_static_assets_contract.py` with playing/paused rename success/failure cases that assert zero successful-path reloads, one audio element identity, monotonic/unchanged time, and retryable error state.
- [X] T006 Extend `apps/server/tests/contract/test_recording_workflow_accessibility.py` with requirements for the visible lane hint, action-oriented track names, semantic resize separator, sticky tab class, and source-target scroll margin.

## Phase 3: User Story 1 — Expand the speaker timeline (Priority: P1)

**Goal**: Let reviewers reveal complete speaker rows without losing playback context.

**Independent Test**: `T003` and `T004` pass for one, fitting, overflowing, and viewport-limited synthetic speaker sets in web and embedded markup.

### Implementation

- [X] T007 [US1] Update `apps/server/src/twobrain_rec_server/cabinet/rendering.py` to emit a shared timeline shell, stable timeline id, resize separator attributes, and no resize affordance when rows fit or interaction is unavailable.
- [X] T008 [US1] Implement bounded pointer and keyboard height behavior with one-time initialization and viewport re-clamping in `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js`, preserving the existing playback handlers.
- [X] T009 [US1] Add default-height, natural-height, viewport-ceiling, focus, cursor, and reduced-motion-safe styles for the timeline shell and separator in `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.css`.

## Phase 4: User Story 2 — Rename without interrupting playback (Priority: P1)

**Goal**: Apply confirmed speaker labels in place while preserving playing and paused review state.

**Independent Test**: `T005` passes for playing/paused success and failure in the shared web/embedded form path.

### Implementation

- [X] T010 [US2] Add stable `data-speaker-key` markers to timeline labels, manager rows, and rename forms in `apps/server/src/twobrain_rec_server/cabinet/rendering.py`.
- [X] T011 [US2] Replace the unconditional successful rename reload with canonical in-place label reconciliation, predictable focus, and existing session/access recovery handling in `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js`.
- [X] T012 [US2] Add label-update, error, focus, and no-media-replacement styling/semantics in `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.css` only where the existing shared form requires it.

## Phase 5: User Story 3 — Discover and use lane navigation (Priority: P1)

**Goal**: Make the existing lane-to-playback interaction understandable before the first click.

**Independent Test**: `T006` passes for available audio, unavailable audio, missing diarization, keyboard focus, narrow viewport, and reduced motion.

### Implementation

- [X] T013 [US3] Render the compact persistent lane interaction hint only for playable audio with interactive lanes and strengthen each track's accessible name in `apps/server/src/twobrain_rec_server/cabinet/rendering.py`.
- [X] T014 [US3] Preserve the existing Enter/Space seek behavior while adding pressed/focus state hooks and reduced-motion-safe hint initialization in `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js`.
- [X] T015 [US3] Style the hint, hover/focus/pressed lane states, and non-overlapping narrow layout in `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.css`.

## Phase 6: User Story 4 — Keep recording/results navigation visible (Priority: P1)

**Goal**: Keep the compact tab choice reachable while reading long review content.

**Independent Test**: `T006` and existing detail-tab tests pass for web/embedded layout, both hashes, keyboard navigation, source jumps, narrow viewport, and reduced motion.

### Implementation

- [X] T016 [US4] Add a single stable `meeting-detail-tabs` class to the existing tablist in `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/meeting_detail_content.html` without changing tab/hash semantics.
- [X] T017 [US4] Implement safe sticky tab styling, shell offset variable, focus-safe background, and scroll margins for transcript/outcome/source targets in `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.css`.
- [X] T018 [US4] Ensure partial HTMX updates reinitialize the shared tab/timeline behavior once and do not create duplicate strips or listeners in `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js`.

## Phase 7: Review and slice closeout

**Purpose**: Validate root cause, security/privacy boundaries, accessibility, brand distance, and release readiness.

- [X] T019 Run `node --check` and the focused isolated runner from `specs/158-meeting-review-continuity/quickstart.md`; fix any regression and add the smallest corresponding check in `apps/server/tests/`.
- [X] T020 Run correctness, security/privacy, UX/accessibility, and clean-room review against the changed files and `specs/158-meeting-review-continuity/contracts/meeting-review-continuity.md`; document no actionable findings or fix them before proceeding.
- [X] T021 Run the manual synthetic browser and native embedded visual matrix from `specs/158-meeting-review-continuity/quickstart.md` and record metadata-only evidence in the slice notes.
- [X] T022 Run `infra/scripts/ci-local.sh --fast`, reconcile all completed tasks and focused evidence in this `tasks.md`, and update `[Unreleased]` in `CHANGELOG.md` with the user-visible behavior.

## Dependencies and execution order

- `T001` and `T002` establish the lane/documentation boundary before implementation.
- `T003`–`T006` are test-first and must complete before `T007`–`T018`.
- `T007`–`T009` must complete before the resize visual matrix; `T010`–`T012` must complete before rename validation; `T013`–`T015` must complete before lane discoverability validation; `T016`–`T018` must complete before sticky navigation validation.
- `T019` depends on all implementation tasks and is the focused regression checkpoint.
- `T020` depends on `T019`; any actionable finding creates a fix task before `T021`.
- `T021` depends on clean focused checks; `T022` is the final slice gate.

## Parallel opportunities

- `T003` and `T006` can be prepared in parallel because they touch different test files.
- After test tasks pass, `T007`/`T009`, `T010`/`T012`, and `T013`/`T015` are file-overlapping pairs and must be applied sequentially within each shared path; do not parallelize edits to `rendering.py`, `cabinet.js`, or `cabinet.css`.
- The four user stories are intentionally executed sequentially because all share the same CSS/JS playback surface.

## Implementation strategy

Ship the smallest continuity increment first: bounded timeline and in-place
rename root-cause fixes, then add the lane hint and sticky tabs around the
existing behavior. Avoid persistence, new abstractions, new dependencies, or
unrelated cabinet cleanup. Mark a task `[X]` only after its implementation and
named validation evidence pass.

## Closeout evidence

- Risk lane: high-risk-feature; release gate: no deploy.
- Review found and fixed stale per-fragment viewport listeners; the focused
  Node harness now asserts one page-level resize listener after HTMX re-init.
- Correctness, privacy, accessibility, reduced-motion, and clean-room review
  found no remaining actionable issues in this slice.
- Focused and fast validation results are recorded in quickstart.md.
- T021 is complete: the browser and native synthetic availability, reduced-motion,
  narrow-viewport, keyboard, and ready-audio visual matrix passed on 2026-08-17.
