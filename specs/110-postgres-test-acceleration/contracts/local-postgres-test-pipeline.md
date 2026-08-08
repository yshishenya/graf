# Contract: local PostgreSQL test pipeline

## Supported entry point

```sh
bash apps/server/scripts/run_local_postgres_tests.sh [pytest arguments]
```

The runner is the only supported local server-test entry point. It starts one
disposable `postgres:17-alpine` Docker container with a random loopback port;
it must never select production Compose, `rec-postgres`, a remote host, a
developer database or SQLite.

## Database safety

- The runner generates a unique lower-case run prefix and a one-run media-role
  credential from local process-safe entropy. It owns its disposable container
  and every database whose name starts with that exact prefix.
- Every main, clean and RLS URL must use the asyncpg PostgreSQL scheme, a
  loopback host, and a database name owned by that prefix before any connect,
  create, migrate, truncate, role operation or drop.
- Cleanup occurs after success, test failure, shell error, `INT` and `TERM`.
  It force-removes only the generated disposable container; this removes all
  worker, clean and RLS databases together and cannot affect a developer or
  production PostgreSQL instance.
- A container is accepted only after PostgreSQL readiness and creation of its
  generated RLS database succeed. A transient local Docker startup failure is
  retried once with a newly generated disposable container; no shared service
  is reused.
- The runner never prints a URL, password, token, raw test payload, meeting
  content or local credential path.

## Full-mode phases

| Phase | Membership | Execution | Isolation |
|-------|------------|-----------|-----------|
| `parallel` | all tests except the explicit global-role RLS modules | fixed bounded worker count, default eight (maximum eight), `pytest-xdist --dist=loadfile` | one migrated worker DB per worker; fast baseline is bounded truncate + seed |
| `strict` | `test_rls_postgres_policies.py` and `test_playback_normalization_postgres.py`, plus callers marked as strict when needed | serial | a clean RLS database; advisory lock serializes fixed global roles within the disposable cluster |

The full mode must first collect the current same-commit node-ID set, then
verify that the union of phase node IDs exactly matches it. The pre-feature
count of 1,822 is a minimum reference, not a frozen final number. Full mode may
use internal phase filtering only for that partition; it must not add a
persistent `--ignore`, `-k`, deselect or skip to make the full result faster.

Focused invocation may run an explicitly named test file, but it must retain
the same database safety checks and must label itself as focused rather than
full evidence. `--full` with a focused pytest selection is rejected rather
than relabelled as complete evidence.

## Fast fixture contract

- `postgres_seeded_database_url` is for normal `client` tests only. It upgrades
  one worker database to the real Alembic head once, resets only the known
  metadata table inventory with quoted identifiers, and restores the
  deterministic base seed before each caller.
- `postgres_clean_database_url` is for migration, RLS and empty-schema tests.
  It starts from a verified empty state and is never substituted with the fast
  fixture.
- Any direct worker execution must apply its exact tenant scope with
  `context_kind="worker"` before protected service work. Scheduler and
  reconciliation tests use the disposable `twobrain_rec_media` role, because
  their production SQL functions verify `session_user`. The service guard is
  not configurable by the runner.

## Observable output

For a completed invocation the runner emits metadata-only lines sufficient to
identify:

- full versus focused mode and effective worker count;
- collection digest/count and outcome/skip/xfail counts for every phase;
- phase wall times, pytest's 20 slowest scenarios and cleanup status;
- a clear Docker/loopback/disposable-target error before unsafe work begins.

`pass` is emitted only after every required phase and cleanup evidence pass.
