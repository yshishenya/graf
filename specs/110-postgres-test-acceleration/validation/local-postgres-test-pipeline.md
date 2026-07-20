# Validation: local PostgreSQL test pipeline

## Collection and coverage accounting

- Current full collection: **1,827** node IDs.
- SHA-256 of the sorted node-ID set:
  `0b00a6985badb09a0ebe85bf1046d055ecc35634594ce66d75cf1186a2cc8b46`.
- Parallel phase: 1,796 passed and 1 expected skipped.
- Strict serial RLS phase: 29 passed and 1 expected skipped.
- The runner verifies that the union of the two phases exactly equals the
  same-commit full collection before it emits a full result.

## Performance decision

All measurements use the same PostgreSQL-only collection on the reference
host, where Docker exposes 10 CPU. Timings are wall-clock seconds and contain
no database URLs, credentials or test content.

| Workers | Full gate time | Result |
| --- | ---: | --- |
| 1 | 943.49 s | pass |
| 4 | 264.47 s | pass |
| 6 | 206.30 s | pass |
| 8 | 193.78 s | pass |

Eight workers is the canonical default. It is the fastest measured setting and
leaves two CPU available for PostgreSQL and the local system.

Three additional clean default-eight runs completed in 179.86 s, 197.94 s and
184.98 s. Each had the same collection digest, completed both required phases,
and removed its disposable container.

## Final startup-guard qualification

After those completed full runs, the runner received one narrow lifecycle
hardening change: it waits not only for PostgreSQL readiness but also for a
successful disposable RLS-database creation before declaring the container
usable. The changed path passed its focused regression and full collection
accounting checks. A new full repetition was deliberately not started after
that change because the user explicitly stopped further test cycles. This note
does not represent the earlier three full runs as a rerun of the final exact
working tree.

## Focused and lifecycle evidence

- The known worker-context/failure-recovery/RLS regressions passed through the
  disposable runner.
- The post-cleanup focused regression group passed 34 tests, including the
  PostgreSQL-only contract, runner contract, fixture isolation and render-only
  callers now using the explicit worker fixture.
- A focused slow integration test passed after the bounded container-start
  initialization guard was added.
- A deliberate `INT` rehearsal exited with status 130 and emitted isolated
  container cleanup. It did not touch a shared developer or production
  database.

## Legacy boundary

- Active server Python, shell, TOML and INI paths contain no SQLite/aiosqlite
  runtime support.
- The obsolete `postgres_test_database_url` compatibility fixture was removed;
  its render-only callers now request the explicit current worker database.
