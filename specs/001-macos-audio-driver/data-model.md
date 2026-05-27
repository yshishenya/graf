# Data Model: macOS Virtual Audio Driver MVP

## VirtualAudioDevice

Represents a 2brain Rec audio endpoint visible to macOS and meeting targets.

**Fields**:

- `id`: stable local identifier.
- `displayName`: must be `2brain Rec Microphone` or `2brain Rec Speaker`.
- `direction`: `input` or `output`.
- `driverVersion`: installed audio component version.
- `availabilityState`: `missing`, `installed`, `available`, `unavailable`,
  `incompatible`, `requires_restart`.
- `routeValidationState`: latest route verification status.
- `lastSeenAt`: local timestamp.

**Validation rules**:

- Exactly two MVP virtual devices are allowed.
- Display names must match the spec.
- A virtual device cannot be selected as its own physical source/output.

## PhysicalAudioDevice

Represents the user-selected real microphone or output device.

**Fields**:

- `id`: OS-provided local device identifier when available.
- `displayName`: user-visible name.
- `direction`: `input`, `output`, or `duplex`.
- `class`: `built_in`, `wired`, `usb`, `bluetooth`, `airpods_class`,
  `unknown`.
- `availabilityState`: `available`, `disconnected`, `muted`, `silent`,
  `noisy`, `profile_switching`, `unsupported`.
- `lastVerificationResult`: route verification reference.
- `lastChangedAt`: local timestamp.

**Validation rules**:

- MVP official support covers built-in, wired, USB, Bluetooth, and AirPods-class
  devices.
- Unsupported or unverified devices must be labeled best-effort.

## RouteVerification

Represents proof that the mic path and speaker path work.

**Fields**:

- `id`: local identifier.
- `path`: `mic_to_virtual_input`, `remote_output_to_virtual_speaker`,
  `speaker_passthrough`, `capture_mirror`.
- `validationType`: `synthetic_signal`, `browser_meeting`, `test_recording`,
  `test_playback`.
- `target`: browser/meeting target when applicable.
- `status`: `not_started`, `running`, `passed`, `failed`, `stale`.
- `failureReason`: typed failure code.
- `recoveryAction`: user-visible next action.
- `startedAt`, `finishedAt`: local timestamps.

**Validation rules**:

- The app cannot show `ready` unless both mic and speaker paths have current
  passing synthetic verification.
- Release-candidate readiness requires approved real browser meeting validation
  for the supported target matrix.

## CaptureSession

Represents a local capture attempt.

**Fields**:

- `id`: local session identifier.
- `mode`: `audio_recording` or `transcript_only`.
- `state`: `idle`, `detecting`, `ready`, `starting`, `active`, `paused`,
  `degraded`, `stopping`, `stopped`, `failed`, `finalized`.
- `sourceAppEligibility`: `eligible`, `ineligible`, `unknown`.
- `policySnapshotRef`: opaque reference to workspace policy snapshot.
- `triggerEvidence`: structured fields for later assisted auto-start; must not
  start capture by itself in this feature.
- `visibleIndicatorState`: `hidden`, `ready`, `active`, `paused`, `degraded`,
  `error`.
- `stopActionAvailable`: boolean.
- `bufferState`: local buffer summary reference.
- `startedAt`, `stoppedAt`: local timestamps.

**Validation rules**:

- Active capture requires visible local indication and one-action stop.
- Manual start/stop remains available when policy permits.
- Missing required tracks mark the session degraded before finalization.

## AudioTrack

Represents one captured audio stream.

**Fields**:

- `id`: local track identifier.
- `sessionId`: capture session reference.
- `role`: `local_mic` or `remote_speaker`.
- `state`: `pending`, `capturing`, `degraded`, `missing`, `finalized`.
- `sampleRate`: observed sample rate.
- `channelLayout`: observed channel layout.
- `timebase`: monotonic local timebase reference.
- `clockDriftMs`: observed drift estimate.
- `dropoutMarkers`: continuity event references.
- `finalizedAt`: local timestamp.

**Validation rules**:

- Local mic track must not contain remote participant audio.
- Remote speaker track must preserve enough timing metadata for alignment.
- Required tracks missing at finalization make the recording degraded.

## LocalBufferItem

Represents encrypted local capture data owned by desktop software.

**Fields**:

- `id`: local artifact identifier.
- `sessionId`: capture session reference.
- `trackId`: audio track reference when applicable.
- `artifactType`: `audio_chunk`, `track_manifest`, `session_manifest`,
  `diagnostic_manifest`.
- `encryptedSizeBytes`: size after local encryption.
- `createdAt`: local timestamp.
- `retentionDeadline`: local purge deadline.
- `uploadState`: `not_ready`, `queued`, `uploading`, `uploaded`, `failed`,
  `server_unavailable`, `network_unavailable`.
- `purgeState`: `retained`, `pending_purge`, `purged`, `purge_failed`,
  `expired_unreachable`.
- `deletionReportState`: `not_requested`, `acknowledged`, `pending_client`,
  `outside_control`.

**Validation rules**:

- Buffer policy is desktop-owned.
- Capture must degrade or stop before buffer limits or disk reserve cause silent
  data loss.
- Server purge cannot be represented as local purge without desktop acknowledgement
  or local expiry.

## DriverHealthReport

Represents user-facing and support-facing driver health state.

**Fields**:

- `id`: local report identifier.
- `driverStatus`: `not_installed`, `installed`, `needs_repair`,
  `needs_update`, `incompatible`, `uninstalling`, `uninstalled`.
- `permissionStatus`: microphone and required OS permission summary.
- `routeGraphStatus`: current route graph summary.
- `passthroughStatus`: `healthy`, `degraded`, `failed`, `unknown`.
- `continuityStatus`: latest dropout/drift summary.
- `diagnosticRedactionStatus`: `redacted`, `blocked_sensitive_content`,
  `admin_content_enabled`.
- `recoveryActions`: ordered user-visible actions.
- `createdAt`: local timestamp.

**Validation rules**:

- Reports must not contain raw audio, transcript text, credentials, tokens, or
  signed URLs by default.
- Failure state must distinguish driver, routing, permission, physical device,
  server, and network failures.

## InstallerState

Represents install, update, repair, rollback, and uninstall lifecycle.

**Fields**:

- `operation`: `install`, `update`, `repair`, `rollback`, `uninstall`.
- `state`: `not_started`, `running`, `requires_permission`, `requires_restart`,
  `succeeded`, `failed`, `partially_completed`, `deferred_active_call`.
- `versionBefore`, `versionAfter`: component versions when known.
- `previousPhysicalInput`, `previousPhysicalOutput`: restoration candidates.
- `manualCleanupRequired`: boolean plus user-visible reason.
- `completedAt`: local timestamp.

**Validation rules**:

- Updates cannot interrupt active calls.
- Uninstall attempts to remove app-managed artifacts and restore previous
  physical devices where OS permits.
- Remaining OS-managed artifacts require truthful manual remediation steps.

## State Transitions

```text
CaptureSession:
idle -> detecting -> ready -> starting -> active -> stopping -> stopped -> finalized
ready -> starting -> failed
active -> paused -> active
active -> degraded -> stopping
active -> failed

RouteVerification:
not_started -> running -> passed
not_started -> running -> failed
passed -> stale
failed -> running

InstallerState:
not_started -> running -> succeeded
not_started -> running -> failed
running -> requires_permission -> running
running -> requires_restart -> succeeded
running -> deferred_active_call
running -> partially_completed -> failed
```
