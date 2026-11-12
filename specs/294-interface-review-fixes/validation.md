# Validation: Исправления после ревью интерфейса

**Feature**: `294-interface-review-fixes` | **Date**: 2026-11-12

## Release candidate

- Release: `v2026.11.12.4`
- Tag: `v2026.11.12.4`
- Source SHA: `c8c2c149f9d07829df187f22b1e8faa7627d349a`
- Candidate: `rc-20261112T163854Z-48f2aaee0b4e`
- Release URL: https://github.com/yshishenya/graf/releases/tag/v2026.11.12.4
- Risk lane: high-risk-feature

## Local checks

| Check | Result |
|---|---|
| `swift build --package-path apps/macos` | PASS |
| `apps/macos/Scripts/run-swift-tests.sh` | PASS: 1332 tests, 9 skipped, 0 failures |
| `swift run --package-path apps/macos ContractValidation` | PASS |
| Focused strict RLS and refund tests | PASS: 48 tests |
| `python3 scripts/validate-changelog-fragments.py` | PASS |
| GitHub `governance-fast`, `macos-pr`, `pr-metadata` | PASS on PR #8026 and release PRs |

## Release checks

| Check | Result |
|---|---|
| GitHub `release-full` run `43260951914` | PASS on exact SHA `c8c2c149f9d07829df187f22b1e8faa7627d349a` |
| Production deploy | `deploy_result=pass` |
| Runtime SHA | `c8c2c149f9d07829df187f22b1e8faa7627d349a` |
| Backup | `/opt/projects/2brain-rec/backups/20261112T181246Z` |
| Public health `/api/v1/health/live` | 200, `{"status":"ok"}` |
| Public health `/api/v1/health/ready` | 200, `{"status":"ready"}` |
| macOS app version | `2026.11.12.4` |
| Code signature | Developer ID Application: Yan Shishenya (94N8HYG672) |
| Notarization / staple / Gatekeeper | PASS |
| Sparkle live appcast | PASS, version `2026.11.12.4` |
| Public archive | HTTP 200, 9,836,508 bytes |

## Fixed behavior

- `⌘0` belongs only to cabinet zoom; «Домой» uses `⇧⌘H`.
- Stop/Pause visibility and accessibility use consistent predicates; repeat Stop is unavailable during `.stopping`; failed sessions offer a working retry.
- Saved missing microphone falls back to the system default and is cleared; policy rejection keeps the saved choice.
- Disconnect of the effective/default microphone degrades the session without stopping system audio.
- Account storage cleanup completes before auth notification/reload; generation is revalidated after cleanup.
- Local recording rows refresh on system time zone changes.
- Menu bar distinguishes recording/degraded/failed and hides unusable Mute for degraded sessions.
- Settings fallback lists all five sections; «Все настройки» opens the account route.
- Window frame is clamped to minimum size and visible screen.
- Microphone discovery no longer runs synchronously on MainActor; resolution uses the cache.
- Dead presentation states/fields, account-reset plan flags and duplicate local-custody copy removed.
- Logs flush on normal termination.

## Deferred

- Mass replacement of 437 source-text assertions; new behavior tests cover this slice.
- Full 60-minute hardware performance gate and full Dynamic Type.
- `LocalBufferService`, encrypted buffer and analytics scaffold product decision.
