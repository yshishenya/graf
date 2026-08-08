# Feature Specification: Local Recording Persistence

**Feature Branch**: `008-local-recording-persistence`

**Created**: 2026-06-02

**Status**: Historical v3 recording persistence; v5 writing is owned by feature 106

**Input**: User observed that pressing `Record` in the manual capture UI does not
produce a discoverable recording and asked where the recording is. The feature
must persist manual recording audio locally after `Stop`, producing local mic
and remote speaker track files plus metadata-only manifest evidence. It must
not add upload, transcription, MediaScribe, Langfuse, dashboard publication,
retention, deletion, or assisted auto-start claims.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Find The Recording After Stop (Priority: P1)

After manually starting and stopping a capture session, the user can see where
the local recording was saved and can inspect the recording artifact without
opening logs or developer tools.

**Why this priority**: A visible `Record` button creates the product expectation
that audio is actually recorded. The first usable recording slice must answer
"where is the recording?" directly.

**Independent Test**: Start a valid manual recording, speak briefly, stop it,
then confirm the UI exposes a local recording location and that the expected
local files exist on disk.

**Acceptance Scenarios**:

1. **Given** the audio route is valid and recording policy permits manual
   recording, **When** the user presses `Record`, speaks briefly, and presses
   `Stop`, **Then** the app shows a saved local recording location for that
   session.
2. **Given** a stopped recording session, **When** the user opens the recording
   location, **Then** the session manifest and at least one non-empty local
   audio track file are present.
3. **Given** a manual recording session with both routed mic and speaker audio
   available, **When** the session is stopped, **Then** local mic and remote
   speaker tracks are saved as separate track artifacts.

---

### User Story 2 - Preserve Recording Truth When A Track Is Missing (Priority: P1)

If a required track cannot be captured or saved, the product must not present
the session as a complete recording. It must clearly mark missing or degraded
tracks and explain what happened.

**Why this priority**: Separate mic and remote speaker capture is the core
product promise. A partial or failed recording must be truthful before upload or
transcription layers exist.

**Independent Test**: Run a recording with one simulated missing source or file
write failure and confirm the session is marked degraded or failed with a
concrete reason.

**Acceptance Scenarios**:

1. **Given** local mic frames are captured but remote speaker frames are absent,
   **When** the user stops recording, **Then** the app marks the remote speaker
   track missing or degraded and does not claim complete recording acceptance.
2. **Given** the local recording directory cannot be created or written,
   **When** the user tries to start recording, **Then** recording is blocked or
   fails closed before claiming an active persisted recording.
3. **Given** recording starts but file persistence fails during the session,
   **When** the failure is detected, **Then** recording stops or degrades with a
   visible local error and metadata-only evidence.

---

### User Story 3 - Keep Local Recording Evidence Metadata-Only (Priority: P2)

QA and diagnostics can prove which local artifacts were created without
including raw audio, transcript text, meeting content, credentials, tokens,
signed URLs, passwords, or live secret paths.

**Why this priority**: Local recording creates meeting-content artifacts. The
diagnostic surface must identify artifacts without leaking the artifacts
themselves or sensitive paths.

**Independent Test**: Generate a recording evidence bundle and confirm it
contains session id, track roles, file basenames, durations, byte counts, and
status, but not raw audio bytes, transcript text, meeting content, credentials,
tokens, signed URLs, passwords, or live secret paths.

**Acceptance Scenarios**:

1. **Given** a successful local recording, **When** diagnostics are exported,
   **Then** metadata identifies the session and track status without embedding
   audio content.
2. **Given** a recording path exists on disk, **When** evidence is generated,
   **Then** diagnostics include safe basename or relative artifact identifiers
   only, not live absolute user paths.

---

### Edge Cases

- The user presses `Stop` immediately after `Record`; the app must either save a
  truthful very short recording or mark the tracks missing/degraded.
- The recording directory is unavailable, unwritable, or out of space.
- The app process is closed during active recording.
- Only local mic or only remote speaker frames are available.
- Remote speaker frames are present in passthrough but not in the recording
  capture mirror.
- File finalization fails after audio frames have been written.
- The recording location contains prior sessions with the same display title.
- Diagnostics are requested for a recording with long local paths or user names
  in the filesystem path.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST create a local recording session artifact after a
  manual `Record`/`Stop` flow when recording prerequisites pass.
- **FR-002**: The system MUST persist local microphone and remote speaker tracks
  as separate local track artifacts when frames for both tracks are available.
- **FR-003**: The system MUST create a metadata-only manifest for each stopped
  local recording session.
- **FR-004**: Users MUST be able to discover the local recording location from
  the app after stopping a recording.
- **FR-005**: The system MUST not claim a complete recording when either required
  track is missing, empty, degraded, or failed to finalize.
- **FR-006**: The system MUST block recording start or fail closed when it cannot
  create or write the local recording directory.
- **FR-007**: The system MUST record track-level status for `local_mic` and
  `remote_speaker`, including saved, missing, degraded, failed, duration, byte
  count, and safe artifact identifier.
- **FR-008**: The system MUST keep recording diagnostics metadata-only and MUST
  exclude raw audio, transcript text, meeting content, credentials, tokens,
  signed URLs, passwords, and live secret paths.
- **FR-009**: The system MUST preserve the visible capture indicator and
  one-action stop behavior from feature `007` while local persistence is active.
- **FR-010**: The system MUST not upload local recordings, call MediaScribe,
  write Langfuse content traces, publish dashboard records, or make retention or
  deletion claims in this feature.
- **FR-011**: The system MUST preserve non-recording passthrough after recording
  stops or fails.
- **FR-012**: The system MUST provide validation evidence that a short local
  recording creates discoverable files and safe manifest metadata.

### Key Entities *(include if feature involves data)*

- **Local Recording Session**: A stopped or active manual recording instance
  associated with one capture session id, start/stop timestamps, save directory,
  completion status, and track summaries.
- **Local Recording Track**: A role-specific artifact for `local_mic` or
  `remote_speaker`, including safe artifact id, file format, byte count,
  duration, sample rate, channel count, and track status.
- **Recording Manifest**: Metadata-only session document that lists local track
  summaries and lifecycle status without raw audio content or live secret data.
- **Persistence Evidence**: QA/diagnostic event proving save outcome, track
  status, blocked/failure reason, and safe artifact identifiers.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: In a valid short manual recording smoke, the user can locate the
  saved recording artifacts within 5 seconds after pressing `Stop`.
- **SC-002**: A valid short recording produces a manifest plus non-empty local
  mic and remote speaker track artifacts when both sources provide frames.
- **SC-003**: A missing required track results in degraded or failed session
  status 100% of the time and never shows complete recording acceptance.
- **SC-004**: Diagnostic/evidence scans find no raw audio, transcript text,
  meeting content, credentials, tokens, signed URLs, passwords, or live secret
  paths in metadata outputs.
- **SC-005**: Stopping local recording does not stop or degrade existing
  non-recording passthrough in automated validation.

## Assumptions

- Feature `007-capture-session-indicator` is the immediate base layer for
  manual start/stop, visible indicator, and blocked-start policy.
- Initial local recording artifacts are development/MVP-local files; encrypted
  local buffering, upload retry, retention, deletion, and server-side meeting
  records are separate future slices.
- The local track file format can be implementation-defined during planning as
  long as it is playable or inspectable by local QA and supports duration/byte
  count validation.
- Track files may use generated session identifiers instead of meeting titles to
  avoid path collisions and content leakage.
- Browser/meeting smoke evidence remains metadata-only and must not include
  participant speech content.
