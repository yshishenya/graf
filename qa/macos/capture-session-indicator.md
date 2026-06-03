# Capture Session Indicator Gate (007)

This gate controls acceptance of manual local recording start/stop and visible
capture indication. It does not accept upload, transcription, dashboard notes,
retention, deletion, or assisted auto-start.

## Required Evidence Before Acceptance

- [x] Manual Record starts only from valid route evidence.
- [x] Recording start is blocked from publication-only, stale, blocked, failed,
  fallback, or unknown route evidence.
- [x] Active recording shows persistent local visible indicator.
- [x] Active recording exposes one-action Stop.
- [x] Stop transitions active recording to stopping/stopped within 1 second in
  local validation.
- [x] Recording stops or fails closed when every visible local indicator becomes
  unavailable.
- [x] Blocked starts record concrete policy, permission, route, storage, or
  indicator reason.
- [x] Evidence is metadata-only and redacted.
- [x] Non-recording passthrough remains usable after recording stops.
- [x] No upload, transcription, MediaScribe, Langfuse, dashboard publication, or
  external egress starts in this feature.

## Automated Validation Log

| Gate | Command | Result | Notes |
|---|---|---|---|
| Swift tests | `swift test --package-path apps/macos --disable-swift-testing` | Passed | Local unit/build test run completed. |
| Contract validation | `swift run --package-path apps/macos ContractValidation` | Passed | Recording evidence fixture accepted. |
| Realtime safety | `sh tests/macos/static/audio-rt-safety-check.sh` | Passed | No realtime callback regression detected. |
| 007 validation script | `sh apps/macos/Scripts/validate-capture-session-indicator.sh` | Passed | Runs Swift tests, contract validation, and realtime safety scan. |
| Secret/content scan | `rg ...` forbidden-content scan | Passed | Matches are policy, fixture, and redaction-test forbidden-field strings only; no live secret, raw audio, transcript text, or meeting content found. |

Latest refresh:

- 2026-06-02 01:48 MSK on `master`: `sh apps/macos/Scripts/validate-capture-session-indicator.sh`
  passed with `capture_session_indicator_validation=passed`.

## Manual Smoke Log

See `tests/macos/browser-meetings/manual-recording-smoke.md`.

## Current Acceptance

Status: Automated 007 gates passed for local manual recording lifecycle and
visible indicator safety. User-confirmed 1-minute manual recording smoke passed
for Yandex Telemost, Chrome, Opera, and Zoom on 2026-06-02. Yandex Browser
remains not accepted in the current cycle.

## Passthrough After Stop

No code change was required in
`apps/macos/RecApp/Sources/Capture/PassthroughRouteEngine.swift` for this
feature. Manual recording stop is handled in the capture session controller and
does not stop or tear down the existing non-recording passthrough route.
