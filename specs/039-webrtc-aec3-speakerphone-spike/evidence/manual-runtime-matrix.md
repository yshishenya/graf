# Manual Runtime Matrix: WebRTC AEC3 Speakerphone Spike

Date: 2026-06-22

This file is the metadata-only template for future controlled real-hardware
runs. No private runtime audio, transcripts, raw device names, screenshots, or
local package paths are committed here.

## Closeout State

Manual controlled real-hardware runs were not recorded into this repository
during this closeout. The implemented evidence uses synthetic and metadata-only
fixtures plus automated self-tests.

## Matrix Template

| Scenario | Route scope | Evidence state | Result rule |
| --- | --- | --- | --- |
| Built-in Mac microphone plus built-in Mac speakers | Immediate-promotion candidate | Not run in this closeout | May promote only after corpus, package-readiness, app-status, rollback, dependency, license, packaging, CPU, memory, and no-hang gates pass |
| Stop while AEC3 is evaluating | Built-in speakerphone | Covered by metadata self-test | Stop remains visible; uncertain state stays blocked |
| App quit while AEC3 is evaluating | Built-in speakerphone | Covered by metadata self-test | Package truth remains original; no clean claim |
| Unsafe reference after candidate promotion | Built-in speakerphone | Covered by rollback self-test | Roll back to original microphone truth |
| USB headset | Supporting route only | Metadata fixture present | Evidence only; cannot broaden 039 promotion scope |
| Wired headset | Supporting route only | Metadata fixture present | Evidence only; cannot broaden 039 promotion scope |
| Bluetooth headset | Supporting route only | Metadata fixture present | Evidence only; cannot broaden 039 promotion scope |
| AirPods | Supporting route only | Metadata fixture present | Evidence only; cannot broaden 039 promotion scope |
| Browser route | Supporting route only | Metadata fixture present | Evidence only; cannot broaden 039 promotion scope |

## Required Fields For Future Manual Rows

- Redacted package id, for example `recording-package-001`.
- Route class and scenario family.
- Threshold profile id.
- Candidate lineage state.
- App status state shown to the user.
- Whether `mic.wav`, `incoming.wav`, and `manifest.json` stayed traceable.
- Safe reason codes and next-step recommendation.
- Rollback trigger, when applicable.
