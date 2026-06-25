# MediaScribe Dual-Track API Contract

Date: 2026-06-03

This document records the server-side MediaScribe contract for future
`2brain Rec` backend transcription work. It intentionally does not contain the
full API key. Store the real key only in server-side secrets as
`MEDIASCRIBE_API_KEY`.

## Boundary

- Desktop clients MUST NOT call MediaScribe directly.
- Desktop clients MUST NOT store MediaScribe credentials.
- `2brain Rec` backend workers call MediaScribe after owner-controlled ingest
  accepts finalized recording artifacts.
- MediaScribe requests, job ids, retention/deletion state, and result imports
  must be represented in backend lifecycle and deletion truth.

## Service

- Production/public base URL: `https://mediascribe.2brain.pro`
- Local development base URL: `http://127.0.0.1:8000`
- External products need only HTTPS API access and an API key. They do not need
  direct access to Postgres, Redis, MinIO, or inference services.

## Authentication

Preferred product-to-product auth:

```http
X-API-Key: <MEDIASCRIBE_API_KEY>
```

Known integration key metadata:

- Owner email: `external-transcription-client@mediascribe.local`
- Owner role: `user`
- Key prefix: `msk_P62tLN6iFMoY`

The full key was provided out of band and verified against `/auth/me` and
`/jobs` on 2026-06-03. Do not commit, log, print, or embed the full key in
application code, specs, diagnostics, screenshots, fixtures, or QA evidence.

Bearer login exists for user-style auth, but `2brain Rec` backend integration
should use `X-API-Key`:

```http
POST /auth/login
Content-Type: application/json
```

```json
{
  "email": "<email>",
  "password": "<password>"
}
```

## Dual-Track Transcription

Endpoint:

```http
POST /v1/audio/transcriptions/dual-track
Content-Type: multipart/form-data
X-API-Key: <MEDIASCRIBE_API_KEY>
```

Multipart fields:

| Field | Required | Type | Notes |
|---|---:|---|---|
| `mic_file` | yes | file | Local microphone track. |
| `incoming_file` | yes | file | Remote/incoming meeting audio; may contain multiple remote speakers. |
| `diarize` | no | bool | Default `false`; use `true` for diarization. |
| `summarize` | no | bool | Default `true`; use `false` when `2brain Rec` owns summaries. |
| `num_speakers` | no | int | Number or upper bound for remote speakers only; allowed only when `diarize=true`. |
| `speaker_count_mode` | no | enum | `exact` or `max`; allowed only when `diarize=true`. |

Recommended request for high-quality dual-track diarization:

```sh
curl -X POST "$MEDIASCRIBE_BASE_URL/v1/audio/transcriptions/dual-track" \
  -H "X-API-Key: $MEDIASCRIBE_API_KEY" \
  -F "mic_file=@/path/mic.wav;type=audio/wav" \
  -F "incoming_file=@/path/incoming.wav;type=audio/wav" \
  -F "diarize=true" \
  -F "summarize=false" \
  -F "speaker_count_mode=max" \
  -F "num_speakers=5"
```

Important:

- `num_speakers` applies only to `incoming_file`; do not include the local
  microphone speaker `MIC` in that count.
- Do not send one mixed file to the dual-track endpoint. It expects exactly two
  files: `mic_file` and `incoming_file`.
- Repeated `POST` creates a new job. There is no `idempotency_key` today, so
  backend workers must persist `job_id` immediately after a successful response
  and must guard retries against duplicate submission.

## Audio File Contract

Preferred upload format to avoid unnecessary conversion:

- Container/extension: `.wav`
- Codec: PCM signed 16-bit little-endian (`pcm_s16le`)
- Channels: mono / 1 channel
- Sample rate: `16000 Hz`

Track alignment rules:

- Both tracks must be continuous from the start of the call.
- Do not remove silence with VAD before submission, because that breaks
  transcript and diarization timestamps.
- If the local microphone is silent, keep silence in `mic_file`.
- `mic_file` and `incoming_file` should share the same `t=0`.
- If one track starts later, pad it with silence so timeline alignment remains
  truthful.

Supported extensions also include `.aac`, `.avi`, `.flac`, `.m4a`, `.mkv`,
`.mov`, `.mp3`, `.mp4`, `.ogg`, `.wav`, and `.webm`, but WAV/PCM mono 16 kHz is
the current recommended contract for quality and minimal server conversion.

## Create Response

`POST /v1/audio/transcriptions/dual-track` returns `202 Accepted`:

```json
{
  "id": "job_abc123",
  "object": "transcription.job",
  "status": "uploaded",
  "source_mode": "dual",
  "source_media": [
    { "role": "mic", "filename": "mic.wav", "content_type": "audio/wav" },
    { "role": "incoming", "filename": "incoming.wav", "content_type": "audio/wav" }
  ],
  "created_at": "2026-06-03T20:00:00+00:00",
  "retrieve_url": "/jobs/job_abc123",
  "result_url": "/jobs/job_abc123/result"
}
```

`retrieve_url` and `result_url` are relative paths. Add the configured base URL.

## Polling

After job creation, persist `id` and poll:

```http
GET /jobs/{job_id}
X-API-Key: <MEDIASCRIBE_API_KEY>
```

Known statuses:

- `uploaded`
- `transcribing`
- `diarizing`
- `summarizing`
- `ready`
- `failed`

Example:

```json
{
  "id": "job_abc123",
  "source_filename": "mic.wav + incoming.wav",
  "content_type": "audio/wav",
  "source_mode": "dual",
  "source_media": [
    { "role": "mic", "filename": "mic.wav", "content_type": "audio/wav" },
    { "role": "incoming", "filename": "incoming.wav", "content_type": "audio/wav" }
  ],
  "diarization_enabled": true,
  "summary_enabled": false,
  "num_speakers": 5,
  "status": "ready",
  "queue_position": null,
  "error_message": null,
  "result_available": true,
  "created_at": "...",
  "updated_at": "..."
}
```

## Result

When `status=ready`:

```http
GET /jobs/{job_id}/result
X-API-Key: <MEDIASCRIBE_API_KEY>
```

Example:

```json
{
  "job": { "...": "..." },
  "transcript": [
    {
      "start": 0.2,
      "end": 1.4,
      "text": "Здравствуйте.",
      "source_role": "mic"
    },
    {
      "start": 0.8,
      "end": 2.1,
      "text": "Добрый день.",
      "source_role": "incoming"
    }
  ],
  "diarization": [
    {
      "start": 0.2,
      "end": 1.4,
      "speaker": "MIC",
      "text": "Здравствуйте.",
      "source_role": "mic"
    },
    {
      "start": 0.8,
      "end": 2.1,
      "speaker": "REMOTE_00",
      "text": "Добрый день.",
      "source_role": "incoming"
    }
  ],
  "summary": null,
  "downloads": {
    "transcript": "/jobs/job_abc123/downloads/transcript",
    "diarization": "/jobs/job_abc123/downloads/diarization",
    "archive": "/jobs/job_abc123/downloads/archive"
  }
}
```

Timing values are seconds. `MIC` is assigned to the microphone track.
`REMOTE_00`, `REMOTE_01`, and later speakers are assigned by diarization on the
incoming track.

## Downloads

Archive:

```sh
curl -L \
  -H "X-API-Key: $MEDIASCRIBE_API_KEY" \
  "$MEDIASCRIBE_BASE_URL/jobs/$JOB_ID/downloads/archive" \
  -o mediascribe-result.zip
```

Available download paths:

- `GET /jobs/{job_id}/downloads/transcript`
- `GET /jobs/{job_id}/downloads/diarization`
- `GET /jobs/{job_id}/downloads/summary`
- `GET /jobs/{job_id}/downloads/archive`

## Errors And Limits

Error shape:

```json
{ "detail": "..." }
```

Common statuses:

| Status | Meaning |
|---:|---|
| `400` | `mic_file` and `incoming_file` are required. |
| `400` | Only audio and video files are supported. |
| `400` | `num_speakers` is only allowed when diarization is enabled. |
| `400` | `speaker_count_mode` is only allowed when diarization is enabled. |
| `400` | `speaker_count_mode` must be `exact` or `max`. |
| `401` | Missing bearer token or `X-API-Key` / invalid API key. |
| `409` | Job result is not ready yet. |
| `409` | Job failed and has no result. |
| `413` | Uploaded file is too large. |

Current public MediaScribe proxy status: large-audio ceiling observed, not a
blocker for large Rec upload packages by itself. As of 2026-06-25,
`mediascribe.2brain.pro` responds with `413 Request Entity Too Large` to
header-only probes with `600 MiB` and `1100 MiB` content lengths. MediaScribe
receives only `mic_file` and `incoming_file`, not the whole Rec upload package
or video file. Raise the MediaScribe OpenResty/nginx request body limit only
when real combined dual-track audio sent to MediaScribe approaches this ceiling.
