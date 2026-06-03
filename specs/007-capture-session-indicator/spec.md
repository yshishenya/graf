# Feature Specification: Manual Capture Session And Visible Indicator

**Feature Branch**: `007-capture-session-indicator`

**Created**: 2026-06-01

**Status**: Draft

**Input**: User description: "Implement recording through a full Spec Kit cycle. Build the first safe manual capture session layer after low-resource non-recording passthrough: manual start/stop, persistent visible local capture indicator, one-action stop, honest recording states, local-only evidence, and no silent or invisible recording."

## Clarifications

### Session 2026-06-01

- Q: Does this slice include upload, MediaScribe transcription, Langfuse tracing,
  dashboard notes, retention, or deletion? → A: No; this slice is local manual
  recording control and metadata-only evidence only.
- Q: What happens if every visible local recording indicator is unavailable
  during active recording? → A: Recording must stop or fail closed; invisible
  recording is never allowed.
- Q: Can recording start from assisted auto-start or meeting detection in this
  slice? → A: No; only explicit manual user start is in scope.
- Q: What browser/app targets count for this slice's short smoke evidence? → A:
  Telemost, Chrome, Opera, and Zoom; Yandex Browser remains skipped/not accepted
  unless explicitly run later.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Start And Stop Manual Recording Safely (Priority: P1)

As an internal 2brain Rec user in a supported macOS meeting, I want to start a
recording manually only after the audio route is valid, then stop it in one
action, so that I can intentionally capture a meeting without hidden automation
or unclear state.

**Why this priority**: Manual start/stop is the smallest trustworthy recording
surface. Without it, upload, transcription, notes, and assisted auto-start would
rest on an unsafe capture foundation.

**Independent Test**: Can be tested by launching 2brain Rec, selecting the
virtual microphone and speaker in a supported meeting target, confirming route
readiness, pressing Record, observing active recording state, pressing Stop once,
and confirming the session stops without upload or transcription starting.

**Acceptance Scenarios**:

1. **Given** 2brain Rec is open, the low-resource route is valid, and recording
   is allowed by local policy, **When** the user presses Record, **Then** the app
   enters active recording state and shows a persistent local capture indicator.
2. **Given** recording is active, **When** the user presses Stop from any visible
   capture surface, **Then** recording stops in one interaction and the app shows
   a stopped or finalizing state within 1 second.
3. **Given** route readiness is stale, blocked, failed, or unknown, **When** the
   user tries to start recording, **Then** recording does not start and the app
   shows the specific route blocker and recovery action.
4. **Given** recording is stopped, **When** the user remains in the meeting,
   **Then** non-recording passthrough may continue but recording state must not
   appear active.

---

### User Story 2 - Keep Active Capture Always Visible And Controllable (Priority: P1)

As a user, I want every active recording to have at least one persistent local
visible indicator with a one-action stop control, so that recording can never be
silent, invisible, or hard to stop.

**Why this priority**: The constitution requires visible capture and immediate
control. This is a trust and safety gate, not UI polish.

**Independent Test**: Can be tested by starting a recording, closing or hiding
the main window, switching focus to the meeting app, and confirming a persistent
local indicator remains visible and can stop recording in one action.

**Acceptance Scenarios**:

1. **Given** active recording starts from the main window, **When** the window is
   closed or backgrounded, **Then** at least one local indicator remains visible.
2. **Given** the floating widget is unavailable or hidden by policy, **When**
   recording is active, **Then** another persistent local indicator remains
   visible and exposes one-action stop.
3. **Given** any active recording state, **When** all visible capture surfaces
   would become unavailable, **Then** the product must stop recording or fail
   closed rather than continue invisibly.
4. **Given** the user uses keyboard navigation or assistive technology, **When**
   recording is active, **Then** the active recording state and stop action are
   discoverable without relying on color alone.

---

### User Story 3 - Preserve Honest Local Recording Evidence (Priority: P2)

As an internal tester, I want each manual recording session to produce local
metadata-only evidence about start, stop, route state, indicator state, and
failure reasons, so that QA can prove recording was intentional, visible, and
bounded without exposing meeting content.

**Why this priority**: Recording introduces audit and privacy risk. Evidence is
needed before the product can safely add upload, transcription, or notes.

**Independent Test**: Can be tested by starting and stopping a short recording,
then reviewing local diagnostics/evidence that include session lifecycle and
visible-control state without raw audio, transcript text, credentials, tokens,
signed URLs, passwords, or meeting content.

**Acceptance Scenarios**:

1. **Given** a recording starts, **When** evidence is generated, **Then** it
   records who initiated start, when start occurred, route state at start, and
   which visible indicator was active.
2. **Given** recording stops, **When** evidence is generated, **Then** it records
   stop initiator, stop reason, duration, final state, and whether stop completed
   within the one-action target.
3. **Given** recording fails, **When** evidence is generated, **Then** it records
   a metadata-only failure category and recovery action without claiming capture
   succeeded.
4. **Given** diagnostics are exported, **When** redaction is checked, **Then**
   no raw audio, transcript text, meeting content, credentials, tokens, signed
   URLs, passwords, or live secret paths appear.

---

### User Story 4 - Block Unsafe Or Policy-Disallowed Recording (Priority: P2)

As a user or admin, I want recording start to be blocked when route, permission,
policy, buffer, or visible-indicator prerequisites are not satisfied, so that
2brain Rec never starts capture in an unsafe or misleading state.

**Why this priority**: The product must fail closed before recording. Silent
partial recording is worse than no recording.

**Independent Test**: Can be tested by simulating stale route evidence, revoked
microphone permission, disabled recording policy, unavailable visible indicator,
and local buffer pressure; each case must prevent recording and show a concrete
reason.

**Acceptance Scenarios**:

1. **Given** recording policy is disabled, **When** the user presses Record,
   **Then** recording is blocked and the policy reason is shown.
2. **Given** microphone permission is revoked or route evidence is stale,
   **When** the user presses Record, **Then** recording is blocked and the app
   shows remediation without starting capture.
3. **Given** local recording storage is unavailable or below reserve, **When**
   the user presses Record, **Then** recording is blocked before audio capture
   begins rather than silently dropping data.
4. **Given** no persistent local indicator can be shown, **When** the user
   presses Record, **Then** recording is blocked or immediately stopped.

### Edge Cases

- The user presses Record twice quickly.
- The user presses Stop while recording is still starting.
- The meeting app begins using the virtual devices while recording is blocked.
- The app crashes, is force-quit, or loses its route bridge during active
  recording.
- `coreaudiod` restarts during starting, active, or stopping states.
- The user closes the main app window while recording is active.
- The route becomes stale, degraded, or failed after recording starts.
- Physical microphone or speaker changes during recording.
- Local disk/buffer reserve becomes unsafe during recording.
- The visible indicator cannot be created or becomes unavailable.
- Recording is stopped without any upload, transcription, MediaScribe, Langfuse,
  or dashboard activity.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST provide a manual Record action only when local
  policy permits recording and the current route state is valid for capture.
- **FR-002**: The system MUST provide a manual Stop action during active
  recording that completes in one user interaction.
- **FR-003**: The system MUST show at least one persistent local visible capture
  indicator for every active recording session.
- **FR-004**: The system MUST NOT continue active recording if all local visible
  capture indicators become unavailable.
- **FR-005**: The system MUST distinguish non-recording passthrough from active
  recording in all user-visible states, diagnostics, and evidence.
- **FR-006**: The system MUST block recording start when route evidence is
  stale, blocked, failed, unknown, or publication-only.
- **FR-007**: The system MUST block recording start when microphone permission,
  local policy, local buffer/storage reserve, or visible-indicator prerequisites
  are not satisfied.
- **FR-008**: The system MUST expose recording states at minimum as idle,
  starting, active, stopping, stopped, failed, and blocked.
- **FR-009**: The system MUST make every active recording stop action accessible
  through keyboard navigation and assistive technology without relying on color
  alone.
- **FR-010**: The system MUST record metadata-only lifecycle evidence for
  recording start, stop, blocker, failure, route state, indicator state, and
  final state.
- **FR-011**: The system MUST NOT start upload, MediaScribe transcription,
  Langfuse tracing, dashboard publication, or external egress as part of this
  feature.
- **FR-012**: The system MUST preserve low-resource non-recording passthrough
  behavior when recording is idle or after recording stops.
- **FR-013**: The system MUST fail closed when app process loss, route bridge
  loss, `coreaudiod` restart, or visible-indicator loss occurs during active
  recording.
- **FR-014**: The system MUST provide clear user-facing blocker and recovery
  messages for policy, permission, route, storage, and indicator failures.
- **FR-015**: The system MUST ensure diagnostics and evidence for this feature
  exclude raw audio, transcript text, meeting content, credentials, tokens,
  signed URLs, passwords, and live secret paths.
- **FR-016**: The system MUST keep manual start/stop available as the control
  model for this feature; assisted auto-start is out of scope.

### Key Entities *(include if feature involves data)*

- **Capture Session**: A local recording attempt with identity, start/stop
  timestamps, initiator, state, route snapshot, indicator state, stop reason,
  failure category, and local evidence references.
- **Capture Indicator State**: The local visible surface that proves active
  recording is observable and stoppable, including availability, accessibility,
  and stop affordance status.
- **Recording Prerequisite Snapshot**: The policy, permission, route, storage,
  and indicator readiness state evaluated before recording starts.
- **Recording Evidence Event**: A metadata-only lifecycle event for start, stop,
  blocked start, failure, recovery, and finalization.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of active recording sessions have at least one persistent
  local visible capture indicator recorded in evidence.
- **SC-002**: 100% of active recording sessions expose a one-action stop path
  from a visible local surface.
- **SC-003**: Manual Stop transitions from active to stopping/stopped within 1
  second in local validation runs.
- **SC-004**: 0 recordings start from publication-only, stale, blocked, failed,
  or unknown route evidence.
- **SC-005**: 0 recordings continue after all visible indicator surfaces are
  unavailable.
- **SC-006**: 100% of blocked starts show a concrete blocker category and next
  action.
- **SC-007**: 100% of evidence and diagnostic artifacts pass forbidden-content
  redaction checks for raw audio, transcript text, credentials, tokens, signed
  URLs, passwords, and meeting content.
- **SC-008**: Telemost, Chrome, Opera, and Zoom short manual recording smoke
  each record pass or blocked/not accepted metadata-only outcomes without
  upload, transcription, or external egress.
- **SC-009**: Non-recording passthrough remains usable after a recording stops
  in local smoke validation.

## Assumptions

- The feature targets the existing macOS app and accepted low-resource audio
  route from `006-low-resource-audio`.
- Manual recording is for internal MVP/local validation only until policy,
  upload, retention, deletion, and admin controls are implemented.
- Recording starts only from explicit local user action in this feature.
- Local capture may create local-only artifacts/evidence, but no server upload,
  MediaScribe job, Langfuse content trace, or dashboard meeting is created.
- Telemost, Chrome, Opera, and Zoom are the current smoke targets; Yandex Browser
  remains skipped/not accepted unless explicitly run later.
- Signed/notarized production installer acceptance remains outside this feature
  unless the plan explicitly pulls it in as validation evidence.
