# Research: macOS Live Route Readiness

## Decision: Use User-Triggered Live Route Proof

Use an explicit `Run Check` flow that proves microphone and speaker paths before
ready. The flow may ask the user to speak/tap the microphone and may play a
short audible speaker stimulus, but it must not start recording or hidden
capture.

**Rationale**: This preserves visible consent, avoids silent capture, and matches
the existing product gate that publication alone is insufficient.

**Alternatives considered**:

- Auto-probing continuously in the background: rejected because it risks hidden
  capture semantics and unclear user consent.
- Treating device publication as ready: rejected because 002 already proved that
  publication does not imply usable passthrough.

## Decision: Measure Readiness With Route Evidence, Not Raw Audio Artifacts

The app should decide readiness from route counters, valid-frame evidence,
latency/leakage measurements, and explicit user stimulus state. Diagnostics must
store status and metrics, not raw audio.

**Rationale**: It satisfies privacy and deletion constraints while still giving
QA enough evidence to verify route health.

**Alternatives considered**:

- Store readiness clips as normal diagnostics: rejected because diagnostics must
  exclude raw audio by default.
- Manual-only user confirmation: rejected because the app needs machine-readable
  route evidence before claiming ready.

## Decision: Keep Fail-Closed Behavior From 002

Private app I/O heartbeat remains the driver gate for public device availability.
If heartbeat is missing or stale, public devices must become hidden/unavailable
within 5 seconds and return only after app recovery and route revalidation.

**Rationale**: This is the clean-room Krisp-like safety behavior already proven
by 002 and prevents meeting apps from using dead virtual devices silently.

**Alternatives considered**:

- Leave devices visible and show app-only warning: rejected because meeting apps
  may continue using broken devices.

## Decision: Treat Built-In/Wired As Release-Quality Targets First

Built-in and wired routes are strict release-readiness targets. Bluetooth and
AirPods-class devices remain managed pilot routes with separate profile,
dropout, one-sided-audio, valid-frame, and latency evidence.

**Rationale**: Bluetooth profile behavior is less deterministic and should not
block built-in/wired readiness or be marketed as equivalent.

**Alternatives considered**:

- Require Bluetooth parity before readiness: rejected because it conflates pilot
  routes with release-quality routes and increases scope.

## Decision: Browser Targets May Be Blocked But Must Be Explicit

Chrome, Opera, Yandex Browser, and Yandex Telemost-in-browser each need pass or
blocked/not accepted evidence before release readiness.

**Rationale**: This avoids pretending support while preserving a complete QA
matrix.

**Alternatives considered**:

- Validate only Chrome first: rejected because the spec explicitly requires the
  listed target matrix before release readiness.

## Decision: Backend Outage Must Not Affect Live Route

Backend, upload, transcription, and network failures must not interrupt live call
passthrough after readiness passes.

**Rationale**: Live route safety belongs to the local driver/app plane. Server
features are out of scope for this slice.

**Alternatives considered**:

- Tie route active state to upload/transcription readiness: rejected because it
  would break calls during backend degradation.
