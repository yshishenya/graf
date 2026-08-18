# Tasks: Адаптивная высота таймлайна спикеров

**Input**: Design documents from `/specs/161-timeline-min-height/`

**Prerequisites**: spec.md, clarify.md, plan.md, research.md, data-model.md,
contracts/timeline-min-height.md, quickstart.md

**Risk lane**: `high-risk-feature`; shared meeting UX and accessibility surface.
No capture, auth, storage, AI or deploy changes.

## Historical closeout from the 120px baseline

- [X] T001 Read the original focused timeline quickstart and preserve its
  metadata-only validation boundary in `specs/161-timeline-min-height/quickstart.md`
- [X] T002 Update the server-rendered three-row baseline in
  `apps/server/src/twobrain_rec_server/cabinet/rendering.py`
- [X] T003 Align the original bounded resize minimum in
  `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js`
- [X] T004 Align the original CSS fallback baseline in
  `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.css`
- [X] T005 Update the original synthetic assertions in
  `apps/server/tests/unit/test_cabinet_web_shell.py` and
  `apps/server/tests/contract/test_cabinet_static_assets_contract.py`
- [X] T006 Run the original focused checks and review unchanged playback state
- [X] T007 Record the original `120px` closeout evidence

## Phase 1: User Story 1 — Видеть только нужную высоту (Priority: P1)

**Goal**: Natural height for 1–3 lanes and bounded expandable height for 4+.

**Independent Test**: Synthetic 1/2/3/4/12/40 lane renders plus Node harness
for fit, overflow, viewport and idempotent partial updates.

### Tests before implementation

- [ ] T008 [P] [US1] Extend the synthetic render assertions for 1/2/3 natural
  rows and 4+/12/40 bounded rows in
  `apps/server/tests/unit/test_cabinet_web_shell.py`
- [ ] T009 [P] [US1] Extend the Node resize harness for dynamic lower bounds,
  natural measurement and playback preservation in
  `apps/server/tests/contract/test_cabinet_static_assets_contract.py`

### Implementation

- [ ] T010 [US1] Measure natural timeline height while temporarily clearing the
  inline height and clamp the shared resize path in
  `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.js`
- [ ] T011 [US1] Replace the fixed CSS height with natural layout plus the safe
  three-row max-height fallback in
  `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.css`
- [ ] T012 [US1] Keep the server-rendered default/ARIA contract explicit for
  dynamic measurement in
  `apps/server/src/twobrain_rec_server/cabinet/rendering.py`

## Phase 2: Review and focused validation

- [ ] T013 [US1] Run the 161 quickstart, `node --check`, `git diff --check`,
  Browser/embedded synthetic visual review and record metadata-only evidence in
  `specs/161-timeline-min-height/quickstart.md` and `analysis.md`

## Dependencies & Execution Order

- T008 and T009 establish focused contracts and can be prepared in parallel;
  T010–T012 touch different layers but share the contract decision.
- T013 follows implementation and is the story closeout check.

## Issue mapping

Existing issues #5270–#5276 cover historical T001–T007. New issue sync must
create only the successor task IDs T008–T013 and must not duplicate those issues.

## Implementation Strategy

Reuse the existing `applyHeight` and one viewport listener. No observer,
storage, dependency or parallel layout abstraction is allowed.
