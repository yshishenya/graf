# Feature Specification: Server Ingest Foundation

**Feature Branch**: `012-server-ingest-foundation`

**Created**: 2026-06-04

**Status**: Draft

**Input**: User description: "Build the first self-hosted 2brain Rec backend foundation that accepts finalized local dual-track recording artifacts from the desktop app through authenticated resumable ingest, stores metadata in Postgres and audio in MinIO, keeps MediaScribe credentials server-side, exposes upload/session state to desktop, and prepares but does not yet ship full dashboard notes deletion or assisted auto-recording."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Upload A Finalized Local Recording (Priority: P1)

As a desktop user who manually recorded a meeting, I want 2brain Rec to upload
the finalized local dual-track artifact to my owner-controlled server, so that
the recording is no longer trapped on one Mac and can later be processed into
transcripts and notes.

**Why this priority**: This is the first end-to-end bridge from accepted local
artifacts to the self-hosted product. Without it, the product cannot reach
transcription, dashboard review, retention, deletion, or team workflows.

**Independent Test**: Start from a valid local package containing
`manifest.json`, `mic.wav`, and `incoming.wav`; authenticate the desktop device;
create a meeting and upload session; upload both tracks; finalize the session;
and verify that the server records a complete, non-processed meeting ingest
state with durable object references and safe metadata.

**Acceptance Scenarios**:

1. **Given** a user has a finalized local recording package that is
   transcription-ready, **When** the desktop app uploads the package through an
   authenticated upload session, **Then** the server stores both required tracks
   and marks the meeting as `ingested_pending_processing`.
2. **Given** the local package manifest maps `local_mic` to `mic_file` and
   `remote_speaker` to `incoming_file`, **When** the server validates the
   package, **Then** the stored meeting preserves those roles without guessing
   from file names alone.
3. **Given** the upload finalizes successfully, **When** the desktop app asks
   for session status, **Then** it receives a user-meaningful status suitable
   for local upload queue UI.

---

### User Story 2 - Resume Interrupted Uploads Safely (Priority: P1)

As a desktop user on an unreliable network, I want uploads to resume after
network, app, or server interruption, so that a long meeting is not lost or
duplicated because one request failed.

**Why this priority**: Meeting audio can be large and sensitive. The first
server foundation must prove durability and idempotency before MediaScribe or
dashboard workflows depend on it.

**Independent Test**: Interrupt a dual-track upload after at least one accepted
chunk or part, restart the desktop uploader with the same local package, request
the missing ranges, reupload only what is missing, and finalize exactly one
meeting ingest record.

**Acceptance Scenarios**:

1. **Given** an upload is interrupted after some bytes are accepted, **When** the
   desktop resumes the same upload session, **Then** the server reports missing
   ranges or parts without requiring the already accepted data again.
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

1. **Given** a desktop client is authenticated, **When** it requests upload
   authorization, **Then** it receives only server-scoped upload authorization
   and no MediaScribe credential, signed MediaScribe URL, or external STT
   endpoint.
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
2. **Given** object storage is unavailable, **When** the desktop attempts upload
   or finalization, **Then** the server reports a retryable storage failure
   without losing accepted metadata or claiming completion.
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
   retrying, uploaded, degraded, failed, and aborted states without needing
   transcript or notes data.
3. **Given** this feature is complete, **When** reviewers inspect behavior,
   **Then** they see no transcript generation, dashboard meeting detail page,
   server deletion execution, or assisted auto-recording implementation.

### Edge Cases

- Desktop is offline when a local recording finishes.
- Desktop loses network mid-track, mid-manifest upload, or during finalization.
- Server restarts during an active upload session.
- User retries the same local package after app restart.
- User accidentally starts two upload sessions for the same local recording
  identity.
- Local package is legacy from feature `008` and is not dual-track
  transcription-ready.
- Local package is marked `degraded` or `failed`.
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

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST accept uploads only from authenticated users and
  registered desktop devices.
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
- **FR-015**: The system MUST expose session status to desktop clients using
  user-meaningful states: `pending`, `uploading`, `retrying`, `uploaded`,
  `degraded`, `failed`, `aborted`, and `expired`.
- **FR-016**: The system MUST block or degrade finalization when required tracks
  are missing, corrupt, mis-role-mapped, unsupported, or not transcription-ready.
- **FR-017**: Finalization MUST create a stable server-side ingest record that
  references object keys, checksums, track roles, manifest metadata, readiness
  state, and audit identity.
- **FR-018**: The first ingest foundation MUST NOT submit audio to MediaScribe,
  create transcripts, generate notes, publish a dashboard meeting detail page,
  execute retention/deletion workflows, or implement assisted auto-recording.
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
- **FR-026**: If the server or storage is unavailable, the system MUST leave the
  local artifact uploadable later and report a retryable blocked state rather
  than claiming upload success.
- **FR-027**: The system MUST ensure that one local recording identity maps to
  at most one active non-terminal upload session per workspace unless the older
  session is aborted or expired.
- **FR-028**: The system MUST expose enough status contract detail for a later
  local upload queue UI without requiring server-rendered capture-critical UI.

### Key Entities *(include if feature involves data)*

- **Registered Device**: A desktop installation authorized to upload recordings
  for a user/workspace. Includes device identity, version metadata, token state,
  revocation state, and heartbeat or last-seen metadata.
- **Meeting Record**: Server-side record representing one captured meeting
  lifecycle. Includes organization/workspace, owner/user, source local recording
  identity, display title when available, ingest state, processing state
  placeholder, deletion state placeholder, and audit identity.
- **Local Recording Identity**: Stable client-side identity for a saved local
  artifact package. It is used for deduplication and upload resumption but does
  not expose local filesystem paths.
- **Upload Session**: Server-minted lifecycle for uploading one local recording
  package. Includes session identity, meeting identity, device binding,
  expiration, upload status, accepted parts/ranges, missing ranges, and abort or
  failure reason.
- **Upload Authorization**: Short-lived scoped authorization that permits only
  the intended device/session/track/range upload operations.
- **Track Artifact**: Server-side representation of a required audio track such
  as local microphone or incoming speaker audio. Includes role, MediaScribe
  field mapping, object key, checksum, byte size, duration, format, readiness,
  and degraded reason when applicable.
- **Manifest Snapshot**: Metadata-only copy of the local artifact manifest
  accepted by the server for validation, audit, future processing, and deletion
  accounting.
- **Ingest State**: Meeting/upload lifecycle state such as pending, uploading,
  retrying, uploaded, ingested pending processing, degraded, failed, aborted, or
  expired.
- **Ingest Audit Event**: Metadata-only record of security, upload, retry,
  finalization, and failure activity.
- **Temporary Upload Object**: Object storage data accepted before finalization.
  It must be distinguishable from finalized artifacts and accountable for
  cleanup.

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
  a `uploaded` or `ingested_pending_processing` state without a truthful
  degraded or blocked reason.
- **SC-007**: Desktop-visible session status reflects pending, uploading,
  retrying, uploaded, degraded, failed, aborted, and expired outcomes in the
  upload-state validation matrix.
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

## Assumptions

- Feature `010-recording-artifact-format` is the accepted local artifact
  baseline for upload input.
- The first server ingest foundation targets internal MVP and self-hosted
  deployment under `https://rec.2brain.dev`, with local development support.
- Authentication and device registration are included only to the extent needed
  for safe desktop ingest. Enterprise SSO, SCIM, and fleet management are out of
  scope.
- Object storage and metadata storage are owner-controlled infrastructure.
- MediaScribe remains a future server-side processing dependency, but this
  feature stops before job submission.
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
