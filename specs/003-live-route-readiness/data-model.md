# Data Model: macOS Live Route Readiness

## LiveRouteReadinessResult

- `status`: `not_started`, `checking`, `ready`, `stale`, `degraded`, `failed`
- `microphoneEvidence`: `MicrophonePathEvidence`
- `speakerEvidence`: `SpeakerPathEvidence`
- `latencyMeasurement`: optional `LatencyMeasurement`
- `leakageMeasurement`: optional `LeakageMeasurement`
- `browserTargetEvidence`: list of `BrowserTargetEvidence`
- `checkedAt`: timestamp
- `expiresAt`: timestamp or route-change invalidation marker
- `recoveryAction`: optional user-facing action key

### Validation Rules

- `ready` requires microphone and speaker evidence to pass.
- Publication-only evidence must never produce `ready`.
- Any route/device/browser/private app I/O invalidation moves `ready` to
  `stale`, `degraded`, or `failed` within 5 seconds.

## MicrophonePathEvidence

- `selectedPhysicalDeviceId`
- `selectedPhysicalDeviceName`
- `virtualMicrophoneName`
- `validFrameCount`
- `emptyBufferCount`
- `capturabilityStatus`
- `selfRoutingRejected`
- `failureReason`
- `checkedAt`

### Validation Rules

- Evidence fails if the selected physical source is a 2brain Rec virtual device.
- Natural silence is not a failure when valid frames continue.
- Missing valid frames for a full 3-second health interval fails the path.

## SpeakerPathEvidence

- `selectedPhysicalOutputId`
- `selectedPhysicalOutputName`
- `virtualSpeakerName`
- `stimulusObserved`
- `validFrameCount`
- `emptyBufferCount`
- `selfRoutingRejected`
- `failureReason`
- `checkedAt`

### Validation Rules

- Evidence fails if the selected physical output is a 2brain Rec virtual device.
- Speaker path proof must result from explicit user-triggered readiness.

## LatencyMeasurement

- `routeClass`: `built_in`, `wired`, `bluetooth`, `airpods_class`, `unknown`
- `addedLatencyMs`
- `thresholdMs`
- `status`: `passed`, `degraded`, `blocked`
- `measuredAt`

### Validation Rules

- Built-in/wired release-ready routes require `addedLatencyMs <= 30`.
- Bluetooth/AirPods-class routes record latency separately and remain managed
  pilot routes.

## LeakageMeasurement

- `speakerReferenceDb`
- `virtualMicLeakageDb`
- `relativeLeakageDb`
- `intelligibilityStatus`
- `status`: `passed`, `degraded`, `blocked`
- `measuredAt`

### Validation Rules

- Built-in/wired release-ready routes require relative leakage at least 45 dB
  below speaker reference and not intelligible.

## BrowserTargetEvidence

- `target`: `chrome`, `opera`, `yandex_browser`, `yandex_telemost_browser`
- `status`: `passed`, `blocked`, `not_accepted`
- `microphoneSelected`
- `speakerSelected`
- `localSpeechUsable`
- `remoteAudioUsable`
- `failureReason`
- `checkedAt`

### Validation Rules

- Every required target must have pass or blocked/not accepted evidence before
  release readiness.
- A blocked target must preserve a concrete reason.

## RouteInvalidationEvent

- `source`: `physical_device`, `output_route`, `browser_target`, `bluetooth_profile`, `app_io`, `coreaudiod`
- `previousReadinessStatus`
- `newReadinessStatus`
- `detectedAt`
- `recoveryAction`

### Validation Rules

- Any event affecting an accepted route invalidates readiness within 5 seconds.
