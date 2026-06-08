# Scope Review

Feature: `025-system-audio-capture-pivot`

Final review is pending until permission, artifact, CPU, 30-minute, and
75-minute evidence gates pass. Blocked, failed, degraded, and not-tested rows
are not acceptance.

## 2026-06-08 Interim Review

- App launch/window: improved. The packaged app now uses an AppKit-managed main
  window and shows `visibleWindowCount=1` without the old fallback-window path.
- System-audio prerequisite truth: improved. Normal system-audio recording no
  longer needs a fake live-route `active` state; it uses explicit
  `system_audio_capture` route evidence.
- Build/contract: passed with `swift build --package-path apps/macos` and
  `swift run --package-path apps/macos ContractValidation`.
- XCTest: not accepted as executed in this environment. SwiftPM compiles the
  XCTest bundle, but full `xcrun xctest` execution is blocked by the active
  Command Line Tools developer path.
- CPU gate: not accepted. The app process stayed idle, but current
  `coreaudiod` baseline exceeded the idle threshold even after the app quit.
- Remaining blockers: #307/T071, #308/T072, #309/T073, #310/T074, #311/T075,
  and #313/T077 remain open.
