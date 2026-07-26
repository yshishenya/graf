# Production closeout: `v2026.07.26.8`

## Immutable release

- Tag: `v2026.07.26.8`
- Deployed SHA: `15309573ff8ff0fa5ed97269c6577f68db57c439`
- Deploy branch: `codex/deploy-202607268`
- Runtime checkout: `master` at the same SHA
- Host/path: `2brain.dev:/opt/projects/2brain-rec`
- GitHub Release: https://github.com/yshishenya/crisp/releases/tag/v2026.07.26.8
- Feature PR: https://github.com/yshishenya/crisp/pull/4644
- Release PR: https://github.com/yshishenya/crisp/pull/4645
- Evidence fix PR: https://github.com/yshishenya/crisp/pull/4669

## macOS release gates

| Gate | Result |
| --- | --- |
| Developer ID Application / Installer identities | pass; Team `94N8HYG672` |
| Apple app notarization | pass; request `284f3183-59a5-44c1-98fb-d3551371cec5` |
| Apple package notarization | pass; request `c80a49db-6d10-42c0-8b95-e80d05072068` |
| Stapler and Gatekeeper | pass for app and package |
| Protected Sparkle signing workflow | pass; run `30207475500` |
| Developer ID → Developer ID continuity | pass; installed `.7 → .8` update |
| Final public HTTPS artifact checks | pass; ZIP, PKG, appcast and SHA-256 match |

## Repository and deployment gates

| Gate | Result |
| --- | --- |
| Full local CI on exact deployed SHA | pass; macOS `642`; server `2441 passed / 1 skipped`; strict `42 passed / 1 skipped`; lint, compile, Compose and evidence scan pass |
| Deploy-time local-CI retry | not reused: host resource/process contention interrupted retries; execute used `--skip-local-ci` with no source or tag changes after the authoritative exact-SHA pass |
| Remote guarded deploy | pass; `deployed_sha` matches the tag |
| Backup | pass; `/opt/projects/2brain-rec/backups/20260726T154448Z` |
| Restore rehearsal | pass |
| Migration verification | pass; head `0041_share_account_created_email` |
| Disposable PostgreSQL RLS validation | pass; production destructive probe not attempted |
| Image capability and profile contract | pass |
| Production smoke and readiness | pass; `infra_smoke_ready` |
| Temporal and processing-worker readiness | pass |
| Automatic dispatch gate | pass |
| Public health | pass; `live=200`, `ready=200` |

The deploy command completed with `deploy_result=pass`; no rollback was
required. Remote post-deploy checks confirmed the exact runtime SHA and a clean
working tree.

## Post-deploy audit

An aggregate-only API log audit covering the rollout window reported:

- `http_500_matches=0`;
- `auth_audit_rls_matches=0`;
- `traceback_matches=0`.

Public health endpoints returned HTTP 200 with `{"status":"ok"}` and
`{"status":"ready"}` respectively.

## Public artifacts

- Feed: https://rec.2brain.pro/static/public/downloads/graf-appcast.xml
- ZIP: https://rec.2brain.pro/static/public/downloads/GRAF-2026.07.26.8.zip
- PKG: https://rec.2brain.pro/static/public/downloads/GRAF-2026.07.26.8.pkg
- ZIP SHA-256: `443412a79af8c956d5a215ce770d26b6c7210cbc87f0a16f4fdfae1f21d990e5`
- PKG SHA-256: `8d3034063f9f3d2bd9fd5289b718b19a822362a73d1bf867a255ae5ab51c2f24`
- Appcast SHA-256: `ffb05f5d5d8c213ce45080acb9708ad973b209ad1b8d1e5e1c18a60efe053834`
- Previous appcast backup:
  `/opt/projects/2brain-rec/infra/runtime/public-downloads/graf-appcast.xml.pre-v2026.07.26.8-20260726T151014Z`

## Compatibility, rollback and follow-up

- Existing `.6` bootstrap and `.7` Developer ID clients remain compatible with
  the `.8` Sparkle update; older pre-bootstrap installations still require the
  one-time notarized `.pkg` path.
- Rollback must restore a previously verified signed feed/archive and use the
  guarded deployment rollback runbook. Never publish an unsigned downgrade.
- CD recorded `automatic_retry_result`, `backfill_inventory_result`,
  `range_playback_result` and `normalization_cleanup_result` as
  `required_post_deploy`; these are separate maintenance follow-ups.

All committed evidence is metadata-only and contains no user-specific data.
