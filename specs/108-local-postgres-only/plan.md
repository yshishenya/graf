# Implementation Plan: Локальная разработка только с PostgreSQL

**Branch**: `codex/108-local-postgres-only` | **Date**: 2026-07-17 | **Spec**: [spec.md](spec.md)

**Input**: Переход активного server/dev/test пути с SQLite на локальный PostgreSQL.

## Summary

Единый локальный PostgreSQL 17 уже описан в `infra/docker-compose.dev.yml`.
Новый безопасный test-runner поднимает только `rec-postgres`, создаёт уникальную
временную базу, передаёт её URL серверным тестам и RLS-проверкам, а затем
удаляет её даже при ошибке. Все SQLite URL, драйвер, частичные индексы,
фикстуры и миграционные проверки заменяются PostgreSQL-вариантами. Production
Compose, его роли, секреты и данные не меняются.

## Technical Context

**Language/Version**: Python 3.13, shell; SQLAlchemy/Alembic migrations

**Primary Dependencies**: FastAPI, SQLAlchemy async, Alembic, asyncpg, pytest, Docker Compose

**Storage**: PostgreSQL 17 only; local development service from `infra/docker-compose.dev.yml`

**Testing**: pytest and Alembic on a generated disposable PostgreSQL database; `infra/scripts/ci-local.sh`

**Risk / Validation Lane**: High-risk feature — it changes Postgres, Docker, migrations, test isolation and a shared server path.

**Release Gate**: No production deploy until the feature is integrated and the full local gate passes; this migration changes no production database or rollout configuration.

**Target Platform**: macOS local development and Linux-compatible CI shell; server runs in Docker

**Project Type**: Server web service and local developer tooling

**Performance Goals**: Test bootstrap fails fast on an unavailable service; a test run uses one isolated temporary database and leaves no test databases behind.

**Constraints**: Never use or derive a production address, secret, database name, role or volume. Keep the existing production Compose file unchanged. Retain only historical SQLite references that are immutable evidence, not active instructions.

**Scale/Scope**: Replace the 37 active SQLite references currently found under `apps/server`, then guard the supported active paths against regression.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

**Pre-design — PASS.**

- Docker and PostgreSQL are explicitly high-risk under Constitution V, so the full Spec Kit lane is used.
- The implementation keeps `infra/docker-compose.yml`, production roles, secrets, network topology and persistent volumes untouched.
- The test runner must reject non-local and non-disposable database targets before any migration, creation or cleanup command.
- No capture, client, audio, retention or production data behavior changes are in scope.

**Post-design — PASS.**

- `research.md` selects the existing pinned PostgreSQL 17 dev service, avoiding a duplicate database image or dependency.
- The test lifecycle owns a generated database name and cleans it through a shell trap; no shared development database is reset.
- The data/configuration contract and quickstart name the safe URL boundary and recovery behavior.

## Validation Plan

- `docker compose -f infra/docker-compose.dev.yml config` validates the local service description without production secrets.
- The local runner validates Docker availability and PostgreSQL readiness, creates a disposable database, runs the focused PostgreSQL migration and fixture tests, then verifies cleanup.
- Focused regression checks prove that active server files contain no SQLite dependency, URL or dialect-specific index branch.
- `infra/scripts/ci-local.sh` is mandatory before PR/closeout; it must prepare the same local PostgreSQL test boundary before server pytest.
- `ruff`, Python compilation, Compose configuration and the existing RLS boundary remain part of the canonical local gate.
- No deploy is run during implementation because no production deployment input, image, secret or schema change is part of this slice.

## Project Structure

### Documentation (this feature)

```text
specs/108-local-postgres-only/
├── plan.md
├── research.md
├── data-model.md
├── contracts/
├── quickstart.md
└── tasks.md
```

### Source Code (repository root)

```text
apps/server/
├── pyproject.toml                         # dependencies and pytest settings
├── uv.lock                                # resolved dependency graph
├── scripts/
│   └── run_local_postgres_tests.sh         # safe test database lifecycle
├── src/twobrain_rec_server/
│   ├── config.py                           # PostgreSQL-only server configuration
│   └── db/
│       ├── models/                         # PostgreSQL partial-index declarations
│       └── migrations/versions/            # PostgreSQL migrations
└── tests/
    ├── conftest.py                         # PostgreSQL fixture boundary
    ├── fixtures/                           # disposable database helpers
    ├── contract/
    ├── integration/
    └── unit/

infra/
├── docker-compose.dev.yml                  # existing pinned local PostgreSQL service
└── scripts/ci-local.sh                     # canonical local gate prepares test DB
```

**Structure Decision**: Reuse the existing server and dev Compose structure.
The only new operational surface is a small server-owned runner/helper so test
database lifecycle is versioned beside the tests that depend on it.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|---|---|---|
| None | The existing local PostgreSQL Compose service and `asyncpg` dependency are reused. | A second Compose stack, a sync driver, or a production database shortcut would add risk without user value. |
