# Contract: Safe sync-state projection

## Source

`GET /api/v1/desktop/recordings/{local_recording_id}/sync-state`

The macOS decoder may consume only these safe fields:

```text
meeting.meeting_id                 -> server meeting fingerprint
meeting.status                     -> server_status
meeting.processing_status          -> server_processing_status
meeting.deletion_state             -> server_deletion_state
meeting.access_state               -> server_access_state
upload_session.session_id          -> upload session fingerprint
upload_session.status              -> server_upload_status
upload_session.expected_tracks     -> expected track roles
upload_session.accepted_bytes...   -> aggregate progress counts
processing.status                  -> server_processing_status
processing.reason_code             -> safe server conflict/processing code
review.available/status             -> booleans and safe status only
conflict.state/reason/next_action   -> sync conflict and safe next action
```

Workflow IDs, review URLs, media object URLs, transcript/content availability
details and raw server identifiers are not copied to the support report.

## Truth precedence

- A confirmed `deletion_state` or `access_state` wins over old local
  `uploaded`/`finalized` flags.
- A missing response maps to `unknown`, not `deleted`.
- The existing `DesktopUploadReconciliation` conflict values remain the queue
  transition source; the additional safe fields are persisted in
  `ServerTruthFingerprint` for later report generation.
