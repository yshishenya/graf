# Production closeout: `v2026.07.27.1`

## Immutable release

- Tag: `v2026.07.27.1`
- Deployed SHA: `7f41dc93584d6fbd23b84356cde85b913c28bee9`
- Deploy branch: `codex/deploy-202607271`
- Runtime checkout: `master` at the same SHA
- Host/path: `2brain.dev:/opt/projects/2brain-rec`
- GitHub Release: https://github.com/yshishenya/crisp/releases/tag/v2026.07.27.1
- Feature PR: https://github.com/yshishenya/crisp/pull/4685
- Release PR: https://github.com/yshishenya/crisp/pull/4686

## macOS release gates

| Gate | Result |
| --- | --- |
| Developer ID Application / Installer identities | pass; Team `94N8HYG672` |
| Apple candidate ZIP notarization | pass; request `12aa69e7-4ed1-405c-adae-4e212becfd6d` |
| Apple package notarization | pass; request `6346e41e-4ec6-41f3-9ac4-410244f6e95c` |
| Stapler and Gatekeeper | pass for app and package |
| Protected Sparkle signing workflow | pass; run `30225833991` |
| Developer ID → Developer ID continuity | pass; validator `v2026.07.26.11 → v2026.07.27.1` |
| Public HTTPS artifact fetch | pass; ZIP, PKG, appcast and checksum manifest match |

## Repository and deployment gates

| Gate | Result |
| --- | --- |
| Full local CI on exact release source | pass; macOS `642`; server `2456 passed / 1 skipped`; strict `42 passed / 1 skipped` |
| Ruff, Python compile, ContractValidation, Compose and evidence scan | pass |
| CD dry-run | pass; branch, clean worktree and required gate list confirmed |
| Remote guarded deploy | pass; `deployed_sha` matches tag |
| Backup | pass; `/opt/projects/2brain-rec/backups/20260726T235630Z` |
| Restore rehearsal | pass; PostgreSQL and MinIO rehearsal targets created |
| Migration verification | pass; head `0041_share_account_created_email` |
| RLS hardening disposable validation | pass; live destructive production probe not attempted |
| Production smoke and readiness | pass; `infra_smoke_ready` |
| Temporal and processing-worker readiness | pass |
| Automatic dispatch gate | pass |
| Public health | pass; `live=200`, `ready=200` |
| Post-deploy retry/backfill/range/cleanup | explicitly `required_post_deploy` |

The deploy command returned `deploy_result=pass`; no rollback was required.
The runtime checkout and the deployed branch both resolve to the immutable tag
SHA.

## Post-deploy audit

Aggregate-only API logs for the rollout window reported:

- `http_500_matches=0`;
- `auth_audit_rls_matches=0`;
- `traceback_matches=0`;
- `error_level_matches=0`.

Public health endpoints returned HTTP 200. The audit collected counts only and
did not record user data, media payloads, credentials or raw request payloads.

## Public artifacts

- Feed: https://rec.2brain.pro/static/public/downloads/graf-appcast.xml
- ZIP: https://rec.2brain.pro/static/public/downloads/GRAF-2026.07.27.1.zip
- PKG: https://rec.2brain.pro/static/public/downloads/GRAF-2026.07.27.1.pkg
- ZIP SHA-256: `3ce77471f8da1f1b8621c7d3e9e9220f7428b67b7b86e1076ab58027e2123308`
- PKG SHA-256: `736ab05c9301e0532690a34f2292f3240250083e2211992dcd7cb74c406811ca`
- Appcast SHA-256: `92c4e5b0d12a89bd815f371b90b542c817a6fe83b9ec527d16569ed208eb01ea`
- Previous appcast backup:
  `/opt/projects/2brain-rec/infra/runtime/public-downloads/graf-appcast.xml.pre-v2026.07.27.1-20260726T234719Z`

## Compatibility and rollback

- Existing `.6` bootstrap and `.11` Developer ID clients remain compatible with
  the `.1` Sparkle update; older pre-bootstrap installations still require the
  one-time notarized `.pkg` path.
- Rollback must restore a previously verified signed feed/archive and use the
  guarded deployment rollback runbook. Never publish an unsigned downgrade.
- The required post-deploy maintenance follow-ups remain separate from this
  release and do not change the verified runtime readiness result.

All committed evidence is metadata-only and contains no user-specific data.
