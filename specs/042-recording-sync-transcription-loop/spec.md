# Feature Specification: Recording Sync And Transcription Loop

**Feature Branch**: `042-recording-sync-transcription-loop`

**Created**: 2026-06-17

**Status**: Draft

**Input**: User description: "Доведем до полностью рабочего состояния отправку записей на сервер, транскрибацию и отображение транскрибации в веб и в приложении. Сделай аудит того, что реализовано, как это запланировано. Сделай по полному циклу SDD Spec Kit, начиная с описания задачи. Посмотри как это реализуют в других приложениях и лучшие практики на GitHub. У нас должна быть возможность записывать без сети и отправлять на сервер когда сеть появляется, при этом данные между клиентом и сервером должны быть консистентны. Редактирование и обрезка файлов должны быть на локальном устройстве. Посмотри Krisp, но сделай лучше: у них нет обещанного offline upload."

## Reference And Audit Context

### Current 2brain Rec Baseline

- Local macOS recording is accepted for visible manual Record/Pause/Resume/Stop,
  dual-track packages, metadata-only manifest truth, mute/pause truth, and
  leakage finalization gates.
- Desktop upload queue work already established a durable local queue,
  resumable server-mediated upload, role mapping, retry truth, and no direct
  MediaScribe or object-storage credentials on the desktop.
- Server ingest already accepts meetings, upload sessions, offset/checksum
  parts, missing-range repair, finalization, and `ingested_pending_processing`
  truth.
- Server processing already owns MediaScribe submit/poll/import through durable
  workflows and stores transcript/diarization results in controlled server
  stores.
- Web cabinet and embedded desktop review surfaces already have meeting
  list/detail, processing states, transcript rendering, notes/action truth, and
  governance placeholders.
- The missing product slice is one proven, user-facing, consistency-preserving
  loop across those surfaces, including offline recording, delayed upload,
  server acceptance, processing, and transcript availability in both browser and
  installed desktop app.
- Local media editing, trimming, online transcript editing, replace/reprocess
  flows, and full video review are intentionally post-MVP product-improvement
  work. This feature must still preserve revision-ready meeting/media identity
  so those future slices do not require duplicate meeting entities.

### External Reference Findings

- Krisp exposes a meeting workspace where uploaded audio/video can become a
  transcript and reviewable meeting record, and its dashboard supports
  transcript/notes editing, speaker assignment, transcript export, and actions.
- Krisp documents local/no-cloud behavior for noise cancellation, but cloud
  storage for recorded meetings and an upload/import flow for files. 2brain Rec
  should keep the Krisp-class meeting workspace lesson while making offline
  recording and delayed upload an explicit product guarantee.
- Resumable upload best practice is to treat server offset/progress as
  authoritative, reject mismatched offsets, and use checksums and explicit
  upload resource state rather than guessing after reconnect.
- Offline-first sync practice favors local-first persistence, quick upload when
  possible, durable local sync state, per-target sync metadata, and visible
  conflict/blocked states instead of silent overwrite or deletion.
- Durable workflow practice requires idempotent side effects and pre-existing
  result checks so retries after network, server, or worker failures do not
  create duplicate processing jobs or duplicate external submissions.

## Clarifications

### Session 2026-06-18

- Q: Is local media or transcript editing/trimming included in feature `042`
  MVP scope? -> A: No. Editing, trimming, online co-editing, replace/reprocess,
  and full video review move to future product-improvement features; `042` must
  keep revision-ready identities and contracts without implementing those flows.

## Actors And User Goals

- **MacOS Meeting Owner**: records meetings even when the network is unavailable,
  uploads them when connectivity returns, and later sees the transcript without
  manual operator work.
- **Workspace Owner**: trusts that local package state, server meeting state,
  processing state, and review state describe the same meeting and never drift
  silently.
- **Privacy/Security Owner**: needs offline buffers, upload retry, transcript
  storage, future revision boundaries, deletion truth, and evidence artifacts to
  remain bounded, auditable, and secret-free.
- **Operator/Support Reviewer**: needs enough metadata-safe evidence to diagnose
  why a meeting is local-only, uploading, processing, ready, blocked, failed, or
  out of sync.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Record Offline And Preserve The Local Package (Priority: P1)

As a macOS meeting owner, I want recording to work when the network is absent so
that a meeting is not lost just because upload cannot start during the call.

**Why this priority**: Offline-safe capture is the core improvement over the
reference product behavior. If local capture depends on network, the MVP loop is
not trustworthy.

**Independent Test**: Disable network before recording, complete a meeting,
restart the app, and confirm the local package and queue state remain visible,
non-terminal, and uploadable once network returns.

**Acceptance Scenarios**:

1. **Given** the network is unavailable before Record, **When** the user records
   and stops a meeting, **Then** the local package is saved with visible local
   truth and no server success is claimed.
2. **Given** the app quits or restarts before upload, **When** the user opens the
   app again, **Then** the same local meeting appears with the same package
   identity, retry state, and local files still retained.
3. **Given** the local package is blocked by recording-quality or privacy truth,
   **When** network returns, **Then** upload remains blocked until the user can
   see the reason and next safe action.

---

### User Story 2 - Keep One Meeting With Revision-Ready Media Truth (Priority: P1)

As a workspace owner, I want each recorded meeting to remain one logical meeting
while the product tracks the accepted media revision explicitly, so future media
editing, video capture, and transcript revision features can be added without
duplicating meetings or mutating accepted content silently.

**Why this priority**: Consistency breaks if the product treats every upload,
retry, future trim, or future video package as a new meeting. The MVP only
uploads the initial accepted revision, but it must establish the identity model
that later editing features will extend.

**Independent Test**: Create a recording, upload it after reconnect, then
inspect local queue state, server meeting state, processing state, and review
state. Confirm there is exactly one meeting identity, exactly one accepted media
revision identity for this MVP flow, and no duplicate meeting/session/processing
records for retries.

**Acceptance Scenarios**:

1. **Given** a recording is local-only or queued, **When** the queue stores it,
   **Then** the item has a stable meeting/package identity and an initial media
   revision identity that survive restart.
2. **Given** retry or reconnect creates or resumes server state, **When** the
   server already knows the same local recording identity, **Then** the existing
   meeting is reused rather than creating a duplicate.
3. **Given** a future editing feature later creates a trimmed audio or video
   revision, **When** it is designed, **Then** `042` has already reserved the
   concept that accepted media is immutable and future edits become new
   revisions rather than in-place mutation.

---

### User Story 3 - Resume Upload With Client/Server Consistency (Priority: P1)

As a user with unstable connectivity, I want upload to resume from known server
truth so that large recordings do not restart from zero and the server never
processes a partial, duplicated, or mismatched package.

**Why this priority**: Offline capture only helps if reconnect behavior is safe,
automatic, and consistent across client and server.

**Independent Test**: Interrupt upload at several points, corrupt or repeat one
part in a controlled test, reconnect, and confirm the client reconciles against
server-accepted ranges, repairs missing parts, and finalizes exactly one server
meeting for the accepted media revision.

**Acceptance Scenarios**:

1. **Given** some parts reached the server before disconnect, **When** the client
   reconnects, **Then** it asks for server truth and sends only missing or
   rejected parts.
2. **Given** the client repeats an already accepted part with the same package
   identity, **When** the server evaluates it, **Then** the result is idempotent
   and does not create duplicate meetings, sessions, tracks, or processing jobs.
3. **Given** client package metadata and server accepted metadata disagree,
   **When** reconciliation runs, **Then** the item becomes blocked or manual-only
   with a visible reason rather than being finalized incorrectly.

---

### User Story 4 - Process And Display Transcript In Web And Desktop (Priority: P1)

As a meeting owner, I want an accepted uploaded recording to be transcribed and
then appear in both the web cabinet and the installed desktop app, so that the
product loop is complete without operator tools.

**Why this priority**: Upload is not the final value. The user-visible value is
the transcript and review state becoming available after server processing.

**Independent Test**: Upload an accepted local package, run processing through
the approved server path, and open the same meeting in browser and embedded
desktop review. Confirm transcript, speaker/provenance, processing status, and
notes/action truth are consistent.

**Acceptance Scenarios**:

1. **Given** the server finalizes an accepted package, **When** processing pickup
   runs, **Then** exactly one processing workflow is associated with that server
   meeting and the desktop queue records the server meeting identity.
2. **Given** transcription imports successfully, **When** the owner opens web
   review, **Then** transcript and speaker/provenance states match the uploaded
   media revision.
3. **Given** the installed desktop app opens the embedded review route, **When**
   the same meeting is selected from upload or meeting list context, **Then** it
   shows the same transcript/review truth while native recording controls remain
   authoritative.

---

### User Story 5 - Make Out-Of-Sync States Visible And Recoverable (Priority: P1)

As a meeting owner or support reviewer, I need clear out-of-sync states so that
I can recover without guessing whether the local copy, server copy, or
transcript is authoritative.

**Why this priority**: Consistency failures are worse than ordinary failures
because they can create false transcripts, duplicate processing, or hidden data
loss.

**Independent Test**: Simulate local file deletion, server accepted range
mismatch, expired auth, processing failure, deleted server meeting, and desktop
offline review. Confirm every state has one user-safe label, one reason, and one
next action.

**Acceptance Scenarios**:

1. **Given** the server meeting exists but local queue metadata is stale, **When**
   reconciliation runs, **Then** the local queue updates from server truth or
   blocks with a safe conflict state.
2. **Given** a local package exists but the server meeting was deleted or access
   is revoked, **When** the desktop syncs, **Then** the app shows a truthful
   local-only or blocked state without re-uploading against policy.
3. **Given** processing fails after upload success, **When** the user views the
   meeting, **Then** upload remains successful while transcription status shows
   retryable/blocked/failed truth separately.

---

### User Story 6 - Preserve Privacy, Security, And Lifecycle Truth (Priority: P1)

As a privacy/security owner, I need the loop to preserve local buffer, server
storage, MediaScribe, Langfuse, deletion, diagnostics, and evidence boundaries
so that launch claims do not exceed what the system can prove.

**Why this priority**: This feature touches capture, local buffers, upload,
server processing, transcript content, external dependencies, and review UI.
Every one of those is a constitutional gate.

**Independent Test**: Inspect logs, diagnostics, screenshots, status responses,
queue files, processing records, and evidence artifacts after success/failure
flows. Confirm no raw audio, private transcript text, credentials, tokens,
signed URLs, private local paths, or hidden egress appear outside approved
controlled stores.

**Acceptance Scenarios**:

1. **Given** a recording is uploaded and processed, **When** lifecycle accounting
   is inspected, **Then** the local media revision, server artifacts,
   MediaScribe dependency state, transcript result, and future deletion
   participation are visible as metadata.
2. **Given** diagnostics or readiness evidence are generated, **When** they are
   committed or exported, **Then** they contain only metadata-safe proof.
3. **Given** transcript content is ready, **When** it appears in product UI,
   **Then** it remains authorized content and is not copied into logs,
   diagnostics, analytics, or Spec Kit evidence.

### Edge Cases

- No network before, during, or after recording.
- App quits, OS sleeps, or device restarts while upload is queued, uploading, or
  processing.
- User expects media trimming, transcript editing, or speaker-label editing in
  this MVP; product must avoid promising those future flows as available.
- Local package, queue item, upload session, server meeting, and processing
  result disagree about checksums or revision identity.
- Auth/session expires after some parts are accepted.
- Server reports accepted bytes or track roles that do not match the local
  media revision.
- Server finalization succeeds but processing pickup is delayed or unavailable.
- Processing succeeds for transcript but diarization is partial or missing.
- User opens web or desktop review while offline, unauthenticated, access
  denied, deleted, or processing.
- Local retention deadline arrives before upload can complete.
- Server deletion or access revocation happens while local buffers still exist.
- Evidence/screenshots accidentally contain private transcript text, account
  identifiers, local paths, tokens, signed URLs, raw audio names, or private
  reference-app material.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The product MUST allow recording to complete and remain visible
  when no network is available.
- **FR-002**: Every finalized local recording package MUST have a stable
  logical meeting/package identity and initial media revision identity that
  survive app restart and are used consistently through queue, server upload,
  processing, and review.
- **FR-003**: The desktop app MUST retain required local files while upload,
  reconciliation, or processing truth is non-terminal, unless an explicit
  deletion/retention policy terminalizes them.
- **FR-004**: Feature `042` MUST NOT implement user-facing audio/video trimming,
  local media editing, online transcript editing, speaker-label editing,
  collaborative editing, replace, restore, or reprocess flows.
- **FR-005**: Accepted media revision content MUST be treated as immutable for
  this MVP. Future trim, replace, video, or reprocess features MUST create
  explicit new media revisions rather than silently mutating the accepted
  revision in place.
- **FR-006**: Upload reconciliation MUST use server truth for accepted bytes,
  accepted roles, checksums, finalization state, meeting identity, and
  processing state before retrying or finalizing after reconnect.
- **FR-007**: Upload retry MUST be idempotent for meeting creation, upload
  session creation, part acceptance, finalization, and processing pickup.
- **FR-008**: The product MUST never mark a queue item as uploaded until the
  server has accepted the required tracks and manifest for the same media
  revision.
- **FR-009**: The server MUST reject or block finalization when the local media
  revision, track roles, byte counts, checksums, or manifest truth do not match
  server-accepted parts.
- **FR-010**: Server-side processing MUST start exactly once per accepted server
  meeting/media revision and MUST reuse existing workflow/job truth on retries.
- **FR-011**: Desktop clients MUST NOT call MediaScribe, receive MediaScribe
  credentials, receive object-storage credentials, or upload directly to a
  third-party STT provider.
- **FR-012**: Web cabinet and embedded desktop review MUST show the same
  transcript, speaker/provenance, processing, notes/action, access, deletion,
  and availability truth for the same server meeting.
- **FR-013**: The desktop app MUST provide a direct path from an uploaded queue
  item to the matching review surface when server meeting identity is known.
- **FR-014**: Out-of-sync states MUST have explicit user-facing labels, reason
  categories, terminality, retryability, and next action.
- **FR-015**: The product MUST distinguish upload truth from transcription
  truth; a successful upload MUST NOT imply successful transcription.
- **FR-016**: Transcript content MUST be visible only in authorized review
  surfaces and controlled content stores; logs, diagnostics, status responses,
  analytics, and Spec Kit evidence MUST stay content-safe.
- **FR-017**: Lifecycle accounting MUST include the local original media
  revision, queue state, server artifacts, MediaScribe dependency state,
  processing result, transcript state, and future deletion/revision
  participation.
- **FR-018**: The feature MUST include metadata-safe validation evidence for
  offline recording, delayed upload, resume, revision identity continuity,
  processing, web transcript display, and desktop embedded transcript display.
- **FR-019**: The feature MUST NOT broaden assisted auto-start, public links,
  external-recipient sharing, signed installer readiness, direct object upload,
  or speakerphone/AEC claims.
- **FR-020**: Product copy MUST be clean-room, Russian-ready, and must not copy
  Krisp visuals, proprietary copy, private screenshots, assets, or brand
  expression.

### Key Entities *(include if feature involves data)*

- **Capture Package**: Local `mic.wav`, `incoming.wav`, manifest, and metadata
  truth created after Record/Stop in the audio-first MVP.
- **Media Revision**: A specific accepted version of a capture package. Feature
  `042` creates only the initial accepted media revision, but the entity name
  intentionally leaves room for future local trim, replace, reprocess, and video
  revisions.
- **Media Track**: A track that belongs to a media revision. MVP tracks are
  microphone audio, system audio, and manifest truth. Future tracks may include
  screen video, camera video, thumbnails, or proxy playback artifacts only after
  separate feature approval.
- **Upload Queue Item**: Durable local state that links media revision,
  upload state, retry state, server truth, and review link availability.
- **Server Meeting**: Tenant-scoped server record representing the accepted
  logical meeting, current accepted media revision, and lifecycle status.
- **Upload Session**: Server-side transfer state, accepted ranges, accepted
  roles, checksum truth, expiry, and finalization state.
- **Processing Job**: Durable server-side transcription workflow state tied to
  one server meeting/media revision.
- **Transcript Result**: Authorized content-bearing transcript/diarization
  result with provenance and lifecycle truth.
- **Sync Conflict State**: Explicit state for mismatched local/server/revision
  truth that prevents silent overwrite, duplicate processing, or false success.

## Out Of Scope

- New automatic meeting detection or assisted auto-start.
- New audio capture path, speakerphone cleanup, Apple Voice Processing, or
  WebRTC AEC3 behavior.
- Direct object-storage upload from desktop clients.
- Direct desktop-to-MediaScribe upload or desktop-held MediaScribe credentials.
- Public unauthenticated links, external-recipient invitations, or broader
  sharing policy changes.
- Signed/notarized installer evidence for broad distribution.
- Generated notes/action creation beyond truthful display of current
  availability, deferred, processing, blocked, or unavailable states.
- User-facing local audio/video trimming, waveform editing, transcript text
  editing, speaker assignment editing, online collaborative editing, replace,
  restore, and reprocess flows.
- Full screen/video capture, full video playback, video timeline review,
  video-native annotations, and video collaboration. `042` may preserve
  media-revision compatibility for those future features but must not claim
  video runtime behavior.
- Server-side destructive editing of already accepted audio/video content
  without explicit media revision/reprocess policy.

## Dependencies

- Accepted local recording, artifact, mute/pause, system-audio, and leakage
  truth from existing macOS recording features.
- Accepted server-mediated ingest, resumable upload, processing, cabinet,
  access, deletion, and desktop embedding foundations.
- Owner authentication/session/device identity sufficient for desktop upload
  and web/embedded review.
- Owner-controlled storage, MediaScribe, Temporal, MinIO, Postgres, and
  metadata-only Langfuse boundaries from the constitution and accepted plans.
- `docs/audio-capture-backlog.md` confirms `042` is the current claimed feature
  number after reserved `037`-`041` backlog slices and before reserved
  post-MVP editing/media features `044`-`047`.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of valid offline recordings used in validation remain visible
  locally after app restart and before network recovery.
- **SC-002**: 100% of validation recordings keep one logical meeting identity
  and one accepted initial media revision identity across local queue, upload,
  processing, web review, and desktop embedded review.
- **SC-003**: 100% of interrupted uploads in validation resume from server truth
  and complete without duplicate server meetings, duplicate upload sessions,
  duplicate processing workflows, or duplicate MediaScribe submissions.
- **SC-004**: 100% of successful finalized uploads used in validation produce a
  traceable server meeting identity visible from the desktop queue.
- **SC-005**: 100% of successful processing validation runs show transcript or
  truthful partial/failed/blocked state in both web review and embedded desktop
  review.
- **SC-006**: 0 cases in validation where upload success is presented as
  transcription success before transcript result truth exists.
- **SC-007**: 100% of injected local/server mismatch cases enter an explicit
  sync conflict or blocked state with a user-safe reason and next action.
- **SC-008**: Forbidden-content scans over committed `042` specs, evidence, and
  screenshots find no raw audio, private transcript text, credentials, tokens,
  signed URLs, cookies, private account identifiers, live local paths, or
  private reference-app material.
- **SC-009**: A reviewer can identify the current state and next action for an
  offline/local-only, uploading, retrying, uploaded, processing, ready, partial,
  blocked, failed, deleted, or out-of-sync meeting within 10 seconds.
- **SC-010**: Final readiness/status docs name one strongest truthful claim for
  the loop and do not list closed `042` scope as future work.

## Assumptions

- Offline recording means capture and local persistence work without network;
  transcription still requires server processing unless a later spec adds local
  transcription.
- Local media editing/trimming, transcript text editing, speaker-label editing,
  replace/reprocess, and online collaborative editing are future
  product-improvement features, not `042` MVP scope.
- Feature `042` remains audio-first at runtime. Future screen/video recording
  and full video review must be separate features, but `042` should avoid data
  and identity choices that would force duplicate meetings when video arrives.
- The product may use existing upload and processing foundations but must prove
  the full user-facing chain as one accepted loop before claiming it works.
- Existing 2brain Rec retention/deletion truth applies to the local original
  media revision, uploaded server artifacts, processing outputs, diagnostics,
  and future purge tasks.
- External reference products are used only for information architecture and
  workflow lessons; 2brain Rec remains original and owner-controlled.
