# Implementation Evidence: Low-Resource Reliable macOS Audio

Feature: `006-low-resource-audio`
Date: 2026-06-01

## Automated Gates

| Gate | Command | Result | Notes |
| --- | --- | --- | --- |
| Swift model/contract build | `swift test --package-path apps/macos --disable-swift-testing` | passed | Local SwiftPM `swift-testing` execution remains disabled per project quickstart. |
| Contract fixtures | `swift run --package-path apps/macos ContractValidation` | passed | Existing contract validator accepted all configured fixtures. |
| Realtime safety scan | `sh tests/macos/static/audio-rt-safety-check.sh` | passed | HAL callback-sensitive static gate accepted. |
| HAL proof/runtime probes | `make -C apps/macos/AudioDriver proof-plugin-build proof-runtime-probe-build proof-hal-io-probe-build && make -C apps/macos/AudioDriver proof-runtime-probe-run RUNTIME_PROBE_ARGS=--expect-default-safe` | passed | Both virtual devices visible/alive, hidden=0, running=0 in idle-safe surface. |
| Low-resource validation | `TWO_BRAIN_REC_RUN_LOW_RESOURCE_COREAUDIOD_RESTART=1 sh apps/macos/Scripts/validate-low-resource-audio.sh` | passed available gates | Coreaudiod restart recovery accepted; browser smoke remains metadata-only until live meeting run. |
| No-hang/startup | `TWO_BRAIN_REC_RUN_UI_NO_HANG=1 sh apps/macos/Scripts/validate-low-resource-no-hang.sh` | passed | macOS Sound, Chrome, Opera, Zoom, and Telemost surfaces opened within 5 seconds. |
| Idle CPU quiet-state gate | `sh apps/macos/Scripts/coreaudiod-cpu-sample.sh` after closing opened UI surfaces | passed | Peak was transient; sustained above 10% lasted 20 seconds, below the 30-second threshold. |
| Auto-idle release after virtual client closes | `make -C apps/macos/AudioDriver proof-hal-io-probe-run`; `pmset -g assertions`; `sh apps/macos/Scripts/coreaudiod-cpu-sample.sh` | passed | HAL I/O client opened and closed both virtual devices; no BuiltIn mic/speaker assertions remained; post-client CPU peak was 0.6%. |
| Browser/meeting smoke | Manual checks in Telemost, Chrome, Opera, and Zoom | passed | User confirmed sound works in all four targets with `2brain Rec Microphone` and `2brain Rec Speaker`. |
| Final idle sanity | `make -C apps/macos/AudioDriver proof-runtime-probe-run RUNTIME_PROBE_ARGS=--expect-default-safe`; `sh apps/macos/Scripts/coreaudiod-cpu-sample.sh` | passed | Runtime proof accepted; CPU peak 8%, sustained above threshold 0 seconds. |
| Installer package build | `TWO_BRAIN_REC_ALLOW_ADHOC_APP_SIGNING=1 sh apps/macos/Installer/Scripts/build-local-installer.sh` | passed | Package written to `apps/macos/.build/installer/2brain-rec-local.pkg`. |
| Installed package baseline | `sudo installer -pkg apps/macos/.build/installer/2brain-rec-local.pkg -target /`; `sudo killall coreaudiod`; `make -C apps/macos/AudioDriver proof-runtime-probe-run RUNTIME_PROBE_ARGS=--expect-default-safe` | passed | Package upgrade succeeded; runtime proof accepted after Core Audio restart. |
| Diagnostics redaction | `swift test --package-path apps/macos --disable-swift-testing --filter DiagnosticRedactionTests` plus secret scan | passed available gates | `rg` matches were policy/fixture forbidden-field strings only. |

## Implemented Evidence Coverage

- Idle-safe publication keeps public virtual devices visible and non-running.
- Automatic route activation arms on launch and waits for virtual-device client IO instead of opening physical devices eagerly.
- Startup attempts resolve to `ready`, `blocked`, `failed`, or `fallback` with a 3000 ms evidence window.
- Recovery events cover stale heartbeat, `coreaudiod` restart, sleep/wake, physical-device changes, and stale browser device IDs.
- Working-device evidence rejects 2brain virtual, other virtual, aggregate, and multi-output selections by default.
- Route truth diagnostics keep publication, client IO, app bridge, physical-device, and recording-trigger planes separate.
- Promotion gate falls back to `005-macos-passthrough-release-hardening` unless all P1 gates pass.

## Not Accepted In This Run

- UI no-hang surfaces passed with `TWO_BRAIN_REC_RUN_UI_NO_HANG=1`.
- Local `coreaudiod` restart recovery passed with `TWO_BRAIN_REC_RUN_LOW_RESOURCE_COREAUDIOD_RESTART=1`.
- A combined run immediately after opening all UI audio surfaces blocked the CPU gate once with sustained CPU above threshold for 35 seconds; after closing those surfaces and waiting for idle, the CPU gate passed. Treat this as a transient-load caveat, not as browser/meeting acceptance.
- A later manual CPU blocker was traced to an active 2brain route holding BuiltIn mic/speaker assertions after a test session. The route engine now auto-releases the physical route when virtual-device client IO closes, and the installed app validated with no remaining BuiltIn assertions and a passed post-client CPU sample.
- Telemost initially failed because the route was released too quickly during sound check; the explicit-route idle grace window was increased to cover real meeting-app sound-check behavior.
- Browser/meeting smoke passed manually for Telemost, Chrome, Opera, and Zoom.
- Final idle sanity passed after browser/meeting smoke: both virtual devices were visible/alive/non-running and `coreaudiod` stayed below sustained CPU threshold.
- Installed package baseline was completed after password-backed sudo approval: package upgrade succeeded, `coreaudiod` restarted, and runtime publication proof accepted.
