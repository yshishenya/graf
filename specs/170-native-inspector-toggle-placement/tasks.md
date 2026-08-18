# Tasks: Нижний toggle native панели управления

**Input**: Design documents from `/specs/170-native-inspector-toggle-placement/`

**Risk lane**: `high-risk-feature`; user-facing macOS shell and accessibility.
No capture, permissions, signing or deploy changes.

## Phase 1: User Story 1 — Сворачивать native panel без поиска кнопки (P1)

**Independent Test**: Focused XCTest/source checks plus Computer Use visual
review of collapsed/expanded footer and two-toggle behavior.

- [X] T001 [P] [US1] Add focused source assertions for fixed footer, one toggle
  per mode, trailing alignment and 44px target in
  `apps/macos/Shared/Tests/DesktopMeetingShellWebViewBoundaryTests.swift` and
  `apps/macos/Shared/Tests/AppControlAccessibilityTests.swift`
- [X] T002 [US1] Move the expanded inspector disclosure control from the header
  into a fixed trailing-aligned footer in
  `apps/macos/RecApp/Sources/Cabinet/DesktopMeetingShellView.swift`

## Phase 2: Review and validation

- [X] T003 [US1] Run focused macOS tests/build and Computer Use visual review for
  collapsed, expanded, hover/focus and two-toggle states; record metadata-only
  evidence in `specs/170-native-inspector-toggle-placement/quickstart.md`

## Dependencies & Execution Order

T001 defines the source contract; T002 implements the smallest layout change;
T003 closes the story after build and visual validation.

## Implementation Strategy

Reuse `InspectorDisclosureButton`, existing state and width constants. Add only
the footer wrapper needed to keep the action fixed and trailing-aligned.
