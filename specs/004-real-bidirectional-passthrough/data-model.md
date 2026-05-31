# Data Model: macOS Real Bidirectional Passthrough

## Live Passthrough Session

Represents a visible, non-recording live route between physical devices and
2brain Rec virtual devices.

- `sessionId`: local unique identifier for diagnostics/audit correlation.
- `status`: `inactive`, `checking`, `ready`, `active`, `stale`, `degraded`,
  `failed`, `blocked`.
- `startedAt`: local timestamp when active passthrough begins.
- `endedAt`: local timestamp when passthrough stops.
- `recordingState`: must remain `not_recording` for this feature.
- `lastRecoveryAction`: current user-facing recovery action, if any.

Validation rules:

- `active` requires microphone and speaker paths to be ready.
- `active` must never imply recording, upload, transcription, or external egress.
- stale, degraded, failed, and blocked states must include a failure category.

## Microphone Passthrough Path

Represents selected physical microphone flow into `2brain Rec Microphone`.

- `physicalInputId`: stable macOS device identifier when available.
- `physicalInputName`: user-facing device name.
- `virtualInputId`: `2brain Rec Microphone`.
- `status`: `not_started`, `checking`, `ready`, `stale`, `degraded`, `failed`,
  `blocked`.
- `validFrameObserved`: whether valid non-empty microphone frames were observed.
- `lastFrameAt`: timestamp of latest valid frame.
- `failureReason`: permission denied, muted, silent, unavailable, self-routed,
  device changed, app heartbeat missing, or unknown.

Validation rules:

- physical input must not be a 2brain Rec virtual device.
- silence alone must not be treated as failure unless the check requires active
  stimulus or the route has no valid frames beyond the accepted window.

## Speaker Passthrough Path

Represents audio sent to `2brain Rec Speaker` and played through selected
physical output.

- `virtualOutputId`: `2brain Rec Speaker`.
- `physicalOutputId`: stable macOS device identifier when available.
- `physicalOutputName`: user-facing device name.
- `status`: `not_started`, `checking`, `ready`, `stale`, `degraded`, `failed`,
  `blocked`.
- `stimulusObserved`: whether the speaker path observed expected stimulus or
  remote audio reference.
- `playbackConfirmedAt`: timestamp when playback evidence last passed.
- `failureReason`: unavailable, muted, disconnected, self-routed, aggregate
  unmanaged, route changed, app heartbeat missing, or unknown.

Validation rules:

- physical output must not be a 2brain Rec virtual device.
- aggregate and multi-output devices are blocked unless measurable by the same
  criteria as direct built-in/wired output.

## Passthrough Health Evidence

Metadata-only evidence for route quality.

- `appHeartbeatStatus`: fresh, stale, missing.
- `latencyMs`: measured added route latency.
- `leakageDbBelowReference`: remote-to-mic leakage measurement.
- `dropoutFraction`: optional local measurement for future extended runs.
- `routeInvalidatedAt`: timestamp of last invalidating event.
- `diagnosticSafe`: must be true before export.

Validation rules:

- ready built-in/wired route requires `latencyMs <= 30`.
- ready built-in/wired route requires `leakageDbBelowReference >= 45` and
  `notIntelligible == true`.
- diagnostics must not include raw audio or transcript text.

## Browser Call Evidence

Per-browser validation result.

- `targetName`: Chrome, Opera, Yandex Browser, or Yandex Telemost-in-browser.
- `targetVersion`: optional version string.
- `selectedMicrophone`: expected `2brain Rec Microphone`.
- `selectedSpeaker`: expected `2brain Rec Speaker`.
- `localSpeechUsable`: pass/fail/not tested.
- `remoteAudioUsable`: pass/fail/not tested.
- `status`: pass, blocked, not accepted.
- `failureReason`: required when not passed.

Validation rules:

- every target must have pass or blocked/not accepted evidence.
- evidence is metadata-only and must not contain meeting content.

## Route Recovery Event

Represents a route-changing event that invalidates or restores passthrough.

- `eventType`: physical input changed, physical output changed, browser target
  changed, Bluetooth profile changed, app heartbeat lost, app heartbeat
  restored, driver reloaded, `coreaudiod` restarted.
- `detectedAt`: timestamp of detection.
- `previousStatus`: status before event.
- `newStatus`: status after event.
- `recoveryAction`: user-facing next action.

Validation rules:

- invalidating events must make active/ready passthrough stale, degraded, or
  failed within 5 seconds.
- recovery must require fresh heartbeat and route revalidation.
