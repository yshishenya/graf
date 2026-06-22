# Evidence: Apple Voice Processing Spike

This directory stores metadata-only validation evidence for feature
`038-apple-voice-processing-spike`.

## Safe Evidence Rules

- Do not store raw audio, debug audio clips, waveform dumps, transcripts,
  private meeting content, participant identifiers, credentials, tokens, signed
  URLs, passwords, live local paths, or screenshots containing private data.
- Use route classes, stable reason codes, outcome values, counters, durations,
  booleans, redacted package identifiers, and redacted device classes.
- If a manual run needs to refer to a local package, use a redacted package id
  such as `recording-package-001`, not a real filesystem path.
- Evidence may record whether `mic.wav`, `incoming.wav`, and `manifest.json`
  existed and stayed traceable, but must not embed their contents.
- Candidate Apple processing evidence must be labeled as original, processed,
  guidance-only, unproven, blocked, or deferred. Do not imply a clean
  speakerphone route unless all accepted gates pass.

## Files

- `manual-runtime-matrix.md`: required manual route and scenario rows for
  built-in speakerphone, headset-class routes, browser target, Stop/quit, route
  changes, and diagnostics.
- `test-results.md`: focused SwiftPM checks, package inspection, CPU/no-hang,
  diagnostic redaction, local CI, and issue-sync evidence.
- `decision-record.md`: final single-outcome decision template for accepted,
  guidance-only, headset-only, blocked, or WebRTC-deferred states.

## Acceptance Boundary

This feature evaluates Apple native voice processing as a bounded candidate. It
does not implement WebRTC AEC3, automatic fallback mixing, production rollout,
or clean built-in speakerphone wording unless built-in speakerphone, lineage,
leakage, double-talk, alignment, no-hang, CPU, and metadata-only gates all pass.
