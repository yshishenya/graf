# Evidence: Microphone Sample Graph Foundation

This directory stores metadata-only validation evidence for feature
`037-microphone-sample-graph-foundation`.

## Safe Evidence Rules

- Do not store raw audio, debug audio clips, waveform dumps, transcripts,
  private meeting content, participant identifiers, credentials, tokens, signed
  URLs, passwords, live local paths, or screenshots containing private data.
- Use stable reason codes, status values, counters, durations, booleans, and
  redacted file/package identifiers.
- If a manual run needs to refer to a local package, use a redacted package id
  such as `recording-package-001`, not a real filesystem path.
- Evidence may describe whether `mic.wav`, `incoming.wav`, and `manifest.json`
  existed, but must not embed their contents.

## Files

- `manual-runtime-matrix.md`: manual selected/default microphone, failure,
  Stop/quit, package, and leakage scenarios.
- `test-results.md`: focused tests, package checks, diagnostics checks, CPU
  gates, and local CI results.

## Acceptance Boundary

This feature proves an app-owned microphone stream foundation. It does not prove
Apple voice processing, WebRTC AEC3, a clean built-in speakerphone fallback, or
recording-readiness onboarding.
