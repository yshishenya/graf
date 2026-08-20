# Local app and package validation

Date: 2026-08-20

## Ad-hoc universal candidate

- Local version: `2026.08.20.1`.
- Universal installer build: PASS.
- Application executable architectures: `arm64`, `x86_64`.
- `validate-app-updates.sh`: PASS for the ad-hoc local app.
- Bundle signature structure: PASS.
- `AEC3-THIRD-PARTY-NOTICES.txt`: present in the app and expanded package.
- WebRTC/Abseil dylib load command or bundled dylib: none observed.
- Expanded package contains one GRAF application component; Sparkle helper code
  remains nested under that app as before.
- Local package SHA-256:
  `3b65fb85dc06069dc641a06984411dfedf340a3933fcb2c260cf1f364f199848`.
- Package signing status: unsigned local artifact, expected for this ad-hoc
  validation lane.

## Repository gate

- `infra/scripts/ci-local.sh --fast`: PASS.
  - legacy audio architecture guard: PASS;
  - server unit suite: 1103 passed, 0 failed;
  - server lint and Python compile: PASS;
  - macOS Swift validation is intentionally skipped by the fast lane and was
    run separately through the full 708-test Swift suite.

This artifact was not published, installed, notarized or treated as a release
candidate. Developer ID, notarization, stapling and Gatekeeper remain separate
authorized release gates.
