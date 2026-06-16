# Tasks: MVP Loop Readiness

**Input**: Design documents from `specs/034-mvp-loop-readiness/`

**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/`, `quickstart.md`

**Tests**: Contract, unit, integration, macOS regression, forbidden-content scan, local CI, and production boundary checks are required because this feature is a launch-readiness gate.

**Organization**: Tasks are grouped by independently testable user story. Each story can produce evidence without requiring private meeting content or destructive production mutation.

## Phase 1: Setup

**Purpose**: Create the readiness artifact locations and durable code entry points.

- [ ] T001 Create the committed evidence directory scaffold in `docs/evidence/034-mvp-loop-readiness/README.md`
- [ ] T002 [P] Create the screenshot evidence placeholder in `docs/evidence/034-mvp-loop-readiness/screenshots/.gitkeep`
- [ ] T003 [P] Create the readiness package entry point in `apps/server/src/twobrain_rec_server/readiness/__init__.py`
- [ ] T004 [P] Create the readiness generator script shell in `apps/server/scripts/generate_mvp_loop_readiness.py`

---

## Phase 2: Foundational

**Purpose**: Define reusable readiness models, validation, and rendering before story-specific evidence is generated.

**Critical**: No user story evidence can be trusted until the schema, matrix, and report renderer enforce bounded claims and forbidden-content metadata.

- [ ] T005 [P] Add JSON schema and required-section contract tests in `apps/server/tests/contract/test_mvp_loop_readiness_contract.py`
- [ ] T006 [P] Add stage, evidence, claim, and launch-gap validation tests in `apps/server/tests/unit/test_mvp_loop_readiness_matrix.py`
- [ ] T007 [P] Add Markdown/JSON generation integration tests in `apps/server/tests/integration/test_mvp_loop_readiness_report.py`
- [ ] T008 Implement metadata-only evidence, stage, gap, comparison, and claim models in `apps/server/src/twobrain_rec_server/readiness/evidence.py`
- [ ] T009 Implement default MVP loop stage definitions and claim validation in `apps/server/src/twobrain_rec_server/readiness/matrix.py`
- [ ] T010 Implement JSON and Markdown report rendering in `apps/server/src/twobrain_rec_server/readiness/report.py`
- [ ] T011 Wire CLI output paths and deterministic generation into `apps/server/scripts/generate_mvp_loop_readiness.py`

**Checkpoint**: Focused readiness tests can fail for story-specific missing evidence, but schema and bounded-claim rules are enforced.

---

## Phase 3: User Story 1 - Prove The Complete Owner Value Loop (Priority: P1)

**Goal**: Produce one trustworthy readiness view for the end-to-end owner loop and prevent overclaiming beyond evidence strength.

**Independent Test**: Run the focused readiness tests and generator; inspect `readiness-report.json` and `readiness-report.md` for every loop stage, evidence strength, launch gap, and bounded claim.

### Tests for User Story 1

- [ ] T012 [P] [US1] Add contract coverage for accepted final outcomes and excluded claims in `apps/server/tests/contract/test_mvp_loop_readiness_contract.py`
- [ ] T013 [P] [US1] Add unit coverage that synthetic-only or missing P1 evidence blocks `mvp_loop_ready` in `apps/server/tests/unit/test_mvp_loop_readiness_matrix.py`
- [ ] T014 [P] [US1] Add integration coverage for complete loop report sections and stage counts in `apps/server/tests/integration/test_mvp_loop_readiness_report.py`

### Implementation for User Story 1

- [ ] T015 [US1] Populate all FR-001 MVP loop stages in `apps/server/src/twobrain_rec_server/readiness/matrix.py`
- [ ] T016 [US1] Populate current feature, PR, deploy, and docs evidence records in `apps/server/src/twobrain_rec_server/readiness/report.py`
- [ ] T017 [US1] Generate the first JSON readiness report in `docs/evidence/034-mvp-loop-readiness/readiness-report.json`
- [ ] T018 [US1] Generate the first Markdown readiness report in `docs/evidence/034-mvp-loop-readiness/readiness-report.md`
- [ ] T019 [US1] Record generator usage and evidence limitations in `docs/evidence/034-mvp-loop-readiness/README.md`

**Checkpoint**: US1 is complete when the report classifies every MVP loop stage and explicitly caps production evidence at `infra_smoke_ready` unless stronger evidence exists.

---

## Phase 4: User Story 2 - Verify The Desktop App As The First Product Surface (Priority: P1)

**Goal**: Verify that the macOS app opens into a meeting workspace or bounded unavailable state while native capture authority stays outside embedded web content.

**Independent Test**: Run the macOS cabinet/capture regression filter and inspect metadata-safe desktop evidence or an explicit blocker.

### Tests for User Story 2

- [ ] T020 [P] [US2] Extend workspace-first and native-control boundary tests in `apps/macos/Shared/Tests/DesktopCabinetWorkspaceTests.swift`
- [ ] T021 [P] [US2] Extend cabinet unavailable/auth route policy tests in `apps/macos/Shared/Tests/DesktopCabinetRoutePolicyTests.swift`
- [ ] T022 [P] [US2] Extend upload-to-review identity continuity tests in `apps/macos/Shared/Tests/DesktopCabinetUploadLinkTests.swift`
- [ ] T023 [P] [US2] Extend local purge acknowledgement boundary tests in `apps/macos/Shared/Tests/DesktopLocalPurgeTests.swift`

### Implementation for User Story 2

- [ ] T024 [US2] Record desktop first-surface evidence or blocker in `docs/evidence/034-mvp-loop-readiness/screenshots/desktop-first-surface-evidence.md`
- [ ] T025 [US2] Record desktop embedded detail evidence or blocker in `docs/evidence/034-mvp-loop-readiness/screenshots/desktop-embedded-detail-evidence.md`
- [ ] T026 [US2] Add desktop evidence records and related gaps in `apps/server/src/twobrain_rec_server/readiness/report.py`
- [ ] T027 [US2] Update desktop evidence and claim sections in `docs/evidence/034-mvp-loop-readiness/readiness-report.md`

**Checkpoint**: US2 is complete when desktop evidence proves or truthfully blocks workspace-first behavior, native Record/Stop authority, embedded route boundaries, and local purge limits.

---

## Phase 5: User Story 3 - Confirm Web Cabinet Review And Governance Fit The Reference IA (Priority: P2)

**Goal**: Verify web and desktop-embedded review surfaces against the owned IA and clean-room reference lessons without copying Krisp visuals, copy, assets, or private content.

**Independent Test**: Review web/embedded evidence and reference comparison records; every action is `available`, `policy-gated`, `truthful placeholder`, or `out of scope`.

### Tests for User Story 3

- [ ] T028 [P] [US3] Add reference-comparison validation coverage in `apps/server/tests/unit/test_mvp_loop_readiness_matrix.py`
- [ ] T029 [P] [US3] Extend web shell and lifecycle state regression coverage in `apps/server/tests/unit/test_cabinet_web_shell.py`
- [ ] T030 [P] [US3] Extend meeting list/detail regression coverage in `apps/server/tests/integration/test_cabinet_meeting_list.py`
- [ ] T031 [P] [US3] Extend meeting detail transcript/playback/provenance coverage in `apps/server/tests/integration/test_cabinet_meeting_detail.py`

### Implementation for User Story 3

- [ ] T032 [US3] Record web meeting-list evidence or blocker in `docs/evidence/034-mvp-loop-readiness/screenshots/web-meeting-list-evidence.md`
- [ ] T033 [US3] Record web meeting-detail evidence or blocker in `docs/evidence/034-mvp-loop-readiness/screenshots/web-meeting-detail-evidence.md`
- [ ] T034 [US3] Record clean-room reference lessons and forbidden-similarity results in `docs/evidence/034-mvp-loop-readiness/reference-comparison.md`
- [ ] T035 [US3] Add reference comparison records to `apps/server/src/twobrain_rec_server/readiness/report.py`
- [ ] T036 [US3] Update web, embedded, and clean-room sections in `docs/evidence/034-mvp-loop-readiness/readiness-report.md`

**Checkpoint**: US3 is complete when the report shows discoverable review/governance surfaces, lifecycle state truth, and zero committed Krisp private/copy evidence.

---

## Phase 6: User Story 4 - Exercise Policy And Lifecycle Boundaries Before Pilot (Priority: P2)

**Goal**: Verify that access, sharing, downloads, export, retention, deletion, local purge, and dependency limits are visible and not overclaimed.

**Independent Test**: Run the access/egress/deletion regressions and inspect the readiness report for owner/team/shared/denied/policy/deleted/deleting/local-purge states.

### Tests for User Story 4

- [ ] T037 [P] [US4] Extend access/sharing/download bounded-claim coverage in `apps/server/tests/contract/test_access_sharing_downloads_contract.py`
- [ ] T038 [P] [US4] Extend retention/deletion execution truth coverage in `apps/server/tests/contract/test_retention_deletion_contract.py`
- [ ] T039 [P] [US4] Extend deletion report copy and dependency-state view-model coverage in `apps/server/tests/unit/test_deletion_report_view_models.py`
- [ ] T040 [P] [US4] Extend local purge coordination integration coverage in `apps/server/tests/integration/test_local_purge_coordination.py`

### Implementation for User Story 4

- [ ] T041 [US4] Add policy, access, egress, retention, deletion, and local-purge stage records in `apps/server/src/twobrain_rec_server/readiness/matrix.py`
- [ ] T042 [US4] Add policy and lifecycle evidence records in `apps/server/src/twobrain_rec_server/readiness/report.py`
- [ ] T043 [US4] Record policy and lifecycle evidence limitations in `docs/evidence/034-mvp-loop-readiness/policy-lifecycle-evidence.md`
- [ ] T044 [US4] Update access, egress, retention, and deletion truth sections in `docs/evidence/034-mvp-loop-readiness/readiness-report.md`

**Checkpoint**: US4 is complete when 034 distinguishes controlled storage, local desktop purge, backup expiry, MediaScribe, Langfuse, workflow/temp payloads, diagnostics, and post-egress limits.

---

## Phase 7: User Story 5 - Produce A Launch Gap Register And Next-Slice Decision (Priority: P3)

**Goal**: Produce a concrete gap register and update product status so the next Spec Kit slice is evidence-based.

**Independent Test**: Inspect the gap register and product status; every P0/P1 gap has a next action or explicit deferral and completed slices are no longer listed as future work.

### Tests for User Story 5

- [ ] T045 [P] [US5] Add launch-gap sorting, severity, and next-action coverage in `apps/server/tests/unit/test_mvp_loop_readiness_matrix.py`
- [ ] T046 [P] [US5] Add report coverage for next-slice recommendation and stale-status prevention in `apps/server/tests/integration/test_mvp_loop_readiness_report.py`

### Implementation for User Story 5

- [ ] T047 [US5] Seed required launch blockers for mute truth, signed installer evidence, browser target gaps, live app evidence, and notes/action output in `apps/server/src/twobrain_rec_server/readiness/matrix.py`
- [ ] T048 [US5] Generate the launch gap register in `docs/evidence/034-mvp-loop-readiness/launch-gap-register.md`
- [ ] T049 [US5] Update completed-slice status and the next product slice in `docs/current-product-status.md`
- [ ] T050 [US5] Add the 034 readiness gate entry in `CHANGELOG.md`
- [ ] T051 [US5] Update final bounded outcome and next-slice recommendation in `docs/evidence/034-mvp-loop-readiness/readiness-report.md`

**Checkpoint**: US5 is complete when a reviewer can choose the next slice from evidence rather than intuition.

---

## Phase 8: Polish And Cross-Cutting Validation

**Purpose**: Prove the feature is safe to review, merge, and deploy within the strongest evidence boundary actually achieved.

- [ ] T052 [P] Run focused readiness tests and record results in `docs/evidence/034-mvp-loop-readiness/validation-log.md`
- [ ] T053 [P] Run web cabinet and lifecycle regression tests and record results in `docs/evidence/034-mvp-loop-readiness/validation-log.md`
- [ ] T054 [P] Run macOS desktop shell regression tests and record results in `docs/evidence/034-mvp-loop-readiness/validation-log.md`
- [ ] T055 Run forbidden-content text and screenshot payload scans and record results in `docs/evidence/034-mvp-loop-readiness/validation-log.md`
- [ ] T056 Run local repository CI and record `ci_local_result` in `docs/evidence/034-mvp-loop-readiness/validation-log.md`
- [ ] T057 Run production health or CD/smoke boundary checks and record the strongest valid claim in `docs/evidence/034-mvp-loop-readiness/validation-log.md`
- [ ] T058 Review `specs/034-mvp-loop-readiness/checklists/` against completed evidence and update blockers in `specs/034-mvp-loop-readiness/tasks.md`
- [ ] T059 Verify GitHub issue traceability after `$speckit-taskstoissues` in `docs/evidence/034-mvp-loop-readiness/validation-log.md`

---

## Dependencies And Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: No dependencies.
- **Foundational (Phase 2)**: Depends on Setup and blocks all user stories.
- **US1 and US2 (P1)**: Start after Foundational; both are required for MVP loop truth.
- **US3 and US4 (P2)**: Start after Foundational; may run after or alongside P1 work, but final claims depend on P1 evidence.
- **US5 (P3)**: Depends on current findings from US1-US4.
- **Polish (Phase 8)**: Depends on all selected story tasks and must run before acceptance.

### User Story Dependencies

- **US1**: No dependency on other stories after Foundational; creates the report spine.
- **US2**: No dependency on other stories after Foundational; adds desktop evidence.
- **US3**: Depends on Foundational and benefits from US1 report spine.
- **US4**: Depends on Foundational and benefits from US1 report spine.
- **US5**: Depends on US1-US4 findings.

### Parallel Opportunities

- T002, T003, and T004 can run in parallel after T001.
- T005, T006, and T007 can run in parallel.
- Story-specific test tasks marked `[P]` can run in parallel because they touch separate test files.
- Desktop evidence tasks and web evidence tasks can run in parallel after the readiness report spine exists.
- Validation tasks T052, T053, and T054 can run in parallel, then T055-T057 must reconcile final evidence.

## Parallel Example: User Story 2

```text
Task: "T020 [P] [US2] Extend workspace-first and native-control boundary tests in apps/macos/Shared/Tests/DesktopCabinetWorkspaceTests.swift"
Task: "T021 [P] [US2] Extend cabinet unavailable/auth route policy tests in apps/macos/Shared/Tests/DesktopCabinetRoutePolicyTests.swift"
Task: "T022 [P] [US2] Extend upload-to-review identity continuity tests in apps/macos/Shared/Tests/DesktopCabinetUploadLinkTests.swift"
Task: "T023 [P] [US2] Extend local purge acknowledgement boundary tests in apps/macos/Shared/Tests/DesktopLocalPurgeTests.swift"
```

## Implementation Strategy

### MVP First

1. Complete Phase 1 and Phase 2.
2. Complete US1 and US2.
3. Validate that the MVP loop report exists and desktop evidence is either proven or explicitly blocked.
4. Stop and review if any P0/P1 launch blocker lacks a next action.

### Full Readiness Pass

1. Complete US1-US4 evidence and bounded claim generation.
2. Complete US5 gap register and product-status update.
3. Run Phase 8 validation.
4. Only then proceed to final review, PR, merge, and production smoke.

## Notes

- Evidence must remain metadata-only and safe to commit.
- `infra_smoke_ready` is not pilot readiness or user rollout readiness.
- Krisp reference material may inform category-level IA comparison only; do not commit private Krisp captures or copy visual expression.
- Mark tasks `[X]` only after evidence or test output supports completion.
