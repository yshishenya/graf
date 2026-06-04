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

Latest refresh:

- 2026-06-02 01:48 MSK on `master`: `sh apps/macos/Scripts/validate-local-recording-persistence.sh`
  passed with `local_recording_persistence_validation=passed`.

## Manual Smoke Log

See `tests/macos/local-recording/local-recording-smoke.md`.

## Manual Smoke Evidence

- 2026-06-02 01:19 MSK: User ran the freshly rebuilt
  `apps/macos/RecApp/.build/2brain Rec.app`, pressed `Record`, pressed `Stop`,
  and confirmed that a local recording exists. This accepts the local artifact
  presence smoke for feature `008`; upload, transcription, dashboard,
  retention, deletion, encryption, and assisted auto-start remain out of scope.
- 2026-06-02 01:52 MSK: User recorded and checked a 1-minute local recording;
  the recording saves successfully. This accepts 1-minute local artifact
  persistence smoke for feature `008`; target-specific meeting smoke remains
  pending until recorded separately.
- 2026-06-02 02:02 MSK: User confirmed the 1-minute recording save check across
  Yandex Telemost, Chrome, Opera, and Zoom. This accepts target local recording
  persistence smoke for feature `008`; upload, transcription, dashboard,
  retention, deletion, encryption, assisted auto-start, and meeting-app mute
  truth remain out of scope.

## Current Acceptance

Status: Automated 008 gates passed and fresh local app bundle launched from
`apps/macos/RecApp/.build/2brain Rec.app`. User-confirmed local recording
artifact presence after manual `Record`/`Stop` and a user-confirmed 1-minute
saved recording across Yandex Telemost, Chrome, Opera, and Zoom are accepted for
this slice. Yandex Browser remains not accepted in the current cycle.

## Known Follow-Up

- Feature `022-meeting-mute-truth` tracks the unresolved meeting-app mute privacy
  boundary discovered during validation. Feature `008` accepts local artifact
  persistence only; it does not prove that speech is excluded from local mic
  artifacts when the user mutes inside Zoom, browser meeting targets, or other
  meeting apps.
- Future acceptance must define canonical mute truth evidence, unsupported-target
  behavior, muted interval artifact truth, user-facing limitation copy, and a QA
  target matrix before local recording can claim privacy-correct mute behavior.

## Passthrough After Stop

No code change was required in
`apps/macos/RecApp/Sources/Capture/PassthroughBridge.swift` for writer stop.
The local writer finalizes app-owned files and does not stop the existing
non-recording passthrough route.
