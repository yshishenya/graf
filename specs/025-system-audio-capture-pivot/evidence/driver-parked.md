# Driver Parked Evidence

This file records evidence that driver work is parked for the system-audio MVP
and cannot become a normal recording prerequisite.

Acceptance boundary:

- Recording readiness is checked from the Record flow and macOS permissions.
- Driver install, repair, virtual-device publication, and Core Audio restart are
  future passthrough diagnostics, not MVP recording gates.
- UI copy may show driver diagnostics, but it must not instruct the user to fix
  the driver before system-audio recording.

## 2026-06-08 Driver-Parked Template

- Feature: `025-system-audio-capture-pivot`
- Tasks: `T056`-`T061`
- Evidence status: automated checks passed for this slice.
- Validation:
  - `swift test --package-path apps/macos`
  - `swift build --package-path apps/macos`
  - `swift run --package-path apps/macos ContractValidation`
  - `./apps/macos/Scripts/validate-system-audio-no-hal-probe.sh`
- Notes: SwiftPM compiles the XCTest bundle in this CommandLineTools
  environment; full `xcrun xctest` execution remains a full-Xcode validation
  item.
