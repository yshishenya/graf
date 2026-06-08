# Contract: Dual-Track Manifest

## Required Files

Accepted or degraded recording packages use:

- `manifest.json`
- `mic.wav`
- `incoming.wav`

Both WAV files must be normalized to the existing local artifact expectation:
PCM signed 16-bit little-endian, mono, 16000 Hz, unless a later spec explicitly
changes the backend contract.

## Required Manifest Fields

Top-level fields:

- `schemaVersion`
- `sessionId`
- `directoryId`
- `status`: `saved`, `degraded`, `blocked`, `failed`
- `startedAt`
- `stoppedAt`
- `durationDifferenceSeconds`
- `transcriptionReadiness`
- `mediaScribeSourceMode`: `dual`
- `externalEgressStarted`: `false`
- `transcriptionStarted`: `false`
- `diagnosticSafe`: `true`
- `scopeApproval`
- `permissions`
- `tracks`
- `captureHealth`

Track fields:

- `trackId`
- `role`: existing backend-compatible audio track role: `localMic`,
  `remoteSpeaker`
- `sourceKind`: `microphone`, `systemAudio`
- `fileName`: `mic.wav` or `incoming.wav`
- `status`: `saved`, `missing`, `degraded`, `blocked`, `failed`
- `format`
- `sampleRate`
- `channelCount`
- `bitsPerSample`
- `durationMs`
- `byteCount`
- `frameCount`
- `timelineStartMs`
- `timelineAligned`
- `failureReason`

## Failure Reasons

Allowed failure reasons:

- `none`
- `permissionDenied`
- `scopeUnavailable`
- `protectedAudioBlocked`
- `silentInput`
- `noFrames`
- `emptyRequiredTrack`
- `timelineMisaligned`
- `captureFailed`
- `cpuGateFailed`
- `stoppedBeforeFrames`
- `halProbeObserved`

## Acceptance Rules

- `status=saved` requires both tracks `status=saved`.
- `status=saved` requires `durationDifferenceSeconds <= 3`.
- `status=saved` requires `scopeApproval` and both permissions granted.
- Any missing, protected, blocked, silent, empty, or misaligned incoming track
  must produce `degraded`, `blocked`, or `failed`, not `saved`.
- `externalEgressStarted` and `transcriptionStarted` must remain `false` in
  this feature.
- The incoming/system-audio file must keep the existing `remoteSpeaker` role
  and `incoming.wav` mapping so local artifacts remain compatible with the
  current dual-track backend and MediaScribe contract.
