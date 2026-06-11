# Processing Lifecycle Events

All events are metadata-only by default. Event metadata must not include raw
audio, transcript text, credentials, tokens, signed URLs, passwords, or live
secret paths.

## Event Types

| Event | Required Metadata |
|---|---|
| `processing_pickup_attempted` | meeting_id, workspace_id, source, attempt |
| `processing_blocked` | meeting_id, workspace_id, reason_code |
| `workflow_started` | meeting_id, workspace_id, workflow_id |
| `workflow_duplicate_reused` | meeting_id, workspace_id, workflow_id |
| `mediascribe_submitted` | meeting_id, workspace_id, job_id_present, request_mode |
| `mediascribe_polled` | meeting_id, workspace_id, dependency_status |
| `result_import_started` | meeting_id, workspace_id, job_id_present |
| `result_imported` | meeting_id, workspace_id, transcript_segments, diarization_segments, summary_status |
| `processing_failed_retryable` | meeting_id, workspace_id, reason_code, attempt |
| `processing_failed_terminal` | meeting_id, workspace_id, reason_code |
| `processing_canceled` | meeting_id, workspace_id, reason_code |

## Reason Codes

- `meeting_not_ready`
- `missing_track_artifact`
- `track_not_transcription_ready`
- `processing_already_started`
- `workflow_unavailable`
- `mediascribe_not_configured`
- `mediascribe_auth_failed`
- `mediascribe_payload_too_large`
- `mediascribe_transient_error`
- `mediascribe_job_failed`
- `mediascribe_result_not_ready`
- `mediascribe_result_malformed`
- `result_import_failed`
- `tenant_not_authorized`
- `processing_canceled_for_future_deletion`

## Redaction Rules

- Store `job_id_present=true` in broad logs/status when the exact job id is not
  needed.
- Exact MediaScribe job id may be stored in server DB for dependency
  accounting, but must not be treated as a user-facing identifier.
- Transcript and diarization text are content-bearing and excluded from audit
  metadata.
