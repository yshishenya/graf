# Feature Specification: System Audio Capture Pivot

**Feature Branch**: `025-system-audio-capture-pivot`

**Created**: 2026-06-08

**Status**: Clarified - ready for planning

**Input**: User decision: "давай сделаем пивот" after repeated CoreAudio/HAL
runaway during `019-live-route-stability` validation.

## Governance Context

This feature depends on constitution v2.0.0 and ADR 002. It changes the MVP
capture path from driver-first to system-audio-first.

The driver/HAL route is not deleted by this feature. It is removed from the MVP
acceptance path and parked as future advanced routing work.

## Clarifications

### Session 2026-06-08

- Q: What audio scope counts as MVP system-audio capture? → A: Approved meeting app/window/display scope selected or confirmed by the user; arbitrary background system audio is not a recording trigger.
- Q: Can an accepted MVP recording start with missing microphone or Screen/System Audio permission? → A: No; normal accepted recording requires both permissions, while explicit degraded attempts must be labelled before start and in the manifest.
- Q: How should silent, protected, or blocked incoming audio be represented? → A: It is not success; the app records frame/level evidence and marks the incoming track degraded or blocked with a specific reason.
- Q: What runtime stability gate replaces the unsafe HAL live-publication checks? → A: No HAL probes for MVP; idle `coreaudiod` and app CPU must settle below 5% each, and active recording must avoid sustained `coreaudiod` CPU above 10% or combined app/helper CPU above 25%.
- Q: What duration evidence is required before release acceptance? → A: Reuse the two-level gate: 30-minute development validation plus 75-minute manual release validation with system-audio capture.

## User Scenarios & Testing

### User Story 1 - Record A Meeting Without Virtual Devices (Priority: P1)

As a user, I want to record a meeting by capturing system audio and my
microphone directly, so that I do not need to install, select, or debug
`2brain Rec` virtual audio devices.

**Why this priority**: This is the pivot MVP. It avoids the CoreAudio driver
runaway class while preserving the product's core value: botless dual-track
meeting recording.

**Independent Test**: Start a controlled meeting, press Record, speak locally,
play/receive remote audio, press Stop, and verify a local package contains
`mic.wav`, `incoming.wav`, and `manifest.json` without selecting virtual
devices in the meeting app.

**Acceptance Scenarios**:

1. **Given** microphone and screen/system-audio permissions are granted, **When**
   the user records a controlled meeting, **Then** both local microphone and
   incoming/system audio tracks are saved.
2. **Given** the user never selects `2brain Rec Microphone` or `2brain Rec
   Speaker` in the meeting app, **When** the recording finishes, **Then** the
   manifest still reports saved `mic.wav` and `incoming.wav` tracks.
3. **Given** recording is active, **When** the user looks at the desktop app,
   **Then** a visible local recording indicator and one-action Stop are present.
4. **Given** music, notification sounds, or non-meeting media are playing, **When**
   the user has not explicitly selected or confirmed that scope for recording,
   **Then** the app does not treat that audio as an approved meeting recording
   trigger.

---

### User Story 2 - Make Permissions And Blockers Obvious (Priority: P1)

As a user, I want the app to clearly explain missing microphone or
screen/system-audio permissions, so that I can fix setup without guessing.

**Why this priority**: System-audio-first MVP relies on macOS permissions
instead of virtual-device routing. Missing permission must block truthfully and
must not create empty artifacts that look successful.

**Independent Test**: Revoke microphone or screen/system-audio permission and
verify the app blocks recording with a specific reason and recovery action.

**Acceptance Scenarios**:

1. **Given** microphone permission is missing, **When** the user attempts to
   record, **Then** recording is blocked before creating a misleading accepted
   artifact.
2. **Given** screen/system-audio permission is missing, **When** the user
   attempts to start a normal accepted recording, **Then** recording is blocked
   with a recovery action before creating a misleading accepted artifact.
3. **Given** permission is granted after being blocked, **When** the user
   retries, **Then** the app rechecks permission state without requiring a
   driver reinstall or CoreAudio restart.
4. **Given** the user explicitly chooses a degraded recording attempt, **When**
   one required permission remains missing, **Then** the app labels the attempt
   as degraded before start and persists the same reason in the manifest.

---

### User Story 3 - Preserve Dual-Track Truth (Priority: P1)

As a user and QA owner, I want saved artifacts to truthfully show whether both
tracks were captured and aligned, so that transcription and notes are based on
trustworthy audio.

**Why this priority**: The old driver path could leave `incoming.wav` empty
while the user still heard audio. The pivot must prevent or plainly report that
failure.

**Independent Test**: Record scenarios with both tracks present, mic-only,
incoming-only, and no incoming audio, then inspect the manifest.

**Acceptance Scenarios**:

1. **Given** both sources provide frames, **When** recording stops, **Then** the
   manifest marks both tracks saved and aligned within the accepted tolerance.
2. **Given** incoming/system audio produces no frames, protected frames, or
   blocked frames, **When** recording stops, **Then** `incoming.wav` is marked
   missing/degraded with a specific failure reason.
3. **Given** one track starts late or stops early, **When** recording stops,
   **Then** the manifest reports the duration difference and alignment band.

---

### User Story 4 - Keep The Mac Responsive And Cool (Priority: P1)

As a user, I want recording to avoid CoreAudio hangs and CPU runaway, so that my
meeting app and Mac remain usable during a call.

**Why this priority**: The pivot exists because the driver path repeatedly
overheated or froze the audio stack during validation.

**Independent Test**: Run a controlled recording and idle/quit cycle while
sampling `coreaudiod`, the app, and any capture helper processes.

**Acceptance Scenarios**:

1. **Given** the app is idle, **When** no recording is active, **Then** the app
   does not publish or probe HAL virtual devices and `coreaudiod` plus the app
   settle below the idle CPU gate.
2. **Given** recording is active, **When** a controlled meeting runs, **Then**
   system load remains within the active CPU gate.
3. **Given** the user stops recording or quits the app, **When** the app settles,
   **Then** capture resources are released and CPU returns below the idle gate
   within 10 seconds.

---

### User Story 5 - Keep Driver Work Parked Safely (Priority: P2)

As an engineer, I want the old driver route clearly separated from the MVP path,
so that future driver experiments cannot regress normal recording.

**Why this priority**: The repository still contains driver code. The product
must not accidentally depend on it for MVP recording.

**Independent Test**: Disable or remove the HAL driver locally and verify the
system-audio MVP recording flow still works.

**Acceptance Scenarios**:

1. **Given** the HAL driver is absent, **When** the app records via the pivot
   path, **Then** the recording can still succeed.
2. **Given** driver diagnostics are unavailable, **When** the user opens the
   app, **Then** MVP recording status does not claim that driver repair is
   required.
3. **Given** future driver code exists, **When** MVP validation runs, **Then**
   no HAL runtime probe is required for acceptance.

## Edge Cases

- User grants microphone permission but denies screen/system-audio permission.
- User grants screen/system-audio permission but denies microphone permission.
- System audio is silent because the meeting has no remote audio yet.
- User plays music/video while recording a meeting.
- User plays music/video or notification audio while no approved meeting scope
  is selected.
- Protected/blocked audio cannot be captured by macOS.
- User stops recording while one capture stream is still finalizing.
- App crashes during recording.
- Screen/system-audio permission changes while recording is active.
- Multiple displays/windows are available for ScreenCaptureKit selection.
- Meeting audio comes from browser tab, native Zoom, Telemost, or another
  supported app.
- Existing HAL driver is installed but not used by the MVP path.
- `coreaudiod`, the desktop app, or a capture helper exceeds the CPU gate during
  idle, active recording, stop, or quit.

## Requirements

### Functional Requirements

- **FR-001**: The MVP recording path MUST capture incoming/system audio without
  requiring `2brain Rec Speaker` to be selected in the meeting app.
- **FR-002**: The MVP recording path MUST capture local microphone audio through
  explicit macOS microphone authorization.
- **FR-003**: The system MUST save separate `mic.wav` and `incoming.wav` tracks
  for accepted recordings.
- **FR-004**: The system MUST save `manifest.json` with per-track status,
  duration, byte count, frame count, alignment band, and failure reason.
- **FR-005**: The system MUST block normal accepted recording when microphone or
  screen/system-audio permission is missing, and MUST label any explicit
  degraded attempt before start and in the manifest.
- **FR-006**: The system MUST show a persistent local visible recording
  indicator and one-action Stop while recording is active.
- **FR-007**: The system MUST NOT publish, probe, or require HAL virtual audio
  devices for MVP recording acceptance.
- **FR-008**: The system MUST keep all capture diagnostics metadata-only by
  default and MUST NOT include raw audio samples, transcript text, meeting
  content, credentials, tokens, signed URLs, or passwords.
- **FR-009**: The system MUST keep recording local-first and MUST NOT upload,
  call MediaScribe, or emit Langfuse content traces in this feature.
- **FR-010**: The system MUST release microphone and system-audio capture
  resources after Stop, failure, or app quit.
- **FR-011**: The system MUST record CPU/memory evidence for idle, active
  recording, stop, and quit states.
- **FR-012**: The system MUST preserve compatibility with future backend ingest
  by keeping the dual-track artifact contract MediaScribe-ready.
- **FR-013**: The system MUST clearly mark the virtual-driver path as not part
  of MVP acceptance until a future advanced-routing spec reintroduces it.
- **FR-014**: The system MUST require an approved meeting app/window/display
  scope selected or confirmed by the user before capture can be accepted as a
  meeting recording.
- **FR-015**: The system MUST NOT use arbitrary background system audio, media
  playback, music, notifications, or non-approved apps as recording triggers.
- **FR-016**: The system MUST record metadata-only evidence for silent,
  protected, blocked, dropped, or missing incoming audio frames and map those
  states to manifest failure reasons.
- **FR-017**: The system MUST run 30-minute development validation and
  75-minute manual release validation before release acceptance can be claimed.
- **FR-018**: The system MUST define accessibility requirements for the
  recording indicator, one-action Stop, level meters, permission blockers,
  capture scope picker, and degraded-state banners.
- **FR-019**: The system MUST use localization-safe state labels for permission,
  capture scope, recording, degraded, blocked, saved, failed, no-HAL, and CPU
  gate states.
- **FR-020**: The system MUST preserve critical state meaning at small window
  sizes and with long app, window, display, and device names.

### Key Entities

- **SystemAudioCaptureSession**: A local capture session for incoming/system
  audio, including permission state, selected capture scope, scope approval
  source, frame counters, protected/blocked/silent-frame evidence, start/stop
  timestamps, and failure reason.
- **MicrophoneCaptureSession**: A local capture session for microphone audio,
  including permission state, selected input, frame counters, levels,
  start/stop timestamps, and failure reason.
- **DualTrackRecordingPackage**: Local artifact directory containing
  `manifest.json`, `mic.wav`, `incoming.wav`, diagnostics, and lifecycle state.
- **CapturePermissionState**: Per-permission state for microphone and
  screen/system-audio capture: unknown, granted, denied, restricted, stale.
- **CaptureHealthSnapshot**: Metadata-only evidence for frame continuity,
  CPU/memory, dropped frames, silence windows, and final track alignment.
- **CaptureScopeApproval**: Metadata-only record that identifies the
  user-selected or user-confirmed app/window/display scope, approval time, and
  reason why the scope is eligible for meeting recording.

## Success Criteria

### Measurable Outcomes

- **SC-001**: A controlled meeting recording produces `mic.wav`,
  `incoming.wav`, and `manifest.json` without selecting virtual 2brain Rec
  devices in the meeting app.
- **SC-002**: Accepted recordings have `durationDifferenceSeconds <= 3` between
  mic and incoming tracks.
- **SC-003**: Missing microphone or screen/system-audio permission is reported
  before normal recording starts and never creates a false saved/success state.
- **SC-004**: After a 10-second idle settle window, `coreaudiod` and the app
  each remain below 5% CPU during idle validation.
- **SC-005**: Active recording avoids CoreAudio CPU runaway, app freeze, and
  meeting-app freeze; sustained `coreaudiod` CPU above 10% or combined
  app/helper CPU above 25% fails the validation run.
- **SC-006**: Stop returns the app and capture services below the idle CPU gate
  within 10 seconds.
- **SC-007**: MVP validation can run with the HAL driver absent or ignored.
- **SC-008**: Release acceptance requires passing a 30-minute development run
  and a 75-minute manual release run with system-audio capture and microphone
  capture enabled.
- **SC-009**: Accepted recordings include a user-selected or user-confirmed
  capture scope and do not count arbitrary background system audio as a meeting
  trigger.
- **SC-010**: P1 UI states remain understandable through labels or accessible
  descriptions for screen readers, keyboard users, small windows, and long
  source names.

## Out Of Scope

- Virtual microphone/speaker routing.
- Live passthrough into meeting apps.
- Driver installer, signing, notarization, repair, rollback, or HAL runtime
  probe acceptance.
- Speaker-to-mic acoustic leakage cleanup.
- Meeting-app mute truth beyond manifest/degraded evidence.
- Backend upload, MediaScribe processing, Langfuse tracing, dashboard,
  retention, or deletion execution.
- Assisted auto-start from arbitrary system audio.

## Assumptions

- macOS Screen/System Audio capture is available on the MVP target macOS
  version.
- The user can grant microphone and screen/system-audio permissions.
- The first pivot validation can use manual Record/Stop before assisted
  auto-start is reintroduced.
- The current dual-track artifact format remains the backend/MediaScribe-ready
  contract.
- The HAL driver may remain installed during transition, but MVP recording must
  not depend on it.
