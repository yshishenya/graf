# Contract: Desktop App <-> Thin Audio Component

## Purpose

This contract defines the product-level interface between the 2brain Rec macOS
desktop app and the thin audio component. It does not choose a concrete IPC
transport. Implementation may use the safest macOS-supported mechanism selected
in Phase 0, but the messages and state guarantees below must remain intact.

## Boundary Rules

- The audio component owns virtual device publication, passthrough, routing,
  mirroring, timing, and continuity/dropout signals.
- The desktop app owns policy, capture lifecycle, local encrypted buffering,
  upload readiness, retention/purge state, user-visible state, diagnostics
  packaging, and audit hooks.
- The audio component must not store MediaScribe credentials, server credentials,
  transcripts, or retention policy.
- The audio component must not silently drop audio. If it cannot deliver frames,
  timing, or passthrough, it must surface a continuity or health event.

## Required Virtual Devices

```text
2brain Rec Microphone
direction: input
source: selected physical microphone
must_exclude: remote participant audio

2brain Rec Speaker
direction: output
sink: selected physical output
mirror: remote speaker track for desktop capture
```

## State Values

### DriverInstallationState

`not_installed`, `installed`, `needs_repair`, `needs_update`, `incompatible`,
`uninstalling`, `uninstalled`, `requires_restart`

### RouteStatus

`unknown`, `verifying`, `passed`, `failed`, `stale`, `blocked_self_routing`

### PassthroughStatus

`healthy`, `degraded`, `failed`, `muted_by_physical_device`,
`physical_device_missing`, `unknown`

### ContinuityEventType

`dropout_detected`, `clock_drift_detected`, `format_changed`,
`device_disconnected`, `device_profile_changed`, `buffer_pressure`,
`stream_restarted`

## Required Events

### `driver.status_changed`

Emitted when install/version/availability changes.

Required fields:

- `driverInstallationState`
- `driverVersion`
- `macOSVersion`
- `appleSilicon`
- `requiresRestart`
- `recoveryAction`

Forbidden fields:

- raw audio
- transcript text
- credentials, tokens, signed URLs

### `route.verification_result`

Emitted after route verification for one path.

Required fields:

- `path`
- `validationType`
- `target`
- `status`
- `failureReason`
- `recoveryAction`
- `timestamp`

### `audio.passthrough_changed`

Emitted when live passthrough health changes.

Required fields:

- `path`
- `passthroughStatus`
- `physicalDeviceClass`
- `sampleRate`
- `channelLayout`
- `timestamp`

### `audio.continuity_event`

Emitted when timing or continuity changes enough for the desktop app to mark
dropouts or drift.

Required fields:

- `trackRole`
- `eventType`
- `monotonicTime`
- `durationMs`
- `driftEstimateMs`
- `severity`

### `capture.frame_available`

Internal handoff of captured audio frames from the audio component to the
desktop-owned capture pipeline.

Required metadata:

- `trackRole`
- `monotonicTimestamp`
- `sampleRate`
- `channelLayout`
- `frameCount`
- `continuitySequence`

Frame payload rules:

- Payload is local-only and must go to the desktop-owned encrypted buffer or
  live processing path.
- Payload must never be sent directly from the audio component to MediaScribe.
- Payload must not be included in diagnostics by default.

## Readiness Rules

- Desktop may show `ready` only when both virtual devices are available and the
  current route verification status for mic and speaker paths is `passed`.
- Desktop must downgrade `ready` to `degraded` or `error` when any required
  route becomes stale, blocked, disconnected, or failed.
- Assisted auto-start readiness fields may be populated, but this contract does
  not allow automatic capture start by itself.

## Failure Semantics

- Permission failure must be distinguishable from route failure.
- Physical device failure must be distinguishable from virtual device failure.
- Server/network failure must never be reported as driver failure unless it
  actually affects local capture state.
- Active-call update attempts must return `deferred_active_call`.
