# Validation: Честная проверка локального места

**Feature**: `295-capture-storage-gate` | **Date**: 2026-11-14

## Code candidate

- Branch: `295-capture-storage-gate`
- Risk lane: high-risk-product
- Base: `f90c253555a8128c4164270d97c1d996cbee8e70`
- PR: `#8050`
- Merge SHA: `3b8abbec13d5a964648c970dd32e27fa09c6ee9e` (F295 code, PR #8050)
- Rename SHA: `e44aae0a3c174249b72db77894ff761e67e2d962` (PR #8052)
- Release: `v2026.11.12.6`

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
| GitHub `governance-fast`, `macos-pr`, `pr-metadata` | PASS on PR #8050 and release PR #8051 |
| `release-full` on exact SHA | PASS: run 43760323486, candidate `rc-20261115T205038Z-ea5fa4032db6`, decision `go` |
| Developer ID / notarization / staple / Gatekeeper | PASS for app and PKG `2026.11.12.6` |
| Sparkle / live appcast | PASS: live feed offers `2026.11.12.6`, archive HTTP 200, signature match |
| Production deploy / health / runtime SHA | PASS: `deploy_result=pass`, runtime `e44aae0a3`, health live/ready 200 |

## Evidence

- Queue fixture: 74 items, 35 uploaded (31 processed/ready, 4 failed-terminal), 37 terminal_deleted, 10 accepted deletion operations, 2 blocked.
- Actual recordings folder: ~1.16 GB; historical queue metadata: ~1.53 GB.
- F295 deletes no files and changes no queue schema.
- Checklist review: PASS 27/27 (requirements 15/15, UX 12/12).
- Local footprint: 6 tests; provider: 9 tests; gate: 9 tests; tray: 45 tests; performance contract: 7 tests.
- `LocalRecordingFootprintMeasurer` runs off-main via `LocalRecordingFootprintProvider`; 2s timeout; fail-closed on error.
- F284/local-only/deletion regression: full suite green; no player/bridge/local-only code changed.
- F296 server library/cache remains out of scope and blocked behind the server playback/storage contract.
- Release evidence: `.dev/ci-evidence/authoritative-rc-20261115T205038Z-ea5fa4032db6.json`.
- Deploy backup: `/opt/projects/2brain-rec/backups/20261115T215456Z`.
- Final notarized PKG: `GRAF-2026.11.12.6.pkg`, 9 706 266 bytes, SHA256 `5acf5d3eb18659255afa30708ad63f548dae4250830806b95a3d5ee721ba363e`.
- GitHub Release `v2026.11.12.6` published with PKG, Sparkle archive, appcast, checksum and attestation.
- Website `/static/public/downloads/graf.pkg` replaced with the final PKG; HTTP 200 and SHA256 verified, previous file kept as `graf.pkg.pre-2026.11.12.6-20261115T221852Z`.
