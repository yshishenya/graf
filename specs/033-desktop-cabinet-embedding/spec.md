# Feature Specification: Desktop Cabinet Embedding

**Feature Branch**: `033-desktop-cabinet-embedding`

**Created**: 2026-06-16

**Status**: Implemented as the native macOS embedded cabinet shell

**Input**: User description: "Continue toward MVP through the full SDD Spec Kit cycle. After feature 016 created the server-owned meeting dashboard and desktop-embedded routes, make the macOS app show that product surface inside the native shell. Keep comparing against the final V8 mockups and the Krisp desktop/web reference, but do not copy Krisp visuals, copy, assets, or proprietary behavior. Keep capture-critical controls native and move product UI that can live on the web into the web cabinet."

## Product Scope Boundary

This feature connects the already implemented server-owned meeting dashboard
surface from feature `016` to the macOS desktop shell. The user should be able
to open meetings and meeting review from the desktop app without leaving the
native capture context. The embedded product surface is allowed to show meeting
list, meeting detail, transcript, processing truth, speaker review entry
points, and gated future governance actions that already belong to the web
cabinet.

The native app remains authoritative for capture-critical trust surfaces:
recording start/stop, active recording indicator, local permission recovery,
local recording truth, upload queue truth, local diagnostics, and any future
driver or system-audio recovery. The embedded cabinet must never become the
authority for active capture or local file-system truth.

This feature preserves the clean-room reference rule. Krisp/Krisp references
may inform information architecture, density, and state placement only. 2brain
Rec must keep its own visual language, Russian product copy, controls, icons,
spacing, and product behavior.

Out of scope for this feature:

- public sharing, role-based links, exports, downloads, or share-page lifecycle;
- retention jobs, deletion execution, backup expiry accounting, or purge
  coordination;
- new recording, auto-start, detection, audio routing, permissions, or upload
  implementation;
- native reimplementation of the web cabinet meeting list or transcript review;
- broad account/admin/settings surfaces beyond a bounded desktop cabinet entry.

## Clarifications

### Session 2026-06-16

- Q: Should this slice introduce broad desktop navigation or stay limited to the meeting review value loop? -> A: Limit to the meetings workspace, meeting detail, and upload-to-review entry points.
- Q: Can embedded web content own capture, upload, deletion, sharing, or local diagnostics actions? -> A: No; embedded content is review-only for this slice and all risky/local actions stay native or future-gated.
- Q: What authentication mode is acceptable for first validation before production desktop auth handoff is complete? -> A: Existing auth/session context or seeded development identity only; no hard-coded secrets, tokens, or private account identifiers.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Open Meetings In The Desktop Shell (Priority: P1)

As a desktop user, I want the app to open on a meetings-first workspace that
includes the server-owned meeting cabinet, so that I can review processed
meetings without leaving the capture app.

**Why this priority**: Feature `016` made meeting review usable on the server,
but the MVP still feels incomplete until the desktop app can host that
surface. This is the smallest product slice that makes the app feel connected
to the processed meeting value loop.

**Independent Test**: Launch the macOS app with a configured Rec server and an
authorized user context, open the meetings workspace, and verify the embedded
surface shows the same current meeting list/detail state as the browser
cabinet while the native app chrome remains visible.

**Acceptance Scenarios**:

1. **Given** the desktop app has a valid server connection and authorized
   session, **When** the user opens the meetings workspace, **Then** the app
   shows the approved embedded meeting list surface with meeting rows,
   statuses, dates, sources, and next actions.
2. **Given** the user opens a ready meeting from the embedded list, **When**
   the meeting detail loads, **Then** transcript and speaker review content
   match the authorized web cabinet state without exposing secret paths,
   credentials, signed URLs, or raw local filesystem locations.
3. **Given** the user returns from a detail surface, **When** they navigate
   back to meetings, **Then** the desktop shell stays in the same native app
   context instead of opening a separate unrelated product destination.

---

### User Story 2 - Preserve Native Capture Authority (Priority: P1)

As a user who may be recording or preparing to record, I want the native
recording state and one-action stop path to remain visible outside the embedded
cabinet, so that reviewing meetings cannot hide or weaken capture safety.

**Why this priority**: The constitution requires visible capture and
one-action stop. Embedding web UI is only acceptable if it cannot obscure or
replace native capture truth.

**Independent Test**: Start or simulate an active desktop recording, open the
embedded meetings workspace, and verify the native active-recording indicator
and stop action remain visible, accessible, and authoritative while the
embedded surface contains no recording start/stop or device-routing controls.

**Acceptance Scenarios**:

1. **Given** a recording is active, **When** the embedded meetings surface is
   visible, **Then** the native active recording indicator and one-action stop
   remain visible and usable outside the embedded surface.
2. **Given** the embedded cabinet tries to display or navigate to a capture
   control, **When** the desktop shell evaluates the route, **Then** the shell
   blocks or bounds the route and keeps capture controls native-only.
3. **Given** the user is idle and not recording, **When** the meetings surface
   is open, **Then** the app still keeps recording start controls in the native
   shell and does not duplicate them inside the embedded cabinet.

---

### User Story 3 - Show Bounded Unavailable And Auth States (Priority: P1)

As a desktop user, I want clear unavailable, offline, expired-session, and
access-denied states, so that I know whether the server surface is unavailable
without losing local recording capability.

**Why this priority**: The web cabinet depends on server and auth state, while
desktop recording must remain truthful even when that surface cannot load.

**Independent Test**: Launch the app with server offline, invalid session,
forbidden workspace, and slow response scenarios; verify the embedded area
shows bounded recovery guidance while native recording and upload truth remain
visible and unchanged.

**Acceptance Scenarios**:

1. **Given** the Rec server is unreachable, **When** the user opens meetings,
   **Then** the embedded area shows a bounded unavailable state and the native
   app keeps local capture and upload status available.
2. **Given** the desktop session is expired or unauthorized, **When** the
   embedded cabinet loads, **Then** the user sees a sign-in or access state
   that does not disclose foreign meeting content.
3. **Given** a meeting URL points to a meeting outside the authorized
   workspace, **When** the desktop app opens it, **Then** the UI shows a
   privacy-preserving not-found or access-denied state without confirming the
   meeting exists.

---

### User Story 4 - Connect Local Upload Outcomes To Review (Priority: P2)

As a user who just recorded or uploaded a meeting, I want successful upload or
processing status to lead into the same embedded review surface, so that the
local-to-server path feels continuous.

**Why this priority**: The MVP value loop is capture, upload, process, review.
The desktop shell should make that loop visible without making upload or
processing a separate product destination.

**Independent Test**: Use seeded or simulated desktop upload queue states for
uploaded, processing, ready, and failed meetings; verify available server
meeting identifiers open the embedded review route and missing identifiers keep
truthful local upload guidance.

**Acceptance Scenarios**:

1. **Given** an upload queue item has a server meeting identifier, **When** the
   user selects its review action, **Then** the desktop app opens the embedded
   meeting detail for that item.
2. **Given** an upload is queued, uploading, failed, or locally blocked, **When**
   the user views the meetings workspace, **Then** the desktop app does not
   imply a server review exists before upload truth proves it.
3. **Given** processing is not complete, **When** the user opens the linked
   meeting detail, **Then** the embedded surface shows the server processing
   truth instead of fake transcript or notes.

---

### User Story 5 - Maintain Clean-Room Desktop/Web UX Consistency (Priority: P2)

As a product reviewer, I want the desktop embedded surface to follow the V8
meeting-first IA and Krisp-derived clean-room gates, so that the product feels
coherent without copying Krisp.

**Why this priority**: The user explicitly asked to compare against final
mockups and the reference app/web. The desktop embedding must satisfy that
quality bar before it becomes the MVP baseline.

**Independent Test**: Compare desktop screenshots, browser cabinet screenshots,
V8 reference gates, and Krisp clean-room findings; verify the desktop app uses
meeting-first IA, dense list/detail review, contextual status placement, and
separate native live controls without copied Krisp visuals or copy.

**Acceptance Scenarios**:

1. **Given** the app is open at the default workspace, **When** a reviewer
   inspects the first viewport, **Then** meetings and current recording/upload
   status are visible without a diagnostics-first layout.
2. **Given** the same meeting is opened in browser and desktop, **When** a
   reviewer compares the surfaces, **Then** product state and labels are
   consistent while native-only capture controls remain outside the embedded
   content.
3. **Given** the reference audit is repeated, **When** visual and copy checks
   run, **Then** there are no Krisp brand/copy/icon leaks and no clipped,
   overlapping, or inaccessible primary controls.

### Edge Cases

- Server cabinet route is reachable but returns an error page or malformed
  route response.
- Server takes longer than the allowed initial-load threshold.
- Auth expires while the embedded detail page is open.
- User opens an embedded meeting detail directly while no server URL is
  configured.
- The desktop app has a local upload queue item without a server meeting ID.
- A recording is active while the embedded surface reloads or navigates.
- The embedded surface attempts an external link, unsupported route, download,
  share, delete, or capture-control route.
- The user switches between light and dark macOS appearance.
- Keyboard focus moves between native shell controls and embedded content.
- The app is offline but local recording remains available.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The desktop app MUST provide a user-visible meetings workspace
  entry that opens the approved server-owned embedded meeting list surface.
- **FR-002**: The desktop app MUST support opening an approved embedded meeting
  detail from the meetings workspace and from a local upload item when a server
  meeting identifier is available.
- **FR-003**: The native shell MUST keep active recording state, one-action
  stop, recording start, local upload status, and local diagnostics outside the
  embedded cabinet and authoritative over any embedded content.
- **FR-004**: The embedded surface MUST NOT contain or execute recording
  start/stop, device routing, permission recovery, local file selection,
  local purge, or driver/system-audio recovery controls.
- **FR-005**: The desktop shell MUST restrict embedded navigation to approved
  meeting cabinet routes and handle unsupported, external, share, export,
  download, delete, or capture-control destinations with bounded behavior.
- **FR-006**: The desktop shell MUST show bounded unavailable states for server
  offline, timeout, malformed response, expired session, unauthorized access,
  and direct-link not-found outcomes without weakening local capture status.
- **FR-007**: The embedded desktop route MUST preserve the same authorized
  meeting state, labels, and content-safety behavior as the browser cabinet.
- **FR-008**: The app MUST avoid exposing MediaScribe credentials, object
  storage credentials, signed URLs, bearer tokens, passwords, raw audio,
  transcript text in logs, or live local filesystem paths through desktop UI,
  logs, screenshots, diagnostics, or accessibility labels.
- **FR-009**: The desktop shell MUST provide keyboard-reachable focus movement
  between native controls and the embedded surface, with visible focus on
  native controls and no focus trap that prevents one-action stop.
- **FR-010**: The desktop shell MUST preserve usable layout at compact desktop
  widths and standard 1440x900 review width without clipped primary controls,
  overlapping text, or hidden stop actions.
- **FR-011**: The feature MUST record validation evidence comparing the
  implemented desktop surface to V8 gates and Krisp clean-room reference
  findings without committing private reference screenshots or account data.
- **FR-012**: The feature MUST update product status and changelog notes so
  `016` is no longer listed as the next product slice once embedding is
  implemented.

### Key Entities

- **Desktop Cabinet Surface**: The embedded post-meeting product area hosted
  inside the native macOS app. It displays approved web-owned meeting routes
  but does not own capture-critical actions.
- **Native Trust Shell**: The macOS-owned app chrome and controls responsible
  for active recording truth, stop, recording start, local upload truth,
  local diagnostics, permission recovery, and local offline behavior.
- **Embedded Route Policy**: The allow/deny rules for which server-owned routes
  may load inside the desktop app and how unsupported destinations are handled.
- **Desktop Cabinet Session State**: The desktop-facing state describing
  configured server, authorization, loading, ready, offline, expired, denied,
  malformed, and timeout outcomes.
- **Upload Review Link**: The relationship between a local upload queue item
  and a server meeting identifier that can open the embedded review surface.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: With a reachable configured server and authorized session, the
  user can open the desktop meetings workspace and see the embedded meeting
  list within 3 seconds in local validation.
- **SC-002**: During an active recording, 100% of validated desktop embedded
  states keep the native active indicator and one-action stop visible and
  keyboard reachable outside the embedded surface.
- **SC-003**: Unsupported embedded navigation attempts are blocked, bounded, or
  opened outside the app according to policy in 100% of route-policy tests.
- **SC-004**: Offline, timeout, expired-session, denied, and malformed-response
  scenarios each show truthful bounded desktop states without changing local
  recording/upload truth in validation.
- **SC-005**: Content/secret scans over desktop UI strings, diagnostics,
  evidence, screenshots, and logs find zero MediaScribe credentials, object
  storage credentials, signed URLs, bearer tokens, passwords, raw audio,
  private reference content, or live local filesystem paths.
- **SC-006**: Browser cabinet and desktop embedded screenshots for the same
  seeded ready and processing meetings show consistent meeting state and
  labels, while desktop preserves native-only capture controls.
- **SC-007**: Accessibility validation confirms no focus trap prevents reaching
  the native stop action from the embedded meetings workspace.

## Assumptions

- Feature `016` routes and content-safe meeting API behavior are available and
  remain the server-owned source for list/detail/review product state.
- The first embedding slice may use local development or seeded auth context
  for validation if production desktop auth handoff is not yet ready, but the
  UI must not hard-code secrets or private account identifiers.
- The macOS app remains the only MVP native shell in scope; Windows/Linux
  shells can reuse the route contract later.
- Existing local upload queue state already contains or can safely expose a
  server meeting identifier after successful upload/finalize.
- Reference screenshots from Krisp/Krisp and private account data stay outside
  git. Tracked evidence must be sanitized and metadata-only.
