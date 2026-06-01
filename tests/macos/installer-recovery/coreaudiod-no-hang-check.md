# Core Audio No-Hang Check

Status: pending stabilization validation

Purpose: prove that installing and launching `2brain Rec` does not destabilize
the macOS Core Audio stack when the non-recording live passthrough route starts
automatically.

## Preconditions

- Local package is installed.
- `2brain Rec Microphone` and `2brain Rec Speaker` are visible in Core Audio.
- No meeting app is actively using `2brain Rec Speaker` for live passthrough.
- For metadata-only dry runs, leave `TWO_BRAIN_REC_RUN_UI_NO_HANG` unset.
- For actual UI-launch evidence, set `TWO_BRAIN_REC_RUN_UI_NO_HANG=1`.

## Steps

- [ ] Restart `coreaudiod`.
- [ ] Launch `2brain Rec` normally.
- [ ] Run `sh apps/macos/Scripts/coreaudiod-cpu-sample.sh`.
- [ ] Confirm `coreaudiod` remains near idle and does not sustain CPU above 10%.
- [ ] Run `sh apps/macos/Scripts/audio-settings-no-hang-check.sh all`.
- [ ] For final no-hang evidence, rerun with
  `TWO_BRAIN_REC_RUN_UI_NO_HANG=1` and record whether each target opens within
  5 seconds.
- [ ] Include macOS Sound settings, Chrome audio settings, Opera audio settings,
  Zoom audio settings, and Yandex Telemost audio settings.
- [ ] Run `make -C apps/macos/AudioDriver proof-runtime-probe-run`.
- [ ] Confirm the probe reports both virtual devices visible with `running=0`.
- [ ] Confirm app diagnostics include `passthrough_bridge_started` with
  automatic non-recording startup detail.

## Evidence To Record

- Date/time and macOS version.
- `coreaudiod` PID and CPU before/after.
- Runtime probe output.
- App log tail without raw audio or meeting content.
- Pass/blocked/not accepted status for macOS Sound, Chrome, Opera, Zoom, and
  Yandex Telemost launch behavior.

## Acceptance

Accepted only when all steps pass. Any sustained `coreaudiod` CPU spike,
application hang, hidden recording/transcription/upload, or unexpected
`running=1` state without a Core Audio client blocks live passthrough
acceptance.
