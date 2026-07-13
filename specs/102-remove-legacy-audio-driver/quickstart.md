# Quickstart: Validate Legacy Driver Removal

Run from repository root on macOS. These commands are read-only with respect to
system audio services; the installer command builds a package under the local
workspace and does not install it.

## 1. Current recording regression suite

```sh
swift test --package-path apps/macos --filter 'LocalRecordingWriterSystemAudioTests|SystemAudioCaptureServiceTests|MicrophoneCaptureServiceTests|RecordingPrerequisiteGateTests|SystemAudioRecordingPackageTests|CaptureSessionSafetyTests'
```

Expected: all supported graph, artifact, gate, and visible-stop tests pass. The
pre-change baseline on 2026-07-13 was 62 tests with zero failures.

## 2. Full remaining macOS suite and app build

```sh
swift test --package-path apps/macos --disable-swift-testing
swift build --package-path apps/macos -c release --product TwoBrainRecApp
```

Expected: no missing legacy symbol and no driver/shared-memory target compiled.

## 3. Current capture and artifact validators

```sh
apps/macos/Scripts/validate-system-audio-capture-pivot.sh --self-test-artifact-metadata
apps/macos/Scripts/validate-system-audio-capture-pivot.sh --self-test-cpu-evidence
apps/macos/Scripts/validate-system-audio-capture-pivot.sh --self-test-latest-artifact-selection
apps/macos/Scripts/validate-system-audio-capture-pivot.sh --self-test-duration-evidence
apps/macos/Scripts/validate-system-audio-capture-pivot.sh --self-test-permission-evidence
apps/macos/Scripts/validate-system-audio-capture-pivot.sh --self-test-review-evidence
apps/macos/Scripts/validate-recording-artifact-format.sh
apps/macos/Scripts/validate-no-legacy-audio-driver.sh
apps/macos/Scripts/validate-foundation.sh
```

Expected: current capture truth passes; the architecture guard reports no
forbidden active legacy surface and writes no evidence.

## 4. App-only installer proof

```sh
scratch_dir="$(mktemp -d)"
GRAF_INSTALLER_BUILD_DIR="$scratch_dir/build" \
GRAF_ALLOW_ADHOC_APP_SIGNING=1 \
  apps/macos/Installer/Scripts/build-local-installer.sh \
  "$scratch_dir/graf-local.pkg"
pkgutil --expand-full "$scratch_dir/graf-local.pkg" "$scratch_dir/expanded"
find "$scratch_dir/build/components" -maxdepth 1 -type f -name '*.pkg' -print
find "$scratch_dir/expanded" -print
```

Inspect the generated distribution and component directory reported by the
script. Expected:

- one desktop app component;
- no `Library/Audio/Plug-Ins/HAL` payload;
- no audio-driver package/choice;
- no repair/rollback/postinstall audio hook;
- no `coreaudiod` restart command.

Do not run `installer`, `sudo`, an uninstall, or an audio-service restart as part
of this quickstart. Remove `$scratch_dir` afterward only if you created it for
this validation run.

## 5. Repository gate

```sh
infra/scripts/ci-local.sh
```

Expected: PASS. This is additive to the direct macOS proof above, not a
replacement for it.

## 6. Manual product smoke

On a Mac with granted microphone and screen/system-audio permissions:

1. Launch the newly built app.
2. Confirm no driver, virtual-device, repair, or passthrough controls appear.
3. Start a controlled recording.
4. Confirm both live meters reflect the current sources.
5. Confirm the visible active indicator and one-action Stop.
6. Stop and inspect the local package for the original mic track, incoming
   system-audio track, and manifest.
7. Deny one permission and confirm truthful blocking copy with no driver repair
   recommendation.

Record metadata-only evidence; never store raw meeting audio or transcript text
in the repository.

## Validation Results — 2026-07-13

- Pre-change selection: 62 tests, zero failures.
- Post-change selection: 60 tests, zero failures. The net reduction of two is
  intentional: six route/publication/stale-state prerequisite cases were
  removed with their retired API, while three current permission/prerequisite
  cases and one fail-closed unknown-input case were added. The writer,
  ScreenCaptureKit, package, and visible-stop suite counts did not decrease.
- Expanded current-capture regression selection: 117 tests, zero failures.
- Full macOS suite: 608 tests, zero failures both in the working build tree and
  from an empty SwiftPM scratch path.
- `TwoBrainRecApp` release build from the empty scratch path: PASS.
- All six `validate-system-audio-capture-pivot.sh` self-tests: PASS.
- Recording artifact validator: PASS, including `ContractValidation`, current
  dual-source artifact tests, and the retirement guard.
- Foundation validator and standalone retirement guard: PASS.
- Fresh package build/expansion: one `graf-desktop-app.pkg`, one payload at
  `Applications/GRAF.app`, and zero HAL bundle, driver, shared-memory,
  passthrough, repair, rollback, or `coreaudiod` matches.
- `infra/scripts/ci-local.sh`: PASS. It repeated 608 macOS tests, passed
  `ContractValidation`, ran 1226 server tests with four expected skips, and
  passed lint, compile, compose, and deployment-evidence checks. The bounded RLS
  probe truthfully remained unavailable because no dedicated Postgres test
  database was supplied; production enforcement was not claimed or inspected.
- Review follow-up preserved the persisted `hal_probe_observed` failure value
  as readable `legacy_not_ready` state and proved that it remains non-uploadable.
- Review follow-up removed the remaining inert driver-era status/refresh UI,
  corrected active validation commands, and hardened the operator cleanup
  procedure with exact bundle-identifier and symlink checks.
- Review follow-up also removed environment-overridable deletion targets from
  the normal app-only uninstaller; it can remove only the two exact supported
  application bundle paths and never touches HAL or restarts `coreaudiod`.
- A user-authorized app-only install and two controlled recording runs were
  completed before the final review follow-ups. Both live meters moved and both
  original tracks were present. The newest metadata-only inspection showed
  granted permissions, `mic.wav` at 852638 bytes, `incoming.wav` at 852422
  bytes, a 0.007-second duration difference, and no egress or transcription.
- That newest manifest truthfully failed with `leakage_detected` and
  `blocked_leakage_detected`; the user also reported that the review M4A masks
  microphone speech when system audio dominates. The removal diff does not
  change the pre-existing review-mix implementation, and these quality/leakage
  defects remain a separate high-risk recording feature rather than being
  claimed as solved by driver retirement.
- The permission-denied row and a reinstall of the exact final reviewed source
  were not rerun manually. Automated permission, capture, resource-release,
  artifact, compatibility, and installer tests passed. The final review did not
  run uninstall, `sudo`, HAL mutation, `coreaudiod` restart, deployment, or
  proof-bundle cleanup.
- After explicit user approval, implementation commit `9a9179d3` was pushed;
  the post-commit retirement guard passed. PR
  [#3222](https://github.com/yshishenya/crisp/pull/3222) then passed formal
  review with no blocking findings and was merged into `master` as `100b25c8`.
  GitHub closed all 31 linked issues, and each received status plus post-merge
  closure evidence.

## Existing Host State Cases

- **Known bundle absent**: no action; source/package retirement is complete.
- **Exact known proof bundle present**: follow the separate operator procedure
  in `docs/agent-guidance/legacy-audio-driver-cleanup.md` only during an
  explicitly approved maintenance window with no active call or recording.
- **Lookalike or unknown HAL bundle present**: preserve it and investigate; the
  GRAF cleanup procedure never authorizes broad HAL-directory deletion.
