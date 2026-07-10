# Data Model: Own Media Upload Processing

## Manual Media Upload

- `filename`: safe display filename or omitted.
- `content_type`: client-provided media content type, used as metadata only.
- `byte_length`: accepted media bytes.
- `sha256`: checksum of the accepted media bytes.
- `title`: safe optional meeting title.
- `duration_seconds`: required approximate duration for existing meeting limits.
- `local_recording_id`: stable idempotency identity for the logical upload.

Validation:

- Exactly one content-bearing media file is accepted.
- Empty files are rejected.
- Existing max upload part, max track, max package, and duration limits apply.
- Unsafe title and metadata policy applies.

## Track Artifact

Use existing `track_artifacts`.

- `track_role`: `media` for manual one-track uploads.
- `status`: `stored`.
- `media_revision_id`: accepted media revision.
- `storage_object_key`: internal object-store key; never client-visible.
- `byte_length` and `sha256`: preserved for provenance.

State:

- `pending_upload` -> `accepted` after finalize.
- Existing deletion and retention accounting must include this artifact class.

## MediaScribe Job

Use existing `mediascribe_jobs` with one schema extension.

- `request_mode`: `dual_track` or `single_track`.
- `source_track_artifact_id`: nullable reference to the single media artifact.
- `mic_track_artifact_id`: nullable for one-track jobs, present for dual-track.
- `incoming_track_artifact_id`: nullable for one-track jobs, present for dual-track.
- `external_job_id`: persisted before retry continues.

Validation:

- `single_track` jobs have `source_track_artifact_id`.
- `dual_track` jobs have microphone and incoming artifact ids.
- Existing unique workspace/meeting and workspace/external job constraints stay.

## Processing Result And Outcomes

Use existing `processing_results`, `transcript_segments`,
`diarization_segments`, `meeting_outcome_sets`, and `meeting_outcome_items`.

- Transcript import remains the primary result availability and outcomes signal.
- Diarization is optional for one-track results.
- Manual-upload review uses content-bearing diarization rows as the
  speaker-attributed transcript display source when present. If diarization has
  no display text, review falls back to transcript rows while using diarization
  timing to derive `SPEAKER_XX` labels when possible.
- Summary status is stored from MediaScribe result metadata.
- GRAF generated outcomes are produced from stored transcript rows.

Lifecycle:

- `workflow_started` -> `submitting` -> `submitted` -> `polling` -> `importing`
  -> `processed`.
- Dependency and malformed result failures reuse existing retryable/terminal
  processing status vocabulary.
