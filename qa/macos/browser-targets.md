# macOS Browser Target Matrix

## Purpose

Track browser and meeting-app recording coverage for the app-owned capture
architecture. Meeting apps use their normal microphone and speaker settings;
GRAF captures system audio through `SystemAudioCaptureService` and captures the
selected physical microphone through `MicrophoneCaptureService`.

## Current Targets

| Target | Support scope | Cleanup-slice status |
|---|---|---|
| Chrome browser meetings | Official MVP target | Manual recording smoke must be rerun |
| Opera browser meetings | Official MVP target | Manual recording smoke must be rerun |
| Yandex Browser meetings | Official MVP target, not previously accepted | Not accepted until rerun |
| Yandex Telemost in browser | Official MVP target | Manual recording smoke must be rerun |
| Zoom | Best-effort additional evidence | Manual recording smoke must be rerun |

Previous smoke results remain historical evidence only. Removing the retired
audio-routing implementation requires a fresh current-build smoke before any
target is called release-ready.

## Required Assertions

- Manual `Record` starts only after microphone and system-audio permissions,
  storage, visible-indicator, policy, and source-eligibility gates pass.
- One shared canonical timeline contains the app-owned microphone and
  system-audio contribution without creating separate source files.
- One-action `Stop` finalizes the canonical WAV, review M4A and
  `manifest.json`.
- Only the canonical WAV reaches one transcription job; the review M4A never
  reaches ASR.
- A meeting-app mute does not get inferred from route selection; mute truth
  follows the dedicated meeting-mute policy.
- No browser-specific audio-device setup is required by GRAF.
- Skipped or unavailable targets are recorded as `blocked` or
  `not_accepted`, never as passed.

## Evidence

- Automated contract: `BrowserTargetEvidenceTests`.
- Current recording smoke:
  `tests/macos/browser-meetings/manual-recording-smoke.md`.
- Recording package checks:
  `SystemAudioRecordingPackageTests`.
