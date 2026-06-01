# Research: macOS Live Audio Passthrough

## Decision 1: Keep HAL Thin, Run Physical-Device Passthrough From Visible App Control

**Decision**: Use the HAL virtual devices for meeting-facing input/output and
shared real-time buffers, while the desktop app owns physical-device selection,
permission prompts, readiness probes, and starting/stopping the local physical
audio bridge.

**Rationale**: macOS microphone permission, user-visible readiness, diagnostics,
and recovery belong in the app. The HAL bundle must stay small, deterministic,
and free of policy, prompts, network, or UI behavior.

**Alternatives considered**:

- Driver starts physical-device IO itself: rejected because it hides permission
  and device-selection behavior inside a privileged/hosted component.
- App-only audio capture without virtual devices: rejected by constitution and
  product scope; it would not provide browser-independent routing.

## Decision 2: Ready Requires Audio Movement, Not Device Visibility

**Decision**: The app can show installed/visible when Core Audio lists both
virtual devices, but can show ready only after user-triggered microphone and
speaker checks produce route evidence.

**Rationale**: The current bug class is exactly "devices visible, not usable."
Readiness must be tied to actual audio movement and invalidated after route
changes.

**Alternatives considered**:

- Treat Core Audio publication as ready: rejected because it can silently break
  calls.
- Let browser meeting validation be the only readiness test: rejected because the
  user needs a pre-call local check.

## Decision 3: Proof Devices Must Stay Safe Until Passthrough Is Accepted

**Decision**: Publication-only proof devices must not become system default
devices, and verbose HAL callback trace must be opt-in.

**Rationale**: Before real passthrough, selecting the virtual speaker as normal
macOS output can make the user lose sound. High-frequency callback logging can
also overload `coreaudiod`.

**Alternatives considered**:

- Let users select proof devices freely: rejected until live passthrough works.
- Always-on trace: rejected because audio callbacks are high frequency and must
  remain real-time safe.

## Decision 4: Readiness Check May Use Short Local Signals But Must Not Capture Hidden Meeting Content

**Decision**: The readiness check may generate short local test signals and
measure buffer movement, but it must not start meeting recording, upload audio,
or store raw audio content.

**Rationale**: Speaker path proof requires a known stimulus. The check must be
obvious, bounded, and local to preserve consent and trust.

**Alternatives considered**:

- Passive check only: rejected because silence can be ambiguous.
- Store probe audio for diagnostics: rejected; diagnostics should store statuses
  and metrics, not raw audio.

## Decision 5: Browser Validation Remains A Release Gate

**Decision**: Local readiness can unlock internal testing, but release readiness
requires real browser meeting evidence on the approved browser matrix.

**Rationale**: Browser audio device behavior differs from synthetic local tests.
The product promise is meeting capture, so browser validation must remain an
explicit gate.

**Alternatives considered**:

- Rely only on synthetic route harnesses: rejected because they do not prove
  browser integration.
- Delay browser QA to backend transcription slice: rejected because audio route
  correctness is a macOS client responsibility.

## Decision 6: Use Clean-Room Krisp-Like App I/O, AEC Reference, And Stream Health

**Decision**: 2brain Rec should follow the observed Krisp architectural pattern
without copying closed implementation: public meeting-facing virtual microphone
and speaker devices, private app I/O between the HAL driver and desktop audio
engine, speaker audio as an AEC/reference stream, fail-closed public-device
availability, and periodic stream-health checks.

**Observed Krisp basis**:

- Krisp exposes public `krisp microphone` and `krisp speaker` Core Audio devices
  while also using hidden/private app I/O between its driver and app engine.
- The observed virtual devices use a 48 kHz Core Audio-facing format, while the
  app engine logs show low-latency frame processing, bounded caches, and separate
  microphone and speaker graphs.
- Krisp separates outbound microphone processing from inbound speaker processing
  and uses an AEC-style reference path: microphone graph entries are marked as
  AEC processing, speaker graph entries as AEC monitor/reference.
- When the user-space Krisp app engine is killed, the Core Audio driver remains
  installed but the public devices become unavailable; relaunching the app
  restores them after route recovery. This is the desired fail-closed behavior.
- Krisp logs show capturability monitoring at a 3000 ms interval. All-zero
  checks exist in strings/log messages, but the observed configuration has the
  all-zero interval set to `0`, so natural user silence should not be treated as
  failure by itself.
- Krisp logs track frame/cache counters such as stored/retrieved/processed and
  dropped frames. This supports route-health evidence based on frame continuity
  rather than speech detection alone.
- Krisp app configuration includes longer audio-degradation windows, including a
  30-second call-start or alert window, which should be treated separately from
  hard route/capturability failure.

**Rationale**: This gives the MVP a proven shape for low-latency calls: meeting
apps see stable public devices, real-time app/driver transport stays private,
speaker audio is available as an echo/leakage reference, and broken app I/O
does not leave a fake-ready route behind. Distinguishing capturability from
speech prevents the app from marking a quiet user as broken.

**Requirements derived from the observation**:

- Built-in and wired release-ready routes must keep added 2brain Rec route
  latency at or below 30 ms.
- Remote speaker leakage in the virtual microphone must be at least 45 dB below
  the speaker reference and not intelligible.
- Expected streams must be marked degraded when they are not capturable or have
  no valid frames for one 3-second health interval.
- Ordinary user silence with valid frames must not mark capture degraded.
- Non-critical audio-quality warnings should use a longer 30-second observation
  window, while hard route failures still fail fast.

**Alternatives considered**:

- Copy Krisp binaries, private protocols, or model behavior directly: rejected
  because the project must stay clean-room and brand-distant.
- Treat absence of speech as a degraded microphone: rejected because it confuses
  ordinary silence with route failure.
- Keep public virtual devices visible after private app I/O is gone: rejected
  because it can leave meeting apps connected to a route that cannot actually
  pass audio.
