# Recording Artifact Format Gate (010)

This gate controls acceptance of local recording artifacts as MediaScribe-ready
dual-track packages. It does not accept upload, resumable ingest, MediaScribe
job submission, polling, result import, dashboard publication, retention,
deletion, encryption, or assisted auto-start.

## Required Evidence Before Acceptance

- [x] Manual `Record`/`Stop` creates `mic.wav` and `incoming.wav`.
- [x] `mic.wav` is WAV PCM signed 16-bit little-endian, mono, 16000 Hz.
- [x] `incoming.wav` is WAV PCM signed 16-bit little-endian, mono, 16000 Hz.
- [x] Manifest maps `local_mic` to future MediaScribe `mic_file`.
- [x] Manifest maps `remote_speaker` to future MediaScribe `incoming_file`.
- [x] Manifest records transcription readiness and degraded/failed reasons.
- [x] Silence/timeline alignment is preserved or truthfully degraded.
- [x] Diagnostics remain metadata-only and redacted.
- [x] Desktop does not read or expose `MEDIASCRIBE_API_KEY`.
- [x] No upload, MediaScribe request, Langfuse trace, dashboard publication, or
  external egress starts in this feature.
- [x] Existing `007` and `008` validation gates still pass.

## Automated Validation Log

| Gate | Command | Result | Notes |
|---|---|---|---|
| Swift tests | `swift test --package-path apps/macos --disable-swift-testing` | Passed | 2026-06-04 00:22 MSK: build/test target completed. |
| Contract validation | `swift run --package-path apps/macos ContractValidation` | Passed | 2026-06-04 00:22 MSK: local manifest and artifact-format fixtures accepted. |
| Realtime safety | `sh tests/macos/static/audio-rt-safety-check.sh` | Passed | 2026-06-04 00:22 MSK: realtime callback safety scan accepted. |
| 010 validation script | `sh apps/macos/Scripts/validate-recording-artifact-format.sh` | Passed | 2026-06-04 00:22 MSK: Swift tests, contract validation, realtime safety, and fixture check passed. |
| Secret/content scan | `rg ...` forbidden-content scan | Passed | 2026-06-04 00:22 MSK: matches are policy, fixture, validation, and redaction-test strings only; no live secret, raw audio, transcript text, or meeting content found. |
| 007 regression | `sh apps/macos/Scripts/validate-capture-session-indicator.sh` | Passed | 2026-06-04 00:22 MSK: existing visible manual recording gate still passes. |
| 008 regression | `sh apps/macos/Scripts/validate-local-recording-persistence.sh` | Passed | 2026-06-04 00:22 MSK: existing local persistence gate still passes. |

## Manual Smoke Log

See `tests/macos/local-recording/recording-artifact-format-smoke.md`.

## Current Acceptance

Status: Accepted for local artifact format. Automated 010 gates pass for the
MediaScribe-ready artifact model, contract, diagnostics, and writer behavior.
Manual smoke on 2026-06-04 MSK confirmed a fresh workspace bundle created
`mic.wav`, `incoming.wav`, and `manifest.json` from a real `Record`/`Stop` flow
with manifest readiness `ready` and source mode `dual`.
