# Validation: F296 — proof, cleanup, eviction

**Feature**: `296-server-cache-proof` | **Date**: 2026-11-16

## Code candidate

- Branch: `296-server-cache-proof`
- Risk lane: `high-risk-product`
- Base: `5223422357487ab28cfc83084c9e45717d0a6568`
- PR: `#8099`
- Merge SHA: `f6322eeb5d9185e83a52b86b9bec30e31ff73a2d`
- Release: `v2026.11.16.2`
- Release: next free CalVer

## Design gates

| Check | Result |
|---|---|
| Spec / plan / research / data-model / contracts | PASS |
| Clarify recorded | PASS |
| Independent checklist review | IMPLEMENTATION-GO after code review fixes; only production dry-run/release gates remain |
| Analyze | PASS: 0 unresolved critical/high for F296 |
| GitHub issues | umbrella #8063 + T001–T030 child issues #8064–#8093 |

## Local checks

| Check | Result |
|---|---|
| Server focused pytest | PASS: 61 passed; OpenAPI drift `openapi_equal=True`; ruff PASS |
| OpenAPI drift | PASS |
| `swift build --package-path apps/macos` | PASS |
| Focused Swift tests | PASS: LocalCache/Cleanup/Scheduler/Client/InterfacePerformance |
| `apps/macos/Scripts/run-swift-tests.sh` | PASS: 1521 tests, 9 skipped, 0 failures |
| ContractValidation | PASS |
| `python3 scripts/validate-changelog-fragments.py` | PASS |

## Release checks

| Check | Result |
|---|---|
| GitHub `governance-fast`, `macos-pr`, `pr-metadata` | pending |
| `release-full` on exact SHA | pending |
| Developer ID / notarization / staple / Gatekeeper | pending |
| Sparkle / live appcast | pending |
| Production deploy / health / runtime SHA | pending |
| Production dry run: zero file/queue mutation | pending |

## Release order gate

1. Deploy the server contract (Phase A) before publishing the app update.
2. Build/notarize the candidate and install it on the operator Mac with `GRAF_DISABLE_LOCAL_CACHE_AUTO_EVICTION=1`.
3. Run the production dry run; require zero file/queue mutation and zero false `potentially_eligible` verdicts.
4. Only then publish the appcast/GitHub Release and remove the operator kill switch.
5. If the dry run finds a defect, keep the operator switch on, ship no appcast update, and fix before publication.

## Evidence

- Code review: P0 playback UUID/local revision and P1 finalized/active session mixing fixed; queue re-read, hash, starvation, truncation, scope fence, concurrent cleanup, UI availability and F284 checks added.
- Full Swift suite after rebase: 1521 tests, 9 skipped, 0 failures.
- Server focused Postgres lane after rebase: 61 passed; OpenAPI drift PASS; ruff PASS.
- Exact implementation SHA before PR: `2408c668c` (will be updated to the PR SHA).
- Real-queue dry run must record report SHA, before/after queue SHA256/mtime and recordings tree hashes.
- No deletion in Phase A; Phase B/C enablement only after the production dry run is clean.
