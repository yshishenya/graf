# Implementation Plan: Speaker-To-Mic Leakage Control

**Branch**: `codex/020-speaker-to-mic-leakage` | **Date**: 2026-06-04 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/020-speaker-to-mic-leakage/spec.md`

## Summary

This slice makes finalized recording packages truthful about speaker-to-mic
leakage. During the meeting the app continues to record evidence as-is and does
not ask the user to fix routes or run live leakage cleanup. After `Stop`,
package finalization evaluates saved `mic.wav`, `incoming.wav`, timeline
alignment, route metadata, and safe leakage metrics, then assigns a package
status: `clean`, `leakage_detected`, `unproven`, `not_measured`, or
`not_applicable`.

The first implementation path is finalization-time detection, evidence, and
transcription-readiness gating. Post-recording derived cleaned tracks are
allowed only as separate artifacts with lineage and residual-leakage evidence;
the original `mic.wav` and `incoming.wav` remain immutable evidence. Live Apple
voice processing, WebRTC AEC3, or mixed-audio architecture are planned as
bounded decision gates before any future claim that built-in speakerphone
recordings are clean. The explicit decision for this slice is no-go for clean
built-in speakerphone dual-track MVP claims, and go for truthful package
finalization that fails closed.

## Technical Context

**Language/Version**: Swift 6 package for macOS app/shared models/tests; C++17
for Core Audio HAL driver; Bash/Swift scripts for validation.

**Primary Dependencies**: Swift Foundation/AVFoundation/AVFAudio, Core Audio
HAL/AudioToolbox, existing shared-memory bridge, XCTest/Swift Testing through
SwiftPM, existing metadata redaction utilities.

**Storage**: Local recording package directory with `manifest.json`, `mic.wav`,
`incoming.wav`, optional derived cleaned track files, and metadata-only
finalization evidence. No server storage, upload, MediaScribe, Langfuse, or
network egress in this slice.

**Testing**: Swift package tests under `apps/macos/Shared/Tests`, contract
validation tool under `apps/macos/Shared/Tools/ContractValidation`, shell checks
under `apps/macos/Scripts` and `tests/macos/static`, plus controlled local audio
fixture/manual matrix validation.

**Target Platform**: macOS MVP on Apple Silicon with the existing 2brain Rec
virtual audio driver and desktop app.

**Project Type**: Native macOS desktop app plus Core Audio driver, with
repository-owned validation fixtures and contracts.

**Performance Goals**: Package finalization leakage analysis must run after
recording stop without blocking HAL/Core Audio realtime callbacks. For 020,
ordinary local packages up to 2 hours should finalize leakage metadata in under
60 seconds on Apple Silicon while keeping analysis memory under 256 MB through
windowed reads. Packages longer than 2 hours are outside the 020 timing
acceptance target; they must still use windowed reads, avoid unbounded memory
growth, and must not block recording stop, passthrough, or realtime audio paths.
Future live AEC spikes must define separate CPU and latency gates before
promotion.

**Constraints**: No live leakage cleanup in this feature. No user-facing route
readiness or recording-time leakage warnings. No raw audio, transcript text,
participant speech, secrets, signed URLs, live absolute user paths, or external
egress in diagnostics. No new HAL callback file IO, allocation, locks, logging,
network calls, process launches, UI work, or unbounded waits.

**Scale/Scope**: One macOS local recording package at a time. Required
validation matrix covers built-in mic/speakers, wired headphones, USB headset,
Bluetooth/AirPods-class devices, aggregate/multi-output routes, and at least one
supported browser/meeting target.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Gate | Status | Finding |
| --- | --- | --- |
| Driver-first capture integrity | Pass with scoped risk | The plan keeps the macOS virtual driver MVP and does not add a no-driver fallback. This slice does not claim live remote-to-mic prevention; it makes finalized package truth fail closed until a later live-processing or architecture gate proves clean output. |
| Visible consent and user control | Pass | Manual `Record`/`Stop`, visible recording indicator, and one-action stop remain unchanged. Leakage status appears only after finalization. |
| Data boundary and secrets | Pass | All new evidence is local and metadata-only. No MediaScribe, Langfuse, LLM, analytics, or external network dependency is added. |
| Deletion truth and lifecycle accounting | Pass | The feature adds local recording-quality metadata and optional derived artifacts. Derived artifacts must be registered in local retention/deletion accounting before they can be created or used. |
| Spec-driven delivery | Pass | Clarification is complete for planning. This plan creates research, data model, contracts, and quickstart; checklist/tasks/analyze remain required before implementation. |
| Realtime safety | Pass | Leakage analysis and derived cleanup run only after stop/finalization, outside HAL callbacks. Future live AEC spikes require a separate realtime-safety gate. |
| Clean-room/brand distance | Pass | Research relies on public OS/API docs, behavior-level category requirements, original code, or approved dependencies. No proprietary Krisp implementation, strings, assets, or binaries are used. |

**Scoped constitution tension**: The constitution says the virtual audio layer
must prevent loopback from remote audio into `2brain Rec Microphone`. The latest
clarification says this slice must not clean leakage during the live meeting.
This plan resolves the tension by limiting this feature to recording-package
truth, post-recording derived artifacts, and fail-closed transcription
readiness. It must not ship as a claim that live built-in speakerphone capture
is clean. A future plan must either prove live Apple/WebRTC/app-side clean
dual-track output or propose an alternative architecture before MVP can rely on
built-in speakerphone clean dual-track semantics.

## Project Structure

### Documentation (this feature)

```text
specs/020-speaker-to-mic-leakage/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── speakerphone-go-no-go.md
├── contracts/
│   ├── leakage-finalization-events.schema.json
│   └── local-recording-package-leakage.schema.json
├── checklists/
│   ├── driver.md
│   ├── finalization.md
│   ├── infra.md
│   ├── requirements.md
│   ├── security.md
│   ├── ux.md
│   └── validation.md
├── feasibility-research.md
├── problem-analysis.md
├── tasks.md
└── spec.md
```

### Source Code (repository root)

```text
apps/macos/
├── AudioDriver/
│   └── Sources/
│       ├── Bridge/
│       ├── Device/
│       └── Plugin/
├── RecApp/
│   └── Sources/
│       ├── Capture/
│       ├── Diagnostics/
│       └── AudioSetup/
├── Shared/
│   ├── Sources/
│   │   ├── Diagnostics/
│   │   └── Models/
│   ├── Tests/
│   └── Tools/ContractValidation/
└── Scripts/

tests/macos/
├── contract/
├── local-recording/
├── physical-devices/
├── route-synthetic/
└── static/
```

**Structure Decision**: Implement in the existing macOS app/shared-model
structure. Recording package models and finalization status belong in
`apps/macos/Shared/Sources/Models` and capture services in
`apps/macos/RecApp/Sources/Capture`. Metadata redaction remains in
`apps/macos/Shared/Sources/Diagnostics`. Validation fixtures stay under
`tests/macos/contract`, with static realtime checks under `tests/macos/static`.
No new backend, web service, database migration, or external service is part of
this feature.

## Implementation Approach

1. Extend the local recording manifest contract with package-level leakage
   finalization metadata, original evidence track status, optional derived track
   status, threshold version, timeline alignment evidence, measurement
   confidence, and safe failure reasons.
2. Add a finalization-time leakage evaluator that runs after `Stop`. It uses
   saved track metadata and safe audio-derived metrics, but writes only
   metadata-only evidence.
3. Preserve original `mic.wav` and `incoming.wav` as immutable evidence.
   Derived cleaned tracks may be created after recording, but must be labeled,
   linked to source tracks, and separately gated before transcription use.
4. Gate transcription readiness on timeline alignment, track completeness,
   leakage status, and derived residual-leakage status. `clean` is the only
   original-evidence status that can support clean dual-track readiness.
5. Remove leakage route readiness from this slice. Route facts are captured as
   metadata when available and never become recording-time blockers.
6. Add controlled validation fixtures and manual route matrix evidence for
   built-in speakerphone, headphones/headsets, Bluetooth/AirPods-class,
   aggregate/multi-output, and browser meeting target paths.
7. Record the explicit built-in speakerphone decision for this slice:
   `no_go_for_clean_builtin_speakerphone_mvp` and
   `go_for_truthful_finalization`. This means 020 may ship truthful package
   finalization, but it must not allow MVP logic to rely on built-in Mac
   microphone plus built-in speakers as clean live dual-track capture until a
   later Spec Kit slice proves live Apple/WebRTC/app-side processing or selects
   an alternative architecture.
8. Record Apple/macOS built-in voice-processing, WebRTC AEC3, post-recording
   cleanup, and mixed-audio fallback decisions as durable decision records, not
   implicit implementation dependencies for this finalization-only slice.

## Phase 0 Research Output

Research is captured in [research.md](research.md). It resolves the planning
unknowns for:

- finalization-only leakage analysis;
- leakage status decision rules;
- threshold versioning with initial `leakage-threshold.v1` numeric gates;
- original versus derived artifact truth;
- built-in speakerphone go/no-go for this slice;
- Apple built-in voice-processing spike states;
- WebRTC AEC3/custom AEC deferral;
- mixed-audio fallback decision-record conditions;
- metadata-only diagnostics and retention/deletion boundaries.

## Phase 1 Design Output

Design artifacts:

- [data-model.md](data-model.md)
- [contracts/local-recording-package-leakage.schema.json](contracts/local-recording-package-leakage.schema.json)
- [contracts/leakage-finalization-events.schema.json](contracts/leakage-finalization-events.schema.json)
- [quickstart.md](quickstart.md)
- [speakerphone-go-no-go.md](speakerphone-go-no-go.md)

## Post-Design Constitution Check

| Gate | Status | Finding |
| --- | --- | --- |
| Driver-first capture integrity | Pass with explicit follow-up | The design does not weaken driver-first recording. It prevents false clean/transcription-ready package claims now and requires a later live-processing or alternative-architecture decision before built-in speakerphone clean dual-track MVP acceptance. |
| Visible consent and user control | Pass | No hidden recording or live warning/remediation burden is introduced. |
| Data boundary and secrets | Pass | Contracts forbid content-bearing diagnostics, secrets, live paths, and external egress fields. |
| Deletion truth and lifecycle accounting | Pass | Derived artifacts are modeled as package artifacts and must participate in local purge/retention accounting in this slice before creation or transcription use. |
| Spec-driven delivery | Pass | No implementation begins until checklist, tasks, and analyze gates run. |
| Realtime safety | Pass | Contracts and quickstart include static checks to prove HAL callbacks stay free of unsafe work. |
| Clean-room/brand distance | Pass | Dependency decisions are documented at public API/behavior level only. |

## Complexity Tracking

No constitution violations require acceptance. The only scoped risk is that this
feature does not itself solve live speakerphone echo. The explicit decision for
020 is `no_go_for_clean_builtin_speakerphone_mvp` plus
`go_for_truthful_finalization`; a later live-processing or alternative
architecture plan is required before built-in speakerphone can be treated as
clean MVP dual-track capture.
