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
| Chrome browser meetings | Not accepted in this cycle | Physical browser-call validation not run yet; do not mark supported |
| Opera browser meetings | Not accepted in this cycle | Physical browser-call validation not run yet; do not mark supported |
| Yandex Browser meetings | Not accepted in this cycle | Physical browser-call validation not run yet; do not mark supported |
| Yandex Telemost in browser | Not accepted in this cycle | Physical browser-call validation not run yet; do not mark supported |

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

Real browser meeting validation is not accepted for this cycle. Until physical
browser calls are run, the targets above remain not accepted rather than
passed. This is metadata-only release evidence: the local passthrough stack may
be validated synthetically, but browser target support is still pending.

## 004 Stabilization Update 2026-06-01

Spec Kit Phase 7 split evidence into four lanes:

- default-safe publication evidence: virtual devices are visible, alive, and
  `running=0`;
- synthetic policy evidence: model and contract checks may print `ACCEPTED`;
- controlled live-engineering evidence: enabled only with explicit experiment
  gates and not release accepted by default;
- physical/browser acceptance evidence: required before any browser target can
  move from `Not accepted` to `Passed`.

The browser matrix remains `Not accepted` until physical/browser acceptance
evidence exists. Synthetic checks and runtime publication proof are not browser
support evidence.

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
