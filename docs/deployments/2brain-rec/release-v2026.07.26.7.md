# Production closeout: v2026.07.26.7

## Immutable release

- Tag: `v2026.07.26.7`
- Deployed SHA: `0b2680433ffda9137ea63e16ec99153e37bcb562`
- Deploy branch: `codex/deploy-202607267`
- Host/path: `2brain.dev:/opt/projects/2brain-rec`
- GitHub Release: https://github.com/yshishenya/crisp/releases/tag/v2026.07.26.7
- Feature PR: https://github.com/yshishenya/crisp/pull/4626
- Release PR: https://github.com/yshishenya/crisp/pull/4627
- Tracking issue: https://github.com/yshishenya/crisp/issues/4624

## What changed

The first-entry external invitation path now flushes its auth-audit row while
the personal workspace context is active, before switching to the source
meeting workspace. This removes the production RLS autoflush 500 without
weakening recipient, CSRF, replay, expiry, revoke, grant or notification
boundaries.

No database migration was introduced.

## Gates

| Gate | Result |
| --- | --- |
| Focused invitation contract/integration matrix | pass (`23/23`) |
| Full local/CD CI | pass (macOS `640`; server `2441 passed / 1 skipped`; strict `42 passed / 1 skipped`) |
| Contract, lint, compile, Compose and evidence scans | pass |
| Protected macOS signing workflow | pass (`30201742396`) |
| Candidate continuity, ZIP and Sparkle signatures | pass |
| macOS update smoke | pass (trusted v6 bootstrap → v7, relaunch and deep strict codesign) |
| Remote deploy | pass (`deployed_sha=0b268043…`) |
| Backup | pass (`20260726T123714Z`) |
| Restore rehearsal | pass |
| Migration verification | pass (`0041_share_account_created_email`) |
| Disposable PostgreSQL RLS probes | pass; live destructive probe not attempted |
| Production smoke and readiness | pass (`infra_smoke_ready`) |
| Public health | pass (`live=200`, `ready=200`) |
| Post-deploy retry/backfill/range/cleanup follow-up | explicitly `required_post_deploy` |

## Production log audit

An aggregate-only API log audit covering the first 20 minutes after rollout
reported:

- `http_500_matches=0`;
- `auth_audit_rls_error_matches=0`;
- `traceback_matches=0`;
- `error_level_matches=0`.

No user invitation token, email address, meeting material, audio or transcript
was replayed or recorded in evidence.

## Public update artifacts

- Feed: https://rec.2brain.pro/static/public/downloads/graf-appcast.xml
- Archive: https://rec.2brain.pro/static/public/downloads/GRAF-2026.07.26.7.zip
- ZIP SHA-256: `f71af4dd687b5a7a4d2d1faae1fb54c78bc5439ebead7b52bd60ac9e19c77500`
- Appcast SHA-256: `aa3d1b9993a786b8efc9f29bbc07a7d85575fd71e7007381b4a64ef040982e49`
- Previous appcast backup:
  `/opt/projects/2brain-rec/infra/runtime/public-downloads/graf-appcast.xml.pre-v2026.07.26.7-20260726T121942Z`.

## Compatibility and rollback

- The existing migration head and stored user data remain compatible; no
  migration or data transfer is required.
- Rollback must restore a previously signed appcast/archive and use the guarded
  deployment rollback runbook; never publish an unsigned downgrade.
- v6 is the notarized manual bootstrap. v7 is Developer ID signed and passed
  Sparkle continuity/update smoke, but v7 notarization staple and public
  Gatekeeper trust remain unclaimed because Apple credentials were unavailable
  in this release operator environment.
