# Contract: WebRTC AEC3 Spike Result

## Purpose

Define the metadata-only result shape required before `039` can claim a WebRTC
AEC3 outcome.

## Required Result Fields

| Field | Required | Allowed Values / Notes |
|---|---:|---|
| `feature` | yes | `039-webrtc-aec3-speakerphone-spike` |
| `candidateId` | yes | Stable local id, no private content |
| `candidateKind` | yes | `nativeWebRTCAEC3`, `adapterUnavailable`, `dependencyBlocked`, `offlineCorpusOnly` |
| `routeClass` | yes | `builtInSpeakerphone`, `wiredHeadphones`, `usbHeadset`, `bluetoothAirPodsClass`, `browserTargetSupporting`, `unknown` |
| `promotionScope` | yes | `builtInMacMicAndSpeakers` or `notPromotable` |
| `scenarioFamily` | yes | `farEndOnlyLeakage`, `nearEndOnlySpeech`, `doubleTalk`, `loudSpeakerClipping`, `routeChangeTimingStress`, `unsafeReferenceNegativeControl`, `stopQuit`, `diagnostics`, `appStatus` |
| `validationKind` | yes | `slice`, `fullFile`, `longFormFullFile`, `controlledRealHardware`, `negativeControl`, `stopQuit`, `diagnostics`, `appStatus` |
| `baselineStatus` | yes | Existing leakage/package status before AEC3 |
| `candidateStatus` | yes | `accepted`, `degraded`, `blocked`, `unproven`, `notMeasured` |
| `lineageStatus` | yes | `originalOnly`, `candidateMetadata`, `derivedCandidate`, `promotedBuiltinRoute`, `rolledBackToOriginal`, `blocked`, `unproven` |
| `referenceStatus` | yes | `present`, `missing`, `late`, `protected`, `silent`, `clipped`, `notRepresentative`, `unknown` |
| `timingConfidence` | yes | `safe`, `degraded`, `failed`, `notMeasured`, `unknown` |
| `speechPreservationStatus` | yes | `preserved`, `degraded`, `suppressed`, `notMeasured`, `unknown` |
| `residualLeakageStatus` | yes | `clean`, `leakageDetected`, `unproven`, `notMeasured`, `notApplicable` |
| `stabilityStatus` | yes | `accepted`, `blockedRouteTopology`, `blockedQuality`, `blockedStability`, `rollbackRequired`, `unproven`, `notMeasured` |
| `thresholdProfileId` | yes | Versioned profile declared before validation begins |
| `thresholdSummary` | yes | Bounded pass/block summaries only, no raw audio/content |
| `appStatusState` | yes | Current app status state or `notApplicable` |
| `diagnosticSafe` | yes | Must be `true` |
| `failureReason` | conditional | Required for blocked, rolled back, deferred, unproven, or not-measured rows |

## Immediate Promotion Rules

- `accepted_for_immediate_promotion` is valid only for built-in Mac microphone
  plus built-in Mac speakers.
- Every required scenario family must have at least ten full-file validations
  and at least fifty sliced-window validations.
- Every required scenario family must include at least two full-file runs of 20
  minutes or more.
- Controlled real-hardware app recording rows must pass for far-end-only,
  near-end-only, double-talk, loud-speaker/clipping, route-change/timing,
  unsafe-reference, Stop/quit, diagnostics, app-status, and rollback scenarios.
- App status rows must prove that candidate, blocked, rollback, and
  fallback-relevant states are visible and consistent with package truth.
- A single declared acceptance-threshold profile must be used consistently for
  all promoted rows; changing the profile requires rerunning affected evidence.
- Licensing, patent-grant review, packaging, signing, and notarization readiness
  must be recorded as passing.

## Failure Rules

- Missing or unsafe render reference is `blocked_route_topology` or `unproven`.
- Unsafe capture/render call ordering, delay, jitter, or drift is
  `blocked_stability` or `rollbackRequired`.
- Local speech suppression during near-end or double-talk scenarios is
  `blocked_quality`.
- Favorable non-built-in route evidence cannot broaden promotion scope.
- Offline corpus success without controlled app recording remains unproven for
  immediate promotion.
- Missing, late, or changed acceptance-threshold profile makes the row
  `unproven` for immediate promotion.
- Any raw content or unsafe diagnostics makes the row `blocked_stability`.

## Forbidden Content

Spike result records must not include:

- raw audio samples, clips, or debug WAVs;
- transcript text or inferred meeting content;
- participant names, private meeting identifiers, or real account identifiers;
- signed URLs, credentials, tokens, passwords, object keys, or secret paths;
- live local filesystem paths outside bounded feature evidence references.
