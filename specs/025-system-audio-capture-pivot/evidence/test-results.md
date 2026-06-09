# Test Results

## 2026-06-08 Foundation Build

- Feature: `025-system-audio-capture-pivot`
- Scope: Phase 1 setup and Phase 2 foundational model/writer/contract changes
- Command: `swift build --package-path apps/macos`
- Result: passed
- Notes: This is a foundational build checkpoint only. It is not release
  acceptance and does not replace the later 30-minute development run,
  75-minute manual release run, CPU gate evidence, no-HAL evidence, permission
  matrix, or artifact matrix.

## 2026-06-08 US1 Service/Test Slice

- Feature: `025-system-audio-capture-pivot`
- Scope: US1 tests for system-audio service lifecycle with fake samples,
  microphone permission preflight, capture scope approval, and dual-source
  writer package generation.
- Commands:
  - `swift test --package-path apps/macos --disable-swift-testing`
  - `swift build --package-path apps/macos`
  - `swift run --package-path apps/macos ContractValidation`
- Result: passed
- Notes: This validates service seams and local package writing. Native
  ScreenCaptureKit runtime integration remains open under T023/#259.

## 2026-06-08 US2 Permission Gate Slice

- Feature: `025-system-audio-capture-pivot`
- Scope: Permission gate matrix, permission blocker copy, denied-permission
  manifest truth, app start blocker wiring, and local installer permission
  usage declarations.
- Commands:
  - `swift test --package-path apps/macos --disable-swift-testing`
  - `swift build --package-path apps/macos`
  - `swift run --package-path apps/macos ContractValidation`
- Result: passed
- Notes: This validates that missing microphone or Screen/System Audio
  permission cannot become a normal `saved` acceptance path. Manual permission
  toggling remains required in the later permission matrix validation task.

## 2026-06-08 US3 Artifact Truth Slice

- Feature: `025-system-audio-capture-pivot`
- Scope: Saved/aligned manifest truth, missing/silent/protected/dropped incoming
  failure reasons, duration alignment gate, capture health metadata, and safe
  local recording evidence.
- Commands:
  - `swift test --package-path apps/macos --disable-swift-testing`
  - `swift build --package-path apps/macos`
  - `swift run --package-path apps/macos ContractValidation`
- Result: passed
- Notes: This validates model and writer behavior. Manual controlled artifact
  validation remains required in the later artifact matrix validation task.

## 2026-06-08 US4 Runtime Stability Gate Slice

- Feature: `025-system-audio-capture-pivot`
- Scope: CPU gate model semantics, metadata-only CPU sampling script, no-HAL
  acceptance-path validation script, app-exit system-audio resource release,
  and CPU/no-HAL evidence templates.
- Commands:
  - `swift test --package-path apps/macos`
  - `swift build --package-path apps/macos`
  - `swift run --package-path apps/macos ContractValidation`
  - `./apps/macos/Scripts/validate-system-audio-no-hal-probe.sh`
  - `SYSTEM_AUDIO_CPU_GATE_SETTLE_SECONDS=0 SYSTEM_AUDIO_CPU_GATE_INTERVAL_SECONDS=1 ./apps/macos/Scripts/sample-system-audio-cpu-gate.sh idle`
- Result: passed
- Notes: CPU sampling was a fast metadata-only validation run. The active
  developer path is `/Library/Developer/CommandLineTools`, so `xcrun xctest`
  is unavailable even though SwiftPM compiles the XCTest bundle. This does not
  replace later settled idle/stop/quit checks, active recording checks,
  30-minute development run, 75-minute manual release run, or a full-Xcode
  XCTest execution.

## 2026-06-08 US5 Driver-Parked Slice

- Feature: `025-system-audio-capture-pivot`
- Scope: driver-parked readiness model, driver diagnostics UI copy, MVP summary
  language, future-driver README boundary, and driver-parked evidence template.
- Commands:
  - `swift test --package-path apps/macos`
  - `swift build --package-path apps/macos`
  - `swift run --package-path apps/macos ContractValidation`
  - `./apps/macos/Scripts/validate-system-audio-no-hal-probe.sh`
- Result: passed
- Notes: `swift test` compiles the XCTest bundle in the current
  CommandLineTools environment. Full `xcrun xctest` execution remains pending
  until full Xcode is selected.

## 2026-06-08 UX Accessibility And Localization Slice

- Feature: `025-system-audio-capture-pivot`
- Scope: shared localization-safe labels, stable accessibility identifiers,
  keyboard shortcuts for Record/Stop, long-path handling, fixed meter sizing,
  and compact text behavior in capture controls.
- Commands:
  - `swift test --package-path apps/macos`
  - `swift build --package-path apps/macos`
  - `swift run --package-path apps/macos ContractValidation`
  - `./apps/macos/Scripts/validate-system-audio-no-hal-probe.sh`
- Result: passed
- Notes: `swift test` compiles the XCTest bundle in the current
  CommandLineTools environment. Full `xcrun xctest` execution remains pending
  until full Xcode is selected.

## 2026-06-08 Final Automated Validation Slice

- Feature: `025-system-audio-capture-pivot`
- Scope: final automated build, SwiftPM test-bundle compile, contract
  validation, no-HAL validation, and forbidden-content scan.
- Commands:
  - `swift build --package-path apps/macos`
  - `swift test --package-path apps/macos`
  - `swift run --package-path apps/macos ContractValidation`
  - `./apps/macos/Scripts/validate-system-audio-no-hal-probe.sh`
  - `rg -n "rawAudio|transcriptText|meetingContent|signedUrl|password|apiKey|secret|token" specs/025-system-audio-capture-pivot apps/macos/Shared/Sources apps/macos/RecApp/Sources apps/macos/RecApp/App --glob '!**/.build/**'`
  - `rg -n "NEEDS CLARIFICATION|020-system-audio-capture-pivot|022-system-audio-capture-pivot" specs/025-system-audio-capture-pivot AGENTS.md docs .specify/memory/constitution.md`
- Result: passed for automated gates.
- XCTest runner note: active developer path is
  `/Library/Developer/CommandLineTools`; SwiftPM compiles the XCTest bundle, but
  full `xcrun xctest` execution remains pending until full Xcode is selected.
- Forbidden-content scan note: matches were limited to policy/quickstart
  wording, evidence safety instructions, and `DiagnosticRedactor` forbidden-key
  allowlist entries. No raw audio, transcript content, signed URLs, passwords,
  API keys, tokens, or secrets were found as payload data.
- Clarification/stale-feature scan note: matches were limited to quickstart
  command text and checklist statements that no clarification markers remain.
- Remaining gates not completed by this automated slice: permission matrix,
  controlled artifact validation, settled CPU gates for idle/active/stop/quit,
  30-minute development run, 75-minute manual release run, and final scope
  review.

## 2026-06-08 Packaged App Runtime Smoke

- Feature: `025-system-audio-capture-pivot`
- Scope: launch packaged `.app`, verify window visibility, launch logs, idle
  CPU/memory, and no obvious app log/system log errors.
- Package build:
  - `TWO_BRAIN_REC_ALLOW_ADHOC_APP_SIGNING=1 sh apps/macos/Installer/Scripts/build-local-installer.sh`
  - App bundle: `apps/macos/RecApp/.build/2brain Rec.app`
  - Local package: `apps/macos/.build/installer/2brain-rec-local.pkg`
- Runtime launch command:
  - `open -n "apps/macos/RecApp/.build/2brain Rec.app"`
- Window evidence:
  - `CGWindowListCopyWindowInfo` reported a visible content window named
    `2brain Rec`, size `900x652`, after the AppDelegate fallback check.
  - Window screenshot showed the first viewport with `Driver Diagnostics`,
    `Recording Status`, `Recording idle`, visible `Record System Audio`, and
    `Capture Audio` meters. The Record command is no longer below the first
    viewport.
- App log evidence from `~/Library/Logs/2brain Rec/2brain-rec.log`:
  - `passthrough_bridge_launch_available detail=non-recording route engine is available but not armed by launch check`
  - `app_opened summary=System audio recording is checked from Record; driver diagnostics are parked for MVP`
  - `passthrough_bridge_auto_start_skipped detail=automatic non-recording route engine disabled by default for safe launch`
  - `app_launch_finished detail=activationPolicy=regular`
  - `app_window_visibility_checked detail=visibleWindowCount=1`
- Idle resource evidence:
  - App process after launch: `0.1%` CPU, `0.3%` MEM, `113808` RSS.
  - `coreaudiod`: `0.0%` CPU during launch smoke.
  - `sample-system-audio-cpu-gate.sh idle`: passed with
    `maxCoreaudiodCpuPercent=0.00`, `maxAppHelperCpuPercent=4.20`; later samples
    settled to `0.10`.
- System log scan:
  - `log show --last 5m` for `2brain Rec` with error/fault/crash/hang/exception
    predicates returned no matching entries.
- Result: passed for packaged launch/idle smoke.
- Notes: This smoke proves launch/window/idle behavior only. It does not close
  permission matrix, controlled artifact validation, active/stop/quit CPU gate,
  30-minute development, or 75-minute release validation.

## 2026-06-08 AppKit Main Window And System-Audio Route Truth Review

- Feature: `025-system-audio-capture-pivot`
- Scope: packaged app launch stability, window visibility, idle CPU evidence,
  system-audio MVP prerequisite truth, and current XCTest/toolchain evidence.
- Code review fixes:
  - Replaced the SwiftUI `WindowGroup` launch path with an AppKit-managed main
    `NSWindow` hosting the existing SwiftUI content. This removes dependence on
    the previous fallback window path.
  - Added `system_audio_capture` as an explicit recording route evidence kind so
    the system-audio MVP no longer marks old live-route state as `active` just
    to satisfy the legacy route gate.
- Commands:
  - `swift build --package-path apps/macos`
  - `swift run --package-path apps/macos ContractValidation`
  - `swift test --package-path apps/macos`
  - `swift test --package-path apps/macos list`
  - `xcrun xctest apps/macos/.build/arm64-apple-macosx/debug/TwoBrainRecMacOSPackageTests.xctest`
  - `TWO_BRAIN_REC_ALLOW_ADHOC_APP_SIGNING=1 sh apps/macos/Installer/Scripts/build-local-installer.sh`
  - `open -n "apps/macos/RecApp/.build/2brain Rec.app"`
  - `apps/macos/Scripts/sample-system-audio-cpu-gate.sh idle`
  - `apps/macos/Scripts/validate-system-audio-no-hal-probe.sh`
- Build and contract result: passed.
- XCTest runner result: blocked by local toolchain. SwiftPM compiles and links
  `TwoBrainRecMacOSPackageTests.xctest`, but `swift test list` prints no test
  cases and `xcrun xctest` is unavailable under the active
  `/Library/Developer/CommandLineTools` developer path.
- Packaged runtime result:
  - App bundle launched successfully.
  - App process after 12 seconds: `0.0%` CPU, `0.3%` MEM, `96736` RSS.
  - AppLog showed `app_main_window_presented reason=launch reused=false` and
    `app_window_visibility_checked visibleWindowCount=1`.
  - `CGWindowListCopyWindowInfo` found a visible content window named
    `2brain Rec`; screenshot captured at `/tmp/twobrain-final-main-window.png`.
  - System log scan for crash/hang/exception/fault after launch returned no app
    crash or hang evidence. macOS still emits benign AppKit/state-restoration
    debug noise.
- CPU gate result:
  - A settled idle run at `2026-06-08T17:59:02Z` passed with
    `maxCoreaudiodCpuPercent=0.00` and `maxAppHelperCpuPercent=0.00`.
  - A later settled idle run at `2026-06-08T18:04:27Z` failed because
    `coreaudiod` stayed between `5.30%` and `5.70%` while app CPU was
    `0.00-0.10%`.
  - After terminating `2brain Rec`, `coreaudiod` remained above the gate
    (`5.9%` observed), so this is recorded as an external baseline blocker for
    #309/T073 rather than proof of app overheating.
- Result: partial pass. Launch/window/no-HAL/build/contract evidence improved,
  but #309/T073 remains open until idle baseline, active recording, stop, and
  quit CPU gates pass in the same validation environment.

## 2026-06-08 CPU Sampler PID Hardening Review

- Feature: `025-system-audio-capture-pivot`
- Scope: CPU gate evidence script PID matching, baseline diagnostics, packaged
  app idle/quit CPU smoke, and no-HAL regression.
- Code review fix:
  - Hardened `sample-system-audio-cpu-gate.sh` so app CPU is sampled only from
    the real packaged executable path or SwiftPM `TwoBrainRecApp` executable.
    This avoids false matches against shell commands that merely contain
    `2brain Rec` in their command text.
  - Added a diagnostic-only `baseline` phase. It records coreaudiod/app/helper
    CPU without counting as acceptance and without weakening idle/stop/quit or
    active-recording thresholds.
- Commands:
  - `sh -n apps/macos/Scripts/sample-system-audio-cpu-gate.sh`
  - `SYSTEM_AUDIO_CPU_GATE_SETTLE_SECONDS=0 SYSTEM_AUDIO_CPU_GATE_INTERVAL_SECONDS=1 apps/macos/Scripts/sample-system-audio-cpu-gate.sh baseline`
  - `SYSTEM_AUDIO_CPU_GATE_SETTLE_SECONDS=0 SYSTEM_AUDIO_CPU_GATE_INTERVAL_SECONDS=1 apps/macos/Scripts/sample-system-audio-cpu-gate.sh idle`
  - `TWO_BRAIN_REC_ALLOW_ADHOC_APP_SIGNING=1 sh apps/macos/Installer/Scripts/build-local-installer.sh`
  - `open -n "apps/macos/RecApp/.build/2brain Rec.app"`
  - `apps/macos/Scripts/sample-system-audio-cpu-gate.sh idle`
  - `apps/macos/Scripts/sample-system-audio-cpu-gate.sh quit`
  - `swift build --package-path apps/macos`
  - `swift run --package-path apps/macos ContractValidation`
  - `apps/macos/Scripts/validate-system-audio-no-hal-probe.sh`
- Result:
  - Baseline diagnostic passed as `observed` with app/helper `0.00%` while the
    app was not running.
  - Settled packaged-app idle gate passed at `2026-06-08T18:12:50Z` with
    `maxCoreaudiodCpuPercent=0.00` and `maxAppHelperCpuPercent=0.10`.
  - Quit gate passed at `2026-06-08T18:13:27Z` with no remaining app process
    and `maxCoreaudiodCpuPercent=0.00`.
  - Build, contract validation, and no-HAL validation passed.
- Remaining CPU evidence gap: #309/T073 is still open because active-recording
  and stop gates require a real controlled recording run; they are not accepted
  by idle/quit evidence alone.

## 2026-06-08 Artifact Directory Validator Self-Test

- Feature: `025-system-audio-capture-pivot`
- Scope: metadata-only validation of a completed local recording directory.
- Code review fix:
  - Added `validate-system-audio-capture-pivot.sh --artifact-directory <path>`.
  - The validator checks `manifest.json`, `mic.wav`, `incoming.wav`, saved
    dual-track status, `remoteSpeaker` source `systemAudio`, granted
    permissions, scope approval, no external egress, no transcription,
    diagnostic-safe metadata, and `durationDifferenceSeconds <= 3`.
  - Added `SYSTEM_AUDIO_CAPTURE_PIVOT_NO_APPEND=1` so synthetic self-tests do
    not pollute real artifact evidence.
- Commands:
  - positive synthetic artifact:
    `SYSTEM_AUDIO_CAPTURE_PIVOT_NO_APPEND=1 apps/macos/Scripts/validate-system-audio-capture-pivot.sh --artifact-directory <tmpdir>`
  - negative synthetic artifact with wrong incoming `sourceKind`:
    `SYSTEM_AUDIO_CAPTURE_PIVOT_NO_APPEND=1 apps/macos/Scripts/validate-system-audio-capture-pivot.sh --artifact-directory <tmpdir>`
- Result:
  - Positive synthetic artifact passed.
  - Negative synthetic artifact returned `blocked` with finding:
    `remoteSpeaker track must be saved systemAudio wav-pcm-s16le metadata`.
- Notes: This is validator tooling evidence only. It does not close #308/T072
  until a real controlled recording artifact is validated.

## 2026-06-08 Packaged App Lifecycle Smoke

- Feature: `025-system-audio-capture-pivot`
- Scope: packaged app launch responsiveness, AppKit window lifecycle, idle/quit
  CPU, and no-HAL regression after review.
- Code review fix:
  - Disabled AppKit application state save/restore for the managed main-window
    app lifecycle.
  - Marked the managed `2brain Rec` main window as non-restorable.
  - This removes the stale restored-window failure path from launch logs while
    keeping the explicit AppKit-managed window path.
- Commands:
  - `swift build --package-path apps/macos`
  - `swift test --package-path apps/macos`
  - `swift run --package-path apps/macos ContractValidation`
  - `apps/macos/Scripts/validate-system-audio-no-hal-probe.sh`
  - `TWO_BRAIN_REC_ALLOW_ADHOC_APP_SIGNING=1 sh apps/macos/Installer/Scripts/build-local-installer.sh`
  - `open -n "apps/macos/RecApp/.build/2brain Rec.app"`
  - CoreGraphics window-list check for owner `2brain Rec`
  - `apps/macos/Scripts/sample-system-audio-cpu-gate.sh idle`
  - `apps/macos/Scripts/sample-system-audio-cpu-gate.sh quit`
- Result:
  - Packaged app launched with process `2brain Rec`.
  - CoreGraphics found a visible window named `2brain Rec` at `720x620`.
  - App log showed `app_main_window_presented reason=launch reused=false` and
    `app_window_visibility_checked visibleWindowCount=1`.
  - Unified log no longer showed the previous stale restoration error
    `Unable to find className=(null)` for the fresh launch.
  - Idle CPU gate passed at `2026-06-08T18:34:46Z` with
    `maxCoreaudiodCpuPercent=0.00` and `maxAppHelperCpuPercent=0.10`.
  - Quit CPU gate passed at `2026-06-08T18:36:39Z` with no remaining app
    process and `maxCoreaudiodCpuPercent=0.00`.
  - `swift test` still only compiled the test bundle in this local Command Line
    Tools environment; it is not counted as full XCTest execution.
- Notes: #309/T073 remains open because active-recording and stop CPU evidence
  still require a real controlled recording run.

## 2026-06-08 Final Evidence CPU Gate Hardening

- Feature: `025-system-audio-capture-pivot`
- Scope: `validate-system-audio-capture-pivot.sh --review-evidence`.
- Code review fix:
  - Final evidence review now requires explicit latest `status=passed`
    evaluations for all accepted CPU phases: `idle`, `activeRecording`, `stop`,
    and `quit`.
  - `baseline` remains diagnostic-only and cannot satisfy acceptance.
  - Mere mention of phase names in evidence text can no longer satisfy the CPU
    gate.
- Synthetic self-tests:
  - Missing `activeRecording` and `stop` CPU evaluations returned
    `system_audio_capture_pivot_validation=blocked` with explicit missing-phase
    findings.
  - A later failed `activeRecording` evaluation blocked final review even when
    an older passed `activeRecording` entry existed.
  - A synthetic complete set with latest `idle`, `activeRecording`, `stop`, and
    `quit` evaluations all `status=passed` returned
    `system_audio_capture_pivot_validation=passed`.
- Notes: This hardens #313/T077. It does not close #309/T073; real
  active-recording and stop CPU evidence is still required.

## 2026-06-08 Recorder Meter Visibility Review

- Feature: `025-system-audio-capture-pivot`
- Scope: idle UI clarity for microphone and incoming/system-audio indicators.
- Code review fix:
  - Renamed the capture meter section to `Recorder Input Meters` so users know
    the indicators represent audio reaching the recorder, not only selected
    hardware devices.
  - Changed idle copy to `Meters show audio only while recording`.
  - Laid out `Microphone` and `Incoming` meters side by side so the incoming
    system-audio indicator is visible in the main packaged-app window without
    needing to infer it is below the fold.
  - Compacted equalizer bars so both channels show labels, state, bars, and
    waiting copy in the visible meter region.
  - Updated permission blocker copy to say `retry recording` instead of sending
    users back to the readiness check.
- Commands:
  - `swift build --package-path apps/macos`
  - `swift test --package-path apps/macos`
  - `swift run --package-path apps/macos ContractValidation`
  - `TWO_BRAIN_REC_ALLOW_ADHOC_APP_SIGNING=1 sh apps/macos/Installer/Scripts/build-local-installer.sh`
  - `open -n "apps/macos/RecApp/.build/2brain Rec.app"`
  - Packaged app window screenshot:
    `/tmp/twobrain-app-window-meter-layout2.png`
  - `apps/macos/Scripts/sample-system-audio-cpu-gate.sh idle`
  - `apps/macos/Scripts/sample-system-audio-cpu-gate.sh quit`
- Result:
  - Packaged app launched and displayed both `Microphone` and `Incoming`
    recorder meters in the main window.
  - Idle CPU gate passed at `2026-06-08T18:47:31Z` with
    `maxCoreaudiodCpuPercent=0.00` and `maxAppHelperCpuPercent=0.10`.
  - Quit CPU gate passed at `2026-06-08T18:54:41Z` with no remaining app
    process and `maxCoreaudiodCpuPercent=0.00`.
  - `swift test` still only compiled the test bundle in this local Command Line
    Tools environment; it is not counted as full XCTest execution.

## 2026-06-08 Recorder Meter Source Wiring Review

- Feature: `025-system-audio-capture-pivot`
- Scope: live meter source correctness during system-audio recording.
- Code review finding:
  - The UI meter section was visible, but its live data path still preferred
    the older passthrough/shared-memory route monitor.
  - That could make the `Incoming` meter stay silent during the system-audio
    MVP path even when `incoming.wav` was being fed by the local recording
    writer.
- Code review fix:
  - During local recording, `TwoBrainRecApp` now maps
    `LocalRecordingWriter.currentLevels()` into the meter model.
  - This means `Microphone` and `Incoming` meters reflect the recorder path that
    writes `mic.wav` and `incoming.wav`, not the parked virtual-device route.
  - The passthrough monitor remains only as a diagnostic fallback when the old
    route engine is explicitly active and local recording is not running.
- Test coverage:
  - Added a `LocalRecordingWriterSystemAudioTests` assertion that an independent
    incoming/system-audio sample source produces a live incoming recorder level.
- Commands:
  - `swift build --package-path apps/macos`
  - `swift test --package-path apps/macos`
  - `swift run --package-path apps/macos ContractValidation`
  - `apps/macos/Scripts/validate-system-audio-no-hal-probe.sh`
  - `TWO_BRAIN_REC_ALLOW_ADHOC_APP_SIGNING=1 sh apps/macos/Installer/Scripts/build-local-installer.sh`
  - `open -n "apps/macos/RecApp/.build/2brain Rec.app"`
  - Packaged app window screenshot:
    `/tmp/twobrain-app-window-recorder-level-wiring.png`
  - `apps/macos/Scripts/sample-system-audio-cpu-gate.sh idle`
  - `apps/macos/Scripts/sample-system-audio-cpu-gate.sh quit`
- Result:
  - Packaged app launched and showed the recorder meter section.
  - Idle CPU gate passed at `2026-06-08T19:10:50Z` with
    `maxCoreaudiodCpuPercent=0.00` and `maxAppHelperCpuPercent=0.10`.
  - Quit CPU gate passed at `2026-06-08T19:11:31Z` with no remaining app
    process and `maxCoreaudiodCpuPercent=0.00`.
- Notes: Real moving meter validation still requires a controlled recording
  with actual microphone and system audio. That remains part of #308/#309.

## 2026-06-08 System-Audio Runtime Frame Truth Review

- Feature: `025-system-audio-capture-pivot`
- Scope: system-audio service session truth when ScreenCaptureKit writes samples
  directly to the buffered recording source.
- Code review finding:
  - `SystemAudioCaptureService.appendIncomingSamples(...)` updated
    `SystemAudioCaptureSession.frameCount`, but the default ScreenCaptureKit
    runtime writes samples directly into `BufferedLocalRecordingSampleSource`.
  - That meant the local writer could receive frames for `incoming.wav` while
    the service-level session could still finalize with `frameCount=0` and a
    false `noFrames`/`stoppedBeforeFrames` reason.
- Code review fix:
  - `BufferedLocalRecordingSampleSource` now records total appended frames and
    latest append timestamp.
  - `SystemAudioCaptureService.stop(...)` and `releaseForTermination(...)` merge
    that buffered runtime stat into the final `SystemAudioCaptureSession`.
  - Runtime-direct samples and actor-appended samples now produce the same frame
    truth.
- Test coverage:
  - Added service stop coverage for samples that bypass actor append and arrive
    through the shared buffered runtime source.
  - Added termination-release coverage to prove app exit preserves buffered
    frame truth instead of marking `stoppedBeforeFrames`.
- Commands:
  - `swift build --package-path apps/macos`
  - `swift test --package-path apps/macos`
  - `swift run --package-path apps/macos ContractValidation`
  - `apps/macos/Scripts/validate-system-audio-no-hal-probe.sh`
  - `TWO_BRAIN_REC_ALLOW_ADHOC_APP_SIGNING=1 sh apps/macos/Installer/Scripts/build-local-installer.sh`
  - `open -n "apps/macos/RecApp/.build/2brain Rec.app"`
  - `apps/macos/Scripts/sample-system-audio-cpu-gate.sh idle`
  - `apps/macos/Scripts/sample-system-audio-cpu-gate.sh quit`
- Result:
  - Build, test bundle compilation, contract validation, and no-HAL validation
    passed.
  - Packaged app launched with visible `2brain Rec` window in CoreGraphics and
    AppLog `visibleWindowCount=1`.
  - Idle CPU gate passed at `2026-06-08T19:19:09Z` with
    `maxCoreaudiodCpuPercent=0.00` and `maxAppHelperCpuPercent=0.10`.
  - Quit CPU gate passed at `2026-06-08T19:20:10Z` with no remaining app
    process and `maxCoreaudiodCpuPercent=0.00`.
- Notes: Real accepted artifact validation still requires a controlled recording
  run and `--artifact-directory` against the produced directory.

## 2026-06-08 Recording Manifest Metadata Propagation Review

- Feature: `025-system-audio-capture-pivot`
- Scope: real local recording manifest fields required by
  `validate-system-audio-capture-pivot.sh --artifact-directory`.
- Code review finding:
  - `startManualRecording` created a real `CaptureScopeApproval` and
    `SystemAudioPermissionSnapshot`, but `LocalRecordingWriter.stop()` did not
    pass them into `LocalRecordingManifestService`.
  - A real `manifest.json` could therefore miss `scopeApproval` and
    `permissions`, even though the start gate had evaluated them.
- Code review fix:
  - `LocalRecordingWriter.start(...)` now accepts optional `scopeApproval` and
    `permissions` metadata and stores them for finalization.
  - `LocalRecordingWriter.stop(...)` passes that metadata into the written
    manifest.
  - `TwoBrainRecApp.startManualRecording()` now supplies the actual approved
    scope and permission snapshot from the accepted recording start.
- Test coverage:
  - Updated the dual-source package test to assert that writer-produced
    manifests preserve `scopeApproval`, microphone permission, and system-audio
    permission metadata.
- Commands:
  - `swift build --package-path apps/macos`
  - `swift test --package-path apps/macos`
  - attempted direct test-bundle execution:
    `apps/macos/.build/arm64-apple-macosx/debug/TwoBrainRecMacOSPackageTests.xctest/Contents/MacOS/TwoBrainRecMacOSPackageTests`
  - `swift run --package-path apps/macos ContractValidation`
  - `apps/macos/Scripts/validate-system-audio-no-hal-probe.sh`
  - `apps/macos/Scripts/validate-system-audio-capture-pivot.sh --review-evidence`
  - `TWO_BRAIN_REC_ALLOW_ADHOC_APP_SIGNING=1 sh apps/macos/Installer/Scripts/build-local-installer.sh`
  - `open -n "apps/macos/RecApp/.build/2brain Rec.app"`
  - `apps/macos/Scripts/sample-system-audio-cpu-gate.sh idle`
  - `apps/macos/Scripts/sample-system-audio-cpu-gate.sh quit`
- Result:
  - Build, test bundle compilation, contract validation, and no-HAL validation
    passed.
  - Direct test-bundle execution is still not available in this local CLT
    environment: the `.xctest` Mach-O bundle returned `exec format error`
    without an XCTest runner.
  - Final evidence review remained correctly blocked because manual permission,
    artifact, active/stop CPU, 30-minute, and 75-minute gates are still open.
  - Packaged app launched with visible `2brain Rec` window.
  - Idle CPU gate passed at `2026-06-08T19:29:12Z` with
    `maxCoreaudiodCpuPercent=0.00` and `maxAppHelperCpuPercent=0.10`.
  - Quit CPU gate passed at `2026-06-08T19:29:58Z` with no remaining app
    process and `maxCoreaudiodCpuPercent=0.00`.
- Notes: Real artifact acceptance still requires a controlled recording and
  `--artifact-directory` against the produced directory.

## 2026-06-08 Latest Artifact Helper Review

- Feature: `025-system-audio-capture-pivot`
- Scope: metadata-only helper flow for #308/T072 controlled artifact validation.
- Code review finding:
  - The manual run procedure asked the tester to inspect the newest directory
    under `~/Library/Application Support/2brain Rec/Recordings/` and paste the
    selected directory ID into `--artifact-directory`.
  - That created an avoidable risk of validating a stale or partial recording
    package during the controlled run.
- Code review fix:
  - Added `validate-system-audio-capture-pivot.sh --latest-artifact-directory`
    to print the newest completed local recording directory containing
    `manifest.json`, `mic.wav`, and `incoming.wav`.
  - Added `--validate-latest-artifact` to validate that newest completed
    package through the same strict metadata-only contract as
    `--artifact-directory`.
  - Added `TWO_BRAIN_REC_RECORDINGS_DIR` override so the helper can be
    self-tested against temporary directories without reading real user
    recordings.
  - Updated `quickstart.md` and `artifact-matrix.md` to use the helper in the
    controlled run procedure.
- Synthetic self-tests:
  - A newer partial directory was ignored; the helper selected the newest
    completed directory and validation passed.
  - A newer completed but invalid directory was selected and validation returned
    `blocked` for `durationDifferenceSeconds must be <= 3`, proving the helper
    does not silently fall back to an older valid package.
- Notes: This removes a manual selection hazard for #308/T072. It does not
  close #308/T072 because the accepted artifact still requires a real controlled
  recording run.

## 2026-06-08 Quit CPU Gate Process-Truth Review

- Feature: `025-system-audio-capture-pivot`
- Scope: #309/T073 quit CPU gate correctness.
- Code review finding:
  - `sample-system-audio-cpu-gate.sh quit` evaluated only CPU thresholds.
  - A still-running `2brain Rec` process with `0.00%` CPU could therefore
    produce `status=passed`, even though the quit gate requires the app/helper
    process to be gone after the settle window.
- Code review fix:
  - Added `appProcessCount` and `helperProcessCount` to each CPU sample line.
  - Added `maxAppProcessCount` and `maxHelperProcessCount` to the evaluation
    summary.
  - `quit` now fails with `failureReason=appStillRunning` when either count is
    non-zero after the settle window, even if CPU usage is low.
- Runtime proof:
  - With the packaged app still running, `quit` returned `status=failed
    failureReason=appStillRunning ... maxAppProcessCount=1`.
  - After quitting the app, `quit` returned `status=passed failureReason=none
    ... maxAppProcessCount=0 maxHelperProcessCount=0`.
- Additional checks:
  - Packaged app launch still showed one visible `2brain Rec` window via
    CoreGraphics.
  - Idle CPU stayed below gate with `maxCoreaudiodCpuPercent=0.00` and
    `maxAppHelperCpuPercent=0.00`.
  - AppLog showed `app_launch_finished`, `app_main_window_presented`,
    `app_window_visibility_checked visibleWindowCount=1`, and
    `passthrough_bridge_auto_start_skipped`.
- Notes: This hardens #309/T073 and #313/T077. #309 remains open because
  accepted active-recording and stop CPU gates still require a real controlled
  recording run.

## 2026-06-08 App Exit Recording Finalization Review

- Feature: `025-system-audio-capture-pivot`
- Scope: local recording finalization when the user quits the app during an
  active recording.
- Code review finding:
  - `willTerminateNotification` and `onDisappear` scheduled
    `Task { await releaseCaptureResourcesForAppExit() }`.
  - macOS can terminate the process before that async task finishes, which
    could leave `mic.wav`, `incoming.wav`, or `manifest.json` incomplete during
    an app-quit path.
- Code review fix:
  - Local recording finalization now happens synchronously in
    `finalizeLocalRecordingForAppExit()` before the async system-audio runtime
    release is scheduled.
  - `releaseSystemAudioForAppExit()` still releases the ScreenCaptureKit runtime
    asynchronously, but WAV/manifest finalization no longer depends on that
    async task being scheduled before process exit.
- Runtime checks after fix:
  - `swift build --package-path apps/macos` passed.
  - `swift test --package-path apps/macos` completed in the local SwiftPM
    runner.
  - `swift run --package-path apps/macos ContractValidation` passed.
  - `apps/macos/Scripts/validate-system-audio-no-hal-probe.sh` passed.
  - Packaged app launched and CoreGraphics found `window_count=1`.
  - Idle CPU passed with `maxCoreaudiodCpuPercent=0.00` and
    `maxAppHelperCpuPercent=0.10`.
  - Quit CPU passed with `maxAppProcessCount=0` and
    `maxHelperProcessCount=0`.
- Notes: Real proof that app-exit finalization saves a controlled active
  recording still belongs to #308/#309 controlled recording validation.

## 2026-06-08 Stop-Time Incoming Buffer Drain Review

- Feature: `025-system-audio-capture-pivot`
- Scope: incoming/system-audio tail preservation at Stop.
- Code review finding:
  - `LocalRecordingWriter.stop()` canceled the writer timer and closed WAV
    writers without first draining samples already buffered in the incoming
    `LocalRecordingSampleSource`.
  - If ScreenCaptureKit appended system-audio frames immediately before Stop,
    those frames could remain in the buffer and never reach `incoming.wav`,
    creating avoidable track-size/duration skew.
- Code review fix:
  - Added a synchronous stop-time drain for microphone sample sources and
    incoming/system-audio sample sources before WAV close and manifest
    finalization.
  - Added regression coverage where incoming samples are appended after
    `start()` and immediately before `stop()`; the manifest now reports
    incoming frames instead of `noFrames`.
- Validation:
  - `swift build --package-path apps/macos` passed.
  - `swift test --package-path apps/macos` completed in the local SwiftPM
    runner.
  - `swift run --package-path apps/macos ContractValidation` passed.
  - `apps/macos/Scripts/validate-system-audio-no-hal-probe.sh` passed.
  - Packaged app launched and CoreGraphics found `window_count=1`.
  - Idle CPU passed with `maxCoreaudiodCpuPercent=0.00` and
    `maxAppHelperCpuPercent=0.00`.
  - Quit CPU passed with `maxAppProcessCount=0` and
    `maxHelperProcessCount=0`.
- Notes: This directly addresses the observed risk of `mic.wav` and
  `incoming.wav` size skew at Stop. Real accepted artifact proof still requires
  #308 controlled recording validation.

## 2026-06-08 Terminate-Later Cleanup Review

- Feature: `025-system-audio-capture-pivot`
- Scope: app termination ordering for active recording cleanup.
- Code review finding:
  - A synchronous local writer finalization in `willTerminateNotification`
    protects the manifest from async scheduling loss, but it still runs after
    AppKit has already decided to terminate and cannot reliably wait for the
    async ScreenCaptureKit/system-audio runtime release.
  - It also risks closing `incoming.wav` before the runtime has stopped
    appending the final buffered system-audio frames.
- Code review fix:
  - `AppLifecycleDelegate.applicationShouldTerminate` now returns
    `terminateLater` and posts an internal cleanup notification.
  - `ContentView` awaits `systemAudioCaptureService.releaseForTermination()`
    first, then synchronously finalizes local WAV/manifest output, then signals
    cleanup completion back to the delegate.
  - The delegate replies to AppKit only after cleanup completes, with a
    defensive timeout fallback.
- Runtime proof:
  - Packaged app launched and CoreGraphics found `window_count=1`.
  - Idle CPU passed with `maxCoreaudiodCpuPercent=0.00` and
    `maxAppHelperCpuPercent=0.10`.
  - AppLog recorded `app_termination_cleanup_requested reply=terminateLater`
    followed by `app_termination_cleanup_completed reason=cleanup_finished`.
  - Quit CPU passed with `maxAppProcessCount=0` and
    `maxHelperProcessCount=0`.
- Notes: This makes the app-exit cleanup order match the normal Stop order:
  stop system-audio runtime first, then close local recording artifacts.

## 2026-06-08 Incoming Timeline Padding Review

- Feature: `025-system-audio-capture-pivot`
- Scope: intermittent incoming/system-audio alignment against continuous
  microphone recording.
- Code review finding:
  - `incoming.wav` grew only when incoming/system-audio samples were delivered,
    while `mic.wav` records against the wall-clock recording duration.
  - During pauses or batched system-audio delivery, `incoming.wav` could become
    shorter than the recording timeline even when some incoming audio was
    captured, creating avoidable duration and file-size skew.
- Code review fix:
  - After draining pending samples at Stop, the writer pads silence up to the
    elapsed recording timeline for tracks that already received frames.
  - A true no-frames incoming case remains `noFrames` and is not converted into
    a false saved track.
  - Added regression coverage proving an intermittent incoming source is padded
    to roughly the recording duration and does not become `timelineMisaligned`.
- Validation:
  - `swift build --package-path apps/macos` passed.
  - `swift test --package-path apps/macos` completed in the local SwiftPM
    runner.
  - `swift run --package-path apps/macos ContractValidation` passed.
  - `apps/macos/Scripts/validate-system-audio-no-hal-probe.sh` passed.
  - Packaged app launched and CoreGraphics found `window_count=1`.
  - Idle CPU passed with `maxCoreaudiodCpuPercent=0.00` and
    `maxAppHelperCpuPercent=0.10`.
  - Quit CPU passed with `maxAppProcessCount=0` and
    `maxHelperProcessCount=0`.
- Notes: This directly reduces file-size/duration skew for recordings with
  intermittent incoming audio. Real accepted artifact proof still requires #308.

## 2026-06-08 Microphone Permission Request Review

- Feature: `025-system-audio-capture-pivot`
- Scope: user-visible permission behavior before recording.
- Code review finding:
  - `startManualRecording()` used microphone `preflight()` only.
  - On a fresh install, `.notDetermined` microphone permission could therefore
    be presented as a blocker telling the user to go to System Settings instead
    of showing the native macOS microphone prompt when the user presses Record.
- Code review fix:
  - `startManualRecording()` now calls
    `requestPermissionAndPreflight(...)` for microphone permission.
  - This keeps launch/readiness non-invasive, but makes Record trigger the
    native microphone permission path when needed.
  - Added test coverage for the microphone request/preflight path.
- Validation:
  - `swift build --package-path apps/macos` passed.
  - `swift test --package-path apps/macos` completed in the local SwiftPM
    runner.
  - `swift run --package-path apps/macos ContractValidation` passed.
  - `apps/macos/Scripts/validate-system-audio-no-hal-probe.sh` passed.
  - Packaged app launched and CoreGraphics found `window_count=1`.
  - Idle CPU passed with `maxCoreaudiodCpuPercent=0.00` and
    `maxAppHelperCpuPercent=0.10`.
  - Quit CPU passed with `maxAppProcessCount=0` and
    `maxHelperProcessCount=0`.
- Notes: Screen/System Audio remains preflighted until ScreenCaptureKit start,
  so launch still does not start recording or request permissions silently.

## 2026-06-08 Legacy Route Check Parked For MVP UI

- Feature: `025-system-audio-capture-pivot`
- Scope: remove old readiness/route-check prompts from the MVP recording UI
  path while keeping explicit recording permission checks on `Record`.
- Code review finding:
  - The visible `Run Check` action still started the old
    `PassthroughRouteEngine` route verification path.
  - That path belongs to the previous virtual route/driver flow and is not
    required for the system-audio MVP.
  - Keeping it in the first-run UI could confuse validation because meters are
    expected to become live only when recording starts, and it could reintroduce
    route/hang risk outside the explicit recording path.
- Code review fix:
  - Renamed the panel to `Recording Status` and the action to
    `Refresh Status`.
  - `Refresh Status` now performs a metadata-only local audio refresh and no
    longer starts the passthrough route engine.
  - Removed MVP recovery copy that told users to repair the audio driver or run
    the readiness check again.
  - Updated adaptive recovery labels to use status refresh wording instead of
    readiness-check wording.
- Validation:
  - `rg -n "Run Check|Readiness Check|Not ready for calls yet|Run the readiness check again|Install or repair the audio driver" apps/macos/RecApp apps/macos/Shared/Tests || true`
    returned no matches in the app code after the fix.
  - `swift build --package-path apps/macos` passed.
  - `swift test --package-path apps/macos` built and linked
    `TwoBrainRecMacOSPackageTests`; this Command Line Tools environment did
    not emit full XCTest execution details for this run.
  - `swift run --package-path apps/macos ContractValidation` passed.
  - `apps/macos/Scripts/validate-system-audio-no-hal-probe.sh` passed with
    `checkedFiles=7`.
  - `TWO_BRAIN_REC_ALLOW_ADHOC_APP_SIGNING=1 sh apps/macos/Installer/Scripts/build-local-installer.sh`
    produced `apps/macos/RecApp/.build/2brain Rec.app` and
    `apps/macos/.build/installer/2brain-rec-local.pkg`.
  - Packaged app launch produced one visible `2brain Rec` window.
  - `apps/macos/Scripts/sample-system-audio-cpu-gate.sh idle` passed with
    `maxCoreaudiodCpuPercent=0.00` and `maxAppHelperCpuPercent=0.10`.
  - `SYSTEM_AUDIO_CPU_GATE_SETTLE_SECONDS=0 SYSTEM_AUDIO_CPU_GATE_INTERVAL_SECONDS=1 apps/macos/Scripts/sample-system-audio-cpu-gate.sh quit`
    passed with `maxAppProcessCount=0`.
- Result: passed for UI copy, no-HAL boundary, packaged launch, idle CPU, and
  quit CPU after parking the legacy route check.
- Remaining gates not completed by this automated slice: permission matrix,
  controlled artifact validation, active/stop CPU gate, 30-minute development
  run, 75-minute manual release run, and final scope review.

## 2026-06-09 Guided Controlled Manual Gate Harness

- Feature: `025-system-audio-capture-pivot`
- Scope: reduce manual sequencing mistakes for #307/#308/#309 controlled
  recording validation.
- Code review finding:
  - Quickstart and artifact matrix documented the correct manual sequence, but
    the tester still had to remember to run app-only installer validation,
    baseline CPU, activeRecording CPU, stop CPU, and latest artifact validation
    in the right order.
  - Since Codex cannot use macOS Accessibility in this session to press Record
    or Stop, the remaining manual gates needed a guided harness that keeps the
    human-controlled boundary explicit without faking acceptance.
- Code review fix:
  - Added `apps/macos/Scripts/run-system-audio-controlled-manual-gate.sh`.
  - The harness verifies the app-only package boundary, records baseline CPU,
    launches the repo app bundle, prompts the tester to press Record manually,
    samples `activeRecording` CPU, prompts for manual Stop, samples `stop` CPU,
    and validates the newest local artifact metadata-only.
  - It does not click UI, start recording by itself, inspect audio content,
    reset TCC, install the package, run HAL probes, or auto-continue through
    Record/Stop prompts.
  - Quickstart and artifact matrix now point to the harness before the manual
    equivalent steps.
- Validation:
  - `sh -n apps/macos/Scripts/run-system-audio-controlled-manual-gate.sh`
    passed.
  - `apps/macos/Scripts/run-system-audio-controlled-manual-gate.sh --help`
    documents the metadata-only and no-auto-recording boundaries.
  - `swift build --package-path apps/macos` passed.
  - `swift test --package-path apps/macos` built and linked the package test
    bundle; local environment is Command Line Tools only, so `xctest` is not
    available for full XCTest execution.
  - `swift run --package-path apps/macos ContractValidation` passed.
  - `apps/macos/Scripts/validate-system-audio-no-hal-probe.sh` passed with
    `checkedFiles=7`.
  - `apps/macos/Scripts/validate-system-audio-capture-pivot.sh --installer-app-only`
    passed.
  - `apps/macos/Scripts/validate-system-audio-capture-pivot.sh --review-evidence`
    remained correctly blocked on manual permission/artifact/duration gates and
    missing real `activeRecording`/`stop` CPU evidence.
  - App-only bundle launch produced one visible `2brain Rec` window.
  - Runtime process snapshot showed app CPU `0.0`, `coreaudiod` CPU `0.0`, and
    no thermal/performance warning recorded by `pmset -g therm`.
  - `apps/macos/Scripts/sample-system-audio-cpu-gate.sh idle` passed with
    `maxCoreaudiodCpuPercent=0.00` and `maxAppHelperCpuPercent=0.00`.
  - `SYSTEM_AUDIO_CPU_GATE_SETTLE_SECONDS=0 SYSTEM_AUDIO_CPU_GATE_INTERVAL_SECONDS=1 apps/macos/Scripts/sample-system-audio-cpu-gate.sh quit`
    passed with `maxAppProcessCount=0`.
- Result: passed for guided manual harness syntax/help, metadata-only safety,
  build, contract, no-HAL, app-only installer gate, app launch, idle CPU, and
  quit CPU.
- Remaining gates not completed by this automated slice: permission matrix,
  controlled artifact validation, active/stop CPU gate, 30-minute development
  run, 75-minute manual release run, and final scope review.

## 2026-06-08 App-Only Installer Safety Review

- Feature: `025-system-audio-capture-pivot`
- Scope: local installer defaults and driver/CoreAudio side effects.
- Code review finding:
  - `build-local-installer.sh` always built and packaged the proof HAL driver
    component alongside the desktop app.
  - The driver package `postinstall` and repair/lifecycle scripts could restart
    `coreaudiod`.
  - This contradicted the system-audio MVP boundary: local MVP validation should
    not require installing a driver or refreshing CoreAudio, and accidental
    installer use should not look like the app froze the meeting stack.
- Code review fix:
  - `build-local-installer.sh` now defaults to an app-only package.
  - The proof HAL driver component is included only with explicit
    `TWO_BRAIN_REC_INCLUDE_DRIVER_COMPONENT=1`.
  - `postinstall.sh`, `repair.sh`, and installer lifecycle validation now skip
    `coreaudiod` restart unless
    `TWO_BRAIN_REC_ALLOW_COREAUDIOD_RESTART=1` is explicitly set.
  - Installer README now documents app-only MVP default and keeps driver
    packaging as parked future-driver diagnostics.
  - `validate-system-audio-capture-pivot.sh` now includes
    `--installer-app-only`, a reproducible metadata-only gate that builds the
    default package and fails if the desktop-app-only boundary regresses.
- Validation:
  - `sh -n` passed for `build-local-installer.sh`, `postinstall.sh`,
    `repair.sh`, and `installer-lifecycle-release-hardening.sh`.
  - `swift build --package-path apps/macos` passed.
  - `swift test --package-path apps/macos` built and linked the package test
    bundle; local environment is Command Line Tools only, so `xctest` is not
    available for full XCTest execution.
  - `swift run --package-path apps/macos ContractValidation` passed.
  - `apps/macos/Scripts/validate-system-audio-no-hal-probe.sh` passed with
    `checkedFiles=7`.
  - `TWO_BRAIN_REC_ALLOW_ADHOC_APP_SIGNING=1 sh apps/macos/Installer/Scripts/build-local-installer.sh`
    produced `apps/macos/.build/installer/2brain-rec-local.pkg`.
  - The default package components directory contained only
    `2brain-rec-desktop-app.pkg`.
  - `apps/macos/.build/installer/distribution.xml` contained only
    `desktop-app` package references and no `audio-driver` package references.
  - `apps/macos/Scripts/validate-system-audio-capture-pivot.sh --installer-app-only`
    passed and recorded metadata-only evidence in `driver-parked.md`.
  - App-only packaged app launch produced one visible `2brain Rec` window.
  - Runtime process snapshot showed app CPU `0.0`, `coreaudiod` CPU `0.0`, and
    no thermal/performance warning recorded by `pmset -g therm`.
  - `apps/macos/Scripts/sample-system-audio-cpu-gate.sh idle` passed with
    `maxCoreaudiodCpuPercent=0.00` and latest
    `maxAppHelperCpuPercent=0.10`.
  - `SYSTEM_AUDIO_CPU_GATE_SETTLE_SECONDS=0 SYSTEM_AUDIO_CPU_GATE_INTERVAL_SECONDS=1 apps/macos/Scripts/sample-system-audio-cpu-gate.sh quit`
    passed with `maxAppProcessCount=0`.
- Result: passed for app-only installer default, no implicit driver package,
  no implicit CoreAudio restart, build, contract, no-HAL, launch, idle CPU, and
  quit CPU.
- Remaining gates not completed by this automated slice: permission matrix,
  controlled artifact validation, active/stop CPU gate, 30-minute development
  run, 75-minute manual release run, and final scope review.

## 2026-06-08 Audio Health Recovery Driver-Parked Review

- Feature: `025-system-audio-capture-pivot`
- Scope: Audio Health recovery actions produced by `AudioEnvironmentMonitor`.
- Code review finding:
  - `AudioEnvironmentMonitor.gatherRecoveryActions(...)` still emitted old
    recovery actions such as installing or repairing the virtual audio driver,
    re-verifying virtual device visibility, and repairing the driver path.
  - This was a second path, separate from the primary `LocalAudioSnapshot`, that
    could reintroduce driver-first guidance into MVP health/status UI.
- Code review fix:
  - Driver states that are not usable for MVP now produce parked diagnostics
    copy instead of install/repair instructions.
  - Missing virtual devices now state that virtual devices are not required for
    system-audio recording.
  - Failed passthrough now points to parked passthrough diagnostics for future
    driver experiments, not driver repair before recording.
  - Added regression coverage for `AudioEnvironmentMonitor` recovery actions to
    ensure they mention parked/not-required semantics and do not mention install
    or repair.
- Validation:
  - `swift build --package-path apps/macos` passed.
  - `swift test --package-path apps/macos` built and linked the package test
    bundle; local environment is Command Line Tools only, so `xctest` is not
    available for full XCTest execution.
  - `swift run --package-path apps/macos ContractValidation` passed.
  - `apps/macos/Scripts/validate-system-audio-no-hal-probe.sh` passed with
    `checkedFiles=7`.
  - Targeted search for legacy driver install/repair/readiness copy returned no
    matches in app code/tests after the fix.
  - Fresh packaged build and launch produced one visible `2brain Rec` window.
  - Runtime process snapshot showed app CPU `0.0`, `coreaudiod` CPU `0.0`, and
    no thermal/performance warning recorded by `pmset -g therm`.
  - `apps/macos/Scripts/sample-system-audio-cpu-gate.sh idle` passed with
    `maxCoreaudiodCpuPercent=0.00` and `maxAppHelperCpuPercent=0.00`.
  - `SYSTEM_AUDIO_CPU_GATE_SETTLE_SECONDS=0 SYSTEM_AUDIO_CPU_GATE_INTERVAL_SECONDS=1 apps/macos/Scripts/sample-system-audio-cpu-gate.sh quit`
    passed with `maxAppProcessCount=0`.
- Result: passed for Audio Health recovery copy, build, contract, no-HAL,
  packaged launch, idle CPU, quit CPU, and thermal/process sanity.
- Remaining gates not completed by this automated slice: permission matrix,
  controlled artifact validation, active/stop CPU gate, 30-minute development
  run, 75-minute manual release run, and final scope review.

## 2026-06-08 MVP Status Snapshot Driver-Repair Copy Review

- Feature: `025-system-audio-capture-pivot`
- Scope: default launch/status refresh copy when virtual devices are absent or
  parked.
- Code review finding:
  - The primary `Refresh Status` action no longer started the old route engine,
    but `LocalAudioSnapshot.current()` still built the default route snapshot
    as `failed` when virtual devices were not visible.
  - That could surface `install_or_repair_driver` through the Audio Health
    route recovery row before any explicit recording attempt.
  - This contradicted the MVP pivot rule that system-audio recording must not
    require driver repair or virtual-device visibility before pressing Record.
- Code review fix:
  - For the normal not-checked/status-refresh path, missing virtual microphone
    or speaker now stays `notStarted` with `refresh_local_audio_status` instead
    of becoming a failed driver route.
  - The explicit legacy readiness/debug path can still report driver failures
    when it is intentionally invoked with the old passthrough route check.
  - The no-virtual-device continuity copy now says system audio recording uses
    macOS permissions and virtual devices are parked.
  - The driver diagnostics header no longer presents `Install Driver` or
    `Repair Driver` buttons in the MVP UI; it displays the driver area as
    parked diagnostic information.
  - Added regression coverage for `refresh_local_audio_status` copy so it does
    not ask for driver repair.
- Validation:
  - `swift build --package-path apps/macos` passed.
  - `swift test --package-path apps/macos` built and linked the package test
    bundle; local environment is Command Line Tools only, `xctest` is not
    available, and SwiftPM did not emit XCTest execution details.
  - `swift run --package-path apps/macos ContractValidation` passed.
  - `apps/macos/Scripts/validate-system-audio-no-hal-probe.sh` passed with
    `checkedFiles=7`.
  - Targeted UI search for `Install Driver`, `Repair Driver`, `Run Check`,
    `Readiness Check`, `Not ready for calls yet`, and old readiness/driver
    repair prompts returned no matches in app code/tests after the fix.
  - Fresh packaged build completed with
    `TWO_BRAIN_REC_ALLOW_ADHOC_APP_SIGNING=1 sh apps/macos/Installer/Scripts/build-local-installer.sh`.
  - Packaged app launch produced one visible `2brain Rec` window.
  - Runtime process snapshot after the final packaged launch showed app CPU
    `0.1`, `coreaudiod`
    CPU `0.0`, and no thermal/performance warning recorded by `pmset -g therm`.
  - `log show --last 5m` for `2brain Rec` error/fault/crash/hang/exception
    predicates returned no entries.
  - `apps/macos/Scripts/sample-system-audio-cpu-gate.sh idle` passed with
    `maxCoreaudiodCpuPercent=0.00` and `maxAppHelperCpuPercent=0.10`.
  - `SYSTEM_AUDIO_CPU_GATE_SETTLE_SECONDS=0 SYSTEM_AUDIO_CPU_GATE_INTERVAL_SECONDS=1 apps/macos/Scripts/sample-system-audio-cpu-gate.sh quit`
    passed with `maxAppProcessCount=0`.
- Result: passed for launch/status UI semantics, build, contract, no-HAL,
  packaged launch, idle CPU, quit CPU, and basic log/thermal review.
- Remaining gates not completed by this automated slice: permission matrix,
  controlled artifact validation, active/stop CPU gate, 30-minute development
  run, 75-minute manual release run, and final scope review.

## 2026-06-09 Local Recording Timeline Padding Review

- Feature: `025-system-audio-capture-pivot`
- Scope: local dual-track artifact finalization and timeline alignment.
- Code review finding:
  - `LocalRecordingWriter.stop()` drained pending incoming samples and then
    closed the microphone/incoming WAV writers before calling
    `padTimelineSilence(...)`.
  - If incoming/system audio was intermittent but present, timeline padding
    could attempt to write silence after the WAV handle had been closed.
  - This could produce failed finalization or misleading degraded/misaligned
    artifact metadata for a recording that otherwise had valid incoming audio.
- Code review fix:
  - `padTimelineSilence(...)` now runs before `PCM16MonoWAVFileWriter.close()`
    for both sample-source microphone writers and incoming/system audio.
  - The manifest still computes track duration and alignment only after writers
    are padded, closed, and their frame counts are final.
- Validation:
  - `swift build --package-path apps/macos` passed.
  - `swift test --package-path apps/macos` built and linked
    `TwoBrainRecMacOSPackageTests`; local environment is Command Line Tools
    only, `xcrun --find xctest` exits `72`, so XCTest case execution is not
    available here.
  - Existing regression coverage includes
    `LocalRecordingWriterSystemAudioTests.testStopPadsIntermittentIncomingAudioToRecordingTimeline`,
    but this host can only compile/link that test bundle until a full Xcode
    XCTest runner is available.
  - `swift run --package-path apps/macos ContractValidation` passed.
  - `apps/macos/Scripts/validate-system-audio-no-hal-probe.sh` passed with
    `checkedFiles=7`.
  - `apps/macos/Scripts/validate-system-audio-capture-pivot.sh --installer-app-only`
    passed.
  - Fresh packaged app launch produced one visible `2brain Rec` window.
  - Runtime process snapshot after launch showed app CPU `0.0`, `coreaudiod`
    CPU `0.0`, and no thermal/performance warning recorded by `pmset -g therm`.
  - `log show --last 5m` for `2brain Rec` error/fault/crash/hang/exception
    predicates returned no entries.
  - `apps/macos/Scripts/sample-system-audio-cpu-gate.sh idle` passed with
    `maxCoreaudiodCpuPercent=0.00` and `maxAppHelperCpuPercent=0.10`.
  - `SYSTEM_AUDIO_CPU_GATE_SETTLE_SECONDS=0 SYSTEM_AUDIO_CPU_GATE_INTERVAL_SECONDS=1 apps/macos/Scripts/sample-system-audio-cpu-gate.sh quit`
    passed with `maxAppProcessCount=0`.
  - `apps/macos/Scripts/validate-system-audio-capture-pivot.sh --review-evidence`
    still blocks, as expected, because permission matrix, controlled artifact,
    active/stop CPU, 30-minute, and 75-minute manual gates remain unaccepted.
- Result: passed for code review fix, build, contract, no-HAL, app-only
  installer, packaged launch, idle CPU, quit CPU, and basic log/thermal review.
- Remaining gates not completed by this automated slice: permission matrix,
  controlled artifact validation, active/stop CPU gate, 30-minute development
  run, 75-minute manual release run, and final scope review.

## 2026-06-09 Fresh Automated Baseline And Idle Runtime Review

- Feature: `025-system-audio-capture-pivot`
- Scope: repeated safe baseline before continuing manual acceptance gates.
- Validation:
  - `swift build --package-path apps/macos` passed.
  - `swift test --package-path apps/macos` built and linked the package tests;
    full XCTest execution is not available in this Command Line Tools host
    because `xcrun --find xctest` exits `72`.
  - `swift run --package-path apps/macos ContractValidation` passed.
  - `apps/macos/Scripts/validate-system-audio-no-hal-probe.sh` passed with
    `checkedFiles=7`.
  - `apps/macos/Scripts/validate-system-audio-capture-pivot.sh --installer-app-only`
    passed.
  - `apps/macos/Scripts/validate-system-audio-capture-pivot.sh --review-evidence`
    remains blocked only on manual acceptance evidence: permission matrix,
    artifact matrix, activeRecording CPU, stop CPU, 30-minute run, 75-minute
    run, and final scope review.
  - Fresh packaged app launch produced one visible `2brain Rec` window from
    CoreGraphics with bounds `706x608`.
  - Runtime process snapshot showed app CPU `0.1` and RSS about `90736 KB`.
  - `pmset -g therm` reported no thermal or performance warning level.
  - Idle CPU gate passed with `maxCoreaudiodCpuPercent=0.00` and
    `maxAppHelperCpuPercent=0.00`.
  - Quit CPU gate passed with `maxAppProcessCount=0` and
    `maxHelperProcessCount=0`.
  - Accessibility UI inspection through `osascript` was not available because
    this host has not granted Accessibility trust to `osascript`; no UI click
    or manual Record/Stop claim was made.
  - Broad unified-log crash/hang/error predicate for `2brain Rec` showed Apple
    framework `AppIntents/linkd.autoShortcut` connection errors during launch;
    a narrower app-subsystem predicate returned no project subsystem entries.
- Result: passed for automated build, contract, no-HAL, app-only package,
  packaged launch, idle CPU, quit CPU, and thermal review.
- Remaining gates not completed by this automated slice: permission matrix,
  controlled artifact validation, active/stop CPU gate, 30-minute development
  run, 75-minute manual release run, and final scope review.

## 2026-06-09 MVP Status Refresh Driver-Parked Review

- Feature: `025-system-audio-capture-pivot`
- Scope: normal `Refresh Status` / readiness copy after the system-audio MVP
  pivot.
- Code review finding:
  - The normal status refresh path still classified missing `2brain Rec`
    virtual devices as `virtual_microphone_not_visible` /
    `virtual_speaker_not_visible` and returned `install_or_repair_driver`.
  - That did not start recording or run HAL probes, but it could send a tester
    back to the old driver-repair workflow even though driver diagnostics are
    parked for the MVP.
- Code review fix:
  - Normal status refresh now checks physical microphone/output availability
    and labels rows as `Local Microphone` and `System Audio`.
  - Passed row copy now says the physical microphone is available and system
    audio is checked when recording starts, instead of saying audio reaches the
    virtual 2brain devices.
  - Legacy `install_or_repair_driver` copy is mapped to a parked-driver message.
  - `validate-system-audio-no-hal-probe.sh` now scans the MVP-facing status
    files for old virtual-device repair recovery strings.
  - Added regression coverage for legacy driver-repair action copy.
- Validation:
  - `swift build --package-path apps/macos` passed.
  - `swift test --package-path apps/macos` built and linked
    `TwoBrainRecMacOSPackageTests`, including
    `SystemAudioNoVirtualDeviceCopyTests`; full XCTest execution is not
    available in this Command Line Tools host because `xcrun --find xctest`
    exits `72`.
  - `swift run --package-path apps/macos ContractValidation` passed.
  - `apps/macos/Scripts/validate-system-audio-no-hal-probe.sh` passed with
    `checkedFiles=9`.
  - `apps/macos/Scripts/validate-system-audio-capture-pivot.sh --installer-app-only`
    passed.
  - Fresh packaged app launch produced one visible `2brain Rec` window from
    CoreGraphics with bounds `706x608`.
  - `pmset -g therm` reported no thermal or performance warning level.
  - Idle CPU gate passed with `maxCoreaudiodCpuPercent=0.00` and
    `maxAppHelperCpuPercent=0.10`.
  - Quit CPU gate passed with `maxAppProcessCount=0` and
    `maxHelperProcessCount=0`.
  - Broad unified-log crash/hang/error predicate for `2brain Rec` showed Apple
    framework `AppIntents/linkd.autoShortcut` connection errors during launch;
    a narrower app-subsystem predicate returned no project subsystem entries.
  - `apps/macos/Scripts/validate-system-audio-capture-pivot.sh --review-evidence`
    remains blocked, as expected, because manual permission, artifact,
    active/stop CPU, 30-minute, 75-minute, and final scope evidence are not
    complete.
- Result: passed for the MVP status-refresh driver-parked fix and automated
  checks.
- Remaining gates not completed by this automated slice: permission matrix,
  controlled artifact validation, active/stop CPU gate, 30-minute development
  run, 75-minute manual release run, and final scope review.

## 2026-06-09 System Audio Session Buffer Reset Review

- Feature: `025-system-audio-capture-pivot`
- Scope: repeated manual recordings in one app process.
- Code review finding:
  - `SystemAudioCaptureService` reuses one buffered incoming sample source
    across recording sessions.
  - The buffer and cumulative frame stats were not reset when a new session
    started.
  - A second recording could therefore inherit unread incoming samples or stale
    frame stats from a previous recording, making `incoming.wav` or session
    frame truth misleading.
- Code review fix:
  - Added `BufferedLocalRecordingSampleSource.reset()`.
  - `SystemAudioCaptureService.start(...)` resets the buffer and stats before
    starting the ScreenCaptureKit runtime.
  - Added regression coverage proving a second session starts with no stale
    unread samples and no inherited frame count.
- Validation:
  - `swift build --package-path apps/macos` passed.
  - `swift test --package-path apps/macos` built and linked
    `TwoBrainRecMacOSPackageTests`, including
    `SystemAudioCaptureServiceTests`; full XCTest execution is not available
    in this Command Line Tools host because `xcrun --find xctest` exits `72`.
  - `swift run --package-path apps/macos ContractValidation` passed.
  - `apps/macos/Scripts/validate-system-audio-no-hal-probe.sh` passed with
    `checkedFiles=9`.
  - `apps/macos/Scripts/validate-system-audio-capture-pivot.sh --installer-app-only`
    passed.
  - Fresh packaged app launch produced one visible `2brain Rec` window from
    CoreGraphics with bounds `706x608`.
  - `pmset -g therm` reported no thermal or performance warning level.
  - Idle CPU gate passed with `maxCoreaudiodCpuPercent=0.00` and
    `maxAppHelperCpuPercent=0.10`.
  - Quit CPU gate passed with `maxAppProcessCount=0` and
    `maxHelperProcessCount=0`.
  - Broad unified-log crash/hang/error predicate for `2brain Rec` showed Apple
    framework `AppIntents/linkd.autoShortcut` connection errors during launch;
    a narrower app-subsystem predicate returned no project subsystem entries.
- Result: passed for stale incoming buffer prevention and automated checks.
- Remaining gates not completed by this automated slice: permission matrix,
  controlled artifact validation, active/stop CPU gate, 30-minute development
  run, 75-minute manual release run, and final scope review.

## 2026-06-09 Manifest Required-Role Cardinality Review

- Feature: `025-system-audio-capture-pivot`
- Scope: manifest truth for accepted controlled artifacts.
- Code review finding:
  - `LocalRecordingManifestService` used a `Set` of track roles to decide
    whether both required roles were present.
  - That proved the role names appeared, but did not prove there was exactly one
    `localMic` and exactly one `remoteSpeaker` track.
  - The current writer emits two tracks, but the manifest model should enforce
    the acceptance invariant itself so duplicate-role manifests cannot become
    `saved`.
- Code review fix:
  - `saved` now requires exactly two tracks: one `localMic` and one
    `remoteSpeaker`.
  - Added regression coverage proving a duplicate required role remains
    degraded even when individual tracks look media-ready.
- Validation:
  - `swift build --package-path apps/macos` passed.
  - `swift test --package-path apps/macos` built and linked
    `TwoBrainRecMacOSPackageTests`, including `LocalRecordingManifestTests`;
    full XCTest execution is not available in this Command Line Tools host
    because `xcrun --find xctest` exits `72`.
  - `swift run --package-path apps/macos ContractValidation` passed.
  - `apps/macos/Scripts/validate-system-audio-no-hal-probe.sh` passed with
    `checkedFiles=9`.
  - `apps/macos/Scripts/validate-system-audio-capture-pivot.sh --installer-app-only`
    passed.
  - Fresh packaged app launch produced one visible `2brain Rec` window from
    CoreGraphics with bounds `706x608`.
  - `pmset -g therm` reported no thermal or performance warning level.
  - Idle CPU gate passed with `maxCoreaudiodCpuPercent=0.00` and
    `maxAppHelperCpuPercent=0.00`.
  - Quit CPU gate passed with `maxAppProcessCount=0` and
    `maxHelperProcessCount=0`.
  - Broad unified-log crash/hang/error predicate for `2brain Rec` showed Apple
    framework `AppIntents/linkd.autoShortcut` connection errors during launch;
    a narrower app-subsystem predicate returned no project subsystem entries.
- Result: passed for required-role cardinality and automated checks.
- Remaining gates not completed by this automated slice: permission matrix,
  controlled artifact validation, active/stop CPU gate, 30-minute development
  run, 75-minute manual release run, and final scope review.

## 2026-06-09 Artifact Duration Difference Validator Review

- Feature: `025-system-audio-capture-pivot`
- Scope: metadata-only validation of controlled artifact manifests.
- Code review finding:
  - `validate-system-audio-capture-pivot.sh --artifact-directory` checked that
    `durationDifferenceSeconds <= 3`.
  - The check did not explicitly require the value to be numeric and
    non-negative.
  - The app writer computes this field with an absolute duration difference,
    but the release gate should reject malformed or hand-edited manifest values
    instead of accepting a negative number.
- Code review fix:
  - The artifact validator now requires `durationDifferenceSeconds` to be a
    number between `0` and `3`, inclusive.
- Validation:
  - Synthetic accepted artifact with `durationDifferenceSeconds=-1` returned
    `blocked` with `durationDifferenceSeconds must be a number between 0 and 3`.
  - Synthetic accepted artifact with `durationDifferenceSeconds=0` passed
    metadata validation.
  - `swift build --package-path apps/macos` passed.
  - `swift test --package-path apps/macos` built and linked package tests; full
    XCTest execution is not available in this Command Line Tools host because
    `xcrun --find xctest` exits `72`.
  - `swift run --package-path apps/macos ContractValidation` passed.
  - `apps/macos/Scripts/validate-system-audio-no-hal-probe.sh` passed with
    `checkedFiles=9`.
  - `apps/macos/Scripts/validate-system-audio-capture-pivot.sh --installer-app-only`
    passed.
  - Fresh packaged app launch produced one visible `2brain Rec` window from
    CoreGraphics with bounds `706x608`.
  - `pmset -g therm` reported no thermal or performance warning level.
  - Idle CPU gate passed with `maxCoreaudiodCpuPercent=0.00` and
    `maxAppHelperCpuPercent=0.50`.
  - Quit CPU gate passed with `maxAppProcessCount=0` and
    `maxHelperProcessCount=0`.
  - Broad unified-log crash/hang/error predicate for `2brain Rec` showed Apple
    framework `AppIntents/linkd.autoShortcut` connection errors during launch;
    a narrower app-subsystem predicate returned no project subsystem entries.
- Result: passed for artifact duration-difference validator hardening and
  automated checks.
- Remaining gates not completed by this automated slice: permission matrix,
  controlled artifact validation, active/stop CPU gate, 30-minute development
  run, 75-minute manual release run, and final scope review.

## 2026-06-09 Screen/System Audio Permission Request Review

- Feature: `025-system-audio-capture-pivot`
- Scope: explicit Record permission behavior for incoming/system audio.
- Code review finding:
  - `startManualRecording()` requested microphone permission on explicit Record,
    but only preflighted Screen/System Audio permission with
    `CGPreflightScreenCaptureAccess()`.
  - On a fresh install, the app could therefore block recording as
    `unknown`/missing Screen/System Audio access without initiating the native
    macOS permission request at the moment the user pressed Record.
  - Launch/readiness still must not request permissions or start capture.
- Code review fix:
  - Added `requestPermission()` to `SystemAudioPermissionAuthorizing`.
  - `CoreGraphicsSystemAudioPermissionAuthorizer.requestPermission()` now uses
    `CGRequestScreenCaptureAccess()` and falls back to the current preflight
    state if access is not granted.
  - `TwoBrainRecApp.startManualRecording()` now evaluates the permission gate
    from the requested Screen/System Audio state, matching the microphone
    request flow.
  - Added regression coverage for the system-audio request path feeding the
    permission gate.
- Validation:
  - `swift build --package-path apps/macos` passed.
  - `swift test --package-path apps/macos` built and linked
    `TwoBrainRecMacOSPackageTests`, including
    `SystemAudioPermissionGateTests`; full XCTest execution is not available in
    this Command Line Tools host because `xcrun --find xctest` exits `72`.
  - `swift run --package-path apps/macos ContractValidation` passed.
  - `apps/macos/Scripts/validate-system-audio-no-hal-probe.sh` passed with
    `checkedFiles=7`.
  - `apps/macos/Scripts/validate-system-audio-capture-pivot.sh --installer-app-only`
    passed.
  - Fresh packaged app launch without pressing Record produced one visible
    `2brain Rec` window at `706x608`.
  - Idle CPU passed with `maxCoreaudiodCpuPercent=0.00` and
    `maxAppHelperCpuPercent=0.10`.
  - `pmset -g therm` reported no thermal or performance warning level.
  - Quit CPU passed with `maxAppProcessCount=0` and
    `maxHelperProcessCount=0`.
  - Crash/hang/exception log review found no app crash or hang evidence.
    A broader `error` predicate showed macOS AppIntents/linkd registration
    noise during SwiftUI launch, and a naive `fatal` substring predicate is
    noisy because it matches Apple's `availability` log text. These entries
    were not associated with capture, CoreAudio, ScreenCaptureKit, crash, hang,
    or quit failure.
  - `apps/macos/Scripts/validate-system-audio-capture-pivot.sh --review-evidence`
    remains blocked, as expected, because permission matrix, controlled
    artifact, active/stop CPU, 30-minute, 75-minute, and final scope review
    manual evidence are not complete.
- Result: passed for code review fix, build, contract, no-HAL, app-only
  installer, packaged launch, idle CPU, quit CPU, and thermal/crash-hang review.
- Remaining gates not completed by this automated slice: permission matrix,
  controlled artifact validation, active/stop CPU gate, 30-minute development
  run, 75-minute manual release run, and final scope review.

## 2026-06-09 Incoming Buffer CPU/Responsiveness Review

- Feature: `025-system-audio-capture-pivot`
- Scope: active-recording incoming/system-audio buffering before
  `incoming.wav` writing and live meter updates.
- Code review finding:
  - `BufferedLocalRecordingSampleSource.readSamples(...)` removed consumed
    samples with `Array.removeFirst(count)` on every writer drain.
  - During long active recordings this can repeatedly shift a large Swift array
    on the capture/write path, increasing CPU and responsiveness risk.
  - This is especially relevant to the 30-minute and 75-minute manual gates.
- Code review fix:
  - Replaced per-read `removeFirst` with a `readOffset`.
  - The buffer now advances reads in O(1), trims only unread samples to capacity,
    and compacts storage only when fully consumed or when the offset is large.
  - Added regression coverage for partial reads preserving order, capacity
    overflow dropping the oldest unread samples, and append statistics.
- Validation:
  - `swift build --package-path apps/macos` passed.
  - `swift test --package-path apps/macos` built and linked
    `TwoBrainRecMacOSPackageTests`, including the new
    `LocalRecordingWriterSystemAudioTests` cases; full XCTest execution is not
    available in this Command Line Tools host because `xcrun --find xctest`
    exits `72`.
  - `swift run --package-path apps/macos ContractValidation` passed.
  - `apps/macos/Scripts/validate-system-audio-no-hal-probe.sh` passed with
    `checkedFiles=7`.
  - `apps/macos/Scripts/validate-system-audio-capture-pivot.sh --installer-app-only`
    passed.
  - Fresh packaged app launch without pressing Record produced one visible
    `2brain Rec` window at `706x608`.
  - Idle CPU passed with `maxCoreaudiodCpuPercent=0.00` and
    `maxAppHelperCpuPercent=0.10`.
  - `pmset -g therm` reported no thermal or performance warning level.
  - Quit CPU passed with `maxAppProcessCount=0` and
    `maxHelperProcessCount=0`.
  - `apps/macos/Scripts/validate-system-audio-capture-pivot.sh --review-evidence`
    remains blocked, as expected, because the manual active recording and
    duration gates are not complete.
- Result: passed for code review fix, build, contract, no-HAL, app-only
  installer, packaged launch, idle CPU, quit CPU, and thermal/runtime smoke.
- Remaining gates not completed by this automated slice: permission matrix,
  controlled artifact validation, active/stop CPU gate, 30-minute development
  run, 75-minute manual release run, and final scope review.

## 2026-06-09 Manual Artifact Gate Instruction Review

- Feature: `025-system-audio-capture-pivot`
- Scope: manual controlled-artifact instructions and latest-artifact evidence.
- Code review finding:
  - `quickstart.md` and the guided harness already set
    `SYSTEM_AUDIO_CAPTURE_PIVOT_MIN_ARTIFACT_MTIME` before launch/Record, but
    `evidence/artifact-matrix.md` manual-equivalent steps did not.
  - A tester following only the matrix instructions could therefore validate
    the newest completed artifact without an explicit manual gate start epoch.
  - The validator would still honor the epoch when provided, but the evidence
    append did not show that epoch to reviewers.
- Code review fix:
  - Updated `artifact-matrix.md` manual-equivalent steps to export
    `SYSTEM_AUDIO_CAPTURE_PIVOT_MIN_ARTIFACT_MTIME="$(date +%s)"` before build
    and launch.
  - Updated `validate-system-audio-capture-pivot.sh` to record the artifact
    minimum mtime epoch in appended artifact validator evidence when present.
- Validation:
  - `sh -n apps/macos/Scripts/validate-system-audio-capture-pivot.sh` passed.
  - `sh -n apps/macos/Scripts/run-system-audio-controlled-manual-gate.sh`
    passed.
  - Temp metadata-only latest-artifact validation with
    `SYSTEM_AUDIO_CAPTURE_PIVOT_NO_APPEND=1`,
    `TWO_BRAIN_REC_RECORDINGS_DIR=<tmp>`, and
    `SYSTEM_AUDIO_CAPTURE_PIVOT_MIN_ARTIFACT_MTIME=1` passed for a synthetic
    valid manifest/files directory.
  - Empty temp recordings root with future min epoch returned
    `system_audio_capture_pivot_validation=invalid` and exit code `3`, so it
    cannot be counted as acceptance.
  - `swift build --package-path apps/macos` passed.
  - `apps/macos/Scripts/validate-system-audio-no-hal-probe.sh` passed with
    `checkedFiles=7`.
  - `apps/macos/Scripts/validate-system-audio-capture-pivot.sh --installer-app-only`
    passed.
  - `apps/macos/Scripts/validate-system-audio-capture-pivot.sh --review-evidence`
    remains blocked, as expected, because manual permission, artifact,
    active/stop CPU, 30-minute, 75-minute, and final scope evidence are not
    complete.
- Result: passed for instruction/validator hardening and automated checks.
- Remaining gates not completed by this automated slice: permission matrix,
  controlled artifact validation, active/stop CPU gate, 30-minute development
  run, 75-minute manual release run, and final scope review.

## 2026-06-09 Record/Stop Reentrancy Review

- Feature: `025-system-audio-capture-pivot`
- Scope: UI responsiveness and duplicate action handling around Record/Stop.
- Code review finding:
  - `Record System Audio` remained enabled until `captureSession` changed.
  - `startManualRecording()` requests microphone and Screen/System Audio
    permission before updating `captureSession`, so a fast double click or
    repeated keyboard shortcut could start multiple async start flows during
    permission/system prompt latency.
  - `Stop` likewise had no in-flight UI/action guard while stop/finalization was
    running.
- Code review fix:
  - Added `recordingStartInProgress` and `recordingStopInProgress` state in
    `TwoBrainRecApp`.
  - `startManualRecording()` and `stopManualRecording()` now return early when
    their respective operation is already in progress.
  - `CaptureControlView` disables Record immediately while start/stop is in
    flight.
  - `CaptureStatusItem` disables Stop while stop is in flight.
  - Added regression coverage for Record disabled during an in-flight start and
    Stop disabled during an in-flight stop.
- Validation:
  - `swift build --package-path apps/macos` passed.
  - `swift test --package-path apps/macos` built and linked
    `TwoBrainRecMacOSPackageTests`, including the new
    `CaptureIndicatorTests` cases; full XCTest execution is not available in
    this Command Line Tools host because `xcrun --find xctest` exits `72`.
  - `swift run --package-path apps/macos ContractValidation` passed.
  - `apps/macos/Scripts/validate-system-audio-no-hal-probe.sh` passed with
    `checkedFiles=7`.
  - `apps/macos/Scripts/validate-system-audio-capture-pivot.sh --installer-app-only`
    passed.
  - Fresh packaged app launch without pressing Record produced one visible
    `2brain Rec` window at `706x608`.
  - Idle CPU passed with `maxCoreaudiodCpuPercent=0.00` and
    `maxAppHelperCpuPercent=0.00`.
  - `pmset -g therm` reported no thermal or performance warning level.
  - Quit CPU passed with `maxAppProcessCount=0` and
    `maxHelperProcessCount=0`.
  - `apps/macos/Scripts/validate-system-audio-capture-pivot.sh --review-evidence`
    remains blocked, as expected, because manual permission, artifact,
    active/stop CPU, 30-minute, 75-minute, and final scope evidence are not
    complete.
- Result: passed for reentrancy hardening and automated checks.
- Remaining gates not completed by this automated slice: permission matrix,
  controlled artifact validation, active/stop CPU gate, 30-minute development
  run, 75-minute manual release run, and final scope review.

## 2026-06-09 WAV Metadata Validator Review

- Feature: `025-system-audio-capture-pivot`
- Scope: metadata-only validation of accepted `mic.wav` and `incoming.wav`
  artifacts.
- Code review finding:
  - `validate-system-audio-capture-pivot.sh --artifact-directory` checked that
    files existed and were not smaller than manifest `byteCount`.
  - It did not require exact file size equality, did not inspect the 44-byte WAV
    header, and did not verify that manifest `frameCount`/`durationMs` matched
    the actual PCM WAV header metadata.
  - A malformed, stale, or mismatched WAV could therefore pass if the manifest
    looked correct and the file was large enough.
- Code review fix:
  - The artifact validator now checks exact file size equality against manifest
    `byteCount`.
  - It reads only WAV header metadata and verifies `RIFF`, `WAVE`, `fmt `,
    `data`, PCM format, sample rate, channel count, bits per sample, byte rate,
    block align, data byte count, frame count, and duration.
  - It still does not inspect raw audio content.
- Validation:
  - `sh -n apps/macos/Scripts/validate-system-audio-capture-pivot.sh` passed.
  - Temp metadata-only latest-artifact validation with matching manifest and
    synthetic 16 kHz mono PCM WAV headers passed.
  - Temp latest-artifact validation with mismatched `incoming.wav` manifest
    `byteCount` returned `blocked` with exit code `2`.
  - `swift build --package-path apps/macos` passed.
  - `swift test --package-path apps/macos` built and linked
    `TwoBrainRecMacOSPackageTests`; full XCTest execution is not available in
    this Command Line Tools host because `xcrun --find xctest` exits `72`.
  - `swift run --package-path apps/macos ContractValidation` passed.
  - `apps/macos/Scripts/validate-system-audio-no-hal-probe.sh` passed with
    `checkedFiles=7`.
  - `apps/macos/Scripts/validate-system-audio-capture-pivot.sh --installer-app-only`
    passed.
  - Fresh packaged app launch without pressing Record produced one visible
    `2brain Rec` window at `706x608`.
  - Idle CPU passed with `maxCoreaudiodCpuPercent=0.00` and
    `maxAppHelperCpuPercent=0.00`.
  - `pmset -g therm` reported no thermal or performance warning level.
  - Quit CPU passed with `maxAppProcessCount=0` and
    `maxHelperProcessCount=0`.
  - `apps/macos/Scripts/validate-system-audio-capture-pivot.sh --review-evidence`
    remains blocked, as expected, because manual permission, artifact,
    active/stop CPU, 30-minute, 75-minute, and final scope evidence are not
    complete.
- Result: passed for metadata-only artifact validator hardening and automated
  checks.
- Remaining gates not completed by this automated slice: permission matrix,
  controlled artifact validation, active/stop CPU gate, 30-minute development
  run, 75-minute manual release run, and final scope review.

## 2026-06-09 System Audio Session Metadata Review

- Feature: `025-system-audio-capture-pivot`
- Scope: ScreenCaptureKit system-audio session telemetry.
- Code review finding:
  - `SystemAudioCaptureSession` was started with default `sampleRate=0` and
    `channelCount=0`, even though the runtime config captures 48 kHz stereo.
  - `appendIncomingSamples(...)` counted raw float samples as `frameCount`.
    Because ScreenCaptureKit audio is configured as stereo and the writer
    downmixes interleaved stereo to mono, this could overstate the session frame
    count by two and make diagnostics inconsistent with artifact metadata.
- Code review fix:
  - `SystemAudioCaptureService` now records `sampleRate=48000` and
    `channelCount=2` in the system-audio session.
  - Session `frameCount` now converts buffered interleaved sample counts to
    audio frames using the configured channel count.
  - Updated regression expectations for actor-appended samples and buffered
    runtime stats that bypass the actor.
- Validation:
  - `swift build --package-path apps/macos` passed.
  - `swift test --package-path apps/macos` built and linked
    `TwoBrainRecMacOSPackageTests`, including
    `SystemAudioCaptureServiceTests` and `SystemAudioResourceReleaseTests`;
    full XCTest execution is not available in this Command Line Tools host
    because `xcrun --find xctest` exits `72`.
  - `swift run --package-path apps/macos ContractValidation` passed.
  - `apps/macos/Scripts/validate-system-audio-no-hal-probe.sh` passed with
    `checkedFiles=7`.
  - `apps/macos/Scripts/validate-system-audio-capture-pivot.sh --installer-app-only`
    passed.
  - Fresh packaged app launch without pressing Record produced one visible
    `2brain Rec` window at `706x608`.
  - Idle CPU passed with `maxCoreaudiodCpuPercent=0.00` and
    `maxAppHelperCpuPercent=0.00`.
  - `pmset -g therm` reported no thermal or performance warning level.
  - Quit CPU passed with `maxAppProcessCount=0` and
    `maxHelperProcessCount=0`.
  - `apps/macos/Scripts/validate-system-audio-capture-pivot.sh --review-evidence`
    remains blocked, as expected, because manual permission, artifact,
    active/stop CPU, 30-minute, 75-minute, and final scope evidence are not
    complete.
- Result: passed for system-audio session metadata correctness and automated
  checks.
- Remaining gates not completed by this automated slice: permission matrix,
  controlled artifact validation, active/stop CPU gate, 30-minute development
  run, 75-minute manual release run, and final scope review.

## 2026-06-09 Start Failure Classification Review

- Feature: `025-system-audio-capture-pivot`
- Scope: failed manual recording start after permission and prerequisite checks.
- Code review finding:
  - If `SystemAudioCaptureService.start(...)` failed after the capture
    controller had moved toward active recording, the UI/log path classified the
    failure as `storage_unsafe` and displayed "local file capture" wording.
  - That could send the tester toward the wrong recovery path when the real
    problem was ScreenCaptureKit/system-audio capture startup, scope, or
    permission.
- Code review fix:
  - Added `RecordingStartBlocker.captureFailed`.
  - `startManualRecording()` now maps system-audio runtime/scope/display
    failures to `capture_failed`, permission failures to `permission_denied`,
    already-running failures to `already_recording`, and local directory
    failures to `storage_unsafe`.
  - User-facing start failure copy now names the failing layer more accurately
    instead of always saying local file capture.
  - Added regression coverage for the new blocker raw value and fixed the
    prerequisite blocker copy switch for the new case.
- Validation:
  - `swift build --package-path apps/macos` passed.
  - `swift test --package-path apps/macos` built and linked
    `TwoBrainRecMacOSPackageTests`, including `CaptureControlTests`; full
    XCTest execution is not available in this Command Line Tools host because
    `xcrun --find xctest` exits `72`.
  - `swift run --package-path apps/macos ContractValidation` passed.
  - `apps/macos/Scripts/validate-system-audio-no-hal-probe.sh` passed with
    `checkedFiles=7`.
  - `apps/macos/Scripts/validate-system-audio-capture-pivot.sh --installer-app-only`
    passed.
  - Fresh packaged app launch without pressing Record produced one visible
    `2brain Rec` window at `706x608`.
  - Idle CPU passed with `maxCoreaudiodCpuPercent=0.00` and
    `maxAppHelperCpuPercent=0.00`.
  - `pmset -g therm` reported no thermal or performance warning level.
  - Quit CPU passed with `maxAppProcessCount=0` and
    `maxHelperProcessCount=0`.
  - `apps/macos/Scripts/validate-system-audio-capture-pivot.sh --review-evidence`
    remains blocked, as expected, because manual permission, artifact,
    active/stop CPU, 30-minute, 75-minute, and final scope evidence are not
    complete.
- Result: passed for start failure classification and automated checks.
- Remaining gates not completed by this automated slice: permission matrix,
  controlled artifact validation, active/stop CPU gate, 30-minute development
  run, 75-minute manual release run, and final scope review.

## 2026-06-09 Guided Harness Stale Artifact Guard Review

- Feature: `025-system-audio-capture-pivot`
- Scope: guided manual controlled-recording harness and latest artifact
  validation safety.
- Code review finding:
  - `run-system-audio-controlled-manual-gate.sh` validated the newest completed
    local recording artifact, but did not prove that the artifact was produced
    during the current manual gate run.
  - If Record failed, permissions blocked recording, or an older completed
    artifact existed, the harness could accidentally validate stale evidence.
- Code review fix:
  - `validate-system-audio-capture-pivot.sh --latest-artifact-directory` and
    `--validate-latest-artifact` now honor
    `SYSTEM_AUDIO_CAPTURE_PIVOT_MIN_ARTIFACT_MTIME`.
  - `run-system-audio-controlled-manual-gate.sh` records/export its start epoch
    and ignores artifacts older than the harness start.
  - Quickstart manual-equivalent steps now set the same epoch before launching
    and recording.
- Validation:
  - `sh -n` passed for both affected scripts.
  - Harness help documents that latest artifact validation is limited to
    artifacts modified after the harness started.
  - Validator help documents
    `SYSTEM_AUDIO_CAPTURE_PIVOT_MIN_ARTIFACT_MTIME`.
  - `SYSTEM_AUDIO_CAPTURE_PIVOT_MIN_ARTIFACT_MTIME=9999999999 apps/macos/Scripts/validate-system-audio-capture-pivot.sh --latest-artifact-directory`
    returned `invalid` with no stale artifact accepted.
  - `swift build --package-path apps/macos` passed.
  - `swift test --package-path apps/macos` built the package test bundle; full
    XCTest execution is not available in this Command Line Tools host because
    `xcrun --find xctest` exits `72`.
  - `swift run --package-path apps/macos ContractValidation` passed.
  - `apps/macos/Scripts/validate-system-audio-no-hal-probe.sh` passed with
    `checkedFiles=7`.
  - `apps/macos/Scripts/validate-system-audio-capture-pivot.sh --installer-app-only`
    passed.
  - Fresh packaged app launch produced one visible `2brain Rec` window.
  - Runtime process snapshot after launch showed app CPU `0.0`, `coreaudiod`
    CPU `0.0`, and no thermal/performance warning recorded by `pmset -g therm`.
  - `log show --last 5m` for `2brain Rec` error/fault/crash/hang/exception
    predicates returned no entries.
  - `apps/macos/Scripts/sample-system-audio-cpu-gate.sh idle` passed with
    `maxCoreaudiodCpuPercent=0.00` and `maxAppHelperCpuPercent=0.10`.
  - `SYSTEM_AUDIO_CPU_GATE_SETTLE_SECONDS=0 SYSTEM_AUDIO_CPU_GATE_INTERVAL_SECONDS=1 apps/macos/Scripts/sample-system-audio-cpu-gate.sh quit`
    passed with `maxAppProcessCount=0`.
- Result: passed for harness stale-artifact guard, build, contract, no-HAL,
  app-only installer, packaged launch, idle CPU, quit CPU, and basic
  log/thermal review.
- Remaining gates not completed by this automated slice: permission matrix,
  controlled artifact validation, active/stop CPU gate, 30-minute development
  run, 75-minute manual release run, and final scope review.

## 2026-06-09 Live Meter Stale Level Review

- Feature: `025-system-audio-capture-pivot`
- Scope: live microphone/incoming meter state freshness and UI non-staleness.
- Code review finding:
  - `LiveAudioSignalMonitor` correctly marked stale signals as not live by
    timestamp, but retained the last non-zero level value.
  - In the UI this could leave equalizer bars holding a stale last value while
    the label says the source is silent, making the meter feel stuck.
- Code review fix:
  - `LiveAudioSignalMonitor` now resets microphone and incoming levels to zero
    when their last frame timestamp is stale.
  - Added regression coverage for stale incoming and stale microphone levels so
    bars do not hold the last value after audio stops.
- Validation:
  - `swift build --package-path apps/macos` passed.
  - `swift test --package-path apps/macos` built and linked
    `TwoBrainRecMacOSPackageTests`; full XCTest execution is not available in
    this Command Line Tools host because `xcrun --find xctest` exits `72`.
  - `swift run --package-path apps/macos ContractValidation` passed.
  - `apps/macos/Scripts/validate-system-audio-no-hal-probe.sh` passed with
    `checkedFiles=7`.
  - `apps/macos/Scripts/validate-system-audio-capture-pivot.sh --installer-app-only`
    passed.
  - Fresh packaged app launch produced one visible `2brain Rec` window.
  - Runtime process snapshot after launch showed app CPU `0.0`, `coreaudiod`
    CPU `0.0`, and no thermal/performance warning recorded by `pmset -g therm`.
  - `log show --last 5m` for `2brain Rec` error/fault/crash/hang/exception
    predicates returned no entries.
  - `apps/macos/Scripts/sample-system-audio-cpu-gate.sh idle` passed with
    `maxCoreaudiodCpuPercent=0.00` and `maxAppHelperCpuPercent=0.00`.
  - `SYSTEM_AUDIO_CPU_GATE_SETTLE_SECONDS=0 SYSTEM_AUDIO_CPU_GATE_INTERVAL_SECONDS=1 apps/macos/Scripts/sample-system-audio-cpu-gate.sh quit`
    passed with `maxAppProcessCount=0`.
- Result: passed for code review fix, build, contract, no-HAL, app-only
  installer, packaged launch, idle CPU, quit CPU, and basic log/thermal review.
- Remaining gates not completed by this automated slice: permission matrix,
  controlled artifact validation, active/stop CPU gate, 30-minute development
  run, 75-minute manual release run, and final scope review.

## 2026-06-09 System Audio Sample Endianness Review

- Feature: `025-system-audio-capture-pivot`
- Scope: ScreenCaptureKit/CoreMedia sample conversion for incoming/system audio.
- Code review finding:
  - `SystemAudioSampleExtractor` assumed little/native-endian PCM while reading
    float32 and signed int16 samples.
  - That is correct for the current Apple Silicon host, but the CoreAudio format
    description can explicitly mark buffers as big-endian.
  - If such a buffer appears, incoming levels and `incoming.wav` content could
    be decoded incorrectly even though capture itself is running.
- Code review fix:
  - Float32 and signed int16 decoding now respects
    `kAudioFormatFlagIsBigEndian`.
  - Added regression coverage for big-endian float32 and big-endian signed int16
    sample buffers.
- Validation:
  - `swift build --package-path apps/macos` passed.
  - `swift test --package-path apps/macos` built and linked
    `TwoBrainRecMacOSPackageTests`; full XCTest execution is not available in
    this Command Line Tools host because `xcrun --find xctest` exits `72`.
  - `swift run --package-path apps/macos ContractValidation` passed.
  - `apps/macos/Scripts/validate-system-audio-no-hal-probe.sh` passed with
    `checkedFiles=7`.
  - `apps/macos/Scripts/validate-system-audio-capture-pivot.sh --installer-app-only`
    passed.
  - Fresh packaged app launch produced one visible `2brain Rec` window.
  - Runtime process snapshot after launch showed app CPU `0.0`, `coreaudiod`
    CPU `0.0`, and no thermal/performance warning recorded by `pmset -g therm`.
  - `log show --last 5m` for `2brain Rec` error/fault/crash/hang/exception
    predicates returned no entries.
  - `apps/macos/Scripts/sample-system-audio-cpu-gate.sh idle` passed with
    `maxCoreaudiodCpuPercent=0.00` and `maxAppHelperCpuPercent=0.10`.
  - `SYSTEM_AUDIO_CPU_GATE_SETTLE_SECONDS=0 SYSTEM_AUDIO_CPU_GATE_INTERVAL_SECONDS=1 apps/macos/Scripts/sample-system-audio-cpu-gate.sh quit`
    passed with `maxAppProcessCount=0`.
- Result: passed for code review fix, build, contract, no-HAL, app-only
  installer, packaged launch, idle CPU, quit CPU, and basic log/thermal review.
- Remaining gates not completed by this automated slice: permission matrix,
  controlled artifact validation, active/stop CPU gate, 30-minute development
  run, 75-minute manual release run, and final scope review.

## 2026-06-09 Stop Failure Cleanup Review

- Feature: `025-system-audio-capture-pivot`
- Scope: local recording stop/finalize failure handling and UI session state.
- Code review finding:
  - If `LocalRecordingWriter.stop()` failed after `CaptureSessionController`
    entered `stopping`, `stopManualRecording()` only displayed a blocker and
    logged the error.
  - The capture session could remain in `stopping` with Stop still available,
    which would look like a frozen UI during a bad finalize path.
  - `LocalRecordingWriter.stop()` also cleared `active` only on the success
    path, so a finalize error could leave the writer internally recording.
- Code review fix:
  - `LocalRecordingWriter.stop()` now uses cleanup `defer` so recorder, WAV
    handles, scratch buffer, and `active` are released on both success and
    failure.
  - `PCM16MonoWAVFileWriter.close()` is idempotent, preventing duplicate close
    cleanup from becoming a secondary error.
  - `stopManualRecording()` now moves the capture session to `failed` and
    releases system-audio resources if stop/finalize throws.
  - Added regression coverage for the `stopping -> failed` transition so Stop
    cannot remain available after a stop failure.
- Validation:
  - `swift build --package-path apps/macos` passed.
  - `swift test --package-path apps/macos` built and linked
    `TwoBrainRecMacOSPackageTests`; full XCTest execution is not available in
    this Command Line Tools host because `xcrun --find xctest` exits `72`.
  - `swift run --package-path apps/macos ContractValidation` passed.
  - `apps/macos/Scripts/validate-system-audio-no-hal-probe.sh` passed with
    `checkedFiles=7`.
  - `apps/macos/Scripts/validate-system-audio-capture-pivot.sh --installer-app-only`
    passed.
  - Fresh packaged app launch produced one visible `2brain Rec` window.
  - Runtime process snapshot after launch showed app CPU `0.0`, `coreaudiod`
    CPU `0.0`, and no thermal/performance warning recorded by `pmset -g therm`.
  - `log show --last 5m` for `2brain Rec` error/fault/crash/hang/exception
    predicates returned no entries.
  - `apps/macos/Scripts/sample-system-audio-cpu-gate.sh idle` passed with
    `maxCoreaudiodCpuPercent=0.00` and `maxAppHelperCpuPercent=0.10`.
  - `SYSTEM_AUDIO_CPU_GATE_SETTLE_SECONDS=0 SYSTEM_AUDIO_CPU_GATE_INTERVAL_SECONDS=1 apps/macos/Scripts/sample-system-audio-cpu-gate.sh quit`
    passed with `maxAppProcessCount=0`.
- Result: passed for code review fix, build, contract, no-HAL, app-only
  installer, packaged launch, idle CPU, quit CPU, and basic log/thermal review.
- Remaining gates not completed by this automated slice: permission matrix,
  controlled artifact validation, active/stop CPU gate, 30-minute development
  run, 75-minute manual release run, and final scope review.

## 2026-06-09 Manifest Acceptance Metadata Hardening Review

- Feature: `025-system-audio-capture-pivot`
- Scope: local recording manifest `saved`, `ready`, and `isComplete` truth.
- Code review finding:
  - `LocalRecordingManifestService` could mark a complete pair of WAV tracks as
    `saved` when `scopeApproval` and `permissions` metadata were absent.
  - `LocalRecordingManifest.isComplete` had the same weakness for direct model
    usage.
  - The artifact validator already required scope and granted permissions, but
    the model itself could still produce misleading completion in future code or
    synthetic tests.
- Code review fix:
  - `LocalRecordingManifestService` now requires accepted scope approval and
    granted microphone + system-audio permissions before returning
    `saved`/`ready`.
  - `LocalRecordingManifest.isComplete` now requires the same scope and
    permission metadata.
  - Added regression coverage that complete tracks without scope/permissions
    remain degraded and not complete.
- Validation:
  - `swift build --package-path apps/macos` passed.
  - `swift test --package-path apps/macos` built and linked
    `TwoBrainRecMacOSPackageTests`; full XCTest execution is not available in
    this Command Line Tools host because `xcrun --find xctest` exits `72`.
  - `swift run --package-path apps/macos ContractValidation` passed.
  - `apps/macos/Scripts/validate-system-audio-no-hal-probe.sh` passed with
    `checkedFiles=7`.
  - `apps/macos/Scripts/validate-system-audio-capture-pivot.sh --installer-app-only`
    passed.
  - Fresh packaged app launch produced one visible `2brain Rec` window.
  - Runtime process snapshot after launch showed app CPU `0.1`, `coreaudiod`
    CPU `0.0`, and no thermal/performance warning recorded by `pmset -g therm`.
  - `log show --last 5m` for `2brain Rec` error/fault/crash/hang/exception
    predicates returned no entries.
  - `apps/macos/Scripts/sample-system-audio-cpu-gate.sh idle` passed with
    `maxCoreaudiodCpuPercent=0.00` and `maxAppHelperCpuPercent=0.10`.
  - `SYSTEM_AUDIO_CPU_GATE_SETTLE_SECONDS=0 SYSTEM_AUDIO_CPU_GATE_INTERVAL_SECONDS=1 apps/macos/Scripts/sample-system-audio-cpu-gate.sh quit`
    passed with `maxAppProcessCount=0`.
- Result: passed for code review fix, build, contract, no-HAL, app-only
  installer, packaged launch, idle CPU, quit CPU, and basic log/thermal review.
- Remaining gates not completed by this automated slice: permission matrix,
  controlled artifact validation, active/stop CPU gate, 30-minute development
  run, 75-minute manual release run, and final scope review.

## 2026-06-09 ScreenCaptureKit Audio Buffer Extraction Review

- Feature: `025-system-audio-capture-pivot`
- Scope: incoming/system audio sample extraction before `incoming.wav` writing
  and live incoming meter updates.
- Code review finding:
  - `ScreenCaptureKitSystemAudioRuntime` only read contiguous
    `CMBlockBuffer` audio payloads from `CMSampleBuffer`.
  - CoreMedia audio samples can also arrive through an `AudioBufferList`,
    including non-interleaved left/right buffers.
  - In that representation, incoming/system audio could be silently dropped,
    which would make the incoming meter stay inactive and produce missing or
    degraded `incoming.wav` evidence even when remote audio was present.
- Code review fix:
  - Added `SystemAudioSampleExtractor` for ScreenCaptureKit sample conversion.
  - The extractor still supports contiguous block buffers, and now falls back
    to `CMSampleBufferGetAudioBufferListWithRetainedBlockBuffer(...)`.
  - Non-interleaved buffers are interleaved before being passed to the local WAV
    writer, preserving the writer's stereo-to-mono downmix assumptions.
  - Added regression coverage for interleaved float buffers, non-interleaved
    float buffers, and signed 16-bit PCM normalization.
- Validation:
  - `swift build --package-path apps/macos` passed.
  - `swift test --package-path apps/macos` built and linked
    `TwoBrainRecMacOSPackageTests`, including
    `SystemAudioSampleExtractorTests`; full XCTest execution is not available
    in this Command Line Tools host because `xcrun --find xctest` exits `72`.
  - `swift run --package-path apps/macos ContractValidation` passed.
  - `apps/macos/Scripts/validate-system-audio-no-hal-probe.sh` passed with
    `checkedFiles=7`.
  - `apps/macos/Scripts/validate-system-audio-capture-pivot.sh --installer-app-only`
    passed.
  - Fresh packaged app launch produced one visible `2brain Rec` window.
  - Runtime process snapshot after launch showed app CPU `0.0`, `coreaudiod`
    CPU `0.0`, and no thermal/performance warning recorded by `pmset -g therm`.
  - `log show --last 5m` for `2brain Rec` error/fault/crash/hang/exception
    predicates returned no entries.
  - `apps/macos/Scripts/sample-system-audio-cpu-gate.sh idle` passed with
    `maxCoreaudiodCpuPercent=0.00` and `maxAppHelperCpuPercent=0.10`.
  - `SYSTEM_AUDIO_CPU_GATE_SETTLE_SECONDS=0 SYSTEM_AUDIO_CPU_GATE_INTERVAL_SECONDS=1 apps/macos/Scripts/sample-system-audio-cpu-gate.sh quit`
    passed with `maxAppProcessCount=0`.
- Result: passed for code review fix, build, contract, no-HAL, app-only
  installer, packaged launch, idle CPU, quit CPU, and basic log/thermal review.
- Remaining gates not completed by this automated slice: permission matrix,
  controlled artifact validation, active/stop CPU gate, 30-minute development
  run, 75-minute manual release run, and final scope review.

## 2026-06-09 Recording Meter Freshness Review

- Feature: `025-system-audio-capture-pivot`
- Scope: live microphone and incoming/system-audio meter responsiveness during
  recording.
- Code review finding:
  - `CaptureControlView` treated microphone and incoming samples as stale after
    `0.45` seconds.
  - Microphone levels are refreshed on every UI poll through `AVAudioRecorder`,
    but incoming ScreenCaptureKit/system-audio levels update only when the
    writer receives another audio batch.
  - The short freshness window could show a false `Silent` state between valid
    incoming audio batches, matching the manual symptom where the incoming meter
    appeared unresponsive while recording.
- Code review fix:
  - Added shared `recordingMeterFreshnessWindowSeconds = 1.5` for recording
    meters.
  - Updated `CaptureControlView` to use the shared freshness window for both
    microphone and incoming meters.
  - Added regression coverage that the recording meter window remains large
    enough for batched system-audio delivery without holding stale state for
    longer than `2.0` seconds.
- Validation:
  - `swift build --package-path apps/macos` passed.
  - `swift test --package-path apps/macos` built and linked
    `TwoBrainRecMacOSPackageTests`, including
    `SystemAudioLocalizationTests`; full XCTest execution is not available in
    this Command Line Tools host because `xcrun --find xctest` exits `72`.
  - `swift run --package-path apps/macos ContractValidation` passed.
  - `apps/macos/Scripts/validate-system-audio-no-hal-probe.sh` passed with
    `checkedFiles=9`.
  - `apps/macos/Scripts/validate-system-audio-capture-pivot.sh --installer-app-only`
    passed.
  - `apps/macos/Scripts/validate-system-audio-capture-pivot.sh --review-evidence`
    remained blocked only by the known manual evidence gaps tracked in #307,
    #308, #309, #310, #311, and #313.
- Result: passed for code review fix, build, contract, no-HAL, and app-only
  installer validation.
- Remaining gates not completed by this automated slice: permission matrix,
  controlled artifact validation, active/stop CPU gate, 30-minute development
  run, 75-minute manual release run, and final scope review.

## 2026-06-09 Main Window Recovery And Runtime Smoke

- Feature: `025-system-audio-capture-pivot`
- Scope: packaged app launch/reopen window lifecycle, idle/quit CPU, app logs,
  unified logs, and thermal status after the live-meter fix.
- Code review finding:
  - The AppKit main window path only called `presentMainWindow` on reopen when
    macOS reported no visible windows.
  - Reused windows were ordered with `makeKeyAndOrderFront`, but were not
    explicitly deminiaturized or ordered regardless.
  - This left a weak recovery path for the user-reported class of problems
    where the app process remains alive but the UI does not reliably return to
    the foreground.
- Code review fix:
  - `applicationShouldHandleReopen` now always re-presents the main window.
  - `applicationDidBecomeActive` re-presents the main window when no visible
    main window is available.
  - Reused and newly created main windows now call `orderFrontRegardless()`;
    reused windows are explicitly deminiaturized and made visible.
  - Window visibility logs now include `mainWindowVisible`, `key`,
    `miniaturized`, `activeSpace`, and `occlusion` so future runtime evidence
    can distinguish an internal window from an actually visible active-space
    window.
- Validation:
  - `swift build --package-path apps/macos` passed.
  - `swift test --package-path apps/macos` built and linked the test bundle;
    full XCTest execution is not available in this Command Line Tools host
    because `xcrun --find xctest` exits `72`.
  - `swift run --package-path apps/macos ContractValidation` passed.
  - `apps/macos/Scripts/validate-system-audio-no-hal-probe.sh` passed with
    `checkedFiles=9`.
  - `apps/macos/Scripts/validate-system-audio-capture-pivot.sh --installer-app-only`
    passed.
  - Packaged app launched from
    `apps/macos/RecApp/.build/2brain Rec.app`.
  - AppLog recorded
    `app_window_visibility_checked visibleWindowCount=1 mainWindowVisible=true key=false miniaturized=false activeSpace=true occlusion=8192`.
  - Runtime snapshot after launch showed app CPU `0.0`, app RSS about `95392`,
    and `coreaudiod` CPU `0.0`.
  - `apps/macos/Scripts/sample-system-audio-cpu-gate.sh idle` passed with
    `maxCoreaudiodCpuPercent=0.00` and `maxAppHelperCpuPercent=0.00`.
  - Quit cleanup logged `app_termination_cleanup_completed` and
    `passthrough_bridge_stopped`.
  - `SYSTEM_AUDIO_CPU_GATE_SETTLE_SECONDS=0 SYSTEM_AUDIO_CPU_GATE_INTERVAL_SECONDS=1 apps/macos/Scripts/sample-system-audio-cpu-gate.sh quit`
    passed with `maxAppProcessCount=0`.
  - `log show --last 5m` for `2brain Rec` error/fault/crash/hang/exception
    predicates returned no app entries.
  - `pmset -g therm` reported no thermal or performance warning level.
- Visual caveat:
  - The current automation screen capture was all black and CoreGraphics window
    enumeration from the external automation session returned no `2brain Rec`
    windows, so visual UI inspection from this session is not accepted as
    evidence. The accepted evidence for this smoke is app-internal active-space
    window state, process lifecycle, logs, and CPU/thermal gates.
- Result: passed for code review fix, build, contract, no-HAL, app-only
  installer, packaged app lifecycle, idle CPU, quit CPU, log scan, and thermal
  smoke.
- Remaining gates not completed by this automated slice: permission matrix,
  controlled artifact validation, active/stop CPU gate, 30-minute development
  run, 75-minute manual release run, and final scope review.

## 2026-06-09 System Audio Stop Timeout Hardening

- Feature: `025-system-audio-capture-pivot`
- Scope: active recording stop/release resilience when ScreenCaptureKit runtime
  stop is slow or unresponsive.
- Code review finding:
  - `SystemAudioCaptureService.stop()` and `releaseForTermination()` awaited
    the runtime's `stop()` directly.
  - The default runtime calls ScreenCaptureKit `stopCapture()`. If that call
    stalls, manual Stop or app termination cleanup can remain blocked in the
    capture stop path.
  - This matches the user-reported risk class where the app or meeting app
    appears to hang during recording lifecycle transitions.
- Code review fix:
  - Added a bounded runtime-stop wait inside `SystemAudioCaptureService`
    (`2` seconds by default).
  - Stop and termination release now clear the service active state and return
    even when runtime stop exceeds the timeout.
  - Timeout outcomes are marked as `captureFailed` instead of being reported as
    normal empty recordings.
  - Added resource-release regression tests covering `stop()` and
    `releaseForTermination()` with a slow runtime.
- Validation:
  - `swift build --package-path apps/macos` passed.
  - `swift test --package-path apps/macos` built and linked
    `TwoBrainRecMacOSPackageTests`, including
    `SystemAudioResourceReleaseTests`; full XCTest execution is not available
    in this Command Line Tools host because `xcrun --find xctest` exits `72`.
  - `swift run --package-path apps/macos ContractValidation` passed.
  - `apps/macos/Scripts/validate-system-audio-no-hal-probe.sh` passed with
    `checkedFiles=9`.
  - `apps/macos/Scripts/validate-system-audio-capture-pivot.sh --installer-app-only`
    passed.
  - Packaged app launched from
    `apps/macos/RecApp/.build/2brain Rec.app`; AppLog recorded
    `mainWindowVisible=true`, `activeSpace=true`, and `occlusion=8192`.
  - Runtime snapshot after launch showed app CPU `0.1` and `coreaudiod` CPU
    `0.0`.
  - `apps/macos/Scripts/sample-system-audio-cpu-gate.sh idle` passed with
    `maxCoreaudiodCpuPercent=0.00` and `maxAppHelperCpuPercent=0.00`.
  - Quit cleanup logged `app_termination_cleanup_completed` and
    `passthrough_bridge_stopped`.
  - `SYSTEM_AUDIO_CPU_GATE_SETTLE_SECONDS=0 SYSTEM_AUDIO_CPU_GATE_INTERVAL_SECONDS=1 apps/macos/Scripts/sample-system-audio-cpu-gate.sh quit`
    passed with `maxAppProcessCount=0`.
  - `log show --last 5m` for `2brain Rec` error/fault/crash/hang/exception
    predicates returned no app entries.
  - `pmset -g therm` reported no thermal or performance warning level.
- Result: passed for code review fix, build, contract, no-HAL, app-only
  installer, packaged app lifecycle, idle CPU, quit CPU, log scan, and thermal
  smoke.
- Remaining gates not completed by this automated slice: permission matrix,
  controlled artifact validation, active/stop CPU gate for a real recording,
  30-minute development run, 75-minute manual release run, and final scope
  review.

## 2026-06-09 ScreenCaptureKit Late Stop Race Hardening

- Feature: `025-system-audio-capture-pivot`
- Scope: repeated recording safety after a runtime stop timeout or slow
  ScreenCaptureKit stop completion.
- Code review finding:
  - The timeout hardening allowed the service to recover from a slow runtime
    stop, but `ScreenCaptureKitSystemAudioRuntime.stop()` still cleared
    `self.stream` after awaiting `stopCapture()`.
  - If a user started another recording before the previous `stopCapture()`
    returned, the late completion from the old stream could clear the new
    stream reference.
  - Late audio callbacks from an old stream also needed an identity guard so
    stale system-audio samples cannot contaminate a later recording buffer.
- Code review fix:
  - `ScreenCaptureKitSystemAudioRuntime` now protects `stream` with a lock.
  - `stop()` clears the current stream only when the stopped stream is still the
    current stream.
  - Audio output callbacks are accepted only when the callback stream matches
    the current stream.
  - Added service-level regression coverage proving a new session remains
    running after a late runtime stop completion from the previous session.
- Validation:
  - `swift build --package-path apps/macos` passed.
  - `swift test --package-path apps/macos` built and linked
    `TwoBrainRecMacOSPackageTests`, including the added late-stop regression;
    full XCTest execution is not available in this Command Line Tools host
    because `xcrun --find xctest` exits `72`.
  - `swift run --package-path apps/macos ContractValidation` passed.
  - `apps/macos/Scripts/validate-system-audio-no-hal-probe.sh` passed with
    `checkedFiles=9`.
  - `apps/macos/Scripts/validate-system-audio-capture-pivot.sh --installer-app-only`
    passed.
  - Packaged app launched from
    `apps/macos/RecApp/.build/2brain Rec.app`; AppLog recorded
    `mainWindowVisible=true`, `activeSpace=true`, and `occlusion=8192`.
  - Runtime snapshot after launch showed app CPU `0.0` and `coreaudiod` CPU
    `0.0`.
  - `apps/macos/Scripts/sample-system-audio-cpu-gate.sh idle` passed with
    `maxCoreaudiodCpuPercent=0.00` and `maxAppHelperCpuPercent=0.10`.
  - Quit cleanup logged `app_termination_cleanup_completed` and
    `passthrough_bridge_stopped`.
  - `SYSTEM_AUDIO_CPU_GATE_SETTLE_SECONDS=0 SYSTEM_AUDIO_CPU_GATE_INTERVAL_SECONDS=1 apps/macos/Scripts/sample-system-audio-cpu-gate.sh quit`
    passed with `maxAppProcessCount=0`.
  - `log show --last 5m` for `2brain Rec` error/fault/crash/hang/exception
    predicates returned no app entries.
  - `pmset -g therm` reported no thermal or performance warning level.
- Result: passed for code review fix, build, contract, no-HAL, app-only
  installer, packaged app lifecycle, idle CPU, quit CPU, log scan, and thermal
  smoke.
- Remaining gates not completed by this automated slice: permission matrix,
  controlled artifact validation, active/stop CPU gate for a real recording,
  30-minute development run, 75-minute manual release run, and final scope
  review.

## 2026-06-09 Artifact Duration Recompute Validator Hardening

- Feature: `025-system-audio-capture-pivot`
- Scope: metadata-only controlled artifact validation for dual-track alignment.
- Code review finding:
  - `validate-system-audio-capture-pivot.sh --artifact-directory` required
    `manifest.durationDifferenceSeconds` to be a number between `0` and `3`,
    and validated each WAV against its own track metadata.
  - The validator did not independently recompute duration difference from the
    `localMic.durationMs` and `remoteSpeaker.durationMs` values.
  - A malformed or hand-edited manifest could therefore claim
    `durationDifferenceSeconds=0` while the track durations were actually more
    than `3` seconds apart.
- Code review fix:
  - The artifact validator now requires exactly one numeric `durationMs` for
    `localMic` and exactly one numeric `durationMs` for `remoteSpeaker`.
  - It recomputes absolute mic/incoming duration difference from track metadata
    and requires it to be `<= 3000ms`.
  - It also requires `durationDifferenceSeconds` to equal the recomputed track
    difference in seconds.
- Validation:
  - `sh -n apps/macos/Scripts/validate-system-audio-capture-pivot.sh` passed.
  - A synthetic accepted artifact with matching `mic.wav`, `incoming.wav`, and
    `durationDifferenceSeconds=0` passed metadata validation.
  - A synthetic artifact with `mic.durationMs=1000`,
    `incoming.durationMs=5000`, and forged `durationDifferenceSeconds=0`
    returned blocked with `durationDifferenceSeconds must equal the absolute
    mic/incoming duration difference and be <= 3`.
  - `swift build --package-path apps/macos` passed.
  - `swift test --package-path apps/macos` built and linked the test bundle;
    full XCTest execution is not available in this Command Line Tools host
    because `xcrun --find xctest` exits `72`.
  - `swift run --package-path apps/macos ContractValidation` passed.
  - `apps/macos/Scripts/validate-system-audio-no-hal-probe.sh` passed with
    `checkedFiles=9`.
  - `apps/macos/Scripts/validate-system-audio-capture-pivot.sh --installer-app-only`
    passed.
  - Packaged app launched from
    `apps/macos/RecApp/.build/2brain Rec.app`; AppLog recorded
    `mainWindowVisible=true`, `activeSpace=true`, and `occlusion=8192`.
  - Runtime snapshot after launch showed app CPU `0.0` and `coreaudiod` CPU
    `0.0`.
  - `apps/macos/Scripts/sample-system-audio-cpu-gate.sh idle` passed with
    `maxCoreaudiodCpuPercent=0.00` and `maxAppHelperCpuPercent=0.30`.
  - Quit cleanup logged `app_termination_cleanup_completed` and
    `passthrough_bridge_stopped`.
  - `SYSTEM_AUDIO_CPU_GATE_SETTLE_SECONDS=0 SYSTEM_AUDIO_CPU_GATE_INTERVAL_SECONDS=1 apps/macos/Scripts/sample-system-audio-cpu-gate.sh quit`
    passed with `maxAppProcessCount=0`.
  - `log show --last 5m` for `2brain Rec` error/fault/crash/hang/exception
    predicates returned no app entries.
  - `pmset -g therm` reported no thermal or performance warning level.
- Result: passed for artifact validator hardening, build, contract, no-HAL,
  app-only installer, packaged app lifecycle, idle CPU, quit CPU, log scan, and
  thermal smoke.
- Remaining gates not completed by this automated slice: permission matrix,
  controlled artifact validation on a real recording, active/stop CPU gate for
  a real recording, 30-minute development run, 75-minute manual release run,
  and final scope review.

## 2026-06-09 Permission Stale-State Gate Hardening

- Feature: `025-system-audio-capture-pivot`
- Scope: permission-gate truth for non-granted microphone and Screen/System
  Audio states before starting an accepted recording.
- Code review finding:
  - `SystemAudioPermissionGate` blocked all non-granted states, but the
    `retryPermissionCheck` recovery action was effectively unreachable.
  - A `stale` permission state was shown with generic grant-access copy even
    though the truthful recovery is to rerun the permission check before
    recording.
  - Tests covered denied states, but did not explicitly lock every non-granted
    state (`unknown`, `denied`, `restricted`, `stale`) out of the accepted path
    for both microphone and system audio.
- Code review fix:
  - `stale` microphone or system-audio permission now returns
    `Recording blocked: permission check stale` with
    `retry_permission_check`.
  - Added regression coverage that every non-granted permission state blocks
    accepted recording and maps to `permissionDenied`.
  - Added regression coverage that stale permission states use retry copy
    instead of grant-access copy.
- Validation:
  - `swift build --package-path apps/macos` passed.
  - `swift test --package-path apps/macos` built and linked
    `TwoBrainRecMacOSPackageTests`, including
    `SystemAudioPermissionGateTests`; full XCTest execution is not available
    in this Command Line Tools host because `xcrun --find xctest` exits `72`.
  - `swift run --package-path apps/macos ContractValidation` passed.
  - `apps/macos/Scripts/validate-system-audio-no-hal-probe.sh` passed with
    `checkedFiles=9`.
  - `apps/macos/Scripts/validate-system-audio-capture-pivot.sh --installer-app-only`
    passed.
  - Packaged app launched from
    `apps/macos/RecApp/.build/2brain Rec.app`; AppLog recorded
    `mainWindowVisible=true`, `activeSpace=true`, and `occlusion=8192`.
  - Runtime snapshot after launch showed app CPU `0.0` and `coreaudiod` CPU
    `0.0`.
  - `apps/macos/Scripts/sample-system-audio-cpu-gate.sh idle` passed with
    `maxCoreaudiodCpuPercent=0.00` and `maxAppHelperCpuPercent=0.10`.
  - Quit cleanup logged `app_termination_cleanup_completed` and
    `passthrough_bridge_stopped`.
  - `SYSTEM_AUDIO_CPU_GATE_SETTLE_SECONDS=0 SYSTEM_AUDIO_CPU_GATE_INTERVAL_SECONDS=1 apps/macos/Scripts/sample-system-audio-cpu-gate.sh quit`
    passed with `maxAppProcessCount=0`.
  - `log show --last 5m` for `2brain Rec` error/fault/crash/hang/exception
    predicates returned no app entries.
  - `pmset -g therm` reported no thermal or performance warning level.
- Result: passed for permission gate hardening, build, contract, no-HAL,
  app-only installer, packaged app lifecycle, idle CPU, quit CPU, log scan, and
  thermal smoke.
- Remaining gates not completed by this automated slice: permission matrix with
  real TCC grant/deny/revoke rows, controlled artifact validation on a real
  recording, active/stop CPU gate for a real recording, 30-minute development
  run, 75-minute manual release run, and final scope review.

## 2026-06-09T00:42:40Z CPU Gate App-Process Guard Hardening

- Commit before change: `5f458fe`
- Scope: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh`.
- Issue links: #309, #313.
- Finding:
  - `activeRecording` and `stop` CPU phases could previously report `passed`
    when the app process was not observable, because the CPU samples were below
    threshold.
  - That was a validation false-positive risk: a tester could accidentally run
    the phase outside the app lifecycle and create evidence that did not prove
    the packaged app was participating.
- Change:
  - `activeRecording` and `stop` now fail with `failureReason=appNotRunning`
    when `maxAppProcessCount=0`.
  - Added `SYSTEM_AUDIO_CPU_GATE_NO_APPEND=1` for synthetic script checks that
    must not update `specs/025-system-audio-capture-pivot/evidence/cpu-gates.md`.
- Validation:
  - `sh -n apps/macos/Scripts/sample-system-audio-cpu-gate.sh`
  - `sh -n apps/macos/Scripts/run-system-audio-controlled-manual-gate.sh`
  - `sh -n apps/macos/Scripts/validate-system-audio-capture-pivot.sh`
  - `SYSTEM_AUDIO_CPU_GATE_NO_APPEND=1 SYSTEM_AUDIO_CPU_GATE_SAMPLES=1 SYSTEM_AUDIO_CPU_GATE_SETTLE_SECONDS=0 SYSTEM_AUDIO_CPU_GATE_INTERVAL_SECONDS=1 apps/macos/Scripts/sample-system-audio-cpu-gate.sh baseline`
    returned `status=observed failureReason=diagnosticOnly` with
    `maxAppProcessCount=0`.
  - `SYSTEM_AUDIO_CPU_GATE_NO_APPEND=1 SYSTEM_AUDIO_CPU_GATE_SAMPLES=1 SYSTEM_AUDIO_CPU_GATE_SETTLE_SECONDS=0 SYSTEM_AUDIO_CPU_GATE_INTERVAL_SECONDS=1 apps/macos/Scripts/sample-system-audio-cpu-gate.sh activeRecording`
    returned exit `1` with `status=failed failureReason=appNotRunning`.
  - `SYSTEM_AUDIO_CPU_GATE_NO_APPEND=1 SYSTEM_AUDIO_CPU_GATE_SAMPLES=1 SYSTEM_AUDIO_CPU_GATE_SETTLE_SECONDS=0 SYSTEM_AUDIO_CPU_GATE_INTERVAL_SECONDS=1 apps/macos/Scripts/sample-system-audio-cpu-gate.sh stop`
    returned exit `1` with `status=failed failureReason=appNotRunning`.
- Acceptance impact:
  - This does not close #309/T073. Real `activeRecording` and `stop` CPU
    evidence still has to be captured during a controlled manual recording.

## 2026-06-09T00:50:24Z CPU Gate Repo-App Path Guard Hardening

- Commit before change: `ba9d6d9`
- Scope: `apps/macos/Scripts/sample-system-audio-cpu-gate.sh`.
- Issue links: #309, #313.
- Finding:
  - The CPU sampler required an app process for `activeRecording` and `stop`,
    but the process matcher accepted any `2brain Rec.app` binary path.
  - That could accidentally count an older installed app or a different
    worktree as evidence for this feature branch.
- Change:
  - The sampler now defaults to the packaged app binary in the current repo:
    `apps/macos/RecApp/.build/2brain Rec.app/Contents/MacOS/2brain Rec`.
  - `SYSTEM_AUDIO_CPU_GATE_APP_BINARY` can override that path for an explicit
    controlled run.
  - CPU evidence now records the sampled app binary path next to the command.
- Validation:
  - `sh -n apps/macos/Scripts/sample-system-audio-cpu-gate.sh` passed.
  - With no repo app running,
    `SYSTEM_AUDIO_CPU_GATE_NO_APPEND=1 SYSTEM_AUDIO_CPU_GATE_SAMPLES=1 SYSTEM_AUDIO_CPU_GATE_SETTLE_SECONDS=0 SYSTEM_AUDIO_CPU_GATE_INTERVAL_SECONDS=1 apps/macos/Scripts/sample-system-audio-cpu-gate.sh activeRecording`
    returned exit `1` with `failureReason=appNotRunning`.
  - With no repo app running,
    `SYSTEM_AUDIO_CPU_GATE_NO_APPEND=1 SYSTEM_AUDIO_CPU_GATE_SAMPLES=1 SYSTEM_AUDIO_CPU_GATE_SETTLE_SECONDS=0 SYSTEM_AUDIO_CPU_GATE_INTERVAL_SECONDS=1 apps/macos/Scripts/sample-system-audio-cpu-gate.sh stop`
    returned exit `1` with `failureReason=appNotRunning`.
  - Launched `apps/macos/RecApp/.build/2brain Rec.app`; `idle` CPU gate passed
    with `maxAppProcessCount=1`, `maxCoreaudiodCpuPercent=0.00`, and
    `maxAppHelperCpuPercent=0.40`.
  - Quit cleanup then `quit` CPU gate passed with `maxAppProcessCount=0`,
    `maxCoreaudiodCpuPercent=0.00`, and `maxAppHelperCpuPercent=0.00`.
- Runtime notes:
  - App-internal log showed `mainWindowVisible=true`, `activeSpace=true`, and
    `passthrough_bridge_auto_start_skipped`.
  - `pmset -g therm` reported no thermal or performance warning level.
  - Full-screen `screencapture` returned a black image in this automation
    environment, so no visual UI claim is made from screenshot evidence.
  - Unified log contained macOS AppIntents/linkd connection errors on launch,
    but repository search found no AppIntents/Shortcuts declarations and the
    app-internal launch/window/cleanup logs remained healthy. Treat as reviewed
    system framework noise unless it becomes user-visible.
- Acceptance impact:
  - This still does not close #309/T073. Real `activeRecording` and `stop` CPU
    evidence must be captured during a controlled manual recording.

## 2026-06-09T00:56:27Z System-Audio Buffered Frame Count Review Fix

- Commit before change: `7800c1f`
- Scope:
  - `apps/macos/RecApp/Sources/Capture/LocalRecordingWriter.swift`
  - `apps/macos/RecApp/Sources/Capture/SystemAudioCaptureService.swift`
  - `apps/macos/Shared/Tests/SystemAudioCaptureServiceTests.swift`
- Issue links: #308, #313.
- Finding:
  - `BufferedLocalRecordingSampleSource.stats()` counted appended float samples
    as frames.
  - For stereo system audio, that doubled the buffered frame count; then
    `SystemAudioCaptureService.stop()` divided that value again when reconciling
    runtime-bypassed samples.
  - The net effect could under-report system-audio session frame truth in
    service evidence when callbacks wrote directly to the buffered source.
- Change:
  - `BufferedLocalRecordingSampleSource` now has an explicit `channelCount`
    and records appended frames as `ceil(sampleCount / channelCount)`.
  - `SystemAudioCaptureService.stop()` and `releaseForTermination()` now treat
    buffer stats as frame counts directly.
  - Kept a `capacity` convenience initializer so existing default arguments
    and callers remain link-compatible.
  - Added regression coverage: 512 stereo samples are reported as 256 frames,
    not 128 and not 512.
- Validation:
  - Initial `swift build --package-path apps/macos` caught a Swift default
    argument/link symbol issue after the initializer signature changed.
  - Added the compatibility initializer and reran:
    - `swift build --package-path apps/macos` passed.
    - `swift test --package-path apps/macos` built and linked the test bundle;
      full XCTest execution is not available on this Command Line Tools host.
    - `swift run --package-path apps/macos ContractValidation` passed.
    - `apps/macos/Scripts/validate-system-audio-no-hal-probe.sh` passed with
      `checkedFiles=9`.
    - `apps/macos/Scripts/validate-system-audio-capture-pivot.sh --installer-app-only`
      passed.
    - `apps/macos/Scripts/validate-system-audio-capture-pivot.sh --review-evidence`
      remained blocked only by manual gates.
  - Packaged app runtime smoke after the fix:
    - repo app launched and app-internal log recorded `mainWindowVisible=true`,
      `activeSpace=true`, and `passthrough_bridge_auto_start_skipped`;
    - `sample-system-audio-cpu-gate.sh idle` passed with
      `maxCoreaudiodCpuPercent=0.00`, `maxAppHelperCpuPercent=0.00`, and
      `maxAppProcessCount=1`;
    - after quit, `sample-system-audio-cpu-gate.sh quit` passed with
      `maxAppProcessCount=0`;
    - `pmset -g therm` reported no thermal or performance warning level.
- Acceptance impact:
  - This strengthens artifact/session truth for #308/#313, but does not replace
    the required controlled artifact run.

## 2026-06-09T01:01:40Z Buffered Frame Count Test Expectation Follow-Up

- Commit before change: `6aaac3d`
- Scope: `apps/macos/Shared/Tests/LocalRecordingWriterSystemAudioTests.swift`.
- Issue links: #308, #313.
- Finding:
  - After frame counting moved from samples to channel-aware frames, one
    existing buffer test still expected total sample count (`6`) rather than
    stereo frame count (`3`).
  - The local CLT host builds and links the XCTest bundle but does not execute
    XCTest, so this stale expectation needed a source review pass to catch it
    before CI or a full Xcode host runs the test.
- Change:
  - Updated the existing buffer overflow stats expectation to `3` frames for
    six stereo samples.
  - Added an explicit regression test that `channelCount=2` reports 512 samples
    as 256 frames while `channelCount=1` reports 512 samples as 512 frames.
- Validation:
  - `swift build --package-path apps/macos` passed.
  - `swift test --package-path apps/macos` built and linked the updated test
    bundle on this CLT host.
- Acceptance impact:
  - Test expectation follow-up only; controlled artifact validation is still
    required for #308/T072.
