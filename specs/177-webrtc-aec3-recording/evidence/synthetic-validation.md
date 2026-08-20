# Synthetic validation

Date: 2026-08-21

Lane: high-risk capture; deterministic local tests with generated signals only.

## Results

- `RecordingEchoProcessorTests`: 3 passed, 0 failed, including a 1,000-frame
  local p95 check under the 10 ms processing budget.
- `RecordingAudioTimelineTests`: 23 passed, 0 failed, including callback
  partitions `1/479/480/481/1024/4096`, final pad/trim, missing reference,
  route discontinuity and cleaned-prefix-only failure.
- `RecordingAEC3QualityTests`: 3 passed, 0 failed.
  - all 12 far-end rows for delays `20/80/150/300 ms` and RT60
    `0.2/0.5/0.8 s` met the required 20 dB threshold;
  - double-talk echo-component reduction met the required 10 dB threshold;
  - near-end level change stayed within 1 dB and correlation met 0.98;
  - the harness accounts for measured internal AEC3 delay.
  - smooth 80-to-85 ms delay drift retains at least 10 dB reduction;
  - the real AEC3-to-canonical-mix path reduces the added mic echo component by
    at least 20 dB and does not reintroduce raw microphone echo during mixing.
- Gradual opposing callback clocks and a 60-minute plus/minus 100 ppm model are
  recovered within the one-millisecond boundary; large/backward/overflowing
  boundaries and format changes remain terminal.
- Manifest, writer, package, capture-source, diagnostics and product-surface
  focused suites passed with no failures.
- Full `swift test --package-path apps/macos`: 722 passed, 0 failed; the
  expanded delay/RT60 quality row then passed again as a focused rerun.
- `swift run --package-path apps/macos ContractValidation`: PASS.

The quality harness keeps generated samples in memory and writes no audio,
spectrogram, speech or transcript to disk or repository evidence.
