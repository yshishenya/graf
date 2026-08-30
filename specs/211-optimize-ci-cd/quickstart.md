# Quickstart: проверка быстрого и доказуемого CI/CD

Run from the repository root. These scenarios are local-only and do not deploy.

## Pre-change baseline — 2026-08-30

The unchanged runner was measured before implementation with:

```sh
/usr/bin/time -p infra/scripts/ci-local.sh --full
```

Result: PASS at exact base SHA `124e96dfff36beadb6d555b3402126ac13bf5a58` with documentation/spec files only untracked.

- wall time: `1406.36s` (`23m 26.36s`), user `2932.26s`, sys `166.25s`;
- cold macOS build: `63.47s`;
- macOS: `769/769` tests plus `ContractValidation: PASS`;
- server collection: `3775`, digest `66c3cf535952a51884974a2541b76348ffb5ce15657460ee913cad9fef66c7e0`;
- PostgreSQL parallel: `3720 passed, 1 skipped`, phase `1097s`;
- serial performance: `1 passed`, phase `11s`;
- strict RLS suite: `52 passed, 1 skipped`, phase `35s`;
- Ruff, Python compile, Compose rendering and deployment evidence scan: PASS;
- local live-production RLS truth remained correctly `blocked` because no separate production/disposable probe URL was supplied.

Pre-change drift inventory found `115` standalone bare `infra/scripts/ci-local.sh` commands across tracked Markdown. Historical specs/validation/deployment/release receipts are facts and will not be rewritten; enforcement is limited to active operator guidance and templates.

## Implementation validation — 2026-08-30

Focused static/contract evidence:

- Bash 3.2 syntax, Python compile and `git diff --check`: PASS;
- CI/CD contract suites after follow-up review corrections: `52 passed`, 2 dependency
  deprecation warnings;
- bare shared runner: exit `2` before stages; `--help`: exit `0`;
- active operator guidance: `0` ambiguous CI commands;
- CD dry-run: PASS with `valid_full_receipt_or_full_fallback` and unchanged remote gate list.

The first real `infra/scripts/ci-local.sh --fast` attempt correctly escalated to
full and failed closed at Ruff after all product tests passed. Ruff found two
issues in the new contract test (import order and `capture_output`); both were
fixed, focused checks were repeated, and that failed attempt is not counted as
PASS.

The repeated fast request passed with `effective=full` because this slice changes
CI/deploy infrastructure and governance:

- total: `950s` (`15m 50s`; `/usr/bin/time` wall `949.91s`);
- macOS: `769/769`, ContractValidation PASS;
- server collection: `3808`, digest `94b79743f937f9a9f04fde2a62b97041467e7525e66d8bcf3e7052a7bcc04a31`;
- PostgreSQL parallel: `3753 passed, 1 skipped`, `846s`;
- serial performance: `1 passed`, `10s`;
- strict RLS: `52 passed, 1 skipped`, `27s`;
- Ruff, Python compile, Compose, deployment evidence and active docs: PASS;
- live-production RLS truth remained correctly blocked; receipt creation was
  correctly skipped with `reason=dirty_worktree`.

The separate explicit `infra/scripts/ci-local.sh --full` re-check also passed:

- total: `1216s` (`20m 16s`; `/usr/bin/time` wall `1216.03s`);
- macOS: `769/769`, ContractValidation PASS;
- server collection/digest: unchanged at `3808` / `94b79743f937f9a9f04fde2a62b97041467e7525e66d8bcf3e7052a7bcc04a31`;
- PostgreSQL parallel: `3753 passed, 1 skipped`, `1106s`;
- serial performance: `1 passed`, `12s`;
- strict RLS: `52 passed, 1 skipped`, `35s`;
- Ruff, Python compile, Compose, deployment evidence and active docs: PASS;
- live-production RLS truth remained correctly blocked; receipt creation was
  correctly skipped with `reason=dirty_worktree`.

After the final case-sensitive PR-template path correction, the frozen runtime
code received one last explicit full gate. It passed in `693s` (`11m 33s`;
`/usr/bin/time` wall `693.08s`) with the same `3808` collection and digest:
macOS `769/769`, parallel `3753 passed, 1 skipped` (`600s`), performance
`1 passed` (`10s`), strict RLS `52 passed, 1 skipped` (`26s`), and every
post-test gate PASS. No runtime file changed after this run.

PR review then found release-path gaps before merge. The fixes forward the
selected calendar performance gate; require receipt version 2's exact ordered
stage journal and matching clean start snapshot; keep performance
setup/database/functional failures hard while isolating only the p95 threshold;
require that threshold on synchronized-master full; escalate deployment evidence
and high-risk backend/API paths; and propagate tracked-diff failures. The focused
suite now has `52 passed`. Any clean receipt created before these corrections is
invalid for the new commit/schema and must be replaced by a successful full run.

For SC-009, a disposable clean clone of this exact implementation was committed
locally, then given one untracked server-unit probe so the real runner selected
`requested=fast effective=fast components=server`. Three sequential runs passed
in `86s`, `71s` and `70s`; p50 was `71s`, about `94.95%` below the `1406.36s`
baseline and below the required `351.59s` maximum. The disposable probe did not
contact production or modify the feature worktree.

Final CD/documentation reconciliation passed:

- `infra/scripts/cd-remote.sh --dry-run --branch 211-optimize-ci-cd` returned
  `deploy_result=dry_run` and
  `local_ci=valid_full_receipt_or_full_fallback` with the unchanged production
  gate list;
- active operator guidance contained `0` CI commands without `--fast` or
  `--full`;
- the tracked PR template path is the canonical lowercase
  `.github/pull_request_template.md`, and the AGENTS plan marker points to
  Feature 211;
- `origin/master` was six commits ahead at audit time; none changed CI/CD code,
  and its two overlapping changelog lines were preserved locally. The feature
  branch must still be synchronized before any approved commit/PR/release.

## 1. CLI contract

```sh
bash -n infra/scripts/ci-local.sh infra/scripts/cd-remote.sh apps/server/scripts/run_local_postgres_tests.sh
python3 -m py_compile infra/scripts/ci-receipt.py
set +e
infra/scripts/ci-local.sh
status=$?
set -e
test "$status" -eq 2
infra/scripts/ci-local.sh --help
```

Expected: the bare command performs no test stage, exits `2`, and help lists only explicit `--fast`/`--full` lanes.

## 2. Focused contract suite

```sh
cd apps/server
PYTHONPATH=src uv run --extra dev pytest -q tests/contract/test_ci_cd_contract.py
cd ../..
```

Expected: positive/negative component, receipt and deploy contracts pass in disposable repositories; no production network call occurs.

## 3. Documentation consistency

```sh
cd apps/server
PYTHONPATH=src uv run --extra dev pytest -q tests/contract/test_ci_cd_contract.py -k documentation
cd ../..
```

Expected: active instructions contain no ambiguous bare shared-CI command and agree with the CLI contract.

## 4. Fast lane

```sh
infra/scripts/ci-local.sh --fast
```

Expected for this feature: because CI/deploy infrastructure changed, the runner prints a high-risk escalation reason and executes the full effective lane. For a server-source-only change it skips Swift; for a macOS-only change it skips PostgreSQL/server checks.

## 5. Full lane and receipt boundary

```sh
infra/scripts/ci-local.sh --full
```

Expected in the uncommitted implementation worktree: repository gates pass, timings are printed, and receipt creation is skipped with `reason=dirty_worktree`. Contract tests prove receipt creation/reuse in clean disposable repositories.

## 6. CD dry-run

```sh
infra/scripts/cd-remote.sh --dry-run --branch 211-optimize-ci-cd
```

Expected: metadata-only output declares `valid_full_receipt_or_full_fallback` and lists the unchanged production gates. Do not run `--execute` without separate production approval and a synchronized master release candidate.

## 7. Final reconciliation

```sh
git diff --check
git status --short
rg -n 'infra/scripts/ci-local\.sh([`[:space:]]|$)' AGENTS.md README.md CONTRIBUTING.md docs/agent-guidance infra/scripts/README.md .github 2>/dev/null
```

Expected: no whitespace error. Every active match includes an explicit lane or is prose explaining that a bare command is rejected.
