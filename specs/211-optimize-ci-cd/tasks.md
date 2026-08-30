# Tasks: Быстрый и доказуемый CI/CD

**Input**: Design documents from `specs/211-optimize-ci-cd/`
**Tests**: Required by FR-011 and the user request to re-check all behavior before rollout.

## Phase 1: Setup

**Purpose**: Freeze the executable contract and current drift baseline.

- [X] T001 Record the approved scope, receipt boundary and immutable-image exclusion in `specs/211-optimize-ci-cd/spec.md`, `plan.md`, `research.md` and `contracts/ci-cd-cli.md`
- [X] T002 Inventory ambiguous active CI commands and current deploy/full behavior in `specs/211-optimize-ci-cd/quickstart.md`
- [X] T003 Capture one pre-change explicit full-lane stage/test timing baseline in `specs/211-optimize-ci-cd/quickstart.md`

---

## Phase 2: Foundational

**Purpose**: Add reusable evidence primitives before changing lane/deploy behavior.

- [X] T004 Add failing CLI, receipt, deploy-fallback and documentation contract cases in `apps/server/tests/contract/test_ci_cd_contract.py`
- [X] T005 Implement versioned exact-input receipt create/validate/path commands with atomic metadata-only storage in `infra/scripts/ci-receipt.py`
- [X] T006 Extend full server test metadata and configurable performance-gate semantics in `apps/server/scripts/run_local_postgres_tests.sh`

**Checkpoint**: Receipt and test-runner contracts pass independently; no deploy path changed yet.

---

## Phase 3: User Story 1 — Быстрая проверка небольшого изменения (Priority: P1) 🎯 MVP

**Goal**: Require an explicit lane and avoid unrelated component work while failing closed on ambiguity.

**Independent Test**: Bare invocation exits before stages; known server/macOS/docs diffs select only required components; shared/unknown/high-risk diffs select full.

- [X] T007 [US1] Implement explicit `--fast`/`--full` parsing, `--help`, stage timings and final-result trap in `infra/scripts/ci-local.sh`
- [X] T008 [US1] Implement conservative changed-path component classification and full escalation in `infra/scripts/ci-local.sh`
- [X] T009 [US1] Connect server, macOS and documentation stage selection without duplicate stages in `infra/scripts/ci-local.sh`
- [X] T010 [US1] Complete missing-mode, component-union and escalation contract assertions in `apps/server/tests/contract/test_ci_cd_contract.py`

**Checkpoint**: User Story 1 is runnable without receipt reuse or deploy modification.

---

## Phase 4: User Story 2 — Один доказанный полный прогон на release candidate (Priority: P1)

**Goal**: Create and safely reuse a full-CI receipt for one unchanged exact release candidate.

**Independent Test**: A clean disposable repository creates and validates a receipt; stale, dirty, malformed and every input mismatch reject it; deploy reuses valid evidence and otherwise invokes full fallback.

- [X] T011 [US2] Capture successful full result, collection metadata and receipt creation/dirty-tree skip in `infra/scripts/ci-local.sh`
- [X] T012 [US2] Replace tracked-only cleanliness with tracked-and-untracked cleanliness and add receipt reuse/full fallback in `infra/scripts/cd-remote.sh`
- [X] T013 [US2] Preserve incident-only `--skip-local-ci` and all remote production steps while updating dry-run evidence in `infra/scripts/cd-remote.sh`
- [X] T014 [US2] Complete valid, stale, malformed, dirty, SHA/tree/runner/lock/test/toolchain mismatch and deploy fallback tests in `apps/server/tests/contract/test_ci_cd_contract.py`

**Checkpoint**: User Story 2 proves one-full-run behavior locally without contacting production.

---

## Phase 5: User Story 3 — Понятная диагностика времени и результата (Priority: P2)

**Goal**: Make cost, selection and failure visible and isolate host-load-sensitive timing noise.

**Independent Test**: Successful and failing stubbed stages produce one final result plus stage durations; ordinary unrelated full reports a performance-only miss without false functional failure, while related/controlled runs require it.

- [X] T015 [US3] Add stable requested/effective lane, component, reason, per-stage and total-duration output contracts in `infra/scripts/ci-local.sh`
- [X] T016 [US3] Keep performance setup/database/functional failures hard while making only the load-sensitive p95 threshold report-only by default in `apps/server/scripts/run_local_postgres_tests.sh` and the marked test
- [X] T017 [US3] Select the hard performance threshold for related calendar paths, explicit controlled runs and synchronized-master full fallback in `infra/scripts/ci-local.sh`
- [X] T018 [US3] Add timing, failure-trap and performance-gate contract assertions in `apps/server/tests/contract/test_ci_cd_contract.py`

**Checkpoint**: Timing diagnostics cannot generate a passing receipt after any hard-stage failure.

---

## Phase 6: User Story 4 — Документация совпадает с исполняемым контрактом (Priority: P2)

**Goal**: Give operators one current focused → fast → full → receipt-aware deploy workflow.

**Independent Test**: Active guidance/template scan has no ambiguous bare command and every stated behavior matches CLI output/contracts; historical evidence remains untouched.

- [X] T019 [P] [US4] Update risk lanes, full receipt reuse, fallback, batching guidance and performance boundary in `docs/agent-guidance/release-and-validation.md`
- [X] T020 [P] [US4] Update operator command examples and deploy description in `infra/scripts/README.md` and `AGENTS.md`
- [X] T021 [P] [US4] Update validation evidence fields and explicit lanes in `.github/pull_request_template.md`
- [X] T022 [US4] Add active-document consistency enforcement and historical-path exclusions in `apps/server/tests/contract/test_ci_cd_contract.py`
- [X] T023 [US4] Record the implemented current-state boundary and operational change in `docs/current-product-status.md` and `CHANGELOG.md`

**Checkpoint**: Active docs, help, contracts and code describe the same behavior.

---

## Phase 7: Polish & Cross-Cutting Validation

**Purpose**: Reconcile every surface and produce proportionate high-risk evidence.

- [X] T024 Run shell/Python static checks and the focused contract suite from `specs/211-optimize-ci-cd/quickstart.md`
- [X] T025 Run `infra/scripts/ci-local.sh --fast` and record its conservative effective lane/result in `specs/211-optimize-ci-cd/quickstart.md`
- [X] T026 Run `infra/scripts/ci-local.sh --full` and record stage/test/timing/dirty-receipt evidence in `specs/211-optimize-ci-cd/quickstart.md`
- [X] T027 Run `infra/scripts/cd-remote.sh --dry-run --branch 211-optimize-ci-cd` and final docs/code consistency scan, then record results in `specs/211-optimize-ci-cd/quickstart.md`
- [X] T028 Measure component-only fast p50, perform a final spec/plan/tasks/code/docs/contract diff audit and record findings in `specs/211-optimize-ci-cd/analysis.md`

---

## Dependencies & Execution Order

- Phase 1 → Phase 2 → all user stories.
- US1 depends on T003 and T005; it is the smallest independently useful slice.
- US2 depends on T004 plus the full-lane path from US1.
- US3 depends on US1 timing infrastructure and T005 performance controls.
- US4 may begin after the contracts stabilize; T018–T020 are parallel, then T021–T022 reconcile them.
- Final validation depends on US1–US4 complete.

## Parallel Opportunities

- After T004, T005 and T006 touch separate files but converge before US1/US2 integration.
- T019, T020 and T021 update independent active documentation surfaces.
- Static checks and documentation scan can run independently before the repository lanes.

## Implementation Strategy

1. Land the smallest safe behavior first: explicit lane plus conservative component selection.
2. Add local receipt reuse without changing any remote deployment stage.
3. Add diagnostics/performance isolation, then reconcile active docs.
4. Require focused contracts, explicit fast, explicit full and CD dry-run before calling the slice ready.

## Format Validation

- All 28 tasks use checkbox + sequential ID.
- Every user-story task has `[USn]`; parallel markers appear only on independent files.
- Every task names concrete repository paths.
