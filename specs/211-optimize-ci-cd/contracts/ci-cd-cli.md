# CI/CD CLI Contract

## `infra/scripts/ci-local.sh`

```text
ci-local.sh --fast
ci-local.sh --full
ci-local.sh --help
```

- No argument or any unknown argument exits `2` before tests and prints usage.
- `--fast` always prints `effective=fast`, selected components, coverage and the required next gate; it never invokes the full repository suite.
- `--full` executes the canonical repository gate.
- Every completed stage emits `ci_stage=<name> status=<status> duration_seconds=<n>`.
- Every exit emits exactly one `ci_local_result=<pass|fail> mode=<effective>
  duration_seconds=<n> next_gate=<gate>`; full emits `release_ready` only in a
  passing final result.

Fast classification is bounded and truthful:

- `apps/server/src/**`, dependency metadata and server tests → server fast; changed contract/integration test files are included directly.
- `apps/macos/**` → macOS build/test/contracts on Darwin plus the legacy architecture guard.
- infrastructure and CI/release tooling → bounded syntax, contract and configuration checks.
- deployment evidence → infrastructure checks plus the dedicated
  secret/verdict scanner.
- ordinary documentation/spec text → documentation consistency.
- shared/high-risk/unknown path, missing base or diff failure → bounded
  component/common safety checks plus
  `coverage=partial next_gate=full_before_release`.
- multiple known components execute their union once.
- calendar performance paths run the focused required performance proof without
  changing the effective lane; the full suite remains a separate release gate.
- if the canonical performance proof was deleted or renamed, fast does not pass
  the missing file to pytest and reports partial coverage for the release gate.
- no path classification or environment override may change an explicit fast
  request into `effective=full`.

## `infra/scripts/cd-remote.sh`

- Dry-run declares `local_ci=full_required` unless the incident bypass is explicitly selected.
- Execute fails closed if the worktree status probe fails, then proves a clean
  worktree, branch equality and exact `origin/<branch>` SHA.
- Execute runs `ci-local.sh --full`, re-checks clean worktree plus unchanged local
  and remote SHA, prints `local_ci=full_passed`, and only then starts remote
  production gates. Candidate drift blocks with
  `reason=candidate_changed_during_full`.
- `--skip-local-ci` behavior remains incident-only and does not bypass any remote gate.
- The change does not alter remote backup, restore rehearsal, migration/RLS, secret, health, smoke, cleanup, lock or rollback contracts.

## Documentation consistency

Active operator guidance and templates may not contain `infra/scripts/ci-local.sh` without `--fast` or `--full`. Historical specs, release/deployment receipts and changelog facts are excluded from rewriting.
