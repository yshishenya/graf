# Data Model: Локальная разработка только с PostgreSQL

## Local PostgreSQL service

| Field | Rule |
|---|---|
| image family | PostgreSQL 17, inherited from `infra/docker-compose.dev.yml` |
| scope | Local Docker development only |
| readiness | PostgreSQL health check must succeed before tests start |
| protected resources | Production Compose, production hosts, secrets, roles and volumes are out of scope |

## Disposable test database

| Field | Rule |
|---|---|
| name | Generated `twobrain_rec_test_<random>` identifier |
| owner | The current test-runner process |
| lifecycle | Create after local readiness; drop in normal and error cleanup paths |
| connection | PostgreSQL async URL exported only to the test process |
| isolation | Never the developer's `twobrain_rec` database; never a remote host |
| validation | Host is loopback and database name has the approved generated prefix |

## Server database configuration

| Field | Rule |
|---|---|
| accepted scheme | PostgreSQL async driver URL only |
| rejected input | SQLite URLs and every unsupported storage driver |
| production behavior | Existing PostgreSQL URLs remain valid; this feature creates no migration of production data |
| test behavior | The runner overrides the database URL only in its child process |
