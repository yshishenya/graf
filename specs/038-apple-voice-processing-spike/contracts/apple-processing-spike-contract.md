# Contract: Apple Processing Spike Result

## Purpose

Define the metadata-only result shape required before `038` can claim an Apple
processing outcome.

## Required Result Fields

| Field | Required | Allowed Values / Notes |
|---|---:|---|
| `feature` | yes | `038-apple-voice-processing-spike` |
| `candidateId` | yes | Stable local id, no private content |
| `candidateKind` | yes | `appOwnedGraphVoiceProcessing`, `voiceProcessingIO`, `micModeGuidance` |
| `routeClass` | yes | Built-in speakerphone, wired/headphones, USB headset, Bluetooth/AirPods-class, unknown |
| `scenario` | yes | Far-end-only, near-end-only, double-talk, loud speaker, route change, browser meeting, Stop/quit, diagnostics |
| `baselineStatus` | yes | Existing leakage/package status before processing |
| `candidateStatus` | yes | Processed/candidate status after processing |
| `lineageStatus` | yes | Live path, persisted mic artifact, incoming reference, and manifest relation |
| `speechPreservationStatus` | yes | Preserved, degraded, suppressed, not measured, unknown |
| `alignmentStatus` | yes | Accepted, degraded, failed, not measured |
| `stabilityStatus` | yes | Accepted, blocked route topology, blocked quality, blocked stability, unproven, not measured |
| `diagnosticSafe` | yes | Must be `true` |
| `failureReason` | no | Required for blocked, deferred, unproven, or not-measured rows |

## Acceptance Rules

- Built-in speakerphone cannot be accepted unless all required route/scenario
  rows are present and accepted.
- A row with missing baseline, missing candidate evidence, missing lineage, or
  missing diagnostic safety is `unproven`.
- A row with local speech suppression during double-talk is `blocked_quality`.
- A row with crash, hang, Stop/quit regression, or route disappearance is
  `blocked_stability`.
- A row where Apple processing cannot see the same output that reaches physical
  speakers is `blocked_route_topology` or `accepted_for_guidance_only`.

## Forbidden Content

Spike result records must not include:

- raw audio samples or clips;
- transcript text or inferred meeting content;
- participant names or private meeting identifiers;
- signed URLs, credentials, tokens, passwords, or secret paths;
- live local filesystem paths outside bounded feature evidence references.
