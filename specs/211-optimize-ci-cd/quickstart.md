# Quickstart: проверка быстрого и доказуемого CI/CD

## Publication continuation — 2026-09-09

After the local A2 result below, the user approved continuation with commit,
synchronization with current master, push, draft PR and exact-input GitHub
checks. Merge, required-check changes, real Full CI and release remain excluded.
The PR includes the existing A1 and new A2; A1 PR #6846 stays unchanged.
Below, the local-only permission/evidence statements describe the completed
pre-publication stage, not a prohibition on this separately approved step.
Final SHA/run evidence belongs in the PR/status comment, not a self-referential
source commit. No new implementation requirement or review checkbox changed.

## A2 focused acceptance — 2026-09-09

Run from the separate A2 checkout on `6789-pr-metadata-check`, Feature 211. Use the existing pytest/Ruff tools; frozen Spec Kit checks require the existing isolated pinned Specify 1.0.1 environment, not the global 1.0.4. Do not modify global tools or project lock.

```sh
PYTHONDONTWRITEBYTECODE=1 pytest -q tests/governance/test_pr_metadata_event.py tests/governance/test_governance_workflow.py --tb=short
PYTHONDONTWRITEBYTECODE=1 pytest -q tests/governance/test_validator_safety.py -k pr_metadata --tb=short
python3 scripts/validate-pr-metadata.py --self-test
python3 scripts/validate-governance-workflow.py
ruff check scripts/validate-pr-metadata.py tests/governance/test_pr_metadata_event.py
actionlint .github/workflows/pr-metadata.yml .github/workflows/governance-fast.yml
python3 scripts/check-development-process.py
python3 scripts/validate-changelog-fragments.py
python3 scripts/check_spec_kit_governance.py
git diff --check
git diff --exit-code -- .github/workflows/governance-fast.yml .github/workflows/release-full.yml
```

Expected: US6's current text/identity/failure/fork/scope scenarios pass against real disposable Git and local API fixtures; actual new workflow shell fails on an API error without executing product commands. Existing metadata body-file CLI and governance tests pass. New workflow has separate concurrency and read-only permissions; combined gate/release files stay unchanged.

Local gate only: no commits, push/PR, real Full CI, protection settings or release. Live workflows/fork approvals, merge-group metadata, base-retarget/race acceptance, required-check activation and tracker closeout remain pending. Publication will require synchronization with current master without modifying A1 PR #6846; this branch currently depends on its commit. No claim that edited-code reruns are eliminated.

### A2 local evidence — 2026-09-09

- HEAD/base: `5b436a7a771bd2ff14f47df2e0e328678ad1b066` plus uncommitted A2 changes on `6789-pr-metadata-check`; this is not a committed candidate or exact-SHA GitHub approval.
- Test-first evidence: the initial event-mode/old-CLI test failed before the adapter; six workflow/shell cases failed before the new YAML. Follow-up regressions exposed scoped empty-title acceptance, trailing-newline feature misclassification and oversized-number traceback; all corrected in the event adapter without changing `validate()` or old CLI semantics.
- Final pytest 9.1.1: **65 passed** in 10 seconds approximately (44 new event/workflow cases plus 21 existing workflow cases); **7 passed** existing metadata cases. All selected tests ran. Actual new workflow shell used real disposable Git and a local fake API; no product tests, database or network request was made by these tests.
- Evidence covers stale event/current text in both directions; invalid identities/types/JSON/history/checkout; explicit scoped and multi-feature rules; deletion/rename ownership and moving default branch; newline filenames, long numeric values and command-looking text; positive old feature/scoped CLI compatibility.
- Ruff, actionlint, PR metadata self-test, existing workflow validator, changelog fragments, development-process and whitespace: PASS. Frozen Spec Kit governance: PASS using existing isolated Specify 1.0.1; global tools and project lock unchanged.
- Initial development-process check rejected inherited A1 paths missing from the local ownership pointer. The ignored pointer now enumerates the same Feature 211's inherited A1 paths because that validator checks the cumulative branch diff against master; the A1 files themselves are byte-for-byte unchanged from this branch base.
- Independent requirements review: 10/10; clean pre-implementation analyze covered all six new FRs, two SCs and eight US6 scenarios. Local code review found no remaining blocking issue. Simplicity review removed unused test options and needless Git setup for CLI-argument errors; no new dependency, cache or receipt mechanism.
- Canon hooks: PASS after correcting the automatically created branch-reservation issue #6848's task context/area. [#6850](https://github.com/yshishenya/graf/issues/6850) owns T038–T042; 268 open Spec Kit issues checked. Both records remain open, not completed by local evidence.
- `governance-fast.yml`, `release-full.yml`, their validators/receipt/closeout consumers, root AGENTS, installed skills and protection settings were not changed by A2. The concurrency and fork checks here establish local workflow contracts, not live GitHub cancellation/approval behavior.
- Not run: real Full CI, GitHub PR/merge-group execution of A2, application/runtime acceptance, deployment or release. No repository commit, push, PR creation, merge or tag; temporary Git fixture commits are test data only. Old edited-code reruns remain.
- A2 converge: 6 FRs, 2 SCs, 8 US6 scenarios, 6 plan decisions and 7 constitution principles assessed (product-only principles unchanged/not exercised). Findings: missing/partial/contradictory/unrequested 0; CRITICAL/HIGH/MEDIUM/LOW 0. No convergence tasks appended; tasks digest before/after converge remained `80ce1c97a5df7576880cc2997b924a6edb1d91dafc92f3ee39526f20df1e0dea`. Subsequent checkbox updates record local completion only.

Run from the repository root. A1 is local focused validation only: no real Full CI, deploy, release or live branch-protection changes.

## A1 focused acceptance — 2026-09-09

```sh
bash -n infra/scripts/ci-local.sh
python3 scripts/validate-governance-workflow.py --self-test
python3 scripts/validate-governance-workflow.py
PYTHONDONTWRITEBYTECODE=1 pytest -q tests/governance/test_governance_workflow.py tests/governance/test_ci_event_identity.py tests/governance/test_ci_guard.py tests/governance/test_ci_evidence_producer.py
PYTHONDONTWRITEBYTECODE=1 pytest -q --confcutdir=apps/server/tests/contract apps/server/tests/contract/test_ci_cd_contract.py
ruff check apps/server/tests/contract/test_ci_cd_contract.py scripts/validate-governance-workflow.py tests/governance/test_governance_workflow.py
actionlint .github/workflows/governance-fast.yml
python3 scripts/check-development-process.py
python3 scripts/validate-changelog-fragments.py
git diff --check
```

Expected: real-Git selection follows event base despite a different/moving `origin/master`; invalid/unavailable PR/MG base blocks before tests; dispatch stays diagnostic. Existing stubbed fast/full checks prove unchanged lint/compile once before every selected server-test stage and no tests after either static failure. Workflow and documentation contracts pass. A stubbed full is not Full CI evidence.

Local focused checks do not replace the mandatory exact-SHA GitHub `governance-fast` after separately approved publication. Local wide fast is only diagnostic/fallback. A1 leaves edited reruns and current required contexts unchanged; splitting them is a later protected migration. No new timing/token savings are claimed.

Use the existing pytest/Ruff environment. `--confcutdir` excludes unrelated server database setup for this standalone CLI contract file; every test in that file still runs. No database, application build or actual full pipeline is needed for these contracts.

For the separate frozen check, run `python3 scripts/check_spec_kit_governance.py` with Specify `1.0.1` from commit `9118ed15a0ba65053469a94c560ea5d233f75884` on PATH, as pinned by the project/workflow. A different globally installed CLI is not a reason to update the project lock. The verification here used an isolated `.dev/ci-specify-v1.0.1` environment, without changing global tools or generated project skills.

### A1 local evidence — 2026-09-09

- Source checkout HEAD: `3abaaab428256f72e4c5bcd12b247c117c712344` plus the uncommitted A1 changes; this is local evidence, not exact-SHA GitHub approval.
- Before fixes: 11 workflow/base regression cases and 6 server-order/failure cases failed; the documentation regression also failed before its edit.
- Final pytest `9.1.1`: 52 workflow/identity/CI-guard/evidence cases passed; 64 CLI contracts passed. This includes real Git selection across differing/moving bases, missing/invalid/unavailable/unrelated PR/MG bases, diagnostic dispatch and early lint/compile failure.
- Bash syntax, Ruff, actionlint, workflow validator/self-test, changelog fragment, development-process preflight and `git diff --check`: PASS.
- Frozen Spec Kit governance: PASS with isolated pinned Specify `1.0.1`. Initial checks correctly rejected global `1.0.4` and a transient tool installation without a discoverable commit record; neither failure was treated as a pass.
- Independent requirements review: 8/8 in `checklists/ci-feedback.md`; local code review found no blocking issue in A1. Managed PR template, AGENTS, installed skills, lock, release implementation and required-check settings are unchanged.
- Tracking: [#6845](https://github.com/yshishenya/graf/issues/6845) owns T033–T037; canon.ensure and canon.validate passed (266 open Spec Kit issues checked). Issue remains open pending reviewed merge and exact-SHA GitHub fast.
- Not run: real Full CI, GitHub PR workflow, product/runtime acceptance or production/release. No commit/push/tag, no branch-protection change, no claim that edited reruns are eliminated.
- A1 converge: 4 new FRs, 2 success criteria, 5 US5 scenarios and 6 plan decisions checked; no missing/partial/contradictory/unrequested implementation work found. No convergence tasks appended; `tasks.md` unchanged by the convergence pass. This is local implementation convergence, not merged/released acceptance.

## Historical baseline and target (not an A1 measurement)

Pre-change full at SHA `124e96dfff36beadb6d555b3402126ac13bf5a58`:

- total `1406.36s`;
- macOS `769/769`;
- PostgreSQL parallel `3720 passed, 1 skipped`;
- performance `1 passed`;
- strict RLS `52 passed, 1 skipped`.

Three real component-only server fast runs passed in `86s`, `71s` and `70s`.
The p50 `71s` is below the SC-009 ceiling `351.59s`.

Post-fix infrastructure/test-only fast on 2026-08-31 passed in `29s` with
`requested=fast effective=fast components=server,infra,docs`,
`coverage=partial` and `next_gate=full_before_release`. It ran the changed CI
contract (`52 passed`) and bounded infrastructure contracts (`60 passed`),
including deployment-evidence and release-readiness edge cases, without
starting the server unit or full repository suites. The preceding profiling run
proved the same no-escalation invariant but took `207s` because it still
duplicated all `1351` server unit tests; that duplicate was then removed.

## 1. Static contract

```sh
for script in infra/scripts/ci-local.sh infra/scripts/cd-remote.sh apps/server/scripts/run_local_postgres_tests.sh; do
  bash -n "$script"
done
speckit-bootstrap . --doctor --frozen
set +e
infra/scripts/ci-local.sh
status=$?
set -e
test "$status" -eq 2
infra/scripts/ci-local.sh --help
git diff --check "$(git merge-base origin/master HEAD)" HEAD
```

Expected: frozen bootstrap state matches its lock; bare CI performs no stage
and exits `2`; help lists only `--fast` and `--full`; shell syntax and
whitespace pass.

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
documentation consistency and clean → sync → authoritative evidence verification → remote deploy ordering pass.

## 3. Fast lane

Optional local diagnosis/fallback, not a second required pre-PR run:

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

Outside A1. Use only for broad diagnosis; it does not replace authoritative GitHub `release-full`. Deploy verifies that immutable authoritative evidence without a second Full CI.

## 5. CD dry-run

```sh
infra/scripts/cd-remote.sh --dry-run --branch master
```

Expected: `local_ci=full_required` and the complete unchanged remote gate list.

## 6. Production execute

Not authorized in A1. Follow `docs/agent-guidance/release-and-validation.md` for the separately approved candidate/decision/evidence workflow. Clean tree, exact local/remote SHA, authoritative evidence verification and all remote safety gates remain mandatory. Historical commands without candidate/evidence are not current instructions.

## 7. Documentation reconciliation

```sh
cd apps/server
PYTHONPATH=src uv run --extra dev pytest -q \
  tests/contract/test_ci_cd_contract.py -k documentation
cd ../..
```

Expected: documentation tests pass; active guidance agrees on local focused, required GitHub fast and authoritative GitHub full reuse. Historical evidence is unchanged.
