# Implementation Plan: Desktop Cabinet Embedding

**Branch**: `033-desktop-cabinet-embedding` | **Date**: 2026-06-16 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/033-desktop-cabinet-embedding/spec.md`

## Summary

Embed the already accepted server-owned meeting review surface from feature
`016` inside the macOS app so the desktop product opens on the meeting value
loop: native recording/upload controls plus web-owned meeting list/detail. The
implementation adds a small SwiftUI desktop workspace, a bounded WebKit host,
route allow/deny policy, desktop cabinet configuration/state models, upload
queue review links, and validation evidence. It does not implement sharing,
downloads, deletion, retention, new auth providers, or new capture/upload
behavior.

## Technical Context

**Language/Version**: Swift 6 package targeting macOS 14 for the native app;
existing Python 3.13/FastAPI server remains unchanged except for validation of
existing `016` routes.

**Primary Dependencies**: SwiftUI for native shell layout, WebKit for the
embedded cabinet host, existing `TwoBrainRecAppCore` and `TwoBrainRecShared`
targets, existing FastAPI `016` cabinet routes.

**Storage**: Existing desktop upload queue JSON and local recording state only.
No new content-bearing storage is introduced. Server meeting/transcript data
continues to live in existing `016`/processing tables behind server auth/RLS.

**Testing**: `swift test --package-path apps/macos --disable-swift-testing`
with focused filters for desktop cabinet models, route policy, accessibility,
and upload review links; `swift build --package-path apps/macos -c release
--product TwoBrainRecApp`; existing server cabinet tests for route contract
regression when needed.

**Target Platform**: macOS desktop app on Apple Silicon for MVP. Browser
cabinet remains available separately; Windows/Linux shells are later platform
slices.

**Project Type**: SwiftPM macOS SwiftUI desktop app embedding a server-owned
web product surface.

**Performance Goals**: Desktop shell initializes the cabinet workspace without
blocking native capture controls. When the configured local server is reachable
and authorized, the embedded meetings route starts loading within 1 second and
shows a ready or bounded state within 3 seconds in local validation.

**Constraints**: Native capture indicator and one-action stop must remain
visible outside embedded content. Embedded content cannot start/stop recording,
change devices, recover permissions, purge local files, execute share/export/
delete/download, or expose credentials, tokens, signed URLs, raw audio, private
reference content, transcript text in logs, or live local filesystem paths.

**Scale/Scope**: One desktop meetings workspace, one embedded list route, one
embedded detail route, bounded unavailable/auth states, route policy, upload
item review action, screenshots/evidence for ready and unavailable states.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Gate | Status | Reason |
|------|--------|--------|
| Capture-first MVP integrity | PASS | Feature does not change capture, system audio, microphone, driver, local recording, or upload transport behavior. |
| Visible consent and user control | PASS | Native recording indicator, Record, Stop, and upload truth stay outside the embedded surface and remain authoritative. |
| Data boundary and secret discipline | PASS | WebKit host uses approved server routes only; docs/tasks require no tokens, signed URLs, secrets, raw audio, transcript logs, or live paths in UI/evidence. |
| Deletion truth and lifecycle accounting | PASS | Deletion/share/export/download remain out of scope or bounded future-gated destinations; no execution path is introduced. |
| Spec-driven delivery with testable gates | PASS | This plan creates research, data model, route/native contracts, quickstart, checklists, tasks, analyze, and implementation evidence. |
| Product/platform constraints | PASS | MacOS-native shell owns capture-critical surfaces while server/web owns variable post-meeting review UI, matching ADR 001 and feature 030/016 boundaries. |

## Project Structure

### Documentation (this feature)

```text
specs/033-desktop-cabinet-embedding/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── desktop-cabinet-route-contract.md
│   ├── desktop-native-shell-contract.md
│   └── desktop-cabinet-validation-contract.md
├── checklists/
│   ├── requirements.md
│   ├── ux.md
│   └── security.md
└── validation/
    ├── implementation-evidence.md
    └── screenshots/
```

### Source Code (repository root)

```text
apps/macos/
├── Package.swift
├── RecApp/
│   ├── App/
│   │   └── TwoBrainRecApp.swift
│   └── Sources/
│       ├── Cabinet/
│       │   ├── DesktopCabinetConfiguration.swift
│       │   ├── DesktopCabinetRoutePolicy.swift
│       │   ├── DesktopCabinetState.swift
│       │   ├── DesktopCabinetWorkspaceView.swift
│       │   └── EmbeddedCabinetWebView.swift
│       ├── Capture/
│       │   └── CaptureControlView.swift
│       └── Upload/
│           └── DesktopUploadQueueService.swift
└── Shared/
    └── Tests/
        ├── DesktopCabinetConfigurationTests.swift
        ├── DesktopCabinetRoutePolicyTests.swift
        ├── DesktopCabinetWorkspaceTests.swift
        ├── DesktopCabinetUploadLinkTests.swift
        └── AppControlAccessibilityTests.swift
```

**Structure Decision**: Add a focused `RecApp/Sources/Cabinet` module inside
the existing `TwoBrainRecAppCore` target. Keep WebKit/AppKit bridge code in
the app core target and keep the executable target as composition only. Do not
introduce a separate frontend build system or duplicate the `016` cabinet UI in
native Swift.

## Phase 0 Research

Research output is captured in [research.md](./research.md).

Resolved decisions:

- Use SwiftUI shell composition with a WebKit host instead of rebuilding the
  meeting dashboard natively.
- Add an explicit embedded route allowlist rather than trusting arbitrary
  in-page navigation.
- Derive cabinet base URL from existing desktop server configuration concepts
  and environment/UserDefaults in development without hard-coding secrets.
- Keep local upload queue review links optional and truth-preserving: only
  uploaded/server-identified items open review.
- Validate against V8/Krisp clean-room gates through sanitized screenshots and
  evidence, not committed private reference captures.

## Phase 1 Design

Design artifacts created by this plan:

- [data-model.md](./data-model.md): desktop cabinet configuration, state,
  route, and upload review link entities.
- [contracts/desktop-cabinet-route-contract.md](./contracts/desktop-cabinet-route-contract.md):
  route allowlist, blocked destinations, external handling, and forbidden
  capture/governance actions.
- [contracts/desktop-native-shell-contract.md](./contracts/desktop-native-shell-contract.md):
  native shell ownership for capture, upload, focus, and offline behavior.
- [contracts/desktop-cabinet-validation-contract.md](./contracts/desktop-cabinet-validation-contract.md):
  validation matrix for route policy, state, security, accessibility,
  screenshots, and reference alignment.
- [quickstart.md](./quickstart.md): runnable validation scenarios and expected
  evidence.

## Post-Design Constitution Check

| Gate | Status | Reason |
|------|--------|--------|
| Capture-first MVP integrity | PASS | Design explicitly excludes capture changes and preserves native shell ownership for active capture, Stop, permissions, and local diagnostics. |
| Visible consent and user control | PASS | Native controls remain visible/keyboard reachable and the WebKit host is not allowed to own or duplicate capture actions. |
| Data boundary and secret discipline | PASS | Contracts require route allowlist, no hard-coded secrets, no private screenshot commits, and content-safe logs/evidence. |
| Deletion truth and lifecycle accounting | PASS | Share/export/download/delete are blocked or future-gated destinations with no execution, matching `017`/`018` separation. |
| Spec-driven delivery with testable gates | PASS | Tasks will be story-scoped with tests before implementation and analyze before code. |
| Product/platform constraints | PASS | Server-owned review surface is reused inside the macOS-native shell; future platform shells can reuse contracts later. |

## Complexity Tracking

No constitution violations or complexity exceptions are required.
