# Tasks: MVP Loop Live Evidence

**Input**: Design documents from `specs/035-mvp-loop-live-evidence/`

**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/`, `quickstart.md`

**Tests**: Tests and validation tasks are required because this feature gates MVP/pilot claims and evidence safety.

**Organization**: Tasks are grouped by independently testable user story. Each story can produce useful evidence without private meeting content or new product behavior.

## Phase 1: Setup

**Purpose**: Create the feature evidence locations and baseline documentation.

- [X] T001 Create evidence scaffold in `docs/evidence/035-mvp-loop-live-evidence/README.md`
- [X] T002 [P] Create screenshot directory placeholder in `docs/evidence/035-mvp-loop-live-evidence/screenshots/.gitkeep`
- [X] T003 [P] Create initial validation log in `docs/evidence/035-mvp-loop-live-evidence/validation-log.md`
- [X] T004 [P] Create initial clean-room reference note in `docs/evidence/035-mvp-loop-live-evidence/clean-room-reference.md`

---

## Phase 2: Foundational

**Purpose**: Ensure report and evidence contracts can enforce validation-only scope before story evidence is collected.

**Critical**: No live-loop claim work can proceed until stale recommendation, forbidden-content, and P0/P1 claim gates are covered.

- [X] T005 [P] Add live evidence pack contract coverage in `apps/server/tests/integration/test_mvp_loop_live_evidence.py`
- [X] T006 [P] Add stale next-slice and P0/P1 claim coverage in `apps/server/tests/integration/test_mvp_loop_readiness_report.py`
- [X] T007 [P] Add launch-gap and accepted-022 evidence coverage in `apps/server/tests/unit/test_mvp_loop_readiness_matrix.py`
- [X] T008 Update readiness model/report generation for 035 evidence outputs in `apps/server/src/twobrain_rec_server/readiness/report.py`
- [X] T009 Update readiness matrix current gaps and claim rules after 022 in `apps/server/src/twobrain_rec_server/readiness/matrix.py`

**Checkpoint**: Focused readiness tests prove the report cannot recommend a completed feature or claim MVP readiness with unresolved P0/P1 gaps.

---

## Phase 3: User Story 1 - Prove Installed Desktop Capture Loop (Priority: P1) 🎯 MVP

**Goal**: Prove or explicitly block the installed `/Applications/2brain Rec.app` desktop capture loop.

**Independent Test**: Run the installed app from `/Applications`, perform Record/Pause/Resume/Stop, save screenshots, and validate the latest local artifact manifest.

### Tests for User Story 1

- [X] T010 [P] [US1] Add installed desktop evidence assertions in `apps/server/tests/integration/test_mvp_loop_live_evidence.py`
- [X] T011 [P] [US1] Add latest-artifact validation command expectation in `docs/evidence/035-mvp-loop-live-evidence/validation-log.md`

### Implementation for User Story 1

- [X] T012 [US1] Install the staged macOS app into `/Applications/2brain Rec.app` and record the command evidence in `docs/evidence/035-mvp-loop-live-evidence/validation-log.md`
- [X] T013 [US1] Capture installed desktop idle/ready screenshot in `docs/evidence/035-mvp-loop-live-evidence/screenshots/`
- [X] T014 [US1] Capture installed desktop active recording screenshot in `docs/evidence/035-mvp-loop-live-evidence/screenshots/`
- [X] T015 [US1] Capture installed desktop paused recording screenshot in `docs/evidence/035-mvp-loop-live-evidence/screenshots/`
- [X] T016 [US1] Capture installed desktop resumed recording screenshot in `docs/evidence/035-mvp-loop-live-evidence/screenshots/`
- [X] T017 [US1] Capture installed desktop stopped/list screenshot in `docs/evidence/035-mvp-loop-live-evidence/screenshots/`
- [X] T018 [US1] Run `apps/macos/Scripts/validate-meeting-mute-truth.sh --latest-artifact-directory` and record result in `docs/evidence/035-mvp-loop-live-evidence/validation-log.md`
- [X] T019 [US1] Summarize installed desktop artifact metadata and limitations in `docs/evidence/035-mvp-loop-live-evidence/README.md`

**Checkpoint**: US1 is complete when installed desktop evidence is either accepted with latest-artifact validation or blocks the claim with a precise failing gate.

---

## Phase 4: User Story 2 - Prove Owner Web Review Loop (Priority: P1)

**Goal**: Prove or explicitly block the owner web review portion of the MVP loop.

**Independent Test**: Open safe owner list/detail/governance states, capture metadata-safe evidence or blocker notes, and classify notes/action truth.

### Tests for User Story 2

- [ ] T020 [P] [US2] Add web evidence assertions in `apps/server/tests/integration/test_mvp_loop_live_evidence.py`
- [ ] T021 [P] [US2] Add notes/action blocker or ready-state assertion in `apps/server/tests/integration/test_mvp_loop_readiness_report.py`

### Implementation for User Story 2

- [ ] T022 [US2] Capture or document web meeting-list evidence in `docs/evidence/035-mvp-loop-live-evidence/screenshots/web-meeting-list-evidence.md`
- [ ] T023 [US2] Capture or document web meeting-detail evidence in `docs/evidence/035-mvp-loop-live-evidence/screenshots/web-meeting-detail-evidence.md`
- [ ] T024 [US2] Capture or document governance/share/export/deletion evidence in `docs/evidence/035-mvp-loop-live-evidence/screenshots/web-governance-evidence.md`
- [ ] T025 [US2] Record notes/action output truth and limitations in `docs/evidence/035-mvp-loop-live-evidence/validation-log.md`

**Checkpoint**: US2 is complete when web owner review is represented as ready, blocked, or fixture-backed without private meeting content.

---

## Phase 5: User Story 3 - Produce Decision-Ready MVP Claim (Priority: P1)

**Goal**: Generate a single current readiness pack with the strongest truthful claim and next action.

**Independent Test**: Generate readiness outputs and inspect that claim summary, gap register, status docs, and changelog agree.

### Tests for User Story 3

- [ ] T026 [P] [US3] Add 035 readiness output generation coverage in `apps/server/tests/integration/test_mvp_loop_live_evidence.py`
- [ ] T027 [P] [US3] Add current status/changelog stale-claim coverage in `apps/server/tests/integration/test_mvp_loop_readiness_report.py`

### Implementation for User Story 3

- [ ] T028 [US3] Generate `docs/evidence/035-mvp-loop-live-evidence/readiness-report.json`
- [ ] T029 [US3] Generate `docs/evidence/035-mvp-loop-live-evidence/readiness-report.md`
- [ ] T030 [US3] Generate `docs/evidence/035-mvp-loop-live-evidence/launch-gap-register.md`
- [ ] T031 [US3] Update current strongest claim and next product slice in `docs/current-product-status.md`
- [ ] T032 [US3] Update 035 changelog entry in `CHANGELOG.md`

**Checkpoint**: US3 is complete when a reviewer can see exactly why the product is `mvp_loop_ready` or still blocked.

---

## Phase 6: User Story 4 - Preserve Clean-Room Reference Alignment (Priority: P2)

**Goal**: Compare live 2brain desktop/web surfaces against allowed Krisp lessons without copying protected expression.

**Independent Test**: Review `clean-room-reference.md` for allowed lessons, intentional differences, forbidden checks, and result.

### Tests for User Story 4

- [ ] T033 [P] [US4] Add clean-room reference assertions in `apps/server/tests/integration/test_mvp_loop_live_evidence.py`

### Implementation for User Story 4

- [ ] T034 [US4] Record allowed reference lessons and forbidden similarity checks in `docs/evidence/035-mvp-loop-live-evidence/clean-room-reference.md`
- [ ] T035 [US4] Record reference-driven UI polish gaps or pass result in `docs/evidence/035-mvp-loop-live-evidence/readiness-report.md`

**Checkpoint**: US4 is complete when reference comparison is useful for quality but contains no copied Krisp expression or private reference data.

---

## Phase 7: Polish And Cross-Cutting Validation

**Purpose**: Prove the feature is safe to review, issue-sync, and continue toward MVP.

- [ ] T036 [P] Run focused readiness tests and record results in `docs/evidence/035-mvp-loop-live-evidence/validation-log.md`
- [ ] T037 [P] Run `infra/scripts/ci-local.sh` and record result in `docs/evidence/035-mvp-loop-live-evidence/validation-log.md`
- [ ] T038 [P] Run macOS build/focused tests from quickstart and record results in `docs/evidence/035-mvp-loop-live-evidence/validation-log.md`
- [ ] T039 Run forbidden-content scans over `specs/035-mvp-loop-live-evidence` and `docs/evidence/035-mvp-loop-live-evidence` and record result in `docs/evidence/035-mvp-loop-live-evidence/validation-log.md`
- [ ] T040 Run `git diff --check` and record result in `docs/evidence/035-mvp-loop-live-evidence/validation-log.md`
- [X] T041 Run `$speckit-taskstoissues`/GitHub issue sync and record issue links in `specs/035-mvp-loop-live-evidence/issues.md`
- [ ] T042 Run `$speckit-analyze` after issue sync changes if tasks or scope changed and record final analysis in `specs/035-mvp-loop-live-evidence/analysis.md`
- [ ] T043 Verify every task is complete, every checklist is complete, and no open `feature:035` GitHub issue lacks evidence in `docs/evidence/035-mvp-loop-live-evidence/validation-log.md`

---

## Dependencies And Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies.
- **Foundational (Phase 2)**: Depends on Setup and blocks user stories.
- **US1 and US2 (P1)**: Start after Foundational; both are required for MVP loop evidence.
- **US3 (P1)**: Depends on findings from US1 and US2.
- **US4 (P2)**: Can run after Foundational but final result should reflect US1/US2 surfaces.
- **Polish (Phase 7)**: Depends on all selected story tasks and must run before acceptance.

### User Story Dependencies

- **US1**: No dependency after Foundational; proves desktop runtime.
- **US2**: No dependency after Foundational; proves web review truth.
- **US3**: Depends on US1/US2 evidence for claim decision.
- **US4**: Depends on the surfaces observed in US1/US2.

### Parallel Opportunities

- T002-T004 can run in parallel.
- T005-T007 can run in parallel.
- US1 screenshot capture tasks are sequential during the manual flow, but US1 tests can run in parallel.
- US2 evidence docs can be prepared in parallel with US1 after Foundational.
- T036-T038 can run in parallel before final validation reconciliation.

## Parallel Example: Foundational Tests

```text
Task: "T005 [P] Add live evidence pack contract coverage in apps/server/tests/integration/test_mvp_loop_live_evidence.py"
Task: "T006 [P] Add stale next-slice and P0/P1 claim coverage in apps/server/tests/integration/test_mvp_loop_readiness_report.py"
Task: "T007 [P] Add launch-gap and accepted-022 evidence coverage in apps/server/tests/unit/test_mvp_loop_readiness_matrix.py"
```

## Implementation Strategy

### MVP First

1. Complete Setup and Foundational.
2. Complete US1 installed desktop proof.
3. Complete US2 web owner review proof or blocker.
4. Complete US3 claim decision.
5. Stop and review if any P0/P1 gap lacks owner and next action.

### Full Readiness Pass

1. Complete all user stories.
2. Run polish validation.
3. Sync GitHub issues.
4. Keep the goal active unless the full MVP objective is proven, not merely this slice.
