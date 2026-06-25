# Tasks: MVP Live Owner Journey And UI Proof

**Input**: Design documents from `specs/052-mvp-live-ui-proof/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/](./contracts/), [quickstart.md](./quickstart.md)

**Tests**: Tests are required where 052 changes product behavior or readiness logic. Evidence-only tasks must still leave metadata-safe proof.

**Organization**: Tasks are grouped by independently testable user story. Do not mark a task `[X]` until direct evidence exists.

## Phase 1: Setup And Governance

**Purpose**: Lock the active 052 context, evidence locations, and product truth boundaries.

- [X] T001 Create metadata-safe validation log in `specs/052-mvp-live-ui-proof/evidence/validation-log.md`
- [X] T002 [P] Record branch/master/deploy baseline and dirty-worktree boundary in `specs/052-mvp-live-ui-proof/evidence/validation-log.md`
- [X] T003 [P] Verify `AGENTS.md` points to `specs/052-mvp-live-ui-proof/plan.md`
- [X] T004 [P] Add simple Russian `[Unreleased]` changelog entry for 052 in `CHANGELOG.md`
- [X] T005 Run `SPECIFY_FEATURE_DIRECTORY=specs/052-mvp-live-ui-proof .specify/scripts/bash/check-prerequisites.sh --json --require-tasks --include-tasks` and record the metadata-only result in `specs/052-mvp-live-ui-proof/evidence/validation-log.md`
- [X] T006 Run checklist status validation for `specs/052-mvp-live-ui-proof/checklists/*.md` and record the result in `specs/052-mvp-live-ui-proof/evidence/validation-log.md`

---

## Phase 2: Foundational Contracts And Harnesses

**Purpose**: Reuse accepted proof harnesses and add only the 052-specific gaps before product changes.

- [X] T007 [P] Add or update 052 owner journey readiness contract tests in `apps/server/tests/contract/test_mvp_owner_journey_proof_contract.py`
- [X] T008 [P] Add or update 052 readiness claim rule tests in `apps/server/tests/unit/test_mvp_owner_journey_readiness.py`
- [X] T009 [P] Add 052 product status regression in `apps/server/tests/integration/test_mvp_launch_status_truth.py`
- [X] T010 [P] Add metadata-only 052 production owner journey probe in `specs/052-mvp-live-ui-proof/evidence/production-owner-journey-probe.py`
- [X] T011 [P] Add 052 browser runtime verifier by reusing the 051 verifier pattern in `specs/052-mvp-live-ui-proof/evidence/browser-runtime-check.cjs`
- [X] T012 Add 052 readiness/gap support in `apps/server/src/twobrain_rec_server/readiness/matrix.py` and `apps/server/src/twobrain_rec_server/readiness/report.py`
- [X] T013 Add 052 closeout, timing, installed-app, and UI review evidence templates in `specs/052-mvp-live-ui-proof/evidence/mvp-closeout-report.md`, `specs/052-mvp-live-ui-proof/evidence/timing-proof.md`, `specs/052-mvp-live-ui-proof/evidence/installed-app-check.md`, and `specs/052-mvp-live-ui-proof/evidence/ui-reference-review.md`
- [X] T014 Run foundational focused tests and record RED/GREEN results in `specs/052-mvp-live-ui-proof/evidence/validation-log.md`

**Checkpoint**: 052 can evaluate MVP proof and readiness claims without live private content.

---

## Phase 2A: Pre-Implementation Spec Kit Gates

**Purpose**: Run required consistency and tracker gates before implementation.

- [X] T015 Run read-only Spec Kit analyze across `specs/052-mvp-live-ui-proof/spec.md`, `specs/052-mvp-live-ui-proof/plan.md`, and `specs/052-mvp-live-ui-proof/tasks.md`, then record blocker-free result in `specs/052-mvp-live-ui-proof/evidence/validation-log.md`
- [X] T016 Run `$speckit-taskstoissues`, create/update issue mapping in `specs/052-mvp-live-ui-proof/issues.md`, and record GitHub issue canon validation in `specs/052-mvp-live-ui-proof/evidence/validation-log.md`

---

## Phase 3: User Story 1 - Fresh Recording Reaches Review (Priority: P1)

**Goal**: A current installed-app owner journey reaches production review, or the exact blocking gate is visible.

**Independent Test**: A metadata-safe gate table shows pass/fail/blocked/unproven for installed app, record/stop/upload, finalization, processing, transcript/diarization, playback, speaker timeline, stored outcomes, embedded parity, timing, and forbidden-content scan.

- [X] T017 [US1] Verify `/Applications/2brain Rec.app` version, launch/code-sign state, and active recording safety; record result in `specs/052-mvp-live-ui-proof/evidence/installed-app-check.md`
- [X] T018 [US1] Run production health/deployed SHA checks and record release/deploy truth in `specs/052-mvp-live-ui-proof/evidence/validation-log.md`
- [ ] T019 [US1] Run or collect current installed-app record/stop/upload-to-review metadata and record gate states in `specs/052-mvp-live-ui-proof/evidence/mvp-closeout-report.md`
- [ ] T020 [US1] Run production candidate metadata probe through `specs/052-mvp-live-ui-proof/evidence/production-owner-journey-probe.py` and record stored outcome/transcript/playback/timeline counts in `specs/052-mvp-live-ui-proof/evidence/mvp-closeout-report.md`
- [X] T021 [US1] Fix any discovered normal-path owner journey blocker in `apps/server/src/twobrain_rec_server/`, `apps/macos/RecApp/Sources`, or `infra/docker-compose.yml`
- [X] T022 [US1] If any owner journey gate fails or is unproven, add the exact P1 launch gap and next action to `docs/evidence/052-mvp-live-ui-proof/launch-gap-register.md`

**Checkpoint**: Fresh owner journey readiness is proven or explicitly blocked; no assumed P1 gate remains.

---

## Phase 4: User Story 2 - MVP Timing Is Proven Or Bounded (Priority: P1)

**Goal**: Representative timing is measured against the 180-second-per-hour target, or the timing gate remains honestly open.

**Independent Test**: Timing report separates audio duration, raw processing, provider processing, queue/wait, finalize-to-review, and target result.

- [X] T023 [P] [US2] Add or update timing proof tests in `apps/server/tests/unit/test_mvp_owner_journey_readiness.py`
- [X] T024 [US2] Record representative production timing evidence in `specs/052-mvp-live-ui-proof/evidence/timing-proof.md`
- [X] T025 [US2] Reconcile `processing-time-target-evidence` in `docs/evidence/052-mvp-live-ui-proof/launch-gap-register.md` after timing proof

**Checkpoint**: Timing target is pass/fail/unproven with direct evidence, never extrapolated from a short run.

---

## Phase 5: User Story 3 - Web And Desktop Review Feel Coherent (Priority: P1)

**Goal**: Web cabinet, macOS embedded review, compact review, and native shell are readable, truthful, and aligned with MVP playback/timeline/outcome expectations.

**Independent Test**: Browser/runtime, macOS checks, and KRISP clean-room notes show no P1 overlap, false-ready cabinet state, hidden speaker lanes, hidden native capture truth, or web/embedded contradiction.

- [X] T026 [P] [US3] Add or update web-shell tests for 052 review quality in `apps/server/tests/unit/test_cabinet_web_shell.py`
- [X] T027 [P] [US3] Add or update macOS cabinet truth tests in `apps/macos/Shared/Tests/DesktopCabinetWorkspaceTests.swift`
- [X] T028 [US3] Inspect KRISP web/app reference and record clean-room interaction findings in `specs/052-mvp-live-ui-proof/evidence/ui-reference-review.md`
- [X] T029 [US3] Run 052 browser runtime verifier and record `failures=[]` or findings in `specs/052-mvp-live-ui-proof/evidence/validation-log.md`
- [X] T030 [US3] Fix any discovered web cabinet layout/truth gap in `apps/server/src/twobrain_rec_server/cabinet/web.py`, `apps/server/src/twobrain_rec_server/api/cabinet.py`, or `apps/server/src/twobrain_rec_server/cabinet/view_models.py`
- [X] T031 [US3] Fix any discovered native macOS cabinet truth gap in `apps/macos/RecApp/Sources` or `apps/macos/Shared/Sources`
- [X] T032 [US3] Re-run browser runtime verifier and focused macOS cabinet tests, then record evidence in `specs/052-mvp-live-ui-proof/evidence/validation-log.md`

**Checkpoint**: MVP review interface is validated or has explicit P1 findings.

---

## Phase 6: User Story 4 - Launch Claim Is Truthful (Priority: P2)

**Goal**: The final 052 output states one allowed claim with evidence and no hidden blockers.

**Independent Test**: The closeout report can be audited gate-by-gate and matches status docs, readiness report, launch gaps, validation log, changelog, and release notes.

- [X] T033 [US4] Generate `docs/evidence/052-mvp-live-ui-proof/readiness-report.md`, `docs/evidence/052-mvp-live-ui-proof/readiness-report.json`, and `docs/evidence/052-mvp-live-ui-proof/launch-gap-register.md`
- [X] T034 [US4] Update `docs/current-product-status.md` with 052 outcome and remaining P1/P2 boundaries
- [X] T035 [US4] Compute final P1 gate summary in `specs/052-mvp-live-ui-proof/evidence/mvp-closeout-report.md`
- [X] T036 [US4] Update `CHANGELOG.md` with final 052 outcome in simple Russian
- [X] T037 [US4] Run forbidden-content scan from `specs/052-mvp-live-ui-proof/quickstart.md`
- [X] T038 [US4] Reconcile every task checkbox with direct evidence and leave unverified tasks open in `specs/052-mvp-live-ui-proof/tasks.md`

---

## Phase 7: Final Validation, PR, Release, Deploy

**Purpose**: Close the slice only after implementation, UI proof, and production gates.

- [X] T039 Run all focused commands from `specs/052-mvp-live-ui-proof/quickstart.md` and record results in `specs/052-mvp-live-ui-proof/evidence/validation-log.md`
- [X] T040 Run full `infra/scripts/ci-local.sh` and record `ci_local_result` in `specs/052-mvp-live-ui-proof/evidence/validation-log.md`
- [X] T041 Run `infra/scripts/cd-remote.sh --dry-run` and record deploy-readiness evidence in `specs/052-mvp-live-ui-proof/evidence/validation-log.md`
- [X] T042 Run a Ponytail over-engineering pass over the final diff and remove avoidable new abstractions before PR; record result in `specs/052-mvp-live-ui-proof/evidence/validation-log.md`
- [X] T043 Prepare PR description and release notes draft in simple Russian in `specs/052-mvp-live-ui-proof/evidence/pr-draft.md`
- [X] T044 After merge/release gate, run release and production deploy, then record deployed SHA and public health in `specs/052-mvp-live-ui-proof/evidence/validation-log.md`

---

## Dependencies & Execution Order

- Phase 1 must complete before all other phases.
- Phase 2 blocks implementation because it defines 052 readiness contracts and harnesses.
- Phase 2A must pass before user story implementation.
- US1 can run after Phase 2A; US2 uses the US1 candidate when available.
- US3 can run after Phase 2A and must be re-run after any web/macOS fixes.
- US4 depends on US1-US3 evidence.
- Phase 7 depends on all selected tasks and P1 gates being reconciled.

## Parallel Opportunities

- T002-T004 can run in parallel after T001.
- T007-T011 can run in parallel.
- T023 and T026-T027 can run in parallel after Phase 2A.
- T030-T031 can run in parallel only if both web and native defects are found.

## Implementation Strategy

1. Reuse 051 readiness, browser, docs, and production probe patterns; add no new architecture unless a P1 proof requires it.
2. Prove the current production/app state first.
3. Fix only P1 failures found by proof.
4. Re-run focused and full gates.
5. Release/deploy only when evidence supports the final claim.
