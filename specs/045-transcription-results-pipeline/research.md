# Research: Transcription Results Pipeline

## Decision: Keep Server Integrity As The Hard Pre-Processing Gate

**Rationale**: The server must know that the accepted package is the package the
desktop intended to upload. Required roles, one object per role, size, checksum,
role mapping, consent, permission, access, and deletion state protect against
processing missing, swapped, truncated, unauthorized, or deleted content. These
checks are not audio-quality judgments; they are package truth.

**Alternatives considered**:

- Remove all pre-send checks: rejected because it can send missing or corrupted
  media and produce false or unrecoverable processing state.
- Move all validation to MediaScribe: rejected because the product would lose
  control over package identity, retry safety, and user-safe reason codes.

## Decision: Local Audio Quality Signals Must Not Block Structurally Valid Uploads

**Rationale**: Real recordings may contain echo, leakage, silence, timing
imperfections, or inconclusive local measurements, but they can still produce a
useful transcript. Blocking them locally harms the core product outcome. Quality
signals should be retained as diagnostics and review/provenance context, not as
pre-transcription hard blockers.

**Alternatives considered**:

- Keep leakage/transcription-readiness as a hard local gate: rejected because it
  prevents processing the only available recording in common speakerphone
  scenarios.
- Delete quality signals entirely: rejected because support and future cleanup
  features still need metadata-safe evidence about source condition.

## Decision: Auto-Start Server Processing After Accepted Finalization When Enabled

**Rationale**: The user value is transcript availability, not upload completion.
The server already owns MediaScribe credentials, Temporal workflow start, and
processing/result storage. Triggering pickup after accepted finalization when
processing is enabled closes the product loop while preserving server-owned
egress boundaries.

**Alternatives considered**:

- Require an operator to call the internal pickup endpoint: rejected because it
  leaves the product flow incomplete for normal users.
- Let the desktop call MediaScribe or Temporal directly: rejected by the data
  boundary and secret discipline gates.
- Run processing synchronously inside finalize: rejected because external
  transcription and polling should not hold the upload request open.

## Decision: Preserve One Processing Identity Per Accepted Media Revision

**Rationale**: Offline retry, duplicate pickup, worker restart, and repeated
finalization can all happen in normal operation. Deterministic processing
identity and idempotent import keep retries safe and prevent duplicate jobs or
duplicate transcript rows for the same media revision.

**Alternatives considered**:

- Create a new job on every pickup: rejected because it duplicates costs and
  can create conflicting transcripts.
- Bind processing only to meeting identity: rejected because future media
  revisions must have separate processing truth without duplicating meetings.

## Decision: Reuse Existing Web And Desktop Review Surfaces

**Rationale**: The product already has web cabinet and embedded desktop review
routes. The missing piece is reliable state propagation from accepted upload to
processing and imported result. Reusing these surfaces keeps user navigation
simple and avoids introducing another result location.

**Alternatives considered**:

- Add a new transcription-only result page: rejected because it fragments the
  meeting review experience.
- Show results only in web cabinet first: rejected because desktop users need
  the same status and review truth from the upload context.

## Decision: Treat AEC/Noise Suppression As A Separate Evidence Track

**Rationale**: Feature `044` is still useful for improving microphone source
quality, but transcription should not wait for perfect local cleanup. The
pipeline should process the best structurally valid source available today and
allow later cleanup features to add derived media revisions when proven.

**Alternatives considered**:

- Wait for AEC before sending recordings to transcription: rejected because it
  blocks product value and turns an optional quality improvement into a launch
  dependency.
- Collapse to single mixed track now: rejected because prior evidence showed
  role separation remains important for diarization and speaker/provenance
  truth.
