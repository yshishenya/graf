# Implementation Plan: Нижний toggle native панели управления

**Branch**: `codex/168-cabinet-layout-polish` | **Date**: 2026-08-19 | **Spec**: [spec.md](spec.md)

## Summary

Разделить expanded inspector на scrollable content и fixed bottom footer.
Переместить существующий `InspectorDisclosureButton` из верхнего HStack в
footer и выровнять его по trailing edge, сохранив compact footer и все ARIA/
accessibility semantics.

## Technical Context

**Language/Version**: Swift 5.9+, SwiftUI, XCTest

**Primary Dependencies**: Existing macOS app shell; no new dependency

**Storage**: N/A

**Testing**: Focused XCTest/source accessibility checks, macOS build and
Computer Use visual review

**Risk / Validation Lane**: `high-risk-feature` — user-facing macOS shell and
accessibility geometry; capture semantics are intentionally unchanged

**Release Gate**: `no deploy`; public macOS release requires separate Developer
ID/notarization gate

**Target Platform**: macOS native AppKit/SwiftUI shell

**Project Type**: Desktop app

**Performance Goals**: No new state, observer or animation path

**Constraints**: Preserve 52px/308px widths, 44px target, reduced-motion
behavior, attention dismissal and settings action

**Scale/Scope**: One SwiftUI view and two focused XCTest source contracts

## Constitution Check

- Capture-First MVP Integrity: PASS — capture buttons and status are untouched.
- Visible Consent and User Control: PASS — recording Stop remains available.
- Privacy and secret discipline: PASS — no data or diagnostics added.
- UI/accessibility/clean-room: PASS — native target and labels remain explicit.
- Public macOS distribution: PASS — no packaging/signing/release artifact change.
- Spec-driven delivery: PASS — clarify, UX checklist, tasks, analyze and visual
  evidence are required.

## Validation Plan

1. Run focused Swift tests for geometry, identifiers and footer source markers.
2. Build the existing macOS target using the repository's narrow build path.
3. Launch installed GRAF/GRAF Dev with Computer Use and inspect collapsed,
   expanded, hover/focus and two-toggle states.
4. Run the combined fast lane after all web/native slices; no full CI here.

## Project Structure

```text
specs/170-native-inspector-toggle-placement/
├── spec.md
├── clarify.md
├── plan.md
├── research.md
├── data-model.md
├── contracts/native-inspector-toggle.md
├── checklists/requirements.md
├── checklists/ux.md
├── quickstart.md
└── tasks.md

apps/macos/RecApp/Sources/Cabinet/DesktopMeetingShellView.swift
apps/macos/Shared/Tests/DesktopMeetingShellWebViewBoundaryTests.swift
apps/macos/Shared/Tests/AppControlAccessibilityTests.swift
```

**Structure Decision**: Reuse the current `InspectorDisclosureButton` and make
the expanded inspector a VStack with scrollable content plus footer.

## Complexity Tracking

No violations. One footer wrapper is sufficient; no coordinator or new state.
