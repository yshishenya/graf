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
    `Readiness Check`, `Recording idle`, visible `Record System Audio`, and
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
