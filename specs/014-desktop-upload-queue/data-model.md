# Data Model: Desktop Upload Queue And Resilient Upload Behavior

## UploadQueueItem

Durable local record for one finalized local recording package.

Fields:

- `id`: Stable queue ID, derived from local package identity.
- `sessionId`: Local recording session ID from `manifest.json`.
- `directoryId`: Local recording package directory ID.
- `directoryPath`: Local directory path used only locally; excluded from
  default diagnostics.
- `manifestPath`, `microphonePath`, `systemAudioPath`: Local artifact paths.
- `state`: `UploadItemState`.
- `failureCategory`: `UploadFailureCategory`.
- `failureReason`: Safe diagnostic reason string.
- `retryMode`: `automatic`, `manualOnly`, or `terminal`.
- `attemptCount`: Number of upload attempts.
- `nextRetryAt`: Next automatic retry time, if any.
- `retentionDeadline`: Deadline from local buffer policy.
- `createdAt`, `updatedAt`.
- `meetingId`: Server meeting ID after creation.
- `uploadSessionId`: Server upload session ID after creation.
- `artifactProfile`: `ArtifactCompletenessProfile`.
- `serverTruth`: `ServerTruthFingerprint`.
- `retryRecords`: Ordered `RetryRecord` history.
- `retentionDecision`: Latest `RetentionDecision`.

Validation rules:

- `id` must be deterministic for the same local recording package.
- Terminal states cannot regress to recoverable states.
- Non-terminal states must keep local artifact references.
- `uploaded` requires server truth showing all required tracks accepted.
- Default diagnostics must not include absolute local paths.

## UploadItemState

User-facing and diagnostic upload truth.

Values:

- `queued`: Local package is ready for upload.
- `uploading`: Worker is sending or reconciling accepted bytes.
- `retrying`: A recoverable failure occurred and automatic retry is scheduled.
- `uploaded`: Server finalized required package truth.
- `degraded`: Some upload/server truth exists but normal completion is blocked.
- `failed`: Terminal failure that cannot continue automatically.
- `blocked`: Recoverable, manual-only, or policy-gated state.
- `terminalDeleted`: Explicit local/policy terminal deletion state.

Validation rules:

- Terminal states: `uploaded`, `failed`, `terminalDeleted`.
- Recoverable states: `queued`, `uploading`, `retrying`, `degraded`, `blocked`.
- `failed` is terminal only when `retryMode=terminal`.
- UI must show retryability for every state.

## UploadFailureCategory

Safe failure classification.

Values:

- `none`
- `network`
- `authSession`
- `serverValidation`
- `schemaIncompatibility`
- `localResource`
- `storageQuota`
- `cancelled`
- `unknown`

Validation rules:

- `network`, `unknown`, and `storageQuota` may be retryable depending on policy.
- `authSession` becomes `blocked/manualOnly` until session context is refreshed.
- `schemaIncompatibility` and server validation checksum mismatches become
  `blocked` or terminal according to server truth.

## ArtifactCompletenessProfile

Snapshot of local package readiness.

Fields:

- `manifestPresent`, `microphonePresent`, `systemAudioPresent`.
- `manifestSha256`, `microphoneSha256`, `systemAudioSha256`.
- `manifestSizeBytes`, `microphoneSizeBytes`, `systemAudioSizeBytes`.
- `trackCompleteness`: Array of `UploadTrackCompleteness`.
- `isUploadable`.
- `schemaVersion`.

Validation rules:

- Uploadable packages require all three artifacts present and non-empty.
- Manifest track roles map to backend transport roles:
  `local_mic -> microphone`, `remote_speaker -> system`, `manifest.json -> manifest`.
- Non-uploadable packages are visible as `blocked` with a schema/local-resource reason.

## RetryRecord

Metadata-only attempt history.

Fields:

- `attemptNumber`
- `startedAt`
- `finishedAt`
- `stateBefore`
- `stateAfter`
- `failureCategory`
- `failureReason`
- `acceptedBytesByTrack`
- `nextRetryAt`

Validation rules:

- Records must not contain raw audio, transcript text, credentials, tokens,
  signed URLs, or absolute local paths.
- Attempt numbers are monotonic per queue item.

## ServerTruthFingerprint

Read-only server confirmation evidence.

Fields:

- `meetingId`
- `uploadSessionId`
- `serverStatus`
- `processingStatus`
- `acceptedBytesByTrack`
- `requiredTrackSha256`
- `finalizedAt`
- `desktopTruthRule`

Validation rules:

- `uploaded` requires `serverStatus=finalized` or
  `serverStatus=ingested_pending_processing` with all required bytes accepted.
- Server truth never implies transcript, summary, MediaScribe, Temporal, or
  dashboard readiness.

## RetentionDecision

Local retention and terminalization evidence.

Fields:

- `decision`: `retain`, `manualOnly`, `terminalUploaded`, `terminalFailed`,
  `terminalDeleted`.
- `decidedAt`
- `reason`
- `localArtifactsRetained`
- `policyReference`

Validation rules:

- Local artifacts remain retained for non-terminal upload truth.
- Terminal deletion requires explicit policy/user decision evidence.

## State Transitions

```text
discovered
  -> queued
queued
  -> uploading
  -> blocked
uploading
  -> retrying
  -> degraded
  -> uploaded
  -> failed
retrying
  -> uploading
  -> blocked
  -> failed
blocked
  -> queued
  -> uploading
  -> failed
uploaded
  -> terminalDeleted
failed
  -> terminalDeleted
```

Forbidden transition:

```text
uploaded|failed|terminalDeleted -> queued|uploading|retrying|degraded|blocked
```
