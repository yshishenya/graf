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

- Remote speaker audio must not be written into the microphone buffer.
- If microphone frames are unavailable, the virtual microphone may output silence
  but readiness must fail or become degraded.
- The path must expose timing/dropout evidence to the app.

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

## Capture Mirror

Rules:

- Local microphone and remote speaker evidence must be tracked separately.
- Capture mirror must never be the only proof of live passthrough; the user must
  still hear and speak normally.
- Missing expected track evidence forces degraded finalization.

## Safety Rules

- Publication-only virtual devices must not become normal system defaults before
  passthrough is accepted.
- High-frequency driver tracing must be off by default.
- Readiness probes may use bounded synthetic signals, but must not persist raw
  probe audio by default.
