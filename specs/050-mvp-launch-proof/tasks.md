# Tasks: MVP Launch Proof

**Input**: Design documents from `specs/050-mvp-launch-proof/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md), [research.md](./research.md), [data-model.md](./data-model.md), [contracts/](./contracts/), [quickstart.md](./quickstart.md)

**Tests**: Tests are required. This slice gates MVP readiness, live production truth, privacy-safe evidence, and web/macOS interface quality.

**Organization**: Tasks are grouped by independently testable user story. Do not mark a task `[X]` until direct evidence exists.

## Phase 1: Setup And Governance

**Purpose**: Lock the active 050 context, governance correction, and metadata-safe evidence location.

- [X] T001 Create metadata-safe validation log in `specs/050-mvp-launch-proof/evidence/validation-log.md`
- [X] T002 [P] Record the clean branch/master baseline and dirty-worktree boundary in `specs/050-mvp-launch-proof/evidence/validation-log.md`
- [X] T003 [P] Keep `AGENTS.md` Spec Kit pointer on `specs/050-mvp-launch-proof/plan.md`
- [X] T004 [P] Keep `.specify/memory/constitution.md` and `docs/agent-guidance/product-gates.md` aligned on public URL `https://rec.2brain.pro`
- [X] T005 [P] Add simple Russian `[Unreleased]` changelog entry for 050 MVP proof/status correction in `CHANGELOG.md`
- [X] T006 Run `SPECIFY_FEATURE_DIRECTORY=specs/050-mvp-launch-proof .specify/scripts/bash/check-prerequisites.sh --json --require-tasks --include-tasks` and record the metadata-only result in `specs/050-mvp-launch-proof/evidence/validation-log.md`
- [X] T007 Run checklist status validation for `specs/050-mvp-launch-proof/checklists/*.md` and record the result in `specs/050-mvp-launch-proof/evidence/validation-log.md`

---

## Phase 2: Foundational Readiness Contracts And Harnesses

**Purpose**: Define machine-checkable readiness and UI proof expectations before changing status docs or product behavior.

- [X] T008 [P] Add RED tests for 050 readiness claim rules in `apps/server/tests/unit/test_mvp_launch_proof_readiness.py`
- [X] T009 [P] Add RED tests that current product status has no stale branch-local 045-049 claims in `apps/server/tests/integration/test_mvp_launch_status_truth.py`
- [X] T010 [P] Add RED tests for production URL governance consistency in `apps/server/tests/unit/test_product_gate_url_truth.py`
- [X] T011 [P] Add 050 browser runtime verifier scaffold in `specs/050-mvp-launch-proof/evidence/browser-runtime-check.cjs`
- [X] T012 Add 050 readiness/evidence support in `apps/server/src/twobrain_rec_server/readiness/matrix.py` and `apps/server/src/twobrain_rec_server/readiness/report.py`
- [X] T013 Add metadata-only 050 closeout report template in `specs/050-mvp-launch-proof/evidence/mvp-closeout-report.md`
- [X] T014 Run foundational focused tests and record RED/GREEN results in `specs/050-mvp-launch-proof/evidence/validation-log.md`

**Checkpoint**: 050 can evaluate readiness claims and stale status truth without live private content.

---

## Phase 2A: Pre-Implementation Spec Kit Gates

**Purpose**: Run the required read-only consistency and tracker gates before user story implementation.

- [X] T015 Run read-only Spec Kit analyze pass across `specs/050-mvp-launch-proof/spec.md`, `specs/050-mvp-launch-proof/plan.md`, and `specs/050-mvp-launch-proof/tasks.md`, then record blocker-free result in `specs/050-mvp-launch-proof/evidence/validation-log.md`
- [X] T016 Run `$speckit-taskstoissues`, create/update issue mapping in `specs/050-mvp-launch-proof/issues.md`, and record GitHub issue canon validation in `specs/050-mvp-launch-proof/evidence/validation-log.md`

---

## Phase 3: User Story 1 - Prove The Full Owner Journey (Priority: P1)

**Goal**: Current installed app and production server have direct evidence for record/upload/process/review, or the exact blocking gate is visible.

**Independent Test**: A metadata-safe journey gate table shows pass/fail/blocked/unproven for release, installed app, record/stop/upload, finalization, processing, transcript/diarization, playback, stored outcomes, embedded parity, timing, and forbidden-content scan.

### Tests for User Story 1

- [X] T017 [P] [US1] Add production health/deployed SHA verifier in `specs/050-mvp-launch-proof/evidence/production-health-check.sh`
- [X] T018 [P] [US1] Add macOS installed-app identity and safe launch verifier notes in `specs/050-mvp-launch-proof/evidence/installed-app-check.md`
- [X] T019 [P] [US1] Add metadata-only production journey gate contract test in `apps/server/tests/contract/test_mvp_launch_proof_contract.py`

### Implementation for User Story 1

- [X] T020 [US1] Run production health/deployed SHA checks and record release/deploy gate evidence in `specs/050-mvp-launch-proof/evidence/validation-log.md`
- [X] T021 [US1] Verify `/Applications/2brain Rec.app` identity, launch, native capture controls, and cabinet truth state; record metadata-only result in `specs/050-mvp-launch-proof/evidence/validation-log.md`
- [X] T022 [US1] Run or collect a current production upload-to-review journey with no private committed content, then record gate states in `specs/050-mvp-launch-proof/evidence/mvp-closeout-report.md`
- [X] T023 [US1] Record processing-time evidence against the three-minute-per-hour target in `specs/050-mvp-launch-proof/evidence/mvp-closeout-report.md`
- [X] T024 [US1] If any P1 owner-journey gate fails or is unproven, add the exact launch gap and next action to `docs/evidence/050-mvp-launch-proof/launch-gap-register.md`

**Checkpoint**: Owner journey readiness is proven or explicitly blocked; no assumed gate remains.

---

## Phase 4: User Story 2 - Verify MVP Interface Quality (Priority: P1)

**Goal**: Web cabinet, embedded macOS review, mobile-width review, and native shell are readable, truthful, and aligned with the accepted playback/outcome UX.

**Independent Test**: Browser/runtime and macOS checks show no overlap, stale active tabs, hidden native capture truth, false green cabinet state, or web/embedded contradiction.

### Tests for User Story 2

- [X] T025 [P] [US2] Extend web-shell tests for active review tabs, speaker lanes, timestamp seek, stored outcomes, and mobile-safe markup in `apps/server/tests/unit/test_cabinet_web_shell.py`
- [X] T026 [P] [US2] Extend macOS cabinet truth tests for server/auth/cached-ready states in `apps/macos/Shared/Tests/DesktopCabinetWorkspaceTests.swift` or adjacent DesktopCabinet tests
- [X] T027 [P] [US2] Implement browser runtime checks for desktop, embedded, mobile-width, timestamp seek, speaker timeline labels, outcomes tab, console health, and overflow in `specs/050-mvp-launch-proof/evidence/browser-runtime-check.cjs`

### Implementation for User Story 2

- [X] T028 [US2] Fix any discovered cabinet tab/player/timeline/outcome layout gaps in `apps/server/src/twobrain_rec_server/cabinet/web.py`
- [X] T029 [US2] Fix any discovered web/embedded route truth gaps in `apps/server/src/twobrain_rec_server/api/cabinet.py` or `apps/server/src/twobrain_rec_server/cabinet/view_models.py`
- [X] T030 [US2] Fix any discovered native macOS cabinet truth gaps in `apps/macos/RecApp/Sources` or `apps/macos/Shared/Sources`
- [X] T031 [US2] Run browser runtime verifier and focused macOS cabinet tests, then record metadata-only evidence in `specs/050-mvp-launch-proof/evidence/validation-log.md`

**Checkpoint**: MVP review interface is either validated or has explicit P1 findings.

---

## Phase 5: User Story 3 - Keep Product Truth Current (Priority: P1)

**Goal**: Product docs and generated readiness artifacts match shipped 045-049 behavior and current 050 evidence.

**Independent Test**: Status/readiness tests and human review show no stale statements that 045-049 are branch-local or awaiting release, and no inflated pilot/production claims.

### Tests for User Story 3

- [X] T032 [P] [US3] Add status/readiness tests for closed `notes-action-output` and remaining production-user-rollout boundary in `apps/server/tests/integration/test_mvp_loop_readiness_report.py`
- [X] T033 [P] [US3] Add current-product-status text regression for 049 release/deploy truth in `apps/server/tests/integration/test_mvp_launch_status_truth.py`

### Implementation for User Story 3

- [X] T034 [US3] Update `docs/current-product-status.md` to reflect merged/released/deployed 045-049 truth and current 050 launch boundary
- [X] T035 [US3] Update or generate `docs/evidence/050-mvp-launch-proof/readiness-report.md`, `docs/evidence/050-mvp-launch-proof/readiness-report.json`, and `docs/evidence/050-mvp-launch-proof/launch-gap-register.md`
- [X] T036 [US3] Update `docs/evidence/036-owner-review-live-polish/readiness-report.md` only with supersession notes needed to point to current 049/050 evidence
- [X] T037 [US3] Run status/readiness tests and record results in `specs/050-mvp-launch-proof/evidence/validation-log.md`

**Checkpoint**: Product truth is current and claim-safe.

---

## Phase 6: User Story 4 - Decide And Record The MVP Claim (Priority: P2)

**Goal**: The final 050 output states one allowed claim with evidence and no hidden blockers.

**Independent Test**: The closeout report can be audited gate-by-gate and matches the status docs, readiness report, and validation log.

- [X] T038 [US4] Compute final P1 gate summary in `specs/050-mvp-launch-proof/evidence/mvp-closeout-report.md`
- [X] T039 [US4] Update `CHANGELOG.md` with final 050 outcome in simple Russian
- [X] T040 [US4] Run forbidden-content scan from `specs/050-mvp-launch-proof/quickstart.md`
- [X] T041 [US4] Reconcile every task checkbox with direct evidence and leave unverified tasks open in `specs/050-mvp-launch-proof/tasks.md`

---

## Phase 7: Final Validation, PR, Release, Deploy

**Purpose**: Close the slice only after implementation, UI proof, and production gates.

- [X] T042 Run all focused commands from `specs/050-mvp-launch-proof/quickstart.md` and record results in `specs/050-mvp-launch-proof/evidence/validation-log.md`
- [X] T043 Run full `infra/scripts/ci-local.sh` and record `ci_local_result` in `specs/050-mvp-launch-proof/evidence/validation-log.md`
- [X] T044 Run `infra/scripts/cd-remote.sh --dry-run` and record deploy-readiness evidence in `specs/050-mvp-launch-proof/evidence/validation-log.md`
- [X] T045 Prepare PR description and release notes draft in simple Russian in `specs/050-mvp-launch-proof/evidence/pr-draft.md`
- [X] T046 After merge/release gate, run release and production deploy, then record deployed SHA and public health in `specs/050-mvp-launch-proof/evidence/validation-log.md`

---

## Dependencies & Execution Order

- Phase 1 must complete before all other phases.
- Phase 2 blocks implementation because it defines 050 readiness contracts.
- US1 and US2 may run after Phase 2; US2 fixes must be re-validated before final claim.
- US3 depends on current evidence from US1/US2.
- US4 depends on US1-US3 evidence.
- Phase 7 depends on all selected tasks and all P1 gates being reconciled.

## Parallel Opportunities

- T003-T005 can run in parallel after T001.
- T008-T011 can run in parallel.
- T017-T019 can run in parallel.
- T025-T027 can run in parallel.
- T032-T033 can run in parallel.

## Implementation Strategy

1. Prove the baseline and write RED tests for stale truth and readiness claim rules.
2. Implement minimal readiness/evidence support for 050.
3. Run live production/app/UI proof.
4. Fix only P1 gaps found by proof.
5. Update current product truth and readiness outputs.
6. Run full gates, then prepare PR/release/deploy only when evidence supports it.
