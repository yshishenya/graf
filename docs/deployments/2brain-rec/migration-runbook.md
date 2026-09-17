# Migration Runbook

Target host: `2brain.dev`
Deploy path: `/opt/projects/2brain-rec`
Compose project: `twobrain-rec`

This runbook is release-first. Local execution is limited to tests, compile,
compose rendering, static scans and the CD dry-run. Production migration
verification is owned by the canonical release command.

## Required Order

1. Record backup evidence using `docs/deployments/2brain-rec/backup-evidence-template.md`.
2. Start the canonical release flow with `infra/scripts/cd-remote.sh --dry-run --branch master`.
3. After explicit release approval, run `infra/scripts/cd-remote.sh --execute --branch master`. It creates the backup, verifies the migration head and keeps the production lock for the entire sequence.
4. Do not invoke `verify-rec-migration.sh --remote`, `cd-remote-runtime.sh` or production smoke `--execute` directly: those entrypoints fail closed outside the release gate.
5. Continue only if the canonical release command reports backup, migration verification, health and smoke as passed.
6. The restore rehearsal is no longer part of the release. It runs weekly through `.github/workflows/backup-restore-rehearsal.yml`, or on demand with `infra/scripts/rehearse-restore-scheduled.sh --execute` from a workstation that can reach the host. Run it before a migration-heavy release when the last weekly run predates the change.

## Halt Criteria

- DNS/TLS for `rec.2brain.pro` does not point to the deployment host.
- Required Docker secrets are missing.
- Compose config does not render on `2brain.dev`.
- Backup reference is missing or unsafe.
- Restore/rollback rehearsal is blocked, failed, inconclusive, or older than the
  last week: the rehearsal runs weekly rather than per release, and a missing
  recent rehearsal blocks the rollout.
- Evidence would require committing raw logs or live secrets.

## Evidence

Evidence must state `infra_smoke_ready` only after all 021 blocking gates pass.
Any failed or blocked migration step must produce `readiness_verdict=blocked`.
