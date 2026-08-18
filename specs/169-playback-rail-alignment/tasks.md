# Tasks: Выравнивание нижнего playback относительно rail

**Input**: Design documents from `/specs/169-playback-rail-alignment/`

**Risk lane**: `high-risk-feature`; shared fixed playback UX. No audio semantics
or deploy changes.

## Phase 1: User Story 1 — Использовать всю ширину рабочего пространства (P1)

**Independent Test**: Static contract plus synthetic compact/expanded playback
matrix with unchanged currentTime/source.

- [ ] T001 [P] [US1] Add assertions for paired grid and playback inline-start
  selectors in `apps/server/tests/contract/test_cabinet_static_assets_contract.py`
- [ ] T002 [US1] Align the final collapsed/expanded playback origin with the
  active rail in `apps/server/src/twobrain_rec_server/cabinet/static/cabinet/cabinet.css`

## Phase 2: Review and validation

- [ ] T003 [US1] Run focused playback/rail checks, `node --check`,
  `git diff --check` and synthetic Browser/embedded degraded-state review; record
  evidence in `specs/169-playback-rail-alignment/quickstart.md`

## Dependencies & Execution Order

T001 precedes T002; T003 closes the story after code and contract checks.

## Implementation Strategy

One CSS state pair is the root-cause fix. Do not add JavaScript offset mutation
or a second playback wrapper.
