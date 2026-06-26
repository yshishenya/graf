# Data Model: Local Upload Custody

Date: 2026-06-26

## Custody Item

Product-level lifecycle for one stopped local recording from local save through
server delivery or terminal undelivered outcome.

Backed by existing `DesktopUploadQueueItem`.

Key fields:

- `id`: deterministic queue id from local recording identity and session id.
- `sessionId`: local recording session id.
- `directoryId`: local recording/package identity and server
  `local_recording_id`.
- `localMediaRevisionId`: immutable initial local media revision id.
- `meetingId`: server meeting id when known.
- `mediaRevisionId`: server media revision id when known.
- `uploadSessionId`: server upload session id when known.
- `artifactProfile`: manifest/microphone/system presence, sizes, checksums,
  duration, uploadability, and quality warning.
- `serverTruth`: server meeting/upload/processing fingerprint.
- `retryRecords`: metadata-only upload attempts.
- `retentionDeadline`: local retention deadline.
- `retentionDecision`: current lifecycle decision and policy reference.

Validation:

- A valid custody item is not terminal until delivered or explicitly
  terminalized by user deletion, policy purge, server deletion, or unrecoverable
  cannot-send state.
- Private local paths may exist in local app state but must not appear in normal
  UI, committed evidence, diagnostics, or server reports.
- `localMediaRevisionId` must remain stable across retry, relaunch,
  re-authentication, and reconciliation.

## Custody Projection

User-safe view derived from queue and server truth.

Fields:

- `custody_state`: one of `server_unknown_local_saved`,
  `server_registered`, `upload_session_created`, `partial_uploaded`,
  `finalized`, `processing`, `delivered`, `retained_awaiting_condition`,
  `cannot_send`, `terminal_undelivered`.
- `display_priority`: integer priority from imminent local loss through all
  synced.
- `owner`: `product_automatic`, `meeting_owner`, `workspace_admin`, `support`,
  or `policy_lifecycle`.
- `retry_class`: `automatic`, `paused_until_user_action`,
  `paused_until_admin_action`, `not_retryable`, or `terminal`.
- `normal_user_action`: `none`, `sign_in`, `choose_workspace`,
  `grant_permission`, `open_review`, `open_diagnostics`, `copy_safe_report`, or
  `delete_local_copy`.
- `summary_copy_key`: stable copy key; UI owns Russian text.
- `review_available`: boolean.
- `review_desktop_url`: present only for server-known recordings with review
  availability.
- `safe_incident_available`: boolean.
- `retention_deadline`: optional timestamp for retained local media.

Validation:

- Unknown enum values fall back to `owner=support`,
  `normal_user_action=copy_safe_report`, and non-ready copy.
- Normal UI never exposes transport actions: Retry, Stop retry, manual retry,
  or manual verification.
- Review URL is never fabricated for server-unknown custody.

## Custody Owner

Role responsible for the next meaningful change.

Values:

- `product_automatic`: product will retry without user action.
- `meeting_owner`: sign-in, workspace selection, or permission grant is needed.
- `workspace_admin`: workspace policy, quota, access, legal hold, or device
  enrollment must change.
- `support`: product/support investigation is needed.
- `policy_lifecycle`: retention/deletion policy is terminalizing the recording.

Validation:

- Every blocker maps to exactly one owner.
- Copy must not blame the meeting owner for product/server transport failures.

## Server Truth Fingerprint

Existing local snapshot of server state, backed by `ServerTruthFingerprint` and
`DesktopRecordingSyncStateResponse`.

Fields:

- `meetingId`
- `mediaRevisionId`
- `uploadSessionId`
- `serverStatus`
- `processingStatus`
- `acceptedBytesByTrack`
- `requiredTrackSha256`
- `desktopTruthRule`
- `finalizedAt`

Validation:

- Accepted server ranges are authoritative for resume.
- Server deletion/access/policy truth blocks upload against policy.
- 404 sync-state is not terminal loss; it means the item remains
  server-unknown local custody.

## Custody Incident

Metadata-only explanation for blocked or terminal custody.

Fields:

- `safe_recording_identity`: local or server id safe for support.
- `reason_category`
- `problem_code`
- `owner`
- `retry_class`
- `normal_user_action`
- `created_at`
- `updated_at`
- `lifecycle_state`
- `retention_deadline`
- `server_identity_present`

Forbidden:

- raw audio
- transcript text
- local absolute paths
- bearer tokens, cookies, signed URLs, credentials, or secret values
- private meeting content

## Local Purge Verification

Desktop proof boundary for server-requested local purge tasks.

Fields:

- `task_id`
- `meeting_id`
- `task_type`
- `requested_state`
- `verification_state`: `deleted`, `tombstoned`,
  `cryptographically_unrecoverable`, `failed`, or `unverified`.
- `safe_reason`
- `completed_at`
- `client_version`

Validation:

- Acknowledge `acknowledged` only for verified deletion, tombstone, or
  cryptographic unrecoverability.
- Send `failed` or equivalent safe failure when local files are missing but
  deletion cannot be verified.
- Do not upload proof payloads or private paths.

## Queue Document Quarantine

Metadata-safe state for malformed, partially written, or schema-incompatible
local custody ledger.

Fields:

- `queue_url_fingerprint`: safe hash or redacted local identifier.
- `schema_version_seen`
- `parse_error_category`
- `quarantined_at`
- `recovery_owner`: `support`.
- `normal_user_action`: `copy_safe_report` or `open_diagnostics`.

Validation:

- Do not delete the malformed ledger automatically.
- Do not replace it with an empty "all synced" document.
- Do not show raw JSON, private local path, or stack trace in normal UI.

## State Transitions

```text
server_unknown_local_saved
  -> server_registered
  -> upload_session_created
  -> partial_uploaded
  -> finalized
  -> processing
  -> delivered

server_unknown_local_saved
  -> retained_awaiting_condition
  -> server_registered

server_registered | upload_session_created | partial_uploaded
  -> retained_awaiting_condition
  -> finalized

any non-terminal state
  -> cannot_send
  -> terminal_undelivered

any retained state near policy deadline
  -> terminal_undelivered
```

Terminal rules:

- `delivered` is terminal for local upload custody, but server processing,
  review, retention, and deletion truth continue separately.
- `terminal_undelivered` requires metadata-only lifecycle evidence.
- `terminal_undelivered` must not promise recovery.
