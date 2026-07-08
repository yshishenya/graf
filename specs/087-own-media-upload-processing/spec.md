# Feature Specification: Own Media Upload Processing

**Feature Branch**: `codex/087-own-media-upload-processing`

**Created**: 2026-07-06

**Status**: Ready for planning

**Input**: User direction: create the next numbered implementation slice for
uploading a user's own media file, then processing it through conversion or
normalization, transcription, summary/outcomes, and review. Reuse what already
exists, use a one-track MediaScribe endpoint, think through and verify the
existing flow before coding, and keep `@ponytail` active.

## Clarifications

### Session 2026-07-06

- Lane: significant/high-risk feature. The slice touches user upload, storage,
  MediaScribe, processing, transcript content, generated outcomes, review, and
  lifecycle accounting.
- One-track means the backend submits a single owner-uploaded media source to
  MediaScribe's base transcription endpoint. It must not fabricate a missing
  second track or submit a mixed file to the existing dual-track endpoint.
- V1 is API-first. A full cabinet upload screen may reuse the same endpoint in
  a later UX slice; this slice only needs enough web/API visibility for review
  state after processing.
- Server-side MediaScribe credentials remain server-only. Desktop and browser
  clients never receive dependency secrets, signed dependency URLs, raw object
  keys, or private local paths.
- No new transcoding dependency is approved unless planning proves the
  one-track dependency endpoint cannot accept the required user media formats.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Upload One Media File (Priority: P1)

An authenticated meeting owner can submit one audio or video file as a new GRAF
meeting and receive a normal meeting identifier, upload status, and processing
status without using the macOS recorder.

**Why this priority**: This is the smallest useful workflow: a user has a
recording file already and wants GRAF to process it.

**Independent Test**: Submit a small supported media file through the one-file
upload contract and confirm a meeting is created, one media source is retained,
and processing becomes eligible without requiring microphone and system tracks.

**Acceptance Scenarios**:

1. **Given** an authenticated owner with an active workspace and trusted device,
   **When** they upload one supported media file with a safe optional title,
   **Then** GRAF creates one meeting owned by that user and marks the media
   source as accepted for processing.
2. **Given** the same upload request is retried with the same client-provided
   identity, **When** the file, title, and duration metadata match, **Then** the
   system returns the same logical meeting rather than creating a duplicate.
3. **Given** the uploaded file exceeds configured package or dependency limits,
   **When** the upload is submitted, **Then** the system fails with safe status
   and no transcript, summary, dependency secret, or raw storage path is exposed.

---

### User Story 2 - Process Through One-Track Transcription (Priority: P1)

After a single media upload is accepted, the backend submits exactly that one
media source to the one-track transcription dependency and imports transcript,
diarization when returned, summary availability, and generated outcomes into the
existing review model.

**Why this priority**: The feature is valuable only if the uploaded file reaches
the same review loop as recorded meetings.

**Independent Test**: Use a fake MediaScribe client that records request mode
and result payload, then confirm one-track submission happens once, the result
is imported, and generated outcomes become available from stored transcript
segments.

**Acceptance Scenarios**:

1. **Given** an accepted manual media upload, **When** processing starts, **Then**
   the backend calls the one-track endpoint once and records the dependency job
   as server-side state.
2. **Given** MediaScribe returns transcript and summary metadata, **When** the
   result is imported, **Then** GRAF stores transcript rows, summary status, and
   generated outcome categories using existing review/read APIs.
3. **Given** processing is retried after a successful dependency submission,
   **When** a dependency job id is already stored, **Then** the backend reuses it
   instead of creating a duplicate MediaScribe job.

---

### User Story 3 - Preserve Existing Dual-Track Recording Behavior (Priority: P1)

Existing desktop dual-track recordings continue to upload, finalize, submit to
the dual-track endpoint, and render review exactly as before.

**Why this priority**: The new manual upload workflow must not regress the core
macOS recording path.

**Independent Test**: Run existing dual-track ingest and MediaScribe submission
tests unchanged, plus a focused regression that proves dual-track requests still
use `mic_file` and `incoming_file`.

**Acceptance Scenarios**:

1. **Given** a normal desktop package with manifest, microphone, and system
   tracks, **When** it finalizes, **Then** processing still uses the dual-track
   dependency contract.
2. **Given** a single media upload and a dual-track desktop upload exist in the
   same workspace, **When** both are processed, **Then** each meeting records the
   correct request mode and review state without cross-contaminating track roles.

### Edge Cases

- MediaScribe base endpoint exists but returns an authentication, validation,
  unsupported-media, payload-too-large, timeout, or malformed response error.
- A file is empty, too large, has an unsafe title or filename, or arrives with a
  misleading content type.
- A caller tries to finalize a one-track upload as dual-track, or a dual-track
  upload with only one source.
- Processing restarts after the one-track job id is persisted but before import.
- Result import contains transcript but no diarization, summary marked
  unavailable, empty transcript, or unknown source role labels.
- Deletion and retention must account for the uploaded media source and any
  generated transcript/outcome content without claiming external dependency
  erasure that GRAF cannot prove.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST expose an authenticated one-file upload contract
  for owner-provided media and MUST keep it tenant, owner, and device scoped.
- **FR-002**: The upload contract MUST accept exactly one content-bearing media
  source for this workflow and MUST reject attempts to use the dual-track route
  with a missing or fabricated second track.
- **FR-003**: The uploaded media MUST become a normal meeting review candidate
  with source identified as manual upload or equivalent user-provided media.
- **FR-004**: The system MUST reuse existing ingest limits, checksum, object
  storage, media revision, processing workflow, result import, outcome
  generation, and cabinet review behavior wherever those contracts fit.
- **FR-005**: The system MUST submit one-track uploads to MediaScribe through a
  server-side one-track request mode and MUST keep desktop/browser clients away
  from MediaScribe credentials and dependency URLs.
- **FR-006**: The system MUST preserve the existing dual-track MediaScribe
  request mode for desktop recordings with microphone and system tracks.
- **FR-007**: The system MUST persist enough server-side provenance to
  distinguish one-track manual uploads from dual-track desktop recordings in
  processing, audit, deletion, and review evidence.
- **FR-008**: The system MUST import transcript rows, diarization rows when
  present, summary status, and generated outcome categories through the existing
  content-safe review model. For manual uploads, review MUST use content-bearing
  diarization rows as the speaker-attributed transcript display source when
  available; if diarization has no display text, review MUST fall back to
  transcript rows and use diarization timing only to derive safe `SPEAKER_XX`
  labels when possible.
- **FR-009**: The system MUST make dependency failures visible as processing
  blocked, retryable, or terminal states without leaking raw transcript text,
  secrets, signed URLs, object keys, private filenames, or private local paths.
- **FR-010**: The system MUST keep user deletion and retention wording truthful
  for uploaded media, transcript, summary/outcomes, MediaScribe dependency
  state, workflows, diagnostics, and post-egress limits.
- **FR-011**: The implementation MUST update changelog and validation evidence
  for the new behavior and MUST not perform production deploy in this slice.

### Key Entities

- **Manual Media Upload**: A user-provided audio or video file accepted as one
  content-bearing media source for a meeting.
- **Manual Upload Meeting**: A meeting created from user-provided media rather
  than live desktop capture.
- **Single-Track Media Source**: The retained object-store artifact submitted
  to one-track transcription.
- **Processing Request Mode**: The server-side distinction between one-track
  and dual-track MediaScribe submission.
- **Processing Result**: Imported transcript, diarization when available,
  summary status, and generated outcomes tied to the accepted media revision.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A small supported media file can be submitted through the one-file
  contract and reaches `ingested_pending_processing` with exactly one retained
  content media source.
- **SC-002**: One-track processing submits exactly one file to the dependency
  and records `request_mode=single_track`; existing dual-track tests still
  record `request_mode=dual_track`.
- **SC-003**: Imported one-track results render through the existing meeting
  review API with visible transcript text, `SPEAKER_XX` speaker labels, and
  generated outcomes when transcript content exists.
- **SC-004**: Duplicate retry after stored one-track job id does not create a
  second dependency submission.
- **SC-005**: Focused server tests for one-track upload, one-track MediaScribe
  mapping, dual-track regression, result import, and safe failure states pass.
- **SC-006**: `infra/scripts/ci-local.sh` passes before closeout because this
  slice changes shared backend behavior and user-facing review readiness.

## Assumptions

- MediaScribe's base `POST /v1/audio/transcriptions` endpoint is the intended
  one-track endpoint; live unauthenticated probe on 2026-07-06 returned `401`
  for that route and `405 Allow: POST` for HEAD.
- V1 uses the existing authenticated API/device boundary; a browser-only upload
  surface without device scope is future work.
- V1 does not add a new transcoding dependency. Unsupported or oversized media
  is represented as safe processing failure unless a later plan proves local
  normalization is required.
- Existing generated outcomes are sufficient for the first summary/outcome
  experience after transcript import.
