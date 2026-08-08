# Feature Specification: Modernize macOS Application UI

**Feature Branch**: `144-macos-modernization`
**Created**: 2026-08-08
**Status**: Draft

## Goal
To continue the user interface overhaul started in `143-cabinet-modernization` by extending the modern, trustworthy, and consistent design language (glassmorphism, updated typography, deep bento-style rounded corners) to the native macOS application (SwiftUI). The native shell (`DesktopMeetingShellView.swift`) must visually harmonize with the web cabinet it encapsulates.

## Scope
1. Update `DesktopMeetingShellChrome` (in `apps/macos/RecApp/Sources/Cabinet/DesktopMeetingShellView.swift`) to use modern colors, corner radiuses, and potentially native Materials (like `.ultraThinMaterial`).
2. Update font styling in macOS native views (like `CaptureControlViewCore.swift` and `DesktopMeetingShellView.swift`) to match the new weight and feel of the web/landing fonts (e.g. relying on standard SF Pro but with tighter weights or rounded variants if applicable).
3. Ensure consistency in native UI elements (buttons, inputs, alerts, controls) avoiding flat `1px` borders, preferring soft shadows and refined contrast levels.

## Constraints
- **Do not break SwiftUI view functionality or accessibility identifiers**. Many elements are tightly coupled to the UI testing or accessibility layers.
- Do not introduce new massive third party dependencies. Use native SwiftUI styling and extensions.

## Execution Requirements
Follow the standard Spec Kit Flow for `144-macos-modernization` before writing code.
