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

- Postgres artifact: `postgres.dump`
- MinIO artifact: `minio-objects/`
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
- postgres_artifact:
- minio_artifact:
- open_risks:
