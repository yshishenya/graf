# Data Model: Local Recording Persistence

## LocalRecordingSession

Represents one manual local recording attempt.

Fields:

- `sessionId`: generated capture session id.
- `startedAt`: timestamp when local persistence started.
- `stoppedAt`: timestamp when local persistence stopped or failed.
- `directoryId`: generated local artifact directory name, safe for diagnostics.
- `status`: `active`, `saved`, `degraded`, or `failed`.
- `tracks`: local mic and remote speaker track summaries.
- `manifestFileName`: safe basename for the manifest.
- `failureReason`: optional concrete reason.
- `diagnosticSafe`: true only when metadata excludes raw content and live paths.

Validation:

- One active local recording session at a time.
- A complete saved session requires both required tracks in `saved` status with
  non-zero byte counts and positive durations.
- Degraded/failed sessions must include a concrete `failureReason`.

## LocalRecordingTrack

Represents one role-specific audio artifact.

Fields:

- `trackId`: generated track id.
- `role`: `local_mic` or `remote_speaker`.
- `status`: `pending`, `recording`, `saved`, `missing`, `degraded`, or `failed`.
- `fileName`: safe basename only.
- `format`: local audio format identifier.
- `sampleRate`: expected sample rate.
- `channelCount`: expected channel count.
- `durationMs`: duration derived from written frames.
- `byteCount`: finalized file byte count.
- `frameCount`: count of persisted frames.
- `failureReason`: optional concrete reason.

Validation:

- `saved` tracks require `byteCount > 0`, `frameCount > 0`, and `durationMs > 0`.
- `missing`, `degraded`, and `failed` tracks must not be counted as complete.
- Track evidence must never include raw sample data.

## LocalRecordingManifest

Metadata-only file saved with the local track artifacts.

Fields:

- `schemaVersion`: `local-recording-manifest.v1`.
- `sessionId`
- `createdAt`
- `startedAt`
- `stoppedAt`
- `status`
- `directoryId`
- `tracks`
- `externalEgressStarted`: always false for this feature.
- `transcriptionStarted`: always false for this feature.
- `diagnosticSafe`: true when manifest contains metadata only.

Validation:

- Manifest must be valid JSON.
- Manifest must reference only local safe filenames, not absolute user paths.
- Manifest must include both required roles, even when one is missing/degraded.

## PersistenceEvidence

Metadata-only diagnostics and QA output.

Fields:

- `sessionId`
- `status`
- `trackStatuses`
- `safeArtifactIds`
- `durationMs`
- `byteCounts`
- `failureReason`
- `diagnosticSafe`

Validation:

- Must not include raw audio, transcript text, meeting content, credentials,
  tokens, signed URLs, passwords, API keys, or live secret paths.
