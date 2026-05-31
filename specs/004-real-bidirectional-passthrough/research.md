# Research: macOS Real Bidirectional Passthrough

## Decision: Keep HAL Driver As Meeting-Facing Boundary

`2brain Rec Microphone` and `2brain Rec Speaker` remain HAL virtual devices.
Meeting apps interact only with those virtual devices; the desktop app bridges
between shared memory and selected physical devices.

**Rationale**: This preserves the accepted driver-first architecture, keeps the
meeting app integration stable, and matches the KRISP-like model documented in
003 without copying proprietary implementation.

**Alternatives considered**:

- App-only audio capture without driver: rejected by constitution and PRD.
- Browser-specific extension or capture path: rejected because the product must
  work across meeting targets through system audio device selection.

## Decision: App Owns Physical Device Capture And Playback

The Swift desktop app owns selected physical microphone capture and selected
physical output playback through macOS audio APIs. The HAL driver owns virtual
device callbacks and shared-memory handoff.

**Rationale**: The app can safely present visible state, recover from route
changes, handle permissions, and keep credentials/egress out of the driver. The
driver can stay minimal and real-time focused.

**Alternatives considered**:

- Driver directly opens physical devices: rejected because it increases
  privilege, recovery, permission, and UI coupling.
- Separate helper daemon for physical devices: deferred until the app bridge
  proves insufficient; it would add lifecycle complexity.

## Decision: Stable Shared Ring Buffer Contract, Not Expanding Layout Casually

Use the existing stable shared-memory heartbeat/ring-buffer layout as the
default handoff. Any layout change must include stale-layout resize/recovery and
matching Swift/C++ tests before install evidence is accepted.

**Rationale**: 003 proved that stale shared-memory layouts can break runtime
publication and recovery. Real passthrough must not destabilize the accepted HAL
loading path.

**Alternatives considered**:

- Add ad hoc counters to shared memory: rejected unless they are versioned or
  covered by stale-layout migration.
- Store raw audio evidence in diagnostics: rejected by privacy and deletion
  constraints.

## Decision: Built-In/Wired Release Target First

Built-in and wired microphone/output routes are the release-quality target for
this feature. Bluetooth and AirPods-class routes remain managed pilot routes
with explicit blocked/degraded evidence unless separately proven.

**Rationale**: Bluetooth profile switching and one-sided audio behavior are less
deterministic. Treating them as parity would blur release criteria.

**Alternatives considered**:

- Require Bluetooth parity before implementation completion: rejected because it
  expands scope beyond the reliable MVP route.

## Decision: Browser Evidence Can Be Blocked, But Never Silent

Chrome, Opera, Yandex Browser, and Yandex Telemost-in-browser must each have
pass or blocked/not accepted metadata-only evidence before the feature is
considered ready for implementation review.

**Rationale**: A browser route that cannot be safely validated must not be
marketed as supported, but the matrix should still be explicit and actionable.

**Alternatives considered**:

- Validate Chrome only: rejected because the spec requires the full target
  matrix.

## Decision: Backend Outage Is Non-Interference Evidence Only

Backend, upload, transcription, and network failures are not implemented in this
feature, but they must be proven not to interrupt local live passthrough.

**Rationale**: Live call audio must be local and resilient even before recording
and upload layers are added.

**Alternatives considered**:

- Couple passthrough readiness to server state: rejected because it would make
  calls fail for reasons unrelated to local audio routing.
