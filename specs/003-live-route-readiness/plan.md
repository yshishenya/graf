# Implementation Plan: macOS Live Route Readiness

**Branch**: `003-live-route-readiness` | **Date**: 2026-05-31 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/003-live-route-readiness/spec.md`

## Summary

Implement real macOS bidirectional route readiness on top of the 002 foundation.
The app must prove physical microphone movement into `2brain Rec Microphone`,
prove `2brain Rec Speaker` movement into the selected physical output, keep
publication-only routes blocked, preserve private app I/O fail-closed behavior,
and record browser/latency/leakage evidence before release readiness.

The technical approach keeps the HAL driver as the real-time audio surface and
the desktop app as the user-visible readiness orchestrator. Readiness uses local
audio stimulus, stable app heartbeat/shared-memory evidence, stream-health
evidence, and browser QA
artifacts. It must never start recording or send audio to external services.

## Technical Context

**Language/Version**: Swift 6 for macOS app, route orchestration, Audio Unit
bridge, UI, and tests; C/C++17 for the Core Audio HAL AudioServerPlugIn,
stable shared-memory heartbeat bridge, and runtime proof tools; shell for installer and
validation harnesses.

**Primary Dependencies**: macOS Core Audio, AudioToolbox/HAL Output Audio Unit,
AudioServerPlugIn-compatible HAL bundle, SwiftUI, Swift Package Manager,
pkgbuild/productbuild, local POSIX shared memory.

**Storage**: Local app-managed readiness evidence and diagnostics only. No
MediaScribe, MinIO, Postgres, Temporal, Langfuse, or Docker storage is added.

**Testing**: Swift unit tests for route state and policies, C++ proof/runtime
tools, synthetic route harnesses, interactive runtime probe, browser meeting
matrix evidence, and installer/restart checks.

**Target Platform**: macOS 14.5+ on Apple Silicon. Built-in and wired devices are
strict release-readiness targets; Bluetooth/AirPods-class routes remain managed
pilot routes.

**Project Type**: macOS desktop app plus HAL virtual audio component, local
installer scripts, shared route models, and QA harnesses.

**Performance Goals**:

- app reaches ready only after microphone and speaker live route evidence pass;
- private app I/O loss hides or removes public devices within 5 seconds;
- readiness becomes stale within 5 seconds after relevant route/browser/device
  changes;
- built-in/wired added 2brain Rec latency stays at or below 30 ms when marked
  release-ready;
- built-in/wired remote-to-mic leakage stays at least 45 dB below speaker
  reference and is not intelligible when marked release-ready;
- backend/network outage for 5 minutes does not interrupt live call
  passthrough after readiness passes.

**Constraints**:

- no no-driver fallback;
- no hidden recording or hidden capture during readiness;
- no direct desktop-to-MediaScribe upload;
- no raw audio, transcript text, credentials, tokens, or signed URLs in
  diagnostics or committed evidence;
- public devices must keep the 002 fail-closed behavior;
- browser targets can be recorded as blocked/not accepted, but not silently
  treated as supported.

**Scale/Scope**: Internal macOS pilot on Apple Silicon. Browser targets are
Chrome, Opera, Yandex Browser, and Yandex Telemost-in-browser. Server upload,
transcription, storage, deletion, assisted auto-start, Windows/Linux/mobile, and
MDM/silent install remain out of scope.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### 2brain Rec Constitutional Gates

- **Driver-first capture integrity**: PASS. The feature remains driver-first,
  preserves public virtual devices, private app I/O, fail-closed behavior,
  no-loopback requirements, and measurable latency/leakage gates.
- **Visible consent and control**: PASS. Readiness is user-triggered, active
  route state is visible, and no recording starts during checks.
- **Data boundary and secrets**: PASS. The feature is local route readiness only
  and adds no external egress, MediaScribe, Langfuse, LLM, analytics, or client
  credentials.
- **Deletion truth and lifecycle accounting**: PASS. Evidence is local metadata;
  any temporary development audio stimulus must be explicit, local, excluded
  from diagnostics by default, and cleanable.
- **Spec-driven delivery**: PASS. Spec and checklist exist; this plan creates
  research, data model, contracts, and quickstart before tasks/analyze.
- **Brand-distance and accessibility**: PASS. UI copy must stay original to
  2brain Rec and include non-color-only states and localization-safe labels.
- **Operational readiness**: N/A. No Docker/server/deployment storage changes.

**Initial Gate Result**: PASS. No constitution rule blocks planning.
**Post-Design Gate Result**: PASS. Design artifacts keep the driver-first,
visible, local-only, fail-closed, and no-secret boundaries.

## Project Structure

### Documentation (this feature)

```text
specs/003-live-route-readiness/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── readiness-contract.md
│   ├── route-evidence-contract.md
│   └── browser-validation-contract.md
└── tasks.md
```

### Source Code (repository root)

```text
apps/macos/
├── AudioDriver/
│   ├── Sources/Plugin/TwoBrainRecProofDriver.cpp
│   ├── Sources/Bridge/SharedAudioBuffer.hpp
│   └── Sources/Proof/RuntimeDeviceProbe.cpp
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
├── release-candidate-checklist.md
├── driver-gate-approval.md
└── driver-lifecycle-checklist.md
```

**Structure Decision**: Continue the macOS-native structure from 002. Driver
code owns public device state and the stable app I/O heartbeat boundary; RecApp
owns readiness orchestration and UI; Shared owns policy models; tests/qa own
validation and evidence.

## Complexity Tracking

No constitution violations are accepted in this plan.
