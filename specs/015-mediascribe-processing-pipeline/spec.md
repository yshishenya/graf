# Feature Specification: MediaScribe Processing Pipeline

**Feature Branch**: `015-mediascribe-processing-pipeline`

**Created**: 2026-06-11

**Status**: Draft

**Input**: User description: "Start implementation of feature 015. Follow SDD / Spec Kit carefully, rerun checks after clarifications, fix every issue found, and use Product Design only if design work is needed."

## Clarifications

### Session 2026-06-11

- Q: What does `015` own after `012-server-ingest-foundation` finalizes an upload? -> A: `015` owns server-side durable processing pickup, MediaScribe submit/poll/result import, processing status truth, dependency audit, and lifecycle accounting for future deletion.
- Q: Can desktop clients start workflows or call MediaScribe? -> A: No. Desktop clients never start workflows directly, never call MediaScribe, and never receive MediaScribe credentials or signed dependency URLs.
- Q: Which processing engine is in scope? -> A: Temporal is the selected durable workflow engine for MVP workflows, with deterministic local/test adapters allowed only for validation without a live Temporal cluster.
- Q: Should this slice generate 2brain notes or ship a dashboard? -> A: No. `015` imports transcription and diarization output, records summary dependency state if present or explicitly not requested, and leaves notes/dashboard review to `016-meeting-dashboard-review`.
- Q: Should ingest success depend on MediaScribe availability? -> A: No. `012` ingest remains successful without MediaScribe. `015` reports processing as blocked/degraded when MediaScribe or workflow dependencies are unavailable.

### Clarification Review 2026-06-11

- No additional user decision is required before planning. The remaining
  high-risk choices are already constrained by accepted project artifacts:
  Temporal is required by the constitution, MediaScribe is the MVP STT
  dependency, desktop egress is forbidden, and transcript content may be stored
  only in controlled server result stores rather than logs, diagnostics, status
  responses, or external observability by default.
- Public transcript/audio/summary downloads are not part of `015`. Internal
  server-side result fetch/import is allowed only as part of MediaScribe
  processing and lifecycle accounting.

### Product Scope Boundary

This feature turns finalized server-ingested recordings into processing jobs. It
starts from meetings that already reached `ingested_pending_processing` in
`012-server-ingest-foundation`, submits validated dual-track artifacts to
MediaScribe from the server side only, polls processing state, imports
transcript and diarization results, and records enough lifecycle truth for
future dashboard, sharing, retention, deletion, and audit features.

This feature does not change macOS capture, recording, local buffering,
desktop upload, federated login, dashboard review, share/download behavior,
retention/deletion execution, assisted auto-start, or future virtual-driver
routing. It does not expose transcript or audio download surfaces to end users.

### Downstream Slice Guardrail

- **016-meeting-dashboard-review** owns web meeting list/detail views,
  transcript review, notes display, playback, and user/admin review flows.
- **017-access-sharing-downloads** owns role-based meeting access,
  team visibility, download/export permissions, share links/pages, and audit
  for external sharing.
- **018-retention-deletion-execution** owns deletion workflows, deletion
  verification reports, local desktop purge coordination, backup expiry, and
  external dependency deletion truth.
- **022-meeting-mute-truth** and future capture-route features remain outside
  this processing pipeline.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Start Processing After Finalized Ingest (Priority: P1)

As a meeting owner, I want a successfully uploaded recording to enter
server-side processing automatically, so that I do not have to manually trigger
transcription after the desktop upload is complete.

**Why this priority**: This is the first step after ingest. Without reliable
pickup, MediaScribe transcription cannot become a product workflow.

**Independent Test**: Create a finalized meeting with `ingested_pending_processing`
and valid track artifacts; trigger processing pickup; verify exactly one
durable workflow is created for the internal meeting identity and the meeting
leaves the inert `not_submitted` placeholder state.

**Acceptance Scenarios**:

1. **Given** a valid finalized meeting has microphone and incoming track
   artifacts, **When** processing pickup runs, **Then** the system starts one
   durable processing workflow and records processing as started for that
   meeting.
2. **Given** pickup is retried for the same meeting, **When** the existing
   workflow identity already exists, **Then** the system does not create a
   duplicate workflow or duplicate MediaScribe submission.
3. **Given** a meeting is degraded, failed, aborted, expired, missing required
   tracks, or not transcription-ready, **When** processing pickup runs, **Then**
   processing is blocked with a truthful reason and no MediaScribe request is
   sent.

---

### User Story 2 - Submit Dual-Track Audio To MediaScribe Server-Side (Priority: P1)

As an operator, I want 2brain Rec backend workers to submit the accepted
dual-track artifact to MediaScribe with the correct roles and credentials, so
that transcription happens without exposing secrets or breaking track truth.

**Why this priority**: MediaScribe is the MVP STT dependency, and the desktop
must never own this egress or credential boundary.

**Independent Test**: Use a fake MediaScribe server or client adapter to assert
that the backend submits exactly `mic_file` and `incoming_file` from server-side
storage, uses server-side credentials, requests diarization for incoming
speakers, and persists the returned job identifier before any retry can submit
again.

**Acceptance Scenarios**:

1. **Given** a processing workflow starts for a valid dual-track meeting,
   **When** the backend submits to MediaScribe, **Then** it sends the local
   microphone track as `mic_file` and incoming/system audio as `incoming_file`.
2. **Given** a MediaScribe submission is accepted, **When** MediaScribe returns
   a job id, **Then** the backend persists the job id and request metadata before
   the workflow can continue polling.
3. **Given** MediaScribe credentials are missing, invalid, or not readable,
   **When** submission is attempted, **Then** processing is blocked or failed
   with a safe reason and no secret value is logged, returned, or stored in a
   client-visible field.

---

### User Story 3 - Poll And Import Processing Results (Priority: P1)

As a meeting owner, I want completed transcription and diarization results to be
stored by 2brain Rec, so that a later dashboard can review the meeting without
calling MediaScribe again.

**Why this priority**: Imported results are the durable product artifact that
later dashboard, sharing, export, retention, and deletion slices will consume.

**Independent Test**: Simulate MediaScribe state transitions from accepted job
to ready result; poll until ready; import transcript and diarization segments;
verify source roles, speakers, timestamps, language hints, result version, and
content storage are persisted.

**Acceptance Scenarios**:

1. **Given** MediaScribe reports `uploaded`, `transcribing`, or `diarizing`,
   **When** polling runs, **Then** the backend records current processing state
   without importing incomplete results.
2. **Given** MediaScribe reports `ready`, **When** the result is fetched, **Then**
   transcript and diarization segments are imported with timestamps,
   `source_role`, speaker labels, and result provenance.
3. **Given** a result includes summary output or download references, **When**
   the backend imports the result, **Then** summary/download dependency state is
   recorded for future slices without exposing dashboard notes or public
   download links in `015`.

---

### User Story 4 - Handle Failures, Retries, And Dependency Outages (Priority: P1)

As an operator, I need processing to be retryable, observable, and safe during
worker restarts or MediaScribe outages, so that recordings are not duplicated,
lost, or falsely marked as processed.

**Why this priority**: Transcription is asynchronous and depends on external
infrastructure. Incorrect retry behavior can duplicate sensitive egress or make
meeting state untrustworthy.

**Independent Test**: Drive submission, polling, result import, timeout,
invalid credential, 4xx, 5xx, network, worker-restart, and duplicate-trigger
scenarios; verify terminal vs retryable outcomes, backoff, safe audit metadata,
and no duplicate MediaScribe jobs.

**Acceptance Scenarios**:

1. **Given** MediaScribe returns a transient error or network timeout,
   **When** retry policy allows retry, **Then** the workflow retries with bounded
   backoff and keeps a safe retryable processing state.
2. **Given** MediaScribe returns an unrecoverable error, **When** the workflow
   records the failure, **Then** the meeting is marked failed or blocked for
   processing without changing ingest truth.
3. **Given** the worker restarts after job submission, **When** processing
   resumes, **Then** it polls the persisted job id instead of resubmitting the
   same audio.

---

### User Story 5 - Preserve Privacy, Audit, And Lifecycle Truth (Priority: P1)

As an admin or privacy reviewer, I need processing events, credentials, content,
and deletion dependencies to be represented truthfully, so that the product can
explain where meeting data went and what later deletion must cover.

**Why this priority**: MediaScribe is a content-bearing external dependency.
Security and deletion truth are non-negotiable constitutional gates.

**Independent Test**: Inspect API responses, logs, audit events, diagnostics,
processing records, and lifecycle metadata after successful and failed
processing; verify no secrets or raw content leak outside controlled content
stores, and deletion dependency records include MediaScribe job/result state.

**Acceptance Scenarios**:

1. **Given** processing submits audio to MediaScribe, **When** audit records are
   created, **Then** they include safe identifiers, status transitions, request
   configuration, timestamps, and failure reasons without raw audio, transcript
   text, credentials, tokens, signed URLs, or live secret paths.
2. **Given** transcript text is imported, **When** logs or diagnostics are
   emitted, **Then** transcript content is not included in those logs or
   diagnostics by default.
3. **Given** future deletion work inspects a processed meeting, **When** it
   reads processing lifecycle metadata, **Then** it can tell whether MediaScribe
   received audio, which job/result states exist, and what external dependency
   deletion/accounting remains.

---

### User Story 6 - Expose Processing Status For Future Product Surfaces (Priority: P2)

As a future dashboard or desktop status client, I want stable processing status
truth from the backend, so that users can later see "processing", "failed", or
"ready" without guessing from raw implementation details.

**Why this priority**: This enables `016` without shipping UI in `015`.

**Independent Test**: Query the processing status for pending, submitted,
polling, ready, failed, blocked, and imported meetings; verify the response is
tenant-scoped, stable, content-safe, and does not expose dependency credentials
or raw transcript text.

**Acceptance Scenarios**:

1. **Given** a meeting is being processed, **When** an authorized caller requests
   processing status, **Then** the backend returns canonical processing state,
   safe reason codes, timestamps, and whether result content is available.
2. **Given** an unauthorized or cross-tenant caller requests processing status,
   **When** the request is evaluated, **Then** the backend denies or hides the
   resource without revealing another tenant's meeting existence.
3. **Given** transcript content is ready, **When** status is requested in `015`,
   **Then** only content availability and safe metadata are returned; dashboard
   rendering and downloads remain out of scope.

### Edge Cases

- Finalized meeting has missing, quarantined, deleted, or mis-role-mapped track
  artifacts.
- Processing pickup runs concurrently in two workers for the same meeting.
- Workflow starts but crashes before or after MediaScribe job id persistence.
- MediaScribe accepts the job but polling returns unknown status, malformed
  JSON, missing result fields, failed job, or not-ready result.
- MediaScribe public request limit is lower than a stored artifact size.
- MediaScribe credentials are absent, invalid, expired, unreadable, or
  accidentally configured as development placeholders.
- Postgres is available but MinIO object retrieval fails during submission.
- Result import succeeds for transcript but fails for diarization, or vice
  versa.
- User/workspace/device state changes after ingest but before processing.
- A meeting is marked for future deletion while processing is pending or
  running.
- Logs, diagnostics, problem responses, and test evidence contain strings that
  resemble secrets or transcript content.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST pick up only authorized meetings that reached
  `ingested_pending_processing` with required microphone, incoming/system, and
  manifest artifacts present and transcription-ready.
- **FR-002**: The system MUST start exactly one durable processing workflow per
  meeting using an idempotent workflow identity derived from internal meeting
  metadata, not client-supplied titles or file names.
- **FR-003**: The system MUST preserve ingest truth: MediaScribe or workflow
  failures MUST NOT rewrite a successful ingest into an upload failure.
- **FR-004**: The system MUST keep all MediaScribe calls server-side and MUST
  NOT expose MediaScribe credentials, signed dependency URLs, or server storage
  credentials to desktop clients or future dashboard clients.
- **FR-005**: The system MUST submit exactly the accepted local microphone track
  as `mic_file` and the accepted incoming/system audio track as
  `incoming_file`.
- **FR-006**: The system MUST request diarization for incoming speakers and
  keep local microphone speaker identity distinct from remote speaker labels.
- **FR-007**: The system MUST NOT collapse dual-track audio into a mixed file,
  strip silence with VAD, or otherwise alter track timing in a way that breaks
  transcript timestamp truth.
- **FR-008**: The system MUST persist MediaScribe job id, request parameters,
  source artifact identifiers, and processing state before any retry can submit
  the same meeting again.
- **FR-009**: The system MUST map MediaScribe job states into canonical
  processing states suitable for future product status surfaces.
- **FR-010**: The system MUST poll MediaScribe until a terminal ready or failed
  state, respecting bounded retry, timeout, and backoff rules.
- **FR-011**: The system MUST import transcript segments with start time, end
  time, text, source role, sequence, and provenance.
- **FR-012**: The system MUST import diarization segments with start time, end
  time, speaker label, text, source role, sequence, and provenance.
- **FR-013**: The system MUST record summary dependency state as
  `not_requested`, `available`, `unavailable`, or `failed` without exposing
  generated notes or dashboard surfaces in this slice.
- **FR-014**: The system MUST preserve result version, import timestamp,
  source job id, source artifact checksums, and importer version for replay and
  audit.
- **FR-015**: The system MUST make result import idempotent so rerunning import
  for the same job does not duplicate segments or corrupt meeting state.
- **FR-016**: The system MUST distinguish retryable failures, terminal
  failures, blocked configuration, canceled/deleted-later state, and successful
  processed state.
- **FR-017**: The system MUST expose content-safe processing status metadata to
  authorized server-side or future product callers.
- **FR-018**: Processing status responses MUST NOT include raw transcript text,
  raw audio, MediaScribe credentials, object-storage credentials, signed URLs,
  bearer tokens, passwords, or live secret paths.
- **FR-019**: Audit events MUST record pickup, workflow start, submission,
  polling transitions, result import, retry, blocked, failed, and processed
  transitions using metadata-only payloads by default.
- **FR-020**: Logs, diagnostics, traces, and validation evidence MUST NOT
  contain raw audio, transcript text, meeting content, credentials, tokens,
  signed URLs, passwords, or live secret paths.
- **FR-021**: Langfuse or similar observability MUST remain metadata-only by
  default for this slice; content-bearing traces are out of scope.
- **FR-022**: The system MUST register MediaScribe job/result lifecycle state
  for future deletion and dependency accounting.
- **FR-023**: The system MUST keep MediaScribe readiness separate from ingest
  readiness: missing MediaScribe or workflow dependencies may block processing
  but must not block finalized ingest reads.
- **FR-024**: The system MUST provide operator-visible health or readiness
  truth for processing dependencies without revealing secrets or meeting
  content.
- **FR-025**: The system MUST be replayable from persisted meeting, artifact,
  workflow, MediaScribe job, and result state after worker restart.
- **FR-026**: The system MUST reject or block processing for meetings whose
  ownership, workspace, device, or authorization context no longer permits
  processing.
- **FR-027**: The system MUST keep `016` dashboard, `017` share/download, and
  `018` deletion execution out of `015`, while preserving the metadata those
  slices need.
- **FR-028**: The system MUST include migration-safe schema changes for
  processing jobs, result artifacts, transcript segments, diarization segments,
  lifecycle/deletion dependency state, and audit/status metadata.
- **FR-029**: The system MUST include deterministic contract, unit, and
  integration validation for happy path, duplicate trigger, worker restart,
  MediaScribe failure, result import, tenant denial, and secret/content leak
  boundaries.
- **FR-030**: The system MUST keep desktop behavior unchanged except for future
  status consumers reading server-side processing state; no macOS capture or
  upload behavior changes are accepted in this feature.

### Key Entities *(include if feature involves data)*

- **ProcessingWorkflow**: Durable processing run for one meeting. Includes
  workflow identity, meeting id, workspace id, status, started/ended timestamps,
  retry counters, and failure reason.
- **MediaScribeJob**: Server-side record of a submitted MediaScribe job.
  Includes job id, request settings, source artifacts, status, polling metadata,
  and dependency lifecycle state.
- **ProcessingResult**: Imported result envelope for a MediaScribe job. Includes
  source job id, result version, import timestamp, transcript availability,
  diarization availability, summary dependency state, and provenance.
- **TranscriptSegment**: Ordered transcript item with timestamps, source role,
  text, and provenance.
- **DiarizationSegment**: Ordered speaker-attributed item with timestamps,
  source role, speaker label, text, and provenance.
- **ProcessingAuditEvent**: Metadata-only audit event for processing lifecycle
  transitions.
- **ProcessingDependencyState**: Lifecycle accounting record for MediaScribe,
  workflow payloads, imported content, and future deletion truth.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of valid finalized dual-track meetings in validation start
  exactly one durable processing workflow and no duplicate workflows.
- **SC-002**: 100% of duplicate pickup or worker-restart validation cases reuse
  the existing workflow or MediaScribe job instead of submitting duplicate audio.
- **SC-003**: 100% of valid MediaScribe accepted responses persist job id and
  request metadata before polling begins.
- **SC-004**: 100% of ready MediaScribe result validation cases import
  transcript and diarization segments with timestamps, source roles, speaker
  labels, sequence, and provenance.
- **SC-005**: 100% of retryable, terminal, blocked configuration, and malformed
  result scenarios end in distinct processing states with safe reason codes.
- **SC-006**: Processing dependency outages do not change successful ingest
  status in 100% of validation cases.
- **SC-007**: Secret/content leak scans across processing API responses, logs,
  diagnostics, audit metadata, tests, and evidence find 0 MediaScribe
  credentials, raw audio, transcript text, signed URLs, bearer tokens,
  passwords, or live secret paths outside controlled content stores.
- **SC-008**: Cross-tenant processing status and pickup attempts are denied or
  hidden in 100% of authorization validation cases.
- **SC-009**: Processing readiness truth distinguishes ingest readiness,
  workflow readiness, MediaScribe configuration, MediaScribe reachability, and
  result import health in 100% of readiness validation cases.
- **SC-010**: `015` validation exposes 0 dashboard detail pages, share links,
  transcript/audio downloads, deletion execution endpoints, assisted recording
  behavior, or macOS capture/upload behavior changes.
- **SC-011**: Future deletion accounting can identify whether a meeting has no
  MediaScribe job, a submitted job, imported results, failed dependency state,
  or blocked processing state in 100% of processed/degraded validation cases.

## Assumptions

- `012-server-ingest-foundation` and its persistent Postgres/MinIO ingest
  records are the accepted starting point for this feature.
- `013-federated-auth-foundation` and `014-desktop-upload-queue` may exist in
  parallel, but `015` consumes authenticated tenant/meeting state rather than
  changing login or desktop upload behavior.
- Temporal is the selected durable workflow engine for MVP, but local
  validation may use deterministic fakes or adapters where a live Temporal
  cluster is not available.
- MediaScribe production/public base URL is `https://mediascribe.2brain.pro`.
- The real MediaScribe API key is provided only through server-side secret
  configuration and is never committed.
- MediaScribe currently has no idempotency key for job creation, so 2brain Rec
  must persist the external job id immediately and guard retries from its own
  state.
- The MVP import language scope is Russian and English; automatic language
  detection may be recorded if MediaScribe returns it.
- Generated 2brain notes, semantic search, embeddings, exports, user-facing
  review UI, public sharing, and deletion execution are later feature slices.
