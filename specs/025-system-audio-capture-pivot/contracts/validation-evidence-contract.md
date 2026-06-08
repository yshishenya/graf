# Contract: Validation Evidence

## Purpose

Define the metadata-only evidence required before system-audio-first recording
can be accepted.

## Evidence Files

Recommended evidence directory:

```text
specs/025-system-audio-capture-pivot/evidence/
├── test-results.md
├── cpu-gates.md
├── no-hal-probe.md
├── development-30-minute.md
├── release-75-minute.md
├── permission-matrix.md
└── artifact-matrix.md
```

## CPU Gate Evidence

Each run must record:

- run ID;
- date/time;
- app version/commit;
- macOS version and Apple Silicon model;
- recording phase: `idle`, `activeRecording`, `stop`, `quit`;
- `coreaudiod` CPU samples;
- app CPU samples;
- helper CPU samples;
- memory samples;
- gate verdict: `passed`, `degraded`, `failed`, `blocked`;
- failure reason when not passed.

Passing criteria:

- idle after 10 seconds: `coreaudiod < 5%`, app `< 5%`;
- active recording: no sustained `coreaudiod > 10%`;
- active recording: no sustained app/helper total `> 25%`;
- stop/quit returns below idle gate within 10 seconds.

For this feature, `sustained` means at least three consecutive samples above
the threshold at 2-second sampling intervals after the relevant settle window.

## No-HAL Evidence

Each run must record:

- HAL driver installed/absent state;
- whether any HAL runtime probe script or binary was executed;
- whether MVP recording used virtual devices;
- whether driver repair/update/restart was required;
- verdict.

Passing criteria:

- no HAL runtime probe required;
- no virtual device selection required;
- recording works with HAL driver absent or ignored.

## Permission Evidence

Matrix rows:

- microphone granted + system audio granted;
- microphone denied + system audio granted;
- microphone granted + system audio denied;
- both denied;
- permission revoked while recording.

Each row records:

- visible blocker/degraded copy;
- recovery action;
- artifact outcome;
- manifest reason.

## Duration Evidence

Required gates:

- 30-minute development validation;
- 75-minute manual release validation.

Each gate records:

- meeting target/scope;
- device class;
- `mic.wav` and `incoming.wav` durations;
- `durationDifferenceSeconds`;
- CPU gate result;
- app/meeting responsiveness result;
- stop/quit release result;
- final verdict.

Blocked, failed, degraded, or not-tested rows must not be counted as accepted.
