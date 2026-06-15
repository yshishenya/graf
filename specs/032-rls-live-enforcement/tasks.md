# Tasks: RLS Production Enforcement Truth

**Input**: Design documents from `specs/032-rls-live-enforcement/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md),
[research.md](./research.md), [data-model.md](./data-model.md),
[contracts/](./contracts/), [quickstart.md](./quickstart.md)

**Tests**: Required. This is a high-risk security/production truth slice. Test
tasks must precede implementation tasks for validation output, production
read-only RLS state, and stale wording remediation.

**Organization**: Tasks are grouped by user story to enable independent
implementation and validation.

## Phase 1: Setup

**Purpose**: Prepare traceable fixtures and contract-test scaffolding.

- [X] T001 [P] Add production RLS truth fixture helpers in `apps/server/tests/fixtures/rls_production_truth.py`
- [X] T002 [P] Add 032 validation command sections in `specs/032-rls-live-enforcement/quickstart.md`
- [X] T003 Add 032 stale-wording scan sections in `specs/032-rls-live-enforcement/quickstart.md`

---

## Phase 2: Foundational

**Purpose**: Establish one covered-table inventory and output vocabulary used
by all stories.

**Critical**: No user story implementation starts until this phase is complete.

### Tests First

- [X] T004 [P] Add covered table inventory contract tests in `apps/server/tests/contract/test_rls_table_inventory_contract.py`
- [X] T005 [P] Add validation output vocabulary tests in `apps/server/tests/contract/test_rls_validation_output_contract.py`

### Implementation

- [X] T006 Extract canonical RLS covered table inventory in `apps/server/src/twobrain_rec_server/db/rls_validation.py`
- [X] T007 Update RLS validation report states in `apps/server/src/twobrain_rec_server/db/rls_validation.py`
- [X] T008 Update validation script output mapping in `apps/server/scripts/verify_rls_hardening.py`

**Checkpoint**: Table inventory and validation output vocabulary are stable
for story work.

---

## Phase 3: User Story 1 - Preserve Test Gate Before Production Claims (Priority: P1)

**Goal**: Destructive same/cross-tenant RLS probes remain limited to
disposable or explicit test databases and no longer imply production RLS is
disabled.

**Independent Test**: Run the validation script without a test DB, with a fake
live DB URL, and with contract tests proving test output is test-scoped.

### Tests First

- [X] T009 [P] [US1] Update live database guard tests in `apps/server/tests/contract/test_rls_production_boundary.py`
- [X] T010 [P] [US1] Add disposable/test probe output tests in `apps/server/tests/contract/test_rls_validation_output_contract.py`

### Implementation

- [X] T011 [US1] Preserve live `twobrain_rec` destructive probe blocking in `apps/server/scripts/verify_rls_hardening.py`
- [X] T012 [US1] Replace ambiguous test-mode `live_production_enforcement=not_changed` output in `apps/server/src/twobrain_rec_server/db/rls_validation.py`
- [X] T013 [US1] Update disposable/test validation notes in `specs/031-rls-hardening/quickstart.md`
- [X] T014 [US1] Update 032 test-gate validation evidence notes in `specs/032-rls-live-enforcement/quickstart.md`

**Checkpoint**: US1 proves test/disposable validation remains safe and
truthful independently of production state.

---

## Phase 4: User Story 2 - Verify Production RLS Is Actually Enabled (Priority: P1)

**Goal**: Operators can prove production RLS enabled/forced state through
read-only catalog metadata.

**Independent Test**: Run contract tests against fake table-state inputs and
run the production read-only inspection command to produce metadata-only
evidence.

### Tests First

- [X] T015 [P] [US2] Add production RLS state contract tests in `apps/server/tests/contract/test_rls_production_state_contract.py`
- [X] T016 [P] [US2] Add production verifier CLI tests in `apps/server/tests/contract/test_rls_production_boundary.py`

### Implementation

- [X] T017 [US2] Implement covered-table state evaluation in `apps/server/src/twobrain_rec_server/db/rls_validation.py`
- [X] T018 [US2] Add production read-only verification mode in `apps/server/scripts/verify_rls_hardening.py`
- [X] T019 [US2] Add remote-safe production state helper command documentation in `docs/deployments/2brain-rec/rls-hardening-runbook.md`
- [X] T020 [US2] Record production read-only state evidence in `specs/032-rls-live-enforcement/quickstart.md`

**Checkpoint**: US2 can independently prove production RLS enabled/forced
state without customer-row access or mutation.

---

## Phase 5: User Story 3 - Correct Stale 031 Rollout Language (Priority: P1)

**Goal**: Stale `031` wording no longer says production RLS is still separate
or unchanged when production metadata proves enabled/forced.

**Independent Test**: Run stale-language scan tests and review required docs
for current production truth.

### Tests First

- [X] T021 [P] [US3] Add stale rollout wording tests in `apps/server/tests/contract/test_rls_rollout_truth_docs.py`
- [X] T022 [US3] Add product status truth tests in `apps/server/tests/contract/test_rls_rollout_truth_docs.py`

### Implementation

- [X] T023 [US3] Update RLS production status in `docs/current-product-status.md`
- [X] T024 [US3] Update RLS production decision wording in `docs/adr/003-tenant-isolation-rls.md`
- [X] T025 [US3] Update RLS runbook production truth wording in `docs/deployments/2brain-rec/rls-hardening-runbook.md`
- [X] T026 [US3] Update 031 analysis or quickstart historical wording in `specs/031-rls-hardening/quickstart.md`
- [X] T027 [US3] Update unreleased changelog with 032 production truth correction in `CHANGELOG.md`

**Checkpoint**: US3 can independently prove stale wording is corrected or
scoped as historical/test-only.

---

## Phase 6: User Story 4 - Keep Status And Changelog Truthful (Priority: P2)

**Goal**: Closeout evidence states exactly whether production is verified
enabled, verification is blocked, halted, rolled back, or unchanged.

**Independent Test**: Run final quickstart checks and verify all status docs
and evidence scans pass without forbidden content.

### Tests First

- [X] T028 [P] [US4] Add quickstart closeout evidence contract tests in `apps/server/tests/contract/test_rls_production_truth_contract.py`
- [X] T029 [US4] Add forbidden content regression coverage for 032 evidence in `apps/server/tests/contract/test_rls_production_truth_contract.py`

### Implementation

- [X] T030 [US4] Update 032 closeout evidence section in `specs/032-rls-live-enforcement/quickstart.md`
- [X] T031 [US4] Update deployment evidence scan expectations in `apps/server/src/twobrain_rec_server/deployment.py`
- [X] T032 [US4] Record final task/evidence notes in `specs/032-rls-live-enforcement/tasks.md`

**Checkpoint**: US4 gives a truthful closeout path for production-enabled or
blocked outcomes.

---

## Final Phase: Polish & Cross-Cutting

**Purpose**: Run the planned gates and record safe evidence.

- [X] T033 Run focused RLS production truth tests and record results in `specs/032-rls-live-enforcement/quickstart.md`
- [X] T034 Run `./infra/scripts/ci-local.sh` and record result in `specs/032-rls-live-enforcement/quickstart.md`
- [X] T035 Run production read-only RLS state inspection and record metadata-only result in `specs/032-rls-live-enforcement/quickstart.md`
- [X] T036 Run stale-language scan and record remaining justified matches in `specs/032-rls-live-enforcement/quickstart.md`
- [X] T037 Run forbidden-content scan and record result in `specs/032-rls-live-enforcement/quickstart.md`

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: no dependencies.
- **Foundational (Phase 2)**: depends on Setup and blocks all user stories.
- **US1 and US2**: depend on Foundational. They can proceed in parallel after
  coordination around shared validation output files.
- **US3**: depends on US2 production truth vocabulary and can start after the
  verifier contract is clear.
- **US4**: depends on US1, US2, and US3.
- **Final Phase**: depends on all selected user stories.

### Parallel Opportunities

- T001 and T002 can run in parallel; T003 follows T002 because both touch
  `specs/032-rls-live-enforcement/quickstart.md`.
- T004-T005 can run in parallel.
- T009-T010 can run in parallel.
- T015-T016 can run in parallel.
- T021 and T022 run sequentially because both touch
  `apps/server/tests/contract/test_rls_rollout_truth_docs.py`.
- T028 and T029 run sequentially because both touch
  `apps/server/tests/contract/test_rls_production_truth_contract.py`.

### MVP Scope

MVP for this correction is US1 + US2: preserve safe test probes and add
read-only production RLS state verification. US3 is required before closeout
because stale docs are the user-visible bug. US4 is required before final
merge.

## GitHub Issue Sync

Issues must use `docs/github-issue-canon.md`, Russian issue text, and labels:
`feature:032`, `type:hardening`, `area:security` or `area:infra`, and the
appropriate priority/gate labels.

Created issues:

- #737: T001-T008 foundation, covered table inventory, validation vocabulary.
- #738: T009-T014 safe disposable/test RLS probe gate.
- #739: T015-T020 production read-only RLS state verifier.
- #740: T021-T027 stale 031 production RLS wording correction.
- #741: T028-T032 closeout evidence and forbidden-content safety.
- #742: T033-T037 final RLS truth validation gates.

Implementation evidence recorded on 2026-06-15:

- Focused 032 RLS truth tests: `31 passed`.
- Full local CI: `336 passed, 4 skipped`; Ruff, Python compile, production
  Compose config, RLS boundary, and deployment evidence scan passed.
- Production read-only metadata inspection: remote commit `3fd2162f9899`,
  Alembic `0005_rls_hardening (head)`, `covered_table_count=28`,
  `rls_enabled_and_forced_count=28`, `failed_table_names=none`.
- Stale-language scan: remaining matches are historical `031` artifacts or
  negative tests/scanner rules; current status, ADR, runbook, changelog, and
  command output are corrected.
- Forbidden-content scan: remaining matches are approved deployment paths,
  code field names, placeholders, or redaction negative tests; deployment
  evidence scan passed.
