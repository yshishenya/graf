# Production receipt: `v2026.07.26.6`

Дата: 2026-07-26
Repository tag: `v2026.07.26.6`
Release commit: `85bea4c0bdaf71989070ca40e960ea3c5050ad17`
GitHub Release: [v2026.07.26.6](https://github.com/yshishenya/crisp/releases/tag/v2026.07.26.6)

## Public macOS artifacts

- `GRAF-2026.07.26.6.zip` и `graf-2026.07.26.6.pkg` опубликованы по HTTPS.
- ZIP SHA-256: `9e462819b1c1940c407d054bc1ac8ebce3072124ff24205f08c605faf3cdb8a9`.
- PKG SHA-256: `d8eccb6d044ff45b13497e3f6113e209367d441adff58edda9a8680495dc8bf9`.
- `graf-local.pkg` указывает на тот же Developer ID/notarized package.
- `graf-appcast.xml` намеренно не заменялся: `.6` — ручной переход с
  исторической local/self-signed `.5`, а не ordinary Sparkle update.

## Gate evidence

- App: `Developer ID Application: Yan Shishenya (94N8HYG672)`.
- Installer: `Developer ID Installer: Yan Shishenya (94N8HYG672)`.
- App notarization: `c8642a45-dae5-41a2-be72-d2f382c8ea48`.
- Package notarization: `85f79bf3-1151-47bc-a0f7-43dd9943999a`.
- Stapler validation and Gatekeeper assessment passed for app/package.
- Public health/readiness remained `200/200` after deployment.

## Repository closeout evidence

- `infra/scripts/ci-local.sh`: `ci_local_result=pass`; 642 macOS-теста,
  2439 параллельных и 41 строгий PostgreSQL-тест, lint, compile, compose и
  deployment evidence scan прошли.
- `infra/scripts/cd-remote.sh --dry-run`: `deploy_result=dry_run` для ветки
  документационной миграции; повторный production execute не выполнялся.

## Migration boundary

Existing `.5` installations must use the versioned notarized `.pkg` once.
The active next-release path is only Developer ID Application/Installer with
notarization, stapling and Gatekeeper, then Developer ID → Developer ID Sparkle
validation. No local, ad-hoc or self-signed artifact may be uploaded to the
public host, GitHub Release or appcast.
