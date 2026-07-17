# Quickstart: Локальная разработка только с PostgreSQL

## Prerequisites

- Docker Desktop or Docker Engine is running locally.
- Run commands from the repository root.
- Do not export a production database URL for this workflow.

## Run focused server tests

```sh
bash apps/server/scripts/run_local_postgres_tests.sh
```

Expected result: the script starts or reuses only the local `rec-postgres`
service, reports readiness, runs pytest against a generated disposable
PostgreSQL database, and removes that database before exiting.

To run one focused path:

```sh
bash apps/server/scripts/run_local_postgres_tests.sh tests/integration/test_postgres_migrations.py -q
```

## Verify the canonical local gate

```sh
infra/scripts/ci-local.sh
```

Expected result: server tests use the same local PostgreSQL-only runner;
lint, compilation, Compose validation and the RLS boundary also complete.

## Recovery

If the runner says that Docker is unavailable, start Docker Desktop and retry.
If the local port is occupied, inspect the local development Compose project;
do not change the target to a remote database. The runner must never fall back
to SQLite.

## Regression proof

```sh
rg -n -i 'sqlite|aiosqlite|sqlite3|sqlite\\+' apps/server infra/scripts infra/docker-compose.dev.yml
```

Expected result: no active runtime, test, dependency or local operational
instruction matches. Historical artifacts outside those active paths may
truthfully mention past SQLite support.
