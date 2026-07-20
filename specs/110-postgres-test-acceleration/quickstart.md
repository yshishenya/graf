# Quickstart: validate the PostgreSQL test pipeline

## Prerequisites

- Docker Desktop is running and can start a disposable `postgres:17-alpine`
  container. The runner never starts or reuses `rec-postgres`.
- If Docker has a transient readiness race, the runner removes that container
  and makes one clean retry before returning an error.
- `uv` can resolve the server development environment.
- Do not export a production database URL. The supported runner derives and
  validates all disposable local targets itself.

## Focused regression proof

Run the direct worker-context regressions through the safe runner:

```sh
bash apps/server/scripts/run_local_postgres_tests.sh \
  tests/integration/test_playback_normalization_failures.py \
  tests/integration/test_playback_normalization_deletion.py -q
```

Expected: every parameterized failure scenario reaches its intended recovery
assertion, deletion reaches the deliberately blocked upload, and no test
weakens the missing-context guard.

## Test-pipeline proof

```sh
# Verify the dependency/runner mechanics.
bash -n apps/server/scripts/run_local_postgres_tests.sh
cd apps/server && uv lock --check
cd apps/server && PYTHONPATH=src uv run --extra dev pytest --help | rg 'xdist|numprocesses'

# Establish the collection boundary, then execute serial and parallel evidence.
bash apps/server/scripts/run_local_postgres_tests.sh --collect-only -q
GRAF_TEST_WORKERS=1 bash apps/server/scripts/run_local_postgres_tests.sh --durations=20 -q
GRAF_TEST_WORKERS=4 bash apps/server/scripts/run_local_postgres_tests.sh --durations=20 -q
GRAF_TEST_WORKERS=6 bash apps/server/scripts/run_local_postgres_tests.sh --durations=20 -q
GRAF_TEST_WORKERS=8 bash apps/server/scripts/run_local_postgres_tests.sh --durations=20 -q
```

Expected: all modes use PostgreSQL only; full-mode collection/outcome accounting
is identical; strict RLS tests are present; no disposable database remains;
and the fastest stable worker setting is selected from the completed runs.
On the reference run for this feature, the same 1,827-node collection completed
in 943.49 seconds with one worker, 264.47 seconds with four, 206.30 seconds
with six, and 193.78 seconds with eight. Docker exposed 10 CPU on that host, so
eight leaves capacity for PostgreSQL and the system and is the fastest verified
default. These are aggregate timings only, not a performance promise for a
different host.

## Closeout

After focused and benchmark evidence passes, run the canonical repository gate:

```sh
infra/scripts/ci-local.sh
```

Repeat the selected full PostgreSQL run three times. The feature is ready only
when all three are stable, finish within the specification target, and emit
only metadata-safe timing/cleanup evidence.
