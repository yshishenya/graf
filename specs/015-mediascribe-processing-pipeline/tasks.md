# Tasks: MediaScribe Processing Pipeline

**Input**: Design documents from `specs/015-mediascribe-processing-pipeline/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/, quickstart.md

**Tests**: Required. This feature touches Temporal, MediaScribe, Postgres, MinIO, transcript content, secrets, audit, and deletion lifecycle truth.

**Organization**: Tasks are grouped by independently testable user story and should be executed in order unless marked `[P]`.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel because it touches different files and does not depend on incomplete work.
- **[Story]**: User story label for story-scoped tasks.
- Every task includes an exact path.

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Add runtime/development dependency hooks and processing module skeletons without changing behavior.

- [ ] T001 Add runtime dependencies for `httpx` and `temporalio` plus any required dev constraints in `apps/server/pyproject.toml`
- [ ] T002 [P] Add processing package exports in `apps/server/src/twobrain_rec_server/processing/__init__.py`
- [ ] T003 [P] Add MediaScribe package exports in `apps/server/src/twobrain_rec_server/mediascribe/__init__.py`
- [ ] T004 [P] Add workflow package exports in `apps/server/src/twobrain_rec_server/workflows/__init__.py`
- [ ] T005 Add processing configuration fields and production validation for MediaScribe/Temporal secrets in `apps/server/src/twobrain_rec_server/config.py`
- [ ] T006 [P] Add local fake MediaScribe helper scaffold in `apps/server/tests/fakes/fake_mediascribe.py`
- [ ] T007 [P] Add local fake Temporal helper scaffold in `apps/server/tests/fakes/fake_temporal.py`
- [ ] T008 Add processing env placeholders without live secrets in `apps/server/.env.example`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Create shared status vocabulary, persistent schema, schemas, and low-level utilities needed by every story.

**Critical**: No user story implementation starts until these tasks are complete.

- [ ] T009 Add processing status enums and MediaScribe status enums in `apps/server/src/twobrain_rec_server/domain/statuses.py`
- [ ] T010 [P] Add SQLAlchemy processing models in `apps/server/src/twobrain_rec_server/db/models/processing.py`
- [ ] T011 Add processing models to DB model exports in `apps/server/src/twobrain_rec_server/db/models/__init__.py`
- [ ] T012 Add Alembic migration for processing workflows, jobs, results, segments, audit events, and dependency states in `apps/server/src/twobrain_rec_server/db/migrations/versions/0004_mediascribe_processing_pipeline.py`
- [ ] T013 [P] Add processing Pydantic schemas in `apps/server/src/twobrain_rec_server/api/schemas.py`
- [ ] T014 [P] Add MediaScribe request/response schemas in `apps/server/src/twobrain_rec_server/mediascribe/schemas.py`
- [ ] T015 [P] Add processing reason-code constants in `apps/server/src/twobrain_rec_server/processing/reasons.py`
- [ ] T016 Add server-side MinIO read helpers for stored track artifacts in `apps/server/src/twobrain_rec_server/storage/minio_client.py`
- [ ] T017 [P] Add processing audit metadata builder in `apps/server/src/twobrain_rec_server/processing/audit.py`
- [ ] T018 Add processing persistence helpers in `apps/server/src/twobrain_rec_server/processing/store.py`
- [ ] T019 Add processing state transition helpers in `apps/server/src/twobrain_rec_server/processing/lifecycle.py`
- [ ] T020 [P] Add processing contract tests for OpenAPI status schema in `apps/server/tests/contract/test_processing_status_contract.py`
- [ ] T021 [P] Add MediaScribe client contract tests in `apps/server/tests/contract/test_mediascribe_client_contract.py`
- [ ] T022 [P] Add processing state-machine unit tests in `apps/server/tests/unit/test_processing_state_machine.py`
- [ ] T023 [P] Add processing migration integration tests in `apps/server/tests/integration/test_processing_migrations.py`
- [ ] T024 Verify foundational tests fail before implementation and record expected red state in `specs/015-mediascribe-processing-pipeline/quickstart.md`

**Checkpoint**: Foundation ready. User story implementation can now begin.

---

## Phase 3: User Story 1 - Start Processing After Finalized Ingest (Priority: P1) MVP

**Goal**: Eligible finalized meetings are picked up once, get an idempotent workflow id, and never process invalid or unauthorized meetings.

**Independent Test**: A finalized `ingested_pending_processing` meeting starts exactly one workflow; duplicate pickup reuses it; invalid states are blocked with safe reasons.

### Tests for User Story 1

- [ ] T025 [P] [US1] Add integration tests for eligible pickup and duplicate workflow reuse in `apps/server/tests/integration/test_processing_pickup.py`
- [ ] T026 [P] [US1] Add integration tests blocking degraded/failed/aborted/expired/incomplete meetings in `apps/server/tests/integration/test_processing_pickup_blockers.py`
- [ ] T027 [P] [US1] Add workflow id safety tests in `apps/server/tests/unit/test_processing_workflow_identity.py`

### Implementation for User Story 1

- [ ] T028 [US1] Implement workflow id generation and validation in `apps/server/src/twobrain_rec_server/workflows/temporal_client.py`
- [ ] T029 [US1] Implement processing eligibility checks in `apps/server/src/twobrain_rec_server/processing/pickup.py`
- [ ] T030 [US1] Implement idempotent workflow start/reuse using the Temporal adapter in `apps/server/src/twobrain_rec_server/processing/pickup.py`
- [ ] T031 [US1] Implement workflow orchestration shell in `apps/server/src/twobrain_rec_server/workflows/processing_workflow.py`
- [ ] T032 [US1] Add internal processing pickup endpoint in `apps/server/src/twobrain_rec_server/api/processing.py`
- [ ] T033 [US1] Register processing router in `apps/server/src/twobrain_rec_server/main.py`
- [ ] T034 [US1] Update processing placeholder loader to prefer persisted processing workflow state in `apps/server/src/twobrain_rec_server/ingest/processing_placeholder.py`
- [ ] T035 [US1] Run US1 tests and update validation evidence in `specs/015-mediascribe-processing-pipeline/quickstart.md`

**Checkpoint**: US1 is independently functional and testable.

---

## Phase 4: User Story 2 - Submit Dual-Track Audio To MediaScribe Server-Side (Priority: P1)

**Goal**: Backend workers submit accepted microphone/incoming artifacts to MediaScribe with server-side credentials and persist the external job id before retry.

**Independent Test**: Fake MediaScribe receives exactly `mic_file` and `incoming_file`, no desktop credentials exist, and accepted job id is persisted before polling.

### Tests for User Story 2

- [ ] T036 [P] [US2] Add dual-track request mapping tests in `apps/server/tests/unit/test_mediascribe_request_mapping.py`
- [ ] T037 [P] [US2] Add integration happy-path submit test in `apps/server/tests/integration/test_mediascribe_submit.py`
- [ ] T038 [P] [US2] Add no desktop/response secret egress tests in `apps/server/tests/contract/test_processing_no_secret_content_egress.py`

### Implementation for User Story 2

- [ ] T039 [US2] Implement server-side MediaScribe HTTP client in `apps/server/src/twobrain_rec_server/mediascribe/client.py`
- [ ] T040 [US2] Implement artifact-to-MediaScribe request mapping in `apps/server/src/twobrain_rec_server/mediascribe/client.py`
- [ ] T041 [US2] Implement submit activity/service in `apps/server/src/twobrain_rec_server/processing/submit.py`
- [ ] T042 [US2] Persist MediaScribe job id and request metadata before retry continuation in `apps/server/src/twobrain_rec_server/processing/store.py`
- [ ] T043 [US2] Wire submission step into workflow orchestration in `apps/server/src/twobrain_rec_server/workflows/processing_workflow.py`
- [ ] T044 [US2] Extend health/readiness detail with processing dependency configuration in `apps/server/src/twobrain_rec_server/api/health.py`
- [ ] T045 [US2] Run US2 tests and update validation evidence in `specs/015-mediascribe-processing-pipeline/quickstart.md`

**Checkpoint**: US2 is independently functional and testable with fake MediaScribe.

---

## Phase 5: User Story 3 - Poll And Import Processing Results (Priority: P1)

**Goal**: MediaScribe ready results import transcript and diarization segments with source roles, timestamps, speaker labels, and provenance.

**Independent Test**: Fake MediaScribe status transitions to ready and result import creates idempotent transcript/diarization rows without dashboard/download exposure.

### Tests for User Story 3

- [ ] T046 [P] [US3] Add result import unit tests in `apps/server/tests/unit/test_mediascribe_result_import.py`
- [ ] T047 [P] [US3] Add processing happy-path integration tests in `apps/server/tests/integration/test_mediascribe_processing_happy_path.py`
- [ ] T048 [P] [US3] Add idempotent import tests in `apps/server/tests/integration/test_processing_result_idempotency.py`

### Implementation for User Story 3

- [ ] T049 [US3] Implement MediaScribe polling response mapping in `apps/server/src/twobrain_rec_server/mediascribe/client.py`
- [ ] T050 [US3] Implement result normalization and validation in `apps/server/src/twobrain_rec_server/mediascribe/import_results.py`
- [ ] T051 [US3] Implement transcript and diarization segment persistence in `apps/server/src/twobrain_rec_server/processing/store.py`
- [ ] T052 [US3] Implement summary dependency state persistence in `apps/server/src/twobrain_rec_server/processing/store.py`
- [ ] T053 [US3] Wire poll/fetch/import steps into workflow orchestration in `apps/server/src/twobrain_rec_server/workflows/processing_workflow.py`
- [ ] T054 [US3] Run US3 tests and update validation evidence in `specs/015-mediascribe-processing-pipeline/quickstart.md`

**Checkpoint**: US3 is independently functional and testable.

---

## Phase 6: User Story 4 - Handle Failures, Retries, And Dependency Outages (Priority: P1)

**Goal**: Processing distinguishes retryable, terminal, blocked, and restart recovery cases without duplicate egress or ingest-status corruption.

**Independent Test**: Failure matrix covers credential, payload, 409, 429, 5xx, timeout, malformed result, and worker restart cases.

### Tests for User Story 4

- [ ] T055 [P] [US4] Add failure matrix integration tests in `apps/server/tests/integration/test_processing_failures.py`
- [ ] T056 [P] [US4] Add worker restart/resume integration tests in `apps/server/tests/integration/test_processing_worker_restart.py`
- [ ] T057 [P] [US4] Add readiness separation tests in `apps/server/tests/integration/test_processing_readiness.py`

### Implementation for User Story 4

- [ ] T058 [US4] Implement MediaScribe error classification in `apps/server/src/twobrain_rec_server/mediascribe/client.py`
- [ ] T059 [US4] Implement retry/terminal transition handling in `apps/server/src/twobrain_rec_server/processing/lifecycle.py`
- [ ] T060 [US4] Implement restart-safe resume from persisted job/result state in `apps/server/src/twobrain_rec_server/processing/pickup.py`
- [ ] T061 [US4] Ensure processing failures do not rewrite ingest status in `apps/server/src/twobrain_rec_server/processing/store.py`
- [ ] T062 [US4] Run US4 tests and update validation evidence in `specs/015-mediascribe-processing-pipeline/quickstart.md`

**Checkpoint**: US4 is independently functional and testable.

---

## Phase 7: User Story 5 - Preserve Privacy, Audit, And Lifecycle Truth (Priority: P1)

**Goal**: Processing records metadata-only audit/dependency truth and passes secret/content leak gates.

**Independent Test**: Logs, audit metadata, problem responses, status responses, diagnostics, and evidence contain no credentials, raw audio, transcript text, signed URLs, or live secret paths.

### Tests for User Story 5

- [ ] T063 [P] [US5] Add processing audit metadata tests in `apps/server/tests/integration/test_processing_audit.py`
- [ ] T064 [P] [US5] Add deletion dependency accounting tests in `apps/server/tests/integration/test_processing_deletion_dependency.py`
- [ ] T065 [P] [US5] Add no secret/content egress scans for processing in `apps/server/tests/contract/test_processing_no_secret_content_egress.py`

### Implementation for User Story 5

- [ ] T066 [US5] Persist metadata-only processing audit events in `apps/server/src/twobrain_rec_server/processing/audit.py`
- [ ] T067 [US5] Persist ProcessingDependencyState records in `apps/server/src/twobrain_rec_server/processing/store.py`
- [ ] T068 [US5] Extend redaction/scan helpers for processing content classes in `apps/server/src/twobrain_rec_server/observability/redaction.py`
- [ ] T069 [US5] Add deployment/env templates for MediaScribe/Temporal secret files without live values in `infra/env/rec.production.env.example`
- [ ] T070 [US5] Run US5 tests and update validation evidence in `specs/015-mediascribe-processing-pipeline/quickstart.md`

**Checkpoint**: US5 is independently functional and testable.

---

## Phase 8: User Story 6 - Expose Processing Status For Future Product Surfaces (Priority: P2)

**Goal**: Authorized callers can read content-safe processing status for future dashboard/desktop surfaces without exposing transcript text or credentials.

**Independent Test**: Status endpoint returns canonical state and availability metadata for all lifecycle states, denies cross-tenant reads, and exposes no content.

### Tests for User Story 6

- [ ] T071 [P] [US6] Add processing status API contract tests in `apps/server/tests/contract/test_processing_status_contract.py`
- [ ] T072 [P] [US6] Add tenant authorization tests for processing status in `apps/server/tests/integration/test_processing_tenant_authorization.py`
- [ ] T073 [P] [US6] Add out-of-scope boundary tests in `apps/server/tests/integration/test_processing_out_of_scope_boundaries.py`

### Implementation for User Story 6

- [ ] T074 [US6] Implement content-safe processing status query service in `apps/server/src/twobrain_rec_server/processing/status.py`
- [ ] T075 [US6] Implement processing status endpoint in `apps/server/src/twobrain_rec_server/api/processing.py`
- [ ] T076 [US6] Ensure transcript/audio/summary download, share, dashboard, delete, and assisted-recording endpoints remain absent in `apps/server/src/twobrain_rec_server/api/processing.py`
- [ ] T077 [US6] Run US6 tests and update validation evidence in `specs/015-mediascribe-processing-pipeline/quickstart.md`

**Checkpoint**: US6 is independently functional and testable.

---

## Phase 9: Polish & Cross-Cutting Validation

**Purpose**: Full feature validation, docs, and release-readiness evidence.

- [ ] T078 Update `apps/server/README.md` with processing boundary, local fake dependency flow, and no-secret rules
- [ ] T079 Update `docs/current-product-status.md` to describe accepted `015` behavior and remaining `016/017/018` boundaries
- [ ] T080 Update `CHANGELOG.md` under `[Unreleased]` for feature `015`
- [ ] T081 Run full server pytest gate and record result in `specs/015-mediascribe-processing-pipeline/quickstart.md`
- [ ] T082 Run Ruff and compileall gates and record result in `specs/015-mediascribe-processing-pipeline/quickstart.md`
- [ ] T083 Run Docker Compose config/readiness validation and record result in `specs/015-mediascribe-processing-pipeline/quickstart.md`
- [ ] T084 Run secret/content scan for processing artifacts and record result in `specs/015-mediascribe-processing-pipeline/quickstart.md`
- [ ] T085 Review implementation against spec, plan, contracts, checklists, and constitution, then record audit notes in `specs/015-mediascribe-processing-pipeline/quickstart.md`

---

## Dependencies & Execution Order

### Phase Dependencies

- Phase 1 Setup has no dependencies.
- Phase 2 Foundational depends on Phase 1 and blocks all user stories.
- US1 is MVP and starts after Phase 2.
- US2 depends on US1 workflow/pickup state.
- US3 depends on US2 job submission and MediaScribe client mapping.
- US4 depends on US2/US3 state transitions and persistence.
- US5 can start after Phase 2 but should be validated after US2/US3 create real processing events.
- US6 depends on persisted processing state from US1-US5.
- Polish depends on selected user stories and must run before completion.

### Parallel Opportunities

- T002-T004 and T006-T007 can run in parallel after T001.
- T010, T013-T015, T017, and T020-T023 can run in parallel after T009.
- Test tasks within each user story marked `[P]` can be written in parallel before implementation.
- US5 audit/dependency tests can be drafted while US2/US3 implementation proceeds, but acceptance requires real processing transitions.

### MVP Scope

MVP for this feature is Phases 1-3: setup, foundation, and US1. Product
acceptance for `015` requires all P1 stories (US1-US5), with US6 needed for
future dashboard readiness.

## Parallel Examples

```text
Task: "T020 [P] Add processing contract tests for OpenAPI status schema in apps/server/tests/contract/test_processing_status_contract.py"
Task: "T021 [P] Add MediaScribe client contract tests in apps/server/tests/contract/test_mediascribe_client_contract.py"
Task: "T022 [P] Add processing state-machine unit tests in apps/server/tests/unit/test_processing_state_machine.py"
Task: "T023 [P] Add processing migration integration tests in apps/server/tests/integration/test_processing_migrations.py"
```

```text
Task: "T046 [P] [US3] Add result import unit tests in apps/server/tests/unit/test_mediascribe_result_import.py"
Task: "T047 [P] [US3] Add processing happy-path integration tests in apps/server/tests/integration/test_mediascribe_processing_happy_path.py"
Task: "T048 [P] [US3] Add idempotent import tests in apps/server/tests/integration/test_processing_result_idempotency.py"
```

## Implementation Strategy

1. Complete setup and foundational schema/status work first.
2. Write failing tests for each story before implementation.
3. Implement US1 pickup/workflow identity as the first working slice.
4. Add MediaScribe submit/import with fake adapters before touching real dependency configuration.
5. Add failure/privacy/status gates.
6. Run full quickstart validation and audit against spec/contracts/checklists.
