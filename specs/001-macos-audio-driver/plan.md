# Implementation Plan: macOS Virtual Audio Driver MVP

**Branch**: `001-macos-audio-driver` | **Date**: 2026-05-27 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/001-macos-audio-driver/spec.md`

## Summary

Deliver the first macOS capture layer for 2brain Rec: two virtual audio devices,
`2brain Rec Microphone` and `2brain Rec Speaker`, with route verification,
separate local/remote audio tracks, live passthrough independent of backend
availability, visible capture control, Audio Health diagnostics, and an
interactive signed/notarized installer. The driver/audio component remains thin;
desktop software owns local encrypted buffering, upload coordination hooks,
retention/purge state, visible UX state, diagnostics packaging, and audit hooks.

The technical approach is a macOS desktop app plus a Core Audio virtual audio
component packaged through an interactive signed/notarized installer. Phase 0
must prove the selected virtual-device technology on Apple Silicon before
implementation tasks begin.

## Technical Context

**Language/Version**: Swift 6 for macOS app, helper tools, and UI; C/C++ for the
real-time Core Audio virtual audio component where required by Apple APIs; shell
only for installer/notarization automation.

**Primary Dependencies**: macOS Core Audio/Audio Hardware APIs, Core Audio
AudioServerPlugIn-compatible virtual device implementation path, Apple Developer
ID signing, Apple notarization, macOS System Settings audio routing, local
desktop IPC between app/helper/audio component, encrypted local file storage
owned by the desktop app. AudioDriverKit remains a researched alternative if the
Phase 0 spike proves it is a better Apple-supported route for this exact virtual
device shape.

**Storage**: Local encrypted desktop-owned capture buffer and metadata store for
capture state, route verification, track timing, dropout markers, retention
deadlines, purge state, and diagnostics manifests. No server persistence,
MediaScribe upload, MinIO, Postgres, or Temporal implementation belongs to this
feature.

**Testing**: XCTest/unit tests for app-domain logic; driver/component integration
tests for virtual device publication, routing, passthrough, and continuity
signals; synthetic audio route tests for mic and speaker paths; real browser
meeting QA in Chrome, Opera, Yandex Browser, and Yandex Telemost-in-browser;
manual installer/notarization, repair, rollback, and uninstall acceptance runs.

**Target Platform**: macOS on Apple Silicon, minimum macOS 14.5, plus latest
stable macOS at release-candidate time. Intel Macs are unsupported for MVP.

**Project Type**: Desktop app plus macOS virtual audio layer, installer package,
and QA harness.

**Performance Goals**: Two tracks aligned within 100 ms over 60 minutes; dropped
frames below 0.1% for supported wired audio; dropped frames below 0.5% for
supported Bluetooth and AirPods-class devices; 5-minute network/server outage
does not interrupt passthrough; route verification blocks `ready` until both
paths pass synthetic checks and at least one approved browser validation path.

**Constraints**: No no-driver fallback; no invisible/silent recording; one-action
local stop during active capture; virtual speaker audio must never loop into
virtual microphone; driver/audio component owns only real-time audio behavior,
routing, mirroring, timing, and continuity signals; desktop app never stores
MediaScribe credentials and never sends audio directly to MediaScribe; diagnostics
must exclude raw audio, transcript text, credentials, tokens, and signed URLs by
default.

**Scale/Scope**: Internal MVP for the owner/team, 1-10 pilot users, approved
browser meeting targets, built-in/wired/USB/Bluetooth/AirPods-class physical
device matrix, interactive installer only. Silent install, MDM, enterprise
deployment, Windows, live transcription, backend upload protocol, and full
assisted auto-start detection are out of scope.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### 2brain Rec Constitutional Gates

- **Driver-first capture integrity**: PASS. The feature is explicitly driver
  first, exposes two virtual devices, requires separate mic/speaker tracks,
  prevents loopback, preserves passthrough during backend/network failure, and
  includes measurable latency/dropout/alignment gates.
- **Visible consent and control**: PASS. The spec requires persistent visible
  capture indication, one-action stop, manual start/pause/resume/stop, and only
  readiness/hooks for later assisted auto-start.
- **Data boundary and secrets**: PASS. Desktop-side work is local only; no
  MediaScribe direct upload or credentials are introduced. Diagnostics redact
  secrets, signed URLs, raw audio, and transcript text by default.
- **Deletion truth and lifecycle accounting**: PASS. Local buffer entities carry
  retention deadlines, purge state, and desktop acknowledgement hooks. Server
  deletion is not promised by this driver feature.
- **Spec-driven delivery**: PASS. Specify and clarify are complete; this plan
  creates research, data model, contracts, and quickstart artifacts. Checklist,
  tasks, analyze, and implement remain next gates.
- **Brand-distance and accessibility**: PASS. The spec requires original 2brain
  Rec UI, accessible state labels, non-color cues, keyboard-reachable stop, and
  localization-safe labels for onboarding, tray/widget, Audio Health, and
  capture state.
- **Operational readiness**: N/A for Docker/server deployment in this feature.
  Local disk-full, buffering, installer rollback, log redaction, and failure
  states are covered.

**Initial Gate Result**: PASS. No constitution conflict blocks Phase 0 research.

**Post-Design Gate Result**: PASS. Design artifacts preserve the thin-driver
boundary, visible-control requirements, local artifact lifecycle, diagnostic
redaction, and installer/QA gates. Implementation must not begin until the
virtual-device Phase 0 spike confirms the selected Core Audio approach can
publish both MVP devices and sustain passthrough on supported macOS versions.
The scaffold build is not sufficient evidence; the proof gate requires a
recorded Apple Silicon runtime result in
`apps/macos/AudioDriver/RuntimeProofReport.md` before any US1 task that
publishes real virtual devices or installer behavior.

**Phase 0 Runtime Gate Result**: PASS. `RuntimeProofReport.md` records
`**Status**: ACCEPTED`; the local Core Audio proof bundle publishes
`2brain Rec Microphone` and `2brain Rec Speaker` on Apple Silicon macOS.
This unlocks US1 route-verification work. It does not prove production routing,
passthrough, capture, signing, notarization, or installer UX.

## Project Structure

### Documentation (this feature)

```text
specs/001-macos-audio-driver/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── desktop-driver-contract.md
│   ├── diagnostics-redaction-contract.md
│   └── qa-acceptance-contract.md
└── tasks.md
```

### Source Code (repository root)

```text
apps/macos/
├── RecApp/
│   ├── Sources/
│   ├── Resources/
│   └── Tests/
├── AudioDriver/
│   ├── Sources/
│   ├── Resources/
│   └── Tests/
├── Shared/
│   ├── Sources/
│   └── Tests/
└── Installer/
    ├── Packages/
    ├── Scripts/
    └── Tests/

tests/macos/
├── route-synthetic/
├── browser-meetings/
├── physical-devices/
└── installer-recovery/

qa/macos/
├── device-matrix.md
├── browser-targets.md
└── release-candidate-checklist.md
```

**Structure Decision**: Create a macOS-first workspace under `apps/macos/`.
`RecApp` owns visible UX, policy state, local buffer policy, diagnostics
packaging, and upload/readiness hooks. `AudioDriver` owns the virtual audio
component and real-time routing/mirroring/timing signals. `Shared` holds common
value types and contracts used by app, helper, and tests. `Installer` owns the
interactive signed/notarized package and repair/rollback/uninstall scripts.
`tests/macos/` and `qa/macos/` hold validation harnesses and manual matrices
that are not app source.

## Complexity Tracking

No constitution violations are accepted in this plan.
