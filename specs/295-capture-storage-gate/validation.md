# Validation: Честная проверка локального места

**Feature**: `295-capture-storage-gate` | **Date**: 2026-11-14

## Code candidate

- Branch: `295-capture-storage-gate`
- Risk lane: high-risk-product
- Base: `f90c253555a8128c4164270d97c1d996cbee8e70`
- Release: next free CalVer after `v2026.11.12.5`

## Local checks

| Check | Result |
|---|---|
| `swift build --package-path apps/macos` | PASS |
| `apps/macos/Scripts/run-swift-tests.sh` | PASS: 1354 tests, 9 skipped, 0 failures |
| `swift run --package-path apps/macos ContractValidation` | PASS |
| `python3 scripts/validate-changelog-fragments.py` | PASS |
| Focused footprint/provider/gate/tray tests | PASS |

## Release checks

| Check | Result |
|---|---|
| GitHub `governance-fast`, `macos-pr`, `pr-metadata` | pending PR |
| `release-full` on exact SHA | pending |
| Developer ID / notarization / staple / Gatekeeper | pending |
| Sparkle / live appcast | pending |
| Production deploy / health / runtime SHA | pending |

## Evidence

- Queue fixture: 74 items, 35 uploaded (31 processed/ready, 4 failed-terminal), 37 terminal_deleted, 10 accepted deletion operations, 2 blocked.
- Actual recordings folder: ~1.16 GB; historical queue metadata: ~1.53 GB.
- F295 deletes no files and changes no queue schema.
- Checklist review: PASS 27/27 (requirements 15/15, UX 12/12).
- Local footprint: 6 tests; provider: 9 tests; gate: 9 tests; tray: 45 tests; performance contract: 7 tests.
- `LocalRecordingFootprintMeasurer` runs off-main via `LocalRecordingFootprintProvider`; 2s timeout; fail-closed on error.
- F284/local-only/deletion regression: full suite green; no player/bridge/local-only code changed.
- F296 server library/cache remains out of scope and blocked behind the server playback/storage contract.
