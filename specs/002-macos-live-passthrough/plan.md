# Implementation Plan: macOS Live Audio Passthrough

**Branch**: `002-macos-live-passthrough` | **Date**: 2026-05-31 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/002-macos-live-passthrough/spec.md`

## Summary

Turn the accepted macOS publication proof into the safe foundation for a
call-usable audio route. This feature establishes private app I/O,
fail-closed public devices, readiness-blocking UI, diagnostics, route/track
evidence models, lifecycle gates, and synthetic validation. It must not claim
release-ready browser-call passthrough until the next feature proves real
microphone and speaker audio movement end to end.

The technical approach keeps the HAL component thin and real-time safe while the
desktop app owns user-visible readiness, physical-device selection, permission
prompts, diagnostics, and capture state. The existing proof driver remains the
publication baseline, but it must not claim readiness or steal system defaults
until live passthrough is accepted.

Clean-room Krisp observations shape the audio-route design: public
meeting-facing virtual devices, private app I/O between driver and desktop audio
engine, speaker audio as an AEC/reference stream, fail-closed public-device
availability when app I/O is gone, and stream-health checks that distinguish
ordinary user silence from missing valid audio frames.

## Technical Context

**Language/Version**: Swift 6 for macOS app, Audio Unit bridge, UI, state, and
tests; C/C++17 for the Core Audio HAL AudioServerPlugIn and proof/runtime tools;
shell for local installer and validation commands.

**Primary Dependencies**: macOS Core Audio, AudioToolbox/HAL Output Audio Unit,
AudioServerPlugIn-compatible HAL bundle, SwiftUI, Swift Package Manager,
pkgbuild/productbuild, local POSIX shared memory for driver/app audio buffers.

**Storage**: Local app-managed readiness/capture metadata and diagnostics only.
No server upload, MediaScribe, MinIO, Postgres, Temporal, Langfuse, or Docker
storage is implemented by this feature.

**Testing**: Swift unit tests for route state and safety models, C++ proof builds
for the HAL bundle, runtime Core Audio probes, synthetic route harnesses, manual
browser meeting validation, long-run audio QA, and installer/restart checks.

**Target Platform**: macOS 14.5+ on Apple Silicon. Intel remains unsupported for
this MVP slice unless a later decision changes support scope.

**Project Type**: macOS desktop app plus HAL virtual audio component, local
installer scripts, and QA harnesses.

**Performance Goals**:

- readiness invalidates within 5 seconds after route/device change;
- built-in/wired pilot calls keep local/remote alignment within 100 ms over 30
  minutes;
- supported built-in/wired routes keep added 2brain Rec route latency at or
  below 30 ms;
- supported built-in/wired routes keep remote speaker leakage in the virtual
  microphone at least 45 dB below the speaker reference and not intelligible;
- expected streams fail hard when they are not capturable or have no valid
  frames for one 3-second health interval;
- ordinary user silence with valid input frames does not mark capture degraded;
- built-in/wired dropped-frame rate stays below 0.1%;
- Bluetooth/AirPods-class dropped-frame rate stays below 0.5%;
- Bluetooth/AirPods-class pilot calls record profile stability, bidirectional
  valid-frame evidence for every 3-second health interval, one-sided-audio
  events, and measured latency evidence for the full 30-minute pilot;
- 5-minute backend/network outage does not interrupt live audio passthrough;
- readiness check must never show ready from device visibility alone.

**Constraints**:

- no no-driver fallback;
- no invisible recording or hidden capture during readiness checks;
- virtual speaker audio must never enter the virtual microphone path above the
  accepted non-intelligible leakage threshold;
- public virtual devices must fail closed when private app I/O or the desktop
  audio engine is unavailable;
- the app must keep one-action stop visible for active capture;
- diagnostics must exclude raw audio, transcript text, credentials, tokens, and
  signed URLs by default;
- desktop must not send audio directly to MediaScribe or store MediaScribe
  credentials.

**Scale/Scope**: Internal macOS pilot for owner/team, approved browsers Chrome,
Opera, Yandex Browser, and Yandex Telemost-in-browser, built-in/wired/USB/
Bluetooth/AirPods-class physical-device matrix. Backend upload, transcription,
Windows/Linux/mobile clients, MDM/silent install, and assisted auto-start are out
of scope.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### 2brain Rec Constitutional Gates

- **Driver-first capture integrity**: PASS. This feature exists specifically to
  move beyond publication proof into real driver-backed passthrough, separate
  track evidence, no loopback, and degraded states.
- **Visible consent and control**: PASS. Readiness checks are user-triggered and
  must not start hidden recording. Active capture keeps visible local indication
  and one-action stop.
- **Data boundary and secrets**: PASS. The feature is local macOS audio only. It
  adds no MediaScribe upload, Langfuse tracing, LLM calls, analytics, credentials,
  or new network egress.
- **Deletion truth and lifecycle accounting**: PASS. Any local route/capture
  evidence must be app-managed metadata and eligible for existing local deletion
  reporting; no server deletion promise is added.
- **Spec-driven delivery**: PASS with process note. The spec exists and this plan
  creates research, data model, contracts, and quickstart. Tasks/analyze must
  run before broader implementation. A small bridge hardening commit already
  landed to prevent false success and unsafe AudioUnit buffer behavior.
- **Brand-distance and accessibility**: PASS. UI changes must keep original
  2brain Rec copy, non-color-only states, keyboard reachable controls, and
  localization-safe labels.
- **Operational readiness**: N/A for Docker/server deployment. Local installer,
  diagnostics, device-change, and disk/buffer degraded behavior remain covered.

**Initial Gate Result**: PASS. No constitution rule blocks planning.

**Post-Design Gate Result**: PASS. The design keeps the driver-first model,
visible readiness, no hidden recording, local-only data boundaries, and truthful
diagnostics. Implementation must not mark ready until both live paths are proven.

## Project Structure

### Documentation (this feature)

```text
specs/002-macos-live-passthrough/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── readiness-contract.md
│   ├── audio-route-contract.md
│   └── diagnostics-contract.md
└── tasks.md
```

### Source Code (repository root)

```text
apps/macos/
├── AudioDriver/
│   ├── Sources/Plugin/TwoBrainRecProofDriver.cpp
│   ├── Sources/Bridge/
│   ├── Sources/Routing/
│   ├── Sources/Timing/
│   └── RuntimeProofReport.md
├── RecApp/
│   ├── App/TwoBrainRecApp.swift
│   └── Sources/
│       ├── AudioSetup/
│       ├── AudioHealth/
│       ├── Capture/
│       └── Diagnostics/
├── Shared/
│   ├── Sources/
│   └── Tests/
└── Installer/
    └── Scripts/

tests/macos/
├── route-synthetic/
├── browser-meetings/
├── physical-devices/
└── installer-recovery/

qa/macos/
├── browser-targets.md
├── device-matrix.md
└── release-candidate-checklist.md
```

**Structure Decision**: Continue the macOS-native workspace established by
`001-macos-audio-driver`. `AudioDriver` owns real-time virtual-device behavior
and shared memory IO; `RecApp` owns user-visible readiness, selected device
state, safe probes, capture status, and logs; `Shared` owns common models and
testable state transitions; `tests/macos` and `qa/macos` own validation evidence.

## Complexity Tracking

No constitution violations are accepted in this plan.
