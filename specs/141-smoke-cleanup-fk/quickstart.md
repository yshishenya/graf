# Quickstart: Надёжная очистка production smoke-данных

Run all commands from the repository root in a clean `codex/smoke-cleanup-fk`
worktree.

## Focused validation

```sh
PYTHONPATH=src uv run --extra dev pytest apps/server/tests/unit/test_smoke_cleanup.py -q
bash apps/server/scripts/run_local_postgres_tests.sh --focused \
  tests/integration/test_rls_postgres_policies.py \
  -k 'production_smoke_cleanup or production_smoke_setup' -q
git diff --check
```

Expected result: unit ordering/contract checks pass; disposable Postgres smoke
cleanup removes revision-linked rows, returns an empty residue list, and a
second cleanup run removes zero additional rows.

## Repository gate

```sh
infra/scripts/ci-local.sh
```

Expected result: `ci_local_result=pass`.

## Release gate

```sh
infra/scripts/cd-remote.sh --dry-run --branch master
infra/scripts/cd-remote.sh --execute --branch master
```

Expected result: backup and restore rehearsal pass, staged cleanup has no FK
error or residue, health/smoke pass, and the script reports `deploy_result=pass`.
If any gate fails, the script must report a successful rollback before further
action.
