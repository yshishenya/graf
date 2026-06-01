# Implementation Plan: Low-Resource Reliable macOS Audio

**Branch**: `006-low-resource-audio` | **Date**: 2026-06-01 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/006-low-resource-audio/spec.md`

## Summary

Refactor the accepted non-recording macOS passthrough path into a lower-resource
route lifecycle without sacrificing call reliability. The virtual microphone and
speaker remain always published and fail-closed. Heavy physical Core Audio
routing starts only when explicit virtual-device client IO requires it, never
because of a manual readiness button, and never because recording/transcription
is active. Recording and transcription remain future application-layer triggers,
not HAL driver responsibilities.

The technical approach is to preserve the useful existing driver/app split while
hardening the risky boundary: make HAL callbacks realtime-safe, keep route truth
as separate evidence planes, isolate/bound physical Core Audio setup to 3
seconds, reject self/chained virtual devices as physical working devices, and
retain a fallback switch to the accepted `005-macos-passthrough-release-hardening`
app-launch lifecycle until all P1 gates pass.

## Technical Context

**Language/Version**: Swift 6 for macOS app, route engine, shared models, tests,
diagnostics, and validation helpers; C/C++17 for HAL driver and proof/runtime
tools; shell for local installer, CPU/no-hang, and validation harnesses;
Markdown/JSON for contracts and evidence artifacts.

**Primary Dependencies**: macOS Core Audio, AudioToolbox HAL Output Audio Unit,
AudioServerPlugIn HAL bundle, SwiftUI, Swift Package Manager, POSIX shared
memory, `pkgbuild`/`productbuild`, `ps`/`pgrep`/`open`/`osascript`, local
browser/meeting app surfaces, and existing `apps/macos` validation scripts.

**Storage**: Local metadata-only diagnostics and validation evidence. No raw
audio, meeting recording, transcript text, upload payload, MediaScribe,
Langfuse, MinIO, Postgres, Temporal, Docker, or server storage is added by this
slice.

**Testing**: Swift unit tests; C++ proof tools; runtime probe; HAL IO probe;
static realtime-safety scan; route lifecycle contract tests; no-hang/CPU
harness; installed-app smoke checks; diagnostics redaction scan; self-routing
and virtual-device-chain rejection tests.

**Target Platform**: macOS 14.5+ on Apple Silicon with local package installed
in `/Applications`; built-in or wired physical input/output are the
release-quality working-device targets.

**Project Type**: macOS desktop app plus native HAL virtual audio driver,
shared route models, local installer scripts, and local validation harnesses.

**Performance Goals**:

- physical route startup returns `ready`, `blocked`, `failed`, or `fallback`
  within 3 seconds;
- macOS Sound settings, Chrome, Opera, Zoom, and Telemost audio surfaces open
  within 5 seconds or record a blocked failure without hanging;
- `coreaudiod` idle/no-call CPU does not sustain above 10% for more than 30
  consecutive seconds;
- route stale/degraded/blocked state is reflected within 5 seconds after
  `coreaudiod` restart, sleep/wake, or physical device change;
- silent-but-open client streams remain active until explicit Core Audio IO state
  closes, not until energy drops.

**Constraints**:

- no recording, transcription, upload, MediaScribe, Langfuse, analytics, or
  external network egress;
- no no-driver fallback;
- no surprise hiding/removing public virtual devices as the MVP default;
- no heavy physical passthrough work sustained without an active client stream;
- no UI/main-path unbounded Core Audio setup, enumeration, or AudioUnit binding;
- no file IO, logging, allocation, lock waits, blocking IPC, wall-clock calls,
  process launches, network calls, or UI dependencies in HAL IO callbacks;
- diagnostics and evidence are metadata-only and must not include raw audio,
  transcripts, meeting content, credentials, tokens, signed URLs, or passwords.

**Scale/Scope**: Internal macOS pilot route-lifecycle refactor for 2brain Rec.
Primary validation surfaces are built-in/wired physical devices, macOS Sound
settings, Chrome, Opera, Zoom, and Yandex Telemost. Yandex Browser remains
outside acceptance unless explicitly added later.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### 2brain Rec Constitutional Gates

- **Driver-first capture integrity**: PASS. The feature keeps the macOS HAL
  virtual audio layer as the MVP route boundary, preserves separate virtual mic
  and speaker paths, no-loopback gates, fail-closed behavior, route recovery,
  and measurable latency/no-hang/CPU criteria.
- **Visible consent and control**: PASS. The feature does not start recording or
  transcription. It improves truthful route status while preserving future
  visible capture requirements for a later recording feature.
- **Data boundary and secrets**: PASS. The slice is local-only and metadata-only.
  It adds no MediaScribe, Langfuse, upload, external egress, credentials, or
  server-side processing.
- **Deletion truth and lifecycle accounting**: PASS. No meeting-content artifact
  is created. Validation evidence is metadata-only and does not create retention
  or deletion obligations for raw audio or transcripts.
- **Spec-driven delivery**: PASS. Specification, clarification, and requirement
  checklist are complete; this plan creates the Phase 0/1 artifacts. Checklist,
  tasks, analyze, and implement remain required before code changes.
- **Brand-distance and accessibility**: PASS. Any readiness/status UI changes
  must use original 2brain Rec language, keyboard reachable states, non-color-only
  status, and localization-safe copy.
- **Operational readiness**: N/A for Docker/server storage. PASS for local
  installer/runtime/no-hang/recovery/diagnostics gates.

**Initial Gate Result**: PASS. No constitution violation. Recording/transcription
remain out of scope, and route optimization is guarded by explicit fallback.

**Post-Design Gate Result**: PASS. Phase 1 artifacts preserve driver-first,
local-only, metadata-only, visible-state, no-loopback, and no-secret constraints.
No server/storage/deletion scope is introduced.

## Project Structure

### Documentation (this feature)

```text
specs/006-low-resource-audio/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── checklists/
│   └── requirements.md
├── contracts/
│   ├── route-lifecycle-contract.md
│   ├── driver-app-handoff-contract.md
│   └── low-resource-validation-contract.md
└── tasks.md              # created by /speckit-tasks, not by /speckit-plan
```

### Source Code (repository root)

```text
apps/macos/
├── RecApp/
│   ├── App/TwoBrainRecApp.swift
│   └── Sources/
│       ├── AudioSetup/
│       ├── Capture/
│       └── Diagnostics/
├── AudioDriver/
│   ├── Makefile
│   └── Sources/
│       ├── Bridge/
│       ├── Device/
│       ├── Plugin/
│       └── Proof/
├── Shared/
│   ├── Sources/
│   │   ├── Diagnostics/
│   │   ├── Models/
│   │   └── Routing/
│   └── Tests/
└── Scripts/

tests/macos/
├── browser-meetings/
├── contract/
├── installer-recovery/
├── physical-devices/
├── route-synthetic/
└── static/

qa/macos/
├── browser-targets.md
├── device-matrix.md
└── release-candidate-checklist.md
```

**Structure Decision**: Extend the existing macOS app/driver/shared model
structure. Keep the HAL driver focused on virtual device publication,
realtime-safe IO, explicit client IO state, shared-buffer handoff, and
fail-closed behavior. Keep physical device selection, bounded route startup,
Core Audio recovery, diagnostics, and future recording triggers in the app/shared
layer. Do not introduce server services or storage components in this slice.

## Phase 0 Research Outcome

Research is consolidated in [research.md](research.md). All planning unknowns
are resolved for this slice:

- visible fail-closed virtual devices are the MVP default;
- shared memory plus app heartbeat and explicit client IO state is sufficient for
  this slice; no hidden app-IO virtual device is required before implementation;
- startup isolation and timeout handling are foundational refactor work;
- HAL IO callbacks must be audited and kept realtime-safe;
- active client streams are detected from Core Audio IO state, never sample
  energy;
- KRISP is used only as behavior-level clean-room research, not implementation
  source material.

## Phase 1 Design Outcome

Design artifacts produced by this plan:

- [data-model.md](data-model.md): route state, evidence, health, validation, and
  fallback entities;
- [contracts/route-lifecycle-contract.md](contracts/route-lifecycle-contract.md):
  state machine, triggers, transitions, and readiness planes;
- [contracts/driver-app-handoff-contract.md](contracts/driver-app-handoff-contract.md):
  realtime-safe HAL/app shared-memory handoff and fail-closed rules;
- [contracts/low-resource-validation-contract.md](contracts/low-resource-validation-contract.md):
  metadata-only validation evidence and pass/fail thresholds;
- [quickstart.md](quickstart.md): local validation sequence before and after
  implementation.

## Complexity Tracking

No constitution violations or complexity exceptions.
