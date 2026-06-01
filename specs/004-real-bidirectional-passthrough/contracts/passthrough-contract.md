# Contract: Live Passthrough

## Purpose

Define the local app/driver behavior required for non-recording bidirectional
passthrough.

## Preconditions

- HAL bundle is installed and loaded.
- `2brain Rec Microphone` and `2brain Rec Speaker` are published for Core Audio
  enumeration in default safe mode, but live route acceptance requires fresh app
  heartbeat and measured route evidence.
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
- Default app launch does not start the app-side live bridge or write app-I/O
  heartbeat unless a controlled live passthrough experiment or accepted route
  start explicitly enables it.
- Realtime audio callbacks do not allocate heap memory, format strings, access
  wall-clock time, write files, or emit diagnostics directly.
- Synthetic policy checks are labeled as synthetic and cannot be used as
  physical/browser live audio acceptance evidence.

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

## Shared Ring-Buffer Contract

The app/driver shared-memory rings are single-producer/single-consumer buffers.
Each direction has exactly one writer and one reader:

- microphone ring: app bridge writes, HAL microphone device reads;
- speaker ring: HAL speaker device writes, app bridge reads;
- capture mirror ring: HAL speaker device writes, diagnostics/capture readers
  read metadata-safe evidence.

Required behavior:

- Writer owns only the write index.
- Reader owns only the read index.
- Writer MUST NOT advance or rewrite the reader-owned read index to make room.
- A write is all-or-nothing. If `count` samples do not fit, the write returns
  `false`, leaves both indices unchanged, and the caller records drop/degraded
  evidence outside the realtime callback.
- A zero-length write returns `true` and leaves indices unchanged.
- A null-source write returns `false` and leaves indices unchanged.
- A write larger than ring capacity returns `false`; callers must chunk, resample,
  or drop before writing.
- A read may return fewer samples than requested. Partial reads are underrun
  evidence; release code must not stretch partial audio to pretend the route is
  healthy.
- Memory ordering must publish samples before the write index advances and must
  observe the write index before reading samples.

This contract intentionally prefers explicit drops/underruns over producer-side
overwrite. It keeps ownership clear across Swift and C++ and avoids races where
the producer changes the consumer index while the consumer is reading.
