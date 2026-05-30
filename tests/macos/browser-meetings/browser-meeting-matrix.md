# Browser Meeting Matrix

## Scope

Validate US2 in real browser meetings after passthrough and capture routing are
implemented. These scenarios are not satisfied by the current publication proof;
they become release-candidate evidence only after real capture artifacts are
produced by the driver/app stack.

## Required Setup

- `2brain Rec Microphone` selected as the meeting microphone.
- `2brain Rec Speaker` selected as the meeting speaker.
- A real physical microphone and physical output selected inside 2brain Rec.
- Manual capture start; no assisted auto-start required for this feature.
- Visible local capture indicator and one-action stop available before capture.
- Diagnostics stay redacted and must not include raw audio or transcript text.

## Target Matrix

| Target | US2 Status | Required Evidence |
|---|---|---|
| Chrome browser meetings | Planned | 30-minute call, separate local/remote tracks, no-loopback harness pass |
| Opera browser meetings | Planned | 30-minute call, separate local/remote tracks, no-loopback harness pass |
| Yandex Browser meetings | Planned | 30-minute call, separate local/remote tracks, no-loopback harness pass |
| Yandex Telemost in browser | Planned after QA | 30-minute call, separate local/remote tracks, no-loopback harness pass |

## Per-Target Steps

- [ ] Join a meeting with one local speaker and at least one remote speaker.
- [ ] Confirm browser uses `2brain Rec Microphone` and `2brain Rec Speaker`.
- [ ] Start capture manually from visible 2brain Rec UI.
- [ ] Speak locally and play remote speech.
- [ ] Confirm local mic audio appears only on the local mic track.
- [ ] Confirm remote speaker audio appears only on the remote speaker track.
- [ ] Confirm remote speaker audio is absent from the virtual microphone path.
- [ ] Run `tests/macos/route-synthetic/no-loopback-check.swift` against
      exported/fixture route data when real capture export exists.
- [ ] Confirm stopping capture takes one local action.

## Pass Criteria

- Live call audio remains usable during capture.
- No remote-to-mic loopback is detected.
- Local and remote tracks are separate and timestamped.
- Any missing or degraded track marks the session degraded before finalization.
- Unsupported/browser-specific failures are recorded without marketing the
  target as supported.
