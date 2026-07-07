# Feature Specification: Manual Media Upload UI

**Feature Branch**: `codex/090-manual-media-upload-ui`

**Created**: 2026-07-07

**Status**: Ready for planning

**Input**: User direction: continue by Spec Kit and think through all details
carefully. Implement the web and embedded desktop app surface for uploading a
user-owned media file on top of the completed `087` one-file backend upload and
processing path.

## Clarifications

### Session 2026-07-07

- Lane: high-risk product area. The slice touches browser and embedded desktop
  upload UX, authenticated unsafe actions, CSRF, storage custody, processing
  handoff, review readiness, accessibility, localization, and desktop WebView
  trust boundaries.
- This slice is stacked on `087-own-media-upload-processing`. It depends on
  the accepted one-file backend upload and one-track processing contract, and
  must not reimplement MediaScribe submission, storage custody, transcription
  import, generated outcomes, or deletion accounting.
- Upload stays meeting-first. The entry belongs in the meetings workspace
  header and empty state, opens a compact upload sheet, and then becomes a
  normal meeting row/status. A separate upload dashboard is out of scope.
- Browser and embedded desktop use the same server-owned upload surface.
  Native macOS remains responsible for capture, active recording truth, Stop,
  local upload queue truth, permissions, diagnostics, and offline recovery.
- The embedded desktop MVP path is the authenticated cabinet session/cookie
  path. If the desktop cabinet is loaded only through legacy injected headers
  without a browser session capable of unsafe uploads, the upload surface must
  show a safe sign-in or unavailable state rather than a broken file transfer.
- File duration is required by the existing backend contract. The UI should
  derive it from media metadata when available and require a user-entered
  approximate duration when metadata cannot be read before upload.
- Upload progress covers file transfer through server acceptance. After server
  acceptance, the existing meeting list/detail processing statuses own audio
  extraction, transcription, notes, blocked, partial, and ready states.
- Cancellation before server acceptance may abort the transfer. After server
  acceptance, the user is directed to the existing meeting detail/deletion
  truth rather than a false "undo" promise.
- Clarify scan found no additional critical user questions before planning:
  upload location, duration fallback, embedded desktop boundary, cancellation
  semantics, and session/CSRF rules are resolved by existing 030/087 product
  artifacts and constitution gates.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Upload Owned Media From Web Cabinet (Priority: P1)

An authenticated meeting owner can upload one owned audio or common meeting
media file from the browser meetings workspace, see safe validation and upload
progress, and receive a normal meeting row that continues into processing and
review.

**Why this priority**: This is the first user-visible value from the `087`
backend. Without a browser upload entry, users still cannot use GRAF for
recordings they already have.

**Independent Test**: Sign in as a meeting owner, open the browser meetings
workspace with no special desktop headers, select one small supported media
file, complete title/duration metadata, start upload, and confirm the accepted
meeting appears with manual-upload provenance and processing status.

**Acceptance Scenarios**:

1. **Given** an authenticated owner is viewing the browser meetings list,
   **When** they choose `Загрузить медиа`, select one supported media file, and
   start the upload, **Then** the UI shows transfer progress and does not claim
   transcript or notes readiness before processing creates them.
2. **Given** media metadata exposes a finite duration, **When** the file is
   selected, **Then** the duration is filled from the file and can be reviewed
   before upload.
3. **Given** media duration cannot be read locally, **When** the owner tries to
   start upload, **Then** the UI requires a positive approximate duration and
   explains that it is used for meeting length and upload limits.
4. **Given** the backend accepts the upload, **When** the transfer completes,
   **Then** the upload sheet shows the accepted meeting state and the meeting
   list can show the new row or a direct detail action without a page refresh
   dead end.

---

### User Story 2 - Upload From Embedded Desktop Cabinet (Priority: P1)

A macOS user who is signed in to the embedded cabinet can use the same upload
surface from the desktop meetings workspace while native capture controls,
active recording state, and local upload queue truth remain visible and
unchanged.

**Why this priority**: First launch requires manual upload in both browser and
app, but the desktop app must not make remote web UI responsible for recording
trust or local file custody.

**Independent Test**: Open the embedded desktop meetings workspace with a valid
owner session, trigger the upload sheet, upload a small media file, and confirm
the embedded surface follows the same accepted/processing handoff while native
capture UI remains outside the web content boundary.

**Acceptance Scenarios**:

1. **Given** the desktop app is showing the embedded meetings workspace with a
   valid owner session, **When** the user opens the upload sheet, **Then** the
   sheet uses desktop-safe copy and does not expose browser-only admin,
   billing, sharing, export, or diagnostics workflows.
2. **Given** active recording is visible in the native app shell, **When** the
   embedded upload sheet is opened or a transfer is in progress, **Then** the
   native active recording indicator and one-action Stop remain locally visible
   and are not replaced by web content.
3. **Given** the embedded cabinet lacks an unsafe-action-capable session,
   **When** the user opens the upload action, **Then** the UI shows sign-in or
   unavailable state with a safe next action instead of sending a request that
   fails without explanation.
4. **Given** the upload is accepted from the embedded surface, **When** the new
   meeting enters processing, **Then** the embedded list/detail status matches
   the browser meaning for accepted, transcribing, partial, failed, and ready.

---

### User Story 3 - Handle Upload Errors Safely (Priority: P1)

An owner receives clear, safe, localized recovery states for unsupported,
empty, oversized, corrupt, no-audio, duplicate, authentication, network, and
processing-unavailable cases without leaking secrets, object keys, private file
paths, dependency identifiers, raw transcript text, or raw media content.

**Why this priority**: Upload is a sensitive storage boundary. Incorrect error
states can leak private data, mislead users about custody, or make the product
look broken at the most trust-sensitive moment.

**Independent Test**: Try representative invalid uploads and auth/session
failure paths from browser and embedded desktop, then confirm messages are
actionable, localized, metadata-only, and keep any accepted meeting state
truthful.

**Acceptance Scenarios**:

1. **Given** no file is selected, an empty file is selected, or duration is not
   positive, **When** the user starts upload, **Then** validation blocks the
   action before transfer and identifies the missing safe input.
2. **Given** the selected file is rejected by server limits or dependency
   readiness, **When** the server responds, **Then** the UI shows a bounded
   failure reason and offers retry/change-file/detail actions without exposing
   storage or dependency internals.
3. **Given** a network failure happens before server acceptance, **When** the
   request fails, **Then** the UI says the transfer was not confirmed and
   allows retry without claiming that a meeting exists.
4. **Given** the server accepted the media but processing later blocks or
   fails, **When** the user sees the meeting row/detail, **Then** the product
   shows the accepted media and processing state separately from transcript or
   notes readiness.

---

### User Story 4 - Preserve Meeting List And Review Continuity (Priority: P2)

After upload acceptance, manual uploads behave like other GRAF meetings in the
list and review surfaces: source/provenance is truthful, filtering/search does
not hide them unexpectedly, and the user can move from upload to detail or back
to the list without losing status.

**Why this priority**: Upload is only useful if it joins the same review loop
as recorded meetings and does not create a parallel product surface.

**Independent Test**: Upload a media file, return to the meetings list, filter
or search around its title/status/source, and open its detail page while it is
processing and after it is ready.

**Acceptance Scenarios**:

1. **Given** a manual upload has been accepted, **When** the meetings list is
   refreshed or polled, **Then** the row shows a human meeting title, manual
   media source/provenance, duration, current status, and one clear next action.
2. **Given** the user searches or filters the list, **When** the uploaded
   meeting matches the visible criteria, **Then** it appears with the same row
   density and status rules as recorded meetings.
3. **Given** the user opens detail while processing is still running, **When**
   transcript or notes are not ready, **Then** the detail view shows a useful
   processing state rather than a blank or failed transcript.

### Edge Cases

- The selected media is empty, oversized, encrypted, corrupt, unsupported, or
  has no usable duration metadata.
- The selected media is a common video or meeting container with usable audio,
  but full video playback/review is not available in MVP.
- The user supplies a very long title, an unsafe title-like value, or no title.
- The user starts upload twice, refreshes during upload, or retries after an
  accepted duplicate.
- The upload request times out, is interrupted, or is aborted before server
  acceptance.
- The server accepts the media but processing is unavailable, blocked, partial,
  retrying, or terminally failed.
- The user is signed out, the owner session expires, CSRF proof is missing or
  stale, or the workspace/device scope is rejected.
- Embedded desktop has only legacy injected headers and no unsafe-action
  session.
- Active recording is running while the embedded upload sheet is open.
- The meeting list is empty, filtered to zero results, or polling while upload
  completes.
- Keyboard, screen reader, reduced motion, compact width, and long Russian copy
  must not make the sheet unusable.
- Deletion or cancellation copy must not promise erasure outside GRAF control.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The browser meetings workspace MUST expose a manual media upload
  entry from the list header and empty state for authenticated owners.
- **FR-002**: The embedded desktop meetings workspace MUST expose the same
  manual upload capability only when the current cabinet session can safely
  perform authenticated unsafe actions; otherwise it MUST show sign-in or
  unavailable state with a safe next action.
- **FR-003**: The upload interaction MUST accept exactly one user-owned media
  file per submission and MUST not present bulk import as available in this
  slice.
- **FR-004**: The upload interaction MUST support user-owned audio files and
  common video/meeting containers while presenting the MVP promise as audio
  extraction, transcript, notes, and meeting review rather than full video
  review.
- **FR-005**: The upload interaction MUST collect or derive enough safe
  metadata to satisfy the existing one-file backend contract, including a
  positive duration and an optional safe title.
- **FR-006**: When local media metadata cannot provide a finite duration, the
  UI MUST require a positive approximate duration before transfer starts.
- **FR-007**: The UI MUST show distinct states for selecting, validating,
  uploading, accepted for processing, transcribing, partial/degraded, failed,
  and ready, and MUST keep upload success separate from transcript and notes
  readiness.
- **FR-008**: The UI MUST show determinate transfer progress when the browser
  can report upload bytes, and an accessible indeterminate state when byte
  totals are unavailable.
- **FR-009**: The user MUST be able to abort a transfer before server
  acceptance; after server acceptance, available next actions MUST use existing
  meeting detail or bounded deletion truth rather than an unsafe undo claim.
- **FR-010**: The upload request from browser and embedded cabinet MUST require
  the same unsafe-action protection as other cookie-authenticated cabinet
  mutations.
- **FR-011**: Upload errors MUST be safe, localized, and actionable without
  exposing MediaScribe credentials, signed URLs, object keys, private local
  paths, raw media, raw transcript text, dependency job identifiers, or internal
  storage names.
- **FR-012**: Accepted manual uploads MUST appear as normal meeting list rows
  with truthful manual-media provenance, title, duration, status, progress when
  active, updated time, and one clear next action.
- **FR-013**: Accepted manual uploads MUST link to the existing meeting detail
  and review flow according to current access and processing state.
- **FR-014**: Browser and embedded desktop surfaces MUST use the same status
  meanings for accepted, uploading, transcribing, partial/degraded, failed,
  ready, deleted, access denied, signed out, and server offline.
- **FR-015**: Embedded upload UI MUST NOT own, obscure, restyle, replace,
  contradict, or delay native macOS active recording indicators, Stop,
  permission state, local queue truth, diagnostics, or offline recovery.
- **FR-016**: The upload surface MUST be keyboard operable, screen-reader
  labeled, reduced-motion safe, and responsive across compact embedded desktop
  and browser widths without overlapping text or controls.
- **FR-017**: User-facing copy MUST be Russian-first for this slice and MUST
  avoid implementation labels such as API, worker, object key, native layer,
  backend route, MediaScribe job id, or raw hostnames in normal product UI.
- **FR-018**: Duplicate or retried submissions MUST use the existing backend
  idempotency behavior and MUST not present duplicate meetings as a normal
  success path when the same upload identity is accepted again.
- **FR-019**: This slice MUST preserve existing desktop recording upload,
  dual-track processing, meeting review, deletion, sharing/export handoff, and
  calendar/settings behavior.
- **FR-020**: The slice MUST update changelog and validation evidence for the
  new user-visible upload UI and MUST NOT perform production deploy.

### Key Entities

- **Manual Upload Entry**: The visible action in browser and embedded meetings
  workspaces that starts the upload sheet.
- **Upload Sheet**: The server-owned modal/sheet experience for file
  selection, metadata, validation, upload progress, safe errors, and accepted
  handoff.
- **Upload Draft**: Client-side state before server acceptance, including the
  selected file, optional title, derived or entered duration, validation state,
  and abortable transfer state.
- **Manual Upload Submission**: A confirmed transfer attempt tied to the
  authenticated owner, workspace, device/session scope, and one selected media
  file.
- **Uploaded Meeting Row**: The meeting list representation created after
  server acceptance, with manual media provenance and normal processing/review
  status.
- **Upload Failure State**: A safe user-visible reason and recovery path for
  validation, auth, network, server limit, unsupported media, no-audio,
  dependency, or processing failures.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A signed-in browser owner can upload one small supported media
  file from the meetings workspace and reach an accepted meeting row in under
  two minutes on a local validation environment.
- **SC-002**: The same accepted upload path is available from the embedded
  desktop meetings workspace for a valid owner session, without adding native
  macOS file-upload business logic or hiding native capture controls.
- **SC-003**: Missing file, missing/invalid duration, empty upload, oversized
  upload, stale CSRF proof, expired session, and network failure each produce a
  safe localized recovery state with no secret, object key, private path,
  dependency job id, raw media, or raw transcript leakage.
- **SC-004**: After server acceptance, the meetings list or detail surface shows
  manual upload provenance and processing status separately from transcript and
  notes readiness within one list refresh or polling interval.
- **SC-005**: Existing `087` backend upload/processing behavior, dual-track
  desktop processing, deletion CSRF protection, meeting list/detail rendering,
  and desktop route safety tests remain passing.
- **SC-006**: Focused browser/cabinet/server/macOS route-policy tests and
  `infra/scripts/ci-local.sh` pass before closeout because this slice changes
  high-risk user-facing upload workflow and shared web surfaces.

## Assumptions

- Feature `087-own-media-upload-processing` remains the backend/API dependency
  for one-file upload acceptance and one-track processing.
- No new transcoding, video playback, waveform, resumable browser upload,
  direct object-storage upload, or MediaScribe client-side integration is
  approved in this slice.
- The first embedded desktop upload implementation uses the authenticated
  server-owned cabinet surface. A future native macOS file picker or header-only
  desktop upload bridge requires a separate safety and route-policy slice.
- Browser drag/drop may be supported when it fits the existing UI without
  reducing keyboard/file-input accessibility, but the required path is the
  explicit file picker.
- The upload surface may show a single accepted meeting handoff rather than
  implementing a full notification/reminder system.

## Out Of Scope

- Bulk import, resumable multipart browser upload, direct MinIO/object-storage
  upload URLs, background browser uploads after navigation, and upload queue
  management as a separate product destination.
- Full video playback, video timeline review, video annotations, and
  video-native collaboration.
- Native macOS capture, recording start/stop, local package uploader,
  permission recovery, diagnostics, desktop local purge, or desktop-owned
  MediaScribe behavior.
- Sharing, export/download management, deletion reports, admin/billing/team
  workflows, and production deployment.
