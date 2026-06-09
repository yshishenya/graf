# Scope Review

Feature: `025-system-audio-capture-pivot`

Final review is pending until permission, artifact, CPU, 30-minute, and
75-minute evidence gates pass. Blocked, failed, degraded, and not-tested rows
are not acceptance.

Final acceptance requires an explicit final review entry with the accepted
scope-review marker, a yes/no quickstart/contracts review result, and exact
evidence traceability across the required gates. Do not add the accepted marker
until permission, artifact, CPU, 30-minute, and 75-minute evidence gates have
all passed and the final review has been recorded.

Accepted final review entries must be recorded under a dedicated
`## Final Accepted Scope Review` section. That section must include exact
standalone lines for final acceptance, quickstart/contracts review, and
evidence traceability across `#307/T071`, `#308/T072`, `#309/T073`,
`#310/T074`, `#311/T075`, `#312/T076`, and `#313/T077`.

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

## 2026-06-08 CPU Gate Interim Update

- CPU sampler: improved. App PID matching now uses exact executable paths
  instead of broad command-line matching.
- Baseline diagnostic: added as evidence-only; it does not count as acceptance.
- Settled idle gate: passed in the current clean baseline with packaged app
  running (`maxCoreaudiodCpuPercent=0.00`, `maxAppHelperCpuPercent=0.10`).
- Quit gate: passed after terminating the packaged app, with no remaining app
  process.
- Still not accepted: active-recording and stop CPU gates remain untested and
  require a real controlled recording run.

## 2026-06-08 Packaged App Lifecycle Review

- Main-window lifecycle: improved. AppKit application state save/restore is
  disabled for the managed main-window path, and the main `2brain Rec` window is
  marked non-restorable.
- Runtime smoke: passed for packaged-app launch. CoreGraphics found one visible
  `2brain Rec` window at `720x620`, and AppLog recorded
  `app_main_window_presented reason=launch reused=false` plus
  `app_window_visibility_checked visibleWindowCount=1`.
- Log review: the previous stale AppKit restoration error
  `Unable to find className=(null)` did not recur on the fresh launch after the
  lifecycle fix. Remaining AppKit/AppIntents lines are OS framework noise and
  were not accompanied by app crash, hang, missing-window, or CPU evidence.
- CPU review: packaged-app idle and quit gates passed in the current baseline.
  Active-recording and stop CPU gates remain unaccepted until a real controlled
  recording run is executed.
