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
