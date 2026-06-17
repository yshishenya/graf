# Implementation Plan: App Zoom Shortcuts

**Branch**: `043-app-zoom-shortcuts` | **Date**: 2026-06-18 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/043-app-zoom-shortcuts/spec.md`

## Summary

Add standard macOS keyboard zoom commands for the embedded meeting workspace:
Command-Plus/Command-Equals increases zoom, Command-Minus decreases zoom, and
Command-0 resets to 100%. The implementation keeps zoom state in the macOS app
core, persists a bounded local preference, wires commands through the existing
AppKit application delegate/menu layer, passes the selected zoom into the
SwiftUI cabinet workspace, and applies it only to the embedded WebKit surface.
Native recording controls, upload truth, local audio readiness, backend routes,
and audio/processing flows remain unchanged.

## Technical Context

**Language/Version**: Swift 6 via `apps/macos/Package.swift`; macOS 14 target.

**Primary Dependencies**: SwiftUI, AppKit, WebKit, Foundation/UserDefaults,
XCTest. No new third-party dependencies.

**Storage**: One local desktop user preference for workspace zoom in
`UserDefaults`. No server storage or migrations.

**Testing**: SwiftPM XCTest in `apps/macos/Shared/Tests` with focused model,
persistence, menu-command, WebKit-bridge, and native-shell boundary coverage.

**Target Platform**: macOS desktop MVP app only.

**Project Type**: SwiftPM macOS desktop app with AppKit lifecycle, SwiftUI root
views, and an embedded WebKit meeting workspace.

**Performance Goals**: Zoom command handling is synchronous and local; applying
a new value must not reload the embedded route, perform network requests, or
touch recording/upload state.

**Constraints**:

- Zoom affects only the embedded meeting workspace surface.
- Native Record/Stop/upload truth/local audio readiness stays outside zoom.
- Existing Command-Shift-R recording shortcut and Escape stop shortcut remain
unchanged.
- No backend request, authorization header, upload, recording, deletion,
MediaScribe, Langfuse, MinIO, Postgres, Temporal, Docker, or deployment change.
- User-facing copy must stay clean-room/product-facing and avoid implementation
labels such as "web view".

**Scale/Scope**: One macOS app window and one embedded meeting workspace per
window. Preference is local to the desktop app user account.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Evidence |
|-----------|--------|----------|
| Capture-First MVP Integrity | PASS | Feature does not touch capture, permissions, routing, local recording, system audio, microphone capture, or driver behavior. |
| Visible Consent And User Control | PASS | Native visible indicator and one-action stop stay outside workspace zoom and receive explicit test coverage. |
| Data Boundary And Secret Discipline | PASS | Only a numeric local preference is stored; no secrets, headers, audio, transcripts, signed URLs, or diagnostics are persisted. |
| Deletion Truth And Lifecycle Accounting | PASS | Feature creates no meeting artifact and changes no retention/deletion behavior. |
| Spec-Driven Delivery With Testable Gates | PASS | Specify/clarify/plan/checklist/tasks/analyze/implement flow is used with exact validation commands. |
| Product And Platform Constraints | PASS | Implementation stays in the native macOS app stack and does not reintroduce virtual-driver requirements. |
| UI Brand-Distance | PASS | No external brand assets/copy are introduced; feature has no new visible product copy beyond system menu labels. |

No constitution violations are introduced.

## Project Structure

### Documentation (this feature)

```text
specs/043-app-zoom-shortcuts/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── embedded-workspace-zoom-contract.md
├── checklists/
│   ├── requirements.md
│   └── ux.md
└── tasks.md
```

### Source Code (repository root)

```text
apps/macos/RecApp/App/
└── TwoBrainRecApp.swift

apps/macos/RecApp/Sources/Cabinet/
├── DesktopCabinetState.swift
├── DesktopCabinetWorkspaceView.swift
├── EmbeddedCabinetWebView.swift
└── WorkspaceZoom.swift

apps/macos/Shared/Tests/
├── DesktopCabinetWorkspaceTests.swift
├── WorkspaceZoomTests.swift
└── EmbeddedCabinetWebViewZoomTests.swift

CHANGELOG.md
```

**Structure Decision**: Keep the feature in the existing macOS app core because
the current app already owns the desktop shell and embedded cabinet boundary.
Add one focused `WorkspaceZoom.swift` model/store file rather than broadening
the server or web cabinet. Use existing shared XCTest target for validation.

## Phase 0: Research

Research resolves feasibility of host-owned zoom for an embedded WebKit surface,
keyboard command ownership in the current AppKit lifecycle, preference bounds,
and testability without production cabinet data. Output:
[research.md](./research.md).

## Phase 1: Design And Contracts

- [data-model.md](./data-model.md) defines the local zoom preference, commands,
  supported range, and native-shell boundary state.
- [contracts/embedded-workspace-zoom-contract.md](./contracts/embedded-workspace-zoom-contract.md)
  defines observable behavior for shortcuts, clamping, persistence, reset, and
  non-interference with native controls.
- [quickstart.md](./quickstart.md) defines local validation commands and manual
  smoke coverage.

## Post-Design Constitution Check

| Principle | Status | Evidence |
|-----------|--------|----------|
| Capture-First MVP Integrity | PASS | Design leaves capture services and recording state untouched. |
| Visible Consent And User Control | PASS | Contract and tasks require native stop/indicator boundary tests. |
| Data Boundary And Secret Discipline | PASS | Data model stores only a bounded numeric local preference. |
| Deletion Truth And Lifecycle Accounting | PASS | No lifecycle artifact or deletion promise changes. |
| Spec-Driven Delivery With Testable Gates | PASS | Quickstart and tasks provide independent validation by story. |
| Product And Platform Constraints | PASS | Uses native macOS AppKit/SwiftUI/WebKit stack. |
| UI Brand-Distance | PASS | User-facing labels remain generic system zoom commands and do not mention competitor or implementation names. |

No complexity waivers are required.

## Complexity Tracking

No constitution violations or extra architectural complexity are introduced.
