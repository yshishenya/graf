# MediaScribe Client Contract

## Boundary

- Only 2brain Rec server workers call MediaScribe.
- Desktop clients never call MediaScribe, hold MediaScribe credentials, or
  receive MediaScribe signed URLs.
- MediaScribe credentials are loaded from server-side secret configuration.

## Submit Request

Endpoint:

```http
POST /v1/audio/transcriptions/dual-track
X-API-Key: <server-side secret>
Content-Type: multipart/form-data
```

Fields:

| Field | Required | Source |
|---|---:|---|
| `mic_file` | yes | Stored `TrackArtifact` with role `microphone` |
| `incoming_file` | yes | Stored `TrackArtifact` with role `system` / incoming audio |
| `diarize` | yes | `true` |
| `summarize` | yes | `false` unless a later accepted feature changes summary ownership |
| `speaker_count_mode` | optional | `max` when configured |
| `num_speakers` | optional | Remote speaker upper bound only |

Rules:

- Do not submit a mixed file.
- Do not strip silence or alter timing before submit.
- Persist accepted `job_id` before any retry can continue.

## Accepted Response

```json
{
  "id": "job_abc123",
  "status": "uploaded",
  "source_mode": "dual",
  "retrieve_url": "/jobs/job_abc123",
  "result_url": "/jobs/job_abc123/result"
}
```

Persist:

- `external_job_id`
- accepted status
- submit timestamp
- request settings
- source artifact ids and checksums

Do not persist or expose:

- API key value
- signed dependency URL
- local private file path
- raw transcript content in job metadata

## Polling Status Mapping

| MediaScribe Status | 2brain Rec Processing Status |
|---|---|
| `uploaded` | `submitted` / `polling` |
| `transcribing` | `polling` |
| `diarizing` | `polling` |
| `summarizing` | `polling` with summary dependency awareness |
| `ready` | `importing` then `processed` after import |
| `failed` | `failed_terminal` unless retry policy classifies safe retry |
| unknown/malformed | `failed_retryable` until retry budget ends |

## Result Mapping

`transcript[]` imports into `TranscriptSegment`.

`diarization[]` imports into `DiarizationSegment`.

`summary` updates summary dependency state but does not become 2brain notes in
this feature.

`downloads` may be recorded as dependency availability metadata only. Do not
expose public or client-visible download URLs in `015`.

## Error Handling

| Error | Behavior |
|---|---|
| Missing credentials | `blocked_config`, no request sent |
| 401 | terminal failure with `mediascribe_auth_failed` |
| 400 | terminal failure with safe validation reason |
| 409 result not ready | keep polling |
| 409 failed job | terminal failure |
| 413 | terminal failure with `mediascribe_payload_too_large` |
| 429 / 5xx / timeout | retryable with bounded backoff |

All problem details and logs must redact credentials, transcript text, raw
audio, signed URLs, and private paths.
