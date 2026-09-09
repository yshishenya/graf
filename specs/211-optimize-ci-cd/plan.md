# Implementation Plan: Быстрый и доказуемый CI/CD

## Active follow-up A2 — 2026-09-09

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

## Active follow-up A1 — 2026-09-09

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
