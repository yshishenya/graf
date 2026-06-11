# Temporal Workflow Contract: 015 MediaScribe Processing

## Workflow Identity

- Workflow type: `MediaScribeProcessingWorkflow`
- Task queue: `twobrain-rec-processing`
- Workflow id: `processing/<meeting_id>`
- Workflow id content rule: internal UUIDs and fixed prefixes only; no titles,
  email addresses, provider subjects, file paths, transcript text, credentials,
  or tenant names.
- Duplicate start rule: if a workflow is already open for the same meeting,
  return/reuse the existing workflow reference and do not submit audio again.

## Input

```json
{
  "meeting_id": "00000000-0000-0000-0000-000000000000",
  "workspace_id": "00000000-0000-0000-0000-000000000000",
  "requested_by": "processing-pickup",
  "source": "ingested_pending_processing"
}
```

## Activity Boundaries

Workflow code orchestrates only. The following are activities or service
adapters:

- Load meeting and track artifact metadata.
- Validate processing eligibility.
- Read audio objects from server-controlled storage.
- Submit dual-track audio to MediaScribe.
- Persist MediaScribe job id immediately after accepted submission.
- Poll MediaScribe job state.
- Fetch and import result.
- Record metadata-only audit events and lifecycle dependency state.

## Retry Semantics

- Submission retries are allowed only until an external MediaScribe job id is
  persisted.
- After job id persistence, retries poll/fetch the existing job.
- Retryable categories: network timeout, connection failure, 429, 5xx,
  not-ready result, malformed transient response.
- Terminal categories: invalid credentials, missing required files, unsupported
  MediaScribe contract, 413 too large, 4xx validation failures, result failed
  with no retryable reason.
- Worker restart must resume from persisted workflow/job/result state.

## Output

```json
{
  "meeting_id": "00000000-0000-0000-0000-000000000000",
  "processing_status": "processed",
  "mediascribe_job_id": "job_abc123",
  "transcript_available": true,
  "diarization_available": true,
  "summary_status": "not_requested"
}
```

## Observability

- Workflow logs may include workflow id, meeting id, workspace id, state,
  reason code, retry count, and dependency status.
- Workflow logs must not include raw audio, transcript text, credentials,
  tokens, signed URLs, passwords, or live secret paths.
