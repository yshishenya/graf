# Implementation Plan: Быстрый и доказуемый CI/CD

**Branch**: `211-optimize-ci-cd` | **Date**: 2026-08-30 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/211-optimize-ci-cd/spec.md`

## Summary

Убрать две причины лишнего времени: неявный `full` при запуске общего CI и повтор того же `full` внутри deploy. Общий runner потребует явный lane, `fast` выберет затронутые компоненты консервативно, а успешный чистый `full` создаст локальную metadata-only receipt для exact SHA. Deploy переиспользует только свежую receipt с совпадающими runner/dependency/test/toolchain inputs; любое расхождение запускает обычный `full`. Все остальные production gates остаются без изменений.

## Technical Context

**Language/Version**: Bash 3.2-compatible shell; Python 3 standard library for deterministic JSON receipt; existing Swift and Python application toolchains unchanged

**Primary Dependencies**: Git, `shasum`, existing `uv`, pytest, SwiftPM, Docker Compose; no new dependency

**Storage**: One local receipt under the worktree Git metadata directory; no application database or production storage change

**Testing**: pytest contract tests invoking the CLIs in disposable repositories; focused shell syntax checks; feature quickstart; explicit `--fast`; final `--full`

**Risk / Validation Lane**: high-risk feature — infrastructure, validation governance and production preflight behavior change

**Release Gate**: no deploy in this task; `cd-remote.sh --dry-run` only. `--execute`, push, tag, release and commit require separate approval

**Target Platform**: trusted macOS release workstation plus Linux-compatible shell paths used by server test/deploy helpers

**Project Type**: monorepo with macOS desktop app, Python server, local CI and SSH-driven production CD

**Performance Goals**: small server-only changes avoid Swift validation; macOS-only changes avoid PostgreSQL/server validation; component-only fast p50 is at most 25% of the `1406.36s` full baseline; one unchanged exact release candidate runs full CI at most once before deploy

**Constraints**: fail closed for unknown/shared/high-risk paths and invalid receipts; preserve security/privacy/RLS/backup/smoke/rollback/notarization gates; no secrets or private content in receipt; Bash 3.2 compatibility

**Scale/Scope**: one local CI entrypoint, one deploy entrypoint, one server test runner, active operator guidance and contract tests; immutable image registry delivery excluded

## Constitution Check

*GATE: Passed before Phase 0 and re-checked after Phase 1.*

- **Spec-first / high-risk governance**: PASS — specification, clarification scan, plan, contracts, quickstart, checklist, tasks and analyze precede implementation.
- **Privacy and secret custody**: PASS — receipt contains only hashes, versions, counts, timestamps and result; no meeting content, credentials, secret paths or signed URLs.
- **Security and trust boundaries**: PASS — invalid/missing receipt expands to full CI; receipt cannot bypass clean tree, remote sync, exact SHA, backup, restore, RLS, secret, health, smoke or rollback gates.
- **Testability and evidence**: PASS — positive and negative CLI/receipt/deploy paths have runnable contracts; final full repository gate remains required.
- **Minimality / dependency policy**: PASS — reuse shell, Git and Python stdlib; no service, framework, remote attestation system or registry is added.
- **Release integrity**: PASS — implementation does not deploy or publish; notarization and product release rules remain untouched.

Post-design re-check: PASS. The design stores the receipt outside the working tree, binds it to exact immutable inputs, and preserves the existing remote runtime path.

## Validation Plan

1. Static/focused: `bash -n` for changed shell scripts; Python compile; receipt/CLI contract test file; documentation consistency test.
2. Contract scenarios: missing mode, component mapping, unknown/shared escalation, receipt create/validate, stale and mismatched receipt, dirty-tree rejection, deploy reuse and fallback.
3. Feature quickstart: exercise real CLI help/error and disposable receipt cases without production access.
4. Repository fast lane: run explicit `infra/scripts/ci-local.sh --fast`; this infrastructure diff must conservatively expand to full.
5. Repository full lane: run explicit `infra/scripts/ci-local.sh --full`; because the tree is intentionally uncommitted, it may pass while reporting receipt creation skipped for `dirty_worktree`.
6. CD: run `infra/scripts/cd-remote.sh --dry-run --branch 211-optimize-ci-cd`; do not execute production.
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
├── ci-receipt.py
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

**Structure Decision**: Keep orchestration in existing operator entrypoints, add one stdlib helper solely for receipt canonicalization/validation, and keep behavioral contracts with the existing server contract tests. Documentation changes are limited to active sources of operational truth plus the current-status/changelog record.

## Complexity Tracking

No constitution violations or new architectural layers require justification.
