# Implementation Evidence: macOS Permission Retention And Relaunch Reliability

> Historical local permission-retention evidence. It does not prove public
> release readiness and must not replace Feature 130 Developer ID,
> notarization, stapling and Gatekeeper evidence.

Feature: `095-macos-permission-retention`

Status: Historical local fixture, formerly referenced by `v2026.07.09.6`.

## Lane

- Risk / validation lane: high-risk feature.
- Reason: macOS microphone and Screen/System Audio permissions, installer
  signing, permission onboarding UX, and app termination/relaunch behavior.
- Release gate: historical local self-signed owner-machine fixture only. No
  public download refresh is allowed from this evidence; current public
  distribution is Developer ID/notarized under Feature 130.

## Preliminary Local Evidence From 2026-07-09

This evidence was collected before the final `095` task list existed. It is
useful context and must be reconciled during implementation before any task is
marked `[X]`.

| Check | Result | Notes |
|-------|--------|-------|
| Local code-signing identity availability | pass | A local identity named `GRAF Local Code Signing` was available to `codesign` on the owner's Mac. Private key material was not recorded. |
| Local package build with self-signed app identity | partial | The existing `build-local-installer.sh` signed the app but rejected non-Apple identities before product package creation. Manual `pkgbuild` packaging was used as a temporary exploratory workaround. Formal implementation must add an explicit supported local path or record a blocker. |
| Installed app signature | pass | `/Applications/GRAF.app` verified as signed by the local identity. Evidence did not include private key material. |
| Permission state after reinstall | pass | Read-only summaries showed microphone and Screen/System Audio allowed for `pro.2brain.graf`; app log showed `microphone=granted systemAudio=granted ready=true`. |
| Permission onboarding with granted permissions | pass | No permission modal was observed after launch with both permissions granted. |
| Quit after local fix | pass | AppleScript quit returned successfully and logs showed termination cleanup completed. |
| Focused Swift tests | pass | `swift test --package-path apps/macos --filter 'AppControlAccessibilityTests|SystemAudioPermissionGateTests|SystemAudioPermissionUXTests|InstallerLifecycleEvidenceTests'` passed on 2026-07-09 with 27 tests and 0 failures. |

## Implementation Sync

| Check | Result | Notes |
|-------|--------|-------|
| GitHub issue sync | pass | Created canonical GitHub issues #2979-#3018 for Spec Kit tasks T001-T040 with `feature:095` labels before implementation continued. |
| GitHub issue closeout | pass | After validation passed and `tasks.md` was marked `[X]`, issues #2979-#3018 were closed with Russian closure comments referencing task, evidence, validation, and out-of-scope release boundaries. |
| GitHub issue canon hooks | pass | `python3 .specify/extensions/github-issue-canon/scripts/ensure_issue_canon.py` passed; `python3 .specify/extensions/github-issue-canon/scripts/validate_issue_canon.py` passed with `OK (174 Spec Kit issue(s) checked)`. |
| Local self-signed build script support | pass | `apps/macos/Installer/Scripts/build-local-installer.sh` accepts `GRAF_ALLOW_LOCAL_SELF_SIGNED_APP_SIGNING=1` with an explicit local-only warning while keeping release-like Apple signing strict by default. |
| Installer README boundary | pass | `apps/macos/Installer/README.md` documents the historical free local self-signed fixture, certificate/key continuity, and the current Developer ID/notarization public release boundary. |
| Permission modal termination hardening | pass | `apps/macos/RecApp/App/TwoBrainRecApp.swift` clears permission onboarding, permission request, meeting prompt, and AppKit sheet state during termination. |
| Validation helper | pass | `apps/macos/Scripts/validate-macos-permission-retention.sh` supports metadata-only preflight/build/identity/permission/quit checks and does not reset or mutate TCC. |

## Final Local Validation

| Check | Result | Evidence |
|-------|--------|----------|
| Shell syntax | pass | `sh -n apps/macos/Installer/Scripts/build-local-installer.sh && sh -n apps/macos/Installer/Scripts/install-user-app.sh && sh -n apps/macos/Scripts/validate-macos-permission-retention.sh` |
| Focused Swift tests | pass | `swift test --package-path apps/macos --filter 'AppControlAccessibilityTests|SystemAudioPermissionGateTests|SystemAudioPermissionUXTests|InstallerLifecycleEvidenceTests'`: 33 tests, 0 failures. |
| Local signing preflight | pass | `apps/macos/Scripts/validate-macos-permission-retention.sh preflight`: `signing_identity_present name=GRAF Local Code Signing`. |
| Local self-signed package build | pass | `apps/macos/Scripts/validate-macos-permission-retention.sh build` created `apps/macos/.build/installer/graf-local-permission-retention.pkg` and printed the local-only warning. |
| Staged app identity | pass | `bundle_id=pro.2brain.graf`, `Authority=GRAF Local Code Signing`, `TeamIdentifier=not set`, designated requirement uses the local certificate root. |
| First install/launch | pass | Admin-prompted `installer` upgrade succeeded; `/Applications/GRAF.app` verified with the same bundle id and local certificate-root designated requirement. |
| Permission state after install | pass | App log: `desktop.permission_onboarding_checked detail=reason=app_appeared microphone=granted systemAudio=granted ready=true`; user TCC summary: `kTCCServiceMicrophone|pro.2brain.graf|2`. Direct system TCC DB read was blocked by macOS authorization, so Screen/System Audio acceptance uses app preflight/log state rather than raw DB evidence. |
| Quit/relaunch | pass | `apps/macos/Scripts/validate-macos-permission-retention.sh quit`: `quit_ok app=GRAF`; logs include `app_termination_cleanup_completed detail=reason=cleanup_finished`. |
| Second reinstall cycle | pass | Reinstalling the same local package succeeded; relaunch again logged `microphone=granted systemAudio=granted ready=true`, identity stayed on the same local certificate-root DR, and quit returned `quit_ok`. |
| Static placeholder scan | pass | Only literal scan/checklist policy lines matched; no unresolved template fields remain in feature artifacts. |
| Focused forbidden-content scan | pass with policy matches | Matches were policy strings in quickstart and existing redaction code (`token=` allowlist); no private keys, passwords, tokens, raw audio, transcripts, signed URLs, or private meeting content were added as evidence payloads. |
| Release-version package build | pass | `GRAF_VERSION=2026.07.09.6 apps/macos/Scripts/validate-macos-permission-retention.sh build` created `apps/macos/.build/installer/graf-local-permission-retention.pkg`; package metadata reports `CFBundleShortVersionString=2026.07.09.6`, `CFBundleVersion=2026.07.09.6`, and bundle id `pro.2brain.graf`. |
| Public download package refresh | pass | `apps/server/src/twobrain_rec_server/public/static/public/downloads/graf-local.pkg` was refreshed from the validated local package; SHA-256 matched `apps/macos/.build/installer/graf-local-permission-retention.pkg` at `41d31b78bf5f6bda25818b060c3c1a534702629ed8cab2a1235ac24adcf3efa3`. |
| Release dry-run | pass | `infra/scripts/cd-remote.sh --dry-run --branch codex/095-release-v202607096`: `deploy_result=dry_run`, branch `codex/095-release-v202607096`, and planned gates `clean_worktree,branch_sync,pinned_sha,local_ci,remote_fetch,backup,restore_rehearsal,compose_config_secret_scan,deploy_build_up,runtime_secret_env_scan,production_smoke,public_health`. |
| Full local CI | pass | `infra/scripts/ci-local.sh`: server tests `1177 passed, 4 skipped, 1 warning`; server lint passed; compile passed; deployment evidence scan passed; `ci_local_result=pass`. |

## Evidence Collected During Implementation

- [X] Static spec and forbidden-content scan.
- [X] Signing identity preflight.
- [X] Focused Swift tests from [quickstart.md](../quickstart.md).
- [X] Shell syntax checks for installer scripts.
- [X] Local signed package build with explicit local-self-signed flag.
- [X] First install and permission grant evidence.
- [X] Reinstall with same signing continuity identity.
- [X] Permission state snapshot after reinstall.
- [X] No permission onboarding modal when permissions are granted.
- [X] Quit/relaunch with normal granted-permission state.
- [X] Quit/relaunch with permission modal state visible or simulated.
- [X] Changelog/status evidence.
- [X] Full `infra/scripts/ci-local.sh` gate.

## Public Release Boundary

The following are not completed by this feature unless a later release lane
explicitly does them:

- Apple Developer account enrollment.
- Developer ID Application certificate.
- Developer ID Installer certificate.
- Notarization submission and success.
- Stapling verification.
- Public download Gatekeeper validation.
- MDM/fleet PPPC policy.

## Evidence Safety

Allowed:

- bundle id;
- app path class;
- app version;
- signing authority class/name;
- TeamIdentifier presence/absence;
- designated requirement shape;
- permission state labels;
- pass/fail outcomes.

Forbidden:

- certificates/private keys or exported identities;
- passwords or app-specific passwords;
- raw audio, transcript text, private meeting content;
- credentials, tokens, signed URLs;
- unrelated private local file paths or screenshots.
