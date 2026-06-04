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

- [X] T001 Create backend package directory structure in `apps/server/src/twobrain_rec_server/`
- [X] T002 Create server test directory structure in `apps/server/tests/`
- [X] T003 Create backend Python project configuration with FastAPI, Pydantic, SQLAlchemy, Alembic, asyncpg, MinIO, pytest, pytest-asyncio, httpx, and lint tooling in `apps/server/pyproject.toml`
- [X] T004 Create backend package marker and public module exports in `apps/server/src/twobrain_rec_server/__init__.py`
- [X] T005 Create local server environment template without secrets in `apps/server/.env.example`
- [X] T006 Create API container Dockerfile in `infra/server/Dockerfile`
- [X] T007 Create local development Docker Compose stack for API, Postgres, and MinIO in `infra/docker-compose.dev.yml`
- [X] T008 Create production Docker Compose scaffold for an isolated Rec stack with API, Postgres, MinIO, dedicated network, dedicated volumes, health checks, and secret placeholders in `infra/docker-compose.yml`
- [X] T009 Add server build/cache/secret ignore rules in `.gitignore`

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Core app, config, persistence, storage, auth context, observability, and test helpers required by all stories.

**Critical**: No user story work should begin until this phase is complete.

- [X] T010 Create FastAPI application factory and router registration shell in `apps/server/src/twobrain_rec_server/main.py`
- [X] T011 Create typed settings model for API, Postgres, MinIO, ingest limits, upload TTL, and log redaction in `apps/server/src/twobrain_rec_server/config.py`
- [X] T012 Create structured error/problem response helpers in `apps/server/src/twobrain_rec_server/api/problems.py`
- [X] T013 Create request ID and safe JSON logging middleware in `apps/server/src/twobrain_rec_server/observability/logging.py`
- [X] T014 Create database engine/session lifecycle module in `apps/server/src/twobrain_rec_server/db/session.py`
- [X] T015 Create Alembic configuration in `apps/server/alembic.ini`
- [X] T016 Create Alembic environment wired to app metadata in `apps/server/src/twobrain_rec_server/db/migrations/env.py`
- [X] T017 Create initial SQLAlchemy base metadata module in `apps/server/src/twobrain_rec_server/db/base.py`
- [X] T018 Create provider-neutral authenticated principal and device context models in `apps/server/src/twobrain_rec_server/auth/context.py`
- [X] T019 Implement application-level tenant authorization dependencies that verify organization, workspace, user, membership, device, and upload-session scope before ingest reads or writes in `apps/server/src/twobrain_rec_server/auth/dependencies.py`
- [X] T020 Create MinIO storage client wrapper with server-only credential handling in `apps/server/src/twobrain_rec_server/storage/minio_client.py`
- [X] T021 Create object key builder for tenant/workspace/meeting/session scoped keys in `apps/server/src/twobrain_rec_server/storage/object_keys.py`
- [X] T022 Create ingest status and enum definitions in `apps/server/src/twobrain_rec_server/domain/statuses.py`
- [X] T023 Create shared pytest configuration and dependency overrides in `apps/server/tests/conftest.py`
- [X] T024 [P] Create fake MinIO test double in `apps/server/tests/fakes/fake_minio.py`
- [X] T025 [P] Create authenticated principal/device test fixtures in `apps/server/tests/fakes/auth_contexts.py`
- [X] T026 [P] Create artifact fixture generator helper in `apps/server/tests/fixtures/artifacts.py`
- [X] T027 Create health route skeleton for liveness and ingest readiness in `apps/server/src/twobrain_rec_server/api/health.py`
- [X] T028 Create base Pydantic API request/response schemas for health, problem errors, meeting, upload session, upload parts, missing ranges, finalize, and abort in `apps/server/src/twobrain_rec_server/api/schemas.py`
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

- [X] T033 [P] [US1] Add OpenAPI contract tests for meeting/session/part/finalize happy path in `apps/server/tests/contract/test_ingest_openapi_contract.py`
- [X] T034 [P] [US1] Add unit tests for artifact manifest role validation and checksum metadata in `apps/server/tests/unit/test_manifest_validation.py`
- [X] T035 [P] [US1] Add unit tests for configurable ingest duration and byte-size policy acceptance boundaries in `apps/server/tests/unit/test_ingest_limits.py`
- [X] T036 [P] [US1] Add integration test for 30-minute dual-track happy-path ingest in `apps/server/tests/integration/test_ingest_happy_path.py`

### Implementation for User Story 1

- [X] T037 [P] [US1] Create organization/workspace/user/device SQLAlchemy models in `apps/server/src/twobrain_rec_server/db/models/identity.py`
- [X] T038 [P] [US1] Create meeting and processing placeholder SQLAlchemy models in `apps/server/src/twobrain_rec_server/db/models/meeting.py`
- [X] T039 [P] [US1] Create upload session, upload part, temporary upload object, track artifact, manifest snapshot, and audit event SQLAlchemy models in `apps/server/src/twobrain_rec_server/db/models/ingest.py`
- [X] T040 [US1] Create initial Alembic migration for identity, meeting, ingest, and audit tables in `apps/server/src/twobrain_rec_server/db/migrations/versions/0001_ingest_foundation.py`
- [X] T041 [US1] Implement manifest validation service in `apps/server/src/twobrain_rec_server/ingest/manifest.py`
- [X] T042 [US1] Implement ingest policy and limit validation service in `apps/server/src/twobrain_rec_server/ingest/policy.py`
- [X] T043 [US1] Implement meeting creation/idempotency service in `apps/server/src/twobrain_rec_server/ingest/meetings.py`
- [X] T044 [US1] Implement upload session creation service in `apps/server/src/twobrain_rec_server/ingest/sessions.py`
- [X] T045 [US1] Implement server-mediated upload part acceptance and durable storage in `apps/server/src/twobrain_rec_server/ingest/parts.py`
- [X] T046 [US1] Implement finalize service that creates track artifacts and inert processing placeholders in `apps/server/src/twobrain_rec_server/ingest/finalize.py`
- [X] T047 [US1] Implement meeting and upload session API routes with T019 authorization dependencies applied to every read/write operation in `apps/server/src/twobrain_rec_server/api/ingest.py`
- [X] T048 [US1] Wire ingest routes into FastAPI app in `apps/server/src/twobrain_rec_server/main.py`
- [X] T049 [US1] Add safe audit events for meeting creation, session creation, part acceptance, and finalization in `apps/server/src/twobrain_rec_server/ingest/audit.py`
- [X] T050 [US1] Create test artifact generator script in `apps/server/scripts/create_test_artifact.py`

**Checkpoint**: US1 MVP is independently testable with happy-path upload and finalize.

---

## Phase 4: User Story 2 - Resume Interrupted Uploads Safely (Priority: P1)

**Goal**: Support resumable/idempotent upload after interruption without duplicate objects, duplicate meetings, or conflicting bytes.

**Independent Test**: Interrupt after accepted parts, query missing ranges, replay matching parts idempotently, reject conflicting checksum replay, and finalize exactly one meeting.

### Tests for User Story 2

- [X] T051 [P] [US2] Add unit tests for accepted/missing range calculation in `apps/server/tests/unit/test_missing_ranges.py`
- [X] T052 [P] [US2] Add unit tests for idempotent matching retry and conflicting retry rejection in `apps/server/tests/unit/test_upload_idempotency.py`
- [X] T053 [P] [US2] Add integration test for interrupted upload resume and single finalization in `apps/server/tests/integration/test_upload_resume.py`

### Implementation for User Story 2

- [X] T054 [US2] Implement accepted and missing range calculation service in `apps/server/src/twobrain_rec_server/ingest/ranges.py`
- [X] T055 [US2] Implement idempotent part replay and checksum conflict handling in `apps/server/src/twobrain_rec_server/ingest/parts.py`
- [X] T056 [US2] Implement missing ranges API route in `apps/server/src/twobrain_rec_server/api/ingest.py`
- [X] T057 [US2] Implement upload session status read service in `apps/server/src/twobrain_rec_server/ingest/status.py`
- [X] T058 [US2] Add audit event handling for retry and checksum conflict events in `apps/server/src/twobrain_rec_server/ingest/audit.py`
- [X] T059 [US2] Create resumable upload helper script for quickstart validation in `apps/server/scripts/upload_test_artifact.py`

**Checkpoint**: US2 can be validated independently after US1 foundation.

---

## Phase 5: User Story 3 - Keep MediaScribe And Egress Server-Side (Priority: P1)

**Goal**: Prove desktop-facing ingest never exposes MediaScribe/object-storage credentials and 012 never starts MediaScribe or Temporal work.

**Independent Test**: Inspect ingest responses, health output, diagnostics/logs, and finalized records to confirm zero MediaScribe credentials, zero direct object-storage credentials, zero workflow starts, and metadata-only observability.

### Tests for User Story 3

- [X] T060 [P] [US3] Add contract tests asserting no MediaScribe, object-storage credential, signed URL, workflow ID, or job ID fields leak in ingest responses in `apps/server/tests/contract/test_no_secret_egress_contract.py`
- [X] T061 [P] [US3] Add unit tests for log redaction and safe audit metadata filtering in `apps/server/tests/unit/test_redaction.py`
- [X] T062 [P] [US3] Add integration test proving finalize creates no Temporal workflow and no MediaScribe job identifiers in `apps/server/tests/integration/test_no_processing_side_effects.py`

### Implementation for User Story 3

- [X] T063 [US3] Implement secret/content redaction helpers in `apps/server/src/twobrain_rec_server/observability/redaction.py`
- [X] T064 [US3] Apply redaction to API problem details and request logging in `apps/server/src/twobrain_rec_server/api/problems.py`
- [X] T065 [US3] Ensure upload authorization DTOs expose only server-mediated session scope in `apps/server/src/twobrain_rec_server/ingest/authorization.py`
- [X] T066 [US3] Ensure finalize response always reports null workflow/job identifiers and false workflow/job side effects in `apps/server/src/twobrain_rec_server/ingest/finalize.py`
- [X] T067 [US3] Implement ingest readiness checks excluding MediaScribe and Temporal dependencies in `apps/server/src/twobrain_rec_server/api/health.py`
- [X] T068 [US3] Document metadata-only observability fields in `apps/server/README.md`

**Checkpoint**: US3 security boundary is independently testable.

---

## Phase 6: User Story 4 - Represent Degraded Or Failed Ingest Truthfully (Priority: P2)

**Goal**: Distinguish complete, degraded, blocked, failed, aborted, expired, and recoverable states without false success.

**Independent Test**: Missing/corrupt tracks, invalid manifest, storage outage, premature finalize, abort, expiry, and over-limit cases return precise states and recovery/policy reasons.

### Tests for User Story 4

- [X] T069 [P] [US4] Add unit tests for upload session and meeting state transitions in `apps/server/tests/unit/test_ingest_state_machine.py`
- [X] T070 [P] [US4] Add integration tests for missing, corrupt, wrong-role, and unsupported artifacts in `apps/server/tests/integration/test_degraded_ingest.py`
- [X] T071 [P] [US4] Add integration tests for storage outage, partial object write, and premature finalization states in `apps/server/tests/integration/test_ingest_failure_truth.py`
- [X] T072 [P] [US4] Add integration tests for over-limit duration, track bytes, package bytes, and session lifetime outcomes in `apps/server/tests/integration/test_ingest_limits.py`

### Implementation for User Story 4

- [X] T073 [US4] Implement upload session state machine rules in `apps/server/src/twobrain_rec_server/ingest/state_machine.py`
- [X] T074 [US4] Implement degraded and failed reason catalog in `apps/server/src/twobrain_rec_server/domain/reasons.py`
- [X] T075 [US4] Implement abort and expiry service logic in `apps/server/src/twobrain_rec_server/ingest/lifecycle.py`
- [X] T076 [US4] Implement abort API route in `apps/server/src/twobrain_rec_server/api/ingest.py`
- [X] T077 [US4] Add temporary object cleanup accounting records for non-success terminal states in `apps/server/src/twobrain_rec_server/ingest/lifecycle.py`
- [X] T078 [US4] Add audit event handling for degraded, failed, aborted, and expired states in `apps/server/src/twobrain_rec_server/ingest/audit.py`

**Checkpoint**: US4 truth states are independently testable.

---

## Phase 7: User Story 6 - Preserve Ownership And Future Access Control (Priority: P2)

**Goal**: Persist organization, workspace, owner, device, default visibility, and access/share/download placeholders for future RBAC without implementing those behaviors.

**Independent Test**: Ingest across users/devices/workspaces, prove ownership isolation, local recording identity scoping, access placeholder storage, and blocked share/download behavior.

### Tests for User Story 6

- [X] T079 [P] [US6] Add authorization integration tests for cross-user, cross-device, cross-workspace, and cross-organization denial in `apps/server/tests/integration/test_tenant_authorization.py`
- [X] T080 [P] [US6] Add unit tests for tenant-scoped object key construction and collision prevention in `apps/server/tests/unit/test_object_keys.py`
- [X] T081 [P] [US6] Add integration test for access policy and share/download placeholder persistence in `apps/server/tests/integration/test_access_placeholders.py`

### Implementation for User Story 6

- [X] T082 [US6] Implement reusable tenant authorization policy helpers for owner/workspace/admin placeholder decisions in `apps/server/src/twobrain_rec_server/auth/authorization.py`
- [X] T083 [US6] Audit ingest route authorization coverage against FR-042 and add missing dependency coverage if any route drift is found in `apps/server/src/twobrain_rec_server/api/ingest.py`
- [X] T084 [US6] Implement access policy snapshot model/service in `apps/server/src/twobrain_rec_server/ingest/access_policy.py`
- [X] T085 [US6] Implement share/download capability placeholder model fields in `apps/server/src/twobrain_rec_server/db/models/meeting.py`
- [X] T086 [US6] Add migration for access policy snapshot and share/download placeholder fields in `apps/server/src/twobrain_rec_server/db/migrations/versions/0002_access_placeholders.py`
- [X] T087 [US6] Document RLS-hardening follow-up issue candidate and compensating application checks in `specs/012-server-ingest-foundation/tasks.md`

**Checkpoint**: US6 ownership/access metadata is independently testable without dashboard/share implementation.

---

## Phase 8: User Story 5 - Prepare For Dashboard And Processing Without Shipping Them (Priority: P3)

**Goal**: Expose stable lifecycle metadata for future desktop queue, processing, and dashboard slices while keeping transcript, notes, deletion, sharing, and assisted recording out of 012.

**Independent Test**: Inspect records/contracts after success and failure to ensure future fields exist only as safe references/placeholders and no out-of-scope behavior is observable.

### Tests for User Story 5

- [X] T088 [P] [US5] Add contract tests for desktop status vocabulary and canonical API state mapping in `apps/server/tests/contract/test_desktop_status_contract.py`
- [X] T089 [P] [US5] Add integration tests proving transcript, notes, dashboard detail, deletion execution, share, download, indexing, and assisted recording endpoints are absent or not implemented in `apps/server/tests/integration/test_out_of_scope_boundaries.py`
- [X] T090 [P] [US5] Add integration test for future processing pickup metadata without workflow execution in `apps/server/tests/integration/test_processing_placeholder.py`

### Implementation for User Story 5

- [X] T091 [US5] Implement desktop status mapping DTOs in `apps/server/src/twobrain_rec_server/ingest/desktop_status.py`
- [X] T092 [US5] Add status mapping to upload session response serializers in `apps/server/src/twobrain_rec_server/api/schemas.py`
- [X] T093 [US5] Implement processing placeholder query service for future 015 pickup in `apps/server/src/twobrain_rec_server/ingest/processing_placeholder.py`
- [X] T094 [US5] Add explicit not-implemented route policy documentation in `apps/server/README.md`
- [X] T095 [US5] Update desktop ingest status contract notes if implementation discovers naming drift in `specs/012-server-ingest-foundation/contracts/desktop-ingest-status.md`

**Checkpoint**: US5 future-slice readiness is independently testable without scope creep.

---

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: Final validation, evidence capture, post-implementation checklist re-review, and hardening register cleanup across all stories.

- [X] T096 [P] Re-review security checklist after implementation and mark any newly resolved or regressed items in `specs/012-server-ingest-foundation/checklists/security.md`
- [X] T097 [P] Re-review infra checklist after implementation and mark any newly resolved or regressed items in `specs/012-server-ingest-foundation/checklists/infra.md`
- [X] T098 [P] Re-review UX/status checklist after implementation and mark any newly resolved or regressed items in `specs/012-server-ingest-foundation/checklists/ux.md`
- [X] T099 [P] Re-review driver-boundary checklist after implementation and mark any newly resolved or regressed items in `specs/012-server-ingest-foundation/checklists/driver.md`
- [X] T100 Run full server unit, contract, and integration suite and record validation evidence in `specs/012-server-ingest-foundation/quickstart.md`
- [X] T101 Run local and production Docker Compose quickstart validation, including `docker compose -f infra/docker-compose.yml config`, and update commands or caveats in `specs/012-server-ingest-foundation/quickstart.md`
- [X] T102 Run log/API response secret-content scan and record evidence in `specs/012-server-ingest-foundation/quickstart.md`
- [X] T103 Update current product status for completed 012 scope and remaining follow-ups in `docs/current-product-status.md`
- [X] T104 Update PRD implementation slice status and deferred work register if 012 scope changes in `docs/prd-voice-layer-final.md`
- [X] T105 Verify no unintended macOS driver/uploader source changes are required by 012 in `apps/macos/Package.swift`

---

## Phase 10: Review Remediation Before PR/Deployment Plan

**Purpose**: Close final sanity review blockers found after the initial 012 implementation commit. These tasks must be completed before representing 012 as a durable ingest foundation or before writing the production deployment plan.

- [X] T106 [P] Add integration tests proving accepted meeting, upload session, upload part metadata, and audit records survive in Postgres-backed persistence in `apps/server/tests/integration/test_persistent_ingest_storage.py`
- [X] T107 [P] Add integration tests proving accepted upload bytes are written to MinIO-compatible storage without retaining audio bytes in API session state in `apps/server/tests/integration/test_minio_upload_storage.py`
- [X] T108 [P] Add authorization tests for forged user, organization, workspace membership, and revoked device contexts in `apps/server/tests/integration/test_tenant_authorization.py`
- [X] T109 [P] Add API tests proving missing-ranges uses stored expected track sizes rather than already-uploaded byte totals in `apps/server/tests/integration/test_upload_resume.py`
- [X] T110 [P] Add readiness tests proving `/api/v1/health/ready` fails when Postgres or MinIO checks fail and passes when both are reachable in `apps/server/tests/integration/test_health_readiness.py`
- [X] T111 [P] Fix Ruff target-version compatibility and add a lint validation note in `apps/server/pyproject.toml`
- [X] T112 Implement Postgres-backed ingest repository and replace in-memory meeting/session/audit persistence in `apps/server/src/twobrain_rec_server/ingest/store.py`
- [X] T113 Wire SQLAlchemy session dependencies through ingest routes and services in `apps/server/src/twobrain_rec_server/api/ingest.py`
- [X] T114 Implement server-mediated MinIO writes for accepted upload parts and persist object metadata without storing raw bytes in `apps/server/src/twobrain_rec_server/ingest/parts.py`
- [X] T115 Persist expected upload track descriptors from upload session creation and use them for missing-range responses in `apps/server/src/twobrain_rec_server/ingest/sessions.py`
- [X] T116 Implement provider-neutral application auth checks against persisted user membership and registered device status in `apps/server/src/twobrain_rec_server/auth/dependencies.py`
- [X] T117 Implement real Postgres and MinIO readiness probes for 012 dependencies in `apps/server/src/twobrain_rec_server/api/health.py`
- [X] T118 Run pytest, Ruff, compileall, local compose config, production compose config, and secret/content scan, then update evidence in `specs/012-server-ingest-foundation/quickstart.md`

---

## Phase 11: Second Review Hackathon Remediation Before PR

**Purpose**: Close blockers found by the five-round multi-agent review hackathon. These tasks supersede the earlier "ready for PR" assumption and block PR/deployment-plan readiness until completed.

**GitHub tracking**: Main blocker packages are #112-#119; additional confirmed findings are #120-#124.

### Tests And Proof Gates

- [X] T119 [P] Add finalize integrity negative tests for mismatched manifest SHA, track SHA, byte length, role/object mapping, and expected size mismatches in `apps/server/tests/integration/test_finalize_integrity.py`
- [X] T120 [P] Add resumable range tests for byte offsets, gaps, overlapping parts, out-of-order parts, negative offsets, negative expected sizes, and offset-mismatched idempotent replay in `apps/server/tests/integration/test_upload_resume.py`
- [X] T121 [P] Add session lifecycle and idempotency tests for expired sessions, terminal-state finalize/abort, one-active-session-per-meeting, and conflicting meeting creates in `apps/server/tests/integration/test_upload_session_lifecycle.py`
- [X] T122 [P] Add same-workspace meeting hijack, inactive membership, wrong organization, wrong user/device binding, and missing DB fail-closed auth tests in `apps/server/tests/integration/test_tenant_authorization.py`
- [X] T123 [P] Add true cold-start persistence tests that reset all ingest store references and prove meeting/session/status/missing-ranges/finalize reads reload from Postgres in `apps/server/tests/integration/test_persistent_ingest_storage.py`
- [X] T124 [P] Add persisted audit content tests for event type, tenant, actor user, device, event ordering, and redacted metadata values in `apps/server/tests/integration/test_audit_persistence.py`
- [X] T125 [P] Add TrackArtifact and ManifestSnapshot persistence assertions for finalized rows, descriptor metadata, object keys, checksums, and manifest provenance in `apps/server/tests/integration/test_persistent_ingest_storage.py`
- [X] T126 [P] Add positive and negative readiness tests for `200 ready`, `503 not_ready`, and non-mutating dependency checks in `apps/server/tests/integration/test_health_readiness.py`
- [X] T127 [P] Add actual OpenAPI contract tests that compare runtime `/openapi.json` with `specs/012-server-ingest-foundation/contracts/openapi.yaml` for schemas, status codes, headers, and field names in `apps/server/tests/contract/test_openapi_contract_drift.py`
- [X] T128 [P] Add Alembic migration smoke tests against a Postgres-compatible test database or compose service, without `Base.metadata.create_all`, in `apps/server/tests/integration/test_postgres_migrations.py`
- [X] T129 [P] Add real MinIO round-trip tests for bucket provisioning, object write/read, object key compatibility, and storage failure behavior in `apps/server/tests/integration/test_minio_upload_storage.py`
- [X] T130 [P] Add upload memory/streaming tests that prove large parts are not fully buffered before checksum/size enforcement in `apps/server/tests/integration/test_streaming_upload.py`

### Implementation Remediation

- [X] T131 Fix ingest store ownership so all services use a single module-owned store reference and tests can perform a true process-store reset in `apps/server/src/twobrain_rec_server/ingest/store.py`
- [X] T132 Implement finalize integrity validation against uploaded part SHA, byte length, manifest SHA, expected track sizes, and role mapping in `apps/server/src/twobrain_rec_server/ingest/finalize.py`
- [X] T133 Persist finalized TrackArtifact rows from validated TrackDescriptor metadata and create ManifestSnapshot rows on finalize in `apps/server/src/twobrain_rec_server/ingest/store.py`
- [X] T134 Rewrite missing-range calculation to use persisted byte intervals and reject gaps, overlaps, negative offsets, invalid part numbers, and mismatched offset replay in `apps/server/src/twobrain_rec_server/ingest/ranges.py`
- [X] T135 Enforce cumulative per-track and per-package/session upload limits, expected track sizes, and package bounds before object writes in `apps/server/src/twobrain_rec_server/ingest/parts.py`
- [X] T136 Replace full-body upload buffering with bounded streaming checksum and size enforcement in `apps/server/src/twobrain_rec_server/api/ingest.py`
- [X] T137 Make upload part persistence cleanup-aware and race-safe for duplicate concurrent PUTs, DB failures after object writes, and temporary object accounting in `apps/server/src/twobrain_rec_server/ingest/parts.py`
- [X] T138 Enforce upload session TTL, terminal-state transition guards, finalized_at persistence, and one active non-terminal upload session per meeting in `apps/server/src/twobrain_rec_server/ingest/lifecycle.py`
- [X] T139 Load persisted meetings when creating upload sessions, persist meeting status on session creation, and reject conflicting idempotent meeting creates in `apps/server/src/twobrain_rec_server/ingest/sessions.py`
- [X] T140 Persist started_at, ended_at, processing placeholder status, upload session processing fields, and lifecycle timing consistently in `apps/server/src/twobrain_rec_server/ingest/store.py`
- [X] T141 Fail closed when persistent auth context is unavailable and enforce meeting owner/device authorization before creating upload sessions in `apps/server/src/twobrain_rec_server/auth/dependencies.py`
- [X] T142 Sanitize and bound client-supplied audit metadata, abort reasons, local recording identifiers, title, request IDs, and auth-context logging in `apps/server/src/twobrain_rec_server/ingest/audit.py`
- [X] T143 Persist actor user and device identifiers on every ingest audit event in `apps/server/src/twobrain_rec_server/ingest/audit.py`
- [X] T144 Align runtime schemas, committed OpenAPI YAML, status codes, auth headers, idempotency key semantics, Problem schema fields, part numbering, readiness response shape, and missing-ranges field names in `specs/012-server-ingest-foundation/contracts/openapi.yaml`
- [X] T145 Implement Idempotency-Key handling for meeting creation, upload session creation, and upload part replay/conflict responses in `apps/server/src/twobrain_rec_server/api/ingest.py`
- [X] T146 Add explicit Alembic migration command/entrypoint, copy `alembic.ini` and migration files into the image, and document migration execution in `infra/server/Dockerfile`
- [X] T147 Add deterministic local identity/device bootstrap command for 012 smoke tests and document production-safe bootstrap boundaries in `apps/server/scripts/seed_dev_identity.py`
- [X] T148 Update `apps/server/scripts/upload_test_artifact.py` to accept organization, user, workspace, and device IDs separately and to match the finalized auth/header contract
- [X] T149 Move MinIO bucket provisioning out of readiness or guarantee it before first upload, and use least-privilege API MinIO credentials separate from MinIO root credentials in `infra/docker-compose.yml`
- [X] T150 Return contract-compliant readiness status codes, add API healthchecks, and avoid leaking dependency detail from public readiness surfaces in `apps/server/src/twobrain_rec_server/api/health.py`
- [X] T151 Remove import-time app construction or align it with the selected uvicorn mode, and add FastAPI lifespan cleanup for DB engine/runtime clients in `apps/server/src/twobrain_rec_server/main.py`
- [X] T152 Split production runtime dependencies from dev/test tooling and add reproducible dependency constraints for the server image in `apps/server/pyproject.toml`
- [X] T153 Harden production compose API exposure, resource limits, log rotation, and production fail-closed config validation in `infra/docker-compose.yml`
- [X] T154 Update `specs/012-server-ingest-foundation/quickstart.md`, `docs/current-product-status.md`, and `docs/prd-voice-layer-final.md` with the second review verdict, validation requirements, and remaining PR blockers

### Additional Confirmed Findings

- [X] T155 Persist degraded finalize failure state and audit event before returning manifest validation errors in `apps/server/src/twobrain_rec_server/ingest/finalize.py`
- [X] T156 Persist explicit audit event objects returned by the current operation instead of reading the global latest event from `store.audit_events[-1]` in `apps/server/src/twobrain_rec_server/ingest/audit.py`
- [X] T157 Add cleanup accounting rows for temporary upload objects and orphaned object writes in `apps/server/src/twobrain_rec_server/db/models/ingest.py`
- [X] T158 Load processing placeholder views from Postgres after restart instead of only reading process-local meetings in `apps/server/src/twobrain_rec_server/ingest/processing_placeholder.py`
- [X] T159 Extend access policy placeholders to represent admin eligibility, deletion-state placeholders, and future share/download/export denial reasons in `apps/server/src/twobrain_rec_server/ingest/access_policy.py`
- [X] T160 Split expected track roles from expected track sizes in API schemas, data model, database model, and migration semantics in `apps/server/src/twobrain_rec_server/api/schemas.py`
- [X] T161 Validate `local_recording_id`, `title`, `expected_track_sizes`, `part_number`, `X-Byte-Offset`, and `X-Request-Id` length/charset/range constraints at the API boundary in `apps/server/src/twobrain_rec_server/api/schemas.py`
- [X] T162 Map upload-part limit violations, storage dependency failures, and DB persistence failures to contract Problem responses instead of generic 500s in `apps/server/src/twobrain_rec_server/api/ingest.py`
- [X] T163 Make readiness checks non-mutating or move provisioning to startup, and add protected/internal readiness routing if dependency detail must remain visible in `apps/server/src/twobrain_rec_server/api/health.py`
- [X] T164 Disable or protect FastAPI `/docs`, `/redoc`, and `/openapi.json` in production while preserving local developer access in `apps/server/src/twobrain_rec_server/main.py`
- [X] T165 Move synchronous MinIO SDK calls off the async event loop or wrap them in bounded worker execution in `apps/server/src/twobrain_rec_server/storage/minio_client.py`
- [X] T166 Use structured JSON logging that actually emits request_id, status, duration, safe headers, and redacted/template paths instead of dropping `extra` fields in `apps/server/src/twobrain_rec_server/observability/logging.py`
- [X] T167 Redact or template resource UUIDs in request path logs for meeting/upload-session endpoints in `apps/server/src/twobrain_rec_server/observability/logging.py`
- [X] T168 Add branch-complete auth tests for inactive membership, wrong organization, device bound to another workspace, and device bound to another user in `apps/server/tests/integration/test_tenant_authorization.py`
- [X] T169 Add exact degraded/failure response assertions for domain error codes instead of loose `{400, 422}` acceptance in `apps/server/tests/integration/test_degraded_ingest.py`
- [X] T170 Add positive readiness tests, protected readiness tests, and 503 response assertions in `apps/server/tests/integration/test_health_readiness.py`
- [X] T171 Add audit event ordering/content/redaction assertions beyond count-only checks in `apps/server/tests/integration/test_audit_persistence.py`
- [X] T172 Make fake object storage enforce exact stream length invariants and failure injection hooks in `apps/server/tests/fakes/fake_minio.py`
- [X] T173 Remove ad-hoc `asyncio.run()` calls from integration tests and use pytest-asyncio/anyio-compatible helpers in `apps/server/tests/integration/test_persistent_ingest_storage.py`
- [X] T174 Add OpenAPI Problem schema/code enum tests for `request_id` versus `trace_id` naming and runtime error code coverage in `apps/server/tests/contract/test_openapi_contract_drift.py`
- [X] T175 Add tests for `started_at` and `ended_at` persistence and response behavior in `apps/server/tests/integration/test_persistent_ingest_storage.py`
- [X] T176 Add tests proving ManifestSnapshot rows are persisted and used for future processing/deletion provenance in `apps/server/tests/integration/test_persistent_ingest_storage.py`
- [X] T177 Add tests proving ProcessingPlaceholder status is synchronized with finalized/degraded/aborted meeting state in `apps/server/tests/integration/test_processing_placeholder.py`
- [X] T178 Add tests proving the upload helper uses separate organization, user, workspace, and device IDs and no ignored bearer-token-only auth path in `apps/server/tests/integration/test_upload_helper_contract.py`
- [X] T179 Add production config validation tests that reject localhost endpoints, default dev secrets, and root MinIO credentials when `TWOBRAIN_ENV=production` in `apps/server/tests/unit/test_config_validation.py`
- [X] T180 Add compose validation tests or lint checks for API healthcheck, localhost/proxy binding policy, resource limits, log rotation, runtime-only dependencies, and locked dependency constraints in `apps/server/tests/integration/test_compose_hardening.py`

---

## Phase 12: Final Sanity Remediation Before Ready PR

**Purpose**: Close the final 012 review findings found after PR #125 was opened and after `speckit-bootstrap` / issue-canon was merged into `master`. These tasks block converting PR #125 from draft to ready-for-review and block any deployment plan handoff.

**GitHub tracking**: Final sanity packages are #127-#131.

- #127: T181, T182, T187, T188, T195
- #128: T183, T189, T190, T191, T195
- #129: T184, T192, T195
- #130: T186, T193, T195
- #131: T185, T194, T195

### Tests And Proof Gates

- [X] T181 [P] Add an empty-schema readiness regression test proving `/api/v1/health/ready` returns `503 not_ready` until required ingest tables or Alembic version state exist in `apps/server/tests/integration/test_health_readiness.py`
- [X] T182 [P] Add migration bootstrap proof that starts from a clean database, runs the documented Alembic path, and then proves identity seeding plus `/api/v1/meetings` works without `Base.metadata.create_all` in `apps/server/tests/integration/test_postgres_migrations.py`
- [X] T183 [P] Add upload memory/part-size tests proving successful large upload parts are not accumulated as a full in-memory `bytes` object and that configured part limits fail before MinIO writes in `apps/server/tests/integration/test_streaming_upload.py`
- [X] T184 [P] Add current-toolchain OpenAPI drift assertions for FastAPI/Pydantic `ValidationError.input` and `ValidationError.ctx` fields so runtime `/openapi.json` and `specs/012-server-ingest-foundation/contracts/openapi.yaml` stay aligned in `apps/server/tests/contract/test_openapi_contract_drift.py`
- [X] T185 [P] Add recursive audit redaction tests for substring secret keys, nested metadata, `api_token`, `minio_secret_key`, `signed_url`, and content-bearing fields in `apps/server/tests/integration/test_audit_persistence.py`
- [X] T186 [P] Add lint/toolchain reproducibility coverage or lockfile policy proving `uv run --extra dev ruff check .` uses a deterministic supported Ruff version and import ordering in `apps/server/pyproject.toml`

### Implementation Remediation

- [X] T187 Add a documented Alembic migration bootstrap path for local and production Compose, either as a one-shot migration service or explicit entrypoint command, in `infra/docker-compose.yml`
- [X] T188 Make readiness schema-aware and fail closed when required ingest tables or Alembic version state are missing instead of only executing `SELECT 1` in `apps/server/src/twobrain_rec_server/api/health.py`
- [X] T189 Add explicit configurable upload part-size limits separate from full track/package limits and expose the setting in `apps/server/src/twobrain_rec_server/config.py`
- [X] T190 Replace successful upload full-body buffering with a bounded spool/streaming checksum path that does not return a full track-sized `bytes` object before MinIO persistence in `apps/server/src/twobrain_rec_server/api/upload_stream.py`
- [X] T191 Update upload part acceptance to consume the new bounded stream/spool contract and preserve checksum, object-key, cleanup-accounting, idempotency, and range semantics in `apps/server/src/twobrain_rec_server/ingest/parts.py`
- [X] T192 Regenerate and commit the runtime-aligned OpenAPI contract after the current toolchain changes in `specs/012-server-ingest-foundation/contracts/openapi.yaml`
- [X] T193 Fix Ruff import-order violations under the current supported dev toolchain across `apps/server/src/twobrain_rec_server/`
- [X] T194 Harden audit metadata filtering by reusing recursive redaction semantics and substring secret/content matching in `apps/server/src/twobrain_rec_server/ingest/audit.py`
- [X] T195 Run full final validation (`pytest`, Ruff, compileall, dev/prod Compose config, empty-schema readiness smoke, OpenAPI drift, secret/content scan) and update evidence plus remaining-risk notes in `specs/012-server-ingest-foundation/quickstart.md`

---

## Phase 13: Pre-Merge Polish To Remove Residual Warnings

**Purpose**: Remove the final non-blocking test warnings found after Phase 12 so PR #125 can merge without known warning debt.

**GitHub tracking**: Pre-merge polish packages are #132-#133.

- #132: T196, T198, T200
- #133: T197, T199, T200

- [X] T196 Add the Starlette-supported `httpx2` TestClient dependency and lock it in `apps/server/pyproject.toml` and `apps/server/uv.lock`
- [X] T197 Add Alembic `path_separator = os` configuration to remove legacy config parsing warnings in `apps/server/alembic.ini`
- [X] T198 Prove the server test suite has no residual warnings under current dependencies in `apps/server/tests/`
- [X] T199 Prove Alembic clean-database migration smoke runs without legacy config warnings in `apps/server/tests/integration/test_postgres_migrations.py`
- [X] T200 Run full pre-merge validation and update evidence in `specs/012-server-ingest-foundation/quickstart.md`

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
- **Phase 10 Review Remediation**: Depends on all prior 012 implementation phases and blocks PR/deployment-plan readiness until T106-T118 are complete.
- **Phase 11 Second Review Hackathon Remediation**: Depends on Phase 10 and blocks PR/deployment-plan readiness until T119-T180 are complete.
- **Phase 12 Final Sanity Remediation**: Depends on Phase 11 and the merged issue-canon/bootstrap layer from `master`; blocks ready PR/deployment-plan handoff until T181-T195 are complete and verified.
- **Phase 13 Pre-Merge Polish**: Depends on Phase 12; removes residual warning debt before merge.

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
- Review remediation tests T106-T111 can run in parallel before implementation tasks T112-T117.
- Second review tests T119-T130 can run in parallel before implementation tasks T131-T154.
- Additional confirmed finding tasks T155-T180 can be split by domain and run alongside matching Phase 11 implementation work once their owning tests are in place.
- Final sanity tests T181-T186 can run in parallel before implementation tasks T187-T194. T195 must run last after all Phase 12 remediation tasks are complete.
- Pre-merge polish tasks T196-T197 can run in parallel; T198-T200 must run after dependency/config changes are complete.

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
- `RLS-hardening` GitHub issue candidate: implement PostgreSQL RLS policies for `organizations`, `workspaces`, `meetings`, `upload_sessions`, `upload_parts`, `track_artifacts`, `manifest_snapshots`, `temporary_upload_objects`, and `ingest_audit_events` after auth provider context propagation is stable. Until then, application-level checks in `apps/server/src/twobrain_rec_server/auth/dependencies.py`, `apps/server/src/twobrain_rec_server/auth/authorization.py`, and ingest route dependencies remain the compensating control.
- `direct-object-upload`: Direct object-storage upload URLs remain out of scope for 012 and require a separate security/lifecycle review.
- `015-mediascribe-processing-pipeline`: Temporal workflow start and MediaScribe job submission remain out of scope for 012.
