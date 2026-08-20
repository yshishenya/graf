# Production closeout: `v2026.08.21.1`

## Immutable release

- Tag and GitHub Release: `v2026.08.21.1`
- Release SHA: `d357c52e0eea2f2bc0ca663577fcf10dd49bb5d1`
- Runtime branch: `master` at the same SHA
- Implementation PR: https://github.com/yshishenya/crisp/pull/5468
- Release preparation PRs: https://github.com/yshishenya/crisp/pull/5469,
  https://github.com/yshishenya/crisp/pull/5470 and
  https://github.com/yshishenya/crisp/pull/5471
- Release: https://github.com/yshishenya/crisp/releases/tag/v2026.08.21.1

## Validation and deployment

| Gate | Result |
| --- | --- |
| Full exact-SHA macOS suite | pass; 701 tests |
| Full exact-SHA server suite | pass; 3147 passed, 1 expected skip |
| Strict PostgreSQL/RLS matrix | pass; 50 passed, 1 expected skip |
| Lint, compile and evidence scan | pass; 31 receipts scanned |
| Backup and restore rehearsal | pass; backup `20260820T232032Z` |
| Migration | pass; `0074_linked_workspace_proofs` |
| Production smoke and cleanup | pass; no residue |
| API, Temporal and workers | healthy |
| Runtime SHA | matches release SHA |
| Rollback | not required; guarded backup and previous appcast remain available |

## macOS release gates

| Gate | Result |
| --- | --- |
| Developer ID Application and Installer | pass; Team `94N8HYG672` |
| Apple app notarization | accepted; request `17ac0398-8dc1-47d0-9fc1-3bbdf33bb76c` |
| Apple package notarization | accepted; request `ed095c1a-70c1-4de1-ae5b-7b97fa6df97d` |
| Stapler and Gatekeeper | pass for freshly downloaded app and package |
| Sparkle Keychain custody | pass; active trust generation 1 |
| Developer ID continuity | pass against `2026.08.20.2` |
| Installed Sparkle update | pass; `2026.08.20.2` → `2026.08.21.1` and relaunch |
| Permission retention | pass; microphone and system-audio functional probes granted without a new prompt |
| Public archive/appcast validation | pass after fresh HTTPS download |

## Public artifacts

- Feed: https://rec.2brain.pro/static/public/downloads/graf-appcast.xml
- ZIP: https://rec.2brain.pro/static/public/downloads/GRAF-2026.08.21.1.zip
- PKG: https://rec.2brain.pro/static/public/downloads/GRAF-2026.08.21.1.pkg
- ZIP SHA-256: `37a261cc83948c11df8f325c8dd26c166b7662c33786560757d8a707480e17c3`
- PKG SHA-256: `858eb24ba52b3cc67873199aaac4f4ff9d3f7cfe34f39569ad39f0ba11b1a7d8`
- Appcast SHA-256: `8de37127f6900d2299b48fe06040f90a966f61e4f829f181f97220c339c19d3f`
- The previous signed appcast was retained before the live feed was replaced.

## Post-deploy product evidence

- Live `/api/v1/health/live` returned `ok`; `/api/v1/health/ready` returned
  `ready`.
- The production landing and login surfaces rendered in the in-app browser at
  1280 px without horizontal overflow.
- The installed app kept the existing signed-in session. Account settings
  exposed the bounded provider list, the email-link entry point and the
  preview-first explanation without a permission prompt.
- The sidebar toggle remained at the top in expanded and compact states; a
  second click at the same position restored the panel and no controls
  overlapped.
- Immediately after the Sparkle relaunch the embedded document needed one
  explicit Reload before it rendered. The session remained valid and all
  subsequent navigation worked. This single observation was not reproduced as
  an account-linking failure and is retained in follow-up issue
  https://github.com/yshishenya/crisp/issues/5472 rather than hidden.
- Real email, Yandex ID and VK ID sign-ins were not repeated because they
  require user-owned confirmation codes. The release gate used synthetic auth
  profiles and did not read or modify production accounts.

To halt rollout, restore the retained previous signed appcast. A client that
already installed this version requires a higher-CalVer forward rollback; never
publish an unsigned or lower-version downgrade.

All evidence is metadata-only. Personal identifiers, one-time codes,
credentials, private meeting data and private captures are excluded.
