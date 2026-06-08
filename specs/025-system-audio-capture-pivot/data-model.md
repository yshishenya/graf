# Data Model: System Audio Capture Pivot

## SystemAudioCaptureSession

Represents one incoming/system-audio capture stream.

Fields:

- `sessionId`: Stable local capture session ID.
- `permissionState`: `unknown`, `granted`, `denied`, `restricted`, `stale`.
- `scopeApprovalId`: Link to `CaptureScopeApproval`.
- `scopeKind`: `application`, `window`, `display`.
- `sourceDisplayName`: User-facing selected scope label.
- `startedAt`: Wall-clock timestamp when stream starts.
- `stoppedAt`: Wall-clock timestamp when stream stops.
- `monotonicStartMs`: Monotonic start timestamp.
- `monotonicStopMs`: Monotonic stop timestamp.
- `sampleRate`: Captured sample rate before normalization.
- `channelCount`: Captured channel count before normalization.
- `frameCount`: Captured incoming frame count.
- `droppedFrameCount`: Dropped or invalid audio frames.
- `silentFrameCount`: Frames below silence threshold.
- `protectedFrameCount`: Frames reported or inferred as protected/blocked.
- `lastFrameAt`: Last incoming audio frame timestamp.
- `failureReason`: `none`, `permissionDenied`, `scopeUnavailable`,
  `protectedAudioBlocked`, `silentInput`, `noFrames`, `captureFailed`,
  `cpuGateFailed`, `stoppedBeforeFrames`.

Validation rules:

- Accepted recordings require `permissionState=granted`.
- Accepted recordings require a linked approved `CaptureScopeApproval`.
- `noFrames`, `protectedAudioBlocked`, and `silentInput` must create degraded or
  blocked manifest status, not `saved` success.

## MicrophoneCaptureSession

Represents one local microphone capture stream.

Fields:

- `sessionId`: Stable local capture session ID.
- `permissionState`: `unknown`, `granted`, `denied`, `restricted`, `stale`.
- `inputDeviceId`: Stable local device identifier when available.
- `inputDisplayName`: User-facing device label.
- `startedAt`, `stoppedAt`, `monotonicStartMs`, `monotonicStopMs`.
- `sampleRate`, `channelCount`, `frameCount`.
- `droppedFrameCount`, `silentFrameCount`.
- `lastFrameAt`.
- `failureReason`: `none`, `permissionDenied`, `deviceUnavailable`,
  `silentInput`, `noFrames`, `captureFailed`, `cpuGateFailed`.

Validation rules:

- Normal accepted recording requires `permissionState=granted`.
- Missing microphone permission blocks normal recording before artifact success.
- A degraded attempt must be labeled before start and in the manifest.

## CaptureScopeApproval

Records why a system-audio scope is eligible for meeting recording.

Fields:

- `scopeApprovalId`: Stable local ID.
- `scopeKind`: `application`, `window`, `display`.
- `sourceDisplayName`: User-facing label.
- `approvedBy`: `user`.
- `approvedAt`: Wall-clock approval timestamp.
- `approvalMode`: `manualSelection`, `userConfirmedSuggestedScope`.
- `eligibleReason`: `approvedMeetingApp`, `approvedBrowserMeeting`,
  `manualMeetingScope`.
- `notTriggerForBackgroundAudio`: Always `true` for MVP.

Validation rules:

- Accepted recording requires this record.
- Background audio without a scope approval cannot start or accept a meeting
  recording.

## DualTrackRecordingPackage

Local artifact directory for one recording.

Fields:

- `directoryId`
- `sessionId`
- `manifestFileName`: `manifest.json`
- `micFileName`: `mic.wav`
- `incomingFileName`: `incoming.wav`
- `status`: `saved`, `degraded`, `blocked`, `failed`
- `transcriptionReadiness`: `ready`, `degraded`, `blocked`, `notReady`
- `mediaScribeSourceMode`: `dual`
- `externalEgressStarted`: `false` in this feature
- `transcriptionStarted`: `false` in this feature
- `diagnosticSafe`: `true`
- `scopeApproval`
- `microphoneSession`
- `systemAudioSession`
- `captureHealthSnapshot`

Validation rules:

- `saved` requires both tracks present, non-empty, and aligned within 3 seconds.
- `degraded` requires a specific missing/degraded track reason.
- `blocked` or `failed` must not be presented as accepted success.

## CaptureHealthSnapshot

Metadata-only runtime stability and track health evidence.

Fields:

- `recordingSessionId`
- `phase`: `idle`, `activeRecording`, `stop`, `quit`
- `sampledAt`
- `coreaudiodCpuPercent`
- `appCpuPercent`
- `helperCpuPercent`
- `memoryMb`
- `durationDifferenceSeconds`
- `micFrameCount`
- `incomingFrameCount`
- `droppedFrameCount`
- `silentFrameCount`
- `protectedFrameCount`
- `halProbeObserved`: `false` required for MVP acceptance.
- `gateStatus`: `passed`, `degraded`, `failed`
- `failureReason`

Validation rules:

- Idle passes only when `coreaudiodCpuPercent < 5` and `appCpuPercent < 5`
  after a 10-second settle window.
- Active recording fails on sustained `coreaudiodCpuPercent > 10` or sustained
  `appCpuPercent + helperCpuPercent > 25`.
- `halProbeObserved=true` fails MVP validation.

## State Transitions

```text
idle
  -> permissionBlocked
  -> scopeRequired
  -> ready
  -> recording
  -> stopping
  -> saved
  -> degraded
  -> failed

recording
  -> degraded (missing/protected/silent incoming audio)
  -> stopping
  -> failed (capture/file/CPU gate failure)

stopping
  -> saved
  -> degraded
  -> failed
```
