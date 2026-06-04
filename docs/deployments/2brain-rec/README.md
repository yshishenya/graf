# 2brain Rec Deployment Evidence

This directory stores metadata-only deployment evidence for the 2brain Rec
production deployment slice.

021 can only claim `infra_smoke_ready`. It must not claim production readiness,
user rollout readiness, or internal pilot readiness.

Do not commit live secrets, raw production logs, raw audio, transcript text,
bearer tokens, signed URLs, MinIO credentials, MediaScribe credentials, or
Langfuse credentials.

Expected production endpoint: `https://rec.2brain.pro`.

Remote deployment target:

- SSH host: `2brain.dev`
- Host address: `162.120.16.66`
- Deploy path: `/opt/projects/2brain-rec`
- Docker Compose project: `twobrain-rec`

Rec-owned persistent services:

- Postgres metadata volume.
- MinIO ingest object volume.

Internal-only services must stay on the private deployment network unless a
later Spec Kit slice explicitly changes the exposure model.

## Public And Private Boundary

The Rec API is expected to be reachable through the public endpoint
`https://rec.2brain.pro`. The compose service binds locally by default so the
2brain-controlled reverse proxy owns public TLS and routing.

Host nginx proxies `rec.2brain.pro` to the Rec API host binding
`127.0.0.1:18081`, while the container continues to listen on `8080`
internally.

DNS/TLS is a deployment gate. Before first smoke, `rec.2brain.pro` must resolve
to the `2brain.dev` deployment host and serve valid TLS. If DNS has not
propagated, smoke evidence must use `readiness_verdict=blocked`.

Postgres, MinIO, migration/init jobs, and MinIO console access are internal-only
for this slice.

## Volume Expectations

Postgres and MinIO volumes are Rec-owned deployment assets. They are included in
backup and restore rehearsal scope before migration or first smoke can claim
`infra_smoke_ready`.

Encryption expectation: use host/container-platform supported encryption where
available. If the production-like host cannot provide encryption, record the
exception in deployment evidence before smoke.

Disk-full behavior is a rollout halt condition. Do not accept smoke artifacts
when free-space checks are blocked or failed.

## Local Versus Remote

Local commands are limited to repository validation:

- tests and lint;
- Python compile checks;
- Docker Compose config rendering;
- secret/content scans.

Production deployment actions run on `2brain.dev` under `/opt/projects/2brain-rec`:

- backup-before-migration;
- migration verification;
- restore/rollback rehearsal;
- first production smoke through `https://rec.2brain.pro`;
- smoke cleanup and evidence capture.

Cleanup evidence must record residue owner and follow-up reason whenever
database records, MinIO objects, logs, or evidence fragments remain after a
blocked or failed smoke. A non-pass cleanup blocks `infra_smoke_ready`.

## Out Of Scope

021 does not implement federated auth, desktop uploader, MediaScribe processing,
Temporal processing starts, meeting dashboard, sharing, retention/deletion
execution, or driver packaging.
