# Data Model: Speaker-To-Mic Leakage Control

## RecordingPackage

Represents one finalized local recording directory.

**Fields**:

- `sessionId`
- `directoryId`
- `schemaVersion`
- `startedAt`, `stoppedAt`, `finalizedAt`
- `status`: `saved`, `degraded`, or `failed`
- `transcriptionReadiness`: `ready`, `degraded`, `failed`, or
  `legacy_not_ready`
- `mediaScribeSourceMode`: usually `dual`
- `externalEgressStarted`: must remain `false` in this feature
- `transcriptionStarted`: must remain `false` in this feature
- `diagnosticSafe`: must be `true`
- `localDeletionRegistered`: must be `true` before derived artifacts can be
  created or used
- `tracks`: original and optional derived package tracks
- `leakageFinalization`: optional until stop, required after finalization

**Validation rules**:

- A package cannot be `ready` unless leakage status and timeline alignment pass.
- A package with `externalEgressStarted=true` is outside this feature's allowed
  scope.
- Final leakage truth is assigned only after recording stops.
- Derived artifacts must be registered in local retention/deletion accounting
  before `eligibleForTranscription=true`.

## OriginalTrack

Represents immutable package evidence such as `mic.wav` and `incoming.wav`.

**Fields**:

- `trackId`
- `role`: `local_mic` or `remote_speaker`
- `fileName`: `mic.wav` or `incoming.wav`
- `mediaScribeField`: `mic_file` or `incoming_file`
- `format`, `sampleRate`, `channelCount`, `bitsPerSample`
- `durationMs`, `byteCount`, `frameCount`
- `timelineStartMs`
- `timelineAligned`
- `failureReason`
- `evidenceRole`: `original`

**Validation rules**:

- Original tracks must not be overwritten by derived cleanup.
- `local_mic` cannot be treated as clean local-speaker truth when package
  leakage status is `leakage_detected`, `unproven`, or `not_measured`.

## DerivedCleanedTrack

Represents a post-recording artifact created from original evidence.

**Fields**:

- `trackId`
- `role`: usually `derived_local_mic`
- `fileName`
- `sourceTrackIds`
- `processorId`
- `processorVersion`
- `createdAt`
- `lineageHash`
- `confidence`
- `residualLeakageStatus`
- `residualThresholdVersion`
- `eligibleForTranscription`
- `retentionClass`
- `deletionScope`
- `localDeletionRegistered`
- `failureReason`

**Validation rules**:

- Must reference original source tracks.
- Must not replace `mic.wav` or `incoming.wav`.
- Can be transcription-eligible only when residual leakage evidence passes.
- Can be created or used only after local retention/deletion accounting knows
  the artifact file, lineage, retention class, and deletion scope.

## LeakageFinalization

Represents the authoritative package-level leakage result.

**Fields**:

- `status`: `clean`, `leakage_detected`, `unproven`, `not_measured`, or
  `not_applicable`
- `evaluatedAt`
- `thresholdVersion`
- `measurementAttempted`
- `measurementApplicable`
- `alignmentStatus`
- `confidence`
- `failureReason`
- `originalEvidenceStatus`
- `derivedArtifactStatus`
- `transcriptionGate`

**Validation rules**:

- `clean` requires `measurementAttempted=true`,
  `measurementApplicable=true`, reliable alignment, sufficient far-end-only
  evidence, and metrics below threshold.
- `leakage_detected` requires measurement evidence above threshold.
- `unproven` requires `measurementAttempted=true` but insufficient reliable
  proof.
- `not_measured` requires measurement skipped, unsupported, or inapplicable to
  this package shape.
- `not_applicable` is reserved for package/artifact types where speaker-to-mic
  leakage cannot apply.

## LeakageMeasurement

Metadata-only metrics used by finalization.

**Fields**:

- `measurementId`
- `windowCount`
- `farEndOnlyWindowMs`
- `doubleTalkExcludedWindowMs`
- `alignmentOffsetMs`
- `alignmentDriftMs`
- `leakageLevelDb`
- `correlationPeak`
- `correlationLagMs`
- `directLoopbackSuspicion`
- `acousticLeakageSuspicion`
- `clippingObserved`
- `dropoutObserved`
- `confidence`

**Validation rules**:

- Must not include raw audio, transcript text, participant names, or meeting
  content.
- Must include enough reason codes to distinguish contamination from
  unmeasurable evidence.

## RecordingRouteMetadata

Safe route facts captured for finalization evidence.

**Fields**:

- `inputRouteClass`
- `outputRouteClass`
- `outputVolumeBucket`
- `muteState`
- `browserTarget`
- `routeChangeCount`
- `coreaudiodState`
- `sleepWakeObserved`
- `selfRoutingRejected`

**Validation rules**:

- Used only as evidence after finalization in this feature.
- Must not create live route readiness or user-facing blockers.
- Must avoid live absolute device/user paths and secrets.

## ThresholdVersion

Named rule set used to interpret leakage measurement.

**Fields**:

- `id`: `leakage-threshold.v1`
- `timelineToleranceMs`: `1000`
- `minimumFarEndOnlyWindowMs`: `15000`
- `maximumLeakageLevelDb`: `-45.0`
- `maximumCorrelationPeak`: `0.12`
- `minimumConfidence`: `0.80`
- `maximumAlignmentDriftMs`: `250`
- `minimumDerivedConfidence`: `0.85`
- `maximumDerivedResidualLeakageDb`: `-50.0`
- `doubleTalkPolicy`
- `derivedResidualPolicy`

**Validation rules**:

- Every finalization result must record the threshold version used.
- Changing thresholds must create a new version so old evidence remains
  understandable.
- Implementations must not silently retune `leakage-threshold.v1`; any changed
  acceptance value requires a new threshold version.

## State Transitions

```text
recording_in_progress
  -> stopped
  -> finalization_started
  -> finalization_completed(clean)
  -> finalization_completed(leakage_detected)
  -> finalization_completed(unproven)
  -> finalization_completed(not_measured)
  -> finalization_completed(not_applicable)
  -> derived_cleanup_created(optional)
  -> derived_cleanup_validated(optional)
```

Transcription readiness can become `ready` only from `finalization_completed`
with `clean` original evidence or a validated derived cleaned track. All other
leakage states remain `degraded` or `failed`.
