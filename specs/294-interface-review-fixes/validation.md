# Validation: Исправления после ревью интерфейса

**Feature**: `294-interface-review-fixes` | **Date**: 2026-11-12

## Code candidate

- Branch: `294-interface-review-fixes`
- Risk lane: high-risk-feature
- Release: `v2026.11.12.1` (or next free CalVer)
- Base: `cbdbae725e14a7c261210ca0e56f7fd9087b5b48`

## Local checks

| Check | Result |
|---|---|
| `swift build --package-path apps/macos` | PASS |
| `apps/macos/Scripts/run-swift-tests.sh` | PASS: 1331 tests, 2 skipped, 0 failures |
| `swift run --package-path apps/macos ContractValidation` | PASS |
| `python3 scripts/validate-changelog-fragments.py` | PASS (to rerun in fast lane) |
| `infra/scripts/ci-local.sh --fast` | pending |
| GitHub `governance-fast`, `macos-pr`, `pr-metadata` | pending |

## Fixed behavior

- `⌘0` belongs only to cabinet zoom; «Домой» uses `⇧⌘H`.
- Stop/Pause visibility and accessibility use consistent predicates; repeat Stop is unavailable during `.stopping`.
- Saved missing microphone falls back to the system default and is cleared.
- Disconnect of the effective/default microphone degrades the session.
- Account storage cleanup completes before auth notification/reload.
- Local recording rows refresh on time zone changes.
- Menu bar distinguishes recording/degraded/failed.
- Settings fallback lists all five sections; «Все настройки» opens the account route.
- Window frame is clamped to minimum size and visible screen.
- Microphone discovery no longer runs synchronously on MainActor; resolution uses the cache.
- Dead presentation states/fields, account-reset plan flags and duplicate local-custody copy removed.
- Logs flush on normal termination.

## Deferred

- Mass replacement of 437 source-text assertions; new behavior tests cover this slice.
- Full 60-minute hardware performance gate and full Dynamic Type.
- `LocalBufferService`, encrypted buffer and analytics scaffold product decision.
