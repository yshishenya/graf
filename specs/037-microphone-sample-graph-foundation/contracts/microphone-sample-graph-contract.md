# Contract: Microphone Sample Graph

## Purpose

Define the app-owned microphone sample source that feeds `mic.wav` through the
existing local recording writer.

## Preconditions

- Recording microphone selection is accepted.
- Microphone permission is granted.
- The app-owned capture source can bind to the selected/default input or prove a
  bounded failure.
- System-audio permission and capture scope are evaluated by the existing `025`
  path.

## Accepted Path

1. Start an app-owned microphone capture source for the resolved input.
2. Deliver floating-point PCM samples through `LocalRecordingSampleSource`.
3. Feed the source into `LocalRecordingWriter.microphoneSampleSourceFactory`.
4. Let `LocalRecordingWriter` produce `mic.wav` using the existing 16 kHz mono
   PCM writer contract.
5. Track metadata-only frame, timing, level, silence, route-change, and failure
   truth.
6. Stop and release the source on Stop, failed start, app quit, or writer
   finalization.

## Success Response

- `streamKind = appOwnedSampleSource`
- `permissionState = granted`
- `frameCount > 0` or a truthful empty/silent state is recorded.
- `failureReason = none` for graph-ready accepted recordings.
- `stoppedAt` is present after finalization.
- Live levels can be read through existing recording level APIs.

## Failure Responses

- No frames: track and stream truth use `no_frames` or a more specific failure.
- Silent input: track and stream truth use `silent_input` when silence is proven.
- Write failure: affected track and manifest use `write_failed`.
- Route change/device loss: stream truth uses `device_unavailable`,
  `capture_failed`, or `unproven` according to observed state.
- Stop/quit interruption: stream is released and final state records `app_closed`
  or another bounded failure instead of invisible capture.
- Legacy recorder fallback: package may exist, but graph readiness is
  `legacyNotReady` or `unproven`.

## Forbidden

- Do not claim echo cancellation, Apple voice processing acceptance, WebRTC AEC3
  acceptance, or clean built-in speakerphone output in this feature.
- Do not write raw diagnostic sample dumps.
- Do not let the capture source continue after Stop/quit.
- Do not hide a failed or wrong-device microphone stream behind a clean
  recording state.
