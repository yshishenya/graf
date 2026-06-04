# Backup Evidence Template

Use this template before any production migration or first-smoke operation that
can create persistent artifacts.

Do not include live secrets, raw logs, raw audio, transcript text, signed URLs,
or raw object contents.

## Backup Metadata

- run_id:
- date:
- branch_or_commit:
- operator:
- remote_host: `2brain.dev`
- deploy_path: `/opt/projects/2brain-rec`
- compose_project: `twobrain-rec`

## Scope

- Postgres volume: `twobrain-rec-postgres-data`
- MinIO volume: `twobrain-rec-minio-data`
- Backup destination reference:
- Encryption expectation:
- Retention expectation:

## Preflight

- [ ] DNS/TLS status recorded.
- [ ] Free disk status recorded.
- [ ] Required Docker secrets present on host.
- [ ] Compose config renders on remote host.

## Result

- backup_result: pass / blocked / failed
- backup_reference:
- open_risks:
