# Data Model: WebRTC AEC3 Speakerphone Spike

## WebRTCAEC3Candidate

Represents one AEC3 candidate under evaluation.

### Fields

- `candidateId`: Stable local identifier for the candidate run.
- `feature`: Always `039-webrtc-aec3-speakerphone-spike`.
- `candidateKind`: `nativeWebRTCAEC3`, `adapterUnavailable`,
  `dependencyBlocked`, or `offlineCorpusOnly`.
- `routeClass`: `builtInSpeakerphone`, `wiredHeadphones`, `usbHeadset`,
  `bluetoothAirPodsClass`, `browserTargetSupporting`, or `unknown`.
- `promotionScope`: `builtInMacMicAndSpeakers` or `notPromotable`.
- `dependencyReadiness`: `ready`, `unavailable`, `licenseBlocked`,
  `packagingBlocked`, `signingBlocked`, or `unknown`.
- `renderReferenceStatus`: `present`, `missing`, `late`, `protected`,
  `silent`, `clipped`, `notRepresentative`, or `unknown`.
- `captureTimingStatus`: `safe`, `jittery`, `delayed`, `callOrderUnsafe`,
  `drifted`, or `unknown`.
- `metricsStatus`: `available`, `partial`, `notAvailable`, or `unknown`.
- `thresholdProfileId`: Versioned acceptance-threshold profile used for
  validation.
- `diagnosticSafe`: Always required to be `true`.
- `failureReason`: Bounded reason code when not accepted.

### Validation Rules

- Immediate promotion requires `routeClass = builtInSpeakerphone`,
  `promotionScope = builtInMacMicAndSpeakers`, `dependencyReadiness = ready`,
  safe render reference, safe capture timing, complete metadata, a declared
  acceptance-threshold profile, and `diagnosticSafe = true`.
- Missing dependency, missing reference, unsafe call order, drift, unsafe
  diagnostics, or missing lineage fails closed.
- Non-built-in routes cannot be promoted by `039`.

## WebRTCAEC3AcceptanceThresholdProfile

The versioned pass/block profile declared before validation begins.

### Fields

- `thresholdProfileId`: Stable id and version.
- `appliesToFeature`: Always `039-webrtc-aec3-speakerphone-spike`.
- `residualLeakageGate`: Bounded acceptance rule summary.
- `speechPreservationGate`: Bounded acceptance rule summary.
- `doubleTalkGate`: Bounded acceptance rule summary.
- `timingDriftGate`: Bounded acceptance rule summary.
- `clippingDropoutGate`: Bounded acceptance rule summary.
- `cpuNoHangGate`: Bounded acceptance rule summary.
- `stopQuitGate`: Bounded acceptance rule summary.
- `diagnosticSafetyGate`: Bounded acceptance rule summary.
- `appStatusConsistencyGate`: Bounded acceptance rule summary.
- `rollbackTriggerGate`: Bounded acceptance rule summary.
- `declaredBeforeValidation`: Boolean.
- `diagnosticSafe`: Always required to be `true`.

### Validation Rules

- Immediate promotion requires one declared profile used consistently by every
  promoted row.
- Any profile change invalidates affected promotion evidence until those rows
  are rerun.
- Profile fields must be bounded summaries and must not include raw audio,
  transcript text, private meeting content, or private local paths.

## WebRTCAEC3ValidationCorpus

The lab-grade evidence set required before immediate promotion.

### Fields

- `corpusId`: Stable id for the corpus package.
- `scenarioFamilies`: Required set of `farEndOnlyLeakage`,
  `nearEndOnlySpeech`, `doubleTalk`, `loudSpeakerClipping`,
  `routeChangeTimingStress`, and `unsafeReferenceNegativeControl`.
- `fileCountByScenario`: Count of full files per scenario family.
- `sliceCountByFile`: Count of deterministic slices per file.
- `longFormRunCountByScenario`: Count of 20 minute or longer full-file runs.
- `roomConditionCount`: Number of distinct acoustic conditions.
- `deviceProfileCount`: Number of Mac/device profiles.
- `speakerVolumeLevelCount`: Number of volume buckets.
- `criticalGateFailures`: Count and reason summary.
- `thresholdProfileId`: Profile applied to the corpus.
- `diagnosticSafe`: Always required to be `true`.

### Validation Rules

- Immediate promotion requires at least ten files per required scenario family.
- Every file must have at least five deterministic slices and a full-file run.
- Every scenario family must include at least two 20 minute or longer full-file
  runs.
- Corpus must include at least two room conditions, two Mac/device profiles, and
  three speaker-volume levels.
- Corpus rows for immediate promotion must use the same declared
  acceptance-threshold profile.
- Any missing required row blocks promotion.

## WebRTCAEC3ValidationRow

One route, scenario, file, slice, or full-file validation result.

### Fields

- `rowId`: Stable row identifier.
- `candidateId`: Links to `WebRTCAEC3Candidate`.
- `corpusId`: Links to `WebRTCAEC3ValidationCorpus` when corpus-backed.
- `scenarioFamily`: One required scenario family.
- `validationKind`: `slice`, `fullFile`, `longFormFullFile`,
  `controlledRealHardware`, `negativeControl`, `stopQuit`, `diagnostics`, or
  `appStatus`.
- `routeClass`: Route under test.
- `baselineStatus`: Original microphone leakage/package status.
- `candidateStatus`: `accepted`, `degraded`, `blocked`, `unproven`, or
  `notMeasured`.
- `lineageStatus`: `originalOnly`, `candidateMetadata`, `derivedCandidate`,
  `promotedBuiltinRoute`, `rolledBackToOriginal`, `blocked`, or `unproven`.
- `speechPreservationStatus`: `preserved`, `degraded`, `suppressed`,
  `notMeasured`, or `unknown`.
- `residualLeakageStatus`: `clean`, `leakageDetected`, `unproven`,
  `notMeasured`, or `notApplicable`.
- `timingConfidence`: `safe`, `degraded`, `failed`, `notMeasured`, or
  `unknown`.
- `referenceStatus`: Same vocabulary as `renderReferenceStatus`.
- `stabilityStatus`: `accepted`, `blockedRouteTopology`, `blockedQuality`,
  `blockedStability`, `rollbackRequired`, `unproven`, or `notMeasured`.
- `thresholdProfileId`: Profile used to judge the row.
- `thresholdSummary`: Bounded pass/block summary for applicable gates.
- `diagnosticSafe`: Always required to be `true`.
- `failureReason`: Required for blocked, rolled back, unproven, or not-measured
  rows.

### Validation Rules

- Every required row must include baseline, candidate, lineage, speech
  preservation, residual leakage, timing, reference, stability, and diagnostic
  status.
- `residualLeakageStatus = clean` is insufficient without speech preservation,
  lineage, timing, reference, stability, route scope, rollback, and app status.
- Missing baseline or candidate evidence makes the row `unproven`.
- Missing or mismatched threshold profile makes the row `unproven`.
- Unsafe diagnostics makes the row `blockedStability`.

## ControlledRealHardwareRecordingEvidence

Metadata-only proof from the actual app recording path on a physical Mac.

### Fields

- `recordingEvidenceId`: Stable id for the proof row.
- `candidateId`: Links to `WebRTCAEC3Candidate`.
- `routeClass`: Must be `builtInSpeakerphone` for immediate promotion.
- `scenarioFamily`: Critical scenario under test.
- `packageLineageStatus`: `originalOnly`, `candidateMetadata`,
  `derivedCandidate`, `promotedBuiltinRoute`, `rolledBackToOriginal`, or
  `blocked`.
- `stopBehaviorStatus`: `available`, `blocked`, `failed`, or `notMeasured`.
- `appStatusShown`: Boolean.
- `thresholdProfileId`: Profile used to judge the recording row.
- `diagnosticSafe`: Always required to be `true`.
- `failureReason`: Bounded reason when not accepted.

### Validation Rules

- Immediate promotion requires 100% passing controlled real-hardware rows for
  far-end-only, near-end-only, double-talk, loud-speaker/clipping,
  route-change/timing, unsafe-reference, Stop/quit, diagnostics, app-status, and
  rollback scenarios.
- Rows must use consented test content or synthetic fixtures.
- Committed evidence must not include raw audio, transcripts, private meeting
  content, signed URLs, credentials, or private local paths.

## AEC3RollbackEvent

Metadata-only evidence that a promoted candidate was withdrawn.

### Fields

- `rollbackId`: Stable id.
- `candidateId`: Links to `WebRTCAEC3Candidate`.
- `trigger`: `routeChanged`, `referenceMissing`, `referenceUnsafe`,
  `qualityDropped`, `timingUnsafe`, `lineageIncomplete`, `diagnosticsUnsafe`,
  or `stopQuit`.
- `previousLineageStatus`: Expected to be `promotedBuiltinRoute`.
- `restoredLineageStatus`: Expected to be `originalOnly`.
- `cleanRecordingClaimRemoved`: Boolean.
- `appStatusShown`: Boolean.
- `thresholdProfileId`: Profile whose rollback triggers were applied.
- `occurredAt`: Timestamp.
- `diagnosticSafe`: Always required to be `true`.

### Validation Rules

- Unsafe runtime conditions after promotion require a rollback event.
- Rollback must restore original microphone truth and remove the clean-recording
  claim without hiding active capture or blocking Stop.

## AppRecordingStatus

The local user-facing status shown during recording.

### Fields

- `statusId`: Stable id.
- `candidateId`: Optional link to `WebRTCAEC3Candidate`.
- `state`: `notEvaluated`, `evaluatingAEC3`, `usingOriginalMicTruth`,
  `candidateBlocked`, `promotedBuiltinRoute`, `rolledBackToOriginal`,
  `fallbackRelevant`, or `requiresUserAttention`.
- `routeScope`: `builtInMacMicAndSpeakers`, `supportingRouteOnly`, or
  `notApplicable`.
- `copySafety`: `safe`, `tooTechnical`, `tooNoisy`, `stale`, or
  `inconsistentWithPackageTruth`.
- `actionHint`: `none`, `continueRecording`, `reviewStatus`, `useHeadphones`,
  `retryCheck`, or `stopAvailable`.
- `matchesPackageTruth`: Boolean.
- `diagnosticSafe`: Always required to be `true`.

### Validation Rules

- App status must match package truth.
- App status must never expose private content or unnecessary technical
  internals.
- Rollback and fallback-relevant states must be visible and calm.

## WebRTCAEC3Outcome

Final decision record for the spike.

### Values

- `accepted_for_immediate_promotion`
- `accepted_for_derived_candidate_only`
- `accepted_for_guidance_only`
- `blocked_route_topology`
- `blocked_quality`
- `blocked_stability`
- `defer_to_fallback_decision`

### Validation Rules

- Exactly one primary outcome is required before implementation closeout.
- `accepted_for_immediate_promotion` is valid only for built-in Mac microphone
  plus built-in Mac speakers and only when every lab-grade, full-file,
  real-hardware, rollback, app-status, license, and package-readiness gate
  passes.
- Blocked/deferred outcomes must include a safe failure reason and next-step
  recommendation.
- No outcome may broaden clean-recording claims beyond the 039 route.
