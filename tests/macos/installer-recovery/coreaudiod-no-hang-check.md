# Core Audio No-Hang Check

Status: pending stabilization validation

Purpose: prove that installing and launching `2brain Rec` does not destabilize
the macOS Core Audio stack when live passthrough is disabled by default.

## Preconditions

- Local package is installed.
- `TWO_BRAIN_REC_ENABLE_EXPERIMENTAL_PASSTHROUGH` is not set.
- `2brain Rec Microphone` and `2brain Rec Speaker` are visible in Core Audio.
- No meeting app is actively using `2brain Rec Speaker` for live passthrough.

## Steps

- [ ] Restart `coreaudiod`.
- [ ] Launch `2brain Rec` normally.
- [ ] Wait 30 seconds with no call active.
- [ ] Confirm `coreaudiod` remains near idle and does not sustain CPU above 10%.
- [ ] Launch System Settings → Sound and confirm it opens without hanging.
- [ ] Launch Zoom audio settings and confirm it opens without hanging.
- [ ] Launch Yandex Telemost audio settings and confirm it opens without hanging.
- [ ] Run `make -C apps/macos/AudioDriver proof-runtime-probe-run`.
- [ ] Confirm the probe reports both virtual devices visible with `running=0`.
- [ ] Confirm app diagnostics include `passthrough_bridge_disabled`, not
  `passthrough_bridge_started`.

## Evidence To Record

- Date/time and macOS version.
- `coreaudiod` PID and CPU before/after.
- Runtime probe output.
- App log tail without raw audio or meeting content.
- Pass/blocked/not accepted status for System Settings, Zoom, and Yandex
  Telemost launch behavior.

## Acceptance

Accepted only when all steps pass. Any sustained `coreaudiod` CPU spike,
application hang, automatic bridge start, or `running=1` state blocks live
passthrough acceptance.
