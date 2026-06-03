# Implementation Plan: Recording Artifact Format

**Branch**: `010-recording-artifact-format` | **Date**: 2026-06-04 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/010-recording-artifact-format/spec.md`

## Summary

Change the local macOS recording artifact contract from feature `008` into a
MediaScribe-ready dual-track package. New manual recordings must save two
continuous role-specific WAV files: `mic.wav` and `incoming.wav`, both PCM
signed 16-bit little-endian, mono, 16000 Hz, sharing the same session timeline.
The manifest must describe transcription readiness, MediaScribe field mapping,
format details, timeline alignment, safe file names, byte counts, frame counts,
and degraded/failed reasons. This slice does not upload, call MediaScribe, read
MediaScribe secrets, publish dashboard data, or claim retention/deletion.

## Technical Context

**Language/Version**: Swift 6 for macOS app/core/shared models; shell for validation.

**Primary Dependencies**: SwiftUI app, `TwoBrainRecShared`,
`TwoBrainRecAppCore`, `AVFoundation`, existing `SharedAudioMemory`,
`LocalRecordingWriter`, `LocalRecordingManifestService`,
`DiagnosticBundleService`, SwiftPM/XCTest.

**Storage**: App-owned local recording directories under Application Support,
containing two WAV track files plus `manifest.json`. No server storage in this
slice.

**Testing**: `swift test --package-path apps/macos --disable-swift-testing`,
`swift run --package-path apps/macos ContractValidation`,
`sh tests/macos/static/audio-rt-safety-check.sh`, and a new artifact-format
validation script.

**Target Platform**: macOS 14.5+ on Apple Silicon.

**Project Type**: Native macOS desktop app plus Core Audio virtual audio layer.

**Performance Goals**: Stop finalization remains visible within 2 seconds for
short smoke recordings. Recording writer must not add file IO, conversion,
allocation, logging, lock waits, or network calls to HAL/Core Audio callbacks.

**Constraints**: Manual recording only. Visible indicator and one-action stop
remain required. Desktop never calls MediaScribe and never reads or stores
MediaScribe credentials. WAV output is larger than compressed formats but is the
current MediaScribe-preferred contract for minimal conversion and timestamp
quality.

**Scale/Scope**: One active local manual recording at a time. Short smoke and
developer MVP validation. Long-duration storage sizing, upload chunking,
backend ingest, MediaScribe job submission, retention, deletion, and dashboard
publication are future slices.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Driver-first capture integrity**: PASS. The feature preserves the macOS
  virtual audio route and only changes app-owned local artifact finalization.
- **Visible consent and user control**: PASS. Manual `Record`/`Stop`, visible
  recording state, and one-action stop remain required from `007`.
- **Data boundary and secret discipline**: PASS. No upload, direct desktop
  MediaScribe call, MediaScribe key access, Langfuse content trace, dashboard
  publish, or new external egress is introduced.
- **Deletion truth and lifecycle accounting**: PASS. The manifest becomes a
  better lifecycle input but does not claim deletion coverage. Future deletion
  reports must account for these local files.
- **Spec-driven delivery with testable gates**: PASS. Specification,
  checklist, plan, research, data model, contracts, quickstart, tasks, analyze,
  and implementation are required before coding.

**Initial Gate Result**: PASS. No constitution conflict blocks Phase 0.

## Project Structure

### Documentation (this feature)

```text
specs/010-recording-artifact-format/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── mediascribe-ready-artifact-contract.md
│   └── wav-track-format-contract.md
├── checklists/
│   └── requirements.md
└── tasks.md
```

### Source Code (repository root)

```text
apps/macos/
├── RecApp/
│   └── Sources/Capture/
│       ├── LocalRecordingStore.swift
│       ├── LocalRecordingWriter.swift
│       └── LocalRecordingManifestService.swift
├── Shared/
│   ├── Sources/
│   │   ├── Models/AudioModels.swift
│   │   ├── Models/AudioStates.swift
│   │   └── Diagnostics/DiagnosticRedactor.swift
│   ├── Tests/
│   │   ├── LocalRecordingWriterTests.swift
│   │   ├── LocalRecordingManifestTests.swift
│   │   ├── RecordingEvidenceTests.swift
│   │   └── DiagnosticRedactionTests.swift
│   └── Tools/ContractValidation/main.swift
└── Scripts/
    └── validate-recording-artifact-format.sh

tests/macos/
├── contract/
│   ├── local-recording-manifest.json
│   └── recording-artifact-format.json
└── local-recording/
    └── recording-artifact-format-smoke.md

qa/macos/
└── recording-artifact-format.md
```

**Structure Decision**: Keep audio artifact writing in the existing app-owned
local writer, extend shared model contracts for manifest/readiness metadata, and
add validation fixtures under `tests/macos`. Do not move format conversion into
HAL/Core Audio callbacks.

## Phase 0: Research

See [research.md](research.md).

## Phase 1: Design And Contracts

See [data-model.md](data-model.md), [contracts/](contracts/), and
[quickstart.md](quickstart.md).

### Post-Design Constitution Check

- **Driver-first capture integrity**: PASS. Design keeps capture sources
  separate and preserves route truth.
- **Visible consent and user control**: PASS. Format changes do not alter
  manual start/stop or visible indicator UX.
- **Data boundary and secret discipline**: PASS. Contracts explicitly prohibit
  MediaScribe credential access and direct desktop-to-MediaScribe upload.
- **Deletion truth and lifecycle accounting**: PASS. New manifest fields improve
  future lifecycle accounting without claiming purge.
- **Spec-driven delivery with testable gates**: PASS. Design artifacts define
  testable contracts and validation commands before tasks/implementation.

**Post-Design Gate Result**: PASS.

## Complexity Tracking

No constitution violations or justified complexity exceptions.
