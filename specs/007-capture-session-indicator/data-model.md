# Data Model: Manual Capture Session And Visible Indicator

## Capture Session

Represents one local manual recording attempt.

Fields:

- `id`: stable local identifier.
- `mode`: `audio_recording` for this slice; `transcript_only` remains modeled
  but not accepted as a working mode here.
- `state`: `idle`, `detecting`, `ready`, `starting`, `active`, `stopping`,
  `stopped`, `degraded`, `failed`, or `finalized`.
- `sourceAppEligibility`: whether the current target is eligible, ineligible,
  unknown, or policy-blocked.
- `policySnapshotRef`: metadata reference to the policy decision used at start.
- `triggerEvidence`: metadata-only start/readiness/stop evidence.
- `visibleIndicatorState`: local capture indicator state.
- `stopActionAvailable`: whether one-action stop is currently available.
- `bufferSummaryId`: local buffer/evidence summary reference, if created.
- `startedAt`: timestamp set when recording becomes active.
- `stoppedAt`: timestamp set when stop/failure/finalization completes.
- `stopReason`: reason for stop or failure; added by this slice.
- `failureCategory`: metadata-only category when start or active capture fails.

State rules:

- `idle` or terminal states may begin a new manual start.
- `ready` may transition to `starting`.
- `starting` may transition to `active`, `stopping`, or `failed`.
- `active` may transition to `stopping`, `degraded`, or `failed`.
- `degraded` may transition to `stopping` or `failed`.
- `stopping` may transition to `stopped`, `degraded`, or `failed`.
- `stopped` may transition to `finalized`.
- Active-like states must have visible indicator and stop available unless the
  session is immediately failing closed.

## Recording Prerequisite Snapshot

Represents the gate evaluated before recording starts.

Fields:

- `routeState`: current route readiness state.
- `routeEvidenceKind`: e.g. live route, low-resource truth, publication-only.
- `policyAllowsRecording`: whether local/workspace policy permits recording.
- `microphonePermission`: current permission status.
- `storageRisk`: local buffer/storage reserve state.
- `indicatorAvailable`: whether a persistent local indicator can be shown.
- `sourceAppEligibility`: target eligibility state.
- `blockedReason`: concrete category if any prerequisite fails.
- `recoveryAction`: user-facing next action.
- `evaluatedAt`: timestamp.

Validation rules:

- Recording start is allowed only when route is valid, policy allows recording,
  microphone permission is granted or not needed for the current route, storage
  risk is safe, and indicator is available.
- Publication-only, stale, blocked, failed, unknown, or fallback route evidence
  cannot allow recording start.
- Missing visible indicator blocks start.

## Capture Indicator State

Represents the local visible recording surface.

Fields:

- `surface`: main window, status item, floating widget, or fallback visible
  local surface.
- `state`: ready, active, paused, degraded, error, hidden.
- `visible`: whether the surface is currently visible to the user.
- `stopActionAvailable`: whether stop is exposed in one action.
- `accessibilityLabel`: non-empty label for screen readers.
- `lastVerifiedAt`: timestamp of the last visibility/stop assertion.

Validation rules:

- Active recording requires at least one visible indicator with one-action stop.
- If all indicators become hidden/unavailable, recording must stop or fail
  closed.
- Color alone cannot be the only active recording signal.

## Recording Evidence Event

Metadata-only lifecycle event.

Fields:

- `eventId`: stable event identifier.
- `sessionId`: capture session identifier.
- `eventType`: start_requested, start_blocked, started, stop_requested,
  stopped, failed, indicator_lost, route_invalidated, storage_blocked.
- `occurredAt`: timestamp.
- `initiator`: user, system_fail_closed, recovery, or validation.
- `routeState`: route state at the event.
- `indicatorState`: visible indicator state at the event.
- `stopActionAvailable`: boolean.
- `blockedReason`: optional category.
- `recoveryAction`: optional user-facing next action.
- `diagnosticSafe`: boolean.

Validation rules:

- Evidence must not include raw audio, transcript text, meeting content,
  credentials, tokens, signed URLs, passwords, or live secret paths.
- Every started session must have corresponding stop/fail evidence before it is
  considered closed.

## Local Recording Artifact Reference

Represents local-only capture artifacts without server upload.

Fields:

- `artifactId`: local reference.
- `sessionId`: capture session identifier.
- `artifactType`: local mic track, remote speaker track, session evidence, or
  buffer summary.
- `state`: pending, capturing, degraded, missing, finalized.
- `createdAt`: timestamp.
- `retentionDeadline`: local retention metadata placeholder.
- `uploadState`: must remain not started or local only in this slice.

Validation rules:

- This slice must not create uploaded/server/MediaScribe/Langfuse artifact
  states.
- Missing or degraded local track references must be represented truthfully.
