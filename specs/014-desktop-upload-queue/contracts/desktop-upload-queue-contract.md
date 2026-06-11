# Contract: Desktop Upload Queue

## Purpose

This contract defines the desktop-side behavior between finalized local
recordings, local durable queue state, the existing UI, diagnostics, and the
`012-server-ingest-foundation` server-mediated ingest API.

## Local Queue Store Contract

Queue state is persisted as metadata-only JSON.

Required top-level fields:

- `schemaVersion`: `desktop-upload-queue.v1`
- `updatedAt`
- `items`

Each item requires:

- `id`
- `sessionId`
- `directoryId`
- `state`
- `failureCategory`
- `retryMode`
- `attemptCount`
- `createdAt`
- `updatedAt`
- `retentionDeadline`
- `artifactProfile`

Forbidden persisted fields:

- raw audio bytes
- transcript text
- meeting content
- MediaScribe credentials
- object storage credentials
- signed URLs
- upload tokens
- auth bearer tokens
- passwords

Absolute local paths may be stored only in the private queue file and must be
removed from default diagnostic bundles.

## Local Package Discovery Contract

A local recording package is queueable when:

- `manifest.json` exists and decodes as the current local manifest schema.
- `mic.wav` exists and has non-empty audio payload evidence.
- `incoming.wav` exists and has non-empty audio payload evidence.
- Manifest status is `saved` or another policy-allowed uploadable terminal
  local state.
- `externalEgressStarted=false` in the local manifest before upload begins.

If a package is incomplete, the queue item is `blocked` with
`failureCategory=schemaIncompatibility` or `failureCategory=localResource`.

## Backend Role Mapping Contract

| Local artifact | Local role | Backend track_role |
|----------------|------------|--------------------|
| `mic.wav` | `local_mic` | `microphone` |
| `incoming.wav` | `remote_speaker` / system audio | `system` |
| `manifest.json` | manifest metadata | `manifest` |

The desktop must not send `local_mic` or `remote_speaker` as path values to the
backend `track_role` parameter.

## Server-Mediated Upload Contract

Allowed request sequence:

1. `POST /api/v1/meetings`
2. `POST /api/v1/meetings/{meeting_id}/upload-sessions`
3. `PUT /api/v1/upload-sessions/{session_id}/tracks/{track_role}/parts/{part_number}`
4. `GET /api/v1/upload-sessions/{session_id}/missing-ranges`
5. `POST /api/v1/upload-sessions/{session_id}/finalize`
6. Optional: `POST /api/v1/upload-sessions/{session_id}/abort`
7. Optional: `GET /api/v1/upload-sessions/{session_id}`

Required request behavior:

- Use deterministic idempotency keys for meeting/session creation.
- When bearer authentication is required, send `Authorization: Bearer ...`
  from ephemeral process environment variable
  `TWO_BRAIN_REC_UPLOAD_BEARER_TOKEN`.
- Use `X-Byte-Offset` and `X-Content-SHA256` for part uploads.
- Derive progress from accepted bytes or missing ranges.
- Finalize only after all required track parts are accepted.
- Treat `finalized` as uploaded/ingested, not transcript or summary readiness.

Forbidden request behavior:

- Direct MediaScribe upload.
- Direct object-storage upload.
- Persistent signed URL storage.
- Credential or token logging.
- Reading bearer credentials from UserDefaults or writing them to queue state.

## Retry Contract

Retryable categories:

- `network`
- `unknown` when no server validation failure is known
- `storageQuota` when policy allows retry

Manual-only categories:

- `authSession`
- `serverValidation`
- `schemaIncompatibility`
- `localResource`

Terminal categories:

- explicit user/policy deletion
- non-retryable server rejection
- local package permanently missing after explicit terminal decision

Automatic retries stop at the queue item's `retentionDeadline`.

## UI Contract

The existing recording control surface shows:

- one aggregate queue count;
- most relevant queue item state;
- progress percentage when total bytes are known;
- safe reason text for blocked, degraded, failed, or retrying states;
- one action label: retry, stop retry, recover manually, or none.

The upload queue UI must not cover or replace active recording status or the
one-action Stop control.

## Diagnostic Contract

Allowed diagnostic keys:

- `uploadQueue`
- `uploadQueueItems`
- `uploadAttempt`
- `uploadFailureCategory`
- `uploadReadiness`
- `retentionDeadlines`
- `acceptedBytesByTrack`
- `retryMode`
- `serverTruth`

Forbidden diagnostic fields:

- raw audio
- transcript text
- meeting content
- credentials
- tokens
- signed URLs
- absolute local paths
- MediaScribe credentials
- Langfuse content traces
