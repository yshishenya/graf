# Implementation Plan: Быстрый и доказуемый CI/CD

## Active A4 — 2026-09-13

**Lane**: high-risk CI/governance. **Branch**: `codex/211-delivery-optimization`.
**Authority**: user requests completion of the delivery optimization program; validated implementation and the necessary delivery steps are in scope. Research for later trust/artifact changes is separate from this first code slice.
**Constitution pre/post-design**: compatible with 7.0.0, no principle amendment. Product data, permission, release identity and deployment safety remain unchanged. No real app launch is needed for A4's runner contracts.

1. Reorder the two existing lint/compile commands in `.github/workflows/release-full.yml` before `pytest -q tests/governance` and before PostgreSQL. Keep the same commands, all other commands, the shell failure boundary and authoritative aggregation. Extend the existing validator only for the new ordering invariant; prove actual workflow shell with stub commands and failures.
2. In `infra/scripts/ci-local.sh`, remove the two infra-owned CI contract paths from `changed_server_tests` when `has_infra=1`. Reuse the existing deduplication loop; the existing `CI contracts` stage remains the sole owner, with its original failure propagation. No general cache, parser, scheduler or extra test framework.
3. Make CD dry-run say `authoritative_full_required` without candidate and `authoritative_full_reused` for a validated candidate. Keep incident text and all execute gates. Mark nearby historical documentation as historical without rewriting recorded evidence.
4. Add only focused regression cases to `test_ci_cd_contract.py`; use its existing runner fixture. Run both CI contract files and the affected workflow validator/self-test, Bash syntax, Ruff, actionlint and Spec Kit checks once after the slice is complete.
5. Review/converge, record actual results, publish a reviewed PR with exact-SHA GitHub fast. No claim that this small slice reduces the 33-minute successful PostgreSQL phase; E02/E03 own that measured work.

Full program work remains tracked by subsequent tasks, not silently declared complete by this slice. The current research covers resource/fixture minimization, trusted PR metadata/macOS checks, images and packaging.


## Active follow-up A3 / E01 — 2026-09-12

**Anchor**: F211, `codex/211-behavior-test-selection`, base `ad71f2ce4db68d846d7c333213961c5f5f7d5e89` (current master verified by GitHub). A1/A2 merged in #6851; #6845/#6850 closed. Historical text below is preserved as evidence, not current status.
**Lane**: high-risk CI/governance, active Spec Kit continuation. US7, FR-025–030, SC-014–015. Requirements review, analyze and task ownership precede code. Local implementation/tests completed; after validation the user authorized the implementation commit and publication of a PR ready for release inclusion on 2026-09-12. Merge and release gates remain separate.
**Constitution check before/after design**: compatible with version 7.0.0; no principle amendment, product/source/data/secret/publication change. Existing exact-SHA, release-full, deploy and macOS gates remain. No application install or full diagnostic is needed for selector acceptance.
**Tooling**: Bash/Git/Python stdlib and existing pytest/Node. The shared Specify is 1.0.6 but this checkout pins 1.0.1; isolated ignored installation at the pinned commit passes `speckit-bootstrap . --doctor --frozen`. Generated files and lock stay unchanged.

### Smallest shared selection

1. Keep existing `merge_base_commit`/`changed_files` in `infra/scripts/ci-local.sh`. Decode Git NUL-delimited output before the existing line-based classifier, sort/deduplicate and reject control characters explicitly. Include both rename ends and dirty/untracked files. Propagate a bad explicit base or unsafe path as a failure; the unavailable implicit diagnostic base retains bounded fast fallback. Do not copy event-identity logic or change workflow guards.
2. Add one stdlib helper, `scripts/ci-behavior-tests.py`, called by this runner for both local focused and GitHub fast. It owns only the following small map; no dependency graph or separate configuration file.

| Source scope | Required group | Existing targets (server-relative) |
|---|---|---|
| `cabinet/static/**`, `cabinet/templates/**`, `cabinet/rendering*.py` | cabinet-shell and settings | all three files below |
| `cabinet/view_models*.py`, `cabinet/web_routes/settings.py` | settings | `tests/unit/test_settings_view_models.py`, `tests/contract/test_settings_ui_contract.py` |
| A mapped test file, including deletion/rename | its owning group | same group as production selection |
| cabinet-shell group | shared normal/embedded behavior | `tests/contract/test_cabinet_static_assets_contract.py` including the existing rail regression |

All production paths above start with `apps/server/src/twobrain_rec_server/`. Use the whole existing static-asset file to cover neighboring shared behavior, rather than copying selected assertions. Check mapped files contain tests and retain the named rail regression; missing or empty mandatory proof fails before product tests.

3. Public entrypoints: `infra/scripts/ci-local.sh --plan` prints a JSON plan only; `--focused` prints the same plan and runs only these groups in the already prepared server environment. Both reuse the existing diff function and are diagnostic, including dirty trees. A missing diagnostic base gives a partial empty plan; focused execution then fails with guidance. Plan exit 0 means a valid plan, never passing tests. It does not write evidence, install dependencies, start Docker/app or access the network. Empty/unmatched focused execution exits 2. Git/path/proof errors exit nonzero, without a success result.
4. Plan fields: input paths, head SHA, base ref, group names/reasons/targets, `tests`, `covered_tests`, required environment, dirty diagnostic state, partial coverage and next GitHub/release gates. Fast receives `--covered tests/unit` when its existing unit set is selected; remove those covered targets from added execution. Mapped contract files execute in the behavior stage with execution-proof validation; remove them from the later changed-file stage to avoid duplicate execution. Preserve all pre-existing unit/changed/performance/components. Local focused runs the union once. An empty added group starts no behavior stage, while all prior safety stages still run.
5. Fast runs added tests after existing lint/compile and before broad server tests. Use prepared `apps/server/.venv/bin/python -m pytest` and explicit `PYTHONPATH`, argument arrays only; no `uv sync`, Docker or custom environment manager inside the helper. A missing interpreter/Node fails clearly. Clear pytest addopts for this mandatory group and inspect temporary standard JUnit output: each selected file and the named rail test (when selected) must actually execute, with zero skips. Missing/deselected/skipped mandatory proof is failure, not PASS. Existing fast lint still prepares its own server environment as before; full execution remains unchanged.
6. Reuse `run_stubbed_ci` plus real temporary Git repositories in existing CI contracts. First prove unchanged rail test omission. Then verify union/coverage, absent/empty required proof, deletion/rename, spaces/shell metacharacters/Unicode, rejected control characters, no plan side effects, unknown/dirty identity and exact PR/MG/manual behavior. Exercise actual selected tests; negative control reads bad `cabinet.js` from `4fbddd00de10f89fa5644d581f32b6b4d19a7bbd` into a temporary copy, never replacing working source.
7. Update this quickstart, F6792 quickstart and the focused paragraph in release guidance; add the owned F211 changelog fragment. Update existing `check_active_docs` and its contract to accept all explicit supported modes (`--plan`, `--focused`, `--fast`, `--full`) while still rejecting bare CI commands. Align the existing help assertion in `apps/server/tests/contract/test_local_postgres_test_runner.py` with those same public modes. Record measurements and converge locally. Commit/PR/GitHub-fast/merge/live acceptance remain outstanding until their actual gates, never inferred from local PASS.

Optional agent-context hooks are skipped because the ignored feature pointer already identifies F211 and root AGENTS stays stable. The once-per-feature branch creation hook is not repeated for this existing feature. All commit hooks are disabled. Mandatory issue-canon hooks run at task sync.

## Historical follow-up A2 — 2026-09-09

**Feature/branch**: `211-optimize-ci-cd` on `6789-pr-metadata-check`, based on A1 commit `5b436a7a771bd2ff14f47df2e0e328678ad1b066`. The branch number is not a new Feature ID. A1 PR #6846 remains untouched; synchronization with current master is a later publication gate.
**Scope**: US6, FR-019–FR-024, SC-012–SC-013. Additive PR metadata only; current combined workflow, receipts, release and closeout consumers stay unchanged.
**Lane/authority**: high-risk-product (CI/governance). User approved local work and, after its validation, continuation with commit, synchronization with current master, push, draft PR and GitHub checks. No merge, protection update, Full CI or release. A1 stays unchanged in PR #6846; the new publication branch includes A1 + A2.
**Technical context**: Python stdlib and existing Git/gh/pytest; GitHub-hosted Ubuntu; existing actions/checkout v4 pinned to its verified commit. No package installation, application data, new persistent evidence store or runtime dependency.

### Constitution check before research and after design

PASS: current A2 clarify defines scope and authority; spec/checklist/tasks/analyze/issue gates preceded code. No capture, consent, AI, storage, deletion, public distribution or production change. PR text remains untrusted data; only read permissions, no secrets, no privileged pull_request_target. Existing required checks and release evidence are retained. No principle amendment or legacy exception is needed. Independent requirements review passed 10/10, analyze and issue sync passed; T038–T042 are locally complete. Quickstart records tests/review/converge evidence; publication and live acceptance remain pending.

### Design

1. Add `--event <event.json> --current-pr <pr.json>` to existing `scripts/validate-pr-metadata.py`. Keep the body-file CLI, `validate()` contract and self-test compatible. The adapter validates object/field types, open state, matching positive PR number, full head/base SHAs, base ref and checkout HEAD before resolving a real Git diff. Parse NUL-delimited `git diff --name-only --no-renames -z base...head`, including both sides of renames/deletions. Derive Feature IDs using the same spec/changelog ownership rules; call existing `validate()` on current title/body.
2. The current PR JSON is fetched once by authenticated `gh api` from the repository PR endpoint. Use current text even if event text differs; identity drift fails. The result covers that fetched snapshot, not a transactional guarantee against later edits. A stale same-SHA event cannot validate its older body instead of current data. No raw body/API response or token is printed.
3. Add `.github/workflows/pr-metadata.yml`: `pull_request` to master with opened/synchronize/reopened/ready_for_review/edited, one unconditional `pr-metadata` job, five-minute timeout, exact head checkout with full history and no persisted credentials. Permissions are contents:read and pull-requests:read; token only on the API-fetch step. Separate `graf-pr-metadata-<PR number>` concurrency cancels only older runs of this workflow. Body/title never enter shell expressions. API failure is a hard failure with a bounded generic message.
4. This is deliberately PR-only and non-required. Do not modify `.github/workflows/governance-fast.yml`, release workflows, branch protection or receipt/closeout validators. Keeping the combined metadata extractor temporarily avoids changing the current authoritative path during introduction; both paths share the same description validator, not a second set of rules.
5. Add focused cases in `tests/governance/test_pr_metadata_event.py`, reuse existing validator tests in `test_validator_safety.py` and current workflow tests. Exercise actual new workflow shell with a local gh fixture and real Git, including API error, edited current text, fork metadata, invalid identity/JSON/types, scoped/multiple features and rename/deletion ownership. No real API writes, test database or product tests are needed.
6. Add a concise additive-stage note to `docs/agent-guidance/release-and-validation.md` and extend the owned `changes/unreleased/F211.yaml` after issue sync. Record commands/evidence in quickstart. No new user skill, required development stage or installation command.

### Gate for the later cutover (not authorized in A2)

Before making pr-metadata required: implement and test merge_group metadata/identity, current-body freshness, base retargets and code evidence/closeout compatibility; obtain successful exact-input live checks on PRs (including external PRs) and merge groups. Separately authorize and verify both required contexts with strict base protection, without any gap. Only then remove edited-body code reruns; base retarget or changed integrated inputs still require code checks. Failed, missing, skipped, cancelled, stale or ambiguous results are not evidence. Existing Full CI/artifact trust is not broadened. No general result cache or new receipt scheme is introduced here.

### Optional hooks

`after_specify` / `after_plan` agent-context hooks are optional and not invoked: the ignored feature pointer routes this slice and root AGENTS stays stable. Documentation auto-commit hooks are disabled. Requirements review, task sync and its mandatory canon hooks remain separate explicit stages.

## Historical follow-up A1 — 2026-09-09

**Feature**: `211-optimize-ci-cd`; work branch `codex/reduce-delivery-overhead`.
**Scope**: US5, FR-015–FR-018; no application, database, dependency, installed-skill or deploy changes.
**Lane**: high-risk CI/governance. Independent checklist, clean analyze and issue sync precede implementation.
**Authority**: local implementation, requirements reviewer and T033–T037 issue sync approved; no Full CI, commit/push, release, production or live branch-protection change.

Use existing Bash 3.2, Git, Python/pytest and helpers; no new dependency, command or evidence store. Constitution design check: no principle changes or conflicts; spec-first gates must actually pass, not inherit old marks. Privacy/runtime/production gates remain intact.

### Design and validation

1. Add a failing real-Git contract using different event base and `origin/master`. Selection must follow event base and remain stable when the default ref moves; an unavailable explicit base must not fall back.
2. In `.github/workflows/governance-fast.yml`, pass `identity.base_sha` through existing `GRAF_CI_BASE_REF`. Existing identity validation rejects malformed/missing PR/MG SHA; verify that the base commit is available before tests. Manual dispatch retains `base_sha=null` and diagnostic default. Extend `scripts/validate-governance-workflow.py` and `tests/governance/test_governance_workflow.py` to reject a missing binding/guard, covering PR, MG and dispatch.
3. In `apps/server/tests/contract/test_ci_cd_contract.py`, reuse `run_stubbed_ci`: same lint/compile commands execute once before all selected server/changed/performance test stages in fast/full; either static failure prevents tests. Move existing commands in `infra/scripts/ci-local.sh`, preserving selection, performance/RLS and final evidence semantics.
4. Align `docs/agent-guidance/spec-kit-flow.md` and `docs/agent-guidance/release-and-validation.md` with already-correct AGENTS/development-process/infra README: local focused → mandatory GitHub fast; local wide fast only diagnostic/fallback. Review `.github/pull_request_template.md` unchanged: it already names GitHub fast as mandatory and local CI as diagnostic/fallback. Its installed extension owns the template; do not patch generated copies. Add `changes/unreleased/F211.yaml`, not root CHANGELOG.
5. Run focused CLI contracts, workflow tests/validator/self-test, Bash syntax, Ruff, whitespace and active-doc consistency. Stubbed full is not real Full CI. Report ordering and fail-fast proof, not an invented speed percentage or a new SC-009 benchmark.
6. After separately approved publication, GitHub `governance-fast` on exact PR SHA remains mandatory. Existing authoritative GitHub `release-full` and immutable evidence reuse at deploy remain separate release gates; no deploy command is run in A1.

### Deferred metadata-check migration

Keep check names, events, permissions, concurrency and closeout trust unchanged in A1. A later slice first adds metadata checks while retaining the combined required gate; with separate approval it activates and verifies both required contexts; only then removes duplicate edited-code runs. Cover separate concurrency, base retargeting, forks, merge_group, failed/skipped/cancelled runs, expired/ambiguous artifacts and workflow/closeout validators. A skipped required job is not code PASS. A1 does not claim to eliminate edited reruns.

## Historical plan — 2026-08-30 (not current instructions)

The remaining plan describes completed T001–T032. Its full-inside-execute design and release approval are superseded; do not use them for A1. Current contract: one authoritative GitHub `release-full` result, verified and reused by deploy. Historical validation/evidence is preserved.

**Branch**: `211-optimize-ci-cd` | **Date**: 2026-08-30 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/211-optimize-ci-cd/spec.md`

## Summary

Убрать три причины лишнего времени: неявный `full` без выбранного lane, скрытое расширение явно запрошенного `fast` до full и ручной full перед тем же deploy. Общий runner требует явный lane, `fast` всегда остаётся ограниченным и выбирает затронутые компоненты, а `cd-remote.sh --execute` после синхронизации exact SHA выполняет один authoritative full. Все остальные production gates остаются без изменений.

## Technical Context

**Language/Version**: Bash 3.2-compatible shell; existing Swift and Python application toolchains unchanged

**Primary Dependencies**: Git, `shasum`, existing `uv`, pytest, SwiftPM, Docker Compose; no new dependency

**Storage**: No new storage

**Testing**: pytest contract tests invoking the CLIs in disposable repositories; focused shell syntax checks; feature quickstart; explicit `--fast`; final `--full`

**Risk / Validation Lane**: high-risk feature — infrastructure, validation governance and production preflight behavior change

**Release Gate**: user approved commit, push, PR, merge, tag, release and production execute

**Target Platform**: trusted macOS release workstation plus Linux-compatible shell paths used by server test/deploy helpers

**Project Type**: monorepo with macOS desktop app, Python server, local CI and SSH-driven production CD

**Performance Goals**: every explicit fast run avoids the repository full suite; small server-only changes avoid Swift validation; macOS-only changes avoid PostgreSQL/server validation; component-only fast p50 is at most 25% of the `1406.36s` full baseline; the normal execute flow runs full CI once before remote production actions

**Constraints**: unknown/shared/high-risk fast runs must report partial coverage and a required release full without starting full; preserve security/privacy/RLS/backup/smoke/rollback/notarization gates; Bash 3.2 compatibility

**Scale/Scope**: one local CI entrypoint, one deploy entrypoint, one server test runner, active operator guidance and contract tests; immutable image registry delivery excluded

## Constitution Check

*GATE: Passed before Phase 0 and re-checked after Phase 1.*

- **Spec-first / high-risk governance**: PASS — specification, clarification scan, plan, contracts, quickstart, checklist, tasks and analyze precede implementation.
- **Privacy and secret custody**: PASS — no new persisted evidence or sensitive data path.
- **Security and trust boundaries**: PASS — authoritative full runs only after exact-SHA sync and cannot bypass the remaining production gates.
- **Testability and evidence**: PASS — CLI/deploy ordering and failure paths have runnable contracts; final full repository gate remains required.
- **Minimality / dependency policy**: PASS — receipt helper and local attestation complexity are deleted; no dependency is added.
- **Release integrity**: PASS — exact-SHA, backup, restore, RLS, secret, health, smoke and rollback rules remain untouched.

Post-design re-check: PASS. The design uses the existing deploy entrypoint for the single authoritative full and preserves the remote runtime path.

## Validation Plan

1. Static/focused: `bash -n` for changed shell scripts; Ruff/Python compile; CLI contract and documentation consistency tests.
2. Contract scenarios: missing mode, component mapping, invariant that fast never becomes full, partial-coverage reporting for unknown/shared paths, dirty-tree rejection, post-full candidate drift and deploy ordering.
3. Feature quickstart: exercise real CLI help/error and deploy dry-run without production access.
4. Repository fast lane: run explicit `infra/scripts/ci-local.sh --fast`; this infrastructure diff must stay fast, run its bounded CI-contract/static checks and report that release full is still required.
5. Repository full lane: run once on the frozen PR candidate after review.
6. CD: after merge, run dry-run and approved execute from synchronized `master`; execute owns the authoritative full.
7. Consistency: compare active guidance, PR template, `--help`, contract and actual output; scan active docs for bare ambiguous CI invocation.

## Project Structure

### Documentation (this feature)

```text
specs/211-optimize-ci-cd/
├── spec.md
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── ci-cd-cli.md
├── checklists/
│   ├── requirements.md
│   └── operational-readiness.md
└── tasks.md
```

### Source Code (repository root)

```text
infra/scripts/
├── ci-local.sh
├── cd-remote.sh
└── README.md

apps/server/
├── scripts/run_local_postgres_tests.sh
└── tests/contract/test_ci_cd_contract.py

docs/agent-guidance/release-and-validation.md
docs/current-product-status.md
.github/pull_request_template.md
AGENTS.md
CHANGELOG.md
```

**Structure Decision**: Keep orchestration in the two existing operator entrypoints and behavioral contracts in the existing server contract tests. Add no helper, service or dependency.

## Complexity Tracking

No constitution violations or new architectural layers require justification.


## A5 implementation design

Constitution 7.0.0 PASS: test infrastructure only; real RLS, transactions, deletion/privacy checks retained. Existing high-risk lane and F211 ownership. No new dependency.

1. Register `postgres` from pytest fixture dependency closure in existing `tests/conftest.py` (root resource fixtures `postgres_worker_database_url`, `postgres_clean_database_url`, `postgres_advisory_lock`). Run pure unit first with `-m 'not postgres and not browser'`, then resource unit with `-m 'postgres or browser' -n 4 --dist=loadfile`; preserve ordinary/performance/strict Full. Explicit marker covers future tests creating their own DB. Mark all three current skipped Playwright scenarios browser and fail before test execution if browser dependencies are missing; prepare pinned Playwright/Chromium in both hosted jobs, reuse one package-lock under tests/browser. Pure never needs Docker or browser installation. Remove account-close module skip; DB fixtures already fail closed. Inventory current collection and ensure the union and disjointness.
2. Move argument validation before Docker in the existing PostgreSQL runner. Explicit help and collection-only exit through prepared pytest before resource startup. One `--collect-only` is inventory, never release evidence. Keep generated names, loopback ports, cleanup, worker/role safeguards.
3. Rename existing `_create_ready_meeting` to public `create_ready_meeting`, retaining its original behavior and defaults. Replace only inspected single-ready families with that existing helper; keep list/foreign/multi-state cases unchanged. Measure before/after via same isolated runner and exact selected node IDs.
4. Pin Python 3.13 via server `.python-version` and hosted env/Node setup. Use frozen resolution. Add optional metadata-only JSONL directory to existing runner, unique file per phase. Existing pytest hooks write only relative file, hashed node ID, when/outcome/duration in controller; workers do not write reports. Never serialize longrepr, properties, output or SQL. Upload only that report directory. Assert actual collection union is nonempty and disjoint before Full.
5. Tests before implementation, focused DB acceptance, targeted runner/governance checks and review/converge. Final hosted Full on the final frozen candidate provides full regression coverage once; no repeated local Full after every edit.

A5 report identity: upload `graf-test-timings-<requested_sha>-<run_id>-<run_attempt>` from RUNNER_TEMP, with unique `<phase>.jsonl` names. Existing authoritative evidence continues to identify the same requested SHA/run/attempt. The reports never claim independent PASS. Collection can run once before Docker; pytest emits the actual marker-based phase inventory and the runner checks its nonempty disjoint union before execution, replacing repeated collection of the same suite.


## A6 implementation design

High-risk CI/governance; constitution 7.0.0 PASS, read-only permissions and existing owner trust retained. Research confirms native merge queue/required workflows unavailable for the personal repository; no migration or external service.

1. Reuse `ci-event-identity.py` in a small `scripts/ci-pr-scope.py`: validate exact head/base and NUL Git diff, classify only exact title/body edits as text-only, conservative native scope otherwise. Pure documentation means Markdown notes/specs/changelog and owned changelog fragments. Independent server modules can skip native, while API/cabinet/shared/unknown/native paths require it. Explicit reasons are outputs. Failure of scope causes a failed required final check.
2. Add `.github/workflows/macos-pr.yml`: scope on Ubuntu; conditional macos-14 Swift 6.0.3 build/tests/ContractValidation; unconditional result assertion with stable required name `macos-pr`. A proven text edit validates existing exact-head/base native proof instead of executing native again; a skipped native job alone never authorizes merge. Existing local/Full Swift runner and native execution concurrency are retained. No application installation or manual app launch.
3. Extend existing metadata validator with explicit trusted-policy SHA and optional second current snapshot/result output. Keep legacy event CLI requiring PR checkout. Trusted mode verifies checkout=policy SHA, repository identity, exact Git object availability and before/after snapshots, then reuses current title/body validation. Target workflow checks out `github.workflow_sha`, fetches only exact SHA Git objects (no PR code checkout), uses `python3 -I`, read-only GitHub token only for API, safe metadata artifact tied to run/attempt/head/base/policy/hash.
4. First publication retains combined governance-fast metadata execution. After the foundation merge, verify trusted target checks on the cutover PR, add `pr-metadata` and `macos-pr` to required GitHub contexts without removing governance-fast, read back strict/app IDs. After cutover, the existing governance-fast job keeps a stable required name: exact text-only events skip expensive steps/new receipts and validate existing source proof; genuine code events retain current receipt v1 and tests. Separate text concurrency never cancels code/native. A skipped job or an unconditional text PASS cannot replace source validation. The initial different-name design was disproved by GitHub's live expected-check state; FR-040 now specifies validated reuse.
5. Extend existing closeout/release consumers through one reusable live PR check validator. Pin the foundation commit as the historical policy boundary after it exists; do not invent its SHA. New PRs require correct workflow/event/head/conclusion for all three checks and fresh current body validation. Historical pre-cutover evidence remains valid; post-merge identity uses final head and merge ancestry. The current personal-repo train remains serial; no unsupported live merge-group claim.
6. Verify with existing metadata/event/workflow/closeout/train tests and executable shell/event fixtures. Use no new runtime dependency. Record actual activation and final-SHA hosted checks separately from local proofs; update active guidance and owned changelog only after the switch.

A6 consumer implementation details: one `.github/pr-check-policy.json` records the actual foundation SHA/PR and successful protection read-back UTC timestamp. Policy selection uses merged_at < activation only for already merged PRs; open PRs never qualify for the historical exemption. New policy requires code receipt + native scope + metadata snapshot at common head/base and correct run/attempt; current API base for open PRs, exact squash parent or linear rebase-range predecessor plus equal final trees for merged PRs. Trusted metadata refresh also supports verified merged closed PRs and derives the checked base from their immutable merge, retaining double snapshot checks; closed/unmerged is rejected. No missing artifact or ambiguous merge falls back to old policy. Consumers use existing Git/GitHub data and validators; no new external service.

### A6 исправление последнего набора GitHub checks (T080–T081)

Минимальный scope: две существующие workflow, `scripts/validate-pr-checks.py`, `scripts/validate-governance-workflow.py`, три целевых governance test modules и соответствующие A6 документы/фрагмент F211. A8/A9/A10, Full CI, состав продуктовых тестов и branch protection не меняются. До code edits обязательны независимый requirements PASS, чистый analyze и issue evidence.

1. В `.github/workflows/governance-fast.yml` сохранить существующий job ID и постоянное display name. После успешного scope общими остаются exact checkout и guards допустимого `text_only`; text-only step вызывает компонентную проверку. Все installation/fixture/browser/fast/terminal/receipt/upload steps получают условия ветви кода, включая `always()` cleanup/evidence steps. Scope failure/неизвестное значение завершают required check ошибкой. Текстовая concurrency уникальна по run ID и не отменяет существующую code group.
2. В `.github/workflows/macos-pr.yml` существующий `result` становится постоянным `macos-pr`; заменить `TEXT_ONLY=true → exit 0` на компонентную проверку. Сохранить `true:success|false:skipped` для обычного native scope. Native job/concurrency остаются прежними. Ожидание исходного native выполняется на Ubuntu с конечным timeout, покрывающим нынешние 30 минут native с запасом; нынешние 2 минуты result недостаточны для body edit во время тестов.
3. В `scripts/validate-pr-checks.py` выделить валидацию одного исходного компонента из `current_run()` / `validate_bundle()` и добавить узкий CLI для точного текущего text event/run. Использовать существующие metadata/scope/receipt helpers и stdlib. Выбор без фильтра success, по `run_started_at`/run ID, с точным run attempt. Исключать лишь проверенные text scope artifacts; не полагаться на `*-text-change` или невычисленное имя пропущенной задачи. Текущий self-run исключается только после собственной проверки scope/event/API identity.
4. Повторно используемый source всегда является реальным code/native run: текущий native scope `text_only=false` и фактические native jobs либо исходный code receipt. Не создавать new source receipts/новый reuse artifact format или цепочку text proofs. Публиковать в summary только source run/attempt/head/base и ссылку. Срок хранения и существующая artifact identity сохраняются.
5. Известный running/queued source проверять с ограниченным ожиданием: source terminal success → проверка proof; source failure/cancel/timeout/API failure → ошибка. Каждый проход обновляет актуальность; финальные PR identity и source run/attempt перечитываются перед PASS. Подтверждённые text scopes исключаются независимо от окончания их итогов, чтобы отсутствовало взаимное ожидание. Полный `verify()` выбирает последний соответствующий workflow run/attempt **включая text**, затем требует его terminal success и ровно один успешный job с fixed required name, точной repository/PR/head/base/workflow/event identity. Не использовать status rollup или поиск последнего success. Перед общим PASS повторно выбрать и сверить source attempts **и gate attempts всех компонентов**, а не только PR snapshot: same-SHA rerun во время проверки native/metadata должен блокировать старый набор. Текстовый компонентный режим не вызывает полный `verify()` и не ждёт metadata/другой компонент.
6. Права только `contents: read`, `pull-requests: read`, `actions: read`; никаких Checks/Actions write, dispatch, новых credentials или исполнения downloaded artifacts. Native result и text governance выполняют только Python/gh/API/scope работу; новые runtimes не устанавливаются. Для governance остаётся timeout 45 минут, внутреннее ожидание меньше бюджета job. Partial rerun не получает исключения для старого scope attempt; whole text rerun остаётся дешёвым.
7. Сначала T080: исполняемые API/selection/terminal-shell tests, включая later retry, two simultaneous text runs, self-run exclusion, required-gate failure и no heavy commands/new receipts. Затем T081: минимальная реализация, актуальный workflow validator, targeted suite/actionlint и reviewer. Hosted acceptance выполняет основной агент на новом exact SHA, наблюдая реальный merge box, отсутствие `expected` и отсутствие отмены/повтора source tests; локальный API mock этого не доказывает.

Не выбран простой отказ от `edited`: retarget/неизвестные события перестанут запускать код. Не выбраны job skip или `exit 0`: они могут разрешить merge после failed/running source. Отдельный dispatcher, статус через write API и новые result jobs не нужны для этого объёма.


## A7 implementation design

Constitution 7.0.0 PASS, existing high-risk test infrastructure lane. Reuse the already measured ready helper; no new dependency or test framework. Research traced every direct/indirect caller and embedded browser assertions.

1. Baseline the same 14 files using the existing isolated PostgreSQL runner, Python 3.13/frozen lock, xdist 4/loadfile and safe timing reports. Inspect collection parity.
2. Replace direct single-ready setup only within the research allowlist. Keep the six exact exclusions on the complete fixture. In comments use `setup_comments(client, *, full_seed=False)` returning the existing tuple; the minimal single-ready container is `types.SimpleNamespace(ready_id=create_ready_meeting(client))`. Missing non-ready attributes fail loudly; no widened optional CabinetSeed fields. Two negative callers explicitly use full_seed=True.
3. Run the same files and compare safe node hashes/outcomes with baseline; preserve original assertions and call sites for actual behavior. Review diff for exception identities, Ruff and existing fixture contracts. Existing Full later covers the full final candidate once.


## A8 implementation design

Constitution 7.0.0 PASS, high-risk infrastructure lane. Existing Docker/Compose, Python stdlib, deploy lock, candidate validation, backup and rollback functions remain the mechanism. No registry/credential/service is added.

1. Split Dockerfile into frozen dependencies, application install-prefix, media dependencies and the two existing final targets. Copy only the project install prefix into final images; retain /app scripts/src/config/resources. Attach requested SHA after costly layers. Preserve the base image pin and FFmpeg snapshot/version.
2. Add one small `infra/scripts/release-images.py` for Docker metadata preparation and create-once attempts. Read resolved Compose in memory, persist only safe image references/IDs. Capture previous before any builds from container IDs (checked project/service labels), prior manifest or individual previous refs. Derive previous Compose using git show without changing checkout. Existing top-level project name is twobrain-rec. All six runtime services and the one media service derive their targets from Compose; rec-minio-init is a third-party minio/mc image, not an application build. Reject unknown build targets.
3. Prepare/cached-validate runtime/media using --iidfile and source SHA labels, plus native Docker platform. Reuse an existing third-party image only when its old/new refs match; changed refs are pulled before downtime. Save candidate and previous overrides and hold IDs under explicit graf-release tags. An unfinished attempt causes a bounded failure, never overwrites its baseline.
4. `cd-remote.sh` forwards already validated candidate ID, decision digest and Full digest. Runtime copies the helper into its private attempt location before any reset, prepares images before backup/mutation, and appends the candidate override to existing compose array. Build/pull failure triggers source restoration while runtime_mutated=0.
5. Downgrade and compatibility remain candidate. Only restore_previous_services / restore_previous_safe_processing_runtime switch to previous override after permitted schema decisions and source reset; delete their rebuilds. Ensure explicit no-pull and correct CLI options. Capture/verify actual service IDs after recreate, retain existing readiness/network/poller/dispatch decisions.
6. Pass override to run-production-smoke.sh (including its cleanup), not only COMPOSE_FILE env, because it currently supplies explicit -f. Preserve standalone smoke without an override and validate supplied metadata-only mapping. Final attempt result is persisted before clearing the trap. Only verified unchanged runtime or successful recovery of all existing gates (including public download) closes a failed attempt. Failed rollback, compatibility/forward-fix or uncertain state preserves the active baseline and requires recovery. EXIT trap execution alone proves nothing. Failure to persist baseline/helper/overrides fails before stop; final-write failure never reports deploy_result=pass or unlocks the incomplete attempt (including disk-full).
7. Focused executable lifecycle tests with Docker CLI stubs, existing deployment/rollback/smoke contracts, real local two-target cache/resource check, review/converge; final exact-SHA Full and release dry-run separately. No production traffic is changed during local validation.

### A6 review correction T087

Reuse `metadata.checked_base` in `ci-pr-scope.resolve` and code snapshots,
preserve actual merged SHA, and allow valid merged title/body events through
the existing component verifier. Name governance uploads by run ID/attempt;
use exact-first legacy-compatible reading in the shared artifact loader.
Execute real Git history and fake-provider ZIP regressions before acceptance;
retain full-consumer metadata/source/gate validation. No workflow dispatcher,
new evidence schema, product-test change, or permission expansion is needed.

T090 completes the same historical-PR contract: keep the primary checkout at
the exact event head, but read scope/reuse tools from `github.workflow_sha` in
a second sparse `.ci-tools` checkout. Scope always uses those tools; result
jobs obtain them only for proven text events. The verifier resolves sibling
helpers/policy beside its own file while Git still reads the primary checkout.
The shared release PR-check subprocess runs with `cwd=root`, matching the
script's other Git readers. Regressions cover old heads without these tools,
real merged history, failure propagation and invocation from another directory.
Post-merge acceptance must edit an older merged PR (#6991), as well as #6990.


## A9 implementation design

High-risk macOS release infrastructure, constitution 7.0.0 PASS before research
and after design. Existing F211/US9 and public Developer ID/Sparkle gates; stdlib
only. Architecture research completed independently on current scripts.

1. Keep installer scratch under a separate `.build/installer-cache/<key>`;
   hash resolved checkout identity, Swift version, SDK version/build/path,
   Package.swift/resolved and fixed release build arguments. Derive per-triple
   scratch paths under that key. Never omit swift build on cache hit. One
   checkout lock covers shared packaging output and GRAF.app; retain both arch
   and all resource/license/signature checks. Emit a safe source/input/output
   build receipt for notarization from the public clean-source build.
2. Add one bounded Python stdlib helper `apps/macos/Installer/Scripts/release-artifacts.py`
   for content fingerprints and local prepared-state persistence. Reuse existing
   shell validators and platform commands for trust; do not implement cryptography
   or a release service. State remains under ignored `.build`, no secret paths or
   credentials in JSON. Atomic replace + file/directory fsync; no terminal success
   after a failed persistence acknowledgement. Lock/stale-state refusal explicit.
3. Move prepare-app-update.sh's current staging lock before existing-state checks.
   Same-version archive → verify saved full input identity/output hashes, rerun
   current signature/public-trust validation and return unchanged. Otherwise keep
   strict version increase and existing working/backup directory replacement.
   Produce checksum/public attestation with the signed files before recording the
   state, so the complete final output set is immutable and atomically staged.
4. sign-graf-app-update-local.sh keeps its lock and temporary safe extraction,
   Developer ID/team/designated requirement checks; packaged startup checks execute
   once inside the final upload boundary after public validation. Cache
   only checked Sparkle ZIP by the existing pinned hash; always rehash and extract
   into the same temporary replacement/restore path. Persist checked input asset
   IDs/release IDs/source/hash/size in local cache; on mismatch fail, not silently
   change the requested release. Fresh Keychain verifier remains every invocation;
   prepare also validates retained public attestation, including its original TTL.
5. Replace --clobber with a bounded helper upload of the existing four assets.
   Reuse `prepare-app-update.sh --verify-only` at the upload boundary for the
   complete public/Keychain/Sparkle validation, then lock/recheck prepared hashes
   and run both startup checks. It cannot sign or replace an absent version.
   Preflight all names before any mutation; same digest/size skips, absent uploads.
   If GitHub lacks digest, download and compare. Refetch exact draft/source identity
   before each upload and final readback. Interrupted upload reconciles matching
   remote bytes without overwrite. No automatic GitHub Release publication/feed
   switch, no claimed atomic transaction against a concurrent owner publication.
6. Add helper notarize subcommand around xcrun notarytool using the build receipt.
   Keep immutable submitted ZIP/PKG and safe state in one per-version/source local
   directory, copy app only as a packaging artifact, never launch/register it.
   Durable submitting intent precedes submit; durable ID precedes next submit.
   Submit both before waiting; known IDs use bounded info/wait. Unknown ID is a
   blocked ambiguous attempt, never guessed from history. Resume only with proven
   Apple log/response digest binding. Accepted stages staple separate working copies,
   run codesign/stapler/Gatekeeper, recreate final ZIP, atomically retain final hashes.
   Repeating a completed attempt validates the same public output without resubmission.
7. Existing shell signing tests + focused executable Python lifecycle regressions,
   shell syntax/Ruff and native packaging contracts; independent review/converge.
   Final hosted checks/Full and real notarized release validation are distinct.
   Keep operator commands and general MD plan aligned with the actual final path.


## A10 implementation design

Active high-risk F211 continuation, FR-055 / SC-023; constitution unchanged.
Reuse the existing runner collection and strict/performance marker partition.
An explicit --partitioned option is valid only with --focused; only the
run_changed_server_tests caller enables it. Preserve each selector unchanged; use an exact phase selector in the existing
test_resources.py plugin and the shared phase function for inventory. Avoid
prefix-based --deselect, which can drop similarly named cases. Reject conflicting xdist flags
before Docker. Use the existing worker databases and cleanup. Tests precede code.
No dependency, new general scheduler or product database change is required.

## A11 source-template correction

High-risk active F211 governance continuation, constitution unchanged. FR-056 /
SC-024 полностью определены существующим bootstrap install-if-missing contract.
В source extension изменить только условие копирования PR template, нейтрализовать
названия GRAF checks в общем шаблоне и добавить regression в существующий unittest.
Выпустить patch SemVer расширения и обновить GRAF штатным pinned bootstrap путём;
сохранить проектный template с тремя required checks и протестировать два ensure.
Исполняемый bootstrap уже сохраняет файл; его чужие dirty edits не менять.
Requirements reviewer → analyze → owner #6986 → implementation → review/checks.

## A12 — закрытие конкретных пробелов качества тестов

Existing high-risk F211; FR-057/058, SC-025, constitution unchanged. До кода:
requirements review → clean analyze → task ownership. В существующем
`test_cabinet_static_assets_contract.py` заменить только word-search CSRF test
на Node vm execution реального обработчика и объявления токена, с событием и
проверкой headers; переиспользовать текущий subprocess pattern. Не требуется
браузер для этой границы. Серверный `test_cabinet_csrf.py` остаётся настоящим
отрицательным HTTP/DB подтверждением. Из `test_config_validation.py` убрать один
AST-идентичный дубль, сохранив web/non-web/file cases. Дополнительно закрыть два
изначально найденных дубля E05.04: скалярный cookie-name из
`integration/test_web_owner_session_context.py` уже проверяется тем же импортом в
`unit/test_auth_web_session_context.py`; три forbidden-readiness вызова из
`contract/test_deployment_readiness_contract.py` уже проверяются в
`unit/test_deployment_helpers.py`. Доказать равенство AST/импортов/параметров,
оставить независимый буквальный список unit, прочие проверки/fixtures не менять.
В full ветке существующего
PostgreSQL runner только переставить strict → performance → parallel; selectors
и состав не менять. Расширить существующий synthetic pytest/Docker contract для
полного режима, порядка, отказов каждого раннего этапа и cleanup. Отдельно
выполнить реальную strict/performance группу и конечный Full на frozen source.

### A12 T088: remove hidden bootstrap skip

Add one narrowly used function fixture in tests/fixtures/postgres_test_database.py,
imported by test_playback_normalization_postgres.py. Reuse prepare_schema, URL
validation and stdlib subprocess; use existing Docker/postgres image with the
same bounded final-postmaster readiness criterion. Switch only the bootstrap
proof to this URL and turn impossible owned-cluster preconditions into FAIL.
Do not change phase scheduling or production scripts. Verify failed setup
cleanup and run the real media-before-bootstrap file and strict/performance
group with unchanged collection, expecting69 PASS/0SKIP instead of68/1.

### A12 T089: require the existing synthetic media tests

Replace only FFmpeg-related skips in media_matrix, workflow and authorized
TestRec integration files with a clear failure. Keep TestRec directory opt-in
first. Add conditional FFmpeg preparation to the existing resource steps in
`.github/workflows/release-full.yml` and `governance-fast.yml`; never install
for non-server PR paths. Reuse system packages and existing tests. One focused
contract file exercises the three real missing-tool entrypoints and retained
private opt-in; existing `test_governance_workflow.py` executes both actual
resource shell blocks with synthetic commands. Check working/missing/broken
tools, failed install, and non-server fast scope. Actual acceptance runs the
unchanged 49-case media matrix plus one dual-source workflow test exactly once,
with metadata-only collection/outcomes and no private audio. Requirements
review, issue6994 ownership and clean analyze precede implementation.

T091 convergence after hosted native failures is test-only: the existing signing
entrypoint contract follows the actual upload helper and its bound input record;
the notice test waits for panel removal with ContinuousClock and a finite10 s
deadline. Existing nonactivating/replacement/dismissal assertions stay; production
6 s notice lifetime and30 s capture threshold are unchanged. No new runtime
helper, injected clock or test framework is needed.

T092 addresses hosted evidence34770443870. Initial suspicion that only the
absolute corruption offset10700 differed was disproved by the independent
Ubuntu24 experiment: FFmpeg6.1.1 also reports actual interior-frame errors but
returns0 with -xerror; local8.1.2 returns183. The fixture must prove its strict
failure on both versions before testing unchanged recovery/output assertions.
The concrete corruption is selected from that evidence. Do not silently weaken
runtime policy or accept/skip a missing recovery. If a runtime defect is found,
reassess that scope before implementation.


T092 выбранный и принятый вариант: настоящий ffprobe находит первый аудиопакет,
helper сохраняет4-байтовый заголовок и повреждает следующие32 байта. Первый
пакет даёт подтверждённый strict failure и на6.1.1, и на8.1.2. Проверка5.1.9
из production-образа также прошла; recovery/выход/число subprocess проверяются
старыми assertions. Независимый review PASS, новые зависимости не требуются.
