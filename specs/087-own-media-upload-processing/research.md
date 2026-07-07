# Research: Own Media Upload Processing

## Decision: Reuse Existing Ingest Instead Of Building A New Blob Pipeline

**Decision**: Manual media upload creates a normal meeting, upload session,
track artifact, media revision, and processing workflow.

**Rationale**: The existing path already handles tenant/device scope, checksums,
object storage, upload status, audit rows, processing pickup, review, deletion,
and generated outcomes. A separate upload subsystem would duplicate the riskiest
parts.

**Alternatives considered**:

- Direct object-store write plus ad hoc meeting row: rejected because it bypasses
  existing custody/deletion/review behavior.
- Browser-only cabinet UI first: rejected for v1 because the user asked for an
  endpoint and the API contract unblocks UI later.

## Decision: Use MediaScribe Base One-Track Endpoint

**Decision**: Submit one-track uploads to `POST /v1/audio/transcriptions` with
one multipart file field.

**Rationale**: Live probe on 2026-07-06 showed `HEAD /v1/audio/transcriptions`
returns `405` with `Allow: POST`; unauthenticated `POST` returns `401` instead
of `404`. `/v1/audio/transcriptions/single` returns `404`. The current
dual-track endpoint stays reserved for `mic_file` + `incoming_file`.

**Alternatives considered**:

- Send the same file as both dual-track inputs: rejected because it lies about
  source roles and would corrupt diarization/review semantics.
- Add `/single` endpoint assumption: rejected because live route probe showed
  no such path.

## Decision: No New Transcoding Dependency In V1

**Decision**: V1 relies on the one-track dependency endpoint to accept supported
audio/video formats and reports unsupported media as safe processing failure.

**Rationale**: The repository has no existing ffmpeg/ffprobe/transcoding stack,
while `python-multipart` is already installed. Adding a new media conversion
dependency is larger than the first useful slice.

**Alternatives considered**:

- Add ffmpeg wrapper now: rejected until a real dependency failure proves local
  normalization is required.
- Limit to WAV-only: rejected because the user asked for media file upload and
  existing MediaScribe documentation lists broader audio/video formats.

## Decision: Store Explicit Request Mode

**Decision**: Processing must record whether a MediaScribe job is `dual_track`
or `single_track`.

**Rationale**: Review, debugging, deletion/accounting, and retry behavior need
truthful provenance. Existing `request_mode` already exists; one nullable source
artifact column is enough to avoid overloading microphone/incoming columns.

**Alternatives considered**:

- Reuse microphone/incoming artifact columns for one-track uploads: rejected
  because it hides the new trust boundary and can confuse support/deletion
  evidence.

## Decision: Keep Generated Outcomes As The Summary Layer

**Decision**: Import MediaScribe summary availability as result metadata and
reuse existing GRAF outcome generation from transcript rows for visible summary,
key points, decisions, and actions.

**Rationale**: The existing outcome service already turns transcript into
review-visible notes. This avoids adding a second summary renderer before the
first one-track workflow works.

**Alternatives considered**:

- Expose MediaScribe summary text directly: rejected because current result
  schema tracks summary status but does not store a reviewed summary text field.
