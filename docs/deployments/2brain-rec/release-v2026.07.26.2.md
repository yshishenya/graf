# Production closeout: v2026.07.26.2

## Immutable release

- Tag: `v2026.07.26.2`
- Deployed SHA: `0c16b218466f43863dbb5db0cea06dcf21921910`
- Deploy branch: `codex/deploy-v2026.07.26.2`
- Host/path: `2brain.dev:/opt/projects/2brain-rec`
- GitHub Release: https://github.com/yshishenya/crisp/releases/tag/v2026.07.26.2
- Feature PR: https://github.com/yshishenya/crisp/pull/4602
- Release PR: https://github.com/yshishenya/crisp/pull/4603
- Signing workflow: https://github.com/yshishenya/crisp/actions/runs/30177577349

## Gates

| Gate | Result |
| --- | --- |
| Local CI | pass (macOS 639/639; server 2,426 passed / 1 skipped; strict PostgreSQL 41 passed / 1 skipped) |
| Contract, lint, compile, Compose and evidence scans | pass |
| Remote deploy | pass (`deployed_sha=0c16b218…`) |
| Backup | pass (`20260725T230245Z`) |
| Restore rehearsal | pass |
| Migration verification | pass (`0041_share_account_created_email`) |
| Disposable PostgreSQL RLS probes | pass; live destructive production probe not attempted |
| Production smoke | pass (`infra_smoke_ready`) |
| External invitation API/worker configuration | pass |
| Automatic dispatch | pass |
| Temporal and processing worker readiness | pass |
| Public health | pass (`live=200`, `ready=200`) |
| Post-deploy retry/backfill/range/cleanup follow-up | explicitly marked `required_post_deploy` by the deploy gate; not run as part of this release |

## macOS update artifacts

- Public feed version: `2026.07.26.2`.
- ZIP SHA-256: `93303094f0bfa0f3ff37b100551cf752171c6f0141a5a94ef4db28e3790127b4`.
- PKG SHA-256: `b48068705daab18298f84658648f9c12bcaf292679fddc0b2c22031482e6c343`.
- Appcast SHA-256: `f683027e752e984ee80ecedbc1660850735dfdff74591fd5f49599991db2f873`.
- Public HTTPS download, ZIP/XML validation, Sparkle signature and owner-only
  trust continuity validation passed.
- The installed `2026.07.26.1` app found and displayed the signed
  `2026.07.26.2` offer through `GRAF > Check for Updates…`.
- The final in-app install click could not be completed in this session because
  the macOS desktop was locked. The PKG was not used as a substitute for the
  Sparkle update.

## Rollback reference

- Public feed backup:
  `/opt/projects/2brain-rec/infra/runtime/public-downloads/graf-appcast.xml.pre-v2026.07.26.2-20260725T223349Z`.
- Server backup:
  `/opt/projects/2brain-rec/backups/20260725T230245Z`.
- A rollback must publish only a previously signed appcast and archive; never
  publish an unsigned downgrade.
- The macOS package is signed with the local owner-only GRAF signing identity;
  this release is not a public Apple Developer ID/notarized distribution.
