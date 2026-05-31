# Contract: Live Passthrough

## Purpose

Define the local app/driver behavior required for non-recording bidirectional
passthrough.

## Preconditions

- HAL bundle is installed and loaded.
- `2brain Rec Microphone` and `2brain Rec Speaker` are visible while app
  heartbeat is fresh.
- User selected non-2brain physical microphone and output devices.
- Microphone and speaker route readiness passed.

## Required Behavior

- Physical microphone frames are delivered to `2brain Rec Microphone`.
- Audio written by a meeting app to `2brain Rec Speaker` is played through the
  selected physical output.
- App heartbeat is refreshed while app-side route engine is available.
- Missing/stale heartbeat hides or removes public devices within 5 seconds.
- Route/device/browser/coreaudiod changes mark passthrough stale within 5
  seconds.

## Prohibited Behavior

- Starting recording, transcript-only capture, upload, MediaScribe, Langfuse, or
  server workflow.
- Writing raw audio into diagnostics by default.
- Self-routing virtual devices into physical-device selections.
- Copying Krisp UI, copy, assets, binaries, or proprietary behavior.

## Evidence

- Route status and failure category.
- Selected physical/virtual device names and identifiers.
- Heartbeat freshness.
- Latency and leakage measurements.
- Recovery action.

Raw audio, transcript text, credentials, tokens, signed URLs, and meeting
content are forbidden in default evidence.
