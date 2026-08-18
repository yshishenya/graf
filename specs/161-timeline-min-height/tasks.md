# Tasks: Минимальная высота таймлайна спикеров

**Input**: Design documents from `/specs/161-timeline-min-height/`

## Phase 1: Setup

- [X] T001 Read `specs/161-timeline-min-height/quickstart.md` and confirm the focused validation commands

## Phase 2: User Story 1 - Сразу видеть трёх спикеров (Priority: P1)

**Goal**: Базовый размер панели показывает три полные дорожки и сохраняет
bounded resize.

**Independent Test**: Synthetic 1/3/4/12/40-speaker render plus focused
pytest and Node harness checks.

- [X] T002 [P] [US1] Update the shared timeline minimum in `apps/server/src/twobrain_rec_server/cabinet/rendering.py`
- [X] T003 [P] [US1] Align default height and bounded keyboard/pointer resize in `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js`
- [X] T004 [P] [US1] Align the initial timeline height in `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.css`
- [X] T005 [US1] Update the synthetic timeline assertions and Node harness expectations in `apps/server/tests/unit/test_cabinet_web_shell.py` and `apps/server/tests/contract/test_cabinet_static_assets_contract.py`
- [X] T006 [US1] Run the focused quickstart checks and review the diff for unchanged playback/viewport behavior

## Dependencies & Execution Order

- T001 precedes all implementation tasks.
- T002, T003 and T004 can be edited in parallel because they touch separate
  layers; T005 follows their contract choice; T006 closes the story.

## Implementation Strategy

Deliver the single shared minimum first, then run the existing bounded resize
harness. Do not add storage, new abstractions or a new test framework.

## Final Validation

- [X] T007 Record the selected `high-risk-feature` lane and focused evidence in `specs/161-timeline-min-height/quickstart.md`
