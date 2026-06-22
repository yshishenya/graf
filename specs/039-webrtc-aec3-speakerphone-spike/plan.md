# Implementation Plan: WebRTC AEC3 Speakerphone Spike

**Branch**: `039-webrtc-aec3-speakerphone-spike` | **Date**: 2026-06-22 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/039-webrtc-aec3-speakerphone-spike/spec.md`

## Summary

Evaluate WebRTC AEC3 as the next clean-recording candidate after `038` deferred
Apple processing. The implementation will add a feature-gated WebRTC AEC3
adapter boundary, metadata-only validation models, lab-grade corpus tooling,
controlled real-hardware proof rows, a declared acceptance-threshold profile,
reversible rollback state, and local app status copy. Original `mic.wav`,
`incoming.wav`, and `manifest.json` remain traceable and authoritative unless
the built-in Mac microphone plus built-in Mac speakers route passes all
immediate-promotion gates.

## Technical Context

**Language/Version**: Swift 6.0 package, macOS-native SwiftUI/AppKit app,
existing Swift shared libraries under `apps/macos`, C-family shim only if the
WebRTC dependency readiness gate passes.

**Primary Dependencies**: Existing `037` app-owned microphone sample graph,
`038` Apple candidate evidence patterns, `020` leakage finalization authority,
existing `LocalRecordingManifestService`, `RecordingEvidenceService`,
`DiagnosticBundleService`, `CaptureControlView`, SwiftPM test infrastructure,
and a feature-gated WebRTC AEC3 adapter. WebRTC source/package use is blocked
until license, patent-grant, packaging, signing, notarization, and binary-size
evidence are recorded.

**Storage**: Existing local recording package and metadata-only evidence.
Original `mic.wav`, `incoming.wav`, and `manifest.json` remain traceable.
AEC3 candidate output may be represented as metadata, derived-candidate
lineage, or a promoted built-in route state only after the lab-grade corpus,
full-file runs, controlled app recording, route scope, acceptance-threshold,
rollback, and app-status gates pass.

**Testing**: SwiftPM tests in `apps/macos` (`swift test`), contract tests,
metadata redaction tests, candidate outcome tests, app status copy tests,
corpus slicing/full-file validation tooling, controlled real-hardware manual
runtime matrix evidence, and final `infra/scripts/ci-local.sh`.

**Target Platform**: macOS 14+ on Apple Silicon for MVP validation.

**Project Type**: SwiftPM macOS desktop app with shared Swift libraries, local
recording pipeline, and optional native AEC shim.

**Performance Goals**:

- Preserve existing `025`/`037` package compatibility and current accepted
  track alignment tolerance.
- Process candidate evidence in 10 ms frame terms and record any unsupported
  sample-rate/channel conversions as blocked or unproven.
- Keep Stop/quit bounded; candidate processing cannot hide active capture or
  block one-action Stop.
- Avoid CPU/no-hang regressions against accepted local capture gates.
- Immediate promotion requires at least ten files per required scenario family,
  at least five slices per file, every full file, at least two 20 minute or
  longer full-file runs per scenario family, and controlled real-hardware app
  recording rows with 100% critical gate pass.
- Immediate promotion requires a versioned acceptance-threshold profile declared
  before validation begins; changing it invalidates affected promotion evidence
  until rerun.

**Constraints**:

- Built-in Mac microphone plus built-in Mac speakers is the only route that
  `039` may promote or claim.
- Non-built-in routes are supporting evidence only unless a later route-specific
  feature validates them.
- Existing `020` leakage finalization remains the authority for clean,
  leakage-detected, unproven, and not-measured package states until all
  immediate-promotion gates pass.
- Diagnostics, evidence, app statuses, issue comments, PR text, and release
  notes must not contain raw audio, transcript text, meeting content,
  credentials, signed URLs, private local paths, or private identifiers.
- WebRTC dependency readiness is a release gate, not an assumption.

**Scale/Scope**: Single-user local MVP recording spike for the built-in Mac
speakerphone route. The required validation matrix covers far-end-only leakage,
near-end-only local speech, double-talk, loud speaker/clipping,
route-change/timing stress, unsafe-reference negative controls, Stop/quit,
diagnostics, app status, rollback, and supporting non-built-in route evidence.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Capture-first MVP integrity**: PASS. The feature builds on the accepted
  system-audio-first path and app-owned microphone graph without requiring
  virtual-driver routing for MVP acceptance.
- **Visible consent and user control**: PASS. Active capture, one-action Stop,
  and local app statuses remain visible; AEC3 cannot hide capture or remove
  Stop.
- **Data boundary and secret discipline**: PASS. The design is local-first and
  metadata-only for committed evidence; no direct desktop MediaScribe egress,
  Langfuse content traces, raw audio evidence, or credentials are introduced.
- **Deletion truth and lifecycle accounting**: PASS. Original artifacts remain
  traceable. Any derived/promoted candidate semantics must preserve lineage and
  deletion accounting before affecting package readiness.
- **Spec-driven delivery with testable gates**: PASS. Specification has no
  clarification markers; plan artifacts define research decisions, data model,
  contracts, and quickstart before tasks/implementation.

## Project Structure

### Documentation (this feature)

```text
specs/039-webrtc-aec3-speakerphone-spike/
|-- plan.md
|-- research.md
|-- data-model.md
|-- quickstart.md
|-- contracts/
|   |-- app-status-contract.md
|   |-- diagnostics-contract.md
|   |-- recording-package-lineage-contract.md
|   `-- webrtc-aec3-spike-contract.md
`-- tasks.md
```

### Source Code (repository root)

```text
apps/macos/
|-- Package.swift
|-- RecApp/
|   `-- Sources/
|       |-- Capture/
|       |   |-- CaptureControlView.swift
|       |   |-- LocalRecordingManifestService.swift
|       |   |-- RecordingEvidenceService.swift
|       |   |-- WebRTCAEC3Adapter.swift
|       |   `-- WebRTCAEC3EvaluationService.swift
|       `-- Diagnostics/
|           `-- DiagnosticBundleService.swift
|-- Shared/
|   |-- Sources/
|   |   `-- Models/
|   |       `-- SystemAudioCaptureModels.swift
|   |-- Tests/
|   |   |-- WebRTCAEC3ModelsTests.swift
|   |   |-- WebRTCAEC3EvaluationTests.swift
|   |   |-- WebRTCAEC3ValidationCorpusTests.swift
|   |   |-- CaptureControlTests.swift
|   |   |-- LocalRecordingManifestTests.swift
|   |   |-- DiagnosticRedactionTests.swift
|   |   `-- ContractTests/
|   |       `-- WebRTCAEC3SpikeContractTests.swift
|   `-- Tools/
|       `-- WebRTCAEC3Validation/
|           `-- main.swift
`-- Scripts/
    `-- validate-webrtc-aec3-speakerphone-spike.sh
```

**Structure Decision**: Extend the existing SwiftPM macOS package and reuse the
`038` candidate evidence pattern. Add a WebRTC AEC3 adapter boundary rather
than coupling the recording graph directly to a native dependency. Keep
candidate evaluation, package lineage, app status, rollback, and diagnostics
testable even when the native WebRTC dependency is unavailable or blocked.

## Complexity Tracking

No constitution violations or complexity exceptions are required.

## Phase 0 Research Summary

See [research.md](./research.md). Key decisions:

- Use a feature-gated WebRTC AEC3 adapter boundary and fail closed when the
  dependency, render reference, call ordering, timing, or packaging evidence is
  unsafe.
- Treat AEC3 as candidate evidence until the lab-grade corpus, full-file,
  controlled real-hardware, route scope, acceptance-threshold, rollback, and
  app-status gates pass.
- Keep original package truth traceable and record promoted candidate state as
  reversible built-in-route state, not a silent rewrite.
- Surface candidate/problem/rollback/fallback-relevant states in the app with
  calm, metadata-safe status copy.
- Require licensing, patent-grant, packaging, signing, and notarization review
  before promoting any WebRTC dependency beyond spike evidence.

## Phase 1 Design Summary

See:

- [data-model.md](./data-model.md)
- [contracts/webrtc-aec3-spike-contract.md](./contracts/webrtc-aec3-spike-contract.md)
- [contracts/recording-package-lineage-contract.md](./contracts/recording-package-lineage-contract.md)
- [contracts/app-status-contract.md](./contracts/app-status-contract.md)
- [contracts/diagnostics-contract.md](./contracts/diagnostics-contract.md)
- [quickstart.md](./quickstart.md)

## Post-Design Constitution Check

- **Capture-first MVP integrity**: PASS. The design preserves the accepted local
  dual-track package and requires fail-closed AEC3 evidence before the built-in
  route can affect recording/transcription truth.
- **Visible consent and user control**: PASS. App statuses, active capture
  visibility, rollback state, and one-action Stop are explicit design artifacts.
- **Data boundary and secret discipline**: PASS. Contracts require
  metadata-only evidence and explicitly prohibit raw content, credentials,
  signed URLs, private paths, and meeting content.
- **Deletion truth and lifecycle accounting**: PASS. Original artifacts remain
  authoritative unless a reversible promoted route state passes gates; derived
  evidence remains labeled and traceable.
- **Spec-driven delivery with testable gates**: PASS. Design artifacts map to
  user stories, requirements, and success criteria; no unresolved `NEEDS
  CLARIFICATION` markers remain.
