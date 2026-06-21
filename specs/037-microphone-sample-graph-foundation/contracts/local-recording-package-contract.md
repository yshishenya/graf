# Contract: Local Recording Package Compatibility

## Purpose

Preserve the accepted `025` local package and `020` leakage truth while adding
microphone stream metadata.

## Required Artifacts

- `mic.wav`
- `incoming.wav`
- `manifest.json`

## Required Track Truth

- Exactly one original `localMic` track for `mic.wav`.
- Exactly one original `remoteSpeaker` track for `incoming.wav`.
- Accepted tracks remain `wav-pcm-s16le`, 16 kHz, mono, timeline start `0`, and
  timeline-aligned.
- Accepted package `durationDifferenceSeconds <= 3`.

## Required Manifest Truth

- Existing scope approval, permission snapshot, capture health, recording
  timeline evidence, privacy segment, mute truth, and leakage finalization fields
  remain compatible.
- New microphone selection/stream metadata is optional for older manifests and
  required for accepted `037` graph-readiness evidence.
- `externalEgressStarted = false` and `transcriptionStarted = false` remain true
  for local desktop recording before upload/transcription workflows.
- Leakage finalization remains authoritative for `clean`,
  `leakage_detected`, `unproven`, `not_measured`, `not_applicable`, and derived
  cleanup readiness.

## Failure Truth

- A healthy app-owned microphone stream does not override leakage detected or
  leakage unproven states.
- Missing/empty/silent/wrong-device microphone evidence must degrade, block, or
  fail the package according to existing status semantics.
- Legacy recorder fallback must not satisfy future cleanup readiness.

## Forbidden

- Do not create derived cleaned audio tracks in this feature.
- Do not change server upload or MediaScribe field names.
- Do not add raw audio, transcript text, credentials, tokens, signed URLs,
  private meeting content, live local paths, or participant identifiers to the
  manifest or diagnostics.
