# Feature 099 Implementation Evidence

**Feature**: `099-review-m4a-normalization`

**Date**: 2026-07-14

## Focused acceptance gate (T095)

The exact unit, contract and integration surfaces from quickstart sections 2,
4, 6, 7, 8 and 9 were run together against a disposable PostgreSQL 17
database. The set covered normalization state/profile/BMFF/selection/audit,
ingest/finalize/OpenAPI, workflow/idempotency, retry/restart/backfill/priority,
migration/partial uniqueness/locks/force-RLS, deletion/retention/privacy and
cabinet/Range/accessibility projections.

Final result after fixing one stale fail-open test expectation:

- `497 passed`;
- exit code: `0`;
- elapsed time: `146.56s`;
- one pre-existing Starlette/httpx deprecation warning;
- PostgreSQL tests executed rather than skipped;
- disposable PostgreSQL container residue: `0`.

The first aggregate run reported `496 passed, 1 failed`. The failure was a
test that still expected a dispatch maintenance context to receive a silent
empty inventory result. The implemented security boundary correctly rejected
that context before query execution. The expectation now requires
`database maintenance context is not exact`; its real-PostgreSQL rerun passed
`17/17`, and the complete 497-test gate then passed from scratch.

Prerequisite evidence before the run:

- feature directory resolved exactly to
  `specs/099-review-m4a-normalization`;
- Git branch: `codex/099-review-m4a-normalization`;
- implementation base/current uncommitted HEAD:
  `ab818459467d11006e24575242236b5f7872d8e4`;
- `git diff --check`: pass.

## Static, compile and import gate (T096)

The quickstart Ruff surface was expanded with readiness, deployment, compose
and lifecycle tests changed by US6:

```text
PYTHONPATH=src uv run --extra dev ruff check \
  src/twobrain_rec_server/normalization \
  src/twobrain_rec_server/workflows \
  src/twobrain_rec_server/ingest \
  src/twobrain_rec_server/cabinet \
  src/twobrain_rec_server/deletion \
  src/twobrain_rec_server/db \
  src/twobrain_rec_server/admin/metrics.py \
  src/twobrain_rec_server/deployment.py \
  scripts/verify_playback_normalization_runtime.py \
  tests/unit/test_playback_normalization_*.py \
  tests/contract/test_playback_normalization_*.py \
  tests/integration/test_playback_normalization_*.py \
  tests/integration/test_compose_hardening.py \
  tests/integration/test_deployment_readiness_gates.py \
  tests/unit/test_deployment_rollback_decisions.py
```

Result: `All checks passed!`

Additional import/bytecode gates:

```text
python3 -m compileall -q apps/server/src apps/server/tests apps/server/scripts
PYTHONPATH=apps/server/src apps/server/.venv/bin/python -c \
  'import <normalization service, pickup, worker, deployment, readiness matrix>'
```

Both returned exit code `0`. The repository has no separate configured
mypy/pyright gate; the canonical CI type/import boundary is Ruff plus Python
compile/import.

## Ordinary high-risk acceptance gate (T107)

The final authorization/RLS, bounded-subprocess, audit/redaction, deletion and
runtime-isolation neighborhood ran after the last code-affecting fix:

```text
tests/contract/test_playback_normalization_no_secret_egress.py
tests/contract/test_playback_normalization_rls_contract.py
tests/contract/test_retention_deletion_contract.py
tests/unit/test_playback_normalization_audit.py
tests/unit/test_playback_normalization_profile.py
tests/unit/test_playback_normalization_bmff.py
tests/integration/test_playback_normalization_failures.py
tests/integration/test_playback_normalization_deletion.py
tests/integration/test_rls_worker_context.py
tests/integration/test_rls_maintenance_context.py
tests/integration/test_compose_hardening.py
```

Result: `110 passed`, one pre-existing Starlette/httpx deprecation warning,
exit code `0`.

The disposable PostgreSQL 17 role/policy/concurrency rerun passed `19/19`;
the direct destructive-test-database RLS probe returned `pass`, and all
temporary runtime roles were removed. Independent reviewers also reproduced
and closed the API-role spoof, raw-rollback role residue and response-loss
late-object cases.

These are ordinary feature-099 acceptance checks only. They did not open,
resume, mutate, fail or complete feature 097 or Codex Security scan
`97e2db82-ff16-4fda-9167-aa52b9b9cf59`, which remains separately deferred by
the user.

## Canonical local CI gate (T108)

### Post-review tenant-context regression and repair

Independent code review found that PostgreSQL `set_config(..., true)` is
transaction-local while a reused SQLAlchemy session retained only stale
`session.info` after an internal commit. That could remove the restricted media
role's tenant GUCs between finalize and dispatch, claim and run-id persistence,
or prepare and canonical publication.

The central session boundary now replays the already validated tenant context
from `session.info` on every PostgreSQL `after_begin` event. It remains
transaction-local, so no tenant identity can leak through a pooled connection.
Three real-PostgreSQL regressions cover the exact commit boundaries. Results:

- affected non-PostgreSQL dispatch/workflow/RLS neighborhood: `15 passed`;
- the three new restricted-media-role commit-boundary tests: `3 passed`;
- complete native `test_playback_normalization_postgres.py`: `12 passed`;
- focused current cabinet/polling suite after the visible recovery-copy fix:
  `102 passed`;
- disposable PostgreSQL cluster and role residue: `0`.

After the current-master integration documented in `master-sync.md`, the
canonical repository gate ran from the final code-affecting working copy at
uncommitted HEAD `98d57f7431d302b0d2060fb020fc2b320f854753`:

```text
infra/scripts/ci-local.sh
```

The definitive rerun returned exit code `0` and printed
`ci_local_result=pass`. Exact results:

- macOS legacy audio architecture guard: pass;
- macOS Swift release/debug build gate: pass;
- macOS Swift tests: `643 tests`, `0 failures`;
- macOS ContractValidation: pass;
- server pytest: `1713 passed`, `21 skipped`, one pre-existing
  Starlette/httpx deprecation warning, `409.11s`;
- server Ruff: `All checks passed!`;
- Python compile: pass;
- production Compose rendering: pass;
- deployment evidence scan: `pass`, `files=7`;
- `git diff --check`: pass.

The `21` pytest skips are the expected environment-gated PostgreSQL cases in
the ordinary SQLite/full-repository run. They are not an untested RLS claim:
after the master sync, a fresh native disposable PostgreSQL subset passed
`23/23`, the complete normalization PostgreSQL file passed `12/12` after the
last fix, the direct destructive-test-database probe returned
`rls_validation_result=pass`, and temporary cluster residue was zero. The
increase from 18 to 21 skips is exactly the three new real-PostgreSQL
commit-boundary tests.

The local CI RLS boundary intentionally printed
`rls_validation_result=blocked` and `ready_for_production_truth=false` because
no live/destructive PostgreSQL URL is supplied to canonical local CI. That
command exits successfully by design and does not claim production readiness;
the disposable PostgreSQL receipt above owns local policy evidence, while a
future deploy gate must own production truth.

The final candidate/commit SHA remains pending explicit user approval. No
files were staged or committed by this gate.

Feature 097 and its standalone Codex Security scan remain deferred and were not
touched by these ordinary feature checks.
