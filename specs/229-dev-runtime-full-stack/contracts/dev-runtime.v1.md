# GRAF Dev Runtime Contract v1

This is the GRAF-specific extension of `infra/dev/manifest.schema.json`.

## Candidate identity

- Input is one full 40-character `source_sha` from the checked-out branch.
- Checkout must be a named branch, clean and exactly at that SHA.
- Backend, server-rendered frontend, processing/media/maintenance workers,
  migration image and macOS app must report or carry the same source SHA.
- Mutable branch names, `latest` tags and an unverified manifest are not identity.

## Service set

The full local candidate contains these logical services:

`rec-postgres`, `rec-minio`, `rec-minio-init`, `rec-migrate`, `rec-temporal`,
`api`, `rec-processing-worker`, `rec-maintenance`, and `rec-media-worker`.

The frontend is server-rendered by `api`; a second frontend server is not part
of v1. The macOS client is the separately staged `GRAF Dev.app`.

## Boundary

- Compose project, network, volume and state names are explicit and Dev-scoped.
- Host bindings are loopback-only.
- The reserved loopback bindings are API/frontend `8081`, PostgreSQL `54329`,
  MinIO API/console `9002/9003` and Temporal `7233`; a configured port collision
  blocks startup before promotion.
- `GRAF Dev.app` is the only Dev destination and has bundle ID
  `pro.2brain.graf.dev`, channel `dev`, stable designated requirement/signing
  identity, display/bundle name `GRAF Dev`, an icon distinct from production
  with the Dev badge, and no production updater metadata.
- Production app, origins, volumes, databases and credentials are rejected
  before mutation.

## Migration gate

1. Resolve current graph heads from the checked-out code.
2. Read observed database state through the isolated connection.
3. Treat empty new state as eligible for the normal migration command.
4. Treat exact match as eligible to continue.
5. Treat unknown, missing, divergent or multiple heads as `blocked` with a safe
   fresh-namespace instruction.
6. Never stamp, directly edit `alembic_version`, or destroy a volume to hide a
   mismatch.

The API and workers must not become ready before this gate succeeds.

## Readiness/smoke gate

Required metadata-only check names are:

`backend_health`, `frontend_reachability`, `auth_session_bootstrap`,
`representative_api`, `temporal_readiness`, `processing_worker_readiness`,
`media_worker_readiness`, `database_readiness`, `storage_readiness`,
`app_identity`, `app_presentation`, and `exact_source_sha`.

`app_presentation` passes only when the newly launched process belongs to the
installed `/Applications/GRAF Dev.app`, both visible bundle names are
`GRAF Dev`, the channel is `dev`, and `AppIcon.icns` is present and distinct
from the production icon.

Every required check must be `pass`. A provider call is not required for this
local contract; provider credentials are never placed in the desktop app or
receipt.

Readiness uses bounded probes: HTTP probes have a 3-second per-attempt timeout
and a 90-second aggregate deadline; Compose health checks use explicit 5–10
second intervals and finite retry counts. An exhausted deadline is `fail`, not
`unknown` or an implicit retry loop.

## Transaction and rollback

- Promotion takes the shared Dev lock and validates the candidate's parent.
- The installed Dev process is identified by its bundle path, gracefully
  terminated with native macOS APIs and given a bounded exit deadline before
  replacement; direct installer use fails closed while that process is running.
- App and runtime are staged before active pointer replacement.
- Native app registration is refreshed and the newly installed bundle is
  launched before smoke.
- The pointer is committed only after all smoke checks pass.
- On failure, previous app/runtime/pointer and the previous app launch state
  remain recoverable; an unowned PID or unknown Compose project is never
  terminated.
- Rollback checks out the target SHA, restores the app and stack, runs the same
  smoke gate and records a metadata-only result.
