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

## 2026-06-09 App-Only Installer Validator Run

- Run ID: `20260608T233518Z`
- Timestamp: `2026-06-08T23:35:18Z`
- Commit: `ff7ae0a`
- macOS: `26.5`
- Hardware: `Mac15,10`
- Mode: `--installer-app-only`
- Package: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/2brain-rec-local.pkg`
- Component directory: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/components`
- Validator result: `passed`
- Safe checks: default package built, desktop app component present, audio-driver component absent, distribution has no audio-driver references, and package was not installed.

## 2026-06-09 App-Only Installer Validator Run

- Run ID: `20260608T234416Z`
- Timestamp: `2026-06-08T23:44:16Z`
- Commit: `d2b7521`
- macOS: `26.5`
- Hardware: `Mac15,10`
- Mode: `--installer-app-only`
- Package: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/2brain-rec-local.pkg`
- Component directory: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/components`
- Validator result: `passed`
- Safe checks: default package built, desktop app component present, audio-driver component absent, distribution has no audio-driver references, and package was not installed.

## 2026-06-09 App-Only Installer Validator Run

- Run ID: `20260608T234743Z`
- Timestamp: `2026-06-08T23:47:43Z`
- Commit: `2ec1140`
- macOS: `26.5`
- Hardware: `Mac15,10`
- Mode: `--installer-app-only`
- Package: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/2brain-rec-local.pkg`
- Component directory: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/components`
- Validator result: `passed`
- Safe checks: default package built, desktop app component present, audio-driver component absent, distribution has no audio-driver references, and package was not installed.

## 2026-06-09 App-Only Installer Validator Run

- Run ID: `20260608T235158Z`
- Timestamp: `2026-06-08T23:51:58Z`
- Commit: `2ec1140`
- macOS: `26.5`
- Hardware: `Mac15,10`
- Mode: `--installer-app-only`
- Package: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/2brain-rec-local.pkg`
- Component directory: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/components`
- Validator result: `passed`
- Safe checks: default package built, desktop app component present, audio-driver component absent, distribution has no audio-driver references, and package was not installed.

## 2026-06-09 App-Only Installer Validator Run

- Run ID: `20260609T001541Z`
- Timestamp: `2026-06-09T00:15:41Z`
- Commit: `8b3fa87`
- macOS: `26.5`
- Hardware: `Mac15,10`
- Mode: `--installer-app-only`
- Package: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/2brain-rec-local.pkg`
- Component directory: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/components`
- Validator result: `passed`
- Safe checks: default package built, desktop app component present, audio-driver component absent, distribution has no audio-driver references, and package was not installed.

## 2026-06-09 App-Only Installer Validator Run

- Run ID: `20260609T002119Z`
- Timestamp: `2026-06-09T00:21:19Z`
- Commit: `33043b3`
- macOS: `26.5`
- Hardware: `Mac15,10`
- Mode: `--installer-app-only`
- Package: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/2brain-rec-local.pkg`
- Component directory: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/components`
- Validator result: `passed`
- Safe checks: default package built, desktop app component present, audio-driver component absent, distribution has no audio-driver references, and package was not installed.

## 2026-06-09 App-Only Installer Validator Run

- Run ID: `20260609T002734Z`
- Timestamp: `2026-06-09T00:27:34Z`
- Commit: `5d8ef0f`
- macOS: `26.5`
- Hardware: `Mac15,10`
- Mode: `--installer-app-only`
- Package: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/2brain-rec-local.pkg`
- Component directory: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/components`
- Validator result: `passed`
- Safe checks: default package built, desktop app component present, audio-driver component absent, distribution has no audio-driver references, and package was not installed.

## 2026-06-09 App-Only Installer Validator Run

- Run ID: `20260609T003327Z`
- Timestamp: `2026-06-09T00:33:27Z`
- Commit: `6b6b13b`
- macOS: `26.5`
- Hardware: `Mac15,10`
- Mode: `--installer-app-only`
- Package: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/2brain-rec-local.pkg`
- Component directory: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/components`
- Validator result: `passed`
- Safe checks: default package built, desktop app component present, audio-driver component absent, distribution has no audio-driver references, and package was not installed.

## 2026-06-09 App-Only Installer Validator Run

- Run ID: `20260609T004319Z`
- Timestamp: `2026-06-09T00:43:19Z`
- Commit: `5f458fe`
- macOS: `26.5`
- Hardware: `Mac15,10`
- Mode: `--installer-app-only`
- Package: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/2brain-rec-local.pkg`
- Component directory: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/components`
- Validator result: `passed`
- Safe checks: default package built, desktop app component present, audio-driver component absent, distribution has no audio-driver references, and package was not installed.

## 2026-06-09 App-Only Installer Validator Run

- Run ID: `20260609T005106Z`
- Timestamp: `2026-06-09T00:51:06Z`
- Commit: `ba9d6d9`
- macOS: `26.5`
- Hardware: `Mac15,10`
- Mode: `--installer-app-only`
- Package: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/2brain-rec-local.pkg`
- Component directory: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/components`
- Validator result: `passed`
- Safe checks: default package built, desktop app component present, audio-driver component absent, distribution has no audio-driver references, and package was not installed.

## 2026-06-09 App-Only Installer Validator Run

- Run ID: `20260609T005709Z`
- Timestamp: `2026-06-09T00:57:09Z`
- Commit: `7800c1f`
- macOS: `26.5`
- Hardware: `Mac15,10`
- Mode: `--installer-app-only`
- Package: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/2brain-rec-local.pkg`
- Component directory: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/components`
- Validator result: `passed`
- Safe checks: default package built, desktop app component present, audio-driver component absent, distribution has no audio-driver references, and package was not installed.

## 2026-06-09 App-Only Installer Validator Run

- Run ID: `20260609T010205Z`
- Timestamp: `2026-06-09T01:02:05Z`
- Commit: `6aaac3d`
- macOS: `26.5`
- Hardware: `Mac15,10`
- Mode: `--installer-app-only`
- Package: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/2brain-rec-local.pkg`
- Component directory: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/components`
- Validator result: `passed`
- Safe checks: default package built, desktop app component present, audio-driver component absent, distribution has no audio-driver references, and package was not installed.

## 2026-06-09 App-Only Installer Validator Run

- Run ID: `20260609T010713Z`
- Timestamp: `2026-06-09T01:07:13Z`
- Commit: `300074b`
- macOS: `26.5`
- Hardware: `Mac15,10`
- Mode: `--installer-app-only`
- Package: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/2brain-rec-local.pkg`
- Component directory: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/components`
- Validator result: `passed`
- Safe checks: default package built, desktop app component present, audio-driver component absent, distribution has no audio-driver references, and package was not installed.

## 2026-06-09 App-Only Installer Validator Run

- Run ID: `20260609T011633Z`
- Timestamp: `2026-06-09T01:16:33Z`
- Commit: `fabcba4`
- macOS: `26.5`
- Hardware: `Mac15,10`
- Mode: `--installer-app-only`
- Package: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/2brain-rec-local.pkg`
- Component directory: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/components`
- Validator result: `passed`
- Safe checks: default package built, desktop app component present, audio-driver component absent, distribution has no audio-driver references, and package was not installed.

## App-Only Installer Validator Run

- Run ID: `20260609T020629Z`
- Timestamp: `2026-06-09T02:06:29Z`
- Commit: `5480626`
- macOS: `26.5`
- Hardware: `Mac15,10`
- Mode: `--installer-app-only`
- Package: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/2brain-rec-local.pkg`
- Component directory: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/components`
- Validator result: `passed`
- Safe checks: default package built, desktop app component present, audio-driver component absent, distribution has no audio-driver references, and package was not installed.

## App-Only Installer Validator Run

- Run ID: `20260609T021540Z`
- Timestamp: `2026-06-09T02:15:40Z`
- Commit: `7a90c8f`
- macOS: `26.5`
- Hardware: `Mac15,10`
- Mode: `--installer-app-only`
- Package: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/2brain-rec-local.pkg`
- Component directory: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/components`
- Validator result: `passed`
- Safe checks: default package built, desktop app component present, audio-driver component absent, distribution has no audio-driver references, and package was not installed.

## App-Only Installer Validator Run

- Run ID: `20260609T022251Z`
- Timestamp: `2026-06-09T02:22:51Z`
- Commit: `2b11c31`
- macOS: `26.5`
- Hardware: `Mac15,10`
- Mode: `--installer-app-only`
- Package: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/2brain-rec-local.pkg`
- Component directory: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/components`
- Validator result: `passed`
- Safe checks: default package built, desktop app component present, audio-driver component absent, distribution has no audio-driver references, and package was not installed.

## App-Only Installer Validator Run

- Run ID: `20260609T023032Z`
- Timestamp: `2026-06-09T02:30:32Z`
- Commit: `d0265d0`
- macOS: `26.5`
- Hardware: `Mac15,10`
- Mode: `--installer-app-only`
- Package: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/2brain-rec-local.pkg`
- Component directory: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/components`
- Validator result: `passed`
- Safe checks: default package built, desktop app component present, audio-driver component absent, distribution has no audio-driver references, and package was not installed.

## App-Only Installer Validator Run

- Run ID: `20260609T023653Z`
- Timestamp: `2026-06-09T02:36:53Z`
- Commit: `d8085bb`
- macOS: `26.5`
- Hardware: `Mac15,10`
- Mode: `--installer-app-only`
- Package: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/2brain-rec-local.pkg`
- Component directory: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/components`
- Validator result: `passed`
- Safe checks: default package built, desktop app component present, audio-driver component absent, distribution has no audio-driver references, and package was not installed.

## App-Only Installer Validator Run

- Run ID: `20260609T024552Z`
- Timestamp: `2026-06-09T02:45:52Z`
- Commit: `d83e315`
- macOS: `26.5`
- Hardware: `Mac15,10`
- Mode: `--installer-app-only`
- Package: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/2brain-rec-local.pkg`
- Component directory: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/components`
- Validator result: `passed`
- Safe checks: default package built, desktop app component present, audio-driver component absent, distribution has no audio-driver references, and package was not installed.

## App-Only Installer Validator Run

- Run ID: `20260609T025234Z`
- Timestamp: `2026-06-09T02:52:34Z`
- Commit: `a2f5169`
- macOS: `26.5`
- Hardware: `Mac15,10`
- Mode: `--installer-app-only`
- Package: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/2brain-rec-local.pkg`
- Component directory: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/components`
- Validator result: `passed`
- Safe checks: default package built, desktop app component present, audio-driver component absent, distribution has no audio-driver references, and package was not installed.

## App-Only Installer Validator Run

- Run ID: `20260609T030039Z`
- Timestamp: `2026-06-09T03:00:39Z`
- Commit: `cbea541`
- macOS: `26.5`
- Hardware: `Mac15,10`
- Mode: `--installer-app-only`
- Package: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/2brain-rec-local.pkg`
- Component directory: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/components`
- Validator result: `passed`
- Safe checks: default package built, desktop app component present, audio-driver component absent, distribution has no audio-driver references, and package was not installed.

## App-Only Installer Validator Run

- Run ID: `20260609T040050Z`
- Timestamp: `2026-06-09T04:00:50Z`
- Commit: `c626768`
- macOS: `26.5`
- Hardware: `Mac15,10`
- Mode: `--installer-app-only`
- Package: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/2brain-rec-local.pkg`
- Component directory: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/components`
- Validator result: `passed`
- Safe checks: default package built, desktop app component present, audio-driver component absent, distribution has no audio-driver references, and package was not installed.

## App-Only Installer Validator Run

- Run ID: `20260609T040612Z`
- Timestamp: `2026-06-09T04:06:12Z`
- Commit: `8a27981`
- macOS: `26.5`
- Hardware: `Mac15,10`
- Mode: `--installer-app-only`
- Package: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/2brain-rec-local.pkg`
- Component directory: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/components`
- Validator result: `passed`
- Safe checks: default package built, desktop app component present, audio-driver component absent, distribution has no audio-driver references, and package was not installed.

## App-Only Installer Validator Run

- Run ID: `20260609T041052Z`
- Timestamp: `2026-06-09T04:10:52Z`
- Commit: `9a069fb`
- macOS: `26.5`
- Hardware: `Mac15,10`
- Mode: `--installer-app-only`
- Package: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/2brain-rec-local.pkg`
- Component directory: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/components`
- Validator result: `passed`
- Safe checks: default package built, desktop app component present, audio-driver component absent, distribution has no audio-driver references, and package was not installed.

## App-Only Installer Validator Run

- Run ID: `20260609T041608Z`
- Timestamp: `2026-06-09T04:16:08Z`
- Commit: `c26fdb9`
- macOS: `26.5`
- Hardware: `Mac15,10`
- Mode: `--installer-app-only`
- Package: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/2brain-rec-local.pkg`
- Component directory: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/components`
- Validator result: `passed`
- Safe checks: default package built, desktop app component present, audio-driver component absent, distribution has no audio-driver references, and package was not installed.

## App-Only Installer Validator Run

- Run ID: `20260609T042152Z`
- Timestamp: `2026-06-09T04:21:52Z`
- Commit: `f4cf5c3`
- macOS: `26.5`
- Hardware: `Mac15,10`
- Mode: `--installer-app-only`
- Package: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/2brain-rec-local.pkg`
- Component directory: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/components`
- Validator result: `passed`
- Safe checks: default package built, desktop app component present, audio-driver component absent, distribution has no audio-driver references, and package was not installed.

## App-Only Installer Validator Run

- Run ID: `20260609T042704Z`
- Timestamp: `2026-06-09T04:27:04Z`
- Commit: `36f5516`
- macOS: `26.5`
- Hardware: `Mac15,10`
- Mode: `--installer-app-only`
- Package: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/2brain-rec-local.pkg`
- Component directory: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/components`
- Validator result: `passed`
- Safe checks: default package built, desktop app component present, audio-driver component absent, distribution has no audio-driver references, and package was not installed.

## App-Only Installer Validator Run

- Run ID: `20260609T042956Z`
- Timestamp: `2026-06-09T04:29:56Z`
- Commit: `36f5516`
- macOS: `26.5`
- Hardware: `Mac15,10`
- Mode: `--installer-app-only`
- Package: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/2brain-rec-local.pkg`
- Component directory: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/components`
- Validator result: `passed`
- Safe checks: default package built, desktop app component present, audio-driver component absent, distribution has no audio-driver references, and package was not installed.

## App-Only Installer Validator Run

- Run ID: `20260609T043421Z`
- Timestamp: `2026-06-09T04:34:21Z`
- Commit: `716f3be`
- macOS: `26.5`
- Hardware: `Mac15,10`
- Mode: `--installer-app-only`
- Package: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/2brain-rec-local.pkg`
- Component directory: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/components`
- Validator result: `passed`
- Safe checks: default package built, desktop app component present, audio-driver component absent, distribution has no audio-driver references, and package was not installed.

## App-Only Installer Validator Run

- Run ID: `20260609T043853Z`
- Timestamp: `2026-06-09T04:38:53Z`
- Commit: `fbbfe30`
- macOS: `26.5`
- Hardware: `Mac15,10`
- Mode: `--installer-app-only`
- Package: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/2brain-rec-local.pkg`
- Component directory: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/components`
- Validator result: `passed`
- Safe checks: default package built, desktop app component present, audio-driver component absent, distribution has no audio-driver references, and package was not installed.

## App-Only Installer Validator Run

- Run ID: `20260609T044332Z`
- Timestamp: `2026-06-09T04:43:32Z`
- Commit: `8af9e20`
- macOS: `26.5`
- Hardware: `Mac15,10`
- Mode: `--installer-app-only`
- Package: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/2brain-rec-local.pkg`
- Component directory: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/components`
- Validator result: `passed`
- Safe checks: default package built, desktop app component present, audio-driver component absent, distribution has no audio-driver references, and package was not installed.

## App-Only Installer Validator Run

- Run ID: `20260609T044731Z`
- Timestamp: `2026-06-09T04:47:31Z`
- Commit: `27a6936`
- macOS: `26.5`
- Hardware: `Mac15,10`
- Mode: `--installer-app-only`
- Package: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/2brain-rec-local.pkg`
- Component directory: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/components`
- Validator result: `passed`
- Safe checks: default package built, desktop app component present, audio-driver component absent, distribution has no audio-driver references, and package was not installed.

## App-Only Installer Validator Run

- Run ID: `20260609T045149Z`
- Timestamp: `2026-06-09T04:51:49Z`
- Commit: `ecc849a`
- macOS: `26.5`
- Hardware: `Mac15,10`
- Mode: `--installer-app-only`
- Package: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/2brain-rec-local.pkg`
- Component directory: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/components`
- Validator result: `passed`
- Safe checks: default package built, desktop app component present, audio-driver component absent, distribution has no audio-driver references, and package was not installed.

## App-Only Installer Validator Run

- Run ID: `20260609T045604Z`
- Timestamp: `2026-06-09T04:56:04Z`
- Commit: `5c5f4f6`
- macOS: `26.5`
- Hardware: `Mac15,10`
- Mode: `--installer-app-only`
- Package: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/2brain-rec-local.pkg`
- Component directory: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/components`
- Validator result: `passed`
- Safe checks: default package built, desktop app component present, audio-driver component absent, distribution has no audio-driver references, and package was not installed.

## App-Only Installer Validator Run

- Run ID: `20260609T050045Z`
- Timestamp: `2026-06-09T05:00:45Z`
- Commit: `ba11af9`
- macOS: `26.5`
- Hardware: `Mac15,10`
- Mode: `--installer-app-only`
- Package: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/2brain-rec-local.pkg`
- Component directory: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/components`
- Validator result: `passed`
- Safe checks: default package built, desktop app component present, audio-driver component absent, distribution has no audio-driver references, and package was not installed.

## App-Only Installer Validator Run

- Run ID: `20260609T050426Z`
- Timestamp: `2026-06-09T05:04:26Z`
- Commit: `6194692`
- macOS: `26.5`
- Hardware: `Mac15,10`
- Mode: `--installer-app-only`
- Package: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/2brain-rec-local.pkg`
- Component directory: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/components`
- Validator result: `passed`
- Safe checks: default package built, desktop app component present, audio-driver component absent, distribution has no audio-driver references, and package was not installed.

## App-Only Installer Validator Run

- Run ID: `20260609T050828Z`
- Timestamp: `2026-06-09T05:08:28Z`
- Commit: `8811b80`
- macOS: `26.5`
- Hardware: `Mac15,10`
- Mode: `--installer-app-only`
- Package: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/2brain-rec-local.pkg`
- Component directory: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/components`
- Validator result: `passed`
- Safe checks: default package built, desktop app component present, audio-driver component absent, distribution has no audio-driver references, and package was not installed.

## App-Only Installer Validator Run

- Run ID: `20260609T051349Z`
- Timestamp: `2026-06-09T05:13:49Z`
- Commit: `edbe621`
- macOS: `26.5`
- Hardware: `Mac15,10`
- Mode: `--installer-app-only`
- Package: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/2brain-rec-local.pkg`
- Component directory: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/components`
- Validator result: `passed`
- Safe checks: default package built, desktop app component present, audio-driver component absent, distribution has no audio-driver references, and package was not installed.

## App-Only Installer Validator Run

- Run ID: `20260609T051747Z`
- Timestamp: `2026-06-09T05:17:47Z`
- Commit: `8aeb76e`
- macOS: `26.5`
- Hardware: `Mac15,10`
- Mode: `--installer-app-only`
- Package: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/2brain-rec-local.pkg`
- Component directory: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/components`
- Validator result: `passed`
- Safe checks: default package built, desktop app component present, audio-driver component absent, distribution has no audio-driver references, and package was not installed.

## App-Only Installer Validator Run

- Run ID: `20260609T052143Z`
- Timestamp: `2026-06-09T05:21:43Z`
- Commit: `178532e`
- macOS: `26.5`
- Hardware: `Mac15,10`
- Mode: `--installer-app-only`
- Package: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/2brain-rec-local.pkg`
- Component directory: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/components`
- Validator result: `passed`
- Safe checks: default package built, desktop app component present, audio-driver component absent, distribution has no audio-driver references, and package was not installed.

## App-Only Installer Validator Run

- Run ID: `20260609T052833Z`
- Timestamp: `2026-06-09T05:28:33Z`
- Commit: `201d207`
- macOS: `26.5`
- Hardware: `Mac15,10`
- Mode: `--installer-app-only`
- Package: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/2brain-rec-local.pkg`
- Component directory: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/components`
- Validator result: `passed`
- Safe checks: default package built, desktop app component present, audio-driver component absent, distribution has no audio-driver references, and package was not installed.

## App-Only Installer Validator Run

- Run ID: `20260609T053253Z`
- Timestamp: `2026-06-09T05:32:53Z`
- Commit: `17e7010`
- macOS: `26.5`
- Hardware: `Mac15,10`
- Mode: `--installer-app-only`
- Package: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/2brain-rec-local.pkg`
- Component directory: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/components`
- Validator result: `passed`
- Safe checks: default package built, desktop app component present, audio-driver component absent, distribution has no audio-driver references, and package was not installed.

## App-Only Installer Validator Run

- Run ID: `20260609T054313Z`
- Timestamp: `2026-06-09T05:43:13Z`
- Commit: `d3942a2`
- macOS: `26.5`
- Hardware: `Mac15,10`
- Mode: `--installer-app-only`
- Package: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/2brain-rec-local.pkg`
- Component directory: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/components`
- Validator result: `passed`
- Safe checks: default package built, desktop app component present, audio-driver component absent, distribution has no audio-driver references, and package was not installed.

## App-Only Installer Validator Run

- Run ID: `20260609T054655Z`
- Timestamp: `2026-06-09T05:46:55Z`
- Commit: `6f5d771`
- macOS: `26.5`
- Hardware: `Mac15,10`
- Mode: `--installer-app-only`
- Package: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/2brain-rec-local.pkg`
- Component directory: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/components`
- Validator result: `passed`
- Safe checks: default package built, desktop app component present, audio-driver component absent, distribution has no audio-driver references, and package was not installed.

## App-Only Installer Validator Run

- Run ID: `20260609T061149Z`
- Timestamp: `2026-06-09T06:11:49Z`
- Commit: `6f5d771`
- macOS: `26.5`
- Hardware: `Mac15,10`
- Mode: `--installer-app-only`
- Package: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/2brain-rec-local.pkg`
- Component directory: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/components`
- Validator result: `passed`
- Safe checks: default package built, desktop app component present, audio-driver component absent, distribution has no audio-driver references, and package was not installed.

## App-Only Installer Validator Run

- Run ID: `20260609T063430Z`
- Timestamp: `2026-06-09T06:34:30Z`
- Commit: `05b548c`
- macOS: `26.5`
- Hardware: `Mac15,10`
- Mode: `--installer-app-only`
- Package: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/2brain-rec-local.pkg`
- Component directory: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/components`
- Validator result: `passed`
- Safe checks: default package built, desktop app component present, audio-driver component absent, distribution has no audio-driver references, and package was not installed.

## App-Only Installer Validator Run

- Run ID: `20260609T064256Z`
- Timestamp: `2026-06-09T06:42:56Z`
- Commit: `54c7733`
- macOS: `26.5`
- Hardware: `Mac15,10`
- Mode: `--installer-app-only`
- Package: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/2brain-rec-local.pkg`
- Component directory: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/components`
- Validator result: `passed`
- Safe checks: default package built, desktop app component present, audio-driver component absent, distribution has no audio-driver references, and package was not installed.

## App-Only Installer Validator Run

- Run ID: `20260609T064442Z`
- Timestamp: `2026-06-09T06:44:42Z`
- Commit: `54c7733`
- macOS: `26.5`
- Hardware: `Mac15,10`
- Mode: `--installer-app-only`
- Package: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/2brain-rec-local.pkg`
- Component directory: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/components`
- Validator result: `passed`
- Safe checks: default package built, desktop app component present, audio-driver component absent, distribution has no audio-driver references, and package was not installed.

## App-Only Installer Validator Run

- Run ID: `20260609T064513Z`
- Timestamp: `2026-06-09T06:45:13Z`
- Commit: `54c7733`
- macOS: `26.5`
- Hardware: `Mac15,10`
- Mode: `--installer-app-only`
- Package: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/2brain-rec-local.pkg`
- Component directory: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/components`
- Validator result: `blocked`
- Reason: default local package is not app-only.
- Findings:
  - desktop app package payload contains AppleDouble or Finder sidecar files
  - payload sidecar: ./Applications/2brain Rec.app/Contents/_CodeSignature/._CodeResources
  - payload sidecar: ./Applications/2brain Rec.app/Contents/.__CodeSignature
  - payload sidecar: ./Applications/2brain Rec.app/Contents/MacOS/._2brain Rec
  - payload sidecar: ./Applications/2brain Rec.app/Contents/._MacOS
  - payload sidecar: ./Applications/2brain Rec.app/Contents/._Resources
  - payload sidecar: ./Applications/2brain Rec.app/Contents/._Info.plist
  - payload sidecar: ./Applications/2brain Rec.app/._Contents
  - payload sidecar: ./Applications/._2brain Rec.app
  - payload sidecar: ./._Applications
- Build output tail:

```text
Building for production...
[0/2] Write swift-version--1AB21518FC5DEDBE.txt
Build of product 'TwoBrainRecApp' complete! (0.12s)
Using ad-hoc app signing for local development because Developer Tools Security is enabled.
/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/RecApp/.build/2brain Rec.app: replacing existing signature
pkgbuild: Inferring bundle components from contents of /Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/stage/app
pkgbuild: Adding component at Applications/2brain Rec.app
pkgbuild: Wrote package to /Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/components/2brain-rec-desktop-app.pkg
productbuild: Wrote product to /Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/2brain-rec-local.pkg
/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/2brain-rec-local.pkg
```

## App-Only Installer Validator Run

- Run ID: `20260609T064726Z`
- Timestamp: `2026-06-09T06:47:26Z`
- Commit: `54c7733`
- macOS: `26.5`
- Hardware: `Mac15,10`
- Mode: `--installer-app-only`
- Package: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/2brain-rec-local.pkg`
- Component directory: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/components`
- Validator result: `passed`
- Safe checks: default package built, desktop app component present, audio-driver component absent, distribution has no audio-driver references, staging root has no Finder sidecar files, and package was not installed.

## App-Only Installer Validator Run

- Run ID: `20260609T064741Z`
- Timestamp: `2026-06-09T06:47:41Z`
- Commit: `54c7733`
- macOS: `26.5`
- Hardware: `Mac15,10`
- Mode: `--installer-app-only`
- Package: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/2brain-rec-local.pkg`
- Component directory: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/components`
- Validator result: `passed`
- Safe checks: default package built, desktop app component present, audio-driver component absent, distribution has no audio-driver references, staging root has no Finder sidecar files, and package was not installed.

## App-Only Installer Validator Run

- Run ID: `20260609T065627Z`
- Timestamp: `2026-06-09T06:56:27Z`
- Commit: `1732ce3`
- macOS: `26.5`
- Hardware: `Mac15,10`
- Mode: `--installer-app-only`
- Package: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/2brain-rec-local.pkg`
- Component directory: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/components`
- Validator result: `passed`
- Safe checks: default package built, desktop app component present, audio-driver component absent, distribution has no audio-driver references, staging root has no Finder sidecar files, and package was not installed.

## App-Only Installer Validator Run

- Run ID: `20260609T070550Z`
- Timestamp: `2026-06-09T07:05:50Z`
- Commit: `e33cdf8`
- macOS: `26.5`
- Hardware: `Mac15,10`
- Mode: `--installer-app-only`
- Package: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/2brain-rec-local.pkg`
- Component directory: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/components`
- Validator result: `passed`
- Safe checks: default package built, desktop app component present, audio-driver component absent, distribution has no audio-driver references, staging root has no Finder sidecar files, and package was not installed.

## App-Only Installer Validator Run

- Run ID: `20260609T070905Z`
- Timestamp: `2026-06-09T07:09:05Z`
- Commit: `e33cdf8`
- macOS: `26.5`
- Hardware: `Mac15,10`
- Mode: `--installer-app-only`
- Package: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/2brain-rec-local.pkg`
- Component directory: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/components`
- Validator result: `passed`
- Safe checks: default package built, desktop app component present, audio-driver component absent, distribution has no audio-driver references, staging root has no Finder sidecar files, and package was not installed.

## App-Only Installer Validator Run

- Run ID: `20260609T071800Z`
- Timestamp: `2026-06-09T07:18:00Z`
- Commit: `2ee186e`
- macOS: `26.5`
- Hardware: `Mac15,10`
- Mode: `--installer-app-only`
- Package: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/2brain-rec-local.pkg`
- Component directory: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/components`
- Validator result: `passed`
- Safe checks: default package built, desktop app component present, audio-driver component absent, distribution has no audio-driver references, staging root has no Finder sidecar files, and package was not installed.

## App-Only Installer Validator Run

- Run ID: `20260609T072500Z`
- Timestamp: `2026-06-09T07:25:00Z`
- Commit: `74a5eea`
- macOS: `26.5`
- Hardware: `Mac15,10`
- Mode: `--installer-app-only`
- Package: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/2brain-rec-local.pkg`
- Component directory: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/components`
- Validator result: `passed`
- Safe checks: default package built, desktop app component present, audio-driver component absent, distribution has no audio-driver references, staging root has no Finder sidecar files, and package was not installed.

## App-Only Installer Validator Run

- Run ID: `20260609T073258Z`
- Timestamp: `2026-06-09T07:32:58Z`
- Commit: `249f281`
- macOS: `26.5`
- Hardware: `Mac15,10`
- Mode: `--installer-app-only`
- Package: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/2brain-rec-local.pkg`
- Component directory: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/components`
- Validator result: `passed`
- Safe checks: default package built, desktop app component present, audio-driver component absent, distribution has no audio-driver references, staging root has no Finder sidecar files, and package was not installed.

## App-Only Installer Validator Run

- Run ID: `20260609T074259Z`
- Timestamp: `2026-06-09T07:42:59Z`
- Commit: `82202e6`
- macOS: `26.5`
- Hardware: `Mac15,10`
- Mode: `--installer-app-only`
- Package: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/2brain-rec-local.pkg`
- Component directory: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/components`
- Validator result: `passed`
- Safe checks: default package built, desktop app component present, audio-driver component absent, distribution has no audio-driver references, staging root has no Finder sidecar files, and package was not installed.

## App-Only Installer Validator Run

- Run ID: `20260609T075118Z`
- Timestamp: `2026-06-09T07:51:18Z`
- Commit: `de28198`
- macOS: `26.5`
- Hardware: `Mac15,10`
- Mode: `--installer-app-only`
- Package: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/2brain-rec-local.pkg`
- Component directory: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/components`
- Validator result: `passed`
- Safe checks: default package built, desktop app component present, audio-driver component absent, distribution has no audio-driver references, staging root has no Finder sidecar files, and package was not installed.

## App-Only Installer Validator Run

- Run ID: `20260609T080116Z`
- Timestamp: `2026-06-09T08:01:16Z`
- Commit: `f73493e`
- macOS: `26.5`
- Hardware: `Mac15,10`
- Mode: `--installer-app-only`
- Package: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/2brain-rec-local.pkg`
- Component directory: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/components`
- Validator result: `passed`
- Safe checks: default package built, desktop app component present, audio-driver component absent, distribution has no audio-driver references, staging root has no Finder sidecar files, and package was not installed.

## App-Only Installer Validator Run

- Run ID: `20260609T080737Z`
- Timestamp: `2026-06-09T08:07:37Z`
- Commit: `07df98d`
- macOS: `26.5`
- Hardware: `Mac15,10`
- Mode: `--installer-app-only`
- Package: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/2brain-rec-local.pkg`
- Component directory: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/components`
- Validator result: `passed`
- Safe checks: default package built, desktop app component present, audio-driver component absent, distribution has no audio-driver references, staging root has no Finder sidecar files, and package was not installed.

## App-Only Installer Validator Run

- Run ID: `20260609T081409Z`
- Timestamp: `2026-06-09T08:14:09Z`
- Commit: `78be59e`
- macOS: `26.5`
- Hardware: `Mac15,10`
- Mode: `--installer-app-only`
- Package: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/2brain-rec-local.pkg`
- Component directory: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/components`
- Validator result: `passed`
- Safe checks: default package built, desktop app component present, audio-driver component absent, distribution has no audio-driver references, staging root has no Finder sidecar files, and package was not installed.

## App-Only Installer Validator Run

- Run ID: `20260609T081940Z`
- Timestamp: `2026-06-09T08:19:40Z`
- Commit: `97db39f`
- macOS: `26.5`
- Hardware: `Mac15,10`
- Mode: `--installer-app-only`
- Package: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/2brain-rec-local.pkg`
- Component directory: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/components`
- Validator result: `passed`
- Safe checks: default package built, desktop app component present, audio-driver component absent, distribution has no audio-driver references, staging root has no Finder sidecar files, and package was not installed.

## App-Only Installer Validator Run

- Run ID: `20260609T082523Z`
- Timestamp: `2026-06-09T08:25:23Z`
- Commit: `b97aa74`
- macOS: `26.5`
- Hardware: `Mac15,10`
- Mode: `--installer-app-only`
- Package: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/2brain-rec-local.pkg`
- Component directory: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/components`
- Validator result: `passed`
- Safe checks: default package built, desktop app component present, audio-driver component absent, distribution has no audio-driver references, staging root has no Finder sidecar files, and package was not installed.

## App-Only Installer Validator Run

- Run ID: `20260609T083110Z`
- Timestamp: `2026-06-09T08:31:10Z`
- Commit: `ecf0e51`
- macOS: `26.5`
- Hardware: `Mac15,10`
- Mode: `--installer-app-only`
- Package: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/2brain-rec-local.pkg`
- Component directory: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/components`
- Validator result: `passed`
- Safe checks: default package built, desktop app component present, audio-driver component absent, distribution has no audio-driver references, staging root has no Finder sidecar files, and package was not installed.

## App-Only Installer Validator Run

- Run ID: `20260609T083738Z`
- Timestamp: `2026-06-09T08:37:38Z`
- Commit: `a23c311`
- macOS: `26.5`
- Hardware: `Mac15,10`
- Mode: `--installer-app-only`
- Package: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/2brain-rec-local.pkg`
- Component directory: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/components`
- Validator result: `passed`
- Safe checks: default package built, desktop app component present, audio-driver component absent, distribution has no audio-driver references, staging root has no Finder sidecar files, and package was not installed.

## App-Only Installer Validator Run

- Run ID: `20260609T084054Z`
- Timestamp: `2026-06-09T08:40:54Z`
- Commit: `a23c311`
- macOS: `26.5`
- Hardware: `Mac15,10`
- Mode: `--installer-app-only`
- Package: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/2brain-rec-local.pkg`
- Component directory: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/components`
- Validator result: `passed`
- Safe checks: default package built, desktop app component present, audio-driver component absent, distribution has no audio-driver references, staging root has no Finder sidecar files, and package was not installed.

## App-Only Installer Validator Run

- Run ID: `20260609T084647Z`
- Timestamp: `2026-06-09T08:46:47Z`
- Commit: `d9aaeab`
- macOS: `26.5`
- Hardware: `Mac15,10`
- Mode: `--installer-app-only`
- Package: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/2brain-rec-local.pkg`
- Component directory: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/components`
- Validator result: `passed`
- Safe checks: default package built, desktop app component present, audio-driver component absent, distribution has no audio-driver references, staging root has no Finder sidecar files, and package was not installed.

## App-Only Installer Validator Run

- Run ID: `20260609T085327Z`
- Timestamp: `2026-06-09T08:53:27Z`
- Commit: `f0c96d7`
- macOS: `26.5`
- Hardware: `Mac15,10`
- Mode: `--installer-app-only`
- Package: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/2brain-rec-local.pkg`
- Component directory: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/components`
- Validator result: `passed`
- Safe checks: default package built, desktop app component present, audio-driver component absent, distribution has no audio-driver references, staging root has no Finder sidecar files, and package was not installed.

## App-Only Installer Validator Run

- Run ID: `20260609T090049Z`
- Timestamp: `2026-06-09T09:00:49Z`
- Commit: `e01db77`
- macOS: `26.5`
- Hardware: `Mac15,10`
- Mode: `--installer-app-only`
- Package: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/2brain-rec-local.pkg`
- Component directory: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/components`
- Validator result: `passed`
- Safe checks: default package built, desktop app component present, audio-driver component absent, distribution has no audio-driver references, staging root has no Finder sidecar files, and package was not installed.

## App-Only Installer Validator Run

- Run ID: `20260609T090659Z`
- Timestamp: `2026-06-09T09:06:59Z`
- Commit: `120f249`
- macOS: `26.5`
- Hardware: `Mac15,10`
- Mode: `--installer-app-only`
- Package: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/2brain-rec-local.pkg`
- Component directory: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/components`
- Validator result: `passed`
- Safe checks: default package built, desktop app component present, audio-driver component absent, distribution has no audio-driver references, staging root has no Finder sidecar files, and package was not installed.

## App-Only Installer Validator Run

- Run ID: `20260609T091233Z`
- Timestamp: `2026-06-09T09:12:33Z`
- Commit: `0e750b1`
- macOS: `26.5`
- Hardware: `Mac15,10`
- Mode: `--installer-app-only`
- Package: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/2brain-rec-local.pkg`
- Component directory: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/components`
- Validator result: `passed`
- Safe checks: default package built, desktop app component present, audio-driver component absent, distribution has no audio-driver references, staging root has no Finder sidecar files, and package was not installed.

## App-Only Installer Validator Run

- Run ID: `20260609T092042Z`
- Timestamp: `2026-06-09T09:20:42Z`
- Commit: `bdb39ab`
- macOS: `26.5`
- Hardware: `Mac15,10`
- Mode: `--installer-app-only`
- Package: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/2brain-rec-local.pkg`
- Component directory: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/components`
- Validator result: `passed`
- Safe checks: default package built, desktop app component present, audio-driver component absent, distribution has no audio-driver references, staging root has no Finder sidecar files, and package was not installed.

## App-Only Installer Validator Run

- Run ID: `20260609T092621Z`
- Timestamp: `2026-06-09T09:26:21Z`
- Commit: `b5bae41`
- macOS: `26.5`
- Hardware: `Mac15,10`
- Mode: `--installer-app-only`
- Package: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/2brain-rec-local.pkg`
- Component directory: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/components`
- Validator result: `passed`
- Safe checks: default package built, desktop app component present, audio-driver component absent, distribution has no audio-driver references, staging root has no Finder sidecar files, and package was not installed.

## App-Only Installer Validator Run

- Run ID: `20260609T092632Z`
- Timestamp: `2026-06-09T09:26:32Z`
- Commit: `b5bae41`
- macOS: `26.5`
- Hardware: `Mac15,10`
- Mode: `--installer-app-only`
- Package: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/2brain-rec-local.pkg`
- Component directory: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/components`
- Validator result: `passed`
- Safe checks: default package built, desktop app component present, audio-driver component absent, distribution has no audio-driver references, staging root has no Finder sidecar files, and package was not installed.

## App-Only Installer Validator Run

- Run ID: `20260609T093026Z`
- Timestamp: `2026-06-09T09:30:26Z`
- Commit: `b5bae41`
- macOS: `26.5`
- Hardware: `Mac15,10`
- Mode: `--installer-app-only`
- Package: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/2brain-rec-local.pkg`
- Component directory: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/components`
- Validator result: `passed`
- Safe checks: default package built, desktop app component present, audio-driver component absent, distribution has no audio-driver references, staging root has no Finder sidecar files, and package was not installed.

## App-Only Installer Validator Run

- Run ID: `20260609T093643Z`
- Timestamp: `2026-06-09T09:36:43Z`
- Commit: `b2df4b6`
- macOS: `26.5`
- Hardware: `Mac15,10`
- Mode: `--installer-app-only`
- Package: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/2brain-rec-local.pkg`
- Component directory: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/components`
- Validator result: `passed`
- Safe checks: default package built, desktop app component present, audio-driver component absent, distribution has no audio-driver references, staging root has no Finder sidecar files, and package was not installed.

## App-Only Installer Validator Run

- Run ID: `20260609T094135Z`
- Timestamp: `2026-06-09T09:41:35Z`
- Commit: `51685f3`
- macOS: `26.5`
- Hardware: `Mac15,10`
- Mode: `--installer-app-only`
- Package: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/2brain-rec-local.pkg`
- Component directory: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/components`
- Validator result: `passed`
- Safe checks: default package built, desktop app component present, audio-driver component absent, distribution has no audio-driver references, staging root has no Finder sidecar files, and package was not installed.

## App-Only Installer Validator Run

- Run ID: `20260609T094558Z`
- Timestamp: `2026-06-09T09:45:58Z`
- Commit: `4a10c73`
- macOS: `26.5`
- Hardware: `Mac15,10`
- Mode: `--installer-app-only`
- Package: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/2brain-rec-local.pkg`
- Component directory: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/components`
- Validator result: `passed`
- Safe checks: default package built, desktop app component present, audio-driver component absent, distribution has no audio-driver references, staging root has no Finder sidecar files, and package was not installed.

## App-Only Installer Validator Run

- Run ID: `20260609T095345Z`
- Timestamp: `2026-06-09T09:53:45Z`
- Commit: `140d176`
- macOS: `26.5`
- Hardware: `Mac15,10`
- Mode: `--installer-app-only`
- Package: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/2brain-rec-local.pkg`
- Component directory: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/components`
- Validator result: `passed`
- Safe checks: default package built, desktop app component present, audio-driver component absent, distribution has no audio-driver references, staging root has no Finder sidecar files, and package was not installed.

## App-Only Installer Validator Run

- Run ID: `20260609T095943Z`
- Timestamp: `2026-06-09T09:59:43Z`
- Commit: `a643c00`
- macOS: `26.5`
- Hardware: `Mac15,10`
- Mode: `--installer-app-only`
- Package: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/2brain-rec-local.pkg`
- Component directory: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/components`
- Validator result: `passed`
- Safe checks: default package built, desktop app component present, audio-driver component absent, distribution has no audio-driver references, staging root has no Finder sidecar files, and package was not installed.

## App-Only Installer Validator Run

- Run ID: `20260609T100625Z`
- Timestamp: `2026-06-09T10:06:25Z`
- Commit: `d5556f5`
- macOS: `26.5`
- Hardware: `Mac15,10`
- Mode: `--installer-app-only`
- Package: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/2brain-rec-local.pkg`
- Component directory: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/components`
- Validator result: `passed`
- Safe checks: default package built, desktop app component present, audio-driver component absent, distribution has no audio-driver references, staging root has no Finder sidecar files, and package was not installed.

## App-Only Installer Validator Run

- Run ID: `20260609T101309Z`
- Timestamp: `2026-06-09T10:13:09Z`
- Commit: `fd1e359`
- macOS: `26.5`
- Hardware: `Mac15,10`
- Mode: `--installer-app-only`
- Package: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/2brain-rec-local.pkg`
- Component directory: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/components`
- Validator result: `passed`
- Safe checks: default package built, desktop app component present, audio-driver component absent, distribution has no audio-driver references, staging root has no Finder sidecar files, and package was not installed.

## App-Only Installer Validator Run

- Run ID: `20260609T101719Z`
- Timestamp: `2026-06-09T10:17:19Z`
- Commit: `fd1e359`
- macOS: `26.5`
- Hardware: `Mac15,10`
- Mode: `--installer-app-only`
- Package: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/2brain-rec-local.pkg`
- Component directory: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/components`
- Validator result: `passed`
- Safe checks: default package built, desktop app component present, audio-driver component absent, distribution has no audio-driver references, staging root has no Finder sidecar files, and package was not installed.

## App-Only Installer Validator Run

- Run ID: `20260609T101911Z`
- Timestamp: `2026-06-09T10:19:11Z`
- Commit: `fd1e359`
- macOS: `26.5`
- Hardware: `Mac15,10`
- Mode: `--installer-app-only`
- Package: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/2brain-rec-local.pkg`
- Component directory: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/components`
- Validator result: `passed`
- Safe checks: default package built, desktop app component present, audio-driver component absent, distribution has no audio-driver references, staging root has no Finder sidecar files, and package was not installed.

## App-Only Installer Validator Run

- Run ID: `20260609T102527Z`
- Timestamp: `2026-06-09T10:25:27Z`
- Commit: `da2ca2c`
- macOS: `26.5`
- Hardware: `Mac15,10`
- Mode: `--installer-app-only`
- Package: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/2brain-rec-local.pkg`
- Component directory: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/components`
- Validator result: `passed`
- Safe checks: default package built, desktop app component present, audio-driver component absent, distribution has no audio-driver references, staging root has no Finder sidecar files, and package was not installed.

## App-Only Installer Validator Run

- Run ID: `20260609T124123Z`
- Timestamp: `2026-06-09T12:41:23Z`
- Commit: `0fa5027`
- macOS: `26.5`
- Hardware: `Mac15,10`
- Mode: `--installer-app-only`
- Package: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/2brain-rec-local.pkg`
- Component directory: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/components`
- Validator result: `passed`
- Safe checks: default package built, desktop app component present, audio-driver component absent, distribution has no audio-driver references, staging root has no Finder sidecar files, and package was not installed.

## App-Only Installer Validator Run

- Run ID: `20260609T132342Z`
- Timestamp: `2026-06-09T13:23:42Z`
- Commit: `54d561c`
- macOS: `26.5`
- Hardware: `Mac15,10`
- Mode: `--installer-app-only`
- Package: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/2brain-rec-local.pkg`
- Component directory: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/components`
- Validator result: `passed`
- Safe checks: default package built, desktop app component present, audio-driver component absent, distribution has no audio-driver references, staging root has no Finder sidecar files, and package was not installed.

## App-Only Installer Validator Run

- Run ID: `20260609T132622Z`
- Timestamp: `2026-06-09T13:26:22Z`
- Commit: `0c7ef5a`
- macOS: `26.5`
- Hardware: `Mac15,10`
- Mode: `--installer-app-only`
- Package: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/2brain-rec-local.pkg`
- Component directory: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/components`
- Validator result: `passed`
- Safe checks: default package built, desktop app component present, audio-driver component absent, distribution has no audio-driver references, staging root has no Finder sidecar files, and package was not installed.

## App-Only Installer Validator Run

- Run ID: `20260609T133420Z`
- Timestamp: `2026-06-09T13:34:20Z`
- Commit: `be0e402`
- macOS: `26.5`
- Hardware: `Mac15,10`
- Mode: `--installer-app-only`
- Package: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/2brain-rec-local.pkg`
- Component directory: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/components`
- Validator result: `blocked`
- Reason: default local package is not app-only.
- Findings:
  - default app-only package build failed
  - missing local product package
  - missing desktop app component package
- Build output tail:

```text
You have not agreed to the Xcode license agreements. Please run 'sudo xcodebuild -license' from within a Terminal window to review and agree to the Xcode and Apple SDKs license.
```

## App-Only Installer Validator Run

- Run ID: `20260609T133814Z`
- Timestamp: `2026-06-09T13:38:14Z`
- Commit: `be0e402`
- macOS: `26.5`
- Hardware: `Mac15,10`
- Mode: `--installer-app-only`
- Package: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/2brain-rec-local.pkg`
- Component directory: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/components`
- Validator result: `passed`
- Safe checks: default package built, desktop app component present, audio-driver component absent, distribution has no audio-driver references, staging root has no Finder sidecar files, and package was not installed.

## App-Only Installer Validator Run

- Run ID: `20260609T134743Z`
- Timestamp: `2026-06-09T13:47:43Z`
- Commit: `be0e402`
- macOS: `26.5`
- Hardware: `Mac15,10`
- Mode: `--installer-app-only`
- Package: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/2brain-rec-local.pkg`
- Component directory: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/components`
- Validator result: `passed`
- Safe checks: default package built, desktop app component present, audio-driver component absent, distribution has no audio-driver references, staging root has no Finder sidecar files, and package was not installed.

## App-Only Installer Validator Run

- Run ID: `20260609T135402Z`
- Timestamp: `2026-06-09T13:54:02Z`
- Commit: `f83ac11`
- macOS: `26.5`
- Hardware: `Mac15,10`
- Mode: `--installer-app-only`
- Package: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/2brain-rec-local.pkg`
- Component directory: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/components`
- Validator result: `passed`
- Safe checks: default package built, desktop app component present, audio-driver component absent, distribution has no audio-driver references, staging root has no Finder sidecar files, and package was not installed.

## App-Only Installer Validator Run

- Run ID: `20260609T140135Z`
- Timestamp: `2026-06-09T14:01:35Z`
- Commit: `f83ac11`
- macOS: `26.5`
- Hardware: `Mac15,10`
- Mode: `--installer-app-only`
- Package: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/2brain-rec-local.pkg`
- Component directory: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/components`
- Validator result: `passed`
- Safe checks: default package built, desktop app component present, audio-driver component absent, distribution has no audio-driver references, staging root has no Finder sidecar files, and package was not installed.

## App-Only Installer Validator Run

- Run ID: `20260609T140808Z`
- Timestamp: `2026-06-09T14:08:08Z`
- Commit: `4fe148b`
- macOS: `26.5`
- Hardware: `Mac15,10`
- Mode: `--installer-app-only`
- Package: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/2brain-rec-local.pkg`
- Component directory: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/components`
- Validator result: `passed`
- Safe checks: default package built, desktop app component present, audio-driver component absent, distribution has no audio-driver references, staging root has no Finder sidecar files, and package was not installed.

## App-Only Installer Validator Run

- Run ID: `20260609T141540Z`
- Timestamp: `2026-06-09T14:15:40Z`
- Commit: `4fe148b`
- macOS: `26.5`
- Hardware: `Mac15,10`
- Mode: `--installer-app-only`
- Package: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/2brain-rec-local.pkg`
- Component directory: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/components`
- Validator result: `passed`
- Safe checks: default package built, desktop app component present, audio-driver component absent, distribution has no audio-driver references, staging root has no Finder sidecar files, and package was not installed.

## App-Only Installer Validator Run

- Run ID: `20260609T142441Z`
- Timestamp: `2026-06-09T14:24:41Z`
- Commit: `6aa5096`
- macOS: `26.5`
- Hardware: `Mac15,10`
- Mode: `--installer-app-only`
- Package: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/2brain-rec-local.pkg`
- Component directory: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/components`
- Validator result: `passed`
- Safe checks: default package built, desktop app component present, audio-driver component absent, distribution has no audio-driver references, staging root has no Finder sidecar files, and package was not installed.

## App-Only Installer Validator Run

- Run ID: `20260609T142845Z`
- Timestamp: `2026-06-09T14:28:45Z`
- Commit: `6aa5096`
- macOS: `26.5`
- Hardware: `Mac15,10`
- Mode: `--installer-app-only`
- Package: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/2brain-rec-local.pkg`
- Component directory: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/components`
- Validator result: `passed`
- Safe checks: default package built, desktop app component present, audio-driver component absent, distribution has no audio-driver references, staging root has no Finder sidecar files, and package was not installed.

## App-Only Installer Validator Run

- Run ID: `20260609T142938Z`
- Timestamp: `2026-06-09T14:29:38Z`
- Commit: `6aa5096`
- macOS: `26.5`
- Hardware: `Mac15,10`
- Mode: `--installer-app-only`
- Package: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/2brain-rec-local.pkg`
- Component directory: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/components`
- Validator result: `passed`
- Safe checks: default package built, desktop app component present, audio-driver component absent, distribution has no audio-driver references, staging root has no Finder sidecar files, and package was not installed.

## App-Only Installer Validator Run

- Run ID: `20260609T144015Z`
- Timestamp: `2026-06-09T14:40:15Z`
- Commit: `c44cb14`
- macOS: `26.5`
- Hardware: `Mac15,10`
- Mode: `--installer-app-only`
- Package: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/2brain-rec-local.pkg`
- Component directory: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/components`
- Validator result: `passed`
- Safe checks: default package built, desktop app component present, audio-driver component absent, distribution has no audio-driver references, staging root has no Finder sidecar files, and package was not installed.

## App-Only Installer Validator Run

- Run ID: `20260609T144016Z`
- Timestamp: `2026-06-09T14:40:16Z`
- Commit: `c44cb14`
- macOS: `26.5`
- Hardware: `Mac15,10`
- Mode: `--installer-app-only`
- Package: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/2brain-rec-local.pkg`
- Component directory: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/components`
- Validator result: `passed`
- Safe checks: default package built, desktop app component present, audio-driver component absent, distribution has no audio-driver references, staging root has no Finder sidecar files, and package was not installed.

## App-Only Installer Validator Run

- Run ID: `20260609T145247Z`
- Timestamp: `2026-06-09T14:52:47Z`
- Commit: `c44cb14`
- macOS: `26.5`
- Hardware: `Mac15,10`
- Mode: `--installer-app-only`
- Package: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/2brain-rec-local.pkg`
- Component directory: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/components`
- Validator result: `passed`
- Safe checks: default package built, desktop app component present, audio-driver component absent, distribution has no audio-driver references, staging root has no Finder sidecar files, and package was not installed.

## App-Only Installer Validator Run

- Run ID: `20260609T145513Z`
- Timestamp: `2026-06-09T14:55:13Z`
- Commit: `c44cb14`
- macOS: `26.5`
- Hardware: `Mac15,10`
- Mode: `--installer-app-only`
- Package: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/2brain-rec-local.pkg`
- Component directory: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/components`
- Validator result: `passed`
- Safe checks: default package built, desktop app component present, audio-driver component absent, distribution has no audio-driver references, staging root has no Finder sidecar files, and package was not installed.

## App-Only Installer Validator Run

- Run ID: `20260609T145809Z`
- Timestamp: `2026-06-09T14:58:09Z`
- Commit: `c44cb14`
- macOS: `26.5`
- Hardware: `Mac15,10`
- Mode: `--installer-app-only`
- Package: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/2brain-rec-local.pkg`
- Component directory: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/components`
- Validator result: `passed`
- Safe checks: default package built, desktop app component present, audio-driver component absent, distribution has no audio-driver references, staging root has no Finder sidecar files, and package was not installed.

## App-Only Installer Validator Run

- Run ID: `20260609T151013Z`
- Timestamp: `2026-06-09T15:10:13Z`
- Commit: `5a3a074`
- macOS: `26.5`
- Hardware: `Mac15,10`
- Mode: `--installer-app-only`
- Package: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/2brain-rec-local.pkg`
- Component directory: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/components`
- Validator result: `passed`
- Safe checks: default package built, desktop app component present, audio-driver component absent, distribution has no audio-driver references, staging root has no Finder sidecar files, and package was not installed.

## App-Only Installer Validator Run

- Run ID: `20260609T151549Z`
- Timestamp: `2026-06-09T15:15:49Z`
- Commit: `3f669df`
- macOS: `26.5`
- Hardware: `Mac15,10`
- Mode: `--installer-app-only`
- Package: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/2brain-rec-local.pkg`
- Component directory: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/components`
- Validator result: `passed`
- Safe checks: default package built, desktop app component present, audio-driver component absent, distribution has no audio-driver references, staging root has no Finder sidecar files, and package was not installed.

## App-Only Installer Validator Run

- Run ID: `20260609T152108Z`
- Timestamp: `2026-06-09T15:21:08Z`
- Commit: `eec313b`
- macOS: `26.5`
- Hardware: `Mac15,10`
- Mode: `--installer-app-only`
- Package: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/2brain-rec-local.pkg`
- Component directory: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/components`
- Validator result: `passed`
- Safe checks: default package built, desktop app component present, audio-driver component absent, distribution has no audio-driver references, staging root has no Finder sidecar files, and package was not installed.

## App-Only Installer Validator Run

- Run ID: `20260610T093042Z`
- Timestamp: `2026-06-10T09:30:42Z`
- Commit: `c09e9f6`
- macOS: `26.5`
- Hardware: `Mac15,10`
- Mode: `--installer-app-only`
- Package: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/2brain-rec-local.pkg`
- Component directory: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/components`
- Validator result: `passed`
- Safe checks: default package built, desktop app component present, audio-driver component absent, distribution has no audio-driver references, staging root has no Finder sidecar files, and package was not installed.

## App-Only Installer Validator Run

- Run ID: `20260610T094041Z`
- Timestamp: `2026-06-10T09:40:41Z`
- Commit: `3fca17e`
- macOS: `26.5`
- Hardware: `Mac15,10`
- Mode: `--installer-app-only`
- Package: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/2brain-rec-local.pkg`
- Component directory: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/components`
- Validator result: `passed`
- Safe checks: default package built, desktop app component present, audio-driver component absent, distribution has no audio-driver references, staging root has no Finder sidecar files, and package was not installed.

## App-Only Installer Validator Run

- Run ID: `20260610T103309Z`
- Timestamp: `2026-06-10T10:33:09Z`
- Commit: `3fca17e`
- macOS: `26.5`
- Hardware: `Mac15,10`
- Mode: `--installer-app-only`
- Package: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/2brain-rec-local.pkg`
- Component directory: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/components`
- Validator result: `passed`
- Safe checks: default package built, desktop app component present, audio-driver component absent, distribution has no audio-driver references, staging root has no Finder sidecar files, and package was not installed.

## App-Only Installer Validator Run

- Run ID: `20260610T103642Z`
- Timestamp: `2026-06-10T10:36:42Z`
- Commit: `3fca17e`
- macOS: `26.5`
- Hardware: `Mac15,10`
- Mode: `--installer-app-only`
- Package: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/2brain-rec-local.pkg`
- Component directory: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/components`
- Validator result: `passed`
- Safe checks: default package built, desktop app component present, audio-driver component absent, distribution has no audio-driver references, staging root has no Finder sidecar files, and package was not installed.

## App-Only Installer Validator Run

- Run ID: `20260610T104344Z`
- Timestamp: `2026-06-10T10:43:44Z`
- Commit: `3fca17e`
- macOS: `26.5`
- Hardware: `Mac15,10`
- Mode: `--installer-app-only`
- Package: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/2brain-rec-local.pkg`
- Component directory: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/components`
- Validator result: `passed`
- Safe checks: default package built, desktop app component present, audio-driver component absent, distribution has no audio-driver references, staging root has no Finder sidecar files, and package was not installed.

## App-Only Installer Validator Run

- Run ID: `20260610T104512Z`
- Timestamp: `2026-06-10T10:45:12Z`
- Commit: `3fca17e`
- macOS: `26.5`
- Hardware: `Mac15,10`
- Mode: `--installer-app-only`
- Package: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/2brain-rec-local.pkg`
- Component directory: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/components`
- Validator result: `passed`
- Safe checks: default package built, desktop app component present, audio-driver component absent, distribution has no audio-driver references, staging root has no Finder sidecar files, and package was not installed.

## App-Only Installer Validator Run

- Run ID: `20260610T104524Z`
- Timestamp: `2026-06-10T10:45:24Z`
- Commit: `3fca17e`
- macOS: `26.5`
- Hardware: `Mac15,10`
- Mode: `--installer-app-only`
- Package: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/2brain-rec-local.pkg`
- Component directory: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/components`
- Validator result: `passed`
- Safe checks: default package built, desktop app component present, audio-driver component absent, distribution has no audio-driver references, staging root has no Finder sidecar files, and package was not installed.

## App-Only Installer Validator Run

- Run ID: `20260610T104856Z`
- Timestamp: `2026-06-10T10:48:56Z`
- Commit: `3fca17e`
- macOS: `26.5`
- Hardware: `Mac15,10`
- Mode: `--installer-app-only`
- Package: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/2brain-rec-local.pkg`
- Component directory: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/components`
- Validator result: `passed`
- Safe checks: default package built, desktop app component present, audio-driver component absent, distribution has no audio-driver references, staging root has no Finder sidecar files, and package was not installed.

## App-Only Installer Validator Run

- Run ID: `20260610T105235Z`
- Timestamp: `2026-06-10T10:52:35Z`
- Commit: `3fca17e`
- macOS: `26.5`
- Hardware: `Mac15,10`
- Mode: `--installer-app-only`
- Package: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/2brain-rec-local.pkg`
- Component directory: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/components`
- Validator result: `passed`
- Safe checks: default package built, desktop app component present, audio-driver component absent, distribution has no audio-driver references, staging root has no Finder sidecar files, and package was not installed.

## App-Only Installer Validator Run

- Run ID: `20260610T105740Z`
- Timestamp: `2026-06-10T10:57:40Z`
- Commit: `3fca17e`
- macOS: `26.5`
- Hardware: `Mac15,10`
- Mode: `--installer-app-only`
- Package: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/2brain-rec-local.pkg`
- Component directory: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/components`
- Validator result: `passed`
- Safe checks: default package built, desktop app component present, audio-driver component absent, distribution has no audio-driver references, staging root has no Finder sidecar files, and package was not installed.

## App-Only Installer Validator Run

- Run ID: `20260610T105747Z`
- Timestamp: `2026-06-10T10:57:47Z`
- Commit: `3fca17e`
- macOS: `26.5`
- Hardware: `Mac15,10`
- Mode: `--installer-app-only`
- Package: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/2brain-rec-local.pkg`
- Component directory: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/components`
- Validator result: `passed`
- Safe checks: default package built, desktop app component present, audio-driver component absent, distribution has no audio-driver references, staging root has no Finder sidecar files, and package was not installed.

## App-Only Installer Validator Run

- Run ID: `20260610T110141Z`
- Timestamp: `2026-06-10T11:01:41Z`
- Commit: `3fca17e`
- macOS: `26.5`
- Hardware: `Mac15,10`
- Mode: `--installer-app-only`
- Package: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/2brain-rec-local.pkg`
- Component directory: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/components`
- Validator result: `passed`
- Safe checks: default package built, desktop app component present, audio-driver component absent, distribution has no audio-driver references, staging root has no Finder sidecar files, and package was not installed.

## App-Only Installer Validator Run

- Run ID: `20260610T110151Z`
- Timestamp: `2026-06-10T11:01:51Z`
- Commit: `3fca17e`
- macOS: `26.5`
- Hardware: `Mac15,10`
- Mode: `--installer-app-only`
- Package: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/2brain-rec-local.pkg`
- Component directory: `/Users/yshishenya/.config/superpowers/worktrees/crisp/025-system-audio-capture-pivot/apps/macos/.build/installer/components`
- Validator result: `passed`
- Safe checks: default package built, desktop app component present, audio-driver component absent, distribution has no audio-driver references, staging root has no Finder sidecar files, and package was not installed.

## App-Only Installer Validator Run

- Run ID: `20260610T175150Z`
- Timestamp: `2026-06-10T17:51:50Z`
- Commit: `bf81356`
- macOS: `26.5`
- Hardware: `Mac15,10`
- Mode: `--installer-app-only`
- Package: `/Users/yshishenya/.config/superpowers/worktrees/crisp/020-speaker-to-mic-leakage/apps/macos/.build/installer/2brain-rec-local.pkg`
- Component directory: `/Users/yshishenya/.config/superpowers/worktrees/crisp/020-speaker-to-mic-leakage/apps/macos/.build/installer/components`
- Validator result: `passed`
- Safe checks: default package built, desktop app component present, audio-driver component absent, distribution has no audio-driver references, staging root has no Finder sidecar files, and package was not installed.

## App-Only Installer Validator Run

- Run ID: `20260624T021346Z`
- Timestamp: `2026-06-24T02:13:46Z`
- Commit: `94fadf5`
- macOS: `26.5`
- Hardware: `Mac15,10`
- Mode: `--installer-app-only`
- Package: `<feature-worktree>/apps/macos/.build/installer/2brain-rec-local.pkg`
- Component directory: `<feature-worktree>/apps/macos/.build/installer/components`
- Validator result: `passed`
- Safe checks: default package built, desktop app component present, audio-driver component absent, distribution has no audio-driver references, staging root has no Finder sidecar files, and package was not installed.

## App-Only Installer Validator Run

- Run ID: `20260624T021902Z`
- Timestamp: `2026-06-24T02:19:02Z`
- Commit: `94fadf5`
- macOS: `26.5`
- Hardware: `Mac15,10`
- Mode: `--installer-app-only`
- Package: `<feature-worktree>/apps/macos/.build/installer/2brain-rec-local.pkg`
- Component directory: `<feature-worktree>/apps/macos/.build/installer/components`
- Validator result: `passed`
- Safe checks: default package built, desktop app component present, audio-driver component absent, distribution has no audio-driver references, staging root has no Finder sidecar files, and package was not installed.

## App-Only Installer Validator Run

- Run ID: `20260624T031916Z`
- Timestamp: `2026-06-24T03:19:16Z`
- Commit: `94fadf5`
- macOS: `26.5`
- Hardware: `Mac15,10`
- Mode: `--installer-app-only`
- Package: `<feature-worktree>/apps/macos/.build/installer/2brain-rec-local.pkg`
- Component directory: `<feature-worktree>/apps/macos/.build/installer/components`
- Validator result: `passed`
- Safe checks: default package built, desktop app component present, audio-driver component absent, distribution has no audio-driver references, staging root has no Finder sidecar files, and package was not installed.

## App-Only Installer Validator Run

- Run ID: `20260624T040016Z`
- Timestamp: `2026-06-24T04:00:16Z`
- Commit: `94fadf5`
- macOS: `26.5`
- Hardware: `Mac15,10`
- Mode: `--installer-app-only`
- Package: `<feature-worktree>/apps/macos/.build/installer/2brain-rec-local.pkg`
- Component directory: `<feature-worktree>/apps/macos/.build/installer/components`
- Validator result: `passed`
- Safe checks: default package built, desktop app component present, audio-driver component absent, distribution has no audio-driver references, staging root has no Finder sidecar files, and package was not installed.

## App-Only Installer Validator Run

- Run ID: `20260624T150259Z`
- Timestamp: `2026-06-24T15:02:59Z`
- Commit: `94fadf5`
- macOS: `26.5`
- Hardware: `Mac15,10`
- Mode: `--installer-app-only`
- Package: `<feature-worktree>/apps/macos/.build/installer/2brain-rec-local.pkg`
- Component directory: `<feature-worktree>/apps/macos/.build/installer/components`
- Validator result: `passed`
- Safe checks: default package built, desktop app component present, audio-driver component absent, distribution has no audio-driver references, staging root has no Finder sidecar files, and package was not installed.

## App-Only Installer Validator Run

- Run ID: `20260624T150631Z`
- Timestamp: `2026-06-24T15:06:31Z`
- Commit: `94fadf5`
- macOS: `26.5`
- Hardware: `Mac15,10`
- Mode: `--installer-app-only`
- Package: `<feature-worktree>/apps/macos/.build/installer/2brain-rec-local.pkg`
- Component directory: `<feature-worktree>/apps/macos/.build/installer/components`
- Validator result: `passed`
- Safe checks: default package built, desktop app component present, audio-driver component absent, distribution has no audio-driver references, staging root has no Finder sidecar files, and package was not installed.

## App-Only Installer Validator Run

- Run ID: `20260624T150834Z`
- Timestamp: `2026-06-24T15:08:34Z`
- Commit: `94fadf5`
- macOS: `26.5`
- Hardware: `Mac15,10`
- Mode: `--installer-app-only`
- Package: `<feature-worktree>/apps/macos/.build/installer/2brain-rec-local.pkg`
- Component directory: `<feature-worktree>/apps/macos/.build/installer/components`
- Validator result: `passed`
- Safe checks: default package built, desktop app component present, audio-driver component absent, distribution has no audio-driver references, staging root has no Finder sidecar files, and package was not installed.

## App-Only Installer Validator Run

- Run ID: `20260624T151010Z`
- Timestamp: `2026-06-24T15:10:10Z`
- Commit: `94fadf5`
- macOS: `26.5`
- Hardware: `Mac15,10`
- Mode: `--installer-app-only`
- Package: `<feature-worktree>/apps/macos/.build/installer/2brain-rec-local.pkg`
- Component directory: `<feature-worktree>/apps/macos/.build/installer/components`
- Validator result: `passed`
- Safe checks: default package built, desktop app component present, audio-driver component absent, distribution has no audio-driver references, staging root has no Finder sidecar files, and package was not installed.

## App-Only Installer Validator Run

- Run ID: `20260624T151033Z`
- Timestamp: `2026-06-24T15:10:33Z`
- Commit: `94fadf5`
- macOS: `26.5`
- Hardware: `Mac15,10`
- Mode: `--installer-app-only`
- Package: `<feature-worktree>/apps/macos/.build/installer/2brain-rec-local.pkg`
- Component directory: `<feature-worktree>/apps/macos/.build/installer/components`
- Validator result: `passed`
- Safe checks: default package built, desktop app component present, audio-driver component absent, distribution has no audio-driver references, staging root has no Finder sidecar files, and package was not installed.

## App-Only Installer Validator Run

- Run ID: `20260624T151617Z`
- Timestamp: `2026-06-24T15:16:17Z`
- Commit: `94fadf5`
- macOS: `26.5`
- Hardware: `Mac15,10`
- Mode: `--installer-app-only`
- Package: `<feature-worktree>/apps/macos/.build/installer/2brain-rec-local.pkg`
- Component directory: `<feature-worktree>/apps/macos/.build/installer/components`
- Validator result: `passed`
- Safe checks: default package built, desktop app component present, audio-driver component absent, distribution has no audio-driver references, staging root has no Finder sidecar files, and package was not installed.

## App-Only Installer Validator Run

- Run ID: `20260624T163503Z`
- Timestamp: `2026-06-24T16:35:03Z`
- Commit: `94fadf5`
- macOS: `26.5`
- Hardware: `Mac15,10`
- Mode: `--installer-app-only`
- Package: `<feature-worktree>/apps/macos/.build/installer/2brain-rec-local.pkg`
- Component directory: `<feature-worktree>/apps/macos/.build/installer/components`
- Validator result: `passed`
- Safe checks: default package built, desktop app component present, audio-driver component absent, distribution has no audio-driver references, staging root has no Finder sidecar files, and package was not installed.

## App-Only Installer Validator Run

- Run ID: `20260624T163657Z`
- Timestamp: `2026-06-24T16:36:57Z`
- Commit: `94fadf5`
- macOS: `26.5`
- Hardware: `Mac15,10`
- Mode: `--installer-app-only`
- Package: `<feature-worktree>/apps/macos/.build/installer/2brain-rec-local.pkg`
- Component directory: `<feature-worktree>/apps/macos/.build/installer/components`
- Validator result: `passed`
- Safe checks: default package built, desktop app component present, audio-driver component absent, distribution has no audio-driver references, staging root has no Finder sidecar files, and package was not installed.

## App-Only Installer Validator Run

- Run ID: `20260624T165853Z`
- Timestamp: `2026-06-24T16:58:53Z`
- Commit: `94fadf5`
- macOS: `26.5`
- Hardware: `Mac15,10`
- Mode: `--installer-app-only`
- Package: `<feature-worktree>/apps/macos/.build/installer/2brain-rec-local.pkg`
- Component directory: `<feature-worktree>/apps/macos/.build/installer/components`
- Validator result: `passed`
- Safe checks: default package built, desktop app component present, audio-driver component absent, distribution has no audio-driver references, staging root has no Finder sidecar files, and package was not installed.

## App-Only Installer Validator Run

- Run ID: `20260624T172111Z`
- Timestamp: `2026-06-24T17:21:11Z`
- Commit: `94fadf5`
- macOS: `26.5`
- Hardware: `Mac15,10`
- Mode: `--installer-app-only`
- Package: `<feature-worktree>/apps/macos/.build/installer/2brain-rec-local.pkg`
- Component directory: `<feature-worktree>/apps/macos/.build/installer/components`
- Validator result: `passed`
- Safe checks: default package built, desktop app component present, audio-driver component absent, distribution has no audio-driver references, staging root has no Finder sidecar files, and package was not installed.

## App-Only Installer Validator Run

- Run ID: `20260624T180823Z`
- Timestamp: `2026-06-24T18:08:23Z`
- Commit: `94fadf5`
- macOS: `26.5`
- Hardware: `Mac15,10`
- Mode: `--installer-app-only`
- Package: `/Users/yshishenya/.codex/worktrees/e040/crisp/apps/macos/.build/installer/2brain-rec-local.pkg`
- Component directory: `/Users/yshishenya/.codex/worktrees/e040/crisp/apps/macos/.build/installer/components`
- Validator result: `passed`
- Safe checks: default package built, desktop app component present, audio-driver component absent, distribution has no audio-driver references, staging root has no Finder sidecar files, and package was not installed.

## App-Only Installer Validator Run

- Run ID: `20260624T180905Z`
- Timestamp: `2026-06-24T18:09:05Z`
- Commit: `94fadf5`
- macOS: `26.5`
- Hardware: `Mac15,10`
- Mode: `--installer-app-only`
- Package: `/Users/yshishenya/.codex/worktrees/e040/crisp/apps/macos/.build/installer/2brain-rec-local.pkg`
- Component directory: `/Users/yshishenya/.codex/worktrees/e040/crisp/apps/macos/.build/installer/components`
- Validator result: `passed`
- Safe checks: default package built, desktop app component present, audio-driver component absent, distribution has no audio-driver references, staging root has no Finder sidecar files, and package was not installed.
