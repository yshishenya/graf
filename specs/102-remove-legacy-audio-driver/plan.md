# Implementation Plan: Remove Legacy Separate Audio Driver

**Branch**: `102-remove-legacy-audio-driver` | **Date**: 2026-07-13 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from
`/specs/102-remove-legacy-audio-driver/spec.md`

## Summary

Retire the abandoned macOS HAL/virtual-device architecture completely while
preserving the accepted system-audio-first recording graph. The implementation
deletes the driver, shared-memory bridge, passthrough orchestration, driver-only
models/UI/tests/install flows, and stale active documentation. Mixed files are
adapted so the supported graph remains exactly:

```text
ScreenCaptureKit system audio ─┐
                              ├─> LocalRecordingWriter ─> original dual tracks + manifest
App-owned microphone source ──┘
```

The app-only installer remains. A read-only architecture guard prevents legacy
symbols and payloads from returning. Historical Spec Kit evidence remains as an
audit trail, and cleanup of an already installed proof bundle is documented as
a separate deliberate host operation rather than a build/test side effect.

## Technical Context

**Language/Version**: Swift 6 / SwiftPM, C/C++ legacy code being removed, POSIX
shell validators and packaging scripts, Markdown Spec Kit artifacts.

**Primary Dependencies**: Existing SwiftUI/AppKit application shell,
ScreenCaptureKit system-audio runtime, AVFoundation/Core Audio APIs used by the
app-owned microphone path, Foundation, existing local artifact writers. Remove
the `CShmHelpers` target; add no dependency.

**Storage**: Existing local recording directory and
`local-recording-manifest.v3` remain unchanged for current artifacts. Ephemeral
driver readiness/evidence models are removed. Historical files may still decode
with unknown removed JSON keys because synthesized `Decodable` ignores unknown
keys; no migration or rewrite of user recordings is required.

**Testing**: XCTest/SwiftPM, focused system-audio and microphone suites, app
build, app-only installer package inspection, shell architecture guard,
artifact-format validators, and `infra/scripts/ci-local.sh`.

**Risk / Validation Lane**: High-risk feature. The change removes a former
capture architecture and touches app start/stop eligibility, native audio
models, packaging, diagnostics, and validation. Full Spec Kit flow, capture and
architecture checklists, clean analyze, GitHub issue sync, focused regression
proof, and repository gate are required.

**Release Gate**: No deploy and no privileged host cleanup. Release publication,
production deployment, local HAL deletion, and `coreaudiod` restart require
separate explicit approval.

**Target Platform**: macOS 14+ desktop application and local `.pkg` builder;
repository validation also runs on the existing project CI hosts.

**Project Type**: Native macOS desktop application with SwiftPM libraries,
shell-based local packaging, and repository documentation/validation.

**Performance Goals**: Preserve the accepted current capture budgets and avoid
adding work to audio callbacks. App launch performs no driver bridge mapping or
passthrough startup. Recording levels continue to come from the active writer's
two app-owned sample sources.

**Constraints**: Do not change ScreenCaptureKit or microphone-source ownership,
dual-track artifact roles/formats, visible active state, one-action stop,
permission truth, metadata-only diagnostics, local custody, upload, or meeting
detection behavior. Do not install/uninstall components or restart privileged
services during build/test. Preserve unrelated worktree state. Introduce no
replacement routing layer.

**Scale/Scope**: One macOS package graph, one application composition root, the
former `AudioDriver` source tree, shared routing/model clusters, installer and
validator scripts, macOS tests/QA, active product docs, one ADR, and one
architecture finding. Historical `specs/` remain outside executable scope.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

**Before Phase 0**: PASS with high-risk gates.

- Capture-first MVP integrity: PASS with regression tasks. The accepted native
  system-audio and app-owned microphone graph is explicitly the keep boundary.
- Visible consent and control: PASS. Manual start/stop, persistent active state,
  and one-action Stop are protected by unchanged controller and focused tests.
- Data boundary and secret discipline: PASS. The change adds no egress and all
  evidence remains metadata-only.
- Deletion truth: PASS. Source removal is not represented as host uninstall;
  stale installed proof components have separate bounded guidance.
- Spec-driven delivery: PASS. Full specify, clarify, plan, checklist, tasks,
  analyze, issue sync, and implement flow is used.
- UI and brand distance: PASS. Obsolete controls are deleted; no replacement UI
  or external design is introduced.
- Ponytail form: PASS. Prefer deletion, reuse `LiveRecordingLevels`, retain the
  existing current capture graph, add no dependency or abstraction.

**After Phase 1 design**: PASS. The retirement contract separates executable
source, current capture, historical evidence, and host state. The data-model
decision removes required driver fields from ephemeral evidence while keeping
the current recording manifest contract. The quickstart requires before/after
focused proof and an app-only package-content assertion.

## Validation Plan

1. Preserve the baseline already observed on 2026-07-13: 62 selected tests
   covering `LocalRecordingWriterSystemAudioTests`,
   `SystemAudioCaptureServiceTests`, `MicrophoneCaptureServiceTests`,
   `RecordingPrerequisiteGateTests`, `SystemAudioRecordingPackageTests`, and
   `CaptureSessionSafetyTests` passed with zero failures.
2. Run the same suite after implementation and compare test count/intent; any
   removed driver-only cases are replaced only where a current invariant would
   otherwise lose coverage.
3. Run all remaining macOS SwiftPM tests and build `TwoBrainRecApp` in release
   mode to catch deleted-symbol and composition-root regressions.
4. Run the retained system-audio artifact, permission, CPU evidence, resource
   release, accessibility, and recording-format validators.
5. Build the local installer and inspect the distribution/package contents:
   exactly the desktop app component, no HAL path, driver bundle, driver choice,
   repair/rollback hook, or privileged audio-service restart.
6. Run the new read-only retirement guard across active roots with an explicit
   historical allowlist. The guard must not write evidence or mutate host state.
7. Run quickstart scenarios from [quickstart.md](./quickstart.md).
8. Run `infra/scripts/ci-local.sh` before closeout. This gate does not currently
   substitute for the direct macOS suite, so both are mandatory.
9. Do not run deploy, install, uninstall, or `coreaudiod` restart in this slice.

## Project Structure

### Documentation (this feature)

```text
specs/102-remove-legacy-audio-driver/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── current-recording-path.md
│   ├── local-proof-cleanup.md
│   └── retirement-boundary.md
├── checklists/
│   ├── requirements.md
│   ├── architecture.md
│   ├── audio-capture.md
│   └── packaging-safety.md
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
│       │   ├── LocalRecordingWriter.swift
│       │   ├── MicrophoneCaptureService.swift
│       │   ├── RecordingEvidenceService.swift
│       │   ├── RecordingPrerequisiteGate.swift
│       │   └── SystemAudioCaptureService.swift
│       └── Diagnostics/DiagnosticBundleService.swift
├── Shared/
│   ├── Sources/
│   │   ├── Models/AudioModels.swift
│   │   ├── Models/AudioStates.swift
│   │   └── Models/SystemAudioCaptureModels.swift
│   └── Tests/
├── Installer/Scripts/
│   ├── build-local-installer.sh
│   ├── install-user-app.sh
│   ├── uninstall.sh
│   └── update-preflight.sh
└── Scripts/
    ├── validate-foundation.sh
    ├── validate-system-audio-capture-pivot.sh
    └── validate-no-legacy-audio-driver.sh

tests/macos/
qa/macos/
docs/
├── adr/004-remove-legacy-separate-audio-driver.md
├── current-product-status.md
└── prd-voice-layer-final.md

CHANGELOG.md
AGENTS.md
```

Deleted clusters include `apps/macos/AudioDriver`, `Shared/CShmHelpers`,
`SharedAudioMemory`, passthrough/route orchestration, driver setup and route
health UI, driver installer hooks, driver-only validators/tests/QA, and their
obsolete contract fixtures.

**Structure Decision**: Keep the existing native app and SwiftPM layout. Adapt
mixed current files in place, delete legacy-only clusters, and retain one small
read-only negative guard. Do not create a replacement audio module.

## Complexity Tracking

No constitution violations.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| None | N/A | N/A |

## Ponytail Review

Completed on 2026-07-13 after the full removal diff was buildable. The result is
deletion-dominant: the current `ScreenCaptureKit` and app-owned microphone graph
is reused directly, `LiveRecordingLevels` replaces the deleted route-shaped
meter type, `CShmHelpers` is removed, and no dependency, bridge, routing layer,
or replacement abstraction is introduced. The only new runtime policy is the
small fail-closed `RecordingMicrophoneInputPolicy`, which preserves physical
input classification after the driver-specific guard is deleted.

The review removed one redundant `singleValueContainer()` decode from the
backward-compatibility initializer. No intentional shortcut with a known
ceiling remains, so no `ponytail:` code comment or upgrade path is required.
Any future advanced-routing work must enter as a separately specified and
validated architecture, not as an extension point left in this removal diff.
