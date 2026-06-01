# Quickstart: macOS Passthrough Release Hardening

Run from repository root.

## Baseline Build And Existing Gates

```sh
swift build --package-path apps/macos -c release --product TwoBrainRecApp
swift test --package-path apps/macos --disable-swift-testing
sh tests/macos/static/audio-rt-safety-check.sh
make -C apps/macos/AudioDriver proof-plugin-build proof-runtime-probe-build proof-hal-io-probe-build
sh apps/macos/Scripts/validate-real-bidirectional-passthrough.sh
```

Expected result: all commands pass before new hardening work is accepted.

## Installed Runtime Baseline

```sh
TWO_BRAIN_REC_ALLOW_ADHOC_APP_SIGNING=1 sh apps/macos/Installer/Scripts/build-local-installer.sh
sudo installer -pkg apps/macos/.build/installer/2brain-rec-local.pkg -target /
sudo killall coreaudiod || true
make -C apps/macos/AudioDriver proof-runtime-probe-run RUNTIME_PROBE_ARGS=--expect-default-safe
sh tests/macos/installer-recovery/default-passthrough-disabled-check.sh
```

Expected result: both virtual devices are visible/alive and report `running=0`
when no client is using them. The app auto-starts only non-recording
passthrough.

## No-Hang And CPU Gate

Run or create the hardening harness/checklist for:

- macOS Sound settings;
- Chrome audio/device settings;
- Opera audio/device settings;
- Zoom audio settings;
- Yandex Telemost audio settings.

Expected result: each target opens within 5 seconds or is recorded as
`blocked/not_accepted` with a reason. During no-call idle, `coreaudiod` must not
sustain CPU above 10% for more than 30 consecutive seconds.

## Route Recovery Gate

Record metadata-only evidence for:

- physical microphone change;
- physical output change;
- aggregate or multi-output route;
- Bluetooth route as managed pilot or not accepted;
- stale browser device ID after restart;
- `coreaudiod` restart;
- sleep/wake.

Expected result: route state becomes stale/degraded/blocked within 5 seconds or
recovers to ready only after valid route evidence.

## Installer Lifecycle Gate

Run/check:

- install;
- update;
- repair;
- rollback;
- uninstall;
- reinstall.

Expected result: each operation records passed/blocked/not accepted evidence and
does not require hidden manual cleanup.

## Diagnostics And UX Gate

```sh
swift test --package-path apps/macos --disable-swift-testing --filter DiagnosticRedactionTests
rg -n "(BEGIN (RSA|OPENSSH|PRIVATE) KEY|AKIA[0-9A-Z]{16}|xox[baprs]-|ghp_|sk-[A-Za-z0-9]{20,}|signed_url|signedUrl|token=|password=)" apps/macos tests/macos qa/macos specs/005-macos-passthrough-release-hardening || true
```

Expected result: tests pass; scan results are policy text or deliberate fixture
strings only. UI evidence shows non-recording passthrough state without implying
recording/transcription/capture.

## Deferred Recording-Assisted Acceptance

Do not require long-duration recorded call replay in this slice. Create or
update the future checklist that will become mandatory after local recording
exists. The current slice may pass only when the future checklist is explicitly
blocked until local recording, retention, and deletion rules exist.
