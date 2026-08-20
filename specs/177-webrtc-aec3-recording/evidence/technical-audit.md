# Technical audit: Feature 177 AEC3 recording

Date: 2026-08-21

Lane: significant/high-risk capture; code, architecture, historical evidence and
deterministic local validation. No release or deployment.

## Audit scope

The review traced the active path from ScreenCaptureKit and app-owned
microphone callbacks through PTS normalization, buffering, AEC3 framing,
canonical mixing, WAV/M4A finalization, manifest health, diagnostics and
upload-readiness gates. It also reviewed the C ABI, pinned artifact and all
repository evidence for Features 020, 038, 039, 106 and 177.

## Why the previous attempts did not remove echo

| Feature | What it proved | Why it did not solve live speaker echo |
| --- | --- | --- |
| 020 | A real v2 package had plausible physical speaker-to-mic leakage and a `152.19 s` mic/system duration mismatch. | It measured and reported leakage after capture. Its research explicitly says the slice performs no live cleanup. |
| 038 | Apple candidate lifecycle, lineage, diagnostics and fail-closed metadata were exercised. | The decision is `defer_to_webrtc_aec3`; no accepted live Apple voice-processing route, far-end reduction, near-end preservation or double-talk result was proven. |
| 039 | A large metadata/evaluation harness and rollback/status contracts were built. | The runtime adapter was deliberately unavailable, the decision is `defer_to_fallback_decision`, and no real processing or controlled hardware recording was promoted. |
| 106 | The current v5 single-timeline WAV/M4A package, PTS behavior and a 60-minute package run were established. | It contained no AEC. Its installed run did not prove an observable incoming signal, and its hardware acceptance remained open. |
| 177 before this audit | The first real mandatory AEC3 implementation was connected to the production writer. | Synthetic AEC passed, but three live-integrity gaps and several missing stress checks remained. |

Primary repository evidence:

- `specs/020-speaker-to-mic-leakage/problem-analysis.md`;
- `specs/020-speaker-to-mic-leakage/research.md`;
- `specs/038-apple-voice-processing-spike/evidence/decision-record.md`;
- `specs/038-apple-voice-processing-spike/evidence/manual-runtime-matrix.md`;
- `specs/039-webrtc-aec3-speakerphone-spike/evidence/decision-record.md`;
- `specs/039-webrtc-aec3-speakerphone-spike/evidence/manual-runtime-matrix.md`;
- `specs/106-mixed-wav-recording/evidence/validation.md`;
- `specs/106-mixed-wav-recording/evidence/hardware-acceptance.md`.

## Findings fixed by the audit

### 1. Real clock drift could terminate a valid recording

The former timeline expected each callback PTS to equal the previous PTS plus
the previous sample count. A deterministic plus/minus clock-rate model
reproduced `missingRequiredSource`; the existing drift test covered only one
fixed `0.1 ms` offset.

The timeline now corrects at most 48 canonical frames (1 ms) at each monotonic
batch boundary: a small positive delta is interpolated and a small overlap is
trimmed. Larger, backward, overflowing or discontinuous boundaries still fail
closed. Tests cover ten seconds of opposing gradual drift, an analytical
60-minute plus/minus 100 ppm model, random callback partitions/jitter and
excessive overlap.

### 2. A real output-device switch was not observed

Route generation previously changed only when a new capture runtime was
created. Switching the default macOS output while a recording was active could
therefore leave the same generation and allow AEC state to cross an acoustic
route boundary.

The ScreenCaptureKit runtime now observes CoreAudio's default-output-device
property. It emits one terminal `routeChanged` discontinuity and removes the
listener on failed start, Stop and stream failure. A queued listener callback
cannot publish after listener removal.

### 3. In-stream sample-rate or channel-count changes were accepted

The converter could silently accept `48 kHz -> 44.1 kHz`, and downmixing could
accept `mono -> stereo`, despite the feature contract requiring a truthful
format boundary. Each source now pins its first observed format and returns a
separate `format_changed` terminal reason on any later change.

### 4. The retired non-PTS FIFO duplicated every live sample

`BufferedLocalRecordingSampleSource` stored the same live audio in a flat FIFO
and in PTS-bearing batches. The production writer only accepted the timestamped
path, while the flat protocol and two unused ContractValidation sources were
legacy residue. The flat buffer, casts, protocol, wrappers and dead fixtures
were removed. New capture now has one bounded PTS-bearing source queue.

### 5. Quality and timing coverage was incomplete

- Double-talk near-end preservation now measures the component projected onto
  the known near-end stimulus, rather than total output RMS contaminated by
  residual far-end echo.
- Smooth acoustic-delay drift from 80 to 85 ms over 12 seconds must retain at
  least 10 dB reduction.
- A sustained 1,000-frame processor check must keep local p95 below the 10 ms
  frame budget.
- A canonical-mix test uses the real AEC3 processor and verifies that the
  cleaned microphone, not raw microphone, reaches the final mix; the added echo
  contribution must fall by at least 20 dB.

## Code and logic verdict

- The C bridge validates exact finite 48 kHz mono 480-sample frames, zeroes the
  output before failures, closes after reverse/capture errors and contains C++
  exceptions.
- Optional HPF, NS/ANC, AGC, transient suppression, VAD/gates and AecDump remain
  disabled. The system reference is processed before the corresponding mic
  frame, with stream delay zero because both streams already share one PTS
  timeline.
- `RecordingEchoProcessor` destroys the native instance once after terminal
  failure. Production calls are serialized on the writer queue.
- Stop drains system capture, then stops microphone capture, then drains and
  finalizes the writer. Only already-cleaned output can be salvaged after a
  terminal boundary.
- The final mix remains `0.5 * (cleaned microphone + unchanged system audio)`;
  its range is bounded when the accepted inputs are bounded.
- A degraded manifest blocks normal package readiness/upload, and no raw mic,
  render-reference file, AecDump or second ASR artifact is published.

No additional abstraction or dependency was added. Persisted historical v3/v4
manifest enums/readers were retained because removing them would break package
compatibility; they are not runtime selectors.

## Remaining limits

- The CoreAudio listener proves default output-device identity changes. A data
  source change inside the same device (for example, a driver exposing two
  physical outputs under one device ID) still requires the T035 wired/hardware
  route matrix; an actual batch format change is already terminal.
- Synthetic delay drift is not a substitute for abrupt physical movement,
  Bluetooth behavior, speaker non-linearity, clipping or real-room double-talk.
- No controlled built-in-speaker recording was made in this audit. Therefore
  the repository still cannot claim that audible real-world echo is eliminated.
- T035 remains open: two Apple Silicon Macs, two rooms, 25/50/75% speaker
  volume, far-end/near-end/double-talk, headphones, wired/Bluetooth route
  changes, clipping, a 60-minute run and listening acceptance.

## Validation result

- Vendored arm64/x86_64 artifact and native/Rosetta smoke: PASS.
- Full macOS suite: 722 passed, 0 failed.
- `RecordingAudioTimelineTests`: 23 passed, 0 failed.
- `RecordingAEC3QualityTests`: 3 passed, 0 failed.
- `RecordingEchoProcessorTests`: 3 passed, 0 failed.
- `SystemAudioCaptureServiceTests`: 16 passed, 0 failed.
- `ContractValidation`: PASS.
- Fast repository gate: 1120 server tests passed; legacy guard, Ruff and Python
  compile passed.
- `git diff --check`: PASS.

All generated quality signals stayed in memory. No raw audio, transcript,
meeting content, secret, signed URL or private device/path evidence was added.
