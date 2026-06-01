# Contract: Audio Route And Passthrough

## Purpose

Define the expected local audio paths for live call usability.

## Microphone Path

Path:

```text
selected physical microphone
  -> desktop-controlled physical input bridge
  -> shared real-time microphone buffer
  -> 2brain Rec Microphone
  -> meeting target microphone input
```

Rules:

- Remote speaker audio must not be written into the microphone buffer except for
  non-intelligible leakage at least 45 dB below the speaker reference on
  release-ready built-in and wired routes.
- Speaker audio must be available as a reference stream for echo and leakage
  monitoring.
- If microphone frames are unavailable, the virtual microphone may output silence
  but readiness must fail or become degraded after one full 3-second
  stream-health interval.
- Natural user silence with valid microphone frames must not by itself fail
  readiness or degrade capture.
- The path must expose timing, dropout, empty-buffer, capturability, and last
  valid frame evidence to the app.

## Speaker Path

Path:

```text
meeting target speaker output
  -> 2brain Rec Speaker
  -> shared real-time speaker buffer
  -> selected physical speaker
  -> remote speaker capture mirror
```

Rules:

- Speaker path must continue without backend or network availability.
- Speaker path must not depend on upload, transcription, or MediaScribe.
- If speaker output cannot be rendered to the physical device, readiness must
  fail or become degraded.
- If the desktop audio engine or private app I/O is unavailable, the public
  virtual devices must fail closed by becoming hidden or unavailable until route
  recovery and revalidation.

## Capture Mirror

Rules:

- Local microphone and remote speaker evidence must be tracked separately.
- Capture mirror must never be the only proof of live passthrough; the user must
  still hear and speak normally.
- Missing expected track evidence, no valid frames for one full 3-second health
  interval, or repeated empty buffers during expected active stimulus force
  degraded finalization.
- Ordinary user silence with valid frames does not force degraded finalization.

## Safety Rules

- Publication-only virtual devices must not become normal system defaults before
  passthrough is accepted.
- High-frequency driver tracing must be off by default.
- Readiness probes may use bounded synthetic signals, but must not persist raw
  probe audio by default.
