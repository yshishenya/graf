# Data Model: Live Route Stability

## Overview

`019` adds metadata-only live-route and validation evidence. It does not add
meeting content storage, server APIs, upload state, MediaScribe calls, Langfuse
content tracing, or raw audio diagnostics.

## Entity: LiveRouteSession

Represents one live passthrough route session while a meeting target uses
`2brain Rec Microphone` and `2brain Rec Speaker`.

Fields:

- `routeSessionId: String` - stable UUID for correlation.
- `meetingTarget: MeetingTarget` - Chrome, Opera, Zoom, or Telemost.
- `startedAt: Date`
- `endedAt: Date?`
- `state: LiveRouteState`
- `virtualMicrophoneSelected: Bool`
- `virtualSpeakerSelected: Bool`
- `recordingSessionId: String?`
- `latestMacOSDefaultRoute: MacOSDefaultRouteSnapshot?`
- `latestClientActivity: ClientActivitySnapshot?`
- `latestFrameContinuity: FrameContinuitySnapshot?`
- `latestAutorepair: AutorepairAttempt?`

Validation rules:

- `state == active` requires fresh client activity and frame-continuity evidence.
- `state == healthy_after_fresh_evidence` is allowed only after autorepair and
  fresh route evidence.
- `state == blocked` must include a non-recoverable reason.
- A route session cannot claim accepted validation if user action was required.

## Enum: MeetingTarget

Values:

- `chrome`
- `opera`
- `zoom`
- `telemost`

Yandex Browser is not accepted for `019`.

## Enum: LiveRouteState

Values:

- `inactive`
- `armed`
- `starting`
- `active`
- `preserved`
- `recovering`
- `healthy_after_fresh_evidence`
- `stale`
- `degraded`
- `blocked`
- `failed`
- `released`
- `stopped`

State transition rules:

- `active -> released` requires fresh proof that the meeting client closed the
  virtual route.
- `active -> preserved` is used when release was denied because the meeting
  route is still active or evidence is ambiguous.
- `stale -> recovering` is automatic for recoverable disruptions.
- `recovering -> healthy_after_fresh_evidence` requires fresh client activity,
  route, and frame-continuity evidence.
- `recovering -> blocked` is used for non-recoverable conditions.
- `blocked -> recovering` requires a new external condition becoming available.

## Entity: ClientActivitySnapshot

Metadata proving whether the meeting target still uses virtual devices,
independent of audio energy.

Fields:

- `snapshotId: String`
- `capturedAt: Date`
- `source: ClientActivitySource`
- `microphoneClientOpen: Bool`
- `speakerClientOpen: Bool`
- `microphoneRunning: Bool`
- `speakerRunning: Bool`
- `meetingTargetStillUsesVirtualMic: Bool?`
- `meetingTargetStillUsesVirtualSpeaker: Bool?`
- `freshnessMs: Int`
- `naturalSilenceAllowed: Bool`

Validation rules:

- Natural silence must not set client activity to false.
- Ambiguous or stale snapshots must deny release, not approve release.

## Entity: MacOSDefaultRouteSnapshot

The current macOS system default physical input/output that 2brain Rec follows.

Fields:

- `snapshotId: String`
- `capturedAt: Date`
- `defaultInputDeviceId: String?`
- `defaultInputSafeName: String?`
- `defaultInputClass: PhysicalDeviceClass`
- `defaultOutputDeviceId: String?`
- `defaultOutputSafeName: String?`
- `defaultOutputClass: PhysicalDeviceClass`
- `source: RouteObservationSource`
- `acceptedFor019: Bool`
- `blockedReason: String?`

Validation rules:

- `acceptedFor019 == true` only for built-in, wired, or USB input/output.
- Bluetooth/AirPods-class default routes must be logged as deferred/not
  accepted for `019`.
- A route snapshot must never choose a physical device independently of macOS
  default behavior.

## Enum: PhysicalDeviceClass

Values:

- `built_in`
- `wired`
- `usb`
- `bluetooth`
- `airpods_class`
- `aggregate`
- `multi_output`
- `hdmi_airplay`
- `other_virtual`
- `unknown`

Accepted for `019`: `built_in`, `wired`, `usb`.

## Entity: FrameContinuitySnapshot

Metadata-only counters proving whether valid frames continue through mic and
incoming/speaker paths.

Fields:

- `snapshotId: String`
- `capturedAt: Date`
- `routeSessionId: String`
- `microphoneFrameCounter: UInt64`
- `speakerFrameCounter: UInt64`
- `microphoneLastFrameAt: Date?`
- `speakerLastFrameAt: Date?`
- `microphoneGapMs: Int?`
- `speakerGapMs: Int?`
- `summary: String`

Validation rules:

- Must not include raw audio samples.
- Must be safe to use in diagnostics and manifests.

## Entity: RouteReleaseDecision

Explains why a route was preserved, released, stopped, or blocked.

Fields:

- `decisionId: String`
- `routeSessionId: String`
- `decidedAt: Date`
- `stateBefore: LiveRouteState`
- `stateAfter: LiveRouteState`
- `reason: RouteReleaseReason`
- `clientActivitySnapshotId: String?`
- `frameContinuitySnapshotId: String?`
- `userActionRequired: Bool`

Validation rules:

- `reason == idle_timeout` cannot release a route unless fresh client activity
  proves both virtual clients closed.
- Unknown evidence must produce `release_denied_unknown_state`.

## Enum: RouteReleaseReason

Values:

- `client_closed_virtual_route`
- `explicit_user_stop`
- `release_denied_client_active`
- `release_denied_unknown_state`
- `idle_timeout`
- `app_shutdown`
- `unknown`

## Entity: AutorepairAttempt

Metadata-only record of automatic recovery.

Fields:

- `attemptId: String`
- `routeSessionId: String`
- `trigger: AutorepairTrigger`
- `startedAt: Date`
- `completedAt: Date?`
- `stateBefore: LiveRouteState`
- `stateAfter: LiveRouteState?`
- `attemptNumber: Int`
- `elapsedMs: Int?`
- `timingTier: AutorepairTimingTier`
- `outcome: AutorepairOutcome`
- `macOSDefaultRouteBefore: MacOSDefaultRouteSnapshot?`
- `macOSDefaultRouteAfter: MacOSDefaultRouteSnapshot?`
- `freshEvidenceRequired: Bool`
- `freshEvidenceObserved: Bool`
- `userActionRequired: Bool`
- `blockedReason: NonRecoverableRouteReason?`

Validation rules:

- Successful repair requires `userActionRequired == false`.
- `outcome == succeeded` requires fresh evidence.
- `elapsedMs <= 2000` for normal recoverable disruptions.
- `elapsedMs <= 10000` for OS/device-heavy disruptions after required
  conditions are available again.
- Retry budget exhaustion transitions to blocked/failed, not healthy.

## Enum: AutorepairTrigger

Values:

- `coreaudiod_restart`
- `hal_reload`
- `sleep_wake`
- `physical_device_disappeared`
- `physical_device_returned`
- `macos_default_route_changed`
- `browser_stream_recreated`
- `stale_browser_device_id`
- `app_route_engine_restart`
- `unknown_external_disruption`

## Enum: AutorepairOutcome

Values:

- `not_started`
- `succeeded`
- `degraded_slow`
- `blocked_non_recoverable`
- `failed`
- `retry_budget_exhausted`

## Entity: RouteEvidenceEvent

Structured metadata-only log event.

Fields:

- `eventId: String`
- `eventName: String`
- `family: RouteEvidenceFamily`
- `occurredAt: Date`
- `routeSessionId: String`
- `recordingSessionId: String?`
- `meetingTarget: MeetingTarget?`
- `stateBefore: LiveRouteState?`
- `stateAfter: LiveRouteState?`
- `triggerCategory: String?`
- `virtualClientState: String?`
- `macOSDefaultRoute: MacOSDefaultRouteSnapshot?`
- `frameContinuity: FrameContinuitySnapshot?`
- `autorepairAttemptId: String?`
- `userActionRequired: Bool`
- `diagnosticSafe: Bool`

Validation rules:

- `diagnosticSafe` must be true.
- Payload must exclude raw audio, transcript text, meeting content, secrets,
  tokens, signed URLs, passwords, API keys, and live credential paths.

## Entity: RecordingTimelineIntegrityEvidence

Connects route continuity to the final local recording manifest.

Fields:

- `recordingSessionId: String`
- `routeSessionId: String?`
- `micDurationSeconds: Double`
- `incomingDurationSeconds: Double`
- `durationDifferenceSeconds: Double`
- `alignmentBand: TimelineAlignmentBand`
- `routeInterruptionCategory: RouteInterruptionCategory?`
- `autorepairAttemptIds: [String]`
- `countsAsCleanAcceptance: Bool`

Validation rules:

- `accepted` band requires duration difference `<= 3`.
- `degraded_warning` band applies when `> 3` and `<= 10`.
- `failed` applies when `> 10`.
- Tens/minutes differences are route-stability bugs unless superseded by a
  later accepted spec.

## Enum: TimelineAlignmentBand

Values:

- `accepted`
- `degraded_warning`
- `failed`

## Entity: ValidationRunEvidence

Release/development evidence for 30- and 75-minute gates.

Fields:

- `validationRunId: String`
- `durationGate: DurationGate`
- `meetingTarget: MeetingTarget`
- `physicalDeviceClass: PhysicalDeviceClass`
- `startedAt: Date`
- `completedAt: Date`
- `result: ValidationResult`
- `userActionsRequired: [UserActionKind]`
- `routeReleaseCount: Int`
- `unexpectedReleaseCount: Int`
- `autorepairAttempts: [AutorepairAttempt]`
- `timelineIntegrity: RecordingTimelineIntegrityEvidence?`
- `notTestedCombinations: [String]`

Validation rules:

- Clean acceptance requires no normal user actions.
- Clean acceptance requires zero unexpected releases.
- 30-minute and 75-minute gates are distinct.
- Not-tested combinations must be explicit and cannot be claimed release-ready.

## Enum: DurationGate

Values:

- `development_30_minute`
- `release_75_minute`

## Enum: ValidationResult

Values:

- `accepted`
- `degraded`
- `failed`
- `blocked`
- `not_tested`

## Enum: UserActionKind

Values:

- `run_check`
- `meeting_device_reselect`
- `app_relaunch`
- `meeting_settings_reopen`
- `none`
