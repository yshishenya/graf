# Feature Specification: Backend Tenant Isolation RLS Hardening

**Feature Branch**: `031-rls-hardening`

**Created**: 2026-06-15

**Status**: Draft

**Input**: User description: "Implement the independent `031-rls-hardening`
slice. Harden tenant isolation with PostgreSQL row-level security for 2brain
Rec backend data before dashboard, access, sharing, retention, and deletion
slices expose meeting and transcript content. Follow the full SDD Spec Kit
cycle."

## Product Scope Boundary

This feature adds a database-enforced tenant isolation layer for the accepted
backend foundations. The product already has application-level authorization
checks from `012-server-ingest-foundation`, `013-federated-auth-foundation`,
`014-desktop-upload-queue`, and `015-mediascribe-processing-pipeline`. This
slice makes tenant isolation fail closed inside the database as a second line
of defense before future dashboard, sharing, download, retention, deletion, and
admin surfaces expose meeting content to more code paths.

This feature does not add product UI, dashboard screens, sharing, downloads,
retention jobs, deletion execution, MediaScribe behavior, desktop capture,
upload queue behavior, or new account-login flows. It is a backend security and
operational-readiness slice.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Prevent Cross-Workspace Meeting Exposure (Priority: P1)

As a security owner, I want meeting, upload, processing, transcript, and audit
rows to remain invisible outside the active workspace even if a future service
query forgets a workspace filter, so that one customer's meeting content cannot
leak to another customer.

**Why this priority**: Dashboard and review surfaces will soon query
transcript, diarization, audio metadata, and processing state. A single missing
application filter must not become a customer-data breach.

**Independent Test**: Seed two organizations/workspaces with meetings,
artifacts, processing rows, transcript segments, and audit rows. Execute
read/write/update/delete attempts under each workspace context and with no
workspace context. Verify only the matching workspace can see or mutate its own
rows and all missing or mismatched contexts fail closed.

**Acceptance Scenarios**:

1. **Given** workspace A and workspace B both have processed meetings, **When**
   a request authenticated for workspace A queries meeting and processing data,
   **Then** the database returns only workspace A rows.
2. **Given** a request has no active workspace context, **When** it queries or
   mutates tenant-owned backend tables, **Then** the database denies access or
   returns no tenant rows.
3. **Given** a future dashboard query accidentally omits a workspace predicate,
   **When** it runs under workspace A context, **Then** workspace B meetings,
   transcript text, diarization labels, artifact metadata, and audit rows remain
   inaccessible.

---

### User Story 2 - Keep Workers And Internal Jobs Tenant-Scoped (Priority: P1)

As an operator, I want processing workers and internal maintenance jobs to run
with explicit tenant scope, so that background processing, cleanup, smoke tests,
and future retention/deletion jobs cannot accidentally process another
workspace's meetings.

**Why this priority**: `015` added durable processing jobs and imported
transcript content. Background jobs touch sensitive rows without a browser
session, so they need the same isolation guarantee as request paths.

**Independent Test**: Run worker-style pickup, processing-status, smoke-cleanup,
and maintenance scenarios with matching, mismatched, and missing tenant
contexts. Verify matching context works, mismatched context is denied, and
approved internal maintenance context is explicit, audited, and limited.

**Acceptance Scenarios**:

1. **Given** a processing worker is handling a meeting in workspace A, **When**
   it reads required upload, artifact, workflow, MediaScribe, result, segment,
   audit, or dependency rows, **Then** only workspace A rows are visible.
2. **Given** worker context is missing or stale, **When** processing pickup or
   result import runs, **Then** the operation fails closed and records
   metadata-only evidence rather than processing unscoped data.
3. **Given** an approved smoke cleanup or migration verification path needs
   broader access, **When** it runs, **Then** the broader access is explicit,
   bounded to the operation, and produces operator-visible evidence.

---

### User Story 3 - Protect Identity, Device, Session, And Membership Boundaries (Priority: P1)

As a product owner, I want auth, device, session, membership, and workspace
policy data to follow the same tenant isolation rules as meeting data, so that
account linking, registered-device trust, and workspace policies cannot leak or
be confused across tenants.

**Why this priority**: Future dashboard and desktop embedded surfaces depend on
accurate identity and device state. Weak isolation in identity tables would
undermine meeting isolation even if meeting rows are protected.

**Independent Test**: Seed users, sessions, devices, memberships, provider
identities, auth policies, and audit events across organizations/workspaces.
Verify each actor sees only the identity and policy records allowed by their
workspace/organization context and role.

**Acceptance Scenarios**:

1. **Given** a user belongs to workspace A but not workspace B, **When** they
   query session, device, membership, auth-policy, or provider-link state,
   **Then** workspace B identity records remain inaccessible.
2. **Given** an admin role is scoped to one workspace or organization, **When**
   admin-only identity reads are attempted, **Then** access remains limited to
   that authorized scope.
3. **Given** a revoked session or device attempts to reuse stale context,
   **When** it touches tenant-owned rows, **Then** access fails closed.

---

### User Story 4 - Roll Out Safely With Evidence And Rollback (Priority: P2)

As an operator preparing production hardening, I want a safe rollout and
rollback path for tenant isolation changes, so that existing ingest,
authentication, production smoke, and processing flows stay usable while
unscoped access is blocked.

**Why this priority**: RLS-style hardening can break legitimate queries if
context propagation is incomplete. The rollout must prove stronger security
without silently disabling accepted product flows.

**Independent Test**: Apply the hardening migration in local and production-like
test environments, run accepted ingest/auth/processing/smoke validation, run
negative cross-tenant probes, and verify rollback or halt instructions are
available if a gate fails.

**Acceptance Scenarios**:

1. **Given** existing accepted server tests pass before hardening, **When** the
   hardening is enabled, **Then** same-tenant ingest, auth, upload helper,
   processing, and smoke cleanup paths still pass.
2. **Given** any accepted same-tenant path fails after hardening, **When**
   validation reports the result, **Then** rollout is halted or rollback is
   clearly instructed before production readiness is claimed.
3. **Given** cross-tenant negative probes are executed, **When** hardening is
   active, **Then** all probes are denied or return no foreign tenant data.

---

### User Story 5 - Preserve Downstream Product Boundaries (Priority: P2)

As engineering, I want this hardening slice to prepare the backend for future
`016`, `017`, and `018` slices without implementing their product behavior, so
that dashboard, sharing, download, retention, and deletion work can later build
on a secure data boundary.

**Why this priority**: This work is useful only if it lowers future risk without
accidentally broadening scope into unfinished product features.

**Independent Test**: Review API routes, OpenAPI output, tests, and docs after
the slice. Confirm no dashboard meeting detail, transcript download, share,
public page, deletion execution, retention job, or new UI surface was added.

**Acceptance Scenarios**:

1. **Given** the feature is complete, **When** product surface boundaries are
   checked, **Then** `016` dashboard/review, `017` share/download, and `018`
   retention/deletion execution remain unimplemented.
2. **Given** future feature authors inspect this slice, **When** they read the
   contracts and quickstart, **Then** they can see how to run tenant-scoped
   queries safely without guessing isolation rules.

### Edge Cases

- A query has no tenant context because a request dependency, worker bootstrap,
  or test fixture forgot to set it.
- A user belongs to multiple workspaces and switches context between requests.
- A workspace admin attempts to access another workspace in the same
  organization.
- A production smoke identity needs cleanup across seeded rows without
  permanently granting unbounded access.
- A migration, backup, restore, or readiness probe runs before normal request
  context exists.
- A future dashboard query omits a workspace predicate.
- A worker retry resumes after session, membership, device, or workspace state
  changed.
- A row contains both workspace and organization relationships, and the
  workspace relationship must remain the tighter boundary.
- A table has nullable meeting/user references for audit or dependency records.
- Tests use SQLite or local fake stores that cannot enforce database-level
  isolation directly.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST enforce database-level fail-closed tenant
  isolation for tenant-owned backend records in addition to existing
  application-level authorization checks.
- **FR-002**: Tenant-owned reads, inserts, updates, and deletes MUST be denied
  or return no rows when no active tenant context is present.
- **FR-003**: Workspace-scoped context MUST expose only rows belonging to the
  active workspace unless a narrower owner/device rule denies them.
- **FR-004**: Organization-scoped or admin context MUST be explicit,
  role-gated, auditable, and no broader than the actor's approved
  organization/workspace scope.
- **FR-005**: Internal worker and maintenance paths MUST set explicit tenant or
  approved maintenance context before reading or mutating tenant-owned rows.
- **FR-006**: Approved maintenance context MUST be bounded to named operational
  tasks such as migration verification, smoke cleanup, backup/restore
  rehearsal, or explicit operator diagnostics.
- **FR-007**: The system MUST protect meeting, upload, artifact, manifest,
  temporary object, ingest audit, processing workflow, MediaScribe job,
  processing result, transcript segment, diarization segment, processing audit,
  and processing dependency rows.
- **FR-008**: The system MUST protect organization, workspace, user identity,
  workspace membership, registered device, external identity, auth session,
  session-device binding, workspace auth policy, provider-link state, callback
  state, consent copy, and auth audit rows according to their tenant scope.
- **FR-009**: Tenant context MUST be derived from authenticated request,
  session, membership, registered device, worker job, or explicit operator
  maintenance context, not from client-supplied meeting titles, file names, or
  untrusted request body fields.
- **FR-010**: The system MUST reject stale or revoked session/device context
  before tenant-owned rows can be read or mutated.
- **FR-011**: Same-tenant ingest, auth, upload helper, processing pickup,
  processing status, result import, and production-smoke cleanup flows MUST keep
  their accepted behavior after hardening.
- **FR-012**: Cross-tenant reads of transcript text, diarization labels, media
  artifact metadata, storage object references, processing dependency state,
  sessions, devices, memberships, and audit events MUST be blocked in 100% of
  validation probes.
- **FR-013**: Cross-tenant writes and deletes MUST be blocked in 100% of
  validation probes.
- **FR-014**: Hardening rollout MUST include local and production-like
  validation evidence before any production-readiness claim.
- **FR-015**: Rollout evidence MUST include positive same-tenant probes,
  negative cross-tenant probes, missing-context probes, worker-context probes,
  and maintenance-context probes.
- **FR-016**: Migration and rollback guidance MUST distinguish safe rollout,
  halt, rollback, and manual-investigation outcomes.
- **FR-017**: Logs, diagnostics, traces, validation evidence, and failure
  messages MUST NOT expose raw transcript text, raw audio, credentials, tokens,
  signed URLs, passwords, or live secret paths.
- **FR-018**: The system MUST produce metadata-only evidence for denied or
  missing tenant context, including request/job class, table or feature area,
  reason category, and validation outcome.
- **FR-019**: The feature MUST keep dashboard meeting detail, share links,
  downloads/exports, retention jobs, deletion execution, public pages, billing,
  admin UI, and desktop capture/upload behavior out of scope.
- **FR-020**: The feature MUST document compensating controls that remain until
  all future tables and downstream features are covered by tenant isolation.
- **FR-021**: The feature MUST define how newly added tenant-owned tables must
  declare their isolation scope before future implementation begins.
- **FR-022**: The feature MUST provide a repeatable verification path that can
  be run in CI/local validation without requiring live customer data.
- **FR-023**: The feature MUST document how environments without database-level
  enforcement are handled in tests without weakening production guarantees.
- **FR-024**: The feature MUST preserve owner-controlled storage and egress
  boundaries: no desktop-held object-storage credentials, no MediaScribe
  credentials in clients, and no new direct object upload behavior.
- **FR-025**: The feature MUST update product/status documentation only to
  describe the hardening boundary and MUST NOT claim user rollout readiness by
  itself.

### Key Entities *(include if feature involves data)*

- **Tenant Context**: The active organization, workspace, actor, device, role,
  and operation class that determines which tenant-owned rows may be visible or
  mutable.
- **Tenant-Owned Row**: Any backend row belonging to an organization,
  workspace, user, device, meeting, upload session, artifact, processing job,
  transcript, audit event, auth session, or lifecycle dependency.
- **Workspace-Scoped Data**: Meeting, upload, artifact, manifest, processing,
  transcript, diarization, dependency, audit, policy, session, and device rows
  whose tightest isolation boundary is a workspace.
- **Organization-Scoped Data**: Organization, user identity, provider identity,
  and cross-workspace administrative rows whose access must still be bounded by
  explicit membership or approved organization-level role.
- **Maintenance Context**: A bounded operator or internal-job context used for
  migration verification, smoke cleanup, backup/restore rehearsal, or
  diagnostics when ordinary request context is unavailable.
- **Isolation Probe**: A positive or negative validation scenario proving that
  same-tenant access works, missing-context access fails closed, and
  cross-tenant access cannot see or mutate foreign rows.
- **Hardening Evidence**: Metadata-only proof that rollout, validation,
  rollback, and denied-access outcomes were checked without exposing meeting
  content or secrets.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of identified existing tenant-owned backend tables are
  classified by isolation scope before implementation begins.
- **SC-002**: 100% of covered tenant-owned tables deny or return no rows for
  missing tenant context in automated validation.
- **SC-003**: 100% of cross-workspace read probes against covered meeting,
  upload, artifact, processing, transcript, diarization, dependency, auth,
  session, device, membership, and audit data are denied or return no foreign
  rows.
- **SC-004**: 100% of cross-workspace write/delete probes against covered
  tenant-owned data are denied.
- **SC-005**: Existing accepted same-tenant server validation for ingest, auth,
  upload helper, processing, and production-smoke cleanup remains green after
  hardening.
- **SC-006**: Worker-style processing and maintenance-context validation covers
  matching, mismatched, missing, and approved-maintenance context outcomes.
- **SC-007**: Rollout evidence includes pass/blocked verdicts for local and
  production-like validation plus rollback or halt instructions for failures.
- **SC-008**: Secret/content scans over specs, plans, contracts, quickstart,
  evidence, tests, and logs find 0 raw audio, transcript text, credentials,
  tokens, signed URLs, passwords, or live secret paths.
- **SC-009**: No new dashboard detail, transcript download, audio download,
  share, public page, retention, deletion execution, billing, admin UI, desktop
  capture, or desktop upload behavior is observable after the slice.
- **SC-010**: Future feature authors can identify the required tenant isolation
  contract for a new backend table from this feature's artifacts without reading
  implementation code.

## Assumptions

- `030-mvp-experience-design-system` is not an input for this feature.
- The accepted inputs are the PRD, current product status, constitution,
  `012-server-ingest-foundation`, `013-federated-auth-foundation`,
  `014-desktop-upload-queue`, `015-mediascribe-processing-pipeline`, and
  `021-production-deployment-plan`.
- PostgreSQL is the production database for tenant isolation enforcement.
- Existing application-level checks remain mandatory and are not replaced by
  database-level enforcement.
- Local tests may use fakes or SQLite for some paths, but production-like
  validation must prove database-level enforcement on PostgreSQL.
- A future feature must classify any new tenant-owned table before it can be
  merged.
- User-facing dashboard, sharing, download, retention, deletion, and admin UX
  decisions remain in their own future specs.
