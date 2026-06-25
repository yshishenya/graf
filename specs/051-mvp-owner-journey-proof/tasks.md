# Tasks: MVP Owner Journey Proof

**Input**: Design documents from `specs/051-mvp-owner-journey-proof/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/](./contracts/), [quickstart.md](./quickstart.md)

**Tests**: Tests are required. This slice gates live MVP proof, production truth, privacy-safe evidence, and web/macOS interface quality.

**Organization**: Tasks are grouped by independently testable user story. Do not mark a task `[X]` until direct evidence exists.

## Phase 1: Setup And Governance

**Purpose**: Lock the active 051 context, evidence locations, and product truth boundaries.

- [X] T001 Create metadata-safe validation log in `specs/051-mvp-owner-journey-proof/evidence/validation-log.md`
- [X] T002 [P] Record branch/master baseline, dirty-worktree boundary, and Ponytail minimum-scope rule in `specs/051-mvp-owner-journey-proof/evidence/validation-log.md`
- [X] T003 [P] Update `AGENTS.md` Spec Kit pointer to `specs/051-mvp-owner-journey-proof/plan.md`
- [X] T004 [P] Add simple Russian `[Unreleased]` changelog entry for 051 MVP owner journey proof in `CHANGELOG.md`
- [X] T005 Run `SPECIFY_FEATURE_DIRECTORY=specs/051-mvp-owner-journey-proof .specify/scripts/bash/check-prerequisites.sh --json --require-tasks --include-tasks` and record the metadata-only result in `specs/051-mvp-owner-journey-proof/evidence/validation-log.md`
- [X] T006 Run checklist status validation for `specs/051-mvp-owner-journey-proof/checklists/*.md` and record the result in `specs/051-mvp-owner-journey-proof/evidence/validation-log.md`

---

## Phase 2: Foundational Contracts And Harnesses

**Purpose**: Define machine-checkable 051 proof expectations before changing product behavior.

- [X] T007 [P] Add 051 owner journey readiness contract tests in `apps/server/tests/contract/test_mvp_owner_journey_proof_contract.py`
- [X] T008 [P] Add 051 readiness claim rule tests in `apps/server/tests/unit/test_mvp_owner_journey_readiness.py`
- [X] T009 [P] Add current product status regression for 050/051 truth in `apps/server/tests/integration/test_mvp_launch_status_truth.py`
- [X] T010 [P] Add metadata-only production owner journey probe in `specs/051-mvp-owner-journey-proof/evidence/production-owner-journey-probe.py`
- [X] T011 [P] Add 051 browser runtime verifier by reusing the 050 verifier pattern in `specs/051-mvp-owner-journey-proof/evidence/browser-runtime-check.cjs`
- [X] T012 Add 051 readiness/evidence support in `apps/server/src/twobrain_rec_server/readiness/matrix.py` and `apps/server/src/twobrain_rec_server/readiness/report.py`
- [X] T013 Add 051 closeout and timing report templates in `specs/051-mvp-owner-journey-proof/evidence/mvp-closeout-report.md` and `specs/051-mvp-owner-journey-proof/evidence/timing-proof.md`
- [X] T014 Run foundational focused tests and record RED/GREEN results in `specs/051-mvp-owner-journey-proof/evidence/validation-log.md`

**Checkpoint**: 051 can evaluate owner journey proof and readiness claims without live private content.

---

## Phase 2A: Pre-Implementation Spec Kit Gates

**Purpose**: Run the required consistency and tracker gates before implementation.

- [X] T015 Run read-only Spec Kit analyze pass across `specs/051-mvp-owner-journey-proof/spec.md`, `specs/051-mvp-owner-journey-proof/plan.md`, and `specs/051-mvp-owner-journey-proof/tasks.md`, then record blocker-free result in `specs/051-mvp-owner-journey-proof/evidence/validation-log.md`
- [X] T016 Run `$speckit-taskstoissues`, create/update issue mapping in `specs/051-mvp-owner-journey-proof/issues.md`, and record GitHub issue canon validation in `specs/051-mvp-owner-journey-proof/evidence/validation-log.md`

---

## Phase 3: User Story 1 - Prove The Fresh Owner Journey (Priority: P1)

**Goal**: Current installed app and production server have direct evidence for record/upload/process/review, or the exact blocking gate is visible.

**Independent Test**: A metadata-safe journey gate table shows pass/fail/blocked/unproven for installed app, record/stop/upload, finalization, processing, transcript/diarization, playback, stored outcomes, embedded parity, timing, and forbidden-content scan.

- [X] T017 [US1] Verify `/Applications/2brain Rec.app` version, launch/codesign state, and active recording safety; record result in `specs/051-mvp-owner-journey-proof/evidence/installed-app-check.md`
- [X] T018 [US1] Run production health/deployed SHA checks and record release/deploy truth in `specs/051-mvp-owner-journey-proof/evidence/validation-log.md`
- [X] T019 [US1] Run or collect a fresh installed-app record/stop/upload-to-review journey and record metadata-only gate states in `specs/051-mvp-owner-journey-proof/evidence/mvp-closeout-report.md`
- [X] T020 [US1] If any owner journey gate fails or is unproven, add the exact P1 launch gap and next action to `docs/evidence/051-mvp-owner-journey-proof/launch-gap-register.md`

**Checkpoint**: Owner journey readiness is proven or explicitly blocked; no assumed P1 gate remains.

---

## Phase 4: User Story 2 - Prove Stored Outcomes On Production (Priority: P1)

**Goal**: Production candidate has stored outcome category states and counts, or the missing-outcomes blocker stays visible.

**Independent Test**: Production owner journey probe and web/embedded review show outcome availability or truthful category states without committing private generated text.

- [X] T021 [P] [US2] Extend outcome/readiness tests for production category states in `apps/server/tests/integration/test_mvp_loop_readiness_report.py`
- [X] T022 [US2] Run production outcome proof through `specs/051-mvp-owner-journey-proof/evidence/production-owner-journey-probe.py` and record metadata-only counts/states in `specs/051-mvp-owner-journey-proof/evidence/mvp-closeout-report.md`
- [X] T023 [US2] Fix any discovered normal-path outcome generation/import blocker in `apps/server/src/twobrain_rec_server/outcomes/` or `apps/server/src/twobrain_rec_server/processing/`
- [X] T024 [US2] Re-run focused outcome/cabinet tests and record results in `specs/051-mvp-owner-journey-proof/evidence/validation-log.md`

**Checkpoint**: Stored outcomes are proven on production or remain a named P1 blocker.

---

## Phase 5: User Story 3 - Prove Processing Speed (Priority: P1)

**Goal**: Representative timing is measured against the three-minute-per-hour target, or the timing gate remains honestly unproven/failed.

**Independent Test**: Timing report separates audio duration, raw processing, provider processing, queue/wait, finalize-to-review, and target result.

- [X] T025 [P] [US3] Add timing proof unit tests in `apps/server/tests/unit/test_mvp_owner_journey_readiness.py`
- [X] T026 [US3] Record representative production timing evidence in `specs/051-mvp-owner-journey-proof/evidence/timing-proof.md`
- [X] T027 [US3] If timing cannot be proven from a representative recording, keep the target `unproven` in `docs/evidence/051-mvp-owner-journey-proof/launch-gap-register.md`

**Checkpoint**: Timing target is pass/fail/unproven with direct evidence, never extrapolated from a short run.

---

## Phase 6: User Story 4 - Verify Web And macOS Review Interface Quality (Priority: P1)

**Goal**: Web cabinet, embedded macOS review, mobile-width review, and native shell are readable, truthful, and aligned with accepted playback/outcome UX.

**Independent Test**: Browser/runtime and macOS checks show no P1 overlap, stale active tabs, hidden native capture truth, false green cabinet state, or web/embedded contradiction.

- [X] T028 [P] [US4] Extend web-shell tests for 051 owner review quality in `apps/server/tests/unit/test_cabinet_web_shell.py`
- [X] T029 [P] [US4] Extend macOS cabinet truth tests in `apps/macos/Shared/Tests/DesktopCabinetWorkspaceTests.swift`
- [X] T030 [US4] Run 051 browser runtime verifier and record `failures=[]` or findings in `specs/051-mvp-owner-journey-proof/evidence/validation-log.md`
- [X] T031 [US4] Fix any discovered web cabinet layout/truth gap in `apps/server/src/twobrain_rec_server/cabinet/web.py`, `apps/server/src/twobrain_rec_server/api/cabinet.py`, or `apps/server/src/twobrain_rec_server/cabinet/view_models.py`
- [X] T032 [US4] Fix any discovered native macOS cabinet truth gap in `apps/macos/RecApp/Sources` or `apps/macos/Shared/Sources`
- [X] T033 [US4] Re-run browser runtime verifier and focused macOS cabinet tests, then record evidence in `specs/051-mvp-owner-journey-proof/evidence/validation-log.md`

**Checkpoint**: MVP review interface is validated or has explicit P1 findings.

---

## Phase 7: User Story 5 - Publish Truthful MVP Readiness Decision (Priority: P2)

**Goal**: The final 051 output states one allowed claim with evidence and no hidden blockers.

**Independent Test**: The closeout report can be audited gate-by-gate and matches status docs, readiness report, launch gaps, validation log, and release notes.

- [X] T034 [US5] Generate `docs/evidence/051-mvp-owner-journey-proof/readiness-report.md`, `docs/evidence/051-mvp-owner-journey-proof/readiness-report.json`, and `docs/evidence/051-mvp-owner-journey-proof/launch-gap-register.md`
- [X] T035 [US5] Update `docs/current-product-status.md` with 051 outcome and remaining P1/P2 boundaries
- [X] T036 [US5] Compute final P1 gate summary in `specs/051-mvp-owner-journey-proof/evidence/mvp-closeout-report.md`
- [X] T037 [US5] Update `CHANGELOG.md` with final 051 outcome in simple Russian
- [X] T038 [US5] Run forbidden-content scan from `specs/051-mvp-owner-journey-proof/quickstart.md`
- [X] T039 [US5] Reconcile every task checkbox with direct evidence and leave unverified tasks open in `specs/051-mvp-owner-journey-proof/tasks.md`

---

## Phase 8: Final Validation, PR, Release, Deploy

**Purpose**: Close the slice only after implementation, UI proof, and production gates.

- [X] T040 Run all focused commands from `specs/051-mvp-owner-journey-proof/quickstart.md` and record results in `specs/051-mvp-owner-journey-proof/evidence/validation-log.md`
- [X] T041 Run full `infra/scripts/ci-local.sh` and record `ci_local_result` in `specs/051-mvp-owner-journey-proof/evidence/validation-log.md`
- [X] T042 Run `infra/scripts/cd-remote.sh --dry-run` and record deploy-readiness evidence in `specs/051-mvp-owner-journey-proof/evidence/validation-log.md`
- [X] T043 Run a Ponytail over-engineering pass over the final diff and remove avoidable new abstractions before PR; record result in `specs/051-mvp-owner-journey-proof/evidence/validation-log.md`
- [X] T044 Prepare PR description and release notes draft in simple Russian in `specs/051-mvp-owner-journey-proof/evidence/pr-draft.md`
- [ ] T045 After merge/release gate, run release and production deploy, then record deployed SHA and public health in `specs/051-mvp-owner-journey-proof/evidence/validation-log.md`

---

## Dependencies & Execution Order

- Phase 1 must complete before all other phases.
- Phase 2 blocks implementation because it defines 051 readiness contracts and harnesses.
- Phase 2A must pass before user story implementation.
- US1 can run after Phase 2A; US2 and US3 use US1's candidate when available.
- US4 can run after Phase 2A and must be re-run after any web/macOS fixes.
- US5 depends on US1-US4 evidence.
- Phase 8 depends on all selected tasks and P1 gates being reconciled.

## Parallel Opportunities

- T002-T004 can run in parallel after T001.
- T007-T011 can run in parallel.
- T021 and T025 can run in parallel after Phase 2A.
- T028-T029 can run in parallel.

## Implementation Strategy

1. Reuse 050 readiness, browser, and docs patterns; add no new architecture unless a P1 proof requires it.
2. Prove the current production/app state first.
3. Fix only P1 failures found by proof.
4. Re-run focused and full gates.
5. Release/deploy only when evidence supports the final claim.
