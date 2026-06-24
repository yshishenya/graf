# Data Model: Transcription Results Pipeline

## Recording Package

Represents the local capture bundle that may be uploaded and processed.

**Key attributes**:

- Stable local recording identity.
- Stable local media revision identity.
- Manifest file presence and digest.
- Required microphone and incoming/system audio file presence and digests.
- Consent and permission truth.
- Local quality observations: leakage, echo, silence, timing confidence,
  duration difference, transcription readiness, and cleanup/AEC outcome.
- Upload state and retry state.

**Validation rules**:

- Consent and permissions must allow accepted recording before upload.
- Required manifest, microphone, and incoming/system audio files must be
  present and readable.
- Local quality observations do not block upload/transcription when files are
  structurally valid.
- Local quality observations remain available as metadata-safe diagnostics.

## Upload Eligibility Decision

Represents the product decision about whether a local package may be uploaded
and become eligible for transcription.

**States**:

- `eligible`: package can be uploaded and processed.
- `eligible_with_quality_warnings`: package can be uploaded and processed, but
  local source quality or measurement confidence is imperfect.
- `blocked_privacy_or_permission`: consent or permission truth does not allow
  upload.
- `blocked_missing_or_unreadable_file`: required package files are absent or
  unreadable.
- `blocked_integrity`: role, size, checksum, or immutability truth fails.
- `blocked_lifecycle`: meeting deletion, revoked access, or prior terminal
  lifecycle state prevents processing.

**State transition**:

```text
local_package_detected
  -> eligible | eligible_with_quality_warnings | blocked_*
eligible*
  -> uploading
uploading
  -> accepted_media_revision | retryable_upload | blocked_*
```

## Accepted Media Revision

Represents the immutable server-accepted version of a recording package.

**Key attributes**:

- Meeting identity.
- Media revision identity.
- Revision number.
- Source kind.
- Manifest digest.
- Track digests by role.
- Accepted/finalized timestamps.
- Lifecycle and deletion participation.

**Validation rules**:

- The accepted fingerprint cannot silently change.
- Processing, transcript, diarization, and future derived results attach to the
  accepted media revision, not only to the meeting.

## Processing Attempt

Represents transcription and diarization work for one accepted media revision.

**Key attributes**:

- Meeting identity.
- Media revision identity.
- Processing workflow identity.
- External transcription job presence.
- Status.
- Attempt count.
- Safe reason code.
- Started, updated, and ended timestamps.

**States**:

```text
not_submitted
  -> starting
starting
  -> workflow_started | blocked_dependency | failed_retryable
workflow_started
  -> submitting -> submitted -> polling -> importing
importing
  -> processed | partial | failed_retryable | failed_terminal | blocked_dependency
```

**Validation rules**:

- Only one open processing attempt may exist for an accepted media revision.
- Retry and duplicate pickup must reuse the existing workflow identity when
  work is already open.
- Terminal and blocked states must preserve upload success separately from
  processing failure.

## Transcript Result

Represents the imported transcription and diarization output that review
surfaces may display to authorized users.

**Key attributes**:

- Processing result identity.
- Media revision identity.
- Result version.
- Transcript availability.
- Diarization availability.
- Segment timing.
- Speaker/provenance labels.
- Import status.
- Source result hash.

**Validation rules**:

- Re-import of the same result version and hash is idempotent.
- Partial transcript or diarization output must be labeled as partial instead
  of presented as fully ready.
- Transcript text is controlled content and must not appear in diagnostics,
  logs, status-only payloads, or committed evidence.

## Review Surface

Represents web cabinet and desktop embedded review.

**Key attributes**:

- Meeting identity.
- Media revision identity.
- Upload status.
- Processing status.
- Review status.
- Transcript and diarization availability.
- Safe blocked/failed reason.

**Validation rules**:

- Web and desktop review must show the same state for the same meeting and
  media revision.
- Empty/running/blocked/failed review states must not invent transcript content.
- Access/deletion state must hide or block results before content is exposed.
