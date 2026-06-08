# First Production Smoke

This runbook is remote-first. The target host is `2brain.dev`, and the project
directory is `/opt/projects/2brain-rec`.

The first smoke validates only the accepted `012` ingest boundary:
health, migration state, server-mediated upload finalization, Postgres
persistence, MinIO persistence, log redaction, cleanup, and zero forbidden side
effects. It does not validate transcription, notes, retention execution, user
rollout, or production readiness.

## Preconditions

- DNS for `rec.2brain.pro` resolves to the production reverse proxy.
- TLS terminates successfully for `https://rec.2brain.pro`.
- `/opt/projects/2brain-rec` contains the checked-out feature branch.
- Production env and Docker secret files exist only on the remote server.
- `infra/scripts/backup-rec-stack.sh --remote` has produced a backup reference.
- `infra/scripts/rehearse-rec-restore.sh --remote` has passed against that backup.
- `infra/scripts/verify-rec-migration.sh --remote` has passed.

## Dry Run

From the workstation:

```sh
infra/scripts/run-production-smoke.sh --dry-run
```

Expected result:

```text
smoke_result=blocked
reason=remote_execution_required_after_dns_tls_secrets_backup_and_restore_rehearsal
remote_host=2brain.dev
remote_path=/opt/projects/2brain-rec
```

## Remote Smoke

Run only after the preconditions pass:

```sh
infra/scripts/run-production-smoke.sh --remote
```

The script executes in `/opt/projects/2brain-rec` on `2brain.dev`, seeds a
dedicated `internal_smoke` identity/device, validates production config,
verifies migration state, uploads a non-sensitive smoke artifact through the
public Rec API, and cleans up smoke records and object keys.

## Cleanup Expectations

Cleanup must record:

- database records removed or retained;
- MinIO object keys removed or retained;
- residue owner and follow-up reason for any non-pass cleanup;
- no promise of universal erasure outside Rec-owned storage.

## Evidence Scan

Before copying evidence into the deployment notes:

```sh
infra/scripts/scan-deployment-evidence.sh docs/deployments/2brain-rec/infra-smoke-template.md
```

The scan must pass before an `infra_smoke_ready` verdict is accepted.
