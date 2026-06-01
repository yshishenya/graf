# Quickstart: Low-Resource Reliable macOS Audio

Run from repository root.

## Baseline Before Implementation

```sh
swift build --package-path apps/macos -c release --product TwoBrainRecApp
swift test --package-path apps/macos --disable-swift-testing
sh tests/macos/static/audio-rt-safety-check.sh
make -C apps/macos/AudioDriver proof-plugin-build proof-runtime-probe-build proof-hal-io-probe-build
make -C apps/macos/AudioDriver proof-runtime-probe-run RUNTIME_PROBE_ARGS=--expect-default-safe
```

Expected result: current baseline passes before low-resource changes are
accepted. Any failure blocks implementation promotion.

## Installed Package Baseline

```sh
TWO_BRAIN_REC_ALLOW_ADHOC_APP_SIGNING=1 sh apps/macos/Installer/Scripts/build-local-installer.sh
sudo installer -pkg apps/macos/.build/installer/2brain-rec-local.pkg -target /
sudo killall coreaudiod || true
open -a "/Applications/2brain Rec.app"
make -C apps/macos/AudioDriver proof-runtime-probe-run RUNTIME_PROBE_ARGS=--expect-default-safe
```

Expected result: both virtual devices are visible/alive, hidden=0, and safe when
no client is using them. This proves publication only, not live route readiness.

## Low-Resource Startup Gate

After implementation, validate:

1. Open 2brain Rec with no active browser/meeting stream.
2. Confirm route state is `idle_safe` and no recording/transcription/upload is
   started.
3. Open a browser or meeting app using `2brain Rec Microphone` and/or
   `2brain Rec Speaker`.
4. Confirm passthrough activates without pressing `Run Check`.
5. Confirm every startup attempt resolves within 3000 ms as ready, blocked,
   failed, or fallback.

Expected result: user can hear and be heard, no remote-to-mic loopback is
observed, and no hidden recording starts.

## Route Truth Diagnostics Gate

Collect metadata-only route diagnostics for:

- idle-safe with devices visible;
- active microphone stream with natural silence;
- active speaker stream;
- stale app heartbeat;
- app exit while devices remain selected;
- self-routing attempt;
- virtual/aggregate/multi-output physical-device attempt.

Expected result: diagnostics show separate publication, client IO, app bridge,
physical-device, and recording-trigger planes. Device visibility alone never
renders ready.

## Realtime Safety Gate

```sh
sh tests/macos/static/audio-rt-safety-check.sh
rg -n "Trace\\(|TraceVerbose\\(|open\\(|write\\(|std::chrono|Date\\(|DispatchQueue\\.sync|AudioObjectGetPropertyData" apps/macos/AudioDriver/Sources/Plugin apps/macos/RecApp/Sources/Capture || true
```

Expected result: static/manual review confirms HAL callback-sensitive paths have
no file IO, logging, allocation, wall-clock, blocking IPC, lock waits, process
launches, network calls, or UI work. Any finding in a callback path blocks
promotion.

## No-Hang And CPU Gate

Run the existing no-hang/CPU harness or checklist for:

- macOS Sound settings;
- Chrome audio/device settings;
- Opera audio/device settings;
- Zoom audio settings;
- Yandex Telemost audio settings.

Expected result: each surface opens within 5 seconds or is recorded as
blocked/not accepted with a reason. During no-call idle, `coreaudiod` must not
sustain CPU above 10% for more than 30 consecutive seconds.

## Recovery Gate

Record metadata-only evidence for:

- `coreaudiod` restart;
- sleep/wake;
- physical microphone change;
- physical output change;
- stale browser device ID;
- app bridge heartbeat loss.

Expected result: ready UI clears within 5 seconds and returns only after valid
route evidence. Virtual devices remain visible and fail-closed by default.

## Browser/Meeting Smoke Gate

Use local short smoke checks in Chrome, Opera, Zoom, and Telemost:

- selected input: `2brain Rec Microphone`;
- selected output: `2brain Rec Speaker`;
- user is heard: yes;
- user hears: yes;
- remote-to-mic loopback: no;
- recording/transcription/upload: no.

Expected result: low-resource mode matches the accepted 005 smoke matrix before
it can become default.

## Fallback Gate

Trigger or simulate a P1 low-resource failure and restore the accepted
`005-macos-passthrough-release-hardening` app-launch lifecycle without
reinstalling the HAL driver.

Expected result: fallback is metadata-recorded and working route behavior returns
without driver reinstall.

## Redaction Gate

```sh
swift test --package-path apps/macos --disable-swift-testing --filter DiagnosticRedactionTests
rg -n "(BEGIN (RSA|OPENSSH|PRIVATE) KEY|AKIA[0-9A-Z]{16}|xox[baprs]-|ghp_|sk-[A-Za-z0-9]{20,}|signed_url|signedUrl|token=|password=)" apps/macos tests/macos qa/macos specs/006-low-resource-audio || true
```

Expected result: tests pass; scan results are policy text or deliberate fixture
strings only.
