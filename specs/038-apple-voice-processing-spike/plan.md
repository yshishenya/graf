# Implementation Plan: Apple Voice Processing Spike

**Branch**: `038-apple-voice-processing-spike` | **Date**: 2026-06-22 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/038-apple-voice-processing-spike/spec.md`

## Summary

Evaluate Apple native voice processing as a bounded spike after the merged
`037` app-owned microphone graph. The implementation will add feature-gated
candidate evidence, validation contracts, and runtime/manual proof paths that
answer whether Apple processing can reduce built-in speaker-to-mic leakage while
feeding both live microphone behavior and persisted package truth. This feature
does not claim clean speakerphone recording unless built-in speakerphone,
lineage, leakage, double-talk, alignment, no-hang, and metadata-only gates all
pass.

## Technical Context

**Language/Version**: Swift 6.0 package, macOS-native SwiftUI/AppKit app,
existing Swift shared libraries under `apps/macos`, macOS 14 package baseline.

**Primary Dependencies**: Existing `037` app-owned microphone sample source,
AVFAudio/AudioToolbox Apple native voice-processing capabilities,
AVFoundation/CoreAudio route and microphone mode metadata, existing
`LocalRecordingWriter`, `LocalRecordingManifestService`,
`LeakageMeasurementService`, and diagnostic redaction models.

**Storage**: Existing local recording package and metadata-only evidence.
Original `mic.wav`, `incoming.wav`, and `manifest.json` remain authoritative.
Candidate processed evidence may be represented only as metadata or traceable
derived/candidate state until a later spec changes artifact semantics.

**Testing**: SwiftPM tests in `apps/macos` (`swift test`), contract tests for
spike result and manifest lineage, existing leakage finalization tests, existing
recording artifact validators, CPU/resource scripts, and manual controlled
runtime matrix evidence.

**Target Platform**: macOS 14+ on Apple Silicon for MVP validation.

**Project Type**: SwiftPM macOS desktop app with shared Swift libraries and
local recording pipeline.

**Performance Goals**:

- Preserve `025`/`037` package compatibility and `durationDifferenceSeconds <= 3`
  for accepted candidate runs.
- Stop/quit remains bounded and clears active capture state without hidden
  microphone processing.
- Candidate processing must not regress accepted CPU/no-hang gates; any
  unmeasured CPU/latency result remains unproven.
- Built-in speakerphone acceptance requires far-end-only, near-end-only,
  double-talk, loud speaker/clipping, route-change, alignment, and redaction
  gates to pass.

**Constraints**:

- Apple processing is a spike candidate, not a production claim.
- Existing `020` leakage finalization remains the authority for clean,
  leakage-detected, unproven, and not-measured package states.
- Original recording artifacts must remain traceable even if candidate processed
  evidence exists.
- System Mic Mode / Voice Isolation may be observed or guided only as
  user/system-controlled evidence unless the app can prove deterministic control
  for the exact route.
- Diagnostics remain metadata-only and must not include raw audio, transcript
  text, meeting content, credentials, tokens, signed URLs, passwords, live local
  paths, or participant identifiers.

**Scale/Scope**: Single-user local MVP recording spike; required route/scenario
matrix covers built-in mic/speakers, built-in mic/wired headphones, USB headset,
at least one browser meeting target, far-end-only, near-end-only, double-talk,
loud speaker/clipping, and route change. Bluetooth/AirPods evidence is optional
for the initial built-in speakerphone decision.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

- **Capture-first MVP integrity**: PASS. The feature builds on the accepted
  system-audio-first recording path and app-owned microphone graph without
  requiring virtual-driver routing for MVP acceptance.
- **Visible consent and user control**: PASS. Manual Record/Stop, visible
  active capture state, one-action Stop, and explicit route/permission truth are
  preserved for every candidate outcome.
- **Data boundary and secret discipline**: PASS. The design is local-first and
  metadata-only for diagnostics/evidence; no MediaScribe direct desktop egress,
  Langfuse content trace, raw audio evidence, or credentials are introduced.
- **Deletion truth and lifecycle accounting**: PASS. No accepted new content
  artifact is introduced by planning. If implementation creates derived
  candidate audio, tasks must register lifecycle and deletion semantics before
  it can be accepted.
- **Spec-driven delivery with testable gates**: PASS. Specification has no
  clarification markers; plan artifacts define research decisions, data model,
  contracts, quickstart, and measurable gates before tasks/implementation.

## Project Structure

### Documentation (this feature)

```text
specs/038-apple-voice-processing-spike/
|-- plan.md
|-- research.md
|-- data-model.md
|-- quickstart.md
|-- contracts/
|   |-- apple-processing-spike-contract.md
|   |-- recording-package-lineage-contract.md
|   `-- diagnostics-contract.md
`-- tasks.md
```

### Source Code (repository root)

```text
apps/macos/
|-- Package.swift
|-- RecApp/
|   `-- Sources/
|       |-- Capture/
|       |   |-- MicrophoneCaptureService.swift
|       |   |-- LocalRecordingWriter.swift
|       |   |-- LocalRecordingManifestService.swift
|       |   `-- RecordingEvidenceService.swift
|       `-- Diagnostics/
|           `-- DiagnosticBundleService.swift
`-- Shared/
    |-- Sources/
    |   |-- Models/
    |   |   |-- AudioModels.swift
    |   |   `-- SystemAudioCaptureModels.swift
    |   `-- Diagnostics/
    |       `-- DiagnosticRedactor.swift
    `-- Tests/
        |-- MicrophoneCaptureServiceTests.swift
        |-- LocalRecordingWriterSystemAudioTests.swift
        |-- LocalRecordingLeakageFinalizationTests.swift
        |-- DiagnosticRedactionTests.swift
        |-- LeakageDiagnosticBundleTests.swift
        `-- ContractTests/
```

**Structure Decision**: Implement within the existing SwiftPM macOS package and
extend the local recording/diagnostic evidence model rather than creating a new
package format. Candidate Apple processing code should be feature-gated and
proved through existing writer/manifest/leakage paths so `039` can reuse the
same evidence shape if Apple processing defers to WebRTC AEC3.

## Complexity Tracking

No constitution violations or complexity exceptions are required.

## Phase 0 Research Summary

See [research.md](./research.md). Key decisions:

- Evaluate Apple native processing as a bounded candidate, not as implicit
  clean-recording acceptance.
- Prefer the high-level app-owned audio graph path first; evaluate lower-level
  voice-processing I/O only if the high-level path cannot prove the needed
  route/lineage.
- Treat system Mic Modes as user/system-controlled guidance unless the exact
  2brain Rec route can prove deterministic app ownership.
- Preserve original package truth and use existing leakage finalization as the
  clean/not-clean authority.
- Defer to `039` when lineage, quality, stability, or route topology cannot be
  proven.

## Phase 1 Design Summary

See:

- [data-model.md](./data-model.md)
- [contracts/apple-processing-spike-contract.md](./contracts/apple-processing-spike-contract.md)
- [contracts/recording-package-lineage-contract.md](./contracts/recording-package-lineage-contract.md)
- [contracts/diagnostics-contract.md](./contracts/diagnostics-contract.md)
- [quickstart.md](./quickstart.md)

## Post-Design Constitution Check

- **Capture-first MVP integrity**: PASS. The design keeps the accepted local
  dual-track package and requires fail-closed Apple evidence before any clean
  speakerphone claim.
- **Visible consent and user control**: PASS. Candidate processing cannot hide
  active recording or remove one-action Stop.
- **Data boundary and secret discipline**: PASS. Contracts require metadata-only
  evidence and explicitly prohibit raw content/secrets.
- **Deletion truth and lifecycle accounting**: PASS. Original artifacts remain
  authoritative; any derived candidate artifact must be explicitly traceable and
  lifecycle-accounted before acceptance.
- **Spec-driven delivery with testable gates**: PASS. Design artifacts map to
  user stories, requirements, and success criteria; no unresolved `NEEDS
  CLARIFICATION` markers remain.
