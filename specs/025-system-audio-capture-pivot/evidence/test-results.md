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
