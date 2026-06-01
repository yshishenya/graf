# macOS Release Candidate Checklist (MVP)

## Passthrough Release Hardening Evidence (005)

- [ ] Pre-recording stability evidence records installed runtime, short smoke,
  route state, CPU/no-hang behavior, and inactive recording/transcription/upload
  status.
- [ ] Installed runtime baseline includes
  `proof-runtime-probe-run RUNTIME_PROBE_ARGS=--expect-default-safe` or a
  recorded blocked/not accepted reason.
- [ ] Short smoke evidence is explicitly labeled as smoke-only and not
  long-duration recording-assisted acceptance.
- [ ] No-hang evidence covers macOS Sound settings, Chrome audio settings, Opera
  audio settings, Zoom audio settings, and Yandex Telemost audio settings.
- [ ] Audio settings no-hang evidence records actual UI-launch evidence with
  `TWO_BRAIN_REC_RUN_UI_NO_HANG=1`, or records metadata-only `not_accepted`
  reasons when UI launch is intentionally skipped.
- [ ] `coreaudiod` CPU does not sustain above 10% for more than 30 consecutive
  seconds during no-call idle with the app open.
- [ ] Physical input/output changes, aggregate or multi-output routes,
  Bluetooth routes, stale browser device IDs, `coreaudiod` restart, and
  sleep/wake record passed, blocked, or not accepted metadata-only outcomes.
- [ ] Installer lifecycle evidence covers install, update, repair, rollback,
  uninstall, and reinstall without hidden manual cleanup.
- [ ] Destructive installer lifecycle checks are either run with
  `TWO_BRAIN_REC_RUN_INSTALLER_LIFECYCLE=1` or recorded as `not_accepted`, not
  `passed`.
- [ ] Diagnostics and release evidence contain no raw audio, transcript text,
  credentials, tokens, signed URLs, passwords, or meeting content.
- [ ] UI evidence distinguishes non-recording passthrough active/ready state
  from recording, transcription, and capture-active states.
- [ ] Long-duration recording-assisted acceptance remains deferred until local
  recording, retention, and deletion rules exist.
- [ ] `qa/macos/recording-assisted-acceptance.md` remains blocked and is not
  counted as passed for the pre-recording hardening slice.

## Live Route Readiness Evidence (003)

- [ ] Fresh local install moves from `not ready for calls yet` to ready only
  after microphone and speaker live route evidence pass.
- [ ] Publication-only evidence never produces ready state in app UI,
  diagnostics, or release evidence.
- [ ] Self-routing is rejected when a 2brain Rec virtual device is selected as a
  physical working device.
- [ ] Aggregate and multi-output speaker routes are marked managed/blocked
  unless the selected physical output can be measured by the same criteria as a
  direct built-in or wired route.
- [ ] Built-in/wired added route latency is `<= 30 ms` before release-ready
  status is accepted.
- [ ] Built-in/wired remote-to-mic leakage is `<= -45 dB` and not intelligible
  before release-ready status is accepted.
- [ ] Latency/leakage failures map to degraded route state and block
  release-ready status while preserving live-route diagnostics.
- [ ] Chrome, Opera, Yandex Browser, and Yandex Telemost-in-browser each have
  pass or blocked/not accepted metadata-only evidence.
- [ ] Browser evidence records selected meeting microphone/speaker, readiness
  state before join, route state after join, local speech usability, remote
  audio usability, and concrete blocked/not accepted reasons.
- [ ] A 5-minute backend/network outage does not interrupt live route
  passthrough after readiness passes.
- [ ] Physical device, browser target, Bluetooth profile, app heartbeat, and
  `coreaudiod` changes make readiness stale within 5 seconds and show a
  recovery action.
- [ ] Diagnostics contain route status, failure category, recovery action,
  latency/leakage values, and browser evidence without raw audio, transcript
  text, credentials, tokens, signed URLs, or meeting content.

## Real Bidirectional Passthrough Evidence (004)

- [ ] Selected physical microphone audio reaches `2brain Rec Microphone`
  without starting recording.
- [ ] Audio sent to `2brain Rec Speaker` plays through the selected physical
  output without starting recording.
- [ ] Built-in/wired added route latency remains `<= 30 ms` while marked ready.
- [ ] Remote-to-mic leakage remains `<= -45 dB` relative to speaker reference
  and is not intelligible while marked ready.
- [ ] App/route-engine loss makes public virtual devices hidden or unavailable
  within 5 seconds.
- [ ] `coreaudiod` restart marks passthrough stale and requires revalidation.
- [ ] Chrome, Opera, Yandex Browser, and Yandex Telemost-in-browser each have
  pass or blocked/not accepted metadata-only passthrough evidence.
- [ ] Diagnostics contain passthrough state, selected device identifiers,
  heartbeat status, latency/leakage values, browser evidence, and recovery
  action without raw audio, transcript text, credentials, tokens, signed URLs, or
  meeting content.

## Validation Log (2026-05-31 04:16 MSK)

- [x] Updated local package installed with admin privileges: `installer`
  reported `The upgrade was successful`.
- [x] `coreaudiod` restarted after package installation.
- [x] Runtime probe before app kill: `2brain Rec Microphone` and
  `2brain Rec Speaker` were `FOUND hidden=0 alive=1`.
- [x] Runtime probe after app kill and heartbeat timeout: both public virtual
  devices were absent from the current Core Audio device list.
- [x] Runtime probe after app relaunch: both public virtual devices returned as
  `FOUND hidden=0 alive=1`.
- [x] Private app I/O fail-closed validation accepted in
  `apps/macos/AudioDriver/RuntimeProofReport.md`.
- [x] Backend/network outage synthetic check executed:
  `swift tests/macos/route-synthetic/passthrough-outage-check.swift` returned
  `passthrough-outage-check: ACCEPTED`.
- [x] Browser meeting matrix evidence recorded as blocked/not accepted for this
  feature state because the app truthfully remains `not ready for calls yet`
  until real bidirectional passthrough and capture artifacts exist.
- [x] Bluetooth/AirPods managed-route pilot evidence recorded as blocked/not
  accepted for this feature state because no Bluetooth headset route is
  currently connected and real passthrough/capture is not accepted.

## Validation Log (2026-06-01 Stabilization)

- [x] Spec Kit Phase 7 added stabilization/refactor gates after live bridge
  review found realtime callback, ring-buffer, readiness, and app-driver
  ownership blockers.
- [x] `audio-rt-safety-check.sh` added to the validation pipeline and currently
  passes after removing callback allocation/logging from `PassthroughBridge`.
- [x] `default-passthrough-disabled-check.sh` added and executed: PASS. Normal
  app launch does not start the app-side bridge and runtime probe remains
  `running=0`.
- [x] Runtime probe supports parameterized expectations through
  `RUNTIME_PROBE_ARGS=--expect-default-safe`,
  `RUNTIME_PROBE_ARGS=--expect-non-running-surface`, and
  `RUNTIME_PROBE_ARGS=--expect-visible-alive-surface`; these are Core Audio
  surface evidence only and cannot substitute for measured live audio
  acceptance.
- [x] Shared ring-buffer contract changed to explicit SPSC all-or-nothing writes;
  Swift behavior tests and C++ proof vectors pass.
- [x] Main validation script uses `swift test --disable-swift-testing` after the
  local SwiftPM `swift-testing` helper was observed hanging after build
  completion.
- [x] 2026-06-01 14:47 MSK installed runtime proof recorded in
  `apps/macos/AudioDriver/RuntimeProofReport.md`: package upgrade succeeded,
  publication/default-safe/non-running/visible-alive surface probes accepted,
  and `coreaudiod` settled to `0.0%` CPU after restart.
- [x] Diagnostics redaction scan completed for `apps/macos`, `tests/macos`,
  `qa/macos`, and `specs/004-real-bidirectional-passthrough`: matches were
  policy/fixture forbidden-field strings only, not live secrets or meeting
  content.
- [ ] Physical microphone-to-virtual-microphone live acceptance remains pending.
- [ ] Physical virtual-speaker-to-output live acceptance remains pending.
- [ ] Browser target acceptance remains pending for Chrome, Opera, Yandex
  Browser, and Yandex Telemost-in-browser.

## Validation Log (2026-05-31 06:07 MSK)

- [x] `swift build --package-path apps/macos -c release --product TwoBrainRecApp`: PASS.
- [x] `swift test --package-path apps/macos`: PASS.
- [x] `make -C apps/macos/AudioDriver proof-plugin-build proof-runtime-probe-build`: PASS.
- [x] `sh apps/macos/Scripts/validate-live-route-readiness.sh`: PASS for available automated checks.
- [x] Local package rebuilt and installed through `installer`: PASS.
- [x] Installer postinstall clears local HAL loading blockers before restarting
  `coreaudiod`; runtime publication proof is accepted without manual postinstall
  repair.
- [x] Runtime probe before app kill: `2brain Rec Microphone` and
  `2brain Rec Speaker` were `FOUND hidden=0 alive=1`.
- [x] Runtime probe after app kill and heartbeat timeout: both public virtual
  devices were absent from the current Core Audio device list.
- [x] Runtime probe after app relaunch: both public virtual devices returned as
  `FOUND hidden=0 alive=1`.
- [x] Browser target evidence remains blocked/not accepted for Chrome, Opera,
  Yandex Browser, and Yandex Telemost-in-browser until real bidirectional
  passthrough/capture artifacts are accepted.

## Validation Log (2026-05-31)

- [x] `swift build --package-path apps/macos -c release --product TwoBrainRecApp` executed after live passthrough task expansion: PASS.
- [x] `swift test --package-path apps/macos` executed after live passthrough task expansion: PASS.
- [x] `make -C apps/macos/AudioDriver proof-plugin-build` executed after private app I/O/fail-closed updates: PASS.
- [x] `sh apps/macos/Scripts/validate-foundation.sh` executed: `ContractValidation: PASS`, `AudioDriver proof scaffold: PASS`.
- [x] `sh apps/macos/Scripts/validate-live-passthrough-foundation.sh` executed: PASS.
- [x] Synthetic checks executed: no-loopback `-120 dB`, app I/O fail-closed, latency, backend outage, debug clip cleanup, and track integrity all accepted.
- [x] Secret/raw-content scan executed; matches were policy text or deliberate forbidden-field fixtures, not committed credentials or raw audio artifacts.
- [x] Local Developer Tools Security recovery executed: app launches from `/Applications/2brain Rec.app` in local ad-hoc development mode.
- [x] Local installer build executed: `sh apps/macos/Installer/Scripts/build-local-installer.sh` created `apps/macos/.build/installer/2brain-rec-local.pkg`.
- [x] App UI confirms the driver package is installed and both virtual devices are visible in macOS.
- [x] App UI truthfully blocks readiness with `not ready for calls yet` because real audio passthrough is not implemented and verified.
- [x] `swift build --package-path apps/macos -c release --product TwoBrainRecApp` executed: PASS.
- [x] `swift test --package-path apps/macos` executed: PASS.
- [x] `make -C apps/macos/AudioDriver proof-plugin-build` executed after safety correction: PASS.
- [x] `TWO_BRAIN_REC_ALLOW_ADHOC_APP_SIGNING=1 sh apps/macos/Installer/Scripts/build-local-installer.sh` executed in packaging-only shell validation: PASS.
- [x] Updated proof driver installed/restarted with admin privileges on
  2026-05-31 04:16 MSK; earlier sudo limitation is superseded.
- [x] CLI runtime probe from this shell now sees both virtual devices while the
  app heartbeat is alive.
- [ ] Real microphone-to-virtual-microphone passthrough not accepted.
- [ ] Real virtual-speaker-to-physical-speaker passthrough not accepted.
- [x] Private app I/O fail-closed validation accepted for app kill/relaunch.
- [x] Built-in/wired `<=30 ms` added route latency validation accepted in
  synthetic harness.
- [ ] Remote speaker leakage `<= -45 dB` against speaker reference not run in a real browser meeting.
- [ ] Browser meeting end-to-end validation blocked by current product gate:
  real passthrough/capture is not accepted.
- [ ] Separate local/remote track capture not accepted.

## Validation Log (2026-05-27)

- [x] `sh apps/macos/Scripts/validate-foundation.sh` executed: `ContractValidation: PASS`, `AudioDriver proof scaffold: PASS`.
- [x] `make -C apps/macos/AudioDriver proof-runtime-probe-run` executed: both virtual devices found, runtime proof accepted.
- [x] `swift tests/macos/route-synthetic/mic-route-check.swift` executed: ACCEPTED.
- [x] `swift tests/macos/route-synthetic/speaker-route-check.swift` executed: ACCEPTED.
- [x] `swift tests/macos/route-synthetic/no-loopback-check.swift` executed: ACCEPTED for synthetic model coverage only.
- [x] `swift tests/macos/physical-devices/track-integrity-check.swift` executed: ACCEPTED for synthetic model coverage only.
- [x] `sh apps/macos/Scripts/validate-us1-gate.sh` executed: PASS script-level checks (runtime probe remains externally documented by direct proof command).
- [ ] Fresh install/onboarding scenario requiring UI flow and permissions not run (manual).
- [ ] Route verification UI one-action ready-state enforcement not run (manual).
- [ ] Browser meeting matrix for Chrome/Opera/Yandex/Yandex Telemost not run (manual).
- [ ] 60-minute integrity runs (wired/Bluetooth/AirPods) not run (manual).
- [ ] Failure recovery matrix (permission/device/server/network/buffer recovery) not run (manual).
- [ ] Visible control one-action stop not run (manual).
- [ ] Update/repair/rollback/uninstall/reinstall lifecycle scenarios not run (manual).
- [ ] Diagnostics redaction generation per family not run end-to-end (contract tests only).

## Phase 0 Runtime Proof Gate

- [x] Virtual audio publication runtime proof accepted
- [x] OS: Apple Silicon macOS (14.5+)
- [x] Virtual devices are visible:
  - `2brain Rec Microphone`
  - `2brain Rec Speaker`

## US1 Readiness Gate

- [x] Route verification synthetic checks pass for mic and speaker
- [ ] Self-routing rejection enforced
- [ ] App shows `ready` only after both routes passed

## US2 Capture Gate

- [ ] Start capture in `audio_recording` mode only when route readiness evidence exists
- [ ] Capture remains separated as:
  - local microphone track
  - remote speaker track
- [ ] Wired tracks alignment for 60-minute calls remains under **100 ms**
- [ ] Wired track dropouts stay below **0.1%**
- [ ] Bluetooth/AirPods-class track dropouts stay below **0.5%**
- [x] Remote speaker leakage remains below **-45 dB** in synthetic check
- [ ] Remote speaker leakage remains below **-45 dB** in a real browser meeting
- [x] Private app I/O loss hides or makes public devices unavailable within 5 seconds
- [x] Built-in/wired added route latency stays at or below **30 ms** in
  synthetic validation
- [ ] Remote meeting audio does not appear in microphone track
- [ ] Server/network outage for 5 minutes does not stop passthrough
- [ ] Missing-track finalization marks session as degraded before finalization event
- [ ] Local capture indicator is visible during capture and one-action stop is available

## Recovery and UX Gate

- [ ] `detecting` and `ready` states are exposed before assisted start is invoked
- [ ] Local buffer policy can enter warning/critical/must-degrade states before hard loss
- [ ] Track and session finalization records visibility of degraded/missing-track state
- [ ] Unsupported targets/devices remain marked best-effort
- [ ] Diagnostics remain redacted by default (no raw audio, no transcript text, no credentials)

## US3 Recovery Gate

- [ ] Permission denied/revoked scenarios are explicitly surfaced and distinguishable from route failures
- [ ] Device disconnect/Bluetooth profile-switch scenarios produce explicit device/path recovery actions
- [ ] Buffer pressure transitions are reflected as warning/critical/must-degrade before drop occurs
- [ ] Restart recovery preserves buffer state and reports interrupted sessions truthfully
- [ ] Diagnostic redaction checks executed from `tests/macos/installer-recovery/diagnostic-redaction.md`

## US4 Lifecycle Gate

- [ ] Active-call update deferral is deterministic and does not force interruption (`tests/macos/installer-recovery/active-call-update-deferral.md`)
- [ ] Uninstall outputs machine-readable result with manual cleanup details when needed
- [ ] Reinstall flow is idempotent after uninstall and reports restore outcome
- [ ] Rollback and partial cleanup scenarios are reproducible (`tests/macos/installer-recovery/rollback-partial-cleanup.md`)
- [ ] Uninstall + reinstall quick-checks complete from `tests/macos/installer-recovery/uninstall-reinstall.md`

## Measured Thresholds (US2)

- Wired alignment threshold: **≤ 100 ms**
- Wired dropout threshold: **≤ 0.1 %**
- Bluetooth/AirPods dropout threshold: **≤ 0.5 %**
- Loopback signal correlation target: `remote_to_mic <= -45 dB`
- Built-in/wired added route latency threshold: `<= 30 ms`
- Local buffer warning: policy warning fraction / critical fraction and reserve policy must prevent silent loss
- Disk reserve safety: stop capture or degrade before reserve is breached

## Known Deviation Log

- [x] 2026-05-31: Current build is a driver publication and readiness UI build, not a production passthrough build. The expected app state is `not ready for calls yet`.
- [x] 2026-05-31 04:16 MSK: App I/O fail-closed proof is accepted, but browser
  and Bluetooth release-candidate checks remain blocked by the larger real
  passthrough/capture gate.
- [x] 2026-05-31: Feature 004 local package install, `coreaudiod` restart,
  runtime publication probe, driver heartbeat fail-closed gate, and synthetic
  live passthrough checks are accepted. Chrome, Opera, Yandex Browser, and
  Yandex Telemost browser-call evidence is recorded as not accepted until
  physical browser calls are run.
- [ ] Fill remaining observations with run date + artifact reference before release
- [ ] Update this checklist after each quickstart run
