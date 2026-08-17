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
- Validation snapshot: the implementation commit
  `de1da043eec3b3c2b98d658755f5c9110bb0e0d4` passed the exact-SHA full CI gate;
  this metadata-only evidence update is followed by one final full-CI rerun on
  the resulting commit. This is not a release commit; the clean external-Mac
  smoke and all release/deploy gates remain separate.

## Implemented checks

| Check | Result | Evidence |
| --- | --- | --- |
| Shell syntax | pass | `sh -n` for installer, install-user-app, update validator and permission-retention scripts |
| Focused macOS XCTest | pass (baseline) | 50 selected tests, 0 failures: onboarding, installer metadata, packaging and UX |
| Full macOS XCTest | pass (after granted-state probe fix) | 687 tests, 0 failures |
| macOS contract validation | pass | `ContractValidation: PASS` |
| Local package build | pass | Version `2026.07.24.3`, explicit `GRAF Local Code Signing` path; updater-enabled package contains the configured HTTPS feed and active public key |
| App metadata/signature inspection | pass | Bundle id `pro.2brain.graf`; `NSMicrophoneUsageDescription`, `NSAudioCaptureUsageDescription`, `NSScreenCaptureUsageDescription`; strict app signature; hardened-runtime `com.apple.security.device.audio-input=true`; package-level signature absent as expected for no-account channel |
| Update validator | pass | `validate-app-updates.sh` accepted `v2026.07.24.3` against `v2026.07.24.2` with configured updater, in-app continuity, designated-requirement continuity, safe ZIP and signed appcast |
| Native relaunch path | pass | Explicit restart records a relaunch request, clears modal state, preserves bounded cleanup, and opens a fresh app instance via `NSWorkspace` from `applicationWillTerminate` |
| Public download tests | pass | 17 focused server/contract tests, 0 failures |
| Remote production deploy | pass | `cd-remote.sh --execute --skip-local-ci` restored the compatible runtime at `c14a291dd8abdca2b2e042924fd9f50764db3611`; backup `20260724T115334Z`, migration head `0037_auth_rate_limit_buckets`, runtime/worker readiness and production smoke passed |
| Public package deployment | pass | `GRAF-2026.07.24.3.pkg` and stable `graf-local.pkg` match SHA256 `eabe0a36798592a0ed58238f449c24089c5ed40d47d8764a1074fa6a4fe49b73`; previous package and appcast were retained before replacement |
| Sparkle release publication | pass | Protected workflow run `30090039617` signed `v2026.07.24.3`; public ZIP SHA256 `ef7c1b31765f83a2b872c83ba71cc8c6c37bf97b08799059784478a62b999446`, appcast SHA256 `06b3b922caac1fa234e4126f376baeee3be8519ba4a2bbd2cbea2cc01d286fc1`; public appcast and archive signatures verified after HTTPS fetch |
| Full local CI | pass (exact implementation commit) | `infra/scripts/ci-local.sh --full` on `de1da043eec3b3c2b98d658755f5c9110bb0e0d4`: 687 macOS tests, 3026 parallel server tests with one expected skip, 42 strict tests with one expected skip; lint, compile, compose and deployment-evidence scans passed; RLS live-production probe was not attempted because no destructive probe database was provided |
| GitHub issue canon | pass | Canonical issues T096–T098 and T100 were commented with evidence and closed; T099/#4528 remains open for colleague clean-Mac smoke; `validate_issue_canon.py` passed |

## T099 technical recheck — 2026-08-17

- The earlier full-CI row is retained as the pre-T101 baseline. The exact
  implementation-commit full gate is recorded above; after this evidence-only
  update, CI is rerun on the resulting final commit before PR preparation.
- `sh -n` passed for the installer, update validator and permission-retention
  helper.
- Focused macOS XCTest passed: `50 passed`, `0 failures` across
  `AppControlAccessibilityTests`, `SystemAudioPermissionUXTests`,
  `InstallerLifecycleEvidenceTests` and `InstallerPackagingTests`.
- Follow-up focused macOS validation after T101 passed: `65 passed`, `0
  failures`; `ContractValidation: PASS`.
- `infra/scripts/ci-local.sh --fast` passed after T101: `1096 passed`, lint,
  Python compile and legacy-audio guard passed; two pytest warnings were
  non-blocking dependency deprecations.
- After closing the granted-state probe bypass, focused macOS validation passed:
  `42 passed`, `0 failures` across `SystemAudioCaptureServiceTests`,
  `AppControlAccessibilityTests` and `SystemAudioPermissionUXTests`; the
  follow-up `infra/scripts/ci-local.sh --fast` also passed with `1096 passed`,
  lint, compile and legacy-audio guard. Full CI remains required on the exact
  implementation commit.
- Full `swift test --package-path apps/macos` after the same fix passed with
  `687 tests, 0 failures`; this is still a working-tree result until the
  implementation commit is created.
- The probe also checks that ScreenCaptureKit exposes a display, matching the
  real runtime's first capture precondition; the focused rerun passed with
  `42 tests, 0 failures`.
- Final rerun after the display precondition passed: full macOS XCTest `687/687`
  and `infra/scripts/ci-local.sh --fast` `1096 passed`; lint, Python compile,
  legacy-audio guard and `git diff --check` passed. Full CI on the exact commit
  is still required after approval.
- The permission path now includes a metadata-only ScreenCaptureKit functional
  probe when Core Graphics preflight is stale or reports granted but the native
  path fails; it never starts capture or edits TCC, and a failed probe remains
  blocked until the exact app permission is re-enabled and GRAF is relaunched.
- The isolated local self-signed package build passed for CalVer
  `2026.07.24.3`; the staged app passed strict code-signature verification and
  was not installed.
- Public `GRAF-2026.07.24.3.zip` validated against public
  `GRAF-2026.07.24.2.zip`: bundle identity, version monotonicity, privacy
  descriptions, hardened-runtime audio-input entitlement, Sparkle continuity,
  designated-requirement continuity and archive integrity passed.
- The live feed now serves `2026.08.16.7`; this recheck therefore records the
  archive/continuity validator result and does not claim a historical `.3`
  appcast was still the live feed.
- Full `infra/scripts/ci-local.sh` passed on the implementation commit: 687 macOS tests, 3026 parallel
  server tests with one expected skip, 42 strict tests with one expected skip,
  lint, compile, compose and deployment-evidence scan. The live-production RLS
  probe remained intentionally unattempted because no destructive probe
  database was provided.
- No TCC reset, database edit, permission grant, application install, audio,
  transcript or meeting content was used.

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
