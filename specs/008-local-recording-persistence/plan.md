# Implementation Plan: Local Recording Persistence

**Branch**: `008-local-recording-persistence` | **Date**: 2026-06-02 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/008-local-recording-persistence/spec.md`

## Summary

Persist the manual recording created by feature `007` into discoverable local
artifacts after `Stop`. The first complete product answer is: local mic track,
remote speaker track, and metadata-only session manifest are saved locally and
shown in the app. Upload, transcription, MediaScribe, Langfuse, dashboard,
retention, deletion, and assisted auto-start stay out of scope.

The implementation keeps recording ownership in the macOS app/core layer. The
HAL driver remains responsible for virtual-device audio movement and already
mirrors virtual speaker input into shared memory. A non-realtime app writer
reads `mic` and `capture` rings from `SharedAudioMemory`, writes local track
files, finalizes a manifest, and feeds track status back into the existing
capture session/evidence model.

## Technical Context

**Language/Version**: Swift 6 for app/core/shared code; existing C++ HAL driver
unchanged unless validation reveals a mirror contract gap; shell for validation.

**Primary Dependencies**: SwiftUI app, `TwoBrainRecShared`, `TwoBrainRecAppCore`,
`SharedAudioMemory`, existing `CaptureSessionController`, `RecordingEvidenceService`,
diagnostic redaction utilities, SwiftPM/XCTest. Local audio file writing uses
Apple platform audio APIs from the app process, not HAL callbacks.

**Storage**: Local files under an app-owned recording directory, with generated
session ids. Initial artifacts are local track files plus `manifest.json`.
No server persistence, upload queue, retention/deletion engine, or dashboard row.

**Testing**: `swift test --package-path apps/macos --disable-swift-testing`,
`swift run --package-path apps/macos ContractValidation`,
`sh tests/macos/static/audio-rt-safety-check.sh`, and
`sh apps/macos/Scripts/validate-local-recording-persistence.sh`.

**Target Platform**: macOS 14.5+ on Apple Silicon.

**Project Type**: Native macOS desktop app plus existing Core Audio virtual
audio layer.

**Performance Goals**: Stop finalization returns a visible saved/degraded state
within 2 seconds for a short smoke recording. Writer polling must not add file
IO, allocation, logging, locks, or network calls to HAL/Core Audio callbacks.

**Constraints**: Manual start/stop only. Active recording remains visible with
one-action stop. Track artifacts are local only. Evidence is metadata-only.
No upload/transcription/external egress. Missing or empty required tracks are
truthfully degraded/failed, never accepted as complete.

**Scale/Scope**: One active local manual recording at a time. Short smoke and
developer MVP validation. Long-duration encrypted buffering, retry upload,
backend ingest, retention, deletion, and transcript generation are future slices.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Driver-first capture integrity**: PASS. Feature depends on the existing
  macOS driver route and does not introduce a no-driver fallback.
- **Visible consent and user control**: PASS. Manual `Record`/`Stop`, visible
  local indicator, and fail-closed behavior from `007` remain required.
- **Data boundary and secret discipline**: PASS. Local artifacts stay on-device;
  no MediaScribe, Langfuse content traces, credentials, signed URLs, or external
  egress are introduced.
- **Deletion truth and lifecycle accounting**: PASS. The feature records local
  artifact metadata but does not claim retention or deletion behavior beyond
  local artifact creation.
- **Spec-driven delivery with testable gates**: PASS. Spec and checklist are
  complete; plan creates research, data model, contracts, quickstart, then
  checklist, tasks, analyze, and implementation.

**Initial Gate Result**: PASS. No constitution conflict blocks Phase 0.

## Project Structure

### Documentation (this feature)

```text
specs/008-local-recording-persistence/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── local-recording-manifest-contract.md
│   └── local-recording-writer-contract.md
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
│       │   ├── LocalRecordingStore.swift
│       │   ├── LocalRecordingWriter.swift
│       │   ├── LocalRecordingManifestService.swift
│       │   ├── CaptureControlView.swift
│       │   └── CaptureSessionController.swift
│       └── Diagnostics/DiagnosticBundleService.swift
├── Shared/
│   ├── Sources/
│   │   ├── Models/AudioModels.swift
│   │   ├── Models/AudioStates.swift
│   │   ├── SharedAudioMemory.swift
│   │   └── Diagnostics/DiagnosticRedactor.swift
│   ├── Tests/
│   │   ├── LocalRecordingStoreTests.swift
│   │   ├── LocalRecordingWriterTests.swift
│   │   ├── LocalRecordingManifestTests.swift
│   │   └── DiagnosticRedactionTests.swift
│   └── Tools/ContractValidation/main.swift
└── Scripts/
    └── validate-local-recording-persistence.sh

qa/macos/
└── local-recording-persistence.md

tests/macos/
├── contract/local-recording-manifest.json
└── local-recording/local-recording-smoke.md
```

**Structure Decision**: Keep persistence orchestration in `TwoBrainRecAppCore`,
shared data contracts in `TwoBrainRecShared`, and validation fixtures under
`tests/macos`. Do not put file IO in driver callbacks.

## Phase 0: Research

See [research.md](research.md).

## Phase 1: Design And Contracts

See [data-model.md](data-model.md), [contracts/](contracts/), and
[quickstart.md](quickstart.md).

### Post-Design Constitution Check

- **Driver-first capture integrity**: PASS. Writer consumes existing shared
  memory route evidence and treats missing mirrored speaker frames as degraded.
- **Visible consent and user control**: PASS. UI continues to show active
  indicator and adds post-stop saved/degraded location.
- **Data boundary and secret discipline**: PASS. Contracts forbid raw audio in
  diagnostics and live absolute paths in evidence.
- **Deletion truth and lifecycle accounting**: PASS. Manifest is local
  lifecycle input only; no deletion promise is added.
- **Spec-driven delivery with testable gates**: PASS. Design artifacts define
  independently testable local persistence stories.

**Post-Design Gate Result**: PASS.

## Complexity Tracking

No constitution violations or justified complexity exceptions.
