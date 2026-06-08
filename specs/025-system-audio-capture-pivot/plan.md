# Implementation Plan: System Audio Capture Pivot

**Branch**: `025-system-audio-capture-pivot` | **Date**: 2026-06-08 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/025-system-audio-capture-pivot/spec.md`

## Summary

Replace the MVP recording path with native macOS system-audio plus microphone
capture. The app records `mic.wav`, `incoming.wav`, and `manifest.json` without
publishing, probing, or requiring HAL virtual devices. The first implementation
keeps recording local-first, preserves visible recording state and one-action
Stop, records metadata-only health evidence, and parks the existing driver path
as future advanced-routing work.

## Technical Context

**Language/Version**: Swift 6.0 package, macOS-native SwiftUI/AppKit app,
Swift/C++ driver code present but out of MVP path for this feature.

**Primary Dependencies**: ScreenCaptureKit for incoming/system audio capture,
AVFoundation/AVAudioRecorder or AVAudioEngine for microphone capture, existing
`TwoBrainRecShared` and `TwoBrainRecAppCore` models, existing local recording
manifest and diagnostic redaction services.

**Storage**: Local file artifacts under the existing local recording store:
`manifest.json`, `mic.wav`, `incoming.wav`, and metadata-only evidence files.
No backend upload, MediaScribe call, Langfuse content trace, or server storage
is introduced in this feature.

**Testing**: SwiftPM tests in `apps/macos` (`swift test` where supported by the
local toolchain), contract validation executable, shell validation scripts,
manual macOS permission/runtime validation, CPU sampling through existing and
new scripts.

**Target Platform**: macOS 14+ on Apple Silicon for MVP validation. Future
platforms remain out of scope.

**Project Type**: SwiftPM macOS desktop app with shared Swift libraries and a
local recording pipeline.

**Performance Goals**:

- Idle after 10-second settle: `coreaudiod` < 5% CPU and app < 5% CPU.
- Active recording: no sustained `coreaudiod` > 10% CPU and no sustained
  app/helper > 25% CPU.
- Stop/quit: capture resources released and CPU returns below idle gate within
  10 seconds.
- Accepted tracks: `durationDifferenceSeconds <= 3`.

**Constraints**:

- No HAL virtual-device publication, runtime probe, or driver repair can be
  required for MVP acceptance.
- Normal accepted recording requires microphone and Screen/System Audio
  permission before start.
- Arbitrary background system audio is not a recording trigger.
- Diagnostics remain metadata-only and must not include raw audio, transcript
  text, meeting content, credentials, tokens, signed URLs, or passwords.
- The app must remain stoppable locally even if capture, file writing, or future
  server policy surfaces fail.
- "Sustained" CPU threshold means at least three consecutive samples above the
  threshold at 2-second sampling intervals after the relevant settle window.

**Scale/Scope**: Single-user local MVP recording flow; controlled Telemost,
Chrome, Opera, Zoom/browser-style validation; 30-minute development run plus
75-minute manual release run before acceptance.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Capture-first MVP integrity**: PASS. The feature removes unsafe driver
  dependency from MVP acceptance and uses native Screen/System Audio plus
  microphone capture with explicit CPU, alignment, permission, and degraded
  state gates.
- **Visible consent and user control**: PASS. Manual start/stop remains the
  first flow; active recording requires a visible local indicator and one-action
  Stop. Arbitrary system audio is not a trigger.
- **Data boundary and secret discipline**: PASS. This feature is local-first and
  explicitly excludes upload, MediaScribe calls, Langfuse content traces, and
  secrets in diagnostics.
- **Deletion truth and lifecycle accounting**: PASS. Local artifacts remain
  known local lifecycle items; no new external deletion boundary is introduced.
- **Spec-driven delivery with testable gates**: PASS. Clarification is complete,
  plan artifacts define contracts, data model, quickstart, and measurable gates
  before tasks/implementation.

## Project Structure

### Documentation (this feature)

```text
specs/025-system-audio-capture-pivot/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── capture-session-contract.md
│   ├── dual-track-manifest-contract.md
│   └── validation-evidence-contract.md
└── tasks.md
```

### Source Code (repository root)

```text
apps/macos/
├── Package.swift
├── RecApp/
│   ├── App/TwoBrainRecApp.swift
│   └── Sources/
│       ├── Capture/
│       │   ├── SystemAudioCaptureService.swift
│       │   ├── MicrophoneCaptureService.swift
│       │   ├── CaptureScopeApprovalService.swift
│       │   ├── CaptureHealthMonitor.swift
│       │   ├── LocalRecordingWriter.swift
│       │   └── CaptureControlView.swift
│       └── Diagnostics/
│           └── DiagnosticBundleService.swift
├── Shared/
│   ├── Sources/
│   │   ├── Models/
│   │   │   ├── SystemAudioCaptureModels.swift
│   │   │   ├── LocalRecordingModels.swift
│   │   │   └── AudioStates.swift
│   │   └── Diagnostics/
│   │       └── DiagnosticRedactor.swift
│   └── Tests/
│       ├── SystemAudioCaptureContractTests.swift
│       ├── CaptureScopeApprovalTests.swift
│       ├── LocalRecordingManifestTests.swift
│       ├── CaptureHealthMonitorTests.swift
│       └── DiagnosticRedactionTests.swift
└── Scripts/
    ├── validate-system-audio-capture-pivot.sh
    ├── sample-system-audio-cpu-gate.sh
    └── validate-system-audio-no-hal-probe.sh
```

**Structure Decision**: Implement the pivot inside the existing SwiftPM macOS
package. Add new capture services under `RecApp/Sources/Capture`, shared models
under `Shared/Sources/Models`, tests under `Shared/Tests`, and validation
scripts under `apps/macos/Scripts`. Existing `AudioDriver/` code remains in the
repository but is not part of the MVP recording path for this feature.

## Complexity Tracking

No constitution violations or complexity exceptions are required.

## Phase 0 Research Summary

See [research.md](./research.md). Key decisions:

- Use ScreenCaptureKit `SCStream` with audio enabled for incoming/system audio.
- Capture microphone through a separate AVFoundation-backed path instead of
  mixing microphone into ScreenCaptureKit output.
- Use a user-selected or user-confirmed app/window/display scope.
- Keep existing dual-track local artifact shape and extend manifest metadata for
  scope approval, permission state, CPU evidence, protected/blocked/silent audio,
  and no-HAL dependency.
- Do not run HAL runtime probes for MVP validation.

## Phase 1 Design Summary

See:

- [data-model.md](./data-model.md)
- [contracts/capture-session-contract.md](./contracts/capture-session-contract.md)
- [contracts/dual-track-manifest-contract.md](./contracts/dual-track-manifest-contract.md)
- [contracts/validation-evidence-contract.md](./contracts/validation-evidence-contract.md)
- [quickstart.md](./quickstart.md)

## Post-Design Constitution Check

- **Capture-first MVP integrity**: PASS. Design has explicit system-audio,
  microphone, permission, alignment, no-overheat, and no-HAL gates.
- **Visible consent and user control**: PASS. Capture scope approval, active
  indicator, and one-action stop are contractual.
- **Data boundary and secret discipline**: PASS. Contracts prohibit raw content
  in diagnostics and exclude external egress.
- **Deletion truth and lifecycle accounting**: PASS. New local artifacts and
  evidence are represented as local lifecycle items.
- **Spec-driven delivery with testable gates**: PASS. Design artifacts are
  traceable to user stories and success criteria; no unresolved `NEEDS
  CLARIFICATION` markers remain.
