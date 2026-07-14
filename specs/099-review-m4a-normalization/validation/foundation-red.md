# Foundation Red Phase

**Feature**: `099-review-m4a-normalization`

**Date**: 2026-07-14

## Scope

Tasks T005-T009 define the state-machine, media, migration/RLS, and audit
boundaries before implementation begins.

## Command

Run from `$REPO_ROOT/apps/server`:

```sh
uv run --extra dev pytest -q \
  tests/unit/test_playback_normalization_state.py \
  tests/unit/test_playback_normalization_profile.py \
  tests/unit/test_playback_normalization_bmff.py \
  tests/unit/test_playback_normalization_selection.py \
  tests/unit/test_playback_normalization_audit.py \
  tests/contract/test_playback_normalization_no_secret_egress.py \
  tests/contract/test_playback_normalization_rls_contract.py \
  tests/integration/test_playback_normalization_migrations.py \
  tests/integration/test_playback_normalization_postgres.py \
  tests/contract/test_rls_table_inventory_contract.py \
  tests/contract/test_rls_policy_matrix_contract.py \
  tests/integration/test_rls_postgres_migrations.py
```

## Result

- Exit code: `2`.
- Collection stopped with 6 errors.
- Every error was the intended missing implementation boundary:
  `ModuleNotFoundError: No module named 'twobrain_rec_server.normalization'`.
- No pre-existing implementation accidentally satisfied the new state, media,
  or audit tests.

The tests remain open until the corresponding implementation is present and the
same focused suite passes.
