# Implementation Plan: macOS Permission Retention And Relaunch Reliability

> Historical permission-retention fixture plan. Its local/self-signed signing
> material is not a publication path; current macOS release work belongs to
> [Feature 130](../130-developer-id-release/plan.md).

**Branch**: `095-macos-permission-retention` | **Date**: 2026-07-09 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/095-macos-permission-retention/spec.md`

## Summary

Stabilize GRAF's macOS permission identity so local reinstall/upgrade cycles do
not force the same user to grant microphone and Screen/System Audio access on
every build, and harden app termination so permission onboarding sheets cannot
block macOS quit/relaunch. The implementation remains macOS-native and
local-first for this historical fixture: support a free, locally trusted
self-signed code-signing identity for owner-machine validation. It does not
authorize publication. Current public Developer ID signing, installer signing,
notarization, stapling and Gatekeeper are owned by Feature 130.
Also reconcile the existing permission onboarding/termination hotfix under this
Spec Kit slice, with focused Swift tests and metadata-only installed-app
evidence.

## Technical Context

**Language/Version**: Swift Package Manager with Swift tools version 6.0,
macOS 14.5+ app target, POSIX shell installer scripts.

**Primary Dependencies**: SwiftUI/AppKit lifecycle, AVFoundation microphone
authorization, CoreGraphics Screen/System Audio authorization preflight/request
calls, ScreenCaptureKit system-audio capture surface, `codesign`, `security`,
`pkgbuild`, `productbuild`, `installer`, `osascript`, `sqlite3` read-only
permission inspection for local validation, and existing XCTest suites.

**Storage**: No product database changes. macOS TCC remains OS-owned storage;
the feature reads only bounded metadata for validation. Generated local
packages and certificates remain outside git.

**Testing**: Focused Swift tests for permission gate and termination/source
contract behavior; shell validation for build identity, designated requirement,
package install, launch, TCC permission states, no permission modal when
granted, and quit/relaunch under modal state; forbidden-content scans;
`infra/scripts/ci-local.sh` before closeout.

**Risk / Validation Lane**: High-risk feature. The slice touches macOS
microphone and Screen/System Audio permissions, installer/signing, capture
prerequisites, permission onboarding UX, termination/relaunch behavior, and
release-readiness claims.

**Release Gate**: No deploy and no public release may use this slice's local
signer. Local owner installer validation is historical fixture scope. Current
public Developer ID/notarization/stapling/Gatekeeper acceptance is the Feature
130 release lane.

**Target Platform**: macOS 14.5+ on the current owner/development machine for
local validation; future public distribution remains macOS.

**Project Type**: Native macOS desktop app and installer/build tooling.

**Performance Goals**: Permission checks and onboarding refresh must not add
visible launch delay when permissions are already granted. Termination cleanup
must reply within the existing 10-second bound. Signing metadata validation
must complete in seconds and must not run during active recording.

**Constraints**: Do not bypass TCC, automate hidden grants, reset TCC during
normal install, add MDM PPPC profiles, require HAL driver install, restart
CoreAudio for MVP permission retention, commit certificates/private keys, or
claim public distribution readiness without Developer ID signing and
notarization.

**Scale/Scope**: One macOS app bundle id (`pro.2brain.graf`), one local signing
continuity path, one installer/build script area, two permission classes
(microphone and Screen/System Audio), permission onboarding/termination UI, and
focused validation evidence. No server, upload, transcription, AI, storage, or
fleet deployment work.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

**Before Phase 0**: PASS with high-risk gates.

- Capture-first MVP integrity: PASS with required validation. The work supports
  the system-audio-first MVP permission prerequisite and does not change
  recording source selection, buffering, writer truth, or upload behavior.
- Visible consent and user control: PASS with required validation. Permission
  prompts remain explicit OS/user decisions. Manual Record/Stop and one-action
  Stop remain unchanged.
- Data boundary and secret discipline: PASS with required validation.
  Certificates, private keys, app-specific passwords, signed artifacts, raw
  audio, transcript text, private meeting content, and private user files must
  not be committed or copied into evidence.
- Deletion truth and lifecycle accounting: PASS. No meeting data or external
  deletion boundary is introduced.
- Spec-driven delivery: PASS. Full high-risk Spec Kit sequence is required:
  specify, clarify, plan, checklist, tasks, analyze, task-to-issues if
  implementation proceeds with GitHub issue sync, then implement.
- UI and brand distance: PASS. Permission onboarding remains native GRAF
  desktop UX; no public brand or landing surface is changed.
- Ponytail form: PASS. Reuse current SwiftUI/AppKit lifecycle, existing
  installer script, XCTest patterns, and native macOS tools. Do not add new
  runtime dependencies.

**After Phase 1 design**: PASS. Research and contracts keep the solution to
stable app identity, truthful local signing runbook, modal dismissal during
termination, metadata-only evidence, and explicit public-distribution
limitations. No HAL driver, server, or TCC-bypass work is introduced.

## Validation Plan

- Run static spec checks for unresolved clarification markers and stale feature
  references in `specs/095-macos-permission-retention`.
- Run focused Swift tests:

  ```sh
  swift test --package-path apps/macos --filter 'AppControlAccessibilityTests|SystemAudioPermissionGateTests|SystemAudioPermissionUXTests|InstallerLifecycleEvidenceTests'
  ```

- Run shell syntax checks for installer/signing scripts touched by the slice:

  ```sh
  sh -n apps/macos/Installer/Scripts/build-local-installer.sh
  sh -n apps/macos/Installer/Scripts/install-user-app.sh
  ```

- Build a local package with the accepted local signing identity and validate
  `codesign --verify --deep --strict`, `codesign -dv --verbose=4`, and
  `codesign -dr -` metadata.
- Install twice on the same Mac with the same signing continuity identity,
  launch `/Applications/GRAF.app`, and confirm microphone plus Screen/System
  Audio permission states stay granted without showing permission onboarding.
- Validate quit/relaunch while permission onboarding is visible or simulated:
  the app dismisses sheets, records metadata-only termination cleanup, and
  quits within the 10-second bound.
- Run forbidden-content scan over `specs/095-macos-permission-retention`,
  touched macOS scripts, touched Swift app/tests, and validation evidence.
- Run `infra/scripts/ci-local.sh` before closeout because the slice changes a
  high-risk desktop UX/code path and local release-readiness expectations.
- Do not run production CD dry-run/execute, notarization, or Developer ID
  release packaging in this slice.

## Project Structure

### Documentation (this feature)

```text
specs/095-macos-permission-retention/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── analysis.md
├── contracts/
│   ├── macos-app-identity-contract.md
│   ├── local-signing-runbook.md
│   └── termination-relaunch-contract.md
├── checklists/
│   ├── requirements.md
│   ├── audio-capture.md
│   ├── ux.md
│   └── installer-signing.md
├── validation/
│   └── implementation-evidence.md
└── tasks.md
```

### Source Code (repository root)

```text
apps/macos/
├── Installer/
│   ├── README.md
│   └── Scripts/
│       ├── build-local-installer.sh
│       └── install-user-app.sh
├── RecApp/
│   ├── App/TwoBrainRecApp.swift
│   └── Sources/Capture/
│       ├── DesktopPermissionOnboardingView.swift
│       ├── SystemAudioCaptureService.swift
│       └── SystemAudioPermissionGate.swift
└── Shared/Tests/
    ├── AppControlAccessibilityTests.swift
    ├── InstallerLifecycleEvidenceTests.swift
    ├── SystemAudioPermissionGateTests.swift
    └── SystemAudioPermissionUXTests.swift

CHANGELOG.md
AGENTS.md
```

**Structure Decision**: Keep implementation in the existing macOS package and
installer surfaces. The app lifecycle delegate and SwiftUI onboarding state own
modal dismissal and termination cleanup. The installer/build script and README
own local signing policy and package metadata. Tests stay in the existing
`TwoBrainRecSharedTests` target using the current source-inspection and model
test patterns where direct AppKit lifecycle automation is not available in
SwiftPM tests.

## Complexity Tracking

No constitution violations.

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| None | N/A | N/A |
