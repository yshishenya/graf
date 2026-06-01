# Quickstart: macOS Real Bidirectional Passthrough

## Automated Baseline

Run from repository root:

```sh
swift build --package-path apps/macos -c release --product TwoBrainRecApp
swift test --package-path apps/macos
sh tests/macos/static/audio-rt-safety-check.sh
make -C apps/macos/AudioDriver proof-plugin-build proof-runtime-probe-build
sh apps/macos/Scripts/validate-live-route-readiness.sh
```

Expected result: all commands pass before passthrough implementation changes are
accepted.

## Local Installer Runtime Check

```sh
TWO_BRAIN_REC_ALLOW_ADHOC_APP_SIGNING=1 sh apps/macos/Installer/Scripts/build-local-installer.sh
sudo installer -pkg apps/macos/.build/installer/2brain-rec-local.pkg -target /
make -C apps/macos/AudioDriver proof-runtime-probe-run
```

Expected result: both virtual devices are visible and unhidden, with
`running=0` unless a controlled live passthrough experiment is explicitly
enabled. The default installed app must not start the app-side AudioUnit bridge
or write an app-I/O heartbeat on launch.

## Controlled Live Passthrough Safety Gate

Live passthrough is currently guarded because the app-side AudioUnit bridge can
destabilize `coreaudiod` if it starts automatically or performs realtime-unsafe
work in callbacks. Do not enable it during normal installer, publication, or UI
readiness checks.

For local engineering experiments only, launch the app with:

```sh
TWO_BRAIN_REC_ENABLE_EXPERIMENTAL_PASSTHROUGH=1 open -a "2brain Rec"
```

Before accepting any live route result, confirm:

- `coreaudiod` stays near idle when the app is open and no call is active.
- The bridge does not allocate, format log lines, or write files from realtime
  audio callbacks.
- `sh tests/macos/static/audio-rt-safety-check.sh` passes.
- `sh tests/macos/installer-recovery/default-passthrough-disabled-check.sh`
  passes after local package installation.
- `make -C apps/macos/AudioDriver proof-runtime-probe-run` still reports the
  devices visible and the expected fail-closed state after app quit.
- Zoom, Yandex Telemost, and System Settings launch without hanging while the
  driver is installed.

## Microphone Passthrough Check

1. Launch `2brain Rec` with the controlled live passthrough safety gate enabled.
2. Select a built-in or wired physical microphone.
3. Select `2brain Rec Microphone` in a controlled receiver or browser meeting.
4. Speak locally.
5. Confirm local speech is delivered to the receiver without starting recording.

Expected result: microphone path is ready/active and diagnostics contain
metadata only.

## Speaker Passthrough Check

1. Launch `2brain Rec` with the controlled live passthrough safety gate enabled.
2. Select a built-in or wired physical output.
3. Select `2brain Rec Speaker` in a controlled sender or browser meeting.
4. Play remote speech/stimulus.
5. Confirm audio is heard through the selected physical output.
6. Confirm remote audio is not routed into `2brain Rec Microphone` beyond the
   leakage threshold.

Expected result: speaker path is ready/active, latency is at or below 30 ms, and
leakage is at least 45 dB below reference.

## Browser Matrix Check

Record pass or blocked/not accepted evidence for:

- Chrome browser meetings.
- Opera browser meetings.
- Yandex Browser meetings.
- Yandex Telemost in browser.

Expected result: every target has metadata-only evidence in
`tests/macos/browser-meetings/browser-meeting-matrix.md`.

## Fail-Closed Recovery Check

1. Start a validated live route.
2. Kill the desktop app or route engine.
3. Wait at least 6 seconds.
4. Run `make -C apps/macos/AudioDriver proof-runtime-probe-run`.
5. Relaunch app and recheck route.

Expected result: devices remain published for macOS enumeration but report
`running=0`; audio I/O fails closed with silence/drop behavior after heartbeat
loss and returns only after the controlled bridge is explicitly enabled and the
route is revalidated.

## Diagnostics Redaction Check

Run:

```sh
swift test --package-path apps/macos --filter DiagnosticRedactionTests
rg -n "(BEGIN (RSA|OPENSSH|PRIVATE) KEY|AKIA[0-9A-Z]{16}|xox[baprs]-|ghp_|sk-|signed_url|signedUrl|token=|password=)" apps/macos tests/macos qa/macos specs/004-real-bidirectional-passthrough || true
```

Expected result: tests pass; scan results are policy text or deliberate
forbidden-field fixtures only.
