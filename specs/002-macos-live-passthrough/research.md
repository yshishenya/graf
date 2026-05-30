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
