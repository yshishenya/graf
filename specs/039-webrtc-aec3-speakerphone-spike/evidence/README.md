# Evidence: WebRTC AEC3 Speakerphone Spike

This directory stores metadata-only validation evidence for feature
`039-webrtc-aec3-speakerphone-spike`.

## Safe Evidence Rules

- Do not store raw audio, debug clips, waveform dumps, WebRTC trace dumps,
  transcripts, meeting content, participant identifiers, credentials, tokens,
  signed URLs, passwords, live local paths, or screenshots containing private
  data.
- Use route classes, scenario families, stable reason codes, outcome values,
  counters, durations, booleans, threshold profile ids, redacted package ids,
  and redacted device classes.
- If a manual run needs to refer to a local package, use a redacted package id
  such as `recording-package-001`, not a real filesystem path.
- Evidence may record whether `mic.wav`, `incoming.wav`, and `manifest.json`
  existed and stayed traceable, but must not embed their contents.
- Supporting USB, wired, Bluetooth, AirPods, or browser rows are evidence only;
  they must not broaden the `039` promotion scope.

## Files

- `test-results.md`: focused SwiftPM checks, AEC3 helper modes, existing
  recording/package checks, local CI, and review notes.
- `manual-runtime-matrix.md`: controlled real-hardware rows for built-in
  speakerphone, Stop/quit, route/reference changes, rollback, app status,
  diagnostics, and supporting routes.
- `decision-record.md`: final single-outcome decision with limitations,
  fallback-to-040 state, supporting-row summary, and no-broadened-claim note.

## Acceptance Boundary

This feature evaluates WebRTC AEC3 as a bounded candidate for built-in Mac
microphone plus built-in Mac speakers. It does not prove a broad clean-recording
claim, production rollout, direct desktop upload to MediaScribe, or route
promotion for Bluetooth, AirPods, USB, wired, browser, external display, or
other non-built-in speakerphone paths.

## Closeout Summary

Final metadata-only decision: `defer_to_fallback_decision`.

Fallback path: `040-speakerphone-recording-fallback-decision`.

The app now has visible AEC3 status states for blocked, rollback,
fallback-relevant, evaluating, original-truth, promoted, and attention cases.
These statuses are informational and calm: they do not hide active capture or
Stop, do not expose private meeting content, and do not claim clean recording
unless every immediate-promotion gate is satisfied.
