# Implementation Plan: Meeting-App Mute Truth

**Branch**: `022-meeting-mute-truth` | **Date**: 2026-06-16 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/022-meeting-mute-truth/spec.md`

## Summary

Implement the local MVP truth layer for meeting-app mute expectations without
pretending that 2brain Rec can read every third-party meeting app's internal
mute state. The implementation adds a product-owned `2brain Pause` privacy
control, records metadata-only pause and mute-truth evidence in local
recording artifacts, shows limitation copy for unproven meeting-app mute, and
keeps unsupported targets out of mute-respecting acceptance. No server upload,
MediaScribe, Langfuse, retention, deletion, or third-party meeting-app API
behavior is added by this feature.

## Technical Context

**Language/Version**: Swift 6.0 package, macOS-native SwiftUI/AppKit app, shared
Swift models in `TwoBrainRecShared` and `TwoBrainRecAppCore`.

**Primary Dependencies**: Existing `CaptureSessionController`,
`CaptureControlView`, `CaptureStatusItem`, `LocalRecordingWriter`,
`LocalRecordingManifestService`, `LocalRecordingManifest`,
`RecordingEvidenceService`, `DiagnosticRedactor`, and system-audio capture
foundation from feature `025`.

**Storage**: Local recording artifacts only. Extend `manifest.json` with
metadata-only privacy/mute-truth fields and optionally write local
metadata-only evidence rows. Do not upload, transcribe, or egress audio in this
feature.

**Testing**: SwiftPM tests in `apps/macos` (`swift build`, `swift test`,
`swift run ContractValidation`), focused manifest/UI/diagnostic tests, static
forbidden-content scans, and a new metadata-only validation script for the
Zoom native, Chrome/Telemost, Opera/Telemost, Yandex Browser, and unknown
target matrix.

**Target Platform**: macOS 14+ on Apple Silicon for MVP. Future Windows/Linux
shells may reuse server-rendered status later, but capture truth and Pause/Stop
remain native per platform.

**Project Type**: SwiftPM macOS desktop app with shared Swift libraries and a
local recording pipeline.

**Performance Goals**:

- `2brain Pause` must suppress/redact local microphone samples within 250 ms of
  the user action in unit/integration-level timing tests.
- Pause/resume must preserve timeline alignment for `mic.wav` and
  `incoming.wav`; accepted non-paused recordings still require
  `durationDifferenceSeconds <= 3`.
- Adding mute-truth metadata must not create raw audio, transcript text, or
  meeting content in diagnostics.

**Constraints**:

- No third-party meeting-app mute adapter is implemented in this slice.
- No server, upload, MediaScribe, Langfuse, dashboard, retention, deletion,
  sharing, download, or assisted auto-recording behavior is added.
- Product-owned Pause/Stop are the only canonical MVP privacy truth source.
- Unsupported or unobservable targets may be recorded manually, but must show
  limitation copy and carry `meeting_mute_unproven` or equivalent degraded
  artifact truth.
- Active capture must remain visible, with one-action Stop available.
- Diagnostics remain metadata-only and must exclude raw audio, transcript text,
  meeting content, credentials, tokens, signed URLs, passwords, and live secret
  paths.

**Scale/Scope**: Single-user local MVP recording flow. First QA matrix validates
product-owned Pause/Stop and limitation truth for Zoom native, Chrome/Telemost,
and Opera/Telemost; Yandex Browser and generic/unknown targets remain
unsupported or deferred for direct meeting-app mute truth.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Capture-first MVP integrity**: PASS. This feature preserves the native
  system-audio-first MVP capture path and adds a local privacy-control gate
  around microphone samples; it does not reintroduce virtual-driver routing.
- **Visible consent and user control**: PASS. Pause and Stop are explicit local
  controls; active capture remains visible and stoppable.
- **Data boundary and secret discipline**: PASS. The feature is local-first and
  explicitly excludes upload, MediaScribe, Langfuse content traces, and secrets
  in diagnostics.
- **Deletion truth and lifecycle accounting**: PASS. No new external lifecycle
  boundary is introduced; new metadata remains part of the local artifact.
- **Spec-driven delivery with testable gates**: PASS. Clarification is complete
  and this plan produces research, data model, contracts, and quickstart before
  checklist/tasks/analyze.

## Project Structure

### Documentation (this feature)

```text
specs/022-meeting-mute-truth/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── privacy-control-contract.md
│   ├── mute-truth-manifest-contract.md
│   ├── target-matrix-contract.md
│   └── desktop-limitation-copy-contract.md
├── checklists/
│   └── requirements.md
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
│       │   ├── CaptureControlView.swift
│       │   ├── CaptureSessionController.swift
│       │   ├── CaptureStatusItem.swift
│       │   ├── LocalRecordingManifestService.swift
│       │   ├── LocalRecordingWriter.swift
│       │   └── RecordingEvidenceService.swift
│       └── Diagnostics/
│           └── DiagnosticBundleService.swift
├── Shared/
│   ├── Sources/
│   │   ├── Diagnostics/DiagnosticRedactor.swift
│   │   └── Models/
│   │       ├── AudioModels.swift
│   │       ├── AudioStates.swift
│   │       └── MeetingMuteTruthModels.swift
│   └── Tests/
│       ├── CaptureControlTests.swift
│       ├── LocalRecordingManifestTests.swift
│       ├── MeetingMuteTruthTests.swift
│       ├── MeetingMuteTruthDiagnosticTests.swift
│       └── MeetingMuteTruthValidationTests.swift
└── Scripts/
    └── validate-meeting-mute-truth.sh
```

**Structure Decision**: Implement this slice inside the existing SwiftPM macOS
package. Add new shared metadata models under `apps/macos/Shared/Sources/Models`,
extend the existing capture/writer/manifest services under
`apps/macos/RecApp/Sources/Capture`, keep UI changes in the native desktop
capture controls, add tests under `apps/macos/Shared/Tests`, and add one
metadata-only validation script under `apps/macos/Scripts`.

## Complexity Tracking

No constitution violations or complexity exceptions are required.

## Phase 0 Research Summary

See [research.md](./research.md). Key decisions:

- Treat product-owned `2brain Pause`/`2brain Stop` as the only canonical MVP
  privacy truth source.
- Preserve recording timeline alignment by writing silence/redaction markers
  for local microphone intervals during `2brain Pause`, rather than implying
  third-party meeting-app mute support.
- Extend local manifest metadata with optional mute-truth fields; do not change
  backend upload/server contracts in this feature.
- Show limitation copy whenever meeting-app mute truth is unproven.
- Keep direct Zoom/browser/Telemost mute adapters out of scope until separate
  target-specific evidence exists.

## Phase 1 Design Summary

See:

- [data-model.md](./data-model.md)
- [contracts/privacy-control-contract.md](./contracts/privacy-control-contract.md)
- [contracts/mute-truth-manifest-contract.md](./contracts/mute-truth-manifest-contract.md)
- [contracts/target-matrix-contract.md](./contracts/target-matrix-contract.md)
- [contracts/desktop-limitation-copy-contract.md](./contracts/desktop-limitation-copy-contract.md)
- [quickstart.md](./quickstart.md)

## Post-Design Constitution Check

- **Capture-first MVP integrity**: PASS. Design uses existing native capture
  services and adds local sample suppression/metadata truth; no driver or
  third-party adapter dependency is introduced.
- **Visible consent and user control**: PASS. Pause/Resume/Stop states remain
  local and visible; Stop stays available during pause.
- **Data boundary and secret discipline**: PASS. Contracts forbid raw audio,
  transcript text, meeting content, secrets, signed URLs, and live paths in
  diagnostics or evidence.
- **Deletion truth and lifecycle accounting**: PASS. New mute-truth metadata is
  local artifact metadata and does not create a new external deletion boundary.
- **Spec-driven delivery with testable gates**: PASS. Research, data model,
  contracts, quickstart, and AGENTS plan reference are present for the next
  checklist/tasks/analyze stages.
