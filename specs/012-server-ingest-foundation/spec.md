# Feature Specification: Server Ingest Foundation

**Feature Branch**: `012-server-ingest-foundation-continuation`

**Created**: 2026-06-04

**Status**: Draft

**Input**: User description: "Build the first self-hosted 2brain Rec backend foundation that accepts finalized local dual-track recording artifacts from the desktop app through authenticated resumable ingest, stores metadata in Postgres and audio in MinIO, keeps MediaScribe credentials server-side, exposes upload/session state to desktop, and prepares but does not yet ship full dashboard notes deletion or assisted auto-recording."

## Clarifications

### Session 2026-06-04

- Q: Should `012` include desktop uploader/UI work or stay backend-focused? -> A: `012` includes the backend ingest foundation and API/status contracts only; desktop uploader implementation and local upload queue UI are separate later slices.
- Q: Should federated login through Yandex ID, VK ID, Telegram Login, Sber ID, T-ID, and similar providers be implemented in `012`? -> A: No. Federated auth is a separate `013-federated-auth-foundation` slice. `012` must remain provider-neutral and depend only on authenticated user, workspace membership, and registered device identity contracts.
- Q: Should uploads go through the backend API or directly from desktop to object storage? -> A: `012` implements server-mediated upload through the backend API. Contracts remain storage-strategy-neutral so a later slice can add direct object upload without rewriting meeting/session lifecycle.
- Q: Should `012` start Temporal or other processing workflows after finalization? -> A: No. `012` records `ingested_pending_processing` and processing placeholders only. Workflow start and MediaScribe processing are owned by `015-mediascribe-processing-pipeline`.
- Q: Should `012` require database-level row security for tenant isolation? -> A: Application-level tenant checks are mandatory in `012`; PostgreSQL Row-Level Security is recorded as a security hardening gate and must be explicitly included or deferred in planning.
- Q: Should `012` define ingest size and duration limits? -> A: `012` must enforce explicit configurable upload size and duration limits and return truthful rejected or degraded states when a recording exceeds policy.
- Q: Which successful upload status should be canonical in API contracts? -> A: API contracts use upload-session `finalized` and meeting `ingested_pending_processing`; `uploaded` is only a desktop/UI label for users.

### Product Scope Boundary

This feature creates the server-side receiving dock for recordings. It proves
that the backend can authenticate a desktop-like client, accept a finalized
local recording package, resume interrupted upload, store metadata and audio
safely, and return clear status for future UI.

This feature does not build the real macOS upload queue. A later desktop slice
will make the Mac app pick up local recordings, send them to this server, show
pending/uploading/retrying/uploaded labels, and let the user recover failed
uploads.

### Downstream Slice Guardrail

The next product slices are reserved so `012` does not drift into the rest of
the end-to-end product:

- **013-federated-auth-foundation**: users sign in through provider-neutral
  federated auth, with priority providers for the Russian market such as
  Yandex ID, VK ID, and Telegram Login, plus later Sber ID and T-ID where
  partner setup allows. This slice creates internal users, workspace membership,
  sessions, and registered device identity.
- **014-desktop-upload-queue**: the macOS app consumes the `012` ingest
  contracts and `013` user/device identity, sends local recordings to the
  server, shows upload status, retries failures, and preserves local artifacts
  until upload truth is known.
- **015-mediascribe-processing-pipeline**: the server consumes finalized
  ingested artifacts, submits dual-track audio to MediaScribe from the server
  side only, polls job state, imports transcript/diarization/summary results,
  and records processing dependency state.
- **016-meeting-dashboard-review**: the web dashboard shows uploaded meetings,
  processing state, transcript, notes, playback/review surfaces, and user/admin
  meeting review flows.
- **017-access-sharing-downloads**: role-based meeting access, team visibility,
  download/export permissions, login-required share links, optional public-link
  policy, and share-page lifecycle/audit for viral distribution.
- **018-retention-deletion-execution**: server-side retention jobs, deletion
  workflows, deletion verification reports, local desktop purge coordination,
  backup expiry accounting, and external dependency deletion truth.

These slices must not be implemented inside `012`. `012` may only prepare
stable state, contracts, and lifecycle metadata that those slices can consume.
For authentication, `012` assumes an already-authenticated user, workspace
membership, and registered device identity. It must remain provider-neutral and
must not implement Yandex ID, VK ID, Telegram Login, Sber ID, T-ID, or other
login provider flows.

For ownership and access, `012` must store enough metadata to know which user,
device, workspace, and organization a recording belongs to. It must not
implement team-wide browsing, privileged admin review, transcript/audio
downloads, public share links, or share-page UI. Those behaviors are reserved
for later dashboard/access slices.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Upload A Finalized Local Recording (Priority: P1)

As a desktop user who manually recorded a meeting, I want 2brain Rec to upload
the finalized local dual-track artifact to my owner-controlled server, so that
the recording is no longer trapped on one Mac and can later be processed into
transcripts and notes.

**Why this priority**: This is the first end-to-end bridge from accepted local
artifacts to the self-hosted product. Without it, the product cannot reach
transcription, dashboard review, retention, deletion, or team workflows.

**Independent Test**: Start from a valid local package contract containing
`manifest.json`, `mic.wav`, and `incoming.wav`; exercise the server ingest API
as an authenticated registered desktop device; create a meeting and upload
session; upload both tracks; finalize the session; and verify that the server
records a complete, non-processed meeting ingest state with durable object
references and safe metadata.

**Acceptance Scenarios**:

1. **Given** a user has a finalized local recording package that is
   transcription-ready, **When** a contract-valid desktop-like client uploads
   the package through an authenticated upload session, **Then** the server
   stores both required tracks and marks the meeting as
   `ingested_pending_processing`.
2. **Given** the local package manifest maps `local_mic` to `mic_file` and
   `remote_speaker` to `incoming_file`, **When** the server validates the
   package, **Then** the stored meeting preserves those roles without guessing
   from file names alone.
3. **Given** the upload finalizes successfully, **When** a future desktop client
   asks for session status, **Then** it receives a user-meaningful status
   suitable for local upload queue UI.

---

### User Story 2 - Resume Interrupted Uploads Safely (Priority: P1)

As a desktop user on an unreliable network, I need the server upload protocol to
support resume after network, app, or server interruption, so that a long
meeting is not lost or duplicated when the future desktop uploader retries.

**Why this priority**: Meeting audio can be large and sensitive. The first
server foundation must prove durability and idempotency before MediaScribe or
dashboard workflows depend on it.

**Independent Test**: Interrupt a dual-track upload after at least one accepted
chunk or part, resume with the same local recording identity, request the
missing ranges, reupload only what is missing, and finalize exactly one meeting
ingest record.

**Acceptance Scenarios**:

1. **Given** an upload is interrupted after some bytes are accepted, **When** a
   contract-valid client resumes the same upload session, **Then** the server
   reports missing ranges or parts without requiring the already accepted data
   again.
2. **Given** the desktop retries a previously accepted part with the same
   checksum, **When** the server receives it again, **Then** the server treats it
   as idempotent and does not duplicate objects, chunks, audit events, or
   processing work.
3. **Given** the desktop retries a previously accepted part with different
   bytes, **When** checksums do not match, **Then** the server rejects the retry
   and keeps the session in a recoverable error state.

---

### User Story 3 - Keep MediaScribe And Egress Server-Side (Priority: P1)

As a security owner, I want the desktop app to upload only to the 2brain Rec
server and never call MediaScribe or hold MediaScribe credentials, so that audio
egress remains explicit, auditable, and owner-controlled.

**Why this priority**: The constitution requires desktop clients to avoid direct
MediaScribe access and secret exposure. This boundary must be true before any
transcription worker exists.

**Independent Test**: Inspect desktop configuration, upload requests,
diagnostics, server configuration, and server health output during an ingest
run; verify that MediaScribe credentials are available only to server-side
workers or secret configuration and are never sent to the desktop, logs, upload
tokens, diagnostics, or browser bundles.

**Acceptance Scenarios**:

1. **Given** a registered desktop-like client is authenticated, **When** it
   requests upload authorization, **Then** it receives only server-scoped upload
   authorization and no MediaScribe credential, signed MediaScribe URL, or
   external STT endpoint.
2. **Given** the server has accepted an upload, **When** the first ingest
   foundation finalizes the session, **Then** it does not submit audio to
   MediaScribe unless a later processing feature explicitly enables that flow.
3. **Given** diagnostics or health checks are exported, **When** they include
   ingest, storage, or configuration state, **Then** they exclude raw audio,
   transcript text, credentials, tokens, signed URLs, passwords, and live secret
   paths.

---

### User Story 4 - Represent Degraded Or Failed Ingest Truthfully (Priority: P2)

As a user or support operator, I want the system to distinguish complete,
degraded, blocked, failed, and recoverable uploads, so that I know whether a
recording is safe, needs retry, or cannot be processed later.

**Why this priority**: The backend foundation becomes the source of truth for
later processing. False "uploaded" status would break transcript expectations
and deletion accounting.

**Independent Test**: Upload packages with missing tracks, invalid manifest
roles, unsupported readiness, checksum mismatch, insufficient authorization,
storage outage, and finalization before all required data is present; verify
each result has a precise state and recovery path.

**Acceptance Scenarios**:

1. **Given** a package is missing `mic.wav` or `incoming.wav`, **When** the
   upload is finalized, **Then** the server blocks completion or marks the
   meeting degraded with a concrete unavailable reason.
2. **Given** object storage is unavailable, **When** a contract-valid client
   attempts upload or finalization, **Then** the server reports a retryable
   storage failure without losing accepted metadata or claiming completion.
3. **Given** a session is aborted or expires, **When** the desktop queries it
   later, **Then** the server returns a truthful terminal or recoverable state
   and does not expose stale upload authorization.

---

### User Story 5 - Prepare For Dashboard And Processing Without Shipping Them (Priority: P3)

As a product owner, I want the ingest foundation to expose enough meeting and
upload state for future desktop queue UI, MediaScribe processing, and dashboard
work, while keeping those features out of this slice, so that the next slices
can build on a stable lifecycle instead of reworking ingest.

**Why this priority**: This feature must create the foundation, not swallow the
whole product. Clear boundaries prevent accidental dashboard, deletion, or
auto-record scope creep.

**Independent Test**: Inspect the accepted meeting, upload session, object
references, audit events, and state transitions after successful and failed
ingest; verify future processing/dashboard fields are present only as safe
references and statuses, not as implemented transcript, notes, deletion, or
assisted-record behavior.

**Acceptance Scenarios**:

1. **Given** a meeting is ingested, **When** a future processing worker reads
   the meeting state, **Then** it can identify the two track artifacts, checksums,
   readiness, source mode, and lifecycle state without reading desktop-only
   paths.
2. **Given** a user opens a future upload queue UI, **When** it consumes the
   status contract from this feature, **Then** it can show pending, uploading,
   retrying, uploaded, degraded, failed, and aborted labels without needing
   transcript or notes data, while mapping the successful API states from
   upload-session `finalized` and meeting `ingested_pending_processing`.
3. **Given** this feature is complete, **When** reviewers inspect behavior,
   **Then** they see no transcript generation, dashboard meeting detail page,
   server deletion execution, or assisted auto-recording implementation.

---

### User Story 6 - Preserve Ownership And Future Access Control (Priority: P2)

As a future team or workspace admin, I need every ingested recording to carry
clear ownership and access metadata, so that later team visibility, privileged
review, downloads, sharing, and deletion rules can be applied without guessing
who the recording belongs to.

**Why this priority**: Corporate/team versions need different privileges: a
regular user may see only their meetings, while a manager or admin may be
allowed to see team recordings. If ingest stores audio without ownership and
workspace boundaries, later RBAC and sharing features become risky migrations.

**Independent Test**: Ingest recordings for different users, devices, and
workspaces; verify each meeting and artifact records organization, workspace,
owner user, uploader device, source local recording identity, default visibility
policy, and audit identity without exposing another workspace's data.

**Acceptance Scenarios**:

1. **Given** a recording is ingested for a user in a workspace, **When** the
   server creates the meeting record, **Then** the record is bound to exactly
   one organization, workspace, owner user, and uploader device.
2. **Given** two workspaces upload recordings with similar local recording
   identifiers, **When** ingest stores metadata and objects, **Then** the
   records remain isolated by organization/workspace and cannot collide.
3. **Given** a future dashboard or export feature evaluates access, **When** it
   reads the ingest record, **Then** it can distinguish owner-only visibility,
   workspace/team visibility eligibility, privileged admin eligibility, and
   share/download policy placeholders without implementing those actions in
   `012`.
4. **Given** a share link or download is requested, **When** this feature is the
   only implemented slice, **Then** the system reports that sharing/download is
   not available yet and does not expose audio, transcript, summary, or public
   page URLs.

### Edge Cases

- Future desktop uploader is offline when a local recording finishes.
- A contract-valid client loses network mid-track, mid-manifest upload, or
  during finalization.
- Server restarts during an active upload session.
- A future desktop uploader retries the same local package after app restart.
- User accidentally starts two upload sessions for the same local recording
  identity.
- Two users upload recordings with the same generated title or local recording
  identity in different workspaces.
- A user belongs to multiple workspaces and uploads from the same device.
- A device is revoked after creating an upload session but before finalization.
- A future admin/team viewer needs access metadata for a meeting ingested before
  dashboard RBAC is implemented.
- Local package is legacy from feature `008` and is not dual-track
  transcription-ready.
- Local package is marked `degraded` or `failed`.
- Local package duration or byte size exceeds the configured ingest policy.
- One required track is empty, truncated, corrupt, or has a checksum mismatch.
- Manifest and uploaded object metadata disagree on duration, checksum, role,
  format, or readiness.
- Upload token is expired, replayed, or used by the wrong device, user,
  workspace, or meeting.
- Object storage is unavailable, out of space, or returns partial write failure.
- Metadata storage is unavailable after an object write succeeds.
- Finalization is requested before required tracks are present.
- Aborted or expired sessions leave temporary objects behind.
- Diagnostic export is requested after failed, blocked, or partially completed
  ingest.
- Server policy is unavailable or stale when desktop tries to upload a local
  artifact.
- The server is reachable but MediaScribe is unavailable or unconfigured.
- A user requests a transcript, summary, audio download, or share page before
  the later processing/dashboard/sharing slices exist.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST accept uploads only from authenticated users and
  registered desktop-device identities, even when validation uses a
  contract-test client instead of the production macOS uploader.
- **FR-002**: The system MUST allow a desktop client to create or reference a
  meeting record for a finalized local recording artifact.
- **FR-003**: The system MUST create upload sessions bound to organization,
  workspace, user, device, meeting, local recording identity, recording mode,
  policy snapshot, and expiration.
- **FR-004**: The system MUST issue only short-lived, scoped upload
  authorization for the active upload session.
- **FR-005**: Upload authorization MUST NOT contain MediaScribe credentials,
  external STT endpoints, raw storage credentials, or broad server credentials.
- **FR-006**: The system MUST accept a local artifact manifest and validate that
  it is metadata-only and matches the accepted local artifact contract.
- **FR-007**: The system MUST require `mic.wav` mapped to `mic_file` and
  `incoming.wav` mapped to `incoming_file` for a complete dual-track ingest
  unless an explicit degraded unavailable reason is accepted.
- **FR-008**: The system MUST preserve local microphone and incoming speaker
  roles as explicit metadata independent of file-name guessing.
- **FR-009**: The system MUST store uploaded audio bytes in owner-controlled
  object storage and meeting/upload metadata in owner-controlled server
  metadata storage.
- **FR-010**: The system MUST make accepted upload writes durable before
  acknowledging them to the desktop client.
- **FR-011**: The system MUST validate byte size, checksum, track role,
  format/readiness metadata, session identity, device identity, and authorization
  scope before accepting uploaded data.
- **FR-012**: The system MUST support resumable upload by reporting accepted and
  missing ranges or parts for each required artifact.
- **FR-013**: The system MUST make duplicate retries idempotent when session,
  track, sequence/range, byte size, and checksum match a previously accepted
  upload.
- **FR-014**: The system MUST reject conflicting duplicate retries when bytes or
  checksums differ from already accepted data.
- **FR-015**: The system MUST expose canonical API lifecycle states for desktop
  clients, including upload-session `pending`, `uploading`, `retrying`,
  `finalizing`, `finalized`, `degraded`, `failed`, `aborted`, and `expired`,
  plus meeting `ingested_pending_processing`; desktop/UI copy MAY map the
  successful post-finalization state to an `uploaded` or "загружено" label.
- **FR-016**: The system MUST block or degrade finalization when required tracks
  are missing, corrupt, mis-role-mapped, unsupported, or not transcription-ready.
- **FR-017**: Finalization MUST create a stable server-side ingest record that
  references object keys, checksums, track roles, manifest metadata, readiness
  state, and audit identity.
- **FR-018**: The first ingest foundation MUST NOT submit audio to MediaScribe,
  create transcripts, generate notes, publish a dashboard meeting detail page,
  start Temporal or other processing workflows, execute retention/deletion
  workflows, or implement assisted auto-recording.
- **FR-019**: The system MUST keep MediaScribe credentials server-side and out
  of desktop configuration, upload tokens, diagnostics, logs, browser bundles,
  API responses, and committed files.
- **FR-020**: The system MUST record metadata-only audit events for meeting
  creation, upload session creation, accepted upload data, retry, conflict,
  finalization, abort, expiry, degraded finalization, and failed ingest.
- **FR-021**: Audit and diagnostic data MUST NOT include raw audio, transcript
  text, meeting content, credentials, tokens, signed URLs, passwords, or live
  credential paths.
- **FR-022**: The system MUST expose health and readiness information for ingest
  dependencies without revealing secrets or meeting content.
- **FR-023**: The system MUST distinguish temporary upload objects from finalized
  meeting artifacts and record cleanup responsibility for aborted, expired, or
  failed sessions.
- **FR-024**: The system MUST preserve enough lifecycle metadata for future
  retention and deletion reports to distinguish server metadata, object storage,
  temporary objects, local desktop buffers, MediaScribe dependency state, and
  workflow state.
- **FR-025**: The desktop MUST retain local stop/recording truth; server ingest
  status MUST NOT change historical local capture state or claim that a local
  recording was captured differently.
- **FR-026**: If the server or storage is unavailable, the system MUST report a
  retryable blocked state rather than claiming upload success; preserving the
  local artifact on the Mac is the responsibility of the later desktop uploader
  slice.
- **FR-027**: The system MUST ensure that one local recording identity maps to
  at most one active non-terminal upload session per workspace unless the older
  session is aborted or expired.
- **FR-028**: The system MUST expose enough status contract detail for a later
  local upload queue UI without requiring server-rendered capture-critical UI.
- **FR-029**: This feature MUST define and validate desktop-facing ingest
  contracts but MUST NOT implement the production desktop uploader, local upload
  queue UI, or automatic desktop retry loop.
- **FR-030**: This feature MUST treat user identity, workspace membership, and
  registered device identity as provider-neutral prerequisites supplied by auth
  foundation contracts.
- **FR-031**: This feature MUST NOT implement Yandex ID, VK ID, Telegram Login,
  Sber ID, T-ID, email/password, OIDC, or other login provider flows.
- **FR-032**: Every meeting, upload session, track artifact, manifest snapshot,
  temporary upload object, and ingest audit event MUST be scoped to
  organization, workspace, owner user, and uploader device where applicable.
- **FR-033**: The system MUST record a default meeting visibility/access basis
  for future authorization decisions, including owner-only visibility and
  placeholders for workspace/team visibility, privileged admin access,
  download/export permission, and share-link policy.
- **FR-034**: The system MUST NOT expose transcript download, summary download,
  audio download, public share link, login-required share page, team-wide
  meeting browsing, or privileged admin review behavior in this feature.
- **FR-035**: The system MUST prevent local recording identity, meeting title,
  object key, upload session, or retry operations from crossing organization or
  workspace boundaries.
- **FR-036**: The system MUST record metadata needed for later share/download
  audit, including owner, workspace, artifact identity, and future capability
  state, without creating share links or downloadable exports.
- **FR-037**: The first ingest foundation MUST use `server_mediated` upload:
  clients send artifact data to the backend ingest API, and the backend
  validates and writes accepted bytes to owner-controlled object storage.
- **FR-038**: This feature MUST NOT issue direct object-storage upload URLs,
  signed MinIO URLs, broad object-storage credentials, or desktop-visible
  storage credentials.
- **FR-039**: Upload session contracts MUST include an upload strategy field so
  future slices can add `direct_object_upload` without changing meeting identity,
  track role, checksum, missing-range, finalization, audit, or deletion
  semantics.
- **FR-040**: Finalized successful ingest MUST set the meeting processing
  dependency state to `not_submitted` and processing lifecycle state to
  `pending_processing` or equivalent placeholder without creating a workflow run.
- **FR-041**: This feature MUST record workflow/deferred-processing placeholders
  needed by later processing slices, but those placeholders MUST be inert and
  must not enqueue, schedule, or execute MediaScribe, notes, retention, deletion,
  or indexing work.
- **FR-042**: Every create, read, upload-part, missing-range, finalize, abort,
  retry, and status operation MUST verify organization, workspace, user,
  membership, device, and upload-session authorization at the application API
  boundary before reading or mutating meeting data.
- **FR-043**: The server MUST derive or validate organization/workspace scope
  from authenticated membership, registered device identity, and server-minted
  upload session state; it MUST NOT trust client-supplied organization,
  workspace, owner, or device identifiers alone.
- **FR-044**: Persisted meeting, upload, artifact, manifest, temporary object,
  and audit records MUST include tenant-owned identifiers needed to enforce
  authorization and to construct tenant-scoped object keys or object metadata.
- **FR-045**: The implementation plan MUST explicitly decide whether
  PostgreSQL Row-Level Security is included in `012` or deferred as hardening,
  and if deferred, the plan MUST describe the application-level checks and
  create a traceable `RLS-hardening` follow-up task or GitHub issue candidate
  that prevents it from becoming invisible security debt.
- **FR-046**: The system MUST enforce configurable ingest limits for recording
  duration, per-track byte size, total package byte size, and upload/session
  lifetime before accepting finalization.
- **FR-047**: When a recording exceeds configured ingest limits, the system MUST
  reject or mark the ingest as degraded with a concrete policy reason; it MUST
  NOT silently truncate audio, show a desktop/UI `uploaded` label, or allow the
  meeting to reach `ingested_pending_processing`.

### Key Entities *(include if feature involves data)*

- **Registered Device**: A desktop installation authorized to upload recordings
  for a user/workspace. Includes device identity, version metadata, token state,
  revocation state, and heartbeat or last-seen metadata.
- **Organization**: Top-level tenant boundary for future corporate deployment.
  It groups workspaces, users, policies, audit records, and storage ownership.
- **Workspace**: Product collaboration boundary inside an organization. It owns
  meeting records, policy snapshots, default visibility, and future team/admin
  access rules.
- **Workspace Membership**: Relationship between user and workspace. It carries
  future role/permission information but is supplied by the auth/access
  foundation rather than implemented by this ingest slice.
- **Meeting Record**: Server-side record representing one captured meeting
  lifecycle. Includes organization/workspace, owner/user, source local recording
  identity, uploader device, display title when available, ingest state,
  processing state placeholder, visibility/access basis, share/download
  capability placeholders, deletion state placeholder, and audit identity.
- **Local Recording Identity**: Stable client-side identity for a saved local
  artifact package. It is used for deduplication and upload resumption but does
  not expose local filesystem paths.
- **Upload Session**: Server-minted lifecycle for uploading one local recording
  package. Includes session identity, meeting identity, device binding,
  expiration, upload status, accepted parts/ranges, missing ranges, and abort or
  failure reason.
- **Upload Authorization**: Short-lived scoped authorization that permits only
  the intended device/session/track/range upload operations.
- **Upload Strategy**: Contract field describing how artifact bytes are uploaded.
  For `012`, the only executable strategy is `server_mediated`; future slices
  may add `direct_object_upload` after separate security and lifecycle review.
- **Track Artifact**: Server-side representation of a required audio track such
  as local microphone or incoming speaker audio. Includes role, MediaScribe
  field mapping, object key, checksum, byte size, duration, format, readiness,
  and degraded reason when applicable.
- **Manifest Snapshot**: Metadata-only copy of the local artifact manifest
  accepted by the server for validation, audit, future processing, and deletion
  accounting.
- **Ingest State**: Canonical meeting/upload lifecycle state such as pending,
  uploading, retrying, finalizing, finalized, ingested pending processing,
  degraded, failed, aborted, or expired. `Uploaded` is a desktop/UI label, not a
  canonical API state.
- **Processing Placeholder**: Inert metadata describing that a finalized ingest
  is ready for future processing. In `012`, it can record `not_submitted` and
  `pending_processing` but must not create or reference a live workflow run.
- **Ingest Audit Event**: Metadata-only record of security, upload, retry,
  finalization, and failure activity.
- **Temporary Upload Object**: Object storage data accepted before finalization.
  It must be distinguishable from finalized artifacts and accountable for
  cleanup.
- **Access Policy Snapshot**: Metadata-only snapshot of the workspace/user
  access basis at ingest time. It is used later by dashboard, sharing, download,
  audit, and deletion features.
- **Share/Download Capability Placeholder**: Non-executable metadata describing
  whether future sharing or download behavior is not available, policy-blocked,
  owner-only, workspace-visible, or admin-controlled. It does not create a link
  or downloadable file in `012`.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A valid finalized local dual-track artifact can be uploaded and
  finalized into a server meeting ingest record in 100% of happy-path validation
  runs.
- **SC-002**: Finalized happy-path ingests preserve both required roles
  (`mic_file`, `incoming_file`) and checksums in 100% of validation runs.
- **SC-003**: Upload interruption and resume validation reuploads only missing
  ranges or parts and finalizes exactly one meeting ingest record in 100% of
  tested interruption points.
- **SC-004**: Duplicate retries with matching checksums are idempotent in 100%
  of tested retry cases.
- **SC-005**: Conflicting retries with mismatched checksums are rejected in 100%
  of tested conflict cases.
- **SC-006**: Missing, corrupt, legacy, or non-ready local packages never reach
  upload-session `finalized`, meeting `ingested_pending_processing`, or
  desktop/UI `uploaded` label without a truthful degraded or blocked reason.
- **SC-007**: Desktop-visible session status reflects pending, uploading,
  retrying, uploaded, degraded, failed, aborted, and expired user-facing
  outcomes in the upload-state validation matrix, with the uploaded label mapped
  from canonical upload-session `finalized` and meeting
  `ingested_pending_processing` API states.
- **SC-008**: Secret and content scans across server configuration, API
  responses, logs, diagnostics, and desktop-facing outputs find no MediaScribe
  credentials, raw audio, transcript text, meeting content, signed URLs,
  passwords, upload tokens, or live credential paths.
- **SC-009**: With MediaScribe unavailable or unconfigured, ingest finalization
  still succeeds for valid artifacts and records `not_submitted` processing
  dependency state.
- **SC-010**: With server or object storage unavailable, the desktop receives a
  retryable blocked status and local artifacts remain available for later
  upload in 100% of outage validation cases.
- **SC-011**: Aborted, expired, and failed sessions produce cleanup-accounting
  records for temporary upload objects in 100% of lifecycle validation cases.
- **SC-012**: No transcript, notes, dashboard meeting detail, server deletion
  execution, or assisted auto-recording behavior is observable after completing
  this feature.
- **SC-013**: In multi-user and multi-workspace ingest validation, 100% of
  meeting records and artifacts are scoped to the correct organization,
  workspace, owner user, and uploader device.
- **SC-014**: Cross-workspace local recording identity collisions do not merge,
  overwrite, or expose another workspace's meeting in 100% of collision tests.
- **SC-015**: Transcript download, summary download, audio download,
  share-page, public-link, team-wide browsing, and privileged admin review
  attempts are blocked or reported as not implemented in 100% of `012`
  validation cases.
- **SC-016**: In 100% of upload validation runs, desktop-facing authorization
  permits only backend ingest API upload and exposes no direct object-storage
  credentials or signed object-storage upload URLs.
- **SC-017**: Upload session responses include `uploadStrategy=server_mediated`
  and preserve strategy-neutral session, track, checksum, missing-range,
  finalization, audit, and deletion metadata in 100% of contract validation
  cases.
- **SC-018**: Successful finalization records `not_submitted` processing
  dependency state and pending processing placeholder in 100% of validation
  cases without creating any Temporal/workflow run, MediaScribe job, notes job,
  retention job, deletion job, or indexing job.
- **SC-019**: Cross-user, cross-device, cross-workspace, and cross-organization
  attempts to create, query, resume, finalize, abort, or inspect another
  tenant's upload or meeting are rejected in 100% of authorization validation
  cases.
- **SC-020**: In 100% of validation cases, changing client-supplied
  organization/workspace/user/device identifiers cannot move an upload session,
  artifact, object key, or meeting record outside the authenticated server-side
  scope.
- **SC-021**: Planning artifacts explicitly state whether PostgreSQL RLS is
  implemented or deferred, list the compensating application-level authorization
  checks when deferred, and include a traceable hardening follow-up task or
  GitHub issue candidate.
- **SC-022**: Ingest validation covers recordings within and beyond configured
  duration and byte-size limits, including at least the existing 30/60-minute
  acceptance targets, and reports truthful accepted, rejected, or degraded
  outcomes in 100% of limit-boundary cases.

## Assumptions

- Feature `010-recording-artifact-format` is the accepted local artifact
  baseline for upload input.
- The first server ingest foundation targets internal MVP and self-hosted
  deployment under `https://rec.2brain.pro`, with local development support.
- Authentication and registered device identity are prerequisites for safe
  desktop ingest, but provider login and account linking are owned by the
  separate `013-federated-auth-foundation` slice.
- Enterprise SSO, SCIM, and fleet management are out of scope.
- Full role administration, team-wide meeting browsing, privileged admin review,
  share links, public pages, and downloads/exports are out of scope for `012`;
  this feature only preserves the ownership/access metadata they will need.
- Object storage and metadata storage are owner-controlled infrastructure.
- `012` optimizes for safety and debuggability over maximum upload throughput.
  Direct-to-object-storage upload is a future optimization, not part of this
  foundation slice.
- Concrete ingest duration and byte-size limits are configured during planning
  and deployment, but the feature must support policy enforcement and
  validation from the start.
- MediaScribe remains a future server-side processing dependency, but this
  feature stops before job submission.
- Temporal and other durable workflow starts are reserved for later processing,
  retention, and deletion slices. `012` may define placeholders but must not
  enqueue processing work.
- The web dashboard may later display ingested meetings, but this feature does
  not ship full dashboard meeting detail, transcript, notes, search, sharing, or
  deletion UI.
- The desktop local trust shell remains authoritative for active capture
  indicator and one-action stop. Server ingest status is a post-capture upload
  lifecycle, not capture truth.
- Server retention and deletion execution are future slices, but this feature
  must record lifecycle metadata so deletion truth can be implemented later.
- Assisted detect-and-ask and auto-recording remain part of feature `011` and
  later implementation slices.
- Production desktop uploader implementation and local upload queue UI are
  later slices that consume the contracts from this feature.
