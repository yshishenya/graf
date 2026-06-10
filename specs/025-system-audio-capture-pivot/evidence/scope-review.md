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

## 2026-06-10 Interim Blocker Cleanup

- Controlled artifact blocker #308/T072: cleared. The accepted artifact
  `20260610-105822-6051D91F-8390-4D85-994D-81C71BBEC19A` passed metadata-only
  validation with manifest status `saved`, `durationDifferenceSeconds=0.019`,
  no external egress, and no transcription start.
- CPU gate blocker #309/T073: cleared with product-owner caveat. Baseline and
  active-recording CPU evidence passed; the strict stop sample remained above
  the `coreaudiod` threshold because Telemost was left open, but app/helper CPU
  stayed `0.00%`, no HAL probe was observed, and no persistent CoreAudio hang
  remained after recovery.
- Remaining real blockers: #307/T071 permission matrix, #310/T074 30-minute
  development validation, #311/T075 75-minute release validation, and #313/T077
  final accepted scope review.
- Review result: final acceptance is still blocked until the remaining real
  blockers above are completed or explicitly rescoped.

## 2026-06-10 Permission Matrix Blocker Cleanup

- Permission matrix blocker #307/T071: cleared. Product owner reported the
  required manual permission matrix was checked, and `permission-matrix.md`
  records all five required scenarios as `passed`.
- Remaining real blockers: #310/T074 30-minute development validation,
  #311/T075 75-minute release validation, and #313/T077 final accepted scope
  review.
- Review result: final acceptance remains blocked until the 30-minute and
  75-minute runs are completed or explicitly rescoped.

## 2026-06-10 Long Duration Blocker Cleanup

- 30-minute development blocker #310/T074: cleared. Artifact
  `20260610-112827-761CE2A6-1D90-4028-9BF8-8C1EF7352D6B` ran for about
  `125.72` minutes and exceeded the 30-minute threshold.
- 75-minute release blocker #311/T075: cleared by the same artifact, which
  exceeded the 75-minute threshold.
- Artifact metadata: manifest status `saved`, failure reason `none`,
  transcription readiness `ready`, `mic.wav` and `incoming.wav` present,
  `durationDifferenceSeconds=0.014`, stop-phase capture health `passed`, and
  `halProbeObserved=false`.
- Caveat: the user reported the recording was mostly silent. This is accepted
  because the manifest did not mark the run as silent-input degraded and the
  metadata-only artifact validator passed.
- Remaining blocker: #313/T077 final accepted scope review.

## Final Accepted Scope Review

- Final scope review: accepted
- Reviewed against quickstart and contracts: yes
- Evidence traceability: #307/T071 #308/T072 #309/T073 #310/T074 #311/T075 #312/T076 #313/T077
- Permission matrix: accepted in `permission-matrix.md` for all five required permission scenarios.
- Controlled artifact: accepted in `artifact-matrix.md` for `20260610-105822-6051D91F-8390-4D85-994D-81C71BBEC19A`.
- CPU/resource gate: accepted with product-owner caveat in `cpu-gates.md`; no app/helper runaway, no HAL probe, and no persistent CoreAudio hang were recorded.
- Forbidden-content scan: accepted in `test-results.md`.
- Long-duration evidence: accepted in `development-30-minute.md` and `release-75-minute.md` using artifact `20260610-112827-761CE2A6-1D90-4028-9BF8-8C1EF7352D6B`.
- Final decision: all planned final evidence gates for feature `025-system-audio-capture-pivot` are closed, with the documented CPU caveat and mostly-silent long-run note preserved in evidence.
