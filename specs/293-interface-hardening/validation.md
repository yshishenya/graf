# Validation: Сквозное укрепление интерфейса GRAF

**Feature**: `293-interface-hardening` | **Date**: 2026-11-10

## Code candidate

- Branch: `293-interface-hardening`
- Code SHA: `7d3b51ca9aa1` (app code and tests; documentation-only commits may follow)
- Risk lane: high-risk-feature
- Release gate: GitHub `release-full` on frozen candidate, then Developer ID/notarization/Sparkle

## Native build and tests

| Check | Result |
|---|---|
| `swift build --package-path apps/macos` | PASS |
| `apps/macos/Scripts/run-swift-tests.sh` | PASS: 1313 tests, 9 skipped, 0 failures |
| `swift run --package-path apps/macos ContractValidation` | PASS |
| `infra/scripts/ci-local.sh --fast` with pinned Spec Kit 1.0.7/bootstrap 0.9.10 | PASS: components `macos,docs`; coverage `partial`; next gate `full_before_release` |
| `ci-local` evidence | `.dev/ci-evidence/ci-fast-7d3b51ca9aa1-a14bb58d56b8.json` |

## New and changed tests

- `CaptureStatusPresentationTests`: all capture/custody/blocker states, attention flags, no raw failure codes.
- `AppMenuBuilderTests`: Russian menu, unique shortcuts, global Stop `⌘⇧S`, single zoom increase, `⌘0` reset.
- `AccountSwitchResetTests`: reset plan and page-storage cleanup script.
- `AppShellBehaviorTests`: settings-section availability, preference round-trip, invalid frame rejection, unavailable microphone.
- `InterfacePerformanceContractTests`: microphone discovery cache, no local-row computation in the view builder, no direct file/device discovery in `ContentView`, formatter reuse.
- `DesktopDesignTokenContractTests`: CSS `:root`/light palette vs native tokens.
- Updated existing tests for typed statuses, new paths and human error copy.

## Behavior verified

- Capture, local custody and blocker presentations are typed; views no longer decide behavior by `contains` on user copy.
- Visible copy no longer includes raw failure codes; known codes map to human Russian text.
- Application menu is Russian; one visible zoom increase; `⌘0` belongs to cabinet zoom reset; Stop is available from the application menu.
- Account switch resets route, calendar prompt/pending state, selected recording, local player and reloads the cabinet; page storage is cleared and cookies remain owned by the session bridge.
- Settings fallback distinguishes local sections («Запись», «Уведомления») from cabinet sections («Аккаунт», «Календарь», «Биллинг»).
- Window frame, inspector expansion and selected microphone persist.
- Microphone input discovery is cached and invalidated on device connect/disconnect; local recording rows are computed off the view builder.
- Date formatting uses a bounded cache; upload queue reads/writes are detached from MainActor; logs are queued and bounded.
- Notification-card protected regions now use the explicit card owner; the protected-region tests pass.
- Dead types/constants/enums and the outdated raw failure-code copy were removed.

## Deferred / not claimed

- Full 60-minute hardware recording with 100 queue items and Instruments Time Profiler was not run in this worktree. The code-level performance contract and existing queue stress tests pass; the full manual performance gate remains required before release closeout.
- Full Dynamic Type/localization for all 582 strings is out of scope; key fixed widths are scaled and critical contrast/reduce-motion paths are covered.
- `LocalBufferService` write/encryption path, analytics scaffold and test-only contract helpers remain until a separate product decision.
- Web cabinet dead-CSS pruning was not included in this candidate; it is a separate low-risk web-surface change.
- Manual `/Applications/GRAF Dev.app` matrix was not run from this worktree at this point.

## Reproduction

```sh
swift build --package-path apps/macos
apps/macos/Scripts/run-swift-tests.sh
swift run --package-path apps/macos ContractValidation
PATH="$TMPDIR/graf-ci-pin/venv/bin:$TMPDIR/graf-ci-pin/bin:$PATH" infra/scripts/ci-local.sh --fast
```
