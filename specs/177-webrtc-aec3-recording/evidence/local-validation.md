# Local app and package validation

Date: 2026-08-21

## Ad-hoc universal candidate

- Post-audit local version: `2026.08.21.2`.
- Universal installer build: PASS.
- Application executable architectures: `arm64`, `x86_64`.
- `validate-app-updates.sh`: PASS for the ad-hoc local app.
- Bundle signature structure: PASS.
- `AEC3-THIRD-PARTY-NOTICES.txt`: present in the app and expanded package.
- WebRTC/Abseil dylib load command or bundled dylib: none observed.
- Expanded package contains one GRAF application component; Sparkle helper code
  remains nested under that app as before.
- Local package SHA-256:
  `6e40ad6912f2d54b904e5ca3b283a3ed89d1e96cdb01bac9a7694563cce1b4af`.
- Package signing status: unsigned local artifact, expected for this ad-hoc
  validation lane.

## Repository gate

- `infra/scripts/ci-local.sh --fast`: PASS.
  - legacy audio architecture guard: PASS;
  - server unit suite: 1120 passed, 0 failed;
  - server lint and Python compile: PASS;
  - macOS Swift validation is intentionally skipped by the fast lane and was
  run separately through the full 722-test Swift suite.

This artifact was not published, installed, notarized or treated as a release
candidate. Developer ID, notarization, stapling and Gatekeeper remain separate
authorized release gates.
