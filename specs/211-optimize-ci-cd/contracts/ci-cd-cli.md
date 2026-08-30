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

Fast classification is fail closed:

- `apps/server/tests/unit/**` and reviewed calendar/domain source → server fast.
- `apps/macos/**` → macOS build/test/contracts on Darwin plus the legacy architecture guard.
- ordinary documentation/spec text → documentation consistency.
- high-risk backend/API source, deployment evidence, infrastructure,
  dependency/lock, migrations, server contract/integration tests, CI/release
  governance, shared root configuration, unknown path, missing base or any diff
  command failure → full.
- multiple known components execute their union once.

## `infra/scripts/cd-remote.sh`

- Dry-run declares `local_ci=full_required` unless the incident bypass is explicitly selected.
- Execute first proves clean worktree, branch equality and exact `origin/<branch>` SHA.
- Execute runs `ci-local.sh --full`, re-checks clean worktree plus unchanged local
  and remote SHA, prints `local_ci=full_passed`, and only then starts remote
  production gates. Candidate drift blocks with
  `reason=candidate_changed_during_full`.
- `--skip-local-ci` behavior remains incident-only and does not bypass any remote gate.
- The change does not alter remote backup, restore rehearsal, migration/RLS, secret, health, smoke, cleanup, lock or rollback contracts.

## Documentation consistency

Active operator guidance and templates may not contain `infra/scripts/ci-local.sh` without `--fast` or `--full`. Historical specs, release/deployment receipts and changelog facts are excluded from rewriting.
