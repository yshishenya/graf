# Release Evidence: v2026.11.10.3

**Feature**: `293-interface-hardening` | **Date**: 2026-11-10
**Source SHA**: `813e9dabba35c546a782852795e921bd325f3689`
**Candidate**: `rc-20261110T103104Z-24a9a722c7ef`
**GitHub Release**: https://github.com/yshishenya/graf/releases/tag/v2026.11.10.3

## Checks

| Gate | Result |
|---|---|
| `release-full` 42799821665 | PASS: Ubuntu static/governance, Ubuntu postgres strict/performance, 8 parallel shards, macOS full aggregate |
| Swift tests in `release-full` | 1330 tests, 9 skipped, 0 failures |
| `governance-fast` / `macos-pr` / `pr-metadata` | PASS on PR #8002 and PR #8003 exact SHA |
| Release decision | `go` for candidate `rc-20261110T103104Z-24a9a722c7ef` |
| `cd-remote.sh --dry-run` | `deploy_result=dry_run`; production execute not run |

## Package and notarization

| Item | Value |
|---|---|
| App signing | Developer ID Application: Yan Shishenya (94N8HYG672) |
| Installer signing | Developer ID Installer: Yan Shishenya (94N8HYG672) |
| Notary ZIP request | `e0e8ab61-31f7-4ff2-bae0-8eae0856a12b` — Accepted |
| Notary PKG request | `cefcb1ee-d012-4943-9542-f138991e7170` — Accepted |
| Candidate ZIP SHA-256 | `ed9d30b1483d5df1260b36000a5cb39cd86afa83a6542ff0b6828085e5c2d316` |
| Notarized PKG SHA-256 | `264fcef208e27679f29f0b1d76110d0296327981606cbd7ecad3304f5462daec` |
| Public update ZIP SHA-256 | `379ba34ebeba54c9517fd650ea6a65374b9d96315206d6da222db9dfef0790c4` |
| Appcast SHA-256 | `cdb963ca646565de787d2d00f6b277fee0549f3614bc374f0d881676c1816779` |

## Public artifact checks

- Downloaded `GRAF-2026.11.10.3.zip` and `graf-appcast.xml` from the published GitHub Release.
- `shasum -a 256 -c GRAF-2026.11.10.3.sha256` — both files OK.
- Live appcast `https://rec.2brain.pro/static/public/downloads/graf-appcast.xml` SHA-256 equals the published asset.
- Appcast version and short version: `2026.11.10.3`; archive URL `https://rec.2brain.pro/static/public/downloads/GRAF-2026.11.10.3.zip`; length `9831030`; Sparkle EdDSA signature present.
- `codesign` — Developer ID Application, hardened runtime, secure timestamp.
- `spctl -a -vv` — accepted, source Notarized Developer ID.
- `xcrun stapler validate` — validate action worked.
- Packaged app launch validation — PASS for arm64 and x86_64.
- Runtime registry probe — `registry_resolved source=bundled`.

## Review corrections

- PR #8003 fixed the SwiftPM `Contents/Resources/Resources` layout for both the release launch validator and the runtime meeting-target registry lookup.
- `build-local-installer.sh` now uses `swift build --show-bin-path` instead of assuming the pre-Xcode-27 product path; the release itself was built with an equivalent local path compatibility step.

## Limitations

- Production server deployment was not executed; the GitHub Release and Sparkle update are published.
- Full 60-minute hardware performance run and increased-contrast matrix remain deferred.
- Umbrella #7967 remains open for T007, T012, T023, T025, T028, T029.
