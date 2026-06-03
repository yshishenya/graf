# Contract: MediaScribe-Ready Recording Artifact

## Purpose

Define the local artifact package that future backend upload/ingest can submit
to MediaScribe's dual-track endpoint without guessing roles or converting basic
track format.

## Required Package Contents

```text
<recording-directory>/
├── manifest.json
├── mic.wav
└── incoming.wav
```

## Manifest Requirements

Required manifest fields:

- `schemaVersion`
- `sessionId`
- `createdAt`
- `startedAt`
- `stoppedAt`
- `status`
- `directoryId`
- `manifestFileName`
- `transcriptionReadiness`
- `mediaScribeSourceMode`: `dual`
- `tracks`
- `externalEgressStarted`: `false`
- `transcriptionStarted`: `false`
- `diagnosticSafe`: `true`
- `failureReason`

Each track requires:

- `trackId`
- `role`: `local_mic` or `remote_speaker`
- `mediaScribeField`: `mic_file` or `incoming_file`
- `status`
- `fileName`
- `format`: `wav-pcm-s16le`
- `sampleRate`: `16000`
- `channelCount`: `1`
- `bitsPerSample`: `16`
- `durationMs`
- `byteCount`
- `frameCount`
- `timelineStartMs`
- `timelineAligned`
- `failureReason`

## Acceptance Rules

- A ready package requires exactly one `local_mic` track and one
  `remote_speaker` track.
- `local_mic` maps to MediaScribe `mic_file`.
- `remote_speaker` maps to MediaScribe `incoming_file`.
- Both ready tracks must be WAV `pcm_s16le`, mono, 16000 Hz.
- Both ready tracks must preserve the same session timeline.
- `externalEgressStarted` and `transcriptionStarted` must remain `false`.
- A package that cannot satisfy the format/timeline contract must be
  `degraded`, `failed`, or `legacy_not_ready`, never `ready`.

## Forbidden Content

Manifest and diagnostics MUST NOT include raw audio, transcript text, meeting
content, credentials, tokens, signed URLs, passwords, API keys, MediaScribe
secret values, Authorization headers, or live absolute user paths.
