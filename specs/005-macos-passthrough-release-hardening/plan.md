# Implementation Plan: macOS Passthrough Release Hardening

**Branch**: `005-macos-passthrough-release-hardening` | **Date**: 2026-06-01 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/005-macos-passthrough-release-hardening/spec.md`

## Summary

Harden the accepted macOS non-recording passthrough layer before adding local
recording. This slice focuses on automated and low-manual gates: installed
runtime proof, no-hang/CPU monitoring, route recovery, sleep/wake, installer
lifecycle regression, diagnostics redaction, UX truthfulness, and a deferred
recording-assisted long-call acceptance checklist. It explicitly does not add
recording, transcription, upload, MediaScribe, Langfuse, or new server
workflows.

The implementation approach is to extend the existing macOS validation harness,
QA artifacts, and app status surfaces. Any call usability check in this slice is
short smoke evidence only; full long-duration replay acceptance is blocked until
recording exists.

## Technical Context

**Language/Version**: Swift 6 for macOS app, app models, validation helpers, and
tests; C/C++17 for HAL proof/runtime tools; shell for installer and validation
harnesses; Markdown/JSON for evidence contracts.

**Primary Dependencies**: macOS Core Audio, AudioToolbox HAL Output Audio Unit,
AudioServerPlugIn HAL bundle, SwiftUI, Swift Package Manager,
pkgbuild/productbuild, POSIX shared memory, `ps`/`pgrep`/`open`/`osascript` or
equivalent local macOS commands for no-hang evidence.

**Storage**: Local metadata-only release-hardening evidence under repository QA
and test artifacts. No raw audio, meeting recording, transcript, upload,
MediaScribe, Langfuse, MinIO, Postgres, Temporal, or Docker storage is added.

**Testing**: Swift unit tests; C++ proof tools; existing runtime probe; static
realtime-safety check; installed app no-hang/CPU harness; route recovery
checklists or deterministic probes where possible; installer lifecycle
checklists; diagnostics redaction scans.

**Target Platform**: macOS 14.5+ on Apple Silicon, installed local package in
`/Applications`, built-in/wired physical input/output as release-quality route
targets.

**Project Type**: macOS desktop app plus HAL virtual audio component, local
installer scripts, shared route models, QA/evidence harnesses.

**Performance Goals**:

- `coreaudiod` idle/no-call CPU does not sustain above 10% for more than 30
  consecutive seconds while the app is open;
- macOS Sound settings and selected browser/meeting audio settings surfaces open
  within 5 seconds while the driver is installed and app is open;
- route changes and `coreaudiod` restart mark passthrough stale/degraded/blocked
  within 5 seconds or recover only after valid route evidence;
- installed runtime probe remains accepted with public virtual devices
  visible/alive and `running=0` when no Core Audio client is using them.

**Constraints**:

- no recording, transcription, upload, MediaScribe, Langfuse, or server
  workflow implementation in this slice;
- no long-duration manual call replay blocker before local recording exists;
- no no-driver fallback or customer-facing assisted capture automation;
- diagnostics and evidence are metadata-only by default;
- UI must distinguish non-recording passthrough from recording/capture states.

**Scale/Scope**: Internal macOS pilot hardening for 2brain Rec. Primary surfaces
are macOS Sound settings, Chrome audio settings, Opera audio settings, Zoom
audio settings, and Yandex Telemost audio settings. Yandex Browser can remain
skipped/not accepted if explicitly documented.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

### 2brain Rec Constitutional Gates

- **Driver-first capture integrity**: PASS. The slice directly hardens the
  driver-first macOS passthrough layer and preserves separate mic/speaker
  routing, no-loopback, fail-closed behavior, degraded states, and installer QA
  gates.
- **Visible consent and control**: PASS. The slice does not start recording or
  transcription. It improves clarity that passthrough can be active while
  recording is not.
- **Data boundary and secrets**: PASS. No new egress, MediaScribe, Langfuse,
  upload, credentials, or server-side processing are added.
- **Deletion truth and lifecycle accounting**: PASS. Evidence is metadata-only
  local QA material. Full recording-derived evidence is deferred to the future
  recording slice with its own retention/deletion rules.
- **Spec-driven delivery**: PASS. Specification and clarification are complete;
  plan/checklist/tasks/analyze remain required before implementation.
- **Brand-distance and accessibility**: PASS. Any UI copy/status changes must
  use original 2brain Rec language, keyboard-accessible states, non-color-only
  status, and localization-safe copy.
- **Operational readiness**: N/A for Docker/server storage. PASS for local
  installer, rollback, repair, diagnostics, no-hang, and recovery gates.

**Initial Gate Result**: PASS. No constitution violation; full manual
long-duration replay is intentionally deferred until recording exists.
**Post-Design Gate Result**: PASS. Phase 1 artifacts preserve local-only,
metadata-only, no-recording boundaries and define release-hardening evidence
without meeting-content artifacts.

## Project Structure

### Documentation (this feature)

```text
specs/005-macos-passthrough-release-hardening/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── release-hardening-evidence-contract.md
│   ├── no-hang-contract.md
│   └── deferred-recording-acceptance-contract.md
└── tasks.md
```

### Source Code (repository root)

```text
apps/macos/
├── RecApp/
│   ├── App/TwoBrainRecApp.swift
│   └── Sources/
│       ├── AudioHealth/
│       ├── AudioSetup/
│       ├── Capture/
│       └── Diagnostics/
├── AudioDriver/
│   ├── Makefile
│   └── Sources/Proof/
├── Installer/Scripts/
└── Scripts/

tests/macos/
├── browser-meetings/
├── contract/
├── installer-recovery/
├── physical-devices/
├── route-synthetic/
└── static/

qa/macos/
├── browser-targets.md
├── device-matrix.md
└── release-candidate-checklist.md
```

**Structure Decision**: Extend the existing macOS app/driver validation
structure. Add release-hardening evidence contracts and harness/checklist files
under `specs/005-*`, `tests/macos/`, `qa/macos/`, and `apps/macos/Scripts/`.
Do not introduce server services or storage components in this slice.

## Complexity Tracking

No constitution violations or complexity exceptions.
