# Decision Record: WebRTC AEC3 Speakerphone Spike

Date: 2026-06-22

## Final Automated Decision

Primary outcome: `defer_to_fallback_decision`

Fallback feature: `040-speakerphone-recording-fallback-decision`

Route scope: built-in Mac microphone plus built-in Mac speakers only.

Supporting routes can broaden promotion scope: `false`

## What This Means

Feature 039 now has a metadata-only validation harness for WebRTC AEC3 as a
candidate, but it does not ship a production clean-recording guarantee. When
AEC3 is blocked, unproven, rolled back, or fallback-relevant, the app preserves
original microphone truth and shows a calm local status instead of implying that
speaker audio has been removed from the microphone track.

## Limitations

- No committed evidence contains private audio, transcripts, meeting content, or
  raw WebRTC traces.
- The automated decision evidence is not a substitute for controlled
  real-hardware app recordings.
- Non-built-in routes, including USB, wired, Bluetooth, AirPods, browser, and
  external output routes, remain supporting evidence only.
- AEC3 cannot affect upload or transcription readiness until package-readiness
  and immediate-promotion gates pass.
- If dependency, license, packaging, signing, notarization, status, diagnostics,
  Stop/quit, CPU, memory, or no-hang evidence is missing or unsafe, the outcome
  must fail closed.
