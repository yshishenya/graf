# Evidence: установка, разрешения и перезапуск GRAF

Feature: `124-macos-permission-installer-relaunch`

## Lane

- Risk / validation lane: `high-risk-feature`.
- Release gate: high-risk feature release candidate; Apple Developer enrollment,
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
| Local package build | pass | Version `2026.07.24.1`, explicit `GRAF Local Code Signing` path; tracked public package source synchronized with the candidate |
| App metadata/signature inspection | pass | Bundle id `pro.2brain.graf`; `NSMicrophoneUsageDescription`, `NSAudioCaptureUsageDescription`, `NSScreenCaptureUsageDescription`; strict app signature; package-level signature absent as expected for no-account channel |
| Update validator | pass | `validate-app-updates.sh` accepted the staged app as local identity with updater disabled |
| Native relaunch path | pass | Explicit restart records a relaunch request, clears modal state, preserves bounded cleanup, and opens a fresh app instance via `NSWorkspace` from `applicationWillTerminate` |
| Public download tests | pass | 17 focused server/contract tests, 0 failures |
| Remote production deploy | pass | `cd-remote.sh --execute` deployed commit `e485c45e` from `codex/124-microphone-settings-recovery`; backup/restore, migrations, runtime/worker readiness and production smoke passed |
| Public package deployment | pass | Download URL returned HTTP 200 with `3545079` bytes; served SHA256 matched the built candidate; previous package retained as a rollback backup |
| Full local CI | pass | 2254 parallel server tests passed, 41 strict tests passed, 2 skips overall (one in each server phase); lint, compile, compose and deployment-evidence scans passed |
| GitHub issue canon | pass | Canonical issues created, commented with evidence and closed for T001–T013; `validate_issue_canon.py` passed before closeout |

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
