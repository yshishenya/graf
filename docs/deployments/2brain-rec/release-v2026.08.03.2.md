# Production closeout: `v2026.08.03.2`

## Immutable release

- Tag: `v2026.08.03.2`
- Deployed SHA: `04f9075a548de6fc44b0b8c452ef28c8271eedb1`
- Deploy branch: `master`
- Runtime checkout: `master` at the same SHA
- Host/path: `2brain.dev:/opt/projects/2brain-rec`
- GitHub Release: https://github.com/yshishenya/crisp/releases/tag/v2026.08.03.2
- Feature PR: https://github.com/yshishenya/crisp/pull/4747
- Release PR: https://github.com/yshishenya/crisp/pull/4748

## macOS release gates

| Gate | Result |
| --- | --- |
| Developer ID Application / Installer identities | pass; Team `94N8HYG672` |
| Apple candidate ZIP notarization | pass; request `12735106-0278-4351-8912-ac59ebbe00ed` |
| Apple package notarization | pass; request `2168a184-77da-4594-b093-cfaaa293b1c5` |
| Stapler and Gatekeeper | pass for app and package |
| Protected Sparkle signing workflow | pass; run `30795124165` |
| Developer ID → Developer ID continuity | pass; validator `2026.07.27.1 → 2026.08.03.2` |
| Public HTTPS artifact fetch | pass; ZIP, PKG, appcast and checksums match |

## Repository and deployment gates

| Gate | Result |
| --- | --- |
| Full local CI on exact release source | pass; macOS `642`; server `2470 passed / 1 skipped`; strict `42 passed / 1 skipped` |
| Ruff, Python compile, ContractValidation, Compose and evidence scan | pass |
| CD dry-run | pass; branch, clean worktree and required gate list confirmed |
| Remote guarded deploy | pass; `deployed_sha` matches tag |
| Backup | pass; `/opt/projects/2brain-rec/backups/20260803T080149Z` |
| Restore rehearsal | pass; PostgreSQL and MinIO rehearsal targets created |
| Migration verification | pass; head `0042_shared_with_me_lookup` |
| RLS hardening disposable validation | pass; live production probe not attempted |
| Production smoke and readiness | pass; `infra_smoke_ready` |
| Temporal and processing-worker readiness | pass |
| Automatic dispatch gate | pass |
| Public health | pass; deploy script completed with readiness verdict |
| Post-deploy retry/backfill/range/cleanup | required follow-up; not a release blocker |

The deploy command returned `deploy_result=pass`; no rollback was required.
The runtime checkout and deployed branch resolve to the immutable release SHA.

## Public artifacts

- Feed: https://rec.2brain.pro/static/public/downloads/graf-appcast.xml
- ZIP: https://rec.2brain.pro/static/public/downloads/GRAF-2026.08.03.2.zip
- PKG: https://rec.2brain.pro/static/public/downloads/GRAF-2026.08.03.2.pkg
- ZIP SHA-256: `21b4a72095a2775aaee96d3f5e82a3e98daaf1cc7bd89b8040796569366c2813`
- PKG SHA-256: `52db0d7a8bfc25d840f8794fb95e6e73fd372feda459a67ec6e14d93db05a2a9`
- Appcast SHA-256: `4033e01d0774161da9b1958e20fc7c1d04941b2b1aabd6cecc5bac1b2a4afadc`
- Previous appcast backup: `graf-appcast.xml.pre-v2026.08.03.2-20260803T075359Z`

## Compatibility and rollback

- Existing Developer ID clients remain on the ordinary signed Sparkle update
  path; the candidate preserved bundle identity, feed URL and Sparkle trust.
- Rollback must restore the previous verified signed feed/archive and use the
  guarded deployment rollback runbook. Never publish an unsigned downgrade.
- All committed evidence is metadata-only and contains no meeting content.
