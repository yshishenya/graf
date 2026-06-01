# Low-Resource Audio Gate (006)

This gate controls promotion of low-resource macOS audio behavior to the local
default. It validates requirements quality, clean-room boundaries, metadata-only
evidence, and fallback to the accepted 005 app-launch lifecycle.

## Required Evidence Before Promotion

- [ ] Runtime publication evidence shows `2brain Rec Microphone` and
  `2brain Rec Speaker` visible/alive with `hidden=0` while idle-safe.
- [ ] Automatic activation evidence proves browser/meeting audio can activate
  passthrough without pressing `Run Check`.
- [ ] Recording boundary evidence proves the driver creates no recordings,
  transcripts, uploads, MediaScribe requests, Langfuse traces, analytics, or
  external egress.
- [ ] Startup evidence proves every physical route attempt resolves within
  3000 ms as `ready`, `blocked`, `failed`, or `fallback`.
- [ ] No-hang evidence covers macOS Sound settings, Chrome, Opera, Zoom, and
  Yandex Telemost surfaces within 5 seconds or records blocked/not accepted.
- [ ] Idle CPU evidence proves `coreaudiod` does not sustain above 10% for more
  than 30 consecutive seconds during no-call idle.
- [ ] Silent-stream evidence proves natural silence does not downgrade an open
  client IO stream.
- [ ] Physical-device policy evidence rejects 2brain Rec virtual devices and
  marks other virtual, aggregate, or multi-output devices unsupported unless a
  later gate accepts them.
- [ ] Realtime-safety evidence finds no file IO, logging, allocation, wall-clock
  calls, lock waits, blocking IPC, process launches, network calls, or UI work
  in HAL callback-sensitive paths.
- [ ] Recovery evidence covers `coreaudiod` restart, sleep/wake, physical device
  changes, stale browser device IDs, app exit, and stale heartbeat.
- [ ] Fallback evidence proves the accepted 005 app-launch lifecycle can be
  restored without reinstalling the HAL driver.
- [ ] Diagnostics and validation artifacts contain no raw audio, transcript
  text, meeting content, credentials, tokens, signed URLs, passwords, or live
  secret paths.

## Clean-Room Review

- [x] Krisp was used only for public documentation, installed-component
  observation, logs, strings, and behavior-level inference.
- [x] Implementation does not copy Krisp proprietary code, assets, identifiers,
  UI text, protocols, or protected implementation details.
- [x] User-facing language uses original 2brain Rec terminology and remains
  brand-distinct.

## Implementation Evidence (2026-06-01)

- [x] Runtime publication proof accepted with both virtual devices visible,
  alive, hidden=0, and running=0 while idle-safe.
- [x] Static realtime-safety scan accepted.
- [x] Swift model/contract build accepted with `swift test --disable-swift-testing`.
- [x] Contract validation accepted with `ContractValidation: PASS`.
- [x] Low-resource validation script completed available metadata-safe gates.
- [x] No-hang/startup script accepted startup timeout and opened macOS Sound,
  Chrome, Opera, Zoom, and Telemost surfaces within 5 seconds with UI launch
  enabled.
- [x] Idle CPU quiet-state gate passed after closing opened UI surfaces; a
  combined run immediately after opening every surface produced a transient
  sustained CPU blocker and should not be counted as live meeting acceptance.
- [x] Auto-idle release after virtual client close passed: HAL I/O probe opened
  and closed both virtual devices, BuiltIn mic/speaker assertions were absent
  afterward, and post-client CPU sample passed.
- [x] Fallback evidence records fallback to
  `005-macos-passthrough-release-hardening` without claiming recording,
  transcription, upload, MediaScribe, or Langfuse activity.
- [x] Diagnostics scan findings were policy/fixture forbidden-field strings,
  not live secrets or meeting content.
- [x] Installed package baseline upgrade completed with admin approval;
  `coreaudiod` was restarted and runtime publication proof accepted afterward.
- [x] Browser/meeting smoke passed manually for Telemost, Chrome, Opera, and
  Zoom with `2brain Rec Microphone` and `2brain Rec Speaker`.
- [x] Final idle sanity passed after browser/meeting smoke: runtime proof
  accepted and `coreaudiod` CPU peak was 8% with 0 sustained seconds above
  threshold.

## Manual Browser/Meeting Smoke Instructions

Run this once per target: Chrome, Opera, Zoom, and Yandex Telemost.

1. Start from idle: close existing meeting/audio settings windows and wait 10 seconds.
2. Open 2brain Rec and confirm the virtual devices are visible.
3. In the target app, select `2brain Rec Microphone` as microphone and
   `2brain Rec Speaker` as speaker.
4. Join a test call with another device or a trusted helper.
5. Confirm the remote side hears local speech.
6. Confirm local user hears remote speech.
7. Confirm remote audio does not loop back into the virtual microphone.
8. Confirm 2brain Rec does not show or create recording, transcript, upload,
   MediaScribe, Langfuse, or external egress activity.
9. Stop the call, wait 10 seconds, then run:

```sh
make -C apps/macos/AudioDriver proof-runtime-probe-run RUNTIME_PROBE_ARGS=--expect-default-safe
sh apps/macos/Scripts/coreaudiod-cpu-sample.sh
```

Acceptance: each target is either `passed` with user-heard/user-hears/no-loopback
evidence, or `blocked/not_accepted` with a concrete reason. Do not mark browser
smoke as passed from publication-only or settings-only evidence.

## Promotion Rule

Low-resource mode may become the local default only when every P1 gate passes in
one validation run or a documented equivalent run set with no open P1
regressions.

If any P1 gate fails:

- low-resource mode remains `blocked` or `not_accepted`;
- the accepted 005 app-launch lifecycle remains or is restored as default;
- the failure records a metadata-only reason and remediation target.
