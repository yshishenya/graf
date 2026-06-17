# Data Model: Recording Sync And Transcription Loop

Date: 2026-06-18

## Design Rules

- One real meeting maps to one logical `Meeting`.
- `042` creates only the initial accepted `MediaRevision`.
- Accepted media is immutable. Future trim, video, replace, restore, and
  reprocess features create new revisions.
- Upload sessions, track artifacts, processing workflows, MediaScribe jobs,
  processing results, transcript segments, lifecycle, deletion, and diagnostics
  must be attributable to a media revision.
- Desktop/server reconciliation must never create duplicate meetings for retry
  attempts.

## Entity: Local Capture Package

Represents the saved local recording directory created after Stop.

Fields:

- `directoryId`: stable local package id from `LocalRecordingManifest`.
- `sessionId`: local recording session id.
- `manifestPath`: local path, never sent to logs/evidence except redacted
  basename.
- `microphonePath`: local `mic.wav` path.
- `systemAudioPath`: local `incoming.wav` path.
- `manifestSha256`, `microphoneSha256`, `systemAudioSha256`: content
  fingerprints.
- `status`: `saved`, `degraded`, `failed`, `blocked`.
- `transcriptionReadiness`: `ready`, `degraded`, `failed`.
- `failureReason`: metadata-safe reason.
- `startedAt`, `stoppedAt`, `durationSeconds`.

Validation:

- Upload eligibility requires `status == saved`, `isComplete == true`, one
  local mic track, one incoming/system track, accepted permissions/scope truth,
  and leakage/transcription gates passing.
- Local paths must not appear in server logs, diagnostics, or Spec Kit evidence.

## Entity: Local Media Revision

Represents the desktop-side identity for the initial accepted package.

Fields:

- `localMediaRevisionId`: deterministic string, e.g.
  `<directoryId>--initial`.
- `localRecordingId`: `directoryId`.
- `sessionId`: local recording session id.
- `revisionNumber`: `1` for `042`.
- `sourceKind`: `initial_recording`.
- `immutable`: `true` once enqueued for upload.
- `trackSha256ByRole`: manifest/microphone/system checksums.
- `createdAt`, `acceptedAt`.

Validation:

- Recomputed checksums must match queue state before upload resumes.
- If local files differ from the stored revision fingerprint, the queue item
  becomes `conflict_local_changed` or `blocked`, not silently updated.

## Entity: Desktop Upload Queue Item

Extends `DesktopUploadQueueItem`.

Fields:

- Existing v1 fields: `id`, `sessionId`, `directoryId`, paths, upload state,
  retry mode, attempts, `meetingId`, `uploadSessionId`, `serverTruth`.
- New v2 fields:
  - `schemaVersion`: `desktop-upload-queue.v2`.
  - `localMediaRevisionId`.
  - `mediaRevisionId`: server UUID after server acceptance.
  - `syncGeneration`: monotonic local integer for local queue writes.
  - `lastReconciledAt`.
  - `syncConflictState`: see entity below.

State transitions:

```text
queued -> uploading -> uploaded
queued -> retrying -> uploading
uploading -> retrying
uploading -> blocked
retrying -> blocked
blocked -> queued (manual retry only)
uploaded -> terminal_deleted (after accepted deletion/local purge truth)
```

Validation:

- Terminal uploaded items do not return to non-terminal upload states.
- Server truth may fill `meetingId`, `uploadSessionId`, `mediaRevisionId`,
  accepted bytes, processing state, and deletion/access state.
- Local retry never changes `localMediaRevisionId`.

## Entity: Server Meeting

Existing logical meeting row.

Fields:

- `id`.
- `workspaceId`, `createdByUserId`, `deviceId`.
- `localRecordingId`: unique inside workspace.
- `title`, `startedAt`, `endedAt`, `durationSeconds`.
- `status`.
- `processingStatus`: aggregate/latest status for the visible meeting.
- access/share/download/deletion/retention fields from accepted slices.

Validation:

- Unique `(workspace_id, local_recording_id)` remains the meeting dedupe key.
- Creating a meeting with the same `local_recording_id` and different immutable
  metadata is an idempotency conflict.

## Entity: Media Revision

New server entity.

Fields:

- `id`: UUID.
- `workspaceId`, `meetingId`.
- `localMediaRevisionId`: stable desktop-provided revision key.
- `revisionNumber`: `1` for initial MVP revision.
- `sourceKind`: `initial_recording`, future `local_trim`, `video_capture`,
  `replace`, `restore`, `reprocess`.
- `status`: `pending_upload`, `uploading`, `accepted`, `blocked`,
  `superseded`, `deleted`.
- `manifestSha256`.
- `trackSha256ByRole`.
- `durationSeconds`.
- `acceptedAt`, `createdAt`, `updatedAt`.

Relationships:

- One `Meeting` has one or more `MediaRevision` rows.
- `042` creates exactly one accepted revision per meeting.
- Upload sessions, artifacts, processing workflows/jobs/results, transcript
  results, lifecycle rows, and deletion reports reference a media revision.

Validation:

- Unique `(workspace_id, meeting_id, revision_number)`.
- Unique `(workspace_id, local_media_revision_id)`.
- Accepted revision fingerprints are immutable.
- Future revisions do not mutate earlier accepted track artifacts.

## Entity: Upload Session

Extends existing server `UploadSession`.

Fields:

- Existing fields: `id`, `meetingId`, workspace/user/device, status,
  idempotency key, expected roles/sizes, expiry, finalized at.
- New field: `mediaRevisionId`.

Validation:

- Active upload session dedupe is per media revision.
- Expected track sizes and roles must match the media revision identity.
- Finalization only succeeds when required ranges are complete and checksums
  match expected descriptors.

## Entity: Track Artifact

Extends existing server `TrackArtifact`.

Fields:

- Existing fields: `id`, `meetingId`, `workspaceId`, `trackRole`, codec,
  sample rate, channel count, duration, byte length, sha256, storage key,
  status.
- New field: `mediaRevisionId`.

Validation:

- Required roles for `042`: `microphone`, `system`, `manifest`.
- Artifact storage keys remain server-owned and never returned to desktop.

## Entity: Processing Workflow / Job / Result

Extends existing processing entities.

Fields:

- `mediaRevisionId` on processing workflow, MediaScribe job, and processing
  result.
- `workflowId`: `processing/<media_revision_id>`.
- Existing statuses, attempt counts, external job ids, result version,
  language, segment counts, dependency states.

Validation:

- One open processing workflow per accepted media revision.
- Duplicate pickup reuses the open workflow.
- Imported transcript/diarization rows map to the processing result and
  inherited media revision.
- Meeting aggregate status reflects latest accepted/current revision status.

## Entity: Transcript Result

Represents reviewable transcript/diarization content.

Fields:

- `processingResultId`.
- `mediaRevisionId` through processing result.
- `meetingId`, `workspaceId`.
- `TranscriptSegment`: sequence, start/end seconds, source role, text.
- `DiarizationSegment`: sequence, start/end seconds, speaker label, source
  role, text.

Validation:

- Transcript text appears only in authorized product review responses.
- Transcript text is forbidden in diagnostics, logs, analytics, and Spec Kit
  evidence.
- `042` does not allow transcript text edits or speaker assignment edits.

## Entity: Sync Conflict State

Represents a visible local/server mismatch.

Values:

- `none`.
- `local_files_missing`.
- `local_checksum_changed`.
- `server_meeting_deleted`.
- `access_revoked`.
- `server_expected_metadata_mismatch`.
- `server_ranges_inconsistent`.
- `processing_failed`.
- `processing_blocked`.
- `auth_required`.
- `retention_expired`.

Rules:

- Conflict state must include a metadata-safe reason and next action.
- Conflicts block unsafe finalize/reprocess attempts.
- User-visible copy must not expose private local paths or secret values.

## Entity: Lifecycle Accounting

Tracks where revision-related data exists.

Fields:

- `meetingId`, `mediaRevisionId`.
- `localBufferState`.
- `serverArtifactState`.
- `temporaryUploadState`.
- `processingWorkflowState`.
- `mediaScribeDependencyState`.
- `transcriptState`.
- `diagnosticsState`.
- `deletionParticipationState`.

Validation:

- Deletion copy remains "Delete this meeting everywhere 2brain Rec controls."
- Reports distinguish local buffers, server artifacts, backups, Temporal,
  MediaScribe, Langfuse, diagnostics, and post-egress limits.
