# Implementation Plan: Паритет нативных кнопок с веб-частью

**Branch**: `codex/155-native-web-button-parity` | **Date**: 2026-08-16 | **Spec**: [spec.md](spec.md)

## Summary

Сделать нативные macOS-кнопки capture/shell/recovery визуально консистентными с
веб-кабинетом через один SwiftUI style path, повторяющий web button tokens:
32 px высота, 7 px radius, 12 px horizontal padding, blue primary и нейтральная
secondary surface. Действия и accessibility contracts остаются прежними.

## Technical Context

**Language/Version**: Swift 6 language mode, macOS 14+

**Primary Dependencies**: SwiftUI, AppKit, existing Swift Package Manager targets

**Storage**: N/A

**Testing**: XCTest source/contract checks, `swift test`, `swift build`

**Risk / Validation Lane**: `high-risk-feature` — user-facing native UX and
brand-distance surface; current development gate is local focused validation,
with repository-wide CI reserved for the PR/release boundary.

**Release Gate**: `no deploy` — local build and focused checks only.

**Target Platform**: macOS desktop application with embedded web cabinet

**Project Type**: native desktop app + embedded web UI

**Performance Goals**: no additional runtime work beyond SwiftUI style rendering

**Constraints**: preserve visible capture controls, one-action Stop,
accessibility, keyboard shortcuts, system-adaptive themes, no new dependencies

**Scale/Scope**: existing native button call sites in capture, shell recovery,
support strip, settings and permission/onboarding surfaces

## Constitution Check

- Capture-First MVP Integrity: PASS — only presentation/style code changes; no
  capture engine, routing, permission or recording lifecycle changes.
- Visible Consent And User Control: PASS — existing Record/Stop controls,
  shortcuts, indicators and hit areas remain present.
- UI / clean-room: PASS — native surface follows the repository's own web
  palette and spacing tokens; no third-party product styling is introduced.
- Spec-Driven Delivery: PASS — spec, research, UX checklist, tasks and
  consistency analysis are recorded before implementation.

## Validation Plan

1. Add focused XCTest contract assertions for the shared button tokens and
   preserved 40 px interactive target.
2. Run the relevant macOS test filter and build `TwoBrainRecApp`.
3. Do not run full repository CI during this local iteration. The repository
   guidance reserves the full lane for a release candidate/production
   validation; the fast lane remains the PR boundary when a PR is prepared.
4. Manually inspect dark/light theme rendering of primary, secondary,
   destructive, disabled and pressed states in the local app.

## Project Structure

```text
specs/155-native-web-button-parity/
├── spec.md
├── plan.md
├── research.md
├── quickstart.md
├── checklists/
│   ├── requirements.md
│   └── ux.md
└── tasks.md

apps/macos/RecApp/Sources/Cabinet/DesktopMeetingShellView.swift
apps/macos/RecApp/Sources/Cabinet/DesktopCabinetWorkspaceView.swift
apps/macos/RecApp/Sources/Capture/CaptureControlViewCore.swift
apps/macos/RecApp/Sources/Capture/CaptureStatusItem.swift
apps/macos/RecApp/Sources/Upload/DesktopSupportIncidentActionStrip.swift
apps/macos/RecApp/Sources/Capture/DesktopPermissionOnboardingView.swift
apps/macos/RecApp/Sources/MeetingDetection/MeetingDetectionSettingsView.swift
apps/macos/Shared/Tests/AppControlAccessibilityTests.swift
```

**Structure Decision**: переиспользовать один shared SwiftUI style и существующие
chrome constants; новый runtime module или dependency не создаётся.

## Complexity Tracking

Нет нарушений конституции, требующих исключения.
