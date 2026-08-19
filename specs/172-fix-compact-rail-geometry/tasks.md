# Tasks: Цельная геометрия compact rail

**Input**: Design documents from `/specs/172-fix-compact-rail-geometry/`

**Risk lane**: `high-risk-feature`; shared responsive navigation UX,
accessibility and brand-distance. No capture, auth, data, permissions or deploy.

## Phase 1: Historical baseline

**Purpose**: Lock the proven root cause and selected minimum design before code.

- [X] T001 Record the measured current geometry, historical good SHAs and rejected alternatives in `specs/172-fix-compact-rail-geometry/research.md`

## Phase 2: Foundational regression contract

**Purpose**: Make the exact 64/52/40 cascade regression fail before CSS changes.

- [X] T002 Extend the compact rail source contract for one complete 40×40 collapsed geometry owner and no competing 52×36 active item in `apps/server/tests/contract/test_cabinet_static_assets_contract.py`

## Phase 3: User Story 1 — Видеть ровную компактную навигацию (P1)

**Goal**: Toggle, navigation, active/hover/focus states and profile share one
axis and one compact square at every supported width and surface.

**Independent Test**: Focused contracts pass; computed wide/narrow and
web/embedded bounds share center `x=32±1px` and size 40×40px.

- [X] T003 [US1] Make the final JS-ready collapsed state the complete compact geometry owner and remove/narrow conflicting embedded dimensions in `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.css`
- [X] T004 [US1] Run focused rail/server-shell checks and record exact results in `specs/172-fix-compact-rail-geometry/quickstart.md`

## Phase 4: Review and closeout

**Purpose**: Prove root-cause correction visually and leave one clean commit.

- [X] T005 [P] Update the Russian `[Unreleased]` user-facing entry in `CHANGELOG.md`
- [X] T006 Perform correctness, UX/accessibility and Ponytail reviews; resolve actionable findings and record them in `specs/172-fix-compact-rail-geometry/analysis.md`
- [X] T007 Complete the in-app Browser and `GRAF Dev` Computer Use visual matrix from `specs/172-fix-compact-rail-geometry/quickstart.md`
- [X] T008 Run `infra/scripts/ci-local.sh --fast` once, synchronize tasks/issues, record final evidence in `specs/172-fix-compact-rail-geometry/quickstart.md`, and create the validated implementation commit

## Dependencies & Execution Order

- T001 is complete before implementation and establishes the selected model.
- T002 must fail on the current regression before T003.
- T003 precedes T004 and all visual/review work.
- T005 may run in parallel with focused checks after behavior is final.
- T006, T007 and T008 are ordered closeout gates.

## Parallel Opportunities

- Only T005 is safely parallel after implementation. The CSS, its contract and
  visual evidence intentionally remain sequential to avoid judging stale assets.

## Issue mapping

Task IDs remain the source of truth. No issue may close before its evidence is
recorded.

| Task | GitHub issue |
|---|---|
| T001 | #5355 |
| T002 | #5357 |
| T003 | #5356 |
| T004 | #5358 |
| T005 | #5359 |
| T006 | #5360 |
| T007 | #5361 |
| T008 | #5362 |

## Implementation Strategy

One independently testable P1 story is the complete MVP. T003 should be a
deletion/narrowing diff in the existing CSS owner, not a new override layer.
Focused checks run during development; the repository fast gate runs once.
