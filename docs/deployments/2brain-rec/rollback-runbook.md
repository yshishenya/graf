# Rollback And Halt Runbook

This runbook covers the `021-production-deployment-plan` infrastructure smoke
only. A successful run can at most support `infra_smoke_ready`.

## Decision Classes

- `dns_tls`: halt and fix DNS/TLS before retry.
- `secrets`: halt and rotate or repair production secret files before retry.
- `health`: halt and inspect Rec API, Postgres, MinIO, and reverse proxy state.
- `migration`: restore from the latest verified backup reference before retry.
- `backup`: block rollout until backup evidence exists.
- `restore_rehearsal`: block rollout until restore rehearsal passes.
- `storage`: halt and inspect Postgres/MinIO volume availability.
- `disk_full`: halt and free or expand disk before accepting smoke artifacts.
- `unsafe_exposure`: halt and remove public exposure for internal-only services.
- `smoke_upload`: roll back to the prior state reference and clean smoke residue.
- `forbidden_content`: halt, quarantine evidence/log output, and re-run redaction.
- `cleanup`: block readiness until residue owner and follow-up are recorded.

## Dry Run

```sh
infra/scripts/rollback-rec-stack.sh --dry-run --trigger health
```

Expected fields:

```text
rollback_decision=halt
trigger=health
remote_host=2brain.dev
deploy_path=/opt/projects/2brain-rec
cleanup_obligations=record_any_residue_before_retry
```

## Remote Execution

Run on the workstation only after choosing a trigger:

```sh
infra/scripts/rollback-rec-stack.sh --remote --trigger migration --prior-state-reference backup-YYYYMMDD
```

The command runs in `/opt/projects/2brain-rec` on `2brain.dev`. For restore or
rollback decisions, evidence must include a prior-state reference. For any
cleanup obligation, evidence must include residue owner and follow-up reason.

## Truthful Status

Do not mark a failed or partially cleaned run as ready. Use `blocked`, `halt`,
`restore`, or `rollback` evidence until the failed gate is fixed and the smoke
is re-run.
