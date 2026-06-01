# Local Recording Persistence Gate (008)

This gate controls acceptance of local recording artifacts after manual
`Record`/`Stop`. It does not accept upload, transcription, MediaScribe,
Langfuse, dashboard publication, retention, deletion, encryption, or assisted
auto-start.

## Required Evidence Before Acceptance

- [x] Manual `Record` starts local persistence only after recording prerequisites pass.
- [x] Manual `Stop` finalizes a local recording manifest.
- [x] Local mic and remote speaker tracks are represented separately.
- [x] Missing or empty required tracks are degraded or failed, not complete.
- [x] The app exposes the local recording location after stop.
- [x] Local recording diagnostics are metadata-only and redacted.
- [x] No upload, transcription, MediaScribe, Langfuse, dashboard publication, or external egress starts in this feature.
- [x] Non-recording passthrough remains outside writer stop/finalization.

## Automated Validation Log

| Gate | Command | Result | Notes |
|---|---|---|---|
| Swift tests | `swift test --package-path apps/macos --disable-swift-testing` | Passed | Build/test target completed. |
| Contract validation | `swift run --package-path apps/macos ContractValidation` | Passed | Local recording manifest fixture accepted. |
| Realtime safety | `sh tests/macos/static/audio-rt-safety-check.sh` | Passed | Existing realtime callback safety scan accepted. |
| 008 validation script | `sh apps/macos/Scripts/validate-local-recording-persistence.sh` | Passed | Swift tests, contract validation, realtime safety, and manifest fixture check passed. |
| Secret/content scan | `rg ...` forbidden-content scan | Passed | Matches are policy, fixture, and redaction-test forbidden-field strings only; no live secret, raw audio, transcript text, or meeting content found. |

## Manual Smoke Log

See `tests/macos/local-recording/local-recording-smoke.md`.

## Manual Smoke Evidence

- 2026-06-02 01:19 MSK: User ran the freshly rebuilt
  `apps/macos/RecApp/.build/2brain Rec.app`, pressed `Record`, pressed `Stop`,
  and confirmed that a local recording exists. This accepts the local artifact
  presence smoke for feature `008`; upload, transcription, dashboard,
  retention, deletion, encryption, and assisted auto-start remain out of scope.

## Current Acceptance

Status: Automated 008 gates passed and fresh local app bundle launched from
`apps/macos/RecApp/.build/2brain Rec.app`. User-confirmed local recording
artifact presence after manual `Record`/`Stop` is accepted for this slice.
Meeting-target smoke remains pending and must record metadata-only evidence
before broader recording release acceptance.

## Passthrough After Stop

No code change was required in
`apps/macos/RecApp/Sources/Capture/PassthroughBridge.swift` for writer stop.
The local writer finalizes app-owned files and does not stop the existing
non-recording passthrough route.
