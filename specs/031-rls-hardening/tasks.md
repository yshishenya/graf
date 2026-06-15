# Tasks: Backend Tenant Isolation RLS Hardening

**Input**: Design documents from `specs/031-rls-hardening/`

**Prerequisites**: [plan.md](./plan.md), [spec.md](./spec.md),
[research.md](./research.md), [data-model.md](./data-model.md),
[contracts/](./contracts/), [quickstart.md](./quickstart.md)

**Tests**: Required. This is a high-risk security/PostgreSQL RLS slice and the
spec requires positive same-tenant probes, negative cross-tenant probes,
missing-context probes, worker/maintenance probes, and rollout evidence.

**Organization**: Tasks are grouped by user story to enable independent
implementation and validation. Foundation tasks must finish before story work.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel because it touches different files and has no
  dependency on incomplete tasks.
- **[Story]**: User story label from [spec.md](./spec.md).
- Every task includes an exact repository path.

## Phase 1: Setup

**Purpose**: Prepare local task scaffolding and table inventory for the RLS
implementation.

- [ ] T001 [P] Create RLS table inventory fixture in `apps/server/tests/fixtures/rls.py`
- [ ] T002 [P] Create PostgreSQL RLS test helpers in `apps/server/tests/fixtures/postgres_rls.py`
- [ ] T003 [P] Create initial RLS evidence scan test in `apps/server/tests/contract/test_rls_evidence_contract.py`
- [ ] T004 Add feature validation command notes to `specs/031-rls-hardening/quickstart.md`

---

## Phase 2: Foundational

**Purpose**: Shared tenant-context and policy infrastructure that blocks all
user stories.

**Critical**: No user story work starts until this phase is complete.

### Tests First

- [ ] T005 [P] Add tenant-context unit tests in `apps/server/tests/unit/test_rls_tenant_context.py`
- [ ] T006 [P] Add migration helper contract tests in `apps/server/tests/contract/test_rls_policy_matrix_contract.py`
- [ ] T007 [P] Add PostgreSQL migration smoke test in `apps/server/tests/integration/test_rls_postgres_migrations.py`

### Implementation

- [ ] T008 Implement tenant database context helper in `apps/server/src/twobrain_rec_server/db/tenant_context.py`
- [ ] T009 Wire request tenant context into database sessions in `apps/server/src/twobrain_rec_server/auth/dependencies.py`
- [ ] T010 Add RLS helper SQL functions and rollback skeleton in `apps/server/src/twobrain_rec_server/db/migrations/versions/0005_rls_hardening.py`
- [ ] T011 Export tenant context helper symbols in `apps/server/src/twobrain_rec_server/db/__init__.py`
- [ ] T012 Add safe tenant access problem codes in `apps/server/src/twobrain_rec_server/api/problems.py`

**Checkpoint**: Tenant context can be set transaction-locally, migration helpers
exist, and PostgreSQL migration smoke coverage is ready.

---

## Phase 3: User Story 1 - Prevent Cross-Workspace Meeting Exposure (Priority: P1)

**Goal**: Meeting, upload, artifact, transcript, processing, audit, and
dependency rows remain invisible outside active workspace context.

**Independent Test**: Seed two workspaces with meeting-content rows, then prove
same-tenant access works, missing context fails closed, cross-tenant reads are
not found/empty, and cross-tenant writes/deletes are denied.

### Tests First

- [ ] T013 [P] [US1] Add API access-outcome contract tests in `apps/server/tests/contract/test_rls_access_outcomes.py`
- [ ] T014 [P] [US1] Add meeting-content RLS PostgreSQL probes in `apps/server/tests/integration/test_rls_meeting_content_policies.py`
- [ ] T015 [P] [US1] Add application boundary regression tests in `apps/server/tests/integration/test_rls_application_boundaries.py`

### Implementation

- [ ] T016 [US1] Add RLS policies for `meetings`, `upload_sessions`, `upload_parts`, `temporary_upload_objects`, `track_artifacts`, `manifest_snapshots`, and `ingest_audit_events` in `apps/server/src/twobrain_rec_server/db/migrations/versions/0005_rls_hardening.py`
- [ ] T017 [US1] Add RLS policies for `processing_placeholders`, `processing_workflows`, `mediascribe_jobs`, `processing_results`, `transcript_segments`, `diarization_segments`, `processing_audit_events`, and `processing_dependency_states` in `apps/server/src/twobrain_rec_server/db/migrations/versions/0005_rls_hardening.py`
- [ ] T018 [US1] Map cross-tenant read misses to not-found or empty responses in `apps/server/src/twobrain_rec_server/api/ingest.py`
- [ ] T019 [US1] Map cross-tenant processing status reads to not-found behavior in `apps/server/src/twobrain_rec_server/api/processing.py`
- [ ] T020 [US1] Add metadata-only denied-access evidence for meeting-content boundaries in `apps/server/src/twobrain_rec_server/ingest/audit.py`
- [ ] T021 [US1] Add metadata-only denied-access evidence for processing boundaries in `apps/server/src/twobrain_rec_server/processing/audit.py`

**Checkpoint**: US1 can be validated independently with the meeting-content
policy probes and API access-outcome contract tests.

---

## Phase 4: User Story 2 - Keep Workers And Internal Jobs Tenant-Scoped (Priority: P1)

**Goal**: Processing workers, smoke cleanup, migrations, backup/restore
rehearsals, and diagnostics run with explicit tenant or allowlisted maintenance
context.

**Independent Test**: Worker pickup/status/import paths pass for matching
context, fail for mismatched or missing context, and maintenance context is
allowed only for fixed operations with metadata-only evidence.

### Tests First

- [ ] T022 [P] [US2] Add worker tenant context tests in `apps/server/tests/integration/test_rls_worker_context.py`
- [ ] T023 [P] [US2] Add maintenance context tests in `apps/server/tests/integration/test_rls_maintenance_context.py`
- [ ] T024 [P] [US2] Add smoke-cleanup RLS regression tests in `apps/server/tests/integration/test_rls_smoke_cleanup_context.py`

### Implementation

- [ ] T025 [US2] Set worker tenant context for processing pickup in `apps/server/src/twobrain_rec_server/processing/pickup.py`
- [ ] T026 [US2] Set worker tenant context for processing status/store operations in `apps/server/src/twobrain_rec_server/processing/store.py`
- [ ] T027 [US2] Set worker tenant context for MediaScribe result import in `apps/server/src/twobrain_rec_server/mediascribe/import_results.py`
- [ ] T028 [US2] Add allowlisted maintenance context support in `apps/server/src/twobrain_rec_server/db/tenant_context.py`
- [ ] T029 [US2] Use maintenance context for smoke auth cleanup in `apps/server/scripts/cleanup_smoke_auth_session.py`
- [ ] T030 [US2] Use maintenance context for smoke artifact cleanup in `apps/server/scripts/cleanup_smoke_artifacts.py`

**Checkpoint**: US2 can be validated independently with worker and maintenance
context tests.

---

## Phase 5: User Story 3 - Protect Identity, Device, Session, And Membership Boundaries (Priority: P1)

**Goal**: Auth, device, session, membership, workspace policy, provider link,
callback, consent, and auth audit rows follow the same tenant isolation rules.

**Independent Test**: Seed users, sessions, devices, memberships, provider
identities, auth policies, and audit events across organizations/workspaces.
Prove each actor sees only allowed identity and policy records.

### Tests First

- [ ] T031 [P] [US3] Add identity/session RLS PostgreSQL probes in `apps/server/tests/integration/test_rls_identity_policies.py`
- [ ] T032 [P] [US3] Add auth API boundary contract tests in `apps/server/tests/contract/test_rls_auth_access_outcomes.py`
- [ ] T033 [P] [US3] Add stale/revoked context regression tests in `apps/server/tests/integration/test_rls_stale_session_device_context.py`

### Implementation

- [ ] T034 [US3] Add RLS policies for `organizations`, `workspaces`, `user_identities`, `workspace_memberships`, and `registered_devices` in `apps/server/src/twobrain_rec_server/db/migrations/versions/0005_rls_hardening.py`
- [ ] T035 [US3] Add RLS policies for `external_identities`, `auth_sessions`, `auth_session_device_bindings`, `workspace_auth_policies`, `workspace_provider_link_states`, `auth_callback_states`, `workspace_consent_copy`, and `auth_audit_events` in `apps/server/src/twobrain_rec_server/db/migrations/versions/0005_rls_hardening.py`
- [ ] T036 [US3] Ensure auth dependencies reject stale or revoked context before database access in `apps/server/src/twobrain_rec_server/auth/dependencies.py`
- [ ] T037 [US3] Add metadata-only denied-access auth audit evidence in `apps/server/src/twobrain_rec_server/auth/audit.py`

**Checkpoint**: US3 can be validated independently with identity/session policy
probes and auth access-outcome tests.

---

## Phase 6: User Story 4 - Roll Out Safely With Evidence And Rollback (Priority: P2)

**Goal**: Provide local and production-like validation evidence, halt/rollback
instructions, and an explicit separate decision field for live production
enforcement.

**Independent Test**: Run local and PostgreSQL validation with passing and
failing gates. Prove enforcement remains blocked until required probes pass and
live production enablement is not automatic.

### Tests First

- [ ] T038 [P] [US4] Add rollout gate tests in `apps/server/tests/integration/test_rls_rollout_gates.py`
- [ ] T039 [P] [US4] Add migration rollback contract tests in `apps/server/tests/contract/test_rls_migration_rollback_contract.py`
- [ ] T040 [P] [US4] Add production-boundary tests in `apps/server/tests/contract/test_rls_production_boundary.py`

### Implementation

- [ ] T041 [US4] Add RLS validation service in `apps/server/src/twobrain_rec_server/db/rls_validation.py`
- [ ] T042 [US4] Add RLS validation script in `apps/server/scripts/verify_rls_hardening.py`
- [ ] T043 [US4] Document rollout, halt, rollback, and live-production decision states in `docs/deployments/2brain-rec/rls-hardening-runbook.md`
- [ ] T044 [US4] Reference RLS validation without automatic enforcement in `infra/scripts/verify-rec-migration.sh`
- [ ] T045 [US4] Add RLS validation command to `infra/scripts/ci-local.sh`

**Checkpoint**: US4 can be validated independently with rollout gate tests and
the RLS hardening runbook.

---

## Phase 7: User Story 5 - Preserve Downstream Product Boundaries (Priority: P2)

**Goal**: Prepare future dashboard/share/download/retention/deletion work
without implementing those product surfaces.

**Independent Test**: Review routes, OpenAPI, tests, docs, and product status
to prove no new dashboard detail, share/download, deletion, retention, billing,
admin UI, desktop capture/upload, or MediaScribe behavior was added.

### Tests First

- [ ] T046 [P] [US5] Add out-of-scope route boundary tests in `apps/server/tests/contract/test_rls_out_of_scope_boundaries.py`
- [ ] T047 [P] [US5] Add future-table isolation contract tests in `apps/server/tests/contract/test_rls_future_table_contract.py`
- [ ] T048 [P] [US5] Add OpenAPI drift coverage for RLS-only scope in `apps/server/tests/contract/test_rls_openapi_scope.py`

### Implementation

- [ ] T049 [US5] Add future tenant-table guidance in `docs/adr/003-tenant-isolation-rls.md`
- [ ] T050 [US5] Update product status with RLS boundary and no rollout claim in `docs/current-product-status.md`
- [ ] T051 [US5] Add unreleased changelog entry for feature 031 in `CHANGELOG.md`
- [ ] T052 [US5] Update quickstart validation evidence notes in `specs/031-rls-hardening/quickstart.md`

**Checkpoint**: US5 can be validated independently with out-of-scope contract
tests and documentation review.

---

## Final Phase: Polish & Cross-Cutting

**Purpose**: Validation, cleanup, and traceability across the whole feature.

- [ ] T053 Run RLS quickstart validation and record command results in `specs/031-rls-hardening/quickstart.md`
- [ ] T054 Run full local CI and record pass/fail notes in `specs/031-rls-hardening/quickstart.md`
- [ ] T055 Review secret/content scan findings and record safe evidence in `specs/031-rls-hardening/quickstart.md`
- [ ] T056 Update final implementation notes in `specs/031-rls-hardening/tasks.md`

---

## Dependencies & Execution Order

## GitHub Issue Sync

- #716: T001-T012, foundation and RLS migration scaffold.
- #717: T013-T021, US1 meeting-content tenant isolation.
- #718: T022-T030, US2 worker and maintenance tenant context.
- #719: T031-T037, US3 identity, session, device, and membership boundaries.
- #720: T038-T045, US4 rollout gates, rollback, and production boundary.
- #721: T046-T052, US5 future isolation contract and downstream boundary.
- #722: T053-T056, final validation and evidence scan.

### Phase Dependencies

- **Setup (Phase 1)**: no dependencies.
- **Foundational (Phase 2)**: depends on Setup and blocks all user stories.
- **US1, US2, US3**: depend on Foundational. They are all P1 and may be
  developed in parallel only after coordination around the shared migration
  file.
- **US4**: depends on Foundational plus enough US1/US2/US3 policy coverage to
  exercise rollout gates.
- **US5**: depends on Foundational and can run in parallel with US4 after route
  and contract boundaries are known.
- **Final Phase**: depends on selected user stories being complete.

### User Story Dependencies

- **US1 (P1)**: MVP security value for meeting-content isolation.
- **US2 (P1)**: required before production-like processing/maintenance proof.
- **US3 (P1)**: required before claiming full current backend scope.
- **US4 (P2)**: requires policy coverage and validation evidence.
- **US5 (P2)**: requires final scope surface to document and protect future
  work.

### Parallel Opportunities

- T001, T002, T003 can run in parallel.
- T005, T006, T007 can run in parallel.
- Test files inside each story marked `[P]` can be created in parallel.
- US2 and US3 implementation can proceed alongside US1 only if migration-file
  edits are coordinated or serialized.
- Documentation tasks T049, T050, T051, T052 touch different files and can be
  assigned separately after US5 tests exist.

---

## Parallel Example: User Story 1

```text
Task: "T013 [US1] Add API access-outcome contract tests in apps/server/tests/contract/test_rls_access_outcomes.py"
Task: "T014 [US1] Add meeting-content RLS PostgreSQL probes in apps/server/tests/integration/test_rls_meeting_content_policies.py"
Task: "T015 [US1] Add application boundary regression tests in apps/server/tests/integration/test_rls_application_boundaries.py"
```

## Parallel Example: User Story 3

```text
Task: "T031 [US3] Add identity/session RLS PostgreSQL probes in apps/server/tests/integration/test_rls_identity_policies.py"
Task: "T032 [US3] Add auth API boundary contract tests in apps/server/tests/contract/test_rls_auth_access_outcomes.py"
Task: "T033 [US3] Add stale/revoked context regression tests in apps/server/tests/integration/test_rls_stale_session_device_context.py"
```

---

## Implementation Strategy

### MVP First

1. Complete Setup and Foundational tasks.
2. Complete US1 to protect meeting-content rows before future dashboard/review
   work.
3. Validate US1 independently with access-outcome and PostgreSQL policy probes.

### Full Current Backend Scope

1. Add US2 worker/maintenance context coverage.
2. Add US3 identity/session/device coverage.
3. Add US4 rollout gates and runbook.
4. Add US5 downstream-boundary documentation and tests.

### Commit Strategy

- Commit generated Spec Kit artifacts after each Spec Kit phase.
- Do not commit implementation code until validation for the implementation
  slice passes and the user approves the implementation commit.

## Notes

- `[P]` means the task touches a different file and has no dependency on an
  incomplete task.
- Tasks that modify `0005_rls_hardening.py` are intentionally serialized to
  avoid migration conflicts.
- Live production enforcement is not part of these tasks.
