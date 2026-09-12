# CI/CD CLI Contract

## A3 / E01 additions — 2026-09-12

- `infra/scripts/ci-local.sh --plan`: read-only JSON diagnostic selection, no test execution or receipt. Exit 0 means a valid partial plan, including empty/unmatched input. Invalid paths, an invalid explicit base, or missing/empty required test proof exit nonzero.
- `infra/scripts/ci-local.sh --focused`: print the same groups and run their union once from the prepared server venv. Nonempty applicable proof must run and pass; no groups exits 2. Missing Python/Node, pytest collection or assertion failure propagates nonzero. A selected file with no executed cases, a skipped proof or the missing/deselected named rail regression fails after inspecting temporary standard JUnit output. Pytest addopts cannot silently narrow this mandatory set. No dependency installation, Docker, database or app startup.
- The small map and internal `--covered` filtering live in `scripts/ci-behavior-tests.py`; both entrypoints and fast use it. `tests` is the pending set and `covered_tests` is included by the existing fast unit set. Mapped contract files run with behavior-proof validation and are removed from the later changed-file set. Coverage never means a past run can be trusted or skipped.
- Plan fields identify changed paths, groups/reasons, test files, environment, HEAD/base, dirty worktree, diagnostic scope, partial coverage and next mandatory GitHub fast/release-full. Every path is data, never interpolated shell source.
- NUL Git output preserves spaces, Unicode and metacharacters; unsupported control characters fail explicitly. Rename uses both endpoints. An unavailable implicit default base may produce a diagnostic empty partial plan; explicit invalid/unavailable base fails before execution.
- Existing fast adds missing behavior proofs after lint/compile and before broad tests, retaining the previous safety set. Existing full and receipt schemas are unchanged. The result/evidence statements below describe fast/full; plan/focused do not emit their receipt or `ci_local_result`.

## `infra/scripts/ci-local.sh`

```text
ci-local.sh --fast
ci-local.sh --full
ci-local.sh --help
```

- No argument or any unknown argument exits `2` before tests and prints usage.
- `--fast` always prints `effective=fast`, selected components, coverage and the required next gate; it never invokes the full repository suite.
- `--full` executes the broad local diagnostic; authoritative release evidence comes only from GitHub `release-full`.
- Every completed stage emits `ci_stage=<name> status=<status> duration_seconds=<n>`.
- Every exit emits exactly one `ci_local_result=<pass|fail> mode=<effective>
  duration_seconds=<n> next_gate=<gate>`; a passing local full emits `next_gate=full_diagnostic_only`, never release approval.
- PR/MG workflow supplies full `identity.base_sha` as `GRAF_CI_BASE_REF` and rejects a missing/invalid/unavailable event base before tests. The real diff uses its merge base; receipt records that same event base. Manual dispatch retains a null event base and diagnostic default.
- Server lint and Python compile run unchanged, once, before selected server/changed/performance tests in fast/full. Either static failure prevents those tests; selection, performance/RLS and final evidence checks remain unchanged.

Fast classification is bounded and truthful:

- `apps/server/src/**`, dependency metadata and server tests → server fast; changed contract/integration test files are included directly.
- `apps/macos/**` → macOS build/test/contracts on Darwin plus the legacy architecture guard.
- infrastructure and CI/release tooling → bounded syntax, contract and configuration checks.
- deployment evidence → infrastructure checks plus the dedicated
  secret/verdict scanner.
- ordinary documentation/spec text → documentation consistency.
- shared governance documents (`AGENTS.md`, PR template, release/Spec Kit
  guidance) → documentation checks with partial coverage.
- shared/high-risk/unknown path or unavailable implicit diagnostic base → bounded
  component/common safety checks plus
  `coverage=partial next_gate=full_before_release`.
- errors collecting tracked/untracked Git paths fail before selection; partial
  output must never become a successful plan or focused run.
- multiple known components execute their union once.
- calendar performance paths run the focused required performance proof without
  changing the effective lane; the full suite remains a separate release gate.
- if the canonical performance proof was deleted or renamed, fast does not pass
  the missing file to pytest and reports partial coverage for the release gate.
- no path classification or environment override may change an explicit fast
  request into `effective=full`.
- the common whitespace stage covers both the merge-base diff and untracked
  files used by component selection.

## `infra/scripts/cd-remote.sh`

- Dry-run declares `local_ci=full_required` unless the incident bypass is explicitly selected.
- Execute fails closed if the worktree status probe fails, then proves a clean
  worktree, branch equality and exact `origin/<branch>` SHA.
- Execute verifies and reuses immutable authoritative GitHub Full CI evidence, re-checks clean worktree plus unchanged local
  and remote SHA, prints `local_ci=authoritative_full_reused` and `local_ci=full_passed`, and only then starts remote
  production gates. Candidate drift blocks with
  `reason=candidate_changed_during_full`.
- `--skip-local-ci` behavior remains incident-only and does not bypass any remote gate.
- The change does not alter remote backup, restore rehearsal, migration/RLS, secret, health, smoke, cleanup, lock or rollback contracts.

## Documentation consistency

Active operator guidance and templates may not contain `infra/scripts/ci-local.sh` without an explicit supported mode: `--plan`, `--focused`, `--fast` or `--full`. Historical specs, release/deployment receipts and changelog facts are excluded from rewriting.

Ordinary development uses local focused checks; GitHub `governance-fast` on the exact PR SHA is mandatory. Local wide fast is diagnostic/fallback, not a second routine gate. A1 keeps existing events, names, concurrency, permissions and required checks; PR text edits still trigger the current combined workflow.
# A2 additive PR metadata entrypoint

The existing `scripts/validate-pr-metadata.py <body> --feature-id ... --expected-sha ... --title ... [--scoped]` and `--self-test` remain compatible.

New internal invocation: `python3 scripts/validate-pr-metadata.py --event <event.json> --current-pr <current-pr.json>`. Both files are required together and cannot be mixed with body-file options. Git runs from the checkout root. Exit 0 means the fetched open PR snapshot matches event/check-out identity and the existing metadata contract passes; nonzero means invalid inputs, identity/diff or description. No network access occurs inside the validator; the workflow fetches the current PR and fails on API errors without fallback.

The additive workflow runs only PR events. It is not a required gate in A2, does not emit code/release evidence and must not replace governance-fast or qualify merge groups. Required-check activation is a later separately approved migration.
