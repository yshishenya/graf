# Implementation Plan: Microphone Sample Graph Foundation

**Branch**: `037-microphone-sample-graph-foundation` | **Date**: 2026-06-18 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/037-microphone-sample-graph-foundation/spec.md`

## Summary

Introduce an app-owned microphone sample stream for local recordings while
preserving the accepted system-audio-first package shape from `025`:
`mic.wav`, `incoming.wav`, and `manifest.json`. The implementation adds native
recording microphone selection with fallback to the current macOS default input,
rejects self-routing virtual inputs, feeds microphone frames into the existing
`LocalRecordingWriter` through `microphoneSampleSourceFactory`, and records
metadata-only stream truth for future cleanup/AEC work. This feature does not
claim live echo cancellation or built-in speakerphone clean acceptance.

## Technical Context

**Language/Version**: Swift 6.0 package, macOS-native SwiftUI/AppKit app,
existing Swift shared libraries under `apps/macos`, macOS 14 package baseline.

**Primary Dependencies**: AVFoundation/AVFAudio for microphone permission and
app-owned audio capture, CoreAudio device metadata for input identity and
default input fallback, existing `TwoBrainRecShared` and `TwoBrainRecAppCore`
models, existing `LocalRecordingWriter`, `LocalRecordingManifestService`,
`SystemAudioCaptureService`, and `SelfRoutingGuard`.

**Storage**: Existing local recording package only: `manifest.json`, `mic.wav`,
`incoming.wav`, and metadata-only local evidence. No derived cleaned audio,
server upload, MediaScribe call, Langfuse content trace, or desktop-stored
external credential is introduced.

**Testing**: SwiftPM tests in `apps/macos` (`swift test`), existing contract
tests under `apps/macos/Shared/Tests/ContractTests`, focused manual macOS
Record/Stop validation, existing recording artifact validators, and existing
CPU/resource scripts.

**Target Platform**: macOS 14+ on Apple Silicon for MVP validation.

**Project Type**: SwiftPM macOS desktop app with shared Swift libraries and a
local recording pipeline.

**Performance Goals**:

- Preserve `025` CPU gates: idle after settle keeps `coreaudiod` < 5% CPU and
  app < 5% CPU; active recording avoids sustained `coreaudiod` > 10% CPU and
  sustained combined app/helper > 25% CPU.
- Stop/quit releases microphone capture and returns to idle resource behavior
  within 10 seconds.
- Accepted local package keeps `durationDifferenceSeconds <= 3`.
- Microphone sample draining remains bounded by the existing writer drain
  policy and must not hang Stop/finalization.

**Constraints**:

- This feature is foundation work only: no Apple voice-processing acceptance, no
  WebRTC AEC3 acceptance, no mixed fallback, and no claim that speakerphone
  recording is clean.
- Normal MVP recording remains system-audio-first and must not require selecting
  `2brain Rec Microphone` or `2brain Rec Speaker` in the meeting app.
- User-selected recording microphone inputs must be native inputs; 2brain
  virtual devices and unsupported self-routing inputs are rejected.
- If the selected input is unavailable or the app-owned stream cannot prove it
  is using the selected/default input, recording fails closed or records a
  degraded/unproven state.
- Diagnostics remain metadata-only and must not include raw audio, transcript
  text, meeting content, credentials, tokens, signed URLs, passwords, live local
  paths, or participant identifiers.
- Legacy `AVAudioRecorder` behavior may remain only as a bounded compatibility
  path until removed later; accepted `037` evidence must prove the app-owned
  sample source path was used.

**Scale/Scope**: Single-user local MVP recording flow; default microphone and at
least one selected native microphone scenario; failure coverage for denied
permission, unavailable selected input, route change, no frames, silence, Stop,
quit, and unsupported/self-routing input.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Capture-first MVP integrity**: PASS. The feature keeps system-audio-first
  MVP recording, preserves dual-track local artifacts, and adds microphone frame
  control without requiring virtual driver routing.
- **Visible consent and user control**: PASS. Manual Record/Stop, visible active
  capture state, one-action Stop, microphone permission, and native recording
  input selection remain explicit.
- **Data boundary and secret discipline**: PASS. The feature is local-first,
  metadata-only for diagnostics, and excludes upload, MediaScribe calls,
  Langfuse content traces, raw samples, transcript text, and secrets.
- **Deletion truth and lifecycle accounting**: PASS. No derived cleaned audio or
  new external storage boundary is introduced; existing local package retention
  and deletion accounting remain the lifecycle surface.
- **Spec-driven delivery with testable gates**: PASS. Clarification is complete,
  plan artifacts define research decisions, data model, contracts, quickstart,
  and measurable gates before tasks/implementation.

## Project Structure

### Documentation (this feature)

```text
specs/037-microphone-sample-graph-foundation/
|-- plan.md
|-- research.md
|-- data-model.md
|-- quickstart.md
|-- contracts/
|   |-- microphone-selection-contract.md
|   |-- microphone-sample-graph-contract.md
|   `-- local-recording-package-contract.md
`-- tasks.md
```

### Source Code (repository root)

```text
apps/macos/
|-- Package.swift
|-- RecApp/
|   |-- App/
|   |   `-- TwoBrainRecApp.swift
|   `-- Sources/
|       |-- AudioSetup/
|       |   |-- PhysicalDeviceSelectionViewModel.swift
|       |   `-- WorkingDeviceStore.swift
|       `-- Capture/
|           |-- MicrophoneCaptureService.swift
|           |-- SystemAudioCaptureService.swift
|           |-- LocalRecordingWriter.swift
|           `-- LocalRecordingManifestService.swift
`-- Shared/
    |-- Sources/
    |   |-- Models/
    |   |   |-- AudioModels.swift
    |   |   |-- AudioStates.swift
    |   |   `-- SystemAudioCaptureModels.swift
    |   `-- Routing/
    |       `-- SelfRoutingGuard.swift
    `-- Tests/
        |-- MicrophoneCaptureServiceTests.swift
        |-- LocalRecordingWriterSystemAudioTests.swift
        |-- LocalRecordingManifestTests.swift
        |-- LocalRecordingLeakageFinalizationTests.swift
        |-- DiagnosticRedactionTests.swift
        `-- ContractTests/
```

**Structure Decision**: Implement inside the existing SwiftPM macOS package.
Microphone permission, input selection, app-owned capture source, and stream
health live under `RecApp/Sources/Capture` and existing shared models. Native
selection may reuse or narrow existing audio setup and `SelfRoutingGuard`
concepts, but the recording input selection contract belongs to the recording
flow, not the old virtual-route setup flow. Tests stay under
`apps/macos/Shared/Tests` and should extend existing manifest/writer/leakage
coverage rather than introduce a second package format.

## Complexity Tracking

No constitution violations or complexity exceptions are required.

## Phase 0 Research Summary

See [research.md](./research.md). Key decisions:

- Use an app-owned microphone sample source as the accepted `037` path and feed
  it through `LocalRecordingWriter.microphoneSampleSourceFactory`.
- Support native recording microphone selection, with the current macOS default
  input as fallback when no explicit selection exists.
- Reject 2brain virtual/self-routing inputs for the recording microphone.
- Preserve `mic.wav`, `incoming.wav`, `manifest.json`, `020` leakage truth, and
  `025` system-audio behavior.
- Keep diagnostics metadata-only and use explicit degraded/failed/unproven
  states for stream failures.

## Phase 1 Design Summary

See:

- [data-model.md](./data-model.md)
- [contracts/microphone-selection-contract.md](./contracts/microphone-selection-contract.md)
- [contracts/microphone-sample-graph-contract.md](./contracts/microphone-sample-graph-contract.md)
- [contracts/local-recording-package-contract.md](./contracts/local-recording-package-contract.md)
- [quickstart.md](./quickstart.md)

## Post-Design Constitution Check

- **Capture-first MVP integrity**: PASS. The design keeps accepted dual-track
  package behavior and adds app-owned microphone stream truth without a virtual
  driver dependency or cleanup claim.
- **Visible consent and user control**: PASS. Recording still starts manually,
  remains visibly stoppable, and selected/default microphone truth is explicit.
- **Data boundary and secret discipline**: PASS. Contracts prohibit raw content
  and secrets in diagnostics and exclude new desktop egress.
- **Deletion truth and lifecycle accounting**: PASS. Existing local artifacts
  remain the only lifecycle items in this slice; derived cleaned tracks are
  deferred.
- **Spec-driven delivery with testable gates**: PASS. Design artifacts are
  traceable to user stories and success criteria; no unresolved `NEEDS
  CLARIFICATION` markers remain.
