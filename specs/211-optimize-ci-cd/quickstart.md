# Quickstart: проверка быстрого и доказуемого CI/CD

Run from the repository root. Dry-run is local-only; execute deploys production.

## Baseline and target

Pre-change full at SHA `124e96dfff36beadb6d555b3402126ac13bf5a58`:

- total `1406.36s`;
- macOS `769/769`;
- PostgreSQL parallel `3720 passed, 1 skipped`;
- performance `1 passed`;
- strict RLS `52 passed, 1 skipped`.

Three real component-only server fast runs passed in `86s`, `71s` and `70s`.
The p50 `71s` is below the SC-009 ceiling `351.59s`.

Post-fix infrastructure/test-only fast on 2026-08-31 passed in `22s` with
`requested=fast effective=fast components=server,infra,docs`,
`coverage=bounded` and `next_gate=full_before_release`. It ran the changed CI
contract (`36 passed`) and bounded infrastructure contracts (`44 passed`)
without starting the server unit or full repository suites. The preceding
profiling run proved the same no-escalation invariant but took `207s` because it
still duplicated all `1351` server unit tests; that duplicate was then removed.

## 1. Static contract

```sh
bash -n infra/scripts/ci-local.sh infra/scripts/cd-remote.sh apps/server/scripts/run_local_postgres_tests.sh
set +e
infra/scripts/ci-local.sh
status=$?
set -e
test "$status" -eq 2
infra/scripts/ci-local.sh --help
git diff --check
```

Expected: bare CI performs no stage and exits `2`; help lists only `--fast` and
`--full`; shell syntax and whitespace pass.

## 2. Focused contracts and lint

```sh
cd apps/server
PYTHONPATH=src uv run --extra dev pytest -q \
  tests/contract/test_ci_cd_contract.py \
  tests/contract/test_local_postgres_test_runner.py
PYTHONPATH=src uv run --extra dev ruff check \
  tests/contract/test_ci_cd_contract.py \
  tests/contract/test_local_postgres_test_runner.py
cd ../..
```

Expected: explicit lanes, component selection, performance forwarding,
documentation consistency and clean → sync → full → remote deploy ordering pass.

## 3. Fast lane

```sh
infra/scripts/ci-local.sh --fast
```

Expected for every diff, including this infrastructure slice:
`requested=fast effective=fast`. The runner executes bounded checks for the
selected components, prints coverage and `next_gate=full_before_release`, and
does not start the repository full suite. Changed server contract/integration
test files run directly; unrelated components are skipped.

## 4. Diagnostic full

```sh
infra/scripts/ci-local.sh --full
```

Use only for broad diagnosis. It does not replace the authoritative full inside
production execute and is intentionally repeated there.

## 5. CD dry-run

```sh
infra/scripts/cd-remote.sh --dry-run --branch master
```

Expected: `local_ci=full_required` and the complete unchanged remote gate list.

## 6. Production execute

```sh
infra/scripts/cd-remote.sh --execute --branch master
```

Expected order: clean tracked/untracked worktree, branch check, fetch and exact
`origin/master` equality, one `ci-local.sh --full`, post-full clean/local/remote
SHA re-check, then remote deploy lock,
backup/restore, migrations/RLS, secret checks, deployment, readiness, smoke,
public health and rollback guard. Any hard failure stops the sequence.

## 7. Documentation reconciliation

```sh
cd apps/server
PYTHONPATH=src uv run --extra dev pytest -q \
  tests/contract/test_ci_cd_contract.py -k documentation
cd ../..
rg -n "ci-receipt|receipt_reused|valid_full_receipt_or_full_fallback" \
  infra/scripts apps/server/tests/contract docs/agent-guidance \
  .github/pull_request_template.md specs/211-optimize-ci-cd
```

Expected: the documentation test passes. The search may mention why receipt was
removed, but no active executable path or reuse instruction remains.
