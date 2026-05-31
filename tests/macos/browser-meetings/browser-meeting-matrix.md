# Browser Meeting Matrix

## Scope

Validate real browser meetings after bidirectional passthrough is implemented.
These scenarios are not satisfied by publication proof alone; they become
release-candidate evidence only after local speech and remote audio both move
through the 2brain Rec virtual devices without starting recording.

## Required Setup

- `2brain Rec Microphone` selected as the meeting microphone.
- `2brain Rec Speaker` selected as the meeting speaker.
- A real physical microphone and physical output selected inside 2brain Rec.
- Live passthrough is active and visibly non-recording.
- Recording, transcript generation, upload, and assisted auto-start remain off
  for this feature.
- Diagnostics stay redacted and must not include raw audio or transcript text.

## Target Matrix

| Target | 004 Status | Required Evidence |
|---|---|---|
| Chrome browser meetings | Pending 004 passthrough evidence | Local speech usable, remote audio usable, no recording started, no loopback above threshold |
| Opera browser meetings | Pending 004 passthrough evidence | Pass or blocked/not accepted reason with metadata-only evidence |
| Yandex Browser meetings | Pending 004 passthrough evidence | Pass or blocked/not accepted reason with metadata-only evidence |
| Yandex Telemost in browser | Pending 004 passthrough evidence | Pass or blocked/not accepted reason with metadata-only evidence |

## 004 Evidence Fields

Each target must record:

- target name and version if available;
- selected meeting microphone;
- selected meeting speaker;
- live passthrough state before joining;
- route state after joining;
- local speech usability;
- remote audio usability;
- pass, blocked, or not accepted status;
- concrete failure reason when not passed.

Evidence must remain metadata-only and must not include raw audio, transcript
text, credentials, tokens, signed URLs, or meeting content.

## 004 Evidence Recorded 2026-05-31

Backend/network outage synthetic coverage was executed:

```text
live-passthrough-outage-check: ACCEPTED
```

Real browser meeting validation is still pending for 004. Until physical
browser calls are run, the targets above remain pending rather than passed.

## Per-Target Steps

- [ ] Join a meeting with one local speaker and at least one remote speaker.
- [ ] Confirm browser uses `2brain Rec Microphone` and `2brain Rec Speaker`.
- [ ] Confirm 2brain Rec shows visible non-recording live passthrough state.
- [ ] Speak locally and play remote speech.
- [ ] Confirm local speech reaches the remote/control side.
- [ ] Confirm remote speaker audio is heard locally through the selected
      physical output.
- [ ] Confirm remote speaker audio is absent from the virtual microphone path.
- [ ] Run `tests/macos/route-synthetic/no-loopback-check.swift` against
      exported/fixture route data when real capture export exists.
- [ ] Confirm no recording or transcript generation starts during validation.

## Pass Criteria

- Live call audio remains usable during passthrough.
- No remote-to-mic loopback is detected.
- Unsupported/browser-specific failures are recorded without marketing the
  target as supported.
