# Validation: F296 — proof, cleanup, eviction

**Feature**: `296-server-cache-proof` | **Date**: 2026-11-16

## Code candidate

- Branch: `296-server-cache-proof`
- Risk lane: `high-risk-product`
- Base: `5223422357487ab28cfc83084c9e45717d0a6568`
- PR: pending
- Merge SHA: pending
- Release: next free CalVer

## Design gates

| Check | Result |
|---|---|
| Spec / plan / research / data-model / contracts | PASS |
| Clarify recorded | PASS |
| Independent checklist review | DESIGN-GO: 0 design blockers, 9 implementation-evidence items |
| Analyze | PASS: 0 unresolved critical/high for F296 |
| GitHub issues | umbrella #8063 + T001–T030 child issues #8064–#8093 |

## Local checks

| Check | Result |
|---|---|
| Server focused pytest | pending |
| OpenAPI drift | pending |
| `swift build --package-path apps/macos` | pending |
| Focused Swift tests | pending |
| `apps/macos/Scripts/run-swift-tests.sh` | pending |
| ContractValidation | pending |
| `python3 scripts/validate-changelog-fragments.py` | pending |

## Release checks

| Check | Result |
|---|---|
| GitHub `governance-fast`, `macos-pr`, `pr-metadata` | pending |
| `release-full` on exact SHA | pending |
| Developer ID / notarization / staple / Gatekeeper | pending |
| Sparkle / live appcast | pending |
| Production deploy / health / runtime SHA | pending |
| Production dry run: zero file/queue mutation | pending |

## Evidence

- Pending implementation and release evidence.
- Real-queue dry run must record report SHA, before/after queue SHA256/mtime and recordings tree hashes.
- No deletion in Phase A; Phase B/C enablement only after the production dry run is clean.
