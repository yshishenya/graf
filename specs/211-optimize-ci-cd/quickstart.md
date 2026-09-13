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
