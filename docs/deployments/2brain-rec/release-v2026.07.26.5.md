# Production closeout: v2026.07.26.5

> Historical production receipt. `.5` is the local/self-signed predecessor for
> the manual Developer ID bootstrap in `.6`; its signing facts are audit history
> only and not a current release path.

## Immutable release

- Tag: `v2026.07.26.5`
- Deployed SHA: `57dde9fd745a89622f804ac1188eee548e805439`
- Deploy branch: `codex/deploy-v202607265`
- Host/path: `2brain.dev:/opt/projects/2brain-rec`
- GitHub Release: https://github.com/yshishenya/crisp/releases/tag/v2026.07.26.5
- Feature PR: https://github.com/yshishenya/crisp/pull/4612
- Release PR: https://github.com/yshishenya/crisp/pull/4613
- Tracking issues: #4607, #4608, #4609

## What changed

- Valid external invitation links now open a short transition and automatically
  submit the existing CSRF-bound one-time continuation POST.
- The recipient reaches the allowed summary or recording page without a
  mandatory metadata-preview screen.
- GET remains side-effect-free; exact identity, expiry, revoke, deletion and
  egress checks are unchanged. A no-JavaScript fallback action remains visible.

## Gates

| Gate | Result |
| --- | --- |
| Focused direct-link contract/integration matrix | pass (`21/21`) |
| Local CI | pass (macOS `640`; server `2,438 passed / 1 skipped`; strict PostgreSQL `41 passed / 1 skipped`) |
| Contract, lint, compile, Compose and evidence scans | pass |
| Protected macOS update signing workflow | pass (run `30198740256`) |
| Candidate continuity and public update artifacts | pass; ZIP/appcast fetch and SHA checks match |
| Installed-client update smoke | pass (`2026.07.26.4` → `2026.07.26.5`, restart and strict codesign) |
| Remote deploy | pass (`deployed_sha=57dde9fd…`) |
| Backup | pass (`20260726T110215Z`) |
| Restore rehearsal | pass |
| Migration verification | pass (`0041_share_account_created_email`) |
| Disposable PostgreSQL RLS probes | pass; live destructive production probe not attempted |
| Production smoke and readiness | pass (`infra_smoke_ready`) |
| Public health | pass (`live=200`, `ready=200`) |
| Post-deploy retry/backfill/range/cleanup follow-up | explicitly `required_post_deploy`; not run as part of this release |

The first guarded remote attempt stopped at staged rollout because Docker
reported a transient container-removal race; its automatic rollback passed.
The retry used the same immutable SHA after the remote health preflight and
completed successfully.

## Public update artifacts

- Feed: https://rec.2brain.pro/static/public/downloads/graf-appcast.xml
- Archive: https://rec.2brain.pro/static/public/downloads/GRAF-2026.07.26.5.zip
- ZIP SHA-256: `88b3fe3a4bd7c80248d2d60ea240e8ab161d6f87fde116907905d35f0106cce0`
- Appcast SHA-256: `33d21d2aa7040328340bd3a4c8500c05a78a9d634982c9f8b0b978fe01b906da`
- Previous appcast backup:
  `/opt/projects/2brain-rec/infra/runtime/public-downloads/graf-appcast.xml.pre-v2026.07.26.5-20260726T104454Z`.

## Compatibility and rollback

- No new database migration was introduced by this slice; deployment verified
  the existing migration head shown above.
- The update channel uses the repository's owner-only local signing mode; this
  release does not claim Apple Developer ID signing or notarization.
- Production backup reference:
  `/opt/projects/2brain-rec/backups/20260726T110215Z`.
- Rollback must publish only a previously signed appcast/archive and use the
  guarded deployment rollback runbook.
- Live rendered browser smoke was not claimed; the synthetic production smoke
  and live/ready checks passed.
