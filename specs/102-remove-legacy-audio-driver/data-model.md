# Data Model: Driver Retirement

This slice removes obsolete models rather than adding a replacement data model.
The table identifies the supported entities and deletion/compatibility rules.

## Retained current entities

### `SystemAudioCaptureSession`

- Purpose: lifecycle and frame truth for ScreenCaptureKit system audio.
- Retained fields: permission state, approved scope, start/stop timing, incoming
  frame count, source kind, failure reason, diagnostic safety.
- Invariants: accepted start requires current permission and approved scope;
  stop releases runtime resources; no virtual device identity exists.

### `RecordingMicrophoneSelection`

- Purpose: selected app-owned microphone and fail-closed input classification.
- Retained fields: mode, input ID/display name, physical device class,
  generalized working-device kind, result/rejection reason, diagnostic safety.
- Change: remove product-specific virtual-driver kind and rejection reason.
  Virtual/aggregate/multi-output inputs use the generic unsupported-input result;
  unknown identity remains unproven.

### `LiveRecordingLevels`

- Purpose: current recording meter values produced by `LocalRecordingWriter`.
- Retained fields: recording active flag, microphone/incoming levels and update
  timestamps.
- Change: use this directly in `CaptureControlView`; delete
  `LiveRouteSignalLevels` and the shared-memory monitor.

### `RecordingPrerequisiteSnapshot`

- Purpose: ephemeral current recording-start eligibility.
- Retained fields: recording policy, permission truth, storage risk, visible
  capture-permission truth, indicator availability, source eligibility,
  blocker/recovery copy, timestamp.
- Removed fields: legacy passthrough route state and route evidence kind.
- Invariant: no route/driver publication state can allow or block recording.

### `RecordingEvidenceEvent`

- Purpose: metadata-only start/stop/block/failure evidence in app memory and
  diagnostic bundles.
- Retained fields: event/session identity, type/time/initiator, current capture
  session state, indicator/stop truth, blocker/recovery, duration,
  diagnostic-safe flag.
- Removed field: legacy passthrough route state.

### `LocalRecordingManifest`

- Purpose: current saved dual-track package contract.
- Retained schema version: `local-recording-manifest.v3`.
- Retained current fields: track roles/source kinds/formats, scope, permissions,
  microphone stream/health, capture health, leakage/AEC metadata, meeting mute
  truth, recording metadata, custody and failure truth.
- Removed optional field: legacy route-lifecycle timeline evidence. Older JSON
  containing the key remains readable because unknown keys are ignored.
- Invariants: the two original tracks and their existing formats/roles are not
  changed by this retirement.

### `RecordingRouteMetadata`

- Purpose: physical acoustic/leakage context, not virtual-driver control.
- Retained fields: input/output class, volume/mute, browser target, route-change
  count, sleep/wake, and notes.
- Invariant: metadata-only; never starts or configures an audio route.

## Removed entities

The following model families have no supported current producer/consumer after
the executable legacy path is deleted:

- `VirtualAudioDevice`, `VirtualDeviceAvailabilityState`;
- `RouteVerification`, `RouteVerificationSnapshot`, route validation states;
- `LivePassthroughSession`, path/health/browser/recovery evidence;
- `LiveRouteSession`, client activity/default-route/frame continuity,
  autorepair/release/validation evidence;
- `RecordingTimelineIntegrityEvidence` and its builder;
- low-resource virtual publication, bridge heartbeat, startup-attempt and route
  truth entities;
- `SystemAudioNoHALEvidence` and parked-driver readiness entities; absence is a
  static architecture invariant, not persisted product state;
- driver installation/health and installer operation entities;
- private app/driver IO health entities.

## Compatibility decisions

1. Current user recordings are not rewritten.
2. Removed optional/unknown JSON keys do not prevent decoding retained models.
3. No new driver-era values are written after this change.
4. Historical fixtures remain only where stored under an explicit historical
   evidence surface; they are not compiled into active tests.
5. Current manifest track, permission, health, custody, and upload contracts
   remain unchanged.
6. Repository review confirmed that previously saved manifests can contain the
   retired `hal_probe_observed` failure value. Backward reads map it to the
   retained fail-closed `legacy_not_ready` state; current writes never recreate
   the retired value.
7. If implementation discovers another supported persisted file that requires a
   removed type, work stops and the compatibility requirement is returned to
   clarify/analyze rather than adding a silent shim.
