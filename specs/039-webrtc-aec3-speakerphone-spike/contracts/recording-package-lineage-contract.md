# Contract: Recording Package Lineage

## Purpose

Ensure WebRTC AEC3 evidence does not create a false split between live
microphone behavior, saved recording truth, upload readiness, and transcription
truth.

## Package Truth Requirements

- Original `mic.wav`, `incoming.wav`, and `manifest.json` remain traceable for
  every candidate run.
- Existing `020` leakage finalization remains authoritative for clean,
  leakage-detected, unproven, and not-measured package status until the
  immediate-promotion gate passes.
- Candidate evidence must be labeled as one of:
  - `originalOnly`;
  - `candidateMetadata`;
  - `derivedCandidate`;
  - `promotedBuiltinRoute`;
  - `rolledBackToOriginal`;
  - `guidanceOnly`;
  - `unproven`;
  - `blocked`.
- A candidate cannot affect transcription readiness unless the built-in route
  promotion gates and package-readiness gates both pass.
- Rollback restores original microphone truth and removes the clean-recording
  claim.

## Lineage Gate

An accepted WebRTC AEC3 immediate-promotion candidate must prove all of the
following:

1. The render reference is the same signal class that reaches physical built-in
   speakers.
2. The capture signal comes from the app-owned microphone path created by `037`.
3. Candidate timing remains aligned with original `mic.wav` and `incoming.wav`.
4. Original microphone and incoming evidence remain traceable after promotion.
5. The manifest labels original, candidate, promoted, and rollback evidence
   without contradiction.
6. The accepted rows use one declared acceptance-threshold profile.
7. App status matches the manifest/package truth.

## Failure Rules

- Internal-only or offline-only processed files are `unproven` for immediate
  promotion.
- Missing incoming reference, protected/silent reference, clipping, delay,
  jitter, route-topology ambiguity, or route change fails closed.
- Improved residual leakage still fails when local speech is suppressed,
  timing drifts, the threshold profile is missing or changed, app status is
  stale, or diagnostics are unsafe.
- A package can have useful AEC3 candidate evidence and still remain blocked by
  leakage finalization, route scope, app status, rollback, or license gates.
