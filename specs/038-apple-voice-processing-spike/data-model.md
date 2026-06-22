# Data Model: Apple Voice Processing Spike

## AppleProcessingCandidate

Represents one Apple native processing path evaluated by the spike.

### Fields

- `candidateId`: Stable local identifier for the candidate run.
- `candidateKind`: `appOwnedGraphVoiceProcessing`, `voiceProcessingIO`, or
  `micModeGuidance`.
- `routeClass`: Built-in speakerphone, wired/headphones, USB headset,
  Bluetooth/AirPods-class, or unknown.
- `inputDeviceSummary`: Metadata-safe input identity from `037`.
- `outputDeviceSummary`: Metadata-safe output route identity.
- `farEndReferenceVisibility`: `sameOutput`, `differentOutput`,
  `notVisible`, `notMeasured`, or `unknown`.
- `appOwnership`: `proven`, `partial`, `userSystemControlled`, `notOwned`, or
  `unknown`.
- `enabledState`: `enabled`, `unavailable`, `failedToEnable`, `notAttempted`, or
  `unknown`.
- `failureReason`: Bounded metadata-safe reason when not accepted.
- `diagnosticSafe`: Always `true`.

### Validation Rules

- Built-in speakerphone acceptance requires `routeClass = builtInSpeakerphone`,
  `farEndReferenceVisibility = sameOutput`, and `appOwnership = proven`.
- `micModeGuidance` cannot produce clean acceptance unless deterministic app
  ownership is separately proven.
- Unknown route, reference, or ownership evidence cannot be accepted.
- Candidate metadata must not include raw audio, transcript text, participant
  names, private paths, credentials, signed URLs, or meeting content.

## AppleProcessingValidationRow

One route/scenario validation row with baseline and processed evidence.

### Fields

- `rowId`: Stable row identifier.
- `scenario`: `farEndOnly`, `nearEndOnly`, `doubleTalk`, `loudSpeaker`,
  `routeChange`, `stopQuit`, `browserMeeting`, or `diagnosticRedaction`.
- `routeClass`: Route under test.
- `baselineLeakageStatus`: Existing leakage status before processing.
- `processedLeakageStatus`: Candidate leakage status after processing.
- `residualLeakageSummary`: Bounded threshold/correlation/intelligibility
  summary, not raw samples.
- `speechPreservationStatus`: `preserved`, `degraded`, `suppressed`,
  `notMeasured`, or `unknown`.
- `alignmentStatus`: `accepted`, `degraded`, `failed`, or `notMeasured`.
- `stabilityStatus`: `accepted`, `blockedRouteTopology`, `blockedStability`,
  `blockedQuality`, `unproven`, or `notMeasured`.
- `evidenceLocation`: Metadata-only path or reference inside the feature
  evidence directory.

### Validation Rules

- Every required row must include baseline and processed/candidate status.
- `processedLeakageStatus = clean` is not enough for acceptance unless speech
  preservation, alignment, stability, and package lineage also pass.
- Missing baseline or missing processed evidence makes the row `unproven`.
- Evidence references must point to metadata-only files.

## ProcessedMicrophoneEvidence

Metadata-only evidence about processed near-end microphone behavior.

### Fields

- `candidateId`: Links to `AppleProcessingCandidate`.
- `sourceGraph`: `appOwnedMicrophoneGraph`, `systemMicMode`, `testRecorder`, or
  `unknown`.
- `feedsLiveMicrophonePath`: `proven`, `notProven`, or `notApplicable`.
- `feedsPersistedMicArtifact`: `proven`, `notProven`, or `notApplicable`.
- `preservesOriginalMicArtifact`: Boolean.
- `manifestLineageStatus`: `originalOnly`, `candidateMetadata`,
  `derivedCandidate`, `contradictory`, or `missing`.
- `timingConfidence`: `usable`, `degraded`, `missing`, or `unknown`.
- `formatStability`: `stable`, `changedButSupported`, `unsupportedChanged`, or
  `unknown`.
- `diagnosticSafe`: Always `true`.

### Validation Rules

- Accepted built-in speakerphone requires both live path and persisted artifact
  lineage to be `proven`.
- `testRecorder` source cannot prove product acceptance.
- `contradictory` or `missing` manifest lineage fails closed.
- Original mic evidence must remain traceable until a later spec changes package
  semantics.

## AppleProcessingOutcome

Final decision record for the spike.

### Values

- `accepted_for_builtin_speakerphone`: Built-in mic/speakers pass all required
  quality, lineage, stability, and metadata-only gates.
- `accepted_for_guidance_only`: Apple/Mic Mode evidence can help guide users but
  cannot be relied on for clean package acceptance.
- `accepted_for_headset_routes_only`: Apple processing is unnecessary or narrow;
  headset/wired routes remain the clean route story.
- `blocked_route_topology`: The product cannot insert Apple processing into the
  owned recording route without breaking ownership or timing.
- `blocked_quality`: Apple processing runs but fails leakage or double-talk
  quality gates.
- `blocked_stability`: Apple processing causes no-hang, route, crash, channel,
  latency, or resource-release instability.
- `defer_to_webrtc_aec3`: Apple processing is insufficient and the evidence
  supports moving to `039`.

### Validation Rules

- Exactly one primary outcome is required before implementation closeout.
- Accepted outcomes must link to complete validation rows.
- Blocked/deferred outcomes must include a safe failure reason and next-step
  recommendation.
- No outcome may claim MediaScribe readiness or production rollout without
  existing package and leakage gates.
