# Feature Specification: Recording Artifact Format

**Feature Branch**: `010-recording-artifact-format`

**Created**: 2026-06-04

**Status**: Accepted for local artifact format on 2026-06-04

**Input**: User wants the macOS local client to write saved recordings in the
right format before backend upload/transcription work begins. The format must
support convenient MediaScribe dual-track transcription and diarization without
requiring later rework of local artifacts, upload contracts, or backend ingest.
The known MediaScribe contract is recorded in
`docs/integrations/mediascribe-dual-track-api.md`: dual-track submission expects
separate continuous `mic_file` and `incoming_file` files, preferably WAV
`pcm_s16le`, mono, 16000 Hz, with a shared `t=0` timeline and silence preserved.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Save Transcription-Ready Dual Tracks (Priority: P1)

After a manual recording ends, the user has local artifacts that are already
ready for future backend MediaScribe submission: one local microphone track and
one incoming/remote track in the accepted speech transcription format.

**Why this priority**: Upload and transcription must not be built on temporary
or ambiguous local files. The local recording artifact format is the foundation
for server ingest, MediaScribe transcription, diarization, and deletion
accounting.

**Independent Test**: Record a short meeting, stop recording, inspect the saved
artifact package, and confirm it contains separate continuous local microphone
and incoming audio files using WAV `pcm_s16le`, mono, 16000 Hz.

**Acceptance Scenarios**:

1. **Given** a valid manual recording with local microphone and incoming audio,
   **When** the user presses `Stop`, **Then** the saved local package contains
   a `mic` track and an `incoming` track in WAV `pcm_s16le`, mono, 16000 Hz.
2. **Given** the saved package is inspected by QA, **When** track metadata is
   read, **Then** each track reports one channel, 16000 Hz sample rate, and a
   role that maps directly to MediaScribe `mic_file` or `incoming_file`.
3. **Given** a future backend worker reads the package manifest, **When** it
   prepares a MediaScribe dual-track request, **Then** it can select the two
   required files without guessing roles, converting channel layout, or parsing
   file names.

---

### User Story 2 - Preserve Timeline Truth For Diarization (Priority: P1)

The two saved tracks preserve a shared recording timeline so transcripts,
diarization segments, and future playback can align across local and remote
speech.

**Why this priority**: MediaScribe diarization returns timestamps. If local
silence is removed or one track starts later without padding, timestamps drift
and meeting reconstruction becomes untrustworthy.

**Independent Test**: Record a session with alternating local and remote audio
plus silent intervals, stop recording, and confirm both tracks retain the same
session timeline, including silence where no speech occurred.

**Acceptance Scenarios**:

1. **Given** the local microphone is silent for part of the call, **When** the
   recording is finalized, **Then** the mic track keeps silence for that
   interval instead of cutting it out.
2. **Given** incoming audio starts later than the recording start, **When** the
   recording is finalized, **Then** the incoming track is padded or represented
   so it shares the same session `t=0` as the mic track.
3. **Given** both tracks are present, **When** their durations are compared,
   **Then** the manifest reports aligned durations or a concrete degraded
   reason for any mismatch.

---

### User Story 3 - Keep Artifact Metadata Safe And Useful (Priority: P2)

QA, backend ingest, and future deletion workflows can identify the artifact
package safely without exposing meeting content, credentials, full local paths,
or MediaScribe secrets.

**Why this priority**: The package is meeting-content lifecycle input. It must
be traceable enough for future ingest/deletion while preserving the existing
metadata-only diagnostics boundary.

**Independent Test**: Generate the local manifest and diagnostics for a
recording, then confirm they include safe file basenames, roles, codec details,
durations, byte counts, checksums or integrity markers, and future
transcription readiness fields without raw audio or secrets.

**Acceptance Scenarios**:

1. **Given** a successful recording package, **When** diagnostics are generated,
   **Then** diagnostics include safe artifact identifiers, track roles, format,
   duration, byte count, and readiness status without raw audio or transcript
   text.
2. **Given** MediaScribe credentials exist in local `.env` for developer use,
   **When** local app artifacts and diagnostics are generated, **Then** no
   MediaScribe key, live secret value, signed URL, or Authorization header is
   present in the package or diagnostics.
3. **Given** a recording package is degraded or failed, **When** the manifest is
   inspected, **Then** it contains a concrete reason and does not claim
   transcription-ready acceptance.

---

### Edge Cases

- The user stops recording before one or both tracks have non-silent audio.
- One source starts late, drops out, or produces frames at a different rate.
- A track has audio frames but cannot be converted/finalized to the required
  transcription-ready format.
- The package would exceed the current public MediaScribe multipart request
  limit for long recordings.
- The app is closed or crashes during active recording finalization.
- Existing recordings from feature `008` use the older local artifact contract.
- The filesystem path contains user names, meeting titles, or non-ASCII
  characters.
- The incoming track contains multiple remote speakers but no per-speaker
  labels yet.
- Developer `.env` contains MediaScribe secrets, but desktop app output must
  remain secret-free.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST save local recording artifacts as a dual-track
  package with one local microphone track and one incoming/remote track when
  both sources are available.
- **FR-002**: The system MUST write MediaScribe-ready track files using WAV,
  PCM signed 16-bit little-endian, mono, 16000 Hz.
- **FR-003**: The system MUST map the local microphone track to future
  MediaScribe `mic_file` and the incoming/remote track to future MediaScribe
  `incoming_file`.
- **FR-004**: The system MUST preserve a shared recording timeline between the
  two tracks, including silence where speech is absent, instead of applying VAD
  trimming before persistence.
- **FR-005**: The system MUST record enough manifest metadata for future backend
  ingest to submit the package to MediaScribe without guessing file roles,
  format, duration, or readiness.
- **FR-006**: The system MUST mark a package as degraded or failed when either
  track is missing, empty when required, unaligned beyond an accepted tolerance,
  or not finalized in the required format.
- **FR-007**: The system MUST keep file names and manifest identifiers free of
  participant names, meeting titles, transcript text, raw content, credentials,
  tokens, signed URLs, passwords, live absolute user paths, and API keys.
- **FR-008**: The system MUST update local recording diagnostics and evidence so
  they report the new artifact format, role mapping, duration, byte count,
  readiness, and failure reasons without leaking audio content or secrets.
- **FR-009**: The system MUST preserve manual `Record`/`Stop`, visible capture
  indicator, one-action stop, and local saved/degraded/failed truth from
  features `007` and `008`.
- **FR-010**: The desktop app MUST NOT upload recordings, call MediaScribe,
  store MediaScribe credentials, read `MEDIASCRIBE_API_KEY`, start Langfuse
  content traces, publish dashboard records, or make retention/deletion claims
  in this feature.
- **FR-011**: The system MUST preserve non-recording passthrough after
  recording stop or artifact finalization.
- **FR-012**: The system MUST identify existing pre-010 local recording
  artifacts as legacy or not transcription-ready rather than silently claiming
  they satisfy this contract.

### Key Entities *(include if feature involves data)*

- **Recording Artifact Package**: A local saved recording directory or bundle
  containing two role-specific audio tracks plus metadata-only manifest data.
- **Mic Track**: Continuous local microphone audio mapped to future MediaScribe
  `mic_file`; expected to represent the recording owner/local participant.
- **Incoming Track**: Continuous remote/incoming meeting audio mapped to future
  MediaScribe `incoming_file`; may contain multiple remote speakers for
  diarization.
- **Artifact Manifest**: Metadata-only description of package schema version,
  track roles, format, timeline alignment, duration, byte counts, checksums or
  integrity markers, status, readiness, and failure reasons.
- **Transcription Readiness State**: Package-level and track-level status
  describing whether the package is ready for future MediaScribe dual-track
  submission, degraded, failed, or legacy/not ready.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A valid short manual recording produces exactly two required
  transcription-ready track files: mic and incoming.
- **SC-002**: Automated validation confirms each required track is WAV
  `pcm_s16le`, mono, 16000 Hz.
- **SC-003**: A valid short recording manifest maps track roles to
  `mic_file` and `incoming_file` with no ambiguous or missing role labels.
- **SC-004**: Validation confirms silent intervals are preserved well enough
  that both tracks share a common start time and aligned duration, or the
  package is marked degraded/failed with a concrete reason.
- **SC-005**: Diagnostic and manifest scans find no raw audio, transcript text,
  meeting content, credentials, tokens, signed URLs, passwords, live secret
  paths, or full MediaScribe API keys.
- **SC-006**: Existing `007` and `008` validation gates still pass after the
  format change.

## Assumptions

- The MediaScribe dual-track contract in
  `docs/integrations/mediascribe-dual-track-api.md` is the current integration
  source of truth for future backend transcription.
- This feature changes local artifact format and metadata only; upload,
  resumable ingest, MediaScribe job submission, polling, result import,
  dashboard publication, retention, deletion, and summaries remain future
  slices.
- WAV `pcm_s16le`, mono, 16000 Hz is accepted despite larger file size because
  it minimizes server-side conversion and protects diarization/timestamp
  quality.
- File-size controls for recordings that exceed MediaScribe public upload
  limits may be planned separately; this feature must at least record size and
  readiness/degraded state truthfully.
- Existing `008` recording artifacts may remain readable as legacy artifacts,
  but new recordings should satisfy this contract after implementation.
