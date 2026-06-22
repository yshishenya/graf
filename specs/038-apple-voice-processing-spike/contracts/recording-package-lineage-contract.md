# Contract: Recording Package Lineage

## Purpose

Ensure Apple processing evidence does not create a false split between live
microphone behavior and saved recording truth.

## Package Truth Requirements

- Original `mic.wav`, `incoming.wav`, and `manifest.json` remain traceable for
  every candidate run.
- Existing leakage finalization remains authoritative for clean,
  leakage-detected, unproven, and not-measured package status.
- Candidate processed evidence must be labeled as one of:
  - `originalOnly`;
  - `candidateMetadata`;
  - `derivedCandidate`;
  - `guidanceOnly`;
  - `unproven`;
  - `blocked`.
- A candidate cannot affect transcription readiness unless a later spec
  explicitly accepts derived artifact semantics and deletion lifecycle
  accounting.

## Lineage Gate

An accepted Apple processing candidate must prove all of the following:

1. The processed near-end signal is the signal used by the product's live
   microphone path, when live microphone routing is part of the validation.
2. The same processed near-end signal feeds, or is explicitly represented in,
   the persisted microphone artifact lineage.
3. The far-end reference is the same signal class that reaches the physical
   speakers.
4. `incoming.wav` and microphone evidence remain aligned within accepted
   recording tolerance.
5. The manifest labels original and candidate evidence without contradiction.

## Failure Rules

- Internal-only processed test recordings are `unproven` for product acceptance.
- User/system Mic Mode observations are `guidanceOnly` unless app ownership is
  proven.
- Missing incoming reference, protected/silent reference, unsupported format
  change, or route-topology ambiguity fails closed.
- A package can have improved Apple candidate evidence and still remain blocked
  by leakage finalization.
