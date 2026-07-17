# Local PostgreSQL Test Runner Contract

## Purpose

Provide the one supported entry point for local server tests using an isolated
PostgreSQL database.

## Invocation

```sh
bash apps/server/scripts/run_local_postgres_tests.sh [pytest arguments...]
```

The runner starts only the existing local `rec-postgres` service when needed,
waits for readiness, creates a generated test database, runs pytest with the
received arguments and removes that database on exit.

## Preconditions

- Docker Engine is running locally.
- The checked-out repository includes `infra/docker-compose.dev.yml`.
- No production database URL, password or secret is supplied.

## Safety contract

- The runner accepts only a loopback PostgreSQL target and a generated database
  name beginning with `twobrain_rec_test_`.
- It must fail before data mutation if the host, scheme or database name fails
  validation.
- It must not start production Compose, inspect production secrets or change
  `infra/docker-compose.yml`.
- It must remove the generated database on success, failure and interruption.

## Environment exposed only to pytest

| Variable | Meaning |
|---|---|
| `TWOBRAIN_DATABASE_URL` | Generated disposable database URL for ordinary server tests |
| `RLS_TEST_DATABASE_URL` | Same generated disposable database URL for RLS integration proofs |

The runner does not print credentials in normal output. Its error messages name
the failing local condition and the recovery command.
