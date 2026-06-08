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

## 2026-06-09 App-Only Installer Validator Run

- Run ID: `20260608T210619Z`
- Timestamp: `2026-06-08T21:06:19Z`
- Commit: `70c850e`
- macOS: `26.5`
- Hardware: `Mac15,10`
- Mode: `--installer-app-only`
- Package: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/2brain-rec-local.pkg`
- Component directory: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/components`
- Validator result: `passed`
- Safe checks: default package built, desktop app component present, audio-driver component absent, distribution has no audio-driver references, and package was not installed.

## 2026-06-09 App-Only Installer Validator Run

- Run ID: `20260608T210637Z`
- Timestamp: `2026-06-08T21:06:37Z`
- Commit: `70c850e`
- macOS: `26.5`
- Hardware: `Mac15,10`
- Mode: `--installer-app-only`
- Package: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/2brain-rec-local.pkg`
- Component directory: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/components`
- Validator result: `passed`
- Safe checks: default package built, desktop app component present, audio-driver component absent, distribution has no audio-driver references, and package was not installed.

## 2026-06-09 App-Only Installer Validator Run

- Run ID: `20260608T211121Z`
- Timestamp: `2026-06-08T21:11:21Z`
- Commit: `5c10f10`
- macOS: `26.5`
- Hardware: `Mac15,10`
- Mode: `--installer-app-only`
- Package: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/2brain-rec-local.pkg`
- Component directory: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/components`
- Validator result: `passed`
- Safe checks: default package built, desktop app component present, audio-driver component absent, distribution has no audio-driver references, and package was not installed.

## 2026-06-09 App-Only Installer Validator Run

- Run ID: `20260608T211934Z`
- Timestamp: `2026-06-08T21:19:34Z`
- Commit: `c2617ce`
- macOS: `26.5`
- Hardware: `Mac15,10`
- Mode: `--installer-app-only`
- Package: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/2brain-rec-local.pkg`
- Component directory: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/components`
- Validator result: `passed`
- Safe checks: default package built, desktop app component present, audio-driver component absent, distribution has no audio-driver references, and package was not installed.

## 2026-06-09 App-Only Installer Validator Run

- Run ID: `20260608T212305Z`
- Timestamp: `2026-06-08T21:23:05Z`
- Commit: `c2617ce`
- macOS: `26.5`
- Hardware: `Mac15,10`
- Mode: `--installer-app-only`
- Package: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/2brain-rec-local.pkg`
- Component directory: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/components`
- Validator result: `passed`
- Safe checks: default package built, desktop app component present, audio-driver component absent, distribution has no audio-driver references, and package was not installed.

## 2026-06-09 App-Only Installer Validator Run

- Run ID: `20260608T213024Z`
- Timestamp: `2026-06-08T21:30:24Z`
- Commit: `8472dda`
- macOS: `26.5`
- Hardware: `Mac15,10`
- Mode: `--installer-app-only`
- Package: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/2brain-rec-local.pkg`
- Component directory: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/components`
- Validator result: `passed`
- Safe checks: default package built, desktop app component present, audio-driver component absent, distribution has no audio-driver references, and package was not installed.

## 2026-06-09 App-Only Installer Validator Run

- Run ID: `20260608T213842Z`
- Timestamp: `2026-06-08T21:38:42Z`
- Commit: `8319de4`
- macOS: `26.5`
- Hardware: `Mac15,10`
- Mode: `--installer-app-only`
- Package: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/2brain-rec-local.pkg`
- Component directory: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/components`
- Validator result: `passed`
- Safe checks: default package built, desktop app component present, audio-driver component absent, distribution has no audio-driver references, and package was not installed.

## 2026-06-09 App-Only Installer Validator Run

- Run ID: `20260608T214448Z`
- Timestamp: `2026-06-08T21:44:48Z`
- Commit: `5f8b05f`
- macOS: `26.5`
- Hardware: `Mac15,10`
- Mode: `--installer-app-only`
- Package: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/2brain-rec-local.pkg`
- Component directory: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/components`
- Validator result: `passed`
- Safe checks: default package built, desktop app component present, audio-driver component absent, distribution has no audio-driver references, and package was not installed.

## 2026-06-09 App-Only Installer Validator Run

- Run ID: `20260608T215030Z`
- Timestamp: `2026-06-08T21:50:30Z`
- Commit: `c0b6644`
- macOS: `26.5`
- Hardware: `Mac15,10`
- Mode: `--installer-app-only`
- Package: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/2brain-rec-local.pkg`
- Component directory: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/components`
- Validator result: `passed`
- Safe checks: default package built, desktop app component present, audio-driver component absent, distribution has no audio-driver references, and package was not installed.

## 2026-06-09 App-Only Installer Validator Run

- Run ID: `20260608T215535Z`
- Timestamp: `2026-06-08T21:55:35Z`
- Commit: `c661106`
- macOS: `26.5`
- Hardware: `Mac15,10`
- Mode: `--installer-app-only`
- Package: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/2brain-rec-local.pkg`
- Component directory: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/components`
- Validator result: `passed`
- Safe checks: default package built, desktop app component present, audio-driver component absent, distribution has no audio-driver references, and package was not installed.

## 2026-06-09 App-Only Installer Validator Run

- Run ID: `20260608T220154Z`
- Timestamp: `2026-06-08T22:01:54Z`
- Commit: `aea0704`
- macOS: `26.5`
- Hardware: `Mac15,10`
- Mode: `--installer-app-only`
- Package: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/2brain-rec-local.pkg`
- Component directory: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/components`
- Validator result: `passed`
- Safe checks: default package built, desktop app component present, audio-driver component absent, distribution has no audio-driver references, and package was not installed.

## 2026-06-09 App-Only Installer Validator Run

- Run ID: `20260608T220926Z`
- Timestamp: `2026-06-08T22:09:26Z`
- Commit: `3680653`
- macOS: `26.5`
- Hardware: `Mac15,10`
- Mode: `--installer-app-only`
- Package: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/2brain-rec-local.pkg`
- Component directory: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/components`
- Validator result: `passed`
- Safe checks: default package built, desktop app component present, audio-driver component absent, distribution has no audio-driver references, and package was not installed.

## 2026-06-09 App-Only Installer Validator Run

- Run ID: `20260608T223000Z`
- Timestamp: `2026-06-08T22:30:00Z`
- Commit: `041bb01`
- macOS: `26.5`
- Hardware: `Mac15,10`
- Mode: `--installer-app-only`
- Package: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/2brain-rec-local.pkg`
- Component directory: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/components`
- Validator result: `passed`
- Safe checks: default package built, desktop app component present, audio-driver component absent, distribution has no audio-driver references, and package was not installed.

## 2026-06-09 App-Only Installer Validator Run

- Run ID: `20260608T223205Z`
- Timestamp: `2026-06-08T22:32:05Z`
- Commit: `041bb01`
- macOS: `26.5`
- Hardware: `Mac15,10`
- Mode: `--installer-app-only`
- Package: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/2brain-rec-local.pkg`
- Component directory: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/components`
- Validator result: `passed`
- Safe checks: default package built, desktop app component present, audio-driver component absent, distribution has no audio-driver references, and package was not installed.

## 2026-06-09 App-Only Installer Validator Run

- Run ID: `20260608T223735Z`
- Timestamp: `2026-06-08T22:37:35Z`
- Commit: `28cf289`
- macOS: `26.5`
- Hardware: `Mac15,10`
- Mode: `--installer-app-only`
- Package: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/2brain-rec-local.pkg`
- Component directory: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/components`
- Validator result: `passed`
- Safe checks: default package built, desktop app component present, audio-driver component absent, distribution has no audio-driver references, and package was not installed.

## 2026-06-09 App-Only Installer Validator Run

- Run ID: `20260608T224258Z`
- Timestamp: `2026-06-08T22:42:58Z`
- Commit: `f6d4300`
- macOS: `26.5`
- Hardware: `Mac15,10`
- Mode: `--installer-app-only`
- Package: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/2brain-rec-local.pkg`
- Component directory: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/components`
- Validator result: `passed`
- Safe checks: default package built, desktop app component present, audio-driver component absent, distribution has no audio-driver references, and package was not installed.

## 2026-06-09 App-Only Installer Validator Run

- Run ID: `20260608T224826Z`
- Timestamp: `2026-06-08T22:48:26Z`
- Commit: `c5e7175`
- macOS: `26.5`
- Hardware: `Mac15,10`
- Mode: `--installer-app-only`
- Package: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/2brain-rec-local.pkg`
- Component directory: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/components`
- Validator result: `passed`
- Safe checks: default package built, desktop app component present, audio-driver component absent, distribution has no audio-driver references, and package was not installed.

## 2026-06-09 App-Only Installer Validator Run

- Run ID: `20260608T225322Z`
- Timestamp: `2026-06-08T22:53:22Z`
- Commit: `042055e`
- macOS: `26.5`
- Hardware: `Mac15,10`
- Mode: `--installer-app-only`
- Package: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/2brain-rec-local.pkg`
- Component directory: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/components`
- Validator result: `passed`
- Safe checks: default package built, desktop app component present, audio-driver component absent, distribution has no audio-driver references, and package was not installed.

## 2026-06-09 App-Only Installer Validator Run

- Run ID: `20260608T225852Z`
- Timestamp: `2026-06-08T22:58:52Z`
- Commit: `566aebc`
- macOS: `26.5`
- Hardware: `Mac15,10`
- Mode: `--installer-app-only`
- Package: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/2brain-rec-local.pkg`
- Component directory: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/components`
- Validator result: `passed`
- Safe checks: default package built, desktop app component present, audio-driver component absent, distribution has no audio-driver references, and package was not installed.

## 2026-06-09 App-Only Installer Validator Run

- Run ID: `20260608T230530Z`
- Timestamp: `2026-06-08T23:05:30Z`
- Commit: `f7a7454`
- macOS: `26.5`
- Hardware: `Mac15,10`
- Mode: `--installer-app-only`
- Package: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/2brain-rec-local.pkg`
- Component directory: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/components`
- Validator result: `passed`
- Safe checks: default package built, desktop app component present, audio-driver component absent, distribution has no audio-driver references, and package was not installed.

## 2026-06-09 App-Only Installer Validator Run

- Run ID: `20260608T231622Z`
- Timestamp: `2026-06-08T23:16:22Z`
- Commit: `0eebcd5`
- macOS: `26.5`
- Hardware: `Mac15,10`
- Mode: `--installer-app-only`
- Package: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/2brain-rec-local.pkg`
- Component directory: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/components`
- Validator result: `passed`
- Safe checks: default package built, desktop app component present, audio-driver component absent, distribution has no audio-driver references, and package was not installed.

## 2026-06-09 App-Only Installer Validator Run

- Run ID: `20260608T232309Z`
- Timestamp: `2026-06-08T23:23:09Z`
- Commit: `31b6b8b`
- macOS: `26.5`
- Hardware: `Mac15,10`
- Mode: `--installer-app-only`
- Package: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/2brain-rec-local.pkg`
- Component directory: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/components`
- Validator result: `passed`
- Safe checks: default package built, desktop app component present, audio-driver component absent, distribution has no audio-driver references, and package was not installed.

## 2026-06-09 App-Only Installer Validator Run

- Run ID: `20260608T232859Z`
- Timestamp: `2026-06-08T23:28:59Z`
- Commit: `3728bfb`
- macOS: `26.5`
- Hardware: `Mac15,10`
- Mode: `--installer-app-only`
- Package: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/2brain-rec-local.pkg`
- Component directory: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/components`
- Validator result: `passed`
- Safe checks: default package built, desktop app component present, audio-driver component absent, distribution has no audio-driver references, and package was not installed.
