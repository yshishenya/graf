# Contract: Desktop Sync And Upload

Date: 2026-06-18

## Scope

Defines how the macOS app records offline, persists upload state, reconciles
with server truth, resumes upload, and opens review after processing. This is a
contract for `042`; it does not implement edit, trim, video, replace, restore,
or transcript editing flows.

## Local Queue Schema

`DesktopUploadQueueDocument.schemaVersion` MUST become
`desktop-upload-queue.v2`.

Each item MUST include:

- `id`
- `sessionId`
- `directoryId`
- `localMediaRevisionId`
- `meetingId`
- `mediaRevisionId`
- `uploadSessionId`
- `state`
- `failureCategory`
- `failureReason`
- `retryMode`
- `attemptCount`
- `nextRetryAt`
- `retentionDeadline`
- `artifactProfile`
- `serverTruth`
- `syncGeneration`
- `lastReconciledAt`
- `syncConflictState`
- `retryRecords`
- `retentionDecision`

Migration:

- v1 queue items migrate by assigning
  `localMediaRevisionId = "<directoryId>--initial"`.
- Missing `mediaRevisionId` remains null until server reconciliation or upload
  finalization.

## Server Reconciliation Endpoint

The desktop client SHOULD reconcile before upload attempt, on app launch, on
manual retry, and when opening the queue.

```http
GET /api/v1/desktop/recordings/{local_recording_id}/sync-state?local_media_revision_id={id}
```

Response `200`:

```json
{
  "local_recording_id": "recording-dir-id",
  "local_media_revision_id": "recording-dir-id--initial",
  "meeting": {
    "meeting_id": "uuid",
    "status": "uploading",
    "processing_status": "not_submitted",
    "deletion_state": "none",
    "access_state": "owner"
  },
  "media_revision": {
    "media_revision_id": "uuid",
    "revision_number": 1,
    "status": "uploading",
    "manifest_sha256": "hex-or-null",
    "track_sha256_by_role": {}
  },
  "upload_session": {
    "session_id": "uuid-or-null",
    "status": "uploading",
    "accepted_bytes_by_track": {
      "microphone": 0,
      "system": 0,
      "manifest": 0
    },
    "desktop_truth_rule": "server_ranges_authoritative"
  },
  "processing": {
    "status": "not_submitted",
    "workflow_id": null,
    "reason_code": null
  },
  "review": {
    "available": false,
    "web_url": "/meetings/uuid",
    "desktop_url": "/desktop/meetings/uuid"
  },
  "conflict": {
    "state": "none",
    "reason": null,
    "next_action": "continue_upload"
  }
}
```

Response `404`:

- Means the server has no known meeting for this local recording/revision.
- Desktop MAY create the meeting/upload session if local policy allows.

Response `403`:

- Means access is denied or revoked.
- Desktop MUST NOT re-upload automatically.

Response `409`:

- Means server metadata conflicts with local immutable revision truth.
- Desktop MUST enter a visible manual-only conflict state.

## Upload Resume Rules

- Client MUST ask for server truth when `meetingId`, `mediaRevisionId`, or
  `uploadSessionId` already exists locally.
- Server accepted bytes/ranges are authoritative.
- Client MUST send only missing or rejected ranges.
- Each part MUST include byte offset and checksum.
- Repeated part with same offset/checksum is idempotent.
- Repeated part with same part number but different offset/checksum is conflict.
- Finalize MUST fail if required ranges or track descriptors do not match.

## Desktop Review Link Rules

- A review link is available only when server truth has `meetingId`.
- Uploaded/ready meetings open `/desktop/meetings/{meeting_id}` in the embedded
  cabinet.
- Local-only or blocked items show queue status and next action, not fake
  review availability.
- Processing failures keep upload success separate from transcript failure.

## Forbidden Content

The desktop sync contract MUST NOT expose:

- raw audio bytes in logs/evidence;
- transcript text in diagnostics;
- MediaScribe credentials;
- MinIO credentials or signed object URLs;
- bearer tokens;
- private local filesystem paths outside local app state.
