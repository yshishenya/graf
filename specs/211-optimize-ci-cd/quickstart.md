# Quickstart: проверка быстрого и доказуемого CI/CD

## A4 acceptance — 2026-09-13

Lane: high-risk CI/governance. First slice: FR-031–FR-033. Use the prepared server environment for standalone contracts; `--confcutdir` intentionally excludes unrelated application DB fixtures for these CLI-only checks.

```sh
apps/server/.venv/bin/python -m pytest -q --confcutdir=apps/server/tests/contract apps/server/tests/contract/test_ci_cd_contract.py apps/server/tests/contract/test_local_postgres_test_runner.py
python3 scripts/validate-full-ci-workflow.py --self-test
python3 scripts/validate-full-ci-workflow.py
bash -n infra/scripts/ci-local.sh
bash -n infra/scripts/cd-remote.sh
actionlint .github/workflows/release-full.yml
apps/server/.venv/bin/ruff check apps/server/tests/contract/test_ci_cd_contract.py
apps/server/.venv/bin/python -m pytest -q tests/governance/test_ci_guard.py
python3 scripts/check_spec_kit_governance.py
```

The actual extracted workflow shell must stop before every pytest invocation on either static failure, while the successful fixture preserves the remaining sequence. Mixed changes execute each infra-owned CI contract once and retain unrelated changed tests. CD dry-run announces required/reused authoritative evidence. This fixture is not an actual release Full run; exact-SHA hosted checks and the frozen-candidate release gate remain separate.

A4 local evidence: six regression failures on the previous implementation; after the changes, 108 PASS (both CI contracts plus ci_guard) in 13.04 s. Ruff, Bash syntax, actionlint, Full workflow validator and self-test PASS. Independent requirements review 8/8; analyze FR-031–033/SC-016–017 → T048–052: full coverage, no CRITICAL/HIGH/clarification gaps; canon hooks PASS, issue #6982. Code review/converge and exact-SHA PR evidence remain pending. Historical A1–A3 permissions/results below do not describe current authorization or completion.


## A3 / E01 — 2026-09-12

Продолжение после локальной проверки: пользователь поручил довести готовый E01 до PR для включения в релиз. Коммит, публикация PR и необходимые исправления по CI/review разрешены после полученных ниже результатов. На момент начала публикации `origin/master` повторно проверен: `ad71f2ce4db68d846d7c333213961c5f5f7d5e89`. Итоговый SHA и ссылки hosted CI фиксируются в PR и внешнем журнале, чтобы запись результата не меняла проверяемый коммит. Merge, замороженный релизный Full и выпуск остаются следующими отдельными состояниями. Записи о невыданном разрешении ниже — история предыдущего локального этапа.

Первый hosted запуск [34709631762](https://github.com/yshishenya/graf/actions/runs/34709631762) в [PR #6953](https://github.com/yshishenya/graf/pull/6953) выявил ошибку изоляции T045: синтетический `run_stubbed_ci` наследовал `GRAF_CI_BASE_REF` реального PR, поэтому тест отсутствующей неявной базы получал ожидаемый отказ для явной базы. Это воспроизведено локально с `GRAF_CI_BASE_REF=origin/master` до исправления. Теперь только тестовый helper задаёт пустую базу по умолчанию, сохраняя явные overrides конкретных тестов; существующий тест также моделирует загрязнённое окружение через `monkeypatch`. Рабочий runner и строгая проверка PR-базы не менялись. Весь CI-контракт с заданной внешней базой: **78 PASS, 14,35 с**; Ruff, process и whitespace PASS. Неуспешный первый run не является подтверждением готовности; окончательный результат следующего SHA записывается в PR.

Active lane: high-risk CI/governance, local focused acceptance. A1/A2 are merged through #6851 and #6845/#6850 closed; older entries below are preserved as historical snapshots. Current base: `ad71f2ce4db68d846d7c333213961c5f5f7d5e89`.

Запуск [34709948521](https://github.com/yshishenya/graf/actions/runs/34709948521) подтвердил предыдущую поправку: 78 CI-контрактов и 420 governance-проверок прошли (один прежний условный governance skip). Позднее этап `CI contracts` обнаружил старую строку help в соседнем `test_local_postgres_test_runner.py`. Его существующее утверждение согласовано с четырьмя явными режимами; новая runtime-логика не добавлялась. Область T045 и команда ниже теперь явно включают оба файла: **86 PASS, 13,84 с** с внешней базой, Ruff/process/whitespace PASS. Ошибки совместимости найдены в независимых этапах CI, а окончательная готовность определяется только последним успешным run PR.

From the implementation checkout, on `codex/211-behavior-test-selection`:

```sh
# Inspect the exact chosen paths/groups; no environment startup or network.
infra/scripts/ci-local.sh --plan
# Run only related cabinet/settings proofs from an already prepared server venv.
infra/scripts/ci-local.sh --focused
```

For a different known local base, set the existing `GRAF_CI_BASE_REF` explicitly. No diff means no relevant focused tests; do not substitute a passing test result. To prepare a new checkout once, run `uv sync --frozen --extra dev` from `apps/server`; Node must already be available. The plan/helper never installs dependencies. GitHub fast uses this same group map while retaining broad unit and changed-file tests; full remains a separate release gate.

Acceptance before commit:

```sh
bash -n infra/scripts/ci-local.sh
(cd apps/server && GRAF_CI_BASE_REF=origin/master PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=src .venv/bin/python -m pytest -q -o addopts= tests/contract/test_ci_cd_contract.py tests/contract/test_local_postgres_test_runner.py)
PYTHONDONTWRITEBYTECODE=1 apps/server/.venv/bin/python -m pytest -q tests/governance/test_governance_workflow.py tests/governance/test_ci_event_identity.py tests/governance/test_ci_guard.py
apps/server/.venv/bin/ruff check scripts/ci-behavior-tests.py apps/server/tests/contract/test_ci_cd_contract.py tests/governance/test_governance_workflow.py
python3 scripts/validate-governance-workflow.py
python3 scripts/check-development-process.py
git diff --check
```

Also run the real chosen groups in the prepared environment and the unchanged rail regression against historical bad JS in an isolated temporary copy; record expected FAIL and current PASS with durations. Do not replace workspace source, launch GRAF Dev, run Full, or claim GitHub/merged/released acceptance from this local result.

Environment preflight: shared Specify 1.0.6 conflicts with pinned 1.0.1. An ignored isolated installation of commit `9118ed15a0ba65053469a94c560ea5d233f75884` passes frozen bootstrap doctor; tracked generated tooling is unchanged. Use `PATH="$PWD/.dev/speckit-bin:$PATH"` for the frozen doctor and `scripts/check_spec_kit_governance.py` in this checkout. Server dependencies were prepared once with the existing lock, Python 3.14.6 and pytest 9.1.1.

### A3: результат локального внедрения — 2026-09-12

Основание: `ad71f2ce4db68d846d7c333213961c5f5f7d5e89` плюс незакоммиченные изменения A3. Рабочее дерево: `/Users/yshishenya/.codex/worktrees/ci-e01-20260912/crisp`; исходные 46 изменений дерева аудита не переносились. Это проверка местных файлов, не результат GitHub на опубликованном SHA.

| Проверка | Результат | Граница доказательства |
|---|---|---|
| `test_ci_cd_contract.py`, окончательный прогон | **78 PASS, 11,72 с** | Выбор, порядок, сохранение прежних этапов, ошибки Git/базы/пути, обязательное выполнение, отсутствие побочных действий |
| `test_governance_workflow.py`, `test_ci_event_identity.py`, `test_ci_guard.py` | **46 PASS, 4,28 с** | Реальный локальный Git и shell существующего workflow для PR/MG/manual; это не запуск на GitHub |
| `GRAF_CI_BASE_REF=HEAD^ infra/scripts/ci-local.sh --focused` | **112 PASS, 0 skip; pytest 2,77 с, исполнитель 8,81 с** | Три существующих файла, включая неизменённую проверку меню; без Docker/БД/приложения |
| Первый полный замер той же focused-команды | **13,25 с** от запуска до выхода | Подготовленное окружение; установка зависимостей, очередь и Full сюда не входят |
| Исторический ошибочный JS `4fbddd00de10f89fa5644d581f32b6b4d19a7bbd` | Ожидаемый **FAIL, 0,2105 с** | `wrong initial class for embedded 1120`; временная копия JS, неизменённый существующий тест |
| Текущий JS `ad71f2ce4db68d846d7c333213961c5f5f7d5e89` | **PASS, 0,2523 с** | Тот же `test_cabinet_rail_node_harness_keeps_responsive_defaults_and_manual_state` |
| Ruff, `/bin/bash -n`, workflow validator, активные команды документации | **PASS** | Новые Python-файлы и договор существующего runner |
| Frozen bootstrap doctor, Spec Kit governance, development-process, whitespace | **PASS** | Закреплённые инструменты, владение путями и changelog; generated tooling не обновлялся |

Первый тест выбора упал на старом runner: изменение `cabinet.js` не добавляло `related behavior tests`. После внедрения он проходит. При независимом review также воспроизведён R2: ошибка `git ls-files` после успешного `diff` позволяла продолжить с неполным списком. Четыре проверки публичных `--plan`/`--focused` сначала упали; исправление в общей функции отделяет ошибку сбора путей (код 2) от отсутствующей неявной базы (код 1). Повторное независимое review: **PASS**, без незакрытых замечаний; [запись проверяющего](checklists/behavior-selection.md) содержит границы и хеши кода.

Проверены пропуск и исключение обязательного теста из выполнения, отсутствие/пустота файла, ошибка pytest, влияние `PYTEST_ADDOPTS`, добавление/удаление/rename, Unicode/пробелы/кавычки/символы shell, отказ на управляющих символах, неполное покрытие неизвестной области, грязное дерево и неверная точная база. В fast связанные contract-файлы выполняются с проверкой JUnit один раз; файл unit уже покрывается прежним широким набором. Требования: независимое review 9/9, предварительный analyze без CRITICAL/HIGH. Два предупреждения существующего окружения pytest/Starlette не приводили к пропускам.

Канонический владелец T043–T047 — [issue #6952](https://github.com/yshishenya/graf/issues/6952). Поиск дублей и обязательные issue-canon ensure/validate выполнены до кода; validator проверил 300 issues. Issue остаётся открытым до слияния и необходимого внешнего подтверждения.

Converge A3: **converged**, без добавления задач; 6 FR, 2 SC, 6 сценариев US7, 7 решений плана и 7 принципов конституции сверены. Продуктовые области не менялись и повторно не испытывались. Findings всех типов/степеней — 0; `tasks.md` во время converge сохранил SHA-256 `28c43803f424210ae454ac26d3bf61a8fb6709cfc92696744ab941e5f459c003`. Отметки локального выполнения внесены отдельно после этой сверки.

Следующие отдельные состояния: согласование implementation commit после проверки → публикация PR → обязательный `governance-fast` на точном SHA → review/merge. Full на замороженном релизном кандидате, production и публикация выполняются по релизному договору при соответствующем выпуске. В A3 не выполнены commit/push/PR/merge, hosted CI, Full, deploy или установка GRAF. Скорость Full и релиза этим этапом ещё не измерялась; E02 и дальнейшая оптимизация из общего плана остаются впереди.

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


## A5 acceptance — 2026-09-13

Environment for both fixture measurements: CPython 3.13.3, same frozen uv.lock, evaluation/dev extras, one pytest worker, same isolated PostgreSQL 17. Baseline: 27 PASS in 125.71 seconds pytest / 135 seconds runner phase. Compare only the same two test families after the fixture change.

```sh
UV_FROZEN=1 PYTHONDONTWRITEBYTECODE=1 bash apps/server/scripts/run_local_postgres_tests.sh --focused -q -p no:cacheprovider --durations=5 tests/integration/test_artifact_egress_policy.py tests/integration/test_speaker_names.py
# Inventory must not start Docker; pure + resource IDs must be disjoint and cover unit.
bash apps/server/scripts/run_local_postgres_tests.sh --focused --collect-only -q tests/unit
(cd apps/server && PYTHONPATH=src .venv/bin/python -m pytest -q -m 'not postgres and not browser' tests/unit)
# Prepare browser environment once (CI does this explicitly).
npm ci --prefix apps/server/tests/browser
apps/server/tests/browser/node_modules/.bin/playwright install chromium
GRAF_NODE_MODULES="$PWD/apps/server/tests/browser/node_modules" bash apps/server/scripts/run_local_postgres_tests.sh --fast -q
PYTHONPATH=apps/server apps/server/.venv/bin/python -m pytest -q --confcutdir=apps/server/tests/contract apps/server/tests/contract/test_local_postgres_test_runner.py tests/governance/test_test_resources.py
```

Expected: help/invalid/collect/pure succeed or reject invalid arguments without Docker calls; resource tests without safe DB fail, missing Playwright fails rather than skips. Metadata reports have no error/output/property/SQL fields and each setup/call/teardown appears once. Before/after fixtures retain all 27 cases and security assertions. Full keeps ordinary/performance/strict phases and checks nonempty disjoint union. Hosted timing and release acceptance remain separate from this local benchmark.

A5 T053 executable no-Docker matrix (temporary PATH stub records calls): `--help` → exit 0; `--focused --a5-invalid-option` → nonzero argument error; `--fast --full` → nonzero conflicting modes; `--focused --collect-only -q tests/unit` → collection exit 0. Every case asserts an empty Docker-call log, not merely a successful command. The resource hook contract additionally executes a pure case through a transitive fake fixture and proves it cannot trigger a PostgreSQL fixture. Hosted report artifact name: `graf-test-timings-<requested_sha>-<run_id>-<run_attempt>`; its `<phase>.jsonl` files bind timing rows to the existing authoritative run without publishing payloads.


A5 local results (2026-09-13): requirements review PASS 5/5 after explicit browser, safe report identity and no-Docker matrix clarifications. Analyze FR-034–037/SC-018 → T053–057: full coverage, no unresolved CRITICAL/HIGH/clarification gaps; issue #6983 and canon hooks PASS. Six new executable regressions failed before implementation and passed afterward. Combined CI/resource/workflow contracts: 121 PASS, 22.58 s. Fast unit: 1497 pure PASS (26.24 s pytest / 30 s phase), 100 resource PASS (37.46 s / 41 s), no skips. Safe reports contain exactly 4491 + 300 events (setup/call/teardown once per case). Two previously skipped contract/integration Chromium scenarios: 2 PASS, 18.01 s; unit Chromium scenario passed in the 100 resource cases. Both fixture families retain 27 PASS: 125.71 → 66.95 s pytest, 135 → 73 s phase, same Python 3.13.3/lock/single worker. This one local before/after observation is not a hosted Full benchmark. Ruff, actionlint and process checks PASS; frozen Spec Kit verification uses the checkout-pinned CLI, not global 1.0.6. Final review/converge/PR/Full remain subsequent gates.


## A6 acceptance

```sh
apps/server/.venv/bin/python -m pytest -q tests/governance/test_pr_scope.py tests/governance/test_pr_metadata_event.py tests/governance/test_governance_workflow.py tests/governance/test_ci_event_identity.py tests/governance/test_merge_group_mapping.py tests/governance/test_validator_safety.py tests/governance/test_release_train.py
python3 scripts/validate-governance-workflow.py --self-test
actionlint .github/workflows/governance-fast.yml .github/workflows/pr-metadata.yml .github/workflows/macos-pr.yml
```

Before code: negative scope/snapshot/checkout cases; preserve legacy metadata CLI. After foundation merge: record its real SHA, verify fresh target/macOS checks, add all three required contexts and read back strict/app IDs before removing the old gate. In the cutover PR, demonstrate that editing only text does not start/cancel expensive code jobs or replace failed/running code checks. Retarget must still run code at the new base. Final body, source SHA and all checks must agree before merge. Closeout/freeze validate current metadata and final head/merge provenance; archived combined PRs use the explicit foundation boundary. No real merge-group acceptance is claimed while GitHub does not offer it to this personal repo.

A6 negative consumer matrix includes: fresh metadata + stale code base; missing native base; different head/base between any pair; expired/mixed-attempt artifacts; old checked base that is only an ancestor of the actual merge base; merge tree differing from final PR head; invalid/nonlinear rebase shape. Historical-policy cases: foundation PR and merge before activation use combined policy; PR open at activation, old branch updated after activation, and any merge at/after activation require all three. Missing/ambiguous activation record rejects exemption. A merged PR body refresh runs only the trusted metadata validator against the exact historical merge base; an unmerged closed PR fails. Artifact names bind SHA/run/attempt, retention 90 days.


### A6 foundation — local implementation evidence, 2026-09-13

- Analyze A6: FR-038–041 / SC-019 → T058–T063, 100% coverage; no unmapped tasks, duplication, ambiguity or constitution 7.0.0 conflicts. Independent requirements checklist PASS 6/6. Issue-canon validation PASS, existing owner #6986; no activation SHA invented.
- Scope/native regression: 9 FAIL before implementation → 9 PASS. Exact Git rename/delete/base selection, strict title/body shape and actual terminal shell reject missing/failed/cancelled native execution. Job-level native concurrency is entered only after a real code/base scope, so a title/body edit cannot cancel retarget execution either.
- Metadata regression: 13 FAIL before implementation → PASS. Actual workflow shells check fork identity, isolated policy execution despite a replaced PR validator/sitecustomize, both API errors, changed body and malicious strings. Old local CLI remains compatible.
- Full governance collection: 504 PASS / 16 platform skips; two newly added merge cases initially failed because the unmerged-close assertion was misplaced in the test. That test placement was corrected; all 19 trusted/merged cases PASS in 4.51 s. No product behavior changed to satisfy this test correction.
- Final complete metadata/scope suite: 75 PASS / 12.30 s, including all corrected merge cases.
- Final runner/CI contracts: 98 PASS / 19.02 s. Frozen Spec Kit governance, Bash syntax, Ruff, actionlint, Full validator/self-test, governance workflow validator and whitespace PASS.
- A4/A5 and foundation T058/T059 implementation review/convergence finds no new missing implementation tasks. T052 hosted proof and T060–T063 activation/cutover/consumers remain open: source publication, exact-SHA hosted results and live protection are not inferred from local PASS.
- Current remote master advanced by #6985 (release report and example environment only); foundation is rebased before publication. The next code check is bound to that updated base.

A6 independent implementation review found and resolved two concrete cases: ignore open-PR background synthetic merge SHA changes while preserving real merged-history checks; restrict documentation scope to known directories/names, so the existing `outcomes/meeting_minutes.md` product resource still requires native checks. Both cases now have executable regression coverage.


A6 hosted native convergence: run 34757372590 correctly failed on the unchanged short-recording boundary fixture (five assertions in one of six cases; 971 tests). The fixture feeds five seconds of audio every arbitrary 200 ms, so progress depends on runner scheduling despite the real timeline's bounded 20-second buffer. T067 replaces that timing assumption with test-source drain acknowledgment; runtime limits and all boundary assertions remain unchanged. Controlled burst and final paced execution are recorded separately. This is fixture synchronization inside FR-038 acceptance, not a change to the product's 30-second rule.

T067 local evidence: the controlled no-pacing burst reproduced `source_overflow` and failed the boundary test (0.629 s); this diagnoses the fixture mechanism without claiming that the earlier hosted log reported that code. With per-source acknowledgment, `swift test --package-path apps/macos --filter LocalRecordingWriterSystemAudioTests` passed all 11 tests in 14.768 s on local Swift 6.3.3. Overflow, unbounded-source, interruption and WAV/frame checks remain active. Hosted Swift 6.0.3 on the new exact SHA remains required.

Independent T067 implementation review: PASS; actual writer queue confirms append/observe before the next empty read, source lock protects acknowledgment, no coverage or Swift 6.0.3 API blockers found.

### T056 release regression — 2026-09-13

Release Full 34767647027 exposed a missing early plugin load in xdist workers when the real runner passes `--graf-report-file` without explicit test paths. The shared phase now preloads the existing resource plugin with `-p`; all tests, failure handling and metadata fields remain unchanged. A real subprocess regression calls the runner's own phase function with pytest default collection and two workers: before the fix no tests ran and exit was 5; after the fix all three resource-report tests passed (1.75 s), including failure payload redaction and one report per phase. This is a correction of T056 / FR-037 in the active F211 slice. The failed release candidate is not reused; a new exact-SHA candidate and authoritative Full are required after merge.

Hosted follow-up: governance-fast 34768234779 attempt 2 and macos-pr 34768140020 passed on 315c6f5b9dcc8db85ea4ba4775422605e584be3d; pr-metadata 34768234968 passed. GitHub retained separate failed checks from the original malformed SHA line (trailing punctuation), so this evidence commit requests a fresh complete check set with corrected metadata. Local runner contracts: 12 PASS; pinned Spec Kit governance, Bash and Ruff: PASS. No product or runner changes were added after those results.

T056 production-command follow-up: Full 34769117142 exposed that `uv run pytest` does not initially include the server root in `sys.path`, unlike the `python -m pytest` used by the first regression. The runner now exports one explicit server-root/src PYTHONPATH and no longer replaces it during PostgreSQL startup. The regression calls the actual runner and console entrypoint with two workers: it fails before the fix with `No module named 'tests'`, then all three resource tests pass (12.65 s). Frozen Spec Kit governance, Bash and Ruff pass. Product code, dependencies and release gates are unchanged; Full on a new merged SHA is required.
Real PostgreSQL + two-worker autosave contract with phase reporting also passed: 1 test / 10.61 s, three metadata rows, isolated container removed. This exercises the same post-database PYTHONPATH as Full, in addition to the pure path.

## A7 acceptance

Use `GRAF_TEST_REPORT_DIR=<new-empty-directory> bash apps/server/scripts/run_local_postgres_tests.sh --focused -q -n 4 --dist=loadfile` with these tests relative to apps/server: integration/test_recording_share_public_link.py, test_cabinet_meeting_rename.py, test_local_purge_coordination.py, test_transcript_export_egress.py, test_cabinet_playback_route.py, test_meeting_comments.py, test_meeting_comments_api_review.py, test_meeting_comments_boundaries.py, test_meeting_comments_browser.py, test_meeting_comments_read_review.py, test_cabinet_hx_delete_feedback.py, test_meeting_share_links.py, test_meeting_access_policy.py; plus unit/test_meeting_access_decisions.py. Each name after the first retains its integration/ prefix.

Before/after must have the same collected IDs and final outcomes, no skips, same frozen Python/worker environment. Compare the controller timing case hashes and separate setup/call/teardown; no raw output artifact. Check full_seed=True in the two comment exceptions and full seed calls in four direct exception functions, then inspect assertions unchanged. Ruff and existing full candidate remain mandatory at their usual boundary.

A7 analyze: FR-042 / SC-020 → T064–T066, full coverage, no conflicts or missing requirements; independent checklist PASS 3/3. Baseline: 144 PASS / 178.82 s pytest, 182 s phase, collection digest `4f0c8275aa6e32cf887cec499fb4dcd0edc4dec2217a4bfa3ee14b0edf0d185b`, xdist4/loadfile. Owner #6988.


## A8 acceptance

Build runtime and media-runtime locally through the documented helper/Dockerfile with a full synthetic source SHA. For both: inspect IDs/source labels/platform, run pip check and record installed runtime/evaluation versions and packaged migration/template/prompt resources. Only media may run ffmpeg. Test two distinct rebuilds: a new SHA with identical source bytes, and a real source-only edit with a verified changed application output. Both must retain dependency and FFmpeg cache; the real source edit must rebuild the application while preserving distributions/resources.

Run focused image lifecycle tests plus existing cd/rollback/smoke contracts. Required failures: bad SHA/platform/ID; missing previous image; changed external ref pull failure before stop; dirty/missing evidence; incomplete attempt; wrong .Image after recreate; failed rollback/public-download recovery; disk-full or atomic-write error for baseline/helper/overrides before stop; final-result write failure retaining the blocking attempt with no deploy_result=pass. Required successful paths: same-SHA cached retry; schema downgrade and compatibility use candidate IDs; permitted rollback uses previous IDs with zero build/pull; smoke/cleanup consumes candidate override. Actual release still requires one final GitHub Full and cd-remote.sh --dry-run.

A7 final local acceptance, 2026-09-13: the same 144 cases PASS before and after, no skips, identical collection digest `4f0c8275aa6e32cf887cec499fb4dcd0edc4dec2217a4bfa3ee14b0edf0d185b` and all 432 (case_id,file,when,outcome) rows match. Pytest 178.82 → 113.03 s; phase 182 → 117 s. Independent AST review confirms unchanged behavior assertions in all 89 direct replacements, all 26 comments callers, and the six preserved exceptions. Ruff/diff PASS. T064–T066 local converge has no remaining implementation gaps; PR/hosted/merge and final Full are separate.

A8 clean analyze, 2026-09-13: reviewer-owned image-reuse checklist PASS 5/5 after clarifying persistence failures and verified recovery. FR044→T068, FR045/046/047→T069, FR048→T070, SC021 and all negative scenarios→T071. Each task owns named existing files or the single stdlib helper and focused test file. No unresolved clarification, unmapped requirement, contradiction with constitution 7.0.0 or hidden registry dependency. The historical build decision and CLI contract explicitly defer to A8. Production and public artifact proof remains pending.

A4/A5/A6 foundation publication: PR #6987 merged 2026-09-13T13:05:57Z as `a3f5f72e994e7872ee175ebafd9f7699a2d4ffca`; checked source `ab2da6cd081b3b5f8acf876a1b1431109211fc59`. Exact-source governance-fast run 34758484113 PASS and macos-pr run 34758484107 PASS including pinned Swift 6.0.3. T052/T067 are complete. T060 protection activation still waits for separate metadata on the next PR; no activation time is inferred from foundation merge. A8 owner #6989.

T072 discovered by A7 hosted macos-pr run 34758978378: `testProbeTimesOutAndIgnoresLateOrDuplicateCompletion` expected timeout false, but two assertions saw true. The 10 ms utility-queue timer races with a 40 ms callback on a different global queue; nominal deadlines do not guarantee completion order under load. Replace that fixture ordering with an AsyncStream that retains the real callback until the actual probe has timed out, then invoke late/duplicate callbacks. Production probe and timeout remain unchanged. T072 is FR038 convergence, not a new permission behavior.

T060 activation evidence: `.github/pr-check-policy.json` records the real foundation merge and 2026-09-13T13:18:40Z read-back. Required checks are governance-fast, pr-metadata, macos-pr, each app_id 15368; strict=true, linear=true, required approvals=0 remain unchanged. PR #6990 demonstrated trusted pr-metadata PASS (34758978356) and a real failing native check (34758978378), which now blocks merge until T072 passes. Foundation native had passed on ab2da6cd. No failing native gate was bypassed.

T072 local `swift test --package-path apps/macos --filter SystemAudioPermissionUXTests`: 8 PASS and the existing opt-in preview render skip; timing case PASS in 0.011 s. No app installation or preview rendering was performed. Final hosted SHA remains pending.


### A6 local consumer convergence — 2026-09-13

- Реальное read-back GitHub protection: `strict=true`; `governance-fast`, `pr-metadata`, `macos-pr`, все `app_id=15368`. Активация `2026-09-13T13:18:40Z`, foundation #6987 / `a3f5f72e994e7872ee175ebafd9f7699a2d4ffca`; запись `.github/pr-check-policy.json`.
- Общий validator подключён к closeout и candidate/train freeze/current/decision/attestation. Проверяет актуальный run attempt по `run_started_at`, общее head/base, native execution и свежий текст. Squash с обновляющим master merge в исходной ветке проверяется по настоящему родителю и итоговому дереву.
- Диапазон релиза выводится из опубликованного stable product release на строгой цепочке предков source. Уже опубликованный текущий source пропускается как база: последующая аттестация сохраняет проверки всех вошедших PR. Каждый commit принадлежит единственному merged PR; linear rebase покрывается целиком, набор train сверяется точно. Некорректная политика, отсутствующий предшествующий release/PR, неоднозначность и stale/failed proof блокируют действие.
- `apps/server/.venv/bin/python -m pytest -q tests/governance/test_pr_checks.py tests/governance/test_pr_metadata_event.py tests/governance/test_release_candidate.py tests/governance/test_release_train.py tests/governance/test_governance_workflow.py tests/governance/test_pr_scope.py tests/governance/test_validator_safety.py`: **226 PASS / 49.43 s**, `/tmp/graf-a6-all-focused.log`.
- Actionlint трёх workflows, governance validator/self-test, Bash syntax, frozen Spec Kit doctor: PASS. Ruff fixture re-export исправлен без изменения test logic.
- T072 focused Swift: **8 PASS, 1 прежний opt-in skip**, `/tmp/graf-native-permission-green.log`. Истинный timeout настоящего probe предшествует намеренно поздним/повторным completion; рабочие permissions/timers не менялись.
- Локальное сопоставление FR-038–041/SC-019: scope, trust boundary, activation, историческая политика, consumers и негативные сценарии покрыты. Hosted green на новом source и наблюдение body-only edit ещё обязательны для T061/T063/T072. A8 и последующее ускорение упаковки остаются открытыми этапами программы.

- Независимый implementation review A6/T072: **PASS**, новых P1/P2 нет; проверены строгая база предыдущего release, annotated tags, покрытие squash/rebase, все consumers и настоящая последовательность timeout/late callbacks. Результат не заменяет hosted проверки. Ponytail-review: существующие metadata/receipt helpers и stdlib переиспользованы; лишних зависимостей/сервисов нет.

### A6 live text-event acceptance — 2026-09-13

На `59c7072590feaf5c9b1d163c8f17c3742254e07e` Swift6.0.3 native run34760638453 PASS. Правка только body в13:47:25 UTC создала metadata34760821522 PASS и текстовые scope runs34760821336/34760821301; исходный code34760638452 продолжал работу без отмены, Swift повторно skipped. GitHub оставляет dynamic name пропущенного code job невычисленным выражением. Для надёжного consumer добавлен только маленький code-scope artifact текстового события; его run/attempt/head/base/text identity обязателен перед пропуском такой записи. Code receipt из текста не создаётся. Регрессии новых условий и workflow contract:73PASS/10.14с; будущая hosted проверка обновлённого source остаётся обязательной.

A6 documentation contract продолжения: старая проверка единственного «обязательный authoritative PR» обновлена на явное присутствие всех трёх обязательных имён. Поведение тестов не изменено. Связанный CI/CD contract до изменения этой строки имел единственное несовпадение документации; исправленный сценарий PASS.

### A6 expected-check correction: требования T080–T081 — 2026-09-13

Статус: независимый requirements review PASS 4/4; clean analyze PASS, FR-040/SC-019 покрыты T080–T081 без critical/high замечаний. Реализация и live acceptance ещё не завершены. Предыдущая live проверка доказала отсутствие повторов/отмены кода, но не завершила приёмку слияния.

Основной агент проверил авторизованный merge box #6990 на head `c82b1f5db28f60b664b6cc7efbf50f92e31614eb` и base `a3f5f72e994e7872ee175ebafd9f7699a2d4ffca`: после body edit GitHub показывает `governance-fast expected` / `macos-pr expected`, хотя прежние source checks успешны и общий validator их принимает. Новый набор того же workflow скрывает прежний required result. Это основание уточнения FR-040, а не основание менять branch protection или повторять продуктовые тесты.

Приёмка T080–T081:

- Сначала исполняемые tests с подставными API/командами: success + body, failed/cancelled/running + старый success, running→success/failure/timeout, ошибки API, later attempt старого run ID, смена head/base/ref/state/attempt при проверке, wrong PR/repository/workflow/event и missing/expired/mixed artifacts.
- Только проверенный text scope разрешает исключение из source search; неверный self-run ID/похожее имя/неизвестный scope не скрывают реальный code run. Два текстовых итога не ждут друг друга. Текстовый PASS не становится исходным proof; полный consumer требует и source proof, и последний соответствующий gate run/attempt включая text с ровно одним successful fixed-name job и точной identity. Rollup/последний success не подходят. Отдельный сценарий запускает same-SHA повтор source/gate во время проверки другого компонента: финальная сверка всех selected source/gate attempts блокирует прежний набор при неизменных PR snapshots.
- Фактические workflow shell guards доказывают ноль установок ресурсов, вызовов `ci-local --fast`, Swift и новых source receipts на text-only. Обычные code/native/terminal guards и required+skipped ошибки сохраняются. Text concurrency не отменяет code/native; partial rerun не смешивает попытки.
- Targeted governance suite, актуальный governance workflow validator и actionlint; никакого локального Full или изменения правил защиты.
- После commit/push основным агентом: body-only edit во время source execution сохраняет исходный run и ждёт его настоящего результата; на успешном исходе permanent required checks проходят. Проверить сам блок слияния GitHub, отсутствие `expected` и неизменные required names/app IDs/strict rules. Если PR ещё открыт, body edit после завершения source снова запускает только scope/API. Ссылки на runs, source/head/base/attempt и результаты записываются после фактической проверки.

Hosted готовность не выводится только из локального PASS или API status rollup. T061/T063/T081 остаются открытыми до соответствующей текущей приёмки. A8/A9/A10 и ранее записанные результаты других этапов этим исправлением не пересматриваются.

### A6 expected-check correction: локальная реализация T080–T081 — 2026-09-13

- Отрицательная проверка T080 до реализации: **30 FAIL, 6 PASS, 82 deselected / 3,20 с**, `/tmp/graf-a6-reuse-red.log`. В том числе прежний общий consumer принимал исходный proof при отсутствии последнего required `macos-pr`; новые компонентные сценарии ещё не имели реализации, а фактическая native text-ветка не вызывала verifier. Это отдельные причины FAIL, а не 30 воспроизведений одного GitHub дефекта.
- Постоянные required names сохранены в существующих jobs. Governance text-путь выполняет только scope guard, exact checkout/identity и проверку исходного proof; установки, `ci-local.sh --fast`, terminal/source receipts и их upload имеют явный code-only guard. Native text-result проверяет исходный native proof на Ubuntu; существующий Swift job не менялся. Неизвестный или failed scope не входит в concurrency кода и завершает required check ошибкой.
- Компонентная проверка принимает только настоящий text event и scope текущего run/attempt, сверяет текущий PR/head/base/ref/state/repository и exact diff. Последний source выбирается по времени исполнения и run ID без поиска последнего успеха. Bounded wait проверяет настоящий outcome; failure/cancel/timeout/API failure не заменяется старым PASS. Подтверждённые text scopes исключаются до ожидания результата, поэтому два таких запуска не ждут друг друга и не образуют цепочку новых proofs. Summary содержит только исходный run/attempt/head/base и ссылку.
- Полный consumer дополнительно требует последний gate run/attempt каждого компонента, включая text, с ровно одним successful fixed-name job. Перед PASS он повторно проверяет все source/gate attempts и текущий PR. Исполняемый отрицательный сценарий меняет source, text gate или metadata attempt при второй загрузке metadata — после первоначального выбора остальных компонентов и при неизменном SHA/PR snapshot; финальная сверка отклоняет прежний набор.
- Итоговый целевой набор: **273 PASS / 47,34 с**, `/tmp/graf-a6-reuse-consumers.log`: `tests/governance/test_pr_checks.py`, `test_pr_metadata_event.py`, `test_release_candidate.py`, `test_release_train.py`, `test_governance_workflow.py`, `test_pr_scope.py`, `test_validator_safety.py`. API подменяется на границе провайдера; выбор source/gate, проверки доказательств и настоящий Git выполняются. Фактические shell двух workflow передают ошибку proof verifier; governance text-цепочка не создаёт `.dev/ci-evidence`.
- Actionlint обеих workflow, `validate-governance-workflow.py --self-test`, Ruff изменённых Python файлов и `git diff --check`: **PASS**. Два самостоятельных контракта активной документации: **2 PASS** через `pytest --confcutdir=apps/server/tests/contract ... -k active_documentation`, без загрузки продуктового server conftest. Использован существующий Python 3.13 venv с pytest 9.1.1; новый environment не создавался.
- Сопоставление FR-040/SC-019 → T080/T081: условия постоянных names, неизменного source, отказа при ошибках, отсутствия взаимного ожидания, gate/source revalidation и сохранения historical/post-merge policy покрыты. T080 завершён. Локальная реализация T081 подготовлена к независимому implementation review; T081, T061 и T063 остаются открытыми до review, commit/push и настоящей exact-SHA/body-edit приёмки основным агентом. Issue #6986 остаётся открытым. Full CI, сборки продукта, изменения GitHub и production на этом этапе не выполнялись.

### A6 review corrections — 2026-09-13

GitHub review comments 4000081305/4000081311 reproduced: initial executable
Git/ZIP regressions had 5 FAIL, 10 PASS. Minimal fix reuses checked_base for
scope and code snapshots, retains real merge identity and supports merged
text. New uploads use run/attempt names; invalid exact artifacts cannot use
legacy fallback. Requirements reviewer PASS6/6; FR-040/SC-019→T087 and its
Issue #6986 map without critical/high requirements gaps.

Targeted consumers: 293 PASS /52.56 s; additional two-commit linear-rebase and
same-tree/base merge-identity race cases: 14 PASS /5.16 s. Actual source scope
and artifact reader run against real disposable Git and synthetic API/ZIP;
no product suite repeated. actionlint, workflow validator/self-test, Ruff and
diff checks PASS. These are local results; independent delta review, final
SHA checks and post-merge edited acceptance remain open in T087.

Rebased on master90e15a026 (PR #6991). Git followed the consumed F211 fragment
rename automatically; restored the already assembled v2026.09.13.3 fragment
and wrote only subsequent cutover changes to changes/unreleased/F211.yaml.
The earlier body-edit acceptance on97f2348 stays historical evidence: source
runs34766571261/34766571290 attempt1 passed once; edits during source
34766625384/34766625382 and after34767489191/34767489142 passed without
cancelling/repeating source. Actual merge box no longer showed expected
required contexts; its then-current blocker was the newly changed master.

Independent delta review found an additional fresh-checkout ordering P2:
code_snapshot needed Git objects before the existing fetch loop. The one-line
move after fetch is covered by a real local bare-remote regression: 1 FAIL/
1 PASS before, missing head fetch succeeds after and fetch failure stays closed.
Final narrow corrections suite: 24 PASS /6.19 s, Ruff/diff PASS.

Independent final A6 delta review PASS: both original P1 and fetch-order P2
resolved, no open P1/P2. Local scope complete; T087 keeps hosted/post-merge
acceptance open.

### A8 local implementation acceptance — 2026-09-13

- Runtime/media builds preserve all 68 installed distributions (`pip check` PASS) and 1099 application/package resource files. Both old/new content manifests have SHA-256 `1278d910beb56156ad3be65940c92fda1148861438b22a45ed045b1eefde663d`. FFmpeg exists only in media-runtime. Local Docker platform is linux/arm64; these are not production timing measurements.
- New SHA with identical source bytes: runtime 0.83 s, media 0.31 s. Actual source edit: runtime 7.18 s, media 0.53 s, changed application bytes observed; dependency and FFmpeg layers remain CACHED. Both targets use the same frozen dependency/application prefix, with source metadata after expensive layers.
- The existing deploy lock owns a create-once attempt in Git-private `graf-release-images`. Previous actual container IDs and one-off IDs are captured before builds/pulls; same-SHA/platform reuse validates image ID, source label and environment. Candidate/previous overrides pin all services; runtime, downgrade/compatibility, actual rollback and standalone smoke/migration/backup/restore rehearsal use the appropriate saved IDs. A running prompt worker is upgraded and restored symmetrically.
- New helper regression checks and related executable rollback/smoke/backup/RLS contracts: 114 PASS / 3.33 s. Final prompt-worker extension: both previous-safe-processing cases PASS / 0.21 s. Run with the prepared Python 3.13 venv first in PATH so subprocess entrypoints use the same dependencies:

```sh
PATH="$PWD/apps/server/.venv/bin:$PATH" PYTHONPATH=apps/server/src apps/server/.venv/bin/python -m pytest --noconftest -q   tests/governance/test_release_images.py   apps/server/tests/integration/test_production_smoke_boundary.py   apps/server/tests/integration/test_deployment_readiness_gates.py   apps/server/tests/integration/test_deployment_backup_restore_rehearsal.py   apps/server/tests/contract/test_rls_production_boundary.py
```

- Independent implementation review: PASS after all five findings were fixed: signal-safe finalization before trap removal/cleanup, prompt-worker rollback, saved IDs for standalone callers, cache publication after final clean-source check, and preservation of pending active.json when directory fsync fails. Regression coverage includes source drift and failed replacement of an existing active pointer.
- No new service, registry, credentials or dependency. No change to PostgreSQL/RLS/migration/backup/restore/public health/Full requirements. Hosted exact-SHA evidence, final Full and release dry-run remain separate gates; local tests do not prove production deployment.

A8 final related validation after review fixes and documentation: 229 PASS / 39.65 s (image lifecycle, Compose hardening, smoke/readiness, backup/restore, RLS boundary and CI/CD contracts). Ruff, shell syntax, development-process, changelog fragments and diff check PASS.

A6 final hosted proof on `c82b1f5db28f60b664b6cc7efbf50f92e31614eb`: governance-fast 34761402527 PASS (996 s bounded lane), Swift/macOS 34761402545 PASS, metadata 34761675889 PASS. The body-only edit at 14:05:51 UTC produced only text scope/metadata and did not cancel/repeat code/native. Live common validator accepted all three exact head/base/run/attempt proofs and the text-scope artifact. Required protection read-back stayed strict with all three contexts bound to app 15368. The reviewed REST metadata-head concern was disproved by the actual filtered API response. GitHub merge eligibility remains a separate live check.


## A9 acceptance plan

Run focused executable `tests/governance/test_release_artifacts.py` with prepared
Python and `apps/macos/Installer/Scripts/test-release-signing-custody.sh` on macOS.
Use synthetic command responses, no real Keychain signing/submission/publication.
Run native InstallerPackagingTests for the actual wrapper contracts.

Required cases: cache-key independence from full SHA/source-only edits and change
on toolchain/SDK/lock; build still invoked on hit; whole-input and whole-output
fingerprints including file mode/symlink changes; exact-stage repeat with stable
ZIP/appcast/checksum/attestation bytes; damaged cache/missing result; expired proof
and explicit public trust flag; all-assets preflight, mismatch-before-first-upload,
missing-only upload, ambiguous upload readback; known notary ID resume, no-ID
ambiguity, Rejected/invalid/network failure, disk-full/failed fsync, concurrent lock.
Real public acceptance later records exact source, both notary request IDs,
Accepted, stapler/Gatekeeper/Sparkle and downloaded final file hashes. No local
fixture result substitutes for that evidence.

A9 requirements gate: independent review PASS 6/6, coverage FR-049–054/SC-022 = 7/7; analyze CRITICAL 0, HIGH 0. Task ownership T073–T077: #6992; mandatory issue canon ensure/validate PASS. No constitution amendment.

### A9 local implementation checks — 2026-09-13

- `tests/governance/test_release_artifacts.py`: final 22 PASS /20.46 s. Real prepare shell with isolated synthetic commands verifies byte-identical same-version resume, one archive/sign, fresh Keychain, verify-only refusal and public/signature failures. Final notary lifecycle verifies original/stapled copies, failed directory fsync and unchanged recovery; source/API/digest gates have negative cases.
- Existing `test-release-signing-custody.sh`: PASS, including asserted intended failure reasons after the GitHub API cache change. Negative simulations now own a disposable checkout and cannot delete a real `.build/updates` staging directory. Optional app-fixture staging cases remain explicitly skipped without a provided fixture; the new Python test covers the actual prepare wrapper independently.
- Independent correctness/Ponytail review found one P2: after a parent-directory fsync failure, retry could acknowledge a visible rename without retrying its durability. Actual prepare regression reproduced FAIL before the fix. Retry now syncs the parent under the existing lock; repeated failure and recovery preserve all bytes, with exactly one archive/sign. Independent follow-up review: PASS, no open P1/P2.
- Ruff and shell syntax PASS. No Apple submission, real signing, app installation or public upload performed. Final hosted SHA checks and frozen-source Full remain pending T077.

### A10 local implementation acceptance — 2026-09-13

- Contract runner/resource modules: 55 PASS /60.15 s; Ruff/Bash/diff PASS. A real `uv run pytest` console-entrypoint collection regression found the early plugin import failure missed by the earlier shim. Scoped collection-only PYTHONPATH fixes it; independent final review PASS.
- Exact selected 131-case pair (10 historical integration files; the CI contract file is correctly owned by the other stage): serial 342.418 s → partitioned 194.739 s, saving 147.679 s /43.128%. Both 131 PASS, 0 skip/duplicates, 393 passed setup/call/teardown records, identical node/phase sets and source fingerprints. Both cleaned the isolated PostgreSQL container.
- Both used GRAF_TEST_WORKERS=4 and GRAF_PERFORMANCE_GATE=required. Digest `ba7e7c86cb853750e405dcbe1be0c32fac3902c54f274fc6ef58d7fad5e7ccf6`; artifacts `.dev/a10-pair-131-fixed-pfnvqw3l/{comparison,serial,partitioned}.json`. Independent review recalculated all JSONL counts and matched current source hashes.
- The 18-case sample was 72.505 →73.405 s and did not improve. No general speed guarantee is inferred for tiny selections. The 131-case pair is one local sample, not hosted p50/p95 or proof about total release time; hosted validation remains separate.

### A11 acceptance

Source unittest исполняет настоящий ensure main с подставными repo/label вызовами:
нет template → установлен; проект меняет checks → два ensure оставляют байты
неизменными; managed issue canon остаётся обновляемым. В GRAF повторить тот же
сценарий в tmp checkout и проверить three-check template, source version/commit,
`check_spec_kit_governance.py` с frozen Specify. Ни live labels, ни API нужны для
регрессионного теста. Source release/checks и pinned update записать после факта.

A11 clean analyze: FR-056/SC-024 → T082/T083; source/publication/pin and no-API negative checks covered. Reviewer project-template PASS3/3. Unmapped requirements, critical/high findings and constitution contradictions:0. Ownership #6986; implementation starts after this gate.

### A11 source release and pinned installation — 2026-09-13

- Source PR https://github.com/yshishenya/spec-kit-ext-github-issue-canon/pull/12 merged into `894d2f2ccf1cf56cd9753e0a1c7d3d9c53aac281`. Source 22 unittest PASS /0.569 s, independent correctness/Ponytail PASS; CI run34766689288 and CodeQL run34766688090 PASS. Annotated v0.3.4 published by Release run34766795441.
- GRAF installed the published deterministic ZIP through the existing bootstrap0.9.9 catalog installer and lock writer. The bootstrap was read from its released tag, without touching the dirty source checkout. Only the issue-canon dependency changed: the other extension/workflow/Specify/skill lock entries compare equal. The published package omits source-repository tests/workflows/catalog by design; runtime scripts and command skills remain installed.
- Published/locked archive SHA-256 `513294ff7ec810b1d868753e689f767d1e516b5f7084c4a6bf67885aaf8567b5`. Project PR template remained byte-identical: `ab6f31af921c025d599133133032706a6c74e201d4a42ca2db0439957372a5ab`.
- Consumer ensure regression reproduced FAIL against the old version, then 52 validator-safety tests PASS /0.78 s with two real isolated ensure calls. Child Python uses -B to avoid bytecode changing the installed tree. Frozen doctor and `check_spec_kit_governance.py` PASS; no GitHub API/labels in the regression.

### A12 requirements and analyze — 2026-09-13

Independent requirements review PASS4/4 in `checklists/test-quality.md`. Root
cross-artifact analyze: FR-057→T084, FR-058→T085, SC-025→T084–T086/T077;
unmapped requirements, CRITICAL/HIGH findings, unresolved clarification and
constitution contradictions:0. Full-only order is distinct from FR-055's
unchanged focused order. Duplicate removal is scoped to exactly 1 config,
1 cookie-name integration and 3 forbidden-readiness contract cases; the matching
unit tests retain independent literal expectations. Delta requirements review
PASS confirms the same inputs and assertions, with all other cases preserved;
new regression cases are counted separately. Existing issue ownership is assigned
before implementation; actual tests/review/final Full are separate evidence.

### A12 local checks and review delta

- Exact duplicate collection: config70→69; cookie/readiness four-file
  collection102→98, each0.34 s. AST-equal1+1+3 duplicates removed, independent
  unit literals retained.
- Real HTTP/DB CSRF plus retained config/cookie/readiness unit cases:94 PASS
  /38.40 s; isolated container cleanup PASS.
- Full order contract reproduced3 FAIL before change then3 PASS/7.50 s.
  Final CI/runner/resource consumers144 PASS/106.90 s. Ruff/Bash/diff PASS.
- Independent review exposed that slicing token/handler could execute code
  inside a block comment. The test now executes whole cabinet.js under Node vm
  with a minimal empty-page DOM. Actual source1 PASS/0.14 s; both word-only
  and real-handler block-comment negative controls FAIL. No JS parser/browser
  dependency was added, product JS was not changed.
- Real strict/performance69-case collection:68 PASS/1SKIP/26.67 s. The skip
  is a global-role isolation defect in the existing bootstrap proof, recorded
  as T088; this is not claimed as complete acceptance. A separate disposable
  cluster only for that proof is required before final acceptance.

T088 requirements PASS5/5 (CHK005). Cross-artifact analyze maps FR-057/SC-025
to T088, issue6994; no critical/high requirements gaps or constitution
contradictions. Extra cluster is limited to actual execution of the existing
bootstrap proof. Collection, production roles and other fixtures stay intact.

### T088 local acceptance — 2026-09-13

Ten executable fixture contracts PASS /3.61 s, including actual collect-only
without Docker. Entire media→bootstrap file:14 PASS/0 SKIP,11.40 s pytest,
20.191 s wall. Original strict/performance collection:69 PASS/0 SKIP,31.20 s
pytest,41.609 s wall, required performance gate. All69 case IDs match the
baseline; only bootstrap call changed skipped→passed, the other68 cases and
all setup/teardown outcomes match.207 passed report rows,0 duplicates;
collection digest `07274a0c1cbb91b84ad75f6f912bf47519b9365898abc9cf6692bf62f9ab03bc`.
Evidence `.dev/a12-bootstrap-glw9o_78/{file,strict-performance,parity}.json`.
No stopped/running owned containers remain. Independent review PASS confirms
current file hashes, preserved assertions and bounded finally cleanup without
repeating expensive tests. T088 local implementation complete; Full is separate.

A11 pinned installation independent review PASS: all14 installed files and
executable modes equal the published v0.3.4 ZIP; manifest/archive hash and
registry/lock agree, other lock entries unchanged. Real repeated ensure keeps
project template bytes/three checks. No bootstrap source edit was needed.

T089 requirements gate: independent CHK006 PASS; complete checklist6/6.
Root analyze maps required media coverage FR-057/SC-025 to T089 and issue6994,
50 existing synthetic cases plus separate negative contracts. Missing/broken
tools, installation failure, unchanged non-server preparation and private
TestRec opt-in are explicit. CRITICAL0/HIGH0, no unresolved clarification or
constitution conflict. Issue body synchronized before code.

Combined-source checkpoint: A8–A12 rebased onto current A6 plus master
6ca6c6abd5fbb38bb210c74868850f2a5fc03768. After #6991's cabinet.js changes
and #6995's report fix, whole-script CSRF execution plus all three real report
contracts:4 PASS/1.87 s. Only these integration checks repeated; completed
benchmarks and release-image/notary suites were not repeated.

### T089 local media acceptance — 2026-09-13

Actual missing-tool/workflow checks reproduced19 FAIL/2 PASS before the fix.
After the three skip→fail changes and conditional resource preparation,
21 PASS/1.68 s; explicit update/install failure cases were then separated.
Only a supplied authorized TestRec directory reaches tool checks; its absent
opt-in remains a skip before filesystem/media access. Working tools avoid apt,
non-server PR paths avoid resource preparation. No new runtime dependency.

Existing synthetic matrix49 + dual-source1:50 PASS/0 SKIP,5.77 s pytest,
10 s phase.150 passed setup/call/teardown rows,0 duplicates; digest
`471e0b13dadee467b91a18c986402c958b672346a04071e9e938a05d8acd2d1f`.
Evidence `.dev/a12-media-t089/focused.jsonl`, local FFmpeg/ffprobe8.1.2.
Owned PostgreSQL container cleaned. Runtime-image capability and hosted
Ubuntu FFmpeg execution remain distinct checks.

Master correction #6996 (`b48999dbb2c8fe258f636b263b154377c0fd8fa5`)
is included. All runner paths now use the same absolute server-root/src
PYTHONPATH; redundant partition-only root injection was removed. Three
report regressions PASS/11.44 s, including actual uv console execution,
two workers and a real one-case PostgreSQL run with the phase report.
The source product tests were not rerun wholesale after this integration.

Final combined workflow/runner/media contracts:106 PASS/69.48 s, including
separate apt update/install failures. Ruff, actionlint, both workflow validators,
Bash, fragment validation and diff checks PASS. FFmpeg version probing uses
-nostdin so the server-path loop cannot lose its input. Final independent
T089 implementation review, hosted and release acceptance remain separate.
Apple notary profile read-only preflight succeeded; no submission or
publication was performed by this preflight.

### T089 независимый review и T090 исторические инструменты — 2026-09-13

T089 independent implementation review PASS на `91fc8039ef428c32a32c36c5a6904f37f2e7b543`: все три настоящих media entrypoints и оба ресурсных YAML шага соответствуют требованиям. Сохранённые 50 PASS/0 SKIP и 106 contracts PASS проверены независимым рецензентом без повторного выполнения. T089 завершена локально; Ubuntu/Full остаются T077.

T090 FR-040/SC-019: независимый разбор требований PASS, clean analyze без critical/high, задача и #6986 уточнены до реализации. В обеих scope jobs штатный sparse checkout `.ci-tools` закреплён на `github.workflow_sha`; основной checkout сохраняет точный PR head. В terminal jobs этот checkout доступен только text-only. Identity/reuse helpers читают соседние инструменты из `.ci-tools`, а Git — основной checkout. Общий release PR validator получает `cwd=root`.

Проверка: 7 FAIL до исправления; первоначальные 76 PASS/21,23 с; окончательные 265 consumer cases PASS/56,66 с. Последний набор включает реальные Git-истории старого merged head без новых helpers, текущий sparse checkout, YAML shell execution, импорты verifier/policy, отказ при подмене primary HEAD и абсолютный вызов freeze из чужой папки. Actionlint, workflow validator, Bash syntax и diff checks PASS. Независимый implementation review T090 PASS. Повторных source receipts или продуктовых наборов текстовый путь не создаёт.

T087 остаётся открытой: после merge нужна настоящая правка описания #6990 и старого merged #6991, успешные постоянные required contexts и общий validator с исходными code proofs. Локальный PASS не заменяет эту приёмку.

Следующий обнаруженный остаток T091: hosted macos-pr source 34770443873 корректно отказал на двух проверках (972 cases,1 opt-in skip,2 failures). InstallerLifecycleEvidenceTests искал прежний прямой upload в shell, хотя проверенный A9 перенёс его в существующий helper. ShortRecordingNoticeTests сравнил результат после собственного sleep6,2 с, не учитывая планирование отдельной MainActor-задачи с production6 с. Исправление ограничено этими двумя тестами; поведение продукта не меняется.

T091 local validation:22 Swift tests PASS/9,164 с, включая все21 InstallerLifecycleEvidenceTests и ShortRecordingNoticeTests. Устаревшее ожидание заменено точным вызовом upload helper вместе с release-inputs.json; runtime upload и запрет clobber уже покрыты исполняемыми A9-тестами. Проверка уведомления использует существующий ContinuousClock и ограниченное10-секундное ожидание реального panel=nil, сохраняя все прежние assertions и дополнительное подтверждение третьего показа. Product-код,6 секунд и30-секундный порог не менялись. Независимый implementation review перед закрытием T091 обязателен.

### Фактические пропуски Full34769888625 до A12

Неуспешный Full предыдущего v2026.09.13.3 на master b48999dbb2c8fe258f636b263b154377c0fd8fa5 оставил артефакт graf-test-timings-b48999dbb2c8fe258f636b263b154377c0fd8fa5-34769888625-1. Его parallel.jsonl подтверждает37 skipped case IDs:28 media_matrix,4 finalize,1 workflow,3 reuse и1 private TestRec. Первые36 сходятся к существующим media-tool helpers, которые T089 уже делает обязательными; private TestRec opt-in сохранён. В этом прогоне4321 call PASS,22 call FAIL,2 setup FAIL; strict/performance не начались из-за старого порядка Full. Его37 пропусков нельзя объявлять полным сопоставлением с41 историческим пропуском другого выпуска. Требуется окончательный Full с T088/T089 и правильной pytest-конфигурацией; новый результат учитывается по фактическим фазам.

Независимый заключительный review: T083/A11 PASS (14 файлов опубликованного v0.3.4 равны installed, digest ZIP=lock, остальные записи lock и проектный template неизменны); T086/A12 PASS по текущим исходникам,5 дублям, порядку Full и сохранённым69/50 случаям. T091 implementation review PASS: цельная upload-команда содержит правильные inputs; ожидание уведомления не блокирует MainActor, XCTAssertNil выполняется до defer cleanup. Все три локальные задачи завершены. Действительные GitHub/release gates остаются открытыми.

T092 clarification18:39 UTC: независимый запуск Ubuntu24/FFmpeg6.1.1 опроверг первое предположение о единственной проблеме offset. Реальное повреждение кадра даёт stderr-ошибки, но -xerror возвращает0; локальный8.1.2 возвращает183. Требуется подтверждённый общий повреждённый образец и строгая проверка его условия до recovery, без изменения прежних ожиданий. Предварительное описание причины в issue уточняется; production-дефект пока не объявлен.


### T092: подтверждённый повреждённый MP3 — 2026-09-13

Старое повреждение10700:10704 и повреждения среднего реального кадра дали
strict return183 на FFmpeg8.1.2, но0 на Ubuntu24/FFmpeg6.1.1 при настоящих
decoder errors. Общий образец теперь повреждает32 байта после четырёхбайтового
заголовка первого аудиопакета, найденного настоящим ffprobe. На6.1.1 strict
return69, на8.1.2 return183; tolerant return0. Оба прежних caller используют
один helper; проверены длина, границы файла и sync bits. Production-код и все
прежние recovery/output/subprocess-budget assertions сохранены.

Целевые три pytest-случая на локальном8.1.2:3 PASS/1,35 с. Независимый реальный
опыт Ubuntu24/6.1.1 выполнил оба неизменных production-метода derive_single_source
и derive_candidate: recovered_source=True, full_decode_passed=True,
single_source_transcode. Это проверка конкретного pipeline, не всего hosted CI.
Те же три pytest-случая с реальными ffmpeg/ffprobe5.1.9 из закреплённого
production-образа:3 PASS/3,96 с. Временный контейнер без сети удалён. Первоначальные
три отказы этого опыта были ошибкой временной обвязки: безопасное окружение
медиапроцесса удаляет переменные и пользовательский PATH. Обвязка получила
абсолютный Docker CLI, явный endpoint и container ID; runtime protection не менялась.

Независимый implementation review T092 PASS; Ruff/diff checks PASS. Локальная
задача завершена. Фактические Ubuntu required checks и итоговый Full остаются
T077; результаты старого failed run34770443870 не переименованы в успех.


T093 исходный случай `--focused --partitioned -q -- <path>` воспроизведён
существующей real-pytest/xdist fixture: exit4,0 cases, `file or directory not
found: --graf-phase-file`. Новая регрессия сначала1 FAIL/1,84 с, после переноса
служебных phase/worker options перед selectors1 PASS/2,96 с. Все5 synthetic
cases выполнены ровно один раз;2 обычных — workers, остальные3 — последовательно,
cleanup подтверждён. Bash/Ruff/fragments/diff PASS. T093 остаётся открытой до
включения окончательного #6997, проверки общего config/report entrypoint и
независимой приёмки объединённого runner. Benchmark131 не повторялся.


T093 интеграция проверенной CI-части #6997 выполнена отдельно, пока его владелец
дорабатывает поведение тарифа. Источник импорта f73c670564899d91582377403d223a26fa0669dc:
единый run_phase, явный project config до selectors, collection config и два
реальных report/async regressions. Продуктовые файлы соседнего PR не перенесены.
A10 передаёт phase/worker options до пользовательского --; Full по-прежнему
strict → performance → parallel, focused сохраняет свой порядок.

Существующий isolated runner fixture перенаправляет только путь стандартного
project config в свою pytest.ini; настоящий project config проверяется отдельными
реальными uv/pytest workers. Существующий combined env/config selector усилен:
-m selected исключает other, а -k 'not test_performance' отдельно исключает
performance. Старое -k 'not other' дублировало действие -m и не доказывало
сохранение config. Уточнение имени необходимо, потому что -k учитывает маркеры.

Полный двухфайловый consumer запуск:60 PASS,1 FAIL/84,51 с; единственный отказ —
слишком широкое тестовое слово performance, которое дополнительно исключало
случай с обоими маркерами. После уточнения проверены исправленный selector и
четыре настоящих варианта async/config/report (обычный/partitioned × -k/--):
5 PASS/45,16 с. Два новых partitioned варианта дополняют ранее проверенные,
в каждой фазе ровно3 успешных metadata rows для одного случая. Итого покрыты
63 уникальных случая окончательной коллекции; это состав двух ограниченных
запусков, а не один63-case прогон. Bash/Ruff/diff PASS. Повторный131-case benchmark
не требуется. Независимый implementation review T093 PASS: все7 callers, порядок config/report/options, isolated config mapping, состав/xdist/cleanup и4 настоящих worker variants приняты. Окончательное включение master остаётся последним условием T093 перед проверками SHA.
T056 final root/config regression: after the report file exists, xdist's early argument scan can treat its external location as configuration discovery input and lose the server's asyncio_mode=auto. Explicit `-c <server>/pyproject.toml` is now passed to collection and every phase. The actual runner regression selects an async test by `-k` with no path, reproduces failure before the fix, and passes afterward. All 3 report tests PASS; F264's 24 previously failing scenarios PASS with PostgreSQL/four workers/reporting, and the previously unreached serial/performance/RLS set is 68 PASS + 1 expected skip. No test is suppressed; source/currentness/release gates remain intact.


T093 завершена после включения окончательного master323c90fc10e0d4e617498af9c9bc2d134d14c49b
из #6997. Проверенная CI-часть этого master побайтно равна импортированному f73c67056;
после разрешения конфликтов все3 audited source hashes совпадают с independent
review. Все новые product/API/contract исправления #6997 сохранены, журнал
проверок объединён без удаления прежних записей. Повтор63-case набора не нужен:
исполняемый runner и его tests не изменились. Окончательные GitHub проверки
нового commit и Full после подготовки релиза остаются отдельными gates.


T094: настоящий Git no-renames перенос и обычный продуктовый путь с обязательным
фрагментом воспроизвели лишний выбор infra. До исправления новый набор:6 FAIL,
21 PASS/1,51 с. Невалидный unreleased-фрагмент действительно давал PASS в
fixture чистого checkout, потому что process preflight без pointer пропускался.
После точной классификации F<digits>.yaml/CalVer и безусловного существующего
preflight:27 PASS/1,61 с. Реальные checker/fragment validator/emit, Git,
отсутствие pointer, обычный server выбор, mixed infra и ранний invalid category
отказ проверены; дорогие стадии в этой fixture подставные. Архивный validator
не расширялся и не объявляется выполненным этим checker.

Связанный полный consumer: test_ci_cd_contract.py + test_ci_guard.py +
test_validator_safety.py:161 PASS/15,42 с. Bash/Ruff/diff PASS. Локальный
process сначала корректно отверг новую временную копию с узким ownership,
не учитывавшим уже включённые104 файла общего F211 PR. Manifest дополнен
существующим ownership F211; это исправление рабочей конфигурации, не bypass.
После согласования ownership настоящий process checker и pinned Spec Kit governance PASS.
Независимый requirements review CHK007 и implementation review T094: PASS.
Проверенные SHA-256: ci-local.sh
5fb44d39332ba5b3e87d6532d4e45e1be0560daf216863cc3ee2f61b3a10e3de;
test_ci_cd_contract.py
3e06f34a43e3dc4d87398d6ecf4f1452823011422892c76f9bdbdb823283b5bf.
Окончательные hosted/Full и время настоящей подготовки версии остаются
отдельной приёмкой; повтор 161 случаев без изменения этих файлов не требуется.


T095: прерывание настоящего cached_asset после os.replace до atomic_json
воспроизвело FileNotFoundError на повторе:1 FAIL/34 deselected до исправления.
Минимальный общий ремонт охватывает cache_inputs и cache_sparkle. Все35 случаев
существующего test_release_artifacts.py PASS/6,17 с; Ruff/scoped diff PASS.
Новый набор доказывает повторную загрузку без remote digest, отказ считать
подменённый orphan того же размера готовым, третье использование без download;
download/size/remote digest/pinned digest failures сохраняют orphan и отсутствие
record, временные файлы убираются. Symlink/dangling обоих путей,
malformed/invalid record, record без asset и каталог вместо orphan дают отказ
без загрузки/изменения состояния. Прежние identity/corruption отказы сохранены.
Рабочий код меняет6 строк; новых helper/lock/format/dependency нет.
SHA-256 release-artifacts.py:
e42ba309385abac28e36ff6662356bdacb4e0af5f8f8b7d485ea9e02b6581926;
test_release_artifacts.py:
c7e562fcd7e2085bca7bf55efa8b9d1d7ef0aa13f3184db613b8f2a62d2503b7.
Независимый implementation review T095: PASS; оба callers и все границы восстановления согласованы. Hashes обоих файлов совпадают с35 PASS; повтор тестов не требуется. Окончательные hosted/Full остаются отдельными gates.

Сверка T094/T095 перед commit: требования FR-003/FR-008/FR-050/FR-051,
SC-022 и обе принятые границы совпадают с реализацией. Независимые reviews PASS;
новых обязательных code gaps нет. Оставшаяся hosted/release приёмка уже
представлена открытыми задачами, новые дубли задач не добавлены.
Ponytail-review последних изменений: существующие функции/stdlib, новых
зависимостей или необязательных механизмов нет; упрощать защиту не требуется.
Changelog/process и pinned Spec Kit governance PASS после согласования
T094/T095. Общий класс риска остаётся high-risk-product F211.


T096: в двух успешных ветвях prepare-release.sh заменена только устаревшая
подсказка. Теперь она предлагает проверить и сохранить всю подготовку, затем
следовать единственной release guidance; ранний git tag и неполный git add
удалены из вывода. Правила и операции подготовки не менялись. Lane этой дельты:
docs-only/mechanical в существующем F211, FR-010. Bash/diff PASS; два прежних
сценария обычной и повторной подготовки:2 PASS/1,82 с. Новый тест, механизм
или повтор Full только для текста не требуется. Изменение подготовлено отдельно
для release-prep, существующие запуски общего PR2557 не затронуты.
