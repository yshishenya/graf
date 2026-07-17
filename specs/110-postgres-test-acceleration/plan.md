# Implementation Plan: Быстрый и достоверный PostgreSQL test pipeline

**Branch**: `codex/110-postgres-test-acceleration` | **Date**: 2026-07-17 | **Spec**: [spec.md](spec.md)

**Input**: Остановить медленный прогон, исправить PostgreSQL-регрессии и
максимально ускорить полный test flow без возврата к SQLite и без уменьшения
покрытия.

## Summary

Серверный gate остаётся только PostgreSQL. Вместо удаления и повторного
создания схемы перед каждым обычным API/contract-тестом он создаёт безопасные
одноразовые базы на worker, подготавливает схему один раз и перед каждым
`client`-сценарием быстро восстанавливает известный baseline через
ограниченный `TRUNCATE … RESTART IDENTITY CASCADE` и seed. Миграции, RLS,
пустая схема и cluster-global роли остаются в отдельном строгом lane с чистой
базой и advisory-lock, поэтому ускорение не ослабляет реальные PostgreSQL
guarantees.

Одновременно прямые вызовы worker-нормализации в тестах получают тот же
явный `worker` tenant context, который применяет production worker. Защита
`require_database_context` остаётся обязательной и отрицательная проверка
отсутствующего контекста сохраняется.

## Technical Context

**Language/Version**: Python >=3.13, Bash; current local `uv` selects CPython 3.14

**Primary Dependencies**: FastAPI, SQLAlchemy async, asyncpg, Alembic, pytest,
pytest-asyncio; add pytest-xdist only as a development dependency

**Storage**: PostgreSQL 17 in one disposable `postgres:17-alpine` container
per runner invocation; generated loopback-only worker, clean and RLS databases

**Testing**: pytest, pytest-xdist, Alembic/RLS integration tests, shell
contract tests, `infra/scripts/ci-local.sh`

**Risk / Validation Lane**: High-risk feature. It changes a shared PostgreSQL,
Docker and RLS test boundary used by the canonical local quality gate.

**Release Gate**: No deploy. The slice changes local/CI test infrastructure and
does not alter production topology, database data, credentials or rollout.

**Target Platform**: Current macOS development host and Linux-compatible shell
runner; the server and local PostgreSQL service remain Docker based.

**Project Type**: FastAPI server and developer/CI test tooling.

**Performance Goals**: Full warm local gate completes within 10 minutes on the
reference Mac where Docker exposes 10 CPUs; it retains at least the pre-feature reference of
1,822 pytest scenarios and, for every run, proves phase union against the
current same-commit collection before partitioning. It prints the 20 slowest
scenarios/phase timings.

**Constraints**: PostgreSQL-only active path; no production URL/data/secret;
no new skip, deselect or weakened RLS assertion; worker databases must be
independent; global PostgreSQL roles must not collide across worktrees; only
metadata-safe timings may be printed or retained.

**Scale/Scope**: 1,822 currently collected server scenarios, 71 ORM tables,
more than 580 direct `client` scenarios before parametrization, and a small
strict migration/RLS subset requiring clean state.

## Constitution Check

*GATE: Passed before Phase 0 research and re-checked after Phase 1 design.*

**Pre-design — PASS.**

- PostgreSQL, Docker and RLS are explicitly high-risk under Constitution V;
  this feature follows the full Spec Kit lane before code changes.
- The generated database guard remains loopback-only and disposable; no test
  process receives a developer or production target.
- No capture, meeting content, client credentials, retention or deletion
  behaviour changes are in scope.
- The discovered worker-context failures are corrected by making the test
  context truthful, never by bypassing `require_database_context`.

**Post-design — PASS.**

- The fast lane uses a bounded table inventory from `Base.metadata`, quoted
  identifiers and a known seed; it does not issue unbounded schema-wide SQL.
- Migration/RLS/empty-schema tests retain a clean, isolated path. The two
  files that create fixed cluster-global roles run serially under a PostgreSQL
  advisory lock inside the disposable cluster; separate runner containers make
  concurrent local worktrees independent.
- The runner remains the single canonical PostgreSQL entry point and removes
  its generated disposable container on success, failure and interruption.
- Timings and test counts are metadata-only; database URLs, passwords, test
  payloads and private paths are not emitted as evidence.

## Validation Plan

1. Add focused contract/integration tests before implementation for safe
   database names, worker isolation, clean-schema preservation, bounded
   truncate/reset, seed restoration, RLS advisory lock, cleanup on failure and
   exact suite accounting.
2. Reproduce the known normalization failures with the focused two-file
   PostgreSQL invocation; verify direct worker calls apply only the exact
   `worker` context and that the existing negative context guard stays red
   without it.
3. Run ordinary API/contract tests serially first using the fast fixture. Then
   run them with bounded worker database counts and `--dist=loadfile`; compare
   the collected node-id set, outcome count and skip/xfail count with the
   serial baseline.
4. Run the strict migration/RLS lane separately with its advisory lock; prove
   the union of parallel and strict phases equals the original full collection,
   with no permanent ignore, `-k`, deselect or new skip.
5. Capture only `pytest --durations=20`, phase wall times, collection/outcome
   counts and cleanup result. Benchmark one, four, six and eight workers,
   select the fastest stable default, and repeat the selected full gate three
   times.
6. Run `bash -n apps/server/scripts/run_local_postgres_tests.sh`, `uv lock
   --check`, focused pytest suites, Ruff, Python compilation, Compose config,
   the PostgreSQL/RLS hardening boundary and finally
   `infra/scripts/ci-local.sh`.

No deploy runs: the tested surface is local/CI-only and has no production
configuration change.

## Project Structure

### Documentation (this feature)

```text
specs/110-postgres-test-acceleration/
├── plan.md
├── research.md
├── data-model.md
├── contracts/
│   └── local-postgres-test-pipeline.md
├── quickstart.md
└── tasks.md
```

### Source Code (repository root)

```text
apps/server/
├── pyproject.toml                         # development pytest dependencies
├── uv.lock                                # resolved development dependency graph
├── scripts/
│   └── run_local_postgres_tests.sh         # canonical safe full/focused runner
├── src/twobrain_rec_server/
│   └── db/tenant_context.py                # existing guard, not weakened
└── tests/
    ├── conftest.py                         # fast client baseline and app lifetime
    ├── fixtures/
    │   ├── postgres_test_database.py       # worker/clean database lifecycle
    │   └── postgres_rls.py                 # RLS URL guard and advisory lock
    ├── contract/                           # runner and no-regression contracts
    ├── integration/                        # migration/RLS/normalization proof
    └── unit/

infra/
└── scripts/ci-local.sh                     # invokes the canonical runner
```

**Structure Decision**: Extend the existing server-owned runner and fixtures;
the runner owns one ephemeral Docker container per invocation. Do not create a
persistent test Compose stack, a hidden SQLite lane, a production test path or
a competing test framework.

## Complexity Tracking

| Violation | Why Needed | Simpler Alternative Rejected Because |
|-----------|------------|-------------------------------------|
| None | The plan reuses current Docker, PostgreSQL, pytest and fixture surfaces. | A second test stack, SQLite compatibility lane or broad transaction rollback would reduce fidelity or add risk. |
