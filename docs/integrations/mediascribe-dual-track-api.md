# MediaScribe: v5 canonical WAV and historical dual compatibility

Updated: 2026-07-17

This file keeps its historical name so existing links remain valid. Its active
contract is the v5 single-WAV path below; dual-track behavior is an isolated
compatibility drain for recordings made before v5, not a contract for new
recordings.

## Boundary

- The macOS app never calls MediaScribe and never stores its credentials.
- GRAF's backend worker calls MediaScribe only after GRAF accepts a finalized,
  owner-controlled upload session.
- The server reads the API key from its protected runtime secret. Credentials,
  signed URLs, audio bytes, transcript text, and provider payloads are never
  written to application diagnostics or feature evidence.
- One accepted media revision owns at most one persisted MediaScribe job and
  one durable `Idempotency-Key`.

## Active v5 contract

Every new macOS recording has exactly these final package members:

| Purpose | File | Format | Provider behavior |
|---|---|---|---|
| ASR source | `meeting-transcription.wav` | PCM s16le, mono, 16 kHz | The only audio sent to MediaScribe. |
| Local/server playback | `meeting-review.m4a` | AAC, mono, 48 kHz | Stored for playback only; never sent to MediaScribe. |
| Package metadata | `manifest.json` | JSON | Sent to GRAF's upload API, never to MediaScribe. |

The manifest declares:

- `schema_version=local-recording-manifest.v5`
- `source_kind=initial_mixed_recording`
- `media_scribe_source_mode=single_wav_v1`
- upload roles `manifest`, `media`, and `playback`

The `media` object is immutable after ingest and is the sole processing source.
The playback M4A must be valid for the package to be uploadable, but a playback
failure does not cause it to become an ASR substitute or alter the WAV source.
`meeting-review.m4a` is never sent to MediaScribe.

## Active provider request

The backend makes one request for a v5 revision:

```http
POST /v1/audio/transcriptions
Content-Type: multipart/form-data
X-API-Key: <server-side secret>
```

Multipart fields:

| Field | Value for v5 |
|---|---|
| `file` | `meeting-transcription.wav` with `audio/wav` |
| `diarize` | server-configured boolean |
| `summarize` | server-configured boolean |

The provider request contains no `mic_file`, `incoming_file`, playback field,
M4A filename, user path, or client-supplied filename. A successful response
must have a provider job id. GRAF persists the id before future polling and
imports one ordered result for that job.

Manual uploads use the same v1 single-track endpoint after GRAF has produced
and strictly validated one canonical `manual-media.m4a`. GRAF sends that exact
artifact as `audio/mp4`; the same M4A is the playback artifact when audio
archiving is enabled. Manual upload does not create an intermediate WAV.

The canonical WAV is intentionally continuous from a single shared recording
timeline. Silence and proven discontinuities remain timestamped rather than
being removed or filled to a wall-clock stop time. This preserves transcript
timing without trying to reconstruct separate speakers from two recordings.

## Polling and result import

```http
GET /jobs/{job_id}
GET /jobs/{job_id}/result
X-API-Key: <server-side secret>
```

GRAF accepts provider statuses such as `uploaded`, `transcribing`, `ready`, and
`failed`, maps them to its own durable processing state, and keeps transcript,
diarization, and playback availability distinct. Provider result text is
content-bearing data: it is imported into protected product storage, never
copied into logs, diagnostics, source fixtures, or metadata-only evidence.

## Historical dual compatibility drain

Previously accepted `local-recording-manifest.v3` and `.v4` packages can still
be read and processed when their immutable source kind is
`initial_recording`. Only that historical source kind may use the provider's
dual endpoint and its two stored WAV objects. This compatibility behavior:

- cannot be selected by a new v5 writer, upload session, or UI control;
- cannot be used for `initial_mixed_recording`;
- cannot send `meeting-review.m4a` to ASR; and
- is covered by explicit reader/upload tests separate from v5 tests.

The dual endpoint and worker branch may be retired only after all of the
following metadata-only checks are satisfied: the declared retention window has
passed, there are no queued/retrying historical processing jobs, the bounded
inventory has no retained v3/v4 package needing processing, a deletion and
rollback rehearsal is recorded, and a separate migration/removal change is
approved. Until then, it remains a narrow compatibility path rather than an
active product feature.

## Failure rules

- A v5 media object must parse as the exact PCM WAV contract before any provider
  request. A mislabeled or corrupt object blocks processing.
- A v5 playback M4A never bypasses that validation and never becomes a fallback
  ASR input.
- Missing or mismatched stored objects block the workflow with a safe reason;
  they are not silently replaced with another track.
- If an upload response is lost after egress may have started, GRAF retries
  only the exact same multipart request with the same `Idempotency-Key`, bytes,
  filenames, content types and form parameters. MediaScribe v0.5.3 returns the
  original job for that replay. A new key or a changed request is forbidden.

## Operational privacy rules

- Keep `MEDIASCRIBE_API_KEY` only in the backend secret mechanism; do not
  document any real key, prefix, owner address, or local secret path.
- Do not include raw audio, transcript text, diarization text, job payloads,
  signed URLs, or user-local paths in tickets, test fixtures, logs, screenshots,
  or evidence.
- Store only metadata-safe ids, counts, hashes, state codes, and timestamps in
  operational evidence.
