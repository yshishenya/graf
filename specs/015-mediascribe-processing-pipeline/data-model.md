# Data Model: MediaScribe Processing Pipeline

## Entity Overview

### ProcessingWorkflow

- `id`: UUID
- `meeting_id`: UUID
- `workspace_id`: UUID
- `workflow_id`: non-sensitive durable workflow id, for example `processing/<meeting_id>`
- `workflow_run_id`: nullable external run id
- `status`: `not_submitted`, `starting`, `workflow_started`, `submitting`, `submitted`, `polling`, `importing`, `processed`, `blocked`, `failed_retryable`, `failed_terminal`, `canceled`
- `attempt_count`
- `last_reason_code`: nullable safe reason code
- `started_at`, `ended_at`, `created_at`, `updated_at`

Relationships:

- Belongs to one `Meeting`.
- Has zero or one current `MediaScribeJob`.
- Has many `ProcessingAuditEvent` records.

Validation:

- `(workspace_id, meeting_id)` is unique.
- `workflow_id` must not contain title, user email, provider subject, local file
  path, raw recording id, secret, or other PII.
- Only meetings in `ingested_pending_processing` with complete stored track
  artifacts can transition out of `not_submitted`.

### MediaScribeJob

- `id`: UUID
- `meeting_id`: UUID
- `workspace_id`: UUID
- `processing_workflow_id`: UUID
- `external_job_id`: nullable until accepted by MediaScribe
- `status`: `not_submitted`, `submitted`, `uploaded`, `transcribing`, `diarizing`, `summarizing`, `ready`, `failed`, `blocked`
- `mic_track_artifact_id`
- `incoming_track_artifact_id`
- `request_mode`: `dual_track`
- `diarize`: bool
- `summarize`: bool
- `speaker_count_mode`: nullable, `exact` or `max`
- `num_speakers`: nullable
- `submitted_at`, `last_polled_at`, `ready_at`, `failed_at`, `created_at`, `updated_at`
- `last_error_code`: nullable safe code
- `last_error_message`: nullable redacted message

Relationships:

- Belongs to one processing workflow.
- Produces one `ProcessingResult` when ready and imported.

Validation:

- At most one active MediaScribe job exists per meeting.
- If `external_job_id` exists, retries must poll the existing job rather than
  resubmit audio.
- `last_error_message` must be redacted and must not include credentials,
  signed URLs, transcript text, raw audio, or local private paths.

### ProcessingResult

- `id`: UUID
- `meeting_id`: UUID
- `workspace_id`: UUID
- `mediascribe_job_id`: UUID
- `result_version`
- `status`: `importing`, `imported`, `partial`, `failed`
- `transcript_status`: `available`, `unavailable`, `failed`
- `diarization_status`: `available`, `unavailable`, `failed`
- `summary_status`: `not_requested`, `available`, `unavailable`, `failed`
- `language`: nullable
- `segment_count`
- `diarization_segment_count`
- `source_result_hash`: nullable checksum or digest of normalized result
- `imported_at`, `created_at`, `updated_at`

Relationships:

- Has many `TranscriptSegment` rows.
- Has many `DiarizationSegment` rows.
- Has one or more lifecycle dependency records.

Validation:

- `(workspace_id, mediascribe_job_id, result_version)` is unique.
- Import for the same normalized result is idempotent.
- Result availability may be exposed without exposing transcript text.

### TranscriptSegment

- `id`: UUID
- `processing_result_id`: UUID
- `meeting_id`: UUID
- `workspace_id`: UUID
- `sequence`: integer
- `start_seconds`: decimal
- `end_seconds`: decimal
- `text`: transcript text
- `source_role`: `mic` or `incoming`
- `source_role_original`: nullable original MediaScribe role
- `created_at`

Validation:

- `(processing_result_id, sequence)` is unique.
- `end_seconds` must be greater than or equal to `start_seconds`.
- `text` is content-bearing and must not be copied into logs, audit metadata,
  status responses, or default external traces.

### DiarizationSegment

- `id`: UUID
- `processing_result_id`: UUID
- `meeting_id`: UUID
- `workspace_id`: UUID
- `sequence`: integer
- `start_seconds`: decimal
- `end_seconds`: decimal
- `speaker_label`: `MIC`, `REMOTE_00`, `REMOTE_01`, or another dependency label
- `text`: diarized text
- `source_role`: `mic` or `incoming`
- `created_at`

Validation:

- `(processing_result_id, sequence)` is unique.
- `MIC` is reserved for microphone track speech.
- Remote speaker labels must not be inferred from user names unless a later
  accepted speaker identification feature provides that mapping.

### ProcessingAuditEvent

- `id`: UUID
- `workspace_id`: UUID
- `meeting_id`: nullable UUID
- `processing_workflow_id`: nullable UUID
- `mediascribe_job_id`: nullable UUID
- `actor_user_id`: nullable UUID
- `event_type`: `processing_pickup_attempted`, `processing_blocked`, `workflow_started`, `workflow_duplicate_reused`, `mediascribe_submitted`, `mediascribe_polled`, `result_import_started`, `result_imported`, `processing_failed_retryable`, `processing_failed_terminal`, `processing_canceled`
- `metadata_json`: safe metadata only
- `created_at`

Validation:

- Metadata may include ids, statuses, reason codes, counts, timestamps, retry
  numbers, durations, and dependency names.
- Metadata must not include raw audio, transcript text, credentials, tokens,
  signed URLs, passwords, or live secret paths.

### ProcessingDependencyState

- `id`: UUID
- `meeting_id`: UUID
- `workspace_id`: UUID
- `dependency`: `temporal`, `mediascribe`, `postgres`, `minio`, `langfuse`
- `state`: `not_contacted`, `submitted`, `stored`, `imported`, `failed`, `blocked`, `deletion_pending_future`, `delete_not_supported_unknown`, `deleted_future`
- `external_reference`: nullable safe reference such as MediaScribe job id
- `last_verified_at`: nullable
- `notes`: nullable safe operator note
- `created_at`, `updated_at`

Validation:

- Used for future deletion truth; `015` records dependency state but does not
  execute deletion.
- `external_reference` must not be a signed URL, credential, or secret path.

## State Transitions

### ProcessingWorkflow

```text
not_submitted
  -> starting
  -> workflow_started
  -> submitting
  -> submitted
  -> polling
  -> importing
  -> processed

not_submitted|starting -> blocked
submitted|polling|importing -> failed_retryable
submitted|polling|importing -> failed_terminal
submitted|polling|importing -> canceled
failed_retryable -> submitting|polling|failed_terminal
```

Rules:

- `processed`, `blocked`, `failed_terminal`, and `canceled` are terminal for
  the current run unless a later explicit reprocess command is accepted.
- Duplicate pickup while an open workflow exists returns or records the existing
  workflow, not a new one.

### MediaScribeJob

```text
not_submitted -> submitted -> uploaded -> transcribing -> diarizing -> ready
submitted|uploaded|transcribing|diarizing -> failed
not_submitted -> blocked
```

Rules:

- Unknown MediaScribe status maps to retryable failure until max retry/timeout,
  then terminal failure with `unknown_dependency_status`.
- `ready` permits result fetch/import.
- `failed` does not change ingest status.

### ProcessingResult

```text
importing -> imported
importing -> partial
importing -> failed
partial -> imported|failed
```

Rules:

- Transcript and diarization imports are independently accounted, but the
  meeting reaches product-ready processing only when required result classes are
  imported or explicitly unavailable with accepted reason.

## Tenant Isolation Rules

- Every processing table includes `workspace_id`.
- Pickup, status, and replay operations must prove organization, workspace,
  user membership, and device/service authorization before reading or mutating
  state.
- Cross-tenant requests return not found or forbidden without revealing foreign
  meeting existence.
- PostgreSQL RLS remains a hardening follow-up unless implemented explicitly.

## Deletion Truth Hooks

- `ProcessingDependencyState` records whether MediaScribe received audio and
  whether imported transcript/diarization content exists.
- MediaScribe job ids and workflow ids are retained as safe dependency
  references for future deletion reporting.
- `015` does not claim external deletion; it records the dependency state future
  `018-retention-deletion-execution` must reconcile.
