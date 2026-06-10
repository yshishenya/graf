# Migration Runbook

Target host: `2brain.dev`
Deploy path: `/opt/projects/2brain-rec`
Compose project: `twobrain-rec`

This runbook is remote-first. Local execution is limited to tests, compile,
compose rendering, and static scans.

## Required Order

1. Record backup evidence using `docs/deployments/2brain-rec/backup-evidence-template.md`.
2. Run `infra/scripts/backup-rec-stack.sh --remote` from a checked-out deploy artifact or from the remote deploy path. The helper must create a Postgres logical dump and MinIO API mirror, not a live raw volume archive.
3. Verify migration state with `infra/scripts/verify-rec-migration.sh --remote`.
4. Run restore/rollback rehearsal with `infra/scripts/rehearse-rec-restore.sh --remote`. The rehearsal restores the Postgres dump into a temporary database and mirrors MinIO objects into a temporary bucket, then removes both temporary targets.
5. Continue only if backup, migration verification, and rehearsal pass.

## Halt Criteria

- DNS/TLS for `rec.2brain.pro` does not point to the deployment host.
- Required Docker secrets are missing.
- Compose config does not render on `2brain.dev`.
- Backup reference is missing or unsafe.
- Restore/rollback rehearsal is blocked, failed, or inconclusive.
- Evidence would require committing raw logs or live secrets.

## Evidence

Evidence must state `infra_smoke_ready` only after all 021 blocking gates pass.
Any failed or blocked migration step must produce `readiness_verdict=blocked`.
