# Contract: desktop sync-state proof

**Route**: `GET /api/v1/desktop/recordings/{local_recording_id}/sync-state?local_media_revision_id=<id>`

**Compatibility**: additive only. New objects have defaults; old clients ignore unknown keys; new clients treat missing fields as unknown and keep local files.

## Response additions

```json
{
  "playback": {
    "state": "available",
    "can_play": true,
    "reason_code": "canonical_ready",
    "media_revision_id": "00000000-0000-0000-0000-000000000000",
    "local_media_revision_id": "local-recording--initial",
    "object_verified": true,
    "verified_at": "2026-11-16T10:00:00Z",
    "automatic_recovery": false
  },
  "finalized_upload": {
    "session_id": "00000000-0000-0000-0000-000000000000",
    "status": "finalized",
    "media_revision_id": "00000000-0000-0000-0000-000000000000",
    "local_media_revision_id": "local-recording--initial",
    "archive_audio": true,
    "finalized_at": "2026-11-16T09:00:00Z"
  },
  "meeting": {
    "retention": {
      "delete_after": "2027-11-16T09:00:00Z",
      "policy_state": "active"
    }
  }
}
```

## Field semantics

- `playback.media_revision_id` is the server UUID of the actual revision playback serves. `playback.local_media_revision_id` is the local revision string the desktop compares with `item.localMediaRevisionId`. Both may describe an older pinned revision.
- `playback.object_verified=true` only when the canonical playback artifact for that revision exists, `stat.size == artifact.byte_length`, and a bounded read probe (first 12–64 KiB) succeeds within the request timeout.
- `playback.verified_at` is the server UTC time of this response check, not `TrackArtifact.validated_at`.
- `finalized_upload.media_revision_id` must equal `playback.media_revision_id`. `archive_audio/finalized_at` come from the latest `FINALIZED` upload session for that same revision. If both local revision IDs are present, they must match each other and the item. Null/missing means unknown; the client keeps local files. `upload_session` remains the active upload session only and is never mixed with finalized custody.
- `meeting.retention.delete_after` is the effective deadline: explicit column or `started_at + retention_meeting_delete_after_days`. Null means unknown, never forever.

## Fail-closed mapping

| Condition | playback | archive/finalized | retention |
|---|---|---|---|
| No playback revision | `unavailable/no_audio` | unchanged | unchanged |
| No finalized session | `preparing/reconciliation_pending` | `finalized_upload=null` | unchanged |
| `archive_audio=false` | `unavailable/audio_not_archived`, `can_play=false` | `finalized_upload.archive_audio=false`, `finalized_at` set | unchanged |
| Object missing | `preparing/canonical_artifact_missing`, `object_verified=false` | unchanged | unchanged |
| Size mismatch | same as missing | unchanged | unchanged |
| Storage stat error/timeout | `preparing/reconciliation_pending`, `automatic_recovery=true` | unchanged | unchanged |
| Bounded read fails | `preparing/reconciliation_pending`, `object_verified=false` | unchanged | unchanged |
| Normalization terminal | `unavailable/<terminal reason>`, `automatic_recovery=false` | unchanged | unchanged |
| Deletion active | `deleting`/`deleted`, `can_play=false` | unchanged | unchanged |
| Access denied | `unavailable/access_denied`, `can_play=false` | unchanged | unchanged |
| Retention unsafe | unchanged | unchanged | `unsafe/blocked/expired`, keep local |

## Headers

`Cache-Control: no-store`.

## Read-side exception

The existing idempotent upload-session expiry reconciliation may update an expired session during this GET. It must not delete meetings, objects or local files; the dry-run contract forbids destructive server mutations.

## Non-goals

- No object key, signed URL, ETag or local path in the new proof fields. Existing revision `manifest_sha256`/`track_sha256_by_role` fields remain for compatibility and are not part of the proof.
- No change to cabinet `PlaybackPreparationState`.
- No durable `object_verified` column; it is per-response evidence.
