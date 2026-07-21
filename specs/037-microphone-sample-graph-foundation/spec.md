# Feature Specification: Microphone Sample Graph Foundation

**Feature Branch**: `037-microphone-sample-graph-foundation`

**Created**: 2026-06-18

**Status**: Archived microphone-sample spike; not current recording acceptance

**Input**: User description: "Take backlog features 037-041 into implementation, starting from the audio-capture backlog for clean recording so speaker audio does not enter the microphone track."

## Program Context

Features `037`-`041` are the planned clean-recording chain from
`docs/audio-capture-backlog.md`. This specification activates only feature
`037`. It creates the microphone capture foundation required before any Apple
voice-processing, WebRTC AEC, fallback-decision, or recording-readiness
onboarding slice can make stronger claims.

Follow-up slices remain separate:

- `038-apple-voice-processing-spike`
- `039-webrtc-aec3-speakerphone-spike`
- `040-speakerphone-recording-fallback-decision`
- `041-recording-permission-readiness-onboarding`

## Clarifications

### Session 2026-06-18

- Q: Which recording input should the app-owned microphone stream use? -> A: The app must provide native microphone selection for recording. If the user does not choose a specific input, recording uses the current macOS default input as the fallback.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Record With A Selected App-Owned Microphone Stream (Priority: P1)

As a macOS meeting owner, I want 2brain Rec to capture local microphone frames
from the recording microphone I choose, or from the macOS default input when I
have not chosen one, so future cleanup work can process, measure, and align the
microphone track before relying on it.

**Why this priority**: Current accepted recording writes `mic.wav` through an
opaque default microphone recorder path. That is enough for MVP capture, but it
does not give the product enough control to build safe cleanup or AEC later.

**Independent Test**: Start and stop a controlled recording with microphone and
Screen/System Audio permission granted. Confirm the package still contains
`mic.wav`, `incoming.wav`, and `manifest.json`, and that the microphone track is
produced through the app-owned microphone stream with metadata evidence.

**Acceptance Scenarios**:

1. **Given** microphone and Screen/System Audio permissions are granted and the
   user has selected a recording microphone, **When** the user records and stops
   a controlled meeting, **Then** the local package contains a microphone track
   from that selected input, an incoming/system-audio track, and a manifest with
   no hidden egress or virtual-device requirement.
2. **Given** the user has not selected a recording microphone, **When** the user
   records and stops a controlled meeting, **Then** the microphone track uses the
   current macOS default input and records that fallback truth as metadata.
3. **Given** the user opens the native 2brain Rec recording controls before
   recording, **When** a recording microphone is selected, rejected, unavailable,
   or falling back to macOS default input, **Then** the selected/default status
   and recovery action are visible before Record can claim readiness.
4. **Given** the microphone stream is active, **When** recording is in progress,
   **Then** the product can observe metadata-only frame, timing, and level truth
   for the microphone stream without storing raw diagnostic samples.
5. **Given** recording stops or the app quits, **When** the microphone stream is
   released, **Then** the app leaves no active capture state and the visible
   recording indicator is cleared truthfully.

---

### User Story 2 - Fail Closed On Microphone Stream Problems (Priority: P1)

As a recording user, I need microphone permission, silence, device loss, route
change, sleep/wake, and stream-start failures to be truthful so that a broken
microphone stream never looks like a clean accepted recording.

**Why this priority**: A controllable microphone path is only useful if it makes
failure states clearer. False success would damage recording trust and future
transcription readiness.

**Independent Test**: Simulate denied permission, unavailable input, silent
input, stream-start failure, device removal, route change, sleep/wake, and app
quit while recording. Confirm each case produces a bounded blocked, degraded, or
failed state with metadata-only evidence and no hidden capture.

**Acceptance Scenarios**:

1. **Given** microphone permission is denied or restricted, **When** the user
   tries to record, **Then** recording is blocked with a specific recovery action
   and no partial success claim.
2. **Given** microphone frames stop, become silent, or lose timing confidence
   during capture, **When** the package is finalized, **Then** the manifest
   records degraded or failed microphone truth instead of clean readiness.
3. **Given** the input route changes, the device disappears, the app sleeps, or
   the app quits, **When** capture recovers or stops, **Then** the app records the
   outcome as metadata and never leaves an invisible active microphone stream.

---

### User Story 3 - Preserve Existing Package And Leakage Truth (Priority: P1)

As a product owner, I need the new microphone foundation to preserve the accepted
`025` recording package and `020` leakage finalization behavior so that this
slice does not silently redefine what a clean recording means.

**Why this priority**: `037` is foundation work, not cleanup acceptance. It must
make later cleanup possible while keeping current package truth intact.

**Independent Test**: Run accepted recording and leakage-finalization scenarios
from the current MVP path before and after this feature. Confirm existing
package shape, role labels, alignment checks, and leakage status semantics remain
compatible.

**Acceptance Scenarios**:

1. **Given** a controlled recording succeeds, **When** the package is inspected,
   **Then** existing consumers can still find `mic.wav`, `incoming.wav`, and the
   manifest fields required by accepted local recording and leakage gates.
2. **Given** speaker-to-mic leakage is present, **When** finalization runs,
   **Then** the package can still be marked `leakage_detected`, `unproven`,
   `not_measured`, or `clean` only according to existing evidence gates.
3. **Given** future cleanup or AEC work needs a microphone frame source, **When**
   it is planned, **Then** `037` provides traceable timing and stream metadata
   without claiming the current microphone track is already cleaned.

---

### User Story 4 - Keep Diagnostics Metadata-Only (Priority: P2)

As a privacy/security owner, I need microphone stream diagnostics to help debug
quality without exposing raw audio, transcript text, local private paths, or
meeting content.

**Why this priority**: This slice touches live microphone capture. Debuggability
is required, but evidence must stay safe to commit, export, and review.

**Independent Test**: Generate success, degraded, and failed recording evidence.
Confirm diagnostics include only bounded metadata such as state, counters,
timing, levels, and reason codes, with no raw samples, transcripts, credentials,
tokens, signed URLs, private meeting content, or live filesystem paths.

**Acceptance Scenarios**:

1. **Given** a recording succeeds, **When** diagnostics are exported, **Then** the
   microphone evidence contains only metadata-safe stream health and timing
   information.
2. **Given** a microphone stream failure occurs, **When** diagnostics are
   exported, **Then** the failure reason is visible without exposing content or
   secrets.

### Edge Cases

- Microphone permission is denied, restricted, revoked, or stale.
- Screen/System Audio permission is denied while microphone permission is
  granted.
- Microphone input is silent, muted, clipped, disconnected, or unavailable.
- The user-selected recording microphone is no longer available when recording
  starts.
- The user-selected recording microphone is a 2brain virtual device or another
  unsupported self-routing input.
- The user changes the recording microphone while capture is already active.
- The selected/default input route changes before, during, or after recording.
- The Mac sleeps, wakes, restarts `coreaudiod`, or the app is force-quit during
  recording.
- Microphone and incoming/system-audio tracks have duration mismatch, clock
  drift, missing timestamps, or malformed finalization metadata.
- The microphone stream starts but no accepted incoming/system-audio reference is
  available.
- Diagnostics export is requested after success, blocked start, failed start,
  failed stop, degraded finalization, or app restart.
- Future cleanup/AEC code asks for stream metadata that this slice cannot prove
  yet.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The product MUST support an app-owned microphone stream for local
  recording packages.
- **FR-002**: The product MUST continue producing the accepted local recording
  package shape: `mic.wav`, `incoming.wav`, and `manifest.json`.
- **FR-003**: The product MUST preserve the current system-audio-first MVP rule:
  recording does not require selecting `2brain Rec Microphone` or `2brain Rec
  Speaker` in the meeting app.
- **FR-004**: The product MUST let the user choose a native recording
  microphone input from the native 2brain Rec recording controls before
  recording starts and MUST use the current macOS default input when no specific
  recording microphone is selected.
- **FR-005**: The product MUST reject 2brain virtual devices and unsupported
  self-routing inputs as recording microphone selections.
- **FR-006**: The product MUST show selected/default microphone status and any
  rejected/unavailable recovery action before the recording flow can claim
  ready.
- **FR-007**: The product MUST preserve manual Record/Stop, the persistent local
  active-capture indicator, and the one-action Stop path.
- **FR-008**: The product MUST record microphone stream metadata for selected or
  default input identity, start time, stop time, frame progress, level/silence
  truth, stream availability, and failure reason when available.
- **FR-009**: The product MUST fail closed when microphone permission, selected
  input availability, stream start, frame delivery, route-change handling, or
  finalization cannot be proven.
- **FR-010**: The product MUST represent microphone stream failures as blocked,
  degraded, failed, or unproven states instead of a clean accepted recording.
- **FR-011**: The product MUST preserve existing `020` leakage finalization
  semantics and MUST NOT mark built-in speakerphone recordings clean merely
  because the microphone stream is app-owned.
- **FR-012**: The product MUST NOT introduce live echo cancellation, Apple voice
  processing acceptance, WebRTC AEC3 acceptance, or mixed-audio fallback in this
  slice.
- **FR-013**: The product MUST NOT send audio directly from the desktop app to
  MediaScribe or store MediaScribe credentials on the desktop.
- **FR-014**: Diagnostics and evidence MUST remain metadata-only and MUST NOT
  include raw audio, transcript text, credentials, tokens, signed URLs,
  passwords, live local paths, private meeting content, or participant
  identifiers.
- **FR-015**: The product MUST keep the current recording package lifecycle,
  retention, and deletion accounting compatible with future derived cleaned
  tracks without creating derived audio artifacts in this slice.
- **FR-016**: The product MUST provide enough stream truth for future `038` and
  `039` plans to evaluate Apple voice processing or WebRTC AEC using microphone
  frames and incoming/system-audio reference truth.
- **FR-017**: The product MUST preserve accepted CPU, responsiveness, and cleanup
  expectations: microphone capture must stop promptly and must not leave the app
  in a high-resource or invisible-capture state after Stop or quit.

### Key Entities *(include if feature involves data)*

- **Microphone Stream Session**: One local microphone capture attempt for a
  recording session. Key attributes include permission state, selected or default
  input identity when available, started/stopped timing, frame progress,
  level/silence status, and failure reason.
- **Microphone Stream Health**: Metadata-only evidence describing whether frames
  are arriving, timing is usable, the stream is silent or clipped, and the stream
  can be trusted for package finalization.
- **Local Recording Package**: The existing package containing microphone track,
  incoming/system-audio track, manifest, and metadata needed by recording,
  leakage, upload, and deletion workflows.
- **Future Processing Readiness**: A bounded metadata state showing whether this
  recording contains enough microphone stream truth to be considered by later
  cleanup or AEC slices.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of successful controlled recordings still produce
  `mic.wav`, `incoming.wav`, and `manifest.json`.
- **SC-002**: 100% of accepted controlled recordings include metadata proving
  the selected or default microphone stream started, delivered frames or a
  truthful empty/silent state, and stopped or failed closed.
- **SC-003**: 100% of denied-permission, unavailable-device, no-frame,
  unsupported-selection, route-change failure, and forced-stop scenarios produce
  blocked, degraded, failed, or unproven states instead of false clean success.
- **SC-004**: 100% of recording starts expose selected/default microphone status
  or a rejected/unavailable recovery action before the app claims recording
  readiness.
- **SC-005**: Existing accepted leakage finalization scenarios continue to use
  the same `clean`, `leakage_detected`, `unproven`, `not_measured`, and
  `not_applicable` semantics after this feature.
- **SC-006**: Diagnostics generated for success and failure cases contain zero
  raw audio, transcript text, credentials, tokens, signed URLs, passwords, live
  local paths, private meeting content, or participant identifiers.
- **SC-007**: Stop and app quit release microphone capture promptly enough that
  no invisible active capture or sustained high-resource state remains after the
  user-visible stop path completes.
- **SC-008**: Follow-up planning for `038` or `039` can identify microphone
  frame/timing metadata and incoming/system-audio reference metadata without
  changing the `037` package contract.

## Assumptions

- `037` is the first active implementation slice from the `037`-`041` backlog
  chain.
- `038`, `039`, `040`, and `041` remain separate Spec Kit features until the
  user explicitly activates each slice.
- The system-audio-first MVP path from `025` remains the accepted recording path.
- The leakage finalization gate from `020` remains the authority for clean versus
  contaminated package truth.
- This slice may create metadata needed for future cleanup or AEC, but it does
  not create cleaned, derived, mixed, or replacement audio tracks.
