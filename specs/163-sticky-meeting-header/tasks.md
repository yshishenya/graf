# Tasks: Закреплённый верхний блок встречи

**Input**: Design documents from `/specs/163-sticky-meeting-header/`

## Phase 1: Setup

- [X] T001 Read `specs/163-sticky-meeting-header/quickstart.md` and confirm the scroll/keyboard validation matrix

## Phase 2: User Story 1 - Не терять контекст встречи (Priority: P1)

**Goal**: Title, metadata, actions and tabs remain one readable sticky block.

**Independent Test**: Synthetic detail render with long transcript/outcomes,
wide/narrow and embedded states; focused template/CSS/accessibility checks.

- [X] T002 [P] [US1] Wrap the meeting topline, share host and tabs in `apps/server/src/twobrain_rec_server/cabinet/templates/cabinet/pages/meeting_detail_content.html`
- [X] T003 [P] [US1] Replace the independent tabs sticky rule with one responsive header sticky rule in `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.css`
- [X] T004 [US1] Add wrapper, one-tablist and scroll-margin assertions in `apps/server/tests/unit/test_cabinet_web_shell.py` and `apps/server/tests/contract/test_recording_workflow_accessibility.py`
- [X] T005 [US1] Run focused checks and synthetic wide/narrow/embedded scroll review
- [ ] T006 Record implementation SHA and metadata-only evidence in `specs/163-sticky-meeting-header/quickstart.md`

## Dependencies & Execution Order

- T001 precedes the story.
- T002 and T003 can be edited in parallel; T004 follows their contract.
- T005 and T006 close validation.

## Implementation Strategy

Use one wrapper and native CSS sticky. Do not add a scroll event manager or
duplicate title bar.
