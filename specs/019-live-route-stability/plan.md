# Implementation Plan: Live Route Stability

**Branch**: `019-live-route-stability` | **Date**: 2026-06-04 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/019-live-route-stability/spec.md`

## Summary

Keep the live macOS meeting route stable for real long meetings. The plan turns
the current short-smoke passthrough implementation into a long-running route
engine that preserves an active meeting route, follows macOS system default
physical input/output changes for accepted device classes, repairs supported
external disruptions automatically, and emits metadata-only evidence that
explains route lifecycle, autorepair, user actions, and recording timeline
truth.

The implementation must target the observed 2026-06-04 failure mode: the bridge
repeatedly stopped after about 300 seconds and restarted only after explicit
`Run Check`. The planned fix is not "run check more often"; it is to make active
client evidence authoritative, block self-inflicted idle release while the
meeting target still uses the virtual devices, and replace stale/recheck states
with automatic repair where the external condition is recoverable.

## Technical Context

**Language/Version**: Swift 5.x for the macOS app/shared package; C++17-style
Core Audio HAL plug-in code for the audio driver proof layer; shell scripts for
validation gates.

**Primary Dependencies**: Swift Foundation, CoreAudio, AudioToolbox,
Dispatch/GCD, existing `TwoBrainRecShared` package models, existing HAL proof
driver and shared-memory bridge.

**Storage**: Local filesystem only for recording packages, manifests, and
metadata-only diagnostics/evidence. No server database, MinIO, MediaScribe,
Langfuse, upload queue, or external egress in this feature.

**Testing**: SwiftPM/XCTest under `apps/macos`, existing validation shell
scripts under `apps/macos/Scripts`, new long-duration development/release
evidence scripts and metadata contract validation.

**Target Platform**: Apple Silicon macOS MVP, native Core Audio/HAL virtual
microphone and speaker path.

**Project Type**: macOS desktop app plus local virtual audio driver/layer.

**Performance Goals**:

- healthy active route has zero self-inflicted releases during accepted 30- and
  75-minute runs;
- normal recoverable disruptions recover within `<= 2 seconds`;
- OS/device-heavy recoverable disruptions recover within `<= 10 seconds` after
  required OS/device conditions are available again;
- accepted recording runs finish with `mic.wav` and `incoming.wav` duration
  difference `<= 3 seconds`;
- no Core Audio/HAL realtime callback gains file IO, logging, allocation, locks,
  network calls, process launch, UI work, or unbounded waits.

**Constraints**:

- meeting apps select `2brain Rec Microphone` and `2brain Rec Speaker`;
- 2brain Rec follows current macOS system default physical input/output and does
  not add a physical-device picker for `019`;
- accepted physical classes are built-in, wired, and USB only;
- Bluetooth/AirPods-class routes are backlog/not accepted for `019`;
- successful autorepair must be quiet for the meeting user and recorded as
  metadata-only evidence;
- `Run Check` remains diagnostic fallback, not clean acceptance recovery;
- no leakage/echo cleanup work from `020` is in scope.

**Scale/Scope**:

- meeting targets: Chrome, Opera, Zoom, Telemost;
- duration gates: 30-minute automated/development and 75-minute manual/release;
- device-class coverage: every accepted target plus every in-scope device class,
  but not the full `4 targets x 3 device classes` cross-product;
- validation evidence must label accepted, blocked, failed, degraded, and not
  tested outcomes.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Plan Response |
|-----------|--------|---------------|
| I. Driver-First Capture Integrity | PASS | Work stays in the macOS virtual audio route and shared recording manifest path. No no-driver fallback is introduced. Live passthrough and recording timeline truth are first-class gates. |
| II. Visible Consent And User Control | PASS | The feature does not start recording. When recording is active, existing visible indicator and one-action stop remain mandatory. Successful autorepair is passive and must not hide capture state. |
| III. Data Boundary And Secret Discipline | PASS | Evidence is metadata-only and local-first. No raw audio, transcript, meeting content, credentials, tokens, signed URLs, passwords, MediaScribe, Langfuse, analytics, or external egress. |
| IV. Deletion Truth And Lifecycle Accounting | PASS | The feature adds local metadata evidence tied to route sessions/recording packages. It does not add new content artifacts or deletion promises. |
| V. Spec-Driven Delivery With Testable Gates | PASS | Spec and checklist are complete. This plan creates research, data model, contracts, and quickstart. Tasks/analyze/implementation must follow. |

No constitution violations are required.

## Project Structure

### Documentation (this feature)

```text
specs/019-live-route-stability/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── route-evidence-events.md
│   ├── autorepair-state-machine.md
│   ├── recording-timeline-evidence.md
│   └── validation-run-evidence.md
├── checklists/
│   └── requirements.md
└── tasks.md
```

### Source Code (repository root)

```text
apps/macos/
├── Package.swift
├── RecApp/Sources/Capture/
│   ├── PassthroughRouteEngine.swift
│   ├── PassthroughBridge.swift
│   ├── LocalRecordingManifestService.swift
│   └── RecordingEvidenceService.swift
├── RecApp/Sources/AudioSetup/
│   └── RouteVerificationService.swift
├── RecApp/Sources/AudioHealth/
│   ├── AudioEnvironmentMonitor.swift
│   └── BluetoothRoutePolicy.swift
├── Shared/Sources/Models/
│   ├── AudioStates.swift
│   ├── LowResourceAudioModels.swift
│   └── ReleaseHardeningEvidence.swift
├── Shared/Sources/Diagnostics/
│   └── DiagnosticRedactor.swift
├── Shared/Tests/
│   ├── LivePassthroughPolicyTests.swift
│   ├── RouteVerificationTests.swift
│   ├── RouteRecoveryEvidenceTests.swift
│   ├── LocalRecordingManifestTests.swift
│   └── DiagnosticRedactionTests.swift
└── Scripts/
    ├── validate-live-route-readiness.sh
    ├── validate-live-passthrough-foundation.sh
    └── validate-recording-artifact-format.sh
```

**Structure Decision**: Implement in the existing macOS app/shared package and
validation script structure. No new server component, background service, or
cross-platform abstraction is introduced for this slice.

## Phase 0 Research Decisions

See [research.md](./research.md). Key decisions:

- client activity and route freshness, not audio energy, decide whether an
  active meeting route must be preserved;
- idle release is allowed only after fresh evidence proves the meeting client
  closed the virtual route;
- Core Audio property listeners plus polling fallback detect macOS default route
  changes and device-running state changes outside realtime callbacks;
- autorepair is a bounded state machine with recoverable vs non-recoverable
  classification;
- validation uses deterministic long-duration local evidence, not subjective
  "it sounded fine" checks.

## Phase 1 Design Decisions

Design artifacts produced:

- [data-model.md](./data-model.md)
- [contracts/route-evidence-events.md](./contracts/route-evidence-events.md)
- [contracts/autorepair-state-machine.md](./contracts/autorepair-state-machine.md)
- [contracts/recording-timeline-evidence.md](./contracts/recording-timeline-evidence.md)
- [contracts/validation-run-evidence.md](./contracts/validation-run-evidence.md)
- [quickstart.md](./quickstart.md)

Implementation approach:

1. Add first-class `LiveRouteSession`, `ClientActivitySnapshot`,
   `MacOSDefaultRouteSnapshot`, `AutorepairAttempt`, and `RouteEvidenceEvent`
   models in the shared macOS model layer.
2. Replace `anyExpectedVirtualDeviceRunning()` as the sole activity truth with
   per-side client evidence and freshness windows. Natural silence must not
   count as idle.
3. Make idle release fail-closed toward preservation: if evidence is stale or
   ambiguous while a meeting route was active, keep the route and record
   `release_denied_unknown_state`.
4. Convert stale conditions such as `coreaudiod_restarted`, sleep/wake,
   accepted macOS default-route changes, physical-device return, browser stream
   recreation, and app-side route engine restart into bounded autorepair
   attempts.
5. Keep non-recoverable conditions blocked: missing permission, missing accepted
   devices, meeting target no longer using virtual devices, Bluetooth/AirPods
   default route, or any case requiring 2brain Rec to choose physical devices
   independently.
6. Extend local recording manifest/evidence with route-interruption category,
   duration difference band, route session id, and autorepair correlation.
7. Add contract tests before implementation for event schemas, state-machine
   transitions, redaction, timing bands, and target/device-class evidence.
8. Add development validation scripts for 30-minute runs and release quickstart
   steps for 75-minute manual runs.

## Constitution Check - Post Design

| Principle | Status | Design Response |
|-----------|--------|-----------------|
| I. Driver-First Capture Integrity | PASS | Design preserves the virtual audio layer, prevents self-release, repairs recoverable route disruptions, and keeps timeline integrity as an acceptance gate. |
| II. Visible Consent And User Control | PASS | No hidden recording is added. User-facing repair is passive on success. Recording indicator/stop remain unchanged and explicitly guarded. |
| III. Data Boundary And Secret Discipline | PASS | Contracts explicitly exclude raw audio/content/secrets and keep diagnostics local-first. |
| IV. Deletion Truth And Lifecycle Accounting | PASS | New evidence is metadata attached to local route/recording artifacts; no external lifecycle is introduced. |
| V. Spec-Driven Delivery With Testable Gates | PASS | Research/design artifacts are complete enough for `$speckit-tasks`; implementation must wait for tasks and analyze. |

## Complexity Tracking

No constitution violations or extra architectural layers are introduced.
