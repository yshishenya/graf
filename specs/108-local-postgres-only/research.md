# Research: Локальная разработка только с PostgreSQL

## Decision 1 — Reuse the existing local PostgreSQL service

**Decision**: Use only `rec-postgres` from `infra/docker-compose.dev.yml`. It
is pinned to `postgres:17-alpine`, exposes the local development port, and has
a readiness health check.

**Rationale**: The project already has the same PostgreSQL major version in
development and production configuration. Reusing it avoids a divergent second
Compose topology, a second port and an extra source of credentials.

**Alternatives considered**:

- Add a dedicated test Compose file — rejected because it duplicates an
  already-suitable service and creates configuration drift.
- Test against production Compose — rejected because it needs production
  secrets and would violate isolation.
- Keep SQLite as a fast test lane — rejected by the requested scope and because
  it cannot prove PostgreSQL constraints, RLS or locking behavior.

## Decision 2 — Use one generated disposable PostgreSQL database per test run

**Decision**: A server-owned runner creates a randomly suffixed database under
the local development PostgreSQL service, exports its URL to pytest and RLS
tests, and always drops it using a cleanup trap.

**Rationale**: The existing `twobrain_rec` development database may contain
local work. Resetting it would be destructive. A generated database keeps
tests isolated while allowing migration and role tests to use true PostgreSQL
semantics.

**Alternatives considered**:

- Reuse a fixed test database — rejected because interrupted or concurrent
  runs can contaminate each other.
- Use a schema in the local development database — rejected because migrations
  and role/RLS tests expect database-level isolation.
- Create a database per test — rejected because hundreds of database creates
  would make the suite materially slower; one disposable database per run is
  sufficient when fixtures clean their own state.

## Decision 3 — Fail closed for database targets

**Decision**: The runner accepts only a PostgreSQL async URL on a loopback
host with a generated `twobrain_rec_test_` database name. It rejects missing
Docker, unavailable readiness, non-local hosts and non-disposable names before
creating, migrating or deleting data.

**Rationale**: The greatest risk is an accidental command against a developer
or production database. A deterministic local-only boundary makes the safe
path easy and the unsafe path impossible by default.

**Alternatives considered**:

- Trust environment variables — rejected because environment inheritance is
  easy to get wrong.
- Require a manual password or production URL — rejected because local Compose
  already supplies non-production development credentials and no real secret
  is needed.

## Decision 4 — Retain asyncpg and remove SQLite support completely

**Decision**: Remove `aiosqlite` from development dependencies and lockfiles;
validate server database URLs as PostgreSQL async URLs; replace SQLite fixture
URLs, sync SQLite inspection and SQLite-specific partial-index declarations
with PostgreSQL equivalents.

**Rationale**: `asyncpg` is already a runtime dependency. Adding a second
driver only to inspect tests would retain a divergent data path.

**Alternatives considered**:

- Keep a hidden SQLite compatibility test — rejected by FR-004 and because it
  weakens the production-faithful guarantee.
- Add a synchronous PostgreSQL driver — rejected: SQLAlchemy async tooling
  already supports the migrations and test queries without one.

## Decision 5 — Preserve historical evidence but remove active guidance

**Decision**: Remove SQLite references from active server source, tests,
dependency metadata, local configuration and current run instructions. Keep
old changelog/spec/evidence references as archival facts and exclude them from
the regression scan.

**Rationale**: Rewriting historical proof would make the repository less
truthful and cannot affect runtime behavior. The active surface remains fully
SQLite-free.
