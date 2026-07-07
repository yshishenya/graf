# One-Track Media Upload Contract

## Public API: Create Manual Media Upload

```http
POST /api/v1/media-uploads
Authorization: Bearer <session> OR legacy test headers
Content-Type: multipart/form-data
```

Fields:

| Field | Required | Notes |
|---|---:|---|
| `file` | yes | One audio or video file. |
| `title` | no | Safe meeting title, same metadata policy as meeting create. |
| `duration_seconds` | yes | Positive approximate duration for existing ingest limits. |
| `local_recording_id` | no | Client-provided idempotency identity; generated if omitted. |

Response: `202 Accepted`

```json
{
  "meeting": {
    "meeting_id": "00000000-0000-0000-0000-000000000000",
    "status": "ingested_pending_processing",
    "processing_status": "workflow_started"
  },
  "upload_session": {
    "status": "finalized",
    "expected_tracks": ["manifest", "media"]
  },
  "workflow_started": true,
  "request_mode": "single_track"
}
```

Rules:

- The endpoint accepts exactly one media file.
- The endpoint reuses existing upload limits and storage behavior.
- Responses never expose object keys, dependency URLs, MediaScribe job ids, raw
  transcript text, or private local paths.

## Existing Upload Session Contract Extension

Existing upload sessions may accept this track set:

```json
{
  "expected_tracks": ["manifest", "media"]
}
```

Finalize accepts matching descriptors:

```json
{
  "manifest_sha256": "<sha256>",
  "tracks": [
    {"track_role": "manifest", "...": "..."},
    {"track_role": "media", "...": "..."}
  ]
}
```

Rules:

- `["manifest", "microphone", "system"]` remains the dual-track desktop path.
- `["manifest", "media"]` is the manual one-track path.
- Mixed sets such as `["manifest", "media", "system"]` are rejected.

## MediaScribe One-Track Request

```http
POST /v1/audio/transcriptions
X-API-Key: <server-side secret>
Content-Type: multipart/form-data
```

Fields:

| Field | Required | Source |
|---|---:|---|
| `file` | yes | Stored manual media artifact bytes. |
| `diarize` | yes | Existing configuration default. |
| `summarize` | yes | Existing configuration default. |

Mapping:

- `request_mode`: `single_track`
- source artifact: `track_role=media`
- transcript source role fallback: `media`
- dependency failures: existing MediaScribe safe reason codes.

## Dual-Track Regression Contract

Existing dual-track jobs still call:

```http
POST /v1/audio/transcriptions/dual-track
```

with `mic_file` and `incoming_file` only. They must not use the single `file`
field.
