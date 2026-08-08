# Production closeout: v2026.07.26.4

> Historical production receipt. Its owner-only/local signing facts are kept for
> audit history only; current public macOS publication is Developer ID-only.

## Immutable release

- Tag: `v2026.07.26.4`
- Deployed SHA: `672ebcad6e9920652f08a5b2a29a56fc943bc785`
- Deploy branch: `master`
- Host/path: `2brain.dev:/opt/projects/2brain-rec`
- GitHub Release: https://github.com/yshishenya/crisp/releases/tag/v2026.07.26.4
- Feature PR: https://github.com/yshishenya/crisp/pull/4611
- Tracking issue: https://github.com/yshishenya/crisp/issues/4610

## What changed

- The macOS embedded webview now allows the canonical `/desktop/settings`
  overview, category pages and existing settings mutation routes.
- Desktop headers, protected-history behavior and native capture controls remain
  unchanged.
- The native `Автозапись`/capture settings window remains a separate local
  control surface; the web cabinet `Настройки` link opens the web settings IA.

## Gates

| Gate | Result |
| --- | --- |
| Focused Swift route-policy tests | pass (65/65) |
| Local CI | pass (macOS 640 passed; server 2,438 passed / 1 skipped; strict PostgreSQL 41 passed / 1 skipped) |
| Contract, lint, compile, Compose and evidence scans | pass |
| Remote deploy | pass (`deployed_sha=672ebcad…`) |
| Backup | pass (`20260726T101950Z`) |
| Restore rehearsal | pass |
| Migration verification | pass (`0041_share_account_created_email`) |
| Disposable PostgreSQL RLS probes | pass; live destructive production probe not attempted |
| Production smoke and readiness | pass (`infra_smoke_ready`) |
| Public health | pass (`live=200`, `ready=200`) |
| Post-deploy retry/backfill/range/cleanup follow-up | explicitly marked `required_post_deploy` by the deploy gate; not run as part of this release |

## Installed-client update smoke

- Public Sparkle feed was published before the client check and advertised
  `2026.07.26.4`.
- Installed `/Applications/GRAF.app` updated from `2026.07.26.3` to
  `2026.07.26.4` through `GRAF > Check for Updates…` and restarted.
- The web cabinet `Настройки` link then opened the settings overview inside the
  embedded webview; the overview and five category links were present, and the
  old `Функция недоступна` state was absent.
- Native capture behavior was not changed by the update smoke.

## Public update artifacts

- Feed: https://rec.2brain.pro/static/public/downloads/graf-appcast.xml
- Archive: https://rec.2brain.pro/static/public/downloads/GRAF-2026.07.26.4.zip
- ZIP SHA-256: `89599c159ee4aad58428f4b52c192decab2fe3b0ae9d51655ae563c4aacc7a72`
- Appcast SHA-256: `262010a97fa34dd0797016f4be1344d8f63e3eadcf7311993e266943aa958098`
- Public HTTPS fetch, ZIP integrity, appcast version and enclosure checks passed.

## Compatibility and rollback

- No database migration was introduced by this slice.
- The update channel uses the repository's owner-only local signing mode; this
  release does not claim Apple Developer ID signing or notarization.
- Previous appcast backup:
  `/opt/projects/2brain-rec/infra/runtime/public-downloads/graf-appcast.xml.pre-v2026.07.26.4-20260726T102603Z`.
- Rollback must publish only a previously signed appcast and archive.
