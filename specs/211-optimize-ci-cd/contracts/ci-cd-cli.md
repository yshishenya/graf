# CI/CD CLI Contract

## `infra/scripts/ci-local.sh`

```text
ci-local.sh --fast
ci-local.sh --full
ci-local.sh --help
```

- No argument or any unknown argument exits `2` before tests and prints usage.
- `--fast` prints requested/effective lane, components and any escalation reason.
- `--full` executes the canonical repository gate.
- Every completed stage emits `ci_stage=<name> status=<status> duration_seconds=<n>`.
- Every exit emits exactly one `ci_local_result=<pass|fail> mode=<effective> duration_seconds=<n>`.
- A clean successful full emits `ci_receipt_result=created`; a dirty successful full emits `ci_receipt_result=skipped reason=dirty_worktree`.

Fast classification is fail closed:

- `apps/server/tests/unit/**` and reviewed calendar/domain source → server fast.
- `apps/macos/**` → macOS build/test/contracts on Darwin plus the legacy architecture guard.
- ordinary documentation/spec text → documentation consistency.
- high-risk backend/API source, deployment evidence, infrastructure,
  dependency/lock, migrations, server contract/integration tests, CI/release
  governance, shared root configuration, unknown path, missing base or any diff
  command failure → full.
- multiple known components execute their union once.

## `infra/scripts/ci-receipt.py`

```text
ci-receipt.py snapshot --output PATH
ci-receipt.py create --started-at-epoch N --collection-count N --collection-digest HEX --evidence-file PATH --start-snapshot PATH
ci-receipt.py validate [--max-age-seconds N]
ci-receipt.py path
```

- `create` is called by the full runner only. It requires a clean worktree and a
  mode-`0600` ordered journal proving every platform-required full stage passed.
  The clean snapshot captured before the first stage must still match, then the
  helper writes version 2 JSON atomically beneath the Git metadata path.
- `validate` exits `0` only for a fresh exact-input match and prints `ci_receipt_result=valid`.
- Invalid validation exits `1` and prints only `ci_receipt_result=invalid reason=<stable_code>`.
- CLI syntax errors exit `2`; invalid receipt data exits `1` with a stable reason.
- Stable invalid reasons include `missing`, `malformed`, `unsupported_version`,
  `not_pass`, `stale`, `dirty_worktree`, `commit_mismatch`, `tree_mismatch`,
  `runner_mismatch`, `dependency_mismatch`, `test_surface_mismatch`,
  `toolchain_mismatch`, `collection_invalid`, `evidence_invalid`, and
  `snapshot_mismatch`.

## `infra/scripts/cd-remote.sh`

- Dry-run declares `local_ci=valid_full_receipt_or_full_fallback` unless the incident bypass is explicitly selected.
- Execute first proves clean worktree, branch equality and exact `origin/<branch>` SHA.
- With a valid receipt: print `local_ci=receipt_reused` and do not execute full CI again.
- With a missing/invalid receipt: print the safe reason, run full CI, require the newly generated receipt to validate, then continue.
- `--skip-local-ci` behavior remains incident-only and does not bypass any remote gate.
- Receipt reuse never changes the remote backup, restore rehearsal, migration/RLS, secret, health, smoke, cleanup, lock or rollback contract.

## Documentation consistency

Active operator guidance and templates may not contain `infra/scripts/ci-local.sh` without `--fast` or `--full`. Historical specs, release/deployment receipts and changelog facts are excluded from rewriting.
