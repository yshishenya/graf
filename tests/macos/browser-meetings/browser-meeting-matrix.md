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
| Chrome browser meetings | Passed for manual call smoke test | User reported Chrome checked after `Run Check`; bidirectional passthrough accepted for smoke coverage |
| Opera browser meetings | Passed for manual call smoke test | User reported Opera checked after `Run Check`; bidirectional passthrough accepted for smoke coverage |
| Yandex Browser meetings | Not accepted in this cycle | User explicitly chose not to run this target; record as skipped/not accepted, not failed |
| Yandex Telemost | Passed for manual call smoke test | User confirmed after `Run Check`: remote side hears local speech, local user hears remote audio, no echo/loopback |

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

## 004 Failed Browser Report And Fix Probe 2026-06-01

Manual browser checks before the latest driver/app fixes reported that neither
microphone nor speaker audio worked in Telemost, browser Telemost, and Google
Meet even though the virtual devices were selectable. This is recorded as a
real failed browser report, not as a user setup issue.

Root-cause investigation found that the installed stack could publish devices
without a truthful live I/O state:

- the app-side heartbeat could be absent or stale while the devices remained
  visible;
- `DeviceIsRunning` did not reflect `StartIO`/`StopIO`;
- the driver advertised both input and output operations for both virtual
  devices;
- zero timestamp state was shared across the microphone and speaker devices;
- the app bridge could choose devices by name before trying the actual default
  physical input/output.

After the fix, a local HAL I/O probe against the installed virtual devices
started real Core Audio I/O callbacks for both devices:

```text
2brain Rec Microphone: callbacks=188 frames=96256
2brain Rec Speaker: callbacks=188 frames=96256
```

This moves the implementation back to **ready for browser re-test**, but it does
not change any target below to `Passed`. The next browser run must explicitly
record local speech usability and remote audio usability after selecting
`2brain Rec Microphone` and `2brain Rec Speaker`.

## 004 Browser Local Self-Test Evidence 2026-06-01

After pressing `Run Check` in the installed 2brain Rec app, the user confirmed
that browser and Telemost local audio tests became usable. The tested flow was:

- the app started explicit live passthrough readiness;
- the browser/Telemost test recorded audio through the selected microphone path;
- the test played the recorded voice back through the selected speaker path;
- the user heard the recorded voice.

Status: **local browser/Telemost self-test accepted after explicit `Run Check`**.

This is stronger than HAL publication or synthetic proof because it exercises a
real browser/Telemost audio test after the app starts passthrough. It is still
not full browser meeting acceptance: a controlled call with a remote/control
side must still confirm that local speech reaches the other side, remote audio
is heard locally, and remote audio does not leak into `2brain Rec Microphone`.

## 004 Telemost Manual Call Evidence 2026-06-01

After pressing `Run Check` in the installed 2brain Rec app, the user joined a
Telemost call with `2brain Rec Microphone` and `2brain Rec Speaker` selected.

Evidence:

- remote/control side heard the local user: yes;
- local user heard remote/control side: yes;
- echo or remote-to-mic loopback was not observed: yes.

Status: **Yandex Telemost manual call smoke test passed**.

This accepts the Telemost smoke scenario for bidirectional passthrough. It does
not yet accept the full browser matrix: Chrome, Opera, and Yandex Browser still
need the same remote/control-side validation before the broader browser target
task can be closed.

## 004 Chrome, Opera, And Yandex Browser Decision 2026-06-01

After the Telemost call smoke test passed, the user also checked Chrome and
Opera. Both are accepted for manual call smoke coverage after explicit
`Run Check`.

Yandex Browser is intentionally not run in this cycle. Its status is
`Not accepted / skipped by decision`, not failed. This records target evidence
for the matrix without claiming unsupported validation.

Status summary:

- Chrome: passed manual smoke coverage after `Run Check`;
- Opera: passed manual smoke coverage after `Run Check`;
- Yandex Browser: skipped/not accepted by explicit decision;
- Yandex Telemost: passed manual call smoke coverage after `Run Check`.

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
