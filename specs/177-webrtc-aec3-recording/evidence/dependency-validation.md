# Dependency validation

Date: 2026-08-20

Lane: high-risk capture dependency; local metadata-only evidence.

## Result

- Pinned source: `webrtc-audio-processing` v2.1, WebRTC M131, commit
  `846fe90a289f58b7c9303a635142aa2c7caa93e5`.
- Vendored archive SHA-256:
  `6afa1ce70aa1fb0d1c33d44a60d7b5e49b1ce7c21928ee55a418ce89bce13822`.
- `validate-graf-aec3-artifact.sh`: PASS.
- Archive architectures: `arm64`, `x86_64`.
- Native arm64 and Rosetta x86_64 C smoke: PASS.
- `swift build --package-path apps/macos`: PASS.
- `GrafAEC3ArtifactContractTests`: 2 passed, 0 failed.
- Exported C ABI, exact 48 kHz mono 480-sample frame contract and AEC-only
  configuration matched the lock and reviewed source.
- No WebRTC or Abseil dynamic dependency was observed.
- Required WAP/WebRTC, PATENTS, Abseil and bundled-DSP notices are present.

No source checkout, build cache, raw audio, private path or credential is
included in this evidence.
