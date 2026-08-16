# Tasks: Feature 155

## Setup and regression tests

- [X] T001 [P] [US1] Add focused token and hit-area assertions in `apps/macos/Shared/Tests/AppControlAccessibilityTests.swift`.

## Native button styling

- [X] T002 [US1] Add the shared web-parity SwiftUI button style and web tokens in `apps/macos/RecApp/Sources/Cabinet/DesktopMeetingShellView.swift`.
- [X] T003 [US1] Apply the shared style and 32 px base control height to capture and shell buttons in `apps/macos/RecApp/Sources/Capture/CaptureControlViewCore.swift`, `apps/macos/RecApp/Sources/Capture/CaptureStatusItem.swift`, and `apps/macos/RecApp/Sources/Cabinet/DesktopMeetingShellView.swift`.
- [X] T004 [US1] Apply the shared style to native recovery, support, permission and settings button call sites in `apps/macos/RecApp/Sources/Cabinet/DesktopCabinetWorkspaceView.swift`, `apps/macos/RecApp/Sources/Upload/DesktopSupportIncidentActionStrip.swift`, `apps/macos/RecApp/Sources/Capture/DesktopPermissionOnboardingView.swift`, and `apps/macos/RecApp/Sources/MeetingDetection/MeetingDetectionSettingsView.swift`.

## Validation and closeout

- [X] T005 [US2] Update the UX checklist and changelog with the validated native/web button parity result.
- [X] T006 [US1] [US2] Run focused XCTest and the macOS product build under the local development lane; record manual dark/light theme evidence without secrets or meeting content. Defer repository-wide full CI to release/production validation per `docs/agent-guidance/release-and-validation.md`.
