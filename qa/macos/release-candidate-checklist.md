# macOS Release Candidate Checklist (MVP)

## Validation Log (2026-05-31)

- [x] Local Developer Tools Security recovery executed: app launches from `/Applications/2brain Rec.app` in local ad-hoc development mode.
- [x] Local installer build executed: `sh apps/macos/Installer/Scripts/build-local-installer.sh` created `apps/macos/.build/installer/2brain-rec-local.pkg`.
- [x] App UI confirms the driver package is installed and both virtual devices are visible in macOS.
- [x] App UI truthfully blocks readiness with `not ready for calls yet` because real audio passthrough is not implemented and verified.
- [x] `swift build --package-path apps/macos -c release --product TwoBrainRecApp` executed: PASS.
- [x] `swift test --package-path apps/macos` executed: PASS.
- [x] `make -C apps/macos/AudioDriver proof-plugin-build` executed after safety correction: PASS.
- [x] `TWO_BRAIN_REC_ALLOW_ADHOC_APP_SIGNING=1 sh apps/macos/Installer/Scripts/build-local-installer.sh` executed in packaging-only shell validation: PASS.
- [ ] Updated proof driver not installed/restarted from this agent shell because admin `sudo` is unavailable in the Codex execution environment.
- [ ] CLI runtime probe in this shell currently returns an empty Core Audio device list; rerun from the user's interactive Terminal after installing the updated proof driver.
- [ ] Real microphone-to-virtual-microphone passthrough not accepted.
- [ ] Real virtual-speaker-to-physical-speaker passthrough not accepted.
- [ ] Browser meeting end-to-end validation not run.
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
- [x] Local-to-remote loopback remains below **-35 dB** in synthetic check
- [ ] Local-to-remote loopback remains below **-35 dB** in a real browser meeting
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
- Loopback signal correlation target: `remote_to_mic <= -35 dB`
- Local buffer warning: policy warning fraction / critical fraction and reserve policy must prevent silent loss
- Disk reserve safety: stop capture or degrade before reserve is breached

## Known Deviation Log

- [x] 2026-05-31: Current build is a driver publication and readiness UI build, not a production passthrough build. The expected app state is `not ready for calls yet`.
- [ ] Fill remaining observations with run date + artifact reference before release
- [ ] Update this checklist after each quickstart run
