# Implementation Plan: Manual Capture Session And Visible Indicator

**Branch**: `007-capture-session-indicator` | **Date**: 2026-06-01 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/007-capture-session-indicator/spec.md`

## Summary

Implement the first safe recording control layer on top of the accepted
low-resource non-recording passthrough route. The feature adds explicit manual
Record/Stop, prerequisite gating, persistent visible local capture indication,
one-action stop, local metadata-only lifecycle evidence, and fail-closed behavior
when route, policy, storage, permission, app bridge, or visible-indicator
preconditions are not satisfied. It does not add upload, MediaScribe,
Langfuse, dashboard publication, retention, deletion, or assisted auto-start.

The technical approach reuses the existing native macOS app structure:
`TwoBrainRecShared` owns recordable models and safety validators, while
`TwoBrainRecAppCore` owns local capture orchestration, UI surfaces, diagnostics,
and the existing passthrough route engine integration. The HAL driver remains a
thin audio route component; recording ownership stays in app software.

## Technical Context

**Language/Version**: Swift 6 for macOS app/core/shared models; C/C++ Core Audio
driver remains unchanged except where validation proves route state. Shell is
used only for local validation scripts.

**Primary Dependencies**: Existing SwiftUI macOS app, `TwoBrainRecShared`,
`TwoBrainRecAppCore`, Core Audio runtime state, existing low-resource
`PassthroughRouteEngine`, diagnostic redaction utilities, and SwiftPM/XCTest.

**Storage**: Local metadata-only capture evidence and local buffer summary hooks.
This slice may create local capture/evidence records, but no server persistence,
MediaScribe upload, Langfuse content trace, or dashboard meeting record.

**Testing**: `swift test --package-path apps/macos --disable-swift-testing`,
`swift run --package-path apps/macos ContractValidation`,
`sh tests/macos/static/audio-rt-safety-check.sh`, targeted capture control and
diagnostic redaction tests, and short manual smoke for Telemost, Chrome, Opera,
and Zoom.

**Target Platform**: macOS 14.5+ on Apple Silicon. Windows and other platforms
are out of scope.

**Project Type**: Native macOS desktop app plus existing Core Audio virtual audio
layer.

**Performance Goals**: Stop action transitions active recording to
stopping/stopped within 1 second in local validation. Recording start blockers
must resolve synchronously enough for the UI to show a concrete reason without
starting capture. No HAL callback-sensitive realtime path may gain file IO,
network calls, logging, allocation, lock waits, process launches, or UI work.

**Constraints**: No silent or invisible recording. Active recording must always
have a persistent local visible indicator and one-action stop. Manual start/stop
only. No upload/transcription/external egress. Diagnostics and evidence must be
metadata-only and redacted. Existing low-resource non-recording passthrough must
remain usable before and after recording.

**Scale/Scope**: Internal MVP/local validation for one active manual capture
session at a time. Multi-session recording, assisted auto-start, server ingest,
retention/deletion, dashboard meeting details, and production notarization are
future slices.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### 2brain Rec Constitutional Gates

- **Driver-first capture integrity**: PASS. The feature depends on the accepted
  macOS virtual audio route and does not add a no-driver fallback. Capture is
  blocked from publication-only, stale, failed, or unknown route evidence.
- **Visible consent and user control**: PASS. The feature is explicitly manual
  start/stop, persistent local indicator, one-action stop, and fail-closed on
  indicator loss.
- **Data boundary and secrets**: PASS. Desktop does not send audio to
  MediaScribe, store MediaScribe credentials, start Langfuse content tracing, or
  create external egress.
- **Deletion truth and lifecycle accounting**: PASS. This slice creates only
  local lifecycle/evidence concepts and does not promise deletion beyond local
  scope. It records local artifacts for future lifecycle accounting.
- **Spec-driven delivery with testable gates**: PASS. Specify and clarify are
  complete; this plan creates research, data model, contracts, quickstart, then
  checklist, tasks, analyze, and implement.
- **Brand-distance and accessibility**: PASS. UI requirements use original
  2brain Rec language, require keyboard/assistive stop access, and avoid
  competitor wording.
- **Operational readiness**: N/A for Docker/server deployment in this slice.
  Local storage reserve, diagnostics redaction, crash/bridge loss, and route
  recovery are included as local gates.

**Initial Gate Result**: PASS. No constitution conflict blocks Phase 0 research.

## Project Structure

### Documentation (this feature)

```text
specs/007-capture-session-indicator/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── capture-lifecycle-contract.md
│   ├── visible-indicator-contract.md
│   └── recording-evidence-contract.md
├── checklists/
│   ├── requirements.md
│   ├── security.md
│   ├── driver.md
│   └── ux.md
└── tasks.md
```

### Source Code (repository root)

```text
apps/macos/
├── RecApp/
│   ├── App/TwoBrainRecApp.swift
│   └── Sources/
│       ├── Capture/
│       │   ├── CaptureControlView.swift
│       │   ├── CaptureSessionController.swift
│       │   ├── CaptureStatusItem.swift
│       │   ├── CaptureFinalizationService.swift
│       │   ├── CaptureRecoveryService.swift
│       │   ├── RecordingPrerequisiteGate.swift
│       │   └── RecordingEvidenceService.swift
│       └── Diagnostics/DiagnosticBundleService.swift
├── Shared/
│   ├── Sources/
│   │   ├── Audit/AuditEvents.swift
│   │   ├── Diagnostics/DiagnosticRedactor.swift
│   │   └── Models/
│   │       ├── AudioModels.swift
│   │       ├── AudioStates.swift
│   │       └── CaptureSessionSafetyValidator.swift
│   ├── Tests/
│   │   ├── CaptureControlTests.swift
│   │   ├── CaptureSessionSafetyTests.swift
│   │   ├── RecordingPrerequisiteGateTests.swift
│   │   ├── RecordingEvidenceTests.swift
│   │   └── DiagnosticRedactionTests.swift
│   └── Tools/ContractValidation/main.swift
└── Scripts/
    └── validate-capture-session-indicator.sh

qa/macos/
├── capture-session-indicator.md
└── release-candidate-checklist.md

tests/macos/
├── contract/recording-session-evidence.json
├── browser-meetings/manual-recording-smoke.md
└── static/audio-rt-safety-check.sh
```

**Structure Decision**: Keep recording control in the macOS app/core layer and
shared models. Do not move recording ownership into the HAL driver. Add
metadata-only evidence and validation alongside existing diagnostic and contract
fixtures.

## Phase 0: Research

See [research.md](research.md).

## Phase 1: Design And Contracts

See [data-model.md](data-model.md), [contracts/](contracts/), and
[quickstart.md](quickstart.md).

### Post-Design Constitution Check

- **Driver-first capture integrity**: PASS. Contracts require valid route
  evidence before start and fail-closed on bridge loss or `coreaudiod` restart.
- **Visible consent and user control**: PASS. Visible-indicator contract requires
  persistent local surface and one-action stop during active recording.
- **Data boundary and secrets**: PASS. Recording evidence contract excludes
  upload, MediaScribe, Langfuse, credentials, raw audio, transcript text, and
  meeting content.
- **Deletion truth and lifecycle accounting**: PASS. Local evidence records
  capture artifacts for future lifecycle work without promising server deletion.
- **Spec-driven delivery with testable gates**: PASS. Design artifacts are ready
  for checklist, tasks, analyze, and implementation.

**Post-Design Gate Result**: PASS.

## Complexity Tracking

No constitution violations or justified complexity exceptions.
