# Feature Specification: Meeting Dashboard Review

**Feature Branch**: `016-meeting-dashboard-review`

**Created**: 2026-06-16

**Status**: Draft

**Input**: User description: "Start 016. Inspect final mockups, but do not treat them as absolute truth. Study how this is implemented in the Crisp/Krisp app and web page. Think through the logic and begin implementation. Understand what is ready, what is not ready, and what must be reserved in the interface for future implementation so it will not need to be redesigned later. Click every button in web and app, save screenshots as reference. Prioritize quality over speed. Keep the system multiplatform: move product UI that can live in web into the web cabinet and render it in the desktop app."

## Product Scope Boundary

This feature makes processed 2brain Rec meetings usable for the owner. It
turns accepted backend ingest, auth, processing, transcript, diarization, and
RLS foundations into an authorized meeting dashboard and meeting review
experience.

The feature owns the first product-facing meeting list, meeting detail,
processing status, transcript review, speaker review, playback context,
meeting outcomes, source/provenance truth, degraded states, and safe entry
points for future access/export/delete actions.

The server web cabinet owns variable post-meeting product UI. The macOS app
may host the same allowed cabinet surface inside the native desktop trust
shell, but capture-critical state, visible recording indicator, Stop,
permission recovery, local artifact truth, upload queue truth, and local
diagnostics remain native and must not depend on server-rendered UI.

This feature must preserve clean-room distance from Crisp/Krisp references:
use product structure, information architecture, density lessons, and workflow
patterns as references, but do not copy their brand, assets, proprietary copy,
icons, visual expression, or model behavior.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Review Processed Meetings In A Web Cabinet (Priority: P1)

As a meeting owner, I want to open the web cabinet and see my uploaded and
processed meetings with clear status, source, date, participants, and next
action, so that I can find the right recording without using operator tools.

**Why this priority**: The backend can already ingest and process recordings,
but users cannot yet see or use the result. A useful meeting list is the first
launchable product surface after processing.

**Independent Test**: With multiple meetings in different states for one
workspace, open the cabinet as that user and verify only authorized meetings
appear, each row has truthful status and source labels, and ready meetings can
be opened from the list.

**Acceptance Scenarios**:

1. **Given** the user has processed, processing, failed, and local/uploaded
   meetings in the active workspace, **When** the user opens the cabinet,
   **Then** the list shows only authorized workspace meetings with clear status,
   date, source, duration, and primary action.
2. **Given** a meeting is still processing or degraded, **When** it appears in
   the list, **Then** the row explains what is available now and does not imply
   transcript, notes, export, or deletion completion.
3. **Given** the user has no meetings, **When** the cabinet opens, **Then** the
   empty state offers recording/upload next steps without implying hidden
   recording or automatic upload.

---

### User Story 2 - Read Transcript And Speaker Timeline (Priority: P1)

As a meeting owner, I want to open a ready meeting and review transcript
segments, speaker labels, source roles, and timing, so that the recording
becomes useful after transcription.

**Why this priority**: Transcript and speaker review are the first concrete
value produced by the accepted MediaScribe pipeline.

**Independent Test**: Open a processed meeting with transcript and diarization
rows and verify the detail page shows transcript text, timestamps, source role
truth, speaker lanes or speaker labels, and processing provenance without
exposing credentials or storage paths.

**Acceptance Scenarios**:

1. **Given** a meeting has imported transcript and diarization data, **When**
   the user opens meeting detail, **Then** transcript segments are readable,
   timestamped, ordered, and connected to speaker/source context.
2. **Given** local microphone and incoming/system tracks exist, **When** the
   detail page describes provenance, **Then** it distinguishes "You/local" and
   "remote/incoming" truth without exposing storage paths or signed URLs.
3. **Given** diarization is partial or uncertain, **When** the user opens
   speaker review, **Then** the UI makes uncertainty visible and provides a
   reserved correction path without falsely claiming final speaker accuracy.

---

### User Story 3 - Understand Processing And Degraded States (Priority: P1)

As a meeting owner, I want processing, failure, partial transcript, and access
states to be honest and recoverable, so that I know whether to wait, retry,
upload again, or contact an operator.

**Why this priority**: Meeting review cannot be trusted if pending and failed
states look like complete notes.

**Independent Test**: Open meetings across pending, submitted, polling,
processed, blocked, failed, deleted-future, and access-denied states and verify
the UI shows a truthful state, a safe next action, and no unavailable content.

**Acceptance Scenarios**:

1. **Given** processing is pending or running, **When** meeting detail opens,
   **Then** the page shows stage/progress truth and disables transcript-only
   actions until content is available.
2. **Given** processing failed or is blocked, **When** meeting detail opens,
   **Then** the page shows a non-content-bearing reason and safe recovery
   guidance without changing upload truth.
3. **Given** an unauthorized or cross-tenant actor requests a meeting, **When**
   the cabinet evaluates access, **Then** the UI returns a privacy-preserving
   not-found or access-denied state without confirming foreign meeting content.

---

### User Story 4 - Reserve Future Governance Actions Without Overpromising (Priority: P2)

As a workspace owner, I want share, export/download, retention, and deletion
entry points to be visible in the right information architecture but clearly
marked as not yet available or policy-controlled, so that future slices can add
them without redesigning the review surface.

**Why this priority**: The MVP must not paint itself into an IA corner before
`017` access/sharing/downloads and `018` retention/deletion execution.

**Independent Test**: Inspect list/detail/governance actions and verify future
actions are in stable locations, unavailable states are truthful, and no button
claims to share, export, download, or delete anything before those slices are
accepted.

**Acceptance Scenarios**:

1. **Given** a processed meeting is open, **When** the user opens the actions
   area, **Then** share/export/delete entry points are discoverable but clearly
   gated or disabled according to current scope.
2. **Given** deletion copy is shown, **When** the user reads it, **Then** it
   avoids universal erasure claims and distinguishes 2brain Rec controlled
   storage from external dependency/accounting boundaries.
3. **Given** future sharing or export policy is unavailable, **When** the user
   selects that action, **Then** the UI explains that the action is planned or
   policy-controlled and does not transmit data.

---

### User Story 5 - Use The Same Web-Owned Product Surface In Desktop (Priority: P2)

As a desktop user, I want to open the same meeting review surface from the
macOS app without losing local recording controls, so that desktop and browser
stay consistent while capture safety remains native.

**Why this priority**: 2brain Rec is multiplatform. Product review logic should
not be reimplemented separately in every native shell.

**Independent Test**: From the desktop app, open an allowed embedded cabinet
route for recent meetings or meeting review and verify active recording/Stop,
local upload truth, and native status remain visible and authoritative outside
the embedded product surface.

**Acceptance Scenarios**:

1. **Given** the desktop app is idle, **When** the user opens recent meetings
   or a meeting review from the app, **Then** the embedded surface shows the
   same product state and labels as the browser cabinet.
2. **Given** a recording is active, **When** the embedded meeting review is
   visible, **Then** the native recording indicator and one-action Stop remain
   visible and usable.
3. **Given** the server cabinet is offline, stale, or unauthorized, **When**
   the desktop app loads the embedded route, **Then** the native shell keeps
   capture controls and local status truthful while the product surface shows a
   bounded unavailable state.

### Edge Cases

- Meeting has processing status ready but transcript rows are empty or partial.
- Transcript exists but diarization rows are missing, malformed, or low
  confidence.
- Meeting was uploaded from desktop but processing dependency is blocked or
  MediaScribe is unavailable.
- Local recording exists but was not uploaded or has upload failure truth.
- User belongs to multiple workspaces.
- Browser cabinet and embedded desktop route are opened at the same time.
- Server or auth session expires while viewing a meeting.
- RLS hides a foreign meeting that was directly linked by URL.
- Future share/export/delete buttons are visible but unavailable in this slice.
- Reference audit finds a better IA pattern than the current V8 mockups.
- Crisp/Krisp reference pages require login, change layout, or are unavailable.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST provide an authorized meeting list for the active
  workspace with truthful status, source, date/time, duration, and primary
  action for each meeting.
- **FR-002**: The system MUST provide an authorized meeting review detail for
  processed meetings with transcript segments, timestamps, source roles,
  speaker labels, and result provenance.
- **FR-003**: The system MUST keep cross-tenant or unauthorized meeting access
  privacy-preserving by hiding or denying access without confirming foreign
  meeting content.
- **FR-004**: The system MUST show processing, pending, blocked, failed,
  degraded, partial, and unavailable states without implying transcript, notes,
  playback, share, export, download, retention, or deletion completion when
  those outcomes are not available.
- **FR-005**: The system MUST expose transcript text only inside authorized
  review surfaces and controlled content stores; logs, diagnostics, problem
  responses, and evidence MUST NOT include raw transcript text or meeting
  content.
- **FR-006**: The system MUST keep MediaScribe credentials, object-storage
  credentials, signed URLs, bearer tokens, passwords, and live secret paths out
  of product UI, API responses, logs, diagnostics, screenshots, and evidence.
- **FR-007**: The system MUST distinguish local microphone, incoming/system
  audio, desktop recording, manual upload, processing dependency, and review
  readiness in user-facing provenance copy.
- **FR-008**: The system MUST reserve stable locations for share, export,
  download, retention, and deletion actions while making unavailable/currently
  out-of-scope actions truthful and non-mutating.
- **FR-009**: The system MUST preserve deletion truth wording: no universal
  erasure promise outside 2brain Rec controlled storage and lifecycle
  accounting.
- **FR-010**: The browser cabinet MUST own post-meeting product workflows such
  as meeting list, transcript review, speaker review, outcomes, governance
  entry points, search, and filters.
- **FR-011**: The desktop app MUST be able to host allowed cabinet routes
  without server-rendered content owning active capture truth, recording
  indicator, Stop, local artifact truth, upload queue truth, permission
  recovery, or local diagnostics.
- **FR-012**: The feature MUST preserve V8 design handoff direction but allow
  documented deviations when live Crisp/Krisp/product audit evidence shows a
  better information architecture or interaction model.
- **FR-013**: The reference audit MUST capture screenshots and notes for final
  V8 mockups, live Crisp/Krisp web, and live or installed Crisp/Krisp desktop
  app surfaces where accessible.
- **FR-014**: The implementation MUST include interactive controls for primary
  review flows: open meeting, search/filter list, switch status filters, open
  transcript/speaker/outcomes sections, open future governance area, and handle
  disabled actions safely.
- **FR-015**: The system MUST pass accessibility and localization checks for
  Russian UI text, keyboard navigation, focus visibility, readable contrast,
  non-color status cues, and no text overflow in the core cabinet/review
  surfaces.
- **FR-016**: The feature MUST not add public share links, audio/transcript/
  summary downloads, deletion execution, retention jobs, billing, team admin,
  assisted auto-recording, new capture behavior, or direct desktop-to-
  MediaScribe/object-store egress.
- **FR-017**: The meeting list MUST reserve row-level future-action slots for
  saved/starred state, tags, private/shared access, collaboration status,
  sorting, and filtering without requiring those future workflows to execute in
  016.
- **FR-018**: The meeting detail MUST use a stable `Notes` and
  `Recording & Transcript` information architecture. If generated notes are not
  available, the UI MUST show a truthful unavailable/processing state rather
  than inventing content.
- **FR-019**: The meeting detail MUST reserve a meeting-scoped assistant and
  summary-template location, but 016 MUST NOT send transcript content to any AI
  service or external dependency unless a separate accepted feature owns that
  behavior and egress policy.
- **FR-020**: Speaker review MUST expose diarization labels, timestamps, and a
  stable speaker-correction entry point. Full contact mapping, speaker identity
  persistence, and assignment workflows MAY remain gated for later slices.
- **FR-021**: Screen recording, live recording mode changes, audio device
  selection, noise/accent controls, and other capture-time controls MUST remain
  outside the web meeting-review scope for 016.

### Key Entities *(include if feature involves data)*

- **MeetingListItem**: A user-facing summary of an authorized meeting, including
  meeting identity, display title, source, timing, status, duration, owner/
  workspace context, and primary action.
- **MeetingReview**: The authorized detail view state for a meeting, including
  status, transcript availability, speaker availability, provenance, outcomes,
  and governance action availability.
- **TranscriptSegmentView**: A transcript segment with sequence, time range,
  text, source role, speaker label, and confidence/provenance indicators.
- **SpeakerReviewState**: The current speaker labels, roles, uncertainty, and
  reserved correction/save states for a meeting.
- **ProcessingReviewState**: User-facing processing lifecycle summary,
  availability, failure/degraded reason, next action, and stage history.
- **GovernanceActionState**: Share/export/download/retention/deletion entry
  point state, including available, disabled, policy-blocked, planned, or
  out-of-scope reason.
- **EmbeddedCabinetRoute**: A server-owned product route allowed inside a native
  desktop shell with explicit route visibility and safety rules.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A user with processed meetings can open the cabinet and reach a
  ready meeting review in under 30 seconds without operator tooling.
- **SC-002**: 100% of meeting list and detail views hide or deny cross-tenant
  meetings without exposing foreign meeting titles, transcript text, source
  metadata, or existence confirmation.
- **SC-003**: 100% of ready meeting reviews display transcript text,
  timestamps, source role truth, speaker labels, and processing provenance.
- **SC-004**: 100% of pending, blocked, failed, partial, and unavailable states
  show a truthful reason or next action and do not show unavailable transcript,
  notes, share, export, download, retention, or deletion success.
- **SC-005**: 0 reference screenshots, implementation logs, diagnostics,
  problem responses, or validation evidence contain secrets, credentials,
  signed URLs, raw audio, live paths, or real customer meeting content.
- **SC-006**: 100% of visible share/export/delete/retention entry points are
  either safe no-op/planned states or explicitly backed by accepted future
  feature behavior.
- **SC-007**: Core cabinet/review flows pass desktop browser and embedded
  desktop-shell responsive checks with no text overlap, clipped primary
  controls, inaccessible keyboard paths, or color-only status meaning.
- **SC-008**: The final implementation evidence includes saved screenshots and
  an audit log for V8 mockups, Crisp/Krisp web, Crisp/Krisp desktop where
  accessible, and implemented 2brain Rec web/embedded surfaces.

## Assumptions

- The existing backend auth/session/device foundation from feature `013`,
  desktop upload queue from `014`, processing import from `015`, V8 design
  handoff from `030`, and RLS enforcement from `031`/`032` are the baseline.
- The first implementation may use sanitized sample or seeded meeting content
  for local UI validation, but production evidence must avoid real transcript
  text in tracked artifacts.
- Full email-auth fallback, account linking, public sharing, downloads,
  deletion execution, retention jobs, billing, broad admin, and live assisted
  auto-start remain separate slices unless this spec is explicitly amended.
- Meeting chat/assistant execution, summary-template generation, screen
  recording picker workflows, and capture-device controls remain separate
  slices unless this spec is explicitly amended.
- If the live reference product cannot be accessed without account creation,
  payment, CAPTCHA, or sensitive-data transmission, the audit will record the
  blocker and use accessible public pages plus existing saved screenshots.
- The web cabinet is the reusable product surface for future macOS, Windows,
  and Linux desktop shells; each platform keeps its own native capture trust
  shell.
