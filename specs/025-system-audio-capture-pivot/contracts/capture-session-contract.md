# Contract: Capture Session

## Purpose

Define the local desktop contract for starting, monitoring, stopping, and
finalizing system-audio-first recordings.

## Start Preconditions

Normal accepted recording can start only when:

- microphone permission is `granted`;
- Screen/System Audio permission is `granted`;
- `CaptureScopeApproval` exists for the selected app/window/display;
- local visible recording indicator is available;
- local storage reserve is safe;
- no active recording is already running;
- HAL virtual-device probes are not required.

If any precondition fails, the app must show a specific blocker and recovery
action before writing an accepted artifact.

## Start Event

Required metadata:

- `sessionId`
- `startedAt`
- `initiator`: `user`
- `scopeApprovalId`
- `microphonePermissionState`
- `systemAudioPermissionState`
- `visibleIndicatorState`
- `externalEgressStarted=false`
- `transcriptionStarted=false`

Forbidden metadata:

- raw audio samples;
- transcript text;
- meeting content;
- credentials, tokens, signed URLs, passwords;
- MediaScribe credentials or Langfuse content traces.

## Runtime Health

The app must update metadata-only health for:

- microphone frames and levels;
- incoming/system frames and levels;
- dropped, silent, protected, blocked, or missing incoming frames;
- CPU/memory samples for `coreaudiod`, app, and helpers;
- visible indicator and one-action Stop availability.

## Stop Contract

Stop must:

- be available in one local action while recording is active;
- stop microphone and system-audio capture;
- close `mic.wav` and `incoming.wav`;
- write `manifest.json`;
- release capture resources;
- return CPU below idle gate within 10 seconds or mark validation failed.

## Terminal Outcomes

- `saved`: both tracks present, non-empty, aligned within 3 seconds.
- `degraded`: at least one track is missing, silent, protected, blocked,
  misaligned, or otherwise not acceptable, with a specific reason.
- `blocked`: recording could not start as a normal accepted recording.
- `failed`: capture, writer, permission, CPU gate, or stop/finalization failed.
