# Implementation Plan: Desktop UI Polish

**Branch**: `codex/054-desktop-ui-polish` | **Date**: 2026-06-26 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `specs/054-desktop-ui-polish/spec.md`

## Summary

Polish the 2brain Rec meeting list and shell chrome against the supplied KRISP clean-room reference: make the embedded list use the screen, tighten row density, keep sidebars useful, and preserve existing recording/upload/privacy truth. The implementation stays in the existing server-rendered cabinet HTML/CSS and SwiftUI shell constants.

## Technical Context

**Language/Version**: Python >=3.13 for server rendering/tests; Swift 6.0 package targeting macOS 14+ for shell constants/tests.

**Primary Dependencies**: Existing FastAPI/server-rendered cabinet, SwiftUI/AppKit/WebKit shell, existing pytest/XCTest coverage.

**Storage**: N/A for product data. Feature docs/evidence live under `specs/054-desktop-ui-polish/`.

**Testing**: Focused `pytest` for `test_cabinet_web_shell.py` and `test_cabinet_meeting_list.py`; focused `swift test` filters for `AppControlAccessibilityTests` and `DesktopCabinetWorkspaceTests`; existing browser verifier if practical.

**Target Platform**: macOS app embedded cabinet and standalone web cabinet at `https://rec.2brain.pro`.

**Project Type**: Hybrid server-rendered web cabinet plus macOS desktop shell.

**Performance Goals**: No new runtime fetches or client bundles; dense list stays pure HTML/CSS/SwiftUI layout.

**Constraints**: Preserve metadata-only evidence, Russian UI copy, visible capture/stop/upload truth, deletion truth copy, and brand distance from KRISP.

**Scale/Scope**: One UI polish slice covering meeting list, web sidebar, embedded workspace width, and native shell rail widths.

## Constitution Check

- **Capture-first MVP integrity**: PASS. No capture path changes.
- **Visible consent and user control**: PASS. Native capture controls remain visible and reachable.
- **Data boundary and secret discipline**: PASS. No new data egress or evidence with private content.
- **Deletion truth and lifecycle accounting**: PASS. Existing deletion truth copy remains unchanged.
- **Spec-driven delivery**: PASS. 054 has spec, plan, checklist, tasks, analyze, implementation, and validation.
- **Brand-distance UX**: PASS. KRISP is used only as clean-room layout reference.

## Project Structure

### Documentation

```text
specs/054-desktop-ui-polish/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── ui-polish-contract.md
├── checklists/
│   ├── requirements.md
│   └── ux.md
├── evidence/
│   └── validation-log.md
└── tasks.md
```

### Source Code

```text
apps/server/src/twobrain_rec_server/cabinet/web.py
apps/server/tests/unit/test_cabinet_web_shell.py
apps/server/tests/integration/test_cabinet_meeting_list.py
apps/macos/RecApp/Sources/Cabinet/DesktopMeetingShellView.swift
apps/macos/RecApp/Sources/Cabinet/DesktopCabinetWorkspaceView.swift
apps/macos/Shared/Tests/AppControlAccessibilityTests.swift
apps/macos/Shared/Tests/DesktopCabinetWorkspaceTests.swift
```

**Structure Decision**: Reuse existing rendering and shell files. No new component abstraction, dependency, or design-token layer.

## Phase 0: Research

See [research.md](./research.md).

## Phase 1: Design And Contracts

See [data-model.md](./data-model.md), [contracts/ui-polish-contract.md](./contracts/ui-polish-contract.md), and [quickstart.md](./quickstart.md).

## Post-Design Constitution Check

All initial constitution gates remain PASS. The planned edits are layout-only and keep capture, deletion, auth, and data boundaries untouched.

## Complexity Tracking

No constitution violations or extra architecture layers.
