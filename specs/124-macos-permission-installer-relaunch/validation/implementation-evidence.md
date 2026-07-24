# Evidence: установка, разрешения и перезапуск GRAF

Feature: `124-macos-permission-installer-relaunch`

## Lane

- Risk / validation lane: `high-risk-feature`.
- Release gate: high-risk feature release/deploy completed as `v2026.07.24.3`;
  Apple Developer enrollment,
  Developer ID and notarization не требуются для native microphone TCC flow и
  в этот кандидат не включены.
- Evidence metadata-only: без audio, transcript, credentials, raw TCC database
  or private meeting content.

## Implemented checks

| Check | Result | Evidence |
| --- | --- | --- |
| Shell syntax | pass | `sh -n` for installer, install-user-app, update validator and permission-retention scripts |
| Focused macOS XCTest | pass | 56 selected tests, 0 failures: onboarding, microphone service, installer metadata, packaging and UX |
| Full macOS XCTest | pass | 625 tests, 0 failures |
| macOS contract validation | pass | `ContractValidation: PASS` |
| Local package build | pass | Version `2026.07.24.3`, explicit `GRAF Local Code Signing` path; updater-enabled package contains the configured HTTPS feed and active public key |
| App metadata/signature inspection | pass | Bundle id `pro.2brain.graf`; `NSMicrophoneUsageDescription`, `NSAudioCaptureUsageDescription`, `NSScreenCaptureUsageDescription`; strict app signature; hardened-runtime `com.apple.security.device.audio-input=true`; package-level signature absent as expected for no-account channel |
| Update validator | pass | `validate-app-updates.sh` accepted `v2026.07.24.3` against `v2026.07.24.2` with configured updater, in-app continuity, designated-requirement continuity, safe ZIP and signed appcast |
| Native relaunch path | pass | Explicit restart records a relaunch request, clears modal state, preserves bounded cleanup, and opens a fresh app instance via `NSWorkspace` from `applicationWillTerminate` |
| Public download tests | pass | 17 focused server/contract tests, 0 failures |
| Remote production deploy | pass | `cd-remote.sh --execute --skip-local-ci` restored the compatible runtime at `c14a291dd8abdca2b2e042924fd9f50764db3611`; backup `20260724T115334Z`, migration head `0037_auth_rate_limit_buckets`, runtime/worker readiness and production smoke passed |
| Public package deployment | pass | `GRAF-2026.07.24.3.pkg` and stable `graf-local.pkg` match SHA256 `eabe0a36798592a0ed58238f449c24089c5ed40d47d8764a1074fa6a4fe49b73`; previous package and appcast were retained before replacement |
| Sparkle release publication | pass | Protected workflow run `30090039617` signed `v2026.07.24.3`; public ZIP SHA256 `ef7c1b31765f83a2b872c83ba71cc8c6c37bf97b08799059784478a62b999446`, appcast SHA256 `06b3b922caac1fa234e4126f376baeee3be8519ba4a2bbd2cbea2cc01d286fc1`; public appcast and archive signatures verified after HTTPS fetch |
| Full local CI | pass | 625 macOS tests, 2255 parallel server tests, 41 strict tests, 2 expected skips overall; lint, compile, compose and deployment-evidence scans passed |
| GitHub issue canon | pass | Canonical issues T096–T098 and T100 were commented with evidence and closed; T099/#4528 remains open for colleague clean-Mac smoke; `validate_issue_canon.py` passed |

## Manual validation boundary

The clean external-Mac smoke with a colleague's account was not executed from
this worktree. Therefore this evidence does not claim that a public artifact is
Developer ID signed/notarized or that the exact colleague Mac has accepted
permissions. The code and instructions are ready for that controlled smoke:

1. use the documented one-time Gatekeeper confirmation;
2. request microphone access from the running `GRAF.app`;
3. enable Screen & System Audio Recording;
4. use **Перезапустить GRAF** and confirm the old process exits within ten
   seconds and a fresh GRAF process opens;
5. confirm the sheet disappears only after a fresh granted/granted read.

## Explicitly not done

- Apple Developer account, Developer ID certificates, notarization or stapling;
- `spctl --master-disable`, TCC reset/database edits, PPPC profiles or drivers;
- installation into `/Applications` during this validation;
- clean external-Mac download/permission smoke on the colleague's Mac; the candidate still uses
  local self-signing and must be manually trusted in Finder on the external Mac;
  no TCC reset, database edit, PPPC profile or driver workaround is part of the
  release.
