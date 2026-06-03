# Contract: Local Recording Manifest

## Purpose

Define the local metadata file that answers "where is the recording?" without
adding upload, transcription, retention, deletion, or dashboard claims.

## Schema

Required top-level fields:

- `schemaVersion`: must be `local-recording-manifest.v1`
- `sessionId`
- `createdAt`
- `startedAt`
- `stoppedAt`
- `status`: `saved`, `degraded`, or `failed`
- `directoryId`
- `manifestFileName`
- `tracks`
- `externalEgressStarted`: false
- `transcriptionStarted`: false
- `diagnosticSafe`: true

Each track entry requires:

- `trackId`
- `role`: `local_mic` or `remote_speaker`
- `status`: `saved`, `missing`, `degraded`, or `failed`
- `fileName`
- `format`
- `sampleRate`
- `channelCount`
- `durationMs`
- `byteCount`
- `frameCount`
- `failureReason`

## Acceptance Rules

- A manifest is complete only when both required roles are present.
- A `saved` manifest requires both required tracks to be `saved`.
- A `degraded` or `failed` manifest must include a concrete failure reason.
- Manifest paths must be safe basenames or generated ids, not live absolute
  user paths.
- `externalEgressStarted` and `transcriptionStarted` must remain false.

## Forbidden Content

Manifest and diagnostics MUST NOT include raw audio, transcript text, meeting
content, credentials, tokens, signed URLs, passwords, API keys, MediaScribe
payloads, Langfuse content traces, or live secret paths.
