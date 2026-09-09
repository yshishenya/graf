# Quickstart: проверка быстрого и доказуемого CI/CD

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
