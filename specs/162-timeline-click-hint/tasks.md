# Tasks: Понятная подсказка на таймлайне

**Input**: Design documents from `/specs/162-timeline-click-hint/`

## Phase 1: Setup

- [X] T001 Read `specs/162-timeline-click-hint/quickstart.md` and confirm the focused hint/accessibility matrix

## Phase 2: User Story 1 - Понять действие без обучения (Priority: P1)

**Goal**: One short inline action/result hint explains the clickable colored
segment without adding a new interaction layer.

**Independent Test**: Synthetic playable/unavailable render at wide and narrow
widths; focused rendering/accessibility tests and node syntax check.

- [X] T002 [P] [US1] Replace the timeline hint copy in `apps/server/src/twobrain_rec_server/cabinet/rendering.py`
- [X] T003 [P] [US1] Add minimal wrapping/secondary presentation rules in `apps/server/src/twobrain_rec_server/cabinet/static/cabinet.css`
- [X] T004 [US1] Update hint count/copy/accessibility assertions in `apps/server/tests/unit/test_cabinet_web_shell.py` and `apps/server/tests/contract/test_recording_workflow_accessibility.py`
- [X] T005 [US1] Run the focused quickstart and review wide/narrow synthetic behavior
- [ ] T006 Record implementation SHA and metadata-only validation in `specs/162-timeline-click-hint/quickstart.md`

## Dependencies & Execution Order

- T001 precedes the story.
- T002 and T003 touch separate layers and can be edited in parallel.
- T004 follows the contract wording; T005 and T006 close validation.

## Implementation Strategy

Use existing markup and styles. Do not add tooltip code, local storage,
analytics or a new icon dependency.
