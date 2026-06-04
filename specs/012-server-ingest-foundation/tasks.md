# Tasks: Server Ingest Foundation

**Input**: Design documents from `specs/012-server-ingest-foundation/`

**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/`, `quickstart.md`

**Tests**: Required for this high-risk backend ingest slice. Contract, unit, integration, and smoke tasks appear before implementation work for each story where practical.

**Organization**: Tasks are grouped by user story so each story can be implemented and validated independently.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel because it touches different files and does not depend on incomplete tasks
- **[Story]**: User story label from `spec.md`
- Every task includes an exact file path

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create the backend service and self-hosted development skeleton.

- [ ] T001 Create backend package directory structure in `apps/server/src/twobrain_rec_server/`
- [ ] T002 Create server test directory structure in `apps/server/tests/`
- [ ] T003 Create backend Python project configuration with FastAPI, Pydantic, SQLAlchemy, Alembic, asyncpg, MinIO, pytest, pytest-asyncio, httpx, and lint tooling in `apps/server/pyproject.toml`
- [ ] T004 Create backend package marker and public module exports in `apps/server/src/twobrain_rec_server/__init__.py`
- [ ] T005 Create local server environment template without secrets in `apps/server/.env.example`
- [ ] T006 Create API container Dockerfile in `infra/server/Dockerfile`
- [ ] T007 Create local development Docker Compose stack for API, Postgres, and MinIO in `infra/docker-compose.dev.yml`
- [ ] T008 Create production-oriented Docker Compose scaffold with secret placeholders in `infra/docker-compose.yml`
- [ ] T009 Add server build/cache/secret ignore rules in `.gitignore`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core app, config, persistence, storage, auth context, observability, and test helpers required by all stories.

**Critical**: No user story work should begin until this phase is complete.

- [ ] T010 Create FastAPI application factory and router registration shell in `apps/server/src/twobrain_rec_server/main.py`
- [ ] T011 Create typed settings model for API, Postgres, MinIO, ingest limits, upload TTL, and log redaction in `apps/server/src/twobrain_rec_server/config.py`
- [ ] T012 Create structured error/problem response helpers in `apps/server/src/twobrain_rec_server/api/problems.py`
- [ ] T013 Create request ID and safe JSON logging middleware in `apps/server/src/twobrain_rec_server/observability/logging.py`
- [ ] T014 Create database engine/session lifecycle module in `apps/server/src/twobrain_rec_server/db/session.py`
- [ ] T015 Create Alembic configuration in `apps/server/alembic.ini`
- [ ] T016 Create Alembic environment wired to app metadata in `apps/server/src/twobrain_rec_server/db/migrations/env.py`
- [ ] T017 Create initial SQLAlchemy base metadata module in `apps/server/src/twobrain_rec_server/db/base.py`
- [ ] T018 Create provider-neutral authenticated principal and device context models in `apps/server/src/twobrain_rec_server/auth/context.py`
- [ ] T019 Implement application-level tenant authorization dependencies that verify organization, workspace, user, membership, device, and upload-session scope before ingest reads or writes in `apps/server/src/twobrain_rec_server/auth/dependencies.py`
- [ ] T020 Create MinIO storage client wrapper with server-only credential handling in `apps/server/src/twobrain_rec_server/storage/minio_client.py`
- [ ] T021 Create object key builder for tenant/workspace/meeting/session scoped keys in `apps/server/src/twobrain_rec_server/storage/object_keys.py`
- [ ] T022 Create ingest status and enum definitions in `apps/server/src/twobrain_rec_server/domain/statuses.py`
- [ ] T023 Create shared pytest configuration and dependency overrides in `apps/server/tests/conftest.py`
- [ ] T024 [P] Create fake MinIO test double in `apps/server/tests/fakes/fake_minio.py`
- [ ] T025 [P] Create authenticated principal/device test fixtures in `apps/server/tests/fakes/auth_contexts.py`
- [ ] T026 [P] Create artifact fixture generator helper in `apps/server/tests/fixtures/artifacts.py`
- [ ] T027 Create health route skeleton for liveness and ingest readiness in `apps/server/src/twobrain_rec_server/api/health.py`
- [ ] T028 Create base Pydantic API request/response schemas for health, problem errors, meeting, upload session, upload parts, missing ranges, finalize, and abort in `apps/server/src/twobrain_rec_server/api/schemas.py`
- [X] T029 Complete pre-implementation requirement-quality review and mark resolved or explicitly risk-accepted items in `specs/012-server-ingest-foundation/checklists/security.md`
- [X] T030 Complete pre-implementation requirement-quality review and mark resolved or explicitly risk-accepted items in `specs/012-server-ingest-foundation/checklists/infra.md`
- [X] T031 Complete pre-implementation requirement-quality review and mark resolved or explicitly risk-accepted items in `specs/012-server-ingest-foundation/checklists/ux.md`
- [X] T032 Complete pre-implementation requirement-quality review and mark resolved or explicitly risk-accepted items in `specs/012-server-ingest-foundation/checklists/driver.md`

**Checkpoint**: Foundation and requirement-quality gates ready; user story implementation can start only after T029-T032 are complete or their remaining risks are explicitly accepted.

---

## Phase 3: User Story 1 - Upload A Finalized Local Recording (Priority: P1) MVP

**Goal**: Accept a valid finalized local dual-track artifact through authenticated server-mediated upload and finalize one durable meeting ingest record.

**Independent Test**: A contract-valid client creates a meeting/session, uploads manifest/microphone/system parts, finalizes, and reads a meeting state of `ingested_pending_processing` with durable object references and no processing job.

### Tests for User Story 1

- [ ] T033 [P] [US1] Add OpenAPI contract tests for meeting/session/part/finalize happy path in `apps/server/tests/contract/test_ingest_openapi_contract.py`
- [ ] T034 [P] [US1] Add unit tests for artifact manifest role validation and checksum metadata in `apps/server/tests/unit/test_manifest_validation.py`
- [ ] T035 [P] [US1] Add unit tests for configurable ingest duration and byte-size policy acceptance boundaries in `apps/server/tests/unit/test_ingest_limits.py`
- [ ] T036 [P] [US1] Add integration test for 30-minute dual-track happy-path ingest in `apps/server/tests/integration/test_ingest_happy_path.py`

### Implementation for User Story 1

- [ ] T037 [P] [US1] Create organization/workspace/user/device SQLAlchemy models in `apps/server/src/twobrain_rec_server/db/models/identity.py`
- [ ] T038 [P] [US1] Create meeting and processing placeholder SQLAlchemy models in `apps/server/src/twobrain_rec_server/db/models/meeting.py`
- [ ] T039 [P] [US1] Create upload session, upload part, temporary upload object, track artifact, manifest snapshot, and audit event SQLAlchemy models in `apps/server/src/twobrain_rec_server/db/models/ingest.py`
- [ ] T040 [US1] Create initial Alembic migration for identity, meeting, ingest, and audit tables in `apps/server/src/twobrain_rec_server/db/migrations/versions/0001_ingest_foundation.py`
- [ ] T041 [US1] Implement manifest validation service in `apps/server/src/twobrain_rec_server/ingest/manifest.py`
- [ ] T042 [US1] Implement ingest policy and limit validation service in `apps/server/src/twobrain_rec_server/ingest/policy.py`
- [ ] T043 [US1] Implement meeting creation/idempotency service in `apps/server/src/twobrain_rec_server/ingest/meetings.py`
- [ ] T044 [US1] Implement upload session creation service in `apps/server/src/twobrain_rec_server/ingest/sessions.py`
- [ ] T045 [US1] Implement server-mediated upload part acceptance and durable storage in `apps/server/src/twobrain_rec_server/ingest/parts.py`
- [ ] T046 [US1] Implement finalize service that creates track artifacts and inert processing placeholders in `apps/server/src/twobrain_rec_server/ingest/finalize.py`
- [ ] T047 [US1] Implement meeting and upload session API routes with T019 authorization dependencies applied to every read/write operation in `apps/server/src/twobrain_rec_server/api/ingest.py`
- [ ] T048 [US1] Wire ingest routes into FastAPI app in `apps/server/src/twobrain_rec_server/main.py`
- [ ] T049 [US1] Add safe audit events for meeting creation, session creation, part acceptance, and finalization in `apps/server/src/twobrain_rec_server/ingest/audit.py`
- [ ] T050 [US1] Create test artifact generator script in `apps/server/scripts/create_test_artifact.py`

**Checkpoint**: US1 MVP is independently testable with happy-path upload and finalize.

---

## Phase 4: User Story 2 - Resume Interrupted Uploads Safely (Priority: P1)

**Goal**: Support resumable/idempotent upload after interruption without duplicate objects, duplicate meetings, or conflicting bytes.

**Independent Test**: Interrupt after accepted parts, query missing ranges, replay matching parts idempotently, reject conflicting checksum replay, and finalize exactly one meeting.

### Tests for User Story 2

- [ ] T051 [P] [US2] Add unit tests for accepted/missing range calculation in `apps/server/tests/unit/test_missing_ranges.py`
- [ ] T052 [P] [US2] Add unit tests for idempotent matching retry and conflicting retry rejection in `apps/server/tests/unit/test_upload_idempotency.py`
- [ ] T053 [P] [US2] Add integration test for interrupted upload resume and single finalization in `apps/server/tests/integration/test_upload_resume.py`

### Implementation for User Story 2

- [ ] T054 [US2] Implement accepted and missing range calculation service in `apps/server/src/twobrain_rec_server/ingest/ranges.py`
- [ ] T055 [US2] Implement idempotent part replay and checksum conflict handling in `apps/server/src/twobrain_rec_server/ingest/parts.py`
- [ ] T056 [US2] Implement missing ranges API route in `apps/server/src/twobrain_rec_server/api/ingest.py`
- [ ] T057 [US2] Implement upload session status read service in `apps/server/src/twobrain_rec_server/ingest/status.py`
- [ ] T058 [US2] Add audit event handling for retry and checksum conflict events in `apps/server/src/twobrain_rec_server/ingest/audit.py`
- [ ] T059 [US2] Create resumable upload helper script for quickstart validation in `apps/server/scripts/upload_test_artifact.py`

**Checkpoint**: US2 can be validated independently after US1 foundation.

---

## Phase 5: User Story 3 - Keep MediaScribe And Egress Server-Side (Priority: P1)

**Goal**: Prove desktop-facing ingest never exposes MediaScribe/object-storage credentials and 012 never starts MediaScribe or Temporal work.

**Independent Test**: Inspect ingest responses, health output, diagnostics/logs, and finalized records to confirm zero MediaScribe credentials, zero direct object-storage credentials, zero workflow starts, and metadata-only observability.

### Tests for User Story 3

- [ ] T060 [P] [US3] Add contract tests asserting no MediaScribe, object-storage credential, signed URL, workflow ID, or job ID fields leak in ingest responses in `apps/server/tests/contract/test_no_secret_egress_contract.py`
- [ ] T061 [P] [US3] Add unit tests for log redaction and safe audit metadata filtering in `apps/server/tests/unit/test_redaction.py`
- [ ] T062 [P] [US3] Add integration test proving finalize creates no Temporal workflow and no MediaScribe job identifiers in `apps/server/tests/integration/test_no_processing_side_effects.py`

### Implementation for User Story 3

- [ ] T063 [US3] Implement secret/content redaction helpers in `apps/server/src/twobrain_rec_server/observability/redaction.py`
- [ ] T064 [US3] Apply redaction to API problem details and request logging in `apps/server/src/twobrain_rec_server/api/problems.py`
- [ ] T065 [US3] Ensure upload authorization DTOs expose only server-mediated session scope in `apps/server/src/twobrain_rec_server/ingest/authorization.py`
- [ ] T066 [US3] Ensure finalize response always reports null workflow/job identifiers and false workflow/job side effects in `apps/server/src/twobrain_rec_server/ingest/finalize.py`
- [ ] T067 [US3] Implement ingest readiness checks excluding MediaScribe and Temporal dependencies in `apps/server/src/twobrain_rec_server/api/health.py`
- [ ] T068 [US3] Document metadata-only observability fields in `apps/server/README.md`

**Checkpoint**: US3 security boundary is independently testable.

---

## Phase 6: User Story 4 - Represent Degraded Or Failed Ingest Truthfully (Priority: P2)

**Goal**: Distinguish complete, degraded, blocked, failed, aborted, expired, and recoverable states without false success.

**Independent Test**: Missing/corrupt tracks, invalid manifest, storage outage, premature finalize, abort, expiry, and over-limit cases return precise states and recovery/policy reasons.

### Tests for User Story 4

- [ ] T069 [P] [US4] Add unit tests for upload session and meeting state transitions in `apps/server/tests/unit/test_ingest_state_machine.py`
- [ ] T070 [P] [US4] Add integration tests for missing, corrupt, wrong-role, and unsupported artifacts in `apps/server/tests/integration/test_degraded_ingest.py`
- [ ] T071 [P] [US4] Add integration tests for storage outage, partial object write, and premature finalization states in `apps/server/tests/integration/test_ingest_failure_truth.py`
- [ ] T072 [P] [US4] Add integration tests for over-limit duration, track bytes, package bytes, and session lifetime outcomes in `apps/server/tests/integration/test_ingest_limits.py`

### Implementation for User Story 4

- [ ] T073 [US4] Implement upload session state machine rules in `apps/server/src/twobrain_rec_server/ingest/state_machine.py`
- [ ] T074 [US4] Implement degraded and failed reason catalog in `apps/server/src/twobrain_rec_server/domain/reasons.py`
- [ ] T075 [US4] Implement abort and expiry service logic in `apps/server/src/twobrain_rec_server/ingest/lifecycle.py`
- [ ] T076 [US4] Implement abort API route in `apps/server/src/twobrain_rec_server/api/ingest.py`
- [ ] T077 [US4] Add temporary object cleanup accounting records for non-success terminal states in `apps/server/src/twobrain_rec_server/ingest/lifecycle.py`
- [ ] T078 [US4] Add audit event handling for degraded, failed, aborted, and expired states in `apps/server/src/twobrain_rec_server/ingest/audit.py`

**Checkpoint**: US4 truth states are independently testable.

---

## Phase 7: User Story 6 - Preserve Ownership And Future Access Control (Priority: P2)

**Goal**: Persist organization, workspace, owner, device, default visibility, and access/share/download placeholders for future RBAC without implementing those behaviors.

**Independent Test**: Ingest across users/devices/workspaces, prove ownership isolation, local recording identity scoping, access placeholder storage, and blocked share/download behavior.

### Tests for User Story 6

- [ ] T079 [P] [US6] Add authorization integration tests for cross-user, cross-device, cross-workspace, and cross-organization denial in `apps/server/tests/integration/test_tenant_authorization.py`
- [ ] T080 [P] [US6] Add unit tests for tenant-scoped object key construction and collision prevention in `apps/server/tests/unit/test_object_keys.py`
- [ ] T081 [P] [US6] Add integration test for access policy and share/download placeholder persistence in `apps/server/tests/integration/test_access_placeholders.py`

### Implementation for User Story 6

- [ ] T082 [US6] Implement reusable tenant authorization policy helpers for owner/workspace/admin placeholder decisions in `apps/server/src/twobrain_rec_server/auth/authorization.py`
- [ ] T083 [US6] Audit ingest route authorization coverage against FR-042 and add missing dependency coverage if any route drift is found in `apps/server/src/twobrain_rec_server/api/ingest.py`
- [ ] T084 [US6] Implement access policy snapshot model/service in `apps/server/src/twobrain_rec_server/ingest/access_policy.py`
- [ ] T085 [US6] Implement share/download capability placeholder model fields in `apps/server/src/twobrain_rec_server/db/models/meeting.py`
- [ ] T086 [US6] Add migration for access policy snapshot and share/download placeholder fields in `apps/server/src/twobrain_rec_server/db/migrations/versions/0002_access_placeholders.py`
- [ ] T087 [US6] Document RLS-hardening follow-up issue candidate and compensating application checks in `specs/012-server-ingest-foundation/tasks.md`

**Checkpoint**: US6 ownership/access metadata is independently testable without dashboard/share implementation.

---

## Phase 8: User Story 5 - Prepare For Dashboard And Processing Without Shipping Them (Priority: P3)

**Goal**: Expose stable lifecycle metadata for future desktop queue, processing, and dashboard slices while keeping transcript, notes, deletion, sharing, and assisted recording out of 012.

**Independent Test**: Inspect records/contracts after success and failure to ensure future fields exist only as safe references/placeholders and no out-of-scope behavior is observable.

### Tests for User Story 5

- [ ] T088 [P] [US5] Add contract tests for desktop status vocabulary and canonical API state mapping in `apps/server/tests/contract/test_desktop_status_contract.py`
- [ ] T089 [P] [US5] Add integration tests proving transcript, notes, dashboard detail, deletion execution, share, download, indexing, and assisted recording endpoints are absent or not implemented in `apps/server/tests/integration/test_out_of_scope_boundaries.py`
- [ ] T090 [P] [US5] Add integration test for future processing pickup metadata without workflow execution in `apps/server/tests/integration/test_processing_placeholder.py`

### Implementation for User Story 5

- [ ] T091 [US5] Implement desktop status mapping DTOs in `apps/server/src/twobrain_rec_server/ingest/desktop_status.py`
- [ ] T092 [US5] Add status mapping to upload session response serializers in `apps/server/src/twobrain_rec_server/api/schemas.py`
- [ ] T093 [US5] Implement processing placeholder query service for future 015 pickup in `apps/server/src/twobrain_rec_server/ingest/processing_placeholder.py`
- [ ] T094 [US5] Add explicit not-implemented route policy documentation in `apps/server/README.md`
- [ ] T095 [US5] Update desktop ingest status contract notes if implementation discovers naming drift in `specs/012-server-ingest-foundation/contracts/desktop-ingest-status.md`

**Checkpoint**: US5 future-slice readiness is independently testable without scope creep.

---

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: Final validation, evidence capture, post-implementation checklist re-review, and hardening register cleanup across all stories.

- [ ] T096 [P] Re-review security checklist after implementation and mark any newly resolved or regressed items in `specs/012-server-ingest-foundation/checklists/security.md`
- [ ] T097 [P] Re-review infra checklist after implementation and mark any newly resolved or regressed items in `specs/012-server-ingest-foundation/checklists/infra.md`
- [ ] T098 [P] Re-review UX/status checklist after implementation and mark any newly resolved or regressed items in `specs/012-server-ingest-foundation/checklists/ux.md`
- [ ] T099 [P] Re-review driver-boundary checklist after implementation and mark any newly resolved or regressed items in `specs/012-server-ingest-foundation/checklists/driver.md`
- [ ] T100 Run full server unit, contract, and integration suite and record validation evidence in `specs/012-server-ingest-foundation/quickstart.md`
- [ ] T101 Run Docker Compose quickstart validation and update commands or caveats in `specs/012-server-ingest-foundation/quickstart.md`
- [ ] T102 Run log/API response secret-content scan and record evidence in `specs/012-server-ingest-foundation/quickstart.md`
- [ ] T103 Update current product status for completed 012 scope and remaining follow-ups in `docs/current-product-status.md`
- [ ] T104 Update PRD implementation slice status and deferred work register if 012 scope changes in `docs/prd-voice-layer-final.md`
- [ ] T105 Verify no unintended macOS driver/uploader source changes are required by 012 in `apps/macos/Package.swift`

---

## Dependencies & Execution Order

### Phase Dependencies

- **Phase 1 Setup**: No dependencies.
- **Phase 2 Foundational**: Depends on Phase 1; blocks all user story phases and includes the pre-implementation checklist gate T029-T032.
- **Phase 3 US1**: Depends on Phase 2 and is the MVP.
- **Phase 4 US2**: Depends on Phase 2; practically uses US1 upload session/part models and can be implemented after or alongside US1 services.
- **Phase 5 US3**: Depends on Phase 2; can run alongside US1/US2 once response schemas and logging shell exist.
- **Phase 6 US4**: Depends on US1 and US2 state/session foundations.
- **Phase 7 US6**: Depends on Phase 2 identity/tenant models; should be complete before external use.
- **Phase 8 US5**: Depends on US1 status/finalize outputs and US3/US6 boundaries.
- **Phase 9 Polish**: Depends on selected story completion.

### User Story Dependencies

- **US1 (P1)**: MVP path; no dependency on other user stories after foundation, but API route work depends on base schemas from T028 and authorization dependencies from T019.
- **US2 (P1)**: Independent validation of resume/idempotency; shares upload part/session services with US1.
- **US3 (P1)**: Independent security boundary; should be complete before any external ingest use.
- **US4 (P2)**: Depends on state/session primitives from US1/US2.
- **US6 (P2)**: Depends on identity/tenant foundation; required before broader workspace/team use.
- **US5 (P3)**: Depends on finalized lifecycle/status outputs from earlier stories.

### Parallel Opportunities

- Setup tasks T006-T009 can run in parallel after directory creation.
- Foundational test helpers T024-T026 can run in parallel.
- Pre-implementation checklist gate tasks T029-T032 can run in parallel after plan/spec/tasks are present.
- US1 model tasks T037-T039 can run in parallel.
- Test tasks within each user story can run in parallel before implementation.
- US3 security boundary tests can run in parallel with US1 happy-path tests once test scaffolding exists.
- Post-implementation checklist re-review tasks T096-T099 can run in parallel.

## Parallel Example: User Story 1

```text
Task: "T033 [US1] Add OpenAPI contract tests for meeting/session/part/finalize happy path in apps/server/tests/contract/test_ingest_openapi_contract.py"
Task: "T034 [US1] Add unit tests for artifact manifest role validation and checksum metadata in apps/server/tests/unit/test_manifest_validation.py"
Task: "T035 [US1] Add unit tests for configurable ingest duration and byte-size policy acceptance boundaries in apps/server/tests/unit/test_ingest_limits.py"
Task: "T036 [US1] Add integration test for 30-minute dual-track happy-path ingest in apps/server/tests/integration/test_ingest_happy_path.py"
```

## Implementation Strategy

### MVP First

1. Complete Phase 1 Setup.
2. Complete Phase 2 Foundational.
3. Complete Phase 3 US1.
4. Stop and validate happy-path dual-track ingest from `quickstart.md`.
5. Continue with US2 and US3 before any external demo.

### Safety Gate Before Implementation

1. Run `$speckit-analyze 012`.
2. Resolve critical/high analyze findings before `$speckit-implement 012`.
3. Do not start implementation with unresolved checklist blockers unless the risk is explicitly accepted.

### Hardening Register

- `RLS-hardening`: PostgreSQL Row Level Security is deferred in 012 with mandatory application-level tenant checks. A future task or GitHub issue must implement RLS or record explicit risk acceptance before broad external customer exposure.
- `direct-object-upload`: Direct object-storage upload URLs remain out of scope for 012 and require a separate security/lifecycle review.
- `015-mediascribe-processing-pipeline`: Temporal workflow start and MediaScribe job submission remain out of scope for 012.
