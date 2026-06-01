# Implementation Plan: macOS Real Bidirectional Passthrough

**Branch**: `004-real-bidirectional-passthrough` | **Date**: 2026-05-31 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/004-real-bidirectional-passthrough/spec.md`

## Summary

Implement real non-recording macOS bidirectional passthrough on top of the
accepted 003 route-readiness layer. The selected physical microphone must feed
`2brain Rec Microphone`; audio sent by meeting apps to `2brain Rec Speaker`
must play through the selected physical output; browser calls must remain usable
through both virtual devices; and private app I/O fail-closed behavior must
remain intact.

The technical approach keeps the HAL AudioServerPlugIn as the meeting-facing
virtual device boundary and the Swift desktop app as the physical-device bridge,
route orchestrator, visible state surface, and diagnostics owner. Shared memory
remains the local realtime handoff between driver and app. This feature does not
start recording, upload audio, call MediaScribe, write Langfuse traces, or add
new network egress.

### Stabilization Review Update - 2026-06-01

The first live-passthrough spike exposed system-level instability: `coreaudiod`
CPU spikes, audio distortion, intermittent silence, and hangs in audio clients
such as Zoom, Yandex Telemost, and System Settings. The feature remains in SDD
implementation, but live route acceptance is paused until the following
refactor gates pass:

- separate UI lifecycle from route-engine ownership;
- separate publication proof from live-route proof;
- make AudioUnit callbacks realtime-safe;
- formalize and test the shared-memory ring-buffer contract;
- restore truthful readiness based on measured route evidence;
- add automatic non-recording app-route startup, `coreaudiod` CPU/no-hang, and
  RT-safety checks to the validation pipeline.

Startup safe-mode behavior is allowed only as a stabilization measure: the
driver may publish devices for Core Audio enumeration while the app-side
non-recording bridge starts automatically and virtual devices still report
`running=0` until a client opens them. This startup state is not recording,
transcription, upload, or hidden capture, and does not replace browser/physical
evidence tasks.

## Technical Context

**Language/Version**: Swift 6 for macOS app, Audio Unit bridge, route
orchestration, UI, and tests; C/C++17 for the Core Audio HAL AudioServerPlugIn,
shared ring buffer, and runtime proof tools; shell for installer and validation
harnesses.

**Primary Dependencies**: macOS Core Audio, AudioToolbox HAL Output Audio Unit,
AudioServerPlugIn-compatible HAL bundle, SwiftUI, Swift Package Manager,
pkgbuild/productbuild, POSIX shared memory.

**Storage**: Local app-managed passthrough evidence and diagnostics only. No
MediaScribe, MinIO, Postgres, Temporal, Langfuse, Docker storage, server upload,
or meeting-content persistence is added.

**Testing**: Swift unit tests for route state, ring-buffer policy, diagnostics,
and fail-closed behavior; C++ proof/runtime tools; synthetic passthrough harness;
local installer/runtime probe; static realtime-safety checks; automatic
non-recording startup checks; `coreaudiod` CPU/no-hang checks; browser meeting matrix
evidence; manual physical device checks where macOS hardware observation is
required.

**Target Platform**: macOS 14.5+ on Apple Silicon. Built-in and wired
microphone/output routes are release-quality targets. Bluetooth and
AirPods-class routes remain managed pilot routes unless separately proven.

**Project Type**: macOS desktop app plus HAL virtual audio component, local
installer scripts, shared route models, and QA harnesses.

**Performance Goals**:

- built-in/wired live passthrough adds no more than 30 ms of 2brain Rec route
  latency when marked ready;
- remote-to-mic leakage stays at least 45 dB below speaker reference and is not
  intelligible when marked ready;
- app/route-engine loss hides or removes public virtual devices within 5
  seconds;
- physical device, browser target, app heartbeat, or `coreaudiod` change marks
  the route stale within 5 seconds;
- a 5-minute backend/network outage does not interrupt live passthrough.

**Constraints**:

- no no-driver fallback;
- no hidden recording, hidden capture, transcript generation, or assisted
  auto-start of capture in this slice;
- app launch may automatically start only the local non-recording passthrough
  route so meetings work without a manual `Run Check`;
- no direct desktop-to-MediaScribe upload and no new external network egress;
- diagnostics and evidence are metadata-only by default;
- public devices keep the 003 private app I/O fail-closed behavior;
- browser targets can be blocked/not accepted only with explicit evidence.

**Scale/Scope**: Internal macOS pilot on Apple Silicon. Browser targets are
Chrome, Opera, Yandex Browser, and Yandex Telemost-in-browser. Server upload,
recording, transcription, local buffering, deletion, Windows/Linux/mobile,
production notarization, and MDM/silent install are out of scope unless a later
feature supersedes this slice.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### 2brain Rec Constitutional Gates

- **Driver-first capture integrity**: PASS. The feature is driver-first, owns
  macOS virtual audio routing, keeps separate mic/speaker directions, preserves
  private app I/O fail-closed behavior, and defines measurable latency/leakage
  gates.
- **Visible consent and control**: PASS. Live passthrough is visible and
  non-recording. The feature does not start capture, transcription, upload, or
  hidden recording, and must preserve existing one-action stop surfaces if
  touched.
- **Data boundary and secrets**: PASS. The feature is local route plumbing only.
  It adds no MediaScribe, Langfuse, LLM, analytics, server upload, credentials,
  or new network egress.
- **Deletion truth and lifecycle accounting**: PASS. Evidence is local metadata;
  temporary development stimulus must be explicit, local, release-disabled by
  default, and absent from default diagnostics.
- **Spec-driven delivery**: PASS. Spec exists, clarify found no blocking
  ambiguity, and this plan creates research, data model, contracts, quickstart,
  checklists, tasks, and analyze gates before implementation.
- **Brand-distance and accessibility**: PASS. UI copy/state must remain original
  2brain Rec language with non-color-only states and localization-safe labels.
- **Operational readiness**: N/A. No Docker/server/deployment/storage changes.

**Initial Gate Result**: PASS. No constitution rule blocks planning.
**Post-Design Gate Result**: PASS. Design artifacts keep the driver-first,
visible, local-only, metadata-only, fail-closed, and no-secret boundaries.

## Project Structure

### Documentation (this feature)

```text
specs/004-real-bidirectional-passthrough/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── passthrough-contract.md
│   ├── browser-call-contract.md
│   └── diagnostics-contract.md
└── tasks.md
```

### Source Code (repository root)

```text
apps/macos/
├── AudioDriver/
│   ├── Sources/Plugin/TwoBrainRecProofDriver.cpp
│   ├── Sources/Bridge/SharedAudioBuffer.hpp
│   ├── Sources/Bridge/AudioBridge.cpp
│   └── Sources/Proof/RuntimeDeviceProbe.cpp
├── RecApp/
│   ├── App/TwoBrainRecApp.swift
│   └── Sources/
│       ├── AudioSetup/
│       ├── AudioHealth/
│       ├── Capture/PassthroughBridge.swift
│       └── Diagnostics/
├── Shared/
│   ├── Sources/
│   │   ├── Models/
│   │   ├── Routing/
│   │   └── SharedAudioMemory.swift
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

**Structure Decision**: Continue the macOS-native structure from 002/003.
Driver code owns meeting-facing virtual device publication, ring-buffer
handoff, and fail-closed public device state. RecApp owns physical-device
capture/playback, visible route state, recovery actions, and diagnostics. Shared
owns policy models and metadata contracts. Tests/QA own synthetic, physical, and
browser evidence.

## Complexity Tracking

No constitution violations are accepted in this plan.
