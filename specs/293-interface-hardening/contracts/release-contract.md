# Release Contract: Сквозное укрепление интерфейса GRAF

**Feature**: `293-interface-hardening` | **Date**: 2026-11-10

## Version

- CalVer: `v2026.11.10.3` (or the next free CalVer if the date changes).
- Tag: annotated `v2026.11.10.3`.
- GitHub Release title: `v2026.11.10.3 - interface hardening`.
- Release notes: Russian, with changes, validation evidence, compatibility, known limitations, PR/issues links.

## Required checks

1. PR: `governance-fast`, `macos-pr`, `pr-metadata` on the exact head SHA and checked base.
2. Frozen candidate: one full GitHub `release-full`.
3. `swift build --package-path apps/macos`.
4. Focused `swift test` for changed native surfaces.
5. Server `pytest` for cabinet CSS/template contracts if web CSS changes.
6. `infra/scripts/ci-local.sh --fast` as diagnostic (not a substitute).
7. `infra/scripts/cd-remote.sh --dry-run` before production execution.

## macOS artifact gates

1. Developer ID Application and Developer ID Installer identities only.
2. Hardened runtime and secure timestamp.
3. Apple notarization accepted for ZIP and PKG; request IDs recorded.
4. Stapled app and package; `spctl`/Gatekeeper accepted.
5. Sparkle signature valid; candidate validated against the previous published app.
6. Live appcast version strictly greater and ZIP reachable with matching length/SHA.
7. Public feed matches the release tag and version.

## Evidence

Record in the feature/release evidence:
- exact source SHA and tag;
- build JSON and package hashes;
- notary request IDs and Accepted status;
- stapler/Gatekeeper/Sparkle outputs;
- GitHub check IDs/URLs;
- live appcast XML and hashes;
- Russian release notes;
- known limitations and rollback note.

## Rollback

- Keep the previous appcast and ZIP until the new feed is verified.
- If notarization, Gatekeeper, Sparkle or live feed validation fails, stop publication and keep the previous feed.
- Do not replace a notarized candidate with a rebuilt one under the same version.
