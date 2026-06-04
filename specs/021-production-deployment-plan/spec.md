# Feature Specification: Production Deployment Plan

**Feature Branch**: `021-production-deployment-plan`

**Created**: 2026-06-04

**Status**: Draft

**Input**: User description: "Deployment plan for the 2brain Rec production rollout in 2brain.pro infrastructure with public rec.2brain.dev endpoint: Docker Compose layout, secrets and environment policy, volumes and backups, migration runbook, first production smoke, and rollback."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Operator Can Prepare The Production Stack (Priority: P1)

A deployment operator can read a single production deployment plan and understand which 2brain Rec services, domains, secrets, volumes, networks, and operational boundaries must exist before the first production rollout.

**Why this priority**: The first production rollout cannot be trusted until the operator has a complete, reviewable deployment boundary that preserves owner-controlled storage, secret discipline, and isolated Rec infrastructure.

**Independent Test**: Can be tested by having an operator review the plan and confirm every required service, public endpoint, secret source, persistent volume, backup boundary, and external dependency is accounted for without needing tribal knowledge.

**Acceptance Scenarios**:

1. **Given** the deployment plan, **When** an operator prepares production infrastructure, **Then** the operator can identify the Rec-owned services, exposed ports, internal-only services, named volumes, required secrets, and expected public URL.
2. **Given** the deployment plan, **When** security reviews it, **Then** no required credential, token, API key, password, signed URL, or private endpoint is stored in product documentation or client-facing configuration.
3. **Given** existing shared 2brain infrastructure, **When** the operator reviews Rec storage requirements, **Then** the plan distinguishes Rec-owned Postgres and MinIO boundaries from shared operational services.

---

### User Story 2 - Operator Can Run Migration And Backup Safely (Priority: P1)

A deployment operator can run the first production database/storage migration with a documented backup-before-change procedure and a clear decision point for forward progress or rollback.

**Why this priority**: Production deployment can lose user trust if migration, backup, restore, or volume ownership is ambiguous.

**Independent Test**: Can be tested by dry-running the migration runbook against a staging or production-like environment and verifying preflight, backup, migration, verification, and rollback decision steps are explicit and ordered.

**Acceptance Scenarios**:

1. **Given** a production-like environment, **When** the operator follows the migration runbook, **Then** the operator can produce backup evidence before any irreversible schema or storage change.
2. **Given** a failed migration verification, **When** the operator follows the rollback runbook, **Then** the operator can restore the prior service state or stop rollout without claiming a successful deployment.
3. **Given** a successful migration, **When** the operator records evidence, **Then** the deployment record includes migration version, backup reference, verification outcome, and outstanding risks without exposing secrets.

---

### User Story 3 - Operator Can Perform First Production Smoke (Priority: P1)

A deployment operator can execute a first production smoke test for the Rec backend foundation and confirm the public endpoint, health checks, storage, metadata persistence, and upload boundary work without implying MediaScribe processing, dashboard readiness, or deletion execution is complete.

**Why this priority**: The first live smoke must prove the production deployment boundary works while preserving the accepted scope of 012 and avoiding false product claims.

**Independent Test**: Can be tested by running the smoke procedure from a clean environment using a fixed non-sensitive test artifact and verifying expected status, logs, storage artifacts, and rollback decision points.

**Acceptance Scenarios**:

1. **Given** production deployment is started, **When** the operator checks the public endpoint, **Then** liveness succeeds and readiness succeeds only when required Rec-owned dependencies and required secrets are available.
2. **Given** a small non-sensitive test recording artifact, **When** the operator uploads it through the production endpoint, **Then** the artifact finalizes at the accepted ingest boundary and does not create MediaScribe, Temporal, notes, retention, deletion, share, or dashboard claims outside the active scope.
3. **Given** production logs and smoke evidence, **When** they are reviewed, **Then** they contain safe metadata only and no raw audio, transcript text, bearer tokens, MinIO credentials, MediaScribe credentials, Langfuse credentials, signed URLs, or secret values.

---

### User Story 4 - Operator Can Roll Back Or Halt Rollout (Priority: P2)

A deployment operator can roll back or halt the first production rollout when health, migration, storage, upload, backup, or secret checks fail.

**Why this priority**: Rollback must be defined before rollout so production failure does not create improvised, unsafe operations.

**Independent Test**: Can be tested by reviewing rollback scenarios and performing at least one non-destructive rollback rehearsal in a production-like environment.

**Acceptance Scenarios**:

1. **Given** a deployment health check fails, **When** the operator follows rollback guidance, **Then** the operator can return to the prior known-good state or keep the service offline with truthful status.
2. **Given** a storage or database backup cannot be verified, **When** rollout is attempted, **Then** the runbook blocks rollout before user traffic or smoke artifacts are accepted.
3. **Given** rollback leaves temporary artifacts, **When** the operator records the outcome, **Then** the deployment record lists cleanup obligations, retention/deletion implications, and owner follow-up.

### Edge Cases

- Required secrets are missing, malformed, expired, or accidentally set to local development defaults.
- DNS or TLS for `rec.2brain.dev` is not ready or points to the wrong host.
- Production Compose configuration renders but would expose internal-only services publicly.
- Postgres is reachable but migration state is unexpected.
- MinIO is reachable but bucket, credential, lifecycle, or volume ownership policy is incomplete.
- Disk space is insufficient before, during, or after the smoke upload.
- Backup succeeds but restore verification is missing or inconclusive.
- A migration partially applies and readiness fails.
- A smoke upload succeeds but logs contain forbidden content.
- MediaScribe, Langfuse, or Temporal are unavailable during this deployment slice; the plan must preserve truthful boundaries instead of failing 012-only ingest smoke for future-scope dependencies.
- Rollback cannot delete all temporary artifacts immediately; the record must state what remains and who owns cleanup.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The deployment plan MUST define the production public endpoint as `https://rec.2brain.dev` hosted within 2brain-controlled infrastructure and distinguish it from the broader `2brain.pro` service dependency boundary.
- **FR-002**: The deployment plan MUST define the production Rec service layout, including public-facing services, internal-only services, persistent storage services, and dependencies required for first ingest readiness.
- **FR-003**: The deployment plan MUST define which network ports may be publicly exposed and which services must remain private to the deployment network.
- **FR-004**: The deployment plan MUST define all required production secrets and environment values by purpose, source, owner, rotation expectation, and failure behavior without recording live secret values.
- **FR-005**: The deployment plan MUST require production startup and smoke validation to fail closed when required secrets are missing or set to unsafe local-development defaults.
- **FR-006**: The deployment plan MUST define persistent volumes, ownership expectations, backup inclusion/exclusion, encryption expectations where supported, and disk-full behavior for Rec metadata and object storage.
- **FR-007**: The deployment plan MUST define backup-before-migration requirements for metadata and object storage before any production migration or first-smoke change that can create persistent artifacts.
- **FR-008**: The deployment plan MUST define a migration runbook with preflight, backup evidence, migration execution, verification, failure handling, and rollback decision points.
- **FR-009**: The deployment plan MUST define a restore or rollback rehearsal requirement before production rollout is represented as ready.
- **FR-010**: The deployment plan MUST define the first production smoke procedure for liveness, readiness, configuration, migration state, storage persistence, safe upload finalization, and log redaction.
- **FR-011**: The production smoke MUST use only non-sensitive test artifacts and MUST NOT require raw customer meeting content.
- **FR-012**: The deployment plan MUST define expected smoke outcomes without claiming MediaScribe processing, Temporal workflow starts, dashboard review, sharing, retention execution, or deletion execution unless those later feature slices are active.
- **FR-013**: The deployment plan MUST define how MediaScribe and Langfuse are represented as owner-controlled external dependencies, including health/degraded reporting, server-side secret boundaries, and no desktop-held credentials.
- **FR-014**: The deployment plan MUST define production log and diagnostic forbidden-content rules covering raw audio, transcript text, credentials, tokens, signed URLs, passwords, and sensitive meeting metadata by default.
- **FR-015**: The deployment plan MUST define rollback or halt criteria for failed health checks, failed migrations, failed backup verification, failed storage checks, failed smoke upload, forbidden log content, or unsafe exposure.
- **FR-016**: The deployment plan MUST define deployment evidence that operators must record, including version, configuration fingerprint, migration version, backup reference, smoke result, rollback rehearsal result, and open risks.
- **FR-017**: The deployment plan MUST preserve 012 boundaries: server-mediated ingest, dedicated Rec Postgres and MinIO, no desktop object-storage credentials, no direct object-storage upload URLs, and no processing workflow starts from ingest-only smoke.
- **FR-018**: The deployment plan MUST define how temporary smoke artifacts are labeled, retained, cleaned up, or truthfully accounted for if cleanup cannot complete immediately.
- **FR-019**: The deployment plan MUST define operator-facing degraded states for unavailable optional/future dependencies without weakening readiness gates for active required dependencies.
- **FR-020**: The deployment plan MUST include explicit out-of-scope boundaries for federated auth implementation, desktop uploader implementation, MediaScribe processing implementation, meeting dashboard implementation, sharing/downloads, retention/deletion execution, and driver packaging.

### Key Entities

- **Deployment Environment**: The production or production-like runtime being prepared, including public URL, network exposure, service boundaries, and dependency availability.
- **Service Layout**: The set of Rec-owned services and external dependencies required for first rollout, including which are public, private, persistent, or future-scope.
- **Secret And Environment Policy**: The inventory of required configuration values, where they come from, who owns them, how missing values fail, and how rotation is handled.
- **Persistent Volume**: A storage location that must have ownership, backup, restore, disk-full, encryption, and lifecycle expectations.
- **Migration Runbook**: The ordered production procedure for preflight, backup, migration, verification, failure handling, and rollback.
- **Smoke Test Record**: A metadata-only evidence record proving which health, ingest, storage, log-redaction, and rollback checks passed or failed.
- **Rollback Decision**: A documented halt, restore, or prior-version return decision with cleanup and lifecycle implications.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A deployment operator can identify 100% of public services, private services, persistent volumes, required secrets, and external dependencies from the plan without consulting undocumented tribal knowledge.
- **SC-002**: Security review finds 0 live secrets, tokens, passwords, signed URLs, or credential values in deployment documentation, smoke evidence, logs, or client-facing configuration.
- **SC-003**: Production configuration validation fails closed in 100% of test cases where required secrets are missing or set to unsafe local-development defaults.
- **SC-004**: Migration rehearsal records backup evidence before migration execution in 100% of production-like validation runs.
- **SC-005**: Restore or rollback rehearsal completes or produces an explicit blocked verdict before production rollout is marked ready.
- **SC-006**: First production smoke verifies liveness, readiness, migration state, metadata persistence, object persistence, and safe upload finalization with 100% of expected checks recorded.
- **SC-007**: First production smoke produces 0 MediaScribe jobs, 0 Temporal workflow starts, 0 notes jobs, 0 retention jobs, and 0 deletion jobs when validating only the 012 ingest boundary.
- **SC-008**: Log and evidence scan finds 0 raw audio bytes, transcript text, bearer tokens, MinIO credentials, MediaScribe credentials, Langfuse credentials, signed URLs, or secret values.
- **SC-009**: Rollback or halt criteria cover 100% of documented failure classes: DNS/TLS, secret validation, service health, migration, backup, storage, disk-full, unsafe exposure, smoke upload, and forbidden log content.
- **SC-010**: The deployment record states cleanup or lifecycle accounting for 100% of smoke artifacts and temporary objects created during validation.

## Assumptions

- Feature `012-server-ingest-foundation` is implemented locally and accepted as the active backend ingest foundation, but it is not yet production-deployed.
- Feature numbers `013` through `018` remain reserved for auth, uploader, processing, dashboard, sharing, and retention/deletion slices; this deployment-plan slice uses `021` to avoid changing the existing reserved sequence.
- The production runtime is hosted within 2brain-controlled infrastructure, while the public Rec endpoint remains `https://rec.2brain.dev` unless a later architecture decision changes the domain.
- This slice creates deployment and operational readiness artifacts first; implementation changes should be driven by later plan/tasks if gaps are discovered.
- First production smoke is scoped to the accepted ingest boundary and does not prove end-to-end transcription, notes, dashboard review, sharing, retention, or deletion execution.
- Live customer meeting content is not required for deployment validation.
- MediaScribe at `https://mediascribe.2brain.pro` and Langfuse at `https://langfuse.2brain.pro` remain owner-controlled dependencies for the internal MVP and must be represented truthfully even when not required for ingest-only smoke.
