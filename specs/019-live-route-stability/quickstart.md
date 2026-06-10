# Quickstart: Live Route Stability Validation

## Scope

Use this guide to validate `019-live-route-stability` after implementation
tasks are complete. This guide is not an implementation task list.

## Prerequisites

- macOS on Apple Silicon.
- 2brain Rec virtual microphone and speaker installed.
- Meeting target uses:
  - input: `2brain Rec Microphone`
  - output: `2brain Rec Speaker`
- macOS system default physical input/output resolves to an accepted class:
  built-in, wired, or USB.
- Bluetooth/AirPods-class routes are not accepted for `019`.
- Backend, upload, MediaScribe, Langfuse, and network services may be offline;
  live passthrough must remain local.

## Baseline Commands

```sh
cd apps/macos
swift test
```

```sh
apps/macos/Scripts/validate-live-passthrough-foundation.sh
apps/macos/Scripts/validate-live-route-readiness.sh
apps/macos/Scripts/validate-recording-artifact-format.sh
```

Expected outcome:

- Swift tests pass.
- Existing short-smoke/foundation gates remain green.
- No diagnostic redaction failures.

## Development Gate: 30-Minute Long Run

For each accepted meeting target:

- Chrome
- Opera
- Zoom
- Telemost

Run a controlled 30-minute meeting with:

- `2brain Rec Microphone` selected in the target;
- `2brain Rec Speaker` selected in the target;
- no `Run Check`;
- no app relaunch;
- no meeting settings reopen;
- no manual meeting-target device reselect;
- recording active for artifact continuity where the run is intended to count
  as recording acceptance.

Expected evidence:

- `ValidationRunEvidence.durationGate == development_30_minute`
- `result == accepted`
- `unexpectedReleaseCount == 0`
- `userActionsRequired == []`
- all route evidence families present;
- if recording active, `durationDifferenceSeconds <= 3`.

## Release Gate: 75-Minute Long Run

Repeat release validation for Chrome, Opera, Zoom, and Telemost with a
75-minute window matching the 2026-06-04 incident length.

Expected evidence:

- `ValidationRunEvidence.durationGate == release_75_minute`
- each target has accepted evidence;
- built-in, wired, and USB classes each have accepted long-duration evidence;
- untested target/device-class combinations are explicitly listed as
  `not_tested`;
- Bluetooth/AirPods-class routes are listed as backlog/not accepted.

## Autorepair Scenarios

During controlled meetings where the target still uses 2brain Rec virtual
devices, induce:

- `coreaudiod` restart or HAL reload;
- sleep/wake;
- temporary physical device disappearance then return;
- macOS default input/output route change to accepted built-in/wired/USB;
- browser or meeting app stream recreation;
- app-side route engine restart.

Expected evidence:

- supported normal disruptions recover within `<= 10 seconds`;
- OS/device-heavy disruptions recover within `<= 30 seconds` after the required
  OS/device condition is available again;
- successful repair has `userActionRequired == false`;
- route reports healthy only after fresh evidence;
- non-recoverable states are blocked without infinite retry.

## Non-Recoverable Scenarios

Induce or simulate:

- microphone permission revoked;
- no accepted physical input/output available;
- meeting target changed away from 2brain Rec virtual devices;
- macOS default route resolves to Bluetooth/AirPods-class;
- OS or meeting target refuses to reopen the stream.

Expected evidence:

- result is `blocked`, `failed`, or `not_accepted`, not clean accepted;
- no infinite repair loop;
- no false healthy state;
- detailed metadata-only blocked reason.

## Recording Timeline Validation

For accepted recording runs:

- stop the recording normally;
- inspect `manifest.json`;
- inspect route timeline evidence.

Expected:

- both `mic.wav` and `incoming.wav` exist;
- `durationDifferenceSeconds <= 3`;
- `alignmentBand == accepted`;
- route evidence links any interruption to a precise category.

Failure bands:

- `> 3` and `<= 10` seconds: degraded/warning, not clean acceptance;
- `> 10` seconds: feature failure;
- tens/minutes difference: route-stability bug.

## Redaction Validation

Scan route diagnostics, validation evidence, and manifest evidence.

Expected absent:

- raw audio;
- transcript text;
- meeting content;
- credentials;
- tokens;
- signed URLs;
- passwords;
- live credential paths.

## Acceptance Summary

The feature is accepted only when release evidence shows:

- Chrome accepted;
- Opera accepted;
- Zoom accepted;
- Telemost accepted;
- built-in device class accepted;
- wired device class accepted;
- USB device class accepted;
- no accepted run required `Run Check`;
- no accepted run had unexpected route release;
- recording timeline accepted where recording was active;
- all untested combinations are explicitly listed.

## Evidence Paths

- `specs/019-live-route-stability/evidence/test-results.md`
- `specs/019-live-route-stability/evidence/development-30-minute.md`
- `specs/019-live-route-stability/evidence/release-75-minute.md`
- `specs/019-live-route-stability/evidence/local-offline.md`
- `specs/019-live-route-stability/evidence/scope-review.md`
- `specs/019-live-route-stability/evidence/acceptance-matrix.md`
