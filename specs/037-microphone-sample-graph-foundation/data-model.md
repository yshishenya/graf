# Data Model: Microphone Sample Graph Foundation

## RecordingMicrophoneSelection

Represents the input selected for the app-owned microphone stream.

### Fields

- `selectionId`: Stable local identifier for this selection decision.
- `mode`: `userSelected` or `macOSDefaultFallback`.
- `inputDeviceId`: Native input identifier when available.
- `inputDisplayName`: User-facing input name when available.
- `deviceClass`: Existing `PhysicalDeviceClass` or `unknown`.
- `workingDeviceKind`: Existing physical/virtual/aggregate classification when
  available.
- `selectionResult`: `accepted`, `rejected`, or `unavailable`.
- `rejectionReason`: Metadata-safe reason code for rejected/unavailable inputs.
- `resolvedAt`: Time selection was resolved for recording.
- `diagnosticSafe`: Always `true`.

### Validation Rules

- `userSelected` requires a non-empty `inputDeviceId` and `inputDisplayName`.
- `macOSDefaultFallback` requires metadata stating that no explicit selection
  was active.
- 2brain virtual devices and unsupported self-routing inputs must be rejected
  before capture starts.
- If a previously selected device is unavailable at start, the result is
  `unavailable` and recording must fail closed or require explicit fallback
  confirmation by product policy.
- Selection metadata must not include private local paths, participant names, or
  raw audio evidence.

## AppOwnedMicrophoneStreamSession

One microphone stream attempt tied to a local recording session.

### Fields

- `sessionId`: Recording session identifier.
- `selection`: `RecordingMicrophoneSelection`.
- `permissionState`: Existing `CapturePermissionState`.
- `streamKind`: `appOwnedSampleSource` or `legacyRecorderFallback`.
- `startedAt`, `stoppedAt`: Wall-clock timestamps.
- `monotonicStartMs`, `monotonicStopMs`: Recording-relative monotonic offsets.
- `sampleRate`: Captured sample rate before writer normalization.
- `channelCount`: Captured channel count before writer normalization.
- `writerSampleRate`: Expected `16000` for accepted `mic.wav`.
- `writerChannelCount`: Expected `1` for accepted `mic.wav`.
- `frameCount`: Frames delivered to the app-owned sample source.
- `droppedFrameCount`: Frames dropped before writer consumption, when known.
- `silentFrameCount`: Frames classified as silent by metadata-only level logic.
- `clippedFrameCount`: Frames classified as clipped, when known.
- `routeChangeCount`: Number of observed input-route changes during capture.
- `lastFrameAt`: Last metadata timestamp for delivered frames.
- `failureReason`: Existing `LocalRecordingFailureReason`.
- `diagnosticSafe`: Always `true`.

### Validation Rules

- Accepted `037` graph readiness requires `streamKind =
  appOwnedSampleSource`, `permissionState = granted`, `frameCount > 0`,
  selected/default input identity, and `failureReason = none`.
- `legacyRecorderFallback` cannot prove graph readiness and must be represented
  as degraded, unproven, or `legacy_not_ready` for future cleanup readiness.
- `stoppedAt` must be present after Stop/quit/failure finalization.
- Route-change, device-loss, and no-frame cases must not become clean saved
  graph-readiness evidence.
- Stream metadata must not store raw sample payloads.

## MicrophoneStreamHealth

Metadata-only health summary for diagnostics, manifest, and validation.

### Fields

- `gateStatus`: Existing `CaptureHealthGateStatus`.
- `failureReason`: Existing `LocalRecordingFailureReason`.
- `framesObserved`: Boolean derived from `frameCount > 0`.
- `timingConfidence`: `usable`, `degraded`, `missing`, or `unknown`.
- `silenceStatus`: `audible`, `silent`, `clipped`, `notMeasured`, or
  `unknown`.
- `lastLevel`: Normalized `0...1` level value when measured.
- `lastLevelAt`: Time the level was updated.
- `cleanupReadiness`: `readyForFutureProcessing`, `unproven`,
  `legacyNotReady`, or `blocked`.
- `evidenceCodes`: Bounded metadata-safe reason codes.

### Validation Rules

- `readyForFutureProcessing` requires app-owned stream evidence and accepted
  package compatibility.
- `legacyNotReady` is required when the old recorder path produced `mic.wav`.
- `blocked` is required for permission denial or unsupported selection before
  capture starts.
- `unproven` is required when stream identity, frames, timing, or finalization
  cannot be proven.

## LocalRecordingManifest Extensions

The existing `LocalRecordingManifest` remains the package source of truth.
`037` may extend it with optional microphone stream metadata while preserving
backward-compatible decoding.

### Fields To Add Or Populate

- `microphoneSelection`: Optional `RecordingMicrophoneSelection`.
- `microphoneStream`: Optional `AppOwnedMicrophoneStreamSession`.
- `microphoneStreamHealth`: Optional `MicrophoneStreamHealth`.
- Existing `tracks`: Continue to include exactly one `localMic` original track
  and one `remoteSpeaker` original track for accepted local packages.
- Existing `captureHealth`: Continue to summarize package-level recording
  health and failure truth.
- Existing `leakageFinalization`: Continue to own `clean`,
  `leakage_detected`, `unproven`, `not_measured`, and related transcription gate
  semantics.

### Validation Rules

- Accepted package compatibility still requires `mic.wav`, `incoming.wav`,
  `manifest.json`, dual source roles, 16 kHz mono PCM WAV readiness, and
  `durationDifferenceSeconds <= 3`.
- Graph readiness is additional metadata and must not override leakage
  finalization.
- A recording can have healthy microphone stream metadata and still be blocked
  for transcription by leakage finalization.
- Diagnostics and manifest fields must stay metadata-only.

## FutureProcessingReadiness

Bounded state that tells later `038` and `039` planning whether the recording
has enough microphone/input truth to evaluate Apple voice processing or WebRTC
AEC.

### Values

- `readyForFutureProcessing`: App-owned microphone stream, selected/default
  input identity, frame/timing evidence, and compatible incoming reference are
  present.
- `unproven`: Required stream or incoming reference truth is missing/degraded.
- `legacyNotReady`: Package used legacy recorder fallback for local mic.
- `blocked`: Permission, unsupported selection, or device availability blocked
  stream capture.

### Validation Rules

- Future readiness is not transcription readiness.
- Future readiness is not a clean speakerphone claim.
- Future readiness must be derivable from manifest metadata without reading raw
  audio samples.
