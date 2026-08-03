# Tasks: transcript-export-recovery

**Input**: Design documents from `/specs/137-transcript-export-recovery/`

**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`,
`contracts/transcript-summary-recovery.md`, `quickstart.md`

**Tests**: Required by the high-risk validation lane. Focused tests must be
written before the matching implementation task and pass before the task is
marked complete.

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Prepare the existing maintenance boundary for a bounded outcome
reconcile. This requires only the RLS maintenance helper update; no data schema
change or new dependency is needed.

- [X] T001 [P] Register `outcome_initial_baseline_reconciliation` as an allowed maintenance operation in `apps/server/src/twobrain_rec_server/db/tenant_context.py`, `apps/server/src/twobrain_rec_server/db/migrations/versions/0043_outcome_initial_baseline_reconciliation.py`, and the RLS allowlist tests in `apps/server/tests/contract/test_rls_policy_matrix_contract.py`, `apps/server/tests/fixtures/rls.py`, and `apps/server/tests/unit/test_rls_tenant_context.py`.

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: No additional blocking foundation is required; the feature reuses
the existing egress, outcome, result/revision fence and tenant-context layers.

## Phase 3: User Story 1 - Owner downloads ready content (Priority: P1) 🎯 MVP

**Goal**: A meeting without an explicit artifact-policy row exposes ready
transcript/summary/package actions to the owner while preserving explicit deny
and non-owner blocks.

**Independent Test**: A synthetic ready owner meeting with no policy row returns
available owner transcript state and can export it; a permitted non-owner and an
explicit `meeting_override=disabled` remain blocked.

### Tests for User Story 1

- [X] T002 [P] [US1] Add no-row owner, permitted non-owner and explicit-deny regression coverage for transcript/summary/package capability and download states in `apps/server/tests/integration/test_artifact_egress_policy.py` and `apps/server/tests/integration/test_transcript_export_egress.py`.

### Implementation for User Story 1

- [X] T003 [US1] Add one effective implicit owner-only policy helper and route content capabilities plus artifact states through it in `apps/server/src/twobrain_rec_server/cabinet/egress.py`, leaving `meeting_override` values unchanged.

## Phase 4: User Story 2 - First summary is usable without replacing accepted history (Priority: P1)

**Goal**: The trusted processing import publishes a valid first deterministic
baseline when no accepted outcome exists; later revisions and accepted history
retain candidate review semantics.

**Independent Test**: A revision-scoped ready fixture becomes current only with
the trusted publish flag, repeated reconciliation is idempotent, and an existing
accepted pointer is unchanged.

### Tests for User Story 2

- [X] T004 [P] [US2] Add trusted-import publication, candidate-promotion and accepted-history preservation tests in `apps/server/tests/integration/test_meeting_outcomes_generation.py`.

### Implementation for User Story 2

- [X] T005 [US2] Add the opt-in `publish_initial_baseline` argument, deterministic-candidate guard, attempt-state update and idempotent pointer transition in `apps/server/src/twobrain_rec_server/outcomes/service.py`.
- [X] T006 [US2] Pass `publish_initial_baseline=True` only from the successful trusted MediaScribe import path in `apps/server/src/twobrain_rec_server/processing/submit.py`.
- [X] T007 [US2] Implement metadata-only dry-run and explicit `--execute` bounded reconciliation for eligible meetings in `apps/server/scripts/reconcile_initial_outcomes.py`, using `outcome_initial_baseline_reconciliation` tenant context and the fenced outcome service.

## Phase 5: User Story 3 - AI source references recover safely (Priority: P1)

**Goal**: A valid pinned segment ID with a provider sequence mismatch is
canonicalized, while unknown or malformed references still fail closed.

**Independent Test**: The validator returns the stored sequence for a known ID
and raises for unknown ID, missing fields, invalid type or negative sequence.

### Tests for User Story 3

- [X] T008 [P] [US3] Update source-reference validation coverage for canonical sequence recovery, unknown-ID rejection and preserving an existing accepted result after candidate validation failure in `apps/server/tests/unit/test_outcome_prompts.py` and `apps/server/tests/unit/test_summary_candidate_revisions.py`.

### Implementation for User Story 3

- [X] T009 [US3] Canonicalize known segment sequences after validating source ownership, without weakening structure or unknown-ID checks, in `apps/server/src/twobrain_rec_server/outcomes/prompts.py`.

## Phase 6: User Story 4 - Processing readiness is truthful (Priority: P2)

**Goal**: The processed result drives ready review/export state even when the
legacy immutable meeting lifecycle status remains pending.

**Independent Test**: A synthetic meeting with processed result and pending
meeting status produces ready view-model state and does not mutate the meeting
status during outcome reconciliation.

### Tests for User Story 4

- [X] T010 [P] [US4] Add or strengthen the pending-meeting-status/processed-result regression in `apps/server/tests/unit/test_recording_workflow_view_model.py` and `apps/server/tests/integration/test_meeting_outcomes_generation.py`.

### Implementation for User Story 4

- [X] T011 [US4] Confirm the existing `review_status()` and processing import path consume `processing_status`/imported result without changing `Meeting.status`, and record the no-runtime-change invariant in `specs/137-transcript-export-recovery/quickstart.md`.

## Phase 7: Polish & Cross-Cutting Concerns

**Purpose**: Record behavior changes and execute the selected validation lane.

- [X] T012 [P] Add the owner-default content egress, trusted baseline publication, source-reference recovery and bounded reconcile notes to `CHANGELOG.md`.
- [X] T013 Run `git diff --check`, the focused pytest commands from `specs/137-transcript-export-recovery/quickstart.md`, and `infra/scripts/ci-local.sh --fast`; record evidence without transcript/audio content in `specs/137-transcript-export-recovery/quickstart.md` if command details need updating.

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: T001 is independent and must complete before the
  maintenance script is used.
- **Foundational (Phase 2)**: no additional tasks; existing platform foundation
  is the prerequisite.
- **User Stories**: US1, US2 and US3 can be implemented in parallel after
  setup; US4 is a regression-only confirmation and can run in parallel.
- **Polish (Phase 7)**: depends on the selected user stories and validation.

### User Story Dependencies

- **US1**: independent; it changes only the shared egress decision.
- **US2**: independent of US1/US3; it uses existing outcome provenance and
  processing import paths.
- **US3**: independent; it changes only shared AI output validation.
- **US4**: independent regression evidence; no lifecycle mutation is planned.

### Parallel Opportunities

- T002/T004/T008/T010 can be written in parallel because they touch separate
  test concerns.
- After T001, US1, US2 and US3 implementation streams can proceed in parallel;
  T007 follows T005.
- T012 waits for code behavior to settle; T013 is the final validation gate.

## Implementation Strategy

### MVP First (User Story 1)

1. Complete T001.
2. Complete T002-T003 and validate owner/no-policy egress independently.
3. Continue with US2/US3 before any production rollout because the original
   incident includes both missing export policy and unusable summary recovery.

### Incremental Delivery

1. Land effective owner-only content policy with explicit deny tests.
2. Land trusted initial-baseline publication and bounded historical reconcile.
3. Land source-reference canonicalization with strict unknown-ID rejection.
4. Confirm readiness semantics, update changelog, and run the fast lane.

## Notes

- `[P]` means tasks use separate files and can run in parallel.
- Every task names the exact source/test/document path it changes or validates.
- No task authorizes a production deploy or production database write; those
  remain a separate approval-gated operation.
